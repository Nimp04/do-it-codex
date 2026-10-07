import pygame

from player import Player
from level_design import Level
from render import Renderer

pygame.init()
screen = pygame.display.set_mode((600, 800))
clock = pygame.time.Clock()

player = Player(100,150)
level = Level()
render = Renderer(screen)

running = True
while(running): 
    dt = clock.tick(60)/1000
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    key = pygame.key.get_pressed()
    player.update(key,dt)
    platforms=level.get_platforms()
    running=player.check_platforms(platforms)
    render.render(player,platforms)

pygame.quit()