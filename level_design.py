from dataclasses import dataclass
import pygame

@dataclass
class Platform:
    """1. Platform dataclass 정의 (위치, 크기, 타입, 상태)"""
    position: pygame.Vector2
    size: tuple[int, int]
    type: str = "normal"
    state: str = "active"

    @property
    def rect(self) -> pygame.Rect:
        """플레이어 충돌 처리를 쉽게 하기 위한 Pygame Rect 객체 반환"""
        return pygame.Rect(self.position.x, self.position.y, self.size[0], self.size[1])


class Level:
    def __init__(self):
        self.platforms: list[Platform] = []
        self.reset()

    def reset(self):
        """3. reset(self): 게임 시작 또는 리셋 시 발판 초기화 로직"""
        # main.py의 화면 크기(600x800)를 고려하여 테스트용 발판 배치
        self.platforms = [
            Platform(position=pygame.Vector2(0, 750), size=(600, 50), type="normal"),  # 바닥 발판
            Platform(position=pygame.Vector2(100, 600), size=(150, 20), type="normal"), # 공중 발판 1
            Platform(position=pygame.Vector2(350, 480), size=(150, 20), type="normal"), # 공중 발판 2
            Platform(position=pygame.Vector2(200, 350), size=(150, 20), type="normal"), # 공중 발판 3
        ]

    def update(self, dt: float):
        """3. update(self, dt): 발판 상태 갱신 로직 (추후 움직이는 발판 확장용)"""
        # 현재 이슈 범위에서는 별도의 동적 변화가 없으므로 비워둡니다.
        pass

    def get_platforms(self) -> list[Platform]:
        """2. get_platforms(self): player.py 등 다른 모듈에 발판 리스트 반환 (완료 조건)"""
        return self.platforms