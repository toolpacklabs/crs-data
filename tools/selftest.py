import json

from parse_rounds import parse_draws

MISS = {"rounds": {"rx": {"drawNumber": "454", "drawDateFull": "November 8, 2026",
                          "drawName": "General", "drawSize": "100"}}}

def main():
    doc = json.load(open("fixtures/ee_rounds_snippet.json", encoding="utf-8"))
    draws = parse_draws(doc)
    assert len(draws) == 2, draws
    latest = draws[-1]
    assert latest["draw_number"] == 453, latest
    assert latest["draw_date"] == "2026-10-28", latest
    assert latest["number_of_invitations"] == 150, latest
    assert latest["crs_cutoff"] == 477, latest
    assert latest["tie_break"] == "June 4, 2026 at 21:48:22 UTC", latest
    assert draws[0]["number_of_invitations"] == 2500, draws[0]
    try:
        parse_draws(MISS)
    except ValueError:
        pass
    else:
        raise AssertionError("malformed record must raise")
    print("selftest ok: 2 draws, malformed rejected")

if __name__ == "__main__":
    main()
