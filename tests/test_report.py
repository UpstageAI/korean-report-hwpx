"""보고서 모드: 가상 원고(sample_report)로 보고서 규칙 기관 42곳 + 공통 생성 → 열림·정화(실명·전화·원본 문장·그림 0건)·서식 수치=규칙값."""
import re, zipfile

import pytest

import compose as C
import report as R
from hwpx_doc import Hwpx, balanced
from sample_report import SAMPLE_REPORT as S
from test_sanitize import PHONE, ALLOWED_PHONES, NAME_TITLE

ORGS = R.ministries() + [""]   # "" = 기관 미지정(공통 규칙)
LABELS = {"붙임 1", "[붙임 1]", "< 붙임 1 >", "□", "ㅇ", "○", "◦", "❍", "-", "*", "※", "　"}


def _allowed(doc):
    out = [doc["title"], doc["date"], doc["dept"]]
    def blocks(bs):
        for b in bs:
            if "text" in b:
                t = re.sub(r"\*\*(.+?)\*\*", r"\1", b["text"]); out.append(t); out.append(f"< {t} >")
            for r in b.get("rows", []): out.extend(r)
            out.extend(b.get("lines", []))
    blocks(doc["body"])
    for a in doc["appendix"]: out += [a["title"], a["heading"]]; blocks(a["body"])
    return out


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    d = tmp_path_factory.mktemp("rep"); res = {}
    for org in ORGS:
        dst = d / f"{org or '공통'}.hwpx"; c = R.compose(org, S, dst)
        z = zipfile.ZipFile(dst)
        res[org] = (c, z, z.read("Contents/section0.xml").decode(), z.read("Contents/header.xml").decode(), z.read("Preview/PrvText.txt").decode())
    return res


def test_counts(built):
    assert len(R.ministries()) == 42 and len(built) == 43


@pytest.mark.parametrize("org", ORGS)
def test_clean(built, org):
    c, z, sec, head, prv = built[org]
    assert not [n for n in z.namelist() if n.startswith("BinData/")] and "binaryItemIDRef" not in sec
    text = Hwpx.text(sec, True)
    bad = [m.group(0) for src in (text, prv) for m in PHONE.finditer(src) if re.sub(r"[()\s]", "", m.group(0)) not in ALLOWED_PHONES]
    assert not bad, bad
    for raw in re.findall(r"<hp:t>(.*?)</hp:t>", sec, re.S) + prv.splitlines():
        t = Hwpx.text(f"<hp:t>{raw}</hp:t>").strip()
        for m in NAME_TITLE.finditer(t): assert "○" in m.group(1), (org, t)
        if not t or t in LABELS: continue
        if any(t in a for a in _allowed(S)): continue
        if org and t == "  ".join(x for x in (S["date"], org, S["dept"]) if x): continue
        if not org and t == "  ".join((S["date"], S["dept"])): continue
        raise AssertionError(f"{org}: 원고에 없는 글 '{t}'")
    # 보고서에는 보도자료 머리·담당 표가 없음, 붙임 쪽은 새 쪽
    assert "보도자료" not in text and "책임자" not in text and "보도시점" not in text
    assert "붙임 1" in text and 'pageBreak="1"' in sec


@pytest.mark.parametrize("org", ORGS)
def test_format_matches_report_rules(built, org):
    c, _, sec, head, _ = built[org]
    fonts = dict(re.findall(r'<hh:font id="(\d+)" face="([^"]+)"', re.search(r'<hh:fontface lang="HANGUL".*?</hh:fontface>', head, re.S).group(0)))
    chars = {m.group(1): m.group(0) for m in re.finditer(r'<hh:charPr id="(\d+)".*?</hh:charPr>', head, re.S)}
    tops = [p for *_, p in balanced(sec, "p")]
    pos = {re.search(r'<hp:p id="(\d+)"', p).group(1): i for i, p in enumerate(tops)}
    rules = R.load_rules(org); n = 0
    for pno, it in c.items.items():
        p = re.sub(r"<hp:rect\b.*?</hp:rect>", "", tops[pos[pno]], flags=re.S); L_ = c.level(it["lv"])
        cid = max(re.findall(r'<hp:run charPrIDRef="(\d+)"><hp:t>(.*?)</hp:t>', p), key=lambda r: len(r[1]))[0]
        s = chars[cid]
        assert fonts[re.search(r'<hh:fontRef hangul="(\d+)"', s).group(1)] == L_["font"]
        assert int(re.search(r'height="(\d+)"', s).group(1)) == int(L_["pt"] * 100)
        assert it["text"].startswith(" " * L_["lead"] + L_["mark"]), (org, it)
        rv = rules["levels"].get(it["lv"]) or rules["_base"]["levels"][it["lv"]]
        assert L_["mark"] == rv["mark"]
        n += 1
    assert n >= 20
    # 표 머리 = 규칙 표 머리 배경색, 붙임 라벨 칸 = 규칙 상자 색
    assert rules["table_head"]["fill"] in head and rules["title_box"]["fill"] in head


