# Jump OverFlow — 구조 설계 및 모듈 연결 계약

기준: 2026-10-12의 `main.py` 호출 구조와 현재 합의한 모듈 책임.

이 문서는 각 담당 모듈이 구현해야 할 연결 계약이다. `main.py`의 호출 뼈대는 작성됐지만,
다른 기능 모듈과의 실제 연동은 완료되지 않았다. `render.py`는 `Renderer()` 생성,
Camera / Background, 좌표 변환과 화면 범위 제공을 구현했다. Player / Level / Item / HUD는
아직 구현이 필요하며, 전체 게임 실행은 완료되지 않았다.

## 1. 모듈 관계도

```text
                         main.py
                전체 실행 / 상태 관리 / 모듈 중재
          ┌──────────────┼──────────────┬──────────────┐
          │              │              │              │
          v              v              v              v
      player.py    level_design.py    item.py        hud.py
          ^              │              │
          │              │              │
          └──────────────┴──────────────┘
                         Player Collision용 데이터 제공

      player.py    level_design.py    item.py        hud.py
          └──────────────┬──────────────┬──────────────┘
                         v              v
                           render.py
                    화면 생성 / 렌더링 / 레이어
                               |
                               v
                     Screen / Camera / Background
```

화살표는 데이터 관계를 나타내며, 게임 모듈의 생성과 호출은 `main.py`가 중재한다.

### 기본 원칙

- `main.py`는 각 모듈의 실행 순서와 연결을 담당한다.
- Game State는 `main.py`의 `Game.state`가 소유하며, 변경도 `main.py`에서 수행한다.
- 화면 생성은 `Renderer()` 내부에서 수행한다. `main.py`는 Screen을 생성하지 않는다.
- `level_design.py`는 Player Collision에 필요한 구조물 정보를 제공한다.
- `item.py`는 Item 정보를 제공하고 획득 시 제거와 효과 전달을 담당한다.
- `player.py`는 Player와 관련된 Collision 판정을 담당한다.
- `render.py`는 각 모듈의 상태를 읽고 화면에 출력한다.
- 한 모듈이 다른 모듈의 내부 데이터를 직접 수정하지 않는다.

---

# 2. 모듈별 책임 정리

| 모듈 | 주요 책임 | 담당하지 않는 것 |
|---|---|---|
| `main.py` | 모듈 객체 생성, Game State 관리, 프레임 루프, 각 모듈 호출, 데이터 전달 및 Event 중재, 종료 시 pygame 정리 | 화면 생성, 물리 계산, Collision 알고리즘, 점수 계산, 렌더링 |
| `player.py` | Player 이동, 중력, 점프, 물리 처리, Player Collision, Item Effect 적용, 사망·화면 하단 추락 판정 | 발판/아이템 생성, Camera 계산, Game State 변경 |
| `level_design.py` | Platform, Obstacle, Enemy 생성 및 관리, 구조물 정보 제공 | Player 상태 직접 수정, 렌더링 |
| `item.py` | Item 생성 및 관리, ItemType / EffectType 정의, 획득 시 제거, Player / Level 공개 메서드를 통한 효과 적용 | Player / Level 내부 상태 직접 수정, Game State 변경 |
| `hud.py` | 현재 점수, 최고 점수, Waiting / Setting / Playing / Game Over UI 상태 관리 | Game State 직접 변경, Player 상태 직접 변경 |
| `render.py` | 화면·글꼴 등 출력 자원 준비, Camera / Background 관리, 레이어 출력, World → Screen 좌표 변환, 보이는 월드 범위 제공 | 물리, Collision, 추락 판정, 점수 계산, Game State 변경 |
| `config.py` | FPS, 화면 크기, 독립적인 월드 원점·너비, 카메라 추적 기준, 배경 이동 비율 | 실행 로직, 월드 높이 상한 |

### Game State

Game State의 원본은 `main.py`가 관리한다.

