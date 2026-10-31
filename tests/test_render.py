import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame

import main
import render
from config import (
    BACKGROUND_SCROLL_RATIO,
    CAMERA_FOLLOW_THRESHOLD,
    WORLD_ORIGIN,
)


def game_object(x, y, size=(24, 24)):
    return SimpleNamespace(position=pygame.Vector2(x, y), size=size)


class RendererTests(unittest.TestCase):
    def setUp(self):
        self.renderer = render.Renderer()

    def tearDown(self):
        pygame.quit()

    def test_camera_follows_by_one_tenth_at_60_fps_and_never_descends(self):
        camera = self.renderer.camera
        player = pygame.Vector2(100, CAMERA_FOLLOW_THRESHOLD - 1)
        camera.update(player, 1 / 60)
        self.assertEqual(camera.position, pygame.Vector2(WORLD_ORIGIN))

        player.y = CAMERA_FOLLOW_THRESHOLD + 300
        camera.update(player, 1 / 60)
        self.assertAlmostEqual(camera.position.y, 30)
        before = camera.position.y
        camera.update(player, 1 / 60)
        self.assertAlmostEqual(
            camera.position.y, before + (300 - before) / 10
        )
        self.assertEqual(player.y, CAMERA_FOLLOW_THRESHOLD + 300)
        before = camera.position.copy()
        camera.update(pygame.Vector2(100, -100), 1 / 60)
        self.assertEqual(camera.position, before)
        self.renderer.reset()
        self.assertEqual(camera.position, pygame.Vector2(WORLD_ORIGIN))

    def test_camera_follow_matches_elapsed_time_across_frame_rates(self):
        player = pygame.Vector2(100, CAMERA_FOLLOW_THRESHOLD + 300)
        for timesteps in (
            [1 / 30] * 15,
            [1 / 60] * 30,
            [1 / 120] * 60,
            [0, 0.01, 0.04, 0.1, 0.35],
        ):
            with self.subTest(timesteps=timesteps):
                camera = render.Camera()
                for dt in timesteps:
                    camera.update(player, dt)
                self.assertAlmostEqual(camera.position.y, 300 * (1 - 0.9 ** 30))

    def test_camera_stays_still_without_elapsed_time_and_does_not_overshoot(self):
        camera = self.renderer.camera
        player = pygame.Vector2(100, CAMERA_FOLLOW_THRESHOLD + 300)
        camera.update(player, 0)
        self.assertEqual(camera.position, pygame.Vector2(WORLD_ORIGIN))
        camera.update(player, 1)
        self.assertAlmostEqual(camera.position.y, 300 * (1 - 0.9 ** 60))
        self.assertLess(camera.position.y, 300)

    def test_world_bounds_and_bottom_left_coordinates_with_scaling(self):
        with patch.object(render, "SCREEN_SIZE", (300, 400)):
            renderer = render.Renderer()
        self.assertEqual(renderer.get_world_bounds(), (0, 0, 600, 800))
        self.assertEqual(
            renderer.world_to_screen(pygame.Vector2(100, 200)),
            pygame.Vector2(50, 300),
        )
        renderer.screen.fill((0, 0, 0))
        renderer.draw_object(game_object(100, 200, (40, 60)), (255, 0, 0))
        self.assertEqual(renderer.screen.get_at((50, 270))[:3], (255, 0, 0))
        self.assertEqual(renderer.screen.get_at((69, 299))[:3], (255, 0, 0))
        self.assertEqual(renderer.screen.get_at((70, 300))[:3], (0, 0, 0))

        renderer.camera.position.y = 1_000_000
        self.assertEqual(
            renderer.get_world_bounds(), (0, 1_000_000, 600, 1_000_800)
        )
        self.assertEqual(
            renderer.world_to_screen(pygame.Vector2(100, 1_000_200)),
            pygame.Vector2(50, 300),
        )

    def test_background_parallax_repeats_without_gaps(self):
        renderer = self.renderer
        screen = renderer.screen
        background = renderer.background
        size = screen.get_size()
        image = pygame.Surface(size)
        image.fill((10, 20, 30))
        image.fill((200, 100, 50), (0, 0, size[0], 10))
        background.image = image

        screen.fill((255, 0, 255))
        background.draw(screen, pygame.Vector2(WORLD_ORIGIN))
        original = pygame.image.tobytes(screen, "RGB")
        background.draw(screen, pygame.Vector2(0, 100))
        offset = int(100 * renderer.scale * BACKGROUND_SCROLL_RATIO)
        self.assertEqual(screen.get_at((0, offset))[:3], (200, 100, 50))
        self.assertEqual(screen.get_at((0, offset - 1))[:3], (10, 20, 30))

        cycle = size[1] / (renderer.scale * BACKGROUND_SCROLL_RATIO)
        background.draw(screen, pygame.Vector2(0, cycle))
        self.assertEqual(pygame.image.tobytes(screen, "RGB"), original)

    def test_layers_do_not_change_world_data_or_advance_camera(self):
        renderer = self.renderer
        player = game_object(100, 100, (20, 20))
        platform = game_object(100, 100, (100, 20))
        item = game_object(100, 100, (10, 10))
        camera_before = renderer.camera.position.copy()
        player_before = player.position.copy()
        renderer.render("PLAYING", player, [platform], items=[item])
        self.assertEqual(renderer.screen.get_at((101, 681))[:3], (55, 110, 220))
        self.assertEqual(renderer.screen.get_at((121, 681))[:3], (60, 160, 90))
        self.assertEqual(player.position, player_before)
        self.assertEqual(renderer.camera.position, camera_before)

        player.position.y = 0
        renderer.render("PLAYING", player, [])
        self.assertEqual(renderer.screen.get_at((101, 799))[:3], (55, 110, 220))

    def test_main_render_call_and_screen_fixed_hud_in_all_states(self):
        renderer = self.renderer
        ui = {
            "current_score": 10,
            "high_score": 20,
            "texts": [{"text": "Jump OverFlow", "position": (12, 90)}],
            "buttons": [{"text": "Start", "rect": pygame.Rect(20, 150, 120, 50)}],
        }
        hud = SimpleNamespace(get_ui_data=lambda: ui)
        player = game_object(500, 100)
        game = main.Game(
            player=player,
            level=SimpleNamespace(
                get_platforms=lambda: [],
                get_obstacles=lambda: [],
                get_enemies=lambda: [],
            ),
            items=SimpleNamespace(get_items=lambda: []),
            hud=hud,
            renderer=renderer,
        )
        with patch.object(renderer, "draw_text", wraps=renderer.draw_text) as text:
            for state in main.GameState:
                game.state = state
                main.render_frame(game)
                text.assert_any_call("Jump OverFlow", (12, 90))
                self.assertEqual(
                    renderer.screen.get_at((21, 151))[:3], (245, 250, 255)
                )
                if state in (main.GameState.PLAYING, main.GameState.GAME_OVER):
                    text.assert_any_call("Score: 10", (12, 12))
                text.reset_mock()

            renderer.camera.update(pygame.Vector2(500, 1_000_000), 1 / 60)
            main.render_frame(game)
            text.assert_any_call("Jump OverFlow", (12, 90))
            text.assert_any_call("Score: 10", (12, 12))


if __name__ == "__main__":
    unittest.main()
