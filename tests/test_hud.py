import unittest
from unittest.mock import Mock

import pygame

from hud import HUD


class ScoreTests(unittest.TestCase):
    def test_score_keeps_highest_point_reached(self):
        hud = HUD()
        player = Mock()

        player.position = pygame.Vector2(100, 450)
        hud.update("PLAYING", player)
        self.assertEqual(hud.get_ui_data()["current_score"], 4)

        # 아래로 떨어져도 점수는 줄지 않는다
        player.position = pygame.Vector2(100, 200)
        hud.update("PLAYING", player)
        self.assertEqual(hud.get_ui_data()["current_score"], 4)

    def test_reset_clears_current_score_but_keeps_high_score(self):
        hud = HUD()
        player = Mock()
        player.position = pygame.Vector2(0, 800)
        hud.update("PLAYING", player)

        hud.reset()

        data = hud.get_ui_data()
        self.assertEqual(data["current_score"], 0)
        self.assertEqual(data["high_score"], 8)


class ButtonTests(unittest.TestCase):
    def find_button(self, hud, text):
        for button in hud.get_ui_data().get("buttons", ()):
            if button["text"] == text:
                return button
        raise AssertionError(f"'{text}' 버튼이 없다")

    def click(self, button):
        return pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, pos=button["rect"].center, button=1
        )

    def test_start_button_in_waiting_returns_start_game(self):
        hud = HUD()
        hud.update("WAITING", Mock())

        button = self.find_button(hud, "시작")

        self.assertEqual(hud.handle_event(self.click(button), "WAITING"), "START_GAME")

    def test_every_state_button_returns_its_action(self):
        cases = [
            ("WAITING", "설정", "OPEN_SETTING"),
            ("SETTING", "돌아가기", "RETURN_HOME"),
            ("GAME_OVER", "다시하기", "RESTART"),
            ("GAME_OVER", "홈으로", "RETURN_HOME"),
        ]
        for state, text, action in cases:
            with self.subTest(state=state, text=text):
                hud = HUD()
                hud.update(state, Mock())

                button = self.find_button(hud, text)

                self.assertEqual(hud.handle_event(self.click(button), state), action)


class TextTests(unittest.TestCase):
    def texts_of(self, hud):
        return [text["text"] for text in hud.get_ui_data().get("texts", ())]

    def test_waiting_shows_title(self):
        hud = HUD()
        hud.update("WAITING", Mock())

        self.assertIn("Jump OverFlow", self.texts_of(hud))

    def test_game_over_shows_final_score(self):
        hud = HUD()
        player = Mock()
        player.position = pygame.Vector2(0, 1234)
        hud.update("PLAYING", player)

        hud.update("GAME_OVER", player)

        self.assertIn("점수 12", self.texts_of(hud))


class NoRequestTests(unittest.TestCase):
    """설계 문서: 요청이 없으면 None을 반환한다."""

    def test_returns_none_without_a_button_request(self):
        hud = HUD()
        hud.update("WAITING", Mock())
        cases = {
            "버튼 밖 클릭": pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, pos=(5, 5), button=1),
            "키 입력": pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE),
        }

        for name, event in cases.items():
            with self.subTest(name):
                self.assertIsNone(hud.handle_event(event, "WAITING"))

    def test_playing_shows_score_without_buttons(self):
        hud = HUD()
        player = Mock()
        player.position = pygame.Vector2(0, 700)
        hud.update("PLAYING", player)

        data = hud.get_ui_data()

        self.assertEqual(data["current_score"], 7)
        self.assertNotIn("buttons", data)


if __name__ == "__main__":
    unittest.main()
