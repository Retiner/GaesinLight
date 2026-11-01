# GaesinLight 블루프린트 구조 정리

BP를 고치기 전에 이 문서에서 대상 BP의 구성요소·변수·함수·흐름을 먼저 확인하고 작업합니다.
- 기능이 바뀔 때마다 이 문서를 같이 갱신합니다 (`레벨 제작 가이드.html` = 레벨 제작자용 사용법, CLAUDE.md = 설계 결정·작업 기록, 이 문서 = BP 내부 구조).
- 근거: 사용자가 붙여 넣은 그래프(K2Node 텍스트), 작업 기록, .uasset의 컴포넌트 이름. **(미확인)** 표시는 그래프를 직접 보지 못하고 기록만으로 적은 부분입니다.
- 표기: `A → B` = 실행 순서, `[I]` = Instance Editable(레벨에서 설정), `(내부)` = 런타임 계산용.

---

## 0. 전체 관계

```
[송신]  BP_Button ─┐  (+ BP_Pickup, BP_FilterReturn)
        BP_PressurePlate ─┼─ BPI_Activatable.Activate(Channel) / Deactivate(Channel) ─→ [수신] BP_Activate 자식
        BP_Trigger ─┘                                                              (BP_Door, BP_Door2, BP_Hatch,
                                                                                    BP_Light, BP_AvilityBlock, BP_Mirror)

[빛]    BP_Charactor(손전등) ─┐
        BP_Light(맵 광원) ────┼─ BPI_LightInteractable.Add/RemoveColorContribution(Source, Color) ─→ BP_AvilityBlock
        BP_Mirror(반사 빔) ───┘                                                                     BP_Mirror

[상호작용] BP_Charactor F키 ─ BPI_Interact.Interact ─→ BP_Button, BP_AvilityBlock(잡기), BP_Pickup(줍기), BP_FilterReturn(반납)

[구역]  BP_Respawn ─ (Cast) ─→ BP_AvilityBlock.ResetToStart
        BP_Trigger ─ OpenLevel(NextLevel)
        BP_Checkpoint ─ GI.SetCheckpoint ─→ SaveProgress ─→ Save0.sav

[저장]  GI Event Init ─ LoadProgress ← Save0.sav ;  BP_Charactor BeginPlay ─ MoveToCheckpoint(GI.Progress)
```

- 송신 → 수신은 전부 **인터페이스 메시지**라 대상이 None이거나 인터페이스가 없어도 오류 없이 무시됩니다.
- 빛 기여는 **Source별로 덮어쓰기**입니다(같은 Source가 다시 보내면 값이 교체됨). 그래서 한 Source가 같은 대상에 여러 빛을 줄 때는 보내기 전에 합쳐서 한 번만 보냅니다(BP_Mirror의 `NewLit`).

---

## 1. 공통 요소

### 인터페이스 (`Content/GameMode/`)
| 이름 | 함수 | 구현하는 BP | 호출하는 BP |
|---|---|---|---|
| `BPI_Activatable` | `Activate(Channel)`, `Deactivate(Channel)` | BP_Activate (자식 전부 상속) | 버튼, 발판, 트리거 |
| `BPI_LightInteractable` | `AddColorContribution(Source, Color)`, `RemoveColorContribution(Source)` | BP_AvilityBlock, BP_Mirror | 손전등, 맵 광원, 거울 |
| `BPI_Interact` | `Interact`, `GetInteractText`, `CanInteract` | BP_Button, BP_AvilityBlock, BP_Pickup, BP_FilterReturn | BP_Charactor |

### 구조체 / Enum (`Content/BluePrint/`)
| 이름 | 내용 |
|---|---|
| `S_SignalTarget` | `Target`(Actor), `Channel`(Int, 기본 0) |
| `EN_ButtonMode` | JustOn / Togle / ReOn / Timed |
| `EN_ChangeColor` | Red / Green / Blue / Rotate |
| `EN_LightColor` | Red / Blue / Green |
| `EN_ColorMode` | Default / ReactOnly / OwnColor |
| `EN_ColorState` | (블록 `UseColor`용) All / Red / Blue / Green / Purple / Yello / SkyBlue / None |
| `EN_BlockMove` | Fixed / Physics / PatrolReturn / PatrolRotation / PatrolRestart (내부 이름 `NewEnumerator1` = Physics) |
| `EN_Avility` | Ready / Active / CoolTime |
| `EN_LightRotate` | 예전 회전 방식용 (미사용으로 보임, 미확인) |
| `EN_PickupType` | Flashlight / Filter (BP_Pickup) |

### 게임 전체 (작업 6, 2026-10-24)
| 이름 | 위치 | 내용 |
|---|---|---|
| `S_PlayerProgress` | `Content/BluePrint/` | `HasFlashlight`(Bool), `UnlockedColors`(Set<EN_LightColor>), `CompletedReturns`(Set<Name>, 반납 끝난 테이블 키 — 작업 14), `CheckpointLevel`(Name, 비면 None = 체크포인트 없음), `CheckpointTransform`(Transform, 다시 시작할 월드 위치·회전 — 작업 12) — 진행 상태 한 덩어리. 저장은 이 구조체를 통째로 복사 |
| `BP_SaveGame` | `Content/GameMode/` | 부모 SaveGame. 변수 `Progress`(S_PlayerProgress) 하나. 슬롯 파일 = `GaesinLight/Saved/SaveGames/Save0.sav`(에디터 Play 기준, 패키징 빌드는 `%LOCALAPPDATA%/GaesinLight/Saved/SaveGames`) (작업 11, 2026-11-01) |
| `BP_GameInstance` | `Content/GameMode/` | 부모 GameInstance. Project Settings → Maps & Modes → Game Instance Class로 지정(Config). 레벨 이동에도 유지 |
| `BP_TestGameMode` | `Content/GameMode/` | 옛 `BP_GameMode`의 새 이름(옛 이름은 리다이렉터). **테스트용**: `UnlockAllForTest` = 켜짐 |
| `BP_RealGameMode` | `Content/GameMode/` | `BP_TestGameMode`의 자식. **본 게임용**: `UnlockAllForTest` = 꺼짐. 실제 스테이지 맵의 GameMode Override. Default Pawn Class = None(2026-11-01 안내, 테스트 전) → 맵에 놓은 BP_Charactor(Auto Possess Player 0)를 조종 |

**BP_GameInstance**
| 변수 / 함수 | 설명 |
|---|---|
| `Progress` | `S_PlayerProgress` — 진행 데이터 본체. 바꾸는 것은 아래 함수로만 (나중에 저장을 여기에 붙임) |
| `Colors` | Set<EN_LightColor> 임시 변수 (UnlockColor/RemoveColor용, 함수 로컬이 아니라 클래스 변수로 만들어짐 — 동작엔 무관) |
| `UnlockFlashlight` | `Set Members in S_PlayerProgress(Progress, HasFlashlight = true)` |
| `UnlockColor(Color)` | `Colors = Break(Progress).UnlockedColors` → `Colors.Add(Color)` → `Set Members(Progress, UnlockedColors = Colors)` |
| `RemoveColor(Color)` | 위와 같고 `Add` 대신 `Remove` (필터 반납 14번용) |
| `HasColor(Color) → Result` (Pure) | `Break(Progress).UnlockedColors.Contains(Color)` |
| `MarkReturned(Key: Name)` | 로컬 `Returns = Break(Progress).CompletedReturns` → `Returns.Add(Key)` → `Set Members(Progress, CompletedReturns = Returns)` (작업 14) |
| `IsReturned(Key) → Returned` (Pure) | `Break(Progress).CompletedReturns.Contains(Key)` (작업 14) |
| `SlotName` | String, 기본 `Save0` — 저장 슬롯 이름 (작업 11) |
| `SaveProgress` | `Create Save Game Object(BP_SaveGame)` → `Set Progress`(Target = 그 Return Value, 값 = GI Progress) → `Save Game to Slot(Return Value, SlotName, 0)`. Set의 Target을 저장 객체로 잡아야 함 — GI 쪽 Set(Target 숨김)을 쓰면 빈 SaveGame이 저장됨 |
| `LoadProgress` | Branch(`Does Save Game Exist(SlotName, 0)`) True → `Load Game from Slot` → `Cast To BP_SaveGame` → GI `Set Progress = As BP Save Game.Progress` |
| `DeleteProgress` | `Delete Game in Slot(SlotName, 0)` → `Set Progress = Make S_PlayerProgress`(빈 값, 여기만 의도적으로 Make). 아직 호출하는 곳 없음(새 게임 버튼 예정) |
| `SetCheckpoint(Level: Name, SpawnTransform: Transform)` | `Set Members(Progress, CheckpointLevel = Level, CheckpointTransform = SpawnTransform)` → `SaveProgress` (작업 12) |
| `Event Init` | → `LoadProgress`. 게임 실행 시 한 번, 첫 맵 액터 BeginPlay보다 먼저 → BP_Pickup·BP_FilterReturn이 불러온 기록으로 판단 |
- `Make S_PlayerProgress`로 덮어쓰지 말 것: 고르지 않은 항목이 기본값으로 지워짐. 항상 `Set Members` (DeleteProgress만 예외).
- 저장 시점은 체크포인트 통과뿐. 줍기·반납은 메모리(GI)만 바꾸고, 다음 체크포인트에서 함께 파일로 감.

**BP_TestGameMode**: 변수 `UnlockAllForTest`(Bool, Class Default 켜짐). 자식 BP_RealGameMode는 꺼짐. 데이터(`Progress`)는 건드리지 않고 플레이어 검사에만 끼어듦.

