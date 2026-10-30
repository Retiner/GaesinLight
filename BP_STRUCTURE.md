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
| `S_PlayerProgress` | `Content/BluePrint/` | `HasFlashlight`(Bool), `UnlockedColors`(Set<EN_LightColor>), `CompletedReturns`(Set<Name>, 반납 끝난 테이블 키 — 작업 14) — 획득 상태 한 덩어리. 저장 기능은 이 구조체를 통째로 복사 |
| `BP_GameInstance` | `Content/GameMode/` | 부모 GameInstance. Project Settings → Maps & Modes → Game Instance Class로 지정(Config). 레벨 이동에도 유지 |
| `BP_TestGameMode` | `Content/GameMode/` | 옛 `BP_GameMode`의 새 이름(옛 이름은 리다이렉터). **테스트용**: `UnlockAllForTest` = 켜짐 |
| `BP_RealGameMode` | `Content/GameMode/` | `BP_TestGameMode`의 자식. **본 게임용**: `UnlockAllForTest` = 꺼짐. 실제 스테이지 맵의 GameMode Override |

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
- `Make S_PlayerProgress`로 덮어쓰지 말 것: 고르지 않은 항목이 기본값으로 지워짐. 항상 `Set Members`.

**BP_TestGameMode**: 변수 `UnlockAllForTest`(Bool, Class Default 켜짐). 자식 BP_RealGameMode는 꺼짐. 데이터(`Progress`)는 건드리지 않고 플레이어 검사에만 끼어듦.

### 기타
- `BP_TestGameMode`(옛 BP_GameMode): LightTestMap의 GameMode Override. 플레이어는 GameMode가 스폰(레벨에 BP_Charactor 배치 없음, 15번에서 배치 방식으로 바꿀 예정).
- `BP_PlayerController`, `IMC_Default` + `IA_*`(입력).
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
| `AvilityTick` / `AvilityStart` / `AvilityEnd` | 능력 진행. Tick에서 `WaitTrigger && TriggerPaused`면 Patrol 스킵 |
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
| `IsStartOn` | 0 → `StartMoving` |

- BeginPlay: `SetMove` → `BaseSize = StaticMesh.GetComponentScale` → `TriggerPaused = WaitTrigger AND NOT StartMoving` → `ResetLocation` → `ResetRotation` (+ WorldPatrolPoints 변환, 미확인 위치).
- Construction: ColorMode로 메시 → Move로 표시등 → UserStaticMesh면 교체 후 종료, 아니면 `BlockMID` 생성 → 크리스탈 색.
- Tick (2026-10-30): `AvilityTick` → Branch(`RestartWaiting`) F → Branch(`WaitTrigger`) → (T면 Branch(`TriggerPaused`) F) → Switch(`Move`). Patrol 핀마다 `Branch(MoveCheck)` → `SetActorLocation(Movelocation(DeltaTime))` → `Branch(getDistance)`(경유지 도착) → `Branch(CheckChange)`(마지막 경유지): Return T → `PatrollCount × -1` → `PatrolIndex += PatrollCount` / Rotation T → `PatrolIndex = 0` / Restart T → `PatrolIndex = 0` → `SetActorLocation(WorldPatrolPoints[0], Teleport)` / **Once T → 없음(끝에서 멈춤)** / 모두 F → `PatrolIndex += PatrollCount`.

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
- `==`의 A는 반드시 이벤트의 **Other Actor** (Cast 결과에 연결하면 Cast Failed 경로에서 None이라 항상 false — 실제로 겪음).
- `Teleport`(K2_TeleportTo)는 겹치면 가까운 빈 자리로 비켜 놓음 → `SetActorLocation`보다 안전.

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
| `CanUseFlashlight` (Pure) | `OR(UnlockAll, Break(GI.Progress).HasFlashlight)` |
| `CanUseColor(Color)` (Pure) | `AND(OR(GI.HasColor(Color), UnlockAll), CanUseFlashlight)` |
| `RefreshFlashlight` | `SM_Flashlight.SetVisibility(CanUseFlashlight, Propagate 끔)` — 메시만. 빛은 LightControll/TurnOff 담당. BeginPlay와 손전등 줍기 직후 호출 |
| 숫자 키 검사 (작업 6) | `IA_Red/Green/Blue` Started → Branch(`CanUseColor(Red/Green/Blue)`) → `LightControll(색)`. `IA_White` Started → Branch(`CanUseFlashlight`) → `LightControll((0,0,0))`. `IA_TurnOff`는 검사 없음. 검사를 LightControll 안이 아니라 키 쪽에 둔 이유: LightControll은 LinearColor를 받고 검사는 EN_LightColor로 묻기 때문 |
| `IA_TurnOff` (E) | 끄기 |
| `IA_Relation` (F) | 바라보는 대상 `Interact` 또는 블록 잡기/놓기 |
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
