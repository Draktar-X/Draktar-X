"""Draws assets/lenguajes.svg: repos per primary language, same layout as the summary-cards
"Top Languages by Repo" card (340x200, legend left, donut right), coloured with the profile's ember gradient.

Env: GH_TOKEN (required unless --sample/--multi), GH_USER.
Usage: python lenguajes.py [--sample | --multi] [output.svg]
"""
import json
import math
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

OUT = next((a for a in sys.argv[1:] if not a.startswith("--")), "assets/lenguajes.svg")
USER = os.environ.get("GH_USER", "")
QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false) {
      pageInfo { hasNextPage endCursor }
      nodes { primaryLanguage { name } }
    }
  }
}
"""


def fetch():
    counts, cursor = {}, None
    while True:
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=json.dumps({"query": QUERY, "variables": {"login": USER, "cursor": cursor}}).encode(),
            headers={"Authorization": f"bearer {os.environ['GH_TOKEN']}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            body = json.load(r)
        if "errors" in body:
            raise RuntimeError(body["errors"])
        data = body["data"]["user"]["repositories"]
        for n in data["nodes"]:
            if n["primaryLanguage"]:
                k = n["primaryLanguage"]["name"]
                counts[k] = counts.get(k, 0) + 1
        if not data["pageInfo"]["hasNextPage"]:
            return counts
        cursor = data["pageInfo"]["endCursor"]


if "--sample" in sys.argv:
    counts = {"Python": 3}
elif "--multi" in sys.argv:
    counts = {"Python": 5, "Shell": 3, "HTML": 2, "Dockerfile": 1}
else:
    try:
        counts = fetch()
    except Exception as e:  # keep the previous card rather than failing the whole workflow
        print(f"lenguajes: no se pudo leer la API ({e}); se conserva la tarjeta anterior")
        sys.exit(0)

langs = sorted(counts.items(), key=lambda kv: -kv[1])[:5]
total = sum(v for _, v in langs) or 1

# ember gradient: gold -> red -> dark red
STOPS = [(0.0, (209, 184, 102)), (0.55, (229, 56, 61)), (1.0, (142, 16, 20))]


def ember(t):
    for (t0, c0), (t1, c1) in zip(STOPS, STOPS[1:]):
        if t <= t1:
            k = (t - t0) / (t1 - t0) if t1 > t0 else 0
            return "#%02x%02x%02x" % tuple(round(a + (b - a) * k) for a, b in zip(c0, c1))
    return "#%02x%02x%02x" % STOPS[-1][1]


BG, BORDER, TITLE, TEXT, MUTED = "#141518", "#30363D", "#E6EDF3", "#C9D1D9", "#6e7681"
CX, CY, RO, RI = 230, 120, 60, 35           # same centre and radii as the original card
parts = []
if not langs:
    parts.append(f'<text x="40" y="70" style="fill:{MUTED};font-size:14px">sin repos todavía</text>')
for i, (name, n) in enumerate(langs):
    col = "#E5383D" if len(langs) == 1 else ember(i / max(1, len(langs) - 1))
    y = 18 + i * 25.2
    pct = round(100 * n / total)
    parts.append(
        f'<rect x="40" y="{40 + y:.1f}" width="14" height="14" fill="{col}" stroke="{BG}" stroke-width="1"/>'
        f'<text x="56.8" y="{40 + y + 12:.1f}" style="fill:{TEXT};font-size:14px">{escape(name)}'
        f'<tspan dx="6" style="fill:{MUTED};font-size:12px">{pct}%</tspan></text>'
    )


def seg(a0, a1):
    def p(r, a):
        return CX + r * math.sin(a), CY - r * math.cos(a)
    large = 1 if a1 - a0 > math.pi else 0
    (x0, y0), (x1, y1) = p(RO, a0), p(RO, a1)
    (x2, y2), (x3, y3) = p(RI, a1), p(RI, a0)
    return (f"M{x0:.2f} {y0:.2f} A{RO} {RO} 0 {large} 1 {x1:.2f} {y1:.2f} "
            f"L{x2:.2f} {y2:.2f} A{RI} {RI} 0 {large} 0 {x3:.2f} {y3:.2f} Z")


defs = ""
if len(langs) == 1:
    defs = ('<linearGradient id="ember" x1="0" y1="0" x2="1" y2="1">'
            '<stop offset="0" stop-color="#D1B866"/><stop offset=".55" stop-color="#E5383D"/>'
            '<stop offset="1" stop-color="#8E1014"/></linearGradient>')
    parts.append(f'<path d="{seg(0, math.pi)} {seg(math.pi, 2 * math.pi)}" fill="url(#ember)"/>')
elif langs:
    a = 0.0
    for i, (name, n) in enumerate(langs):
        b = a + 2 * math.pi * n / total
        parts.append(f'<path d="{seg(a, b)}" fill="{ember(i / max(1, len(langs) - 1))}" stroke="{BG}" stroke-width="2"/>')
        a = b

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="340" height="200" viewBox="0 0 340 200" role="img" aria-label="Top Languages by Repo">
<title>Top Languages by Repo</title>
<style>* {{ font-family: 'Segoe UI', Ubuntu, "Helvetica Neue", Sans-Serif }}</style>
<defs>{defs}</defs>
<rect x="1" y="1" rx="5" ry="5" height="99%" width="99.41176470588235%" stroke="{BORDER}" stroke-width="1" fill="{BG}"/>
<text x="30" y="40" style="font-size:22px;fill:{TITLE}">Top Languages by Repo</text>
{''.join(parts)}
</svg>
"""
os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
with open(OUT, "w") as f:
    f.write(svg)
print(f"wrote {OUT}: {langs}")
