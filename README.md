# GaesinLight

RGB 손전등으로 블록을 비춰 능력을 발동시키고, 버튼·발판·문을 연결해 퍼즐을 만드는 게임입니다. (UE 5.8, 블루프린트)

## 레벨 제작 가이드
레벨 제작 매뉴얼은 HTML 문서로 옮겼습니다. 저장소를 받은 뒤 아래 파일을 브라우저로 여세요 (인터넷·서버 없이 열람 가능).

- **[`Docs/레벨 제작 가이드.html`](Docs/레벨%20제작%20가이드.html)**
  - 맨 위 "신호 채널 한눈에 보기" 표: 장치별 Channel 번호 → 기능
  - 장치별 설정값, 동작, "이렇게 만들 수 있어요" 예시
  - 검색창으로 접힌 내용까지 찾기, 모두 펼치기/접기, 인쇄 지원
- 스타일·동작 파일: `Docs/assets/guide.css`, `Docs/assets/guide.js`

> GitHub 웹 화면에서는 HTML이 그대로 렌더링되지 않습니다. 저장소를 받아 로컬에서 여세요.

## 개발자용 문서
- `BP_STRUCTURE.md`: 블루프린트 내부 구조(컴포넌트·변수·함수·그래프 흐름)
- `CLAUDE.md`: 설계 결정·작업 기록

## 아트 애셋
`Content/Assets/`(Materials, StaticMeshes, Textures)는 git에서 제외되어 있습니다. 구글 드라이브(`ArtManifest.json` 참고)에서 받아 같은 폴더 구조로 넣으세요.
