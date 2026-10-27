
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
        self.state = PlayerState.JUMPING

        self.move_speed = 300
        self.jump_speed = 650
        self.gravity = 1500
        self.previous_bottom = 0

    def reset(self, spawn_position):
        self.position = pygame.Vector2(spawn_position)
        self.velocity = pygame.Vector2(0, self.jump_speed)
        self.previous_bottom = self.position.y - self.size[1] / 2
        self.state = PlayerState.JUMPING

    def update(self, dt, input_state):
        # 이동 전 발 위치 저장
        self.previous_bottom = self.position.y - self.size[1] / 2

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
        # 하강 중에만 발판 충돌 검사
        if self.velocity.y >= 0:
            return []

        player_left = self.position.x - self.size[0] / 2
        player_right = self.position.x + self.size[0] / 2
        current_bottom = self.position.y - self.size[1] / 2

        for platform in platforms:
            platform_left = platform.position.x - platform.size[0] / 2
            platform_right = platform.position.x + platform.size[0] / 2
            platform_top = platform.position.y + platform.size[1] / 2

            if (
                player_right > platform_left
                and player_left < platform_right
                and self.previous_bottom >= platform_top >= current_bottom
            ):
                # 발판 착지 후 자동 점프
                self.position.y = platform_top + self.size[1] / 2
                self.velocity.y = self.jump_speed
                self.state = PlayerState.JUMPING
                break

        return []

    def is_alive(self, world_bounds):
        # main.py 연동용 (추락 판정은 추후 구현)
        return True
