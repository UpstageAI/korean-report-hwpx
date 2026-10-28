"""보도자료 작성 방법(내용) 가이드·사실 메모 → 구조 초안·작성 점검 (SPEC_press_writing_guide.md). 작성 Mia(윤승미)
예시의 인물·숫자는 가상이다."""
import asyncio, copy, json, re, sys, zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from korean_report_hwpx import server as SV  # noqa: E402

PKG = Path(SV.__file__).parent
DATA = json.loads((PKG / "guides" / "press_writing.json").read_text("utf-8"))
EX = {e["ministry"]: e for e in DATA["examples"]}
MSIT, MOIS = "과학기술정보통신부", "행정안전부"


def W(structure, ministry=MSIT):
    return SV.check_structure(structure, "press_release", ministry=ministry)["warnings"]


def wtext(ws):
    return " ".join(ws)


def writing(ws):
    return [w for w in ws if w.startswith("[작성]")]


# ── 데이터·안내 ──
def test_guide_data_shape():
    assert {"G20", "R20", "G11", "H22", "E14", "C"} <= set(DATA["sources"])
    assert set(EX) == {MSIT, MOIS}
    assert len(DATA["guide"]) >= 15 and DATA["guide"][0].startswith("[보도자료 작성 방법")
    assert hasattr(SV, "PRESS_GUIDE") and SV.PRESS_GUIDE["check"]["lead_max"] == DATA["check"]["lead_max"]


def test_instructions_route_press_requests():
    ins = SV.mcp.instructions
    for k in ("보도자료", "보도참고자료", "설명자료", "해명자료", "보고서", "기안문", "HWPX", "한글",
              "직접 만들지 말고", "draft_press_structure", "get_writing_guide", "check_structure", "build_document"):
        assert k in ins, k
    assert ins.index("get_writing_guide") < ins.index("draft_press_structure") < ins.index("build_document")
    assert "지어내지" in ins


def test_tool_descriptions():
    tools = {t.name: t for t in asyncio.run(SV.mcp.list_tools())}
    assert "draft_press_structure" in tools
    assert tools["build_document"].description.strip().startswith("보고서·보도자료(보도참고·설명·해명자료 포함)·기안문을 기관 서식 HWPX(한글 파일)로 만든다.")
    d = tools["get_writing_guide"].description
    assert "press_release" in d and "사실 메모" in d
    assert "ministry" in tools["check_structure"].input_schema["properties"]


def test_writing_guide_press_has_content_method():
    g = SV.get_writing_guide("press_release", MOIS)
    txt = g["guide"]
    assert "[보도자료 작성 방법" in txt
    for k in ("누가·언제·무엇을", "”라고", "인공지능(AI)", "역피라미드", "76억 원", "참고 1"):
        assert k in txt, k
    assert txt.index("[보도자료 규칙]") < txt.index("[보도자료 작성 방법")
    pw = g["press_writing"]
    assert set(pw) >= {"steps", "facts_template", "facts_fields", "kinds", "types_order"}
    assert set(pw["kinds"]) == {"보도자료", "보도참고자료", "설명자료", "해명자료"}
    assert [e["ministry"] for e in g["examples_press_release"]] == [MSIT, MOIS]
    assert g["example_press_release"] == EX[MOIS]["structure"]
    assert SV.get_writing_guide("press_release", "국토교통부")["example_press_release"] == EX[MSIT]["structure"]
    assert "kind" in g["schema"]["press_release"]


def test_writing_guide_other_types_unchanged():
    assert "[보도자료 작성 방법" not in SV.get_writing_guide("report")["guide"]
    assert "[보도자료 작성 방법" not in SV.get_writing_guide("official")["guide"]
    a = SV.get_writing_guide("auto")
    assert "[보도자료 작성 방법" in a["guide"] and a["example_press_release"] == EX[MSIT]["structure"]
    assert not hasattr(SV, "EXAMPLE_PRESS")
    assert "“" in SV.writing_guide_prompt("press_release")


