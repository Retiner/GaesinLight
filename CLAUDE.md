# GaesinLight 프로젝트 — AI 작업 컨텍스트

RGB 손전등 퍼즐 게임. UE 5.8. 새 세션 시작 시 먼저 읽고 시작할 것.
레벨 제작자용 상세 매뉴얼은 **`레벨 제작 가이드.html`**(저장소 맨 위. 2026-10-30 Docs에서 꺼냄, CSS·JS는 그대로 `Docs/assets/`. README.md는 2026-10-30 사용자 요청으로 삭제 — VS Code가 옛 README 미저장 버퍼를 계속 보여 줘서. 맨 위 `#channels` 채널 표, `#changes` 최근 변경 절을 매번 갱신)(2026-10-25 README에서 이전, 로그라이크 프로젝트 가이드 형식: 장·항목 `details` 접이식, `assets/guide.css`·`guide.js`). README.md는 그 HTML을 가리키는 짧은 안내만 둠. (이 파일은 AI / 개발 이어가기용 요약 + 구현 메모)
**BP 내부 구조(구성요소·변수·함수·흐름)는 `BP_STRUCTURE.md`** — BP 수정 안내 전에 먼저 읽고, 구조가 바뀌면 같은 턴에 갱신(2026-10-23 사용자 지시).

---

## 1. 블루프린트 목록과 인스턴스 설정 (사용 매뉴얼 요약)

