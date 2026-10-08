# count-recon

A tiny, standard-library-only CLI that reconciles row counts between a source and a target, key by key. Use it after a load to check that the warehouse got the same number of rows per day (or per partition, table, or region) as the source system sent.

Give it two small CSVs of counts. For each key it reports `match`, `within_tolerance`, `mismatch`, `missing_in_target`, or `missing_in_source`, plus totals. It exits 1 when anything fails, so it can gate a pipeline step.

## Usage

```bash
python3 count_recon.py samples/source.csv samples/target.csv \
  --key load_date --count rows --tolerance-pct 0.5 --failures-only
```

```json
{
  "keys": 4,
  "passed": 2,
  "failed": 2,
  "source_total": 479440,
  "target_total": 353580,
  "ok": false,
  "results": [
    {"key": "2026-10-07", "source": 121040, "target": 115200, "diff": -5840, "diff_pct": 4.8249, "status": "mismatch"},
    {"key": "2026-10-08", "source": 119900, "target": null, "diff": null, "status": "missing_in_target"}
  ]
}
```

Here 2026-10-06 is off by 120 rows (0.1%), so it passes the 0.5% tolerance, 2026-10-07 is short by about 4.8%, and 2026-10-08 never landed.

Options:

- `--tolerance-pct 0.5` allows drift as a percent of the source count.
- `--tolerance-abs 10` allows drift in rows. A key passes if either tolerance holds.
- `--failures-only` lists only failing keys.
- Counts like `"115,200"` are accepted, and repeated keys are summed.
- A source count of 0 with rows in the target always fails.

## Tests

```bash
python3 -m unittest
```
