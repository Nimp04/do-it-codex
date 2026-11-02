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
    "PAUSED": [ #esc눌렀을 때 상태(임의로 PAUSED로 설정)
        ("계속하기", "RESUME", pygame.Rect(200, 380, 200, 56)),
        ("나가기", "RETURN_HOME", pygame.Rect(200, 450, 200, 56)),
    ],
}


TITLES = {  # PLAYING에는 제목이 없으므로 키도 없음
    "WAITING": "Jump OverFlow",
    "SETTING": "설정",
    "GAME_OVER": "게임 오버",
    "PAUSED": "일시정지",
}


class HUD:
    def __init__(self):
        self.current_score = 0
        self.high_score = 0
        self.state = "WAITING"
        self.baseline_y = None

    def reset(self):  # 한 판 시작: 현재 점수만 0으로, 최고 점수는 남김
        self.current_score = 0
        self.baseline_y = None

    def update(self, game_state, player):  # 매 프레임 main이 호출함
        self.state = str(game_state)
        if self.state == "PLAYING":
            # 리셋 후 첫 프레임의 위치를 기준점으로 삼아, 스폰 좌표와 무관하게
            # 거기서 "올라간 높이"만 점수로 센다. max라서 떨어져도 줄지 않음
            if self.baseline_y is None:
                self.baseline_y = player.position.y
            climbed = player.position.y - self.baseline_y
            self.current_score = max(self.current_score, int(climbed / 100))
            self.high_score = max(self.high_score, self.current_score)

    def handle_event(self, event, game_state=None):  # 버튼 클릭 → Action, 없으면 None
        # game_state는 설계 문서상 생략 가능. 없으면 update가 받아둔 상태를 씀
        if event.type != pygame.MOUSEBUTTONDOWN:
            return None
        state = self.state if game_state is None else str(game_state)
        for _, action, rect in BUTTONS.get(state, ()):
            if rect.collidepoint(event.pos):
                return action
        return None

    def get_ui_data(self):  # Renderer가 그릴 정보만 넘김(그리기는 render.py 담당)
        data = {
            "current_score": self.current_score,
            "high_score": self.high_score,
        }
        title = TITLES.get(self.state)
        if title:  # 제목과 버튼은 해당 상태일 때만 키를 넣음
            texts = [{"text": title, "position": (300, 300)}]
            if self.state == "GAME_OVER":
                texts.append(
                    {"text": f"점수 {self.current_score}", "position": (300, 345)}
                )
            data["texts"] = texts

        buttons = BUTTONS.get(self.state)
        if buttons:
            data["buttons"] = [
                {"text": text, "rect": rect} for text, _, rect in buttons
            ]
        return data
