# 발표 준비: main.py와 player.py 코드 설명

작성 기준: 2026-11-06의 로컬 소스. 코드 읽기를 바탕으로 정리했으며 게임·테스트 실행 검증은 하지 않았다.

## 1. 전체 구조

프로젝트는 Pygame 기반 세로 스크롤 자동 점프 게임이다.

| 파일 | 역할 |
|---|---|
| `main.py` | 게임 전체 상태, 모듈 생성, 호출 순서와 데이터 전달 |
| `player.py` | 플레이어 이동, 중력, 충돌, 자동 점프, 추락 판정 |
| `level_design.py` | 맵과 발판 생성·관리 |
| `item.py` | 아이템 관리. 현재 다른 모듈과 인터페이스 조정 필요 |
| `hud.py` | 점수, 메뉴 데이터, 버튼 클릭을 액션으로 변환 |
| `render.py` | 카메라, 배경, 좌표 변환, 화면 출력 |
| `config.py` | FPS, 화면 크기, 월드 크기, 카메라 설정 |

핵심 설명:

> 메인은 게임의 전체 진행을 조율하고, 플레이어는 자신의 이동과 충돌을 계산한다. 플레이어가 반환한 이벤트에 따른 게임 상태 변경과 다른 모듈 호출은 메인이 담당한다.

월드 좌표는 오른쪽이 x 양수, 위쪽이 y 양수다. 게임 객체의 `position`은 왼쪽 아래 좌표다. 화면 좌표는 아래쪽이 y 양수이므로 Renderer가 변환한다.

## 2. main.py

### 2.1 GameState: 게임 전체 상태

```python
class GameState(StrEnum):
    WAITING = "WAITING"
    SETTING = "SETTING"
    PLAYING = "PLAYING"
    GAME_OVER = "GAME_OVER"
```

| 상태 | 의미 | 게임 이동 로직 |
|---|---|---|
| `WAITING` | 대기 화면 | 정지 |
| `SETTING` | 설정 화면 | 정지 |
| `PLAYING` | 게임 진행 | 실행 |
| `GAME_OVER` | 게임 오버 화면 | 정지 |

`StrEnum`은 문자열처럼 사용할 수 있는 열거형이다. 상태 목록을 한곳에 정의해 오타를 줄이고 가능한 상태를 명확히 한다. HUD·Renderer의 문자열 비교와도 연결된다.

### 2.2 Game: 기능 객체를 묶는 데이터 클래스

```python
@dataclass
class Game:
    player: object
    level: object
    items: object
    hud: object
    renderer: object
    state: GameState = GameState.WAITING
```

`@dataclass`는 필드를 받는 생성자 등의 메서드를 자동 생성한다. 여러 객체를 개별 인자로 전달하는 대신 `game` 하나로 전달하고 `game.player`처럼 접근한다. `state`를 생략하면 `WAITING`이다.

`object`는 넓은 타입 힌트다. 실제 코드는 각 객체가 `reset()`, `update()` 등의 메서드를 제공한다는 전제에 의존한다. 타입 힌트는 실행 중 타입을 강제하지 않는다.

### 2.3 initialize_game(): 객체 최초 생성

```python
def initialize_game() -> Game:
    from player import Player
    from level_design import Level
    from item import ItemManager
    from hud import HUD
    from render import Renderer

    renderer = Renderer()
    return Game(
        player=Player(),
        level=Level(),
        items=ItemManager(),
        hud=HUD(),
        renderer=renderer,
    )
```

1. 각 모듈의 클래스를 가져온다. 함수 내부 import는 함수 호출 시 실행된다.
2. Renderer를 먼저 생성해 화면·글꼴 등 출력 환경을 준비한다.
3. Player, Level, ItemManager, HUD 객체를 생성한다.
4. 객체들을 Game에 묶어 반환한다. 초기 상태는 WAITING이다.

`-> Game`은 반환 타입 힌트이며 실제 객체 생성은 `Game(...)`에서 한다. `renderer=renderer`의 왼쪽은 Game의 필드 이름, 오른쪽은 생성한 지역 변수다. 같은 객체를 연결하며 복사하거나 새로 만들지 않는다.

메인에서의 호출:

```python
game = initialize_game()
```

발표 답변:

> 게임에 필요한 기능 객체를 최초로 생성하고 Game 데이터 클래스에 묶어 반환합니다. 이후 메인은 이 객체를 통해 각 모듈에 접근합니다.

### 2.4 reset_game(): 한 판 초기화