def test_unlisted_org_uses_common_with_name(tmp_path):
    org = next(o for o in C.ministries() if o not in R.ministries())
    c = R.compose(org, S, tmp_path / "x.hwpx")
    assert c.rule_key == R.COMMON and org in Hwpx.text(zipfile.ZipFile(tmp_path / "x.hwpx").read("Contents/section0.xml").decode(), True)


# ── 14차 빈 문단 제거 회귀 테스트 (세 서식 공통) ──

def _remove_tables(sec_xml):
    """section0.xml에서 표(<hp:tbl>...</hp:tbl>) 제거."""
    import re
    return re.sub(r'<hp:tbl\b.*?</hp:tbl>', '', sec_xml, flags=re.S)


def _parse_paragraphs(xml):
    """HWPX section XML에서 중첩된 <hp:p>를 올바르게 처리하여 모든 문단 (start, end, content) 목록 반환.

    Stack 기반 단일 패스 파서: 모든 <hp:p ...> 여는 태그와 </hp:p> 닫는 태그의 위치를
    미리 찾아 정렬한 후, 스택으로 중첩을 추적하여 각 문단의 범위 결정.
    <hp:tc> 등 다른 요소는 무시 — <hp:p ...> 여는 태그와 </hp:p> 닫는 태그만 추적.
    """
    import re
    open_positions = []
    close_positions = []
    for m in re.finditer(r'<hp:p(\s|>)', xml):
        open_positions.append(m.start())
    for m in re.finditer(r'</hp:p>', xml):
        close_positions.append(m.start())
    all_tag_positions = sorted(open_positions + close_positions)
    stack = []
    results = []
    for tag_pos in all_tag_positions:
        is_close = tag_pos in close_positions
        if is_close:
            if stack:
                start = stack.pop()
                end = tag_pos + len('</hp:p>')
                results.append((start, end, xml[start:end]))
        else:
            stack.append(tag_pos)
    return results


