# Jump OverFlow — 최종 구조 설계

## 1. 모듈 관계도
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
                    렌더링 / 레이어 / 카메라
                               |
                               v
                             Screen
### 기본 원칙

- `main.py`는 각 모듈의 실행 순서와 연결을 담당한다.
- `level_design.py`는 Player Collision에 필요한 구조물 정보를 제공한다.
- `item.py`는 Player Collision 및 효과 적용에 필요한 Item 정보를 제공한다.
- `player.py`는 Player와 관련된 Collision 판정을 담당한다.
- `render.py`는 각 모듈의 상태를 읽고 화면에 출력한다.
- 한 모듈이 다른 모듈의 내부 데이터를 직접 수정하지 않는다.

---

# 2. 모듈별 책임 정리

| 모듈 | 주요 책임 | 담당하지 않는 것 |
|---|---|---|
| `main.py` | 전체 게임 실행, Game State 관리, 각 모듈 호출, 모듈 간 데이터 전달 및 Event 중재 | 물리 계산, Collision 알고리즘, 렌더링 |
| `player.py` | Player 입력, 이동, 중력, 점프, 물리 처리, Player Collision, Item Effect 적용 | 발판/아이템 생성, Camera 처리 |
| `level_design.py` | Platform, Obstacle, Enemy 생성 및 관리, 구조물 정보 제공 | Player 상태 직접 수정, 렌더링 |
| `item.py` | Item 생성 및 관리, ItemType / EffectType 정의, 획득 효과 정보 제공 | Player / Level 내부 상태 직접 수정 |
| `hud.py` | 현재 점수, 최고 점수, Waiting / Setting / Playing / Game Over UI 상태 관리 | Game State 직접 변경, Player 상태 직접 변경 |
| `render.py` | Background / Map / Player / Item / HUD 렌더링, Layer 관리, Camera Following, World → Screen 좌표 변환 | 물리, Collision, 점수 계산 |
| `config.py` | FPS, Window Size, Gravity, Player Speed 등 공통 설정값 관리 | 실행 로직 |

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
| `game_state` | `GameState(Enum)` | `main.py` |

---

## 좌표 공통 규칙

모든 게임 로직에서는 World 좌표만 사용한다.

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

---

# 4. 모듈별 Input / Output 표

| 모듈 | Input | Output |
|---|---|---|
| `main.py` | pygame Event, 각 모듈의 반환값 | Game State 변경, 각 모듈 호출 및 데이터 전달 |
| `player.py` | `dt`, 사용자 입력, Platform / Obstacle / Enemy / Item 정보 | Player 상태, Collision Event |
| `level_design.py` | `dt`, Level 관련 요청 | Platform / Obstacle / Enemy 정보 |
| `item.py` | `dt`, Item 획득/제거 요청 | Item 정보, EffectType, duration |
| `hud.py` | Game State, Player/Game 정보, UI Event | Score/UI 정보, 버튼 Action |
| `render.py` | Player, Level, Item, HUD 정보 | 화면 출력 |

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

Item 획득이 확인되면 Item 제거 및 실제 Effect 전달은 `main.py`가 중재한다.

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

```text
current_score
high_score
menu state
button state
```

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

프로그램 시작 시 각 모듈 객체를 메인 루프 진입 전에 한 번 생성한다.

```text
pygame 초기화

Player 생성
Level 생성
ItemManager 생성
HUD 생성
Renderer 생성

GameState = WAITING
```

메인 루프:

```text
while 프로그램 실행 중:

    pygame Event 수집

    종료 Event 확인


    if GameState == WAITING:

        HUD Waiting UI 처리

        START_GAME 요청이 발생하면:
            reset_game()
            GameState = PLAYING

        OPEN_SETTING 요청이 발생하면:
            GameState = SETTING

        Render


    elif GameState == SETTING:

        HUD Setting UI 처리

        설정값 변경 처리

        RETURN_HOME 요청이 발생하면:
            GameState = WAITING

        Render


    elif GameState == PLAYING:

        dt 계산

        사용자 입력 확인

        Level.update(dt)

        ItemManager.update(dt)

        Player.update(dt, input_state)

        Level에서
            Platform 정보 획득
            Obstacle 정보 획득
            Enemy 정보 획득

        ItemManager에서
            Item 정보 획득

        Player.check_collisions(
            platforms,
            obstacles,
            enemies,
            items
        )

        발생한 Collision Event 처리

        Item 획득 Event가 발생한 경우:
            ItemManager.collect(item_id)

            Player 대상 Effect:
                Player.apply_effect()

            Level 대상 Effect:
                Level.apply_effect()

        HUD.update(...)

        Game Over 조건 확인

        Game Over이면:
            GameState = GAME_OVER

        Renderer.render(...)


    elif GameState == GAME_OVER:

        HUD Game Over UI 처리

        RETURN_HOME 요청:
            GameState = WAITING

        RESTART 요청:
            reset_game()
            GameState = PLAYING

        Render
```

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
HUD / Score Update
      |
      v
Render
```

## Reset

```text
reset_game()

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

## `main.py`

```python
def reset_game():
    """새 게임 시작을 위해 각 모듈의 상태를 초기화"""
    ...


def handle_game_event(event):
    """각 모듈에서 발생한 Event를 처리"""
    ...


def main():
    """게임 실행 및 Game State 관리"""
    ...
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
            발생한 Event 목록
        """
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

    def collect(self, item_id):
        """
        Item 제거 후 Effect 정보 반환

        Return:
            effect
            duration
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

    def handle_event(self, event):
        """
        버튼 입력 처리

        Return 예:
            START_GAME
            OPEN_SETTING
            RETURN_HOME
            RESTART
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
class Renderer:

    def __init__(self, screen):
        ...

    def reset(self):
        """
        Camera 등 게임 단위 Render 상태 초기화
        """
        ...

    def render(
        self,
        player,
        platforms,
        obstacles,
        enemies,
        items,
        hud
    ):
        """
        현재 게임 상태를 화면에 출력

        - World → Screen 좌표 변환
        - Camera Following
        - Layer 순서에 따른 Rendering
        """
        ...
```

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
