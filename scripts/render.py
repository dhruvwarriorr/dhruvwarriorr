#!/usr/bin/env python3
"""Renders every animated SVG used by the profile README into assets/.

Scenes: the hero and three project cards. Numbers come from data.py and are live.
Standard library only, so the workflow needs no installs.
"""
import math
import os
import random
import textwrap
from html import escape

from data import load_data

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, 'assets')

MONO = "'JetBrains Mono','SF Mono',SFMono-Regular,ui-monospace,Menlo,Consolas,'Liberation Mono',monospace"
SANS = "'Segoe UI',-apple-system,BlinkMacSystemFont,'Inter','Helvetica Neue',Helvetica,Arial,sans-serif"

C = dict(bg='#070b12', card='#0b1018', panel='#0f1621', line='#1c2633', text='#e6edf3', muted='#7d8590',
         dim='#3d4754', g0='#161b22', g1='#0e4429', g2='#006d32', g3='#26a641', g4='#39d353', mint='#aff5b4',
         blue='#4f7bff', sky='#58a6ff', cyan='#22d3ee', gold='#f5c542', silver='#c9d1d9', orange='#ffa116',
         purple='#c084fc', red='#f85149', chef='#b07cd8')
LEVELS = [C['g0'], C['g1'], C['g2'], C['g3'], C['g4']]
R = 14  # corner radius for every card: soft, never pill-shaped

CF_BANDS = [(0, 'newbie', '#9ca3af'), (1200, 'pupil', '#22c55e'), (1400, 'specialist', '#22d3ee'),
            (1600, 'expert', '#4f7bff'), (1900, 'candidate master', '#c084fc'), (2100, 'master', '#ffa94d'),
            (2300, 'international master', '#ffa94d'), (2400, 'grandmaster', '#ff6b6b'),
            (2600, 'international grandmaster', '#ff6b6b'), (3000, 'legendary grandmaster', '#ff6b6b')]


# ───────────────────────────── svg toolkit ─────────────────────────────

BASE_CSS = ('.fb{transform-box:fill-box;transform-origin:center}'
            '.fl{transform-box:fill-box;transform-origin:0 50%}'
            '@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}.blink{animation:blink 1.05s linear infinite}'
            '@keyframes tw{0%,100%{opacity:0}50%{opacity:1}}'
            '@keyframes ping{0%{transform:scale(1);opacity:.8}100%{transform:scale(3.2);opacity:0}}'
            '.ping{animation:ping 2s cubic-bezier(.2,.6,.4,1) infinite}')


class Fx:
    """Collects keyframes. Every animation gets its own name, so timings can be absolute within a loop."""

    def __init__(self, T=None):
        self.T, self.css, self.n = T, [], 0

    def uid(self, p='u'):
        self.n += 1
        return f'{p}{self.n}'

    def anim(self, frames, dur, ease='linear', delay=0.0, count='infinite', fill='both'):
        k = self.uid('k')
        self.css.append(f'@keyframes {k}{{{frames}}}.{k}{{animation:{k} {dur:.3f}s {ease} {delay:.3f}s {count} {fill}}}')
        return k

    def tl(self, stops, ease='linear', T=None):
        T = T or self.T
        frames = ''.join(f'{min(max(t, 0), T) / T * 100:.3f}%{{{css}}}' for t, css in stops)
        return self.anim(frames, T, ease)

    def show(self, t, end=None, T=None, fade=.25):
        T = T or self.T
        end = T - .7 if end is None else end
        return self.tl([(0, 'opacity:0'), (t, 'opacity:0'), (t + fade, 'opacity:1'), (end, 'opacity:1'),
                        (end + .35, 'opacity:0'), (T, 'opacity:0')], T=T)

    def pop(self, t, end=None, T=None, s0=.2, over=1.25):
        T = T or self.T
        end = T - .7 if end is None else end
        a, b = f'opacity:0;transform:scale({s0})', 'opacity:1;transform:scale(1)'
        return self.tl([(0, a), (t, a), (t + .2, f'opacity:1;transform:scale({over})'), (t + .38, b), (end, b),
                        (end + .35, 'opacity:0;transform:scale(1)'), (T, a)], T=T)

    def slide(self, t, dx=0, dy=14, end=None, T=None, dur=.5):
        T = T or self.T
        end = T - .7 if end is None else end
        a, b = f'opacity:0;transform:translate({dx}px,{dy}px)', 'opacity:1;transform:translate(0px,0px)'
        return self.tl([(0, a), (t, a), (t + dur, b), (end, b), (end + .35, 'opacity:0;transform:translate(0px,0px)'),
                        (T, a)], ease='cubic-bezier(.2,.8,.2,1)', T=T)



def esc(s):
    return escape(str(s), quote=True)


