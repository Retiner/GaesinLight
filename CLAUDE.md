# GaesinLight 프로젝트 — AI 작업 컨텍스트

RGB 손전등 퍼즐 게임. UE 5.8. 새 세션 시작 시 먼저 읽고 시작할 것.
레벨 제작자용 상세 매뉴얼은 `README.md`에 있음 (이 파일은 AI / 개발 이어가기용 요약 + 구현 메모).

---

## 1. 블루프린트 목록과 인스턴스 설정 (사용 매뉴얼 요약)

### 1-0. 신호 구조
- 송신: BP_Button, BP_PressurePlate → `SignalTargets`(`S_SignalTarget` 배열: Target Actor + Channel Int, 기본 0)마다 `BPI_Activatable`의 `Activate(Channel)` / `Deactivate(Channel)` 메시지 전송. 상태가 바뀔 때만 보냄. 인터페이스 메시지라 BPI_Activatable 미구현 액터나 None이 들어 있어도 오류 없이 무시됨.
- 수신: BP_Activate를 부모로 하는 BP_Door, BP_Light, BP_AvilityBlock, BP_Hatch.
- 공통 수신 설정: 채널별로 켜진 신호 수(`ChannelCount`)가 필요 개수 이상이면 `OnChannelActive(Channel)`, 아래로 내려가면 `OnChannelDeactive(Channel)`. 필요 개수 = `Max(Map_Find(ChannelRequired, Channel), 1)` (Map 채널→개수, 없으면 1). 2 이상이면 AND. `RequiredCount`는 2026-10-05 삭제(ChannelRequired로 통합). 각 BP Class Defaults에 받는 채널을 `→ 1`로 미리 넣어 둠(문/다락문/블록 `0`, 광원 `0~3`). 모든 수신 장치가 `OnChannelActive`/`OnChannelDeactive`를 직접 오버라이드(`OnActive`/`OnDeactive`/`IsActive`/`ActiveCount`는 2026-10-05 삭제). 채널 번호는 수신 장치 안에서만 의미가 있음. 수신 장치의 기능→채널 번호표는 BP에 고정(인스턴스 설정 아님, 2026-10-04 사용자 결정: 송신 쪽 Channel로 기능을 고르므로 수신 쪽까지 바꿀 수 있으면 중복). 현재 번호표: 문/다락문 0=열기, 능력 블록 0=이동(WaitTrigger), 맵 광원 0=전원(TurnOn+SetVisibility) / 1=색(ChangeColor: R/G/B 켜짐→그 색, 꺼짐→FirstColorValue, Rotate는 `==` 비교로 R→G→B 순환, 꺼짐 무시) / 2=이동·회전 예약(작업 4). README 0번 "채널 번호표"에 표로 정리.
- 시작 상태 반전(2026-10-05): 각 장치에 단순 bool(문/다락문 `StartOpen`, 블록 `StartMoving`, 광원 `StartOn` 완료, 광원 `StartMoving`/`StartRotating` 예정). 부모 순수 함수 `IsStartOn(Channel)→bool`(기본 false)을 자식이 Switch on Int로 오버라이드해 채널별 bool 반환. true면 부모가 Active/Deactive 호출을 서로 바꿈 → 신호 켜짐 = 꺼짐 동작. 장치는 BeginPlay/Construction에서 스스로 "켜진 상태"로 시작해야 함. (Set<채널> 방식은 레벨 제작자 부담이라 사용자가 거절)
- 버튼과 발판은 같은 신호를 보내므로 한 수신 장치에 섞어서 연결 가능(합산). 예: 문 `ChannelRequired 0→2` + Togle 버튼 + 발판 = 버튼 켜고 발판 밟아야 열림. AND에 `ReOn`은 즉시 꺼져서 사용 불가.

### 1-1. BP_Charactor — 플레이어
- 무엇: 손전등을 든 플레이어. 1 키 흰색(`IA_White`), 2·3·4 키 빨강·초록·파랑(`IA_Red/Green/Blue`), F 키 상호작용(`IA_Relation`, 버튼 누르기 / 블록 잡기·놓기).
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

