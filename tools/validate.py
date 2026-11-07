import datetime
import json
import sys

REQUIRED = ["draw_date", "program", "program_key",
            "number_of_invitations", "crs_cutoff", "source_url", "harvested_at"]
CANADA = "https://www.canada.ca/"

def _is_number(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)

def validate_rounds(doc: dict) -> list[str]:
    errors = []
    draws = doc.get("draws") or []
    if not draws:
        errors.append("no draws")
        return errors

    seen = set()
    last_date = None
    last_number = None
    for r in draws:
        n = r.get("draw_number")
        for key in REQUIRED:
            if r.get(key) in (None, ""):
                errors.append(f"draw {n}: missing {key}")
        if n is None and not r.get("number_source"):
            errors.append(f"{r.get('draw_date')}: null draw_number needs number_source")
        # M14: a null-number record is identified by its date and program name, the same
        # pair update.merge uses as its key (spec 5.2 rule 2).
        ident = n if n is not None else (r.get("draw_date"), r.get("program"))
        if ident in seen:
            errors.append(f"draw {n}: duplicate draw_number")
        seen.add(ident)

        # I4: field types.
        if n is not None and not _is_number(n):
            errors.append(f"draw {n}: draw_number {n!r}")
        tb = r.get("tie_break")
        if not (tb is None or isinstance(tb, str)):
            errors.append(f"draw {n}: tie_break {tb!r}")
        pool = r.get("pool_as_of")
        if not (pool is None or isinstance(pool, str)):
            errors.append(f"draw {n}: pool_as_of {pool!r}")
        elif pool is not None:
            try:
                datetime.date.fromisoformat(pool)
            except Exception:
                errors.append(f"draw {n}: bad pool_as_of {pool!r}")

        try:
            d = datetime.date.fromisoformat(r["draw_date"])
        except Exception:
            errors.append(f"draw {n}: bad draw_date {r.get('draw_date')!r}")
            d = None
        if d and last_date and d < last_date:
            errors.append(f"draw {n}: dates not monotonic")
        if d:
            last_date = d

        # I2: numeric draw numbers must strictly increase; null numbers are skipped.
        if _is_number(n):
            if last_number is not None and n <= last_number:
                errors.append(f"draw {n}: draw_number not monotonic")
            last_number = n

        # I3: every harvested_at is stamped by this run, so a future-dated draw fails.
        h = r.get("harvested_at")
        try:
            harvested = datetime.datetime.fromisoformat(str(h).replace("Z", "+00:00"))
        except Exception:
            errors.append(f"draw {n}: harvested_at {h!r}")
            harvested = None
        if d and harvested and d > harvested.date():
            errors.append(f"draw {n}: draw_date after harvested_at")

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