```text
WAITING
   |
   | Start
   v
PLAYING
   |
   | Game Over
   v
GAME_OVER
   |
   | Home
   v
WAITING
```

설정 화면은 다음과 같이 관리한다.

```text
WAITING
   |
   | Setting
   v
SETTING
   |
   | Back
   v
WAITING
```

HUD는 Game State를 직접 변경하지 않고 `START_GAME`, `OPEN_SETTING`, `RETURN_HOME` 등의 요청을 반환하며, 실제 상태 변경은 `main.py`가 수행한다.

`GameState`는 `main.py`의 `StrEnum`이며 값은 `WAITING`, `SETTING`, `PLAYING`, `GAME_OVER`이다.
각 모듈은 전달받은 상태를 읽고, 요청이나 처리 결과를 반환한다. 상태를 읽기 위해
`main.py`를 Import할 필요는 없으며 문자열 값으로 비교할 수 있다.

| 현재 상태 | HUD 요청 | 다음 상태 | 초기화 |
|---|---|---|---|
| `WAITING` | `START_GAME` | `PLAYING` | `reset_game(game)` |
| `WAITING` | `OPEN_SETTING` | `SETTING` | 없음 |
| `SETTING` | `RETURN_HOME` | `WAITING` | 없음 |
| `GAME_OVER` | `RESTART` | `PLAYING` | `reset_game(game)` |
| `GAME_OVER` | `RETURN_HOME` | `WAITING` | 없음 |

요청이 없으면 `None`을 반환한다. 알려진 요청이 현재 상태에 맞지 않으면 무시하고,
정의하지 않은 요청 문자열은 오류로 처리한다. 창 닫기 이벤트가 있으면 UI 요청보다
우선하여 루프를 종료하며, 그 프레임의 게임 갱신과 출력은 수행하지 않는다.

---

# 3. 공통 데이터 구조 표

## Player

`Player`는 데이터와 동작을 함께 가지므로 일반 `class`로 정의한다.

| 데이터 | 자료형 | 설명 |
|---|---|---|
| `position` | `pygame.Vector2` | World 기준 Player 위치 |
| `velocity` | `pygame.Vector2` | x, y 방향 속도 |
| `size` | `tuple[int, int]` | width, height |
| `state` | `PlayerState(Enum)` | Player 현재 상태 |
| `active_effects` | `dict[EffectType, float]` | 활성 효과와 남은 지속시간 |

예:

```python
active_effects = {
    EffectType.JUMP_BOOST: 3.5,
    EffectType.INVINCIBLE: 1.8
}
```

---

## Platform / Obstacle / Enemy

기본적으로 데이터 저장이 중심이므로 `dataclass`를 사용한다.

| 데이터 | 자료형 | 설명 |
|---|---|---|
| `position` | `pygame.Vector2` | World 기준 위치 |
| `size` | `tuple[int, int]` | width, height |
| `type` | 각 객체별 `Enum` | 구조물 종류 |
| `state` | 필요한 경우 `Enum` | 현재 상태 |

Enemy의 동작이 복잡해질 경우 일반 `class`로 확장할 수 있다.

---

## Item

Item은 기본적으로 `dataclass`로 정의하며 기능이 복잡해질 경우 일반 `class`로 확장한다.

| 데이터 | 자료형 | 설명 |
|---|---|---|
| `id` | `int` 또는 `str` | Item 식별값 |
| `position` | `pygame.Vector2` | World 기준 위치 |
| `size` | `tuple[int, int]` | width, height |
| `type` | `ItemType(Enum)` | Item 종류 |
| `effect` | `EffectType(Enum)` | 획득 시 발생하는 효과 |
| `duration` | `float` 또는 `None` | 효과 지속시간 |

---

## Game / HUD

| 데이터 | 자료형 | 소유 모듈 |
|---|---|---|
| `current_score` | `int` | `hud.py` |
| `high_score` | `int` | `hud.py` |
| `Game.state` | `GameState(StrEnum)` | `main.py` |

