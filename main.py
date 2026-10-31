"""게임 상태를 소유하고 각 모듈의 생성, 호출 순서와 데이터 전달을 관리한다."""

from dataclasses import dataclass
from enum import StrEnum

import pygame

from config import FPS


class GameState(StrEnum):
    WAITING = "WAITING"
    SETTING = "SETTING"
    PLAYING = "PLAYING"
    GAME_OVER = "GAME_OVER"


@dataclass
class Game:
    player: object
    level: object
    items: object
    hud: object
    renderer: object
    state: GameState = GameState.WAITING


def initialize_game() -> Game:
    # shortcut: 기능 모듈은 개발 중이다. 완성 후 아래 호출 계약으로 연동 검증한다.
    from player import Player
    from level_design import Level
    from item import ItemManager
    from hud import HUD
    from render import Renderer

    renderer = Renderer()
    return Game(
        player=Player(),
        level=Level(),
        items=ItemManager(),
        hud=HUD(),
        renderer=renderer,
    )


def reset_game(game: Game):
    game.level.reset()
    game.items.reset()
    game.player.reset(game.level.get_spawn_position())
    game.hud.reset()
    game.renderer.reset()


def handle_ui_action(game: Game, action: str | None):
    match game.state, action:
        case (GameState.WAITING, "START_GAME") | (GameState.GAME_OVER, "RESTART"):
            reset_game(game)
            game.state = GameState.PLAYING
        case GameState.WAITING, "OPEN_SETTING":
            game.state = GameState.SETTING
        case (GameState.SETTING | GameState.GAME_OVER), "RETURN_HOME":
            game.state = GameState.WAITING
        case _, None | "START_GAME" | "RESTART" | "OPEN_SETTING" | "RETURN_HOME":
            return
        case _:
            raise ValueError(f"Unknown HUD action: {action!r}")


def handle_events(game: Game, events: list) -> bool:
    if any(event.type == pygame.QUIT for event in events):
        return False

    for event in events:
        action = game.hud.handle_event(event, game.state)
        handle_ui_action(game, action)
    return True


def handle_game_event(game: Game, event: dict):
    """Player가 반환하는 충돌 이벤트를 해당 모듈에 전달한다.

    {"type": "GAME_OVER"}
    {"type": "ITEM_COLLECTED", "item_id": 아이템 식별값}
    ItemManager.collect(item_id, player, level)이 제거와 효과 적용을 담당한다.
    """
    match event["type"]:
        case "GAME_OVER":
            game.state = GameState.GAME_OVER
        case "ITEM_COLLECTED":
            game.items.collect(event["item_id"], game.player, game.level)
        case _:
            raise ValueError(f"Unknown game event: {event!r}")


def update_game(game: Game, dt: float, input_state):
    """게임 로직은 각 모듈이 처리하고 메인은 결과로 게임 상태를 갱신한다.

    Renderer.get_world_bounds()는 (left, bottom, right, top) 월드 범위를 반환한다.
    Player.is_alive(world_bounds)는 사망·화면 하단 추락을 확인해 생존 여부를 반환한다.
    """
    if game.state == GameState.PLAYING:
        game.level.update(dt, game.player.position.y)
        game.items.update(dt)
        game.player.update(dt, input_state)

        collision_events = game.player.check_collisions(
            game.level.get_platforms(),
            game.level.get_obstacles(),
            game.level.get_enemies(),
            game.items.get_items(),
        )
        for event in collision_events:
            handle_game_event(game, event)
            if game.state == GameState.GAME_OVER:
                break

        game.renderer.camera.update(game.player.position)
        if game.state == GameState.PLAYING:
            world_bounds = game.renderer.get_world_bounds()
            if not game.player.is_alive(world_bounds):
                game.state = GameState.GAME_OVER

    game.hud.update(game.state, game.player)


def render_frame(game: Game):
    game.renderer.render(
        game_state=game.state,
        player=game.player,
        platforms=game.level.get_platforms(),
        obstacles=game.level.get_obstacles(),
        enemies=game.level.get_enemies(),
        items=game.items.get_items(),
        hud=game.hud,
    )


def main():
    try:
        game = initialize_game()
        clock = pygame.time.Clock()

        while True:
            dt = clock.tick(FPS) / 1000
            events = pygame.event.get()
            if not handle_events(game, events):
                break

            input_state = pygame.key.get_pressed()
            update_game(game, dt, input_state)
            render_frame(game)
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
