"""월드 좌표는 (0, 0)에서 시작하며 x는 오른쪽, y는 위쪽으로 증가한다."""

FPS = 60

SCREEN_WIDTH = 600
SCREEN_HEIGHT = 800
SCREEN_SIZE = (SCREEN_WIDTH, SCREEN_HEIGHT)

# 화면 해상도와 독립적인 월드 단위이며, 위쪽 높이에는 상한이 없다.
WORLD_ORIGIN = (0, 0)
WORLD_WIDTH = 600  # 임시 너비. 이동 속도와 발판 배치에 맞춰 조정한다.

CAMERA_FOLLOW_THRESHOLD = 300  # 임시 값. 플레이어와 카메라의 월드 y 차이.
CAMERA_FOLLOW_DIVISOR = 10  # 60FPS 기준 프레임당 남은 거리의 1/10씩 따라간다.

BACKGROUND_SCROLL_RATIO = 0.25  # 임시 값. 카메라 이동량 중 배경에 반영할 비율.
