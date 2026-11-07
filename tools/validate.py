import datetime
import json
import sys

REQUIRED = ["draw_date", "program", "program_key",
            "number_of_invitations", "crs_cutoff", "source_url", "harvested_at"]
CANADA = "https://www.canada.ca/"

def validate_rounds(doc: dict) -> list[str]:
    errors = []
    draws = doc.get("draws") or []
    if not draws:
        errors.append("no draws")
        return errors

    seen = set()
    last_date = None
    for r in draws:
        n = r.get("draw_number")
        for key in REQUIRED:
            if r.get(key) in (None, ""):
                errors.append(f"draw {n}: missing {key}")
        if n is None and not r.get("number_source"):
            errors.append(f"{r.get('draw_date')}: null draw_number needs number_source")
        ident = n if n is not None else (r.get("draw_date"), r.get("program_key"))
        if ident in seen:
            errors.append(f"draw {n}: duplicate draw_number")
        seen.add(ident)

        try:
            d = datetime.date.fromisoformat(r["draw_date"])
        except Exception:
            errors.append(f"draw {n}: bad draw_date {r.get('draw_date')!r}")
            d = None
        if d and last_date and d < last_date:
            errors.append(f"draw {n}: dates not monotonic")
        if d:
            last_date = d

        c = r.get("crs_cutoff")
        if not isinstance(c, int) or not 0 <= c <= 1200:
            errors.append(f"draw {n}: crs_cutoff {c}")
        i = r.get("number_of_invitations")
        if not isinstance(i, int) or i <= 0:
            errors.append(f"draw {n}: invitations {i}")
        if not str(r.get("source_url", "")).startswith(CANADA):
            errors.append(f"draw {n}: source_url not canada.ca")

    return errors

if __name__ == "__main__":
    doc = json.load(open(sys.argv[1], encoding="utf-8"))
    errs = validate_rounds(doc)
    print("\n".join(errs) if errs else "rounds ok")
    sys.exit(1 if errs else 0)