def _count_empty_paras_after_first_3(sec_xml_with_tables, sec_xml_no_tables):
    """처음 4개 문단 이후 <hp:t>에 공백 아닌 글자가 없는 문단 수.
    표 셀 안 문단, 표 포함 문단(표 컨테이너), 그리고 표 뒤 5pt 빈 문단(15차 Fix)은 제외.
    15차 Fix: 표 컨테이너 문단 바로 뒤의 5pt 빈 문단(<hp:t></hp:t> 형태, <hp:t/> 없음)은 '의도된 빈 문단'이므로 제외.
    Args:
        sec_xml_with_tables: 원본 섹션 XML (표 포함)
        sec_xml_no_tables: 표 제거된 섹션 XML
    """
    import re

    # 원본 문단 파싱 (stack 기반)
    orig_paras = _parse_paragraphs(sec_xml_with_tables)

    # 표 셀 안의 문단: <hp:tc>...</hp:tc> 범위 내 <hp:p> (원본 위치 기준)
    table_cell_ranges = []
    for m in re.finditer(r'<hp:tc[^>]*>(.*?)</hp:tc>', sec_xml_with_tables, re.S):
        tc_start = m.start()
        tc_end = m.end()
        # 셀 안의 문단 찾기 (중첩 처리 없이 단순 검색)
        pos = tc_start
        while pos < tc_end:
            p_start = sec_xml_with_tables.find('<hp:p', pos)
            if p_start < 0 or p_start >= tc_end:
                break
            gt = sec_xml_with_tables.find('>', p_start)
            if gt < 0 or gt > tc_end:
                break
            # 셀 안 문단은 <hp:tc> 안에서 끝나므로 p_end는 tc_end 이내
            p_end_m = re.search(r'</hp:p>', sec_xml_with_tables[gt + 1:tc_end])
            if p_end_m:
                p_end = gt + 1 + p_end_m.start() + len('</hp:p>')
                table_cell_ranges.append((p_start, p_end))
            pos = gt + 1

    # 표 컨테이너 문단 (원본에서 <hp:tbl>을 직접 포함하는 문단)
    orig_table_container_starts = set()
    for start, end, content in orig_paras:
        if '<hp:tbl' in content:
            orig_table_container_starts.add(start)

    # 표 제거 후 문단 파싱 (stack 기반)
    paras = _parse_paragraphs(sec_xml_no_tables)

    def is_in_table_cell(para_start):
        """문단이 표 셀 안에 있는지 확인."""
        for tc_start, tc_end in table_cell_ranges:
            if tc_start <= para_start < tc_end:
                return True
        return False

    def is_near_original_table_container(para_start):
        """문단이 원본 표 컨테이너 위치 근처에 있는지 확인 (허용 오차 3000 문자)."""
        for orig_pos in orig_table_container_starts:
            if abs(para_start - orig_pos) < 3000:
                return True
        return False

    def is_table_container_by_content(para_content):
        """표 제거 후 표 컨테이너 문단인지 content 기반으로 확인."""
        return '<hp:t/>' in para_content and '<hp:t></hp:t>' not in para_content

    # 처음 4개 "실질적" 문단 찾기
    first_group_count = 0
    first_group_indices = set()
    for i, (s, e, c) in enumerate(paras):
        if is_in_table_cell(s):
            continue
        if is_near_original_table_container(s):
            continue
        first_group_indices.add(i)
        first_group_count += 1
        if first_group_count >= 4:
            break

    # 표 컨테이너 문단 인덱스 식별
    table_container_indices = set()
    for i, (s, e, c) in enumerate(paras):
        if i in first_group_indices:
            continue
        if is_in_table_cell(s):
            continue
        if is_near_original_table_container(s):
            continue
        if is_table_container_by_content(c):
            table_container_indices.add(i)

    # 표 컨테이너 뒤 15차 gap 문단 인덱스 식별
    gap_indices = set()
    for tc_idx in table_container_indices:
        next_idx = tc_idx + 1
        if next_idx < len(paras):
            ns, ne, nc = paras[next_idx]
            if is_table_container_by_content(nc):
                continue
            texts = re.findall(r'<hp:t>(.*?)</hp:t>', nc, re.S)
            if not any(t.strip() for t in texts):
                gap_indices.add(next_idx)

    empty_count = 0
    for i, (s, e, c) in enumerate(paras):
        if i in first_group_indices:
            continue
        if is_in_table_cell(s):
            continue
        if is_near_original_table_container(s):
            continue
        if i in table_container_indices:
            continue
        if i in gap_indices:
            continue
        texts = re.findall(r'<hp:t>(.*?)</hp:t>', c, re.S)
        has_non_empty = any(t.strip() for t in texts)
        if not has_non_empty:
            empty_count += 1
    return empty_count


