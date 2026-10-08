"""빈 HWPX 바탕을 코드로 만든다(원본 문서 없이). 작성 Mia(윤승미)

HWPX = zip(mimetype, version.xml, META-INF/*, Contents/content.hpf, Contents/header.xml, Contents/section0.xml, settings.xml, Preview/PrvText.txt, BinData/*).
header.xml은 글꼴 1개·글자 모양 1개·문단 모양 1개·테두리 2개·스타일 1개만 둔 최소 구성이고,
생성기(compose.Composer)가 규칙값에 따라 글자·문단·테두리 모양을 덧붙인다."""
import zipfile

NS = ('xmlns:ha="http://www.hancom.co.kr/hwpml/2011/app" xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
      'xmlns:hp10="http://www.hancom.co.kr/hwpml/2016/paragraph" xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" '
      'xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core" xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head" '
      'xmlns:hhs="http://www.hancom.co.kr/hwpml/2011/history" xmlns:hm="http://www.hancom.co.kr/hwpml/2011/master-page" '
      'xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf" xmlns:dc="http://purl.org/dc/elements/1.1/" '
      'xmlns:opf="http://www.idpf.org/2007/opf/" xmlns:ooxmlchart="http://www.hancom.co.kr/hwpml/2016/ooxmlchart" '
      'xmlns:hwpunitchar="http://www.hancom.co.kr/hwpml/2016/HwpUnitChar" xmlns:epub="http://www.idpf.org/2007/ops" '
      'xmlns:config="urn:oasis:names:tc:opendocument:xmlns:config:1.0"')
XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
LANGS = ("HANGUL", "LATIN", "HANJA", "JAPANESE", "OTHER", "SYMBOL", "USER")
ALL7 = lambda v: " ".join(f'{l.lower()}="{v}"' for l in LANGS)


def _border_fill(i, line="NONE", width="0.1 mm"):
    side = lambda s: f'<hh:{s}Border type="{line}" width="{width}" color="#000000"/>'
    return (f'<hh:borderFill id="{i}" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">'
            '<hh:slash type="NONE" Crooked="0" isCounter="0"/><hh:backSlash type="NONE" Crooked="0" isCounter="0"/>'
            + side("left") + side("right") + side("top") + side("bottom") +
            '<hh:diagonal type="NONE" width="0.1 mm" color="#000000"/></hh:borderFill>')


def _margin(k=1):
    return ("<hh:margin>" + "".join(f'<hc:{n} value="0" unit="HWPUNIT"/>' for n in ("intent", "left", "right", "prev", "next"))
            + f'</hh:margin><hh:lineSpacing type="PERCENT" value="160" unit="HWPUNIT"/>')


