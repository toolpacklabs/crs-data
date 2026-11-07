"""Recompute every golden case from data/rules.json and compare with the
official calculator's total.

The golden CSV is produced by tools/official_crs.mjs, which runs IRCC's own
calculator code. This script is the independent side of the check: it reads
only our transcription of the published tables, so a disagreement points at
rules.json, not at the golden file.

Usage: python3 tools/cross_check_golden.py [fixtures/golden/golden_cases.csv]
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "data" / "rules.json"
GOLDEN = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "fixtures" / "golden" / "golden_cases.csv"


def age_points(rules, age, mode):
    for band in rules["age"][mode]:
        if band["min"] <= age <= band["max"]:
            return band["points"]
    raise ValueError(f"age {age} outside the table")


def score(rules, row):
    if row["spouse"] != "SINGLE":
        raise ValueError(f"{row['case_id']}: only single profiles are in golden scope")
    if row["french"].lower() == "true":
        raise ValueError(f"{row['case_id']}: French is out of golden scope")
    mode = "single"
    tier = row["education"].lower()
    clb = int(row["first_language_clb"])
    years = min(int(row["canadian_work_years"]), 5)
    total = age_points(rules, int(row["age"]), mode)
    total += rules["education"][mode][row["education"]]
    total += 4 * rules["first_language"][mode][str(clb)]
    total += rules["canadian_work"][mode][str(years)]
    edu_lang = rules["transferability"]["education_language"][tier][str(clb)]
    edu_work = rules["transferability"]["education_work"][tier][str(years)]
    total += min(
        edu_lang + edu_work,
        rules["transferability"]["education_cap"],
        rules["transferability_cap"],
    )
    return total


def main() -> int:
    rules = json.loads(RULES.read_text(encoding="utf-8"))
    mismatches = []
    with GOLDEN.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            expected = int(row["expected_score"])
            actual = score(rules, row)
            if actual != expected:
                mismatches.append(f"{row['case_id']}: rules.json {actual} != official {expected}")
    for line in mismatches:
        print(line)
    print("golden cross-check ok" if not mismatches else "golden cross-check FAILED")
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
