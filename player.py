
"""Player의 기본 이동, 중력, 자동 점프를 처리하는 모듈."""

from enum import StrEnum
from math import isfinite
import pygame

from config import WORLD_ORIGIN, WORLD_WIDTH

class PlayerState(StrEnum):
    JUMPING = "JUMPING"
    FALLING = "FALLING"


class Player:
    def __init__(self):
        self.position = pygame.Vector2(0, 0)
        self.velocity = pygame.Vector2(0, 0)
        self.size = (40, 40)
        self.state = PlayerState.FALLING

        self.move_speed = 300
        self.jump_speed = 650
        self.gravity = 1500
        self.previous_bottom = 0
        self._pending_motion = None

    def reset(self, spawn_position):
        self.position = pygame.Vector2(spawn_position)
        self.velocity = pygame.Vector2(0, self.jump_speed)
        self.previous_bottom = self.position.y
        self.state = PlayerState.JUMPING
        self._pending_motion = None

    def update(self, dt, input_state):
        if not isfinite(dt) or dt < 0:
            raise ValueError("dt must be finite and non-negative")

        # 좌우 이동
        self.velocity.x = 0

        if input_state[pygame.K_LEFT] or input_state[pygame.K_a]:
            self.velocity.x -= self.move_speed

        if input_state[pygame.K_RIGHT] or input_state[pygame.K_d]:
            self.velocity.x += self.move_speed

        # 충돌 검사에서 같은 시간을 짧게 나눠 재계산할 수 있도록 보관한다.
        self._pending_motion = (self.position.copy(), self.velocity.copy(), dt)
        self._move(dt)

    def _move(self, dt):
        self.previous_bottom = self.position.y
        self.position.x += self.velocity.x * dt
        self.position.x = max(
            WORLD_ORIGIN[0],
            min(self.position.x, WORLD_ORIGIN[0] + WORLD_WIDTH - self.size[0]),
        )
        self.position.y += self.velocity.y * dt - self.gravity * dt * dt / 2
        self.velocity.y -= self.gravity * dt

        # 상태 갱신
        if self.velocity.y > 0:
            self.state = PlayerState.JUMPING
        else:
            self.state = PlayerState.FALLING

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

    def _check_collisions(self, platforms, obstacles, enemies, items):
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
        _, bottom, _, _ = world_bounds
        return self.position.y + self.size[1] > bottom
