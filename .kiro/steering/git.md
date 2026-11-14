---
inclusion: always
---

# Git 규칙

심사는 2026-11-14(토) 18:00 시점의 `main`만 봅니다. 제출 요건은 `tech.md`의 "제출 요건"을, 폴더 구조는 `structure.md`를 따릅니다.

## 브랜치
- 기능별 짧은 브랜치에서 작업하고 PR로 `main`에 자주 병합합니다. `main`에 직접 커밋하거나 push하지 않습니다.
- 이름은 `feat/<기능>`, `fix/<내용>`, `docs/<내용>`, `chore/<내용>`. 영문 소문자와 하이픈만 씁니다.
- 백엔드는 `feat/be-<기능>`, 프론트는 `feat/fe-<기능>`을 씁니다. 예: `feat/be-analyze`, `feat/be-evidence-check`, `feat/fe-guide-steps`, `feat/fe-my-reports`
- 한 브랜치는 한 기능만 다룹니다.
- 기능이 로컬에서 동작하면 바로 PR을 엽니다. 브랜치를 1시간 넘게 병합하지 않고 두지 않습니다.

## 병합
1. 병합 전에 `main`의 최신 내용을 브랜치로 가져와 충돌을 브랜치에서 먼저 해결합니다.
2. 브랜치를 push하고 PR을 엽니다. PR 본문은 `.github/pull_request_template.md`의 절(배경, 변경 사항, 검증, 확인 사항, 배포 전 필수, 인수인계, 참고)을 따릅니다. 상대방 작업에 영향을 주는 변경은 인수인계 표에 받는 사람을 적습니다.
3. PR의 CI(`backend`, `frontend`, `docker`)가 통과한 뒤 병합합니다.
4. `main`에 병합되면 `.github/workflows/deploy.yml`이 서버에 자동 배포합니다. 병합 뒤 `https://www.room2ate.cloud/api/health`를 확인합니다.

- `main`은 항상 실행 가능해야 합니다. PR을 열기 전에 로컬에서 `uv run pytest`(프론트를 건드렸으면 `npm run build`)를 확인합니다.
- 병합하지 않은 브랜치의 작업은 심사에 반영되지 않습니다.

## 마감
| 시각 | 규칙 |
|---|---|
| 17:30 이후 | 새 브랜치를 만들지 않습니다 |
| 17:50까지 | 모든 브랜치를 `main`에 병합하고 마지막 push를 끝냅니다 |
| 18:00 이후 | 커밋은 심사에 반영되지 않습니다 |

## 커밋 메시지
- 제목: `<type>: <한국어 제목>`. type은 `feat`, `fix`, `docs`, `chore`, `refactor`, `test` 중 하나입니다.
- 본문에는 무엇을 왜 바꿨는지 짧게 적습니다.

```
feat: 증거 사진 검수 API 추가

사진이 장면별 요건을 채웠는지 AI로 판정해 부족한 점과 재촬영 방법을 돌려줍니다.
```

## 커밋 금지
- `.env`, API 키, `uploads/`, DB 파일(`*.db`), 데모 영상 파일
- 커밋 전에 `git status`와 `git diff --cached`로 위 파일이 섞이지 않았는지 봅니다. 비밀 값 규칙은 `tech.md`의 "금지 사항"과 같습니다.

## 금지 작업
- 강제 push(`--force`)와 `main`의 이력 재작성(`reset --hard` 후 push, `rebase` 후 push 등)은 하지 않습니다.

## 동시 작업
- 백엔드와 프론트를 서로 다른 사람이 동시에 작업할 때는 `backend/`와 `frontend/`를 나눠 맡아 같은 파일을 건드리지 않게 합니다.