### 1-4. BP_Door — 문 (수신)
| 인스턴스 설정 | 설명 | 기본값 |
|---|---|---|
| `ChannelRequired` | 채널별 필요 신호 수 | `0 → 1` |
| `StartOpen` | 열린 채 시작, 신호 켜짐=닫힘 (IsStartOn 0 → StartOpen) | 꺼짐 |
- `OpenDistance`(문짝 이동 거리, 100), `OpenTime`(열리는 시간, 1초)은 BP 내부 고정값.
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
- `PlayerRange`(8000, 플레이어가 이 거리 안일 때만 판정), `ScanInterval`(0.1초, 판정 주기)은 BP 내부 고정값.
- 맵 광원만으로도 능력 발동 (2026-10-02 변경: `ReCalculate`에서 `Map_Contains(ActiveContributions, PlayerCharacter)` + Select 제거, `CurrentColor`를 Switch on Int에 직접 연결). 단 PlayerRange 밖이면 판정 안 함.
- 예시: 빨강 광원 + 파랑 손전등 = 보라 통과 / StartOn 끔+Togle 버튼(Ch 0) = 스위치 조명 / ChangeColor Rotate + ReOn 버튼 = 색 금고.

### 1-6. BP_AvilityBlock — 능력 블록 (수신)
| 인스턴스 설정 | 설명 | 기본값 |
|---|---|---|
| `ColorMode` | `Default`(비춘 색 그대로, UseColor 무시) / `ReactOnly`(합친 색 == UseColor일 때만, All이면 전부) / `OwnColor`(UseColor를 고유색으로 품고 들어온 빛과 OR 합성) | `Default` |
| `UseColor` | All / Red / Blue / Green / Purple / Yello / SkyBlue / None (예전 `ReactColor`를 이름 변경) | `All` |
| `Move` | Fixed / Physics / PatrolReturn / PatrolRotation / PatrolRestart | `Fixed` |
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
- 색 합성 (`ReCalculate`): ActiveContributions 합 → 비트 인코딩(R≥0.5 → 1, G → +2, B → +4)으로 `CurrentColor`. Sequence then_3에서 `ColorMode == OwnColor AND CurrentColor != 0`이면 `CurrentColor = CurrentColor | Select(UseColor)`(All 0, Red 1, Green 2, Yello 3, Blue 4, Purple 5, SkyBlue 6, None 0). 빛이 없으면(0) 고유색만으로는 발동 안 함. 이후 Switch on Int(0/7 → None, 1 Red, 2 Green, 3 Yello, 4 Blue, 5 Purple, 6 SkyBlue).
- `ColorCheck` 매크로: `IsLit = (ColorMode != ReactOnly) OR (UseColor == All) OR (색 == UseColor)`.
- Construction Script: ColorMode Switch로 메시(Default `SM_Element_Plain`, 나머지 `SM_Element_Chain`) → Move Switch로 `SM_Floor_Plain_Light` 표시(Patrol만, NoCollision) → `IsUserStaticMesh`면 UserStaticMesh 후 종료, 아니면 crystal 슬롯에 `M_BlockBase` MID 생성(`BlockMID`) → 크리스탈 색 Select(ColorMode): Default 흰색 / ReactOnly `Lerp(TargetColor, 흰색, 0.3)` / OwnColor `TargetColor` → `BlockColor` + `StartColor`. MID는 모드와 상관없이 항상 만들어야 함(런타임 색 변경·보라 Opacity가 BlockMID 사용).
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
- `Config/DefaultEngine.ini`에서 공유해야 하는 것: `r.VolumetricFog.HistoryWeight=0`(안개 잔상 방지), `LightCencer` 콜리전 채널(맵 광원 감지).
- 커밋 전엔 항상 `git status`로 의도치 않은 변경(에디터 자동저장 애셋 등) 확인.
- 사용자가 커밋을 원하지 않을 때가 많음 — 명시적으로 요청할 때만 커밋.

## 4. 작업 스타일

