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
        발판/스위치 → BP_PlatformController ─ 조건 해제 귀환 / 상시 독립 왕복 ─→ BP_ReturnPlatform
        신호 → BP_RespawnPointSetter ─ SetRespawnDestination ─→ 저장된 ResetLocation만 변경
                                  └ BPI_RespawnDestination ─→ 사용자 정의 비블록 수신 BP
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

추가 인터페이스(2026-11-05): `Content/BluePrint/BPI_RespawnDestination` — `SetRespawnDestination(Location:Vector) → Accepted:Bool`. 사용자 정의 비블록 BP의 다음 리스폰 위치 저장용 계약이다. 구현부는 위치만 기록하고 실제 리스폰 이벤트에서 사용한다. 기본 물리 블록은 아래 공개 함수를 직접 호출하므로 이 인터페이스를 따로 구현하지 않는다.
| 이름 | 내용 |
|---|---|
| `S_SignalTarget` | `Target`(Actor), `Channel`(Int, 기본 0) |
| `EN_ButtonMode` | JustOn / Togle / ReOn / Timed / RepeatOn (기존 항목 순서 유지, 마지막에 추가) |
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
- `BP_PlayerController` Event BeginPlay(2026-11-03, 작업 32): Create Widget(`WBP_HUD`, Owning Player = Self) → Set `HUD`(WBP_HUD 참조 변수) → Add to Viewport. 2026-11-04 로컬 적용, 생성·Viewport 연결을 실제 PIE에서 확인. 기존 ShouldPerformFullTickWhenPaused 유지.
- `Content/UI/WBP_HUD`(작업 32, 2026-11-04 로컬 적용·PIE 검증): Canvas Panel → `Crosshair`(Image 6×6, 정중앙 Anchors·Alignment 0.5, Rounded Box 반지름 3, 흰색 0.8) / `InteractText`(Text, 정중앙 + Y 40, Text 바인딩 `Get_InteractText_Text` = Cast BP_Charactor(Get Owning Player Pawn) → IsValid(HeldBlock) "F: 놓기" → IsValid(FocusTarget) → GetInteractText(FocusTarget) → Text Is Empty면 빈 글자 / 아니면 Format "F: {Action}". 실제 반영 커밋의 메시지 Target은 FocusTarget에 연결되어 있음) / `ColorSlots`(Horizontal Box, 오른쪽 아래 −40, −40) 안에 `WBP_ColorSlot` 4개(1 흰색 UseFlashlight, 2 Red, 3 Green, 4 Blue).
- `Content/UI/WBP_ColorSlot`: Vertical Box → Overlay(`OuterCircle` 44 반지름 22 / `InnerCircle` 26 반지름 13) + `KeyText`. 변수 `SlotColor`·`KeyLabel`·`UseFlashlight`·`FilterColor`[I]. Event Pre Construct → InnerCircle 색 = SlotColor, OuterCircle 색 = SlotColor(A 0.3), KeyText = KeyLabel. InnerCircle Visibility 바인딩 = Cast BP_Charactor → Select(UseFlashlight ? CanUseFlashlight : CanUseColor(FilterColor)) → Visible/Hidden (사용자 결정: 바깥 원 항상, 안쪽 원은 가진 것만).
- HUD 선택 업데이트(2026-11-04): a1e97b7→92a6a5e의 HUD 구현·병합 두 커밋 중 자산 4개만 반영하고 문서 3개를 현재 로컬 설명과 병합했다. BP_Charactor의 유일한 그래프 변경은 FindTarget의 벽 확인 DrawDebugType=ForDuration→None이며 상호작용 로직은 동일하다. 새 컨트롤러 HUD 연결 및 위젯 2개 적용. 기존 캐릭터·컨트롤러 파일이 기준본과 같아 로컬 수정 충돌 없음.
- 별도 복사본의 실제 PIE 16개 검사: HUD 생성, 조준점·빈/버튼/들기 문구, 색 슬롯 4개·키 1~4, 미획득 숨김·손전등/빨강 획득·반납·테스트 모드 표시 통과. 임시 상태 설정 함수는 검증 복사본의 메모리에서만 사용하고 저장하지 않았다. 적용한 원본 파일 4개는 Git 객체와 동일하다. 실제 로컬에서 HUD와 최근 장치 BP 9개 컴파일 오류·경고 0, Blue/Tutorial+Red/Green 로딩 및 일시정지 카메라 지원 확인. 모든 레벨 6개와 다른 BP·Config 해시 보존. 백업/결과 Saved/CodexBackups/HUDUpdate-20261104.
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
| `IsOn` (내부) | JustOn / Togle / Timed / RepeatOn 상태 |

- `Interact` → Switch(ButtonMode): JustOn = 한 번만 `SendActivate` / Togle = 상태 반전 후 Send(De)Activate / ReOn = `SendActivate` → `SendDeactivate` 즉시 / Timed = `SendActivate` → Delay(TimedDuration) → `SendDeactivate`. **(미확인: 세부 노드)**
- `SendActivate` / `SendDeactivate`: ForEach(SignalTargets) → Break S_SignalTarget → `Activate`/`Deactivate`(Message, Target, Channel).

**2026-11-02 로컬 추가 — RepeatOn**: Switch의 `NewEnumerator4` → Branch(IsOn). false면 IsOn=true → SendActivate, true면 SendDeactivate → IsOn=true → SendActivate. 처음 눌렀을 때부터 켜진 채로 유지하며, 이후에는 자기의 기존 신호 하나를 해제한 뒤 다시 제공하므로 ChannelCount가 누적되지 않는다. 채널 번호는 기존 SignalTargets의 Channel 사용(0으로 고정하지 않음). 다른 송신 장치의 신호와 ChannelRequired 계산은 기존 규칙을 따른다. 0번은 출발·정지만 하며 방향을 정방향으로 초기화하지 않는다.

- 공유 enum을 사용하는 BP_BlockSignalTrigger에도 같은 RepeatOn 분기를 연결했다. 기존 네 모드와 모든 기본값은 유지. BP_ResetButton 자식은 기본 ReOn 유지, 파일 수정 없음.
- 검증: 별도 임시 맵의 직접 BP 호출 27개 검사 통과. 100회 눌러도 신호 수 1, 다른 송신자 기여 보존, 0번 재출발/유지, 1번 반복 리셋, 2번 반복 방향 전환, 임의 채널·여러 대상, 기존 모드와 ResetButton 기본값 확인. 새 프로세스 오류·경고 0. F키 상호작용·Timed 만료 PIE는 미실시. 백업: Saved/CodexBackups/ButtonRepeatOn-20261102.

### BP_ResetButton (리셋 버튼, BP_Button 자식 — 2026-11-01 그래프 확인, 2026-11-06 동작 확인)
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

### BP_BlockSignalTrigger (블록 진입 신호 구역, 로컬 추가 2026-11-02)
`BP_Trigger` 복제본이며 부모는 Actor. 원본 Box를 유지하고 플레이어 한 번 감지·레벨 이동 로직은 제거했다. `BP_Button`과 같은 구조체 배열과 인터페이스 메시지로 송신한다.

| 변수 | 설명 |
|---|---|
| `SignalTargets` [I] | 수신 액터와 Channel 정수 배열. 버튼과 동일한 구조 |
| `ButtonMode` [I] | JustOn / Togle / ReOn / Timed / RepeatOn. 기본 ReOn |
| `TimedDuration` [I] | Timed 유지 시간, 기본 10초 |
| `TriggerBlock` [I] | 비우면 조건을 만족하는 모든 능력 블록, 지정하면 그 인스턴스만 |
| `OnlyPhysicsBlocks` [I] | 기본 true. false면 Fixed·Patrol 등 다른 Move도 감지 |
| `IsOn` | JustOn·Togle·Timed용 내부 상태 |

- Box BeginOverlap → `HandleBlockOverlap(OtherActor, OtherComp)` → Cast BP_AvilityBlock → OtherComp가 그 블록의 본체 `StaticMesh`인지 검사 → OnlyPhysicsBlocks면 Move == Physics 검사 → TriggerBlock이 유효하면 OtherActor와 같은지 검사 → `TriggerSignal`.
- `TriggerSignal`: JustOn은 최초 한 번 Activate, Togle은 IsOn 반전 후 Activate/Deactivate, ReOn은 Activate 직후 Deactivate, Timed는 IsOn일 때 재진입 무시하고 Activate → Delay(TimedDuration) → Deactivate.
- RepeatOn(2026-11-02 추가): 첫 진입에 Activate 후 유지. 이후 진입에는 자기 신호를 Deactivate → Activate하여 중복 누적 없이 재작동 후 유지.
- `SendActivate` / `SendDeactivate`: ForEach(SignalTargets) → Break S_SignalTarget → BPI_Activatable 메시지(Target, Channel). 버튼과 같은 구조.
- 콜리전: QueryOnly, Object Type LightSencer(BP_Respawn과 동일), WorldDynamic·PhysicsBody Overlap, 나머지 Ignore. 장식 컴포넌트 진입은 무시한다.
- 플랫폼 복귀: SignalTargets에 플랫폼 / Channel 1, ButtonMode ReOn. 반복 진입 때마다 MovePoint[0]으로 순간이동한다. 낙하 블록 리스폰은 별도 BP_Respawn 담당이며, 신호 구역은 리스폰 구역보다 위에 배치한다.
- 검증: 별도 임시 맵에서 감지 처리 함수를 호출하는 25개 검사 통과. 채널 0 송수신, 채널 1 반복 플랫폼 복귀, 채널 2 ReOn 반복 방향 전환, 선택 블록·Move·본체 필터, 여러 수신 대상, 모드 상태와 콜리전 확인. 새 프로세스 로드·컴파일 오류/경고 0. 실제 물리 진입과 Timed 만료의 PIE 검증은 미실시.
- 현재 플랫폼 채널 2는 OnChannelActive에만 ReverseDirection 연결. OnChannelDeactive의 2번은 미연결이므로 반복 방향 전환에는 ReOn을 사용한다. 원본 동작은 수정하지 않았다.

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

### BP_PlatformController — 시작점 AND 조건·건너편 왕복 (2026-11-05)

- 부모 BP_Activate, 상속 DefaultSceneRoot. 플랫폼 BP의 그래프는 수정하지 않는다. Platform Control의 `TargetPlatform` [I]는 BP_ReturnPlatform 참조 하나. 내부 `ControlMode` Int(0=미조작/1=조건부/2=독립), `HomeGatePaused` Bool(이전 정지 모드 호환용, 현재 false만 기록), `ControllerInitialized` Bool. 기본 ChannelRequired={0:1,1:1,3:1}.
- 0번=시작점 발판 유지, 1번=시작점 Togle 스위치 유지, 3번=건너편 ReOn 펄스. OnChannelActive(0/1), OnChannelDeactive(0/1) → EvaluateHomeConditions. OnChannelActive(3) → HandleRemoteButton. 3번 해제 및 다른 채널은 무동작. 부모 ChannelCount/ActiveChannels/ChannelRequired 임계값 계산 그대로 사용.
- 순수 질의: IsPlatformReady는 유효 대상·HasReturnPath 검사. IsPlatformBusy는 미준비면 true, 준비되면 PlatformPhase==3 OR !TriggerPaused이며 독립 이동에 시작점 조건이 개입하지 않도록 검사할 때 사용한다. IsAtFarEndpoint는 유효 경로 마지막 점과 플랫폼 ActorLocation 거리≤0.01 AND TriggerPaused(진단용 유지, 현재 건너편 버튼 분기에 사용하지 않음). BothHomeInputsActive는 ActiveChannels의 0·1 모두 포함 여부. 무효 대상 분기는 로컬 결과를 저장하여 객체 접근을 방지한다.
- EvaluateHomeConditions(사용자 재조정 2026-11-05): 대상 미준비, 또는 ControlMode=2이고 Busy면 무시한다. 두 조건 충족 AND PlatformPhase=0일 때 Mode=1/GatePaused=false → ReleaseReturnHold로 출발. 미충족 AND Mode=1이면 GatePaused=false → HoldReturnToStart로 귀환한다. 이동 중·건너편 대기 중 모두 귀환하며 출발 지연은 취소된다. 귀환 도중 조건 복구는 방향을 바꾸지 않고 시작점까지 복귀 완료 후 대기한다. 유지 입력으로 자동 재출발하지 않으며 새 조건 활성 전이가 필요하다.
- HandleRemoteButton(사용자 재조정 2026-11-05): Ready만 검사하고 Busy는 검사하지 않는다. Mode=2/GatePaused=false → 현재 PlatformPhase가 1(전진/건너편 대기) 또는 3(출발 지연)이면 HoldReturnToStart, 0(시작점) 또는 2(귀환)이면 ReleaseReturnHold. 매 새 3번 활성 전이마다 현재 목적지를 반대로 바꾸며 지연 중에도 즉시 취소 가능. 중간 위치에서 기존 경로를 따라 반전하고 순간이동/예약/신호 누적 없음. 초록 Freeze는 유지하면서 방향만 변경한다. 독립 왕복 중 시작점 신호는 집계만 갱신하고 이동에는 개입하지 않는다.
- ReceiveBeginPlay/ReceiveTick → InitializeController. 초기화되지 않았고 경로가 준비되면 Initialized=true → EvaluateHomeConditions → SetActorTickEnabled(false). 대상 BeginPlay보다 먼저 받은 시작점 입력도 보존한다. Tick에서 계속 이동/조건/도착을 재평가하지 않는다.
- 기존 함수만 호출하여 경유지 순서·구간 속도·출발 지연·초록 Freeze·PressBox 기능을 유지한다. 플랫폼 채널 신호를 인위적으로 추가하지 않아 5번 유지 래치/0번 필요 개수와 충돌하지 않는다. 직접 플랫폼 신호와 혼용하지 말고 플랫폼 하나당 제어 BP 하나만 사용한다. ReturnOnSignalOff=false 권장. 시작점=MovePoint[0], 건너편=마지막 MovePoint. 연결표는 HTML #platform-controller. 백업·검증 Saved/CodexBackups/PlatformController-20261105.
- 최초 정지/이동 중 입력 무시 구현 검증은 Saved/CodexBackups/PlatformController-20261105(54개 및 저장본 재검사). 현재 귀환/상시 반전 변경의 백업·검증은 Saved/CodexBackups/PlatformControllerReturn-20261105. 현재 동작은 위 재조정 설명을 따른다.
- 재조정 검증: 직접 36개 + 실제 큐브 압력판 진입/제거와 Togle/ReOn 버튼 PIE 19개, 총 55개 및 저장본 55개 재검사 통과. 이동 중 조건 해제/건너편 도착 후 조건 해제 귀환, 귀환 중 조건 복구 유지, 양방향 이동/출발 지연/Freeze 중 원격 목적지 전환, 조건 우회·구간 속도·경유지 인덱스·준비 전 신호·무효 대상 확인. 관련 BP 6개 컴파일 오류·경고 0. 열린 Blue 액터 2,365개 배치·선택·기존 신호/설정·dirty map 상태 보존, 기존 에셋 해시 변경은 BP_PlatformController 한 개뿐이다.

### BP_RespawnPointSetter — 다음 리스폰 위치 지정 (2026-11-05)

