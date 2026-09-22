# GaesinLight

Unreal Engine 5.8 프로젝트. `GaesinLight.uproject`를 열면 `/Game/Code/Levels/TestMap_Blockout`이 열린다.

## 콘텐츠 규칙

Content/
- Code/Blueprints: 앞으로 게임플레이 블루프린트를 만드는 위치. 애니메이션 블루프린트와 컨트롤 리그도 코드로 관리한다.
- Code/Input: 입력 액션 및 매핑 컨텍스트.
- Code/Levels: 레벨(.umap).
- Assets/StaticMeshes: 스태틱 메시.
- Assets/Materials: 머테리얼과 머테리얼 인스턴스.
- Assets/Textures: 텍스처.

Code와 프로젝트 설정은 Git으로 공유한다. Assets 전체는 .gitignore로 제외하고 ZIP으로 별도 공유한다. C++를 추가할 경우 엔진 표준 위치인 프로젝트 루트 Source/에 둔다. Content/Code는 블루프린트용 분류이며 C++ 소스 폴더를 대체하지 않는다.

캐릭터 메시, 애니메이션, 사운드가 필요하면 Assets 아래에 SkeletalMeshes, Animations, Audio 폴더를 추가한다. 블루프린트는 Assets에 넣지 않는다. 월드 파티션이 생성하는 __ExternalActors__/__ExternalObjects__는 언리얼 관리 폴더이므로 임의로 옮기지 않고 레벨과 함께 Git에 포함한다.

## 팀원 최초 실행

1. Git 저장소를 clone한다.
2. ArtManifest.json의 archive에 적힌 ZIP을 팀 공유 저장소에서 받는다.
3. `Get-FileHash -Algorithm SHA256 <ZIP경로>` 결과를 manifest의 archiveSha256과 비교한다.
4. 언리얼을 닫고 .uproject가 있는 폴더에 ZIP을 푼다. 결과가 Content/Assets가 되어야 한다.
5. GaesinLight.uproject를 UE 5.8로 연다.

이전 MapAssets 기반 ZIP 대신 현재 manifest가 지정한 새 구조의 ZIP을 사용한다. Git만 받으면 모델과 재질이 없으므로 ZIP도 필요하다.

## 에셋 변경 후

에셋 저장 및 언리얼 종료 후 프로젝트 폴더에서 실행한다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Tools\Export-Art.ps1 -OutputDirectory C:\lightgame_ai\GaesinLightSetup
```

ZIP을 별도 공유하고 갱신된 ArtManifest.json을 관련 코드/레벨과 함께 commit한다. 삭제나 이름 변경이 포함되면 삭제 목록도 전달한다. 압축을 덮어 푸는 것만으로 옛 파일이 삭제되지는 않으며 팀원의 미공유 작업을 먼저 백업해야 한다.

LFS 필터는 설정하지 않았다. .uasset/.umap은 바이너리이므로 같은 블루프린트/레벨 동시 편집은 담당자를 나눈다. GitHub 저장소: https://github.com/Retiner/GaesinLight (main 브랜치).

## 현재 상태

이번 정리 시작 당시 기존 Characters/FirstPerson/Input/LevelPrototyping 폴더가 이미 제거되어 있었다. 블루프린트/입력 폴더는 앞으로 사용할 빈 폴더로 준비했다. DefaultEngine.ini의 GlobalDefaultGameMode는 삭제된 BP_FirstPersonGameMode를 가리키므로, 플레이 기능을 복구할 때 해당 블루프린트를 복구하거나 새 게임 모드를 지정해야 한다. 이번 작업에서는 사용자가 제거한 파일을 임의로 복구하지 않았다.
