import json

from update import from_community_record

records = json.load(open("fixtures/community_454.json", encoding="utf-8"))
draws = sorted((from_community_record(r) for r in records),
               key=lambda r: (r["draw_date"],
                              r["draw_number"] if r["draw_number"] is not None else -1))
manual = json.load(open("fixtures/manual_453.json", encoding="utf-8"))

assert len(draws) == 454, len(draws)
latest = draws[-1]
assert latest["draw_number"] == manual["draw_number"] == 453, latest["draw_number"]
assert latest["program"] == manual["program"], latest["program"]
assert latest["number_of_invitations"] == manual["number_of_invitations"]
assert latest["crs_cutoff"] == manual["crs_cutoff"]
assert latest["tie_break"].startswith("2026-06-04T21:48:22"), latest["tie_break"]
assert latest["program_key"] == "transport_2026_v2", latest["program_key"]
print("replay ok: 454 records, 453 matches manual")