```python
def reset_game(game: Game):
    game.level.reset()
    game.items.reset()
    game.player.reset(game.level.get_spawn_position())
    game.hud.reset()
    game.renderer.reset()
```

기존 객체를 유지하면서 새 판의 상태를 준비한다. 맵을 먼저 초기화하고 그 맵에서 시작 좌표를 받아 플레이어를 초기화한다. 현재 HUD는 현재 점수를 초기화하고 최고 점수는 유지한다. Renderer는 카메라를 초기화한다.

중첩 호출은 안쪽부터 실행된다.

```python
spawn_position = game.level.get_spawn_position()
game.player.reset(spawn_position)
```

위 코드는 원래 한 줄과 같은 의미다. 이 함수는 상태를 PLAYING으로 바꾸지 않는다. 상태 전환은 호출하는 쪽에서 한다.

**initialize와 reset의 차이:** initialize는 객체 생성, reset은 기존 객체의 한 판 상태 초기화다.

### 2.5 handle_ui_action(): UI 액션에 따른 상태 전환

```python
def handle_ui_action(game: Game, action: str | None):
    match game.state, action:
        case (GameState.WAITING, "START_GAME") | (GameState.GAME_OVER, "RESTART"):
            reset_game(game)
            game.state = GameState.PLAYING
        case GameState.WAITING, "OPEN_SETTING":
            game.state = GameState.SETTING
        case (GameState.SETTING | GameState.GAME_OVER), "RETURN_HOME":
            game.state = GameState.WAITING
        case _, None | "START_GAME" | "RESTART" | "OPEN_SETTING" | "RETURN_HOME":
            return
        case _:
            raise ValueError(f"Unknown HUD action: {action!r}")
```

`action: str | None`은 문자열 또는 처리할 액션이 없음을 나타내는 None을 받는다는 뜻이다. `match`는 현재 상태와 액션의 조합을 검사한다. 패턴의 `|`는 여러 경우 중 하나, `_`는 어떤 값이든 일치한다는 뜻이다.

| 현재 상태 | 액션 | 결과 |
|---|---|---|
| WAITING | START_GAME | 초기화 후 PLAYING |
| GAME_OVER | RESTART | 초기화 후 PLAYING |
| WAITING | OPEN_SETTING | SETTING |
| SETTING 또는 GAME_OVER | RETURN_HOME | WAITING |

앞의 조건에 맞지 않는 알려진 액션과 None은 무시한다. 예를 들어 설정 화면의 START_GAME은 실행하지 않는다. 정의되지 않은 액션은 ValueError로 드러낸다. `!r`은 문자열 따옴표 등을 포함하는 repr 표현이다.

> 현재 상태와 액션을 함께 검사해 허용된 상태 전환만 수행합니다. HUD는 클릭한 버튼을 판단하고, 실제 게임 상태는 메인이 변경합니다.

### 2.6 handle_events(): Pygame 이벤트 처리

```python
def handle_events(game: Game, events: list) -> bool:
    if any(event.type == pygame.QUIT for event in events):
        return False

    for event in events:
        action = game.hud.handle_event(event, game.state)
        handle_ui_action(game, action)
    return True
```

`any()`로 창 닫기 이벤트가 하나라도 있는지 확인한다. 있으면 다른 이벤트보다 우선하여 False를 반환한다. 없으면 각 이벤트를 HUD에 전달하고 반환된 액션을 처리한다.

```text
마우스 클릭 → HUD의 버튼 영역 검사 → START_GAME 등 반환 → 상태 전환
```

반환값은 **게임 오버 여부가 아닌 프로그램 실행 지속 여부**다. True면 계속 실행하고 False면 메인 루프를 끝낸다.

### 2.7 handle_game_event(): 게임 로직이 만든 이벤트 처리

```python
def handle_game_event(game: Game, event: dict):
    match event["type"]:
        case "GAME_OVER":
            game.state = GameState.GAME_OVER
        case "ITEM_COLLECTED":
            game.items.collect(event["item_id"], game.player, game.level)
        case _:
            raise ValueError(f"Unknown game event: {event!r}")
```

입력 이벤트와 구분해야 한다.

| 종류 | 예시 | 발생 주체 |
|---|---|---|
| Pygame 이벤트 | 클릭, 창 닫기 | 사용자·운영체제 |
| 게임 이벤트 | GAME_OVER, ITEM_COLLECTED | 플레이어 충돌 로직 |

`{"type": "GAME_OVER"}`는 게임 상태만 바꾼다. 프로그램을 종료하지 않아 재시작 버튼을 처리할 수 있다.

