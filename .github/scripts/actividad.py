"""Draws assets/actividad.svg: contributions per day over the last 31 days, in the profile's spectrum colours.

Reads the contribution calendar of the profile owner (GitHub GraphQL API) and writes a wide bar-chart card
that matches the Commits card. Standard library only.

Env: GH_TOKEN (required unless --sample/--empty), GH_USER.
Usage: python actividad.py [--sample | --empty] [output.svg]
"""
import json
import math
import os
import random
import sys
import urllib.request
from datetime import date, timedelta

OUT = next((a for a in sys.argv[1:] if not a.startswith("--")), "assets/actividad.svg")
DAYS = 31
USER = os.environ.get("GH_USER", "")

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar { weeks { contributionDays { date contributionCount } } }
    }
  }
}
"""


def fetch_days():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GH_TOKEN']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        body = json.load(r)
    if "errors" in body:
        raise RuntimeError(body["errors"])
    weeks = body["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [(d["date"], d["contributionCount"]) for w in weeks for d in w["contributionDays"]]
    return days[-DAYS:]


def fake_days(sample):
    today = date.today()
    rnd = random.Random(5)
    out = []
    for i in range(DAYS):
        d = today - timedelta(days=DAYS - 1 - i)
        n = max(0, round(3 + 3 * math.sin(i / 3) + rnd.random() * 3 - 1)) if sample else 0
        out.append((d.isoformat(), n))
    return out


if "--empty" in sys.argv or "--sample" in sys.argv:
    days = fake_days("--sample" in sys.argv)
else:
    try:
        days = fetch_days()
    except Exception as e:  # keep the previous card rather than failing the whole workflow
        print(f"actividad: no se pudo leer la API ({e}); se conserva la tarjeta anterior")
        sys.exit(0)

counts = [n for _, n in days]
total, peak = sum(counts), max(counts) if counts else 0

# ---------------------------------------------------------------- card
W, H = 880, 230
L, R, TOP, BASE = 56, 850, 62, 180
MONO = "'JetBrains Mono','Fira Code',Consolas,'DejaVu Sans Mono',Menlo,monospace"
SANS = "'Segoe UI',Ubuntu,'Helvetica Neue',sans-serif"
ymax = max(5, math.ceil(peak * 1.1 / 5) * 5) if total else 5
slot = (R - L) / len(days)
bw = slot * 0.62
peak_h = (BASE - TOP) * peak / ymax if total else 0
parts = []
for i in range(6):
    v = ymax / 5 * i
    yy = BASE - (BASE - TOP) * i / 5
    parts.append(f'<line x1="{L}" y1="{yy:.1f}" x2="{R}" y2="{yy:.1f}" stroke="#1f2228"/>'
                 f'<text x="{L - 8}" y="{yy + 3:.1f}" text-anchor="end" font-family="{SANS}" font-size="10" fill="#8b949e">{v:g}</text>')
parts.append(f'<line x1="{L}" y1="{BASE}" x2="{R}" y2="{BASE}" stroke="#6e7681"/>')
for i, (d, n) in enumerate(days):
    x = L + i * slot + (slot - bw) / 2
    bh = max(1.5, (BASE - TOP) * n / ymax) if n else 1.5
    parts.append(f'<rect x="{x:.1f}" y="{BASE - bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="1" fill="url(#g)">'
                 f'<title>{d} · {n} contribuciones</title></rect>')
    if i % 5 == 0 or i == len(days) - 1:
        dd = date.fromisoformat(d)
        parts.append(f'<text x="{x + bw / 2:.1f}" y="{BASE + 16}" text-anchor="middle" font-family="{SANS}" font-size="10" fill="#8b949e">{dd.day:02d}/{dd.month:02d}</text>')
note = "datos de ejemplo" if "--sample" in sys.argv else (f"{total} contribuciones" if total else "sin contribuciones en este periodo")
gtop = BASE - max(peak_h, 8)
svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Actividad de los últimos 31 días">
<title>Actividad de los últimos 31 días</title>
<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" x1="0" x2="0" y1="{gtop:.1f}" y2="{BASE}">
<stop offset="0" stop-color="#e5383d"/><stop offset="0.07" stop-color="#e5383d"/><stop offset="0.075" stop-color="#e6edf3"/>
<stop offset="0.5" stop-color="#a3a8b3"/><stop offset="1" stop-color="#3a3f47"/></linearGradient></defs>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="6" fill="#141518" stroke="#30363D"/>
<text x="32" y="40" font-family="{SANS}" font-size="20" fill="#E6EDF3">Actividad</text>
<text x="{W - 32}" y="40" text-anchor="end" font-family="{MONO}" font-size="10" fill="#6e7681">últimos 31 días · {note}</text>
{''.join(parts)}
</svg>
"""
os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
with open(OUT, "w") as f:
    f.write(svg)
print(f"wrote {OUT}: total={total} peak={peak}")
