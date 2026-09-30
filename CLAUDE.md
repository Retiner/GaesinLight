# GaesinLight 프로젝트 — AI 작업 컨텍스트

RGB 손전등 퍼즐 게임. UE 5.8. 새 세션 시작 시 먼저 읽고 시작할 것.
레벨 제작자용 상세 매뉴얼은 `README.md`에 있음 (이 파일은 AI / 개발 이어가기용 요약 + 구현 메모).

---

## 1. 블루프린트 목록과 인스턴스 설정 (사용 매뉴얼 요약)

### 1-0. 신호 구조
- 송신: BP_Button, BP_PressurePlate → `Targets`(Actor 배열, 스포이드로 지정)에 `BPI_Activatable`의 `Activate` / `Deactivate` 메시지 전송. 상태가 바뀔 때만 보냄. 인터페이스 메시지라 BPI_Activatable 미구현 액터나 None이 들어 있어도 오류 없이 무시됨.
- 수신: BP_Activate를 부모로 하는 BP_Door, BP_Light, BP_AvilityBlock.
- 공통 수신 설정 `RequiredCount`(기본 1): 켜진 신호 수(`ActiveCount`)가 이 값 이상이면 `OnActive`, 아래로 내려가면 `OnDeactive`. 2 이상이면 AND 조건.
- 버튼과 발판은 같은 신호를 보내므로 한 수신 장치에 섞어서 연결 가능(합산). 예: 문 `RequiredCount=2` + Togle 버튼 + 발판 = 버튼 켜고 발판 밟아야 열림. AND에 `ReOn`은 즉시 꺼져서 사용 불가.

### 1-1. BP_Charactor — 플레이어
- 무엇: 손전등을 든 플레이어. 1·2·3 키 색 전환(`IA_Red/Green/Blue`), F 키 상호작용(`IA_Relation`, 버튼 누르기 / 블록 잡기·놓기).
- 인스턴스 설정: 없음 (손전등 `LightLength`는 BP 내부 고정값).
- 주의: 손전등 메시는 반드시 NoCollision (BlockAll이면 보라 Physics 블록이 WorldStatic으로 보고 부딪혀 튕김).

### 1-2. BP_Button — 버튼 (송신, BPI_Interact)
| 인스턴스 설정 | 설명 | 기본값 |
|---|---|---|
| `Targets` | 신호 받을 장치 | 비어 있음 |
| `ButtonMode` | `JustOn`(한 번 켜고 고정) / `Togle`(켜짐↔꺼짐) / `ReOn`(펄스: Activate 직후 Deactivate) / `Timed`(`TimedDuration`초 후 자동 꺼짐) | `JustOn` |
| `TimedDuration` | Timed 지속 시간 | 10 |
| `UseAsset` + `UseStaticMesh` | 외형 메시 교체 (Construction Script, 메시에 콜리전 필요) | 꺼짐 / 없음 |
- 예시: JustOn+문=영구 출구 / ReOn+Rotate 광원=색 회전 퍼즐 / Timed+문=타임어택.
- ReOn(펄스)이 필요한 이유: BP_Activate는 `ActiveCount`로 세기 때문에 Activate만 반복하면 카운트만 쌓이고 `OnActive`가 다시 안 불림. 즉시 Deactivate해서 카운트를 되돌려야 매번 반응함.

### 1-3. BP_PressurePlate — 발판 (송신)
| 인스턴스 설정 | 설명 | 기본값 |
|---|---|---|
| `Targets` | 신호 받을 장치 | 비어 있음 |
- 감지: BP_Charactor 또는 BP_AvilityBlock(자식 포함)이 Trigger 박스에 하나라도 있으면 켜짐.
- 예시: 발판+문 / 블록 올려두기 / 발판 2개 + 문(`RequiredCount=2`) = AND 퍼즐.

### 1-4. BP_Door — 문 (수신)
| 인스턴스 설정 | 설명 | 기본값 |
|---|---|---|
| `RequiredCount` | 필요한 신호 수 | 1 |
- `OpenDistance`(문짝 이동 거리, 100), `OpenTime`(열리는 시간, 1초)은 BP 내부 고정값.
- 좌우 문(LeftDoor/RightDoor) + DoorFrame, Timeline Play/Reverse라 도중에 꺼져도 자연스럽게 되돌아감.

