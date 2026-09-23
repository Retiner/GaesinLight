# Gesin 블루프린트 설명서

RGB 손전등으로 블록을 비춰서 능력을 발동시키는 퍼즐 게임. 레벨에 배치하는 세 가지 핵심 블루프린트(`BP_Charactor`, `BP_Light`, `BP_AvilityBlock`)를 어떻게 설정하고, 각 옵션이 뭘 하는지 정리한 문서.

---

## 1. BP_Charactor — 플레이어 캐릭터

레벨에 직접 배치할 경우 그 인스턴스의 **Auto Possess Player = Player 0**로 설정해야 플레이어가 조종함 (또는 `PlayerStart` + GameMode의 Default Pawn Class로 스폰).

### 설정 가능한 옵션
| 변수 | 타입 | 설명 |
|---|---|---|
| `LightLength` | Float | 손전등 빛이 닿는 최대 거리 |

(`SpreadRadius`는 감지 판정용 내부 값이라 사용자가 직접 설정하는 옵션이 아님.)

### 동작
- `IA_Red`/`IA_Green`/`IA_Blue` 입력으로 손전등 색을 전환 (`CurrentColor` 갱신 + `SpotLight` 색 변경).
- 매 틱 `SpotLight` 위치에서 13개 지점(중심 1 + 내부링 4 + 외부링 8)으로 레이캐스트를 쏴서, 맞은 액터들에게 `AddColorContribution`/`RemoveColorContribution`을 보냄. 여러 블록을 동시에 비출 수 있음.

---

## 2. BP_Light — 맵 배치용 광원

플레이어 손전등과 별개로, 레벨에 고정 배치해서 항상 빛을 비추는 광원.

### 설정 가능한 옵션
| 변수 | 타입 | 설명 |
|---|---|---|
| `LightColor` | Enum (Red/Blue/Green 3가지만) | 이 광원의 색. Construction Script에서 바로 반영되어 에디터에서도 미리보기됨 |
| `LightLength` | Float | BP_Charactor와 동일 |

(`SpreadRadius`는 감지 판정용 내부 값이라 사용자가 직접 설정하는 옵션이 아님.)

Yellow/Purple 같은 혼합색은 못 고름 — 두 개(Red+Green 등)를 같은 블록에 겹쳐 비추면 블록 쪽에서 합산돼서 혼합색으로 판정됨.

### 아직 없는 기능
- 켜고 끄는 상호작용(PlayerToggle), 회전(RotationSpeed) — 설계만 되어있고 미구현.

### 확인 필요
- "맵 광원 단독으로는 능력을 발동 못 시키고, 플레이어 손전등이 같이 비춰야만 발동"하게 만들자는 설계 논의가 있었음 — 실제로 `ReCalculate`/`IsLit` 로직에 반영됐는지는 별도 확인 필요.

---

## 3. BP_AvilityBlock — 능력 블록

빛을 받으면 색이 바뀌고, `React`에 지정된 색과 일치하면 능력이 발동하는 블록.

### 배치 시 설정 옵션
실제 Details 패널의 "눈" 아이콘(Instance Editable)이 켜진 것만 정리함. 꺼진 건 내부 계산용이라 건드릴 필요 없음.

**Setting (공통)**
| 변수 | 타입 | 설명 |
|---|---|---|
| `ReactColor` | Enum (All/Red/Blue/Green/Purple/Yellow/SkyBlue) | 이 블록이 반응할 색. `All`이면 어떤 색이 비춰지든 그 색으로 반응 + 능력 발동 |
| `Move` | Enum (Fixed/Physics/PatrolReturn/PatrolRotation/PatrolRestart) | 이 블록의 이동 방식. 능력 효과가 이 값에 따라 달라짐 (아래 표 참고) |
| `MovePoint` | Vector 배열 | `Move`가 Patrol 계열일 때 오갈 경유지들. 3D 위젯으로 편집 |
| `MoveSpeed` | Float | Patrol 이동 속도 |
| `IsUserStaticMesh` | Boolean | 켜면 기본 메시 대신 아래 `UserStaticMesh`를 사용 |
| `UserStaticMesh` | Static Mesh | `IsUserStaticMesh`가 true일 때 이 블록에 쓸 커스텀 메시 |

**Red — 폭발**
차징 완료 즉시 발동 (유지 시간 없이 바로 끝). `Move=Physics`면 이 블록 자신이 힘을 받아 튕겨나가고, 그 외 모드는 대신 주변 물체(플레이어 포함)를 밀어냄.

