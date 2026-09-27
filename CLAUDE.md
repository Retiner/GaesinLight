# GaesinLight 프로젝트 — AI 작업 컨텍스트

RGB 손전등 퍼즐 게임. UE 5.8. 이 파일은 이전 세션(C:\unreal\Gesin에서 작업)에서 만든 내용을 정리한 것 — 새 세션 시작 시 먼저 읽고 시작할 것.

## 빛 감지 시스템

- **BP_Charactor**(플레이어): `SpotLight` 위치에서 13개 지점(중심 1 + 내부링 4개@40%반경 + 외부링 8개@100%반경)으로 매 틱 레이캐스트. `SpreadRadius`(퍼짐 범위)/`LightLength`(사거리) 변수 사용. `CurrentHit`/`LastLitActor`(둘 다 Actor 배열)로 diff 계산해서 `LightActor`/`UnLightActor` 호출. `IA_Red`/`IA_Green`/`IA_Blue`로 `CurrentColor`(손전등 색) 전환.
- **BP_Light**(맵 배치 광원): 같은 13포인트 시스템 포팅됨. `LightColor` enum(Red/Blue/Green 3색)만 지원.
- **LightActor/UnLightActor**: `IsValid` + `DoesImplementInterface(BPI_LightInteractable)` 체크 후 `AddColorContribution`/`RemoveColorContribution` 인터페이스 메시지 전송.
- **색 혼합 버그 수정 완료**: 계속 비추는 중 색 바꿔도 반영되도록 `LightActor`를 매 틱 무조건 호출하게 고침 (예전엔 "새로 비춘 것"만 호출해서 색 안 바뀌는 버그 있었음).

## BP_AvilityBlock (능력 블록) — 6색 전부 구현 완료

**공통 변수**: `ReactColor`(반응할 색), `Move`(Fixed/Physics/PatrolReturn/PatrolRotation/PatrolRestart), `MovePoint`(Patrol 경유지 배열), `MoveSpeed`, `IsUserStaticMesh`, `UserStaticMesh`, `BaseSize`(내부용, 편집 대상 아님).

**능력 발동 흐름**: `ChargeAlpha` 0→1 차오르면(색마다 `ChargeTime` 다름, Green은 0.2초로 빠름) `AvilityStart` 호출 → `HoldRemain` 카운트다운(빛 비추는 동안 갱신) → 0 되면 `AvilityEnd` + CoolTime 진입.

| 색 | 변수 | 동작 |
|---|---|---|
| Red(폭발) | `InnerRadius`/`OuterRadius`/`ExplosionForce`/`PushForce`/`Exp_PlayerForce` | `Move=Physics`면 자신이 밀려남(Push), 아니면 주변을 밀어냄(Explosion) |
| Blue(당기기) | `MaxPullSpeed`/`PlayerMaxPullSpeed` | `Move=Physics`면 블록이 끌려옴(BlockPull), 아니면 플레이어가 끌려감(PlayerPull) |
| Green(정지) | (튜닝 변수 없음) | `Move=Physics`면 SimulatePhysics 끔, Patrol이면 이동 멈춤. `Freeze`/`Unfreeze` 함수 |
| Yellow/SkyBlue(크기 변화) | `ChangeSpeed`(공통) + `UpScale`/`DownScale` | 아래 참고 |
| Purple(반투명 통과) | (튜닝 변수 없음, Opacity 목표값 고정) | 아래 참고 |

**Yellow/SkyBlue 상세**: `Y_UpScale(Alpha)`/`SB_DownScale(Alpha)` 함수 = `BaseSize × Lerp(1.0, UpScale 또는 1/DownScale, Alpha)`. EventGraph에 Timeline(Alpha 트랙, 0→0.4초) 추가, `Update`가 이 함수 호출. Custom Event `Grow`(→Timeline `Play`), `Y_Reset`/`SB_Reset`(→Timeline `Reverse`)를 `AvilityStart`/`AvilityEnd`에서 호출. **차징 중엔 크기가 안 변하고 차징 완료 후부터 서서히 변함** — 이게 `ChargeAlpha`를 직접 안 쓰고 독립 Timeline을 쓰는 이유(ChargeAlpha로 하면 차징 중에 이미 커지는 문제 있었음).

