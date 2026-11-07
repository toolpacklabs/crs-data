import datetime
import hashlib
import json
import os
import re
import sys

import requests

from parse_rounds import parse_draws

# Set from the Task 1 runner result: "http" or "community".
# local probe 2026-11-07: canada.ca ee_rounds_4_en.json -> 200, 1,216,086 B, 454 rounds.
# The cloud-IP probe from Task 1 was never run, so the workflow's first run is the real
# test of this mode; the automatic community fallback below covers a block either way.
SOURCE_MODE = "http"

CANADA_PAGE = ("https://www.canada.ca/en/immigration-refugees-citizenship/services/"
               "immigrate-canada/express-entry/submit-profile/rounds-invitations.html")
ROUNDS_JSON = "https://www.canada.ca/content/dam/ircc/documents/json/ee_rounds_4_en.json"
COMMUNITY_URL = ("https://cdn.jsdelivr.net/gh/RB9744/express-entry-draws@main/"
                 "data/express-entry-draws.json")

# Order matters: the first match wins, so the longer, more specific names come first.
CATEGORY_PATTERNS = [
    ("transport", "transport"),
    ("healthcare", "healthcare"),
    ("stem", "stem"),
    ("french", "french"),
    ("federal skilled trades", "fst"),
    ("trade", "trades"),
    ("agriculture", "agriculture"),
    ("education", "education"),
    ("senior managers", "senior_managers"),
    ("physicians", "physicians"),
    ("military", "military"),
    ("canadian experience", "cec"),
    ("federal skilled worker", "fsw"),
    ("provincial nominee", "pnp"),
]

MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)}

TIE_BREAK = re.compile(
    r"([A-Z][a-z]+ \d{1,2}, \d{4}),? (?:at )?(\d{1,2}):(\d{2}):(\d{2})(?: UTC)?")

def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def iso_date(text: str) -> str:
    text = text.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    m = re.fullmatch(r"([A-Z][a-z]+) (\d{1,2}), (\d{4})", text)
    if not m or m.group(1) not in MONTHS:
        raise ValueError(f"unparsed date: {text!r}")
    return datetime.date(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2))).isoformat()

def iso_tie_break(text):
    """Normalise the tie-break stamp, or return the trimmed raw text. Never guesses."""
    if not text:
        return None
    raw = re.sub(r"\s+", " ", str(text).strip())
    m = TIE_BREAK.fullmatch(raw)
    if not m:
        return raw  # missing year, "12th"/"3rd", "20:19:59 PM", ... stay verbatim
    try:
        day = iso_date(m.group(1))
    except ValueError:
        return raw
    return f"{day}T{int(m.group(2)):02d}:{m.group(3)}:{m.group(4)}Z"

def program_key(program: str) -> str:
    low = program.lower()
    if "no program specified" in low or low.strip() == "general":
        return "general"
    base = next((key for pattern, key in CATEGORY_PATTERNS if pattern in low), None)
    if base is None:
        # Unknown future category: slug the whole name so it stays its own stream.
        return re.sub(r"[^a-z0-9]+", "_", low).strip("_")
    parts = [base]
    year = re.search(r"\b(20\d{2})\b", program)
    if year:
        parts.append(year.group(1))
    version = re.search(r"version\s*(\d+)", low)
    if version:
        parts.append(f"v{version.group(1)}")
    return "_".join(parts)

def from_canada() -> list:
    doc = requests.get(ROUNDS_JSON, timeout=45).json()
    rows = parse_draws(doc)
    if not rows:
        raise ValueError("official JSON returned zero rounds")
    out = []
    for row in rows:
        out.append({
            "draw_number": row["draw_number"],
            "draw_date": row["draw_date"],
            "program": row["program"],
            "program_key": program_key(row["program"]),
            "number_of_invitations": row["number_of_invitations"],
            "crs_cutoff": row["crs_cutoff"],
            "tie_break": iso_tie_break(row["tie_break"] or ""),
            "number_source": row["number_source"],
            "pool_as_of": None,  # the official file carries no pool date; never backfill
            "source_url": CANADA_PAGE,
            "harvested_from": ROUNDS_JSON,
            "harvested_at": now_iso(),
        })
    return out

def split_number(raw):
    text = str(raw or "").strip()
    if text.isdigit():
        return int(text), None
    if text:
        return None, f"IRCC drawNumber {text}"
    raise ValueError("missing draw number")

def from_community_record(r: dict) -> dict:
    number, number_source = split_number(r["draw_number"])
    return {
        "draw_number": number,
        "draw_date": iso_date(r["draw_date"]),
        "program": r["draw_name"],
        "program_key": program_key(r["draw_name"]),
        "number_of_invitations": int(r["invitations"]),
        "crs_cutoff": int(r["crs_cutoff"]),
        "tie_break": iso_tie_break(r.get("tie_break_rule") or ""),
        "number_source": number_source,
        "pool_as_of": iso_date(r["distribution_as_of"]) if r.get("distribution_as_of") else None,
        "source_url": CANADA_PAGE,
        "harvested_from": COMMUNITY_URL,
        "harvested_at": now_iso(),
    }

def from_community() -> list:
    records = requests.get(COMMUNITY_URL, timeout=45).json()
    return [from_community_record(r) for r in records]

def draw_id(r: dict):
    return r["draw_number"] if r["draw_number"] is not None \
        else f"{r['draw_date']}:{r['program_key']}"

def merge(old: list, new: list) -> list:
    by_id = {draw_id(r): r for r in old}
    for r in new:
        by_id[draw_id(r)] = r
    return sorted(by_id.values(),
                  key=lambda r: (r["draw_date"], r["draw_number"] or -1))

def write_json(path: str, obj) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")

def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def main() -> None:
    os.makedirs("data", exist_ok=True)
    old = []
    if os.path.exists("data/rounds.json"):
        old = json.load(open("data/rounds.json", encoding="utf-8"))["draws"]

    used = SOURCE_MODE
    try:
        new = from_canada() if SOURCE_MODE != "community" else from_community()
    except Exception as e:
        print(f"primary source failed: {e}; falling back to community", file=sys.stderr)
        new = from_community()
        used = "community"

    draws = merge(old, new)
    if not draws:
        raise SystemExit("no draws parsed; refusing to publish")
    draws[-1]["harvested_at"] = now_iso()  # a successful check refreshes freshness even without a new draw

    write_json("data/rounds.json", {"generated_at": now_iso(), "draws": draws})
    files = {"rounds.json": sha256("data/rounds.json")}
    rules_version = "unversioned"
    if os.path.exists("data/rules.json"):
        files["rules.json"] = sha256("data/rules.json")
        rules_version = json.load(open("data/rules.json", encoding="utf-8"))["version"]
    write_json("data/meta.json", {
        "latest_draw": draws[-1]["draw_number"],
        "rules_version": rules_version,
        "generated_at": now_iso(),
        "files": files,
    })

    latest = draws[-1]
    print(f"wrote {len(draws)} draws, latest {latest['draw_number']} "
          f"({latest['program_key']}, {latest['draw_date']}) via {used}")

if __name__ == "__main__":
    main()