### 1-0. 신호 구조
- 송신: BP_Button, BP_PressurePlate, BP_Trigger(1-3-1) → `SignalTargets`(`S_SignalTarget` 배열: Target Actor + Channel Int, 기본 0)마다 `BPI_Activatable`의 `Activate(Channel)` / `Deactivate(Channel)` 메시지 전송. 상태가 바뀔 때만 보냄. 인터페이스 메시지라 BPI_Activatable 미구현 액터나 None이 들어 있어도 오류 없이 무시됨.
- 수신: BP_Activate를 부모로 하는 BP_Door, BP_Light, BP_AvilityBlock, BP_Hatch.
- 공통 수신 설정: 채널별로 켜진 신호 수(`ChannelCount`)가 필요 개수 이상이면 `OnChannelActive(Channel)`, 아래로 내려가면 `OnChannelDeactive(Channel)`. 필요 개수 = `Max(Map_Find(ChannelRequired, Channel), 1)` (Map 채널→개수, 없으면 1). 2 이상이면 AND. `RequiredCount`는 2026-10-05 삭제(ChannelRequired로 통합). 각 BP Class Defaults에 받는 채널을 `→ 1`로 미리 넣어 둠(문 `0`·`1`, 다락문/블록 `0`, 광원 `0~4`). 모든 수신 장치가 `OnChannelActive`/`OnChannelDeactive`를 직접 오버라이드(`OnActive`/`OnDeactive`/`IsActive`/`ActiveCount`는 2026-10-05 삭제). 채널 번호는 수신 장치 안에서만 의미가 있음. 수신 장치의 기능→채널 번호표는 BP에 고정(인스턴스 설정 아님, 2026-10-04 사용자 결정: 송신 쪽 Channel로 기능을 고르므로 수신 쪽까지 바꿀 수 있으면 중복). 현재 번호표: 문 0=열기 / 1=잠금(Lock, 영구), 다락문 0=열기, 능력 블록 0=이동(WaitTrigger) / 1=처음으로(RestartFromStart, 2026-10-30), 맵 광원 0=전원(TurnOn+SetVisibility) / 1=색(ChangeColor: R/G/B 켜짐→그 색, 꺼짐→FirstColorValue, Rotate는 `==` 비교로 R→G→B 순환, 꺼짐 무시) / 2=상하 회전 / 3=좌우 회전 / 4=이동(작업 4). `Docs/레벨 제작 가이드.html` 맨 위 "신호 채널 한눈에 보기"(#channels)에 표로 정리(2026-10-30 "추천 버튼 모드" 열 추가: 유지형 기능 = Togle/JustOn/Timed, 펄스형(블록 1 처음으로, 광원 1 Rotate) = ReOn).
- 시작 상태 반전(2026-10-05): 각 장치에 단순 bool(문/다락문 `StartOpen`, 블록 `StartMoving`, 광원 `StartOn` 완료. 광원 회전·이동의 시작 상태 반전은 만들지 않기로 함(2026-10-08 사용자 결정)). 부모 순수 함수 `IsStartOn(Channel)→bool`(기본 false)을 자식이 Switch on Int로 오버라이드해 채널별 bool 반환. true면 부모가 Active/Deactive 호출을 서로 바꿈 → 신호 켜짐 = 꺼짐 동작. 장치는 BeginPlay/Construction에서 스스로 "켜진 상태"로 시작해야 함. (Set<채널> 방식은 레벨 제작자 부담이라 사용자가 거절)
- 버튼과 발판은 같은 신호를 보내므로 한 수신 장치에 섞어서 연결 가능(합산). 예: 문 `ChannelRequired 0→2` + Togle 버튼 + 발판 = 버튼 켜고 발판 밟아야 열림. AND에 `ReOn`은 즉시 꺼져서 사용 불가.

### 1-1. BP_Charactor — 플레이어
- 무엇: 손전등을 든 플레이어. 1 키 흰색(`IA_White`: 보이는 색은 흰색, 기여 값은 (0,0,0) → 다른 빛 색을 안 바꾸고 OwnColor 블록의 고유색을 발동시킴. 2026-10-05 사용자 동작 확인), 2·3·4 키 빨강·초록·파랑(`IA_Red/Green/Blue`), 손전등 끄기 = 현재 색의 숫자 키 다시 누르기 또는 E(`IA_TurnOff`), F 키 상호작용(`IA_Relation`, 버튼 누르기 / 블록 잡기·놓기).
- 인스턴스 설정: 없음 (손전등 `LightLength`는 BP 내부 고정값).
- 주의: 손전등 메시는 반드시 NoCollision (BlockAll이면 보라 Physics 블록이 WorldStatic으로 보고 부딪혀 튕김).

### 1-2. BP_Button — 버튼 (송신, BPI_Interact)
| 인스턴스 설정 | 설명 | 기본값 |
|---|---|---|
| `SignalTargets` | 신호 받을 장치 + 채널 (`S_SignalTarget` 배열) | 비어 있음 |
| `ButtonMode` | `JustOn`(한 번 켜고 고정) / `Togle`(켜짐↔꺼짐) / `ReOn`(펄스: Activate 직후 Deactivate) / `Timed`(`TimedDuration`초 후 자동 꺼짐) | `JustOn` |
| `TimedDuration` | Timed 지속 시간 | 10 |
| `UseAsset` + `UseStaticMesh` | 외형 메시 교체 (Construction Script, 메시에 콜리전 필요) | 꺼짐 / 없음 |
- 예시: JustOn+문=영구 출구 / ReOn+Rotate 광원=색 회전 퍼즐 / Timed+문=타임어택.
- ReOn(펄스)이 필요한 이유: BP_Activate는 채널별 카운트로 세기 때문에 Activate만 반복하면 카운트만 쌓이고 `OnActive`가 다시 안 불림. 즉시 Deactivate해서 카운트를 되돌려야 매번 반응함.

### 1-3. BP_PressurePlate — 발판 (송신)
| 인스턴스 설정 | 설명 | 기본값 |
|---|---|---|
| `SignalTargets` | 신호 받을 장치 + 채널 (`S_SignalTarget` 배열) | 비어 있음 |
- 감지: BP_Charactor 또는 BP_AvilityBlock(자식 포함)이 Trigger 박스에 하나라도 있으면 켜짐.
- 예시: 발판+문 / 블록 올려두기 / 발판 2개 + 문(`ChannelRequired 0→2`) = AND 퍼즐.

### 1-3-1. BP_Trigger — 통과 트리거 + 레벨 이동 (송신, 2026-10-08 추가·동작 확인)
| 인스턴스 설정 | 설명 | 기본값 |
|---|---|---|
| `SignalTargets` | 신호 받을 장치 + 채널 (`S_SignalTarget` 배열) | 비어 있음 |
| `NextLevel` | 지나가면 열 레벨 (비면 신호만) | 비어 있음 |
- 컴포넌트 = `Box`(Box Collision, Hidden in Game, OverlapAllDynamic). 크기는 액터 Scale. 배열 변수 이름은 `Targets`(버튼·발판의 `SignalTargets`와 다름).
- `OnComponentBeginOverlap(Box)` → Branch(`OtherActor == GetPlayerCharacter` AND NOT `Triggered`) → `Triggered = true` → ForEach(Targets) → Break → `Activate`(Message). 플레이어만, 한 번만, Deactivate는 보내지 않음(영구 켜짐).
- 용도: 스테이지 전환 — 통로 트리거① → 출구 문 Ch1(잠금) + 입구 문 Ch0(열기), 입구 안쪽 트리거② → 입구 문 Ch1.
- 레벨 이동(2026-10-08 추가·동작 확인): `NextLevel`(World Soft Object Reference, Instance Editable — 타입 목록에서 안 보여서 `Open Level (by Object Reference)`의 Level 핀 Promote to Variable로 만듦). ForEach Completed → Branch(`IsValidSoftObjectReference(NextLevel)`) → `GetPlayerCameraManager.StartCameraFade`(0→1, 0.5초, Hold) → `Delay 0.5` → `OpenLevel(by Object Reference)`. 비어 있으면 신호만. 도착 맵의 PlayerStart + GameMode Override(BP_GameMode) 필요. 이동 시 플레이어 재생성 → 획득 상태는 작업 6 GameInstance에 둘 것.

### 1-3-2. BP_Respawn — 블록·플레이어 되돌리기 구역 (2026-10-08 추가, 플레이어 소환 2026-10-23 추가·동작 확인)
- 인스턴스 설정: `ResetBlock`(기본 켬), `ResetPlayer`(기본 끔), `PlayerRespawnLocation`(3D Widget, 로컬). 크기 = 액터 Scale. 플레이어 분기: Cast Failed → Branch(OtherActor == GetPlayerCharacter AND ResetPlayer) → HeldBlock 있으면 DropBlock → Teleport(TransformLocation(GetActorTransform, PlayerRespawnLocation), 현재 회전) → StopMovementImmediately. 자세한 흐름은 BP_STRUCTURE.md. 컴포넌트 `Box`(Box Collision, Hidden in Game, Custom: Query Only, Object Type `LightCencer`, WorldDynamic/PhysicsBody/Pawn Overlap — 보라 블록은 WorldDynamic/PhysicsBody를 Ignore하지만 LightCencer는 안 건드리므로 잡힘).
- `OnComponentBeginOverlap(Box)` → Cast To BP_AvilityBlock → Branch(`ResetBlock`) → `ResetToStart`.
- BP_AvilityBlock `ResetToStart`: Branch(`Move == Physics`) → Cast(GetPlayerCharacter → BP_Charactor) → `HeldBlock == Self`면 `DropBlock` → (모든 경로 합류) `StaticMesh.SetWorldLocationAndRotation(ResetLocation, ResetRotation, Sweep 끔, Teleport 켬)` → `SetPhysicsLinearVelocity(0)` → `SetPhysicsAngularVelocityInDegrees(0)`. `ResetLocation`/`ResetRotation` = BeginPlay 끝에서 StaticMesh 월드 위치/회전 저장(Scale은 노랑/하늘 능력과 충돌하므로 저장 안 함). 능력 상태는 건드리지 않음.
- 블록 시작 위치가 구역 안이면 BeginOverlap이 안 생겨 동작 안 함.


### 1-3-3. BP_Pickup — 손전등·필터 줍기 (송신 + BPI_Interact, 2026-10-24 추가·동작 확인)
| 인스턴스 설정 | 설명 | 기본값 |
|---|---|---|
| `PickupType` | Flashlight / Filter (`EN_PickupType`) | Flashlight |
| `FilterColor` | 필터 색 (`EN_LightColor`) | Red |
| `SignalTargets` | 주울 때 한 번 Activate | 비어 있음 |
- F → GI `UnlockFlashlight`/`UnlockColor` → `SendActivate` → 플레이어 `RefreshFlashlight` → Destroy. BeginPlay에서 이미 가진 종류면 `SendActivate` 후 Destroy. 자세한 흐름은 BP_STRUCTURE.md.
- 제한은 `BP_RealGameMode` 맵에서만(BP_Charactor `CanUseFlashlight`/`CanUseColor`가 `UnlockAll` OR 진행 데이터로 판정). `BP_TestGameMode`는 전부 사용.
### 1-3-4. BP_FilterReturn — 필터 반납 테이블 (송신 + BPI_Interact, 2026-10-25 추가·동작 확인)
- 인스턴스 설정: `SignalTargets`만. F → (NOT Returned AND 필터 1개 이상) → TurnOff → 가진 필터 전부 GI RemoveColor + 자리 메시(Red/Green/BlueSlot) 표시 → SendActivate → GI `MarkReturned(ReturnKey)`. ReturnKey = 맵 이름 + "_" + 액터 내부 이름 → `S_PlayerProgress.CompletedReturns`. BeginPlay에서 IsReturned면 Returned=true + SendActivate(자리 메시는 안 켬). 테이블을 지우고 다시 놓으면 키가 바뀜. 자세한 흐름은 BP_STRUCTURE.md.
### 1-4. BP_Door — 문 (수신)
| 인스턴스 설정 | 설명 | 기본값 |
|---|---|---|
| `ChannelRequired` | 채널별 필요 신호 수 | `0 → 1` |
| `StartOpen` | 열린 채 시작, 신호 켜짐=닫힘 (IsStartOn 0 → StartOpen) | 꺼짐 |
- 잠금(채널 1, 2026-10-08): 변수 `Lock`. OnChannelActive Switch 1 → `CloseDoor` → `Lock = true`. Switch 0 → Branch(`Lock`) False → `OpenDoor`. OnChannelDeactive는 그대로(잠긴 뒤 0번 꺼짐 = 닫기 재호출, 무해). 1번 꺼짐은 무시 → 영구 잠금. ChannelRequired `1 → 1`.
- `OpenTime`(열리는 시간, 1초)은 인스턴스 설정(2026-10-30, BP_Door·BP_Door2). `OpenDistance`(문짝 이동 거리, 100)는 BP 내부 고정값.
- 좌우 문(LeftDoor/RightDoor) + DoorFrame, Timeline Play/Reverse라 도중에 꺼져도 자연스럽게 되돌아감.
- StartOpen 구현: Construction에서 `Left/RightCloseLocation` = 문짝 RelativeLocation 저장 → StartOpen이면 문짝을 열린 위치(±OpenDistance Y)로 SetRelativeLocation. BeginPlay: SetPlayRate(1/OpenTime) → StartOpen이면 `DoorTimeLine.SetNewTime(GetTimelineLength)` (빠지면 Reverse가 0에서 시작해 애니메이션 없이 즉시 닫힘).

### 1-5. BP_Light — 맵 광원 (수신)
| 인스턴스 설정 | 설명 | 기본값 |
|---|---|---|
| `LightColor` | 기본 색 Red/Blue/Green (Construction Script에서 `LightColorValue`/`FirstColorValue` 설정) | `Red` |
| `StartOn` | 켜진 채 시작. 0번 신호 반전 (IsStartOn 0 → StartOn). `LightActiveMode`/`EN_LightActiveMode`는 2026-10-05 삭제 | 켜짐 |
| `ChangeColor` | `Red`/`Green`/`Blue`(신호 켜지면 그 색, 꺼지면 원래 색) / `Rotate`(켜질 때마다 R→G→B 회전, 꺼짐 무시 → ReOn 버튼과 사용) | `Rotate` |
| `ChannelRequired` | 채널별 필요 신호 수 | `0 → 1` |
| `LightLength` | 판정 거리 | 5000 |
| SpotLight `Outer Cone Angle` | 판정 원뿔 각도 (SpreadRadius / 감지 박스 자동 계산) | 컴포넌트 값 |
| `PitchAngle` / `YawAngle` / `MoveOffset` | 2·3·4번 신호 회전 각도 / 이동 위치 | - |
| `RotateTime` / `MoveSpeed` | 회전 시간(초) / 이동 속도(초당 거리). 2026-10-30 인스턴스 설정으로 변경 | BP 기본값 |
- `PlayerRange`(8000, 플레이어가 이 거리 안일 때만 판정), `ScanInterval`(0.1초, 판정 주기)은 BP 내부 고정값.
- 맵 광원만으로도 능력 발동 (2026-10-02 변경: `ReCalculate`에서 `Map_Contains(ActiveContributions, PlayerCharacter)` + Select 제거, `CurrentColor`를 Switch on Int에 직접 연결). 단 PlayerRange 밖이면 판정 안 함.
- 예시: 빨강 광원 + 파랑 손전등 = 보라 통과 / StartOn 끔+Togle 버튼(Ch 0) = 스위치 조명 / ChangeColor Rotate + ReOn 버튼 = 색 금고.

### 1-6. BP_AvilityBlock — 능력 블록 (수신)
| 인스턴스 설정 | 설명 | 기본값 |
|---|---|---|
| `ColorMode` | `Default`(비춘 색 그대로, UseColor 무시) / `ReactOnly`(합친 색 == UseColor일 때만, All이면 전부) / `OwnColor`(UseColor를 고유색으로 품고 들어온 빛과 OR 합성) | `Default` |
| `UseColor` | All / Red / Blue / Green / Purple / Yello / SkyBlue / None (예전 `ReactColor`를 이름 변경) | `All` |
| `Move` | Fixed / Physics / PatrolReturn / PatrolRotation / PatrolRestart / PatrolOnce(끝에서 멈춤, 2026-10-30) | `Fixed` |
| `RestartDelay` | 채널 1 "처음으로" 후 재출발 대기(초) | 0.5 |
| `MovePoint`, `MoveSpeed` | Patrol 경유지, 속도 | 비어 있음 / 500 |
| `WaitTrigger` | 켜면 신호 받을 때까지 Patrol 대기, 신호 꺼지면 그 자리에서 멈춤 | 꺼짐 |
| `StartMoving` | WaitTrigger에서 처음부터 이동, 신호 켜짐=정지 (IsStartOn 0 → StartMoving) | 꺼짐 |
| `ChannelRequired` | 채널별 필요 신호 수 (0 = WaitTrigger 이동) | `0 → 1` |
| `IsUserStaticMesh` + `UserStaticMesh` | 외형 교체 (발판·벽으로 활용) | 꺼짐 / 없음 |
| `CanGrab` | F로 들기 허용 (`CanInteract` = Move==Physics AND CanGrab2) | 꺼짐 |
| `CanGrabSkyBlue` | SkyBlue로 작아진 동안 들기 허용. `CanGrab`이 꺼진(평소 못 드는) 블록도 작아지면 들 수 있게 하는 용도 | 켜짐 |
- 들기 상태는 런타임 복사본 `CanGrab2`로 관리(Construction Script에서 `CanGrab2 = CanGrab`). Green Freeze / Yellow Y_Grow / Purple P_Silent에서 `CanGrab2 = false`, SkyBlue `SB_Down`에서 `CanGrab2 = CanGrabSkyBlue`. Red/Blue는 그대로.
- BP_Charactor 잡기: `GrabBlock` = `GrabComponentAtLocationWithRotation`(메시 현재 위치/회전) → 메시 Pawn 응답 Ignore → `TurnOff` → `HeldBlock`. Tick: `IsValid(HeldBlock)` → `CanInteract`(Message) → NOT이면 `DropBlock`(Pawn 충돌 복구, 들고 있다가 초록 정지 등으로 못 들게 되면 자동 놓기) / 아니면 `SetTargetLocationAndRotation`(카메라 위치 + Forward×HeldDistance, 회전은 ControlRotation의 Yaw만).
| Red: `InnerRadius`/`OuterRadius`/`ExplosionForce`/`PushForce`/`Exp_PlayerForce` | 폭발 | 200 / 1250 / 2500 / 2000 / 2000 |
| Blue: `MaxPullSpeed`/`PlayerMaxPullSpeed` | 당기기 | 3000 / 2000 |
| Yello/SkyBlue: `ChangeSpeed`/`UpScale`/`DownScale` | 크기 변화 | 0.3 / 2 / 2 |
| Green / Purple | 튜닝 변수 없음 | - |
- `MovePoint`: Show 3D Widget 벡터 배열, 블록 로컬 좌표. BeginPlay 쯤 `GetTransform → TransformLocation`으로 `WorldPatrolPoints`에 변환(이후 블록이 움직여도 경로 고정). `VInterpTo_Constant(MoveSpeed)`로 `PatrolIndex` 순서대로 이동.
- 움직이는 발판/벽은 별도 BP 없이 이 블록으로 만듦: UserStaticMesh + Patrol + WaitTrigger + 버튼/발판 SignalTargets.
- 예시: 버튼으로 출발하는 엘리베이터 / 초록으로 멈추는 발판 / 보라 벽 / 노란 계단 / 파랑으로 끌어와 발판 누르기.
- 충전·유지·쿨타임은 인스턴스 설정 불가 (`AvilityConfig` 함수에 색별 고정).

### 1-7. BP_Hatch — 다락문 (수신, 부모 BP_Activate)
| 인스턴스 설정 | 설명 | 기본값 |
|---|---|---|
| `ChannelRequired` | 채널별 필요 신호 수 | `0 → 1` |
| `WaitTrigger` | 켬 = 신호형(OnActive 열림 / OnDeactive 닫힘). 끔 = 반복형(BeginPlay부터 열림→`HatchWait`→닫힘 반복, 신호 무시) | 꺼짐 |
| `IsDown` | 여는 방향 반전 (Select: false -90 / true 90) | 꺼짐 |
| `StartOpen` | 신호형에서 열린 채 시작, 신호 켜짐=닫힘 (IsStartOn 0 → StartOpen). 반복형은 무시 | 꺼짐 |
| `UseUserStaticMesh` + `UserStaticMesh` | 외형 교체 (Construction) | 꺼짐 / 없음 |
| `OpenTime` / `HatchWait` | 여닫는 시간 / 반복형 대기 시간 | 1 / 2 |
- 각도 90 고정. 빛·능력과 무관 (원래 BP_AvilityBlock의 `Move=Hatch`였으나 초록 정지 등 능력과 얽혀 2026-10-03 별도 BP로 분리, `EN_BlockMove`에서 Hatch 항목 삭제).
- 경첩 = `StaticMesh` 컴포넌트 메시의 −X 면 모서리(높이 중앙), 축 = 메시 RightVector. 경첩 변은 액터 Z 회전으로 선택.

### 1-8. 기타 애셋
- `BP_Activate`: 수신 부모. 직접 배치하지 않음.
- `BP_LightBlock`: BP_AvilityBlock으로 가는 리다이렉터(이름 변경 흔적). 사용 안 함.
- 인터페이스: `BPI_Activatable`(Activate/Deactivate), `BPI_Interact`(Interact, GetInteractText), `BPI_LightInteractable`(Add/RemoveColorContribution).
- Enum: `EN_ButtonMode`, `EN_ChangeColor`, `EN_LightColor`, `EN_ColorState`, `EN_ColorMode`, `EN_BlockMove`, `EN_Avility`(Ready / Active / CoolTime).

---

## 2. 구현 메모

### 2-1. 신호 시스템 (BP_Activate)
- `Activate(Channel)` → `ChannelCount[Channel] = Find + 1` → (Count ≥ 필요 개수 AND NOT `ActiveChannels`.Contains) → `ActiveChannels`.Add → `OnChannelActive(Channel)`. `Deactivate(Channel)` → `Max(Find - 1, 0)` → (Count < 필요 개수 AND Contains) → Remove → `OnChannelDeactive(Channel)`. 필요 개수 = `Max(Select(Map_Contains ? Map_Find(ChannelRequired) : 1), 1)` (사용자 구현: Select 유지, False 옵션 상수 1. `Max(Map_Find, 1)`만으로도 같음) (0이면 Deactivate 조건 `0 < 0`이 영원히 false라 안 꺼지는 버그가 실제로 났음 — Map에 +로 추가하면 `0→0`이 생김). 비교 노드의 A는 `Map_Add` 뒤에 새 `Map_Find(ChannelCount)`로 읽을 것: 순수 노드는 소비하는 실행 노드마다 재계산되므로 `+1`/`Max` 출력을 Branch에 그대로 쓰면 Add 후 한 번 더 더해지거나 빼져서 AND가 틀어짐.
- `OnChannelActive`/`OnChannelDeactive`(함수): 부모 기본 구현은 비어 있음. 모든 자식이 오버라이드: Parent 호출 → `Switch on Int(Channel)` → 핀 번호 = 기능 번호표(기능 추가 시 Add pin). 블록 0 → `TriggerPaused=false/true`, 다락문 0 → `WaitTrigger`면 `HatchOpen/Close`, 문 0 → 열기/닫기 Custom Event, 광원은 1-0 번호표 참고. `S_SignalTarget` 구조체(Target, Channel).
- Timeline은 함수에 못 넣으므로 함수에서 이벤트그래프의 Custom Event 호출.
- 송신 쪽 `SendActivate`/`SendDeactivate` = ForEach(SignalTargets) → Break S_SignalTarget → Activate/Deactivate (Message, Target, Channel).
- 발판 `UpdatePressure`: Begin/End Overlap마다 `GetOverlappingActors` 재집계 → 이전 상태(`IsOn`)와 다를 때만 송신. Trigger 박스는 움직이는 윗판의 자식이 아니라 형제로 둘 것(자식이면 깜빡임).

### 2-2. 빛 감지
- BP_Charactor(손전등): `SpotLight` 위치에서 13점(중심 1 + 40% 링 4 + 100% 링 8) 매 틱 레이캐스트. `CurrentHit`/`LastLitActor` diff → `LightActor`/`UnLightActor`. 계속 비추는 중 색 변경이 반영되도록 `LightActor`는 매번 호출.
- BP_Light(맵 광원) — 최적화 구조:
  ```
  BeginPlay → Set Timer by Event(LightScan, ScanInterval, Looping, Initial Start Delay Variance = ScanInterval)
  LightScan:
    TurnOn? ─아니오→ ClearLitActor
    GetDistanceTo(PlayerPawn) ≤ PlayerRange? ─아니오→ ClearLitActor
    Set Candidates ← LightSencer.GetOverlappingActors(BP_AvilityBlock)   (순수 노드라 변수에 캐싱)
    Length(Candidates) > 0? ─아니오→ ClearLitActor
    Clear CurrentHit → ForEach(Candidates) → IsLit(블록) true면 CurrentHit.AddUnique
    Completed → 기존 diff(UnLightActor / LightActor) → Set LastLitActor
  ```
  - `IsLit(Target)`: Start=SpotLight 위치, Center/Extent=`GetActorBounds`(Extent×0.8). 로컬 배열 `Dirs`(중심 (0,0,0) + (±1,±1,±1) 8개)를 돌며 Point=Center+Dir×Extent → 거리 ≤ LightLength AND `Dot(Normal(Point−Start), Forward) ≥ DegCos(OuterConeAngle)` → LineTrace(Visibility) HitActor==Target이면 즉시 Return true. 전부 실패 → Return false.
  - Construction Script: `SpreadRadius = LightLength × DegTan(OuterConeAngle)`, 감지 박스 `LightSencer`(SpotLight 자식) Extent=(L/2, R, R), 위치=(L/2,0,0). `TurnOn = StartOn` + `SetVisibility(StartOn)` (켜짐/꺼짐 양쪽 다 매번 설정: Construction 재실행 시 이전 false가 남지 않게).
  - 감지 박스 Object Type = `LightCencer` 커스텀 채널(DefaultEngine.ini, 기본 Overlap). 보라 능력이 WorldDynamic 등을 Ignore해도 감지되게 하려고 전용 채널 사용. 박스 응답은 WorldDynamic / PhysicsBody만 Overlap.
  - 예전 13점 격자 방식(BuildTrace, TracePoint, RingCount, PointPerRing)은 먼 거리 빈틈 문제로 폐기됨.
- LightActor/UnLightActor: `IsValid` + `DoesImplementInterface(BPI_LightInteractable)` 후 `AddColorContribution(Source, Color)`/`RemoveColorContribution`. 기여는 Source별로 덮어씀(누적 아님).

### 2-3. BP_AvilityBlock
- 능력 흐름: `ChargeAlpha` 0→1(색마다 ChargeTime, Green 0.2초) → `AvilityStart` → `HoldRemain` 카운트다운(빛 받는 동안 갱신) → 0이면 `AvilityEnd` + CoolTime.
- 색 합성 (`ReCalculate`): ActiveContributions 합 → 비트 인코딩(R≥0.5 → 1, G → +2, B → +4)으로 `CurrentColor`. Sequence then_3에서 `ColorMode == OwnColor AND CurrentColor != 0`이면 `CurrentColor = CurrentColor | Select(UseColor)`(All 0, Red 1, Green 2, Yello 3, Blue 4, Purple 5, SkyBlue 6, None 0). 빛이 없으면(0) 고유색만으로는 발동 안 함. (단 흰 손전등 (0,0,0)으로는 고유색이 발동하는 것을 사용자가 확인함 — 실제 조건은 기여 존재 여부 기준일 수 있으니 수정 시 BP 확인) 이후 Switch on Int(0/7 → None, 1 Red, 2 Green, 3 Yello, 4 Blue, 5 Purple, 6 SkyBlue).
- 빛 주체 판정 `GetLightSource`(Pure, 2026-10-06): 출력 `actor`/`IsPlayer`/`Found`. `ActiveContributions.Contains(GetPlayerCharacter)`면 플레이어, 아니면 `Length>0`이면 `Keys[0]`(첫 광원), 없으면 None/false/false. 빨강 `Push`(Physics 자기 밀기)와 파랑 `BlockPull`(Physics 끌어오기, 목표 = Source 위치 + Source.ForwardVector × `Front`)이 `Select(Found ? actor : GetPlayerCharacter)`로 기준 액터를 정함. 광원 기준이면 광원 액터 Forward를 쓰므로 SpotLight가 액터 정면을 향해야 함. 바로 위에서 비추는 광원은 XY 차이가 0이라 위쪽(UpForce)으로만 힘이 감.
- `ColorCheck` 매크로: `IsLit = (ColorMode != ReactOnly) OR (UseColor == All) OR (색 == UseColor)`.
- Construction Script: ColorMode Switch로 메시(Default `SM_Element_Plain`, OwnColor `SM_Element_Chain`, ReactOnly `SM_Element_Trick`) → Move Switch로 `SM_Floor_Plain_Light` 표시(Patrol AND NOT IsUserStaticMesh면 SetStaticMesh(SM_Floor_Plain_Light), 나머지는 SetStaticMesh(None). NoCollision. 2026-10-30 SetVisibility 숨김에서 변경: 숨겨도 컴포넌트가 GetActorBounds에 포함돼 Physics 블록이 처음 자리에서 멀어지면 맵 광원 IsLit 표본점이 어긋나기 때문. 테스트 대기) → `IsUserStaticMesh`면 UserStaticMesh 후 종료, 아니면 crystal 슬롯에 `M_BlockBase` MID 생성(`BlockMID`) → 크리스탈 색 Select(ColorMode): Default 흰색 / ReactOnly·OwnColor 둘 다 `Lerp(TargetColor, 흰색, 0.05)` (2026-10-30 붙여넣기 기준, 예전 ReactOnly 0.3 / OwnColor TargetColor에서 바뀜 — 모드 구분은 메시로) → `BlockColor` + `StartColor`. MID는 모드와 상관없이 항상 만들어야 함(런타임 색 변경·보라 Opacity가 BlockMID 사용).
- 발광: `M_BlockBase` Emissive = BlockColor × Texture × `Lerp(0.05, 3, GlowAmount)`. 현재 `GlowAmount`는 BP에서 안 건드림(기본 0 → 은은한 기본 발광만). 충전 비례 발광은 사용자가 보류.
- Trigger: `AvilityTick`에서 `WaitTrigger && TriggerPaused`면 Patrol 스킵. BeginPlay에서 `TriggerPaused = WaitTrigger AND NOT StartMoving`, `OnChannelActive` Switch 0 → false, `OnChannelDeactive` Switch 0 → true.
- Yellow/SkyBlue: `BaseSize × Lerp(1, UpScale 또는 1/DownScale, Alpha)`. 독립 Timeline(0→0.4초)을 `Grow`(Play) / `Y_Reset`·`SB_Reset`(Reverse)로 구동. ChargeAlpha를 직접 쓰면 차징 중에 커지는 문제가 있어서 분리함.
- Purple:
  - `M_BlockBase` = Translucent + `Opacity` 파라미터. Cast Dynamic Shadow as Masked 켜야 그림자 생김(Translucent는 기본적으로 그림자 없음). Nanite는 Translucent 미지원이라 이 머티리얼 쓰는 메시(`SM_Element_Plain`, `SM_Element_Chain` 등)는 Nanite 끔.
  - `P_Collision`: 프로필 이름 저장 → Physics면 Pawn/WorldDynamic/PhysicsBody Ignore(WorldStatic은 유지해서 바닥 안 뚫게), 아니면 WorldStatic까지 Ignore. `P_CollisionReset`: 저장한 프로필로 복구. Visibility 채널은 절대 안 건드림.
  - SafeReset(EventGraph Custom Event): AvilityEnd 보라 경로는 `Set PurpleResetPending(true) → SafeReset`. SafeReset은 `PurpleResetPending` 확인 → `BoxOverlapActors`(Bounds×0.9, Pawn만, 자신 제외) → 겹치면 Delay 0.2 후 재호출, 비면 `PurpleResetPending=false → P_CollisionReset → P_Reset`. AvilityStart 보라 경로 맨 앞에서 `PurpleResetPending=false`(대기 취소).
  - 보라 Physics 블록을 떨어뜨릴 바닥은 일반 Static Mesh(WorldStatic)가 아니라 BP_AvilityBlock(UserStaticMesh, Fixed)으로 깔아야 함 — WorldStatic은 유지, 블록끼리는 Ignore라서.
  - Object Types를 Pawn만 두는 이유: 블록끼리 겹치면 서로를 기다려 무한 유지(교착)됨. 블록끼리는 메시 Physics의 Max Depenetration Velocity 100으로 천천히 분리.
  - 블록 안에서는 손전등 레이가 블록을 못 맞힘(콜리전 내부 시작) → 통과 중 HoldRemain이 끝날 수 있음 → SafeReset이 이를 커버.

### 2-4. BP_Hatch
- 회전: Timeline(Alpha 0→1) Update → `Angle = Alpha × Select(IsDown)` → `NewLoc = HingePoint + RotateAngleAxis(HatchStartLoc − HingePoint, Angle, HingeAxis)`, `NewRot = ComposeRotators(HatchStartRot, RotatorFromAxisAndAngle(HingeAxis, Angle))` → `SetActorLocationAndRotation`(Sweep 끔).
- Construction: `UseUserStaticMesh`면 SetStaticMesh → (양쪽 다) `MeshClosedTransform`(변수 이름 끝에 공백 있음) = StaticMesh.GetRelativeTransform → `StartOpen AND WaitTrigger`면 StaticMesh `SetWorldLocationAndRotation`(Hinge + RotateAngleAxis(MeshLoc − Hinge), Compose(MeshRot, RotatorFromAxisAndAngle)) = 에디터 미리보기. 액터가 아니라 컴포넌트를 돌리는 이유: 컴포넌트는 Construction 재실행마다 템플릿에서 재생성되어 누적되지 않음.
- BeginPlay: StaticMesh `SetRelativeTransform(MeshClosedTransform)`(Teleport)로 미리보기 되돌림 → `HatchStartLoc/Rot` 저장 → `HingePoint = TransformLocation(StaticMesh.GetComponentToWorld, (−BoxExtent.X,0,0)+Origin)`(StaticMesh.GetBounds) → `HingeAxis = StaticMesh.GetRightVector` → `WaitTrigger` 꺼짐이면 `HatchOpen`, 켜짐 + `StartOpen`이면 `Timeline.SetPlaybackPosition(GetTimelineLength, FireEvents=false, FireUpdate=true)`(Update로 즉시 열린 자세 + Reverse가 끝에서 시작). 문은 Construction에서 문짝을 직접 열어 두므로 `SetNewTime`(Update 없음)으로 충분.
- `HatchOpen`/`HatchClose`: `Timeline.SetPlayRate(1/OpenTime)` → Play / Reverse (현재 위치에서 이어서). SetPlayRate는 Timeline 컴포넌트 변수에서 끌어야 함(빈 곳 검색 시 BlendSpace 버전이 나옴).
- Finished → `WaitTrigger` 꺼짐이면 `Delay(HatchWait)` → Direction==Forward면 `HatchClose`, 아니면 `HatchOpen` (루프).
- `OnChannelActive`/`OnChannelDeactive` 오버라이드: Parent 호출 → Switch 0 → `WaitTrigger` 켜짐이면 `HatchOpen`/`HatchClose`. Parent 대신 자기 자신을 호출하면 Infinite loop 에러.

### 2-5. 디테일 패널 카테고리 순서
자식 BP의 Details 카테고리 순서는 자식 BP의 My Blueprint 카테고리 정렬을 따름. 부모 카테고리를 위로 올리려면 자식에서 "Show Inherited Variables" 켜고 부모 카테고리를 맨 위로 드래그.

---

## 3. Git / 배포 구조

- 저장소: `https://github.com/Retiner/GaesinLight.git`, 이 폴더(`C:\unreal\GaesinLight`)가 로컬 클론.
- `Content/Assets/`(Materials, StaticMeshes, Textures)는 git 제외 — 구글 드라이브로 별도 배포(`ArtManifest.json`), `.gitignore`에 `/Content/Assets/`. 새 아트 애셋은 같은 폴더 구조로 채울 것.
  - 따라서 `M_BlockBase`의 Cast Dynamic Shadow as Masked 설정도 git으로 안 옮겨짐 — 팀원에게 따로 알릴 것.
- `Config/DefaultEngine.ini`에서 공유해야 하는 것: `r.VolumetricFog.HistoryWeight=0`(안개 잔상 방지), `LightCencer` 콜리전 채널(맵 광원 감지), `GameInstanceClass=BP_GameInstance`(작업 6). **2026-10-24 사용자: 다음 커밋에 Config 포함**(Game Instance Class 줄 때문).
- 커밋 전엔 항상 `git status`로 의도치 않은 변경(에디터 자동저장 애셋 등) 확인.
- 사용자가 커밋을 원하지 않을 때가 많음 — 명시적으로 요청할 때만 커밋.
- 기능·설정·채널·컴포넌트 구조가 바뀌거나 설계 결정이 나면, 묻지 않고 그 턴에 **모든 문서**를 반영: `레벨 제작 가이드.html`(저장소 맨 위. `#channels` 채널 표 + `#changes` 최근 변경 절에 날짜별 한 줄씩 매번 추가. README.md는 2026-10-30 삭제됨 — 다시 만들지 말 것), BP_STRUCTURE.md(BP 구조 + 갱신 기록), CLAUDE.md(작업 표·메모), 필요하면 `Docs/assets/guide.css`·`guide.js`. 답변 끝에 고친 문서를 한 줄로 알림(2026-10-23 사용자 지시, 2026-10-25 "리드미랑 HTML 다른 문서도 다 자동으로"로 확대). 새 장치는 `<details class="chapter" id=…>` + 목차 링크(`nav.local-toc`) 추가. 커밋은 여전히 요청 시에만.
- 커밋/PR에 `Co-Authored-By: Claude` 등 Claude 표기 금지 (2026-10-05: GitHub 기여자에 claude가 떠서 사용자가 제거 요청).

## 4. 작업 스타일

- 사용자는 Blueprint를 배우는 중 — 직접 그래프를 만들고 K2Node 텍스트를 붙여넣어 검증받는 방식. 대신 만들어주지 말 것.
- 설명은 목적 → 노드 역할 → 구체적 행동 순서, 이유 포함, 한 번에 한 단계(하위 단계로 쪼개서). 세션이 길어져도 설명을 압축하지 말 것.
  - 형식(2026-10-30 사용자 예시 "이런 식으로 하는걸 기본으로", 기본값): 확인한 것/못 한 것 한 줄 → `N. 제목` + 이 단계가 다루는 경우 → **1부. 사용하는 것**(부모·다른 BP 이벤트는 누가 제공하는지 + **꺼내는 곳** 메뉴 경로·없을 때 확인할 것 / **출력 핀** 표: 핀 | 위치 | 담겨 오는 값·쓰는 이유(연결 안 하면 그렇다고) / **노드** 표: 이름 | 출처 | 뜻·역할 / **변수** 표: 이름 | 뜻·역할) → **2부. 작업 순서** N-1, N-2… 안에 ①② (굵은 소제목 + "A의 X 핀을 B의 Y에 연결", "값은 -1", "False는 비워 둡니다" 같은 문장 목록 → **의도:** 문단 → 일부러 안 넣는 것과 이유) → 완성 흐름 화살표 → (필요하면 값 표) → **테스트** 표 + "번호로 알려 주세요" + "N번이 안 되면 ○○ 그래프" → "Compile → Save 하고 그래프를 붙여 주세요" + 다음 단계. 노드는 약어 말고 실제 이름으로. 사용자 그래프를 고칠 때도 같은 형식(지울 노드 → 새로 놓을 노드 → 연결).
- 사용자가 스스로 변형(더 나은 방식)을 설계하는 경우가 많음 — 타당하면 받아들이고 검증.
- 한국어로 대화.

## 5. 작업 목록 (2026-10-02)

| # | 작업 | 내용 | 규모 |
|---|---|---|---|
| 1 | ~~능력 블록 색 합성 모드~~ ✅ 완료 | 기존 ReactColor(All / 특정 색) 외에, 블록이 고유 색을 갖고 있다가 들어온 빛과 합친 색의 능력 발동 (예: 고유 빨강 + 파랑 빛 = 보라) | 중 |
| 2 | ~~맵 광원 단독 발동~~ ✅ 완료 | `ReCalculate`의 플레이어 기여 확인(Map_Contains + Select) 제거 | 소 |
| 3 | ~~다락문~~ ✅ 완료 | 별도 BP `BP_Hatch`로 구현 (경첩 회전, 신호형/반복형, IsDown) | 중 |
| 4 | 맵 광원 확장 | 방향 회전, 지정 위치로 이동, 시작 시 켜짐/꺼짐 선택, 신호 받아야 움직일지 / 기본으로 움직일지, 처음 켜진 광원은 첫 신호에 꺼지도록 로직 수정 | 대 |
| 5 | ~~신호 채널~~ ✅ 완료 (2026-10-04) | 버튼/발판 → 한 액터에 기능 하나만 on/off 하던 것을, 채널(신호 값)별로 다른 기능이 켜지게 변경 | 대 (구조 변경) |
| 6 | ~~손전등·필터 획득~~ ✅ 완료 (2026-10-24) | 시작 시 손전등/색 변경 불가. 맵의 손전등·색 필터 아이템(책상 위에 놓인 형태, 2026-10-23)을 상호작용으로 획득해야 사용 가능 (획득 상태로 자격 판정) | 대 |
| 7 | 필터 교체 모션 | 색 변경 시 필터 메시를 손전등 밖으로 빼고 → 색 변경 → 원위치 (단순 이동 연출) | 소~중 |
| 8 | ~~파랑 당기기 조건~~ ✅ 완료 (2026-10-05) | Blue 능력 중 플레이어를 끌어당기는 쪽(비-Physics 블록)은 플레이어가 그 블록에 빛을 쏘고 있을 때만 발동. 구현: `PlayerPull` 입구 → Branch(`ActiveContributions.Contains(GetPlayerCharacter)`) → LaunchCharacter. 매 호출 검사라 손전등을 돌리면 즉시 멈춤. 싱글플레이 전제(멀티 시 Keys→Cast to BP_Charactor로 교체) | 소 |
| 9 | 거울 (2026-10-05 추가) | 빛을 정반사로 튕겨내는 거울. 현재 빛은 스포트라이트(원뿔) 판정이라 원뿔 그대로 반사하기 어려움 → **원통형 빔**으로 반사하는 느낌으로 구현(반사 지점에서 반사 방향으로 일정 반경의 원통 판정). 회전·이동 신호는 만들지 않음(2026-10-25 사용자 결정) | 대 |
| 10 | 시작 화면·UI (2026-10-23 추가) | 게임 시작 화면, 설정창, 상호작용 가능할 때 "F 키를 눌러 ○○" 문구 표시(`BPI_Interact.GetInteractText` 활용), ESC 일시정지 메뉴(계속 / 설정 / 스테이지 초기화 / 게임 종료) | 중~대 |
| 11 | 저장·이어하기 (2026-10-23 추가) | 껐다 켜도 진행 상황 유지. 체크포인트에서 시작 또는 종료 직전 상태에서 시작. 작업 6의 `S_PlayerProgress` → `BP_SaveGame` 구조 확장 | 대 |
| 12 | 체크포인트 (2026-10-23 추가, 2026-10-25 설계 확정·진행 중) | 지나가면 부활·이어하기 위치 갱신. **사용자 결정(2026-10-25)**: 방(구역) 입구 단위, 이어하기 때 그 방 퍼즐은 처음부터(버튼·발판·블록·문·광원 상태 저장 안 함). 레벨을 다시 열 때 되살리는 것은 이미 기록 중인 것만 = 줍기(가진 손전등·필터) + 반납 테이블(CompletedReturns). 트리거·JustOn 버튼 기록은 안 함. 체크포인트 데이터는 `S_PlayerProgress`에 함께(저장 시 구조체 하나만 복사): `CheckpointLevel`(Name, 비면 체크포인트 없음) + `CheckpointTransform`(Transform). 레벨 시작 시 플레이어가 GI 확인 → 같은 레벨이면 그 위치로. BP_Respawn 플레이어 소환은 지금처럼 구역 지정 위치(체크포인트와 무관) | 중 |
| 13 | ~~BP_Respawn 플레이어 리스폰~~ ✅ 완료 (2026-10-23) | bool 두 개(`ResetBlock` / `ResetPlayer`)로 블록·플레이어 각각 되돌릴지 설정. 플레이어는 구역마다 **지정한 위치**로 소환(사용자 확정 2026-10-23, 체크포인트와 무관) | 소~중 |
| 14 | ~~필터 반납~~ ✅ 완료 (2026-10-25, 동작 확인 — 가이드 #returntable·BP_STRUCTURE 반영. 아래 기록 중 "보류"·RequiredColors 안은 지난 내용) (2026-10-23 추가) | 스테이지 끝에서 필터를 반납 → 반납대가 송신 장치처럼 `SignalTargets`로 채널 신호(예: 문 열기). 반납 시 `Progress.UnlockedColors`에서 제거. **보류(2026-10-25, 팀 의견 조율 중 — 1단계 `ReturnedColors`→`CompletedReturns` 안내까지 진행, 사용자 미완료일 수 있음)**. 직전 합의안: 맵마다 필터를 줍고 다음 맵 가기 전 **테이블에서 한 번에 반납**. `BP_FilterReturn` = 테이블 메시 + 색별 자리 메시 3개(RedSlot/GreenSlot/BlueSlot, 처음 숨김) + `RequiredColors`(Set, 전부 가져야 제출) + `SignalTargets`(출구 문 Ch0 열기 + 지나온 문 Ch1 잠금 등, 새 기능 불필요). F → TurnOff → 색마다 GI RemoveColor → 자리 메시 보임 → SendActivate → GI `MarkReturned(Key)`. 기록은 색이 아니라 **테이블 키**(맵 이름 + 액터 이름, Name)로 `S_PlayerProgress.CompletedReturns`(Set<Name>) — 맵마다 같은 색을 다시 줍고 반납하므로 색 기록은 다음 맵 테이블을 오작동시킴. 부분 반납 불가(상태 단순화). BeginPlay: `IsReturned(Key)`면 자리 메시 보임 + SendActivate | 중 | **2026-10-25 재개·변경(사용자 결정)**: `RequiredColors` 없음 → **가진 필터 전부 반납**, 조건은 필터 1개 이상(`HasAnyFilter` = Length(Progress.UnlockedColors) > 0, 0개로 출구가 열리는 것 방지). 문구 "필터 반납" / "반납할 필터가 없습니다". Interact = Branch(NOT Returned AND HasAnyFilter) → Returned=true → TurnOff → ForEach(To Array(UnlockedColors) 복사본) → RemoveColor + ShowSlot → SendActivate → MarkReturned(ReturnKey). ReturnKey = 맵 이름(Remove Prefix) + "_" + GetObjectName(Self). GI 함수 MarkReturned/IsReturned(Pure) 완료, 옛 ReturnColor/IsReturned(색) 삭제, S_PlayerProgress.ReturnedColors → CompletedReturns(Set<Name>). 복원(BeginPlay): IsReturned면 Returned=true + SendActivate만(어떤 색을 냈는지 기록이 없어 자리 메시는 안 켬).
| 15 | 배치한 플레이어로 빙의 (2026-10-24 추가, 나중에) | GameMode가 PlayerStart에 새로 스폰하는 대신, 맵에 직접 놓은 BP_Charactor를 조종. 방법: 배치한 캐릭터 Details → Pawn → `Auto Possess Player = Player 0`. 중복 스폰이 생기면 GameMode의 Default Pawn Class를 None으로(본 게임용 GameMode에서만). 레벨 이동 시 도착 맵에도 배치 필요 | 소 |
| 16 | ~~`BP_Light2` 상자형 맵 광원~~ ✅ 완료 (2026-10-25 — 가이드 #light2·채널 표·BP_STRUCTURE 반영. 파일 이름 BP_Light2, BP_Light1은 BP_Light2로 가는 리다이렉터(이름 변경 흔적, 에디터에서 안 보임. 참조 없음, 2026-10-30 사용자: 그냥 둠)) | BP_Light와 채널·기능 동일(0 전원 / 1 색 / 2 위아래 / 3 좌우 / 4 이동). 차이: 광원이 상자 안에 들어 있고, **4번(이동) 켜짐 → 상자에서 아래쪽 레일(트레일)을 따라 내려감, 꺼짐 → 다시 올라가 상자로 들어감**. 현재 BP_Light 복사본 + `SM_Sliding_Door` / `SM_Sliding_Hatch` 메시 추가 상태(10-24). **2026-10-25 사용자 결정**: 레일 직선 / 움직이는 부분 = 광원 헤드 + 연결부, 통로(상자·레일)는 고정, 문 연출 없음 / 회전(2·3번)은 내려온 광원만(상자 고정). 구현: `Carriage`(Scene) 아래에 연결부·HeadPivot을 두고, 이동은 SetActorLocation 대신 `Carriage.SetRelativeLocation(Lerp(기준, 기준+MoveOffset))`, 좌우 회전도 액터 대신 컴포넌트 회전. 기존 MoveTimeline·YawTimeLine 재사용. 진행(2026-10-25): BeginPlay `MoveStartLoc = Carriage.RelativeLocation`, `MoveEndLoc = MoveOffset + MoveStartLoc` ✅ / 이동 Update `Carriage.SetRelativeLocation(VLerp)` ✅ / 좌우 Update는 사용자가 새 컴포넌트 `PartRotate`에 `SetRelativeRotation(MakeRotator(Roll·Pitch = 기준, Yaw = 기준.Yaw + YawAngle×Alpha))`로 구현 — **기준 `ActorRotateBase`가 아직 Carriage.RelativeRotation에서 저장됨 → PartRotate.RelativeRotation으로 바꾸라고 안내(미확인)**, 이후 테스트. 완성 후 가이드 HTML `#channels` 표·맵 광원 장, BP_STRUCTURE에 `BP_Light2` 추가 | 중 |
| 17 | 빛 나오는 부분 발광 (2026-10-25 추가, 나중에) | 빛을 쏘는 장치의 **빛 나오는 부분이 지금 빛 색으로 빛나게**: 맵 광원 `BP_Light`/`BP_Light2` 헤드 렌즈, 거울 `BP_Mirror` 유리(반사 중), 필요하면 손전등. 꺼지면 발광 0. 기존 설계(2026-10-07 거울 보류안) 재사용: 머티리얼에 `GlowColor`(Vector)·`GlowStrength`(Scalar) 파라미터 → Emissive, BeginPlay에서 MID 생성, 슬롯 번호 변수 `GlowSlotIndex`. 광원 = 켜짐 + `LightColorValue`(색 바꾸기·전원 신호 때 갱신), 거울 = 빔 색(빔 여러 개면 합친 색, 흰 손전등 빔은 흰색). 머티리얼은 아트 담당이 파라미터를 넣어 준다고 가정(MI 부모가 엔진 기본이라 직접 수정 금지, 파라미터 없으면 Set…Parameter는 조용히 무시됨) | 소~중 |
| 18 | 필터 색별 중간 머티리얼 (2026-10-25 추가, 나중에) | 필터 메시의 **중간(유리) 부분 머티리얼이 필터 색에 따라 바뀌게**. 대상: `BP_Pickup`(PickupType=Filter일 때 `FilterColor`로), `BP_FilterReturn` 자리 메시(RedSlot/GreenSlot/BlueSlot), 작업 7 손전등 필터 메시. 방법 후보: Construction에서 `Select(FilterColor)` → 색별 머티리얼 3개 중 하나를 `SetMaterial(중간 슬롯 Index 또는 Slot Name)` / 또는 머티리얼 하나 + MID `SetVectorParameterValue(Color)`. 슬롯 번호·머티리얼은 아트 메시 확인 후 결정(작업 17 발광과 같은 MID 방식으로 묶을 수 있음) | 소 |
| 19 | 배경음악(BGM) (2026-10-28 추가) | 게임에 BGM 넣기. 맵(스테이지)별 곡, 레벨 이동 시 끊김/이어짐 처리, 설정창(작업 10) 볼륨과 연결 예정. 방법 후보: 맵마다 Ambient Sound / Level BP에서 Spawn Sound 2D, 또는 GameInstance가 Audio Component를 들고 레벨 이동에도 이어 재생. Sound Class(Music)로 묶어 볼륨 조절 | 소~중 |
| 20 | 3D 위젯(마름모) 크기 독립 (2026-10-28 추가). | 블록 `MovePoint`, BP_Respawn `PlayerRespawnLocation`, 광원 `MoveOffset` 등 Show 3D Widget 벡터는 **액터 로컬 좌표라 액터 Scale을 키우면 마름모 위치(거리)와 크기가 같이 커짐**(현재 계산 `TransformLocation(GetActorTransform, 점)`도 Scale을 곱함). 목표: 블록·구역 크기와 상관없이 같은 거리·크기. 방법 후보 ① 크기는 액터 Scale 대신 메시/Box 컴포넌트 Scale(또는 Box Extent 변수)로 조절 → 액터 Scale 1 유지(위젯·좌표 모두 해결, 레벨 제작 방식 변경 필요) ② 계산만 Scale 제외: `GetActorLocation + RotateVector(점, GetActorRotation)`(좌표 거리만 해결, 에디터 마름모 표시는 여전히 Scale 따라감). 사용자와 방식 결정 필요 | 소~중 |
| 22 | ~~능력 블록 이동 추가~~ ✅ 완료 (2026-10-30 사용자 "잘 되") — `PatrolOnce` 모드(CheckChange True 비움 = 끝에서 멈춤) + 채널 1 "처음으로"(`RestartFromStart`: PatrolIndex 0, PatrollCount 1, WorldPatrolPoints[0] Teleport, `RestartWaiting` + Retriggerable Delay(`RestartDelay`[I] 0.5)), Tick 앞 Branch(RestartWaiting). 가이드 #block-move·채널 표, BP_STRUCTURE 반영 | ① 새 Move 모드(가칭 `PatrolOnce`): 시작 → 끝까지 한 번 가고 멈춤 ② "처음으로 되돌리기": 이동 중/끝에서 신호가 오면 처음 위치로 즉시 순간이동 후 다시 진행. 제안: ②는 모드가 아니라 **채널 1(신호)** — 모든 Patrol 모드에 공통 적용되고 모드 수가 곱으로 늘지 않음. ① + 채널 1 = "끝에서 멈춤 → 버튼 → 처음으로 가서 다시 끝까지". 펄스라 `ReOn` 버튼 필요. 기존 PatrolRestart의 처음 위치 순간이동 로직 재사용 | 중 |
| 23 | 능력 블록 채널 2 "방향 바꾸기" (2026-10-30 설계 확정, 진행 중) | **사용자 결정**: 2번 = 상태형(켜짐 → 역방향, 꺼짐 → 정방향, **Togle·발판·Timed용**, ReOn 불가 — 켜짐·꺼짐이 연달아 와서 두 번 뒤집힘). 1번 "처음으로" = 펄스형(**ReOn용**). 구현: Custom Event `ReverseDirection` = Branch(Length(WorldPatrolPoints) > 1) → `PatrollCount = PatrollCount × -1` → `PatrolIndex = Clamp(PatrolIndex + PatrollCount, 0, Length − 1)`(위치 그대로, 그 자리에서 돌아섬). `OnChannelActive`·`OnChannelDeactive` 둘 다 Switch 2 → ReverseDirection(BP_Activate가 상태 바뀔 때만 부르므로 번갈아 호출됨). ChannelRequired `2 → 1`. Return 모드는 정방향이 고정이 아니라 켜짐·꺼짐 모두 "돌아서기". **남은 것**: 사용자 그래프 수정 확인(첫 붙여넣기는 Set PatrolIndex/PatrollCount가 서로 바뀌어 있었음) → 22-3 `CheckChange`를 진행 방향 기준 끝 판정으로((Count>0 AND Index==마지막) OR (Count<0 AND Index==0)) — Once가 0번에서 멈춤, Rotation/Restart의 0 보내기도 방향 반영. 2번 켜진 채 1번 처음으로 → 방향이 정방향으로 초기화되는 것, Return 모드에서 켜짐·꺼짐 둘 다 "돌아서기"인 것은 **고치지 않고 가이드에 주의점으로만 적기**(2026-10-30 사용자 결정). 동작 확인 후 가이드 #channels·#block-move·#changes, BP_STRUCTURE 반영 | 중 |
| 21 | 능력 블록 중력·무게 (2026-10-28 추가) | Physics 능력 블록이 중력이 약해 보임(천천히 떨어짐) → **기본 Physics 큐브와 같게**. 확인할 것: StaticMesh Physics의 Mass(kg) Override·Mass Scale, Linear/Angular Damping(기본 0.01 / 0), Enable Gravity, Max Depenetration Velocity(보라 분리용 100 — 낙하와 무관해야 함), 크기 능력(노랑/하늘)으로 바뀐 Scale에 따른 질량 변화, 매 틱 힘을 주는 코드(Push/BlockPull/잡기 Physics Handle) 남아 있는지. 기본 큐브와 Details 값을 나란히 비교해서 차이만 맞춤 | 소 |

- 작업 4 광원 회전 (2026-10-06 설계 확정, 사용자 결정 — 오프셋/Step/PingPong/Loop/방향키 연속 회전안 모두 폐기):
  - 컴포넌트: `Root → BaseMesh` / `HeadPivot(Scene, 관절 위치) → HeadMesh + SpotLight → LightSencer`, 전부 Movable. 헤드 회전 시 빛·감지 박스·IsLit 판정이 따라가는 것 확인함.
  - **Pitch = HeadPivot만, Yaw = 액터 전체**(포탑식). 맵에서도 위아래는 HeadPivot, 좌우는 액터를 돌려 시작 조준(Construction이 덮어쓰지 않음) → BeginPlay에서 `HeadBaseRot`/`ActorBaseRot` 저장.
  - 채널(실제 BP 기준, 2026-10-08 확인): 0 = 전원, 1 = 색, 2 = 상하(Pitch), 3 = 좌우(Yaw), 4 = 이동. 문처럼 신호 켜짐 → `PitchAngle`/`YawAngle`(부호로 방향)만큼 회전, 꺼짐 → 시작 각도로 복귀. 축마다 Timeline(Alpha 0→1) Play/Reverse + SetPlayRate(1/`RotateTime`) → 도중에 꺼져도 그 자리에서 되돌아감.
  - 적용(Rotator를 읽어 와서 더하지 않음, Pitch ±90° 재표기 방지): HeadPivot.SetRelativeRotation(MakeRotator(Pitch=HeadBaseRot.Pitch+PitchAngle×Alpha, Yaw/Roll=HeadBaseRot)), 액터 SetActorRotation(ComposeRotators(MakeRotator(Yaw=YawAngle×Alpha), ActorBaseRot)) — 로컬 Up축 기준이라 기울여 단 광원도 정상.
  - 구현 상태(2026-10-06, 거울로 넘어가며 중단): 변수 `PitchAngle`/`YawAngle`/`RotateTime`, `HeadRotateBase`/`ActorRotateBase`(BeginPlay 저장), `PitchTimeline`/`YawTimeLine` SetPlayRate(1/RotateTime) 완료. Pitch Update(HeadPivot.SetRelativeRotation, Break/Make로 Pitch만 변경) 완료. Custom Event `ActiveRotatePitch`/`DeactiveRotatePitch`/`ActiveRotateYaw`/`DeactiveRotateYaw` → Play/Reverse 연결됨. **남은 것**: ① Yaw Update가 `main.SetRelativeRotation`이라 배치 회전 무시하고 0에서 돎 → `SetActorRotation(ComposeRotators(MakeRotator(Yaw=YawAngle×Alpha), ActorRotateBase))`로 교체 안내함(미확인) ② YawTimeLine·이벤트 3개에 ErrorType=1 표시 — 컴파일 메시지 미확인 ③ OnChannelActive/Deactive Switch 3·4 연결 미확인 ④ README 반영.
  - 파랑 `BlockPull`/빨강 `Push` 기준을 SpotLight로 바꾸는 작업은 하지 않기로 함(2026-10-08 사용자 결정, 액터 위치·Forward 기준 유지).
  - **회전 동작 확인(2026-10-08 사용자)** → 위 남은 것 ①~③ 해결됨(README 반영 완료 2026-10-08: 채널 번호표 2·3·4, 5장 회전·이동 절).
- 광원 회전·이동 시작 상태(StartPitch/StartYaw/StartMoving)는 만들지 않음(2026-10-08 사용자 결정). 회전·이동은 신호로만 동작.
- 광원 이동(채널 4 — 사용자 지정, 2026-10-08 결정: 문처럼 한 점 왕복): 변수 `MoveOffset`(Vector, Instance Editable, Show 3D Widget, 액터 로컬), `MoveSpeed`(초당 이동 거리; PlayRate = MoveSpeed ÷ Max(Distance(Start, End), 1)로 거리와 무관하게 일정 속도), `MoveStartLoc`/`MoveEndLoc`(BeginPlay에서 월드 좌표로 저장: Start = GetActorLocation, End = TransformLocation(GetActorTransform, MoveOffset)). Timeline(Alpha) Update → SetActorLocation(Lerp(Start, End, Alpha)). `ActiveMove`/`DeactiveMove` → Play/Reverse. Switch 4. 액터 전체 이동이라 헤드·빛·감지 박스가 함께 따라감. 에디터 미리보기(Construction)는 이동·회전 모두 하지 않기로 함(2026-10-08 사용자 결정; 액터를 Construction에서 옮기면 누적되고, 회전은 레벨 조준값과 충돌). 도착 지점은 MoveOffset 3D 위젯으로 확인.
- 작업 9 거울 설계 (2026-10-06 사용자 확정):
  - 반사 대상: 손전등 + 맵 광원 + 다른 거울의 빔. 연쇄 반사 O(최대 횟수 BP 고정). 단면(앞면만 반사, 뒷면은 막기만). 빔 외형 = Rect Light(아래 참고). 빔 길이·최대 반사 횟수 BP 고정(BeamLength 3000, MaxBounce 4 예정). 회전은 신호만(F 조작 없음). 이동 = 신호 켜짐 → 오프셋 위치, 꺼짐 → 복귀(Play/Reverse). 빨강/파랑 기준 = 거울(빛을 마지막으로 쏜 주체), 플레이어 우선 유지.
  - 구조: `BP_Mirror`(부모 BP_Activate + BPI_LightInteractable). 블록처럼 `ActiveContributions`(Source→Color)로 빛을 받음 → 합친 색으로 빔. 반사 방향 = MirrorVectorByNormal(Normal(거울 − 기준 Source 위치), 거울 법선), 기준 Source = 플레이어 우선, 아니면 Keys[0]. 단면: Dot(입사, 법선) < 0일 때만. 입사각 제한(2026-10-07 사용자 결정): 정면(법선) 기준 60° 이내만 반사 → UpdateReflection FrontHit 조건 Dot(In, N) < DegCos(120)(=−0.5). DegCos(−각도)는 부호가 안 바뀌므로 180−각도를 넣음.
  - 빔 모양(2026-10-06 사용자 제안으로 변경): 원통이 아니라 **거울판 모양 그대로의 사각 기둥**(판의 각 점에서 반사 방향 R로 평행하게 나감). BeamRadius 상수 없음 — 빔 크기 = MirrorMesh 판 크기(로컬 bounds × 스케일).
  - 빔 판정(타이머 0.1초): 후보 = BoxTraceMultiForObjects(시작 = 판 중심, 방향 R, Orientation = 판 회전, HalfSize = 판 절반 크기, 최대 길이 BeamLength). 후보마다 `IsLitBeam`(맵 광원 IsLit 구조 재사용): 표본점 P(GetLightSamplePoints 또는 bounds 중심+꼭짓점×0.8)마다 ① **판으로 역투영**: s = Dot(P−C, N) / Dot(R, N) (C 판 중심, N 법선), Q = P − R·s → 0 < s ≤ BeamLength AND |Dot(Q−C, 판Right)| ≤ 반폭 AND |Dot(Q−C, 판Up)| ≤ 반높이 ② 가림 레이 Q(+N×약간) → P, HitActor==대상 → 하나라도 통과하면 true. Q가 빛이 실제로 판을 떠나는 지점이라 비스듬한 각도·절반 막힘 모두 정확. 이후 diff로 Add/Remove(BP_Light 방식).
  - 빔 외형(사용자 변경): 메시 대신 **Rect Light**(`BeamLight`, Root 자식). 위치 = 판 중심 + N×약간, 회전 = MakeRotFromXZ(R, 판Up), Source Width/Height = 판 크기(비스듬하면 투영 크기), **Barn Door Angle 90(0은 닫힘=빛 차단) + Barn Door Length 크게**로 평행 빔에 가깝게, Intensity 충분히 크게(작으면 안개 속 빔이 안 보임 — 실제로 겪음), Attenuation Radius = BeamLength, 색 = 합친 색, 빛 없으면 Visibility 끔. 경로는 Volumetric Fog가 있어야 보임. 판정은 위 역투영 계산(빛 컴포넌트와 무관).
  - (보류 2026-10-07: 아래 발광 작업은 사용자가 중지, 판정 먼저) 빔 시작 어색함(2026-10-07): Rect Light 빛 면은 항상 빔 방향에 수직이라 비스듬히 반사하면 기울어진 사각형이 거울판을 가로질러 보임(한 개 Rect Light로는 완전 해결 불가). 사용자 선택 = **B: 반사 중 거울 유리가 빔 색으로 발광**(유리 슬롯 머티리얼에 `GlowColor`(Vector)·`GlowStrength`(Scalar) 파라미터 → Emissive, BeginPlay MID, MirrorScan에서 켜짐/꺼짐). 같은 파라미터 이름으로 BP_Light 헤드 렌즈도 빛 색으로 발광시키기로 함(켜짐 + LightColorValue, 꺼지면 0). 머티리얼은 아트 담당이 `GlowColor`/`GlowStrength` 파라미터를 넣어 준다고 가정하고 BP만 작성(현재 MI 부모가 엔진 기본 머티리얼이라 직접 수정 금지). 슬롯 번호는 BP 변수 `GlowSlotIndex`로 둠. 파라미터가 없는 머티리얼이면 Set…ParameterValue는 에러 없이 무시됨.
  - 연쇄 무한루프 방지: 거울→거울 깊이 카운트(MaxBounce 초과 시 미방출) + 내가 비추고 있는 거울에서 온 빛은 무시(핑퐁 방지).
  - 축 규칙(2026-10-07 사용자 변경: 메시를 돌려 두면 맵에서 스케일 조절이 불편해서): `SM_Mirror` Relative Rotation = (0,0,0) 그대로, **반사면 정면 = MirrorPivot 초록(+Y, RightVector)**. 법선 N = MirrorPivot.GetRightVector, 판 가로축 = MirrorPivot Forward(X), 판 세로축 = MirrorPivot Up(Z). 판 크기 = SM_Mirror 로컬 bounds X(가로)·Z(세로) × 월드 스케일 → 맵에서 스케일 X = 가로, Z = 세로, Y = 두께.
  - M-7(이동·회전 채널) **안 함**(2026-10-25 사용자 결정: 거울은 신호 없음, 배치로 방향·위치 결정). M-5(반사 횟수 제한)는 **사용자가 먼저 말할 때만** 꺼낼 것(2026-10-25 사용자 지시 — 다음 할 일 목록에도 넣지 말 것).
  - 채널(사용자 결정): 0 = 이동, 1 = 상하(MirrorPivot **Roll** — 정면이 +Y라 Pitch(Y축 회전)는 판이 제자리에서 빙글 돌 뿐이므로 X축 회전인 Roll로 기울임), 2 = 좌우(액터 Yaw). ChannelRequired 0·1·2 → 1. 거울·받침대 메시 분리됨.
  - 연동 수정 필요: BP_Light `LightScan`의 GetOverlappingActors ClassFilter(BP_AvilityBlock) → 거울도 잡히게 변경. `IsLit`의 표본점 문제: GetActorBounds는 월드 AABB + 모든 컴포넌트 포함이라 거울은 ① 빔 메시(최대 3000)까지 bounds에 들어가 점이 엉뚱한 곳 ② 기울어진 얇은 판의 AABB 꼭짓점이 허공 → 판 일부만 비추면 감지 실패 ③ 받침대에 맞아도 HitActor==Target. 해결안: BPI_LightInteractable에 `GetLightSamplePoints → Vector 배열` 추가, 거울은 MirrorMesh 로컬 bounds를 TransformLocation한 판 위의 점(중심+모서리)을 반환, 빈 배열이면 IsLit이 기존 bounds 방식 사용(블록은 구현 안 해도 됨). 반사 시작점은 맞은 위치와 상관없이 판 중심(단순화). 빨강/파랑 방향용으로 "빛 방출 위치·방향"을 돌려주는 인터페이스(예: BPI_LightSource.GetEmit) 추가 → BP_Light(SpotLight), 거울(반사 방향), 플레이어 구현 — BP_Light 헤드 회전 시 Forward 문제도 같이 해결.
  - 구현 상태(2026-10-07): M-1~M-4 완료·동작 확인(손전등→거울→블록 발동, 색 변경, 가림, 판 밖 미발동, 각도·뒷면 차단). 함수: `UpdateBeamSource`(HasLight), `UpdateReflection`(FrontHit; N = MirrorPivot RightVector), `IsBeamLit(Target)`(Dirs 9점 → P/S/Q 저장(멤버 변수로 만들어짐) → 판 안 검사 → LineTrace Q→P HitActor==Target), BP_Light에서 복사한 `LightActor`(Color=BeamColor)/`UnLightActor`/`ClearLitActor`. BeginPlay: `Width`/`Height`(SM_Mirror 로컬 bounds X/Z × 월드 스케일, 전체 크기) → RectLight Source Width/Height. MirrorScan: RectLight 위치 BeamStart·회전 MakeRotFromXZ(BeamDir, Pivot Up)·Attenuation BeamLength(라인트레이스로 길이 자르지 않음, 가림은 RectLight Cast Shadows + Cast Volumetric Shadow) → CurrentHit Clear → BoxTraceMultiForObjects(HalfSize (1, W/2, H/2), WorldDynamic/PhysicsBody) → IsBeamLit → AddUnique → diff. 빔 꺼짐 → ClearLitActor(처음에 SetVisibility(false) 뒤 연결이 빠져 거울→거울에서 B가 안 꺼지는 버그가 있었음, 2026-10-08 수정). 거울→거울 연쇄 동작 확인(SM_Mirror WorldDynamic). 핑퐁 방지: 후보 Branch AND에 NOT ActiveContributions.Contains(HitActor)(나를 비추는 대상은 내가 비추지 않음). M-6(BP_Light LightScan ClassFilter Actor + DoesImplementInterface) 완료·맵 광원→거울 동작 확인(2026-10-08). **구조 변경 결정(2026-10-08 사용자)**: 빛 합쳐서 기준 광원 1개(플레이어 우선)로 빔 1개 → **광원마다 각자 반사 빔**(각도 검사도 광원별). 최대 3빔: RectLight 3개 풀(`BeamLights` 배열), UpdateReflection(Source 입력 → Valid/Dir 출력), IsBeamLit(Dir 입력), LightActor(Color 입력), 대상별 색 합산 Map `NewLit`(Actor→Color)으로 diff(블록 기여는 Source=거울 하나로 덮어쓰기라 빔별로 보내면 마지막만 남음). **완료·동작 확인(2026-10-08)**: MirrorScan = Clear(NewLit) → BeamInt=0 → ForEach(Keys(ActiveContributions)) → Branch(BeamInt<3) → UpdateReflection(Source) → FrontHit면 BeamLights[BeamInt]에 위치/회전(MakeRotFromXZ(Dir, Pivot Up))·SetLightColor(Select(R+G+B>0 ? 원래 색 : 흰색), 흰 손전등 빔 표시용)·Attenuation·Visible → BoxTrace(End = BeamStart + Dir×BeamLength, Orientation MakeRotFromXZ(Dir)) → 후보(IsBeamLit(Dir) AND 인터페이스 AND NOT ActiveContributions.Contains(HitActor)) → NewLit.Add(HitActor, NewLit.Find + ActiveContributions.Find(광원) 원래 색(흰색 치환 안 함: 흰 손전등은 (0,0,0)이어야 OwnColor 규칙 유지)) → 빔 하나 끝나면 BeamInt+1. 완료 후 For Loop(BeamInt..2) 남는 RectLight 숨김 → ForEach(LastLitActor) NewLit에 없으면 UnLightActor → ForEach(Keys(NewLit)) LightActor(NewLit.Find) → LastLitActor = Keys(NewLit). 빔 두 개가 같은 판 중심에서 출발해 안개 속 겹치는 부분이 섞인 색(빨+초=노랑)으로 보이는 건 정상(현실도 겹친 곳만 섞임, 판정 값은 정상 확인). 정리 대상: UpdateBeamSource/BeamSource/CombinedColor/BeamColor/BeamLightColor/CurrentHit/BeamDir/ClearLitActor(미사용이면). M-5 보류(2026-10-08 사용자 결정): 핑퐁(거울 2개 마주보기)은 막혀 있음. 3개 이상 고리(A→B→C→A)는 광원이 사라져도 빛이 남을 수 있음(BeamInt<3은 거울당 빔 개수 제한이라 고리를 못 막음) → 실제로 문제 생기면 LinearColor 알파에 반사 횟수를 담아 MaxBounce 이상이면 미방출하는 방식으로 구현. 거울 소스일 때 입사 방향 = 그 거울의 BeamDir(평행광)도 보류.
  - 구현 순서: M-1 BP/컴포넌트 → M-2 빛 받기·합친 색·기준 Source → M-3 반사 방향·단면 → M-4 빔 판정·메시 → M-5 연쇄 제한 → M-6 BP_Light 필터 → M-7 회전/이동 채널 → ~~M-8 방출 인터페이스(빨강/파랑)~~ 안 함(2026-10-08 사용자: 기존 GetLightSource가 거울 액터를 기준으로 잡아 빨강/파랑이 이미 잘 동작. 파랑 목표점이 거울 액터 Forward(X) 기준이라 정면(+Y)과 다를 수 있음 — 문제 시 그때 확인).

- 작업 6 손전등·필터 획득 설계(2026-10-08 사용자 확정):
  - 데이터: 구조체 `S_PlayerProgress`(HasFlashlight bool, UnlockedColors Set<EN_LightColor>)를 `BP_GameInstance.Progress`가 보유(레벨 이동·플레이어 재생성에도 유지). 저장 기능이 생기면 `BP_SaveGame.Progress`에 구조체째 복사/로드만 하면 됨. Project Settings Game Instance Class = BP_GameInstance(Config/DefaultEngine.ini → 커밋 시 이 줄은 공유 필요).
  - 아이템 ID 없음: 종류 자체가 ID. `BP_Pickup`은 BeginPlay에 이미 가진 종류면 Destroy → 저장 후 재진입해도 재등장 안 함.
  - 줍기 = F 상호작용(BPI_Interact). 주우면 GameInstance.Progress 갱신 → 플레이어 갱신 → Destroy.
  - 테스트(2026-10-23 사용자 변경, 2026-10-24 자식 GameMode 방식 확정 — bool 하나로 전환하는 안은 맵마다 다르게 못 하고 팀원 맵에 영향이라 기각): 지금 쓰던 `BP_GameMode`를 `BP_TestGameMode`로 이름 변경(2026-10-24, 옛 이름은 리다이렉터로 남음) = **테스트용**(`UnlockAllForTest` 켜짐 → 줍지 않아도 전부 사용). 본 게임용은 `BP_GameMode`의 자식 GameMode(`BP_RealGameMode`, `UnlockAllForTest` 꺼짐)를 새로 만들어 실제 스테이지 맵의 GameMode Override로 지정. 기존 테스트 맵은 변경 없음. 데이터는 안 바꾸고 플레이어 `CanUseColor`/`CanUseFlashlight` = 테스트 OR Progress 검사에만 끼어듦(가짜 데이터가 저장되지 않게).
  - 플레이어는 GameMode로 스폰됨(LightTestMap = BP_GameMode override, 레벨에 배치된 BP_Charactor 없음).
  - 진행 상태(2026-10-24): **전체 완료·동작 확인** (README 3-3·1장·9장, BP_STRUCTURE 반영). ①~③ 완료(`S_PlayerProgress`는 `Content/BluePrint/`에 있음. BP_GameInstance 함수 UnlockFlashlight / UnlockColor / RemoveColor / HasColor(Pure), Project Settings Game Instance Class 지정). ④ 완료(2026-10-24): GI·UnlockAll 캐싱, CanUseFlashlight/CanUseColor(Pure), 숫자 키 앞 Branch, RefreshFlashlight(SM_Flashlight 표시), 본 게임 모드 시작 시 TurnOff. ⑤ BP_Pickup 완료·동작 확인(2026-10-24): `EN_PickupType`(Flashlight / Filter) + `FilterColor`(EN_LightColor), `ItemMesh`(Query Only, Visibility만 Block), `FlashlightMesh`/`FilterMesh`(Class Defaults, Construction에서 선택), `SignalTargets`(BP_Button 자식·복사 대신 직접 — 버튼의 Togle/Timed는 Destroy 뒤 동작 못 함). 1회성: 줍기 → GI 기록 → `SendActivate` → 플레이어 RefreshFlashlight → Destroy. BeginPlay에서 이미 가진 종류면 `SendActivate` 후 Destroy(레벨 재시작 시 연결된 문이 다시 열리도록). 순서: ① S_PlayerProgress ② BP_GameInstance + Project Settings ③ BP_TestGameMode(테스트용) UnlockAllForTest 켜짐 + 자식 BP_RealGameMode(꺼짐) ④ BP_Charactor CanUseColor/CanUseFlashlight·입력 차단·손전등 메시 표시 ⑤ BP_Pickup ⑥ 테스트.
순서: ~~2~~ → ~~3~~ → ~~1~~ → ~~5~~ → 4 → 6 → 7 (5를 4보다 먼저: 2026-10-03 사용자 결정. 7은 맨 마지막). 8은 5 끝난 뒤 적당한 때에.
- 2026-10-23 추가 작업(10~14) 권장 순서(제안, 사용자 미확정): 6 획득(데이터 기반 S_PlayerProgress·GameInstance) → 14 필터 반납(같은 데이터에서 제거 + 송신) → 13 Respawn 플레이어(지정 위치로 소환, 독립 작업이라 언제든) → 12 체크포인트 → 11 저장·이어하기(Progress + 체크포인트를 SaveGame에) → 10 UI(상호작용 문구는 작아서 언제든, ESC 메뉴의 "스테이지 초기화"·"종료"는 11 이후) → 7 필터 교체 모션. 의존: 11은 6·12의 데이터를 저장.
- `BP_Door2`(2026-10-23 추가·동작 확인): BP_Door와 메시만 다른 문. 설정·채널·동작 동일(README 4장·맨 위 표 반영).
- 리다이렉터 `Content/GameMode/BP_GameMode`(→ BP_TestGameMode, 2026-10-24): 직접 Delete 금지(참조가 None이 됨). 팀원 맵이 BP_TestGameMode/BP_RealGameMode로 다시 지정한 뒤 폴더 우클릭 → Update Redirector References로 정리. 그 전까지 유지.
- `LightTestMap` 로컬 변경(2026-10-23): 나중에 다른 팀원 맵으로 덮어쓸 예정 → 커밋에 넣지 말 것(사용자 확인).
- 5(채널)는 버튼/발판/모든 수신 장치를 건드리는 구조 변경이라, 4의 "신호로 움직임/꺼짐" 로직과 겹침 → 4를 할 때 5의 설계를 먼저 정하는 게 좋음.
- 6과 7은 같은 손전등 필터 시스템이라 6을 먼저 하면 7의 필터 메시를 재사용 가능 (7을 먼저 해도 무방).
