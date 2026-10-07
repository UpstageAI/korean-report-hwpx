"""가상 원고(sample_release)로 전 기관 생성: 열림·예시 번호 외 전화번호 0건·그림 0건."""
import re, zipfile
import pytest
import compose as C
from sample_release import SAMPLE
from test_sanitize import PHONE, ALLOWED_PHONES


@pytest.mark.parametrize("org", C.ministries())
def test_sample_builds(tmp_path, org):
    dst = tmp_path / "a.hwpx"; C.compose(org, SAMPLE, dst)
    z = zipfile.ZipFile(dst); sec = z.read("Contents/section0.xml").decode()
    assert not [n for n in z.namelist() if n.startswith("BinData/")]
    bad = [m.group(0) for m in PHONE.finditer(re.sub(r"<[^>]+>", "", sec)) if re.sub(r"[()\s]", "", m.group(0)) not in ALLOWED_PHONES]
    assert not bad and "참고 1" in sec and "<hp:nbSpace/>" in sec
