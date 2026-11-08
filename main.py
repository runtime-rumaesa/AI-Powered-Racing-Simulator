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

        race.update(pygame.key.get_pressed())

        draw_track(world)
        race.draw(world)

        screen.fill(GRASS_COLOR)
        screen.blit(world, race.effects.shake_offset())
        hud.draw(screen, race)

        pygame.display.update()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()