### 1-5. BP_Light — 맵 광원 (수신)
| 인스턴스 설정 | 설명 | 기본값 |
|---|---|---|
| `LightColor` | 기본 색 Red/Blue/Green (Construction Script에서 `LightColorValue`/`FirstColorValue` 설정) | `Red` |
| `LightActiveMode` | `Default`(항상 켜짐, 신호 무시) / `ON/OFF`(평소 꺼짐, 신호 동안 켜짐) / `ChangeColor` | `Default` |
| `ChangeColor` | `Red`/`Green`/`Blue`(신호 켜지면 그 색, 꺼지면 원래 색) / `Rotate`(켜질 때마다 R→G→B 회전, 꺼짐 무시 → ReOn 버튼과 사용) | `Rotate` |
| `RequiredCount` | 필요한 신호 수 | 1 |
| `LightLength` | 판정 거리 | 5000 |
| SpotLight `Outer Cone Angle` | 판정 원뿔 각도 (SpreadRadius / 감지 박스 자동 계산) | 컴포넌트 값 |
- `PlayerRange`(8000, 플레이어가 이 거리 안일 때만 판정), `ScanInterval`(0.1초, 판정 주기)은 BP 내부 고정값.
- 맵 광원 단독으로는 블록 능력 발동 안 함 — 의도된 설계. 손전등과 색을 섞는 용도.
- 예시: 빨강 광원 + 파랑 손전등 = 보라 통과 / ON/OFF+Togle 버튼 = 스위치 조명 / ChangeColor Rotate + ReOn 버튼 = 색 금고.

### 1-6. BP_AvilityBlock — 능력 블록 (수신)
| 인스턴스 설정 | 설명 | 기본값 |
|---|---|---|
| `ReactColor` | All / Red / Blue / Green / Purple / Yello / SkyBlue | `All` |
| `Move` | Fixed / Physics / PatrolReturn / PatrolRotation / PatrolRestart | `Fixed` |
| `MovePoint`, `MoveSpeed` | Patrol 경유지, 속도 | 비어 있음 / 500 |
| `WaitTrigger` | 켜면 신호 받을 때까지 Patrol 대기, 신호 꺼지면 그 자리에서 멈춤 | 꺼짐 |
| `RequiredCount` | WaitTrigger용 필요 신호 수 | 1 |
| `IsUserStaticMesh` + `UserStaticMesh` | 외형 교체 (발판·벽으로 활용) | 꺼짐 / 없음 |
| Red: `InnerRadius`/`OuterRadius`/`ExplosionForce`/`PushForce`/`Exp_PlayerForce` | 폭발 | 200 / 1250 / 2500 / 2000 / 2000 |
| Blue: `MaxPullSpeed`/`PlayerMaxPullSpeed` | 당기기 | 3000 / 2000 |
| Yello/SkyBlue: `ChangeSpeed`/`UpScale`/`DownScale` | 크기 변화 | 0.3 / 2 / 2 |
| Green / Purple | 튜닝 변수 없음 | - |
- `MovePoint`: Show 3D Widget 벡터 배열, 블록 로컬 좌표. BeginPlay 쯤 `GetTransform → TransformLocation`으로 `WorldPatrolPoints`에 변환(이후 블록이 움직여도 경로 고정). `VInterpTo_Constant(MoveSpeed)`로 `PatrolIndex` 순서대로 이동.
- 움직이는 발판/벽은 별도 BP 없이 이 블록으로 만듦: UserStaticMesh + Patrol + WaitTrigger + 버튼/발판 Targets.
- 예시: 버튼으로 출발하는 엘리베이터 / 초록으로 멈추는 발판 / 보라 벽 / 노란 계단 / 파랑으로 끌어와 발판 누르기.
- 충전·유지·쿨타임은 인스턴스 설정 불가 (`AvilityConfig` 함수에 색별 고정).

### 1-7. 기타 애셋
- `BP_Activate`: 수신 부모. 직접 배치하지 않음.
- `BP_LightBlock`: BP_AvilityBlock으로 가는 리다이렉터(이름 변경 흔적). 사용 안 함.
- 인터페이스: `BPI_Activatable`(Activate/Deactivate), `BPI_Interact`(Interact, GetInteractText), `BPI_LightInteractable`(Add/RemoveColorContribution).
- Enum: `EN_ButtonMode`, `EN_LightActiveMode`, `EN_ChangeColor`, `EN_LightColor`, `EN_ColorState`, `EN_BlockMove`, `EN_Avility`.

---

## 2. 구현 메모