`main.py`의 `Game`은 `dataclass`이며 `player`, `level`, `items`, `hud`, `renderer`의
인스턴스 참조와 `state`를 묶어 보관한다. 각 객체 내부의 게임 데이터는 해당 모듈이 소유한다.
PlayerState, 객체 Type / Effect Enum 등은 각 기능 모듈에서 정의해야 할 설계 항목이다.

---

## 좌표 공통 규칙

모든 게임 로직에서는 World 좌표만 사용한다.

- 월드 원점은 `(0, 0)`이며 x는 오른쪽, y는 위쪽으로 증가한다.
- 월드 너비는 화면 해상도와 독립적인 값이다. 위쪽 높이에는 상한을 두지 않는다.
- pygame Screen 좌표의 y는 아래쪽으로 증가하므로 Renderer에서 방향을 변환한다.
- 게임 객체의 `position`은 월드 좌측 하단이며 `size`는 월드 단위의 너비·높이이다.
- Camera.position은 현재 화면에 보이는 월드의 좌측 하단이다. 초기 위치는 WORLD_ORIGIN이다.
- Renderer는 화면 너비 / WORLD_WIDTH를 배율로 사용하여 위치와 크기를 함께 변환한다.
- 화면 y는 화면 높이 - (월드 y - 카메라 y) × 배율로 계산한다.

```text
World 좌표
    |
    v
render.py
    |
Camera 변환
    |
    v
Screen 좌표
```

Camera 좌표 및 Screen 좌표 계산은 `render.py` 내부에서만 수행한다.

`main.py`는 `renderer.camera.update(player.position)`을 호출하고,
`renderer.get_world_bounds()`의 결과를 Player에 전달한다. 카메라 이동과 범위 계산은
Renderer / Camera가, 사망·화면 하단 추락 판정은 Player가 수행한다.

보이는 월드 범위는 `(left, bottom, right, top)` 순서의 tuple로 반환한다.
`Player.is_alive(world_bounds)`는 생존 여부를 `bool`로 반환하며,
화면 상단으로 올라간 것만으로 게임오버가 되지 않는다.

---

# 4. 모듈별 Input / Output 표

| 모듈 | Input | Output |
|---|---|---|
| `main.py` | pygame Event, 각 모듈의 반환값 | Game State 변경, 각 모듈 호출 및 데이터 전달 |
| `player.py` | `dt`, 사용자 입력, Platform / Obstacle / Enemy / Item 정보, 보이는 월드 범위 | Player 상태, Collision Event 목록, 생존 여부 |
| `level_design.py` | `dt`, Level 관련 요청 | Platform / Obstacle / Enemy 정보 |
| `item.py` | `dt`, Item 획득 요청, 효과 적용 대상 Player / Level | Item 정보, 획득에 따른 제거 및 효과 적용 |
| `hud.py` | Game State, Player/Game 정보, UI Event | Score/UI 정보, 버튼 Action |
| `render.py` | Game State, Player / 구조물 / Item / HUD 정보, 카메라 갱신 요청 | 화면 출력, 보이는 월드 범위 |

### `level_design.py` → `player.py`

전달 데이터:

```text
Platform
- position
- size
- type
- state

Obstacle
- position
- size
- type
- state

Enemy
- position
- size
- type
- state
```

Player는 전달받은 구조물 데이터를 Collision 판정 목적으로 사용한다.

---

### `item.py` → `player.py`

전달 데이터:

```text
Item
- id
- position
- size
- type
- effect
- duration
```

Player는 Item과의 Collision을 판정한다.

Item 획득이 확인되면 Player가 `ITEM_COLLECTED` Event와 `item_id`를 반환한다.
`main.py`는 `ItemManager.collect(item_id, player, level)`을 호출한다.
ItemManager가 Item을 제거하고, 효과 대상의 공개 메서드를 호출한다.
효과 종류·지속시간·적용 대상에 대한 분기 로직은 `item.py`가 담당한다.

### Collision Event 계약

