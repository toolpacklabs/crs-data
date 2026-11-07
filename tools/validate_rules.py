import json
import sys

REQUIRED = ["version", "effective_from", "harvested_at", "source_url", "transferability_cap",
            "age", "education", "first_language", "canadian_work", "additional", "spouse", "transferability",
            "second_language", "foreign_work", "certificate_of_qualification"]
TIERS = ["LESS_THAN_SECONDARY", "SECONDARY", "ONE_YEAR", "TWO_YEAR",
         "BACHELOR", "TWO_OR_MORE", "MASTERS", "DOCTORAL"]
SCORED = [t.lower() for t in TIERS[1:]]
ADDITIONAL_MODEL = ["pnp", "french_with_english_high", "french_with_english_low", "sibling"]
HIGH_WAGE_WORK = ["twice_median", "1_5x_median", "1_3x_median", "none"]
HIGH_WAGE_OFFER = ["twice_median", "1_5x_median", "1_3x_median", "not_high_wage"]

def validate(path: str) -> list[str]:
    errors = []
    rules = json.load(open(path, encoding="utf-8"))
    for key in REQUIRED:
        if key not in rules:
            errors.append(f"missing {key}")
    if errors:
        return errors
    if not rules["source_url"].startswith("https://www.canada.ca/"):
        errors.append("source_url must be canada.ca")
    if rules["effective_from"] != "2026-11-03":
        errors.append("effective_from must be the 2026-11-03 rule change")
    if rules["transferability_cap"] != 100:
        errors.append("transferability_cap must be 100")
    if rules["transferability"].get("education_cap") != 50:
        errors.append("transferability.education_cap must be 50")
    for mode in ("single", "with_spouse"):
        for tier in TIERS:
            if tier not in rules["education"][mode]:
                errors.append(f"education.{mode}.{tier} missing")
        for key in ("4", "5", "6", "7", "8", "9", "10"):
            if key not in rules["first_language"][mode]:
                errors.append(f"first_language.{mode}.{key} missing")
        for key in ("0", "1", "2", "3", "4", "5"):
            if key not in rules["canadian_work"][mode]:
                errors.append(f"canadian_work.{mode}.{key} missing")
    for key in ADDITIONAL_MODEL:
        if key not in rules["additional"]:
            errors.append(f"additional.{key} missing")
    for key in ("canadian_postsecondary_1_2_years", "canadian_postsecondary_3_years"):
        if key not in rules["additional"]:
            errors.append(f"additional.{key} missing")
    for key, bands in (("high_wage_work", HIGH_WAGE_WORK), ("high_wage_job_offer", HIGH_WAGE_OFFER)):
        table = rules["additional"].get(key)
        if not isinstance(table, dict):
            errors.append(f"additional.{key} must be a table")
        else:
            for band in bands:
                if band not in table:
                    errors.append(f"additional.{key}.{band} missing")
    if rules["additional"]["pnp"] != 600:
        errors.append("pnp must be 600")
    for table in ("education_language", "education_work"):
        for tier in SCORED:
            entry = rules["transferability"][table].get(tier)
            if entry is None:
                errors.append(f"transferability.{table}.{tier} missing")
                continue
            keys = [str(k) for k in range(4, 11)] if table == "education_language" else [str(k) for k in range(0, 6)]
            for key in keys:
                if key not in entry:
                    errors.append(f"transferability.{table}.{tier}.{key} missing (write 0, do not omit)")
    if "education_foreign_work" in rules["transferability"]:
        errors.append("education_foreign_work is not an IRCC table; delete it")
    return errors

if __name__ == "__main__":
    errs = validate(sys.argv[1])
    print("\n".join(errs) if errs else "rules ok")
    sys.exit(1 if errs else 0)