### 2-1. 신호 시스템 (BP_Activate)
- `Activate` → `ActiveCount++` → `ActiveCount >= RequiredCount` 이고 `IsActive == false`면 `IsActive = true` → `OnActive`. Deactivate는 반대.
- 자식은 `OnActive`/`OnDeactive`를 함수 오버라이드(Parent 호출 노드 유지). Timeline은 함수에 못 넣으므로 함수에서 이벤트그래프의 Custom Event 호출.
- 송신 쪽 `SendActivate`/`SendDeactivate` = ForEach(Targets) → Activate/Deactivate (Message).
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
  - Construction Script: `SpreadRadius = LightLength × DegTan(OuterConeAngle)`, 감지 박스 `LightSencer`(SpotLight 자식) Extent=(L/2, R, R), 위치=(L/2,0,0). ON/OFF 모드는 여기서 `TurnOn=false` + `SetVisibility`.
  - 감지 박스 Object Type = `LightCencer` 커스텀 채널(DefaultEngine.ini, 기본 Overlap). 보라 능력이 WorldDynamic 등을 Ignore해도 감지되게 하려고 전용 채널 사용. 박스 응답은 WorldDynamic / PhysicsBody만 Overlap.
  - 예전 13점 격자 방식(BuildTrace, TracePoint, RingCount, PointPerRing)은 먼 거리 빈틈 문제로 폐기됨.
- LightActor/UnLightActor: `IsValid` + `DoesImplementInterface(BPI_LightInteractable)` 후 `AddColorContribution(Source, Color)`/`RemoveColorContribution`. 기여는 Source별로 덮어씀(누적 아님).

### 2-3. BP_AvilityBlock
- 능력 흐름: `ChargeAlpha` 0→1(색마다 ChargeTime, Green 0.2초) → `AvilityStart` → `HoldRemain` 카운트다운(빛 받는 동안 갱신) → 0이면 `AvilityEnd` + CoolTime.
- Trigger: `AvilityTick`에서 `WaitTrigger && TriggerPaused`면 Patrol 스킵. BeginPlay에서 `TriggerPaused = WaitTrigger`, OnActive→false, OnDeactive→true.
- Yellow/SkyBlue: `BaseSize × Lerp(1, UpScale 또는 1/DownScale, Alpha)`. 독립 Timeline(0→0.4초)을 `Grow`(Play) / `Y_Reset`·`SB_Reset`(Reverse)로 구동. ChargeAlpha를 직접 쓰면 차징 중에 커지는 문제가 있어서 분리함.
- Purple:
  - `M_BlockBase` = Translucent + `Opacity` 파라미터. Cast Dynamic Shadow as Masked 켜야 그림자 생김(Translucent는 기본적으로 그림자 없음). Nanite는 Translucent 미지원이라 이 머티리얼 쓰는 메시(`SM_Element_Plain`, `SM_Element_Chain` 등)는 Nanite 끔.
  - `P_Collision`: 프로필 이름 저장 → Physics면 Pawn/WorldDynamic/PhysicsBody Ignore(WorldStatic은 유지해서 바닥 안 뚫게), 아니면 WorldStatic까지 Ignore. `P_CollisionReset`: 저장한 프로필로 복구. Visibility 채널은 절대 안 건드림.
  - SafeReset(EventGraph Custom Event): AvilityEnd 보라 경로는 `Set PurpleResetPending(true) → SafeReset`. SafeReset은 `PurpleResetPending` 확인 → `BoxOverlapActors`(Bounds×0.9, Pawn만, 자신 제외) → 겹치면 Delay 0.2 후 재호출, 비면 `PurpleResetPending=false → P_CollisionReset → P_Reset`. AvilityStart 보라 경로 맨 앞에서 `PurpleResetPending=false`(대기 취소).
  - 보라 Physics 블록을 떨어뜨릴 바닥은 일반 Static Mesh(WorldStatic)가 아니라 BP_AvilityBlock(UserStaticMesh, Fixed)으로 깔아야 함 — WorldStatic은 유지, 블록끼리는 Ignore라서.
  - Object Types를 Pawn만 두는 이유: 블록끼리 겹치면 서로를 기다려 무한 유지(교착)됨. 블록끼리는 메시 Physics의 Max Depenetration Velocity 100으로 천천히 분리.
  - 블록 안에서는 손전등 레이가 블록을 못 맞힘(콜리전 내부 시작) → 통과 중 HoldRemain이 끝날 수 있음 → SafeReset이 이를 커버.

### 2-4. 디테일 패널 카테고리 순서
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
