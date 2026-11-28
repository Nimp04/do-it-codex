"""발판·장애물·아이템 배치를 생성하고 관리하는 모듈.

월드 좌표는 x가 오른쪽, y가 위쪽으로 증가하며 모든 position은 좌측 하단 좌표이다.
점수 1점 = 한 행(ROW_GAP)이다.

장애물 배치 규칙 (피할 수 없는 패턴이 나오지 않게 한다)
1. 어떤 발판이든 방향키 없이 제자리로 뛰기만 하면 장애물에 닿지 않는다.
   - 고정 발판 위 수직 통로에는 장애물을 두지 않는다.
   - 장애물 아래의 움직이는 발판은 장애물 반대쪽에서만 왕복하게 범위를 줄인다.
2. 장애물끼리 OBSTACLE_CLEAR_ROWS행 이상 띄워, 장애물을 넘어가는 점프 경로에는
   다른 장애물이 없게 한다.
"""

from collections import deque
from dataclasses import dataclass
import random

import pygame

from config import PLAYER_SIZE, WORLD_ORIGIN, WORLD_WIDTH
from item import DOUBLE_JUMP, GHOST, SHRINK, ITEM_SIZE, Item


# 발판
PLATFORM_WIDTH = 100
PLATFORM_HEIGHT = 15
PLATFORM_MIN_X = WORLD_ORIGIN[0]
PLATFORM_MAX_X = WORLD_ORIGIN[0] + WORLD_WIDTH - PLATFORM_WIDTH

# 행 배치
START_Y = 750  # 시작 발판 높이
ROW_GAP = 100  # 행 사이 간격
INITIAL_ROWS = 10  # reset 때 미리 생성할 행 수
GENERATE_AHEAD = 1200  # 플레이어보다 이만큼 위까지 미리 생성한다.
CLEANUP_BELOW = 1200  # 플레이어보다 이만큼 아래는 삭제한다.

# 행마다 생성할 발판 개수와 가중치
PLATFORM_RULES = [(1, 0.8), (2, 0.2)]

# 난이도는 시작 높이에서 MOVING_MAX_SPEED_SCORE점 높이까지 직선으로 오르고 그 뒤로 유지된다.
MOVING_MAX_SPEED_SCORE = 300

# 발판 하나가 움직이는 발판일 확률 (반반 → 8:2)
MOVING_PLATFORM_CHANCE_START = 0.5
MOVING_PLATFORM_CHANCE_END = 0.8

# 고정 발판 중 스프링 발판의 비율 (일반:스프링 = 7:3)
SPRING_PLATFORM_CHANCE = 0.3

# 움직이는 발판 속도 (초당 월드 단위). 한 행마다 0.8씩 빨라져 느린 발판은 300점,
# 빠른 발판(1.5배, 절반 확률)은 175점에서 최고 속도에 닿는다.
MOVING_BASE_SPEED = 60
MOVING_MAX_SPEED = 300
MOVING_SPEED_PER_HEIGHT = (
    (MOVING_MAX_SPEED - MOVING_BASE_SPEED) / (MOVING_MAX_SPEED_SCORE * ROW_GAP)
)
FAST_PLATFORM_CHANCE = 0.5
FAST_SPEED_MULTIPLIER = 1.5

# 장애물. 두 행 사이 가운데에 생기고, 한 층에 최대 하나다.
# 간격 규칙 때문에 실제 출현율은 100행당 약 17개(시작) → 25개(최대)이다.
OBSTACLE_CHANCE_START = 0.25
OBSTACLE_CHANCE_END = 0.5
OBSTACLE_SIZE = (60, 30)  # 높이는 ROW_GAP / 2 - PLATFORM_HEIGHT보다 작아야 발판과 겹치지 않는다.
SAFE_ROWS = 3  # 처음 몇 행은 장애물 없이 시작한다.
MIN_PATROL = 150  # 범위가 줄어든 움직이는 발판도 최소한 이만큼은 왕복한다.

# shortcut: player.py의 jump_speed(800)와 gravity(1500)로 계산한 점프 높이(약 213). 그 값이 바뀌면 같이 고친다.
PLAYER_JUMP_HEIGHT = 800 ** 2 / (2 * 1500)

# 제자리 점프한 플레이어 머리가 닿는, 장애물 아래 행 수 (현재 3행)
OBSTACLE_CLEAR_ROWS = int(
    (PLATFORM_HEIGHT + PLAYER_JUMP_HEIGHT + PLAYER_SIZE[1] - ROW_GAP / 2) // ROW_GAP
) + 1

# 아이템. 행마다 고정 발판 하나 위에 ITEM_CHANCE 확률로 띄워 놓는다.
ITEM_CHANCE = 0.08
ITEM_TYPES = (DOUBLE_JUMP, GHOST, SHRINK)
ITEM_FLOAT = 10  # 발판 윗면에서 띄우는 높이


