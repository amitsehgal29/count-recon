#!/usr/bin/env python3
"""count-recon: reconcile row counts between a source and a target, per key.

Standard library only. Takes two small CSVs of counts (for example, rows per
load date pulled from the source system and from the warehouse), matches them
on a key column, and reports which keys match, which drifted beyond a
tolerance, and which are missing on either side. Exits 1 when anything fails.
"""
import argparse
import csv
import json
import sys


def load_counts(path, key, count):
    """Read {key: int_count} from a CSV. Duplicate keys are summed."""
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        for col in (key, count):
            if col not in fields:
                raise ValueError(f"{path}: missing column '{col}' (have: {', '.join(fields)})")
        for n, row in enumerate(reader, start=2):
            raw = (row.get(count) or "").strip()
            try:
                value = int(raw.replace(",", ""))
            except ValueError:
                raise ValueError(f"{path}: line {n}: count '{raw}' is not a whole number") from None
            k = (row.get(key) or "").strip()
            out[k] = out.get(k, 0) + value
    return out


def reconcile(source, target, tolerance_pct=0.0, tolerance_abs=0):
    """Compare two {key: count} maps.

    A key passes when |target - source| is within tolerance_abs OR within
    tolerance_pct percent of the source count. Missing keys always fail.
    """
    results = []
    for k in sorted(set(source) | set(target)):
        s, t = source.get(k), target.get(k)
        if s is None:
            results.append({"key": k, "source": None, "target": t, "diff": None, "status": "missing_in_source"})
            continue
        if t is None:
            results.append({"key": k, "source": s, "target": None, "diff": None, "status": "missing_in_target"})
            continue
        diff = t - s
        pct = (abs(diff) / s * 100) if s else (0.0 if diff == 0 else float("inf"))
        ok = abs(diff) <= tolerance_abs or pct <= tolerance_pct
        results.append({
            "key": k, "source": s, "target": t, "diff": diff,
            "diff_pct": None if pct == float("inf") else round(pct, 4),
            "status": "match" if diff == 0 else ("within_tolerance" if ok else "mismatch"),
        })
    failed = [r for r in results if r["status"] in ("mismatch", "missing_in_source", "missing_in_target")]
    return {
        "keys": len(results),
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "source_total": sum(source.values()),
        "target_total": sum(target.values()),
        "ok": not failed,
        "results": results,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="Reconcile per-key row counts between source and target CSVs.")
    p.add_argument("source", help="CSV of source counts")
    p.add_argument("target", help="CSV of target counts")
    p.add_argument("--key", default="key", help="key column name (default: key)")
    p.add_argument("--count", default="count", help="count column name (default: count)")
    p.add_argument("--tolerance-pct", type=float, default=0.0, help="allowed drift as percent of source")
    p.add_argument("--tolerance-abs", type=int, default=0, help="allowed drift in rows")
    p.add_argument("--failures-only", action="store_true", help="list only failing keys in results")
    args = p.parse_args(argv)
    try:
        src = load_counts(args.source, args.key, args.count)
        tgt = load_counts(args.target, args.key, args.count)
    except (ValueError, OSError) as e:
        print(f"count-recon: {e}", file=sys.stderr)
        return 2
    report = reconcile(src, tgt, args.tolerance_pct, args.tolerance_abs)
    if args.failures_only:
        report["results"] = [r for r in report["results"] if r["status"] not in ("match", "within_tolerance")]
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
