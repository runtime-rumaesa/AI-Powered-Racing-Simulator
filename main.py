import pygame
from settings import *
from game.track import draw_track
from game.race import Race
from game.hud import HUD


def main():
    pygame.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()

    race = Race()
    hud = HUD()

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

        draw_track(screen)
        race.draw(screen)
        hud.draw(screen, race)

        pygame.display.update()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()