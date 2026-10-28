"""Fetches live GitHub data and renders the themed stat cards into dist/.

Runs in CI (see .github/workflows/profile.yml) with GITHUB_TOKEN, or locally:
    GITHUB_TOKEN=$(gh auth token) python scripts/build_stats.py dist

Set PROFILE_TOKEN (a classic PAT with read:user) in the repo secrets to also
count private contributions in the language and repository numbers.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgkit import (MONO, SANS, THEMES, aurora_blobs, aurora_defs, beam_gradient, border_beam,  # noqa: E402
                    esc, fmt, font, glass, glow_filter, gradient_text_defs, grain_filter, icon, shimmer, svg, text)

LOGIN = os.environ.get("PROFILE_LOGIN", "ShahzadUmarBaig")
TOKEN = os.environ.get("PROFILE_TOKEN") or os.environ.get("GITHUB_TOKEN")
API = "https://api.github.com"
FEATURED = [("Blocship", "stories_page_view"), ("hashirshoaeb", "star_book"),
            ("Blocship", "code_keg"), ("ShahzadUmarBaig", "Firebase_cloud_messaging_ftth")]
EASE = "cubic-bezier(.22,1,.36,1)"


# --------------------------------------------------------------------------- #
# GitHub API
# --------------------------------------------------------------------------- #
def request(url: str, data: dict | None = None) -> dict:
    if not TOKEN:
        raise SystemExit("GITHUB_TOKEN (or PROFILE_TOKEN) is required")
    req = urllib.request.Request(
        url, data=json.dumps(data).encode() if data else None,
        headers={"Authorization": f"bearer {TOKEN}", "Accept": "application/vnd.github+json",
                 "User-Agent": "profile-stats", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def gql(query: str, **variables) -> dict:
    """GraphQL with retries: GitHub occasionally answers with a partial calendar or a secondary rate limit."""
    import time
    last = None
    for attempt in range(4):
        try:
            out = request(API + "/graphql", {"query": query, "variables": variables})
            if "errors" in out:
                raise RuntimeError(json.dumps(out["errors"], indent=2))
            return out["data"]
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 ** attempt)
    raise SystemExit(f"GraphQL failed after retries: {last}")


Q_USER = """
query($login:String!, $prq:String!, $isq:String!){ user(login:$login){
  name login createdAt
  followers{totalCount}
  organizations(first:1){totalCount}
  repositories(first:100, ownerAffiliations:OWNER, isFork:false, orderBy:{field:STARGAZERS, direction:DESC}){
    totalCount nodes{ stargazerCount languages(first:10, orderBy:{field:SIZE, direction:DESC}){ edges{ size node{ name color } } } } }
  repositoriesContributedTo(first:1, contributionTypes:[COMMIT,PULL_REQUEST,ISSUE,REPOSITORY], includeUserRepositories:false){ totalCount }
  contributionsCollection{ totalCommitContributions restrictedContributionsCount totalRepositoriesWithContributedCommits
    contributionCalendar{ totalContributions weeks{ contributionDays{ date contributionCount contributionLevel weekday } } } }
}
prs: search(query:$prq, type:ISSUE){ issueCount }
issues: search(query:$isq, type:ISSUE){ issueCount }
}"""

Q_YEAR = """
query($login:String!, $from:DateTime!, $to:DateTime!){ user(login:$login){
  contributionsCollection(from:$from, to:$to){ contributionCalendar{ totalContributions weeks{ contributionDays{ date contributionCount } } } } } }"""

Q_REPO = """
query($owner:String!, $name:String!){ repository(owner:$owner, name:$name){
  name nameWithOwner description url stargazerCount forkCount primaryLanguage{ name color } } }"""


def fetch() -> dict:
    u = gql(Q_USER, login=LOGIN, prq=f"author:{LOGIN} is:pr", isq=f"author:{LOGIN} is:issue")
    user = u["user"]
    created = dt.datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00"))
    today = dt.datetime.now(dt.timezone.utc)
    days: dict[str, int] = {}
    yearly: dict[int, int] = {}
    for year in range(created.year, today.year + 1):
        start = max(created, dt.datetime(year, 1, 1, tzinfo=dt.timezone.utc))
        end = min(today, dt.datetime(year, 12, 31, 23, 59, 59, tzinfo=dt.timezone.utc))
        expected = (end.date() - start.date()).days + 1
        for attempt in range(3):  # a full year must come back as full weeks covering every day
            cal = gql(Q_YEAR, **{"login": LOGIN, "from": start.isoformat(), "to": end.isoformat()})["user"]["contributionsCollection"]["contributionCalendar"]
            got = sum(len(w["contributionDays"]) for w in cal["weeks"])
            if got >= expected:
                break
            print(f"  year {year}: calendar returned {got} days, expected {expected}; retrying")
        yearly[year] = cal["totalContributions"]
        for w in cal["weeks"]:
            for d in w["contributionDays"]:
                days[d["date"]] = d["contributionCount"]
    repos = []
    for owner, name in FEATURED:
        try:
            repos.append(gql(Q_REPO, owner=owner, name=name)["repository"])
        except SystemExit as e:  # repo renamed/removed: skip rather than fail the build
            print(f"skip {owner}/{name}: {e}")
    return dict(user=user, days=days, yearly=yearly, repos=[r for r in repos if r], created=created, today=today,
                prs=u["prs"]["issueCount"], issues=u["issues"]["issueCount"])


# --------------------------------------------------------------------------- #
# Derived numbers
# --------------------------------------------------------------------------- #
def streaks(days: dict[str, int], today: dt.date):
    dates = sorted(days)
    cur, longest, run = 0, (0, None, None), (0, None, None)
    prev = None
    for ds in dates:
        d = dt.date.fromisoformat(ds)
        if days[ds] > 0:
            if prev and (d - prev).days == 1 and run[0] > 0:
                run = (run[0] + 1, run[1], d)
            else:
                run = (1, d, d)
            if run[0] > longest[0]:
                longest = run
        else:
            run = (0, None, None)
        prev = d
    # current streak: ends today or yesterday
    d = today
    if days.get(d.isoformat(), 0) == 0:
        d = today - dt.timedelta(days=1)
    cur_start = None
    while days.get(d.isoformat(), 0) > 0:
        cur += 1; cur_start = d; d -= dt.timedelta(days=1)
    return dict(current=cur, current_start=cur_start, longest=longest[0], longest_start=longest[1], longest_end=longest[2])


def human(n: int) -> str:
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 10_000: return f"{n/1000:.1f}k"
    return f"{n:,}"


def date_short(d: dt.date | None) -> str:
    return d.strftime("%b %-d, %Y") if d else "—"


def wrap(s: str, f, size: float, max_w: float, max_lines: int = 2) -> list[str]:
    words, lines, cur = s.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if f.width(trial, size) <= max_w:
            cur = trial
        else:
            lines.append(cur); cur = w
            if len(lines) == max_lines: break
    if len(lines) < max_lines and cur: lines.append(cur)
    if len(lines) == max_lines and (len(" ".join(lines)) < len(s)):
        last = lines[-1]
        while f.width(last + "…", size) > max_w and last: last = last[:-1]
        lines[-1] = last.rstrip() + "…"
    return lines


def smooth_path(pts: list[tuple[float, float]]) -> str:
    """Catmull-Rom -> cubic bezier for a soft sparkline."""
    if len(pts) < 2: return ""
    d = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}"
    return d


def card_frame(t: dict, W: int, H: int, cid: str, seed: int, aurora_op=0.45):
    """Common card background: gradient, soft aurora, grain, border + beam."""
    defs = [f'<clipPath id="{cid}"><rect width="{W}" height="{H}" rx="24"/></clipPath>',
            f'<linearGradient id="{cid}bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["bg"]}"/><stop offset="1" stop-color="{t["bg2"]}"/></linearGradient>',
            aurora_defs(t, cid + "a"), grain_filter(cid + "g"), beam_gradient(t, cid + "b")]
    css, blobs = aurora_blobs(t, W, H, prefix=cid + "a", seed=seed)
    open_ = (f'<g clip-path="url(#{cid})"><rect width="{W}" height="{H}" fill="url(#{cid}bg)"/>'
             f'<g opacity="{aurora_op}">{blobs}</g>'
             f'<rect width="{W}" height="{H}" filter="url(#{cid}g)" opacity="{t["grain"]}" style="mix-blend-mode:overlay"/>')
    close = (f'</g><rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="23.5" fill="none" stroke="{t["line"]}"/>'
             + border_beam(0.5, 0.5, W - 1, H - 1, 23.5, gid=cid + "b", seg=140, dur=7, width=1.4))
    return "".join(defs), css, open_, close


# --------------------------------------------------------------------------- #
# Cards
# --------------------------------------------------------------------------- #
def overview(t: dict, D: dict) -> str:
    W, H = 720, 300
    f800, f500, m600 = font("Sora", 800), font("Sora", 500), font("JetBrains Mono", 600)
    u = D["user"]
    total = sum(D["yearly"].values())
    last12 = u["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    defs, css, open_, close = card_frame(t, W, H, "ov", seed=21)
    defs += gradient_text_defs(t, "ovt", 420) + glow_filter("ovg", 12)
    css += ("@keyframes draw{0%{stroke-dashoffset:1200}100%{stroke-dashoffset:0}}"
            "@keyframes fade{0%{opacity:0}100%{opacity:1}}"
            "@keyframes up{0%{opacity:0;transform:translateY(10px)}100%{opacity:1;transform:translateY(0)}}")
    defs += (f'<linearGradient id="ovs" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{t["cyan"]}"/><stop offset="1" stop-color="{t["magenta"]}"/></linearGradient>'
             f'<linearGradient id="ova" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["violet"]}" stop-opacity=".35"/><stop offset="1" stop-color="{t["violet"]}" stop-opacity="0"/></linearGradient>')
    b = [open_]
    # left: big number
    b.append(text(36, 54, "CONTRIBUTIONS · ALL TIME", 11.5, fill=t["muted"], weight=600, family=MONO, spacing=1.4))
    num = f"{total:,}"
    b.append(f'<g style="animation:up 1s .1s {EASE} both">')
    b.append(text(34, 128, num, 68, fill="url(#ovt)", weight=800, extra=f' filter="url(#ovg)" opacity="{0.5 if t["name"]=="dark" else 0.2}"'))
    b.append(text(34, 128, num, 68, fill="url(#ovt)", weight=800))
    b.append("</g>")
    b.append(text(36, 156, f"since {D['created'].strftime('%B %Y')}  ·  {len([y for y in D['yearly'].values() if y])} active years", 13, fill=t["muted"], weight=500))
    # sparkline: last 12 months
    months = []
    today = D["today"].date()
    for i in range(11, -1, -1):
        m = (today.month - i - 1) % 12 + 1
        y = today.year if today.month - i > 0 else today.year - 1
        months.append((y, m))
    totals = {ym: 0 for ym in months}
    for ds, c in D["days"].items():
        d = dt.date.fromisoformat(ds)
        if (d.year, d.month) in totals: totals[(d.year, d.month)] += c
    vals = [totals[ym] for ym in months]
    mx = max(vals) or 1
    x0, x1, yb, yt = 36, 380, 262, 190
    pts = [(x0 + i * (x1 - x0) / 11, yb - (v / mx) * (yb - yt)) for i, v in enumerate(vals)]
    path = smooth_path(pts)
    b.append(f'<path d="{path} L{x1} {yb+6} L{x0} {yb+6} Z" fill="url(#ova)" style="animation:fade 1.2s .9s both"/>')
    b.append(f'<path d="{path}" fill="none" stroke="url(#ovs)" stroke-width="2.5" stroke-linecap="round" stroke-dasharray="1200" style="animation:draw 2.2s .3s {EASE} both"/>')
    px, py = pts[-1]
    b.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.5" fill="{t["magenta"]}" style="animation:fade .6s 2.2s both"/>'
             f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.5" fill="none" stroke="{t["magenta"]}" style="animation:fade .6s 2.2s both"><animate attributeName="r" values="4;14" dur="1.8s" begin="2.4s" repeatCount="indefinite"/><animate attributeName="opacity" values=".8;0" dur="1.8s" begin="2.4s" repeatCount="indefinite"/></circle>')
    b.append(text(x0, 282, months[0][0].__str__() + " " + dt.date(months[0][0], months[0][1], 1).strftime("%b"), 10.5, fill=t["faint"], weight=600, family=MONO))
    b.append(text(x1, 282, "last 12 months", 10.5, fill=t["faint"], weight=600, family=MONO, anchor="end"))
    # right: tiles
    tiles = [("Last 12 months", human(last12)), ("Repos contributed", str(u["repositoriesContributedTo"]["totalCount"])),
             ("Pull requests", str(D["prs"])), ("Issues opened", str(D["issues"]))]
    tx, ty, tw, th = 404, 44, 142, 100
    for i, (lab, val) in enumerate(tiles):
        x = tx + (i % 2) * (tw + 12); y = ty + (i // 2) * (th + 12)
        b.append(f'<g style="animation:up .9s {0.25 + i*0.12:.2f}s {EASE} both">' + glass(x, y, tw, th, 16, t)
                 + text(x + 16, y + 48, val, 30, fill=t["ink"], weight=800)
                 + text(x + 16, y + 78, lab, 11.5, fill=t["muted"], weight=600, family=MONO) + "</g>")
    b.append(close)
    return svg(W, H, "".join(b), style=css, defs=defs,
               font_specs=(("Sora", 800), ("Sora", 500), ("JetBrains Mono", 600)), aria=f"{total:,} contributions all time")


def streak(t: dict, D: dict) -> str:
    W, H = 460, 300
    s = streaks(D["days"], D["today"].date())
    defs, css, open_, close = card_frame(t, W, H, "st", seed=33)
    defs += (f'<linearGradient id="stg" x1="0" y1="1" x2="1" y2="0"><stop offset="0" stop-color="{t["cyan"]}"/><stop offset=".5" stop-color="{t["violet"]}"/><stop offset="1" stop-color="{t["magenta"]}"/></linearGradient>'
             f'<linearGradient id="fl" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="{t["magenta"]}"/><stop offset="1" stop-color="{t["amber"]}"/></linearGradient>'
             + glow_filter("stglow", 8))
    css += ("@keyframes flick{0%{transform:scale(1,1)}30%{transform:scale(1.05,.96)}60%{transform:scale(.97,1.05)}100%{transform:scale(1,1)}}"
            "@keyframes up{0%{opacity:0;transform:translateY(10px)}100%{opacity:1;transform:translateY(0)}}")
    b = [open_]
    cx, cy, r = 130, 150, 78
    C = 2 * math.pi * r
    ratio = max(0.04, min(1.0, s["current"] / max(s["longest"], 1)))
    b.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{t["line2"]}" stroke-width="10"/>')
    b.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="url(#stg)" stroke-width="10" stroke-linecap="round" '
             f'stroke-dasharray="{C:.1f}" stroke-dashoffset="{C:.1f}" transform="rotate(-90 {cx} {cy})" filter="url(#stglow)">'
             f'<animate attributeName="stroke-dashoffset" from="{C:.1f}" to="{C*(1-ratio):.1f}" dur="1.8s" begin="0.2s" fill="freeze" calcMode="spline" keySplines="0.22 1 0.36 1" keyTimes="0;1"/></circle>')
    # flame
    b.append(f'<g transform="translate({cx} {cy-62})"><g style="animation:flick 1.3s ease-in-out infinite;transform-origin:0 10px">'
             f'<path d="M0 -12 C6 -4 10 2 10 7 A10 10 0 0 1 -10 7 C-10 1 -4 -3 -2 -8 C0 -4 3 -2 3 1 C5 -2 2 -8 0 -12z" fill="url(#fl)"/>'
             f'<path d="M0 -1 C3 2 4.5 4 4.5 6.5 A4.5 4.5 0 0 1 -4.5 6.5 C-4.5 4 -2 2 0 -1z" fill="#fff" opacity=".85"/></g></g>')
    b.append(f'<g style="animation:up 1s .3s {EASE} both">' + text(cx, cy + 18, str(s["current"]), 50, fill=t["ink"], weight=800, anchor="middle")
             + text(cx, cy + 42, "DAY STREAK", 11, fill=t["muted"], weight=600, family=MONO, anchor="middle", spacing=1.6) + "</g>")
    # right column
    rx = 250
    rows = [("Current streak", f"{s['current']} days", f"since {date_short(s['current_start'])}" if s["current"] else "start one today"),
            ("Longest streak", f"{s['longest']} days", f"{date_short(s['longest_start'])} → {date_short(s['longest_end'])}"),
            ("Active days · 12 mo", str(sum(1 for d, c in D["days"].items() if c > 0 and dt.date.fromisoformat(d) >= D["today"].date() - dt.timedelta(days=365))), "days with a contribution")]
    for i, (lab, val, sub) in enumerate(rows):
        y = 70 + i * 80
        b.append(f'<g style="animation:up .9s {0.4 + i*0.15:.2f}s {EASE} both">'
                 + f'<rect x="{rx}" y="{y-6}" width="3" height="40" rx="1.5" fill="{(t["cyan"], t["violet"], t["magenta"])[i]}"/>'
                 + text(rx + 16, y + 6, lab.upper(), 10.5, fill=t["muted"], weight=600, family=MONO, spacing=1.2)
                 + text(rx + 16, y + 30, val, 20, fill=t["ink"], weight=800)
                 + text(rx + 16, y + 48, sub, 11, fill=t["faint"], weight=500) + "</g>")
    b.append(close)
    return svg(W, H, "".join(b), style=css, defs=defs,
               font_specs=(("Sora", 800), ("Sora", 500), ("JetBrains Mono", 600)), aria=f"Current streak {s['current']} days")


def languages(t: dict, D: dict) -> str:
    W, H = 460, 300
    f700 = font("Sora", 700)
    agg: dict[str, tuple[int, str]] = {}
    for r in D["user"]["repositories"]["nodes"]:
        for e in r["languages"]["edges"]:
            n, c = e["node"]["name"], e["node"]["color"] or t["muted"]
            agg[n] = (agg.get(n, (0, c))[0] + e["size"], c)
    total = sum(v[0] for v in agg.values()) or 1
    top = sorted(agg.items(), key=lambda kv: -kv[1][0])[:6]
    defs, css, open_, close = card_frame(t, W, H, "lg", seed=44)
    css += ("@keyframes growx{0%{transform:scaleX(0)}100%{transform:scaleX(1)}}"
            "@keyframes up{0%{opacity:0;transform:translateY(8px)}100%{opacity:1;transform:translateY(0)}}")
    b = [open_]
    b.append(text(36, 48, "LANGUAGES · BY BYTES", 11.5, fill=t["muted"], weight=600, family=MONO, spacing=1.4))
    # stacked bar
    x, y, bw = 36, 66, W - 72
    defs += f'<clipPath id="lgbar"><rect x="{x}" y="{y}" width="{bw}" height="12" rx="6"/></clipPath>'
    b.append(f'<rect x="{x}" y="{y}" width="{bw}" height="12" rx="6" fill="{t["line"]}"/>')
    acc = 0.0
    b.append('<g clip-path="url(#lgbar)">')
    for i, (n, (sz, c)) in enumerate(top):
        w = bw * sz / total
        b.append(f'<rect x="{x+acc:.1f}" y="{y}" width="{w:.1f}" height="12" fill="{c}" style="transform-origin:{x+acc:.1f}px 0;animation:growx 1s {0.1+i*0.12:.2f}s {EASE} both"/>')
        acc += w
    b.append("</g>")
    # rows
    cols = 2
    for i, (n, (sz, c)) in enumerate(top):
        pct = sz / total * 100
        cxp = 36 + (i % cols) * 200; cyp = 112 + (i // cols) * 58
        b.append(f'<g style="animation:up .8s {0.3+i*0.1:.2f}s {EASE} both">'
                 + f'<circle cx="{cxp+6}" cy="{cyp}" r="6" fill="{c}"/>'
                 + text(cxp + 20, cyp + 5, n, 15, fill=t["ink"], weight=700)
                 + text(cxp + 180, cyp + 5, f"{pct:.1f}%", 12.5, fill=t["muted"], weight=600, family=MONO, anchor="end")
                 + f'<rect x="{cxp}" y="{cyp+16}" width="180" height="5" rx="2.5" fill="{t["line"]}"/>'
                 + f'<rect x="{cxp}" y="{cyp+16}" width="{180*pct/100:.1f}" height="5" rx="2.5" fill="{c}" style="transform-origin:{cxp}px 0;animation:growx 1.2s {0.4+i*0.1:.2f}s {EASE} both"/>'
                 + "</g>")
    b.append(close)
    return svg(W, H, "".join(b), style=css, defs=defs,
               font_specs=(("Sora", 700), ("Sora", 500), ("JetBrains Mono", 600)), aria="Top languages")


def rhythm(t: dict, D: dict) -> str:
    W, H = 720, 300
    today = D["today"].date()
    start = today - dt.timedelta(days=365)
    wd = [0] * 7; months = {}
    best = (0, None)
    for ds, c in D["days"].items():
        d = dt.date.fromisoformat(ds)
        if d < start: continue
        wd[d.weekday()] += c
        months[(d.year, d.month)] = months.get((d.year, d.month), 0) + c
        if c > best[0]: best = (c, d)
    defs, css, open_, close = card_frame(t, W, H, "rh", seed=55)
    css += ("@keyframes growy{0%{transform:scaleY(0)}100%{transform:scaleY(1)}}"
            "@keyframes up{0%{opacity:0;transform:translateY(8px)}100%{opacity:1;transform:translateY(0)}}")
    defs += f'<linearGradient id="rhgrad" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="{t["cyan"]}"/><stop offset="1" stop-color="{t["violet"]}"/></linearGradient>'
    b = [open_]
    b.append(text(36, 48, "RHYTHM · LAST 12 MONTHS", 11.5, fill=t["muted"], weight=600, family=MONO, spacing=1.4))
    # weekday bars
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    mx = max(wd) or 1
    bx, by, bw, bh = 36, 90, 34, 130
    for i, v in enumerate(wd):
        h = max(4, bh * v / mx)
        x = bx + i * (bw + 12)
        fill = t["magenta"] if v == mx else "url(#rhgrad)"
        b.append(f'<rect x="{x}" y="{by+bh-h:.1f}" width="{bw}" height="{h:.1f}" rx="8" fill="{fill}" opacity=".9" '
                 f'style="transform-origin:0 {by+bh}px;animation:growy 1.1s {0.1+i*0.08:.2f}s {EASE} both"/>')
        b.append(text(x + bw / 2, by + bh + 20, names[i], 11, fill=t["muted"], weight=600, family=MONO, anchor="middle"))
        b.append(text(x + bw / 2, by + bh - h - 8, human(v), 10.5, fill=t["faint"], weight=600, family=MONO, anchor="middle"))
    # monthly mini bars
    mkeys = sorted(months)[-12:]
    mmx = max((months[k] for k in mkeys), default=1) or 1
    mx0, my0, mw, mh = 400, 90, 18, 90
    for i, k in enumerate(mkeys):
        v = months[k]; h = max(3, mh * v / mmx); x = mx0 + i * (mw + 6)
        b.append(f'<rect x="{x}" y="{my0+mh-h:.1f}" width="{mw}" height="{h:.1f}" rx="5" fill="{t["violet"]}" opacity=".75" '
                 f'style="transform-origin:0 {my0+mh}px;animation:growy 1.1s {0.5+i*0.05:.2f}s {EASE} both"/>')
        b.append(text(x + mw / 2, my0 + mh + 16, dt.date(k[0], k[1], 1).strftime("%b")[0], 10, fill=t["faint"], weight=600, family=MONO, anchor="middle"))
    busiest = names[wd.index(mx)] if mx else "—"
    weekly = sum(wd) / 52
    facts = [("Busiest day", {"Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday", "Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday", "Sun": "Sunday"}[busiest]),
             ("Weekly average", f"{weekly:.0f} contributions"),
             ("Best day", f"{best[0]} on {date_short(best[1])}" if best[1] else "—")]
    for i, (lab, val) in enumerate(facts):
        x = 400 if i == 0 else (400 if i == 2 else 560)
        yy = 230 if i < 2 else 268
        b.append(f'<g style="animation:up .8s {0.9+i*0.1:.2f}s {EASE} both">'
                 + text(x, yy, lab.upper(), 10, fill=t["muted"], weight=600, family=MONO, spacing=1.2)
                 + text(x, yy + 18, val, 14, fill=t["ink"], weight=700) + "</g>")
    b.append(close)
    return svg(W, H, "".join(b), style=css, defs=defs,
               font_specs=(("Sora", 700), ("Sora", 500), ("JetBrains Mono", 600)), aria="Contribution rhythm")


def repos(t: dict, D: dict) -> str:
    n = max(len(D["repos"]), 1)
    W, H = 1200, 232
    f700, f500 = font("Sora", 700), font("Sora", 500)
    defs = [beam_gradient(t, "rpb"), glow_filter("rpg", 6)]
    css = ("@keyframes up{0%{opacity:0;transform:translateY(12px)}100%{opacity:1;transform:translateY(0)}}"
           "@keyframes twinkle{0%,100%{transform:scale(1) rotate(0deg);opacity:1}50%{transform:scale(1.25) rotate(18deg);opacity:.8}}")
    gap = 20
    cw = (W - gap * (n - 1)) / n
    b = []
    for i, r in enumerate(D["repos"]):
        x = i * (cw + gap)
        cid = f"rp{i}"
        defs.append(f'<clipPath id="{cid}"><rect x="{x:.1f}" y="0" width="{cw:.1f}" height="{H}" rx="22"/></clipPath>')
        lang = r.get("primaryLanguage") or {}
        owner = r["nameWithOwner"].split("/")[0]
        b.append(f'<g style="animation:up .9s {0.1+i*0.12:.2f}s {EASE} both">')
        b.append(f'<g clip-path="url(#{cid})">' + glass(x, 0, cw, H, 22, t, fill=t["glass"] if t["name"] == "dark" else "#fff", stroke="none")
                 + f'<circle cx="{x+cw-20}" cy="-10" r="90" fill="{lang.get("color") or t["violet"]}" opacity="{0.18 if t["name"]=="dark" else 0.1}"/></g>')
        b.append(f'<rect x="{x+0.5}" y="0.5" width="{cw-1:.1f}" height="{H-1}" rx="21.5" fill="none" stroke="{t["line"]}"/>')
        b.append(border_beam(x + 0.5, 0.5, cw - 1, H - 1, 21.5, gid="rpb", seg=100, dur=6, delay=-i * 1.5, width=1.3))
        b.append(icon("github", x + 36, 42, 20, t["icon"]))
        b.append(text(x + 54, 39, owner + " /", 12.5, fill=t["muted"], weight=600, family=MONO))
        name = r["name"]
        size = 22
        while f700.width(name, size) > cw - 48 and size > 14: size -= 1
        b.append(text(x + 24, 78, name, size, fill=t["ink"], weight=700))
        for j, ln in enumerate(wrap(r.get("description") or "No description yet.", f500, 13.5, cw - 48, 3)):
            b.append(text(x + 24, 106 + j * 20, ln, 13.5, fill=t["muted"], weight=500))
        yb = H - 30
        if lang:
            b.append(f'<circle cx="{x+30}" cy="{yb-4}" r="5.5" fill="{lang.get("color") or t["muted"]}"/>')
            b.append(text(x + 42, yb, lang["name"], 12.5, fill=t["ink"], weight=600, family=MONO))
        sx = x + cw - 24
        b.append(text(sx, yb, str(r["forkCount"]), 12.5, fill=t["ink"], weight=600, family=MONO, anchor="end"))
        fw = font("JetBrains Mono", 600).width(str(r["forkCount"]), 12.5)
        b.append(f'<path transform="translate({sx-fw-20:.1f} {yb-11}) scale(0.6)" fill="{t["muted"]}" d="M5 3.25a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Zm0 2.122a2.25 2.25 0 1 0-1.5 0v.878A2.25 2.25 0 0 0 5.75 8.5h1.5v2.128a2.251 2.251 0 1 0 1.5 0V8.5h1.5a2.25 2.25 0 0 0 2.25-2.25v-.878a2.25 2.25 0 1 0-1.5 0v.878a.75.75 0 0 1-.75.75h-4.5A.75.75 0 0 1 5 6.25v-.878Zm3.75 7.378a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Zm3-8.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Z" style="transform:translate({sx-fw-20:.1f}px,{yb-11}px) scale(0.6)"/>')
        stx = sx - fw - 36
        b.append(text(stx, yb, str(r["stargazerCount"]), 12.5, fill=t["ink"], weight=600, family=MONO, anchor="end"))
        sw = font("JetBrains Mono", 600).width(str(r["stargazerCount"]), 12.5)
        star = f'M{stx-sw-12:.1f} {yb-11} l2.2 4.6 5 .7-3.6 3.5.9 5-4.5-2.4-4.5 2.4.9-5-3.6-3.5 5-.7z'
        b.append(f'<g style="transform-origin:{stx-sw-12:.1f}px {yb-4}px;animation:twinkle 2.6s {i*0.4:.1f}s ease-in-out infinite">'
                 f'<path d="{star}" fill="{t["amber"]}" filter="url(#rpg)" opacity=".7"/><path d="{star}" fill="{t["amber"]}"/></g>')
        b.append("</g>")
    return svg(W, H, "".join(b), style=css, defs="".join(defs),
               font_specs=(("Sora", 700), ("Sora", 500), ("JetBrains Mono", 600)), aria="Featured repositories")


def calendar3d(t: dict, D: dict) -> str:
    W, H = 1200, 470
    weeks = D["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    s, ca, sa = 15.0, 0.94, 0.34        # cell size, cos/sin of the iso angle
    ox, oy = 36 + 6 * ca * s + 10, 96
    mx = max((d["contributionCount"] for w in weeks for d in w["contributionDays"]), default=1) or 1
    dark = t["name"] == "dark"
    levels = {"NONE": None, "FIRST_QUARTILE": 0.25, "SECOND_QUARTILE": 0.5, "THIRD_QUARTILE": 0.75, "FOURTH_QUARTILE": 1.0}

    def lerp(a, b, u): return tuple(a[i] + (b[i] - a[i]) * u for i in range(3))
    def hexc(c): return "#%02x%02x%02x" % tuple(int(max(0, min(255, v))) for v in c)
    def rgb(h): h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    stops = [rgb(t["cyan"]), rgb(t["violet"]), rgb(t["magenta"])]
    def ramp(u):
        if u <= 0.5: return lerp(stops[0], stops[1], u / 0.5)
        return lerp(stops[1], stops[2], (u - 0.5) / 0.5)
    def shade(c, k): return tuple(v * k for v in c)

    defs, css, open_, close = card_frame(t, W, H, "cal", seed=66, aurora_op=0.35)
    css += "@keyframes rise{0%{opacity:0;transform:translateY(70px)}100%{opacity:1;transform:translateY(0)}}"
    b = [open_]
    b.append(text(36, 48, "CONTRIBUTIONS · LAST 12 MONTHS · ISOMETRIC", 11.5, fill=t["muted"], weight=600, family=MONO, spacing=1.4))
    cubes = []
    month_labels = []
    seen_months = set()
    flat = rgb(t["bg2"]) if dark else (226, 232, 240)
    for c, w in enumerate(weeks):
        for d in w["contributionDays"]:
            r = d["weekday"]
            cnt = d["contributionCount"]
            date = dt.date.fromisoformat(d["date"])
            if r == 0 or (c == 0):
                key = (date.year, date.month)
                if key not in seen_months and date.day <= 7:
                    seen_months.add(key); month_labels.append((c, date.strftime("%b")))
            x = ox + (c - r) * ca * s
            y = oy + (c + r) * sa * s
            u = levels[d["contributionLevel"]]
            h = 2 if u is None else 6 + 44 * math.sqrt(cnt / mx)
            base = flat if u is None else ramp(u)
            top, left, right = hexc(shade(base, 1.0 if u else 1.0)), hexc(shade(base, 0.72)), hexc(shade(base, 0.52))
            if u is None and not dark: left, right = hexc(shade(base, 0.9)), hexc(shade(base, 0.85))
            op = 0.55 if u is None and dark else 1
            tp = f"{x:.1f},{y-h:.1f} {x+ca*s:.1f},{y-h+sa*s:.1f} {x:.1f},{y-h+2*sa*s:.1f} {x-ca*s:.1f},{y-h+sa*s:.1f}"
            lf = f"{x-ca*s:.1f},{y-h+sa*s:.1f} {x:.1f},{y-h+2*sa*s:.1f} {x:.1f},{y+2*sa*s:.1f} {x-ca*s:.1f},{y+sa*s:.1f}"
            rt = f"{x:.1f},{y-h+2*sa*s:.1f} {x+ca*s:.1f},{y-h+sa*s:.1f} {x+ca*s:.1f},{y+sa*s:.1f} {x:.1f},{y+2*sa*s:.1f}"
            delay = c * 0.022 + r * 0.012
            title = f"{cnt} on {date.strftime('%b %-d, %Y')}"
            cubes.append((c + r, f'<g opacity="{op}" style="animation:rise .9s {delay:.2f}s {EASE} both"><title>{esc(title)}</title>'
                                 f'<polygon points="{lf}" fill="{left}"/><polygon points="{rt}" fill="{right}"/><polygon points="{tp}" fill="{top}"/></g>'))
    cubes.sort(key=lambda z: z[0])
    b.extend(cb for _, cb in cubes)
    for c, lab in month_labels:
        x = ox + c * ca * s + ca * s; y = oy + c * sa * s - 6
        b.append(text(x, y, lab, 10.5, fill=t["faint"], weight=600, family=MONO))
    # right panel
    px = 905
    total = D["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    best = max(((d["contributionCount"], d["date"]) for w in weeks for d in w["contributionDays"]), default=(0, None))
    active = sum(1 for w in weeks for d in w["contributionDays"] if d["contributionCount"] > 0)
    b.append(f'<rect x="{px-24}" y="86" width="1" height="300" fill="{t["line"]}"/>')
    b.append(text(px, 112, "TOTAL", 10.5, fill=t["muted"], weight=600, family=MONO, spacing=1.4))
    b.append(text(px, 152, f"{total:,}", 40, fill=t["ink"], weight=800))
    facts = [("Best day", f"{best[0]} contributions", date_short(dt.date.fromisoformat(best[1])) if best[1] else "—"),
             ("Active days", f"{active} of {sum(len(w['contributionDays']) for w in weeks)}", f"{active/max(1,sum(len(w['contributionDays']) for w in weeks))*100:.0f}% of the year"),
             ("Daily average", f"{total/365:.1f}", "contributions per day")]
    for i, (lab, val, sub) in enumerate(facts):
        y = 196 + i * 58
        b.append(text(px, y, lab.upper(), 10.5, fill=t["muted"], weight=600, family=MONO, spacing=1.2))
        b.append(text(px, y + 21, val, 17, fill=t["ink"], weight=700))
        b.append(text(px, y + 38, sub, 11, fill=t["faint"], weight=500))
    # legend
    ly = 400
    b.append(text(px, ly + 11, "less", 10.5, fill=t["faint"], weight=600, family=MONO))
    for i, u in enumerate((None, 0.25, 0.5, 0.75, 1.0)):
        c = hexc(flat if u is None else ramp(u))
        b.append(f'<rect x="{px+38+i*18}" y="{ly}" width="14" height="14" rx="4" fill="{c}" opacity="{0.55 if u is None and dark else 1}"/>')
    b.append(text(px + 38 + 5 * 18 + 6, ly + 11, "more", 10.5, fill=t["faint"], weight=600, family=MONO))
    b.append(close)
    return svg(W, H, "".join(b), style=css, defs=defs,
               font_specs=(("Sora", 800), ("Sora", 700), ("Sora", 500), ("JetBrains Mono", 600)), aria=f"{total:,} contributions in the last year")


CARDS = {"overview": overview, "streak": streak, "languages": languages, "rhythm": rhythm, "repos": repos, "calendar-3d": calendar3d}


def main(out_dir: str = "dist"):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    D = fetch()
    for name, fn in CARDS.items():
        for t in THEMES.values():
            suffix = "" if t["name"] == "dark" else "-light"
            p = out / f"{name}{suffix}.svg"
            p.write_text(fn(t, D), encoding="utf-8")
            print(f"  wrote {p} ({p.stat().st_size//1024} KB)")
    (out / "manifest.json").write_text(json.dumps({"generated_at": D["today"].isoformat(), "login": LOGIN,
                                                   "total_contributions": sum(D["yearly"].values())}, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dist")