def mono(x, y, spans, size, anchor='start', weight=400, cls='', extra='', fill=None, ls=None):
    """Monospace text whose width is pinned with textLength, so animations can rely on exact character cells."""
    if isinstance(spans, str):
        spans = [(spans, fill or C['text'])]
    n = sum(len(s[0]) for s in spans)
    inner = ''.join(f'<tspan fill="{s[1]}"' + (f' font-weight="{s[2]}"' if len(s) > 2 else '') + f'>{esc(s[0])}</tspan>'
                    for s in spans)
    cw = size * .6 + (ls or 0)
    c = f' class="{cls}"' if cls else ''
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{MONO}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" textLength="{n * cw:.1f}" lengthAdjust="spacingAndGlyphs" '
            f'style="white-space:pre" xml:space="preserve"{c}{extra}>{inner}</text>')


def sans(x, y, s, size, fill=None, weight=400, anchor='start', cls='', ls=None):
    c = f' class="{cls}"' if cls else ''
    sp = f' letter-spacing="{ls}"' if ls else ''
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{SANS}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill or C["text"]}" text-anchor="{anchor}"{sp}{c}>{esc(s)}</text>')


def doc(w, h, body, fx, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none" '
            f'role="img" aria-label="{esc(title)}">\n<title>{esc(title)}</title>\n'
            f'<style>{BASE_CSS}{"".join(fx.css)}</style>\n{body}\n</svg>\n')








def icon(name, x, y, s, color):
    paths = {
        'bell': '<path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z"/><path d="M10 20.5a2.2 2.2 0 0 0 4 0"/>',
        'trophy': '<path d="M8 21h8M12 16.5V21M7 4h10v5a5 5 0 0 1-10 0z"/><path d="M7 6H4.5a2 2 0 0 0 0 4H7M17 6h2.5a2 2 0 0 1 0 4H17"/>',
    }
    return (f'<g transform="translate({x},{y}) scale({s})" fill="none" stroke="{color}" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round">{paths[name]}</g>')


def cf_color(r):
    return [c for lo, _, c in CF_BANDS if r >= lo][-1]




FONT = {
    'D': ['11110', '10001', '10001', '10001', '10001', '10001', '11110'],
    'H': ['10001', '10001', '10001', '11111', '10001', '10001', '10001'],
    'R': ['11110', '10001', '10001', '11110', '10100', '10010', '10001'],
    'U': ['10001', '10001', '10001', '10001', '10001', '10001', '01110'],
    'V': ['10001', '10001', '10001', '10001', '10001', '01010', '00100'],
    'K': ['10001', '10010', '10100', '11000', '10100', '10010', '10001'],
    'M': ['10001', '11011', '10101', '10101', '10001', '10001', '10001'],
    'A': ['01110', '10001', '10001', '11111', '10001', '10001', '10001'],
}


# ───────────────────────────── hero ─────────────────────────────

