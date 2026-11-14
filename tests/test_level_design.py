import unittest

import level_design
from item import ItemManager
from level_design import Level


class LevelDesignTests(unittest.TestCase):
    def setUp(self):
        self.level = Level()
        # 충분히 많은 행을 생성해 확률적 요소가 모두 나오게 한다.
        self.level.update(0, 20000)

    def test_moving_platform_ratio_and_speed_tiers(self):
        platforms = self.level.get_platforms()
        moving = [p for p in platforms if p.type == "moving"]
        self.assertAlmostEqual(
            len(moving) / len(platforms),
            level_design.MOVING_PLATFORM_CHANCE,
            delta=0.1,
        )
        jitter = level_design.MOVING_SPEED_JITTER
        used_tiers = set()
        for p in moving:
            speed = abs(p.velocity_x)
            tier = next(
                t for t in level_design.MOVING_SPEED_TIERS
                if t * (1 - jitter) <= speed <= t * (1 + jitter)
            )
            used_tiers.add(tier)
        # 느림/보통/빠름이 모두 나와야 속도 차이가 체감된다.
        self.assertEqual(used_tiers, set(level_design.MOVING_SPEED_TIERS))

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
