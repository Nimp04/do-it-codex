import unittest
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
        self.game.state = main.GameState.GAME_OVER
        main.handle_ui_action(self.game, "RESTART")
        self.assertEqual(self.game.state, main.GameState.PLAYING)
        self.assertEqual(self.game.player.reset.call_count, 2)
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
                      main.GameState.GAME_OVER):
            with self.subTest(state=state):
                self.game.state = state
                main.update_game(self.game, 0.02, [])
                self.game.hud.update.assert_called_with(state, self.game.player)
        self.game.level.update.assert_not_called()
        self.game.items.update.assert_not_called()
        self.game.player.update.assert_not_called()
        self.game.renderer.camera.update.assert_not_called()

    def test_camera_updates_before_player_checks_visible_bounds(self):
        calls = Mock()
        calls.attach_mock(self.game.player.update, "move")
        calls.attach_mock(self.game.renderer.camera.update, "camera")
        calls.attach_mock(self.game.renderer.get_world_bounds, "bounds")
        calls.attach_mock(self.game.player.is_alive, "alive")
        self.game.state = main.GameState.PLAYING
        self.game.player.is_alive.return_value = False
        main.update_game(self.game, 0.02, [])
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