# ── 예시: 초안 = 기대 구조, 점검 통과, 생성 ──
@pytest.mark.parametrize("m", [MSIT, MOIS])
def test_examples_roundtrip(m, tmp_path):
    e = EX[m]
    r = SV.draft_press_structure(e["facts"])
    assert r["doc_type"] == "press_release" and r["ministry"] == m
    assert r["structure"] == e["structure"]
    assert writing(r["warnings"]) == []
    c = SV.check_structure(e["structure"], "press_release", ministry=m)
    assert c["ok"], c["warnings"]
    b = SV.build_document(r["structure"], "press_release", m, str(tmp_path / "x.hwpx"))
    assert Path(b["hwpx"]).exists() and b["warnings"] == []
    zipfile.ZipFile(b["hwpx"]).testzip()
    xml = zipfile.ZipFile(b["hwpx"]).read("Contents/section0.xml").decode("utf-8")
    assert "보도자료" in xml and "라고 말했다" in xml


def test_example_missing_contact_people():
    r = SV.draft_press_structure(EX[MOIS]["facts"])
    assert any(x.startswith("contact") for x in r["missing"])
    assert not any(x.startswith("contact") for x in SV.draft_press_structure(EX[MSIT]["facts"])["missing"])
    assert MOIS in r["next"] and "build_document" in r["next"]


# ── 조사 ──
@pytest.mark.parametrize("word,pair,exp", [
    ("과학기술정보통신부(장관 ○○○)", "은/는", "는"), ("○○○ 과학기술정보통신부 장관", "은/는", "은"),
    ("○○○ 행정안전부 지방재정경제실장", "은/는", "은"), ("행정안전부", "은/는", "는"), ("KT", "은/는", "는"),
    ("LG", "은/는", "는"), ("IBM", "은/는", "은"), ("2030", "은/는", "은"), ("2025", "은/는", "는"),
    ("「인공지능 기본법」", "은/는", "은"), ("국토교통부 (장관 ○○○) ", "은/는", "는"), ("○○청", "이/가", "이"), ("○○부", "이/가", "가")])
def test_josa(word, pair, exp):
    assert SV._josa(word, pair) == exp


# ── 초안 도구 규칙 ──
def F(**kw):
    base = {"ministry": MSIT, "headline": "○○ 서비스 시범 운영", "release": "2026. 11. 2.(월) 조간",
            "who": "과학기술정보통신부(장관 ○○○)", "when": "11월 2일(월)부터", "what": "○○ 서비스를 시범 운영한다",
            "contact": {"dept": "○○과", "people": [["담당자", "사무관", "○○○", "(044-202-0000)"]]}}
    base.update(kw)
    return base


def test_draft_lead_and_order():
    r = SV.draft_press_structure(F(background="이용자가 늘어 안내가 필요하다.", points=["대상은 ○○ 20종이다."], plan="12월에 결과를 공개할 계획이다.",
                                   quote={"speaker": "○○○ 과학기술정보통신부 장관", "text": ["“빠르게 넓히겠다”", "현장 의견을 듣겠다"]}))
    b = r["structure"]["body"]
    assert [x["type"] for x in b] == ["p"] * 5
    assert b[0]["text"] == "과학기술정보통신부(장관 ○○○)는 11월 2일(월)부터 ○○ 서비스를 시범 운영한다."
    assert [x["text"] for x in b[1:4]] == ["이용자가 늘어 안내가 필요하다.", "대상은 ○○ 20종이다.", "12월에 결과를 공개할 계획이다."]
    assert b[4]["text"] == "○○○ 과학기술정보통신부 장관은 “빠르게 넓히겠다.”라며, “현장 의견을 듣겠다.”라고 말했다."
    assert "kind" not in r["structure"] and r["structure"]["appendix"] == []
    assert r["missing"] == []


def test_draft_lead_variants():
    s = SV.draft_press_structure(F(when="", what="○○ 서비스를 시범 운영한다."))["structure"]
    assert s["body"][0]["text"] == "과학기술정보통신부(장관 ○○○)는 ○○ 서비스를 시범 운영한다."
    s = SV.draft_press_structure(F(lead="  직접 쓴 리드 문장이다.  "))["structure"]
    assert s["body"][0]["text"] == "직접 쓴 리드 문장이다."
    r = SV.draft_press_structure(F(what="○○ 서비스 시범 운영"))
    assert any("what" in x for x in r["missing"])
    r = SV.draft_press_structure(F(who="", lead=""))
    assert any("lead" in x for x in r["missing"]) and r["structure"]["body"] == []