### 기타
- `BP_TestGameMode`(옛 BP_GameMode): LightTestMap의 GameMode Override. 플레이어는 GameMode가 스폰(레벨에 BP_Charactor 배치 없음, 15번에서 배치 방식으로 바꿀 예정).
- `BP_PlayerController`: Class Defaults `Should Perform Full Tick When Paused` 켬(2026-11-01, 리스폰 일시정지 중 카메라 암전 진행용). `IMC_Default` + `IA_*`(입력).
- `BP_LightBlock`: BP_AvilityBlock 리다이렉터(사용 안 함).

---

## 2. BP_Activate — 수신 장치 부모

**구성요소**: `DefaultSceneRoot`만. 직접 배치하지 않음.

| 변수 | 타입 | 설명 |
|---|---|---|
| `ChannelRequired` [I] | Map<Int, Int> | 채널 → 필요 신호 수. 없으면 1, 0 이하도 1 |
| `ChannelCount` (내부) | Map<Int, Int> | 채널별 현재 켜진 신호 수 |
| `ActiveChannels` (내부) | Set/Array<Int> | 현재 켜져 있는 채널 |

| 함수 / 이벤트 | 흐름 |
|---|---|
| `Activate(Channel)` (인터페이스) | `ChannelCount[Channel] = Find + 1` → **Add 뒤 새 Find로 다시 읽어** Count ≥ 필요 개수 AND NOT ActiveChannels.Contains → Add → `IsStartOn(Channel)`이면 `OnChannelDeactive`, 아니면 `OnChannelActive` |
| `Deactivate(Channel)` (인터페이스) | `Max(Find − 1, 0)` → Count < 필요 개수 AND Contains → Remove → 반전 규칙대로 `OnChannelDeactive` / `OnChannelActive` |
| `OnChannelActive(Channel)` / `OnChannelDeactive(Channel)` | 빈 함수. 자식이 오버라이드: **Parent 호출 → Switch on Int(Channel)** |
| `IsStartOn(Channel) → bool` (Pure) | 기본 false. 자식이 Switch on Int로 채널별 시작 상태 bool 반환 |

- 주의: 순수 노드는 쓰는 곳마다 다시 계산되므로 `+1`/`Max` 결과를 Branch에 바로 쓰지 말 것 (Add 후 한 번 더 더해짐).
- 주의: 자식에서 Parent 대신 자기 함수를 호출하면 Infinite loop.

---

## 3. 송신 장치

### BP_Button (BPI_Interact)
**구성요소**: `DefaultSceneRoot` → `StaticMesh`

| 변수 | 설명 |
|---|---|
| `SignalTargets` [I] | `S_SignalTarget` 배열 |
| `ButtonMode` [I] | EN_ButtonMode |
| `TimedDuration` [I] | Timed 지속 시간(10) |
| `UseAsset` [I] + `UseStaticMesh` [I] | 외형 교체 (Construction) |
| 켜짐 상태 bool (내부, 이름 미확인) | Togle용 |

- `Interact` → Switch(ButtonMode): JustOn = 한 번만 `SendActivate` / Togle = 상태 반전 후 Send(De)Activate / ReOn = `SendActivate` → `SendDeactivate` 즉시 / Timed = `SendActivate` → Delay(TimedDuration) → `SendDeactivate`. **(미확인: 세부 노드)**
- `SendActivate` / `SendDeactivate`: ForEach(SignalTargets) → Break S_SignalTarget → `Activate`/`Deactivate`(Message, Target, Channel).

### BP_ResetButton (리셋 버튼, BP_Button 자식 — 2026-11-01 그래프 확인, 테스트 전)
**구성요소**: 부모 것 + `ResetArea`(Box Collision, DefaultSceneRoot 자식, NoCollision, Hidden in Game — 범위 표시·계산용). Class Defaults `ButtonMode` = `ReOn`.

```
Event Interact (BPI_Interact) → Parent: Interact (버튼 원래 동작: SignalTargets 신호)
 → Get All Actors Of Class(BP_AvilityBlock) → For Each Loop
     → Branch( Move == Physics
               AND Is Point In Box With Transform(Point = 블록 GetActorLocation,
                                                  BoxWorldTransform = ResetArea.GetWorldTransform,
                                                  BoxExtent = ResetArea.GetUnscaledBoxExtent) )
     → True → ResetToStart(블록)
```
- 블록 액터 위치 = 처음 놓인 자리(Physics는 StaticMesh만 움직임) → 영역 밖으로 던진 블록도 돌아옴.
- Is Point In Box With Transform은 트랜스폼을 역변환(Scale 제거)한 뒤 비교하므로 Extent는 Unscaled.
- Patrol 제외(ResetToStart가 StaticMesh만 옮김) → 같은 버튼 SignalTargets에 Ch1 "처음으로".
- 초록 정지 등 능력 상태는 그대로(자리만 이동).

### BP_PressurePlate
**구성요소**: `DefaultSceneRoot` → `SM_Pressure_Plate1`, `SM_Pressure_Plate2`(윗판), `Trigger`(Box, 윗판의 자식이 아니라 형제 — 자식이면 깜빡임)

| 변수 | 설명 |
|---|---|
| `SignalTargets` [I] | `S_SignalTarget` 배열 |
| `IsOn` (내부) | 이전 상태 |

- Begin/End Overlap(Trigger) → `UpdatePressure`: `GetOverlappingActors`로 BP_Charactor 또는 BP_AvilityBlock이 있는지 재집계 → `IsOn`과 다를 때만 `SendActivate`/`SendDeactivate`.

### BP_Trigger (통과 트리거 + 레벨 이동)
**구성요소**: `DefaultSceneRoot`, `Box`(Box Collision, Hidden in Game, OverlapAllDynamic)

| 변수 | 타입 | 설명 |
|---|---|---|
| `Targets` [I] | `S_SignalTarget` 배열 | **이름이 `SignalTargets`가 아니라 `Targets`** (그래프 확인) |
| `NextLevel` [I] | World Soft Object Reference | 비면 레벨 이동 안 함 |
| `Triggered` (내부) | Boolean | 한 번 보냈는지 |

```
OnComponentBeginOverlap(Box)
 → Branch( OtherActor == GetPlayerCharacter  AND  NOT Triggered )
 → Set Triggered = true
 → ForEach(Targets) → Break → Activate(Message)
 → Completed → Branch( IsValidSoftObjectReference(NextLevel) )
     → GetPlayerCameraManager.StartCameraFade(0→1, 0.5초, Hold) → Delay 0.5 → OpenLevel(by Object Reference, NextLevel)
```
- Deactivate는 보내지 않음(영구 켜짐).

### BP_Pickup (손전등·필터 줍기, BPI_Interact, 작업 6 — 2026-10-24 완료)
**구성요소**: `DefaultSceneRoot` → `ItemMesh`(Static Mesh, Custom: Query Only, WorldDynamic, Visibility만 Block — F 트레이스용, 플레이어·블록과 충돌 없음)

| 변수 | 설명 |
|---|---|
| `PickupType` [I] | `EN_PickupType`(Flashlight / Filter) |
| `FilterColor` [I] | `EN_LightColor`, 필터일 때만 |
| `SignalTargets` [I] | `S_SignalTarget` 배열 (버튼과 같은 이름) |
| `FlashlightMesh` / `FilterMesh` | Class Defaults에서 지정하는 메시 |

| 그래프 | 흐름 |
|---|---|
| Construction | `ItemMesh.SetStaticMesh(Select[PickupType]{FlashlightMesh, FilterMesh})` |
| `SendActivate` | ForEach(SignalTargets) → Break → `Activate`(Message). Deactivate 없음 (1회성·영구) |
| BeginPlay | Cast To BP_GameInstance → Branch(`Select[PickupType]{Break(Progress).HasFlashlight, HasColor(FilterColor)}`) → True → `SendActivate` → `DestroyActor` (이미 가졌으면 신호만 다시 보내고 사라짐 — 레벨 재시작 시 문 복구) |
| `Event Interact` | Cast To BP_GameInstance → Switch on EN_PickupType: `UnlockFlashlight` / `UnlockColor(FilterColor)` → `SendActivate` → Cast To BP_Charactor(GetPlayerCharacter) → `RefreshFlashlight` → `DestroyActor` (Cast Failed도 Destroy로) |
| `CanInteract` | true |
| `GetInteractText` | `Select[PickupType]{"손전등 줍기", Format("{Color} 필터 줍기", Select[FilterColor]{빨강, 파랑, 초록})}` — 10번 UI용 |
- BP_Button 자식·복사로 만들지 않은 이유: Togle/Timed는 Destroy 뒤 실행 못 함, 버튼 메시 교체와 충돌, 불필요한 설정 노출.
- 필터 반납은 별도 BP `BP_FilterReturn`(아래).

### BP_FilterReturn (필터 반납 테이블, BPI_Interact, 작업 14 — 2026-10-25 완료)
**구성요소**: `DefaultSceneRoot` → `TableMesh`(BlockAll, F 트레이스 대상) / `RedSlot`·`GreenSlot`·`BlueSlot`(필터 메시, NoCollision, Visible 꺼짐 — 반납된 색만 켜짐). 부모 Actor(송신 장치라 BP_Activate 아님).

| 변수 | 설명 |
|---|---|
| `SignalTargets` [I] | `S_SignalTarget` 배열 (Target + Channel) |
| `Returned` | 이번 레벨에서 반납 끝 표시 (중복 반납·신호 방지) |
| `ReturnKey` (Name) | 테이블 고유 키 = `GetCurrentLevelName(Remove Prefix ✓)` + `_` + `GetObjectName(Self)` (예: `Stage02_BP_FilterReturn_C_1`). 테이블을 지우고 다시 놓으면 바뀜 |
| `GI` | BP_GameInstance 참조 (BeginPlay 캐싱) |

