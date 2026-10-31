"""발판과 레벨 생성을 담당하는 모듈.

월드 좌표는 x가 오른쪽, y가 위쪽으로 증가한다.
Platform.position은 발판의 좌측 하단 좌표이다.
"""

from dataclasses import dataclass
import random

import pygame

from config import WORLD_ORIGIN, WORLD_WIDTH


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

# 동일한 시드로 reset하면 동일한 초기 맵이 생성된다.
RANDOM_SEED = 42

# Player의 크기
PLAYER_WIDTH = 40
PLAYER_HEIGHT = 40

# 행마다 생성할 발판 개수와 선택 확률
PLATFORM_RULES = [
    (1, 0.8),
    (2, 0.2),
]


@dataclass
class Platform:
    """발판의 위치, 크기, 타입, 상태."""

    position: pygame.Vector2
    size: tuple[int, int]
    type: str = "normal"
    state: str = "active"


class Level:
    """발판 생성 및 레벨 데이터를 관리한다."""

    def __init__(self):
        self.platforms: list[Platform] = []
        self.obstacles: list = []
        self.enemies: list = []

        self.rng = random.Random(RANDOM_SEED)

        # 다음에 생성할 행 번호
        self.next_row_index = 1

        # 가장 최근 생성된 행의 발판 x 좌표
        self.last_row_x: list[int] = []

        self.reset()

    def reset(self):
        """레벨을 초기화하고 초기 발판을 생성한다."""

        self.rng = random.Random(RANDOM_SEED)

        self.platforms.clear()
        self.obstacles.clear()
        self.enemies.clear()

        self.next_row_index = 1
        self.last_row_x = []

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
        self.last_row_x = [int(start_x)]

        # 시작 발판 위쪽으로 초기 발판을 미리 생성한다.
        for _ in range(INITIAL_ROWS):
            self._generate_next_row()

    def _choose_platform_count(self) -> int:
        """해당 행에 생성할 발판 개수를 확률에 따라 결정한다."""

        counts = [count for count, _ in PLATFORM_RULES]
        weights = [weight for _, weight in PLATFORM_RULES]

        return self.rng.choices(
            counts,
            weights=weights,
            k=1,
        )[0]

    def _generate_platform_positions(
        self,
        platform_count: int,
    ) -> list[int]:
        """한 행에서 서로 겹치지 않는 발판 x 좌표를 생성한다."""

        left_bound = WORLD_ORIGIN[0]
        right_bound = left_bound + WORLD_WIDTH - PLATFORM_WIDTH

        if right_bound < left_bound:
            return []

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

        for x in selected_x:
            platform = Platform(
                position=pygame.Vector2(x, y),
                size=(PLATFORM_WIDTH, PLATFORM_HEIGHT),
            )

            self.platforms.append(platform)

        self.last_row_x = selected_x
        self.next_row_index += 1

    def update(self, dt: float, player_y: float | None = None):
        """플레이어의 높이에 맞춰 발판을 계속 생성한다.

        main.py에서 player_y를 전달해야 무한 생성이 동작한다.
        """

        if player_y is None:
            return

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

    def get_platforms(self) -> list[Platform]:
        """Player와 Renderer가 사용할 발판 목록을 반환한다."""
        return self.platforms

    def get_obstacles(self) -> list:
        """장애물 목록을 반환한다."""
        return self.obstacles

    def get_enemies(self) -> list:
        """적 목록을 반환한다."""
        return self.enemies

    def get_spawn_position(self) -> pygame.Vector2:
        """Player가 시작 발판 위에 생성될 좌측 하단 위치를 반환한다."""

        start_platform = self.platforms[0]

        spawn_x = (
            start_platform.position.x
            + (start_platform.size[0] - PLAYER_WIDTH) / 2
        )

        spawn_y = (
            start_platform.position.y
            + start_platform.size[1]
        )

        return pygame.Vector2(spawn_x, spawn_y)