`Player.check_collisions(...)`는 아래 형식의 dict 목록을 반환한다.
Event가 없으면 빈 목록 `[]`을 반환한다.

```python
{"type": "GAME_OVER"}
{"type": "ITEM_COLLECTED", "item_id": 7}
```

`item_id`는 Item의 식별값이며 `int` 또는 `str`이다. `GAME_OVER`를 처리하면
`Game.state`를 변경하고 그 뒤의 Collision Event 처리는 중단한다.
정의하지 않은 Event 종류는 오류로 처리한다.

---

### `player.py` → `render.py`

```text
position
size
state
direction
```

---

### `level_design.py` → `render.py`

```text
Platform / Obstacle / Enemy
- position
- size
- type
- state
```

---

### `item.py` → `render.py`

```text
Item
- position
- size
- type
- state
```

---

### `hud.py` → `render.py`

`HUD.get_ui_data()`는 아래 형식의 dict를 반환한다.

```python
{
    "current_score": 10,
    "high_score": 20,
    "texts": [{"text": "Jump OverFlow", "position": (12, 90)}],
    "buttons": [{"text": "시작", "rect": pygame.Rect(200, 350, 200, 60)}],
}
```

`texts`와 `buttons`는 선택적인 목록이며, 없으면 출력하지 않는다.
각 위치와 Rect는 화면 좌표이며 카메라의 영향을 받지 않는다. 문구 위치는 화면 좌측 상단 기준이다.
버튼 배치와 클릭 판정, 요청 반환은 HUD가 담당하고 Renderer는 해당 Rect와 문구를 출력한다.
PLAYING / GAME_OVER에서는 Score / Best를 출력하고 월드 객체를 그린다.
WAITING / SETTING에서는 배경과 HUD만 출력한다.

---

### 데이터 수정 원칙

다른 모듈이 소유한 데이터는 직접 수정하지 않는다.

예:

```text
Player 상태 변경
→ player.py 메서드 호출

Obstacle 제거
→ level_design.py 메서드 호출

Item 제거
→ item.py 메서드 호출

Score 변경
→ hud.py 메서드 호출
```

---

# 5. main Game Loop 의사코드

프로그램 시작 시 `initialize_game()`에서 각 모듈 객체를 한 번 생성한다.
`Renderer()`를 먼저 생성하여 pygame 화면과 출력 자원을 준비하고,
Player / Level / ItemManager / HUD를 생성하여 `Game`에 보관한다.
생성 직후의 상태는 `WAITING`이다. 각 생성자는 메뉴 출력에 필요한 초기 데이터를 준비한다.

메인 루프는 상태별 계산을 직접 구현하지 않고 아래 함수를 호출한다.

```text
main():
    try:
        game = initialize_game()
        clock = pygame.time.Clock()

        while True:
            dt = clock.tick(FPS) / 1000
            events = pygame.event.get()

            handle_events(game, events)가 False이면:
                루프 종료

            input_state = pygame.key.get_pressed()
            update_game(game, dt, input_state)
            render_frame(game)
    finally:
        pygame.quit()
```

pygame Event와 입력 상태는 프레임당 한 번 수집한다. 기능 모듈은 전달받은 입력을 사용한다.
종료 요청을 받은 프레임은 update / render를 수행하지 않는다.
초기화나 실행 중 예외가 발생해도 `finally`에서 pygame을 정리한다.

### main 함수별 책임

| 함수 | 책임 |
|---|---|
| `initialize_game()` | 각 모듈 객체 생성, `Game` 반환 |
| `reset_game(game)` | 게임마다 초기화할 데이터의 Reset 호출 |
| `handle_ui_action(game, action)` | HUD 요청 검증, 필요한 Reset, Game State 변경 |
| `handle_events(game, events)` | 종료 우선 처리, HUD에 Event와 현재 상태 전달, 루프 지속 여부 반환 |
| `handle_game_event(game, event)` | Collision Event에 따른 상태 변경 또는 ItemManager 호출 |
| `update_game(game, dt, input_state)` | PLAYING에서 게임 모듈 갱신, 모든 상태에서 HUD 갱신 |
| `render_frame(game)` | 현재 Game State와 각 모듈 데이터를 Renderer에 전달 |
| `main()` | 프레임 시간·입력 수집, 루프, 종료 시 정리 |

