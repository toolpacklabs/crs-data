import json

from parse_rounds import parse_draws
from validate import validate_rounds

MISS = {"rounds": {"rx": {"drawNumber": "454", "drawDateFull": "November 8, 2026",
                          "drawName": "General", "drawSize": "100"}}}

GOOD = {"draws": [
    {"draw_number": 453, "draw_date": "2026-10-28",
     "program": "Transport Occupations, 2026-Version 2", "program_key": "transport_2026_v2",
     "number_of_invitations": 150, "crs_cutoff": 477,
     "tie_break": "2026-06-04T21:48:22Z", "pool_as_of": "2026-10-25",
     "source_url": "https://www.canada.ca/en/immigration-refugees-citizenship/",
     "harvested_at": "2026-11-07T00:00:00Z"}
]}

def check_validate():
    assert validate_rounds(GOOD) == []
    bad = {"draws": [dict(GOOD["draws"][0], crs_cutoff=9999)]}
    assert any("crs_cutoff" in e for e in validate_rounds(bad))
    dup = {"draws": GOOD["draws"] * 2}
    assert any("duplicate" in e for e in validate_rounds(dup))
    missing = {"draws": [dict(GOOD["draws"][0], program_key="")]}
    assert any("program_key" in e for e in validate_rounds(missing))

def main():
    doc = json.load(open("fixtures/ee_rounds_snippet.json", encoding="utf-8"))
    draws = parse_draws(doc)
    assert len(draws) == 3, draws
    latest = draws[-1]
    assert latest["draw_number"] == 453, latest
    assert latest["draw_date"] == "2026-10-28", latest
    assert latest["number_of_invitations"] == 150, latest
    assert latest["crs_cutoff"] == 477, latest
    assert latest["tie_break"] == "June 4, 2026 at 21:48:22 UTC", latest
    assert draws[1]["number_of_invitations"] == 2500, draws[1]
    suffixed = draws[0]
    assert suffixed["draw_number"] is None, suffixed
    assert suffixed["number_source"] == "IRCC drawNumber 91a", suffixed
    try:
        parse_draws(MISS)
    except ValueError:
        pass
    else:
        raise AssertionError("malformed record must raise")
    check_validate()
    print("selftest ok: 3 draws, malformed rejected, validate checks pass")

if __name__ == "__main__":
    main()
