"""Render check results as a self-contained HTML report."""
from __future__ import annotations

import html

LABELS = {
    "duplicate": "Duplicate CIs",
    "orphan": "Orphan CIs",
    "stale": "Stale CIs",
    "incomplete": "Incomplete CIs",
    "csdm": "CSDM gaps",
}


def to_html(result: dict, title: str = "CMDB Health Report") -> str:
    s = result["scores"]
    tiles = "".join(
        f'<div class="tile"><div class="v">{s[k]}%</div><div class="l">{k.title()}</div></div>'
        for k in ("overall", "completeness", "correctness", "compliance")
    )
    sections = []
    for key, label in LABELS.items():
        rows = result["findings"][key]
        body = "".join(
            f"<tr><td>{html.escape(str(f['name']))}</td><td>{html.escape(str(f['class']))}</td>"
            f"<td>{html.escape(f['detail'])}</td></tr>" for f in rows
        ) or '<tr><td colspan="3">No findings</td></tr>'
        sections.append(
            f"<h2>{label} <span>({len(rows)})</span></h2>"
            f"<table><tr><th>CI</th><th>Class</th><th>Detail</th></tr>{body}</table>"
        )
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>body{{font-family:system-ui,sans-serif;margin:2rem;color:#1b2430}}
.tiles{{display:flex;gap:1rem;flex-wrap:wrap}}.tile{{border:1px solid #d0d7de;border-radius:8px;padding:1rem 1.5rem}}
.v{{font-size:1.8rem;font-weight:600}}.l{{color:#57606a}}table{{border-collapse:collapse;width:100%;margin-bottom:1rem}}
td,th{{border-bottom:1px solid #d0d7de;padding:.4rem;text-align:left}}h2 span{{color:#57606a;font-weight:400}}</style>
</head><body><h1>{html.escape(title)}</h1><p>{result['total_cis']} CIs analysed</p>
<div class="tiles">{tiles}</div>{''.join(sections)}</body></html>"""
