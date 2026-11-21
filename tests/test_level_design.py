import unittest

import level_design
from item import ItemManager
from level_design import Level


class LevelDesignTests(unittest.TestCase):
    def setUp(self):
        self.level = Level()
        # 충분히 많은 행을 생성해 확률적 요소가 모두 나오게 한다.
        self.level.update(0, 20000)

    def test_moving_platform_ratio(self):
        level = Level()
        # 시드가 고정되지 않으므로 표본을 크게 잡아 비율이 흔들리지 않게 한다.
        for _ in range(1000):
            level._generate_next_row()
        platforms = level.get_platforms()
        moving = [p for p in platforms if p.type == "moving"]
        self.assertAlmostEqual(
            len(moving) / len(platforms),
            level_design.MOVING_PLATFORM_CHANCE,
            delta=0.1,
        )

    def test_moving_speed_grows_with_height_and_is_capped(self):
        level = Level()
        # 삭제 없이 행을 직접 생성해 낮은 행부터 상한 이후까지 모두 확인한다.
        for _ in range(200):
            level._generate_next_row()
        moving = [p for p in level.get_platforms() if p.type == "moving"]

        jitter = level_design.MOVING_SPEED_JITTER
        max_speed = level_design.MOVING_MAX_SPEED
        for p in moving:
            base = (
                level_design.MOVING_BASE_SPEED
                + (p.position.y - level_design.START_Y)
                * level_design.MOVING_SPEED_PER_HEIGHT
            )
            speed = abs(p.velocity_x)
            self.assertLessEqual(speed, max_speed)
            self.assertGreaterEqual(speed, min(base * (1 - jitter), max_speed))
            self.assertLessEqual(speed, base * (1 + jitter))

        def average_speed(rows):
            ys = {level_design.START_Y + r * level_design.ROW_GAP for r in rows}
            speeds = [abs(p.velocity_x) for p in moving if p.position.y in ys]
            return sum(speeds) / len(speeds)

        # 위쪽 행일수록 평균 속도가 빨라지고, 상한 이후에는 최고 속도에 붙는다.
        self.assertLess(average_speed(range(1, 21)), average_speed(range(41, 61)))
        self.assertTrue(any(abs(p.velocity_x) == max_speed for p in moving))

        # 같은 높이 대에서도 편차로 속도가 서로 다르다.
        low = [abs(p.velocity_x) for p in moving if p.position.y < 2750]
        self.assertGreater(len(set(low)), 1)

    def test_moving_platform_stays_in_world(self):
        for _ in range(600):
            self.level.update(1 / 60, 0)
        right = level_design.WORLD_WIDTH - level_design.PLATFORM_WIDTH
        for p in self.level.get_platforms():
            self.assertTrue(0 <= p.position.x <= right)

    def test_obstacles_off_platforms_and_static_paths(self):
        obstacles = self.level.get_obstacles()
        self.assertTrue(obstacles)
        for o in obstacles:
            self.assertLess(o.size[0], level_design.PLATFORM_WIDTH)
            nearby = [
                p for p in self.level.get_platforms()
                if abs(p.position.y - o.position.y) <= level_design.ROW_GAP / 2
            ]
            for p in nearby:
                # 장애물은 위아래 어떤 발판과도 세로로 겹치지 않는다.
                self.assertTrue(
                    o.position.y >= p.position.y + p.size[1]
                    or o.position.y + o.size[1] <= p.position.y
                )
                if p.type == "moving":
                    continue
                # 고정 발판의 수직 통로는 비워 둔다.
                self.assertTrue(
                    o.position.x + o.size[0] <= p.position.x - level_design.PLAYER_SIZE[0]
                    or o.position.x >= p.position.x + p.size[0] + level_design.PLAYER_SIZE[0]
                )

    def test_items_placed_on_static_platforms_and_cleaned_up(self):
        manager = ItemManager()
        level = Level(manager)
        for _ in range(300):
            level._generate_next_row()
        items = manager.get_items()
        self.assertTrue(items)
        self.assertEqual(len({i.id for i in items}), len(items))
        tops = {
            (p.position.x, p.position.y + p.size[1])
            for p in level.get_platforms() if p.type == "normal"
        }
        for i in items:
            self.assertIn(i.item_type, level_design.ITEM_TYPES)
            platform_x = i.position.x - (level_design.PLATFORM_WIDTH - i.size[0]) / 2
            top = i.position.y - level_design.ITEM_FLOAT
            self.assertIn((platform_x, top), tops)

        level.update(0, 1_000_000)
        cleanup_y = 1_000_000 - level_design.CLEANUP_BELOW
        self.assertTrue(all(i.position.y >= cleanup_y for i in manager.get_items()))

    def test_reset_makes_new_map(self):
        level = Level()
        first = [(p.position.x, p.type) for p in level.get_platforms()]
        level.reset()
        second = [(p.position.x, p.type) for p in level.get_platforms()]
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