| 그래프 | 흐름 |
|---|---|
| `HasAnyFilter → HasFilter` (Pure) | `Length(Break(GI.Progress).UnlockedColors) > 0` (원래 `HasAllColors`를 이름 변경) |
| `ShowSlot(Color)` | Switch on EN_LightColor → Red/Green/BlueSlot `SetVisibility(true)` |
| `SendActivate` | ForEach(SignalTargets) → Break → `Activate`(Message). Deactivate 없음 |
| BeginPlay | Cast To BP_GameInstance → `Set GI` → `Set ReturnKey`(위) → Branch(`GI.IsReturned(ReturnKey)`) True → `Set Returned = true` → `SendActivate` (자리 메시는 안 켬: 반납한 색 기록 없음) |
| `Event Interact` | Branch(NOT `Returned` AND `HasAnyFilter`) → `Set Returned = true` → Cast To BP_Charactor(GetPlayerCharacter) → `TurnOff` → `To Array(Break(GI.Progress).UnlockedColors)`(실행 노드 = 복사본, 반복 중 RemoveColor 안전) → ForEach: `GI.RemoveColor` → `ShowSlot` → Completed: `SendActivate` → `GI.MarkReturned(ReturnKey)` |
| `CanInteract` | NOT `Returned` |
| `GetInteractText` | `Select(Returned){False: Select(HasAnyFilter){True "필터 반납", False "반납할 필터가 없습니다"}, True: 빈 문구}` — 10번 UI용 |
- 반납 판정은 진행 데이터만 봄(테스트 모드 `UnlockAll` 무시) → 테스트 모드에서 가짜 반납 기록이 남지 않음.
- 처음 설계(`RequiredColors` 정해진 색 전부 필요)는 2026-10-25 사용자 결정으로 "가진 필터 전부 + 1개 이상"으로 변경.

---

## 4. 수신 장치 (BP_Activate 자식)

### BP_Door / BP_Door2 (미닫이 문)
**구성요소**: `DefaultSceneRoot` → `SM_DoorFrame_Light`, `LeftDoor`, `RightDoor`. BP_Door2는 메시만 다르고 그래프 동일.

| 변수 | 설명 |
|---|---|
| `StartOpen` [I] | 열린 채 시작(0번 반전) |
| `OpenTime` [I](1) | 열리는 시간 (2026-10-30 인스턴스 설정으로 변경, BP_Door2도 같음) |
| `OpenDistance`(100) | 고정값 |
| `LeftCloseLocation` / `RightCloseLocation` (내부) | 닫힌 위치(Construction에서 저장) |
| `Lock` (내부) | 채널 1로 잠겼는지 |
| `DoorTimeLine` | Alpha 0→1 |

- Construction: 문짝 RelativeLocation 저장 → `StartOpen`이면 열린 위치(±OpenDistance Y)로 미리보기.
- BeginPlay: `SetPlayRate(1/OpenTime)` → `StartOpen`이면 `SetNewTime(GetTimelineLength)`.
- `OpenDoor` / `CloseDoor`(Custom Event) → Timeline Play / Reverse. Update → 문짝 SetRelativeLocation(Lerp).
- `OnChannelActive`: Parent → Switch — **0** → Branch(`Lock`) **False** → `OpenDoor` / **1** → `CloseDoor` → `Set Lock = true`.
- `OnChannelDeactive`: Parent → Switch — **0** → `CloseDoor`. (1번 꺼짐은 무시 → 영구 잠금)
- `IsStartOn`: 0 → `StartOpen`.

### BP_Hatch (다락문)
**구성요소**: `DefaultSceneRoot` → `StaticMesh`(문판)

| 변수 | 설명 |
|---|---|
| `WaitTrigger` [I], `IsDown` [I], `StartOpen` [I], `UseUserStaticMesh` [I] + `UserStaticMesh` [I], `OpenTime` [I](1), `HatchWait` [I](2) | README 7장 |
| `MeshClosedTransform ` (내부, **이름 끝에 공백**) | Construction에서 저장 |
| `HatchStartLoc` / `HatchStartRot` / `HingePoint` / `HingeAxis` (내부) | BeginPlay에서 계산 |

- Timeline Update → `Angle = Alpha × Select(IsDown: −90 / 90)` → `SetActorLocationAndRotation(Hinge + RotateAngleAxis(StartLoc − Hinge, Angle, Axis), Compose(StartRot, RotatorFromAxisAndAngle(Axis, Angle)))`.
- `HatchOpen` / `HatchClose`: `SetPlayRate(1/OpenTime)`(Timeline 컴포넌트에서 끌 것) → Play / Reverse.
- Finished → WaitTrigger 꺼짐이면 Delay(HatchWait) → 방향 반대로 (반복형 루프).
- `OnChannelActive/Deactive`: Parent → Switch 0 → WaitTrigger 켜짐이면 `HatchOpen` / `HatchClose`.

### BP_Light (맵 광원)
**구성요소**:
```
DefaultSceneRoot
 ├ Main / StaticMesh / SM_Light_Handle   (받침·몸체 메시)
 └ HeadPivot (Scene, 관절 위치 — 위아래 회전축)
     └ (헤드 메시) + SpotLight
                      └ LightSencer (Box, Object Type LightCencer, WorldDynamic/PhysicsBody만 Overlap)
```

| 변수 | 설명 |
|---|---|
| `LightColor` [I], `StartOn` [I], `ChangeColor` [I], `LightLength` [I](5000) | README 5장 |
| `PitchAngle` [I], `YawAngle` [I], `MoveOffset` [I](3D Widget) | 회전·이동 신호 값 |
| `RotateTime` [I], `MoveSpeed` [I] | 회전 시간(초), 이동 속도(초당 거리) (2026-10-30 인스턴스 설정으로 변경) |
| `PlayerRange`(8000), `ScanInterval`(0.1) | 고정값 |
| `LightColorValue` / `FirstColorValue` (내부) | 현재 색 / 원래 색 |
| `TurnOn` (내부) | 켜짐 상태 |
| `SpreadRadius` (내부) | `LightLength × DegTan(OuterConeAngle)` |
| `Candidates` / `CurrentHit` / `LastLitActor` (내부) | 감지 후보 / 이번 판정 / 지난 판정 |
| `HeadRotateBase` / `ActorRotateBase` (내부) | BeginPlay 시작 회전 |
| `MoveStartLoc` / `MoveEndLoc` (내부) | BeginPlay 이동 시작·끝(월드) |
| `PitchTimeline` / `YawTimeLine` / `MoveTimeline` | Alpha 0→1 |

- Construction: SpreadRadius → LightSencer Extent (L/2, R, R), 위치 (L/2, 0, 0) → 색 값 설정 → `TurnOn = StartOn` + `SetVisibility(StartOn)`.
- BeginPlay: HeadRotateBase → ActorRotateBase → MoveStartLoc(GetActorLocation) → MoveEndLoc(TransformLocation(GetActorTransform, MoveOffset)) → Pitch/Yaw `SetPlayRate(1/RotateTime)` → Move `SetPlayRate(MoveSpeed ÷ Max(Distance, 1))` → `SetTimerByEvent(LightScan, ScanInterval, Looping)`.
- `LightScan`: TurnOn? → 플레이어 거리 ≤ PlayerRange? → `Candidates = LightSencer.GetOverlappingActors(Actor)` → 비면 `ClearLitActor` → ForEach: `DoesImplementInterface(BPI_LightInteractable)` AND `IsLit` → CurrentHit.AddUnique → Completed: LastLitActor에만 있는 것 `UnLightActor`, CurrentHit 전부 `LightActor` → `LastLitActor = CurrentHit`.
- `IsLit(Target)`: SpotLight 위치에서 Target bounds 중심 + 꼭짓점 8곳(Extent×0.8) → 거리·원뿔 각도 검사 → LineTrace(Visibility) HitActor == Target이면 true.
- `LightActor` / `UnLightActor` / `ClearLitActor`: IsValid + 인터페이스 확인 → Add/RemoveColorContribution(Self, LightColorValue).
- Pitch Update → `HeadPivot.SetRelativeRotation(MakeRotator(Pitch = HeadRotateBase.Pitch + PitchAngle × Alpha, 나머지 = HeadRotateBase))`.
- Yaw Update → `SetActorRotation(ComposeRotators(MakeRotator(Yaw = YawAngle × Alpha), ActorRotateBase))`.
- Move Update → `SetActorLocation(VLerp(MoveStartLoc, MoveEndLoc, Alpha))`.
- Custom Event: `ActiveRotatePitch`/`DeactiveRotatePitch`, `ActiveRotateYaw`/`DeactiveRotateYaw`, `ActiveMove`/`DeactiveMove` → Play / Reverse.
- `OnChannelActive`: Parent → Switch — 0 전원 켬(TurnOn + SetVisibility) / 1 색(ChangeColor) / 2 ActiveRotatePitch / 3 ActiveRotateYaw / 4 ActiveMove. `OnChannelDeactive`는 각 반대(1번 Rotate는 무시). **(미확인: Deactive 4 → DeactiveMove 연결)**
- `IsStartOn`: 0 → `StartOn`.

### BP_Light2 (상자형 맵 광원, 2026-10-25 완료)
BP_Light 복사본. 변수·LightScan·IsLit·채널 번호·OnChannelActive/Deactive는 BP_Light와 같음. 차이는 움직이는 대상(액터 → 컴포넌트)뿐. (`BP_Light1`은 BP_Light2로 가는 리다이렉터 — 이름 변경 흔적, 에디터에서 안 보임, 그냥 둠)

