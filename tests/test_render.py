import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame

import main
import render
from hud import HUD
from item import DOUBLE_JUMP, GHOST, SHRINK, Item, ItemManager
from player import Player
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

    def test_pause_hides_scene_score_and_inventory_and_draws_buttons(self):
        player = game_object(100, 400)
        player.item_slots = [GHOST, None]
        platform = game_object(20, 400, (60, 15))
        obstacle = game_object(350, 400)
        item = Item((80, 200), GHOST)
        hud = HUD()
        hud.current_score = 3
        hud.high_score = 5
        before = player.position.copy()
        camera = self.renderer.camera.position.copy()
        points = ((101, 377), (21, 386), (351, 377), (81, 569), (455, 19))
        screen = self.renderer.screen
        hud.update("PLAYING", player)
        self.renderer.render("PLAYING", player, [platform], [obstacle], [item], hud)
        self.assertEqual([screen.get_at(point)[:3] for point in points], [
            (55, 110, 220), (60, 160, 90), (65, 75, 90),
            (190, 150, 240), (190, 150, 240),
        ])

        hud.update("PAUSED", player)
        with patch.object(self.renderer, "draw_text", wraps=self.renderer.draw_text) as text:
            self.renderer.render("PAUSED", player, [platform], [obstacle], [item], hud)
        self.assertEqual(
            [screen.get_at(point)[:3] for point in points],
            [self.renderer.background.image.get_at(point)[:3] for point in points],
        )
        self.assertEqual([call.args[0] for call in text.call_args_list], [
            "일시정지", "계속하기", "다시하기", "홈으로",
        ])
        self.assertEqual(player.position, before)
        self.assertEqual(self.renderer.camera.position, camera)

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
        item = Item((100, 100), DOUBLE_JUMP, size=(10, 10))
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

    def test_world_item_types_have_distinct_colors_and_visible_labels(self):
        items = [
            Item((80 + index * 100, 400), item_type)
            for index, item_type in enumerate((DOUBLE_JUMP, GHOST, SHRINK))
        ]
        self.renderer.render("PLAYING", None, [], [], items)
        colors = []
        for item in items:
            rect = pygame.Rect(item.position.x, 368, 32, 32)
            colors.append(self.renderer.screen.get_at((rect.x + 1, rect.y + 1))[:3])
            self.assertTrue(any(
                self.renderer.screen.get_at((x, y))[:3] == (25, 30, 40)
                for x in range(rect.left, rect.right)
                for y in range(rect.top, rect.bottom)
            ))
        self.assertEqual(len(set(colors)), 3)

    def test_item_slots_follow_hud_order_and_stay_fixed_when_camera_moves(self):
        hud = HUD()
        for slots, expected_colors in (
            ([DOUBLE_JUMP, GHOST], ((245, 185, 40), (190, 150, 240))),
            ([GHOST, DOUBLE_JUMP], ((190, 150, 240), (245, 185, 40))),
            ([None, SHRINK], ((245, 250, 255), (80, 200, 190))),
            ([None, None], ((245, 250, 255), (245, 250, 255))),
        ):
            with self.subTest(slots=slots):
                hud.item_slots = list(slots)
                self.renderer.camera.position.y += 1000
                self.renderer.render("PLAYING", None, [], hud=hud)
                for position, color in zip(((455, 19), (531, 19)), expected_colors):
                    self.assertEqual(self.renderer.screen.get_at(position)[:3], color)
                self.assertEqual(hud.item_slots, slots)

    def test_moving_platform_is_distinct_and_uses_updated_position(self):
        normal = game_object(80, 400, (100, 15))
        moving = game_object(280, 400, (100, 15))
        moving.type = "moving"
        self.renderer.render("PLAYING", None, [normal, moving])
        self.assertEqual(self.renderer.screen.get_at((81, 386))[:3], (60, 160, 90))
        self.assertEqual(self.renderer.screen.get_at((281, 386))[:3], (45, 145, 185))
        self.assertEqual(self.renderer.screen.get_at((300, 392))[:3], (25, 30, 40))

        moving.position.x = 380
        self.renderer.render("PLAYING", None, [normal, moving])
        self.assertNotEqual(self.renderer.screen.get_at((281, 386))[:3], (45, 145, 185))
        self.assertEqual(self.renderer.screen.get_at((381, 386))[:3], (45, 145, 185))
        self.assertEqual(moving.position, pygame.Vector2(380, 400))

    def test_ghost_color_follows_flag_and_preserves_player_size(self):
        player = game_object(100, 400, (20, 20))
        self.renderer.render("PLAYING", player, [])
        self.assertEqual(self.renderer.screen.get_at((101, 381))[:3], (55, 110, 220))

        for state in ("PLAYING", "GAME_OVER"):
            for active, color in (
                (False, (55, 110, 220)),
                (True, (190, 150, 240)),
                (False, (55, 110, 220)),
            ):
                with self.subTest(state=state, active=active):
                    player.is_ghost = active
                    self.renderer.render(state, player, [])
                    self.assertEqual(self.renderer.screen.get_at((101, 381))[:3], color)
                    self.assertNotEqual(self.renderer.screen.get_at((125, 381))[:3], color)
                    self.assertEqual(player.size, (20, 20))
                    self.assertEqual(player.position, pygame.Vector2(100, 400))
                    self.assertEqual(player.is_ghost, active)

    def test_blink_uses_shortest_active_effect_and_speeds_up_at_one_second(self):
        player = game_object(100, 400, (20, 20))
        for effects, color in (
            ((3.1, 0.0), (190, 150, 240)),
            ((3.0, 0.0), (65, 105, 15)),
            ((2.25, 0.0), (190, 150, 240)),
            ((2.25, 1.0), (65, 105, 15)),
            ((0.0, 0.75), (55, 110, 220)),
            ((0.0, 0.6), (200, 145, 35)),
            ((0.0, 0.0), (55, 110, 220)),
        ):
            with self.subTest(effects=effects):
                player.is_ghost = effects[0] > 0
                self.renderer.render("PLAYING", player, [], effect_times=effects)
                self.assertEqual(self.renderer.screen.get_at((110, 390))[:3], color)

    def test_player_stretches_in_the_air_and_returns_to_square_at_apex(self):
        player = Player()
        player.position.update(100, 400)
        color = (55, 110, 220)
        for speed in (0, player.jump_speed, -player.jump_speed):
            with self.subTest(speed=speed):
                player.velocity.y = speed
                self.renderer.render("PLAYING", player, [])
                screen = self.renderer.screen
                self.assertEqual(screen.get_at((101, 380))[:3] == color, speed == 0)
                self.assertEqual(screen.get_at((120, 357))[:3] == color, speed != 0)
                self.assertEqual(screen.get_at((120, 399))[:3], color)
                self.assertNotEqual(screen.get_at((120, 400))[:3], color)
                self.assertEqual(player.size, (40, 40))
                self.assertEqual(player.position, pygame.Vector2(100, 400))

    def test_platform_contact_draws_squash_before_rebound_stretch(self):
        player = Player()
        player.position.update(100, 403)
        player.velocity.y = -400
        platform = game_object(80, 385, (100, 15))
        keys = dict.fromkeys((pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d), False)
        bounds = []
        with patch.object(pygame.draw, "rect") as draw:
            for dt in (1 / 60, 1 / 24, 1 / 16, 1 / 8):
                player.update(dt, keys)
                player.check_collisions([platform], [], [])
                self.renderer.draw_player(player, ())
                bounds.append(draw.call_args.args[2])

        contact, squash, rebound, rising = bounds
        self.assertEqual(contact.bottom, 400)
        self.assertEqual(squash.size, contact.size)
        self.assertLess(squash.bottom, contact.bottom)
        self.assertLess(squash.height, rebound.height)
        self.assertLess(rebound.height, rising.height)
        self.assertGreater(contact.width, player.size[0])
        self.assertLess(rising.width, player.size[0])

    def test_spiked_obstacle_draws_inside_its_original_bounds(self):
        obstacle = game_object(100, 400, (60, 30))
        self.renderer.render("PLAYING", None, [], obstacles=[obstacle])
        screen = self.renderer.screen
        self.assertEqual(screen.get_at((130, 385))[:3], (65, 75, 90))
        self.assertEqual(screen.get_at((100, 377))[:3], (100, 110, 125))
        self.assertEqual(screen.get_at((159, 392))[:3], (100, 110, 125))
        self.assertNotEqual(screen.get_at((100, 370))[:3], (100, 110, 125))
        self.assertEqual(obstacle.size, (60, 30))
        self.assertEqual(obstacle.position, pygame.Vector2(100, 400))

    def test_draw_text_centers_by_default_and_allows_explicit_position(self):
        renderer = self.renderer
        with patch.object(renderer, "screen", wraps=renderer.screen) as screen:
            for value in ("Jump OverFlow", "게임 오버", "점수 123"):
                with self.subTest(text=value):
                    renderer.draw_text(value, (12, 90))
                    label, position = screen.blit.call_args.args
                    self.assertEqual(position[0] + label.get_width() / 2, screen.get_width() / 2)
                    self.assertEqual(position[1], 90)
                    renderer.draw_text(value, (12, 90), centered=False)
                    self.assertEqual(screen.blit.call_args.args[1], (12, 90))

    def test_all_hud_texts_use_default_alignment(self):
        renderer = self.renderer
        hud = HUD()
        for state in ("WAITING", "PAUSED", "SETTING", "GAME_OVER"):
            with self.subTest(state=state):
                hud.state = state
                with patch.object(renderer, "draw_text", wraps=renderer.draw_text) as draw:
                    renderer.render(state, None, [], hud=hud)
                for text in hud.get_ui_data()["texts"]:
                    draw.assert_any_call(text["text"], text["position"])

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
            ),
            items=ItemManager(),
            hud=hud,
            renderer=renderer,
        )
        with patch.object(renderer, "draw_text", wraps=renderer.draw_text) as text:
            for state in main.GameState:
                game.state = state
                main.render_frame(game)
                text.assert_any_call("Jump OverFlow", (12, 90))
                width, height = renderer.font.size("Start")
                rect = ui["buttons"][0]["rect"]
                text.assert_any_call(
                    "Start", (rect.centerx - width / 2, rect.centery - height / 2),
                    centered=False,
                )
                self.assertEqual(
                    renderer.screen.get_at((21, 151))[:3], (245, 250, 255)
                )
                if state in (main.GameState.PLAYING, main.GameState.GAME_OVER):
                    text.assert_any_call("Score: 10", (12, 12), centered=False)
                    text.assert_any_call("Best: 20", (12, 44), centered=False)
                text.reset_mock()

            renderer.camera.update(pygame.Vector2(500, 1_000_000), 1 / 60)
            main.render_frame(game)
            text.assert_any_call("Jump OverFlow", (12, 90))
            text.assert_any_call("Score: 10", (12, 12), centered=False)


if __name__ == "__main__":
    unittest.main()
