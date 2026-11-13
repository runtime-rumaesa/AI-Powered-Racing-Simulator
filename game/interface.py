import pygame
from settings import WHITE, GRAY, YELLOW, BLUE, RED, BLACK


class Button:
    """Interactive UI Button with hover state and click detection."""

    def __init__(self, x, y, width, height, text, bg_color=(40, 120, 240), hover_color=(60, 140, 255), text_color=WHITE,
                 font_size=20):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.font = pygame.font.SysFont("arial", font_size, bold=True)
        self.is_hovered = False

    def handle_event(self, event):
        """Returns True if the button is clicked."""
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

    def draw(self, surface):
        color = self.hover_color if self.is_hovered else self.bg_color
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, WHITE, self.rect, 2, border_radius=8)

        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)


class Panel:
    """Semi-transparent container overlay for UI modules."""

    def __init__(self, x, y, width, height, bg_alpha=200, border_color=WHITE):
        self.rect = pygame.Rect(x, y, width, height)
        self.surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.bg_alpha = bg_alpha
        self.border_color = border_color

    def draw(self, target_surface):
        self.surface.fill((10, 15, 25, self.bg_alpha))
        target_surface.blit(self.surface, self.rect.topleft)
        pygame.draw.rect(target_surface, self.border_color, self.rect, width=1, border_radius=6)


class Label:
    """Text rendering helper."""

    def __init__(self, text, x, y, color=WHITE, font_size=18, bold=False, align="left"):
        self.text = text
        self.x = x
        self.y = y
        self.color = color
        self.align = align
        self.font = pygame.font.SysFont("arial", font_size, bold=bold)

    def draw(self, surface):
        text_surf = self.font.render(self.text, True, self.color)
        rect = text_surf.get_rect()

        if self.align == "center":
            rect.center = (self.x, self.y)
        elif self.align == "right":
            rect.topright = (self.x, self.y)
        else:
            rect.topleft = (self.x, self.y)

        surface.blit(text_surf, rect)