`{"type": "ITEM_COLLECTED", "item_id": 7}`은 아이템 ID, 플레이어, 맵을 ItemManager에 전달한다. 아이템 제거·효과는 그 모듈이 담당하도록 설계되어 있다. 현재 구현과의 불일치는 마지막 주의사항을 참조한다.

### 2.8 update_game(): 프레임의 게임 로직 조율

```python
def update_game(game: Game, dt: float, input_state):
    if game.state == GameState.PLAYING:
        game.level.update(dt, game.player.position.y)
        game.items.update(dt)
        game.player.update(dt, input_state)

        collision_events = game.player.check_collisions(
            game.level.get_platforms(),
            game.level.get_obstacles(),
            game.level.get_enemies(),
            game.items.get_items(),
        )
        for event in collision_events:
            handle_game_event(game, event)
            if game.state == GameState.GAME_OVER:
                break

        game.renderer.camera.update(game.player.position, dt)
        if game.state == GameState.PLAYING:
            world_bounds = game.renderer.get_world_bounds()
            if not game.player.is_alive(world_bounds):
                game.state = GameState.GAME_OVER

    game.hud.update(game.state, game.player)
```

処理 순서:

1. PLAYING일 때만 맵·아이템·플레이어를 갱신한다. 맵에 전달하는 높이는 이번 프레임 플레이어 이동 전 높이다.
2. 각 목록을 Player에 전달해 이동 중 충돌을 검사하고 최종 이동을 확정한다.
3. 반환된 이벤트를 처리한다. 게임 오버면 이벤트 반복문만 중단한다.
4. 최종 플레이어 위치로 카메라를 갱신한다. 충돌로 게임 오버가 된 그 프레임에도 이 줄은 실행된다.
5. 아직 PLAYING이면 갱신된 카메라의 월드 범위를 받아 추락을 검사한다.
6. 모든 상태에서 HUD를 갱신한다. 마지막 줄은 PLAYING 조건 밖에 있다.

카메라 갱신 뒤 생존을 검사하는 이유는 현재 스크롤된 화면 하단을 기준으로 추락을 판단하기 위해서다.

### 2.9 render_frame(): 출력 데이터 전달

```python
def render_frame(game: Game):
    game.renderer.render(
        game_state=game.state,
        player=game.player,
        platforms=game.level.get_platforms(),
        obstacles=game.level.get_obstacles(),
        enemies=game.level.get_enemies(),
        items=game.items.get_items(),
        hud=game.hud,
    )
```

메인은 상태와 객체를 전달하고 Renderer가 좌표 변환·그리기를 한다. `player=game.player`의 왼쪽은 인자 이름, 오른쪽은 실제 객체다. 모든 상태에서 호출되므로 대기·게임 오버 화면도 계속 출력된다.

### 2.10 main(): 전체 프로그램 루프

```python
def main():
    try:
        game = initialize_game()
        clock = pygame.time.Clock()

        while True:
            dt = clock.tick(FPS) / 1000
            events = pygame.event.get()
            if not handle_events(game, events):
                break

            input_state = pygame.key.get_pressed()
            update_game(game, dt, input_state)
            render_frame(game)
    finally:
        pygame.quit()
```

객체 생성과 Clock 생성은 루프 밖에서 한 번 실행한다. 루프 안은 매 프레임 다음 순서로 반복한다.

```text
시간 계산 → 이벤트 처리 → 현재 키 읽기 → 게임 갱신 → 화면 출력
```

- `clock.tick(FPS)`: 목표 FPS에 맞춰 필요한 대기를 하고 경과 밀리초를 반환한다. 정확히 60FPS가 보장되는 것은 아니다.
- `/ 1000`: 밀리초를 초로 변환한다.
- `pygame.event.get()`: 대기 중인 이벤트들을 가져온다.
- `if not handle_events(...)`: False면 while을 종료한다. 종료 프레임에는 이후 갱신·출력을 하지 않는다.
- `pygame.key.get_pressed()`: 현재 눌린 키를 읽는다. 계속 누르는 이동에 적합하다.
- `finally`: 정상 종료나 예외 발생 모두 Pygame 자원을 정리한다. 예외를 없애는 구문은 아니다.

```python
if __name__ == "__main__":
    main()
```

직접 실행할 때만 main을 호출한다. 테스트에서 `import main`으로 가져오면 게임 루프는 자동 실행하지 않는다.

### 2.11 실제 상태별 루프 동작

