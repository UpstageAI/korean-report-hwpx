"""규칙 JSON 캐시(blank.load_json) — 공개 로더는 같은 값·다른 객체를 돌려주고, 돌려받은 것을 고쳐도 다음 호출에 새지 않는다. 작성 Claude"""
import pytest

import blank as B
import compose as C
import official as O
import report as RP

LOADERS = {
    "press_rules": lambda: C.load_rules("행정안전부"),
    "press_layout": lambda: C.load_layout("행정안전부"),
    "report_rules_org": lambda: RP.load_rules("과학기술정보통신부"),
    "report_rules_common": lambda: RP.load_rules(""),
    "official_common": lambda: O._common(),
    "appx_rule": lambda: RP.ReportComposer("과학기술정보통신부").appx_rule(),
    "page_settings": lambda: B.page_settings("과학기술정보통신부"),
}


def _poke(d):
    """가장 깊은 dict 한 곳과 맨 위에 표식을 남긴다(겉만 복사했으면 안쪽 표식이 다음 호출에 샘)."""
    d["__poke__"] = 1
    for v in d.values():
        if isinstance(v, dict): return _poke(v)


def _has_poke(d):
    return "__poke__" in d or any(isinstance(v, dict) and _has_poke(v) for v in d.values())


@pytest.mark.parametrize("name", sorted(LOADERS))
def test_loader_gives_fresh_copy(name):
    fn = LOADERS[name]
    a, b = fn(), fn()
    assert a == b and a is not b
    _poke(a)
    c = fn()
    assert c == b and not _has_poke(c)


def test_load_json_is_cached_once():
    p = C.ROOT / "rules/_전체.json"
    assert B.load_json(p) is B.load_json(p)
    assert C.load_rules("") is not B.load_json(p)   # 공개 로더는 캐시 객체를 그대로 주지 않는다