- 부모 BP_Activate. 상속 DefaultSceneRoot + ArrowComponent `RespawnPointPreview`(HiddenInGame), 별도 Tick/콜리전·직접 이동/리스폰 호출 없음.
- Respawn Point: `RespawnTargets` [I] Actor 배열(빈 배열), `DestinationActor` [I] Actor(기본 None). Respawn Internal: `LastAppliedLocation` Vector, `AppliedTargetCount` Int. 기본 ChannelRequired={0:1}; IsStartOn은 부모 false 유지, 신호 수 합산·임계값 전이 사용.
- OnChannelActive → Parent → Channel==0이면 ApplyRespawnDestination. 해제는 부모의 빈 OnChannelDeactive로 끝나 저장 지점을 유지한다. 다시 적용하려면 새 활성 전이가 필요하며 ReOn/RepeatOn 버튼을 사용할 수 있다.
- ApplyRespawnDestination: AppliedTargetCount=0 → DestinationActor IsValid 분기 → 유효하면 그 ActorLocation, 아니면 자신의 ActorLocation을 로컬 ResolvedDestination에 저장 → LastAppliedLocation 갱신 → RespawnTargets ForEach. 무효/None은 건너뛰고 BP_AvilityBlock 캐스트 성공이면 공개 SetRespawnDestination 호출. 실패이면 DoesImplementInterface(BPI_RespawnDestination) → 인터페이스 캐스트 → SetRespawnDestination 호출. Accepted일 때만 AppliedTargetCount 증가. 대상/지점이 움직여도 한 호출 내 모든 대상은 같은 저장 좌표를 받는다.
- 새 BP_AvilityBlock.SetRespawnDestination(Location)→Accepted: Move==Physics 검사 후 RespawnDestinationOverride=Location, HasRespawnDestinationOverride=true, ResetLocation=Location. 지원하지 않는 Move는 false이며 변경 없음. 두 새 내부 변수는 Instance Editable=false, 기본 false/0. BeginPlay의 기존 ResetLocation 대입 값만 SelectVector(override? RespawnDestinationOverride : 기존 메시 월드 위치)로 감싸 초기 신호를 보존한다. ResetRotation·물리·속도·HeldBlock·능력·위치·낙하 상태는 변경하지 않는다.
- 실제 복귀는 기존 BP_Respawn/PressBox/ResetButton 등이 ResetToStart를 호출할 때 수행된다. 부모 ResetToStart/자식 FallingHazardBlock.ResetToStart는 그대로 사용한다. 메타데이터를 바꿀 때 실제 리스폰을 호출하지 않는다. 기존 Fixed·Patrol·ReturnPlatform 경로는 대상이 아니며 새 함수에서 거절한다. 비블록 BP는 새 인터페이스를 구현하고 자체 리스폰 경로가 저장 위치를 사용하도록 해야 한다.
- 설정 예: 새 지점에 BP_RespawnPointSetter 배치 → RespawnTargets=[해당 Physics 블록] → 버튼/압력판 SignalTargets Target=중간 BP/Channel=0, BP_Trigger는 Targets 사용. BP_Respawn.ResetBlock=true 유지. DestinationActor를 지정하면 그 지점의 현재 월드 위치를 사용하며, 비우면 중간 BP 위치. 위치는 메시 피벗 기준이며 회전·스케일을 바꾸지 않는다. 최신 활성화가 마지막 저장 위치를 결정하고 신호 해제는 되돌리지 않는다. SaveGame과 무관한 현재 플레이 상태이다.
- 검증: 신규 PIE 46개(실제 기존 버튼·압력판·플레이어 트리거와 BP_Respawn 접촉 포함), 기존 ReturnPlatform 118개·낙하 신호 62개·물리/밀기/주기 56개 회귀 통과. 저장본 신규 46개 재확인 및 관련 9개 BP 컴파일 오류·경고 0. 비블록 인터페이스 경로는 컴파일 검증이며 사용자 정의 수신 BP의 자체 리스폰 구현은 별도 필요하다. Tutorial+Red 액터 6,319개 배치·선택, 기존 블록/메시 12개 설정, dirty map/content 상태 보존. 기존 에셋 해시 변경은 BP_AvilityBlock 1개이며 새 에셋은 BP_RespawnPointSetter/BPI_RespawnDestination. 결과 Saved/CodexBackups/RespawnPointSetter-20261104.

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
| `WaitTrigger` [I], `IsDown` [I], `StartOpen` [I], `UseUserStaticMesh` [I] + `UserStaticMesh` [I], `OpenTime` [I](1.5), `HatchWait` [I](2) | 레벨 제작 가이드 7장 |
| `OpenDelay` / `CloseDelay` [I] | Hatch 카테고리, 각각 기본 0초. 열기/닫기 동작 시작 전 지연. 0 이하면 즉시 실행 |
| `CloseAfterFullyOpen` [I] | Hatch 카테고리, 기본 false. 신호형에서 켜면 완전히 열린 경우에만 닫기 요청(기본 StartOpen=false에서는 신호 해제)부터 Max(CloseDelay,0)초 대기. 열림 미완료 상태의 해제는 즉시 닫기 |
| `FullyOpenCloseQueued` / `HatchHasFullyOpened` / `HatchFullyOpenTime` / `FullyOpenCloseTimerHandle` (내부) | 닫기 요청 래치 / 열림 완료 여부·게임 시각 / 별도 단발 타이머 |
| `HatchDelayPending` / `PendingHatchOpen` / `HatchDelayTimerHandle` (내부) | 대기 여부 / 예약 방향 / 인스턴스별 단발 타이머 |
| `MeshClosedTransform ` (내부, **이름 끝에 공백**) | Construction에서 저장 |
| `HatchStartLoc` / `HatchStartRot` / `HingePoint` / `HingeAxis` (내부) | BeginPlay에서 계산 |

- Timeline Update → `Angle = Alpha × Select(IsDown: −90 / 90)` → `SetActorLocationAndRotation(Hinge + RotateAngleAxis(StartLoc − Hinge, Angle, Axis), Compose(StartRot, RotatorFromAxisAndAngle(Axis, Angle)))`.
- `HatchOpen` / `HatchClose`: 기존 Custom Event 이름 유지 → 새 `RequestHatchOpen` / `RequestHatchClose`. 같은 방향을 이미 예약 중이면 무시. 반대 요청이면 타이머 해제·새 방향 저장. 지연 >0이면 Timeline.Stop(현재 자세 유지) → Pending=true → FinishHatchDelay 단발 예약. 지연 ≤0이면 즉시 ExecuteHatchOpen/Close.
- `FinishHatchDelay`: Pending 가드 → 타이머 해제·Pending=false → 예약 방향의 ExecuteHatchOpen/Close. 새 Execute Custom Event는 기존 SetPlayRate(1/OpenTime) → Timeline Play/Reverse에 연결되어 경첩·속도·현재 진행률을 유지한다. 함수/타임라인 삭제 없이 이벤트 실행 경로만 확장했다.
- Finished → WaitTrigger 꺼짐이면 Delay(HatchWait) → 방향 반대로 (반복형 루프).
- `OnChannelActive/Deactive`: 현재 실물 그래프는 Parent → WaitTrigger 켜짐이면 `HatchOpen` / `HatchClose`(Channel 분기 없음; 이번 변경에서 기존 수신 규칙 유지). IsStartOn의 0번은 StartOpen으로 신호 반전. StartOpen 초기 열린 자세는 지연 없이 설정한다.
- 반복형: 기존 HatchWait 뒤 새 방향의 OpenDelay/CloseDelay가 추가된다. 최초 자동 열림에도 OpenDelay 적용. 신호형의 대기 중 반대 입력은 이전 예약을 취소하며, 이동 중 양수 지연 요청은 현재 자세에서 멈춘 뒤 해당 지연 후 이어 움직인다.
- 지연 추가 검증(2026-11-03): 별도 PIE에서 개별 열림/닫힘 시간, 중복 입력, 양방향 예약 취소, 중간 각도 정지·재개, 0/음수, StartOpen 반전, 다중 신호·필요 개수 및 자동 반복 확인. 컴파일 오류·경고 0. 백업/결과 `Saved/CodexBackups/HatchDelay-20261103`.
- 완전 열림 조건부 대기(2026-11-04, 신호 해제 기준으로 정정): `UseFullyOpenClose` = CloseAfterFullyOpen AND WaitTrigger. RequestFullyOpenClose에서 IsHatchFullyOpen=true일 때만 RecordHatchFullyOpen → QueueFullyOpenClose로 닫기 요청 시점부터 전체 CloseDelay를 예약한다. false면 HatchDelayTimerHandle 해제 → HatchDelayPending=false → ExecuteHatchClose로 현재 각도에서 즉시 역방향 이동. OpenDelay 중 해제도 열기 예약을 취소한다. 조기 해제에 강제로 끝까지 열던 동작은 사용하지 않는다.
- Timeline Finished → HandleHatchMotionFinished → 기존 반복 모드 분기. 정방향 완료는 RecordHatchFullyOpen에서 최초 완료 여부·시각을 기록한다. HatchFullyOpenTime은 더 이상 닫힘 지연 계산에 사용하지 않는다. QueueFullyOpenClose는 모드·닫기 요청·완료 여부를 확인하고, K2_IsTimerActiveHandle=true면 중복 예약을 무시한다. 대기 시간 = Max(CloseDelay,0), 양수면 별도 단발 타이머, 0이면 즉시 FinishFullyOpenClose → ExecuteHatchClose. 실제 닫기 시작에서 ResetFullyOpenClose로 플래그·타이머 정리.
- 새 열기 요청은 닫기 래치·타이머를 취소한다. 계속 밟으면 열린 채 유지하며, 얼마나 오래 열린 상태였든 신호가 끊긴 순간부터 전체 CloseDelay를 기다린다. 다시 밟았다 떼면 새 해제 시점부터 전체 지연을 적용한다. StartOpen 초기 자세·신호 반전은 유지하며 반전된 닫기 요청부터 대기한다. 자동 모드와 옵션 꺼짐은 기존 경로 유지.
- 검증: 실제 PressurePlate의 OpenDelay 중 이탈/이동 중 이탈, 완전 열림 뒤 유지 시간, 정지한 중간 각도 회복, 닫기 예약 중 재입력·늦은 해제, StartOpen, 0/음수, 필요 신호 수, 자동 반복 및 기존 지연 회귀 검사 통과. Blue의 발판 BP_PressurePlate_C_3 연결 Hatch 8개(BP_Hatch~3, 5~9)에 CloseAfterFullyOpen=true 적용, 기존 CloseDelay=1초·배치·속도·메시·신호 목록 보존. BP_Hatch4는 기존 설정 유지. 사용자 편집 상태 675개 액터 백업·저장. `Saved/CodexBackups/HatchFullyOpenClose-20261104`.
- 정정 검증: 실제 발판으로 열림 지연 중 해제→예약 취소, 중간 해제→즉시 역방향/완전 열림 미도달, 완전히 연 뒤 해제→완료 시각 기준 대기를 연속 확인. 부분 개방 정지 상태도 즉시 닫히며, 필요 신호 수·재입력·늦은 해제·StartOpen·0/음수·기존 옵션 꺼짐과 자동 반복도 통과. 현재 사용자 편집 상태 667개 액터 및 Hatch 9개 설정·선택·발판 연결 보존. `Saved/CodexBackups/HatchEarlyReleaseClose-20261104`.
- 신호 해제 기준 변경 검증(2026-11-04): 실제 발판을 완전 열림 뒤 CloseDelay보다 오래 밟아도 해제부터 전체 지연을 기다림. 직접 신호·마지막 송신자 해제·중복 닫기 요청의 예약 유지·재입력 취소 후 새 해제·StartOpen·0/음수·조기 해제·기존 옵션 꺼짐·자동 반복 확인. 컴파일 오류·경고 0. 현재 Blue 사용자 편집 상태 802개 액터를 백업·저장하고 Hatch 9개 설정·배치·선택·발판 연결 보존. 닫힘 대기의 현재 기준은 신호 해제이며, 위 과거 검증의 완료 시각 기준을 대체한다. `Saved/CodexBackups/HatchSignalOffDelay-20261104`.

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

### BP_BlinkLight (신호로 반복 점멸 / 한 번 점등, BP_Light 자식 — 2026-11-03)

2026-11-05 레벨 안개 표시: Tutorial+Red·Green·Blue의 기존 BP_Light/BP_BlinkLight 인스턴스 9개는 SpotLight의 Volumetric Scattering Intensity=40. 밝기20·색·켜짐 상태·그림자·빛 판정과 BP 기본값/그래프는 유지했다. 각 맵의 `Lighting/Atmosphere/Fog_Spectrum_LightPaths`는 Density .006, Extinction .5, Scattering Distribution .05, View Distance8000cm인 볼류메트릭 안개다. 환경 전등과 Blue의 DirectionalLight는 산란0. 일반 Fog Max Opacity는 볼류메트릭 안개의 불투명도를 제한하지 않는다. 새 광원을 배치하면 기존 기본 산란2가 적용되므로 필요할 때 인스턴스 컴포넌트에서 조절한다. 백업·검증 `Saved/CodexBackups/LightPathFog-20261105`, `Saved/FogPass20261105`.

- Linear 이동 적용(2026-11-03): 부모 BP_Light의 MoveTimeline은 곡선 보간이라 MoveSpeed=200이어도 중간 최대 약 300cm/s. 자식의 기존 EventGraph BeginPlay → Parent: BeginPlay 뒤에 SetFloatCurve(MoveTimeline, CF_BlinkLight_MoveLinear, Alpha)를 연결했다. 새 CurveFloat `Content/BluePrint/CF_BlinkLight_MoveLinear.uasset`는 (0,0)→(1,1)의 Linear 키 두 개. 부모의 이동 범위·PlayRate 초기화·빛 스캔을 실행한 뒤 자식 인스턴스의 이동 트랙만 교체한다. 부모 BP_Light 및 BP_AvilityBlock 파일은 그대로. 기존 4번 이동·역방향과 7번 점멸·시작 지연을 유지하며 새 인스턴스 설정은 필요 없다.
- Linear 검증: 450cm / 200cm/s에서 광원 2.250초, 기둥 2.267초. 매 프레임 광원 진행률=타임라인 시각, 이동 중 차이 최대 3.33cm(기둥의 첫 MovePoint[0] 처리 1프레임 차이). 종전 곡선에 의한 약 47cm 앞섬 제거. 이동 5개와 기존 점멸/시작 지연 회귀 125개, 총 130개 검사 통과. 컴파일 오류·경고 0. BlinkStartDelay는 점등에만 적용된다.
- 작업 복구: 열린 에디터에서 미완성 BeginPlay 함수 그래프를 제거한 뒤 컴파일 중 비정상 종료되어, 이후 수정·검증은 별도 편집기로 진행했다. Blue_Auto4 자동 저장본의 액터 607개와 기록해 둔 광원·기둥 3개의 배치/설정을 확인한 뒤 엔진과 동일한 복사 방식으로 Blue.umap 복구. 원래 디스크 맵과 자동 저장본 모두 `Saved/CodexBackups/BlinkLightLinearMovement-20261103`에 보존. 사용자 편집기를 다시 열고 선택 액터 복원. 이 작업에서 GitHub PR 수정·추가 업로드 없음.
- 시작 지연 검증(2026-11-03): 실제 PIE 125개 검사 통과. 트리거 수신 후 0.8초 대기, 이후 0.3초 켜짐/0.2초 꺼짐 유지, 지연 중 취소·재시작·중복 입력·0/음수·기존 반복 동작 확인. Green 맵의 기존 광원 3개 위치·설정과 기존 파일 해시 보존. 결과 `Saved/CodexBackups/BlinkLightStartDelay-20261103/verification.json`.
`Content/BluePrint/BP_BlinkLight.uasset`. BP_Light를 부모로 하는 자식이며 메시·색·회전·이동·빛 판정과 BeginPlay를 상속한다. 기존 광원과 레벨은 자동 교체하지 않는다.

| 변수 | 설명 |
|---|---|
| `BlinkOnTime` [I] | Blink Timer 카테고리, 켜짐 유지 시간(초), 기본 3 |
| `BlinkOffTime` [I] | Blink Timer 카테고리, 꺼짐 유지 시간(초), 기본 2 |
| `RepeatBlink` [I] | Blink Timer 카테고리, 기본 true. false면 시작 지연 뒤 한 번 켜고 BlinkOnTime 만료 시 자동 소등·대기. BlinkOffTime 사용 안 함 |
| `BlinkStartDelay` [I] | Blink Timer 카테고리, 7번 수신 후 최초 켜짐까지 지연(초), 기본 0. 0 이하면 즉시 시작 |
| `BlinkRunning` / `BlinkPhaseOn` | 내부 실행 상태 / 현재 켜짐 단계 |
| `BlinkTimerHandle` | 내부 단발 타이머 핸들. 부모 LightScan 타이머와 별개 |