```text
최초 실행
  → initialize_game → WAITING → 반복 시작

WAITING 프레임
  → 입력 처리 → 게임 이동 생략 → HUD 갱신 → 대기 화면 출력

시작 클릭 프레임
  → HUD가 START_GAME 반환 → reset_game → PLAYING
  → 같은 프레임에 이동·충돌 계산 → 게임 화면 출력

게임 오버 프레임
  → 충돌 또는 추락 → GAME_OVER → HUD 갱신 → 종료 화면 출력
  → 이후에도 루프는 유지하지만 이동·충돌 갱신은 생략

재시작 클릭
  → 같은 루프 안에서 reset_game → PLAYING

창 닫기
  → QUIT → handle_events가 False → while의 break → pygame.quit
```

게임 오버는 루프 종료가 아니다. 이벤트 반복문의 break와 메인 while의 break는 각각 가장 가까운 반복문만 끝낸다.

## 3. player.py

### 3.1 상태와 좌표

```python
class PlayerState(StrEnum):
    JUMPING = "JUMPING"
    FALLING = "FALLING"
```

GameState가 게임 전체 상태라면 PlayerState는 플레이어의 상승·하강 상태다. 세로 속도가 양수면 상승, 0 이하이면 하강 상태로 분류한다.

### 3.2 __init__(): 기본 데이터 준비

```python
def __init__(self):
    self.position = pygame.Vector2(0, 0)
    self.velocity = pygame.Vector2(0, 0)
    self.size = (40, 40)
    self.state = PlayerState.FALLING

    self.move_speed = 400
    self.jump_speed = 800
    self.gravity = 1500
    self.previous_bottom = 0
    self._pending_motion = None
```

`Player()` 생성 시 실행된다. `self`는 그 플레이어 객체 자신이다.

| 필드 | 의미 |
|---|---|
| position | 왼쪽 아래의 월드 좌표. Vector2라 소수점 유지 가능 |
| velocity | x·y 방향 속도, 월드 단위/초 |
| size | 가로·세로 40 |
| move_speed | 가로 속도 400 |
| jump_speed | 점프 시작 속도 800 |
| gravity | 아래 방향 가속도 크기 1500 |
| previous_bottom | 직전 이동 전 발 높이 |
| _pending_motion | 충돌 재계산에 사용할 이동 전 위치·속도·시간 |

### 3.3 reset(): 새 판 시작

```python
def reset(self, spawn_position):
    self.position = pygame.Vector2(spawn_position)
    self.velocity = pygame.Vector2(0, self.jump_speed)
    self.previous_bottom = self.position.y
    self.state = PlayerState.JUMPING
    self._pending_motion = None
```

맵이 제공한 위치로 이동하고 가로 속도 0, 세로 속도 +800으로 설정한다. 자동 점프 게임이므로 시작부터 상승한다. 이전 발 위치와 저장된 이동도 초기화한다.

### 3.4 update(): 입력과 이동 준비

```python
def update(self, dt, input_state):
    if not isfinite(dt) or dt < 0:
        raise ValueError("dt must be finite and non-negative")

    self.velocity.x = 0
    if input_state[pygame.K_LEFT] or input_state[pygame.K_a]:
        self.velocity.x -= self.move_speed
    if input_state[pygame.K_RIGHT] or input_state[pygame.K_d]:
        self.velocity.x += self.move_speed

    self._pending_motion = (self.position.copy(), self.velocity.copy(), dt)
    self._move(dt)
```

1. 음수, 무한대, NaN 시간을 거부한다. 0은 허용한다.
2. 가로 속도를 0으로 초기화하고 입력으로 결정한다. 키를 놓으면 즉시 정지하며 관성은 없다.
3. 왼쪽은 -400, 오른쪽은 +400, 양쪽은 상쇄되어 0이다. 방향키와 A/D를 or로 묶어 같은 방향의 두 키를 눌러도 두 배가 되지 않는다.
4. 이동 전 위치·속도·시간을 복사해 저장한다. Vector2는 수정 가능한 객체라 `.copy()`가 필요하다.
5. 전체 dt로 일단 이동한다. 다음 충돌 검사에서 저장된 시작 상태로 복원해 재계산한다.

### 3.5 _move(): 운동과 경계 계산

```python
def _move(self, dt):
    self.previous_bottom = self.position.y
    self.position.x += self.velocity.x * dt
    self.position.x = max(
        WORLD_ORIGIN[0],
        min(self.position.x, WORLD_ORIGIN[0] + WORLD_WIDTH - self.size[0]),
    )
    self.position.y += self.velocity.y * dt - self.gravity * dt * dt / 2
    self.velocity.y -= self.gravity * dt

    if self.velocity.y > 0:
        self.state = PlayerState.JUMPING
    else:
        self.state = PlayerState.FALLING
```

