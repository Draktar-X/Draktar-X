"""Draws assets/commits-hora.svg: commits per hour of day as a bar chart in the spectrum colours of the profile.

Reads the commits the profile owner authored on the default branch of their public repositories
(GitHub GraphQL API, up to 100 repos x 100 commits each), buckets them by local hour and writes an SVG card
that matches the rest of the profile. Standard library only.

Env: GH_TOKEN (required unless --sample), GH_USER, TZ_OFFSET (hours, default -5 for Ecuador).
Usage: python commits_hora.py [--sample | --empty] [output.svg]
"""
import json
import math
import os
import random
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

OUT = next((a for a in sys.argv[1:] if not a.startswith("--")), "assets/commits-hora.svg")
SAMPLE = "--sample" in sys.argv
USER = os.environ.get("GH_USER", "")
TZ = timezone(timedelta(hours=float(os.environ.get("TZ_OFFSET", "-5"))))

QUERY = """
query($login: String!, $cursor: String, $uid: ID!) {
  user(login: $login) {
    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      pageInfo { hasNextPage endCursor }
      nodes { defaultBranchRef { target { ... on Commit {
        history(first: 100, author: {id: $uid}) { nodes { authoredDate } }
      } } } }
    }
  }
}
"""


def gql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {os.environ['GH_TOKEN']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        body = json.load(r)
    if "errors" in body:
        raise SystemExit(f"GraphQL error: {body['errors']}")
    return body["data"]


def fetch_hours():
    uid = gql("query($l:String!){user(login:$l){id}}", {"l": USER})["user"]["id"]
    hours, cursor = [0] * 24, None
    while True:
        data = gql(QUERY, {"login": USER, "cursor": cursor, "uid": uid})["user"]["repositories"]
        for repo in data["nodes"]:
            ref = repo.get("defaultBranchRef")
            if not ref or not ref.get("target"):
                continue
            for c in ref["target"]["history"]["nodes"]:
                t = datetime.fromisoformat(c["authoredDate"].replace("Z", "+00:00")).astimezone(TZ)
                hours[t.hour] += 1
        if not data["pageInfo"]["hasNextPage"]:
            return hours
        cursor = data["pageInfo"]["endCursor"]


def sample_hours():
    rnd = random.Random(3)
    return [max(0, round(14 * math.exp(-((h - 11) / 3.2) ** 2) + 9 * math.exp(-((h - 20) / 1.8) ** 2) + rnd.random() * 2)) for h in range(24)]


if "--empty" in sys.argv:
    hours = [0] * 24
elif SAMPLE:
    hours = sample_hours()
else:
    try:
        hours = fetch_hours()
    except Exception as e:  # keep the previous card rather than failing the whole workflow
        print(f"commits_hora: no se pudo leer la API ({e}); se conserva la tarjeta anterior")
        sys.exit(0)
total, peak = sum(hours), max(hours) or 1

# ---------------------------------------------------------------- card (static bar chart, spectrum colours)
W, H = 340, 200
L, R, TOP, BASE = 52, 322, 58, 160
MONO = "'JetBrains Mono','Fira Code',Consolas,'DejaVu Sans Mono',Menlo,monospace"
SANS = "'Segoe UI',Ubuntu,'Helvetica Neue',sans-serif"


def nice_max(v):
    for e in range(0, 6):
        for m in (1, 2, 5):
            if m * 10 ** e * 5 >= v:
                return m * 10 ** e * 5
    return v


ymax = max(5, math.ceil(peak * 1.1 / 5) * 5) if total else 5
step = ymax / 5
slot = (R - L) / 24
bw = slot * 0.72
peak_h = (BASE - TOP) * peak / ymax if total else 0
parts = []
for i in range(6):  # y axis ticks
    v = step * i
    yy = BASE - (BASE - TOP) * i / 5
    parts.append(f'<line x1="{L - 4}" y1="{yy:.1f}" x2="{L}" y2="{yy:.1f}" stroke="#6e7681"/>'
                 f'<text x="{L - 7}" y="{yy + 3:.1f}" text-anchor="end" font-family="{SANS}" font-size="9" fill="#8b949e">{v:g}</text>')
parts.append(f'<line x1="{L}" y1="{TOP - 4}" x2="{L}" y2="{BASE}" stroke="#6e7681"/>'
             f'<line x1="{L}" y1="{BASE}" x2="{R}" y2="{BASE}" stroke="#6e7681"/>')
for h, n in enumerate(hours):
    x = L + h * slot + (slot - bw) / 2
    bh = max(1.5, (BASE - TOP) * n / ymax) if n else 1.5
    parts.append(f'<rect x="{x:.1f}" y="{BASE - bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="url(#g)">'
                 f'<title>{h:02d}:00 · {n} commits</title></rect>')
for h in (0, 6, 12, 18, 23):
    x = L + h * slot + slot / 2
    parts.append(f'<line x1="{x:.1f}" y1="{BASE}" x2="{x:.1f}" y2="{BASE + 4}" stroke="#6e7681"/>'
                 f'<text x="{x:.1f}" y="{BASE + 14}" text-anchor="middle" font-family="{SANS}" font-size="9" fill="#8b949e">{h}</text>')
parts.append(f'<text x="{R}" y="{BASE + 28}" text-anchor="end" font-family="{SANS}" font-size="8.5" fill="#8b949e">hora del día</text>')
best = max(range(24), key=lambda h: hours[h])
note = "datos de ejemplo" if SAMPLE else (f"pico {best:02d}:00" if total else "sin commits públicos todavía")
gtop = BASE - max(peak_h, 8)
svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Commits por hora">
<title>Commits por hora</title>
<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" x1="0" x2="0" y1="{gtop:.1f}" y2="{BASE}">
<stop offset="0" stop-color="#e5383d"/><stop offset="0.07" stop-color="#e5383d"/><stop offset="0.075" stop-color="#e6edf3"/>
<stop offset="0.5" stop-color="#a3a8b3"/><stop offset="1" stop-color="#3a3f47"/></linearGradient></defs>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="4.5" fill="#141518" stroke="#30363D"/>
<text x="30" y="38" font-family="{SANS}" font-size="20" fill="#E6EDF3">Commits</text>
{''.join(parts)}
<text x="{L}" y="{BASE + 28}" font-family="{MONO}" font-size="8.5" fill="#6e7681">{note}</text>
</svg>
"""
os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
with open(OUT, "w") as f:
    f.write(svg)
print(f"wrote {OUT}: total={total} peak_hour={best}")
