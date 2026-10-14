"""기안문 검증용 가상 원고 (Claude 작성 2026-10-14) — 수정 금지. 실명·실제 전화 없음, 자리표시만."""

SAMPLE_OFFICIAL = {
    "org": "행정안전부",
    "to": "수신자 참조",
    "via": "",
    "title": "2026년 공공부문 AI 업무도구 실증 참여 안내",
    "body": [
        {"type": "l1", "text": "국산 AI 모델 실증(POC) 참여 기관을 다음과 같이 안내합니다."},
        {"type": "l2", "text": "실증 기간: 2026-11-02 ~ 2026-12-19"},
        {"type": "l2", "text": "실증 범위: 업무 단위 도구의 시제품(POC·MVP) 수준"},
        {"type": "l3", "text": "문서 기반 추출·요약·분류, 법령 근거를 붙인 검토, 서식 채우기"},
        {"type": "l3", "text": "민원 분류·배정 같은 정형 판단"},
        {"type": "l1", "text": "참여를 희망하는 기관은 2026. 10. 31.까지 참여 신청서를 제출해 주시기 바랍니다."},
        {"type": "l2", "text": "실증 지원 예산은 기관당 금5,000,000원(금오백만원) 한도입니다."},
        {"type": "table", "rows": [["구분", "내용", "기한"], ["신청", "참여 신청서 제출", "2026. 10. 31."], ["선정", "결과 통보", "2026. 11. 7."]]},
    ],
    "attachments": ["실증 참여 신청서 1부.", "실증 참여 안내문 1부."],
    "recipients": ["기획재정부장관", "국세청장", "조달청장"],
    "sender": "행정안전부장관",
    "approval": {
        "drafter": {"title": "주무관", "name": "", "mark": "★"},
        "reviewers": [{"title": "디지털정부과장", "name": "", "opinion": False}, {"title": "디지털정부국장", "name": "", "opinion": True}],
        "approver": {"title": "차관", "name": ""},
        "coordinators": [{"title": "정보공개정책과장"}],
    },
    "doc_no": {"issue": "디지털정부과-1234", "issue_date": "2026. 10. 14.", "receive": "", "receive_date": ""},
    "contact": {"zip": "30112", "address": "세종특별자치시 한누리대로 411", "homepage": "www.mois.go.kr",
                "phone": "044-000-0000", "fax": "044-000-0001", "email": "○○○@korea.kr", "disclosure": "공개"},
}

SAMPLE_INTERNAL = {
    "org": "행정안전부",
    "to": "내부결재",
    "title": "AI 업무도구 실증 추진 계획 보고",
    "body": [
        {"type": "l1", "text": "추진 배경"},
        {"type": "l2", "text": "공무원이 직접 만드는 업무 도구에서 국산 모델의 신뢰 범위를 확인할 필요"},
        {"type": "l1", "text": "추진 계획"},
        {"type": "l2", "text": "2026-11-02부터 7주간 실증"},
    ],
    "sender": "행정안전부장관",
    "approval": {"drafter": {"title": "주무관", "name": ""}, "reviewers": [{"title": "과장", "name": ""}], "approver": {"title": "국장", "name": ""}},
    "doc_no": {"issue": "디지털정부과-1235", "issue_date": "2026-10-14"},
    "contact": {"zip": "30112", "address": "세종특별자치시 한누리대로 411", "homepage": "www.mois.go.kr",
                "phone": "044-000-0000", "fax": "044-000-0001", "email": "○○○@korea.kr", "disclosure": "비공개"},
}
