"""Command line: python -m cmdb_health --input sample_data/cmdb_sample.json --out report.html"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from .checks import run_all
from .report import to_html


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ServiceNow CMDB health checks")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", help="JSON export with 'cis' and 'relationships'")
    src.add_argument("--live", action="store_true", help="Read from the instance in SN_INSTANCE (read-only)")
    p.add_argument("--query", default="", help="Encoded query to limit cmdb_ci (live mode)")
    p.add_argument("--max-age-days", type=int, default=30)
    p.add_argument("--as-of", help="Evaluate staleness as of YYYY-MM-DD (default: now)")
    p.add_argument("--out", help="Write an HTML report to this path")
    p.add_argument("--json", action="store_true", help="Print full results as JSON")
    args = p.parse_args(argv)

    if args.live:
        from .client import TableClient
        data = TableClient.from_env().snapshot(args.query)
    else:
        with open(args.input, encoding="utf-8") as fh:
            data = json.load(fh)

    now = datetime.strptime(args.as_of, "%Y-%m-%d").replace(tzinfo=timezone.utc) if args.as_of else None
    result = run_all(data["cis"], data["relationships"], now=now, max_age_days=args.max_age_days)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(to_html(result))
    if args.json:
        json.dump(result, sys.stdout, indent=2)
    else:
        s = result["scores"]
        print(f"CIs: {result['total_cis']}  overall {s['overall']}%  completeness {s['completeness']}%  "
              f"correctness {s['correctness']}%  compliance {s['compliance']}%")
        for check, rows in result["findings"].items():
            print(f"  {check:<11} {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