앞의 `_`는 내부용 메서드라는 관례이며 외부 호출을 강제로 막지는 않는다.

가로는 거리 = 속도 × 시간이다. 월드 시작 x=0, 폭=600, 플레이어 폭=40이므로 x를 0~560으로 제한한다. 오른쪽 몸 전체가 남아야 하므로 플레이어 폭을 뺀다.

세로는 등가속도 운동 공식을 사용한다.

```text
새 위치 = 기존 위치 + 초기 속도×시간 − ½×중력×시간²
새 속도 = 기존 속도 − 중력×시간
```

높이 100, 위쪽 속도 800, dt=0.1이면 새 높이는 172.5, 새 속도는 650이다. 위치에 구간 초기 속도를 사용한 후 구간 끝 속도를 계산한다.

충돌 없는 점프의 이론값:

```text
최고점까지 시간 = 800 / 1500 ≈ 0.533초
상승 높이 = 800² / (2×1500) ≈ 213.3 월드 단위
```

### 3.6 check_collisions(): 이동 시간을 나눠 검사

```python
def check_collisions(self, platforms, obstacles, enemies, items):
    if self._pending_motion is None:
        return self._check_collisions(platforms, obstacles, enemies, items)

    position, velocity, remaining = self._pending_motion
    self._pending_motion = None
    self.position.update(position)
    self.velocity.update(velocity)
    if remaining == 0:
        self._move(0)
        return self._check_collisions(platforms, obstacles, enemies, items)
    events = []
    while remaining > 0:
        step = min(remaining, 1 / 120)
        self._move(step)
        for event in self._check_collisions(platforms, obstacles, enemies, items):
            if event["type"] == "GAME_OVER":
                return [event]
            if event not in events:
                events.append(event)
        remaining -= step
    return events
```

처리 순서:

1. 저장한 이동이 없으면 현재 위치에서 충돌만 검사한다.
2. 저장한 시작 위치·속도·시간을 꺼내 시작 상태로 복원한다.
3. 저장 데이터를 None으로 비워 같은 이동을 다시 사용하지 않게 한다.
4. 시간이 0이어도 현재 접촉을 한 번 검사한다.
5. 최대 1/120초씩 이동하고 매번 실제 충돌을 판정한다.
6. 아이템 이벤트는 중복을 제거한다. 사망하면 즉시 사망 이벤트만 반환한다.

`self.position.update(position)`은 Vector2의 값을 덮어쓰는 메서드로 Player의 update와 다르다.

### 3.7 _check_collisions(): 실제 판정 조건

`check_collisions()`는 언제 몇 번 검사할지를, `_check_collisions()`는 무엇을 충돌로 판단할지를 담당한다.

위험 물체 검사:

```python
for objects in (obstacles, enemies):
    for obj in objects:
        if self._overlaps(obj):
            return [{"type": "GAME_OVER"}]
```

장애물·적과 겹치면 상승·하강과 관계없이 즉시 사망 이벤트를 반환한다.

아이템 검사:

```python
events = [
    {"type": "ITEM_COLLECTED", "item_id": item.id}
    for item in items if self._overlaps(item)
]
```

아이템을 직접 제거하지 않고 ID 이벤트를 반환한다. 이는 ItemManager와 데이터 형식이 맞는다는 전제다.

발판 검사:

```python
if self.velocity.y >= 0:
    return events
```

상승 중에는 발판을 통과하고 하강 중에만 착지한다. 위험 물체·아이템 검사는 이 조건 앞에 있어 상승 중에도 처리된다.

```python
player_left = self.position.x
player_right = self.position.x + self.size[0]
current_bottom = self.position.y

landing_top = None
for platform in platforms:
    platform_left = platform.position.x
    platform_right = platform.position.x + platform.size[0]
    platform_top = platform.position.y + platform.size[1]

    if (
        player_right > platform_left
        and player_left < platform_right
        and self.previous_bottom >= platform_top >= current_bottom
    ):
        if landing_top is None or platform_top > landing_top:
            landing_top = platform_top

if landing_top is not None:
    self.position.y = landing_top
    self.velocity.y = self.jump_speed
    self.state = PlayerState.JUMPING

return events
```

가로로 겹치면서 이전 발 높이와 현재 발 높이 사이에 발판 윗면이 있어야 착지 후보다.

