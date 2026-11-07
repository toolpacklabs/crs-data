import datetime
import re

MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)}

def _int(value):
    text = str(value or "").strip()
    if not re.fullmatch(r"[\d,]+", text):
        raise ValueError(f"not a number: {value!r}")
    return int(text.replace(",", ""))

def _iso_date(text):
    m = re.fullmatch(r"([A-Z][a-z]+) (\d{1,2}), (\d{4})", str(text or "").strip())
    if not m or m.group(1) not in MONTHS:
        raise ValueError(f"not a date: {text!r}")
    return datetime.date(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2))).isoformat()

def parse_draws(doc):
    rounds = doc.get("rounds")
    if not isinstance(rounds, dict):
        raise ValueError("rounds is not an object")
    out = []
    for key, rec in rounds.items():
        if not isinstance(rec, dict):
            raise ValueError(f"{key}: not an object")
        program = str(rec.get("drawName") or "").strip()
        if not program or program == "undefined":
            raise ValueError(f"{key}: missing drawName")
        out.append({
            "draw_number": _int(rec.get("drawNumber")),
            "draw_date": _iso_date(rec.get("drawDateFull")),
            "program": program,
            "number_of_invitations": _int(rec.get("drawSize")),
            "crs_cutoff": _int(rec.get("drawCRS")),
            "tie_break": rec.get("drawCutOff") or None,
        })
    return sorted(out, key=lambda r: (r["draw_date"], r["draw_number"]))
