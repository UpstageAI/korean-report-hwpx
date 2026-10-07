"""맥 한컴 한글 제어 — 메뉴 클릭만 사용(키보드 입력 없음). 작성 Mia(윤승미)
한 번 쓸 때마다: 한글 종료 → 문서 하나만 열기 → 창이 뜨고 맨 앞인지 확인 → '파일 > 저장하기' → 저장 확인 → 한글 종료.
(맥 한글은 문서를 탭으로 쌓아 30개 제한에 걸리므로 매번 종료한다)
사용자가 맥을 쓰는 중(최근 90초 입력)이면 한글을 띄우지 않고 기다린다."""
import os, re, subprocess, time, unicodedata, zipfile
from pathlib import Path

APP = "Hancom Office HWP"
BIN = f"/Applications/{APP}.app/Contents/MacOS/{APP}"
MENU = 'tell application "System Events" to tell process "%s" to click menu item "%%s" of menu 1 of menu bar item "파일" of menu bar 1' % APP


def osa(*lines):
    return subprocess.run(["osascript", *sum((["-e", l] for l in lines), [])], capture_output=True, text=True)


def idle_seconds():
    out = subprocess.run(["ioreg", "-c", "IOHIDSystem"], capture_output=True, text=True).stdout
    m = re.search(r'"HIDIdleTime" = (\d+)', out)
    return int(m.group(1)) / 1e9 if m else 0


def screen_locked():
    out = subprocess.run(["ioreg", "-n", "Root", "-d1"], capture_output=True, text=True).stdout
    return '"CGSSessionScreenIsLocked"=Yes' in out


def wait_idle(sec=90):
    """사용 중이 아니고(입력 없음) 화면이 잠기지 않았을 때까지 기다림. 잠긴 화면에서는 한글 조작이 안 됨."""
    while idle_seconds() < sec or screen_locked(): time.sleep(20)


def running():
    return subprocess.run(["pgrep", "-f", BIN], capture_output=True).returncode == 0


def quit_app(timeout=30):
    if not running(): return True
    osa(f'tell application "{APP}" to quit')
    t0 = time.time()
    while time.time() - t0 < timeout:
        if not running(): return True
        time.sleep(1)
    return False  # 저장 안 된 문서 확인창 등으로 안 닫힘 → 강제 종료하지 않음


def front_name():
    return osa('tell application "System Events" to get name of first application process whose frontmost is true').stdout.strip()


def window_names():
    r = osa(f'tell application "System Events" to tell process "{APP}" to get name of every window')
    return r.stdout.strip()


def close_docs(limit=40):
    """한글은 종료하지 않고(재실행 시 한컴 계정 로그인 창이 뜸) 열린 문서 탭만 '문서 닫기'로 모두 닫는다."""
    for _ in range(limit):
        if not running() or not window_names().strip(", "): return True
        osa(f'tell application "{APP}" to activate', "delay 0.8", MENU % "문서 닫기"); time.sleep(0.8)
    return not window_names().strip(", ")


def open_front(path, timeout=40):
    """열린 문서를 모두 닫고 path 하나만 연 뒤, 그 창이 맨 앞에 올 때까지 기다림."""
    if not running(): raise RuntimeError("한글이 실행 중이 아님 — 한컴 계정 로그인 상태로 한글을 먼저 띄워 주세요")
    if not close_docs(): raise RuntimeError("한글 문서가 닫히지 않음 — 작업 중단")
    subprocess.run(["open", "-a", APP, str(path)])
    nfc = lambda x: unicodedata.normalize("NFC", x)  # 맥 파일명(NFD)과 창 제목(NFC) 정규화
    t0 = time.time(); stem = nfc(Path(path).stem)
    while time.time() - t0 < timeout:
        time.sleep(1.5)
        if stem in nfc(window_names()):
            osa(f'tell application "{APP}" to activate'); time.sleep(1.2)
            if front_name() == APP: return True
    return False


def layout(path, tries=3):
    path = Path(path).resolve()
    for k in range(tries):
        wait_idle()
        before = path.stat().st_mtime
        if not open_front(path): close_docs(); continue
        osa(MENU % "저장하기")
        t0 = time.time()
        while time.time() - t0 < 15 and path.stat().st_mtime == before: time.sleep(0.5)
        time.sleep(1)
        close_docs()
        sec = zipfile.ZipFile(path).read("Contents/section0.xml").decode("utf-8")
        if "<hp:lineseg " in sec: return sec
    raise RuntimeError("한글 줄 배치를 얻지 못함: " + str(path))


def capture(path, png, settle=3):
    wait_idle()
    if not open_front(Path(path).resolve()): close_docs(); raise RuntimeError("캡처용 한글 창이 맨 앞에 오지 않음")
    time.sleep(settle)
    if front_name() != APP: close_docs(); raise RuntimeError("캡처 직전 다른 앱이 앞에 옴")
    subprocess.run(["screencapture", "-x", str(png)])
    close_docs()


def close_all():  # 이전 코드 호환
    close_docs()
