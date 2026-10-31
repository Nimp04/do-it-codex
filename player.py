
"""Player의 기본 이동, 중력, 자동 점프를 처리하는 모듈."""

from enum import StrEnum
import pygame

class PlayerState(StrEnum):
    JUMPING = "JUMPING"
    FALLING = "FALLING"


class Player:
    def __init__(self):
        self.position = pygame.Vector2(0, 0)
        self.velocity = pygame.Vector2(0, 0)
        self.size = (40, 40)
        self.state = PlayerState.FALLING

        self.move_speed = 400
        self.jump_speed = 800
        self.gravity = 1500
        self.previous_bottom = 0

    def reset(self, spawn_position):
        self.position = pygame.Vector2(spawn_position)
        self.velocity = pygame.Vector2(0, self.jump_speed)
        self.previous_bottom = self.position.y
        self.state = PlayerState.JUMPING

    def update(self, dt, input_state):
        # 이동 전 발 위치 저장
        self.previous_bottom = self.position.y

        # 좌우 이동
        self.velocity.x = 0

        if input_state[pygame.K_LEFT] or input_state[pygame.K_a]:
            self.velocity.x -= self.move_speed

        if input_state[pygame.K_RIGHT] or input_state[pygame.K_d]:
            self.velocity.x += self.move_speed

        # 중력 적용
        self.velocity.y -= self.gravity * dt

        # dt 기반 위치 갱신
        self.position += self.velocity * dt

        # 상태 갱신
        if self.velocity.y > 0:
            self.state = PlayerState.JUMPING
        else:
            self.state = PlayerState.FALLING

    def check_collisions(self, platforms, obstacles, enemies, items):
        """좌측 하단 기준으로 판정하며, 다른 모듈의 변경은 이벤트로 요청한다."""
        for objects in (obstacles, enemies):
            for obj in objects:
                if self._overlaps(obj):
                    return [{"type": "GAME_OVER"}]

        events = [
            {"type": "ITEM_COLLECTED", "item_id": item.id}
            for item in items if self._overlaps(item)
        ]

        if self.velocity.y >= 0:
            return events

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

    def _overlaps(self, obj):
        return (
            self.position.x < obj.position.x + obj.size[0]
            and self.position.x + self.size[0] > obj.position.x
            and self.position.y < obj.position.y + obj.size[1]
            and self.position.y + self.size[1] > obj.position.y
        )

    def is_alive(self, world_bounds):
        # main.py 연동용 (추락 판정은 추후 구현)
        return True