```text
이전 발 높이 110
발판 윗면   100
현재 발 높이 90

110 >= 100 >= 90 → 이번 이동에서 윗면을 통과
```

세분화 중 previous_bottom은 각 작은 이동 직전 높이다. 여러 후보 중 가장 높은 윗면을 선택해 목록 순서에 영향을 받지 않게 한다.

`landing_top`은 착지 높이 선택과 위치 보정에 필요하다. 속도만 바꾸면 발판 아래로 내려간 위치에서 점프할 수 있다. `is not None`은 높이 0인 발판도 유효하게 처리한다.

### 3.8 _overlaps(): AABB 사각형 겹침 검사

```python
def _overlaps(self, obj):
    return (
        self.position.x < obj.position.x + obj.size[0]
        and self.position.x + self.size[0] > obj.position.x
        and self.position.y < obj.position.y + obj.size[1]
        and self.position.y + self.size[1] > obj.position.y
    )
```

회전하지 않는 사각형의 가로 구간과 세로 구간이 모두 겹치는지 검사한다.

```text
플레이어 왼쪽 < 상대 오른쪽
플레이어 오른쪽 > 상대 왼쪽
플레이어 아래 < 상대 위
플레이어 위 > 상대 아래
```

엄격한 부등호를 사용하므로 경계만 닿으면 겹침으로 보지 않는다. 소수점 월드 좌표를 그대로 비교해 정수 Rect 변환에 따른 정밀도 손실을 피한다. 발판은 옆·아래 접촉과 착지를 구분해야 하므로 별도의 통과 조건을 사용한다.

### 3.9 is_alive(): 화면 아래 추락 판정

```python
def is_alive(self, world_bounds):
    _, bottom, _, _ = world_bounds
    return self.position.y + self.size[1] > bottom
```

world_bounds는 `(left, bottom, right, top)`이다. bottom만 사용하고 나머지는 `_`로 받는다. 플레이어 윗면이 현재 화면 하단보다 높으면 일부라도 보이는 상태이므로 생존한다. 윗면까지 하단에 도달하면 추락이다.

| 화면 하단 | 플레이어 아래 | 플레이어 위 | 생존 |
|---:|---:|---:|---|
| 500 | 470 | 510 | True |
| 500 | 460 | 500 | False |
| 500 | 450 | 490 | False |

고정 y=0 대신 현재 카메라 하단을 사용한다. 적·장애물 사망은 충돌 이벤트가 담당하고 이 함수는 추락만 검사한다.

## 4. remaining과 dt: 자세한 설명

### 4.1 변수의 의미

| 변수 | 의미 |
|---|---|
| dt | 이번 프레임 전체 시간 |
| remaining | 전체 시간 중 아직 계산하지 않은 시간 |
| step | 이번 반복에서 계산할 시간, 최대 1/120초 |

`update()`에서 저장한 dt가 처음 remaining이 된다. 화면 프레임을 더 만드는 것이 아니라 한 화면 프레임 안의 이동·충돌 계산을 나눈다. 실제로 기다리는 sleep 동작도 아니다.

### 4.2 dt=0.02초 예시

| 반복 | 계산 전 remaining | step | 계산 후 remaining |
|---|---:|---:|---:|
| 1 | 0.020000 | 약 0.008333 | 약 0.011667 |
| 2 | 약 0.011667 | 약 0.008333 | 약 0.003333 |
| 3 | 약 0.003333 | 남은 약 0.003333 | 0 |

표의 값은 반올림했다. 각 step의 합은 원래 dt다. 마지막에 `min(remaining, 1/120)`으로 남은 시간만 사용해 과도한 이동을 막는다.

```text
시작 상태로 복원
 → step 이동 → 충돌 검사 → remaining에서 step 차감
 → 반복
 → 시간 소진 → 최종 위치 출력
```

### 4.3 왜 두 번 이동하는 것처럼 보이는가?

```text
update: 전체 dt로 일단 계산
check_collisions: 시작 상태로 복원한 뒤 같은 dt를 나누어 재계산
```

두 배로 이동하지 않는다. 처음 결과를 충돌이 반영된 결과로 대체한다. 다만 실제 계산 중복은 존재한다.

### 4.4 착지 후 남은 시간 반영의 의미

첫 구간에서 착지하면 세로 속도가 +800으로 바뀐다. 이후 구간은 새 속도로 상승한다.

```text
첫 구간: 하강 → 착지 → 발 높이 보정 → 속도 +800
다음 구간: 위로 이동 → 충돌 검사
마지막 구간: 계속 상승 → 충돌 검사
계산 완료 후 화면 한 번 출력
```