- 기본 `StartLightOn=false`, ChannelRequired에 `7→1` 추가. 실제 부모 그래프는 0~4번에만 동작이 연결되어 있고 5·6번은 미연결. 새 기능은 7번 사용.
- `OnChannelActive(7)` → `StartBlink`: 실행/지연 중이면 무시. 아니면 BlinkRunning=true → BlinkPhaseOn=false → ApplyBlinkPower(false). BlinkStartDelay>0이면 동일 BlinkTimerHandle로 BeginBlinkCycle 단발 예약, 아니면 즉시 호출. 시작 지연은 첫 켜짐에 한 번만 적용하며 반복 단계에는 추가하지 않는다.
- `BeginBlinkCycle`: BlinkRunning일 때만 BlinkPhaseOn=true → ApplyBlinkPower(true) → QueueBlinkPhase. 취소 후 이전 시작 콜백을 호출해도 재점등하지 않는다.
- `QueueBlinkPhase`: 현재 단계의 BlinkOnTime/BlinkOffTime을 Select → Max(시간, 0.01초) → SetTimerByFunctionName(AdvanceBlinkPhase, Looping=false) → BlinkTimerHandle 저장. 단계 시작마다 시간을 읽으므로 실행 중 변경은 다음 해당 단계부터 적용.
- `AdvanceBlinkPhase`: RepeatBlink=true이면 기존 실행 가드 → BlinkPhaseOn 반전 → ApplyBlinkPower → QueueBlinkPhase. false이면 StopBlink로 타이머·단계·빛 기여를 정리하고 대기한다. 새 신호마다 타이머를 추가하거나 매 프레임 시간을 계산하지 않는다.
- `ApplyBlinkPower(PowerOn)`: 부모 TurnOn과 SpotLight Visibility를 함께 갱신. false면 부모 ClearLitActor 즉시 호출해 블록·거울에 남은 빛 기여도 제거.
- `OnChannelDeactive(7)`: RepeatBlink=true일 때만 StopBlink로 지연·반복 취소. 단발 모드(false)는 신호 해제를 무시하여 ReOn처럼 즉시 해제되는 펄스도 전체 지연과 켜짐 시간을 유지한다. ReceiveEndPlay는 모드에 관계없이 StopBlink. StopBlink = BlinkRunning=false → ClearAndInvalidateTimerHandle → BlinkPhaseOn=false → ApplyBlinkPower(false).
- 7번 외 OnChannelActive/Deactive는 부모 호출. 부모 IsStartOn을 상속하여 7번은 StartLightOn의 반전을 받지 않음. ChannelRequired의 합산·임계값 유지.
- 연결: BP_Trigger의 **Targets** 배열에 이 자식과 Channel=7, NextLevel 비움. 트리거는 Activate만 보내므로 통과 후 계속 점멸. 버튼 JustOn/Togle/Timed·발판도 가능. ReOn은 즉시 Deactivate해서 점멸을 바로 중지하므로 지속 점멸용으로 쓰지 않는다. 점멸 전원은 7번으로 제어하고, 실행 중 0번 전원 신호와 혼용하면 다음 단계에서 타이머가 전원을 다시 설정한다.
- 단발 모드 사용(2026-11-04): RepeatBlink=false, BlinkOnTime=켜짐 시간, BlinkStartDelay=필요한 시작 지연. BP_Button 또는 BP_BlockSignalTrigger의 ReOn과 Channel=7을 연결하면 매 입력에 한 번 점등한다. RepeatOn도 가능. 실행/지연 중 새 입력은 기존 StartBlink 가드로 무시하며 완료 시각을 미루지 않는다. 완료 뒤 새로운 7번 활성화에서 전체 지연부터 다시 시작한다. 타이머 완료는 ChannelCount를 임의로 초기화하지 않는다. 계속 유지된 신호는 한 번 꺼졌다 다시 켜져야 재작동한다. BP_Trigger는 기본 한 번 작동하는 장치이므로 반복 재점등에는 재입력 가능한 버튼/신호 구역을 사용한다.
- 단발 검증: 실제 PIE 34개 검사(ReOn 재점등, 정확한 ON 시간·자동 정지·신호 유지 시 재점등 없음·중복 무시·지연·0/음수·필요 신호 수·빛 기여 정리·EndPlay) 및 기존 반복/시작 지연 PIE 125개 통과. 기존 Linear 이동 그래프·부모 BP 보존. 백업/결과 Saved/CodexBackups/BlinkLightSingleShot-20261104.
- 검증 결과: 임시 PIE 77개 검사 통과. 실제 플레이어 진입·시간·독립 인스턴스·정지/재시작·부모 상속·빛 기여 해제 확인. 빌드 컴파일 오류·경고 0. 결과 `Saved/CodexBackups/BlinkLight-20261103/verification.json`. 기존 Content/Config 파일 해시 일치, 새 광원만 추가.

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
| `AvilityConfig` | Switch(Color) → 색별 ChargeTime·HoldTime·TargetColor 반환. 2026-11-02 사용자: 충전·유지 시간을 인스턴스 변수로 — Red `RChargeTime` / Blue `BChargeTime` / Green `GChargeTime`·`GreenHoldTime` / Purple `PChargeTime`·`PHoldTime` / Yello `YChargeTime`·`YHoldTime` / SkyBlue `SKChargeTime`·`SKHoldTime` (Red·Blue 유지 0 고정, All·None 1.5/0 상수). 쿨타임은 고정 |
| `AvilityTick` / `AvilityStart` / `AvilityEnd` | 능력 진행(상태 흐름·발광 식은 CLAUDE.md 2-3, 2026-10-31 그래프 확인). Sequence then_0 = Switch(AvilityState) 충전/유지/쿨타임, then_1 = BlockColor·GlowAmount 갱신. Tick에서 `WaitTrigger && TriggerPaused`면 Patrol 스킵 |
| `GetLightSource` (Pure) | 출력 actor / IsPlayer / Found. 플레이어 기여 우선, 아니면 Keys[0] |
| 빨강 `Push`, 폭발 | Push: Select(Found ? actor : 플레이어) 기준. 폭발 `Explosion`(2026-11-07 작업 39 면 방향, 테스트 전): Sphere Overlap Components(메시 위치, 반지름 VSize(ActorBounds Extent)+`OuterRadius`, PhysicsBody·WorldDynamic, Self 제외) → ForEach → IsSimulatingPhysics → `SurfaceDistance`(표면 거리) → 세기 MapRangeClamped(거리, `InnerRadius`→1, `OuterRadius`→0) × `ExplosionForce`, 방향 **`FaceDirection`(대상 위치)** → Z = Max(\|Z\|, `MinLift`) → Normal → AddImpulse(VelChange) / Completed: 플레이어 SurfaceDistance ≤ OuterRadius → 같은 방향식 × `Exp_PlayerForce` → LaunchCharacter(XY·Z Override) |
| `FaceDirection` (Pure, 2026-11-07) | 입력 TargetLocation → 출력 Direction. R = (InverseTransformLocation(StaticMesh Get World Transform, 대상) − 로컬 bounds 중심) ÷ 로컬 반 크기((Max−Min)/2). ① 면: InFootprint = |Rx|≤1 AND |Ry|≤1이면 Up×Sign(Rz), 아니면 |Rx|≥|Ry| ? Forward×Sign(Rx) : Right×Sign(Ry) (면에 직각). ② 모서리: IsCorner = 세 축 중 둘 이상 |R|>1 ((X·Y) OR (X·Z) OR (Y·Z)) → Make Vector(Rx−Clamp(Rx,−1,1), Ry−Clamp, Rz−Clamp) × 반 크기 → Transform Direction(같은 Get World Transform) → Normalize = 블록 위 가장 가까운 모서리 점 → 대상 방향. 최종 Select(IsCorner ? ② : ①). 회전·크기 반영. 동작 확인(2026-11-07). Explosion의 플레이어용 FaceDirection 입력은 발 위치 = GetActorLocation − Make Vector(0,0,Get Capsule Component.Get Scaled Capsule Half Height) (SurfaceDistance는 몸 중심 그대로) |
| 파랑 `BlockPull`, `PlayerPull` | BlockPull(2026-11-06 작업 37, 테스트 전): 빛 주체 = Select(Found ? GetLightSource.actor : PlayerCharacter), 목표 = 주체 위치 + Forward × `Front` → 방향 Normal(GetDirectionUnitVector(메시→목표) + `UpForce`) (높이 포함) → 세기 Clamp(Distance(3D) × Select(IsPlayer ? `PLPullGain` : `MLPullGain`), 500, Select(IsPlayer ? `PLMaxPullSpeed`[I] : `MLMaxPullSpeed`[I])) → AddImpulse(Vel Change) 한 번. PL = 플레이어 손전등, ML = 맵 광원·거울. PlayerPull은 플레이어가 비출 때만(`ActiveContributions.Contains(GetPlayerCharacter)`) |
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

