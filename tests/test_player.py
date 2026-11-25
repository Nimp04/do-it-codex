import os
import unittest
from collections import Counter
from unittest.mock import patch

import pygame

from level_design import ROW_GAP, SPRING_PLATFORM_CHANCE, START_Y, Level
from main import GameState, handle_ui_action, initialize_game, render_frame, update_game
from player import PlayerState


class SpringPlatformIntegrationTests(unittest.TestCase):
    def test_spring_generation_uses_thirty_percent_of_fixed_platforms(self):
        level = Level()
        start = level.get_platforms()[0]
        self.assertEqual(start.type, "normal")
        self.assertEqual(start.velocity_x, 0)
        self.assertEqual(SPRING_PLATFORM_CHANCE, 0.30)

        # 초기 배치를 제외하고 시드 설정 이후 실제 게임이 생성한 행을 수집한다.
        initial_top = max(platform.position.y for platform in level.get_platforms())
        level.rng.seed(20)
        generated = {}
        for row in range(10, 3001, 10):
            level.update(0, START_Y + row * ROW_GAP)
            for platform in level.get_platforms():
                if platform.position.y > initial_top:
                    # 여러 프레임에 걸쳐 남아 있는 발판은 한 번만 센다.
                    generated[tuple(platform.position)] = platform

        counts = Counter(platform.type for platform in generated.values())
        fixed_count = counts["normal"] + counts["spring"]
        self.assertGreaterEqual(fixed_count, 500)
        self.assertGreater(counts["moving"], 0)
        for platform in generated.values():
            self.assertEqual(platform.velocity_x == 0, platform.type != "moving")
        self.assertAlmostEqual(
            counts["spring"] / fixed_count, SPRING_PLATFORM_CHANCE, delta=0.05
        )

    def test_generated_platforms_are_rendered_in_their_configured_colors(self):
        game = self.create_game()
        renderer = game.renderer
        for platform_type, expected_rgb in (
            ("normal", (60, 160, 90)),
            ("spring", (245, 185, 40)),
            ("moving", (45, 145, 185)),
        ):
            with self.subTest(platform_type=platform_type):
                platform = self.find_platform(game, platform_type)
                renderer.camera.position.y = platform.position.y - 400
                # 발판 내부를 읽되 움직이는 발판의 중앙 가로선은 피한다.
                sample = renderer.world_to_screen(
                    platform.position + pygame.Vector2(*platform.size) / 4
                )

                render_frame(game)

                pixel = renderer.screen.get_at((int(sample.x), int(sample.y)))
                self.assertEqual(pixel[:3], expected_rgb)

    def test_landing_on_generated_spring_doubles_jump_and_restart_resets_game(self):
        game = self.create_game()
        level = game.level
        player = game.player
        spring = self.find_platform(game, "spring")
        normal = self.find_platform(game, "normal")
        no_input = dict.fromkeys(
            (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d), False
        )

        for platform, expected_speed in ((normal, 800), (spring, 1600)):
            with self.subTest(platform_type=platform.type):
                top = platform.position.y + platform.size[1]
                player.position.update(platform.position.x, top + 1)
                player.velocity.update(0, -400)

                update_game(game, 1 / 120, no_input)

                self.assertEqual(game.state, GameState.PLAYING)
                self.assertEqual(player.position.y, top)
                self.assertEqual(player.velocity.y, expected_speed)
                self.assertEqual(player.state, PlayerState.JUMPING)

        game.state = GameState.GAME_OVER
        handle_ui_action(game, "RESTART")

        self.assertEqual(game.state, GameState.PLAYING)
        self.assertFalse(any(platform is spring for platform in level.get_platforms()))
        self.assertEqual(level.get_platforms()[0].type, "normal")
        self.assertEqual(player.position, level.get_spawn_position())
        self.assertEqual(player.velocity, pygame.Vector2(0, 800))
        self.assertEqual(player.state, PlayerState.JUMPING)

    def create_game(self):
        self.addCleanup(pygame.quit)
        with patch.dict(os.environ, {"SDL_VIDEODRIVER": "dummy"}):
            game = initialize_game()
        handle_ui_action(game, "START_GAME")
        # 첫 게임 프레임에서 HUD 상태도 PLAYING으로 갱신한다.
        update_game(game, 0, pygame.key.get_pressed())
        game.level.rng.seed(20)
        game.level.update(0, START_Y + 50 * ROW_GAP)
        return game

    def find_platform(self, game, platform_type):
        platform = next(
            (p for p in game.level.get_platforms() if p.type == platform_type), None
        )
        self.assertIsNotNone(platform, f"Level이 {platform_type} 발판을 생성해야 합니다.")
        return platform
