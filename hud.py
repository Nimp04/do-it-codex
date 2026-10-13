"""점수와 UI 상태를 관리한다. Game State와 Player 상태는 직접 바꾸지 않는다."""

import pygame

BUTTONS = {  # 상태별 버튼: (표시 텍스트, main에 돌려줄 Action, 클릭 판정 화면 영역)
    "WAITING": [
        ("시작", "START_GAME", pygame.Rect(200, 380, 200, 56)),
        ("설정", "OPEN_SETTING", pygame.Rect(200, 450, 200, 56)),
    ],
    "SETTING": [
        ("돌아가기", "RETURN_HOME", pygame.Rect(200, 450, 200, 56)),
    ],
    "GAME_OVER": [
        ("다시하기", "RESTART", pygame.Rect(200, 380, 200, 56)),
        ("홈으로", "RETURN_HOME", pygame.Rect(200, 450, 200, 56)),
    ],
}


TITLES = {  # PLAYING에는 제목이 없으므로 키도 없다
    "WAITING": "Jump OverFlow",
    "SETTING": "설정",
    "GAME_OVER": "게임 오버",
}


class HUD:
    def __init__(self):
        self.current_score = 0
        self.high_score = 0
        self.state = "WAITING"

    def reset(self):  # 한 판 시작: 현재 점수만 0으로, 최고 점수는 남긴다
        self.current_score = 0

    def update(self, game_state, player):  # 매 프레임 main이 호출한다
        self.state = str(game_state)
        if self.state == "PLAYING":
            # 점수 = 올라간 월드 높이 / 100. max라서 떨어져도 줄지 않는다.
            self.current_score = max(self.current_score, int(player.position.y / 100))
            self.high_score = max(self.high_score, self.current_score)

    def handle_event(self, event, game_state=None):  # 버튼 클릭 → Action, 없으면 None
        # game_state는 설계 문서상 생략 가능하다. 없으면 update가 받아둔 상태를 쓴다.
        if event.type != pygame.MOUSEBUTTONDOWN:
            return None
        state = self.state if game_state is None else str(game_state)
        for _, action, rect in BUTTONS.get(state, ()):
            if rect.collidepoint(event.pos):
                return action
        return None

    def get_ui_data(self):  # Renderer가 그릴 정보만 넘긴다 (그리기는 render.py 담당)
        data = {
            "current_score": self.current_score,
            "high_score": self.high_score,
        }
        title = TITLES.get(self.state)
        if title:  # 제목과 버튼은 해당 상태일 때만 키를 넣는다
            texts = [{"text": title, "position": (300, 300)}]
            if self.state == "GAME_OVER":
                texts.append(
                    {"text": f"점수 {self.current_score}", "position": (300, 330)}
                )
            data["texts"] = texts

        buttons = BUTTONS.get(self.state)
        if buttons:
            data["buttons"] = [
                {"text": text, "rect": rect} for text, _, rect in buttons
            ]
        return data
