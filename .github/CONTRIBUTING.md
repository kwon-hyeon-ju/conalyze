## 📁 브랜치 전략

- **`main`**: 최종 배포용 브랜치 (실제 서비스 운영 반영)
- **`develop`**: 통합 개발 브랜치 (배포 전 최종 PR)
- **`{BE,FE,AI}/develop`**: 팀 개발 브랜치 (배포 전 최종 PR)
- **기능/이슈 단위 브랜치**:
    - 형식: `{BE,FE,AI}/{feature,fix,refactor,docs,infra}/#이슈번호/작업명`
    - 예: `BE/feature/#12/video-sync`

---

## 🧭 커밋 메시지 규칙

- 형식: `[팀명][기능] #이슈번호 메시지`
- 예: `[AI][fix] #24 정확도 개선`

| 태그         | 의미      |
|------------|---------|
| `Infra`    | 환경 세팅   |
| `Feature`  | 신규 기능   |
| `Fix`      | 버그 수정   |
| `Refactor` | 리팩토링    |
| `Test`     | 테스트 코드  |
| `Docs`     | 문서 변경   |
| `Style`    | 스타일/포맷팅 |
| `Chore`    | 기타 작업   |

---

## 🔀 Pull Request 규칙

- 제목 형식: `[팀명][기능] #이슈번호 이슈 제목`
- 본문에 반드시 `Closes #{이슈번호}` 포함
- **`.github/pull_request_template.md`사용**
- 예시:
  ```md
  [FE][feature] #12 nav개발

  Closes #12