### update_game 호출 순서

```text
Game.state가 PLAYING이면:
    Level.update(dt)
    ItemManager.update(dt)
    Player.update(dt, input_state)

    Level / ItemManager에서 충돌 대상 정보 획득
    Player.check_collisions(platforms, obstacles, enemies, items)
    반환된 Event를 순서대로 handle_game_event()에 전달
    GAME_OVER를 처리하면 남은 Collision Event는 처리하지 않음

    Renderer.camera.update(Player.position)

    여전히 PLAYING이면:
        world_bounds = Renderer.get_world_bounds()
        Player.is_alive(world_bounds)가 False이면:
            Game.state = GAME_OVER

모든 상태에서:
    HUD.update(Game.state, Player)
```

`WAITING`, `SETTING`, `GAME_OVER`에서는 게임 월드와 카메라 갱신을 멈추고
HUD 갱신과 화면 출력은 계속한다. 설정 화면의 버튼 입력과 UI 상태 처리는 HUD가 담당한다.

## PLAYING 상태 한 프레임 실행 순서

```text
Input / Event
      |
      v
Level Update
      |
      v
Item Update
      |
      v
Player 이동 / 물리 Update
      |
      v
Player Collision Check
      |
      v
Collision / Item Event 처리
      |
      v
Camera Update / 보이는 월드 범위 전달
      |
      v
Player 생존 여부 / Game State 갱신
      |
      v
HUD / Score Update
      |
      v
Render
```

## Reset

```text
reset_game(game)

Level.reset()
ItemManager.reset()

Level.get_spawn_position()
        |
        v
Player.reset(spawn_position)

HUD.reset()
Renderer.reset()
```

한 게임마다 초기화되는 데이터:

```text
Player 위치 / 속도 / 상태
active_effects
Platform / Obstacle / Enemy
Item
current_score
Camera 위치
일시적인 시각 효과
```

유지되는 데이터:

```text
high_score
설정값
BGM 설정
이미 로드한 이미지
Sound
Font
```

---

# 6. 최소 Skeleton / 함수 Interface

세부 알고리즘을 구현하기 전에 다음 Interface를 공통 규칙으로 사용한다.
아래는 구현 완료 여부를 뜻하는 코드가 아니라 `main.py`와 연결하기 위한 Skeleton이다.

## `main.py`

```python
def initialize_game() -> Game: ...
def reset_game(game: Game): ...
def handle_ui_action(game: Game, action: str | None): ...
def handle_events(game: Game, events: list) -> bool: ...
def handle_game_event(game: Game, event: dict): ...
def update_game(game: Game, dt: float, input_state): ...
def render_frame(game: Game): ...
def main(): ...
```

---

## `player.py`

```python
class Player:

    def __init__(self):
        ...

    def reset(self, spawn_position):
        """
        Player 위치 / 속도 / 상태 / Effect 초기화
        """
        ...

    def update(self, dt, input_state):
        """
        입력 / 이동 / 중력 / 점프 등
        Player 물리 상태 갱신
        """
        ...

    def check_collisions(
        self,
        platforms,
        obstacles,
        enemies,
        items
    ) -> list:
        """
        Player 관련 Collision 검사

        Return:
            GAME_OVER / ITEM_COLLECTED dict 목록. Event가 없으면 []
        """
        ...

    def is_alive(self, world_bounds) -> bool:
        """사망·화면 하단 추락을 판정하고 생존 여부를 반환한다."""
        ...

    def apply_effect(
        self,
        effect,
        duration=None
    ):
        """
        Player 대상 Item Effect 적용
        """
        ...
```