**구성요소**:
```
DefaultSceneRoot
 ├ 상자·레일 메시 (고정, SM_Sliding_Door / SM_Sliding_Hatch 등)
 └ Carriage (Scene)           ← 4번 이동: 상대 위치
    └ PartRotate (Scene)      ← 3번 좌우: 상대 회전
       ├ 연결부 메시
       └ HeadPivot (Scene)    ← 2번 위아래
           └ 헤드 메시 + SpotLight → LightSencer
```
- BeginPlay: `HeadRotateBase = HeadPivot.RelativeRotation` → `ActorRotateBase = PartRotate.RelativeRotation`(이름은 그대로지만 PartRotate 기준) → `MoveStartLoc = Carriage.RelativeLocation` → `MoveEndLoc = MoveOffset + MoveStartLoc`(상대 좌표) → SetPlayRate 3개 → 타이머.
- Move Update → `Carriage.SetRelativeLocation(VLerp(MoveStartLoc, MoveEndLoc, Alpha))` (Sweep/Teleport 끔).
- Yaw Update → `PartRotate.SetRelativeRotation(MakeRotator(Roll·Pitch = Break(ActorRotateBase), Yaw = ActorRotateBase.Yaw + YawAngle × Alpha))`.
- Pitch Update → BP_Light와 같음(`HeadPivot.SetRelativeRotation`).

### BP_AvilityBlock (능력 블록)
**구성요소**: `DefaultSceneRoot` → `StaticMesh`(본체, Physics 시뮬레이션·잡기 대상), `SM_Floor_Plain_Light`(Patrol 표시등, NoCollision, StaticMesh의 형제). 크기 변화용 Timeline.

**Construction Script** (2026-10-30 붙여넣기 기준): `CanGrab2 = CanGrab` → Switch(ColorMode) → StaticMesh.SetStaticMesh(Default `SM_Element_Plain` / OwnColor `SM_Element_Chain` / ReactOnly `SM_Element_Trick`) → Switch(Move): Fixed·Physics → 표시등 SetStaticMesh(None) / Patrol 3종 → Branch(IsUserStaticMesh) True → SetStaticMesh(None), False → SetStaticMesh(SM_Floor_Plain_Light) → Branch(IsUserStaticMesh) True → SetStaticMesh(UserStaticMesh) 끝 / False → GetMaterialIndex("crystal") → CreateDynamicMaterialInstance(M_BlockBase) → `BlockMID` → AvilityConfig(UseColor) → Select(ColorMode: Default 흰색 / OwnColor·ReactOnly `Lerp(TargetColor, 흰색, 0.05)`) → SetVectorParameterValue("BlockColor") → `StartColor`. 표시등을 SetVisibility로 숨기지 않고 메시를 비우는 이유: 숨긴 컴포넌트도 GetActorBounds(맵 광원 IsLit 표본점, 보라 SafeReset)에 포함되고, 표시등은 StaticMesh의 형제라 Physics 블록이 움직여도 처음 자리에 남아 Bounds가 늘어남 (2026-10-30).

**인스턴스 설정** [I]: `ColorMode`, `UseColor`, `Move`(Fixed / Physics / PatrolReturn / PatrolRotation / PatrolRestart / PatrolOnce), `MovePoint`(3D Widget 배열, 로컬), `MoveSpeed`, `RestartDelay`(0.5, 채널 1 재출발 대기), `WaitTrigger`, `StartMoving`, `IsUserStaticMesh` + `UserStaticMesh`, `CanGrab`, `CanGrabSkyBlue`, 색별 튜닝값(README 6장).

| 내부 변수 | 설명 |
|---|---|
| `ActiveContributions` | Map<Actor, LinearColor> — Source별 빛 |
| `CurrentColor` | 비트 인코딩 색 (R1 + G2 + B4) |
| `ChargeAlpha` / `HoldRemain` / 상태(EN_Avility) | 충전 → 유지 → 쿨타임 |
| `CanGrab2` | 런타임 들기 가능 여부 (Construction에서 = CanGrab) |
| `BlockMID` / `BlockColor` / `StartColor` / `GlowAmount` | 크리스탈 머티리얼 |
| `BaseSize` | BeginPlay StaticMesh 스케일 |
| `WorldPatrolPoints` / `PatrolIndex` | Patrol 경로(월드) |
| `TriggerPaused` | WaitTrigger 대기 중 |
| `PatrollCount` | 경유지 진행 방향 (+1 / -1, PatrolReturn이 끝에서 × -1) |
| `RestartWaiting` | 채널 1로 처음 위치에 돌아가 `RestartDelay` 동안 기다리는 중 (Tick 이동 전체 스킵) |
| `PurpleResetPending` | 보라 복구 대기 |
| `ResetLocation` / `ResetRotation` | BeginPlay StaticMesh 월드 위치·회전 (BP_Respawn용) |

| 함수 / 이벤트 | 역할 |
|---|---|
| `Add/RemoveColorContribution` (인터페이스) | ActiveContributions 갱신 → `ReCalculate` |
| `ReCalculate` | 합친 색 → CurrentColor → (OwnColor면 `| Select(UseColor)`) → Switch on Int(0/7 None, 1 Red, 2 Green, 3 Yello, 4 Blue, 5 Purple, 6 SkyBlue) |
| `ColorCheck` (매크로) | `(ColorMode != ReactOnly) OR (UseColor == All) OR (색 == UseColor)` |
| `AvilityConfig` | 색별 충전·유지·쿨타임 고정값 |
| `AvilityTick` / `AvilityStart` / `AvilityEnd` | 능력 진행(상태 흐름·발광 식은 CLAUDE.md 2-3, 2026-10-31 그래프 확인). Sequence then_0 = Switch(AvilityState) 충전/유지/쿨타임, then_1 = BlockColor·GlowAmount 갱신. Tick에서 `WaitTrigger && TriggerPaused`면 Patrol 스킵 |
| `GetLightSource` (Pure) | 출력 actor / IsPlayer / Found. 플레이어 기여 우선, 아니면 Keys[0] |
| 빨강 `Push`, 폭발 | Select(Found ? actor : 플레이어) 기준 |
| 파랑 `BlockPull`, `PlayerPull` | PlayerPull은 플레이어가 비출 때만(`ActiveContributions.Contains(GetPlayerCharacter)`) |
| 초록 `Freeze` | `CanGrab2 = false` |
| 노랑 `Y_Grow` / `Y_Reset`, 하늘 `SB_Down` / `SB_Reset`, `Grow` | Timeline Play/Reverse로 크기, SB_Down에서 `CanGrab2 = CanGrabSkyBlue` |
| 보라 `P_Silent`, `P_Collision`, `P_CollisionReset`, `P_Reset`, `SafeReset`(Custom Event) | 반투명·통과·안전 복구 |
| `SetMove` | BeginPlay 첫 노드 (Move 설정 적용) |
| `CanInteract` (인터페이스) | `Move == Physics AND CanGrab2` |
| `ResetToStart` | Branch(Move == Physics) → 플레이어 HeldBlock == Self면 `DropBlock` → `StaticMesh.SetWorldLocationAndRotation(Reset*, Teleport)` → 선속도·각속도 0 |
| `OnChannelActive/Deactive` | Switch 0 → `TriggerPaused = false / true`. Active만 Switch 1 → `RestartFromStart` |
| `RestartFromStart` (Custom Event) | Branch(Length(WorldPatrolPoints) > 0) → `PatrolIndex = 0` → `PatrollCount = 1` → `SetActorLocation(WorldPatrolPoints[0], Teleport)` → `RestartWaiting = true` → `Retriggerable Delay(RestartDelay)` → `RestartWaiting = false` |
| `ReverseDirection` (Custom Event, 작업 23, 2026-10-31 그래프 확인) | Branch(Length(WorldPatrolPoints) > 1) → `PatrollCount = PatrollCount × -1` → `PatrolIndex = Clamp(PatrolIndex + 새 PatrollCount, 0, Length − 1)`. 채널 2 켜짐·꺼짐 모두 호출 예정(상태형, Togle용). CheckChange가 아직 마지막 경유지만 끝으로 봐서 거꾸로 가다 0번에 닿으면 Index −1 위험 → 22-3에서 방향 기준으로 수정 예정 |
| `IsStartOn` | 0 → `StartMoving` |

- BeginPlay: `SetMove` → `BaseSize = StaticMesh.GetComponentScale` → `TriggerPaused = WaitTrigger AND NOT StartMoving` → `ResetLocation` → `ResetRotation` (+ WorldPatrolPoints 변환, 미확인 위치).
- Construction: ColorMode로 메시 → Move로 표시등 → UserStaticMesh면 교체 후 종료, 아니면 `BlockMID` 생성 → 크리스탈 색.
- Tick (2026-10-30): `AvilityTick` → Branch(`RestartWaiting`) F → Branch(`WaitTrigger`) → (T면 Branch(`TriggerPaused`) F) → Switch(`Move`). Patrol 핀마다 `Branch(MoveCheck)` → `SetActorLocation(Movelocation(DeltaTime))` → `Branch(getDistance)`(경유지 도착) → `Branch(CheckChange)`(마지막 경유지): Return T → `PatrollCount × -1` → `PatrolIndex += PatrollCount` / Rotation T → `PatrolIndex = 0` / Restart T → `PatrolIndex = 0` → `SetActorLocation(WorldPatrolPoints[0], Teleport)` / **Once T → 없음(끝에서 멈춤)** / 모두 F → `PatrolIndex += PatrollCount`.

