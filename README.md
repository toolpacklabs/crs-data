# crs-data

Data published for the F2 CRS Calculator app. The app fetches `meta.json` first (with its
cached ETag), compares each recorded SHA-256 with the file it already holds, and downloads
only what changed, through a jsDelivr mirror of this repository
(`https://cdn.jsdelivr.net/gh/dz1825/crs-data@main/`).

- `data/rounds.json` — every IRCC Express Entry round we know of (454 at 2026-11-07),
  oldest first, each with its provenance.
- `data/meta.json` — `latest_draw`, `rules_version`, `generated_at` and the SHA-256 of every
  published file. This is the app's freshness check.
- `data/rules.json` — the 2026-11 CRS rule tables (Task 5).
- `fixtures/` — the parser snippet, a **frozen copy of the community mirror**
  (`community_454.json`, so CI never depends on jsDelivr staying up), the hand-transcribed
  draw 453, and the golden rule cases.
- `tools/` — parser (`parse_rounds.py`), validator (`validate.py`), updater (`update.py`),
  replay (`replay.py`), self-test (`selftest.py`), rules validator (`validate_rules.py`).

## Pipeline runbook

`.github/workflows/update.yml` runs every six hours (cron `0 */6 * * *`) and on
`workflow_dispatch`. It needs no secrets; it pushes with the workflow's own token
(`permissions: contents: write`).

**`SOURCE_MODE = "http"`** (`tools/update.py`). The local probe on 2026-11-07 fetched
`ee_rounds_4_en.json` — HTTP 200, 1,216,086 B, 454 rounds. The cloud-IP probe from Task 1
was never run, so the workflow's first run is the real test of this mode. If canada.ca
blocks the runner IP, `update.py` logs `primary source failed: …; falling back to
community` on stderr and reads `RB9744/express-entry-draws` instead; the records then carry
the mirror URL in `harvested_from` while `source_url` stays on the canonical canada.ca page.

The job runs these steps in order. Any failing step fails the job, so a broken parser,
a moved fixture or a bad document **never publishes**:

1. `python tools/selftest.py` — parser self-test plus the validator's own checks.
2. `python tools/replay.py` — re-derives 454 draws from the frozen mirror copy and asserts
   the newest one is draw 453 and matches `fixtures/manual_453.json`.
3. `python tools/validate_rules.py data/rules.json` — the rules pack is still the 2026-11 one.
4. `python tools/update.py` — fetch, normalise, merge with the published file, write
   `data/rounds.json` and `data/meta.json`.
5. `python tools/validate.py data/rounds.json` — the gate on the document about to be
   published.
6. `git add data` and commit only if the tree changed; otherwise print `no change`.

Run the same sequence locally, from the repository root (`update.py` writes relative paths,
so it must run from here):

```bash
python3 tools/selftest.py \
  && python3 tools/replay.py \
  && python3 tools/validate_rules.py data/rules.json \
  && python3 tools/update.py \
  && python3 tools/validate.py data/rounds.json
```

### How to read a red run

| Failing step | Meaning | What to do |
|---|---|---|
| `selftest.py` | The parser or the validator changed behaviour. | Do not "fix" the assertion. Read the traceback; the fixture and the tool disagree. |
| `replay.py` | The frozen mirror changed, or normalisation regressed. | The assertion prints the offending value. If the frozen file moved, re-freeze it and re-check draw 453 by hand. |
| `validate_rules.py` | `data/rules.json` is no longer the 2026-11 pack. | Rules changes are their own reviewed change, not a pipeline fix. |
| `validate.py` | The document `update.py` just wrote is wrong (cut-off out of range, duplicate id, non-monotonic dates, non-canada.ca source, missing field). | Nothing was committed. Read the printed error lines; they name the draw and the field. |
| `update.py` itself | Both sources failed, or the official file returned zero rounds. | Nothing was committed. Re-run once by hand; if canada.ca and the mirror both fail, leave it — the app keeps serving the last good `rounds.json`. |

`update.py` prints one line on success, e.g.
`wrote 454 draws, latest 453 (transport_2026_v2, 2026-10-28) via http`. The last workflow
step then commits `data: refresh draws <timestamp>` or prints `no change`.