def test_draft_quote_single_and_verb():
    r = SV.draft_press_structure(F(quote={"speaker": "○○○ 행정안전부 차관", "text": "꼼꼼히 살피겠다", "verb": "강조했다."}))
    assert r["structure"]["body"][-1]["text"] == "○○○ 행정안전부 차관은 “꼼꼼히 살피겠다.”라고 강조했다."
    r = SV.draft_press_structure(F(quote={"speaker": "", "text": "말"}))
    assert all("“" not in x["text"] for x in r["structure"]["body"])


def test_draft_points_dict_and_box_ministry():
    r = SV.draft_press_structure(F(ministry="국토교통부", who="국토교통부(장관 ○○○)",
                                   points=[{"text": "핵심 내용이다.", "details": ["세부 하나", "세부 둘"], "note": "용어 풀이"}]))
    b = r["structure"]["body"]
    assert [x["type"] for x in b] == ["l1", "l1", "l2", "l2", "note"]
    assert b[0]["text"].startswith("국토교통부(장관 ○○○)는 ")
    assert r["ministry"] == "국토교통부"


def test_draft_ministry_argument_wins_and_invalid():
    assert SV.draft_press_structure(F(), MOIS)["ministry"] == MOIS
    with pytest.raises(ValueError): SV.draft_press_structure(F(ministry="없는부"))
    with pytest.raises(ValueError): SV.draft_press_structure(F(kind="공지"))


def test_draft_accepts_json_string():
    assert SV.draft_press_structure(json.dumps(F(), ensure_ascii=False))["structure"]["title"] == "○○ 서비스 시범 운영"


def test_draft_title_subtitles():
    r = SV.draft_press_structure(F(headline=" 제목이다. ", subtitles=["- 하나 -", "— 둘", "셋", "  "]))
    s = r["structure"]
    assert s["title"] == "제목이다" and s["subtitles"] == ["하나", "둘"]
    assert any("부제" in w for w in r["warnings"])
    r = SV.draft_press_structure(F(headline="", release=""))
    assert any(x.startswith("headline") for x in r["missing"]) and any(x.startswith("release") for x in r["missing"])


def test_draft_numbers_and_appendix():
    r = SV.draft_press_structure(F(appendix=[{"heading": "추진 일정", "items": ["11월 시범", "12월 확대"]},
                                             {"heading": "예산", "rows": [["구분", "금액"], ["구축", "2억 원"]]}],
                                   numbers=[{"item": "접수", "value": 128, "unit": "건"}, {"item": "처리율", "value": "91.4", "unit": ""}]))
    ap = r["structure"]["appendix"]
    assert [a["title"] for a in ap] == ["참고 1", "참고 2", "참고 3"]
    assert ap[0] == {"title": "참고 1", "heading": "추진 일정", "body": [{"type": "l1", "text": "11월 시범"}, {"type": "l1", "text": "12월 확대"}]}
    assert ap[1]["body"] == [{"type": "caption", "text": "예산"}, {"type": "table", "rows": [["구분", "금액"], ["구축", "2억 원"]]}]
    assert ap[2]["heading"] == "주요 수치"
    assert ap[2]["body"][1]["rows"] == [["구분", "수치"], ["접수", "128건"], ["처리율", "91.4"]]
    assert any("numbers[1]" in w and "단위" in w for w in r["warnings"])
    r = SV.draft_press_structure(F(numbers=[{"item": "접수", "value": "128", "unit": "건", "basis": "10. 21. 기준"}], numbers_heading="운영 현황"))
    assert r["structure"]["appendix"][0]["body"][1]["rows"] == [["구분", "수치", "기준·비교"], ["접수", "128건", "10. 21. 기준"]]
    assert r["structure"]["appendix"][0]["heading"] == "운영 현황"