def header_xml(base_font="함초롬바탕"):
    fonts = "".join(f'<hh:fontface lang="{l}" fontCnt="1"><hh:font id="0" face="{base_font}" type="TTF" isEmbedded="0"/></hh:fontface>' for l in LANGS)
    char0 = (f'<hh:charPr id="0" height="1000" textColor="#000000" shadeColor="none" useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="1">'
             f'<hh:fontRef {ALL7(0)}/><hh:ratio {ALL7(100)}/><hh:spacing {ALL7(0)}/><hh:relSz {ALL7(100)}/><hh:offset {ALL7(0)}/>'
             '<hh:underline type="NONE" shape="SOLID" color="#000000"/><hh:strikeout shape="NONE" color="#000000"/>'
             '<hh:outline type="NONE"/><hh:shadow type="NONE" color="#C0C0C0" offsetX="10" offsetY="10"/></hh:charPr>')
    para0 = ('<hh:paraPr id="0" tabPrIDRef="0" condense="0" fontLineHeight="0" snapToGrid="1" suppressLineNumbers="0" checked="0">'
             '<hh:align horizontal="JUSTIFY" vertical="BASELINE"/><hh:heading type="NONE" idRef="0" level="0"/>'
             '<hh:breakSetting breakLatinWord="KEEP_WORD" breakNonLatinWord="KEEP_WORD" widowOrphan="0" keepWithNext="0" keepLines="0" pageBreakBefore="0" lineWrap="BREAK"/>'
             '<hh:autoSpacing eAsianEng="0" eAsianNum="0"/>'
             '<hp:switch><hp:case hp:required-namespace="http://www.hancom.co.kr/hwpml/2016/HwpUnitChar">' + _margin() + '</hp:case>'
             '<hp:default>' + _margin() + '</hp:default></hp:switch>'
             '<hh:border borderFillIDRef="1" offsetLeft="0" offsetRight="0" offsetTop="0" offsetBottom="0" connect="0" ignoreMargin="0"/></hh:paraPr>')
    return (XML + f'<hh:head {NS} version="1.31" secCnt="1">'
            '<hh:beginNum page="1" footnote="1" endnote="1" pic="1" tbl="1" equation="1"/><hh:refList>'
            f'<hh:fontfaces itemCnt="7">{fonts}</hh:fontfaces>'
            f'<hh:borderFills itemCnt="2">{_border_fill(1)}{_border_fill(2, "SOLID", "0.12 mm")}</hh:borderFills>'
            f'<hh:charProperties itemCnt="1">{char0}</hh:charProperties>'
            '<hh:tabProperties itemCnt="1"><hh:tabPr id="0" autoTabLeft="0" autoTabRight="0"/></hh:tabProperties>'
            f'<hh:paraProperties itemCnt="1">{para0}</hh:paraProperties>'
            '<hh:styles itemCnt="1"><hh:style id="0" type="PARA" name="바탕글" engName="Normal" paraPrIDRef="0" charPrIDRef="0" nextStyleIDRef="0" langID="1042" lockForm="0"/></hh:styles>'
            '</hh:refList><hh:compatibleDocument targetProgram="HWP201X"><hh:layoutCompatibility/></hh:compatibleDocument>'
            '<hh:docOption><hh:linkinfo path="" pageInherit="0" footnoteInherit="0"/></hh:docOption>'
            '<hh:trackchageConfig flags="56"/></hh:head>')


def sec_pr(page):
    """구역 정의(쪽 크기·여백) + 단 정의. 첫 문단의 첫 글자 조각에 들어간다."""
    g = lambda k, d: page.get(k, d)
    note = lambda place, ln: (f'<hp:autoNumFormat type="DIGIT" userChar="" prefixChar="" suffixChar=")" supscript="0"/>'
                              f'<hp:noteLine length="{ln}" type="SOLID" width="0.12 mm" color="#000000"/><hp:noteSpacing betweenNotes="283" belowLine="567" aboveLine="850"/>'
                              f'<hp:numbering type="CONTINUOUS" newNum="1"/><hp:placement place="{place}" beneathText="0"/>')
    pbf = lambda t: (f'<hp:pageBorderFill type="{t}" borderFillIDRef="1" textBorder="PAPER" headerInside="0" footerInside="0" fillArea="PAPER">'
                     '<hp:offset left="1417" right="1417" top="1417" bottom="1417"/></hp:pageBorderFill>')
    return ('<hp:secPr id="" textDirection="HORIZONTAL" spaceColumns="1134" tabStop="8000" tabStopVal="4000" tabStopUnit="HWPUNIT" outlineShapeIDRef="0" memoShapeIDRef="0" textVerticalWidthHead="0" masterPageCnt="0">'
            '<hp:grid lineGrid="0" charGrid="0" wonggojiFormat="0"/><hp:startNum pageStartsOn="BOTH" page="0" pic="0" tbl="0" equation="0"/>'
            '<hp:visibility hideFirstHeader="0" hideFirstFooter="0" hideFirstMasterPage="0" border="SHOW_ALL" fill="SHOW_ALL" hideFirstPageNum="0" hideFirstEmptyLine="0" showLineNumber="0"/>'
            '<hp:lineNumberShape restartType="0" countBy="0" distance="0" startNumber="0"/>'
            f'<hp:pagePr landscape="WIDELY" width="{g("width", 59528)}" height="{g("height", 84188)}" gutterType="LEFT_ONLY">'
            f'<hp:margin header="{g("header", 4252)}" footer="{g("footer", 4252)}" gutter="{g("gutter", 0)}" left="{g("left", 5669)}" right="{g("right", 5669)}" top="{g("top", 2834)}" bottom="{g("bottom", 2834)}"/></hp:pagePr>'
            f'<hp:footNotePr>{note("EACH_COLUMN", -1)}</hp:footNotePr><hp:endNotePr>{note("END_OF_DOCUMENT", -4)}</hp:endNotePr>'
            + pbf("BOTH") + pbf("EVEN") + pbf("ODD") + '</hp:secPr>'
            '<hp:ctrl><hp:colPr id="" type="NEWSPAPER" layout="LEFT" colCount="1" sameSz="1" sameGap="0"/></hp:ctrl>')


