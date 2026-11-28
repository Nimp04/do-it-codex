"""월드 좌표는 위쪽 양의 y이며, 객체 position은 좌측 하단이다."""

import pygame

from config import (
    BACKGROUND_SCROLL_RATIO,
    CAMERA_FOLLOW_DIVISOR,
    CAMERA_FOLLOW_THRESHOLD,
    SCREEN_SIZE,
    WORLD_ORIGIN,
    WORLD_WIDTH,
)
from item import DOUBLE_JUMP, GHOST, SHRINK


ITEM_STYLES = {
    DOUBLE_JUMP: ("점", (245, 185, 40)),
    GHOST: ("고", (190, 150, 240)),
    SHRINK: ("소", (80, 200, 190)),
}
LANDING_FOOT_HOLD_TIME = 0.016
LANDING_FOOT_RELEASE_TIME = 0.032
LANDING_SQUASH_TIME = 0.06
LANDING_ANIMATION_TIME = 0.22


class Camera:
    """현재 화면에 보이는 월드의 좌측 하단 위치를 보관한다."""

    def __init__(self):
        self.position = pygame.Vector2(WORLD_ORIGIN)

    def reset(self):
        self.position.update(WORLD_ORIGIN)

    def update(self, player_position, dt):
        target_y = player_position.y - CAMERA_FOLLOW_THRESHOLD
        distance = target_y - self.position.y
        if distance > 0:
            # 60FPS 기준 추적 비율을 경과 시간에 맞춰 환산한다.
            follow_ratio = 1 - (1 - 1 / CAMERA_FOLLOW_DIVISOR) ** (dt * 60)
            self.position.y += distance * follow_ratio


class Background:
    def __init__(self):
        # shortcut: 기본 구름 이미지를 생성한다. 배경 자산 확정 후 이미지 로딩으로 교체한다.
        self.image = pygame.Surface(SCREEN_SIZE).convert()
        self.image.fill((170, 215, 250))
        width, height = self.image.get_size()
        for x, y in ((width * 0.15, height * 0.18),
                     (width * 0.65, height * 0.45),
                     (width * 0.25, height * 0.78)):
            for rect in ((x, y + 20, 130, 35),
                         (x + 20, y, 65, 65),
                         (x + 65, y + 10, 55, 50)):
                pygame.draw.ellipse(self.image, (245, 250, 255), rect)

    def draw(self, screen, camera_position):
        scale = screen.get_width() / WORLD_WIDTH
        distance = camera_position.y - WORLD_ORIGIN[1]
        height = self.image.get_height()
        offset = int(distance * scale * BACKGROUND_SCROLL_RATIO) % height
        for y in range(offset - height, screen.get_height(), height):
            screen.blit(self.image, (0, y))