**Purple 상세**: `M_BlockBase` 머티리얼을 Translucent + `Opacity` 파라미터로 변경. **Nanite가 Translucent 블렌드모드를 지원 안 해서**, `M_BlockBase`를 쓰는 스태틱메시(`SM_Element_Plain`, `SM_Element_Chain` 등)는 Nanite 꺼야 함(Nanite Settings > Enable Nanite Support 해제) — 이미 이 두 개는 처리함, 다른 메시가 더 있으면 동일하게 처리 필요. `P_Collision` 함수: `GetCollisionProfileName` 저장 → `Move==Physics` 분기 → Physics면 Pawn/WorldDynamic/PhysicsBody만 Ignore, 아니면 그 3개+WorldStatic도 Ignore. `P_CollisionReset`: `SetCollisionProfileName`(저장값)으로 한 번에 복구. **Visibility 채널은 항상 안 건드림**(빛 감지 레이캐스트가 이 채널을 쓰기 때문).

## 문서화

`README.md`, `README.txt`에 위 옵션/능력 설명이 사용자 대상으로 정리되어 있음(이 파일과 중복 있음, 이 파일은 AI/개발 이어가기용, README는 팀 공유용).

## Git / 배포 구조

- 저장소: `https://github.com/Retiner/GaesinLight.git`, 이 폴더(`C:\unreal\GaesinLight`)가 로컬 클론이고 `origin/main`과 동기화된 상태.
- `Content/Assets/`(Materials, StaticMeshes, Textures)는 **git 제외** — 구글 드라이브로 별도 배포(`ArtManifest.json`으로 관리), `.gitignore`에 `/Content/Assets/` 있음. 새 아트 애셋 받으면 이 폴더 구조 그대로 채워 넣을 것.
- `Config/*.uproject`는 프로젝트마다 달라서 git으로 안 섞음. **단 예외**: `r.VolumetricFog.HistoryWeight=0`을 `Config/DefaultEngine.ini`의 `[ConsoleVariables]` 섹션에 추가해서 커밋함 (빛이 움직일 때 잔상/고스팅 생기던 문제 수정 — 원래 있던 `Gesin` 프로젝트 설정과 맞춘 것).
- 커밋 전엔 항상 `git status`로 의도치 않은 변경(에디터 열어두면 자동저장되는 애셋 등)이 섞였는지 확인할 것.

## 알려진 미해결 항목

- `Content/Assets/Materials/M_Metal_Gunmetal_002.uasset` 파일 누락 — 드라이브에서 재다운로드 필요.
- 엔진 자체 파일(`FBXLegacyPhongSurfaceMaterial`, 언리얼 설치 폴더 안) 수정 건은 git으로 절대 안 옮겨짐 — 상대방 컴퓨터에서 FBX 메시가 하얗게/까맣게 보이는 증상 나오면 엔진 파일 자체를 직접 고쳐야 함(프로젝트 문제 아님).
- 플레이어가 Physics 블록 직접 드는 기능, Red 폭발 힘 세기 튜닝, 디버그 Print String 정리, 손전등 빛샘(Lighting Channels), FlashBeam RectLight 여부 — 전부 미착수.

## 작업 스타일 (이전 세션 기준)

- 사용자는 Blueprint를 배우는 중 — 직접 그래프를 만들고, 만든 후 K2Node 텍스트를 붙여넣어서 검증받는 방식으로 작업함. 대신 만들어주지 말고, 목적→노드 역할→구체적 행동 순서로 설명하고 한 번에 한 단계씩 진행할 것.
- 한국어로 대화.
