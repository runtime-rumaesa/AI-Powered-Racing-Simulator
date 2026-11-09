import pygame
from settings import *
from game.track import draw_track, get_track
from game.race import Race
from game.hud import HUD


def main():
    pygame.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()

    race = Race()
    hud = HUD(get_track())
    show_routes = False
    world = pygame.Surface((WIDTH, HEIGHT))  # everything that can shake

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    race = Race()  # restart
                elif event.key == pygame.K_t and race.state == "racing":
                    race.respawn(race.player)  # stuck? back on the track
                elif event.key == pygame.K_p:
                    show_routes = not show_routes  # show the AI routes

        race.update(pygame.key.get_pressed())

        draw_track(world)
        if show_routes:
            race.draw_routes(world)
        race.draw(world)

        screen.fill(GRASS_COLOR)
        screen.blit(world, race.effects.shake_offset())
        hud.draw(screen, race)

        pygame.display.update()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()