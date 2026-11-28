import unittest
from collections import defaultdict
from unittest.mock import Mock, patch

import pygame

import main


class MainTests(unittest.TestCase):
    def setUp(self):
        self.game = main.Game(
            player=Mock(), level=Mock(), items=Mock(), hud=Mock(), renderer=Mock()
        )
        self.game.hud.handle_event.return_value = None
        self.game.player.check_collisions.return_value = []
        self.game.player.is_alive.return_value = True

    def test_ui_transitions_and_reset(self):
        main.handle_ui_action(self.game, "OPEN_SETTING")
        self.assertEqual(self.game.state, main.GameState.SETTING)
        main.handle_ui_action(self.game, "START_GAME")
        self.assertEqual(self.game.state, main.GameState.SETTING)
        main.handle_ui_action(self.game, "RETURN_HOME")
        main.handle_ui_action(self.game, "START_GAME")
        self.assertEqual(self.game.state, main.GameState.PLAYING)
        self.game.player.reset.assert_called_once_with(
            self.game.level.get_spawn_position.return_value
        )
        for module in (self.game.level, self.game.items, self.game.hud,
                       self.game.renderer):
            module.reset.assert_called_once_with()
        for state in (main.GameState.GAME_OVER, main.GameState.PAUSED):
            with self.subTest(state=state):
                self.game.state = state
                self.game.player.reset.reset_mock()
                main.handle_ui_action(self.game, "RESTART")
                self.assertEqual(self.game.state, main.GameState.PLAYING)
                self.game.player.reset.assert_called_once_with(
                    self.game.level.get_spawn_position.return_value
                )
        with self.assertRaises(ValueError):
            main.handle_ui_action(self.game, "MISSPELLED_ACTION")

    def test_quit_takes_priority_over_other_events(self):
        events = [pygame.event.Event(pygame.MOUSEBUTTONDOWN),
                  pygame.event.Event(pygame.QUIT)]
        self.assertFalse(main.handle_events(self.game, events))
        self.game.hud.handle_event.assert_not_called()
        self.assertEqual(self.game.state, main.GameState.WAITING)

    def test_paused_states_update_only_hud(self):
        for state in (main.GameState.WAITING, main.GameState.SETTING,
                      main.GameState.GAME_OVER, main.GameState.PAUSED):
            with self.subTest(state=state):
                self.game.state = state
                main.update_game(self.game, 0.02, [])
                self.game.hud.update.assert_called_with(state, self.game.player)
        self.game.level.update.assert_not_called()
        self.game.items.update.assert_not_called()
        self.game.player.update.assert_not_called()
        self.game.renderer.camera.update.assert_not_called()
        self.game.player.check_collisions.assert_not_called()

    def test_escape_toggles_only_playing_and_paused_and_ignores_repeat(self):
        escape = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        for initial, expected in (
            (main.GameState.PLAYING, main.GameState.PAUSED),
            (main.GameState.PAUSED, main.GameState.PLAYING),
            (main.GameState.WAITING, main.GameState.WAITING),
            (main.GameState.SETTING, main.GameState.SETTING),
            (main.GameState.GAME_OVER, main.GameState.GAME_OVER),
        ):
            with self.subTest(initial=initial):
                self.game.state = initial
                self.assertTrue(main.handle_events(self.game, [escape]))
                self.assertEqual(self.game.state, expected)
        self.game.state = main.GameState.PAUSED
        main.handle_events(self.game, [pygame.event.Event(
            pygame.KEYDOWN, key=pygame.K_ESCAPE, repeat=True
        )])
        self.assertEqual(self.game.state, main.GameState.PAUSED)
        self.game.player.reset.assert_not_called()

    def test_quit_while_paused_takes_priority_over_resume(self):
        self.game.state = main.GameState.PAUSED
        self.assertFalse(main.handle_events(self.game, [
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE),
            pygame.event.Event(pygame.QUIT),
        ]))
        self.assertEqual(self.game.state, main.GameState.PAUSED)

    def test_pause_buttons_preserve_progress_and_home_start_resets(self):
        from item import GHOST, Item

        with patch.dict("os.environ", {"SDL_VIDEODRIVER": "dummy"}):
            game = main.initialize_game()
        self.addCleanup(pygame.quit)
        main.handle_ui_action(game, "START_GAME")
        game.hud.update(game.state, game.player)
        game.player.position.y += 300
        game.hud.update(game.state, game.player)
        item = Item(game.player.position, GHOST)
        game.items.add_item(item)
        game.items.collect(item.id, game.player, game.level)
        with patch.object(pygame.key, "get_pressed", return_value=defaultdict(
            bool, {pygame.K_SPACE: True}
        )):
            game.items.update(0)

        position = game.player.position.copy()
        velocity = game.player.velocity.copy()
        camera = game.renderer.camera.position.copy()
        score = game.hud.current_score
        timer = game.items._ghost_remaining
        platforms = [(p.position.copy(), p.size) for p in game.level.get_platforms()]
        self.assertEqual(score, 3)
        self.assertTrue(game.player.is_ghost)

        main.handle_events(game, [pygame.event.Event(
            pygame.KEYDOWN, key=pygame.K_ESCAPE
        )])
        main.update_game(game, 100, defaultdict(bool))
        self.assertEqual(game.state, main.GameState.PAUSED)
        self.assertEqual(game.player.position, position)
        self.assertEqual(game.player.velocity, velocity)
        self.assertEqual(game.renderer.camera.position, camera)
        self.assertEqual(game.items._ghost_remaining, timer)
        self.assertEqual(game.hud.current_score, score)
        self.assertEqual(platforms, [(p.position, p.size) for p in game.level.get_platforms()])

        def click_button(text):
            button = next(b for b in game.hud.get_ui_data()["buttons"]
                          if b["text"] == text)
            return main.handle_events(game, [pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, pos=button["rect"].center, button=1
            )])

        self.assertTrue(click_button("계속하기"))
        self.assertEqual(game.state, main.GameState.PLAYING)
        self.assertEqual(game.player.position, position)
        self.assertEqual(game.hud.current_score, score)
        main.update_game(game, 0, defaultdict(bool))
        self.assertEqual(game.player.position, position)
        self.assertEqual(game.hud.current_score, score)
        main.handle_events(game, [pygame.event.Event(
            pygame.KEYDOWN, key=pygame.K_ESCAPE
        )])
        main.update_game(game, 0, defaultdict(bool))
        self.assertTrue(click_button("홈으로"))
        self.assertEqual(game.state, main.GameState.WAITING)
        self.assertEqual(game.player.position, position)
        main.handle_ui_action(game, "START_GAME")
        self.assertEqual(game.state, main.GameState.PLAYING)
        self.assertEqual(game.player.position, game.level.get_spawn_position())
        self.assertEqual(game.hud.current_score, 0)
        self.assertEqual(game.hud.high_score, score)
        self.assertFalse(game.player.is_ghost)
        self.assertEqual(game.items._ghost_remaining, 0)
        self.assertEqual(game.player.item_slots, [None, None])
        self.assertEqual(game.renderer.camera.position, (0, 0))

    def test_camera_updates_before_player_checks_visible_bounds(self):
        calls = Mock()
        calls.attach_mock(self.game.player.update, "move")
        calls.attach_mock(self.game.renderer.camera.update, "camera")
        calls.attach_mock(self.game.renderer.get_world_bounds, "bounds")
        calls.attach_mock(self.game.player.is_alive, "alive")
        self.game.state = main.GameState.PLAYING
        self.game.player.is_alive.return_value = False
        main.update_game(self.game, 0.02, [])
        self.game.renderer.camera.update.assert_called_once_with(
            self.game.player.position, 0.02
        )
        self.assertEqual(
            [call[0] for call in calls.mock_calls],
            ["move", "camera", "bounds", "alive"],
        )
        self.assertEqual(self.game.state, main.GameState.GAME_OVER)
        self.game.player.is_alive.assert_called_once_with(
            self.game.renderer.get_world_bounds.return_value
        )
        self.game.hud.update.assert_called_once_with(
            main.GameState.GAME_OVER, self.game.player
        )

    def test_item_effects_are_delegated_and_death_stops_event_processing(self):
        self.game.state = main.GameState.PLAYING
        self.game.player.check_collisions.return_value = [
            {"type": "ITEM_COLLECTED", "item_id": 7},
            {"type": "GAME_OVER"},
            {"type": "ITEM_COLLECTED", "item_id": 8},
        ]
        main.update_game(self.game, 0.02, [])
        self.game.items.collect.assert_called_once_with(
            7, self.game.player, self.game.level
        )
        self.assertEqual(self.game.state, main.GameState.GAME_OVER)
        self.game.player.is_alive.assert_not_called()

    def test_main_cleans_up_on_quit_and_initialization_failure(self):
        with patch.object(main, "initialize_game", return_value=self.game), \
             patch.object(pygame.event, "get", return_value=[
                 pygame.event.Event(pygame.QUIT)
             ]) as get_events, patch.object(pygame, "quit") as quit_game:
            main.main()
            get_events.assert_called_once_with()
            self.game.renderer.render.assert_not_called()
            quit_game.assert_called_once_with()
        with patch.object(main, "initialize_game", side_effect=RuntimeError), \
             patch.object(pygame, "quit") as quit_game:
            with self.assertRaises(RuntimeError):
                main.main()
            quit_game.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