def section_xml(paras):
    return XML + f"<hs:sec {NS}>" + "".join(paras) + "</hs:sec>"


def content_hpf(images, title="보도자료"):
    """images: [(id, href, media-type)]"""
    items = "".join(f'<opf:item id="{i}" href="{h}" media-type="{m}" isEmbeded="1"/>' for i, h, m in images)
    return (XML + f'<opf:package {NS} version="" unique-identifier="" id=""><opf:metadata><opf:title>{title}</opf:title><opf:language>ko</opf:language>'
            '<opf:meta name="creator" content="text"/><opf:meta name="subject" content="text"/><opf:meta name="description" content="text"/>'
            '<opf:meta name="lastsaveby" content="text"/><opf:meta name="keyword" content="text"/></opf:metadata>'
            '<opf:manifest><opf:item id="header" href="Contents/header.xml" media-type="application/xml"/>' + items +
            '<opf:item id="section0" href="Contents/section0.xml" media-type="application/xml"/><opf:item id="settings" href="settings.xml" media-type="application/xml"/></opf:manifest>'
            '<opf:spine><opf:itemref idref="header" linear="yes"/><opf:itemref idref="section0"/></opf:spine></opf:package>')


VERSION = (XML + '<hv:HCFVersion xmlns:hv="http://www.hancom.co.kr/hwpml/2011/version" tagetApplication="WORDPROCESSOR" major="5" minor="1" micro="0" '
           'buildNumber="1" os="1" xmlVersion="1.31" application="korean-report-hwpx" appVersion="0.1.0"/>')
CONTAINER = (XML + '<ocf:container xmlns:ocf="urn:oasis:names:tc:opendocument:xmlns:container" xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf">'
             '<ocf:rootfiles><ocf:rootfile full-path="Contents/content.hpf" media-type="application/hwpml-package+xml"/>'
             '<ocf:rootfile full-path="Preview/PrvText.txt" media-type="text/plain"/></ocf:rootfiles></ocf:container>')
MANIFEST = XML + '<odf:manifest xmlns:odf="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"/>'
SETTINGS = (XML + '<ha:HWPApplicationSetting xmlns:ha="http://www.hancom.co.kr/hwpml/2011/app" xmlns:config="urn:oasis:names:tc:opendocument:xmlns:config:1.0">'
            '<ha:CaretPosition listIDRef="0" paraIDRef="0" pos="0"/></ha:HWPApplicationSetting>')


def save(dst, header, section, images=(), preview="", title="보도자료"):
    """images: [(id, ext, bytes)]"""
    mt = lambda e: "image/" + {"jpg": "jpg", "jpeg": "jpg", "png": "png", "bmp": "bmp", "gif": "gif"}.get(e, e)
    hpf = content_hpf([(i, f"BinData/{i}.{e}", mt(e)) for i, e, _ in images], title)
    with zipfile.ZipFile(dst, "w") as z:
        z.writestr("mimetype", "application/hwp+zip", compress_type=zipfile.ZIP_STORED)
        for n, d in (("version.xml", VERSION), ("Contents/header.xml", header), ("Contents/section0.xml", section),
                     ("settings.xml", SETTINGS), ("META-INF/container.xml", CONTAINER), ("META-INF/manifest.xml", MANIFEST),
                     ("Contents/content.hpf", hpf), ("Preview/PrvText.txt", preview)):
            z.writestr(n, d.encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED)
        for i, e, b in images:
            z.writestr(f"BinData/{i}.{e}", b, compress_type=zipfile.ZIP_DEFLATED)
