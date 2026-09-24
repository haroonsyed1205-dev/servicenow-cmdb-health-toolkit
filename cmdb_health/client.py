"""Minimal ServiceNow Table API reader (read-only, standard library only)."""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

CI_FIELDS = "sys_id,name,sys_class_name,serial_number,owned_by,support_group,environment,last_discovered,operational_status"
REL_FIELDS = "parent,child,type"


class TableClient:
    def __init__(self, instance: str, user: str, password: str, page_size: int = 1000, retries: int = 3):
        if not instance.startswith("https://"):
            raise ValueError("instance must be an https:// URL")
        self.base = instance.rstrip("/")
        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        self.headers = {"Authorization": f"Basic {token}", "Accept": "application/json"}
        self.page_size = page_size
        self.retries = retries

    @classmethod
    def from_env(cls) -> "TableClient":
        missing = [k for k in ("SN_INSTANCE", "SN_USER", "SN_PASSWORD") if not os.environ.get(k)]
        if missing:
            raise RuntimeError("Set environment variables: " + ", ".join(missing))
        return cls(os.environ["SN_INSTANCE"], os.environ["SN_USER"], os.environ["SN_PASSWORD"])

    def _get(self, url: str) -> dict:
        for attempt in range(1, self.retries + 1):
            try:
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=60) as resp:
                    return json.loads(resp.read())
            except urllib.error.HTTPError as err:
                if err.code in (429, 500, 502, 503, 504) and attempt < self.retries:
                    time.sleep(2 ** attempt)
                    continue
                raise
        raise RuntimeError("unreachable")

    def records(self, table: str, fields: str, query: str = "") -> list[dict]:
        out, offset = [], 0
        while True:
            params = urllib.parse.urlencode({
                "sysparm_fields": fields,
                "sysparm_query": query,
                "sysparm_limit": self.page_size,
                "sysparm_offset": offset,
                "sysparm_exclude_reference_link": "true",
            })
            batch = self._get(f"{self.base}/api/now/table/{table}?{params}").get("result", [])
            out.extend(batch)
            if len(batch) < self.page_size:
                return out
            offset += self.page_size

    def snapshot(self, ci_query: str = "") -> dict:
        return {
            "cis": self.records("cmdb_ci", CI_FIELDS, ci_query),
            "relationships": self.records("cmdb_rel_ci", REL_FIELDS),
        }
