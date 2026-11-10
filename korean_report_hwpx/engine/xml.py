"""HWPX XML 조각 — 표(tbl)·칸(tc)·테두리(borderFill)·문단(p)의 공통 뼈대와 수치 상수. 작성 Mia(윤승미)
자리마다 다른 속성(treatAsChar·pageBreak·inMargin·header…)은 매개변수로 받고, 문자열은 기존 출력과 바이트 단위로 같다.
표·그림 id는 호출하는 쪽(compose._rid)이 만든다."""
PT = 100                              # 1pt = 100 HWPUNIT
TEXT_PAD = 200                        # 표·상자 폭 = 본문 폭 - 좌우 여유
CELL_MARGIN = 141                     # 칸 안쪽 기본 여백(0.5mm)
TBL_MARGIN = (510, 510, 141, 141)     # 본문 표 칸 여백: 좌우 1.8mm, 위아래 0.5mm
BOX_MARGIN = (850, 850, 566, 566)     # 강조·제목 상자 칸 여백: 좌우 3mm, 위아래 2mm
NO_MARGIN = (0, 0, 0, 0)
SIDES = ("left", "right", "top", "bottom")
SUBLIST_ATTRS = 'id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0"'


def sublist_xml(inner):
    return f'<hp:subList {SUBLIST_ATTRS}>{inner}</hp:subList>'


def run_xml(cid, inner):
    return f'<hp:run charPrIDRef="{cid}">{inner}</hp:run>'


def para_xml(pid, runs, page_break=0):
    """최상위 문단(id 0). runs는 run_xml 조각들."""
    return f'<hp:p id="0" paraPrIDRef="{pid}" styleIDRef="0" pageBreak="{page_break}" columnBreak="0" merged="0">{runs}</hp:p>'


def tc_xml(bf, paras, col, row, w, h, margin=(CELL_MARGIN,) * 4, colspan=1, rowspan=1, header=0, has_margin=1):
    """표 칸. w·h는 받은 그대로 쓴다(정수는 호출하는 쪽에서)."""
    l, r, t, b = margin
    return (f'<hp:tc name="" header="{header}" hasMargin="{has_margin}" protect="0" editable="0" dirty="0" borderFillIDRef="{bf}">'
            f'{sublist_xml(paras)}'
            f'<hp:cellAddr colAddr="{col}" rowAddr="{row}"/><hp:cellSpan colSpan="{colspan}" rowSpan="{rowspan}"/><hp:cellSz width="{w}" height="{h}"/>'
            f'<hp:cellMargin left="{l}" right="{r}" top="{t}" bottom="{b}"/></hp:tc>')


def tbl_xml(rid, bf, nrow, ncol, width, height, rows, page_break="CELL", repeat_header=0, treat_as_char=1, align="CENTER", out_bottom=0, in_margin=(CELL_MARGIN,) * 4):
    """표. rows는 <hp:tr>…</hp:tr> 조각을 이은 문자열. treat_as_char=1이면 글자처럼 취급(본문 흐름 안의 한 덩어리)."""
    il, ir, it, ib = in_margin
    return (f'<hp:tbl id="{rid}" zOrder="1" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="{page_break}" repeatHeader="{repeat_header}" '
            f'rowCnt="{nrow}" colCnt="{ncol}" cellSpacing="0" borderFillIDRef="{bf}" noAdjust="0"><hp:sz width="{width}" widthRelTo="ABSOLUTE" height="{height}" heightRelTo="ABSOLUTE" protect="0"/>'
            f'<hp:pos treatAsChar="{treat_as_char}" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" vertAlign="TOP" horzAlign="{align}" vertOffset="0" horzOffset="0"/>'
            f'<hp:outMargin left="0" right="0" top="0" bottom="{out_bottom}"/><hp:inMargin left="{il}" right="{ir}" top="{it}" bottom="{ib}"/>' + rows + "</hp:tbl>")


def border_xml(sides, fill=None, i=0):
    """테두리·배경(header.xml의 borderFill). sides는 (type, width, color) 네 개를 SIDES 순서(left·right·top·bottom)로."""
    f = f'<hc:fillBrush><hc:winBrush faceColor="{fill}" hatchColor="#999999" alpha="0"/></hc:fillBrush>' if fill else ""
    return (f'<hh:borderFill id="{i}" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0"><hh:slash type="NONE" Crooked="0" isCounter="0"/>'
            '<hh:backSlash type="NONE" Crooked="0" isCounter="0"/>' + "".join(f'<hh:{s}Border type="{t}" width="{w}" color="{c}"/>' for s, (t, w, c) in zip(SIDES, sides)) +
            '<hh:diagonal type="NONE" width="0.1 mm" color="#000000"/>' + f + "</hh:borderFill>")
