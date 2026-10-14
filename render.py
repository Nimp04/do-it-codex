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


class Camera:
    """현재 화면에 보이는 월드의 좌측 하단 위치를 보관한다."""

    def __init__(self):
        self.position = pygame.Vector2(WORLD_ORIGIN)

    def reset(self):
        self.position.update(WORLD_ORIGIN)

    def update(self, player_position):
        target_y = player_position.y - CAMERA_FOLLOW_THRESHOLD
        distance = target_y - self.position.y
        if distance > 0:
            # shortcut: 고정 FPS에서 거리/3을 적용한다. 가변 FPS 지원 시 dt를 받는다.
            self.position.y += distance / CAMERA_FOLLOW_DIVISOR


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

    def draw_object(self, obj, color):
        position = self.world_to_screen(obj.position)
        width, height = obj.size
        # shortcut: 게임 객체는 단색 사각형이다. 스프라이트 자산 확정 후 교체한다.
        rect = pygame.Rect(
            position.x,
            position.y - height * self.scale,
            width * self.scale,
            height * self.scale,
        )
        pygame.draw.rect(self.screen, color, rect)

    def draw_text(self, text: str, screen_position):
        label = self.font.render(text, True, (25, 30, 40))
        self.screen.blit(label, screen_position)

    def render(
        self, game_state, player, platforms,
        obstacles=(), enemies=(), items=(), hud=None,
    ):
        """카메라는 main이 갱신하며, 여기서는 객체 상태를 읽고 출력만 한다.

        HUD.get_ui_data(): current_score, high_score, 선택적인 texts / buttons.
        texts: {"text": str, "position": 화면 좌표} 목록.
        buttons: {"text": str, "rect": pygame.Rect(화면 좌표)} 목록.
        """
        self.background.draw(self.screen, self.camera.position)

        if game_state in ("PLAYING", "GAME_OVER"):
            for objects, color in (
                (platforms, (60, 160, 90)),
                (obstacles, (100, 110, 125)),
                (enemies, (220, 70, 70)),
                (items, (245, 185, 40)),
            ):
                for obj in objects:
                    self.draw_object(obj, color)
            if player is not None:
                self.draw_object(player, (55, 110, 220))

        if hud is not None:
            ui = hud.get_ui_data()
            if game_state in ("PLAYING", "GAME_OVER"):
                self.draw_text(f"Score: {ui['current_score']}", (12, 12))
                self.draw_text(f"Best: {ui['high_score']}", (12, 44))
            for text in ui.get("texts", ()):
                self.draw_text(text["text"], text["position"])
            for button in ui.get("buttons", ()):
                rect = button["rect"]
                pygame.draw.rect(self.screen, (245, 250, 255), rect)
                width, height = self.font.size(button["text"])
                self.draw_text(
                    button["text"],
                    (rect.centerx - width / 2, rect.centery - height / 2),
                )

        pygame.display.flip()