### BP_PressBlock (프레스 블록, BP_AvilityBlock 자식 — 2026-11-01 완료·동작 확인)
**구성요소**: 부모 것 + `PressBox`(Box Collision, DefaultSceneRoot 자식, Hidden in Game, Custom Query Only, Object Type `LightCencer`, WorldDynamic/PhysicsBody/Pawn Overlap·나머지 Ignore — BP_Respawn Box와 같음, Visibility Ignore 필수).

| 변수 (카테고리 Press) | 설명 |
|---|---|
| `ResetBlock` [I] | Bool, 기본 켬 — 닿은 블록 ResetToStart |
| `ResetPlayer` [I] | Bool, 기본 켬 — 닿은 플레이어 소환 |
| `PlayerRespawnLocation` [I] | Vector, 3D Widget, 로컬 |
| `RespawnWorldLocation` | BeginPlay에서 고정한 월드 소환 위치 |

```
Event BeginPlay → Parent: BeginPlay (필수 — 없으면 WorldPatrolPoints 등 부모 준비가 빠져 안 움직임)
 → Set RespawnWorldLocation = TransformLocation(GetActorTransform, PlayerRespawnLocation)
PressBox Begin Overlap → Branch(OtherActor != Self) → Cast To BP_AvilityBlock(OtherActor)
 ├ 성공 → Branch(ResetBlock) → ResetToStart
 └ 실패 → Branch(OtherActor == GetPlayerCharacter AND ResetPlayer) → Cast To BP_Charactor → RespawnAt(RespawnWorldLocation)
```
- 2026-11-01 작업 28: 암전·소환 노드와 `FadeTime`/`Respawning` 변수는 삭제하고 `BP_Charactor.RespawnAt`으로 옮김(아래 기록은 옮기기 전 내용).
- 2026-11-01 사용자: 블록도 리셋 + 블록/플레이어 선택 → BP_Respawn 이벤트 줄 전체 복사, ResetBlock/ResetPlayer 변수(둘 다 기본 켬), 맨 앞 `OtherActor != Self`(자식이라 Cast To BP_AvilityBlock이 자신에게도 성공 → 자기 ResetToStart 방지).
- Delay = `FadeTime + 0.2`(사용자: 완전 암전 0.2초 더 유지).
- 자식 BP의 회색(비활성) `Event BeginPlay → Parent: BeginPlay`는 뒤에 노드를 이어야 활성화됨 — 이었더니 정상(처음엔 비활성이라 RespawnWorldLocation이 원점이었음).
- 레벨에서 PressBox만 크기 조절: 액터 선택 → Details 컴포넌트 목록에서 PressBox → Box Extent(절반 크기)·Location Z. 액터 Scale은 메시·박스·다이아몬드 거리를 모두 키움.
- 박스가 GetActorBounds에 포함돼 맵 광원 IsLit 표본점이 아래로 조금 넓어짐(얇게 두면 영향 작음).

### BP_Mirror (거울)
**구성요소**:
```
DefaultSceneRoot
 ├ SM_Mirror_Handle (받침)
 ├ MirrorPivot (Scene — 정면 = +Y/RightVector)
 │   └ SM_Mirror (판, Relative Rotation 0, WorldDynamic. 스케일 X 가로 / Z 세로)
 └ RectLight / RectLight1 / RectLight2 (빔 3개 풀, BeamLights 배열)
```

| 변수 | 설명 |
|---|---|
| `ActiveContributions` | Map<Actor, LinearColor> — 받은 빛 |
| `BeamLights` | RectLight 3개 배열 |
| `BeamLength` | 3000 고정 |
| `Width` / `Height` | BeginPlay: SM_Mirror 로컬 bounds X/Z × 월드 스케일 |
| `BeamStart` | 판 중심 + N×약간 |
| `BeamInt` | 이번 스캔에서 쓴 빔 개수 |
| `NewLit` | Map<Actor, LinearColor> — 대상별 합친 색 |
| `LastLitActor` | 지난 스캔 대상 |
| `P` / `S` / `Q` | IsBeamLit 계산용(멤버로 만들어짐) |
| 정리 대상 | `UpdateBeamSource`, `BeamSource`, `CombinedColor`, `BeamColor`, `BeamLightColor`, `CurrentHit`, `BeamDir`, `ClearLitActor`(미사용이면) |

| 함수 / 이벤트 | 역할 |
|---|---|
| `Add/RemoveColorContribution` (인터페이스) | ActiveContributions 갱신 |
| `UpdateReflection(Source) → Valid(FrontHit), Dir` | N = MirrorPivot.RightVector. 입사 In = Normal(거울 − Source). `Dot(In, N) < DegCos(120)`(정면 60° 이내)일 때만, Dir = MirrorVectorByNormal(In, N) |
| `IsBeamLit(Target, Dir)` | 표본점 9개 P → 판으로 역투영 Q → 판 안 + 거리 검사 → LineTrace Q→P HitActor == Target |
| `LightActor(Target, Color)` / `UnLightActor(Target)` | 인터페이스로 기여 전달 |
| `MirrorScan` (타이머 0.1초) | 아래 |

```
MirrorScan:
 Clear NewLit → BeamInt = 0
 ForEach( Keys(ActiveContributions) = 광원 )
   Branch(BeamInt < 3) → UpdateReflection(광원) → FrontHit?
     BeamLights[BeamInt]: SetWorldLocationAndRotation(BeamStart, MakeRotFromXZ(Dir, Pivot Up))
                          SetLightColor(Select(R+G+B>0 ? 원래 색 : 흰색)) → SetAttenuationRadius(BeamLength) → SetVisibility(true)
     BoxTraceMultiForObjects(BeamStart → BeamStart + Dir×BeamLength, HalfSize (1, W/2, H/2), Orientation MakeRotFromXZ(Dir, Pivot Up))
     ForEach Hit: IsBeamLit(HitActor, Dir) AND 인터페이스 AND NOT ActiveContributions.Contains(HitActor)   ← 핑퐁 방지
                  → NewLit.Add(HitActor, NewLit.Find(HitActor) + ActiveContributions.Find(광원))    ← 원래 색(흰색 치환 X)
     BeamInt + 1
 Completed:
   For Loop(BeamInt .. 2) → BeamLights[i].SetVisibility(false)
   ForEach(LastLitActor): NewLit에 없으면 UnLightActor
   ForEach(Keys(NewLit)): LightActor(대상, NewLit.Find)
   LastLitActor = Keys(NewLit)
```
- 신호 채널 없음. 회전·이동 신호(M-7)는 만들지 않기로 함(2026-10-25 사용자).

---

### BP_LightSensor (빛 감지 송신 장치, 작업 25 — 2026-10-31 진행 중)
**구성요소**: `DefaultSceneRoot` → `SensorMesh`(Static Mesh, Custom: Object Type WorldDynamic, Visibility Block — 손전등·거울 트레이스와 맵 광원 LightSencer(WorldDynamic/PhysicsBody Overlap)에 잡히게). 부모 Actor(송신 장치). 인터페이스 `BPI_LightInteractable`.

| 변수 | 설명 |
|---|---|
| `SignalTargets` [I] | `S_SignalTarget` 배열 |
| `UseColor` [I] | `EN_ColorState`, 기본 All(아무 빛, 흰 손전등 포함) |
| `ChargeTime` [I] | 계속 비춰야 켜지는 시간(초), 기본 1 (25-2에서 사용) |
| `KeepOn` [I] | 한 번 켜지면 유지, 기본 끔 (25-3에서 사용) |
| `ActiveContributions` | Map Actor → LinearColor, 광원별 빛 |

- 25-1 완료(2026-10-31 붙여넣기 확인): 이벤트 `AddColorContribution` → `ActiveContributions.Add(Source, Color)`, 이벤트 `RemoveColorContribution` → `ActiveContributions.Remove(Source)`. (인터페이스 함수가 반환값이 없어 이벤트로 구현됨)
- `GetColorCode` (Pure, 2026-10-31): 로컬 `Sum` = 0 → ForEach(`ActiveContributions` Values) Sum += 색 → **Completed** → Return `Code` = (R≥0.5 ? 1) + (G≥0.5 ? 2) + (B≥0.5 ? 4). 블록 ReCalculate와 같은 번호(흰 손전등 = 0). (2026-10-31 수정 확인: Return은 Completed에서, Break 입력은 Get Sum)
- 25-2 (2026-10-31 붙여넣기 확인, 테스트 전): 변수 `Matching`(bool, 지난 판정) / `IsOn`(bool) / `ChargeTimer`(Timer Handle). `SendActivate`/`SendDeactivate`는 BP_PressurePlate에서 복사.
  - `AddColorContribution` / `RemoveColorContribution` → Map Add/Remove → `UpdateSensor`.
  - Custom Event `UpdateSensor`: NewMatch = `Length(ActiveContributions) > 0` AND (`UseColor == All` OR `GetColorCode == Select(UseColor: All 0 / Red 1 / Blue 4 / Green 2 / Purple 5 / Yello 3 / SkyBlue 6 / None 99)`) → Branch(NewMatch != `Matching`) True → Set Matching → Branch(Matching): True → Branch(`ChargeTime <= 0`) True → `ChargeDone` / False → `Set Timer by Event`(ChargeDone, ChargeTime, 반복 안 함) → Set `ChargeTimer`; False → `Clear and Invalidate Timer by Handle`(ChargeTimer) → Branch(`IsOn`) True → IsOn = false → `SendDeactivate`. (바뀔 때만 처리: 손전등이 매 틱 Add를 불러도 타이머가 다시 시작되지 않음. 타이머는 0초면 실행 안 돼서 0은 따로)
  - Custom Event `ChargeDone`: IsOn = true → `SendActivate`.
- 다음(25-3): KeepOn + 발광.

## 5. 구역