def test_draft_contact_conversion():
    r = SV.draft_press_structure(F(contact={"dept": "○○과", "people": [{"role": "책임자", "title": "과장", "name": "○○○", "phone": "044-202-0001"}, ["담당자", "주무관", "○○○", "(044-202-0002)"]]}))
    assert r["structure"]["contact"] == {"dept": "○○과", "people": [["책임자", "과장", "○○○", "(044-202-0001)"], ["담당자", "주무관", "○○○", "(044-202-0002)"]]}
    r = SV.draft_press_structure(F(contact=None))
    assert r["structure"]["contact"] == {"dept": "", "people": []} and any(x.startswith("contact") for x in r["missing"])


@pytest.mark.parametrize("kind", ["해명자료", "설명자료"])
def test_draft_explanation_kinds(kind):
    r = SV.draft_press_structure(F(kind=kind, issue="○○일보는 10월 27일 ○○ 사업이 중단됐다고 보도했습니다.", position="○○ 사업은 중단되지 않았습니다.",
                                   grounds=["10월에도 예정대로 집행하고 있습니다.", "11월 계획도 그대로입니다."]))
    s = r["structure"]
    assert s["kind"] == kind
    assert [b["text"] for b in s["body"]] == ["○○일보는 10월 27일 ○○ 사업이 중단됐다고 보도했습니다.", "○○ 사업은 중단되지 않았습니다.",
                                             "10월에도 예정대로 집행하고 있습니다.", "11월 계획도 그대로입니다."]
    assert not any("리드" in w for w in r["warnings"])
    r = SV.draft_press_structure(F(kind=kind))
    assert any(x.startswith("issue") for x in r["missing"]) and any(x.startswith("position") for x in r["missing"])


def test_draft_reference_kind_label(tmp_path):
    r = SV.draft_press_structure(F(kind="보도참고자료"))
    assert r["structure"]["kind"] == "보도참고자료"
    b = SV.build_document(r["structure"], "press_release", MSIT, str(tmp_path / "k.hwpx"))
    assert "보도참고자료" in zipfile.ZipFile(b["hwpx"]).read("Contents/section0.xml").decode("utf-8")


def test_draft_invents_no_numbers():
    e = EX[MSIT]
    r = SV.draft_press_structure(e["facts"])
    st = copy.deepcopy(r["structure"])
    for ap in st["appendix"]: ap.pop("title")   # '참고 N'은 붙이는 고정 말
    for b in st["body"] + [x for ap in st["appendix"] for x in ap["body"]]: b.pop("type")   # 'l2' 같은 블록 종류 이름 제외
    got = set(re.findall(r"\d+", json.dumps(st, ensure_ascii=False)))
    src = set(re.findall(r"\d+", json.dumps(e["facts"], ensure_ascii=False)))
    assert got <= src


# ── 작성 점검(E절) ──
GOOD = {"release": "2026. 11. 2.(월) 조간", "title": "○○ 서비스 시범 운영", "subtitles": ["5곳에서 먼저 운영"],
        "body": [{"type": "p", "text": "과학기술정보통신부(장관 ○○○)는 11월 2일(월)부터 인공지능(AI) 안내 서비스를 시범 운영한다."},
                 {"type": "p", "text": "AI 안내는 누리집에서 받을 수 있고, 이용자는 1,240명이다."},
                 {"type": "p", "text": "과학기술정보통신부는 12월에 결과를 공개할 계획이다."},
                 {"type": "p", "text": "○○○ 과학기술정보통신부 장관은 “빠르게 넓히겠다.”라며, “현장 의견을 듣겠다.”라고 말했다."}],
        "appendix": [], "contact": {"dept": "○○과", "people": []}}


def mod(**kw):
    s = copy.deepcopy(GOOD)
    for k, v in kw.items():
        if k.startswith("b"): s["body"][int(k[1:])]["text"] = v
        else: s[k] = v
    return s


def test_good_has_no_writing_warnings():
    assert writing(W(GOOD)) == []
    assert SV.check_structure(GOOD, "press_release", ministry=MSIT)["ok"]