### BP_FallingHazardBlock (낙하 주기·플레이어 밀기, BP_AvilityBlock 자식 — 2026-11-03)
- 매 낙하 신호 대기 추가(2026-11-04): **Fall Cycle → RequireSignalEachFall** [I], bool 기본 false. true이면 처음부터 0번 신호 대기 → 신호 후 StartDelay만큼 기다려 한 번 낙하 → 기존 BP_Respawn(ResetBlock=true) 접촉으로 원래 위치 복귀 → 시작 허가를 해제하고 다음 0번 신호 대기. false이면 기존 자동 시작/최초 1회 시작 신호/반복/공통 시간표를 유지한다. BP_Respawn·BP_AvilityBlock은 수정하지 않는다.
- 새 `RequestSignalFall`: 아직 허가되지 않았고 초기화 전 또는 WaitingForFall일 때만 FallSequenceStarted=true. 초기화 후 NextReleaseTime=Now+Max(StartDelay,0) → CapturePausedFallDelay → StepSignalFall. 대기 지연 중 중복 입력은 만료 시각을 바꾸지 않고, 공중 입력은 다음 낙하로 예약하지 않는다. 기존 StartFallSequence 맨 앞에 이 모드 분기를 추가하여 0번 및 초기화 전 입력을 보존한다.
- `StepSignalFall`은 MaintainSharedFallState로 대기 물리/가시성·낙하 속도 기록을 유지한 뒤 CycleInitialized/WaitingForFall/FallSequenceStarted/출발 시각을 확인하여 ReleaseFall 호출. ReleaseFall의 새 모드 분기는 허가+대기를 검사하고 기존 공통 시계 전용 가드만 건너뛴다. 기존 3번 정지·신호 허가·IsFrozen 및 실제 물리 출발 처리는 그대로다. QueueNextFall에서 모드 켬이면 FallSequenceStarted=false → HoldForFall. ResetToStart의 부모 리셋/속도 초기화·연속 리셋 방지는 유지한다.
- 새 모드는 RepeatFalls/RepeatInterval/UseSharedSchedule보다 우선하며 공통 시계를 자동 시작·합류시키지 않는다. 신호마다 StartDelay를 적용한다. WaitForStartSignal 값과 무관하게 첫 신호도 필요하며, HideWhileWaiting은 그대로 사용한다. ResumeSignalFall은 3번 해제 시 허가된 대기의 남은 시간만 복원하고, 허가되지 않은 블록은 계속 대기시킨다. Freeze/Unfreeze 역시 새 허가를 만들지 않는다.
- 연결: 블록의 RequireSignalEachFall=true. 반복 입력 장치는 BP_Button ReOn 또는 BP_BlockSignalTrigger ReOn, Target=이 블록 / Channel=0. 리스폰 구역의 ResetBlock=true. 부모 ChannelCount/ChannelRequired 유지. 유지형 신호는 끊겼다가 다시 켜져 임계값을 넘어야 다음 허가가 생기며, 기본 BP_Trigger는 1회 송신이므로 반복 출발에는 반복 송신 장치를 사용한다. 기존 레벨 인스턴스는 새 옵션 기본 false로 보존한다.
- 검증: 새 모드 및 경계 조건 PIE 62개(신호 전 대기·실제 BP_Respawn 왕복·공중 입력 미예약·지연 중 중복·초기화 전 신호·다중 필요 신호·Freeze/3번 정지·독립 인스턴스·기존 공통 시간표), 기존 물리/밀기/반복 낙하 회귀 PIE 56개 통과. 컴파일 오류·경고 0. 열린 Tutorial+Red의 6,319개 액터 Transform과 낙하 블록 1개 기존 설정·선택, 맵 clean 상태를 보존하고 BP_FallingHazardBlock만 저장했다. 첫 병렬 회귀의 프레임 지연으로 주기 허용 오차 검사가 실패했으나 단독 재검사에서 기존 56개 전부 통과했다. 백업·결과 Saved/CodexBackups/FallingHazardEachSignal-20261104.
- 저장본을 새 언리얼 프로세스에서 다시 로딩해 컴파일 오류·경고 0 및 새 모드/경계 조건 실제 PIE 62개 재확인. Content/Config 전체 비교에서 BP_FallingHazardBlock만 변경되었고 맵 파일·부모·리스폰·ReturnPlatform 및 다른 BP는 보존했다.
- 공통 시간표 추가(2026-11-03): 디테일 **Shared Schedule → UseSharedSchedule**(기본 false), **ScheduleController**(BP_FallSchedule 참조). 같은 컨트롤러의 최초 시작 시각을 공유하고 각 블록의 StartDelay / RepeatInterval로 절대 출발 시각을 계산한다. 공통 모드에서도 기존 Fall Cycle의 시간 변수를 그대로 수정. RepeatInterval은 양수 필수이며 0 이하면 대기. StartDelay는 0 이상으로 보정, 양수 주기는 최소 0.01초.
- 새 `BP_FallSchedule`(BP_Activate 자식): 내부 ScheduleStarted=false, ScheduleStartTime=0. StartSchedule은 최초 한 번 Now를 기록하며 0번 Activate로 시작 가능. Deactivate나 반복 입력은 시계를 정지·재시작하지 않는다. 기존 블록 0번도 StartSharedFallSchedule을 통해 같은 시계를 시작한다. 연결된 블록 중 하나가 0번을 받으면 전체가 같은 기준 시각으로 합류. 하나라도 WaitForStartSignal=false면 그 블록 초기화가 전체 시계를 자동 시작하므로 신호 시작 그룹은 전부 true로 둔다.
- StepSharedFallSchedule은 대기/공중/초록 정지/3번 정지 중에도 매 프레임 차례 번호를 소비한다. 이미 지난 차례는 재실행하지 않음. 출발 시각은 ClockStart+Max(StartDelay,0)+회차×Max(RepeatInterval,0.01). 프레임 허용 오차는 Min(0.1초, 주기×0.25). 준비되지 않은 차례나 큰 프레임 지연은 건너뛴다. LastSharedScheduleSlot=-1, SharedReleaseAllowed=false 내부 변수로 중복·직접 ReleaseFall 우회 방지.
- 공통 모드: SetMove의 기존 초기화 뒤 InitializeSharedFallSchedule 실행. StepFallCycle → StepSharedFallSchedule, QueueNextFall → HoldForFall, ResumeFallSpawning → ResumeSharedFallSchedule(시계/남은 시간 수정 없이 정지 해제 후 다음 차례 대기). ReleaseFall은 SharedReleaseAllowed일 때만 기존 물리 출발 처리 실행. 공중 물리·플레이어 밀기용 속도 기록은 MaintainSharedFallState에서 유지. Freeze/Unfreeze·기존 리스폰·0/3번의 의미 유지. RepeatFalls=false는 첫 차례만 시도. UseSharedSchedule=false는 기존 개별 주기·남은 시간 재개를 유지한다.
- Green 맵: `FallSchedule_Green_ThreeGroups` 하나 추가. 기존 12개(첫 묶음 BP_FallingHazardBlock~4 / 둘째 5~8 / 셋째 9~12)를 같은 시계에 연결. StartDelay=0 / 3 / 6초, RepeatInterval=모두 9초, RepeatFalls=true, WaitForStartSignal=true. 실제 Green에서 높은 블록의 정상 복귀까지 약 6.8초가 걸려 초기 제안 5.25초 대신 여유 있는 9초 주기와 균등한 3초 간격으로 확정. 다른 낙하 블록 2개와 기존 트리거 대상·위치·외형·색·밀기 설정 보존. 맵 수정 전 디스크 및 사용자 미저장 작업을 저장한 기준본을 각각 백업하고, 요청한 설정 적용 후 Green 저장.
- 검증: 임시 12개 블록 및 기존 낙하·신호·정지 회귀 172개, 실제 Green 정지/재개 47개와 정상 반복 43개, 총 262개 검사 통과. 최종 9초 주기에서 12개 전부 4회씩 원래 차례에 출발했고, 정지 해제한 블록도 18초/21초 원래 차례에 합류. 공통 모드의 초록빛/3번 정지 회차 건너뛰기·고정 출발 시각·독립 시계·직접 호출 방어·실제 높이/리스폰 검증. 준비 지연으로 실제 레벨에서 더 많은 회차를 건너뛰어도 출발은 원래 시간표에만 일치. 공중에서 초록빛이 풀린 물체의 낙하 재개는 그대로이며 새 출발과는 별개. 컴파일 오류·경고 0. 변경은 이 BP·새 BP_FallSchedule·Green.umap 및 문서. 결과/백업 `Saved/CodexBackups/FallingHazardSharedSchedule-20261103`.
- 개별 모드 정지 신호(2026-11-03): **3번 Activate = 다음 낙하 정지, Deactivate = 남은 대기 시간부터 재개**. 공통 모드는 위 시간표 정책을 따름. 낙하 중인 물체의 위치·속도·물리는 건드리지 않고 기존 BP_Respawn으로 돌아온 뒤 HoldForFall 상태에서 대기한다. HideWhileWaiting 설정을 그대로 사용. 0번 시작 신호는 기존 동작 유지. 영구 정지는 기존 BP_Trigger의 Targets에 이 블록/Channel=3, NextLevel 비움. Togle 버튼·발판은 유지되는 동안 정지, 해제 시 재개. ReOn은 바로 재개되므로 지속 정지용 아님.
- 새 내부 FallSignalPaused(bool=false), PausedFallRemaining(real=0). PauseFallSpawning은 최초 정지에 Max(NextReleaseTime−Now,0)를 저장하고 대기 중인 본체만 HoldForFall. 중복 정지/재개 콜백은 무시. ResumeFallSpawning은 해제 후 초기화 완료라면 NextReleaseTime=Now+남은 시간 → StepFallCycle. 공중에서 재개해도 물리를 리셋하지 않는다.
- ReleaseFall 시작 가드로 모든 재출발을 막고, QueueNextFall은 정지 중 주기를 건너뛰거나 시간을 다시 계산하지 않고 HoldForFall만 실행. RepeatFalls=false 또는 RepeatInterval<=0 경로도 정지 적용. InitializeFallCycle·StartFallSequence가 출발 시간을 정하면 CapturePausedFallDelay가 정지 중 남은 시간을 갱신하므로 초기화 전 정지·정지 중 0번 시작도 정상 처리. 초록 Freeze는 독립적으로 유지되어 두 정지 조건이 모두 해제되어야 출발.
- 3번 외 OnChannelActive/Deactive와 IsStartOn은 기존 흐름 유지. ChannelRequired 기본 맵에 3→1 추가, 기존 키·사용자 값 보존. 실제 PIE 117개 검사 통과(기존 시작/낙하/밀기 회귀 포함), 컴파일 오류·경고 0. 배치된 14개 인스턴스 위치·기존 설정 보존(새 기본 채널 3만 추가). 다른 Content/Config·레벨 파일 해시 일치. 백업/결과: `Saved/CodexBackups/FallingHazardPause-20261103`.
- 신호 시작 추가(2026-11-03): Fall Cycle의 WaitForStartSignal [I] 기본 false. true면 0번 Activate를 받을 때까지 무기한 대기. 0번을 한 번 받은 시점부터 StartDelay를 계산해 반복을 시작한다. 0번 Deactivate/재입력은 무시하므로 ReOn 펄스도 가능. 신호가 BeginPlay보다 빨라도 보존. 기본 false는 기존 자동 낙하 유지.
- 새 내부 FallSequenceStarted/CycleInitialized. InitializeFallCycle은 NOT WaitForStartSignal OR 기존 시작 래치, CycleInitialized=true. ReleaseFall에 신호 가드. StartFallSequence는 옵션 켬 AND 아직 시작 전일 때만 래치 → 초기화 후면 NextReleaseTime=Now+Max(StartDelay,0) → StepFallCycle. OnChannelActive 0은 시작, 3은 정지, 나머지 부모 호출. OnChannelDeactive 0은 무시, 3은 재개, 나머지 부모. IsStartOn은 false로 부모 Patrol의 StartMoving 반전이 0번 시작 명령에 영향을 주지 않음. ChannelRequired 임계값은 그대로.
- 플레이어 진입 연결: 기존 BP_Trigger의 Targets 배열(이름 주의)에 Target=이 낙하 블록, Channel=0, NextLevel 비움. 여러 블록을 함께 넣고 각 StartDelay로 순서 조절. 블록 진입용 BP_BlockSignalTrigger는 SignalTargets에 같은 Target/Channel 설정.
- 신호 대기·실제 BP_Trigger 플레이어 진입·신호 기준 지연/반복·중복/꺼짐 무시·초기 신호·요구 개수·기존 낙하/밀기/초록 정지, 별도 PIE 77개 검사 통과. 기존 레벨 4개 인스턴스의 위치·회전·스케일·설정 보존. 결과 Saved/CodexBackups/FallingHazardSignal-20261103.
- BP_AvilityBlock 자식. 기존 BP·플레이어·Levels 파일 수정 없음. Content/BluePrint/BP_FallingHazardBlock.uasset. 자연 중력 낙하 + 출발 지연/반복 위상 + 낙하 충돌 시 옆으로 밀기.
- 부모 BeginPlay 상속. SetMove에서 Move=Physics 강제 → Parent SetMove → InitializeFallCycle. 이후 부모가 BaseSize/ResetLocation/ResetRotation 저장. CanGrab 기본 false. UserStaticMesh·색 반응·초록 충전/유지 시간 상속. 감쇠/최고속도/질량은 바꾸지 않음.
- Fall Cycle [I]: StartDelay(0초), RepeatFalls(true), RepeatInterval(4초), HideWhileWaiting(true). 같은 높이에 배치하고 StartDelay 0/0.5/1/1.5/2/2.5/3/3.5, RepeatInterval=4로 8개 출발. 대기 중 본체 물리/충돌을 끄며 기본적으로 숨김. 빛 수신/잡기 불가. HideWhileWaiting=false면 보이기만 함.
- 반복 복귀는 기존 BP_Respawn(ResetBlock=true)의 ResetToStart 사용. 자식이 Parent ResetToStart로 메시 복귀·속도 초기화 후 다음 절대 시간 슬롯까지 대기. RepeatInterval은 리스폰 후 추가 대기가 아니라 출발 간격. 늦게 돌아오면 지난 슬롯을 건너뛰며 공중/초록 정지 중 강제 복귀하지 않음. 리스폰 영역에 안 닿으면 자동 반복하지 않음. RepeatFalls=false 또는 RepeatInterval<=0은 초기 StartDelay만 사용하고 이후 리스폰 시 즉시 재낙하.
- ReceiveTick: AvilityTick → StepFallCycle. 대기 중 HoldForFall로 능력 해제의 물리 재활성화 방지. Freeze/Unfreeze는 부모 호출, Freeze는 충돌 전 속도 기록도 0, Unfreeze는 대기 중 HoldForFall 재적용. 초록 정지 중 출발하지 않음.
- Player Push [I]: EnablePlayerPush=true, PushSpeed=500cm/s, PushUpSpeed=100cm/s(현재 수직 속도에 추가), MinImpactSpeed=150cm/s, PushCooldown=0.5초, UseCustomPushDirection=false, PushDirection=(1,0,0)(액터 로컬), EscapeClearance=10cm, MaxEscapeDistance=500cm.
- 실제 본체 Hit + Character만 허용. 직전/현재 아래쪽 물리 속도로 문턱 확인. 대기/정지/저속 접촉 제외. 실제 움직이는 StaticMesh Bounds 중심에서 플레이어 쪽 수평 방향, 중심이 같으면 액터 오른쪽/월드 X 대체. Custom은 로컬 방향을 액터 회전으로 월드 변환 후 수평 정규화.
- 블록 밑 끼임을 줄이기 위해 메시 Bounds+캡슐 반경 바깥까지 필요한 거리만 Sweep 이동(MaxEscapeDistance 한도). 이 블록만 임시 MoveIgnore, 기존 상태 복원. 벽·바닥 콜리전 유지. 이어 LaunchCharacter(XY Override=true, Z Override=false), 쿨타임으로 중복 제한. 벽에 막혀 출구가 없거나 이탈 거리가 부족하면 완전 탈출 보장 안 됨. 멀티플레이 미검증.
- 검증: 별도 PIE에서 실제 낙하 Hit·정지 플레이어 수평 탈출·벽 차단·밀기 설정·Freeze/Unfreeze·기존 BP_Respawn 겹침·8개 블록 반복, 56개 검사 통과. 컴파일 오류/경고 0. 결과 Saved/CodexBackups/FallingHazardBlock-20261103. 기존 레벨 자동 교체 없음.

### BP_ReturnPlatform (시작점 귀환 플랫폼, BP_AvilityBlock 자식 — 로컬 추가 2026-11-02)

즉시 정지·유지형 귀환 추가(2026-11-04): 기존 0/3번 명령과 0번 해제 복귀 옵션은 유지한다. 새 **4번 Activate → StopReturnMovement**는 현재 위치에서 `ReturnSignalStopped=true`, `TriggerPaused=true`로 정지한다. Deactivate는 무시하므로 ReOn 펄스가 끝나도 정지 상태를 유지한다. 출발 지연 중이면 기존 예약을 취소한다. 경로·위치·초록 `IsFrozen`은 변경하지 않는다.

- **5번 Activate → HoldReturnToStart**: 진행 중·접촉 정지 중에도 현재 구간을 역으로 따라 MovePoint[0]으로 이동. 이미 귀환 중이면 재개, 0번 도착 후 계속 밟고 있으면 그 자리에서 대기. **5번 Deactivate → ReleaseReturnHold**: 현재 위치에서 마지막 경유지 방향으로 전환. 귀환 중 재진입/이탈도 즉시 전환하며 지나온 모서리를 건너뛰지 않는다. 상단에서 내려갈 때는 기존 StartDelay를 사용한다. 새 0번 출발 입력은 유효한 5번 유지 신호가 있으면 무시한다. 부모의 ChannelCount/ActiveChannels(Set)/ChannelRequired 집계는 그대로 사용한다. 기본 ChannelRequired에 4→1, 5→1 추가(기존 인스턴스의 미지정 채널도 부모 기본 1).
- 새 **Return Platform → StopOnAbilityBlockContact** [I], 기본 false. true이면 전진(Phase=1) 중 `PressBox`가 다른 BP_AvilityBlock 계열의 본체 StaticMesh를 감지할 때 StopReturnMovement 호출. 위로 귀환할 때는 이 접촉 정지를 적용하지 않아 받침에서 빠져나갈 수 있다. PressBox BeginOverlap의 기존 리스폰 분기 앞에 `HandleReturnBlockContact(OtherActor,OtherComp)`를 연결했다. ResetPlayer/ResetBlock은 독립이며 기존 설정을 보존한다.
- `MoveReturnWithBlockStop(NewLocation)`가 기존 StepReturnPlatform의 SetActorLocation 한 곳을 대체한다. PressBox의 현재 위치→이번 이동 끝 위치를 회전·실제 스케일이 반영된 BoxTraceMultiForObjects로 검사한다. WorldDynamic/PhysicsBody만 검사하는 내부 ReturnBlockObjectTypes, Self 제외, BP_AvilityBlock 본체 필터를 적용하고 가장 이른 Hit.Time으로 실제 이동을 제한한다. 따라서 큰 프레임 이동도 블록을 통과하지 않는다. 접촉 후 정지 래치 설정. StepReturnPlatform 진입과 이동 직후 도착 처리에 래치 가드를 두어 정지 신호/Overlap 이후 경유지 전진을 막는다. 기존 속도 계산·부모 AvilityTick·Freeze는 유지한다.
- **상단 0번/하단 1번 설정:** 플랫폼을 상단에 배치, MovePoint[0]=(0,0,0), [1]=(0,0,-하강거리), StartDelay=0, ReturnOnSignalOff=false, StopOnAbilityBlockContact=true, ResetBlock=false. PressBox는 실제 플랫폼 아랫면에 얇고 넓게 맞춘다(액터·컴포넌트 스케일 포함). 최초 BP_Trigger의 Targets=플랫폼/Channel0, NextLevel 비움. BP_PressurePlate의 SignalTargets=플랫폼/Channel5. 여러 유지 신호 중 마지막 신호가 해제되어야 하강한다(Required=1).
- 선택 신호 정지 구성: BP_BlockSignalTrigger ButtonMode=ReOn, OnlyPhysicsBlocks=false, TriggerBlock=플랫폼, SignalTargets=플랫폼/Channel4. 플랫폼 본체가 이 신호 구역에 들어오면 즉시 정지. 실제 아래 블록 접촉은 위 StopOnAbilityBlockContact 옵션을 사용하면 별도 정지 구역 없이 처리한다. 4번은 펄스로 사용하고, 5번은 유지형 압력판에 연결한다.
- 검증: 기존 경로·0/3번·신호 해제·속도 88개 + 신규 30개 직접 검사 통과. 저장본을 새 프로세스로 다시 읽어 118개 재확인, 컴파일 오류·경고 0. 실제 캐릭터 압력판 진입/이탈·중간 재입력·상단 유지·반복 접촉 정지·빠른 1프레임 관통 방지 PIE 10개, 기존 플레이어·블록 접촉 리스폰 회귀 PIE 13개 통과. 테스트용 송신 대상 setter/직접 신호 연결은 다른 BP의 메모리에만 추가하고 저장하지 않았다. 열린 Blue 액터 1,126개·플랫폼 3개·모든 Transform/기존 설정/선택·미저장 맵 상태 보존, Content/Config 해시상 BP_ReturnPlatform만 변경. 백업·결과 Saved/CodexBackups/ReturnPlatformHoldStop-20261104. 맵 설정은 자동 변경하지 않는다.
접촉 리스폰 추가(2026-11-04): 부모는 BP_AvilityBlock 그대로 유지하고, BP_PressBlock과 같은 `PressBox` BoxCollision을 루트 아래에 추가했다. 상대 위치 (0,0,-15), BoxExtent (32,32,32), 상대 스케일 (3.8,3.8,0.2), HiddenInGame, Custom QueryOnly, ObjectType LightSencer, Pawn/WorldDynamic/PhysicsBody Overlap 및 그 외 Ignore. 레벨에서 PressBox의 위치·크기를 조절한다.

- 디테일 **Press**: `ResetPlayer` [I], `ResetBlock` [I], `PlayerRespawnLocation` [I] 로컬 Vector(3D 위젯 표시). 두 옵션은 기존 플랫폼 보호를 위해 기본 false. 플레이어 소환 위치 기본 (0,0,150). ResetBlock은 기존 ResetToStart를 호출하므로 Physics 블록에 적용된다.
- 기존 EventGraph BeginPlay→Parent: BeginPlay 뒤 `InitializePressRespawn` 추가: `RespawnWorldLocation = TransformLocation(GetTransform, PlayerRespawnLocation)` → `PressRespawnReady=true`. 부모 초기화 유지. 월드 소환 위치는 시작 시 한 번 계산하여 이동 중에도 고정한다. 기존 SetMove·ReceiveTick 및 신호/속도 함수는 수정하지 않았다.
- PressBox BeginOverlap → PressRespawnReady → OtherActor!=Self → Cast BP_AvilityBlock. 성공 시 ResetBlock이면 대상 ResetToStart, 실패 시 ResetPlayer AND OtherActor==GetPlayerCharacter(0) → Cast BP_Charactor → RespawnAt(RespawnWorldLocation). 암전·들고 있는 블록 해제·중복 방지·일시정지는 기존 캐릭터 RespawnAt 사용. PressBox는 플랫폼과 이동한다. 정상 탑승 면과 겹치지 않도록 실제 압사 면에만 배치한다.
- 기존 경로·속도·신호 회귀 88개 및 새 초기화/설정 검사 9개, 실제 접촉 PIE 13개 통과. 백업/검증 Saved/CodexBackups/ReturnPlatformRespawn-20261104. 다른 레벨과 BP 파일 유지.

