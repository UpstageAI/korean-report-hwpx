"""Solar 호출 — Upstage 클라우드 또는 망분리 환경의 내부 Solar. OpenAI 호환 /chat/completions. 작성 Mia(윤승미)

환경변수
- UPSTAGE_API_KEY: Upstage 클라우드 키(https://console.upstage.ai)
- PRESS_RELEASE_SOLAR_BASE_URL: 내부(온프렘) Solar 주소(예: http://10.0.0.5:8000/v1). 없으면 https://api.upstage.ai/v1
- PRESS_RELEASE_SOLAR_KEY: 내부 Solar 키(없으면 UPSTAGE_API_KEY, 키가 필요 없으면 비워도 됨)
- PRESS_RELEASE_MODEL: 모델 이름(기본 solar-pro4 — 내부 설치 이름에 맞게)
- PRESS_RELEASE_SOLAR_VERIFY=0: 사내 자체 인증서일 때 TLS 검증 끄기
"""
import json
import os
import re
import ssl
import urllib.request

CLOUD = "https://api.upstage.ai/v1"


def config():
    base = os.environ.get("PRESS_RELEASE_SOLAR_BASE_URL", "").strip().rstrip("/") or CLOUD
    key = os.environ.get("PRESS_RELEASE_SOLAR_KEY", "").strip() or os.environ.get("UPSTAGE_API_KEY", "").strip()
    return base, key, os.environ.get("PRESS_RELEASE_MODEL", "solar-pro4"), base != CLOUD


def chat_json(prompt, max_tokens=8000, timeout=240):
    base, key, model, onprem = config()
    if not onprem and not key:
        raise RuntimeError("Solar 설정이 없습니다 — UPSTAGE_API_KEY(클라우드) 또는 PRESS_RELEASE_SOLAR_BASE_URL(내부 Solar 주소)")
    ctx = ssl.create_default_context()
    if os.environ.get("PRESS_RELEASE_SOLAR_VERIFY", "1") == "0":
        ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    body = {"model": model, "temperature": 0.1, "max_tokens": max_tokens, "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": prompt}]}
    h = {"Content-Type": "application/json"}
    if key: h["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(f"{base}/chat/completions", data=json.dumps(body).encode(), method="POST", headers=h)
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as r:
        t = json.loads(r.read())["choices"][0]["message"]["content"]
    t = re.sub(r"^```(?:json)?|```$", "", t.strip(), flags=re.M)
    t = t[t.find("{"):t.rfind("}") + 1] if "{" in t else t   # JSON 앞뒤 군더더기 제거
    return json.loads(t)
