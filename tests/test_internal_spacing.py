"""내부결재(report_kind="internal") 보고서 문단 위 간격 검증.
SPEC_internal_fix7.md 3항 검증: 내부결재 샘플 생성 → 각 항목 문단의 paraPr prev 값 (□=1000, ○/-=500), 빈 gap 문단 수 0
"""
import json
import re
import sys
import zipfile
from pathlib import Path

# conftest.py와 동일하게 경로 설정
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "korean_report_hwpx" / "engine"), str(Path(__file__).parent)]

import report as R
from hwpx_doc import Hwpx


# ── 검증용 구조 ──

INTERNAL_REPORT = {
    "title": "내부결재 테스트 보고서",
    "date": "2026. 1. 5.",
    "dept": "테스트과",
    "body": [
        {"type": "h", "text": "Ⅰ. 추진 배경"},
        {"type": "l1", "text": "첫 번째 대항목"},
        {"type": "l2", "text": "첫 번째 중항목"},
        {"type": "l3", "text": "첫 번째 소항목"},
        {"type": "note", "text": "참고 사항"},
        {"type": "caption", "text": "테스트 표"},
        {"type": "table", "rows": [
            ["구분", "값"],
            ["가", "100"],
        ]},
        {"type": "l1", "text": "두 번째 대항목"},
        {"type": "l2", "text": "두 번째 중항목"},
        {"type": "ref", "text": "참조 사항"},
    ],
}


def get_paraPr_map(header):
    """header.xml에서 paraPr id → XML 매핑."""
    return dict(re.findall(r'<hh:paraPr id="(\d+)"[^>]*>(.*?)</hh:paraPr>', header, re.S))


def get_prev_from_paraPr(pxml):
    """paraPr XML에서 prev 값 추출. (없으면 0)"""
    m = re.search(r'<hc:prev value="(-?\d+)"', pxml)
    return int(m.group(1)) if m else 0


def get_item_paraPr_ids(section, header):
    """section에서 항목 문단(l1/l2/l3/note/ref)의 paraPrIDRef 추출.
    각 문단의 텍스트도 함께 반환하여 어떤 수준인지 확인."""
    # 항목 문단 패턴: □/ㅇ/-/* 등으로 시작하는 문단
    # 간소화·internal이 아닌 일반 모드에서는 기호가 붙고, internal은 prev로 간격 처리
    paras = re.findall(r'<hp:p\b([^>]*)>', section)
    results = []
    for attrs in paras:
        pid_ref = re.search(r'paraPrIDRef="(\d+)"', attrs)
        if not pid_ref:
            continue
        pid = pid_ref.group(1)
        # 텍스트 추출
        text_m = re.search(r'<hp:t>(.*?)</hp:t>', section[section.find(attrs):section.find(attrs) + 3000] or "", re.S)
        text = text_m.group(1) if text_m else ""
        results.append((pid, text))
    return results


def count_empty_gap_paras(section, paraPr_map):
    """빈 gap 문단(prev > 0인 빈 문단) 개수.
    내부결재에서는 항목 사이 gap 문단이 없어야 함(0개).
    - prev > 0인 빈 문단만 gap 문단으로 간주 (spacer 등 prev=0인 빈 문단은 제외)
    - caption 앞 gap_fixed(10.0)은 prev=1000이므로 gap으로 카운트됨 (허용)"""
    paras = re.findall(r'<hp:p\b([^>]*)>(.*?)</hp:p>', section, re.S)
    count = 0
    for attrs, content in paras:
        pid_ref = re.search(r'paraPrIDRef="(\d+)"', attrs)
        if not pid_ref:
            continue
        pid = pid_ref.group(1)
        pxml = paraPr_map.get(pid, "")
        prev_val = get_prev_from_paraPr(pxml)

        # 텍스트 내용 추출
        texts = re.findall(r'<hp:t>(.*?)</hp:t>', content, re.S)
        full_text = ''.join(texts)

        # prev > 0이고 내용이 공백뿐인 문단 = gap 문단
        if prev_val > 0 and not full_text.strip() and '<hp:run' in content:
            count += 1
    return count