---

## `level_design.py`

```python
class Level:

    def __init__(self):
        ...

    def reset(self):
        """
        Platform / Obstacle / Enemy 초기화
        """
        ...

    def update(self, dt):
        """
        Level 구조물 상태 갱신
        """
        ...

    def get_platforms(self):
        ...

    def get_obstacles(self):
        ...

    def get_enemies(self):
        ...

    def get_spawn_position(self):
        """
        Player 시작 위치 반환
        """
        ...

    def apply_effect(self, effect):
        """
        Level 대상 Item Effect 처리
        """
        ...
```

---

## `item.py`

```python
class ItemManager:

    def __init__(self):
        ...

    def reset(self):
        """
        Item 상태 초기화
        """
        ...

    def update(self, dt):
        """
        Item 상태 갱신
        """
        ...

    def get_items(self):
        """
        현재 Item 목록 반환
        """
        ...

    def collect(self, item_id, player, level):
        """
        Item 제거 후 효과 대상 Player / Level의 공개 메서드를 호출한다.
        효과 종류·지속시간·적용 대상은 ItemManager가 판단한다.
        main.py는 반환값을 사용하지 않는다.
        """
        ...
```

Item 데이터 예시:

```python
@dataclass
class Item:
    id: int | str
    position: pygame.Vector2
    size: tuple[int, int]
    type: ItemType
    effect: EffectType
    duration: float | None
```

---

## `hud.py`

```python
class HUD:

    def __init__(self):
        ...

    def reset(self):
        """
        현재 Score 및 게임 단위 UI 상태 초기화
        """
        ...

    def update(self, game_state, player):
        """
        Score / UI 상태 갱신
        """
        ...

    def handle_event(self, event, game_state) -> str | None:
        """
        버튼 입력 처리

        Return 예:
            START_GAME
            OPEN_SETTING
            RETURN_HOME
            RESTART
            요청이 없으면 None
        """
        ...

    def get_ui_data(self):
        """
        Renderer에 전달할 UI 정보 반환
        """
        ...
```

---

## `render.py`

```python
class Camera:
    def __init__(self):
        """월드 위치 position을 초기화한다."""
        ...

    def reset(self):
        ...

    def update(self, player_position):
        """플레이어를 기준으로 위쪽으로만 이동한다."""
        ...


class Background:
    def __init__(self):
        """반복 사용할 배경 이미지와 출력 자원을 준비한다."""
        ...

    def draw(self, screen, camera_position):
        """카메라 이동의 일부만 반영하여 배경을 반복 출력한다."""
        ...


class Renderer:

    def __init__(self):
        """화면·글꼴을 준비하고 camera / background 객체를 보관한다."""
        ...

    def reset(self):
        """
        Camera 등 게임 단위 Render 상태 초기화
        """
        ...

    def get_world_bounds(self) -> tuple:
        """현재 보이는 월드 범위를 (left, bottom, right, top)으로 반환한다."""
        ...

    def world_to_screen(self, position):
        """월드 위치를 카메라 위치, 배율과 y축 반전으로 화면 위치로 변환한다."""
        ...

    def draw_object(self, obj, color):
        """객체의 위치 기준점과 월드 크기를 고려하여 출력한다."""
        ...

    def draw_text(self, text, screen_position):
        """카메라와 관계없는 화면 위치에 텍스트를 출력한다."""
        ...

    def render(
        self,
        game_state,
        player,
        platforms,
        obstacles,
        enemies,
        items,
        hud
    ):
        """
        현재 게임 상태를 화면에 출력

        카메라 갱신은 main.py가 출력 전에 camera.update()로 호출한다.
        여기서는 현재 카메라 위치로 상태에 맞는 레이어를 출력한다.
        배경 → 발판/장애물/적/아이템 → 플레이어 → HUD 순서로 출력한다.
        """
        ...
```

### 카메라와 배경 구상

