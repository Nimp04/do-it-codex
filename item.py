import pygame

class Item:
    def __init__(self, x, y, image):
        self.rect = pygame.Rect(x, y, 32, 32)
        self.image = image

class ItemManager:

    def __init__(self):
        self.items = []

    def reset(self):
        self.items.clear()

    def add_item(self, item):
        self.items.append(item)

    def get_items(self):
        return self.items

    def update(self, player_rect):
        for item in self.items[:]:
            if player_rect.colliderect(item.rect):
                self.items.remove(item)