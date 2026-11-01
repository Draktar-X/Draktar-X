"""Draws assets/actividad.svg: contributions per day over the last 31 days as a smooth line chart.

Reads the contribution calendar of the profile owner (GitHub GraphQL API) and writes a wide bar-chart card
in the same look as the activity graph the profile used before. Standard library only.

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

# ---------------------------------------------------------------- card (line chart, same look as the activity graph)
W, H = 1200, 300
L, R, TOP, BASE = 132, 1172, 70, 222
SANS = "'Segoe UI',Ubuntu,'Helvetica Neue',sans-serif"
step = max(1, math.ceil(peak / 4))
ymax = step * 4
n = len(counts)
xs = [L + (R - L) * i / (n - 1) for i in range(n)]
ys = [BASE - (BASE - TOP) * c / ymax for c in counts]

# monotone cubic (Fritsch-Carlson) so the curve never dips below zero or overshoots a peak
d = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(n - 1)]
m = [d[0]] + [0.0 if d[i - 1] * d[i] <= 0 else (d[i - 1] + d[i]) / 2 for i in range(1, n - 1)] + [d[-1]]
for i in range(n - 1):
    if d[i] == 0:
        m[i] = m[i + 1] = 0.0
    else:
        a, b = m[i] / d[i], m[i + 1] / d[i]
        s = a * a + b * b
        if s > 9:
            t = 3 / math.sqrt(s)
            m[i], m[i + 1] = t * a * d[i], t * b * d[i]
path = f"M{xs[0]:.1f} {ys[0]:.1f}"
for i in range(n - 1):
    h = (xs[i + 1] - xs[i]) / 3
    path += (f" C{xs[i] + h:.1f} {ys[i] + m[i] * h:.1f} {xs[i + 1] - h:.1f} {ys[i + 1] - m[i + 1] * h:.1f}"
             f" {xs[i + 1]:.1f} {ys[i + 1]:.1f}")
area = path + f" L{xs[-1]:.1f} {BASE} L{xs[0]:.1f} {BASE} Z"

parts = []
for k in range(5):
    v = step * k
    yy = BASE - (BASE - TOP) * k / 4
    parts.append(f'<line x1="{L}" y1="{yy:.1f}" x2="{R}" y2="{yy:.1f}" stroke="#3a3f47" stroke-dasharray="2 3"/>'
                 f'<text x="{L - 14}" y="{yy + 4:.1f}" text-anchor="end" font-family="{SANS}" font-size="13" font-weight="600" fill="#C9D1D9">{v}</text>')
for i, x in enumerate(xs):
    parts.append(f'<line x1="{x:.1f}" y1="{TOP}" x2="{x:.1f}" y2="{BASE}" stroke="#3a3f47" stroke-dasharray="2 3"/>'
                 f'<text x="{x:.1f}" y="{BASE + 22}" text-anchor="middle" font-family="{SANS}" font-size="13" font-weight="600" fill="#C9D1D9">{i + 1}</text>')
parts.append(f'<path d="{area}" fill="#484F58" opacity=".22"/>')
parts.append(f'<path d="{path}" fill="none" stroke="#A3A8B3" stroke-width="3.2" stroke-linejoin="round" stroke-linecap="round"/>')
for i, (x, y) in enumerate(zip(xs, ys)):
    parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="#E6EDF3"><title>{days[i][0]} · {counts[i]} contribuciones</title></circle>')
svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Actividad de los últimos 31 días">
<title>Actividad de los últimos 31 días</title>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="6" fill="#141518" stroke="#30363D"/>
<text x="{W / 2}" y="40" text-anchor="middle" font-family="{SANS}" font-size="21" font-weight="600" fill="#E6EDF3">Actividad de los últimos 31 días</text>
<text transform="translate(78 {(TOP + BASE) / 2}) rotate(-90)" text-anchor="middle" font-family="{SANS}" font-size="13" font-weight="600" fill="#C9D1D9">Contributions</text>
<text x="{(L + R) / 2}" y="{BASE + 52}" text-anchor="middle" font-family="{SANS}" font-size="13" font-weight="600" fill="#C9D1D9">Days</text>
{''.join(parts)}
</svg>
"""
os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
with open(OUT, "w") as f:
    f.write(svg)
print(f"wrote {OUT}: total={total} peak={peak}")
