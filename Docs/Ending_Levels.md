# 엔딩 레벨

`/Game/Code/Levels/Level_Ending_1`과 `Level_Ending_2`는 캐릭터 없이 검은 화면과 중앙의 흰색 문구를 표시하는 두 엔딩이다.

## 연결

기존 `BP_Trigger`의 **Next Level**에서 원하는 엔딩 레벨을 선택한다. 엔딩마다 별도의 트리거에 연결할 수 있다.

## 문구와 시간 변경

원하는 엔딩 레벨을 열고 아웃라이너의 `Ending_Settings_1` 또는 `Ending_Settings_2`를 선택한다. 디테일의 **Ending Settings**에서 수정하고 레벨을 저장한다.

| 설정 | 기능 | 기본값 |
|---|---|---|
| Ending Text | 화면 가운데 표시할 문구 | 엔딩 1 / 엔딩 2 |
| Initial Black Delay | 입장 후 글씨가 나타나기 전까지 검은 화면 | 2초 |
| Text Fade In Duration | 글씨가 검정에서 흰색으로 밝아지는 시간 | 2초 |
| Text Hold Duration | 완전히 흰색인 글씨를 유지하는 시간 | 4초 |
| Text Fade Out Duration | 글씨가 다시 어두워지는 시간 | 2초 |
| Final Black Delay | 글씨가 사라진 뒤 메뉴로 이동하기 전 대기 | 2초 |
| Font Scale | 글자 크기 배율 | 3 |
| Return Level | 마지막에 이동할 레벨 | /Game/Code/Levels/MainManu |

시간은 각 단계의 **지속 시간**이며 순서대로 누적된다. 기본 설정은 0~2초 암전, 2~4초 페이드 인, 4~8초 흰색 유지, 8~10초 페이드 아웃, 10~12초 암전 후 메뉴 이동이다. 음수는 0초로 처리한다. 0초 페이드는 즉시 전환된다.

두 레벨의 설정은 독립적이다. 문구가 화면 폭을 넘으면 자동으로 축소해 가운데 맞춘다. 글자 색은 흰색이고 배경은 항상 검정이다.

글꼴은 `MainManu`의 게임시작·이어하기 버튼과 같은 `ChaiHwaljjak-Medium_Font`이다. 엔딩 전용 `F_Ending_MainMenu`는 같은 글꼴 데이터를 256 크기로 캐싱해서 큰 Font Scale에서도 선명하게 표시한다. 메뉴의 원본 폰트는 변경하지 않는다.

## 구성

- `BP_EndingSequence`: 각 레벨에 배치된 설정 및 시간 진행 액터
- `BP_EndingHUD`: 검은 배경과 중앙 텍스트 표시
- `BP_EndingGameMode`: 엔딩 전용 게임 모드, 플레이어 Pawn 생성 없음

두 엔딩 레벨에는 게임 모드가 지정되어 있다. 기존 게임플레이 게임 모드로 변경하지 않는다. 메뉴로 이동하면 메뉴의 게임 모드가 다시 적용된다.

프로젝트에서 패키징할 맵을 별도로 제한하는 경우 두 엔딩 레벨과 `MainManu`도 포함한다.
