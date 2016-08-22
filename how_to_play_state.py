import state
import pygame
import sys
# import logging
from pygame.locals import *
from globals import *
from game_state import *


class HowToPlayState(state.State):
    def __init__(self):
        super().__init__()
        self.lines = [
            'Match 4 or more colors in any direction.',
            'White blocks will match any other color.',
            '',
            'Arrow left/right/up to move the piece.',
            'Arrow down to fast forward.',
            '',
            'Right Ctrl to swap the next piece.',
            '(this will lower your score)',
            '',
            'Esc takes you back to the menu.',
            '', '',
            'Try not to suck.'
        ]

    def render(self):
        # blank out the screen
        self.renderer.draw_block_background()
        splash = self.renderer.draw_splash_background()

        # draw the preview window
        # line_offset = WINDOW_HEIGHT / 2 - 100
        # for line in self.lines:
        #     line_offset += self.renderer.draw_centered_text(line, line_offset).get_height()
        self.renderer.draw_centered_text(self.lines, render_surface=splash)

    def update(self, elapsed_time):
        for event in pygame.event.get():
            if event.type == QUIT or event.type == KEYUP:
                self.state_manager.pop_state()

    def enter(self):
        self.logger.info('Enter: Help')

    def exit(self):
        self.logger.info('Exit: Help')