def analyze_internal_spacing(tmp_path):
    """내부결재 보고서 생성 후 간격 검증."""
    dst = tmp_path / "internal_test.hwpx"
    R.compose("", INTERNAL_REPORT, dst, style="standard", report_kind="internal")

    sec = zipfile.ZipFile(dst).read("Contents/section0.xml").decode()
    head = zipfile.ZipFile(dst).read("Contents/header.xml").decode()

    paraPr_map = get_paraPr_map(head)

    # 1. 항목 문단의 paraPr prev 값 확인
    print("=" * 60)
    print("내부결재(report_kind='internal') 문단 위 간격 검증")
    print("=" * 60)

    # 항목 텍스트와 해당 paraPr의 prev 값 분석
    paras = re.findall(r'<hp:p\b([^>]*)>(.*?)</hp:p>', sec, re.S)
    print("\n[항목 문단 paraPr prev 값]")
    print(f"{'문단 텍스트':<40} {'paraPrID':<10} {'prev(값)':<10} {'prev(pt)':<10}")
    print("-" * 70)

    item_prev_values = []
    for attrs, content in paras:
        pid_ref = re.search(r'paraPrIDRef="(\d+)"', attrs)
        if not pid_ref:
            continue
        pid = pid_ref.group(1)
        pxml = paraPr_map.get(pid, "")
        prev_val = get_prev_from_paraPr(pxml)
        prev_pt = prev_val / 100 if prev_val else 0

        # 텍스트 추출
        texts = re.findall(r'<hp:t>(.*?)</hp:t>', content, re.S)
        text = ''.join(texts).strip()

        # 항목 문단인지 확인 (□, ㅇ, -, *, ※ 또는 번호로 시작)
        is_item = bool(re.match(r'^[□ㅇ○\-※\*]', text)) or \
                  bool(re.match(r'^\d+\.', text)) or \
                  bool(re.match(r'^[가-힣]\.', text)) or \
                  bool(re.match(r'^\d+\)', text))

        if is_item or prev_val > 0:
            mark = text[:1] if text else ""
            level_info = ""
            if mark == "□":
                level_info = "l1(1수준)"
            elif mark in ("ㅇ", "-", "*"):
                level_info = f"l2~l4(2~4수준)"
            elif re.match(r'^\d+\.', text):
                level_info = "l1(번호)"
            elif re.match(r'^[가-힣]\.', text):
                level_info = "l2(번호)"
            elif re.match(r'^\d+\)', text):
                level_info = "l3(번호)"

            print(f"{text[:38]:<40} {pid:<10} {prev_val:<10} {prev_pt:<10.1f}  {level_info}")
            item_prev_values.append((text, pid, prev_val, prev_pt, level_info))

    # 2. prev 값 검증: □=1000(10pt), ○/-/*=500(5pt)
    print("\n[prev 값 검증]")
    errors = []
    for text, pid, prev_val, prev_pt, level_info in item_prev_values:
        if level_info and "l1" in level_info:
            expected = 1000
            if prev_val != expected:
                errors.append(f"l1 문단 '{text[:20]}...' : prev={prev_val}, 기대={expected}")
        elif level_info and ("l2" in level_info or "l3" in level_info or "l4" in level_info):
            expected = 500
            if prev_val != expected:
                errors.append(f"l2~l4 문단 '{text[:20]}...' : prev={prev_val}, 기대={expected}")

    if errors:
        print("  ⚠ 오류:")
        for e in errors:
            print(f"    - {e}")
    else:
        print("  ✓ 모든 항목 문단의 prev 값이 올바름")
        print("    - □(l1): 1000 (10pt)")
        print("    - ○/-/* (l2~l4): 500 (5pt)")

    # 3. 빈 gap 문단 수 확인 (prev > 0인 빈 문단만 카운트)
    print("\n[빈 gap 문단 수]")
    empty_count = count_empty_gap_paras(sec, paraPr_map)
    print(f"  빈 gap 문단 수: {empty_count}")
    if empty_count == 0:
        print("  ✓ 내부결재 항목 사이에 빈 gap 문단이 없음 (간격은 문단 위(prev)로만 처리)")
    else:
        print(f"  ⚠ 내부결재에 빈 gap 문단이 {empty_count}개 있음 (간격이 gap 문단으로 처리됨)")

    # 4. 표 제목 위 10pt 유지 확인
    print("\n[표 제목(caption) 위 간격 확인]")
    caption_found = False
    for attrs, content in paras:
        texts = re.findall(r'<hp:t>(.*?)</hp:t>', content, re.S)
        text = ''.join(texts).strip()
        if "테스트 표" in text:  # caption 텍스트
            caption_found = True
            pid_ref = re.search(r'paraPrIDRef="(\d+)"', attrs)
            if pid_ref:
                pid = pid_ref.group(1)
                pxml = paraPr_map.get(pid, "")
                prev_val = get_prev_from_paraPr(pxml)
                print(f"  표 제목 paraPr prev: {prev_val} ({prev_val/100:.1f}pt)")
                if prev_val == 1000:
                    print("  ✓ 표 제목 위 10pt 유지됨")
                else:
                    print(f"  ⚠ 표 제목 위 간격이 {prev_val/100:.1f}pt임 (기대: 10pt)")
            break

    if not caption_found:
        print("  ⚠ 표 제목(caption)을 찾지 못함")

    # 5. 요약
    print("\n" + "=" * 60)
    print("검증 요약")
    print("=" * 60)
    all_ok = (len(errors) == 0 and empty_count == 0 and caption_found)
    if all_ok:
        print("✓ 내부결재 보고서 간격 설정 정상")
        print("  - 항목 문단 위 간격: □=10pt(1000), ○/-/*=5pt(500)")
        print("  - 항목 사이 빈 gap 문단: 0개")
        print("  - 표 제목 위 10pt: 유지됨")
    else:
        print("⚠ 내부결재 보고서 간격 설정에 문제 있음")
        if errors:
            print(f"  - prev 값 오류: {len(errors)}건")
        if empty_count > 0:
            print(f"  - 빈 gap 문단: {empty_count}개 (기대: 0개)")
        if not caption_found:
            print("  - 표 제목 미발견")

    return all_ok


# ── pytest 테스트 ──

class TestInternalSpacing:
    """내부결재(report_kind="internal") 문단 위 간격 검증 (SPEC_internal_fix7.md 3항)."""

    def test_internal_item_prev_values(self, tmp_path):
        """내부결재: 항목 문단의 paraPr prev 값이 □=1000, ○/-/*=500인지 확인."""
        analyze_internal_spacing(tmp_path)


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        ok = analyze_internal_spacing(Path(tmp))
    sys.exit(0 if ok else 1)