@pytest.mark.parametrize("name,s,keys", [
    ("E1 누가", mod(b0="11월 2일(월)부터 인공지능(AI) 안내 서비스를 시범 운영하는 곳이 늘어난다."), ["리드", "누가"]),
    ("E2 언제", mod(b0="과학기술정보통신부(장관 ○○○)는 인공지능(AI) 안내 서비스를 시범 운영한다."), ["리드", "언제"]),
    ("E3 완결", mod(b0="과학기술정보통신부(장관 ○○○)는 11월 2일(월)부터 인공지능(AI) 안내 서비스 시범 운영"), ["리드", "완결"]),
    ("E4 길이", mod(b0="과학기술정보통신부(장관 ○○○)는 11월 2일(월)부터 인공지능(AI) 안내 서비스를 " + "가나다라마바사 " * 22 + "시범 운영한다."), ["리드가 깁니다"]),
    ("E5 리드 인용", mod(b0="과학기술정보통신부(장관 ○○○)는 11월 2일(월)부터 “인공지능(AI) 안내를 시작한다”라고 밝혔다."), ["리드", "인용"]),
    ("E7 과장", mod(title="세계 최초 ○○ 서비스 시범 운영"), ["제목", "최초", "근거"]),
    ("E8 마침표", mod(title="○○ 서비스 시범 운영."), ["제목", "마침표"]),
    ("E9 부제", mod(subtitles=["하나", "둘", "셋"]), ["부제", "2개"]),
    ("E10 단위", mod(b1="AI 안내는 누리집에서 받을 수 있고, 이용자는 1,240, 지난달보다 늘었다."), ["단위", "1,240"]),
    ("E11 띄어", mod(b1="AI 안내는 누리집에서 받을 수 있고, 예산은 76억원이다."), ["띄어"]),
    ("E12 외국 먼저", mod(b1="AI 안내는 Reshoring(리쇼어링) 기업도 받을 수 있다."), ["한글을 먼저"]),
    ("E13 약어", mod(b0="과학기술정보통신부(장관 ○○○)는 11월 2일(월)부터 AI 안내 서비스를 시범 운영한다."), ["AI", "한글"]),
    ("E14 쉬운 말", mod(b2="과학기술정보통신부는 향후 결과를 공개할 계획이다."), ["'향후' → '앞으로'"]),
    ("E15 권위", mod(b2="과학기술정보통신부는 12월에 결과를 공개하라고 지시했다."), ["지시했다", "하도록 했다"]),
    ("E16 혼용", mod(b2="과학기술정보통신부는 12월에 결과를 공개할 계획입니다."), ["혼용"]),
    ("E17 명사형", mod(b2="과학기술정보통신부는 12월에 결과를 공개할 예정임."), ["명사형"]),
    ("E18 긴 문장", mod(b1="AI 안내는 누리집에서 받을 수 있고 " + "이용자의 의견을 받아 화면과 문구를 고치며 " * 5 + "1,240명이 쓴다."), ["문장이 깁니다"]),
])
def test_writing_checks_fire(name, s, keys):
    ws = writing(W(s))
    hit = [w for w in ws if all(k in w for k in keys)]
    assert hit, (name, ws)
    assert all(w.startswith("[작성] ") for w in ws)


def test_quote_position():
    s = copy.deepcopy(GOOD)
    q = s["body"].pop(3)
    s["body"].insert(1, q)   # 인용 뒤에 문장 블록 2개 → 아직 끝 세 문단 안
    assert not [w for w in writing(W(s)) if "인용" in w]
    s["body"].insert(2, {"type": "p", "text": "과학기술정보통신부는 11월에 설명회를 연다."})   # 인용 뒤 3개
    s["body"].insert(3, {"type": "note", "text": "주석은 세지 않음"})
    assert [w for w in writing(W(s)) if "인용" in w and "끝" in w]


def test_unit_check_cases():
    ok = ["2026년 10월 7일에 128건을 받았다.", "40억 원과 3.5%, 044-202-0000으로 문의한다.", "2027~2029년 임기다.",
          "5G 기지국 1,240곳이 늘었다.", "9.30(수)부터 연다.", "2026. 10. 7.(수)에 30여 명이 왔다.", "제10회 회의를 연다.", "3대 과제를 정했다."]
    for t in ok:
        s = mod(b1=t)
        assert not [w for w in writing(W(s)) if "단위" in w], t
    bad = ["확인 요청 128, 이 중 일부를 처리했다.", "처리 건수는 117이다.", "참여 기관은 모두 52."]
    for t in bad:
        assert [w for w in writing(W(mod(b1=t))) if "단위" in w], t


