import json

from parse_rounds import parse_draws
from update import iso_tie_break, program_key
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

    # I2: numeric draw numbers must strictly increase; null numbers are skipped.
    down = {"draws": [GOOD["draws"][0],
                      dict(GOOD["draws"][0], draw_number=452, draw_date="2026-10-29")]}
    assert any("draw_number not monotonic" in e for e in validate_rounds(down)), \
        validate_rounds(down)

    # I3: a draw dated after its own harvest stamp (future data) cannot be published.
    future = {"draws": [dict(GOOD["draws"][0], draw_date="2026-11-08")]}
    assert any("draw_date after harvested_at" in e for e in validate_rounds(future)), \
        validate_rounds(future)

    # I4: field types.
    assert any("tie_break" in e for e in validate_rounds(
        {"draws": [dict(GOOD["draws"][0], tie_break=123)]}))
    assert any("pool_as_of" in e for e in validate_rounds(
        {"draws": [dict(GOOD["draws"][0], pool_as_of="last week")]}))
    assert any("draw_number" in e for e in validate_rounds(
        {"draws": [dict(GOOD["draws"][0], draw_number="453")]}))

def check_normalise():
    assert program_key("General") == "general"
    assert program_key("No Program Specified") == "general"
    assert program_key("Federal Skilled Trades") == "fst"
    assert program_key("Trade occupations (Version 1)") == "trades_v1"
    assert program_key("Transport Occupations, 2026-Version 2") == "transport_2026_v2"
    assert program_key("Skilled Military Recruits, 2026-Version 1") == "military_2026_v1"
    assert program_key("Some Future Category, 2027-Version 9") == "some_future_category_2027_version_9"
    assert iso_tie_break("June 4, 2026 at 21:48:22 UTC") == "2026-06-04T21:48:22Z"
    assert iso_tie_break("October 10, 2022  17:10:53 UTC") == "2022-10-10T17:10:53Z"
    assert iso_tie_break("June 4, 2026 at 3:54:03 UTC") == "2026-06-04T03:54:03Z"
    assert iso_tie_break("December 09, 2022, at 10:49:57 UTC") == "2022-12-09T10:49:57Z"
    assert iso_tie_break("April 12th, 2026 at 04:32:26 UTC") == "April 12th, 2026 at 04:32:26 UTC"
    assert iso_tie_break("") is None

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
    check_normalise()
    print("selftest ok: 3 draws, malformed rejected, validate checks pass, "
          "normalisers pinned")

if __name__ == "__main__":
    main()
