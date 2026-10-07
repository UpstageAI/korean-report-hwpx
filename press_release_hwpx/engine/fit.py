"""줄 바꿈 예측과 자간 맞춤. 작성 Mia(윤승미)
한글(워드프로세서)은 어절 단위로 줄을 바꾸고, 글자 폭 = 글꼴 크기 × 글자 종류별 폭 비율 × 장평 + 자간(크기 × 자간%).
실물 HWPX의 lineseg(줄 시작 위치)로 폭 비율을 보정해 두고, 생성 시 문단마다 자간을 골라
① 줄 수를 최소로 ② 마지막 줄이 너무 짧지 않게(한두 어절 고아 줄 방지) 한다."""
import re, unicodedata

# 글자 종류별 폭(em). 보정값은 calibrate()로 갱신
W = {"hangul": 1.0, "space": 0.5, "digit": 0.5, "latin": 0.5, "upper": 0.62, "narrow": 0.3, "punct": 0.5, "wide": 1.0}
NARROW = set(".,:;'\"`!|()[]{}·‘’“”")


def kind(ch):
    if ch == " ": return "space"
    if "가" <= ch <= "힣" or "ㄱ" <= ch <= "ㆎ": return "hangul"
    if ch.isdigit(): return "digit"
    if "a" <= ch <= "z": return "latin"
    if "A" <= ch <= "Z": return "upper"
    if ch in NARROW: return "narrow"
    if ch in "□■○●◦◯〇ㅇ◇◆❍※①②③④⑤⑥⑦⑧⑨⑩▪▶►☞→←↑↓「」『』《》〈〉【】": return "wide"  # 기호·괄호는 전각(1칸)
    if unicodedata.east_asian_width(ch) in "WF": return "wide"
    return "punct"


def width(s, pt, spacing, ratio=100, w=W):
    em = pt * 100  # HWPUNIT (1pt = 100)
    return sum(em * (w[kind(c)] * ratio / 100 + spacing / 100) for c in s)


def wrap(text, pt, spacing, first_w, rest_w, ratio=100, w=W, keep_word=True):
    """줄 바꿈 → 각 줄 문자열 목록. keep_word=어절 단위(KEEP_WORD), False=한글 글자 단위(BREAK_WORD, 라틴 단어는 유지)."""
    words = re.split(r"(?<= )", text) if keep_word else re.findall(r"[A-Za-z0-9]+ ?|. ?", text)
    lines, cur, limit = [], "", first_w
    for wd in words:
        if cur and width((cur + wd).rstrip(" "), pt, spacing, ratio, w) > limit:
            lines.append(cur); cur = wd; limit = rest_w
            # 한 어절이 줄보다 길면 글자 단위로 자름
            while width(cur.rstrip(" "), pt, spacing, ratio, w) > limit:
                k = len(cur)
                while k > 1 and width(cur[:k], pt, spacing, ratio, w) > limit: k -= 1
                lines.append(cur[:k]); cur = cur[k:]
        else:
            cur += wd
    if cur: lines.append(cur)
    return lines


def choose_spacing(text, pt, base, first_w, rest_w, ratio=100, lo=-8, hi=3, keep_word=True):
    """후보 자간 중 (줄 수 최소, 마지막 줄 충분히 참, 원래 자간에 가까움) 순으로 고른다."""
    best = None
    for s in range(base + lo, base + hi + 1):
        if s < -10: continue
        ls = wrap(text, pt, s, first_w, rest_w, ratio, keep_word=keep_word)
        lw = rest_w if len(ls) > 1 else first_w
        fill = width(ls[-1].rstrip(), pt, s, ratio) / lw
        orphan = len(ls) > 1 and fill < 0.30
        key = (len(ls), orphan, abs(s - base) + (0 if s <= base else 0.5))
        if best is None or key < best[0]: best = (key, s, ls)
    return best[1], best[2]


def calibrate(samples, grid=None):
    """samples: [(text, pt, spacing, ratio, first_w, rest_w, 실제 줄 시작 위치 목록)] → 맞춘 비율 W와 일치율."""
    import itertools
    grid = grid or {"space": [0.25, 0.3, 0.33, 0.4, 0.5], "digit": [0.5, 0.55, 0.6], "narrow": [0.25, 0.3, 0.35, 0.5]}
    best = (-1, None)
    for vals in itertools.product(*grid.values()):
        w = dict(W); w.update(dict(zip(grid, vals))); ok = 0
        for text, pt, sp, ra, fw, rw, starts, kw, *_ in samples:
            ls = wrap(text, pt, sp, fw, rw, ra, w, kw)
            pos, acc = [], 0
            for l in ls: pos.append(acc); acc += len(l)
            ok += pos == starts
        if ok > best[0]: best = (ok, w)
    return best[1], best[0] / max(1, len(samples))
