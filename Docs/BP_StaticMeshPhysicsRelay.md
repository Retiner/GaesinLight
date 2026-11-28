# BP_StaticMeshPhysicsRelay

에셋: `/Game/BluePrint/BP_StaticMeshPhysicsRelay`  
부모: `BP_Activate`

배치된 StaticMeshActor 여러 개를 기존 신호 시스템으로 물리 시뮬레이션 상태로 전환합니다.

## 연결

1. 레벨에 `BP_StaticMeshPhysicsRelay`를 배치합니다.
2. 디테일의 **Physics Release > Physics Targets** 배열에 떨어뜨릴 스태틱메시 액터들을 지정합니다. 콘텐츠 브라우저의 메시 에셋이 아니라 레벨에 배치된 액터를 선택합니다.
3. `BP_Trigger`의 **Targets**에 중계 BP를 지정하고 **Channel = 0**으로 설정합니다.
4. 플레이어가 트리거에 들어오면 대상들이 각각 중력으로 떨어집니다.

## 설정과 동작

| 설정 | 기본값 | 의미 |
|---|---|---|
| Physics Targets | 빈 배열 | 물리로 전환할 StaticMeshActor 목록 |
| Input Channel | 0 | 낙하를 시작할 수신 채널 |
| Channel Required | 0번: 1개 | 부모 BP의 채널별 필요 신호 개수 |

신호가 활성화되면 `ReleaseMeshes`가 한 번 실행됩니다. 각 유효한 대상의 StaticMeshComponent에 Movable → PhysicsActor 충돌 프리셋 → 중력 활성화 → Simulate Physics 활성화 → Wake All Rigid Bodies를 적용합니다. 비어 있거나 삭제된 대상은 건너뜁니다. 신호가 끊겨도 떨어지는 상태를 유지하고, 추가 신호로 위치를 초기화하거나 물리 상태를 재설정하지 않습니다. 새 플레이 세션에서는 다시 작동합니다.

Input Channel을 변경하면 해당 채널의 Channel Required도 설정합니다. 대상은 트리거 전까지 원래 설정을 유지하므로 처음에는 Simulate Physics를 끈 메시를 지정합니다. 목록의 메시들은 서로 독립적인 물리 객체이며, 용접된 한 덩어리로 취급하지 않습니다.

메시 자체에는 물리에 사용할 단순 충돌이 있어야 합니다. 충돌이 없거나 Use Complex Collision As Simple인 메시에는 스태틱메시 에디터에서 적절한 단순 충돌을 먼저 설정해야 합니다. 이 BP는 공유 메시 에셋의 충돌 데이터를 수정하지 않습니다.

## 검증

2026-11-26: BP 컴파일 오류·경고 0개. PIE 검증 14개 통과. 기존 BP_Trigger에 플레이어가 실제로 겹칠 때 낙하, 여러 대상 동시 물리 전환, 중력에 의한 Z 감소, 미지정 대상 유지, 신호 해제 후 낙하 유지, 잘못된 채널·중복 신호·필요 개수·빈 대상·삭제된 대상 처리 확인.
