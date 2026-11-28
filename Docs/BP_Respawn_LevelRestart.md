# BP_Respawn 레벨 재시작

`BP_Respawn`의 기존 접촉 판정에 선택 가능한 레벨 재시작 동작을 추가했습니다.

## 사용법

1. 레벨에 배치한 BP_Respawn의 **Reload Level on Respawn**을 켭니다.
2. **Reset Player**, **Reset Block**에서 재시작을 일으킬 접촉 대상을 선택합니다. 둘 다 켜도 됩니다. 블록은 기존과 동일하게 BP_AvilityBlock 계열입니다.
3. **Restart Destination Actor**에 스폰 지점 액터(예: TargetPoint)를 지정합니다. 지정하면 그 액터의 위치와 회전을 사용합니다. 비워두면 기존 **Player Respawn Location**을 BP의 시작 트랜스폼으로 변환한 위치와 플레이어의 현재 방향을 사용합니다.

| Level Restart 설정 | 기본값 | 기능 |
|---|---|---|
| Reload Level on Respawn | false | 선택한 대상의 접촉 시 현재 레벨 전체 재시작 |
| Restart Destination Actor | None | 재시작 후 플레이어의 위치·방향 기준 액터 |
| Respawn Reload Delay | 0.35초 | 로딩 전 암전 전환 시간 |
| Respawn Fade In Duration | 0.35초 | 로딩 후 화면이 다시 밝아지는 시간 |
| Respawn Black Hold Duration | 0.1초 | 로딩·스폰 적용 후 암전 추가 유지 시간 |

블록이 접촉해도 재시작 후 지정한 위치로 이동하는 대상은 플레이어입니다. 레벨 재로드로 블록·버튼·신호 등의 런타임 상태는 저장된 맵의 초기 상태로 복원됩니다. 재시작용 스폰 위치는 GameInstance에 임시 보관하며 Save0.sav를 변경하지 않습니다.

암전과 스폰 복원은 BP_MovingRestartLaser의 기존 GameInstance·PlayerController 처리와 공유합니다. 로딩 직전 완전한 검정으로 고정하고, 새 컨트롤러에서도 검정을 유지한 뒤 스폰 적용 → 암전 유지 → 화면 복귀 순서로 처리합니다. 같은 재시작 중 추가 요청은 무시합니다.

기본값 false이므로 기존 BP_Respawn은 기존 동작을 유지합니다. UseCustomRespawnProcessing을 사용하는 자식의 별도 오버랩 처리는 변경하지 않았습니다. BP_SignalRespawn/BP_SignalLaser/BP_MovingRestartLaser의 기존 전용 처리는 그대로 유지됩니다.

## 검증

2026-11-28: BP_Respawn 및 신호 리스폰·레이저 자식 BP 컴파일 오류 0, BP_Respawn 컴파일 경고 0. PIE에서 18개 검증 통과: 선택하지 않은 접촉 무시, 플레이어/블록 접촉 각각의 실제 월드 재로드, 지정 액터의 위치·방향 복원, 기존 상대 스폰 좌표 사용, 중복 요청 차단, 로딩 후 암전 대기 중 입력 잠금과 복귀 후 해제, 영구 세이브 보존, BP 런타임 오류 0.