class Renderer:
    def __init__(self):
        pygame.display.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.display.set_caption("Jump OverFlow")
        self.scale = self.screen.get_width() / WORLD_WIDTH
        # shortcut: 시스템 한글 글꼴을 사용한다. 배포 시 글꼴 자산을 포함한다.
        self.font = pygame.font.SysFont("malgungothic", 28)
        self.item_font = pygame.font.SysFont("malgungothic", 20)
        self.camera = Camera()
        self.background = Background()

    def reset(self):
        self.camera.reset()

    def get_world_bounds(self) -> tuple:
        left, bottom = self.camera.position
        return (
            left,
            bottom,
            left + self.screen.get_width() / self.scale,
            bottom + self.screen.get_height() / self.scale,
        )

    def world_to_screen(self, position) -> pygame.Vector2:
        return pygame.Vector2(
            (position.x - self.camera.position.x) * self.scale,
            self.screen.get_height()
            - (position.y - self.camera.position.y) * self.scale,
        )

    def _object_rect(self, obj):
        position = self.world_to_screen(obj.position)
        width, height = obj.size
        return pygame.Rect(
            position.x,
            position.y - height * self.scale,
            width * self.scale,
            height * self.scale,
        )

    def draw_object(self, obj, color):
        rect = self._object_rect(obj)
        pygame.draw.rect(self.screen, color, rect)
        return rect

    def draw_obstacle(self, obstacle):
        rect = self._object_rect(obstacle)
        side = min(rect.width, rect.height)
        body = pygame.Rect(0, 0, side, side)
        body.center = rect.center
        quarter = side // 4
        for edge, tip in ((body.left, rect.left), (body.right - 1, rect.right - 1)):
            pygame.draw.polygon(self.screen, (100, 110, 125), (
                (edge, body.top),
                (tip, body.top + quarter),
                (edge, body.centery),
                (tip, body.bottom - 1 - quarter),
                (edge, body.bottom - 1),
            ))
        pygame.draw.rect(self.screen, (65, 75, 90), body)

    def draw_player(self, player, effect_times):
        color = (
            ITEM_STYLES[GHOST][1] if getattr(player, "is_ghost", False)
            else (55, 110, 220)
        )
        remaining = min((time for time in effect_times if time > 0), default=0.0)
        if 0 < remaining <= 3.0:
            blink_rate = 3 if remaining <= 1.0 else 1
            if int((3.0 - remaining) * 2 * blink_rate) % 2 == 0:
                color = tuple(255 - channel for channel in color)

        rect = self._object_rect(player)
        velocity = getattr(player, "velocity", None)
        if velocity is not None:
            speed_ratio = min(abs(velocity.y) / player.jump_speed, 1.0)
            stretch_amount = 0.25 if velocity.y >= 0 else 0.12
            stretch = 1.0 + stretch_amount * speed_ratio
            landing_height = getattr(player, "landing_height", None)
            if landing_height is not None and player.landing_age < LANDING_ANIMATION_TIME:
                recovery_elapsed = max(0.0, player.landing_age - LANDING_SQUASH_TIME)
                recovery = recovery_elapsed / (LANDING_ANIMATION_TIME - LANDING_SQUASH_TIME)
                compression = (1 - recovery) ** 2
                stretch += (0.75 - stretch) * compression
                # 착지 프레임에 발판에 붙인 발을 상승 위치로 빠르게 돌려준다.
                foot_elapsed = max(0.0, player.landing_age - LANDING_FOOT_HOLD_TIME)
                foot_release = min(1.0, foot_elapsed / LANDING_FOOT_RELEASE_TIME)
                lift = (player.position.y - landing_height) * self.scale
                rect.bottom += round(lift * (1 - foot_release) ** 2)
            feet = rect.midbottom
            rect.size = (round(rect.width / stretch), round(rect.height * stretch))
            rect.midbottom = feet
        pygame.draw.rect(self.screen, color, rect)

    def draw_item_label(self, item_type, rect):
        label = self.item_font.render(
            ITEM_STYLES[item_type][0], True, (25, 30, 40)
        )
        self.screen.blit(label, label.get_rect(center=rect.center))

    def draw_text(self, text: str, screen_position, *, centered=True):
        """기본은 화면 가로 중앙 정렬이며, centered=False면 전달 위치를 사용한다."""
        label = self.font.render(text, True, (25, 30, 40))
        if centered:
            screen_position = (
                (self.screen.get_width() - label.get_width()) / 2,
                screen_position[1],
            )
        self.screen.blit(label, screen_position)

    def render(
        self, game_state, player, platforms,
        obstacles=(), items=(), hud=None, *, effect_times=(),
    ):
        """카메라는 main이 갱신하며, 여기서는 객체 상태를 읽고 출력만 한다.

        HUD.get_ui_data(): current_score, high_score, 선택적인 item_slots / texts / buttons.
        item_slots: 아이템 종류 또는 None을 담은 길이 2 목록. 화면 우상단에 표시한다.
        texts: {"text": str, "position": 화면 좌표} 목록.
        buttons: {"text": str, "rect": pygame.Rect(화면 좌표)} 목록.
        effect_times: 고스트와 소형화 효과의 남은 시간(초).
        """
        self.background.draw(self.screen, self.camera.position)
        show_playfield = game_state in ("PLAYING", "GAME_OVER")

        if show_playfield:
            for platform in platforms:
                platform_type = getattr(platform, "type", "normal")

                if platform_type == "spring":
                    color = (245, 185, 40)  # 스프링 발판
                elif platform_type == "moving":
                    color = (45, 145, 185)  # 움직이는 발판
                else:
                    color = (60, 160, 90)  # 일반 발판

                rect = self.draw_object(platform, color)

                # 기존 움직이는 발판에만 가로선 표시
                if platform_type == "moving":
                    pygame.draw.line(
                        self.screen, (25, 30, 40),
                        (rect.left + 4, rect.centery),
                        (rect.right - 4, rect.centery), 2,
                    )

            for obstacle in obstacles:
                self.draw_obstacle(obstacle)

            for item in items:
                rect = self.draw_object(
                    item, ITEM_STYLES[item.item_type][1]
                )
                self.draw_item_label(item.item_type, rect)

            if player is not None:
                self.draw_player(player, effect_times)

        if hud is not None:
            ui = hud.get_ui_data()

            if show_playfield:
                self.draw_text(
                    f"Score: {ui['current_score']}",
                    (12, 12),
                    centered=False,
                )
                self.draw_text(
                    f"Best: {ui['high_score']}",
                    (12, 44),
                    centered=False,
                )

                for index, item_type in enumerate(
                    ui.get("item_slots", (None, None))
                ):
                    rect = pygame.Rect(
                        self.screen.get_width() - 152 + index * 76,
                        12, 64, 64,
                    )
                    pygame.draw.rect(
                        self.screen, (245, 250, 255), rect
                    )

                    if item_type is not None:
                        pygame.draw.rect(
                            self.screen,
                            ITEM_STYLES[item_type][1],
                            rect.inflate(-12, -12),
                        )
                        self.draw_item_label(item_type, rect)

                    pygame.draw.rect(
                        self.screen,
                        (25, 30, 40),
                        rect,
                        width=3 if index == 0 else 1,
                    )

            for text in ui.get("texts", ()):
                self.draw_text(text["text"], text["position"])

            for button in ui.get("buttons", ()):
                rect = button["rect"]
                pygame.draw.rect(
                    self.screen, (245, 250, 255), rect
                )
                width, height = self.font.size(button["text"])
                self.draw_text(
                    button["text"],
                    (
                        rect.centerx - width / 2,
                        rect.centery - height / 2,
                    ),
                    centered=False,
                )

        pygame.display.flip()