@dataclass
class Platform:
    """발판의 위치, 크기, 타입. 장애물도 type="obstacle"로 재사용한다."""

    position: pygame.Vector2
    size: tuple[int, int]
    type: str = "normal"
    velocity_x: float = 0.0
    # 좌측 x가 오갈 수 있는 범위. 고정 발판은 min_x == max_x == position.x이다.
    min_x: float | None = None
    max_x: float | None = None

    def __post_init__(self):
        if self.min_x is None:
            self.min_x = self.max_x = self.position.x


class Level:
    """발판 생성 및 레벨 데이터를 관리한다."""

    def __init__(self, item_manager=None):
        # 아이템은 ItemManager.add_item으로 등록한다. None이면 아이템을 만들지 않는다.
        self.item_manager = item_manager
        self.reset()

    def reset(self):
        """레벨을 초기화하고 초기 발판을 생성한다. 시드를 고정하지 않아 매번 새 맵이 된다."""

        self.rng = random.Random()
        self.platforms: list[Platform] = []
        self.obstacles: list[Platform] = []
        self.next_row_index = 1
        self.last_obstacle_row = -OBSTACLE_CLEAR_ROWS

        start_platform = Platform(
            pygame.Vector2(WORLD_ORIGIN[0] + (WORLD_WIDTH - PLATFORM_WIDTH) / 2, START_Y),
            (PLATFORM_WIDTH, PLATFORM_HEIGHT),
        )
        self.platforms.append(start_platform)
        # 새 장애물이 수직 통로를 비워 줘야 하는 아래 행들의 발판
        self.recent_rows = deque([[start_platform]], maxlen=OBSTACLE_CLEAR_ROWS)

        for _ in range(INITIAL_ROWS):
            self._generate_next_row()

    def _generate_platform_positions(self) -> list[int]:
        """한 행에서 서로 겹치지 않는 발판 x 좌표들을 고른다."""

        counts, weights = zip(*PLATFORM_RULES)
        count = self.rng.choices(counts, weights=weights)[0]

        available_x = list(range(PLATFORM_MIN_X, PLATFORM_MAX_X + 1, 20))
        if PLATFORM_MAX_X not in available_x:
            available_x.append(PLATFORM_MAX_X)
        self.rng.shuffle(available_x)

        selected_x = []
        for x in available_x:
            if all(abs(x - other) >= PLATFORM_WIDTH for other in selected_x):
                selected_x.append(x)
            if len(selected_x) == count:
                break

        return selected_x

    def _generate_next_row(self):
        """다음 행의 발판을 만들고, 확률에 따라 그 아래 층에 장애물, 발판 위에 아이템을 둔다."""

        y = START_Y + self.next_row_index * ROW_GAP
        row = []

        for x in self._generate_platform_positions():
            platform = Platform(pygame.Vector2(x, y), (PLATFORM_WIDTH, PLATFORM_HEIGHT))

            if self.rng.random() < self._chance_at(
                y, MOVING_PLATFORM_CHANCE_START, MOVING_PLATFORM_CHANCE_END
            ):
                speed = self._moving_speed(y)
                platform.type = "moving"
                platform.velocity_x = self.rng.choice((-speed, speed))
                platform.min_x, platform.max_x = PLATFORM_MIN_X, PLATFORM_MAX_X
            elif self.rng.random() < SPRING_PLATFORM_CHANCE:
                platform.type = "spring"

            self.platforms.append(platform)
            row.append(platform)

        static = [p for p in row if p.velocity_x == 0]

        if (
            self.next_row_index > SAFE_ROWS
            and self.next_row_index - self.last_obstacle_row >= OBSTACLE_CLEAR_ROWS
            and self.rng.random() < self._chance_at(
                y, OBSTACLE_CHANCE_START, OBSTACLE_CHANCE_END
            )
        ):
            # 바로 위 행의 고정 발판도 포함해, 아래에서 올라와 착지하는 통로를 비운다.
            self._generate_obstacle(
                y - ROW_GAP / 2, [p for r in self.recent_rows for p in r] + static
            )

        if self.item_manager is not None and static and self.rng.random() < ITEM_CHANCE:
            self._generate_item(self.rng.choice(static))

        self.recent_rows.append(row)
        self.next_row_index += 1

    def _chance_at(self, y: float, start: float, end: float) -> float:
        """시작 높이의 start에서 MOVING_MAX_SPEED_SCORE점 높이의 end까지 직선으로 늘어난 확률."""

        progress = min((y - START_Y) / (MOVING_MAX_SPEED_SCORE * ROW_GAP), 1)
        return start + (end - start) * progress

    def _moving_speed(self, y: float) -> float:
        """생성 높이에 따른 느린/빠른 두 종류의 속도를 최고 속도 이하로 반환한다."""

        speed = MOVING_BASE_SPEED + (y - START_Y) * MOVING_SPEED_PER_HEIGHT
        if self.rng.random() < FAST_PLATFORM_CHANCE:
            speed *= FAST_SPEED_MULTIPLIER
        return min(speed, MOVING_MAX_SPEED)

    def _range_avoiding(self, platform: Platform, obstacle_x: float):
        """장애물 위치 obstacle_x를 피하는 발판의 왕복 범위 (min_x, max_x). 불가능하면 None.

        발판 위 플레이어(발판에 걸쳐 있는 모든 위치)가 장애물과 가로로 겹치지 않는 범위 중
        더 넓은 쪽을 고른다. 고정 발판은 범위가 한 점이므로 피하는지 여부만 판정된다.
        """

        left = (
            platform.min_x,
            min(platform.max_x, obstacle_x - PLAYER_SIZE[0] - PLATFORM_WIDTH),
        )
        right = (
            max(platform.min_x, obstacle_x + OBSTACLE_SIZE[0] + PLAYER_SIZE[0]),
            platform.max_x,
        )
        need = MIN_PATROL if platform.velocity_x else 0
        ranges = [r for r in (left, right) if r[1] - r[0] >= need]

        return max(ranges, key=lambda r: r[1] - r[0], default=None)

    def _generate_obstacle(self, y: float, platforms: list[Platform]):
        """platforms 모두가 피할 수 있는 위치에 장애물을 만들고, 움직이는 발판의 범위를 줄인다.

        새 장애물과 영향받는 행은 화면 밖 위쪽이라 범위가 바뀌는 모습은 보이지 않는다.
        """

        candidates = [
            x
            for x in range(PLATFORM_MIN_X, WORLD_ORIGIN[0] + WORLD_WIDTH - OBSTACLE_SIZE[0] + 1, 10)
            if all(self._range_avoiding(p, x) for p in platforms)
        ]
        if not candidates:
            return

        obstacle_x = self.rng.choice(candidates)
        self.last_obstacle_row = self.next_row_index

        for platform in platforms:
            if platform.velocity_x:
                platform.min_x, platform.max_x = self._range_avoiding(platform, obstacle_x)
                platform.position.x = min(max(platform.position.x, platform.min_x), platform.max_x)

        self.obstacles.append(
            Platform(pygame.Vector2(obstacle_x, y), OBSTACLE_SIZE, type="obstacle")
        )

    def _generate_item(self, platform: Platform):
        """고정 발판 가운데 위에 무작위 아이템을 띄워 놓는다."""

        x = platform.position.x + (PLATFORM_WIDTH - ITEM_SIZE[0]) / 2
        y = platform.position.y + PLATFORM_HEIGHT + ITEM_FLOAT
        self.item_manager.add_item(Item((x, y), self.rng.choice(ITEM_TYPES)))

    def _move_platforms(self, dt: float):
        """움직이는 발판을 좌우로 이동시키고 왕복 범위 끝에서 튕긴다."""

        for platform in self.platforms:
            if platform.velocity_x == 0:
                continue

            platform.position.x += platform.velocity_x * dt

            if platform.position.x < platform.min_x:
                platform.position.x = platform.min_x
                platform.velocity_x = abs(platform.velocity_x)
            elif platform.position.x > platform.max_x:
                platform.position.x = platform.max_x
                platform.velocity_x = -abs(platform.velocity_x)

    def update(self, dt: float, player_y: float):
        """발판을 움직이고, 플레이어 높이에 맞춰 위쪽을 생성하고 아래쪽을 삭제한다."""

        self._move_platforms(dt)

        while START_Y + self.next_row_index * ROW_GAP <= player_y + GENERATE_AHEAD:
            self._generate_next_row()

        cleanup_y = player_y - CLEANUP_BELOW
        self.platforms = [p for p in self.platforms if p.position.y >= cleanup_y]
        self.obstacles = [o for o in self.obstacles if o.position.y >= cleanup_y]

        if self.item_manager is not None:
            # shortcut: ItemManager에 삭제 함수가 없어 get_items() 리스트를 직접 거른다. 삭제 API가 생기면 교체한다.
            items = self.item_manager.get_items()
            items[:] = [i for i in items if i.position.y >= cleanup_y]

    def get_platforms(self) -> list[Platform]:
        """Player와 Renderer가 사용할 발판 목록을 반환한다."""
        return self.platforms

    def get_obstacles(self) -> list[Platform]:
        """Player와 Renderer가 사용할 장애물 목록을 반환한다."""
        return self.obstacles

    def get_spawn_position(self) -> pygame.Vector2:
        """reset 직후 시작 발판 가운데 위의 플레이어 좌측 하단 위치를 반환한다."""

        start = self.platforms[0]
        return pygame.Vector2(
            start.position.x + (start.size[0] - PLAYER_SIZE[0]) / 2,
            start.position.y + start.size[1],
        )
