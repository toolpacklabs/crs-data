import re

ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
TAG = re.compile(r"<[^>]+>")

def _text(cell: str) -> str:
    return re.sub(r"\s+", " ", TAG.sub(" ", cell)).strip()

def _int(value: str) -> int:
    return int(value.replace(",", ""))

def parse_rounds(html: str) -> list[dict]:
    out = []
    for row in ROW.findall(html):
        cells = [_text(c) for c in CELL.findall(row)]
        if len(cells) < 6:
            continue
        date, number, program, invitations, cutoff, tie = cells[:6]
        if not re.fullmatch(r"\d{1,3}", number):
            continue
        if not re.fullmatch(r"[\d,]+", invitations):
            continue
        if not re.fullmatch(r"\d{1,4}", cutoff):
            continue
        out.append({
            "draw_number": _int(number),
            "draw_date": date,
            "program": program,
            "number_of_invitations": _int(invitations),
            "crs_cutoff": _int(cutoff),
            "tie_break": tie or None,
        })
    return out