기존 능력 블록은 유지하고 별도 자식 BP에 출발·귀환 상태를 구현했다. 경로는 부모의 MovePoint/WorldPatrolPoints, 기본 속도는 MoveSpeed, 구간별 속도는 선택 설정 MovePointSpeeds를 사용한다. 메시·빛 반응은 부모 설정을 사용한다.

| 채널 / 내부 상태 | 동작 |
|---|---|
| Channel 0 켜짐 | 시작점 대기 중일 때만 StartForward. StartDelay 뒤 진행 방향 +1, 경유지 인덱스 0으로 출발 |
| Channel 3 켜짐 | 전진 중 또는 끝점 대기 중이면 ReturnToStart. 현재 목표의 이전 경유지부터 역순 귀환 |
| Channel 0 꺼짐 | ReturnOnSignalOff=true이면 ReturnToStart. false이면 기존 이동 유지 |
| Channel 3 꺼짐 | 무시. 귀환 유지 |
| Channel 4 켜짐 / 꺼짐 | 현재 위치 즉시 정지·출발 예약 취소 / 정지 유지. 별도 ReturnSignalStopped 래치 사용 |
| Channel 5 켜짐 / 꺼짐 | 현재 위치에서 0번으로 귀환·도착 후 고정 / 현재 위치에서 마지막 경유지 방향으로 이동 |
| Channel 1/2 | 이 전용 BP에서는 사용하지 않음. 기존 BP_AvilityBlock의 동작은 변경 없음 |
| PlatformPhase 0/1/2/3 | 0 = 시작점 대기, 1 = 전진(마지막 경유지에서 대기 포함), 2 = 귀환, 3 = 출발 지연 중 |

- BeginPlay는 Parent: BeginPlay 실행 후 접촉 리스폰 위치를 초기화한다. SetMove 오버라이드: Move=PatrolOnce(NewEnumerator8), WaitTrigger=true, StartMoving=false → **Parent SetMove**(물리·월드 경로 초기화) → FinishReturnPlatform. 자식 기본 경로는 (0,0,0) → (300,0,0), ChannelRequired는 0→1 / 3→1.
- IsStartOn은 항상 false. 채널 신호는 출발/귀환 명령으로 처리하며 부모의 StartMoving 반전 규칙을 적용하지 않는다.
- StartForward: Phase==0 AND 경유지 2개 이상이면 StartDelay>0을 검사. 양수는 Phase=3, TriggerPaused=true → StartDelayTimerHandle에 FinishStartDelay 단발 예약. 0 이하는 기존 Phase=1, PatrollCount=1, PatrolIndex=0, TriggerPaused=false 즉시 출발. 지연/전진/귀환 중 재출발 입력은 무시하여 대기 만료 시각을 연장하지 않는다.
- StartDelay [I]: Return Platform 카테고리, 기본 0초. 매번 시작점에서 정방향 출발하기 전에만 적용하며 경유지 사이·귀환에는 추가 대기 없음. FinishStartDelay는 Phase==3일 때 타이머 해제 → 유효 경로 재검사 → 기존 전진 상태로 전환, 무효 경로면 FinishReturnPlatform. 초록 정지 중에도 게임 시간 기준 지연은 만료되고 실제 이동은 기존 IsFrozen 가드로 대기한다.
  - MovePointSpeeds [I] (2026-11-04): Return Platform 카테고리의 실수 배열, 기본 빈 배열. 단위 cm/s. [1]은 MovePoint[0]↔[1], [2]는 [1]↔[2] 구간 속도. [0]은 액터 초기 위치에서 MovePoint[0]까지의 접근 속도이며 보통 MovePoint[0]=(0,0,0)이므로 이동 거리가 없다. 배열에 해당 값이 없거나 0 이하면 기존 MoveSpeed를 사용한다. 여분 항목은 사용하지 않는다. 기본 빈 배열인 기존 인스턴스는 종전 속도를 유지한다.
  - GetReturnMoveSpeed (pure): ResolvedSpeed=MoveSpeed로 시작. 목표 인덱스를 경로 범위로 Clamp하고 전진은 그 인덱스, 귀환(Phase=2)은 목표 인덱스+1을 다시 Clamp하여 SpeedIndex 계산. 배열 범위 검사 뒤 양수일 때만 ResolvedSpeed 교체. StepReturnPlatform의 기존 MoveSpeed 읽기 2개(양수 가드·보간 속도)만 이 함수 결과로 교체하여 경로·도착 판정·출발 지연·초록 정지 유지. 중도 귀환도 현재 물리 구간의 속도를 사용한다.
- ReturnToStart: Phase==3이면 FinishReturnPlatform으로 출발 예약 취소(위치 유지). Phase==1 AND 유효 경로이면 Phase=2, PatrollCount=-1, PatrolIndex=Clamp(현재 목표 인덱스-1, 0, 마지막), TriggerPaused=false. Phase==2에서 다시 받아도 뒤집히지 않는다. FinishReturnPlatform은 기존 대기 초기화 전에 StartDelayTimerHandle을 해제한다.
- ReturnOnSignalOff [I]: bool 기본 false, 디테일 Return Platform 카테고리. OnChannelDeactive 진입 → Branch(Channel==0) → Branch(ReturnOnSignalOff) → ReturnToStart. 0번 신호 개수가 ChannelRequired 아래로 내려갈 때 기존 BP_Activate에서 호출한다. 신호가 하나라도 유지되면 필요 개수=1인 플랫폼은 복귀하지 않는다. 귀환 중 0번 재활성화는 기존 StartForward의 Phase==0 가드로 무시한다.
- ReceiveTick 오버라이드: 부모 AvilityTick → StepReturnPlatform(DeltaSeconds). 부모의 자동 Patrol 이동 Tick은 호출하지 않아 이중 이동을 피한다.
  - StepReturnPlatform: Phase!=3, Phase>0, 경유지 2개 이상, !TriggerPaused, !IsFrozen, dt>0, GetReturnMoveSpeed.Speed>0을 모두 검사. 인덱스를 유효 범위로 Clamp하고 현재 경유지를 로컬 RouteTarget에 저장 → VInterpTo_Constant(InterpSpeed=GetReturnMoveSpeed.Speed) → SetActorLocation(Sweep=false, Teleport=false) → 도착 거리 ≤0.01이면 AdvanceReturnRoute.
- AdvanceReturnRoute: 전진이면 다음 경유지, 마지막이면 그 자리에서 TriggerPaused=true. 귀환이면 이전 경유지, 0번이면 FinishReturnPlatform(Phase=0, Pause=true, Index=0, Direction=+1). 시작점으로 이동하는 순간이동 노드는 없다.
- 연결 예시: BP_Button RepeatOn / Channel 0 → 새 플랫폼, BP_BlockSignalTrigger ReOn / Channel 3 → 같은 플랫폼. 블록 리스폰은 기존 BP_Respawn으로 처리하며 신호 구역을 더 위에 배치한다.
- 기존 0번 PressurePlate 구성: ReturnOnSignalOff=true, 발판 SignalTargets에 Target=플랫폼 / Channel=0. 밟으면 출발하고 떼면 귀환. 기존 RepeatOn + 3번 별도 복귀 구성은 옵션 false 유지(RepeatOn 재입력은 해제→활성화를 연달아 전송). 위쪽 0번으로 밟는 동안 올라가려면 새 Channel=5 구성을 사용한다.
- 검증: 별도 임시 맵에서 실제 ReceiveBeginPlay/ReceiveTick과 버튼·트리거를 호출하는 34개 검사 통과. 프레임 이동 거리 제한, 중간/끝점 귀환, 꺾인 경로 역주행, 반복 신호 무시, 3회 왕복과 재출발, Freeze/Unfreeze, 빈/단일 경로·속도/시간 0, 변환 경로 확인. 새 프로세스 오류·경고 0. 실제 플레이어 탑승·실시간 PIE는 미실시.
- 백업/검증: Saved/CodexBackups/ReturnPlatform-20261102. 기존 BP 및 Levels 파일은 해시 비교로 보존 확인.
  - 구간 속도 검증(2026-11-04): 기존 직접 회귀 60개와 신규 이동 검사 28개, 출발 지연 PIE 27개와 실제 압력판 구간 속도 PIE 12개 통과. 정방향·중도/끝점 복귀·빈/짧은/0/음수 배열·독립 인스턴스·초록 Freeze·회전/스케일 경로 확인. 실제 플레이 프레임에서 120/300cm/s의 두 구간 및 역순 복귀 속도 측정. 컴파일 오류·경고 0. Blue 파일·802개 액터와 기존 플랫폼 설정, 다른 Content/Config 해시 보존. 백업/결과 Saved/CodexBackups/ReturnPlatformPointSpeeds-20261104.
- 신호 해제 복귀 추가 검증(2026-11-03): 기존 34개 포함 직접 검사 60개, 실제 캐릭터 PressurePlate 진입/이탈 PIE 10개 통과. 컴파일 오류·경고 0. 현재 Blue 편집 상태 백업·저장 후 적용, 기존 플랫폼 배치·설정 보존. `Saved/CodexBackups/ReturnOnSignalOff-20261103`.
- 출발 지연 검증(2026-11-04): 기존 직접 검사 60개 + 실제 PIE 27개 통과. 독립 지연, 반복 왕복마다 재적용, 지연 중 3번/옵션 켠 0번 해제로 취소, 옵션 끈 해제 유지, 중복 입력, 다중 송신자, 0/음수, Freeze/Unfreeze, 실제 PressurePlate 취소·재출발·귀환과 이동 속도 상한 확인. 컴파일 오류·경고 0. 기존 플랫폼 설정과 사용자 Blue 편집 상태 보존. 백업/결과 `Saved/CodexBackups/ReturnPlatformStartDelay-20261103`.

### BP_GreenGroupStop (초록빛 그룹 정지, 2026-11-01)
사용자가 만든 BP_AvilityBlock 복제본을 완성한 로컬 BP. 부모는 BP_Activate이며 BP_AvilityBlock의 자식은 아니다. 기존 빛 반응·Freeze/Unfreeze 로직을 유지한다.

| 추가 변수 | 형식 / 용도 |
|---|---|
| `StopTargets` [I] | BP_AvilityBlock Object Reference **배열**. 정지·재개할 Patrol 블록 목록 |
| `GroupStopSent` | Bool, 기본 false. 같은 상태의 신호 중복 전송 방지 |

- `SetGroupStopped(ShouldStop)` → Branch(ShouldStop != GroupStopSent) → True: Set GroupStopSent → ForEachLoop(StopTargets) → IsValid(ArrayElement) → Branch(ShouldStop) → True: BPI_Activatable.Activate(Target, Channel 0), False: Deactivate(Target, Channel 0). False 분기와 None 대상은 건너뛴다.
- `Freeze`: 진입 → SetGroupStopped(true) → 기존 IsFrozen 검사 및 Freeze 처리.
- `Unfreeze`: 진입 → SetGroupStopped(false) → 기존 IsFrozen 검사 및 해제 처리.
- 수신 대상은 Patrol 모드 + WaitTrigger=true + StartMoving=true + ChannelRequired 0→1. 시작 상태 반전으로 Activate=정지, Deactivate=재개가 된다. Physics 블록용 그룹 정지는 아니다.
- Green 레벨의 `BP_AvilityBlock3`(이 BP 인스턴스): 2026-11-01 재확인 시 ReactOnly / Green / PatrolRotation, 사용자 메시 사용 꺼짐. StopTargets에 `BP_AvilityBlock4`~`7` 연결. 이동 모드·경로와 대상 설정은 이번 감지 수정에서 변경하지 않음.
- 손전등 미반응 원인: 이 복제본의 Construction ReactOnly 본체 메시가 None이고, 보이는 `SM_Floor_Plain_Light`는 NoCollision이어서 Visibility 레이가 통과함. 받침 모양을 유지하도록 **이 BP의 받침 컴포넌트만** Custom / QueryOnly로 변경: Visibility=Block, Camera·WorldStatic·WorldDynamic·Pawn·PhysicsBody·Vehicle·Destructible·Projectile=Ignore, LightSencer=Overlap. 공유 메시 에셋·원본 BP·플레이어 BP는 수정하지 않음.
- 검증: 컴파일·저장 성공. PIE에서 3키로 실제 손전등을 초록으로 바꾸고 받침 아래 조준 → ActiveContributions에 플레이어의 (0,1,0,1), GroupStopSent=true, 대상 4개 TriggerPaused=true 확인. 플레이어 TurnOff 호출 후 네 대상 모두 false 복구 확인. 카메라 위치 조정은 PIE에서만 했으며 플레이 종료함. 기존 SIE 중복 Freeze/Unfreeze 검증도 통과.
- 복제본이므로 이후 원본 BP_AvilityBlock 변경이 자동으로 반영되지 않는다. 원본으로 Cast하는 잡기·리스폰 기능의 호환성을 보장하지 않는다. 받침 메시가 제거되는 Fixed/사용자 메시 구성에서는 별도의 실제 수신 본체와 Visibility 충돌이 필요하다.

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