def hero(d):
    W, H = 1000, 400
    fx = Fx()
    P, S = 14, 12
    cf, lc, cc, gh = d['codeforces'], d['leetcode'], d['codechef'], d['github']
    rnd = random.Random(7)

    cells, cx = [], 0
    for ch in 'DHRUV KUMAR':
        if ch == ' ':
            cx += 3
            continue
        for r, row in enumerate(FONT[ch]):
            cells += [(cx + c, r) for c, v in enumerate(row) if v == '1']
        cx += 6
    ncols = cx - 1
    nx0, ny0 = round((W - (ncols * P - (P - S))) / 2), 84

    out = [f'''<defs>
<clipPath id="card"><rect width="{W}" height="{H}" rx="{R}"/></clipPath>
<pattern id="grid" x="{nx0 % P}" y="{ny0 % P}" width="{P}" height="{P}" patternUnits="userSpaceOnUse"><rect width="{S}" height="{S}" rx="2.5" fill="#0c131c"/></pattern>
<radialGradient id="vig" cx="50%" cy="42%" r="72%"><stop offset="40%" stop-color="{C['bg']}" stop-opacity="0"/><stop offset="100%" stop-color="{C['bg']}" stop-opacity=".96"/></radialGradient>
<radialGradient id="glow"><stop offset="0%" stop-color="{C['g4']}" stop-opacity=".30"/><stop offset="100%" stop-color="{C['g4']}" stop-opacity="0"/></radialGradient>
</defs>
<g clip-path="url(#card)">
<rect width="{W}" height="{H}" fill="{C['bg']}"/>
<rect width="{W}" height="{H}" fill="url(#grid)"/>''']

    # twinkling contribution cells, kept off the text
    keep_out = [(nx0 - P, ny0 - P, nx0 + ncols * P + P, ny0 + 8 * P), (60, 196, 940, 304), (90, 300, 910, 362),
                (300, 360, 700, 400), (16, 16, 300, 54), (700, 16, 990, 54)]
    gx0, gy0 = nx0 % P, ny0 % P
    spots = set()
    while len(spots) < 60:
        gx, gy = rnd.randrange(W // P + 1), rnd.randrange(H // P + 1)
        px, py = gx0 + gx * P, gy0 + gy * P
        if any(a <= px <= c and b <= py <= e for a, b, c, e in keep_out):
            continue
        spots.add((px, py))
    for px, py in sorted(spots):
        col = LEVELS[rnd.choice([1, 1, 1, 2, 2, 3])]
        out.append(f'<rect x="{px}" y="{py}" width="{S}" height="{S}" rx="2.5" fill="{col}" fill-opacity=".55" '
                   f'style="animation:tw {rnd.uniform(9, 16):.1f}s ease-in-out {rnd.uniform(0, 10):.1f}s infinite both"/>')

    out.append(f'<rect width="{W}" height="{H}" fill="url(#vig)"/>')
    out.append(f'<ellipse cx="{W / 2}" cy="{ny0 + 48}" rx="440" ry="120" fill="url(#glow)" opacity=".8"/>')

    # the name assembles itself from the background grid: each square starts as a faint cell somewhere
    # on the board and glides into place along the grid lines (across, then down), warming up as it lands
    glide = 'cubic-bezier(.65,0,.35,1)'
    brighter = {2: LEVELS[3], 3: LEVELS[4], 4: '#6fdd8b'}
    for lv in (2, 3, 4):
        c = LEVELS[lv]
        # afterwards a slow, soft wave of green rolls through the letters
        fx.css.append(f'@keyframes wv{lv}{{0%,34%,100%{{fill:{c}}}17%{{fill:{brighter[lv]}}}}}')
    cols, rows = W // P, H // P
    for i, (c, r) in enumerate(cells):
        lv = rnd.choices([2, 3, 4], [2, 3, 6])[0]
        tgx, tgy = (nx0 - gx0) // P + c, (ny0 - gy0) // P + r
        sgx = min(max(tgx + rnd.randint(-22, 22), 0), cols - 1)
        sgy = min(max(tgy + rnd.choice([-1, 1]) * rnd.randint(3, 9), 0), rows - 1)
        dx, dy = (sgx - tgx) * P, (sgy - tgy) * P
        k = f'as{i}'
        fx.css.append(f'@keyframes {k}{{0%{{transform:translate({dx}px,{dy}px);fill:{LEVELS[1]};opacity:0}}'
                      f'12%{{opacity:.45}}55%{{transform:translate(0px,{dy}px);fill:{LEVELS[1]};opacity:.7}}'
                      f'100%{{transform:translate(0px,0px);fill:{LEVELS[lv]};opacity:1}}}}')
        d1 = .3 + rnd.random() * 1.1
        d2 = 4.2 + c * .045 + r * .015
        out.append(f'<rect x="{nx0 + c * P}" y="{ny0 + r * P}" width="{S}" height="{S}" rx="2.5" fill="{LEVELS[lv]}" '
                   f'style="animation:{k} 2.4s {glide} {d1:.2f}s 1 both,wv{lv} 12s ease-in-out {d2:.2f}s infinite"/>')
    # now and then a single square brightens and fades, like a commit landing
    for c, r in rnd.sample(cells, 12):
        period, delay = rnd.uniform(9, 15), rnd.uniform(5, 14)
        k = fx.anim('0%,100%{opacity:0}7%{opacity:.9}22%{opacity:0}', period, 'ease-in-out', delay)
        out.append(f'<rect x="{nx0 + c * P}" y="{ny0 + r * P}" width="{S}" height="{S}" rx="2.5" fill="{C["mint"]}" class="{k}"/>')

    out.append('</g>')

    out.append(mono(30, 40, [('~/', C['dim']), ('dhruvwarriorr', C['muted'])], 12))
    out.append(mono(W - 30, 40, [('MUMBAI, IN', C['text'], 700)], 12, 'end'))
    tag = fx.anim('from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}', .8, 'ease-out', 1.6, 1)
    out.append(sans(W / 2, 222, 'PROBLEM SOLVER',
                    12.5, C['muted'], 600, 'middle', tag, ls=3))

    # command palette: typed phrases, one after another
    bx, by, bw, bh = 170, 244, 660, 54
    boxfill = '#0a1019'
    box_in = fx.anim('from{opacity:0;transform:scale(.96)}to{opacity:1;transform:scale(1)}', .7, 'cubic-bezier(.2,.8,.2,1)', 1.9, 1)
    out.append(f'<g class="fb {box_in}"><rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="10" fill="{boxfill}" stroke="#223041"/>')
    out.append(icon('trophy', bx + 18, by + 16, .92, C['g4']))
    out.append(f'<clipPath id="typeclip"><rect x="{bx + 44}" y="{by + 8}" width="{bw - 110}" height="{bh - 16}"/></clipPath>')
    phrases = [
        'winner at gemini hackday 2026',
        'fy winner at codespree 2025',
        'runner-up at codebuster 2.0',
    ]
    FS = 17
    cw = FS * .6
    tx, ty = bx + 50, by + 33
    sched, t = [], 2.4
    for p in phrases:
        n = len(p)
        s0 = t + .45
        s1 = s0 + n * .045
        s2 = s1 + 2.1
        s3 = s2 + .45
        sched.append((p, t, s0, s1, s2, s3, s3 + .15))
        t = s3 + .15
    T = t
    for p, s, s0, s1, s2, s3, e in sched:
        n = len(p)
        vis = fx.tl([(0, 'opacity:0'), (s, 'opacity:0'), (s + .01, 'opacity:1'), (e, 'opacity:1'), (e + .01, 'opacity:0'),
                     (T, 'opacity:0')], T=T)
        full = f'transform:translateX({n * cw:.2f}px)'
        mv = fx.tl([(0, 'transform:translateX(0px)'), (s0, f'transform:translateX(0px);animation-timing-function:steps({n},end)'),
                    (s1, full), (s2, f'{full};animation-timing-function:steps({n},end)'), (s3, 'transform:translateX(0px)'),
                    (T, 'transform:translateX(0px)')], T=T)
        out.append(f'<g class="{vis}">' + mono(tx, ty, [(p, C['text'])], FS) +
                   f'<g clip-path="url(#typeclip)"><g class="{mv}"><rect x="{tx}" y="{ty - 15}" width="{cw:.1f}" height="20" '
                   f'rx="1.5" fill="{C["g4"]}" class="blink"/><rect x="{tx + cw:.1f}" y="{ty - 18}" width="700" height="26" '
                   f'fill="{boxfill}"/></g></g></g>')
    out.append('</g>')

    # ratings as one powerline status bar: solid segments joined by arrow separators
    ink = '#0b1018'
    marks = {
        'cf': f'<rect x="0" y="6" width="4" height="10" rx="1" fill="{ink}"/><rect x="6" y="1" width="4" height="15" rx="1" fill="{ink}"/>'
              f'<rect x="12" y="4" width="4" height="12" rx="1" fill="{ink}"/>',
        'lc': f'<path d="M10 1.5 3.6 7.9a3 3 0 0 0 0 4.2l2.3 2.3a3 3 0 0 0 4.2 0l1.9-1.9M7 9.5h8" stroke="{ink}" stroke-width="2.2" '
              f'stroke-linecap="round" stroke-linejoin="round"/>',
        'cc': f'<path d="M3.5 15.5h9v-4.4a3.2 3.2 0 1 0-1.2-6.1 3.2 3.2 0 0 0-5.6 0 3.2 3.2 0 1 0-1.2 6.1z" stroke="{ink}" stroke-width="1.8" '
              f'stroke-linejoin="round"/><path d="M3.5 13h9" stroke="{ink}" stroke-width="1.8"/>',
        'gh': f'<path fill="{ink}" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49'
              '-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87'
              ' 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21'
              ' 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82'
              ' 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8'
              'c0-4.42-3.58-8-8-8z"/>',
    }
    segs = [('cf', 'CF', str(cf['rating']), cf['rank'].title(), cf_color(cf['rating'])),
            ('lc', 'LC', str(lc['rating']), lc['badge'], C['orange']),
            ('cc', 'CC', str(cc['rating']), f"{cc['stars']}★", C['chef']),
            ('gh', 'GH', str(gh['total']), 'contributions', C['g4'])]
    y0, h, tip, fs = 322, 28, 10, 11
    cw = fs * .6
    widths = [(len(lab) + len(val) + len(rank) + 2) * cw + 18 + 11 + (tip if i else 0) + 8
              for i, (_, lab, val, rank, _) in enumerate(segs)]
    x = (W - sum(widths) - tip) / 2
    xs = []
    for w in widths:
        xs.append(x)
        x += w
    parts = []
    for i in reversed(range(len(segs))):
        kind, lab, val, rank, col = segs[i]
        x, w = xs[i], widths[i]
        mid, y1 = y0 + h / 2, y0 + h
        if i == 0:
            d_ = (f'M{x + 5:.1f} {y0}H{x + w:.1f}L{x + w + tip:.1f} {mid}L{x + w:.1f} {y1}H{x + 5:.1f}'
                  f'Q{x:.1f} {y1} {x:.1f} {y1 - 5}V{y0 + 5}Q{x:.1f} {y0} {x + 5:.1f} {y0}Z')
        else:
            d_ = f'M{x:.1f} {y0}H{x + w:.1f}L{x + w + tip:.1f} {mid}L{x + w:.1f} {y1}H{x:.1f}L{x + tip:.1f} {mid}Z'
        tx = x + 11 + (tip if i else 0)
        k = fx.anim('from{opacity:0;transform:translateX(-14px)}to{opacity:1;transform:none}', .45,
                    'cubic-bezier(.2,.8,.2,1)', 2.2 + i * .14, 1)
        parts.append(f'<g class="{k}"><path d="{d_}" fill="{col}" stroke="{C["bg"]}" stroke-width="3" stroke-linejoin="round"/>'
                     f'<g transform="translate({tx:.1f} {y0 + 7.6}) scale(.8)">{marks[kind]}</g>'
                     + mono(tx + 18, y0 + 18, [(lab + ' ', ink), (val + ' ', ink, 800), (rank, ink, 600)], fs,
                            extra=' fill-opacity=".9"') + '</g>')
    out.append(''.join(parts))

    out.append(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="{R}" stroke="{C["line"]}"/>')
    return doc(W, H, '\n'.join(out), fx, 'Dhruv Kumar, competitive programmer and builder')




# ───────────────────────────── project cards ─────────────────────────────
# Each card carries the project's real mark, taken from its own repository.

LOGO = {
    'AlgoMemtor': ('0 0 48 48', '<circle cx="24" cy="24" r="24" fill="#0b1220" stroke="#26324a"/><path d="M14.5 34.5 24 14l9.5 20.5" stroke="#f6f9fd" '
                   'stroke-width="4" stroke-linecap="round" stroke-linejoin="round" fill="none"/><circle cx="24" cy="27.2" r="3.4" fill="#f5c33b"/>'),
    'DueCare': ('0 0 100 100', '<defs><clipPath id="dcin"><path d="M34,27.5 H66 A22.5,22.5 0 0 1 66,72.5 H34 A22.5,22.5 0 0 1 34,27.5 Z"/>'
                '</clipPath></defs><rect width="100" height="100" rx="23" fill="#18171B"/><g transform="translate(13 13) scale(0.74)">'
                '<path clip-path="url(#dcin)" d="M-10,-10 L64.2,-10 L39.8,110 L-10,110 Z" fill="#C21C58"/>'
                '<path fill-rule="evenodd" fill="#FFFFFF" d="M34,37 H53 A13,13 0 0 1 53,63 H34 Z M44,45 V55 H53 A5,5 0 0 0 53,45 Z"/>'
                '<path d="M34,24 H66 A26,26 0 0 1 66,76 H34 A26,26 0 0 1 34,24 Z" fill="none" stroke="#FFFFFF" stroke-width="7"/></g>'),
    'Nautiq': ('0 0 26 26', '<rect x="6" y="4" width="18" height="18" fill="#ffffff"/><g fill="#123f6b">'
               + ''.join(f'<rect x="{6 + c * 4.5}" y="{4 + r * 4.5}" width="4.5" height="4.5"/>'
                         for r in range(4) for c in range(4) if (r + c) % 2 == 0) +
               '</g><rect x="6" y="4" width="18" height="18" fill="none" stroke="#123f6b" stroke-width="1"/>'
               '<path d="M3 2v22" stroke="#c9d1d9" stroke-width="1.75" stroke-linecap="round"/>'),
}


def logo(name, x, y, s):
    vb, inner = LOGO[name]
    return f'<svg x="{x}" y="{y}" width="{s}" height="{s}" viewBox="{vb}">{inner}</svg>'


def card(fx, name, accent, canvas, tagline, tags, stars):
    W, H, CH = 320, 440, 196
    out = [f'''<defs><clipPath id="cc"><rect width="{W}" height="{H}" rx="{R}"/></clipPath>
</defs>
<rect width="{W}" height="{H}" rx="{R}" fill="{C['card']}"/>
<g clip-path="url(#cc)">{canvas}<path d="M0 {CH}.5H{W}" stroke="{C['line']}"/></g>''']
    out.append(logo(name, 22, CH + 20, 28))
    out.append(sans(60, CH + 42, name, 24, C['text'], 800))
    if stars:
        out.append(mono(W - 22, CH + 40, [('★ ', C['gold']), (str(stars), C['muted'])], 13, 'end'))
    for i, line in enumerate(textwrap.wrap(tagline, 40)):
        out.append(sans(22, CH + 74 + i * 20, line, 13.5, '#9ba7b4'))
    x = 22
    for j, tg in enumerate(tags):
        w = len(tg) * 6.6 + 20
        col = accent if j == 0 else C['muted']
        out.append(f'<rect x="{x:.1f}" y="{H - 82}" width="{w:.1f}" height="24" rx="6" fill="{C["panel"]}" stroke="{col}" stroke-opacity=".45"/>')
        out.append(mono(x + w / 2, H - 66, [(tg, col)], 11, 'middle'))
        x += w + 8
    out.append(f'<path d="M22 {H - 42}.5H{W - 22}" stroke="{C["line"]}"/>')
    out.append(mono(22, H - 18, [('↗ ', accent, 700), (f'github.com/dhruvwarriorr/{name}', C['text'])], 12))
    out.append(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="{R}" stroke="{C["line"]}"/>')
    return doc(W, H, '\n'.join(out), fx, name)


def project_algomemtor(d):
    T = 8
    fx = Fx(T)
    acc = C['blue']
    nodes = [(160, 72, 8), (96, 118, 3), (224, 118, 10), (62, 164, 1), (130, 164, 6), (192, 164, 9), (258, 164, 14)]
    edges = [(0, 1), (0, 2), (1, 3), (1, 4), (2, 5), (2, 6)]
    cv = [f'<defs><linearGradient id="sky1" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0d1838"/>'
          f'<stop offset="1" stop-color="{C["card"]}"/></linearGradient>'
          f'<pattern id="dots" width="16" height="16" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="#1d2a4a"/></pattern></defs>'
          f'<rect width="320" height="196" fill="url(#sky1)"/><rect width="320" height="196" fill="url(#dots)"/>']
    for a, b in edges:
        (x1, y1, _), (x2, y2, _) = nodes[a], nodes[b]
        cv.append(f'<path d="M{x1} {y1}L{x2} {y2}" stroke="#25324d" stroke-width="2"/>')
    for a, b in edges:
        (x1, y1, _), (x2, y2, _) = nodes[a], nodes[b]
        ln = math.dist((x1, y1), (x2, y2))
        t = .5 + b * .42 - .2
        k = fx.tl([(0, f'stroke-dashoffset:{ln:.1f};opacity:1'), (t, f'stroke-dashoffset:{ln:.1f};opacity:1'),
                   (t + .3, 'stroke-dashoffset:0;opacity:1'), (T - .7, 'stroke-dashoffset:0;opacity:1'),
                   (T - .35, 'stroke-dashoffset:0;opacity:0'), (T, f'stroke-dashoffset:{ln:.1f};opacity:0')])
        cv.append(f'<path d="M{x1} {y1}L{x2} {y2}" stroke="{acc}" stroke-width="2.4" stroke-dasharray="{ln:.1f}" class="{k}"/>')
    for i, (x, y, v) in enumerate(nodes):
        t = .5 + i * .42
        cv.append(f'<circle cx="{x}" cy="{y}" r="15" fill="#111a30" stroke="#2b3a5c" stroke-width="2"/>')
        cv.append(f'<g class="fb {fx.pop(t, over=1.3)}"><circle cx="{x}" cy="{y}" r="15" fill="{acc}" fill-opacity=".25" '
                  f'stroke="{acc}" stroke-width="2.2"/></g>')
        ring = fx.tl([(0, 'opacity:0;transform:scale(1)'), (t, 'opacity:.9;transform:scale(1)'), (t + .8, 'opacity:0;transform:scale(1.8)'),
                      (T, 'opacity:0;transform:scale(1)')], ease='ease-out')
        cv.append(f'<circle cx="{x}" cy="{y}" r="15" stroke="{acc}" class="fb {ring}"/>')
        cv.append(mono(x, y + 4.5, [(str(v), C['text'], 700)], 12, 'middle'))
    th = .5 + 7 * .42 + .2
    cv.append(f'<g class="{fx.slide(th, dy=-10)}"><rect x="34" y="14" width="252" height="30" rx="8" fill="{C["panel"]}" stroke="{acc}" stroke-opacity=".6"/>'
              f'<circle cx="52" cy="29" r="4" fill="{C["gold"]}" class="blink"/>' +
              mono(64, 33.5, [('hint ', C['gold'], 700), ('→ try binary search on answer', C['text'])], 11) + '</g>')
    return card(fx, 'AlgoMemtor', acc, ''.join(cv),
                'AI coach for competitive programmers: personalised problem picks, guided hints and progress tracking across platforms.',
                ['TypeScript', 'FastAPI', 'LangChain'], d['github'].get('repo_stars', {}).get('AlgoMemtor', 0))


def project_duecare(d):
    T = 8
    fx = Fx(T)
    acc = '#ff6b9a'
    cv = [f'<defs><linearGradient id="sky2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1c1236"/>'
          f'<stop offset="1" stop-color="{C["card"]}"/></linearGradient></defs><rect width="320" height="196" fill="url(#sky2)"/>']
    pw, ph = 36, 26
    gx = (320 - 7 * pw + 6) / 2
    gy = 74
    for c, ch in enumerate('MTWTFSS'):
        cv.append(mono(gx + c * pw + 15, gy - 8, ch, 10, 'middle', fill=C['muted']))
    for r in range(4):
        for c in range(7):
            x, y = gx + c * pw, gy + r * ph
            cv.append(f'<rect x="{x:.1f}" y="{y}" width="30" height="20" rx="4" fill="#161a2e" stroke="#262a45"/>')
            cv.append(mono(x + 5, y + 10, str(1 + r * 7 + c), 7.5, fill=C['dim']))
    deadlines = {(1, 0): C['orange'], (4, 1): C['purple'], (2, 2): C['red'], (5, 2): C['sky'], (3, 3): C['orange'], (0, 3): C['purple']}
    for i, ((c, r), col) in enumerate(sorted(deadlines.items(), key=lambda z: (z[0][1], z[0][0]))):
        x, y = gx + c * pw, gy + r * ph
        t = 1.1 + i * .55
        cv.append(f'<rect x="{x + 4:.1f}" y="{y + 13}" width="22" height="4" rx="2" fill="{col}"/>')
        k = fx.tl([(0, 'stroke-dashoffset:16'), (t, 'stroke-dashoffset:16'), (t + .3, 'stroke-dashoffset:0'), (T - .7, 'stroke-dashoffset:0'),
                   (T - .3, 'stroke-dashoffset:16'), (T, 'stroke-dashoffset:16')])
        cv.append(f'<g class="{fx.show(t, fade=.1)}"><rect x="{x:.1f}" y="{y}" width="30" height="20" rx="4" fill="{C["g4"]}" fill-opacity=".14" stroke="{C["g4"]}" stroke-opacity=".6"/></g>')
        cv.append(f'<path d="M{x + 10:.1f} {y + 9}l3.5 3.5 7-7" stroke="{C["g4"]}" stroke-width="2.2" stroke-linecap="round" '
                  f'stroke-linejoin="round" stroke-dasharray="16" class="{k}"/>')
    wig = fx.anim('0%,60%,100%{transform:rotate(0)}64%{transform:rotate(18deg)}70%{transform:rotate(-16deg)}76%{transform:rotate(10deg)}82%{transform:rotate(-6deg)}',
                  2.4, 'ease-in-out')
    cv.append(f'<g class="{fx.slide(.3, dx=40, dy=0)}"><rect x="58" y="12" width="236" height="34" rx="8" fill="{C["panel"]}" stroke="{acc}" stroke-opacity=".6"/>'
              f'<g class="fb {wig}" style="transform-origin:50% 0">{icon("bell", 68, 17, 1, C["gold"])}</g>' +
              mono(98, 33, [('DBMS lab', C['text'], 700), (', due tomorrow', C['muted'])], 11) + '</g>')
    return card(fx, 'DueCare', acc, ''.join(cv),
                'AI academic planner that imports Gmail and Classroom deadlines, fits them to your timetable and nudges you on time.',
                ['Python', 'Flutter'], d['github'].get('repo_stars', {}).get('DueCare', 0))


def wave_path(y, amp, wl, width, depth):
    seg, x = '', 0
    while x < width:
        seg += f' q{wl / 4} {-amp} {wl / 2} 0 t{wl / 2} 0'
        x += wl
    return f'M0 {y}{seg} V{depth} H0 Z'


def project_nautiq(d):
    T = 8
    fx = Fx(T)
    acc = C['cyan']
    rnd = random.Random(5)
    cv = [f'<defs><linearGradient id="sky3" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#04121d"/>'
          f'<stop offset="1" stop-color="#0b3346"/></linearGradient><radialGradient id="moon"><stop offset=".55" stop-color="#e6edf3"/>'
          f'<stop offset=".6" stop-color="#e6edf3" stop-opacity=".25"/><stop offset="1" stop-color="#e6edf3" stop-opacity="0"/></radialGradient></defs>'
          f'<rect width="320" height="196" fill="url(#sky3)"/><circle cx="262" cy="46" r="30" fill="url(#moon)"/>']
    for _ in range(14):
        cv.append(f'<circle cx="{rnd.uniform(10, 310):.0f}" cy="{rnd.uniform(8, 90):.0f}" r="{rnd.choice([.8, 1, 1.3])}" fill="#fff" '
                  f'style="animation:tw {rnd.uniform(2, 5):.1f}s ease-in-out {rnd.uniform(0, 3):.1f}s infinite both"/>')
    for i in range(5):
        k = fx.anim('0%{transform:translateX(0);opacity:0}20%{opacity:.7}100%{transform:translateX(-360px);opacity:0}',
                    rnd.uniform(2.2, 3.4), 'linear', rnd.uniform(0, 2))
        cv.append(f'<path d="M{330 + rnd.uniform(0, 40):.0f} {70 + i * 13}h{rnd.uniform(26, 44):.0f}" stroke="#9fe7f5" stroke-opacity=".5" '
                  f'stroke-width="1.3" stroke-linecap="round" class="{k}"/>')
    for y, amp, wl, col, op, dur in [(122, 6, 160, '#0e7490', .45, 7), (136, 8, 120, '#0891b2', .55, 5)]:
        k = fx.anim(f'from{{transform:translateX(0)}}to{{transform:translateX({-wl}px)}}', dur)
        cv.append(f'<path d="{wave_path(y, amp, wl, 320 + wl * 2, 200)}" fill="{col}" fill-opacity="{op}" class="{k}"/>')
    bob = fx.anim('0%,100%{transform:translateY(0) rotate(-5deg)}50%{transform:translateY(-6px) rotate(6deg)}', 3, 'ease-in-out')
    # the buoy flies Nautiq's own flag
    flag = LOGO['Nautiq'][1].replace('stroke="#c9d1d9"', 'stroke="none"')
    cv.append(f'<g class="fb {bob}"><path d="M150 140h20l-4 -18h-12z" fill="{C["red"]}"/><path d="M152.5 131h15" stroke="#fff" stroke-width="3"/>'
              f'<path d="M160 122v-30" stroke="#c9d1d9" stroke-width="1.6"/>'
              f'<svg x="155" y="90" width="26" height="26" viewBox="0 0 26 26">{flag}</svg></g>')
    k = fx.anim('from{transform:translateX(0)}to{transform:translateX(-100px)}', 3.6)
    cv.append(f'<path d="{wave_path(150, 9, 100, 520, 200)}" fill="#0b4a62" class="{k}"/>')
    cv.append(f'<rect x="12" y="12" width="164" height="44" rx="7" fill="#06141f" fill-opacity=".85" stroke="{acc}" stroke-opacity=".4"/>')
    cv.append(mono(22, 30, [('WAVE ', C['muted']), ('1.4m', C['text'], 700), ('±0.2', C['dim']), (', 8s', C['muted'])], 10))
    cv.append(mono(22, 46, [('WIND ', C['muted']), ('12kn SW', C['text'], 700), (', ', C['muted']), ('28.6°C', acc, 700)], 10))
    return card(fx, 'Nautiq', acc, ''.join(cv),
                "Ocean conditions explorer for India's coast: waves, wind, currents and sea temperature with traceable evidence.",
                ['Go', 'Python'], d['github'].get('repo_stars', {}).get('Nautiq', 0))




# ───────────────────────────── section heading ─────────────────────────────

def heading(cmd, note):
    """A quiet section title: one shell command, typed out between two hairlines, so the name stays the hero."""
    W, H, fs = 1000, 56, 15
    cw = fs * .6
    fx = Fx()
    width = (2 + len(cmd)) * cw + (16 + len(note) * 12 * .6 if note else 0)
    x0 = (W - width) / 2
    y = 34
    tx = x0 + 2 * cw
    typed = ''.join(mono(tx + i * cw, y, [(ch, C['text'], 600)], fs, cls=fx.anim('from{opacity:0}to{opacity:1}', .01, 'linear',
                                                                                 .3 + (i + 1) * .06, 1))
                    for i, ch in enumerate(cmd) if ch != ' ')
    out = [f'<path d="M24 {y - 5}.5H{x0 - 34:.0f}M{x0 + width + 34:.0f} {y - 5}.5H{W - 24}" stroke="#8b949e" stroke-opacity=".35"/>',
           f'<rect x="{x0 - 18:.1f}" y="{y - 23}" width="{width + 36:.1f}" height="34" rx="8" fill="{C["card"]}" stroke="#30363d"/>',
           mono(x0, y, [('❯ ', C['g4'], 700)], fs), typed,
           mono(x0 + (2 + len(cmd)) * cw + 16, y, [(note, C['muted'])], 12,
                cls=fx.anim('from{opacity:0}to{opacity:1}', .4, 'ease-out', 1.2, 1)) if note else '']
    return doc(W, H, '\n'.join(out), fx, f'{cmd}: {note}' if note else cmd)

def main():
    d = load_data()
    os.makedirs(ASSETS, exist_ok=True)
    for name, fn in [('hero', hero), ('project-algomemtor', project_algomemtor), ('project-duecare', project_duecare),
                     ('project-nautiq', project_nautiq)]:
        svg = fn(d)
        with open(os.path.join(ASSETS, f'{name}.svg'), 'w') as f:
            f.write(svg)
        print(f'  wrote assets/{name}.svg ({len(svg) // 1024} KB)')
    with open(os.path.join(ASSETS, 'heading-shipped.svg'), 'w') as f:
        f.write(heading('ls ~/shipped', ''))


if __name__ == '__main__':
    main()
