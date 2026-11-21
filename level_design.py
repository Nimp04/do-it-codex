"""발판과 레벨 생성을 담당하는 모듈.

월드 좌표는 x가 오른쪽, y가 위쪽으로 증가한다.
Platform.position은 발판의 좌측 하단 좌표이다.
"""

from collections import deque
from dataclasses import dataclass
import random

import pygame

from config import PLAYER_SIZE, WORLD_ORIGIN, WORLD_WIDTH
from item import DOUBLE_JUMP, GHOST, SHRINK, ITEM_SIZE, Item


# 발판 크기
PLATFORM_WIDTH = 100
PLATFORM_HEIGHT = 15

# 시작 발판 위치
START_Y = 750

# 발판 행 사이의 간격
ROW_GAP = 100

# 처음에 미리 생성할 행 수
INITIAL_ROWS = 10

# 플레이어보다 이 높이만큼 위까지 발판을 미리 생성한다.
GENERATE_AHEAD = 1200

# 플레이어보다 충분히 아래에 있는 발판은 삭제한다.
CLEANUP_BELOW = 1200

# 행마다 생성할 발판 개수와 선택 확률
PLATFORM_RULES = [
    (1, 0.8),
    (2, 0.2),
]

# 발판 하나가 움직이는 발판일 확률
MOVING_PLATFORM_CHANCE = 0.7

# 움직이는 발판의 속도 (초당 월드 단위)
# 속도 = 기본 속도 + 시작 발판에서 올라간 높이 × 증가량, 최고 속도를 넘지 않는다.
# 증가량 0.01은 한 행(ROW_GAP=100, 점수 1점)마다 1씩 빨라져
# 빠른 발판은 약 100점, 느린 발판은 약 180점에서 최고 속도에 닿는다.
MOVING_BASE_SPEED = 60
MOVING_SPEED_PER_HEIGHT = 0.01
MOVING_MAX_SPEED = 240

# 움직이는 발판의 절반은 빠른 발판으로, 같은 높이의 느린 발판보다 이 배율만큼 빠르다.
# 둘 다 최고 속도에 막히므로 높이 올라갈수록 결국 모두 최고 속도가 된다.
FAST_PLATFORM_CHANCE = 0.5
FAST_SPEED_MULTIPLIER = 1.5

# 행 사이에 장애물이 생길 확률과 크기
# 높이는 행 간격(ROW_GAP)의 절반에서 발판 두께를 뺀 값보다 작아야 발판과 겹치지 않는다.
OBSTACLE_CHANCE = 0.25
OBSTACLE_SIZE = (60, 30)

# 처음 몇 행은 장애물 없이 시작한다.
SAFE_ROWS = 3

# shortcut: player.py의 jump_speed(800)와 gravity(1500)로 계산한 점프 높이(약 213). 그 값이 바뀌면 같이 고친다.
PLAYER_JUMP_HEIGHT = 800 ** 2 / (2 * 1500)

# 고정 발판에서 튀어 오른 플레이어 머리가 닿는 장애물 아래 행 수 (현재 3행).
# 이 행들의 고정 발판 위 수직 경로에는 장애물을 두지 않아 제자리 점프로는 절대 부딪히지 않는다.
OBSTACLE_CLEAR_ROWS = int(
    (PLATFORM_HEIGHT + PLAYER_JUMP_HEIGHT + PLAYER_SIZE[1] - ROW_GAP / 2)
    // ROW_GAP
) + 1

# 행마다 고정 발판 위에 아이템이 생길 확률과 종류
ITEM_CHANCE = 0.08
ITEM_TYPES = (DOUBLE_JUMP, GHOST, SHRINK)

# 아이템을 발판 윗면에서 띄우는 높이
ITEM_FLOAT = 10


@dataclass
class Platform:
    """발판의 위치, 크기, 타입. 장애물도 type="obstacle"로 재사용한다."""

    position: pygame.Vector2
    size: tuple[int, int]
    type: str = "normal"
    velocity_x: float = 0.0