### BP_SmoothPushPressBlock (부드러운 옆면 밀기, BP_PressBlock 자식 — 2026-11-02)
- 추가 컴포넌트 없음. 부모 BeginPlay·PressBox 리스폰 상속. 기본 Move=PatrolOnce, MovePoint [(0,0,0),(300,0,0)].
- EnableSmoothPush [I] true / PushSkin [I] 0.5cm / StopWhenPlayerBlocked [I] true (Smooth Push 카테고리). PushObjectTypes는 내부 WorldStatic/WorldDynamic/PhysicsBody 배열.
- ReceiveTick: AvilityTick → IsSmoothPatrol → StepSmoothPatrol(DeltaSeconds). 부모 Patrol Tick 중복 호출 없음. 모드 ordinal 2/3/4/5=Return/Rotation/Restart/Once.
- StepSmoothPatrol: 경로>=2, !IsFrozen, !RestartWaiting, !(WaitTrigger && TriggerPaused), dt>0, MoveSpeed>0 → 인덱스 Clamp → RouteTarget 저장 → VInterpTo_Constant → SmoothPushMove(목표, GetPlayerCharacter(0)) → 실제 위치가 목표 1cm 안일 때 AdvanceSmoothRoute.
- AdvanceSmoothRoute: 다음 인덱스 유효하면 진행. 끝에서 Return은 방향 반전, Rotation은 인덱스 0, Restart는 인덱스 0과 시작점 Teleport, Once는 대기. 0/1/2 신호는 원본 상속.
- SmoothPushMove: 이동량 저장 → 켬·유효 플레이어·이동량 있음·MovementBaseActor != Self이면 FindPushContact → 접촉 시 PushCharacterForMove → 허용 이동 비율로 블록 이동. 그 외에는 일반 경로 이동.
- FindPushContact: 플레이어 위치 → 위치−이동량으로 CapsuleTraceMultiForObjects(Radius+Max(PushSkin,0), 실제 HalfHeight), 단순 충돌. 플레이어 자신만 Ignore, bIgnoreSelf=false. HitActor==Self, HitComponent.Pawn==Block, |Normal.Z|<0.7, Dot(Delta,Normal)>0인 가장 이른 Time 반환. PressBox는 Pawn Overlap이라 밀기 후보 제외. 실제 충돌 모양 사용.
- PushCharacterForMove: Delta×(1−Time)만 플레이어 Sweep 이동. 캡슐의 기존 MoveIgnoreActors에서 Self 존재 여부 저장 → 일시 Ignore → 이동 → 원래 상태 복구. 실제 변위/요청 변위 비율을 Clamp하여 블록 허용 비율 반환. StopWhenPlayerBlocked=false면 블록 이동량 제한 없음.
- PressBox 리스폰 우선. 레벨 인스턴스에만 추가한 장식은 새 액터에 자동 이전되지 않음. 게임 월드 충돌 34개 및 실제 플레이 프레임 9개 검사 통과. 기존 레벨·BP·BP_Charactor 변경 없음.

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
**구성요소**: `DefaultSceneRoot`, `Box`(Box Collision, Hidden in Game, Custom: Query Only, Object Type `LightCencer`, WorldDynamic / PhysicsBody / **Pawn** Overlap). 플레이어 캡슐은 LightCencer에 Overlap(기존 설정 그대로). `Area`(Static Mesh, M_RespawnFlow 흐르는 이미지, NoCollision, 회전 0 — 크기는 액터 Scale로만, 2026-11-08). 변수 `VisibleArea`[I] Bool → Construction Script `Area.Set Visibility(VisibleArea)` → `Area.Create Dynamic Material Instance(0)` → `Set Vector Parameter Value(Tiling = (Box.GetScaledBoxExtent X×2 ÷ TileSize, Z×2 ÷ TileSize))` — 변수 `TileSize`[I](200, 이미지 한 장 cm)로 줄 굵기 고정(2026-11-08, 동작 확인).

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
| ~~`IA_TurnOff` (E)~~ | 2026-11-08 삭제 완료(끄기는 같은 숫자 키로) |
| `IA_Jump` (Space, 2026-11-06 점프 쿨타임·예약, 테스트 전) | Started → Branch(`CanJumpAgain`) T → Jump / F → `IsJump`=true(예약) → Set Timer(`clear_Jump`, 0.3초) → IsJump=false. Completed → StopJumping. **Event On Landed** → Delay(`JumpCooldown`) → CanJumpAgain=true → Branch(IsJump) → Jump → IsJump=false. **Event On Jumped**(실제로 뜬 순간) → CanJumpAgain=false (2026-11-06 수정: Jump가 실패해도 잠기지 않게). 쿨타임은 착지부터, 예약은 쿨타임 끝나기 0.3초 안에 누른 입력만 |
| `IA_Relation` (F) | Started → IsValid(`HeldBlock`) → 있으면 `DropBlock` / 없으면 `TryInteract` |
| `TryInteract` (함수) | IsValid(`FocusTarget`) → Cast To BP_AvilityBlock → 성공 `GrabBlock(Block)` / 실패 `Interact`(BPI_Interact 메시지, Target FocusTarget) |
| `FindTarget` (함수, `FocusTarget` 갱신, 2026-11-02 개편·동작 확인) | `Sphere Trace Multi For Objects`(Start = Camera 위치, End = + Camera Forward × `InteractDistance`, Radius 20, Object Types WorldStatic/WorldDynamic/PhysicsBody, Ignore Self) → For Each(Out Hits, 가까운 순) → Break Hit Result → `CanInteract`(HitActor) → Branch T → **벽 확인** `Line Trace For Objects`(Camera 위치 → 후보 Impact Point, Object Types **WorldStatic만**, Ignore Self) → Branch(NOT Return Value OR 선 HitActor == 후보) T → `FocusTarget = 후보` → Return / Completed → `FocusTarget = None`. 예전 SphereTraceSingle(R 40)은 큰 공이 받침·책상에 먼저 닿아 작은 대상을 못 고름. 벽 확인을 Visibility 채널로 했을 때는 맵 벽이 Visibility Ignore라 벽 너머 버튼이 눌림 → 물체 종류 방식으로 변경(WorldDynamic은 체크포인트·트리거 상자가 막아서 제외) |
| `IA_Crouch` (C, 2026-10-30) | Started → Branch(`Is Crouched`) True → `Un Crouch` / False → `Crouch`. CharacterMovement `Can Crouch` 켬, `Crouched Half Height`(기본 40)로 앉은 높이. 카메라는 캡슐에 붙은 SpringArm이라 캡슐이 낮아진 만큼 같이 내려감(`Crouched Eye Height`는 안 쓰임). 앉으면 점프 불가·`Max Walk Speed Crouched`(엔진 기본). 틈 아래 Un Crouch는 엔진이 공간 날 때까지 대기. 키 매핑 `IMC_Default` |
| `GrabBlock` | `GrabComponentAtLocationWithRotation`(StaticMesh) → 메시 Pawn 응답 Ignore → `TurnOff` → HeldBlock 저장 |
| `DropBlock` | 놓기 + Pawn 충돌 복구 |

---

## 7. 갱신 기록
| 날짜 | 변경 |
|---|---|
| 2026-11-07 | BP_Mirror 정면 빔(사용자 구현, 그래프 확인, 테스트 전): 반사 빔(광원별 최대 3개) → 앞면 빛을 합쳐 MirrorPivot 정면(RightVector)으로 빔 1개. MirrorScan = 광원 루프에서 FrontHit만 GlowColorSum(표시색, 흰 손전등→흰색)·BeamColorSum(원래 색 합) 누적 + BeamInt+1 → Branch(BeamInt>0) True: RectLight 하나 배치·색·BoxTrace(정면)·NewLit[대상]=BeamColorSum / False: RectLight 숨김 → UnLight/Light → SetMirrorGlow. RectLight1·2 삭제, BeamLights 배열은 RectLight 하나만. 입사각 60° 제한 유지 |
| 2026-11-07 | 거울 주변 벽 얼룩 = M_LensGlow 발광의 Lumen 간접광 → 사용자 해결(방법 미기록: SM_Mirror Affect Dynamic Indirect Lighting 끄기 또는 발광 세기 낮추기 안내) |
| 2026-11-07 | 도감(작업 36) 시작, 미구현: 구조체 S_DexEntry(Title Text, Body Text, Image Texture2D) + 데이터 테이블 DT_Dex(행 이름 = NoteID). 예정: BP_InfoScreen(BPI_Interact, NoteID) → WBP_NotePopup(일시정지) → S_PlayerProgress.CollectedNotes(Set<Name>) → WBP_Dex + ESC 메뉴 도감 버튼 |
| 2026-11-08 | 도감 36-2 안내(미확인): BP_InfoScreen(Actor + BPI_Interact) — ScreenMesh, NoteID [I] Name, CanInteract true, GetInteractText "설명 보기", Interact → Get Data Table Row(DT_Dex, NoteID) → 임시 Print Title |
| 2026-11-08 | 설계 변경(사용자): 도감 → **연구 일지**. 공용 위젯 WBP_Journal(제목·그림·본문 + 이전/다음/페이지 + 닫기) — 맵 스크린은 그 스크린 항목 1개(페이지 버튼 숨김), 연구 일지(ESC 메뉴)는 CollectedNotes 전체를 페이지로 넘김. CollectedNotes = Set<Name>(본 기록만, 순서 무관). 연구 일지 페이지 순서 = DT_Dex 행 순서(2026-11-08 사용자): Entries = Get Data Table Row Names(DT_Dex) 중 CollectedNotes에 있는 것. 36-3 위젯 배치 안내(미확인): Panel 안 Overlay — 내용 Vertical Box(제목·그림·본문·아래 줄 [페이지 표시]·닫기) 위에 Btn_Prev(왼쪽 끝, 세로 가운데)·Btn_Next(오른쪽 끝, 세로 가운데). 그림·본문은 제목 아래 한 줄(Horizontal Box Size Fill: Text_Body 왼쪽 Fill + Box_Picture 오른쪽, 위쪽 맞춤, 그림 없으면 Box_Picture Collapsed), 닫기 아래 가운데. 글은 그림 아래로 감싸 흐르지 않음 → Text_Body를 Scroll Box(Scroll_Body)로 감쌈. 36-4 ShowPage 그래프 확인(그림 없음 갈래 실행선 연결 안내). 36-5 안내(미확인): BP_InfoScreen Interact → Create Widget(WBP_Journal, Entries=[NoteID], ShowPaging=false) → Add to Viewport → UI Only·마우스·일시정지 / WBP_Journal CloseJournal: ShowPaging false면 일시정지 해제·Game Only·마우스 끔 → Remove from Parent |
| 2026-11-08 | 연구 일지: BP_InfoScreen Interact → Get Data Table Row(DT_Dex, NoteID) → Create Widget(WBP_Journal, Entries=[NoteID], ShowPaging false) → Add to Viewport(10) → UI Only → 마우스 → 일시정지. 사용자 "잘나오는거 같아"(창 표시 확인). 다음: WBP_Journal On Key Down(ESC/F → CloseJournal), 미확인 |
| 2026-11-08 | 연구 일지 36-7 안내(미확인): S_PlayerProgress.CollectedNotes(Set<Name>), BP_GameInstance AddNote(NoteID)·HasNote(Pure), BP_InfoScreen Row Found → Cast GI → AddNote → Create Widget. 저장은 체크포인트 SaveProgress에 포함 |
| 2026-11-08 | BP_InfoScreen 그래프 확인: Interact → Get Data Table Row(/Game/Data/DT_Dex) → Row Found → Cast GI → AddNote(NoteID) → Create Widget(WBP_Journal, Entries=[NoteID], ShowPaging false) → Add to Viewport(10) → UI Only → 마우스 → 일시정지. AddNote 내부 미확인 |
| 2026-11-08 | BP_GameInstance AddNote(NoteID) 그래프 확인: 로컬 NewNotes(Set<Name>) = Break(Progress).CollectedNotes → Set Add(NewNotes, NoteID) → Set Members in S_PlayerProgress(Progress, CollectedNotes). CollectedNotes 핀이 Break 출력에 연결돼 있어 NewNotes로 교체 안내, 미확인 |
| 2026-11-08 | AddNote 수정 확인(사용자 "잘 늘어나", CollectedNotes = NewNotes). 36-8 안내(미확인): GI GetJournalEntries(DT_Dex 행 순서 중 HasNote만), WBP_PauseMenu Btn_Journal → Create WBP_Journal(Entries, ShowPaging true) → Add to Viewport(20) |
| 2026-11-08 | BP_GameInstance GetJournalEntries → Entries(Name 배열) 그래프 확인: Get Data Table Row Names(DT_Dex) → For Each → Branch(HasNote) → 로컬 Result.Add → Completed → Return Result. 정상 |
| 2026-11-08 | 연구 일지 수정 안내(미확인): BP_PlayerController IA_Pause(메뉴 열림) 맨 앞 Get All Widgets Of Class(WBP_Journal) Length>0 → For Each CloseJournal (ESC가 ESC 메뉴 대신 연구 일지를 닫게) / WBP_Journal ShowPage ◀▶ Visibility = ShowPaging AND Length(Entries) > 1 |
| 2026-11-08 | WBP_Journal ShowPage 확인: Length>0 False 분기 = Text_Title "아직 기록된 내용이 없습니다" → Text_Body 빈칸 → Btn_Prev/Next Collapsed → (Btn_Close Collapsed — Box_Picture로 교체 안내). 그림 없음 실행선 정상. ◀▶ Select Index = ShowPaging만(AND Length>1 미적용) |
| 2026-11-08 | 연구 일지 완료(사용자 "잘되"): ShowPage ◀▶ Visibility = ShowPaging AND Length(Entries)>1, 0개 분기 Box_Picture Collapsed, IA_Pause가 WBP_Journal부터 CloseJournal. 구성: BP_InfoScreen(NoteID) · DT_Dex/S_DexEntry · WBP_Journal(Entries, PageIndex, ShowPaging, ShowPage, CloseJournal, On Key Down) · GI AddNote/HasNote/GetJournalEntries · S_PlayerProgress.CollectedNotes · WBP_PauseMenu Btn_Journal |
| 2026-11-08 | BP_Mirror 정면 집광: 거울 빔으로 블록 능력 발동 사용자 확인 |
| 2026-11-08 | 사용자 동작 확인: 작업 17 렌즈·거울 유리 발광, 시작 화면(WBP_MainMenu 새 게임·이어하기·종료, ESC 타이틀로·게임 종료). 설정 창은 나중에 확인 |
| 2026-11-08 | 작업 7 필터 교체 모션 설계(사용자): 색 바꾸면 끄기 → 필터 옆으로 빼기 → 메시 교체 → 끼우기 → 켜기, 흰색은 빼고 숨김, 흰색→색은 뺀 위치에서 나타나 끼우기. 7-1 안내(BP_Charactor FilterMesh 컴포넌트·변수·Timeline FilterMove), 미확인. 작업 36 추가 기능은 안 함 |
| 2026-11-08 | 작업 7 BP_Charactor 그래프 확인(테스트 전): 변수 FilterTime·FilterOutOffset·FilterInLoc·InstalledColor·PendingColor·PendingMesh·FilterSwapping·Red/Green/BlueFilterMesh, 컴포넌트 FilterMesh(SM_Flashlight 자식), Timeline FilterMove(Alpha). ChangeFilter(Color, Mesh): Branch(FilterSwapping) F → Branch(Color==InstalledColor) T LightControll(Color) / F Swapping·Pending → TurnOff → Branch(InstalledColor==(0,0,0,1)) T 메시 교체·빠진 자리·보이기·SetNewTime 1·Reverse / F Play. Update: SetRelativeLocation(VLerp(FilterInLoc, +FilterOutOffset, Alpha)). Finished Switch(Direction) Forward: IsValid(PendingMesh) T 교체 → Reverse / F 숨김 → 마무리, Backward → 마무리 = InstalledColor=PendingColor → Swapping false → LightControll(PendingColor) |
| 2026-11-08 | 작업 7 BeginPlay·숫자 키 확인: Sequence then_2 → Set FilterInLoc = FilterMesh.RelativeLocation(정상), FilterMove Set Play Rate(2 ÷ FilterTime) 없음 → 추가 안내. IA_Red/Green/Blue/White Started → Branch(CanUseColor/CanUseFlashlight) True → 아직 LightControll → ChangeFilter(색, 색별 필터 메시 / 흰색 None)로 교체 안내. 미확인 |
| 2026-11-08 | 작업 7: 흰색을 거친 뒤에만 필터가 보이는 문제 → InstalledColor 기본값을 (0,0,0,1)로(LinearColor ==는 알파까지 비교). 선택: Finished Forward True의 Set Static Mesh 뒤 Set Visibility(true). 미확인 |
| 2026-11-08 | 작업 7 그래프 재확인: SetPlayRate(2 ÷ FilterTime)·숫자 키 4개 ChangeFilter 교체 정상. 남은 것: InstalledColor 기본값 A=1, Forward True Set Visibility(true) |
| 2026-11-08 | 작업 7 필터 교체 모션 동작 확인(사용자 "잘되") — 완료 |
| 2026-11-08 | E 키(IA_TurnOff) 삭제 안내: BP_Charactor 이벤트·TurnOff 호출 삭제, IMC_Default 매핑 삭제, IA_TurnOff 애셋 삭제(Reference Viewer 확인). TurnOff 함수는 유지. 2026-11-08 사용자 삭제 완료 |
| 2026-11-08 | 거울 입사각 조정 사용자 완료(값 미기록). 작업 40 BP_Respawn 흐르는 이미지 R-1(텍스처·M_RespawnFlow) 안내, 미확인 |
| 2026-11-08 | 작업 40 M_RespawnFlow 2겹으로 변경 안내: 같은 텍스처 2번 샘플, 1겹 +SpeedU / 2겹 −SpeedU(UV×Layer2Scale+0.37), Add 합성. 미확인 |
| 2026-11-08 | 작업 40 M_RespawnFlow(`/Game/Effect/Respawn`) 그래프 확인: 기본 좌표·1겹/2겹 Panner·Add·GlowColor·Intensity → Emissive 연결 정상. 2026-11-08 사용자 동작 확인 |
| 2026-11-08 | 작업 40 R-2 안내: BP_Respawn FlowPlane + Construction Script 가장 넓은 면 자동 배치(얇은 축 = 법선, FaceAxis 0 Z/1 Y/2 X), TileSize·FlowSpeed. 미확인 |
| 2026-11-08 | 작업 40 자동 맞춤 취소(사용자): BP_Respawn에 FlowPlane(Plane, M_RespawnFlow, NoCollision)만 추가, 배치는 수동. 미확인 |
| 2026-11-08 | BP_Respawn 판 컴포넌트 이름 `Area`, 변수 `VisibleArea`(bool) + Construction Script Branch(미완성) 확인 → Set Visibility(VisibleArea) 하나로 안내. 세운 Plane 대신 얇은 Cube 안내. 미확인 |
| 2026-11-08 | 설정 창 마무리 동작 확인: WBP_Settings Event Destruct → SaveSettings, Apply Settings 명령줄 덮어쓰기 끔, 창 모드 변경 시 Set Screen Resolution(전체·테두리 없음 = 데스크톱 해상도, 창 = 1280×720), "전체 화면"도 WindowedFullscreen(독점 전체 화면 잘림 회피). M-7-4-3 해상도 안내 |
| 2026-11-08 | 설정 창 해상도(Combo_Resolution, Resolutions IntPoint 배열, 창 모드일 때만 사용)·소리 크기(Slider_Volume 0~1, GI/BP_SettingsSave MasterVolume, GI ApplyVolume = Set Sound Mix Class Override(SM_Volume, SC_Master) → Push Sound Mix Modifier) 추가. 사용자 동작 확인(소리 실청취는 BGM 때) |
| 2026-11-08 | 작업 40 완료(사용자 "잘되"): BP_Respawn `Area`(흐르는 이미지 판, M_RespawnFlow) + `VisibleArea`[I] → Construction Script Area.Set Visibility |
| 2026-11-08 | BP_Respawn 줄 굵기 자동: TileSize[I] + Create Dynamic Material Instance → Set Vector Parameter Value(Tiling). 그래프 확인 — Parameter Name 비어 있음(Tiling 입력 안내) → 사용자 "잘되" 동작 확인 |
| 2026-11-08 | M_RespawnFlow 2겹 위아래 반전 안내: 2겹 UV × Append(1, Layer2FlipV[−1]) 를 ×Layer2Scale 앞에 → 사용자 "더 이상하다", 반전 안 함(원래대로) |
| 2026-11-09 | BP_Charactor: 블록 들기 시 필터 메시가 사라지지 않던 문제 사용자 수정(방법 미기록) |
| 2026-11-09 | M_Laser(GlowColor·GlowStrength) 발광 강화 안내: GlowStrength 30 안팎, Unlit. 미확인 |
| 2026-11-09 | BP_Charactor 필터 교체 자가 복구 완료(사용자 "잘되"): FinishFilterSwap/ForceFinishFilter 이벤트, Finished Forward 숨김·Backward·강제 마무리 양 끝에서 FinishFilterSwap, ChangeFilter 교체 중 + NOT FilterMove.IsPlaying이면 ForceFinishFilter, IA_Relation Is Not Valid → Branch(FilterSwapping) T ForceFinishFilter → TryInteract |
| 2026-11-09 | 작업 42-3 안내: BP_PlayerController VoiceQueue·VoicePlaying·CurrentLine·LineTime + QueueVoice(Lines)/PlayNextVoice 대기열. 미확인 |
| 2026-11-09 | 작업 42-3 그래프 확인: QueueVoice·PlayNextVoice 연결 정상(음성 있음/자막만 분기, Delay 뒤 재호출, 없는 행 건너뛰기). 테스트 호출만 남음, 동작 미확인 |
| 2026-11-09 | 작업 42-4 안내: BP_VoiceTrigger(Box, Lines[I], Played) 플레이어 진입 한 번 → BP_PlayerController.QueueVoice(Lines). 미확인 |
| 2026-11-09 | 작업 42-4 그래프 확인: 연결 정상, 에셋 이름 NewBlueprint → BP_VoiceTrigger 변경 필요. 동작 미확인 |
| 2026-11-09 | 리스폰 암전 늘리기 안내(사용자: 변수 추가 없이 시간만): BP_Charactor FadeTime 0.5 → 1.0, Delay의 + 0.2 → + 1.0(완전 암전 유지). 선택: Fade 1→0과 Set Game Paused(false) 사이 Delay(FadeTime)(새 변수 없음). 미확인 |
| 2026-11-10 | 사용자 결정: 리스폰 중 세상 멈춤 없앰 → RespawnAt의 Set Game Paused(true/false) 두 개를 Disable Input / Enable Input(Target Self, Player Controller = Get Player Controller 0)으로 교체 안내. 암전 중 블록·플랫폼은 계속 움직이고 플레이어 입력만 막힘. 미확인 |
| 2026-11-10 | 사용자 수정: 잠깐만 멈추고 암전 중엔 입력만 막기 → RespawnAt = Set Game Paused(true) → Disable Input(Self, PC0) → (DropBlock) → Fade 0→1 → Delay 0.3 → Set Game Paused(false) → Delay(FadeTime+1.0) → Teleport → Stop → Fade 1→0 → Enable Input → Respawning false. 새 변수 없음. 미확인 |
| 2026-11-10 | 작업 43-1-1 안내: BP_LaserBolt 컴포넌트 Hit(Box Collision 루트, Custom Query Only·WorldDynamic, Pawn Overlap, WorldStatic/WorldDynamic/PhysicsBody Block, Visibility·Camera·LightCencer Ignore) → Mesh(SM_Laser, NoCollision) + ProjectileMovement(1500, Gravity 0, Rotation Follows Velocity), Initial Life Span 5. 사용자 요청으로 Sphere → Box. 미확인 |
| 2026-11-10 | BP_Turret 생성(파이썬 커맨드릿, 사용자 요청): 부모 BP_Activate. 컴포넌트 DefaultSceneRoot → Base(Cylinder) / Head(Scene, Z80) → HeadMesh(Cube) + Muzzle(Arrow, X45) / AimLine(Cylinder 0.02×0.02, NoCollision, M_Laser, 숨김). 변수 AttackRange 2000 / AimTime 1 / FireInterval 3 / PlayerRespawnLocation (0,0,100) [I] / Aiming / RespawnWorldLocation. 그래프 없음. 컴파일 오류·경고 0 |
| 2026-11-10 | BP_Turret 그래프 자동 생성(BlueprintGraphEditor): BeginPlay(RespawnWorldLocation 고정 → TurretOn=StartOn → K2_SetTimer TryAim 반복) / TryAim(범위·켜짐·조준 중 아님 → 예고 선 → Delay AimTime → BP_LaserBolt 생성 → 선 숨김) / Tick(조준 중 머리·예고 선 갱신) / OnChannelActive·Deactive(0번 → TurretOn) / IsStartOn(0 AND StartOn). 변수 TurretOn·StartOn[I] 추가. 컴파일 오류·경고 0, 플레이 테스트 전 |
| 2026-11-10 | BP_Turret 수정(스크립트): 예고 선 중점 곱셈 B=(0.5,0.5,0.5) 버그 수정. Tick → Branch(TurretOn AND GetDistanceTo(Player) ≤ AttackRange) T: AimLine Visible → 머리 회전 → 선 위치·회전 → 굵기 Select(Aiming ? 0.1 : 0.05) / F: AimLine 숨김. TryAim은 Aiming true → Delay(AimTime) → 발사 → Aiming false만(Visibility 제거). 컴파일 오류·경고 0 |
| 2026-11-10 | BP_Turret 부채꼴 판정(스크립트): 변수 DetectAngle[I] 추가(기본 90 → 사용자 요청 150), 순수 함수 CanTargetPlayer(→Result) = IsValid(PlayerCharacter) 아니면 false, 맞으면 TurretOn AND GetDistanceTo ≤ AttackRange AND Dot(Normal2D(플레이어−터렛), Normal2D(GetActorForwardVector)) ≥ DegCos(DetectAngle/2). Tick Branch 조건 = CanTargetPlayer, TryAim = TurretOn AND NOT Aiming AND CanTargetPlayer. 사용자가 넣은 Tick 앞 Is Valid 매크로 유지. 컴파일 오류·경고 0 |
| 2026-11-10 | 총알 속도 터렛별(스크립트): BP_LaserBolt Speed(Expose on Spawn, 3000) → BeginPlay IgnoreActorWhenMoving 뒤 ProjectileMovement.SetVelocityInLocalSpace((Speed,0,0)), Max Speed 0. BP_Turret BulletSpeed[I] 3000 → SpawnActor BP_LaserBolt.Speed. 컴파일 오류·경고 0 |
| 2026-11-09 | 작업 43 결정(투사체·예고 선·0번 신호 on/off) + 43-1 안내: 새 BP_LaserBolt(Sphere Hit, SM_Laser, ProjectileMovement, RespawnLocation Expose on Spawn, 플레이어 겹침 → RespawnAt → Destroy, 멈춤 → Destroy). 미확인 |
| 2026-11-09 | 작업 42 음성·자막: S_VoiceLine(Sound·Subtitle·Duration)+DT_Voice(Content/Data), WBP_HUD Text_Subtitle + ShowSubtitle/HideSubtitle 안내(42-2). 이후 BP_PlayerController 대기열·BP_VoiceTrigger 예정. 미확인 |
| 2026-11-01 | 로컬 BP_GreenGroupStop: StopTargets 배열 수정, 정지/재개 인터페이스 호출 및 Freeze/Unfreeze 연결. Green 레벨 대상 4개 지정, 컴파일·SIE 신호 검증 |
| 2026-11-01 | BP_GreenGroupStop 받침 NoCollision으로 손전등이 통과하던 문제 수정. QueryOnly + Visibility Block, 물체 채널 Ignore. 실제 플레이어 초록 손전등 수신 → 대상 4개 정지 → TurnOff 후 재개 확인 |
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
| 2026-11-02 | BP_Charactor F 판정 확인: IA_Relation → TryInteract(FocusTarget 사용) → FindTarget의 SphereTraceSingle Radius 40이 원인(큰 공이 주변 물체에 먼저 닿음). Radius 10 안팎으로 줄이도록 안내(변수 `InteractRadius` 권장) — 미적용. 앞서 안내한 InteractBox는 보류(줄여도 안 될 때만) |
| 2026-11-02 | **F 판정 개편 동작 확인**: FindTarget = Sphere Trace Multi For Objects(R 20) → 가까운 순으로 CanInteract → Line Trace For Objects(WorldStatic) 벽 확인 → 첫 후보 FocusTarget. 맵 벽이 Visibility Ignore라 채널 방식 벽 확인이 실패했던 것 해결. **능력 블록 충전·유지 시간 인스턴스 변수화**(AvilityConfig, 사용자 구현) |
| 2026-11-03 | 작업 32 HUD: WBP_HUD(조준점·상호작용 문구·색 슬롯)·WBP_ColorSlot 생성, BP_PlayerController에서 화면에 띄움. 사용자 요청으로 커밋. 그래프는 상호작용 문구 바인딩만 확인(Target 수정 안내), 나머지 미확인·테스트 결과 미확인 |
| 2026-11-03 | 높은 방 환경 조명 분리: BP_Ceiling_Light_High 추가, Tutorial+Red 128개·Green 100개 교체. 통로 20개 및 벽 16개도 광량·반경 조정. 저장 후 배치 속성·퍼즐 액터·PPV 보존 검증, 화면 밖 렌더 확인. 실제 PIE/FPS 미측정 |
| 2026-11-03 | 수직 통로 누락 보완: 회전된 SM_Wall_Light 16개를 BP_Ceiling_Wall_Light_High로 교체. 환경 전등 4종 기본값과 두 맵 264개 인스턴스의 Light Color를 RGB(225,240,245)로 통일. 퍼즐 광원·PPV·원본 메시 속성 보존 검증 및 6개 시점 렌더 확인 |
| 2026-11-03 | 푸시 전 최종 저장값 확인: BP_Ceiling_Light_High의 Outer Cone Angle 60° 유지. 문서와 검증 기준에 반영. 수직 통로 전용 BP는 기존 10° 유지 |


