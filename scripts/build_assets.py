"""Builds the hand-crafted (static) SVG art in assets/ for dark + light themes.

Run:  python scripts/build_assets.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgkit import (MONO, SANS, ROOT, THEMES, aurora_blobs, aurora_defs, beam_gradient,  # noqa: E402
                    border_beam, dot_grid, esc, fmt, font, glass, glow_filter, gradient_text_defs,
                    grain_filter, icon, particles, shimmer, svg, text, write)

OUT = ROOT / "assets"

NAME_LINES = ("Shahzad", "Umar Baig")
ROLES = (
    "Senior Flutter Engineer",
    "Supabase · NestJS · Next.js behind it",
    "AI-native mobile products",
    "Shipping to App Store & Play Store",
)
STATS = (("6+", "yrs Flutter"), ("30+", "apps built"), ("100+", "devs trained"))


# --------------------------------------------------------------------------- #
# Typing timeline (pure SMIL, per-character accurate widths)
# --------------------------------------------------------------------------- #
def typing_timeline(lines, f, size, type_t=1.25, hold=2.1, erase_t=0.42, gap=0.33):
    per = type_t + hold + erase_t + gap
    total = per * len(lines)
    per_line, caret_kt, caret_v = [], [0.0], [0.0]
    for i, line in enumerate(lines):
        n = len(line)
        widths = [f.width(line[:k], size) for k in range(n + 1)]
        t0 = i * per
        kt, vals = [], []
        for k in range(n + 1):
            kt.append((t0 + k * type_t / n) / total); vals.append(widths[k])
        te = t0 + type_t + hold
        for k in range(n, -1, -1):
            kt.append((te + (n - k) * erase_t / n) / total); vals.append(widths[k])
        per_line.append((kt, vals))
        for a, b in zip(kt, vals):
            if a > caret_kt[-1]:
                caret_kt.append(a); caret_v.append(b)
    caret_kt.append(1.0); caret_v.append(0.0)
    return total, per_line, caret_kt, caret_v


def smil_discrete(attr, kt, vals, dur, offset=0.0):
    kts = [0.0] + [round(k, 5) for k in kt if k > 0] + [1.0]
    vs = [vals[0] + offset] + [v + offset for k, v in zip(kt, vals) if k > 0] + [vals[-1] + offset]
    return (f'<animate attributeName="{attr}" calcMode="discrete" dur="{dur:.3f}s" repeatCount="indefinite" '
            f'keyTimes="{";".join(fmt(k) for k in kts)}" values="{";".join(fmt(v) for v in vs)}"/>')


# --------------------------------------------------------------------------- #
# Phone mockup
# --------------------------------------------------------------------------- #
def phone(t: dict, ox: float, oy: float) -> tuple[str, str, str]:
    """Returns (css, defs, body). Phone is 220 x 380, screen 200 x 360."""
    dark = t["name"] == "dark"
    bezel = "#0B0F1F" if dark else "#111827"
    scr_bg = t["bg"] if dark else "#FFFFFF"
    card = t["glass2"]
    line = t["line"]
    ink, muted = t["ink"], t["muted"]
    css = (
        "@keyframes pages{0%,24%{transform:translateX(0)}33%,57%{transform:translateX(-200px)}"
        "66%,90%{transform:translateX(-400px)}100%{transform:translateX(-600px)}}"
        "@keyframes navdot{0%,24%{transform:translateX(0)}33%,57%{transform:translateX(50px)}"
        "66%,90%{transform:translateX(100px)}100%{transform:translateX(0)}}"
        "@keyframes bar{0%{transform:scaleY(.35)}100%{transform:scaleY(1)}}"
        "@keyframes fabring{0%{r:17;opacity:.7}100%{r:30;opacity:0}}"
        "@keyframes spark{0%{stroke-dashoffset:260}60%,100%{stroke-dashoffset:0}}"
        "@keyframes blob{0%{transform:translate(0,0)}100%{transform:translate(8px,-6px)}}"
    )
    defs = (
        f'<clipPath id="scr"><rect x="{ox+10}" y="{oy+10}" width="200" height="360" rx="24"/></clipPath>'
        f'<clipPath id="pages"><rect x="{ox+10}" y="{oy+84}" width="200" height="236"/></clipPath>'
        f'<linearGradient id="pcard" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["cyan"]}"/>'
        f'<stop offset="0.55" stop-color="{t["violet"]}"/><stop offset="1" stop-color="{t["magenta"]}"/></linearGradient>'
        f'<linearGradient id="pfab" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["magenta"]}"/>'
        f'<stop offset="1" stop-color="{t["violet"]}"/></linearGradient>'
        f'<linearGradient id="pbezel" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["cyan"]}" stop-opacity=".9"/>'
        f'<stop offset="0.5" stop-color="{t["violet"]}" stop-opacity=".9"/><stop offset="1" stop-color="{t["magenta"]}" stop-opacity=".9"/></linearGradient>'
        + glow_filter("pglow", 14)
    )
    b = []
    X, Y = ox, oy
    # glow + body
    b.append(f'<rect x="{X-2}" y="{Y-2}" width="224" height="384" rx="34" fill="none" stroke="url(#pbezel)" stroke-width="6" filter="url(#pglow)" opacity="{0.55 if dark else 0.35}"/>')
    b.append(f'<rect x="{X}" y="{Y}" width="220" height="380" rx="32" fill="{bezel}" stroke="url(#pbezel)" stroke-width="1.5"/>')
    b.append(f'<rect x="{X+10}" y="{Y+10}" width="200" height="360" rx="24" fill="{scr_bg}"/>')
    b.append('<g clip-path="url(#scr)">')
    # status bar + island
    b.append(text(X + 26, Y + 34, "9:41", 11, fill=ink, weight=600, family=MONO))
    b.append(f'<rect x="{X+80}" y="{Y+16}" width="60" height="16" rx="8" fill="{bezel}"/>')
    b.append(f'<rect x="{X+170}" y="{Y+25}" width="18" height="9" rx="2.5" fill="none" stroke="{muted}" stroke-width="1.2"/>'
             f'<rect x="{X+172}" y="{Y+27}" width="11" height="5" rx="1" fill="{t["green"]}"/>'
             f'<rect x="{X+189}" y="{Y+28}" width="2" height="3" rx="1" fill="{muted}"/>')
    for i in range(4):
        b.append(f'<rect x="{X+148+i*4}" y="{Y+33-i*2}" width="2.6" height="{3+i*2}" rx="1" fill="{muted if i<3 else line}"/>')
    # app bar
    b.append(f'<circle cx="{X+30}" cy="{Y+62}" r="12" fill="url(#pcard)"/>')
    b.append(f'<rect x="{X+50}" y="{Y+53}" width="78" height="8" rx="4" fill="{ink}" opacity=".85"/>')
    b.append(f'<rect x="{X+50}" y="{Y+66}" width="48" height="5" rx="2.5" fill="{muted}" opacity=".7"/>')
    b.append(f'<circle cx="{X+184}" cy="{Y+62}" r="13" fill="{card}" stroke="{line}"/>'
             f'<circle cx="{X+184}" cy="{Y+62}" r="3" fill="{t["magenta"]}"/>'
             f'<circle cx="{X+188}" cy="{Y+56}" r="2.2" fill="{t["green"]}"/>')
    # pages (slide)
    b.append(f'<g clip-path="url(#pages)"><g style="animation:pages 13s cubic-bezier(.7,0,.16,1) infinite">')

    def page_home(px):
        s = []
        s.append(f'<rect x="{px+12}" y="{Y+96}" width="176" height="92" rx="16" fill="url(#pcard)"/>')
        s.append(f'<circle cx="{px+160}" cy="{Y+120}" r="34" fill="#fff" opacity=".12" style="animation:blob 5s ease-in-out infinite alternate"/>')
        s.append(f'<rect x="{px+26}" y="{Y+112}" width="52" height="6" rx="3" fill="#fff" opacity=".8"/>')
        s.append(text(px + 26, Y + 146, "$12,480", 17, fill="#fff", weight=800))
        s.append(f'<polyline points="{px+26},{Y+176} {px+46},{Y+168} {px+66},{Y+172} {px+86},{Y+158} {px+106},{Y+164} {px+126},{Y+150} {px+146},{Y+156} {px+172},{Y+140}" '
                 f'fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="260" '
                 f'style="animation:spark 4s ease-out infinite"/>')
        for i, c in enumerate((t["cyan"], t["violet"], t["magenta"])):
            yy = Y + 200 + i * 40
            s.append(f'<rect x="{px+12}" y="{yy}" width="176" height="32" rx="11" fill="{card}" stroke="{line}"/>')
            s.append(f'<rect x="{px+22}" y="{yy+8}" width="16" height="16" rx="5" fill="{c}" opacity=".9"/>')
            s.append(f'<rect x="{px+46}" y="{yy+9}" width="{70-i*12}" height="6" rx="3" fill="{ink}" opacity=".8"/>')
            s.append(f'<rect x="{px+46}" y="{yy+19}" width="{44+i*8}" height="4" rx="2" fill="{muted}" opacity=".6"/>')
            s.append(f'<rect x="{px+156}" y="{yy+11}" width="22" height="10" rx="5" fill="{c}" opacity=".25"/>')
        return "".join(s)

    def page_chart(px):
        s = []
        s.append(f'<rect x="{px+12}" y="{Y+96}" width="100" height="8" rx="4" fill="{ink}" opacity=".85"/>')
        s.append(f'<rect x="{px+12}" y="{Y+110}" width="60" height="5" rx="2.5" fill="{muted}" opacity=".7"/>')
        s.append(f'<rect x="{px+12}" y="{Y+126}" width="176" height="118" rx="16" fill="{card}" stroke="{line}"/>')
        heights = (40, 62, 50, 84, 66, 92, 74)
        for i, h in enumerate(heights):
            bx = px + 26 + i * 23
            c = (t["cyan"], t["violet"], t["magenta"])[i % 3]
            s.append(f'<rect x="{bx}" y="{Y+230-h}" width="13" height="{h}" rx="4" fill="{c}" opacity=".85" '
                     f'style="transform-origin:{bx+6}px {Y+230}px;animation:bar {1.6+i*0.17:.2f}s {-(i*0.3):.2f}s ease-in-out infinite alternate"/>')
        for i in range(2):
            s.append(f'<rect x="{px+12+i*92}" y="{Y+254}" width="84" height="54" rx="12" fill="{card}" stroke="{line}"/>')
            s.append(text(px + 24 + i * 92, Y + 286, ("4.9★", "+38%")[i], 15, fill=(t["amber"], t["green"])[i], weight=800))
            s.append(f'<rect x="{px+24+i*92}" y="{Y+292}" width="40" height="4" rx="2" fill="{muted}" opacity=".6"/>')
        return "".join(s)

    def page_chat(px):
        s = []
        for i in range(5):
            mine = i % 2 == 1
            w = (120, 90, 136, 70, 110)[i]
            yy = Y + 98 + i * 44
            x = px + 188 - w if mine else px + 12
            fill = "url(#pcard)" if mine else card
            s.append(f'<rect x="{x}" y="{yy}" width="{w}" height="32" rx="12" fill="{fill}" stroke="{line if not mine else "none"}"/>')
            s.append(f'<rect x="{x+12}" y="{yy+9}" width="{w-32}" height="5" rx="2.5" fill="{"#fff" if mine else ink}" opacity=".8"/>')
            s.append(f'<rect x="{x+12}" y="{yy+19}" width="{w-52}" height="4" rx="2" fill="{"#fff" if mine else muted}" opacity=".55"/>')
        return "".join(s)

    b.append(page_home(X)); b.append(page_chart(X + 200)); b.append(page_chat(X + 400)); b.append(page_home(X + 600))
    b.append("</g></g>")
    # FAB
    b.append(f'<circle cx="{X+172}" cy="{Y+296}" r="17" fill="url(#pfab)" style="animation:fabring 2.4s ease-out infinite"/>')
    b.append(f'<circle cx="{X+172}" cy="{Y+296}" r="17" fill="url(#pfab)"/>')
    b.append(f'<path d="M{X+172} {Y+290}v12M{X+166} {Y+296}h12" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/>')
    # bottom nav
    b.append(f'<rect x="{X+10}" y="{Y+322}" width="200" height="48" fill="{scr_bg}"/>'
             f'<rect x="{X+10}" y="{Y+322}" width="200" height="1" fill="{line}"/>')
    b.append(f'<rect x="{X+22}" y="{Y+335}" width="36" height="22" rx="11" fill="{t["cyan"]}" opacity=".2" style="animation:navdot 13s cubic-bezier(.7,0,.16,1) infinite"/>')
    for i in range(4):
        cx = X + 40 + i * 50
        b.append(f'<rect x="{cx-6}" y="{Y+340}" width="12" height="12" rx="3.5" fill="none" stroke="{ink}" stroke-width="1.6" opacity=".75"/>')
    b.append(f'<rect x="{X+80}" y="{Y+362}" width="60" height="3" rx="1.5" fill="{ink}" opacity=".5"/>')
    b.append("</g>")
    return css, defs, "".join(b)


# --------------------------------------------------------------------------- #
# Orbits (icons travel behind and in front of the phone)
# --------------------------------------------------------------------------- #
def orbits(t: dict, cx, cy, W, H) -> tuple[str, str, str, str]:
    """Returns (defs, back_body, front_body)."""
    rings = [
        dict(rx=255, ry=216, dy=0, dur=38, sweep=1, icons=["flutter", "supabase", "typescript", "firebase", "nextdotjs", "swift"]),
        dict(rx=200, ry=58, dy=150, dur=24, sweep=0, icons=["dart", "nestjs", "postgresql", "openai"]),
    ]
    defs, back, front = [], [], []
    cy0 = cy
    for ri, r in enumerate(rings):
        rx, ry, sw = r["rx"], r["ry"], r["sweep"]
        cy = cy0 + r["dy"]
        defs.append(f'<clipPath id="orbBack{ri}"><rect x="0" y="0" width="{W}" height="{cy}"/></clipPath>'
                    f'<clipPath id="orbFront{ri}"><rect x="0" y="{cy}" width="{W}" height="{H-cy}"/></clipPath>')
        top = f"{cx} {cy-ry}"; bot = f"{cx} {cy+ry}"
        defs.append(f'<path id="orb{ri}" d="M{top} A{rx} {ry} 0 0 {sw} {bot} A{rx} {ry} 0 0 {sw} {top}"/>')
        # ring strokes: back (upper half) and front (lower half)
        back.append(f'<path d="M{cx-rx} {cy} A{rx} {ry} 0 0 1 {cx+rx} {cy}" fill="none" stroke="{t["line2"]}" stroke-dasharray="3 7" opacity=".7"/>')
        front.append(f'<path d="M{cx-rx} {cy} A{rx} {ry} 0 0 0 {cx+rx} {cy}" fill="none" stroke="{t["line2"]}" stroke-dasharray="3 7"/>')
        n = len(r["icons"])
        for i, name in enumerate(r["icons"]):
            gid = f"ico_{ri}_{i}"
            defs.append(f'<g id="{gid}"><circle r="21" fill="{t["bg2"] if t["name"]=="dark" else "#fff"}" stroke="{t["line2"]}" stroke-width="1.2"/>'
                        f'<circle r="21" fill="{t["glass2"]}"/>{icon(name, 0, 0, 20, t["icon"])}</g>')
            begin = -(i / n) * r["dur"]
            anim = (f'<animateMotion dur="{r["dur"]}s" begin="{begin:.2f}s" repeatCount="indefinite"><mpath href="#orb{ri}"/></animateMotion>'
                    f'<animateTransform attributeName="transform" type="scale" additive="sum" dur="{r["dur"]}s" begin="{begin:.2f}s" repeatCount="indefinite" '
                    f'values="0.72;1.08;0.72" keyTimes="0;0.5;1" calcMode="spline" keySplines="0.45 0 0.55 1;0.45 0 0.55 1"/>'
                    f'<animate attributeName="opacity" dur="{r["dur"]}s" begin="{begin:.2f}s" repeatCount="indefinite" values="0.45;1;0.45" keyTimes="0;0.5;1"/>')
            for layer, clip in ((back, f"orbBack{ri}"), (front, f"orbFront{ri}")):
                layer.append(f'<g clip-path="url(#{clip})"><g>{anim}<use href="#{gid}"/></g></g>')
    return "".join(defs), "".join(back), "".join(front), ""


# --------------------------------------------------------------------------- #
# Hero
# --------------------------------------------------------------------------- #
def hero(t: dict) -> str:
    W, H = 1200, 520
    f800, f500 = font("Sora", 800), font("Sora", 500)
    m600, m400 = font("JetBrains Mono", 600), font("JetBrains Mono", 400)
    defs, css, body = [], [], []
    dark = t["name"] == "dark"

    defs.append(f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["bg"]}"/><stop offset="1" stop-color="{t["bg2"]}"/></linearGradient>')
    defs.append(f'<clipPath id="clip"><rect width="{W}" height="{H}" rx="28"/></clipPath>')
    defs += [aurora_defs(t), grain_filter(), beam_gradient(t), gradient_text_defs(t, span=620), glow_filter("tglow", 16)]
    dd, db = dot_grid(t, W, H)
    defs.append(dd)
    ac, ab = aurora_blobs(t, W, H, seed=11)
    pc, pb = particles(t, W, H, n=26, seed=3)
    css += [ac, pc,
            "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}",
            "@keyframes pulse{0%{r:5;opacity:.9}100%{r:14;opacity:0}}",
            "@keyframes rise{0%{opacity:0;transform:translateY(14px)}100%{opacity:1;transform:translateY(0)}}"]

    body.append('<g clip-path="url(#clip)">')
    body.append(f'<rect width="{W}" height="{H}" fill="url(#bg)"/>')
    body.append(ab)
    body.append(db)
    body.append(f'<rect width="{W}" height="{H}" filter="url(#grain)" opacity="{t["grain"]}" style="mix-blend-mode:overlay"/>')
    body.append(pb)

    # ---- right: phone + orbits
    pcx, pcy = 915, 262
    odefs, oback, ofront, _ = orbits(t, pcx, pcy, W, H)
    pcss, pdefs, pbody = phone(t, pcx - 110, pcy - 190)
    defs += [odefs, pdefs]
    css.append(pcss)
    body.append(oback)
    body.append(pbody)
    body.append(ofront)

    # ---- left column
    L = 72
    ease = "cubic-bezier(.22,1,.36,1)"

    def rise(delay, inner):
        return f'<g style="animation:rise 1.1s {delay}s {ease} both">{inner}</g>'

    # availability pill
    label = "OPEN TO FREELANCE & CONTRACT WORK"
    tw = m600.width(label, 11.5, 1.5)
    pw = 16 + 8 + 10 + tw + 16
    pill = (f'<rect x="{L}" y="54" width="{pw:.0f}" height="32" rx="16" fill="{t["green"]}" fill-opacity="{0.12 if dark else 0.1}" stroke="{t["green"]}" stroke-opacity=".45"/>'
            f'<circle cx="{L+18}" cy="70" r="5" fill="{t["green"]}" style="animation:pulse 2s ease-out infinite"/>'
            f'<circle cx="{L+18}" cy="70" r="4.5" fill="{t["green"]}"/>'
            + text(L + 34, 74.5, label, 11.5, fill=t["green"], weight=600, family=MONO, spacing=1.5))
    body.append(rise(0.05, pill))

    # hello
    body.append(rise(0.15, f'<rect x="{L}" y="118" width="26" height="3" rx="1.5" fill="url(#beam)"/>'
                     + text(L + 36, 124, "Hello, I'm", 19, fill=t["muted"], weight=500)))

    # name (two lines, gradient + glow)
    size = min(76, 540 / f800.width(NAME_LINES[1], 1))
    y1 = 206; y2 = y1 + size * 0.98
    for i, (ln, yy) in enumerate(zip(NAME_LINES, (y1, y2))):
        glow = text(L, yy, ln, size, fill="url(#gtx)", weight=800, extra=f' filter="url(#tglow)" opacity="{0.55 if dark else 0.25}"')
        main = text(L, yy, ln, size, fill="url(#gtx)", weight=800)
        body.append(rise(0.25 + i * 0.1, glow + main))

    # typed roles
    ry = y2 + 52
    rsize = 25
    total, per_line, ckt, cv = typing_timeline(ROLES, f500, rsize)
    roles = []
    for i, (line, (kt, vals)) in enumerate(zip(ROLES, per_line)):
        defs.append(f'<clipPath id="tc{i}"><rect x="{L}" y="{ry-rsize}" height="{rsize*1.4:.0f}" width="0">{smil_discrete("width", kt, vals, total)}</rect></clipPath>')
        roles.append(text(L, ry, line, rsize, fill=t["ink"], weight=500, opacity=0.92, extra=f' clip-path="url(#tc{i})"'))
    roles.append(f'<rect x="{L}" y="{ry-rsize+2}" width="3" height="{rsize+4}" rx="1.5" fill="{t["cyan"]}" style="animation:blink 1s steps(1) infinite">'
                 + smil_discrete("x", ckt[1:-1], cv[1:-1], total, offset=L + 4) + '</rect>')
    body.append(rise(0.5, "".join(roles)))

    # stat tiles with border beam
    ty = ry + 38
    tw_, th, gap = 180, 64, 16
    tiles = []
    for i, (num, lab) in enumerate(STATS):
        x = L + i * (tw_ + gap)
        tiles.append(glass(x, ty, tw_, th, 14, t))
        tiles.append(border_beam(x, ty, tw_, th, 14, seg=70, dur=5.2, delay=-i * 1.7))
        tiles.append(text(x + 18, ty + 40, num, 27, fill=t["ink"], weight=800))
        nw = f800.width(num, 27)
        tiles.append(text(x + 18 + nw + 10, ty + 39, lab, 12, fill=t["muted"], weight=600, family=MONO, spacing=0.4))
    body.append(rise(0.65, "".join(tiles)))

    # location line
    ly = ty + th + 36
    pin = (f'<path transform="translate({L} {ly-12}) scale(0.55)" fill="{t["magenta"]}" '
           f'd="M12 0C7 0 3 4 3 9c0 6.5 9 15 9 15s9-8.5 9-15c0-5-4-9-9-9zm0 12.5a3.5 3.5 0 110-7 3.5 3.5 0 010 7z"/>')
    body.append(rise(0.8, pin + text(L + 20, ly, "Karachi, Pakistan  ·  UTC+5  ·  working with teams worldwide", 12.5, fill=t["muted"], weight=400, family=MONO)))

    body.append("</g>")
    body.append(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="27.5" fill="none" stroke="{t["line"]}"/>')

    return svg(W, H, "".join(body), style="".join(css), defs="".join(defs),
               font_specs=(("Sora", 800), ("Sora", 500), ("JetBrains Mono", 600), ("JetBrains Mono", 400)),
               aria="Shahzad Umar Baig - Senior Flutter Engineer, open to freelance and contract work")


BUILDERS = {"hero": hero}


# =========================================================================== #
# Section headers
# =========================================================================== #
SECTIONS = {
    "about": ("01", "About me", "who I am"),
    "stack": ("02", "Stack", "what I build with"),
    "shipped": ("03", "Shipped", "products in the wild"),
    "opensource": ("04", "Open source", "packages & contributions"),
    "stats": ("05", "GitHub in numbers", "live, regenerated every 6 hours"),
    "writing": ("06", "Writing", "on Medium"),
    "connect": ("07", "Let's build something", "work with me"),
}


def header(t: dict, idx: str, title: str, caption: str) -> str:
    W, H = 1200, 72
    f700, m600 = font("Sora", 700), font("JetBrains Mono", 600)
    defs = [beam_gradient(t, "hb"),
            f'<linearGradient id="hl" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{t["violet"]}" stop-opacity=".9"/>'
            f'<stop offset="1" stop-color="{t["magenta"]}" stop-opacity="0"/></linearGradient>',
            glow_filter("hg", 4)]
    css = ("@keyframes hin{0%{opacity:0;transform:translateX(-14px)}100%{opacity:1;transform:translateX(0)}}"
           "@keyframes hline{0%{transform:scaleX(0)}100%{transform:scaleX(1)}}")
    b = []
    b.append(f'<g style="animation:hin .9s cubic-bezier(.22,1,.36,1) both">')
    b.append(f'<rect x="0" y="20" width="32" height="32" rx="9" fill="url(#hb)"/>')
    b.append(text(16, 41.5, idx, 12.5, fill="#fff", weight=600, family=MONO, anchor="middle"))
    b.append(text(48, 46, title, 30, fill=t["ink"], weight=700))
    b.append("</g>")
    tw = f700.width(title, 30)
    x0 = 48 + tw + 24
    cw = m600.width(caption, 12, 0.6)
    x1 = W - cw - 24
    b.append(f'<rect x="{x0:.0f}" y="35.5" width="{max(x1-x0,0):.0f}" height="1.5" fill="url(#hl)" '
             f'style="transform-origin:{x0:.0f}px 0;animation:hline 1.4s .3s cubic-bezier(.22,1,.36,1) both"/>')
    b.append(f'<circle cy="36.25" r="3" fill="{t["cyan"]}" filter="url(#hg)">'
             f'<animate attributeName="cx" from="{x0:.0f}" to="{x1:.0f}" dur="4.5s" begin="1.2s" repeatCount="indefinite" '
             f'calcMode="spline" keySplines="0.4 0 0.2 1" keyTimes="0;1"/>'
             f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.1;0.85;1" dur="4.5s" begin="1.2s" repeatCount="indefinite"/></circle>')
    b.append(text(W - 2, 40.5, caption, 12, fill=t["muted"], weight=600, family=MONO, anchor="end", spacing=0.6))
    return svg(W, H, "".join(b), style=css, defs="".join(defs),
               font_specs=(("Sora", 700), ("JetBrains Mono", 600)), aria=f"{idx} {title}")


# =========================================================================== #
# Stack
# =========================================================================== #
STACK = [
    ("Mobile", [("flutter", "Flutter"), ("dart", "Dart"), ("swift", "Swift"), ("kotlin", "Kotlin"),
                ("android", "Android"), ("apple", "iOS"), (None, "FlutterFlow"), (None, "Riverpod"), (None, "BLoC")]),
    ("Backend & data", [("supabase", "Supabase"), ("postgresql", "PostgreSQL"), ("nestjs", "NestJS"), ("nodedotjs", "Node.js"),
                        ("firebase", "Firebase"), ("graphql", "GraphQL"), ("laravel", "Laravel"), ("socketdotio", "Socket.IO")]),
    ("Web", [("typescript", "TypeScript"), ("nextdotjs", "Next.js"), ("react", "React"), ("tailwindcss", "Tailwind"),
             ("vercel", "Vercel"), ("javascript", "JavaScript")]),
    ("AI & tooling", [("openai", "OpenAI"), ("anthropic", "Claude"), ("githubactions", "GitHub Actions"), ("docker", "Docker"),
                      ("figma", "Figma"), ("git", "Git"), ("jira", "Jira"), ("posthog", "PostHog"), ("stripe", "Stripe")]),
]


def stack(t: dict) -> str:
    W = 1200
    f500, f700 = font("Sora", 500), font("Sora", 700)
    dark = t["name"] == "dark"
    PAD, LABW, PH, ROW, GAP = 40, 196, 42, 54, 10
    accents = [t["cyan"], t["violet"], t["magenta"], t["teal"]]
    # layout first to know the height
    rows = []
    y = 44
    for ci, (cat, items) in enumerate(STACK):
        x = PAD + LABW
        line_y = y
        placed = []
        for ic, lab in items:
            w = 16 + (18 + 10 if ic else 0) + f500.width(lab, 15) + 18
            if x + w > W - PAD:
                x = PAD + LABW; line_y += ROW
            placed.append((x, line_y, w, ic, lab))
            x += w + GAP
        rows.append((cat, y, placed, accents[ci]))
        y = line_y + ROW + 14
    H = int(y + 8)

    defs = [f'<clipPath id="sc"><rect width="{W}" height="{H}" rx="26"/></clipPath>',
            f'<linearGradient id="sbg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["bg"]}"/><stop offset="1" stop-color="{t["bg2"]}"/></linearGradient>',
            aurora_defs(t, "sa"), grain_filter("sg")]
    css = ["@keyframes pop{0%{opacity:0;transform:translateY(12px) scale(.94)}100%{opacity:1;transform:translateY(0) scale(1)}}"]
    ac, ab = aurora_blobs(t, W, H, prefix="sa", seed=5)
    sc, sd, sb = shimmer(W, H, dur=11, opacity=0.07 if dark else 0.5)
    css += [ac, sc]; defs.append(sd)
    b = [f'<g clip-path="url(#sc)"><rect width="{W}" height="{H}" fill="url(#sbg)"/>',
         f'<g opacity="0.55">{ab}</g>',
         f'<rect width="{W}" height="{H}" filter="url(#sg)" opacity="{t["grain"]}" style="mix-blend-mode:overlay"/>']
    k = 0
    for cat, y, placed, accent in rows:
        b.append(f'<rect x="{PAD}" y="{y+12}" width="4" height="18" rx="2" fill="{accent}"/>')
        b.append(text(PAD + 16, y + 27, cat, 16, fill=t["ink"], weight=700))
        for (x, ly, w, ic, lab) in placed:
            d = 0.06 * k; k += 1
            inner = [glass(x, ly, w, PH, 13, t, fill=t["glass"] if dark else "rgba(255,255,255,0.8)")]
            tx = x + 16
            if ic:
                inner.append(icon(ic, tx + 9, ly + PH / 2, 18, t["icon"]))
                tx += 28
            inner.append(text(tx, ly + PH / 2 + 5.5, lab, 15, fill=t["ink"], weight=500))
            b.append(f'<g style="transform-origin:{x+w/2:.0f}px {ly+PH/2:.0f}px;animation:pop .8s {d:.2f}s cubic-bezier(.22,1,.36,1) both">{"".join(inner)}</g>')
    b.append(sb)
    b.append("</g>")
    b.append(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="25.5" fill="none" stroke="{t["line"]}"/>')
    return svg(W, H, "".join(b), style="".join(css), defs="".join(defs),
               font_specs=(("Sora", 500), ("Sora", 700)), aria="Tech stack: mobile, backend, web, AI and tooling")


# =========================================================================== #
# Terminal
# =========================================================================== #
TERMINAL = [
    ("shahzad --whoami", "Senior Flutter Engineer · 6+ years · Karachi, Pakistan"),
    ("shahzad --stack", "Flutter · Dart · Supabase · NestJS · Next.js · Firebase · Swift"),
    ("shahzad --now", "Shipping AI-native mobile products for clients worldwide"),
    ("shahzad --fun", "gardening · music · chai · mentoring the next generation of devs"),
]


def terminal(t: dict) -> str:
    W, H = 1200, 318
    m400, m600 = font("JetBrains Mono", 400), font("JetBrains Mono", 600)
    dark = t["name"] == "dark"
    size = 16.5
    cw = m400.width("M", size)  # monospace advance
    type_t, pause_out, hold_end = 1.1, 0.9, 5.0
    total = (type_t + pause_out) * len(TERMINAL) + hold_end
    defs = [f'<clipPath id="tw"><rect width="{W}" height="{H}" rx="22"/></clipPath>',
            beam_gradient(t, "tb")]
    css = ["@keyframes tblink{0%,49%{opacity:1}50%,100%{opacity:0}}"]
    b = [f'<g clip-path="url(#tw)"><rect width="{W}" height="{H}" fill="{t["bg"] if dark else "#0F172A"}"/>',
         f'<rect width="{W}" height="46" fill="{t["bg2"] if dark else "#111B33"}"/>',
         f'<rect y="46" width="{W}" height="1" fill="{t["line"] if dark else "rgba(255,255,255,0.08)"}"/>']
    for i, c in enumerate(("#FF5F57", "#FEBC2E", "#28C840")):
        b.append(f'<circle cx="{28+i*22}" cy="23" r="6.5" fill="{c}"/>')
    ink = t["ink"] if dark else "#E2E8F0"
    muted = t["muted"] if dark else "#94A3B8"
    b.append(text(W / 2, 28, "shahzad@karachi — zsh", 13, fill=muted, weight=400, family=MONO, anchor="middle"))
    X, y = 36, 86
    caret_kt, caret_v, caret_y_kt, caret_y_v = [], [], [], []
    for i, (cmd, out) in enumerate(TERMINAL):
        t0 = i * (type_t + pause_out)
        n = len(cmd)
        kt = [(t0 + k * type_t / n) / total for k in range(n + 1)]
        vals = [k * cw for k in range(n + 1)]
        px = X + m600.width("$ ", size)
        defs.append(f'<clipPath id="cl{i}"><rect x="{px:.1f}" y="{y-size}" height="{size*1.5:.0f}" width="0">'
                    + smil_discrete("width", kt, vals, total) + "</rect></clipPath>")
        t_start = t0 / total
        b.append(f'<g opacity="{1 if i == 0 else 0}">' + ("" if i == 0 else
                 f'<animate attributeName="opacity" calcMode="discrete" dur="{total:.3f}s" repeatCount="indefinite" keyTimes="0;{t_start:.5f};1" values="0;1;1"/>')
                 + text(X, y, "$", size, fill=t["violet"], weight=600, family=MONO) + "</g>")
        b.append(text(px, y, cmd, size, fill=t["cyan"], weight=600, family=MONO, extra=f' clip-path="url(#cl{i})"'))
        t_done = (t0 + type_t) / total
        b.append(f'<g opacity="0"><animate attributeName="opacity" calcMode="discrete" dur="{total:.3f}s" repeatCount="indefinite" '
                 f'keyTimes="0;{t_done:.5f};1" values="0;1;1"/>'
                 + text(X, y + 30, "→", size, fill=t["magenta"], weight=400, family=MONO)
                 + text(X + 26, y + 30, out, size, fill=ink, weight=400, family=MONO) + "</g>")
        for k_, v_ in zip(kt, vals):
            caret_kt.append(k_); caret_v.append(px + v_ + 2); caret_y_kt.append(k_); caret_y_v.append(y - size + 1)
        y += 58
    # final idle prompt + caret
    t_idle = ((type_t + pause_out) * len(TERMINAL)) / total
    b.append(f'<g opacity="0"><animate attributeName="opacity" calcMode="discrete" dur="{total:.3f}s" repeatCount="indefinite" keyTimes="0;{t_idle:.5f};1" values="0;1;1"/>'
             + text(X, y, "$", size, fill=t["violet"], weight=600, family=MONO) + "</g>")
    caret_kt.append(t_idle); caret_v.append(X + m600.width("$ ", size)); caret_y_kt.append(t_idle); caret_y_v.append(y - size + 1)
    b.append(f'<rect width="9" height="{size+3}" fill="{t["cyan"]}" opacity=".9" style="animation:tblink 1s steps(1) infinite">'
             + smil_discrete("x", caret_kt, caret_v, total) + smil_discrete("y", caret_y_kt, caret_y_v, total) + "</rect>")
    b.append("</g>")
    b.append(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="21.5" fill="none" stroke="{t["line2"] if dark else "rgba(15,23,42,0.25)"}"/>')
    return svg(W, H, "".join(b), style="".join(css), defs="".join(defs),
               font_specs=(("JetBrains Mono", 400), ("JetBrains Mono", 600)), aria="Terminal: whoami, stack, now, fun")


# =========================================================================== #
# Connect buttons
# =========================================================================== #
BUTTONS = {
    "linkedin": ("linkedin", "LinkedIn", "#0A66C2"),
    "email": ("gmail", "Email me", "#EA4335"),
    "medium": ("medium", "Medium", "#12100E"),
    "stackoverflow": ("stackoverflow", "Stack Overflow", "#F58025"),
    "pubdev": ("dart", "pub.dev", "#0175C2"),
}


def button(t: dict, ic: str, label: str, brand: str) -> str:
    f700 = font("Sora", 700)
    H = 56
    tw = f700.width(label, 17)
    W = int(20 + 22 + 12 + tw + 24)
    dark = t["name"] == "dark"
    defs = [beam_gradient(t, "bb"), f'<clipPath id="bc"><rect width="{W}" height="{H}" rx="16"/></clipPath>']
    sc, sd, sb = shimmer(W, H, dur=6, opacity=0.14 if dark else 0.6)
    defs.append(sd)
    b = [f'<g clip-path="url(#bc)">',
         glass(0, 0, W, H, 16, t, fill=t["glass2"] if dark else "#FFFFFF", stroke="none"),
         f'<circle cx="{W-10}" cy="{H+10}" r="42" fill="{brand}" opacity="{0.28 if dark else 0.14}"/>',
         icon(ic, 31, H / 2, 22, brand if (dark or ic != "medium") else "#000"),
         text(20 + 22 + 12, H / 2 + 6, label, 17, fill=t["ink"], weight=700), sb, "</g>",
         f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="15.5" fill="none" stroke="{t["line2"]}"/>',
         border_beam(0.5, 0.5, W - 1, H - 1, 15.5, gid="bb", seg=60, dur=4.5, width=1.5)]
    return svg(W, H, "".join(b), style=sc, defs="".join(defs), font_specs=(("Sora", 700),), aria=label)


# =========================================================================== #
# Footer
# =========================================================================== #
def footer(t: dict) -> str:
    W, H = 1200, 230
    dark = t["name"] == "dark"
    defs = [f'<clipPath id="fc"><rect width="{W}" height="{H}" rx="26"/></clipPath>',
            f'<linearGradient id="fbg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["bg"]}"/><stop offset="1" stop-color="{t["bg2"]}"/></linearGradient>',
            f'<linearGradient id="w1" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{t["cyan"]}"/><stop offset=".5" stop-color="{t["violet"]}"/><stop offset="1" stop-color="{t["magenta"]}"/></linearGradient>',
            f'<linearGradient id="w2" x1="1" y1="0" x2="0" y2="0"><stop offset="0" stop-color="{t["teal"]}"/><stop offset=".5" stop-color="{t["blue"]}"/><stop offset="1" stop-color="{t["violet"]}"/></linearGradient>',
            gradient_text_defs(t, "fgt", 500), beam_gradient(t, "fb")]
    css = ["@keyframes grow{0%{stroke-dashoffset:120}100%{stroke-dashoffset:0}}",
           "@keyframes leaf{0%{transform:scale(0)}100%{transform:scale(1)}}",
           "@keyframes sway{0%{transform:rotate(-3deg)}100%{transform:rotate(3deg)}}",
           "@keyframes note{0%{transform:translateY(0) rotate(-8deg);opacity:0}15%{opacity:1}100%{transform:translateY(-70px) rotate(10deg);opacity:0}}",
           "@keyframes fin{0%{opacity:0;transform:translateY(10px)}100%{opacity:1;transform:translateY(0)}}"]

    def wave(amp, base, phase):
        pts = []
        for ph in (phase, phase + 1.0, phase + 2.0):
            d = f"M0 {base}"
            for i in range(0, W + 1, 100):
                xx = i
                yy = base + amp * math.sin((xx / W) * 2 * math.pi * 1.4 + ph)
                d += f" L{xx} {yy:.1f}" if False else ""
            # smooth cubic waves
            d = f"M0 {base + amp*math.sin(ph):.1f}"
            step = 150
            for xx in range(0, W, step):
                x1, x2 = xx + step * 0.5, xx + step
                y0 = base + amp * math.sin((xx / W) * 2 * math.pi * 1.4 + ph)
                y2 = base + amp * math.sin((x2 / W) * 2 * math.pi * 1.4 + ph)
                d += f" C{x1:.0f} {y0:.1f} {x1:.0f} {y2:.1f} {x2:.0f} {y2:.1f}"
            d += f" L{W} {H} L0 {H} Z"
            pts.append(d)
        pts.append(pts[0])
        return pts

    b = [f'<g clip-path="url(#fc)"><rect width="{W}" height="{H}" fill="url(#fbg)"/>']
    for amp, base, ph, grad, op, dur in ((16, 168, 0.0, "w2", 0.35 if dark else 0.25, 9), (14, 182, 2.1, "w1", 0.8 if dark else 0.6, 7)):
        ws = wave(amp, base, ph)
        b.append(f'<path fill="url(#{grad})" opacity="{op}"><animate attributeName="d" dur="{dur}s" repeatCount="indefinite" '
                 f'values="{";".join(ws)}" calcMode="spline" keySplines="{";".join(["0.45 0 0.55 1"]*(len(ws)-1))}"/></path>')
    # sprout
    sx, sy = 92, 150
    b.append(f'<g style="transform-origin:{sx}px {sy}px;animation:sway 4s ease-in-out infinite alternate">')
    b.append(f'<path d="M{sx} {sy} C{sx+3} {sy-18} {sx-7} {sy-36} {sx} {sy-64}" fill="none" stroke="{t["green"]}" stroke-width="3.2" stroke-linecap="round" '
             f'stroke-dasharray="120" style="animation:grow 1.6s .2s cubic-bezier(.22,1,.36,1) both"/>')
    b.append(f'<path d="M{sx-1} {sy-36} c-20 -2 -30 -18 -28 -32 c16 1 27 14 28 32z" fill="{t["green"]}" opacity=".95" '
             f'style="transform-origin:{sx-1}px {sy-36}px;animation:leaf .9s 1.2s cubic-bezier(.34,1.56,.64,1) both"/>')
    b.append(f'<path d="M{sx+1} {sy-54} c20 -2 30 -18 28 -32 c-16 1 -27 14 -28 32z" fill="{t["teal"]}" opacity=".95" '
             f'style="transform-origin:{sx+1}px {sy-54}px;animation:leaf .9s 1.6s cubic-bezier(.34,1.56,.64,1) both"/>')
    b.append("</g>")
    b.append(f'<ellipse cx="{sx}" cy="{sy+4}" rx="26" ry="5" fill="{t["green"]}" opacity=".18"/>')
    # music notes
    for i, (nx, ny, d) in enumerate(((1060, 120, 0), (1100, 134, 1.4), (1136, 112, 2.6))):
        c = (t["magenta"], t["violet"], t["cyan"])[i]
        b.append(f'<g style="transform-origin:{nx}px {ny}px;animation:note 4.2s {d}s ease-out infinite">'
                 f'<circle cx="{nx}" cy="{ny}" r="5" fill="{c}"/><rect x="{nx+3.5}" y="{ny-22}" width="2.4" height="22" rx="1" fill="{c}"/>'
                 f'<path d="M{nx+5.9} {ny-22} c6 1 9 5 8 11 c-2 -4 -5 -5 -8 -5z" fill="{c}"/></g>')
    # text
    b.append(f'<g style="animation:fin 1s .2s cubic-bezier(.22,1,.36,1) both">')
    b.append(text(W / 2, 92, "Thanks for scrolling", 38, fill="url(#fgt)", weight=800, anchor="middle"))
    b.append(text(W / 2, 124, "Grown with care in Karachi  ·  Flutter, chai & good music", 14, fill=t["muted"], weight=600, family=MONO, anchor="middle", spacing=0.4))
    b.append("</g></g>")
    b.append(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="25.5" fill="none" stroke="{t["line"]}"/>')
    return svg(W, H, "".join(b), style="".join(css), defs="".join(defs),
               font_specs=(("Sora", 800), ("JetBrains Mono", 600)), aria="Thanks for scrolling")


def build_headers(t: dict):
    for key, (idx, title, cap) in SECTIONS.items():
        suffix = "" if t["name"] == "dark" else "-light"
        write(OUT / "headers" / f"{key}{suffix}.svg", header(t, idx, title, cap))


def build_buttons(t: dict):
    for key, (ic, label, brand) in BUTTONS.items():
        suffix = "" if t["name"] == "dark" else "-light"
        write(OUT / "buttons" / f"{key}{suffix}.svg", button(t, ic, label, brand))


BUILDERS.update({"stack": stack, "terminal": terminal, "footer": footer})
MULTI = {"headers": build_headers, "buttons": build_buttons}


def main(only: set[str] | None = None):
    for name, fn in BUILDERS.items():
        if only and name not in only:
            continue
        for theme in THEMES.values():
            suffix = "" if theme["name"] == "dark" else "-light"
            write(OUT / f"{name}{suffix}.svg", fn(theme))
    for name, fn in MULTI.items():
        if only and name not in only:
            continue
        for theme in THEMES.values():
            fn(theme)


if __name__ == "__main__":
    main(set(sys.argv[1:]) or None)