### BP_Respawn (블록·플레이어 되돌리기 구역)
**구성요소**: `DefaultSceneRoot`, `Box`(Box Collision, Hidden in Game, Custom: Query Only, Object Type `LightCencer`, WorldDynamic / PhysicsBody / **Pawn** Overlap). 플레이어 캡슐은 LightCencer에 Overlap(기존 설정 그대로).

| 변수 | 타입 | 설명 |
|---|---|---|
| `ResetBlock` [I] | Boolean (기본 켜짐) | 블록 되돌리기 |
| `ResetPlayer` [I] | Boolean (기본 꺼짐) | 플레이어 소환 |
| `PlayerRespawnLocation` [I] | Vector, 3D Widget, 로컬 | 플레이어 소환 위치 |

```
OnComponentBeginOverlap(Box) → Cast To BP_AvilityBlock(OtherActor)
 ├ 성공 → Branch(ResetBlock) → True → ResetToStart(Target = As BP Avility Block)
 └ Cast Failed → Branch( OtherActor == GetPlayerCharacter  AND  ResetPlayer )
      → True → Cast To BP_Charactor(GetPlayerCharacter)
                 ├ 성공 → IsValid(HeldBlock) → Is Valid → DropBlock ─┐
                 │                          └ Is Not Valid ──────────┤
                 └ Cast Failed ──────────────────────────────────────┤
      → Teleport(Target = GetPlayerCharacter,                        ←┘
                 DestLocation = TransformLocation(GetActorTransform, PlayerRespawnLocation),
                 DestRotation = 플레이어 GetActorRotation)
      → CharacterMovement.StopMovementImmediately
```
- 2026-11-01 암전: 처음엔 이 BP 안에 Fade·Delay·Respawning을 뒀으나 작업 28에서 BP_Charactor.RespawnAt으로 옮김 → 플레이어 쪽은 `Branch(OtherActor == Player AND ResetPlayer) → Cast To BP_Charactor → RespawnAt(RespawnWorldLocation)`만 남음.
- 2026-11-01 프레스 안내(테스트 전): 변수 `RespawnWorldLocation`(Vector, 내부). `Event BeginPlay` → `Set RespawnWorldLocation = TransformLocation(GetActorTransform, PlayerRespawnLocation)`, Teleport DestLocation = `RespawnWorldLocation`(소환 때 계산하지 않음). 레벨에서 Outliner로 Patrol 능력 블록에 붙이면(Patrol은 SetActorLocation이라 자식 액터가 따라감) 구역만 움직이고 소환 위치는 시작 자리에 고정. 붙인 구역은 ResetBlock 끔(자기 블록과 겹침).
- `==`의 A는 반드시 이벤트의 **Other Actor** (Cast 결과에 연결하면 Cast Failed 경로에서 None이라 항상 false — 실제로 겪음).
- `Teleport`(K2_TeleportTo)는 겹치면 가까운 빈 자리로 비켜 놓음 → `SetActorLocation`보다 안전.

### BP_Checkpoint (체크포인트, 작업 12 — 2026-11-01 완료)
**구성요소**: `DefaultSceneRoot`, `Box`(Box Collision, Hidden in Game, OverlapAllDynamic). 크기 = 액터 Scale.

| 변수 | 타입 | 설명 |
|---|---|---|
| `PlayerSpawnLocation` [I] | Vector, 3D Widget, 로컬 | 다시 시작할 위치. 방향은 액터 회전 |

```
OnComponentBeginOverlap(Box) → Branch(OtherActor == GetPlayerCharacter)
 → True → Cast To BP_GameInstance(GetGameInstance)
 → GetCurrentLevelName(Remove Prefix 켬)
 → SetCheckpoint(Target = As BP Game Instance,
                 Level = String to Name(맵 이름),
                 SpawnTransform = MakeTransform(TransformLocation(GetActorTransform, PlayerSpawnLocation), GetActorRotation, Scale 1))
```
- 2026-11-01 변경(그래프 확인): Branch True 뒤에 `Cast To BP_RealGameMode(GetGameMode)` 성공일 때만 진행, Cast Failed 비움 → 테스트 모드 맵은 저장 안 함.
- 들어올 때마다 저장(한 번만 bool 없음). 마지막에 지난 체크포인트가 기준.
- 위치 복원은 BP_Charactor `MoveToCheckpoint`.

---

## 6. 플레이어

### BP_Charactor
**구성요소**:
```
CapsuleComponent (루트, Character 기본)
 ├ SpringArm → Camera
 │              └ SM_Flashlight (NoCollision 필수) → SpotLight
 └ PhysicsHandle
```
(손전등의 정확한 부착 위치는 미확인)

| 변수 | 설명 |
|---|---|
| `LightLength` | 손전등 판정 거리(고정) |
| 현재 색 / 켜짐 상태 (이름 미확인) | 1~4 키 |
| `CurrentHit` / `LastLitActor` | 이번 / 지난 틱에 비춘 대상 |
| `HeldBlock` | BP_AvilityBlock 참조, 들고 있는 블록 |
| `HeldDistance` | 들기 거리 |
| `CurrentColor` | LinearColor, 현재 손전등 색 |
| `GI` | BP_GameInstance 참조 (BeginPlay에서 캐싱, 작업 6) |
| `UnlockAll` | 테스트 모드 여부 = BP_TestGameMode.UnlockAllForTest (BeginPlay에서 캐싱, 작업 6) |

| 함수 / 이벤트 | 역할 |
|---|---|
| Tick: 손전등 판정 | SpotLight 위치에서 13점(중심 1 + 40% 링 4 + 100% 링 8) 레이캐스트 → CurrentHit → LastLitActor와 비교해 `UnLightActor` / 매번 `LightActor`(색 변경 반영) |
| Tick: 들기 | `IsValid(HeldBlock)` → `CanInteract`(Message) NOT이면 `DropBlock`, 아니면 `PhysicsHandle.SetTargetLocationAndRotation`(카메라 + Forward×HeldDistance, Yaw만) |
| `IA_White` / `IA_Red` / `IA_Green` / `IA_Blue` | Started → `LightControll(LightColor)` (흰색 = (0,0,0)). 같은 키 다시 = 끄기 (LightControll 안에서 처리) |
| BeginPlay 끝 (작업 6) | … → `Set CurrentColor` → `Cast To BP_GameInstance(GetGameInstance)` → `Set GI` → `Cast To BP_TestGameMode(GetGameMode)` → `Set UnlockAll(UnlockAllForTest)` → Branch(`UnlockAll`): False(및 GameMode Cast Failed) → `TurnOff` → `RefreshFlashlight` / True → `RefreshFlashlight`. 본 게임 모드는 항상 빛 꺼진 채 시작 |
| `RespawnAt(Location)` (Custom Event, 작업 28 — 2026-11-01 동작 확인) | Branch(NOT `Respawning`) → `Respawning = true` → `Set Game Paused(true)` → IsValid(HeldBlock) → `DropBlock` / Is Not Valid → (둘 다) `StartCameraFade(0→1, FadeTime, Hold)` → `Delay(FadeTime + 0.2)` → `Teleport(Location, GetActorRotation)` → `CharacterMovement.StopMovementImmediately` → `StartCameraFade(1→0, FadeTime)` → `Set Game Paused(false)` → `Respawning = false`. BP_Respawn·BP_PressBlock이 호출. Class Defaults `Tick Even When Paused` 켬(멈춘 동안 Delay 진행), Event Tick 맨 앞 `Branch(Is Game Paused)` False만 원래 Tick. 일시정지 중 화면 암전은 `BP_PlayerController`의 `Should Perform Full Tick When Paused`가 켜져 있어야 진행됨. 변수 `Respawning`(Bool), `FadeTime`(0.5) |
| BeginPlay 맨 끝 (작업 12) | `Branch(UnlockAll)` **False 쪽** `RefreshFlashlight`만 → `MoveToCheckpoint` → Branch(`Moved`) True → `Delay Until Next Tick` → `Set Control Rotation`(Target = `Get Player Controller`(0), `SpawnRotation`). 본 게임 모드에서만 복원(2026-11-01, 테스트 전) |
| `MoveToCheckpoint → Moved, SpawnRotation` (작업 12) | `GetCurrentLevelName`(Remove Prefix) → Branch(`Break(GI.Progress).CheckpointLevel == String to Name(맵 이름)`) True → `Teleport`(Break Transform(CheckpointTransform) Location / Rotation) → Return(Moved = true, SpawnRotation = Rotation) / False → Return(Moved = false). 카메라 방향을 함수 밖에서 한 프레임 뒤에 넣는 이유: GameMode `FinishRestartPlayer`가 스폰·빙의 뒤 Control Rotation을 PlayerStart 회전으로 덮어씀(함수 안 Delay 불가). 2026-11-01 동작 확인 |
| `CanUseFlashlight` (Pure) | `OR(UnlockAll, Break(GI.Progress).HasFlashlight)` |
| `CanUseColor(Color)` (Pure) | `AND(OR(GI.HasColor(Color), UnlockAll), CanUseFlashlight)` |
| `RefreshFlashlight` | `SM_Flashlight.SetVisibility(CanUseFlashlight, Propagate 끔)` — 메시만. 빛은 LightControll/TurnOff 담당. BeginPlay와 손전등 줍기 직후 호출 |
| 숫자 키 검사 (작업 6) | `IA_Red/Green/Blue` Started → Branch(`CanUseColor(Red/Green/Blue)`) → `LightControll(색)`. `IA_White` Started → Branch(`CanUseFlashlight`) → `LightControll((0,0,0))`. `IA_TurnOff`는 검사 없음. 검사를 LightControll 안이 아니라 키 쪽에 둔 이유: LightControll은 LinearColor를 받고 검사는 EN_LightColor로 묻기 때문 |
| `IA_TurnOff` (E) | 끄기 |
| `IA_Relation` (F) | 바라보는 대상 `Interact` 또는 블록 잡기/놓기 |
| `IA_Crouch` (C, 2026-10-30) | Started → Branch(`Is Crouched`) True → `Un Crouch` / False → `Crouch`. CharacterMovement `Can Crouch` 켬, `Crouched Half Height`(기본 40)로 앉은 높이. 카메라는 캡슐에 붙은 SpringArm이라 캡슐이 낮아진 만큼 같이 내려감(`Crouched Eye Height`는 안 쓰임). 앉으면 점프 불가·`Max Walk Speed Crouched`(엔진 기본). 틈 아래 Un Crouch는 엔진이 공간 날 때까지 대기. 키 매핑 `IMC_Default` |
| `GrabBlock` | `GrabComponentAtLocationWithRotation`(StaticMesh) → 메시 Pawn 응답 Ignore → `TurnOff` → HeldBlock 저장 |
| `DropBlock` | 놓기 + Pawn 충돌 복구 |

