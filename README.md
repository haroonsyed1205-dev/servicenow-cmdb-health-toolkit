# ServiceNow CMDB Health Toolkit

> **Starter template — representative portfolio project.**
> This is not client or employer code, and every record in it is synthetic.
> The first version was generated with AI assistance as a starting point.
> Haroon is validating and extending it on a ServiceNow Personal Developer Instance (PDI).
> The live Table API mode has not yet been run against an instance; the offline mode and tests are verified.

A read-only command-line tool that checks a ServiceNow CMDB for the problems that erode trust in it. It scores the results in the three dimensions the CMDB Health dashboard uses (completeness, correctness, compliance) and writes an HTML report.

## Business problem

Change risk, incident impact, and asset and license reporting all depend on the CMDB. If it has duplicate servers, orphaned CIs or business applications with no link to a running service, impact analysis is wrong, and people stop using it. This toolkit makes those gaps visible and countable, so they can be fixed and tracked over time.

## What it checks

| Check | Rule | Health dimension |
|---|---|---|
| Duplicates | Same serial number, or same name within the same class | Correctness |
| Orphans | CI has no parent or child in `cmdb_rel_ci` | Correctness |
| Stale | Operational, discoverable CI not discovered in 30 days (configurable) | Compliance |
| Incomplete | Missing `owned_by`, `support_group` or `environment` | Completeness |
| CSDM gap | `cmdb_ci_business_app` with no relationship to an application service | Compliance |

- Each dimension score is the percentage of CIs with no finding in that dimension.
- The overall score is the average of the three dimension scores.
- Logical CIs (business applications, application services) and non-operational CIs are excluded from the staleness check.

## How it works

```
 JSON export ─┐
              ├─► checks.run_all() ─► scores + findings ─► console summary
 Table API ───┘        (pure Python)                    └─► HTML report
 (read-only, paginated, retries on 429/5xx)
```

| Path | Purpose |
|---|---|
| `cmdb_health/checks.py` | The checks. Pure functions over plain dictionaries, so they are easy to test |
| `cmdb_health/client.py` | Read-only Table API client (standard library only, paginated, retries on 429/5xx) |
| `cmdb_health/report.py` | HTML report, with all CI values escaped |
| `cmdb_health/__main__.py` | Command-line interface |
| `sample_data/cmdb_sample.json` | Nine synthetic CIs and five relationships covering every check |
| `tests/` | Unit tests (standard-library `unittest`) |
| `docs/WALKTHROUGH.md` | Hands-on guide for running it against a PDI and extending it |

## Quick start (no instance needed)

```bash
python3 --version     # 3.9 or later, no packages to install
python3 -m unittest discover -s tests -v
python3 -m cmdb_health --input sample_data/cmdb_sample.json --as-of 2026-09-24 --out report.html
```

Output on the sample data:

```
CIs: 9  overall 66.7%  completeness 77.8%  correctness 55.6%  compliance 66.7%
  duplicate   2
  orphan      3
  stale       2
  incomplete  2
  csdm        1
```

## Against a Personal Developer Instance

```bash
cp .env.example .env       # fill in your PDI URL and a read-only user
set -a; . ./.env; set +a
python3 -m cmdb_health --live --query "sys_class_nameINcmdb_ci_linux_server,cmdb_ci_win_server" --out report.html
```

See `docs/WALKTHROUGH.md` for creating the read-only user and loading test data.

## Security notes

- **Read-only:** the tool only issues GET requests. Give its user the `cmdb_read` role only (plus `itil` if relationship reads require it on your instance).
- **Credentials:** read from environment variables. `.env` is git-ignored and `.env.example` holds placeholders only.
- **Transport:** HTTPS is required, so `http://` instance URLs are rejected.
- **Report output:** every CI value is HTML-escaped, so a malicious CI name cannot inject script into the report.

## Limitations and next steps

- Duplicate detection is exact-match only. Next: fuzzy matching and IRE-style identifier rules.
- Relationship reads pull the whole `cmdb_rel_ci` table. For large instances, filter it to the CI set being checked.
- Planned: CSV export, a trend file for tracking scores over time, and a GitHub Action that runs nightly against a PDI.

## License

MIT