class TestReportEmptyParagraphRegression15:
    """15차 회귀 테스트: SAMPLE_REPORT를 세 서식으로 생성 →
    - 표 뒤 5pt 빈 문단 외 빈 문단 0개
    - 표 뒤 5pt 빈 문단 존재 확인 (본문에 표가 있는 경우)"""

    def _count_gap_paras(self, sec_xml, head_xml):
        """15차 Fix: 표 뒤 5pt 빈 문단 수 계산.
        원본 section0.xml의 <hp:p> 목록을 순서대로 보고,
        <hp:tbl>을 포함한 문단 바로 다음 문단이 텍스트 없는 문단이고
        그 문단의 charPr 높이가 500(5pt)이면 gap_count += 1.
        charPr 높이는 header.xml의 <hh:charPr height="...">로 확인한다."""
        import re
        charPr_map = {}
        for m in re.finditer(r'<hh:charPr id="(\d+)"[^>]*height="(\d+)"', head_xml):
            charPr_map[m.group(1)] = int(m.group(2))

        paras = _parse_paragraphs(sec_xml)
        gap_count = 0
        for i, (_s, _e, content) in enumerate(paras):
            if '<hp:tbl' not in content:
                continue
            if i + 1 >= len(paras):
                continue
            ns, ne, nc = paras[i + 1]
            texts = re.findall(r'<hp:t>(.*?)</hp:t>', nc, re.S)
            if any(t.strip() for t in texts):
                continue
            pid_ref = re.search(r'charPrIDRef="(\d+)"', nc)
            if not pid_ref:
                continue
            h = charPr_map.get(pid_ref.group(1))
            if h == 500:
                gap_count += 1
        return gap_count

    def _check_all_styles(self, tmp_path):
        """세 서식(standard, simplified, internal) 모두 검증."""
        from sample_report import SAMPLE_REPORT
        results = {}
        for style in ("standard", "simplified"):
            for report_kind in ("standard", "internal"):
                if style == "standard" and report_kind == "internal":
                    continue
                dst = tmp_path / f"sample_{style}_{report_kind}.hwpx"
                kwargs = {"style": style}
                if report_kind != "standard":
                    kwargs["report_kind"] = report_kind
                R.compose("", SAMPLE_REPORT, dst, **kwargs)
                sec = zipfile.ZipFile(dst).read("Contents/section0.xml").decode()
                head = zipfile.ZipFile(dst).read("Contents/header.xml").decode()
                sec_no_tbl = _remove_tables(sec)
                empty_count = _count_empty_paras_after_first_3(sec, sec_no_tbl)
                gap_count = self._count_gap_paras(sec, head)
                key = f"{style}_{report_kind}"
                results[key] = (empty_count, gap_count)
                print(f"  [{key}] 빈 문단(갭 제외): {empty_count}개, 표 뒤 5pt 갭: {gap_count}개")
        return results

    def test_standard_no_unexpected_empty_paras(self, tmp_path):
        """표준 보고서: 표 뒤 5pt 갭 외 빈 문단 0개."""
        from sample_report import SAMPLE_REPORT
        dst = tmp_path / "standard.hwpx"
        R.compose("", SAMPLE_REPORT, dst, style="standard")
        sec = zipfile.ZipFile(dst).read("Contents/section0.xml").decode()
        head = zipfile.ZipFile(dst).read("Contents/header.xml").decode()
        sec_no_tbl = _remove_tables(sec)
        empty_count = _count_empty_paras_after_first_3(sec, sec_no_tbl)
        gap_count = self._count_gap_paras(sec, head)
        assert empty_count == 0, f"표준 보고서 빈 문단 {empty_count}개 발견 (기대: 0)"
        assert gap_count >= 1, f"표준 보고서 표 뒤 5pt 갭 없음 (기대: >=1, 실제: {gap_count})"

    def test_simplified_no_unexpected_empty_paras(self, tmp_path):
        """간소화 보고서: 표 뒤 5pt 갭 외 빈 문단 0개."""
        from sample_report import SAMPLE_REPORT
        dst = tmp_path / "simplified.hwpx"
        R.compose("", SAMPLE_REPORT, dst, style="simplified")
        sec = zipfile.ZipFile(dst).read("Contents/section0.xml").decode()
        head = zipfile.ZipFile(dst).read("Contents/header.xml").decode()
        sec_no_tbl = _remove_tables(sec)
        empty_count = _count_empty_paras_after_first_3(sec, sec_no_tbl)
        gap_count = self._count_gap_paras(sec, head)
        assert empty_count == 0, f"간소화 보고서 빈 문단 {empty_count}개 발견 (기대: 0)"
        assert gap_count >= 1, f"간소화 보고서 표 뒤 5pt 갭 없음 (기대: >=1, 실제: {gap_count})"

    def test_internal_no_unexpected_empty_paras(self, tmp_path):
        """내부결재 보고서: 표 뒤 5pt 갭 외 빈 문단 0개."""
        from sample_report import SAMPLE_REPORT
        dst = tmp_path / "internal.hwpx"
        R.compose("", SAMPLE_REPORT, dst, style="standard", report_kind="internal")
        sec = zipfile.ZipFile(dst).read("Contents/section0.xml").decode()
        head = zipfile.ZipFile(dst).read("Contents/header.xml").decode()
        sec_no_tbl = _remove_tables(sec)
        empty_count = _count_empty_paras_after_first_3(sec, sec_no_tbl)
        gap_count = self._count_gap_paras(sec, head)
        assert empty_count == 0, f"내부결재 보고서 빈 문단 {empty_count}개 발견 (기대: 0)"
        assert gap_count >= 1, f"내부결재 보고서 표 뒤 5pt 갭 없음 (기대: >=1, 실제: {gap_count})"

    def test_all_styles_comprehensive(self, tmp_path):
        """세 서식 모두 검증 + 처음 10개 문단 정보 출력."""
        from sample_report import SAMPLE_REPORT
        print("\n" + "=" * 70)
        print("15차 표 뒤 5pt 빈 문단 검증: 세 서식 SAMPLE_REPORT 생성 결과")
        print("=" * 70)

        for style in ("standard", "simplified"):
            for report_kind in ("standard", "internal"):
                if style == "standard" and report_kind == "internal":
                    continue
                dst = tmp_path / f"sample_{style}_{report_kind}.hwpx"
                kwargs = {"style": style}
                if report_kind != "standard":
                    kwargs["report_kind"] = report_kind
                R.compose("", SAMPLE_REPORT, dst, **kwargs)
                sec = zipfile.ZipFile(dst).read("Contents/section0.xml").decode()
                head = zipfile.ZipFile(dst).read("Contents/header.xml").decode()
                sec_no_tbl = _remove_tables(sec)

                empty_count = _count_empty_paras_after_first_3(sec, sec_no_tbl)
                gap_count = self._count_gap_paras(sec, head)
                key = f"{style}_{report_kind}"
                print(f"\n[{key}]")
                print(f"  빈 문단(갭 제외): {empty_count}개")
                print(f"  표 뒤 5pt 갭 문단: {gap_count}개")

                # 처음 10개 문단 정보
                print(f"  처음 10개 문단 (텍스트 6자, prev, 줄간격%):")
                table_cell_p_ids = set()
                for m in re.finditer(r'<hp:tc[^>]*>(.*?)</hp:tc>', sec, re.S):
                    for pm in re.finditer(r'<hp:p id="(\d+)"[^>]*>', m.group(1)):
                        table_cell_p_ids.add(pm.group(1))

                paraPr_map = dict(re.findall(r'<hh:paraPr id="(\d+)"[^>]*>(.*?)</hh:paraPr>', head, re.S))

                all_paras = _parse_paragraphs(sec)
                count = 0
                for _, _, content in all_paras:
                    if count >= 10:
                        break
                    p_id_m = re.search(r'id="(\d+)"', content)
                    p_id = p_id_m.group(1) if p_id_m else None
                    if p_id and p_id in table_cell_p_ids:
                        continue
                    texts = re.findall(r'<hp:t>(.*?)</hp:t>', content, re.S)
                    text_preview = ''.join(texts)[:6].replace('\u00a0', ' ').strip()
                    pid_ref = re.search(r'paraPrIDRef="(\d+)"', content)
                    prev_val = '0'
                    line_val = '0'
                    if pid_ref:
                        pid = pid_ref.group(1)
                        pxml = paraPr_map.get(pid, "")
                        pm_prev = re.search(r'<hc:prev value="(-?\d+)"', pxml)
                        prev_val = pm_prev.group(1) if pm_prev else '0'
                        pm_line = re.search(r'lineSpacing type="PERCENT" value="(-?\d+)"', pxml)
                        line_val = pm_line.group(1) if pm_line else '0'
                    print(f"    [{count}] text='{text_preview}' prev={prev_val} line={line_val}%")
                    count += 1

                assert empty_count == 0, f"[{key}] 빈 문단 {empty_count}개 발견 (기대: 0)"

        print("\n" + "=" * 70)
        print("검증 완료: 세 서식 모두 표 뒤 5pt 갭 외 빈 문단 없음")
        print("=" * 70)