착지했다고 프레임의 나머지 시간을 버리지 않는다는 뜻이다. 다만 작은 구간 내부의 정확한 충돌 시각까지 계산하지는 않는다.

### 4.5 사망과 시간 0

- 사망 이벤트를 만나면 즉시 반환하여 남은 시간 계산을 중단한다. 이전에 모은 아이템 이벤트도 반환하지 않는다.
- dt=0이어도 현재 겹침을 검사하기 위해 별도 분기가 있다.
- 충돌 없는 자유 운동은 현재 등가속도 공식상 전체 dt 계산과 분할 계산이 수학적으로 같다. 부동소수점 오차는 있을 수 있다.

### 4.6 정상 프레임에서도 완전히 통과할 수 있는가?

현재 속도와 보통 크기의 물체, 정상 60FPS에서는 가능성이 낮다.

```text
dt ≈ 1/60초
가로 이동량 ≈ 400/60 = 6.7
점프 시작 직후 세로 이동량 ≈ 13.1
플레이어 크기 = 40×40
```

세로로 겹치는 상태에서 가로 폭 32인 아이템을 한쪽에서 반대쪽으로 완전히 통과하려면 플레이어 폭 40 + 아이템 폭 32보다 크게 이동해야 한다. 정상 가로 이동량 6.7은 이에 비해 작다.

하지만 프레임 지연으로 dt=0.2초가 되면 가로 이동량은 80이므로 통과할 수 있다. FPS는 목표값이며 지연 시 실제 dt가 커진다. 하강 속도 상한도 없어 장시간 낙하하면 이동량이 커질 수 있다.

발판은 이미 이전·현재 발 위치 사이의 통과를 검사하므로 단순 하강 중 통과를 상당 부분 처리한다. 분할 계산은 긴 프레임 내 상승→하강, 착지 후 움직임도 처리하는 데 도움이 된다.

### 4.7 한계와 비용

- 최대 1/120초 간격 검사도 근사 방식이다. 매우 빠른 이동이나 얇은 물체의 모든 충돌을 보장하지 않는다.
- 프레임 시간이 길수록 반복 횟수가 늘어난다. remaining을 사용한다고 작업량 제한이 생기는 것은 아니다.
- Player만 작은 구간으로 다시 계산한다. 맵·아이템 등의 운동을 함께 같은 시간 간격으로 시뮬레이션하는 구조는 아니다.
- 아이템 이벤트는 계산이 끝나 메인에 반환된 뒤 처리된다. 착지 속도는 Player 내부에서 즉시 바뀌지만 아이템 효과는 같은 방식으로 중간 적용되지 않는다.

## 5. 발표 예상 질문과 답변

### Q. 왜 main과 player를 분리했나요?

> 메인은 전체 상태와 호출 순서를 관리하고, 플레이어는 이동·충돌 계산에 집중하도록 책임을 분리했습니다. 다른 모듈에 영향을 주는 충돌 결과는 이벤트로 반환합니다.

### Q. 60FPS인데 왜 dt가 필요한가요?

> 60FPS는 목표값이고 실제 프레임 시간은 달라질 수 있습니다. 속도에 실제 경과 시간을 곱해 시간 기준으로 움직이도록 합니다.

### Q. 충돌 함수가 두 개인 이유는?

> check_collisions는 이동 시간을 나눠 검사를 반복하는 흐름을 담당하고, _check_collisions는 현재 위치의 실제 충돌 조건을 담당합니다.

### Q. remaining은 무엇인가요?

> 한 프레임의 dt 중 아직 이동·충돌 계산을 하지 않은 시간입니다. 최대 1/120초를 step으로 사용하고, 계산한 만큼 차감합니다.

### Q. 정해진 속도와 물체 크기가 있는데 한 프레임에 지나칠 수 있나요?

> 정상 프레임에서는 이동량이 작아 문제가 적지만, 프레임 지연으로 dt가 커지면 한 번에 많이 이동해 중간 충돌을 놓칠 수 있습니다. 그래서 dt를 최대 1/120초씩 나누어 이동과 충돌을 검사하고 remaining으로 남은 시간을 관리합니다. 모든 충돌을 완전히 방지한다기보다 누락 가능성을 줄이는 방식입니다.

### Q. 이미 이동한 뒤 재계산하면 두 배 이동 아닌가요?

> 저장한 이동 전 위치와 속도로 복원한 후 같은 시간을 다시 계산하므로 두 배로 이동하지 않습니다. 처음 결과를 충돌 반영 결과로 대체합니다.

