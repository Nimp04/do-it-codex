import unittest
from unittest.mock import Mock

import pygame

import item
from item import Item, ItemManager


class FakePlayer:
    def __init__(self):
        self.position = pygame.Vector2(0, 0)
        self.velocity = pygame.Vector2(0, 0)
        self.size = (40, 40)
        self.jump_speed = 800


def press(key_constant):
    """keys[key] 조회를 흉내 내는 딕셔너리를 돌려준다."""
    keys = {k: False for k in (item.USE_KEY,) + item.SWAP_KEYS}
    keys[key_constant] = True
    return keys


class CollectTests(unittest.TestCase):
    def test_collect_fills_first_empty_slot(self):
        manager = ItemManager()
        player = FakePlayer()
        world_item = Item((0, 0), item.GHOST)
        manager.add_item(world_item)

        manager.collect(world_item.id, player, level=None)

        self.assertEqual(player.item_slots, [item.GHOST, None])
        self.assertEqual(manager.get_items(), [])

    def test_collect_is_dropped_when_both_slots_full(self):
        manager = ItemManager()
        player = FakePlayer()
        player.item_slots = [item.GHOST, item.SHRINK]
        world_item = Item((0, 0), item.DOUBLE_JUMP)
        manager.add_item(world_item)

        manager.collect(world_item.id, player, level=None)

        self.assertEqual(player.item_slots, [item.GHOST, item.SHRINK])


class UseAndSwapTests(unittest.TestCase):
    def setUp(self):
        self.manager = ItemManager()
        self.player = FakePlayer()
        self.player.item_slots = [item.DOUBLE_JUMP, item.GHOST]
        self.manager._player = self.player

    def test_use_key_consumes_slot_one_and_applies_double_jump(self):
        with unittest.mock.patch.object(
            pygame.key, "get_pressed", return_value=press(item.USE_KEY)
        ):
            self.manager.update(1 / 60)

        self.assertIsNone(self.player.item_slots[0])
        self.assertEqual(self.player.velocity.y, self.player.jump_speed)

    def test_alt_key_swaps_slots(self):
        with unittest.mock.patch.object(
            pygame.key, "get_pressed", return_value=press(pygame.K_LALT)
        ):
            self.manager.update(1 / 60)

        self.assertEqual(self.player.item_slots, [item.GHOST, item.DOUBLE_JUMP])

    def test_held_use_key_only_triggers_once(self):
        keys = press(item.USE_KEY)
        with unittest.mock.patch.object(pygame.key, "get_pressed", return_value=keys):
            self.manager.update(1 / 60)
            self.player.item_slots[0] = item.DOUBLE_JUMP  # 다시 채워도
            self.manager.update(1 / 60)  # 키를 떼지 않으면 다시 사용되지 않는다

        self.assertEqual(self.player.item_slots[0], item.DOUBLE_JUMP)


class TimedEffectTests(unittest.TestCase):
    def setUp(self):
        self.manager = ItemManager()
        self.player = FakePlayer()
        self.manager._player = self.player

    def test_ghost_flag_reverts_after_duration(self):
        self.manager._apply_effect(self.player, item.GHOST)
        self.assertTrue(self.player.is_ghost)

        self.manager._tick_ghost(self.player, item.GHOST_DURATION + 0.1)

        self.assertFalse(self.player.is_ghost)

    def test_shrink_restores_original_size_after_duration(self):
        self.manager._apply_effect(self.player, item.SHRINK)
        self.assertEqual(self.player.size, item.SHRINK_SIZE)

        self.manager._tick_shrink(self.player, item.SHRINK_DURATION + 0.1)

        self.assertEqual(self.player.size, (40, 40))


class ResetTests(unittest.TestCase):
    def test_reset_clears_world_items_and_inventory_and_effects(self):
        manager = ItemManager()
        player = FakePlayer()
        manager._player = player
        manager._apply_effect(player, item.SHRINK)
        manager.add_item(Item((0, 0), item.GHOST))

        manager.reset()

        self.assertEqual(manager.get_items(), [])
        self.assertEqual(player.item_slots, [None, None])
        self.assertEqual(player.size, (40, 40))


if __name__ == "__main__":
    unittest.main()
