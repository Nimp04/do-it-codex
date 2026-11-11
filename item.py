"""월드 아이템과 2칸 인벤토리를 관리한다.

인벤토리는 player.item_slots(길이 2 리스트, 빈 칸은 None)에 저장되며
hud.py가 이 값을 읽어 itemHUD를 그린다. 효과 적용(player 상태 변경)은
여기서만 담당한다.
"""

import pygame

DOUBLE_JUMP = "DOUBLE_JUMP"
GHOST = "GHOST"
SHRINK = "SHRINK"

ITEM_SIZE = (32, 32)

# 가정값: "사용 키"가 별도로 정해진 바 없어 스페이스바로 임시 지정.
USE_KEY = pygame.K_SPACE
# 교체 키는 사용자가 지정한 대로 알트(좌/우 모두 인정).
SWAP_KEYS = (pygame.K_LALT, pygame.K_RALT)

# 가정값: 지속시간이 명시되지 않아 5초로 임시 지정.
GHOST_DURATION = 5.0
SHRINK_DURATION = 5.0
SHRINK_SIZE = (20, 20)


class Item:
    """월드에 떠 있는 아이템. id는 ItemManager.add_item이 부여한다."""

    def __init__(self, position, item_type, size=ITEM_SIZE):
        self.id = None
        self.position = pygame.Vector2(position)
        self.size = size
        self.item_type = item_type


class ItemManager:
    def __init__(self):
        self.items = []
        self._next_id = 1
        self._player = None
        self._use_pressed = False
        self._swap_pressed = False
        self._ghost_remaining = 0.0
        self._shrink_remaining = 0.0
        self._pre_shrink_size = None

    def reset(self):
        self.items.clear()
        self._next_id = 1
        self._use_pressed = False
        self._swap_pressed = False
        if self._player is not None:
            self._revert_ghost(self._player)
            self._revert_shrink(self._player)
            self._player.item_slots = [None, None]

    def add_item(self, item):
        item.id = self._next_id
        self._next_id += 1
        self.items.append(item)

    def get_items(self):
        return self.items

    def collect(self, item_id, player, level):
        self._player = player
        item = next((i for i in self.items if i.id == item_id), None)
        if item is None:
            return
        self.items.remove(item)
        slots = self._ensure_slots(player)
        if None in slots:  # 둘 다 차있으면 획득은 버려진다(아이템 자체는 이미 제거됨)
            slots[slots.index(None)] = item.item_type

    def update(self, dt):
        player = self._player
        if player is None:
            return

        self._tick_ghost(player, dt)
        self._tick_shrink(player, dt)

        keys = pygame.key.get_pressed()
        use_down = bool(keys[USE_KEY])
        swap_down = any(keys[key] for key in SWAP_KEYS)

        if use_down and not self._use_pressed:
            self._use_first_slot(player)
        if swap_down and not self._swap_pressed:
            slots = self._ensure_slots(player)
            slots[0], slots[1] = slots[1], slots[0]

        self._use_pressed = use_down
        self._swap_pressed = swap_down

    def _ensure_slots(self, player):
        slots = getattr(player, "item_slots", None)
        if not isinstance(slots, list) or len(slots) != 2:
            slots = [None, None]
            player.item_slots = slots
        return slots

    def _use_first_slot(self, player):
        slots = self._ensure_slots(player)
        item_type = slots[0]
        if item_type is None:
            return
        slots[0] = None
        self._apply_effect(player, item_type)

    def _apply_effect(self, player, item_type):
        if item_type == DOUBLE_JUMP:
            # 다음 player.update()의 _move가 velocity.y로 state도 재계산한다.
            player.velocity.y = player.jump_speed
        elif item_type == GHOST:
            player.is_ghost = True
            self._ghost_remaining = GHOST_DURATION
        elif item_type == SHRINK:
            if self._shrink_remaining <= 0:
                self._pre_shrink_size = player.size
            player.size = SHRINK_SIZE
            self._shrink_remaining = SHRINK_DURATION

    def _tick_ghost(self, player, dt):
        if self._ghost_remaining <= 0:
            return
        self._ghost_remaining -= dt
        if self._ghost_remaining <= 0:
            self._revert_ghost(player)

    def _tick_shrink(self, player, dt):
        if self._shrink_remaining <= 0:
            return
        self._shrink_remaining -= dt
        if self._shrink_remaining <= 0:
            self._revert_shrink(player)

    def _revert_ghost(self, player):
        self._ghost_remaining = 0.0
        player.is_ghost = False

    def _revert_shrink(self, player):
        self._shrink_remaining = 0.0
        if self._pre_shrink_size is not None:
            player.size = self._pre_shrink_size
            self._pre_shrink_size = None
