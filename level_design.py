from dataclasses import dataclass
import random
import pygame

# 맵 생성 설정
SCREEN_WIDTH = 600
PLATFORM_WIDTH = 100
PLATFORM_HEIGHT = 15
START_Y = 750
ROW_GAP = 100
ROW_COUNT = 30
RANDOM_SEED = 42

# 행마다 생성할 발판 개수와 선택 확률
# 새 규칙을 추가할 때 이 리스트에 항목을 추가하면 된다.
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

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            round(self.position.x),
            round(self.position.y),
            self.size[0],
            self.size[1],
        )


class Level:
    def __init__(self):
        self.platforms: list[Platform] = []
        self.obstacles: list = []
        self.enemies: list = []
        self.reset()

    def reset(self):
        """시드를 기준으로 맵과 발판을 다시 생성한다."""
        rng = random.Random(RANDOM_SEED)

        self.platforms = []
        self.obstacles = []
        self.enemies = []

        # 시작 발판
        self.platforms.append(
            Platform(
                position=pygame.Vector2(
                    (SCREEN_WIDTH - PLATFORM_WIDTH) / 2,
                    START_Y,
                ),
                size=(PLATFORM_WIDTH, PLATFORM_HEIGHT),
            )
        )

        # Y좌표 구간별로 발판을 자동 생성
        for row_index in range(1, ROW_COUNT + 1):
            y = START_Y + row_index * ROW_GAP

            # 리스트의 규칙과 난수를 이용해 해당 행의 발판 개수 결정
            counts = [rule[0] for rule in PLATFORM_RULES]
            weights = [rule[1] for rule in PLATFORM_RULES]
            platform_count = rng.choices(
                counts, weights=weights, k=1
            )[0]

            # 한 행 안에서 발판이 겹치지 않도록 위치 선택
            available_x = list(
                range(0, SCREEN_WIDTH - PLATFORM_WIDTH + 1, 20)
            )
            rng.shuffle(available_x)
            selected_x = []

            for x in available_x:
                if all(abs(x - prev_x) >= PLATFORM_WIDTH
                       for prev_x in selected_x):
                    selected_x.append(x)
                if len(selected_x) == platform_count:
                    break

            for x in selected_x:
                self.platforms.append(
                    Platform(
                        position=pygame.Vector2(x, y),
                        size=(PLATFORM_WIDTH, PLATFORM_HEIGHT),
                    )
                )

    def update(self, dt: float):
        """발판 업데이트. 현재 발판은 고정형이다."""
        pass

    def get_platforms(self) -> list[Platform]:
        return self.platforms

    def get_obstacles(self) -> list:
        return self.obstacles

    def get_enemies(self) -> list:
        return self.enemies

    def get_spawn_position(self) -> pygame.Vector2:
        """플레이어의 시작 위치를 반환한다."""
        return pygame.Vector2(
            SCREEN_WIDTH / 2,
            START_Y - 50,
        )