### BP_Floor_Plain_Light / BP_Wall_Light — 환경 조명 패널 (2026-11-03)
- 부모: StaticMeshActor. 기존 StaticMeshComponent가 루트이며 원본 메시·재질·콜리전을 유지한다. Event Graph/Tick 로직 없음.
- BP_Floor_Plain_Light: SM_Floor_Plain_Light + 자식 RectLightComponent `PanelLight`. 로컬 위치 (0.6, 0.1, 12), 회전 Pitch 90° → +Z. 현재 80 lm, 반경 600 cm, Source Width/Height 88 cm. 약 3m 높이의 낮은 통로용.
- BP_Wall_Light: SM_Wall_Light + `FrontLight` / `BackLight`. 위치 X ±12 cm, Yaw 0°/180° → ±X. 현재 각 100 lm, 반경 800 cm, Source Width/Height 260 cm.
- 공통: 현재 Light Color RGB(225,240,245), Movable, Cast Shadows=false, Volumetric/Indirect Lighting Intensity=0, Specular Scale=0.25, Max Draw Distance=0, Max Distance Fade Range=0 (2026-11-03 2차 원거리 표시 제한 해제). 밝기·색·반경은 표준 컴포넌트 Details에서 수정.
- 수광체를 작동시키는 빛 판정 및 신호 인터페이스 없음. 기존 능력 블록·맵 광원·거울 BP는 수정하지 않음.
- 현재 적용: Tutorial+Red 낮은 천장 12, 높은 천장 128, 수직 통로 16. Green 낮은 천장 8, 높은 천장 100. BP_Wall_Light의 기존 16개는 모두 회전된 천장 패널이어서 수직 통로용 BP로 교체했다. 엔진 ConvertActors로 변환해 액터 참조를 치환하고 이름·변환·재질·충돌·폴더·태그·부모 연결을 유지. Blue/LightTestMap/Assets는 수정하지 않음.
- 검증: Tools/Verify-EnvironmentLights.py. 저장 파일 재로딩 후 264개 BP, 조명 264개 및 원본 속성 서명 대조. 성능 수치는 플레이 테스트 전.

### BP_Ceiling_Light_High — 높은 방 전용 천장 전등 (2026-11-03)
- 부모 StaticMeshActor. 원래 SM_Floor_Plain_Light 루트 + SpotLightComponent `DownLight` 하나. 별도 이벤트·Tick·퍼즐 신호·빛 판정 없음.
- DownLight 로컬 위치 (0.6, 0.1, 12), Pitch 90° → 메시 로컬 +Z. 기존 천장 액터 회전을 유지하면 월드 아래(-Z)를 비춘다. 신규 배치 시 발광면이 바닥을 향하도록 회전할 것.
- BP 기본값: 600 lm, Attenuation Radius 2000 cm, Inner Cone 30° / Outer Cone 60°(최종 저장값), Inverse Squared Falloff 켜짐, Source Radius 15 cm, 현재 RGB (225,240,245), Specular Scale .5.
- Movable, Cast Shadows=false, Indirect/Volumetric Intensity=0, Max Draw Distance/Max Distance Fade Range=0. 범위를 늘려 도달 거리를 확보하고 실제 밝기는 Intensity로 조정한다.
- 현재 맵 인스턴스는 가까운 하부 보행 바닥까지 높이 h(cm)를 측정해 수동 보정한 값: `50 단위 반올림(600 × (h/900)²)` lm, 반경 `100 단위 반올림(Max(1000, h×2.2))` cm. 배치값은 150/250/400/600 lm 및 1000/1300/1600/2000 cm. 런타임 자동 계산이나 BP Construction Script는 없다.
- Tutorial+Red 높은 방 A1/A2/A3/B1/B2/B3 128개, Green A1/B1/B2/B3 100개. 같은 방 안의 높은 발판 위 전등도 같은 BP를 쓰되 개별 광량을 낮췄다. B3는 상층 통로·퍼즐 발판 기준이며 약 54m 아래 낙하/재시작 공간에 추가 조명을 두지 않았다.
- 기존 메시·재질·충돌·변환·폴더·태그·부모 및 다른 액터·PPV 설정 불변을 저장 후 검증. 보정 전 백업 C:/lightgame_ai/Backups/BeforeHeightLighting_20261103. 5개 고정 시점 렌더로 밝기를 확인했으며 실제 PIE/FPS는 미측정.