플레이어와 카메라의 월드 y 차이가 `CAMERA_FOLLOW_THRESHOLD`를 초과하면
목표 카메라 y를 구하고, 목표까지 남은 거리의 `1 / CAMERA_FOLLOW_DIVISOR`씩 상승한다.
목표 좌표 자체를 나누는 것이 아니라 현재 위치에서 남은 거리를 나눈다.
플레이어가 내려갈 때 카메라는 내려가지 않는다.

현재 `Camera.update(player_position)` 계약은 매 프레임 호출하는 방식이다.
FPS에 따라 추적 속도가 달라지며, `dt` 보정 여부와 강한 점프에서의 추적 지연은
구현 시 확인해야 한다.

Background는 카메라 이동량의 `BACKGROUND_SCROLL_RATIO`만큼 움직여 원근감을 표현한다.
하늘·구름 이미지를 세로로 반복해 빈 공간 없이 이어지도록 출력한다.
현재는 기본 하늘·구름 Surface를 한 번 생성하여 재사용한다. 실제 배경·스프라이트 자산은
확정 후 교체하며, 현재 게임 객체는 레이어별 색상의 사각형으로 표시한다.
글꼴은 시스템의 맑은 고딕을 사용하며 배포 시 한글 글꼴 자산을 준비해야 한다.

## `config.py`

| 상수 | 현재 값 | 의미 |
|---|---|---|
| `FPS` | `60` | 프레임 기준 |
| `SCREEN_WIDTH` / `SCREEN_HEIGHT` | `600` / `800` | 화면 픽셀 크기 |
| `SCREEN_SIZE` | `(600, 800)` | Renderer의 화면 생성에 사용 |
| `WORLD_ORIGIN` | `(0, 0)` | 월드 원점 |
| `WORLD_WIDTH` | `600` | 임시 월드 너비. 화면 너비와 별도로 조정 |
| `CAMERA_FOLLOW_THRESHOLD` | `480` | 임시 추적 기준 높이. 월드 단위 |
| `CAMERA_FOLLOW_DIVISOR` | `3` | 남은 추적 거리의 분모 |
| `BACKGROUND_SCROLL_RATIO` | `0.25` | 임시 배경 이동 비율 |

화면과 월드의 현재 너비 값이 같아도 같은 좌표계는 아니다.
월드에 화면 높이로 결정하는 하단이나 유한한 높이 상한은 정의하지 않는다.
중력·이동 속도 등 물리 상수는 해당 기능 구현 시 추가한다.

---

## 공통 개발 규칙

1. 각 모듈은 자신이 소유한 데이터만 직접 수정한다.
2. 다른 모듈의 데이터는 함수 인자 또는 반환값으로 전달한다.
3. 다른 모듈의 상태 변경이 필요한 경우 해당 모듈의 메서드를 사용한다.
4. Player 관련 Collision 판정은 `player.py`에서 담당한다.
5. Collision으로 타 모듈의 상태 변경이 필요한 경우 Event를 반환하고 `main.py`가 중재한다.
6. `level_design.py`와 `item.py`는 Player Collision에 필요한 데이터를 제공한다.
7. 모든 게임 로직은 World 좌표를 사용한다.
8. Camera 및 Screen 좌표 처리는 `render.py`에서만 수행한다.
9. Game State는 `main.py`만 변경한다.
10. 각 객체는 프로그램 시작 시 한 번 생성하고, 게임 시작 및 재시작 시 `reset()`으로 초기화한다.
11. 기능 모듈끼리의 직접 Import를 최소화하여 Circular Import를 방지한다.
12. FPS, Window Size, Gravity 등의 공통 설정값은 `config.py`에서 관리한다.
13. 화면·Camera·Background 준비는 Renderer가 담당한다. main.py는 화면을 직접 생성하지 않는다.
14. 기능 모듈은 프레임 입력을 전달받아 사용하며 pygame Event를 따로 소비하지 않는다.
15. ItemManager는 효과 대상의 공개 메서드로 상태 변경을 요청한다.