def test_writing_checks_limits_and_skip():
    s = mod(b1="AI 안내는 누리집에서 받고 1,240, 2,310, 3,880, 4,120, 5,000 순이다.",
            b2="과학기술정보통신부는 11, 22, 33, 44 를 공개할 계획이다.")
    assert len([w for w in writing(W(s)) if "단위" in w]) <= 3
    assert len([w for w in writing(W(mod(b1="AI 안내는 1,240, 2,310 순이다."))) if "단위" in w]) == 1   # 블록마다 1개
    ex = mod(b0="보도 내용은 사실과 다릅니다.", kind="해명자료")
    assert not [w for w in writing(W(ex)) if "리드" in w]
    # 보고서에는 작성 점검을 하지 않는다
    rep = {"title": "○○ 계획", "body": [{"type": "l1", "text": "향후 MOU 체결 추진 필요"}]}
    assert not writing(SV.check_structure(rep, "report")["warnings"])


def test_ministry_short_name_counts_as_who():
    s = mod(b0="과기정통부는 11월 2일(월)부터 인공지능(AI) 안내 서비스를 시범 운영한다.")
    assert not [w for w in writing(W(s)) if "누가" in w]


def test_check_positional_compat_and_build_passes_ministry(tmp_path):
    assert SV.check_structure(GOOD, "press_release", "standard")["doc_type"] == "press_release"
    s = mod(b0="11월 2일(월)부터 인공지능(AI) 안내 서비스를 시범 운영하는 곳이 늘어난다.")
    b = SV.build_document(s, "press_release", MSIT, str(tmp_path / "w.hwpx"))
    assert Path(b["hwpx"]).exists() and [w for w in b["warnings"] if "누가" in w]
    assert writing(SV.build_document(GOOD, "press_release", MSIT, str(tmp_path / "g.hwpx"))["warnings"]) == []


# ── F0: 머리 이름·담당 부서·가림 표기 ──
@pytest.mark.parametrize("m", [MSIT, "공정거래위원회", "국세청", MOIS])
def test_cover_label_is_press_release_by_default(m, tmp_path):
    s = copy.deepcopy(GOOD)
    b = SV.build_document(s, "press_release", m, str(tmp_path / "c.hwpx"))
    xml = zipfile.ZipFile(b["hwpx"]).read("Contents/section0.xml").decode("utf-8")
    assert ">보도자료<" in xml and "보도설명자료" not in xml and "보도참고자료" not in xml
    s["kind"] = "보도참고자료"
    b = SV.build_document(s, "press_release", m, str(tmp_path / "d.hwpx"))
    assert ">보도참고자료<" in zipfile.ZipFile(b["hwpx"]).read("Contents/section0.xml").decode("utf-8")


def test_contact_dept_kept_with_placeholder_people(tmp_path):
    b = SV.build_document(EX[MOIS]["structure"], "press_release", MOIS, str(tmp_path / "e.hwpx"))
    xml = zipfile.ZipFile(b["hwpx"]).read("Contents/section0.xml").decode("utf-8")
    assert EX[MOIS]["structure"]["contact"]["dept"] in xml and "044-000-0000" in xml


def test_masked_name_not_stripped():
    s = copy.deepcopy(GOOD)
    s["body"][3]["text"] = "○○○ 과학기술정보통신부 장관은 “빠르게 넓히겠다.”라고 말했다."
    s["body"].append({"type": "l2", "text": "ㅇ 기호는 지운다"})
    r = SV.check_structure(s, "press_release", ministry=MSIT)
    _, n, _ = SV.check(s, "press_release", "standard", MSIT)
    assert n["body"][3]["text"].startswith("○○○ 과학기술정보통신부")
    assert n["body"][4]["text"] == "기호는 지운다"
    assert not any("body[3]" in w and "기호" in w for w in r["warnings"])


# ── H: 리뷰 보완 ──
def test_guide_section_once():
    assert SV.get_writing_guide("press_release", MSIT)["guide"].count("[보도자료 작성 방법") == 1
    assert SV.get_writing_guide("auto")["guide"].count("[보도자료 작성 방법") == 1