| 변수 | 타입 | 설명 |
|---|---|---|
| `InnerRadius` | Float | 이 반경 안에 있는 물체는 폭발력 100% |
| `OuterRadius` | Float | 이 반경 밖은 폭발력 0% (Inner~Outer 사이는 거리에 따라 감쇠) |
| `ExplosionForce` | Float | 주변 물체를 밀어내는 힘 (`Move≠Physics`일 때) |
| `PushForce` | Float | 이 블록 자신이 밀려나는 힘 (`Move=Physics`일 때) |
| `Exp_PlayerForce` | Float | 플레이어에게 따로 적용되는 폭발 힘 |

**Blue — 당기기**
차징 완료 즉시 발동 (유지 시간 없이 바로 끝). `Move=Physics`면 이 블록이 플레이어 쪽으로 끌려오고, 그 외 모드는 대신 플레이어가 블록 쪽으로 끌려감.

| 변수 | 타입 | 설명 |
|---|---|---|
| `MaxPullSpeed` | Float | 이 블록이 끌려올 때 최대 속도 (`Move=Physics`일 때) |
| `PlayerMaxPullSpeed` | Float | 플레이어가 끌려갈 때 최대 속도 (`Move≠Physics`일 때) |

**Green — 완전 정지**
차징 완료 시점부터 빛이 떠난 뒤 일정 시간(`HoldTime`)까지 정지 유지. `Move=Physics`면 물리 시뮬레이션을 꺼버리고, Patrol이면 이동을 멈춤. 다른 능력보다 차징이 훨씬 빠름(0.2초). 별도 튜닝 변수는 없음.

**Yellow & Sky Blue (공통) — 크기 변화**
차징이 **끝난 시점부터** 서서히 커지거나(Yellow) 작아지고(Sky Blue), 빛이 떠나면 서서히 원래 크기로 되돌아옴. (차징 중엔 크기가 안 변함 — 다 채워진 다음에만 애니메이션 시작.)

| 변수 | 타입 | 설명 |
|---|---|---|
| `ChangeSpeed` | Float | 크기가 커지고/작아지는 애니메이션 속도 |

(`BaseSize`는 배율 계산 기준값으로 내부에서 자동 관리 — 인스턴스 편집 대상 아님.)

**Yellow**
| 변수 | 타입 | 설명 |
|---|---|---|
| `UpScale` | Float (기본 2.0 권장) | 몇 배로 커질지 |

**Sky Blue**
| 변수 | 타입 | 설명 |
|---|---|---|
| `DownScale` | Float (기본 2.0 권장) | 몇 분의 1로 작아질지 (2면 절반) |

**Purple — 반투명 통과**
차징 완료 후부터 서서히 반투명해지면서 플레이어/물리 오브젝트가 통과 가능해짐, 빛이 떠나면 서서히 원래대로(불투명+충돌) 복구. `Move=Physics`면 바닥·벽(WorldStatic)은 계속 막고 그 외는 전부 통과. 투명도 목표값은 고정값이라 인스턴스별로 조절하는 변수는 없음.

### 능력 발동 타이밍 (공통)
빛을 계속 비추면 `ChargeAlpha`가 0→1로 차오르고(색마다 충전 시간 다름, Green은 0.2초로 빠름), 다 차면 능력 시작. 이후 빛이 떠나면 일정 시간(`HoldTime`, 보통 5초·Red/Blue는 즉시) 유지되다 쿨타임에 들어감.

### 알아둘 점
- **색 판정 규칙**: 여러 광원이 한 블록에 겹치면 R/G/B 기여도가 각각 더해져서, 채널당 0.5 이상이면 그 색이 켜진 걸로 계산. Red+Green=Yellow, Red+Blue=Purple, Blue+Green=SkyBlue.
- **콜리전 Visibility 채널은 항상 Block 유지**: 능력(특히 Purple의 통과 기능)을 만들 때 Pawn/WorldDynamic/PhysicsBody/WorldStatic은 건드려도 되지만, Visibility 채널을 건드리면 빛 감지 레이캐스트 자체가 블록을 못 찾게 됨.
- **충전/유지/쿨타임 시간 값(`ChargeTime`/`HoldTime`/쿨타임)은 인스턴스별이 아니라 `AvilityConfig` 함수 안에 색깔별로 고정되어 있음** — 블록마다 다르게 주고 싶으면 이 함수 자체를 수정해야 함, Details 패널에서 인스턴스별로는 못 바꿈.

---

## 아직 다루지 않은 것
6가지 색 능력(Red/Blue/Green/Yellow/SkyBlue/Purple)은 전부 구현 완료. 남은 건 아래 잡다한 항목들:
플레이어가 Physics 블록을 직접 드는 기능, Red 폭발 힘 세기 튜닝, 디버그용 Print String 정리, 손전등 빛샘 현상(Lighting Channels), FlashBeam을 RectLight로 바꿀지 여부.
