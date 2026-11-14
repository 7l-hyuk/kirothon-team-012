# data/

신고 절차 데이터(`{type_id}.json`)를 두는 자리입니다. 사람이 검증한 값만 넣고, 확인하지 못한 값은 `verified: false`로 둡니다.
스키마는 `.kiro/steering/structure.md`의 "신고 절차 JSON 스키마"를 따르고, 선택 필드 몇 개를 더했습니다(`.kiro/specs/ai-assist/design.md`).

- 파일 4개: `illegal_parking`, `trash_dumping`, `illegal_ad`, `facility_damage`
- `seed_cases.json`은 절차 데이터가 아니라 예시 사례 3건입니다(`app/seed.py`가 앱 시작 때 `cases`가 비어 있으면 넣어요). 절차 로딩은 위 4개 파일만 읽습니다.
- 서버가 시작할 때 `app/services/procedures.py`가 Pydantic 모델로 검증하고, 형식이 틀리면 시작을 멈춥니다.
- `GET /api/procedures/{type_id}`가 이 파일 내용을 그대로 돌려주고, AI 프롬프트에도 이 값을 넣습니다.
- 현재 값은 기획서에서 가져왔고 안전신문고 화면과 대조하지 못했습니다. 대조한 항목부터 `verified: true`로 바꿉니다.
