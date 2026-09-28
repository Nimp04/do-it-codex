# Jump OverFlow — 개발 리드 사전 구조 설계 요청

목적:
각 담당자가 자신의 모듈을 독립적으로 개발한 뒤
큰 구조 변경 없이 통합할 수 있도록 공통 구조와 데이터 계약을 정의함.

※ 각 모듈의 세부 알고리즘까지 설계할 필요는 없음.
※ 게임 기획 요소(HP 채택 여부, 아이템 종류, 난이도 등)는 임의로 확정하지 않음.


1. 전체 실행 구조

- main.py가 담당할 역할 정의
- 게임 상태 전환 구조 정의
  예: WAITING / PLAYING / GAME_OVER / SETTINGS
- 한 프레임에서 각 모듈이 실행되는 순서 정의

예시:
Input
→ Level / Item 상태 갱신
→ Player 물리·충돌 처리
→ HUD 상태 갱신
→ Render

- 게임 시작 / 재시작 / 종료 시
  각 모듈의 초기화 및 Reset 방식 정의


2. 모듈별 책임과 경계

각 파일이 "무엇을 담당하고 무엇은 담당하지 않는지" 명확히 정의

main.py
- 게임 전체 실행 흐름
- 모듈 호출 및 상태 전환

render.py
- Background / Map / Player / Object / HUD 렌더링
- Layer 관리
- Camera Following
- 인게임 좌표 → 화면 표시 위치 변환
※ Camera 관련 처리는 render.py 내부 책임으로 고정

player.py
- 입력에 따른 플레이어 이동
- 물리엔진
- 플레이어 관련 Collision
- 아이템 효과에 따른 플레이어 상태 변화

level_design.py
- 맵 / 발판 / 장애물 / 적 생성 및 관리
- 각 구조물의 위치·종류·상태 정보 제공
- 필요한 구조물 동작 처리

hud.py
- 현재 점수 / 최고 점수 등의 계산 또는 관리
- 대기화면 / 설정화면 / 게임 UI 상태 관리

item.py
- 아이템 종류 및 효과 정의
- 아이템 위치 / 상태 관리
- 획득된 아이템 효과 정보 제공


3. 공통 데이터 구조

모듈 간에 주고받아야 하는 데이터 형식을 정의

예:
Player
- position
- velocity
- size
- state
- active_effects

Platform / Obstacle / Enemy
- position
- size
- type
- state

Item
- id
- position
- type
- effect
- duration

Game / HUD
- current_score
- high_score
- game_state

각 데이터를
class / dataclass / dict / pygame.Vector2 등
어떤 방식으로 표현할지 결정

※ 좌표는 공통적으로 "인게임(World) 좌표"만 정의
※ 화면 좌표와 Camera 좌표는 render.py 내부에서 처리


4. 데이터 소유권

각 데이터의 원본을 어느 모듈이 관리하는지 결정

예:
- Player 위치 → player.py
- 발판 / 장애물 / 적 → level_design.py
- Item 위치 / 상태 → item.py
- Score → hud.py 또는 별도 GameState
- Game State → main.py

다른 모듈이 데이터를
직접 수정하는지 / 읽기만 하는지 / 함수 요청으로 변경하는지도 정의

목표:
같은 데이터를 여러 모듈이 동시에 관리하지 않도록 함.


5. 모듈 간 Interface

각 모듈이 다른 모듈에
"무엇을 입력받고 무엇을 제공하는지" 정의

필수 관계:

level_design.py → player.py
- 충돌 판정에 필요한 발판 / 장애물 / 적 정보

level_design.py → render.py
- 화면에 표시할 구조물의 위치 / 형태 / 상태

player.py → render.py
- 플레이어 위치 / 방향 / 상태 / 표시 정보

item.py → player.py
- 획득한 Item의 효과 정보

item.py ↔ level_design.py
- 장애물 파괴 등 Level에 영향을 주는 Item 효과 처리 방식

hud.py → render.py
- 점수 / UI / 메뉴 정보

main.py ↔ 각 모듈
- initialize / update / reset 등의 호출 규칙


6. Collision 및 Event 처리 구조

다음 상호작용의 처리 주체 정의

- Player ↔ Platform
- Player ↔ Obstacle
- Player ↔ Enemy
- Player ↔ Item
- Item Effect ↔ Obstacle / Enemy

특히 한 모듈이 다른 담당자의 내부 상태를
직접 수정하지 않도록 처리 방법을 정할 것.

예:
- 함수 호출
- 상태 반환
- Event 반환
- main.py가 중재

중 적절한 구조 선택.


7. 확장 가능한 Item 구조

Item 추가 때문에
player.py / level_design.py를 매번 크게 수정하지 않도록 구조 설계

현재 예상 효과:
- Jump Boost
- Move Speed Boost
- Invincible
- Obstacle Destroy

새 Item 추가 시 기존 코드 수정 범위를
최소화할 수 있는 구조를 고려.


8. 프로젝트 공통 구조

- 파일 / 폴더 구조
- assets 관리 방식
  - images
  - sounds
  - fonts
- Constants / Config 위치
  - FPS
  - Window Size
  - Gravity
  - Player Speed 등
- 최고점수 / 설정값 저장 방식
- Import 방향 및 Circular Import 가능성 점검


9. 최소 Skeleton 설계

본격적인 기능 구현 전에
각 담당자가 맞춰서 개발할 수 있는 최소 인터페이스 작성

예:
Player.update(...)
Level.update(...)
ItemManager.update(...)
HUD.update(...)
Renderer.render(...)

실제 알고리즘 구현은 하지 않아도 되며,
필요한 Parameter / Return 형식 정도까지 정의.


# 최종 산출물

1. 모듈 관계도
2. 모듈별 책임 정리
3. 공통 데이터 구조 표
4. 모듈별 Input / Output 표
5. main Game Loop 의사코드
6. 최소 Skeleton 또는 함수 Interface