def test_who_check_without_ministry():
    s = mod(b0="11월 2일(월)부터 인공지능(AI) 안내 서비스를 시범 운영하는 곳이 늘어난다.")
    ws = writing(SV.check_structure(s, "press_release")["warnings"])
    assert "[작성] 리드(첫 문단) 앞부분에 '누가'(기관·기관장)가 없음 — '○○부(장관 ○○○)는 …'처럼 시작 (G20 39)" in ws
    assert not [w for w in writing(SV.check_structure(GOOD, "press_release")["warnings"]) if "누가" in w]


def test_exact_messages():
    ws = writing(W(mod(b1="AI 안내는 누리집에서 받을 수 있고, 예산은 76억원이다.")))
    assert "[작성] 단위는 띄어 쓴다: '76억원' → '76억 원' (G11 32~33, H22 66)" in ws
    ws = writing(W(mod(b0="과학기술정보통신부(장관 ○○○)는 11월 2일(월)부터 AI 안내 서비스를 시범 운영한다.")))
    assert "[작성] 'AI' 첫 등장에 한글 풀이 없음 — '인공지능(AI)'처럼 한글(약어)로 (G20 63)" in ws
    ws = writing(W(mod(b1="AI 안내는 누리집에서 받을 수 있고, 이용자는 1,240, 지난달보다 늘었다.")))
    assert any(w.startswith("[작성] 숫자 뒤 단위 없음: '") and "1,240" in w and w.endswith("— 건·명·원·% 등 단위를 붙인다 (G11 32, 말뭉치)") for w in ws)
    ws = writing(W(mod(b2="과학기술정보통신부는 12월에 결과를 공개할 예정임.")))
    assert "[작성] 명사형 종결 — '-다'로 끝낸다: '…결과를 공개할 예정임.' (G20 55)" in ws
    ws = writing(W(mod(title="세계 최초 ○○ 서비스 시범 운영.")))
    assert "[작성] 제목의 '최초' — 본문에 비교 기준·근거가 있는지 확인 (말뭉치·G20 33)" in ws
    assert "[작성] 제목 끝에 마침표를 찍지 않는다" in ws
    lead = "과학기술정보통신부(장관 ○○○)는 11월 2일(월)부터 인공지능(AI) 안내 서비스를 " + "가나다라마바사 " * 22 + "시범 운영한다."
    assert f"[작성] 리드가 깁니다({len(lead)}자) — 누가·언제·무엇만 한 문장으로, 세부는 다음 문단 (G20 38)" in writing(W(mod(b0=lead)))


def test_unit_warning_per_block():
    s = mod(b1="AI 안내는 누리집에서 받고 이용자는 1,240, 지난달보다 늘었다.", b2="과학기술정보통신부는 응답 117, 이 중 일부를 공개할 계획이다.")
    assert len([w for w in writing(W(s)) if w.startswith("[작성] 숫자 뒤 단위 없음")]) == 2


def test_replace_words_no_cap():
    s = mod(b2="과학기술정보통신부는 향후 금년 매뉴얼과 로드맵 대신 허브와 클러스터 계획을 공개할 계획이다.")
    ws = writing(W(s))
    for k in ("향후", "금년", "매뉴얼", "허브", "클러스터"):
        assert any(w.startswith(f"[작성] '{k}' → ") for w in ws), k


def test_josa_latin_s_and_draft_schema():
    assert SV._josa("AWS") == "는" and SV._josa("CJ ENM") == "은"
    tools = {t.name: t for t in asyncio.run(SV.mcp.list_tools())}
    sch = json.dumps(tools["draft_press_structure"].input_schema, ensure_ascii=False)
    assert '"object"' in sch and '"string"' in sch
    r = SV.draft_press_structure(F(quote={"speaker": "○○○ 장관", "text": "하겠다", "verb": ""}, points=[{"text": "핵심이다.", "note": "  풀이  "}]))
    b = r["structure"]["body"]
    assert b[-1]["text"] == "○○○ 장관은 “하겠다.”라고 말했다." and {"type": "note", "text": "풀이"} in b