class Level:
    """발판 생성 및 레벨 데이터를 관리한다."""

    def __init__(self, item_manager=None):
        # 아이템은 ItemManager.add_item으로 등록한다. None이면 아이템을 만들지 않는다.
        self.item_manager = item_manager
        self.reset()

    def reset(self):
        """레벨을 초기화하고 초기 발판을 생성한다."""

        # 시드를 고정하지 않아 reset(다시하기)마다 새로운 맵이 생성된다.
        self.rng = random.Random()

        self.platforms: list[Platform] = []
        self.obstacles: list[Platform] = []

        # 다음에 생성할 행 번호
        self.next_row_index = 1

        # 시작 발판
        start_x = (
            WORLD_ORIGIN[0]
            + (WORLD_WIDTH - PLATFORM_WIDTH) / 2
        )

        start_platform = Platform(
            position=pygame.Vector2(start_x, START_Y),
            size=(PLATFORM_WIDTH, PLATFORM_HEIGHT),
        )

        self.platforms.append(start_platform)
        # 최근 OBSTACLE_CLEAR_ROWS개 행의 고정 발판 x 좌표
        self.recent_static_x = deque(
            [[int(start_x)]], maxlen=OBSTACLE_CLEAR_ROWS
        )

        # 시작 발판 위쪽으로 초기 발판을 미리 생성한다.
        for _ in range(INITIAL_ROWS):
            self._generate_next_row()

    def _choose_platform_count(self) -> int:
        """해당 행에 생성할 발판 개수를 확률에 따라 결정한다."""

        counts, weights = zip(*PLATFORM_RULES)

        return self.rng.choices(counts, weights=weights)[0]

    def _generate_platform_positions(
        self,
        platform_count: int,
    ) -> list[int]:
        """한 행에서 서로 겹치지 않는 발판 x 좌표를 생성한다."""

        left_bound = WORLD_ORIGIN[0]
        right_bound = left_bound + WORLD_WIDTH - PLATFORM_WIDTH

        # 20 단위로 발판 위치 후보를 생성한다.
        available_x = list(
            range(left_bound, right_bound + 1, 20)
        )

        # 월드 오른쪽 끝도 후보에 포함한다.
        if right_bound not in available_x:
            available_x.append(right_bound)

        self.rng.shuffle(available_x)

        selected_x = []

        for x in available_x:
            # 같은 행의 발판끼리 겹치지 않도록 한다.
            overlaps = any(
                abs(x - previous_x) < PLATFORM_WIDTH
                for previous_x in selected_x
            )

            if not overlaps:
                selected_x.append(x)

            if len(selected_x) == platform_count:
                break

        return selected_x

    def _generate_next_row(self):
        """다음 발판 행을 생성하고 레벨에 추가한다."""

        y = START_Y + self.next_row_index * ROW_GAP

        platform_count = self._choose_platform_count()

        selected_x = self._generate_platform_positions(
            platform_count
        )

        static_x = []

        for x in selected_x:
            platform = Platform(
                position=pygame.Vector2(x, y),
                size=(PLATFORM_WIDTH, PLATFORM_HEIGHT),
            )

            if self.rng.random() < MOVING_PLATFORM_CHANCE:
                speed = self._moving_speed(y)
                platform.type = "moving"
                platform.velocity_x = self.rng.choice((-speed, speed))
            else:
                static_x.append(x)

            self.platforms.append(platform)

        # 점프가 닿는 아래 행들과 바로 위 행의 고정 발판 수직 경로를 비워 둔다.
        # 움직이는 발판은 제자리 점프로 기다리면 장애물 없는 위치로 온다.
        if (
            self.next_row_index > SAFE_ROWS
            and self.rng.random() < OBSTACLE_CHANCE
        ):
            self._generate_obstacle(
                y - ROW_GAP / 2,
                [x for row in self.recent_static_x for x in row] + static_x,
            )

        if (
            self.item_manager is not None
            and static_x
            and self.rng.random() < ITEM_CHANCE
        ):
            self._generate_item(self.rng.choice(static_x), y)

        self.recent_static_x.append(static_x)
        self.next_row_index += 1

    def _moving_speed(self, y: float) -> float:
        """생성 높이가 높을수록 빠른 속도를 느린/빠른 두 종류로 반환한다."""

        speed = MOVING_BASE_SPEED + (y - START_Y) * MOVING_SPEED_PER_HEIGHT

        if self.rng.random() < FAST_PLATFORM_CHANCE:
            speed *= FAST_SPEED_MULTIPLIER

        return min(speed, MOVING_MAX_SPEED)

    def _generate_obstacle(self, y: float, platform_xs: list[int]):
        """두 행 사이에 고정 발판의 수직 경로를 막지 않는 위치로 장애물을 만든다."""

        width = OBSTACLE_SIZE[0]
        left_bound = WORLD_ORIGIN[0]
        right_bound = left_bound + WORLD_WIDTH - width

        # 발판 위 수직 통로(좌우로 플레이어 너비만큼 여유)를 피한다.
        candidates = [
            x
            for x in range(left_bound, right_bound + 1, 10)
            if all(
                x + width <= px - PLAYER_SIZE[0]
                or x >= px + PLATFORM_WIDTH + PLAYER_SIZE[0]
                for px in platform_xs
            )
        ]

        if not candidates:
            return

        self.obstacles.append(
            Platform(
                position=pygame.Vector2(self.rng.choice(candidates), y),
                size=OBSTACLE_SIZE,
                type="obstacle",
            )
        )

    def _generate_item(self, platform_x: int, platform_y: float):
        """고정 발판 가운데 위에 아이템을 띄워 놓는다."""

        x = platform_x + (PLATFORM_WIDTH - ITEM_SIZE[0]) / 2
        y = platform_y + PLATFORM_HEIGHT + ITEM_FLOAT

        self.item_manager.add_item(
            Item((x, y), self.rng.choice(ITEM_TYPES))
        )

    def _move_platforms(self, dt: float):
        """움직이는 발판을 좌우로 이동시키고 월드 경계에서 튕긴다."""

        left_bound = WORLD_ORIGIN[0]
        right_bound = left_bound + WORLD_WIDTH - PLATFORM_WIDTH

        for platform in self.platforms:
            if platform.velocity_x == 0:
                continue

            platform.position.x += platform.velocity_x * dt

            if platform.position.x < left_bound:
                platform.position.x = left_bound
                platform.velocity_x = abs(platform.velocity_x)
            elif platform.position.x > right_bound:
                platform.position.x = right_bound
                platform.velocity_x = -abs(platform.velocity_x)

    def update(self, dt: float, player_y: float):
        """발판을 움직이고, 플레이어 높이에 맞춰 발판을 생성·삭제한다."""

        self._move_platforms(dt)

        # 플레이어보다 충분히 위쪽까지 발판을 미리 생성한다.
        target_y = player_y + GENERATE_AHEAD

        while (
            START_Y + self.next_row_index * ROW_GAP
            <= target_y
        ):
            self._generate_next_row()

        # 플레이어보다 충분히 아래에 있는 발판을 제거한다.
        cleanup_y = player_y - CLEANUP_BELOW

        self.platforms = [
            platform
            for platform in self.platforms
            if platform.position.y >= cleanup_y
        ]

        self.obstacles = [
            obstacle
            for obstacle in self.obstacles
            if obstacle.position.y >= cleanup_y
        ]

        if self.item_manager is not None:
            # shortcut: ItemManager에 삭제 함수가 없어 get_items() 리스트를 직접 거른다. 삭제 API가 생기면 교체한다.
            items = self.item_manager.get_items()
            items[:] = [
                item for item in items if item.position.y >= cleanup_y
            ]

    def get_platforms(self) -> list[Platform]:
        """Player와 Renderer가 사용할 발판 목록을 반환한다."""
        return self.platforms

    def get_obstacles(self) -> list[Platform]:
        """장애물 목록을 반환한다. 적도 장애물로 통합한다."""
        return self.obstacles

    def get_spawn_position(self) -> pygame.Vector2:
        """Player가 시작 발판 위에 생성될 좌측 하단 위치를 반환한다."""

        start_platform = self.platforms[0]

        spawn_x = (
            start_platform.position.x
            + (start_platform.size[0] - PLAYER_SIZE[0]) / 2
        )

        spawn_y = (
            start_platform.position.y
            + start_platform.size[1]
        )

        return pygame.Vector2(spawn_x, spawn_y)
