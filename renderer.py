import pygame
from globals import *


class Renderer:
    def __init__(self, logger):
        pygame.display.set_caption('BLOCK BUSTER (v%s)' % VERSION_NUMBER)
        self.display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.big_font = pygame.font.Font(None, 30)
        self.small_font = pygame.font.Font(None, 20)

    def update(self):
        pygame.display.update()

    def fill(self, color):
        self.display.fill(color)

    def draw_rect(self, rect, color, border_width=0):
        if border_width == 0:  # filled rectangles can use the fill function which  can be hardware accelerated
            self.display.fill(color, rect)
        else:
            pygame.draw.rect(self.display, color, rect, border_width)

    def draw_block(self, rect, color):
        self.draw_rect(rect, color)  # fill a colored rect
        self.draw_rect(rect, BLACK, 1)  # draw a black border on it

    # todo generate surface once and store it instead of doing it every update tick
    def draw_text(self, text, position=None, small=False):
        '''Draw some text (small or large) on screen.'''
        text_surface = None

        if small:
            text_surface = self.small_font.render(text, True, (200, 200, 200))
        else:
            text_surface = self.big_font.render(text, True, (200, 200, 200))

        text_rect = text_surface.get_rect()

        # if no position was given, center text on board
        if position is None:
            position = [MARGIN_LEFT + ((BLOCK_SIZE * BOARD_WIDTH) / 2), MARGIN_TOP + ((BLOCK_SIZE * BOARD_HEIGHT) / 2)]
            position[0] -= text_surface.get_width() / 2
            position[1] -= text_surface.get_height() / 2

        text_rect.topleft = position
        self.display.blit(text_surface, text_rect)
