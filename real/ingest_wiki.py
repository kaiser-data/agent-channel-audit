"""Stream the public dse-wiki request logs and keep a minimal, pseudonymised event table (PROTOCOL D7).

Raw lines are never written to disk. IPs are replaced by a salted HMAC (salt kept outside the repo,
in ~/.config/aca-wiki-salt). Kept per request: t (unix s), principal, op, page.
  principal = wiki username (NAME) if set, else "ip:" + HMAC(IP)[:12]
  op: 0 = write (action=form_edit save), 1 = read (browse / bare page / view source), 2 = other
Usage: python3 real/ingest_wiki.py 2603 2604 2605 2606 2607
Output: real/data/events_<month>.csv.gz  (not for redistribution; see README)
"""
import csv
import gzip
import hashlib
import hmac
import os
import secrets
import sys
import urllib.request
from urllib.parse import parse_qs, unquote_plus, urlsplit

BASE = "https://www.wikiservice.at/dse/log_{}"
OUT = os.path.join(os.path.dirname(__file__), "data")
SALT_PATH = os.path.expanduser("~/.config/aca-wiki-salt")
READ_ACTIONS = {"browse", "edit"}


def salt():
    if not os.path.exists(SALT_PATH):
        os.makedirs(os.path.dirname(SALT_PATH), exist_ok=True)
        with open(SALT_PATH, "w") as f:
            f.write(secrets.token_hex(32))
        os.chmod(SALT_PATH, 0o600)
    return open(SALT_PATH).read().strip().encode()


def fields(line):
    parts = line.rstrip("\n").split("|")
    d = {}
    for i in range(2, len(parts) - 1, 2):  # parts: #DONE2, 1, then key|value pairs
        d.setdefault(parts[i], parts[i + 1])
    # ACTION may itself contain '|': rebuild it between "ACTION" and the last "TS"
    if "ACTION" in parts and "TS" in parts:
        a, t = parts.index("ACTION"), len(parts) - 1 - parts[::-1].index("TS")
        d["ACTION"] = "|".join(parts[a + 1:t])
        d["TS"] = parts[t + 1] if t + 1 < len(parts) else ""
    return d


def classify(url):
    u = urlsplit(url)
    if "/dse/" not in u.path:
        return None, None
    q = u.query
    if q and "=" not in q.split("&")[0]:  # bare wiki.cgi?PageName
        return 1, unquote_plus(q.split("&")[0])
    p = parse_qs(q, keep_blank_values=True)
    action = (p.get("action") or [""])[0]
    page = (p.get("id") or [""])[0]
    if action == "form_edit" and "form_edit" in p and page:
        return 0, page
    if action in READ_ACTIONS and page:
        return 1, page
    return 2, ""


def ingest(month, key):
    os.makedirs(OUT, exist_ok=True)
    n = {0: 0, 1: 0, 2: 0, "skip": 0}
    with urllib.request.urlopen(BASE.format(month)) as r, \
            gzip.open(f"{OUT}/events_{month}.csv.gz", "wt", newline="") as fo:
        w = csv.writer(fo)
        w.writerow(["t", "principal", "op", "page"])
        for raw in r:
            line = raw.decode("utf-8", "replace")
            if not line.startswith("#DONE2"):
                n["skip"] += 1
                continue
            d = fields(line)
            try:
                t = int(d.get("TS", ""))
            except ValueError:
                n["skip"] += 1
                continue
            op, page = classify(d.get("ACTION", ""))
            if op is None:
                n["skip"] += 1
                continue
            name = d.get("NAME", "").strip()
            principal = name if name else "ip:" + hmac.new(key, d.get("IP", "").encode(), hashlib.sha256).hexdigest()[:12]
            w.writerow([t, principal, op, page])
            n[op] += 1
    print(month, n, flush=True)


if __name__ == "__main__":
    key = salt()
    for m in sys.argv[1:]:
        ingest(m, key)