---

## 7. 갱신 기록
| 날짜 | 변경 |
|---|---|
| 2026-10-23 | 문서 작성. BP_Respawn 13번 작업 중 상태 반영 |
| 2026-10-23 | BP_Respawn: ResetBlock / ResetPlayer / PlayerRespawnLocation, 플레이어 소환 흐름 (13번 완료) |
| 2026-10-24 | 작업 6: S_PlayerProgress, BP_GameInstance(함수 4개), BP_TestGameMode / BP_RealGameMode, BP_Charactor GI·UnlockAll 캐싱 |
| 2026-10-24 | BP_Charactor: CanUseFlashlight / CanUseColor / RefreshFlashlight, 숫자 키 검사, 본 게임 모드 시작 시 TurnOff |
| 2026-10-24 | BP_Pickup 추가 (작업 6 완료) |
| 2026-10-25 | BP_Light2 상자형 광원 추가 (Carriage 이동, PartRotate 좌우). BP_Mirror 회전·이동 신호 안 함 |
| 2026-10-25 | BP_FilterReturn 추가 (작업 14 완료). GI MarkReturned / IsReturned, S_PlayerProgress.CompletedReturns |
| 2026-10-30 | BP_AvilityBlock Construction: ReactOnly 메시 SM_Element_Trick, 표시등은 숨김 대신 SetStaticMesh(None). BP_Door·BP_Door2 `OpenTime`, BP_Light `RotateTime`·`MoveSpeed` 인스턴스 설정으로 |
| 2026-10-30 | BP_AvilityBlock `PatrolOnce` 모드(EN_BlockMove 추가), 채널 1 "처음으로"(`RestartFromStart`, `RestartWaiting`, `RestartDelay`), Tick 앞 Branch(RestartWaiting) |
| 2026-10-30 | BP_Charactor 앉기: `IA_Crouch`(C, `IMC_Default`), Branch(Is Crouched) → Crouch / Un Crouch, CharacterMovement Can Crouch |
| 2026-10-31 | BP_LightSensor 추가(작업 25-1): 컴포넌트·변수·인터페이스 빛 기록 |
| 2026-10-31 | BP_LightSensor 25-2: GetColorCode, UpdateSensor, ChargeDone, 발판 SendActivate/SendDeactivate 복사 |
| 2026-10-31 | BP_LightSensor 25-3 설계: 타이머(ChargeDone·ChargeTimer) → Event Tick 충전/유지/감소(ChargeAlpha·HoldRemain·HoldTime), SensorMID(M_BlockBase) BlockColor·GlowAmount — 안내만, 미구현 |
| 2026-10-31 | BP_LightSensor 25-3 변경: 색 판정을 enum으로(CurrentState·LitState = EN_ColorState, UseColor == CurrentState) — 안내만, 미구현 |
| 2026-10-31 | BP_LightSensor: StateToColor(Pure) 함수, Construction StartColor = Lerp(StateToColor(UseColor), 흰색, 0.05) — 안내만, 미구현 |
| 2026-10-31 | BP_LightSensor Construction 그래프 확인: CreateDynamicMaterialInstance(SensorMesh, 0, M_BlockBase) → Set SensorMID → Set StartColor(Lerp(StateToColor, 흰색, 0.05)) → SetVectorParameterValue(BlockColor). StateToColor의 State에 UseColor 미연결(항상 All=흰색) → 연결 안내 |
| 2026-10-31 | BP_LightSensor 이벤트 그래프 확인: UpdateSensor(CurrentState = Select(GetColorCode), Matching = Length>0 AND (UseColor==All OR UseColor==CurrentState), Matching이면 LitState) ✅, Tick 충전·유지·감소(FClamp ± dt/FMax(ChargeTime,0.01), HoldRemain, Send) ✅, 외형 BlockColor = Lerp(StartColor, StateToColor(LitState), ChargeAlpha^0.25) ✅. 사용자 "색이 바로 바뀜" → ^0.25가 초반에 급히 오르는 곡선이 원인 → Exp 1(직선)로 안내. GlowAmount Set Scalar 빠짐 → 추가 안내 |
| 2026-10-31 | BP_LightSensor: 비추는 중 색이 바뀌면(흰→빨) 즉시 바뀜 → 새 변수 `ShownColor`(LinearColor). Construction에서 ShownColor = StateToColor(UseColor), Tick then_1에서 ShownColor = CInterpTo(ShownColor, StateToColor(LitState), DeltaSeconds, 3) → BlockColor = Lerp(StartColor, ShownColor, ChargeAlpha) — 안내만 |
| 2026-10-31 | BP_LightSensor: 사용자 "All일 때 한 종류 빛을 계속 받아야 켜지게" → LitState 설정을 UpdateSensor에서 Tick으로 이동. 꺼짐 상태: Matching AND (CurrentState == LitState OR ChargeAlpha <= 0)이면 LitState = CurrentState 후 충전, 다른 색이면 감소(다 빠진 뒤 새 색으로 다시 충전). 켜짐 상태: Matching이면 LitState = CurrentState(켜진 뒤엔 색이 바뀌어도 유지, ShownColor로 부드럽게) — 안내만 |
| 2026-10-31 | BP_LightSensor 그래프 확인: 25-3-8 꺼짐 쪽(같은 색 OR Alpha<=0 → LitState 설정 후 충전, 아니면 감소) ✅, GlowAmount ✅, Exp 1. ShownColor(25-3-7)는 만들지 않음 → 불필요해짐. 사용자 변경: 켜진 뒤 색이 바뀌어도 빛 없음처럼 처리 → 켜짐 쪽 조건 (Matching AND CurrentState == LitState) OR KeepOn, 켜짐 쪽 Set LitState 삭제. 처음 충전 때 색이 살짝 먼저 보이게 Exp 0.5 — 안내만 |
| 2026-10-31 | BP_LightSensor 그래프 확인: 켜짐 쪽 조건 (Matching AND CurrentState == LitState) OR KeepOn ✅, 켜짐 쪽 Set LitState 삭제 ✅, Exp 0.5 ✅. 25-3 그래프 전부 안내대로 완성(동작 테스트 결과 대기) |
| 2026-10-31 | BP_AvilityBlock 보라 반투명 교체: AvilityStart 보라 경로 P_Collision → CreateDynamicMaterialInstance(MI_BlockBase_Translucent) → Set BlockMID → P_Silent 확인. 반투명 안 됨 → M_BlockBase Opacity 파라미터가 Opacity Mask에 연결된 것이 원인. 메시마다 crystal 슬롯 번호가 달라 `CrystalIndex` 변수(Construction에서 저장)로 Element Index 지정 안내 — 미확인 |
| 2026-10-31 | 위 수정 후 보라 시작 반투명 동작 확인(사용자 "잘되"). 다음: SafeReset P_Reset 뒤 M_BlockBase로 BlockMID 되돌리기 |
| 2026-10-31 | 작업 11·12 시작 안내: S_PlayerProgress에 `CheckpointLevel`(Name)·`CheckpointTransform`(Transform), 새 `BP_SaveGame`(SaveGame, 변수 Progress), GI `SlotName`·`SaveProgress`·`LoadProgress`(Event Init)·`DeleteProgress` — 안내만, 미구현 |
| 2026-11-01 | GI `LoadProgress`·`DeleteProgress` 그래프 확인, `SaveProgress`는 Set Progress Target 수정 안내(미확인), `CheckpointTransform` Vector → Transform 안내. 임시 저장 키(K/L)는 빼기로 함(사용자: 키 저장은 나중) → 12-1 GI `SetCheckpoint(Level, SpawnTransform)`(Set Members → SaveProgress) + 12-2 `BP_Checkpoint`(Box, `PlayerSpawnLocation` 3D 위젯, 플레이어 겹침마다 저장) 안내 — 미구현 → **같은 날 완료·동작 확인**(아래) |
| 2026-11-01 | BP_Checkpoint Event Graph·GI SetCheckpoint 그래프 확인(Set Members 뒤 Save Progress 미연결 → 연결 안내), 저장 동작 확인(사용자). 12-3 안내: BP_Charactor `MoveToCheckpoint`(같은 맵이면 Teleport + Set Control Rotation) + BeginPlay 끝에서 호출 — 미확인 |
| 2026-11-01 | **작업 11(체크포인트 저장)·12 완료, 사용자 "잘 되는데" 동작 확인.** 구조 반영: S_PlayerProgress 필드, BP_SaveGame, GI 저장 함수·Event Init, 5장 BP_Checkpoint, BP_Charactor MoveToCheckpoint. MoveToCheckpoint `==`는 String to Name을 거쳐 Name끼리 비교(String을 바로 꽂았던 것 수정) |
| 2026-11-01 | 방향이 항상 PlayerStart 방향 → GameMode FinishRestartPlayer가 Control Rotation을 덮어쓰는 것으로 추정. MoveToCheckpoint에 출력 Moved·SpawnRotation, Event Graph에서 Delay Until Next Tick 뒤 Set Control Rotation으로 옮기도록 안내 → **사용자 "방향 잘 되고" 확인**, 6장 표 갱신 |
| 2026-11-01 | 사용자 요청: 저장은 본 게임 모드에서만 + 본 게임 모드는 맵에 놓은 캐릭터 빙의(작업 15). 안내: BP_Checkpoint Cast To BP_RealGameMode, BP_Charactor 복원은 UnlockAll False 쪽만, BP_RealGameMode Default Pawn Class None, 맵의 BP_Charactor Auto Possess Player 0 — 테스트 전 |
| 2026-11-01 | BP_Respawn 플레이어 소환 암전 안내(FadeTime, Respawning, StartCameraFade 두 번 + Delay) — 테스트 전 |
| 2026-11-01 | BP_Respawn 프레스 용도: RespawnWorldLocation(BeginPlay 고정) + Outliner로 Patrol 블록에 부착 안내 — 테스트 전 |
| 2026-11-01 | BP_Respawn 그래프 확인: RespawnWorldLocation(BeginPlay 고정 → Teleport) 적용됨. 암전(StartCameraFade·Delay·Respawning)은 아직 없음. 붙여넣기에 ResetToStart 호출 노드 ErrorType=1 기록 — 컴파일 메시지 확인 요청. BP_PressBlock.uasset 생성됨(내용 미확인) |
| 2026-11-01 | BP_Respawn 암전 그래프 확인: 연결 순서(Respawning·NOT·AND C, 세 갈래 → StartCameraFade → Delay(FadeTime) → Teleport → Stop → StartCameraFade → Respawning false) 정상. 두 StartCameraFade 값이 전부 0 → 첫 번째 To 1·Duration FadeTime·Hold, 두 번째 From 1·Duration FadeTime으로 수정 안내, FadeTime 기본값 0.5 확인 요청 |
| 2026-11-01 | BP_PressBlock 그래프 확인: 이벤트 줄 복사·ResetBlock/ResetPlayer·암전 값(첫 번째 0→1 Hold, 두 번째 1→0, Duration FadeTime) 정상, Delay = FadeTime + 0.2(사용자 변경, 어둠 유지). 빠진 것: Event BeginPlay·Parent: BeginPlay가 회색(자식 BP 기본 생성, 비활성)이고 Set RespawnWorldLocation 없음 → 원점 소환, OtherActor != Self 없음 → 수정 안내 |
| 2026-11-01 | 사용자 확인: 체크포인트 저장(LightTestMap = BP_RealGameMode), BP_Respawn 암전, ResetToStart 컴파일 에러 없음, BP_LightSensor(작업 25), 앉기(24), 보라 SafeReset 불투명 복귀, 채널 2 방향 바꾸기(23), Physics 블록 낙하(물리 값 조정, 21), Patrol 표시등 메시 None 방식(2026-10-30 변경). 작업 20은 안 함(수동). 새 작업 26: 들기 거리 = HeldDistance + 블록 반 크기 안내 |
| 2026-11-01 | 작업 26·27(들기 거리 = HeldDistance + 블록 반 크기, − Camera Up × HeldDownOffset 40) 사용자 수정 → 2026-11-01 동작 확인 |
| 2026-11-01 | 작업 28 안내: 리스폰 연출을 BP_Charactor.RespawnAt(Location)으로 모으고 Set Game Paused로 세상 멈춤(캐릭터 Tick Even When Paused + Tick 앞 Is Game Paused 건너뛰기), BP_Respawn·BP_PressBlock은 호출만 — 미구현 |
| 2026-11-01 | 작업 28 RespawnAt 그래프 확인: 순서 정상(NOT Respawning → Paused → DropBlock → Fade 0→1 Hold → Delay FadeTime+0.2 → Teleport(Location) → Stop → Fade 1→0 → Unpause → Respawning false). Is Valid의 Is Not Valid 미연결 → 블록 안 들면 일시정지 고착, 연결 안내. 두 번째 Fade의 Target 에러는 연결 전 컴파일 흔적으로 추정 |
| 2026-11-01 | 작업 28 테스트: 일시정지 중 Camera Fade가 진행 안 됨(멈춤만 보이고 암전 거의 없음) → ① BP_PlayerController Class Defaults `Should Perform Full Tick When Paused` 체크(GameMode의 Player Controller Class 확인) 안내, 안 되면 ② 완전히 어두워진 뒤에만 Paused(Delay FadeTime → Paused → Teleport → Delay 0.2 → Unpause → Fade 1→0) |
| 2026-11-01 | **작업 28 완료·동작 확인**: ①(BP_PlayerController Should Perform Full Tick When Paused)로 해결. BP_Respawn·BP_PressBlock은 Cast To BP_Charactor → RespawnAt(RespawnWorldLocation)만, 각자 암전 노드·Respawning·FadeTime 삭제 |
| 2026-11-01 | **BP_PressBlock 동작 확인(사용자 "잘되")** — BeginPlay 활성화·Self 확인 반영. 가이드 #block-press-size(UserStaticMesh 때 PressBox만 크기 조절) 추가 |
| 2026-11-01 | 사용자: 레벨 수동 부착 대신 블록 버전 따로 → `BP_PressBlock`(BP_AvilityBlock 자식, 복사 대신 자식 추천) 안내 — 미구현 |
| 2026-11-01 | 작업 29 리셋 버튼 안내: BP_Respawn 부모를 BP_Activate로 바꿔 수신 장치로(Class Settings → Parent Class), BeginPlay에 Parent: BeginPlay 호출, 함수 `ResetAllBlocks` = Box.GetOverlappingActors(BP_AvilityBlock) → ForEach → Branch(Move == Physics) → ResetToStart, `OnChannelActive` 오버라이드 Parent 호출 → Switch on Int 0 → ResetAllBlocks. 방 전체를 덮는 구역 + ResetBlock/ResetPlayer 끔 + ReOn 버튼 Ch0. Patrol 블록 제외 이유: ResetToStart가 StaticMesh만 순간이동해 액터와 어긋남 — 미구현 |
| 2026-11-01 | 작업 29 변경(사용자 "리셋용 버튼으로 따로"): BP_Respawn 수신 장치화 안 취소 → `BP_ResetButton`(BP_Button 자식) + `ResetBlocks`[I](BP_AvilityBlock 배열). Event Interact → Parent: Interact → ForEach → IsValid → Branch(Move == Physics) → ResetToStart. Class Defaults ButtonMode ReOn. 가이드 채널 표의 BP_Respawn 0번 행 삭제 — 미구현 |
| 2026-11-01 | 작업 29 최종안(사용자 "ResetBlock 꺼 두고 버튼 누르면 켜서 초기화하고 다시 꺼지는 동작만"): bool 토글은 BeginOverlap을 다시 만들지 않아 무효 → BP_Respawn 새 함수 `ResetInside`(Box.GetOverlappingActors(BP_AvilityBlock) → ForEach → Branch(Move == Physics) → ResetToStart, ResetBlock 무시) + BP_ResetButton `ResetZones`[I](BP_Respawn 배열) → Event Interact → Parent: Interact → ForEach → IsValid → ResetInside. ResetBlocks 변수 안 씀 — 미구현 |
| 2026-11-01 | 작업 29 최종 설계(사용자 "버튼 주변으로"): BP_ResetButton(BP_Button 자식) `ResetRadius`[I] 2000 + `RangePreview` Sphere(Construction SetSphereRadius). Event Interact → Parent: Interact → Get All Actors Of Class(BP_AvilityBlock) → ForEach → Branch(Move == Physics AND GetDistanceTo ≤ ResetRadius) → ResetToStart. 앞선 ResetBlocks·ResetZones·ResetInside 안은 폐기 — 미구현 |
| 2026-11-01 | 작업 29 변경(사용자 "영역을 사각형으로"): ResetRadius·RangePreview(구) 대신 `ResetArea`(Box Collision, NoCollision, Hidden in Game). 조건 = Move == Physics AND Is Point In Box With Transform(블록 GetActorLocation, ResetArea.GetWorldTransform, ResetArea.GetUnscaledBoxExtent) — 회전·Scale 반영(역변환 후 Unscaled Extent와 비교). 미구현 |
| 2026-11-01 | 작업 29 변경(사용자 "충돌 판정 블록처럼 배치형식"): ResetArea를 BP_Respawn Box와 같은 콜리전(Query Only, LightCencer, WorldDynamic/PhysicsBody Overlap)으로, 판정 = ResetArea.GetOverlappingActors(BP_AvilityBlock) → Branch(Move == Physics) → ResetToStart. Is Point In Box With Transform(처음 위치) 안 폐기. 지금 안에 있는 블록만 — 미구현 |
| 2026-11-01 | **BP_ResetButton 그래프 확인**: Interact → Parent: Interact → Get All Actors Of Class(BP_AvilityBlock) → ForEach → Branch(Move == NewEnumerator1(Physics) AND Is Point In Box With Transform(GetActorLocation, ResetArea.GetComponentToWorld, GetUnscaledBoxExtent)) → ResetToStart. 처음 위치 판정 방식으로 구현(충돌 판정 안 대신). 회색 기본 이벤트 3개(BeginPlay/ActorBeginOverlap/Tick)는 비활성이라 무해. 구조 절 추가 — 테스트 전 |
