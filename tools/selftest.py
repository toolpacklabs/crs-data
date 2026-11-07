from parse_rounds import parse_rounds

HIT = """
<table><tbody>
<tr><td>October 28, 2026</td><td>453</td><td>Transport Occupations, 2026-Version 2</td>
<td>150</td><td>477</td><td>June 4, 2026 at 21:48:22 UTC</td></tr>
</tbody></table>
"""

MISS = """
<table><tbody>
<tr><td>No draws found</td></tr>
</tbody></table>
"""

def main():
    hit = parse_rounds(HIT)
    assert len(hit) == 1, hit
    assert hit[0]["draw_number"] == 453
    assert hit[0]["crs_cutoff"] == 477
    miss = parse_rounds(MISS)
    assert miss == [], miss
    print("selftest ok: hit=1 miss=0")

if __name__ == "__main__":
    main()