A commit per successful run is the intended behaviour: every run rewrites `generated_at`
and the newest record's `harvested_at`, so the app sees a new `meta.json` and moves its
`Data checked` line even in a week with no new draw. Seeing a commit every six hours is the
pipeline working, not churn. `no change` only appears if the bytes came out identical
(same second, or the step re-running after a manual re-run).

### Never guess a number

If a field cannot be parsed, the pipeline fails. It does not carry the previous value
forward into a new record, it does not round, and it does not "repair" a source number.
Two deliberate behaviours sit next to that rule, and neither invents a value: a record
already in `data/rounds.json` is replaced only by a record parsed from a source (the
previous copy of the same draw id is overwritten, never edited), and a record absent from
a fetch is kept — merge, never truncate, so one bad fetch cannot shrink the history. A
non-numeric IRCC draw number (`91a`, `91b`) is kept with `draw_number: null` plus
`number_source: "IRCC drawNumber 91a"`; it is never renumbered.

## Publishing — TODO, not done yet

This checkout has **no git remote**, so nothing is published to jsDelivr yet. The remaining
publish action is a one-time, human step:

1. Create the public repository `dz1825/crs-data` (empty, no README).
2. `git remote add origin git@github.com:dz1825/crs-data.git && git push -u origin main`
3. Run the `update` workflow once (`workflow_dispatch`) so the bot commits the first refresh
   and proves the runner can reach a source.
4. Check `https://cdn.jsdelivr.net/gh/dz1825/crs-data@main/meta.json` returns `files` with
   SHA-256 values. The app's `DATA_BASE_URL` in `app/build.gradle.kts` already points there,
   so no app change is needed once the repository exists under that name.

## Sources, provenance and known defects

`source_url` is the canonical canada.ca rounds page on **every** record, whichever source
the fetch came from; the actual fetch origin is `harvested_from` (`…/ee_rounds_4_en.json`
or the jsDelivr mirror URL). One record never mixes sources.

- **The official file is wrong for draws 1 and 5.** Cross-checking all 454 records against
  the community mirror on 2026-11-07, everything agrees except those two, where IRCC's
  `drawCRS` does not match the real cut-off: draw 1 official 779 vs mirror **886**, draw 5
  official 735 vs mirror **481**. They are published exactly as the official file states
  them — the pipeline does not patch source numbers — so the two oldest cut-offs in
  `rounds.json` are low. Informational only: no rule, score or stream depends on them.
- **`pool_as_of` is `null` on every record published from the official JSON**, because that
  file carries no pool date (the mirror has `distribution_as_of`). `null` is the contract:
  the app renders "not published". Do not backfill it from the mirror — that would mix
  sources inside one record.
- **Tie-break text is passed through, not repaired.** `iso_tie_break` collapses whitespace,
  accepts an optional `at`, zero-pads one-digit hours and emits
  `YYYY-MM-DDTHH:MM:SSZ`. Anything that still does not match — `12th`/`3rd`, a missing
  year (`October 7 at 16:38:21 UTC`), `20:19:59 PM`, `August 30. 2023` — is stored as the
  trimmed raw string and the app prints it verbatim. 10 of the 454 records are in that
  state, and 76 have no tie-break at all (`null`).
- **Draws `91a` and `91b`** (2018-05-30, Federal Skilled Trades and Provincial Nominee
  Program) have no numeric IRCC number; they are published with `draw_number: null` and
  `number_source` set, and the app identifies them by date plus program.

## The 91-second manual transcription (used to verify draw 453)

The pipeline's round-trip check is only as good as its hand-checked sample, so draw 453 was
transcribed from the canada.ca page by hand in **91 seconds**, and that is what
`fixtures/manual_453.json` holds:

1. Open the canada.ca rounds-invitations page and find the newest row of the latest-rounds
   table (draw 453, 2026-10-28).
2. Read five values off that row: draw number, date, program name, invitations, CRS cut-off,
   plus the tie-break stamp from the round's detail.
3. Write them into `fixtures/manual_453.json`, with the tie-break already in
   `YYYY-MM-DDTHH:MM:SSZ` form (nothing is inferred).
4. `python3 tools/replay.py` must print `replay ok: 454 records, 453 matches manual`.

The same procedure, at the same cost, is how to verify any future round if the pipeline
ever looks wrong: transcribe it once by hand and let `replay.py` compare.
