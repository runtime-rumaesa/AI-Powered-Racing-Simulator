import pygame
from settings import *
from game.track import draw_track, get_track
from game.race import Race
from game.hud import HUD
from game.interface import MainMenu, draw_race_tag
from game.results import ResultsScreen


def main():
    pygame.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()

    menu = MainMenu()
    hud = HUD(get_track())
    world = pygame.Surface((WIDTH, HEIGHT))  # everything that can shake

    race = None            # None = the main menu is showing
    results = None         # the results screen, once the race is over
    lineup = None          # (preset, laps, weather) of the current race, so R can restart it
    show_routes = False

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif race is None:  # ---- main menu
                action = menu.handle_event(event)
                if action is None:
                    continue
                if action[0] == "quit":
                    running = False
                elif action[0] == "start":
                    lineup = action[1:]
                    race = Race(preset=lineup[0], total_laps=lineup[1], weather=lineup[2])

            elif results is not None:  # ---- results screen
                action = results.handle_event(event)
                if action == "again":
                    race = Race(preset=lineup[0], total_laps=lineup[1], weather=lineup[2])
                    results = None
                elif action == "menu":
                    race = results = None

            elif event.type == pygame.KEYDOWN:  # ---- race
                if event.key == pygame.K_ESCAPE:
                    race = None  # back to the menu
                elif event.key == pygame.K_r:
                    race = Race(preset=lineup[0], total_laps=lineup[1], weather=lineup[2])  # restart
                elif event.key == pygame.K_t and race.state == "racing":
                    race.respawn(race.player)  # stuck? back on the track
                elif event.key == pygame.K_p:
                    show_routes = not show_routes  # show the AI routes
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    race.skip_to_results()  # you finished: don't wait for the others

        if race is None:
            menu.update()
            menu.draw(screen)
        else:
            if results is None:
                race.update(pygame.key.get_pressed())

            draw_track(world)
            if show_routes:
                race.draw_routes(world)
            race.draw(world)

            screen.fill(GRASS_COLOR)
            screen.blit(world, race.effects.shake_offset())
            if race.state == "finished" and results is None:
                results = ResultsScreen(race, screen)  # the frozen race is the backdrop

            if results is not None:
                results.draw(screen)
            else:
                hud.draw(screen, race)
                draw_race_tag(screen, race, hud.f_small)

        pygame.display.update()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()