- 사용자는 Blueprint를 배우는 중 — 직접 그래프를 만들고 K2Node 텍스트를 붙여넣어 검증받는 방식. 대신 만들어주지 말 것.
- 설명은 목적 → 노드 역할 → 구체적 행동 순서, 이유 포함, 한 번에 한 단계(하위 단계로 쪼개서). 세션이 길어져도 설명을 압축하지 말 것.
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
| 6 | 손전등·필터 획득 | 시작 시 손전등/색 변경 불가. 맵의 손전등·색 필터 아이템을 상호작용으로 획득해야 사용 가능 (획득 상태로 자격 판정) | 대 |
| 7 | 필터 교체 모션 | 색 변경 시 필터 메시를 손전등 밖으로 빼고 → 색 변경 → 원위치 (단순 이동 연출) | 소~중 |
| 8 | ~~파랑 당기기 조건~~ ✅ 완료 (2026-10-05) | Blue 능력 중 플레이어를 끌어당기는 쪽(비-Physics 블록)은 플레이어가 그 블록에 빛을 쏘고 있을 때만 발동. 구현: `PlayerPull` 입구 → Branch(`ActiveContributions.Contains(GetPlayerCharacter)`) → LaunchCharacter. 매 호출 검사라 손전등을 돌리면 즉시 멈춤. 싱글플레이 전제(멀티 시 Keys→Cast to BP_Charactor로 교체) | 소 |
| 9 | 거울 (2026-10-05 추가) | 빛을 정반사로 튕겨내는 거울. 현재 빛은 스포트라이트(원뿔) 판정이라 원뿔 그대로 반사하기 어려움 → **원통형 빔**으로 반사하는 느낌으로 구현(반사 지점에서 반사 방향으로 일정 반경의 원통 판정). 수신 장치(채널 기능 포함)로 **회전**과 **위치 이동** 지원 예정(광원 회전/이동 설계 재사용 가능) | 대 |

- 작업 4 진행 상황(2026-10-05): 시작 상태 반전(StartOpen/StartMoving/StartOn) 완료. 광원 회전은 **보류**(사용자 결정), 설계만 확정:
  - 채널 3 = `RotateOffset` 회전, 4/5 = Yaw ±`AimYawStep`, 6/7 = Pitch ±`AimPitchStep`. `EN_LightRotate`(Step / PingPong / Loop), `RotateMode`, `RotateTime`, `StartRotating`(PingPong/Loop 반전), 내부 `RotBase`/`ActiveOffset`.
  - Step = 한 번 돌고 정지(꺼짐 무시, ReOn용) / PingPong = RotBase↔+Offset 왕복, 꺼지면 정지(방향 채널에선 Step처럼) / Loop = 끝날 때마다 RotBase=현재 회전 후 PlayFromStart로 이어 붙여 계속 회전, 꺼지면 정지.
  - `RotateTimeline`(Alpha 0→1, 1초, Linear) + SetPlayRate(1/RotateTime). Update: SetActorRotation(RotBase + ActiveOffset×Alpha, **성분별 덧셈**: Break/Make Rotator. Combine은 기울어진 광원에서 축이 틀어져 폐기). 루트·SpotLight Mobility = Movable 필요.
  - 사용자가 만든 것: R-1 변수/Enum 일부, R-2 Timeline(Combine 버전일 수 있음) — 재개 시 BP 상태 먼저 확인.
- 광원 이동(채널 2)도 미착수.

순서: ~~2~~ → ~~3~~ → ~~1~~ → ~~5~~ → 4 → 6 → 7 (5를 4보다 먼저: 2026-10-03 사용자 결정. 7은 맨 마지막). 8은 5 끝난 뒤 적당한 때에.
- 5(채널)는 버튼/발판/모든 수신 장치를 건드리는 구조 변경이라, 4의 "신호로 움직임/꺼짐" 로직과 겹침 → 4를 할 때 5의 설계를 먼저 정하는 게 좋음.
- 6과 7은 같은 손전등 필터 시스템이라 6을 먼저 하면 7의 필터 메시를 재사용 가능 (7을 먼저 해도 무방).
