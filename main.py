import pygame
from settings import *
from game.track import draw_track
from game.car import Car


def main():
    pygame.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()

    player = Car()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        player.handle_input(pygame.key.get_pressed())
        player.update()

        draw_track(screen)
        player.draw(screen)

        pygame.display.update()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()