### BP_Ceiling_Wall_Light_High — 수직 통로의 회전된 벽 패널 전등 (2026-11-03)
- 이전 높은 방 분류는 SM_Floor_Plain_Light만 대상으로 했으므로, SM_Wall_Light를 회전해 천장에 단 16개가 누락되었다. Tutorial+Red의 Level_Red/Level_B2/CeilingLight에 배치된 SM_Ceiling218/219/243/246/248~259가 대상. 메시 높이 Z6610 cm, 아래 바닥 Z10 cm로 약 66m의 수직 통로다.
- StaticMeshActor 부모, 원본 SM_Wall_Light 루트 + SpotLightComponent `DownLight` 1개. 로컬 위치 (-12,0,0), Yaw180° → 로컬 -X. 기존 액터의 로컬 +X가 월드 위쪽이어서 -X가 월드 아래를 향한다. 기존 양면 RectLight의 상향 빛은 포함하지 않는다.
- 600 lm, Attenuation Radius 10000 cm, Inner Cone5°/Outer Cone10°. 긴 통로를 따라 아래쪽에 빛을 모으는 좁은 스포트라이트. Inverse Squared Falloff=true, Source Radius15 cm, Specular Scale .5. 그림자·간접광·볼류메트릭 없음, Movable, 표시 거리 제한 0.
- 환경 전등 4종(BP_Floor_Plain_Light/BP_Wall_Light/BP_Ceiling_Light_High/이 BP)의 기본값 및 두 맵 264개 인스턴스의 실제 Light Color를 RGB(225,240,245)로 통일했다. 패널 발광 재질과 퍼즐 광원 RGB·밝기·기존 PPV는 보존. Assets 파일 수정 없음.
- 원본 메시 루트 서명, 다른 액터 및 퍼즐 LightComponent 색·밝기·반경을 저장 후 대조. Tutorial+Red 156개·Green108개, 총 광원 264개. 수직 통로 아래/위/바닥과 다른 구역 3곳을 화면 밖 렌더로 확인. 실제 PIE/FPS 미측정.
- 백업 C:/lightgame_ai/Backups/BeforeShaftAndColor_20261103, 작업 사본 C:/lightgame_ai/ShaftAndColor_20261103. 가이드 #shaft-ceiling-lights 참고.


### PPV_Spectrum_Look_01 — 화면 분위기 1차 (2026-11-03)
BP가 아닌 표준 PostProcessVolume. Tutorial+Red·Green의 기존 임시 볼륨 1개씩을 교체했다. Unbound=true, Enabled=true, Priority=50, BlendWeight=1. 폴더 Lighting/PostProcess.
- Manual 노출, Apply Physical Camera Exposure=false, Exposure Compensation=+1.0.
- Bloom=0.20, Threshold=1.5, Vignette=0.12. Fringe/MotionBlur/FilmGrain/LensFlare=0.
- WhiteTemp=6500, Tint=0. Global Saturation W=0.98, Contrast W=1.04.
- Shadows Gain RGB=(0.985,1,1.02), W=1. Gamma W=1.03. Offset RGB=(0.003,0.004,0.006), W=0. FilmToe=0.50.
- 18개 항목에만 Override 적용. 게임 로직, 재질, 조명 BP는 수정하지 않았고 PPV 외 액터 이름·클래스·변환 서명을 저장 후 재검증.
- 사용자의 실제 플레이 화면을 받은 뒤 2차 보정 예정. 가이드 #spectrum-look. 원본 맵 백업 C:/lightgame_ai/Backups/BeforePostProcess_20261103 (조명 BP 교체가 이미 반영된 시점).


### 2026-11-03 원거리 가독성 보완 (사용자 화면 피드백)
- 사용자 화면에서 먼 구조물이 발광 띠 외에는 보이지 않는 문제 확인. 기존 패널의 Max Draw Distance 1500 cm가 원거리 조명을 끄고, 레드 맵에는 기본 SkyLight가 없었음.
- BP_Floor_Plain_Light / BP_Wall_Light 및 기존 두 맵의 모든 패널 RectLight: Max Draw Distance=0, Max Distance Fade Range=0. 원거리 표시 제한 해제. 사용자 조명 강도·색·반경 보존(현재 배치 바닥 200 lm/1200 cm, 벽 각 350 lm/1800 cm).
- PPV_Spectrum_Look_01에 런타임 엔진 자산 GrayTextureCube를 Ambient Cubemap으로 지정, Intensity=.35, Tint=(1,1,1,1). Global Saturation/Contrast W=1. Shadows Gain=(1,1,1,1), Gamma W=1.10, Offset=(.006,.006,.006,0), FilmToe=.42, Vignette=.05. 기존 노출 +1과 Bloom .20 유지.
- 카메라 거리와 무관한 최소 바탕광 확보. 액터 배치·게임 로직 변경 없음. 실제 FPS 미측정. 원본 백업 C:/lightgame_ai/Backups/BeforeVisibilityFix_20261103.


### 2026-11-03 PPV 명암 3차 조정
사용자 화면에서 회색 막처럼 뜬 암부를 확인. 두 맵의 PPV_Spectrum_Look_01 설정 8개만 변경.
- Ambient Cubemap Intensity .35→.22, Shadows Gamma W 1.10→1.05, Offset RGB .006→.003(W=0).
- Global Contrast W 1.04, Film Toe .47, Vignette .08, Bloom Intensity .12, Threshold 2.0.
- Manual 노출 +1, 중립 색·기본 환경광, 조명 거리 제한 해제 유지. 두 맵에 ExponentialHeightFog가 없는 것도 확인.
- 조명 BP·강도·색·반경 및 게임 로직 변경 없음. 원본 백업 C:/lightgame_ai/Backups/BeforeContrastPass_20261103. 가이드 #spectrum-look에 현재값 반영.

### 2026-11-04 팀원 환경 조명 업데이트 로컬 적용
- PR #13(18aec1b) 이후 a4c7332의 신규 환경 조명 BP 4종과 Green/Tutorial+Red의 저장 맵·검증 도구를 선택 반영. 두 맵의 적용 전 로컬 파일이 PR 기준과 같음을 확인했다. Blue는 로컬 저장본을 유지하고 기존 BluePrint 파일 41개 및 Config·다른 맵의 해시 일치를 확인했다. 오늘 추가한 개폐·복귀·출발 지연과 광원 이동 동작 보존.
- Tools/Verify-EnvironmentLights.py의 저장 조명 264개·원본 배치 서명 검사와 두 맵 PPV 최종값 확인 통과. 새 BP 4종과 기존 BP_Hatch/BP_ReturnPlatform/BP_BlinkLight 컴파일 오류·경고 0. Blue 802개 액터 로딩 확인, 파일 저장 없이 검사. 문서 3개는 로컬 변경과 병합. 백업/결과 Saved/CodexBackups/EnvironmentUpdate-20261104. 이번 작업에서 실제 플레이/FPS 측정·커밋·푸시는 하지 않았다.
| 2026-11-06 | 사용자: 리셋 버튼(작업 29)·플레이 화면 HUD(작업 32) 동작 확인 |
| 2026-11-06 | 작업 18 필터 색별 유리 머티리얼: 사용자 구현 완료(어느 BP에 어떤 방식으로 넣었는지는 미기록 — 그래프 받으면 구조 절에 추가) |
| 2026-11-06 | 작업 33 점프 쿨타임·예약 그래프 확인(테스트 전): 변수 CanJumpAgain·JumpCooldown 추가, 기존 IsJump/clear_Jump를 예약 표시로 재사용 |
| 2026-11-06 | 작업 33 플레이어 속도·점프력 조정 동작 확인(값 미기록). 작업 17 발광 방식 = 색별 머티리얼 교체, 36 = 맵 배치 스크린, 37에 38 합침(설계만) |
| 2026-11-06 | BlockPull 실물 확인: 방향 Z 버림(Break/Make Vector) + UpForce 더함, 세기 Clamp(Distance2D × PullGain, 500, MaxPullSpeed), AddImpulse Vel Change. 작업 37 수정 안내 시작(미구현) |
| 2026-11-06 | 작업 37 BlockPull 수정 그래프 확인(테스트 전): 빛 주체 = Select(Found ? GetLightSource.actor : PlayerCharacter), 목표 = 주체 위치 + Forward × Front. 방향 = Normal(GetDirectionUnitVector(메시→목표) + UpForce) (높이 포함). 세기 = Clamp(Distance(3D)(메시, 목표) × Select(IsPlayer ? PLPullGain : MLPullGain), 500, Select(IsPlayer ? PLMaxPullSpeed : MLMaxPullSpeed)). AddImpulse(Vel Change) 한 번. 변수 PullGain/MaxPullSpeed → MLPullGain/MLMaxPullSpeed 이름 변경, PLPullGain/PLMaxPullSpeed 추가 |
| 2026-11-06 | BP_AvilityBlock Blue 변수 정리(사용자 결정): **PL = Player(플레이어 손전등)**, **ML = Map Light(맵 광원·거울 — GetLightSource.IsPlayer가 false인 모든 빛)**. 인스턴스 [I]는 `PLMaxPullSpeed`·`MLMaxPullSpeed`만. `PLPullGain`·`MLPullGain`(예전 PullGain, Float, 거리에 곱하는 세기)·`UpForce`(Vector, 위로 기울임)·`Front`(Float, 빛 주체 앞 목표 거리)는 BP 고정값. `MLPullGain`/`MLMaxPullSpeed`는 기존 변수 이름 변경이라 GUID·레벨 개별 값 유지 |
| 2026-11-06 | 작업 10/11 메뉴 설계 결정(미구현): 시작 화면 전용 맵 MainMenu(새 게임/이어하기/설정/게임 종료), ESC 메뉴 WBP_PauseMenu(계속/설정/사전/스테이지 초기화/종료→시작 화면). 스테이지 초기화는 현재 맵 다시 열기, 필터·반납 기록 유지 |

## 메뉴 (작업 10, 2026-11-06, 테스트 전)

### ESC 메뉴 — `Content/UI/WBP_PauseMenu` + `BP_PlayerController`
- 입력: `Content/GameMode/IA_Pause`(Digital, **Trigger when Paused**), `IMC_Default`에 Escape. PIE에서는 에디터 단축키 Play World → Stop의 Escape를 지워야 함.
- 위젯: Canvas → Dim(Image 전체, 검정 60%) / 태블릿 배경 이미지 + MenuBox(Vertical Box 정중앙): `Btn_Resume`(계속) / `Btn_Settings`(설정, 미구현) / `Btn_Dictionary`(사전, 작업 36) / `Btn_RestartStage`(스테이지 초기화) / `Btn_ToTitle`(타이틀로 → GoToTitle, 테스트 전) / `Btn_QuitGame`(게임 종료 → Quit Game, 2026-11-06 추가, 테스트 전).
- BP_PlayerController 변수 `PauseMenu`(WBP_PauseMenu), `IsMenuOpen`(bool).
  - `OpenPauseMenu`: IsValid(PauseMenu) Not Valid → Create Widget(Self) → Set PauseMenu → (합류) Add to Viewport(ZOrder 10) → Set Game Paused(true) → Set Input Mode Game And UI(Focus PauseMenu, Hide Cursor During Capture 끔) → Show Mouse Cursor true → IsMenuOpen true.
  - `ClosePauseMenu`: Remove from Parent → Set Game Paused(false) → Set Input Mode Game Only → Show Mouse Cursor false → IsMenuOpen false.
  - `IA_Pause` Started → Branch(IsMenuOpen) T → ClosePauseMenu / F → Get Controlled Pawn → Cast To BP_Charactor → Branch(Respawning) **False** → OpenPauseMenu (리스폰 암전 중 열지 않음).
  - IA_Pause True 쪽(2026-11-06 M-7-1): Get All Widgets Of Class(WBP_Settings) → Length > 0 → 있으면 For Each Remove from Parent(설정 창만 닫기) / 없으면 ClosePauseMenu.
  - `RestartStage`: ClosePauseMenu → Open Level (by Name)(Get Current Level Name, Remove Prefix). 필터·반납 기록은 GameInstance라 유지, 본 게임 모드 맵은 체크포인트에서 시작.
- 위젯 버튼: Btn_Resume → Get Owning Player → Cast To BP_PlayerController → ClosePauseMenu / Btn_RestartStage → … → RestartStage.
- 예정: M-9 본 게임 모드(BP_RealGameMode)에서만 열기.
- 버튼 마우스 올림 강조(M-8, 2026-11-07 사용자 동작 확인): 시작 화면과 같은 `SetMenuHover` 함수·`MenuFont` 변수를 복사. 버튼 글자 `Text_Resume`/`Text_Settings`/`Text_Dictionary`/`Text_RestartStage`/`Text_ToTitle`/`Text_QuitGame`(Is Variable), 버튼마다 On Hovered/On Unhovered → SetMenuHover.

### 시작 화면 — 맵 `Content/Code/Levels/MainManu` + `Content/UI/WBP_MainMenu`
- 맵 World Settings GameMode Override = `Content/GameMode/BP_MenuGameMode`(Game Mode Base, Default Pawn None, HUD None, Player Controller = 엔진 기본 PlayerController — BP_PlayerController는 HUD를 만들어서 안 씀).
- Level Blueprint: BeginPlay → Create Widget(WBP_MainMenu, Get Player Controller 0) → Add to Viewport → Set Input Mode UI Only(Focus 메뉴) → Show Mouse Cursor true.
- WBP_MainMenu: 배경 Image(지금은 이미지, 나중에 게임 화면) / TitleText(텍스트, 위쪽 가운데) / MenuBox: `Btn_NewGame` / `Btn_Continue` / `Btn_Settings`(미구현) / `Btn_Quit`.
  - 변수 `FirstStage`(World Soft Object Reference — Open Level (by Object Reference)의 Level 핀 Promote to Variable, 기본 Tutorial+Red 예정).
  - 함수 `PrepareForGame`: Set Input Mode Game Only(Owning Player) → Show Mouse Cursor false (맵 열기 전에 호출, UI Only 상태가 다음 맵에 남지 않게).
  - Event Construct → Cast BP_GameInstance → Progress → Break S_PlayerProgress → CheckpointLevel != None → Btn_Continue.Set Is Enabled.
  - Btn_NewGame → Cast BP_GameInstance → DeleteProgress → PrepareForGame → Open Level (by Object Reference)(FirstStage).
  - Btn_Continue → Cast BP_GameInstance → PrepareForGame → Open Level (by Name)(Progress.CheckpointLevel) → 맵에서 MoveToCheckpoint.
  - Btn_Quit → Quit Game(Owning Player, Quit).
  - 버튼 마우스 올림 강조(M-8, 2026-11-07 사용자 동작 확인): 버튼 안 글자 `Text_NewGame`/`Text_Continue`/`Text_Settings`/`Text_Quit`(일반 Text Block, Is Variable). 변수 `MenuFont`(Slate Font Info — Text Block은 Get Font 노드가 없어 Designer의 Appearance Font를 복사·붙여넣기, 글꼴을 바꾸면 다시 복사).
  - 함수 `SetMenuHover(Target: Text Block, Hovered: Bool, HoverColor: Linear Color)`: Set Color and Opacity(Make SlateColor(Select(Hovered ? HoverColor : 흰색))) → Set Render Scale(Select(Hovered ? 1.1 : 1)) → Set Font(Make SlateFontInfo(MenuFont를 Break한 값 그대로 + Outline Settings = Make FontOutlineSettings(Size Select 2/0, Color = HoverColor RGB + A 0.6))).
  - 버튼마다 On Hovered → SetMenuHover(글자, true, 색) / On Unhovered → SetMenuHover(글자, false). 색: 새 게임 빨(1, .45, .45) / 이어하기 초(.45, 1, .5) / 설정 파(.5, .65, 1) / 게임 종료 흰.
| 2026-11-06 | 메뉴 섹션 추가(작업 10, 테스트 전): ESC 메뉴 WBP_PauseMenu·BP_PlayerController Open/Close/RestartStage, 시작 화면 MainManu·BP_MenuGameMode·WBP_MainMenu(FirstStage, PrepareForGame, 이어하기 활성화) |
| 2026-11-07 | 빨강 폭발 방향을 블록 면 직각으로: 새 함수 FaceDirection, Explosion의 GetDirectionUnitVector 2개 교체 (테스트 전) |
| 2026-11-07 | FaceDirection: 낮은 블록 위·아래 판정(InFootprint) + 모든 모서리·꼭짓점은 모서리 점→대상 벡터(IsCorner, Clamp 방식) 추가 + Explosion 플레이어 입력 발 위치. 동작 확인 |
| 2026-11-07 | 메뉴 버튼 마우스 올림 강조(SetMenuHover·MenuFont) 시작 화면·ESC 메뉴 동작 확인. 설정 창 감도 슬라이더(WBP_Settings) 그래프 확인 |
| 2026-11-06 | 점프 잠금을 Event On Jumped로 이동(앉은 상태에서 Jump 실패 시 영구 잠김 수정). WBP_PauseMenu Btn_Settings → Create Widget(WBP_Settings) → Add to Viewport(ZOrder 20) 확인 |
