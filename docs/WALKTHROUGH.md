# Walkthrough: run, understand and extend the toolkit

This guide is for making the project your own. By the end you should be able to demo it live and explain every design choice in an interview.

## 1. Get a Personal Developer Instance (15 minutes)

1. Sign in at developer.servicenow.com with your own account.
2. Request an instance on the current release. Note its URL (`https://devNNNNN.service-now.com`).
3. PDIs go to sleep when unused. Wake yours from the developer portal before a demo.

## 2. Create a read-only integration user

1. Go to **User Administration > Users > New**.
   - User ID: `cmdb_health_reader`
   - Check **Web service access only**.
   - Set a password.
2. Add the role `cmdb_read`.
3. Test it with:
   `curl -u cmdb_health_reader:PASSWORD "https://devNNNNN.service-now.com/api/now/table/cmdb_ci?sysparm_limit=1"`

## 3. Seed test problems (do it yourself; this is the learning part)

In your PDI, create or change records so that each check has something to find:

| Check | What to create |
|---|---|
| Duplicate | Two Linux servers with the same serial number |
| Orphan | A computer CI with no relationships |
| Stale | Set `last_discovered` on an operational server to 60 days ago |
| Incomplete | Clear `support_group` on one CI |
| CSDM gap | A business application with no link to an application service |

Then run:

```bash
python3 -m cmdb_health --live --out report.html
```

Open the report and confirm each problem you created appears. Take a screenshot for the README.

## 4. Know the code well enough to explain it

Be ready to answer these, with the file to look at for each:

| Question | Where to look |
|---|---|
| Why are the checks pure functions over dictionaries instead of calling the API directly? (Hint: testing, and the same logic serves exports and live data.) | `checks.py` |
| How does pagination work, and what happens on HTTP 429? | `client.py`, `records()` and `_get()` |
| Why exclude business apps and application services from the staleness check? | `find_stale()` |
| How would this map to CMDB Health's completeness, correctness and compliance KPIs, and to IRE identification rules? | `run_all()` |
| What would change for an instance with 2 million CIs? (Filtering `cmdb_rel_ci`, running server-side, scheduled jobs.) | `snapshot()` |

## 5. Extend it: commit these yourself

Each one is a small, real contribution that shows up in your commit history:

1. **Configurable required fields.** Add a `--required owned_by,support_group,location` option.
2. **CSV export** of findings (`--csv findings.csv`).
3. **Trend tracking.** Append each run's scores to `history.csv`, and draw a line in the HTML report.
4. **Server-side version.** Write a Script Include `CMDBHealthChecks` that runs the duplicate check with `GlideAggregate` (group by `serial_number`, having count > 1). Explain when you'd run it server-side versus through the API.
5. **ATF.** Create an ATF test that inserts a duplicate CI and asserts that your Script Include finds it.

Use clear commit messages, for example `Add CSV export of findings`.

## 6. Demo script (3 minutes)

1. Say the problem in one sentence.
2. Run it on the sample data and point at the scores.
3. Run it live against your PDI.
4. Open the report.
5. Show one fix, run again, and show the score going up.
6. Say what you'd add for a production-scale CMDB.