### Q. previous_bottom >= platform_top >= current_bottom은 가능한가요?

> 위쪽이 양수이므로 하강 중에는 현재 발 높이가 이전보다 작아집니다. 예를 들어 110에서 90으로 내려가면서 높이 100의 발판 윗면을 통과하면 조건이 성립합니다.

### Q. landing_top과 위치 보정이 필요한 이유는?

> 통과한 발판 중 가장 높은 윗면을 선택하고 발을 그 높이에 맞추기 위해서입니다. 속도만 바꾸면 발판 아래로 내려간 위치에서 점프할 수 있습니다.

### Q. 발판과 위험 물체의 충돌 검사가 다른 이유는?

> 위험 물체는 몸이 겹치면 충돌이지만, 발판은 아래에서 통과하고 하강할 때 윗면에만 착지해야 하므로 하강·윗면 통과 조건을 별도로 사용합니다.

### Q. 왜 landing_top is not None인가요?

> 높이 0도 유효한 착지 지점입니다. None은 후보 없음이고 숫자 0과 구분해야 합니다.

### Q. 왜 좌표를 copy하나요?

> Vector2는 수정 가능한 객체라 원본을 그대로 보관하면 이동 중 저장 값도 바뀔 수 있습니다. 이동 전 값을 유지하기 위해 복사합니다.

### Q. 게임 오버인데 왜 while이 계속 도나요?

> 종료 화면 출력과 재시작 입력을 처리해야 하기 때문입니다. GAME_OVER에서는 이동 갱신을 생략하고 입력·HUD·출력은 계속 수행합니다.

### Q. 발만 화면 밖으로 나가면 죽나요?

> 아닙니다. 플레이어 윗면까지 현재 화면 하단에 도달했을 때, 즉 몸 전체가 벗어났을 때 추락으로 판단합니다.

## 6. 다른 파일 관련 대화 요약

- 배경 모양 생성과 출력은 render.py의 Background가 담당한다. 하늘색 바탕과 구름을 만들고 반복해서 출력한다.
- 배경 스크롤 비율은 config.py의 BACKGROUND_SCROLL_RATIO로 설정하며, 카메라 이동량의 25%를 반영한다.
- 배경 담당 팀원은 코드 구조만으로 확정할 수 없다.
- 이전 대화의 빈 item.py, 미구현 추락 판정, 예전 속도 등의 설명은 당시 상태다. 이 문서는 현재 코드의 속도 400/800, 구현된 추락 판정을 기준으로 한다.

## 7. 현재 연동 상태와 확인 범위

현재 item.py에는 ItemManager가 있지만 인터페이스가 맞지 않는 부분이 있다.

| main/player의 기대 | 현재 item.py |
|---|---|
| items.update(dt) | update(player_rect) |
| items.collect(item_id, player, level) | collect 없음 |
| 아이템 position, size, id | rect, image 보유 |

빈 목록에서는 일부 문제가 드러나지 않지만 아이템을 추가하면 호출·데이터 불일치가 드러날 수 있다. 발표에서는 이벤트 방식의 호출 계약과 실제 통합 완료 여부를 구분해 설명해야 한다.

HUD에 PAUSED 관련 데이터가 있어도 현재 main에는 PAUSED 상태와 전환 처리가 없다. 일시정지 기능이 메인에 연결된 상태로 설명하면 안 된다.

이 문서는 코드 설명과 발표 준비용이다. 게임 실행, 자동 테스트 통과 여부를 확인한 결과는 아니다.

## 8. 발표용 설명 예시

> 제가 담당한 main.py는 게임 상태와 전체 실행 순서를 관리합니다. 매 프레임 경과 시간을 계산하고 입력을 처리한 뒤, 진행 상태일 때 맵과 플레이어를 갱신합니다. 충돌 이벤트를 처리하고 카메라와 HUD를 갱신한 후 렌더러에 출력을 요청합니다. 게임 오버가 되어도 루프를 유지해 재시작 입력을 받을 수 있습니다.
>
> player.py는 입력 기반 좌우 이동과 중력에 따른 세로 운동을 계산합니다. 프레임 지연 시 충돌을 놓칠 가능성을 줄이기 위해 dt를 최대 1/120초씩 나누고 remaining으로 남은 시간을 관리합니다. 발판에 착지하면 위치를 보정하고 점프 속도를 설정하며, 위험 물체와 아이템 충돌은 이벤트로 메인에 전달합니다. 화면 아래로 몸 전체가 벗어나면 추락으로 판단합니다.
