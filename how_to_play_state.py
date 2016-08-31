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
            'Swap pieces to find the best fit.',
            '(this will slightly lower your score)',
            '', '',
            'Try not to suck.'
        ]

    def render(self):
        # blank out the screen
        self.renderer.draw_block_background()
        splash = self.renderer.draw_splash_background()
        self.renderer.draw_centered_text(self.lines, render_surface=splash)

    def update(self, elapsed_time):
        for event in pygame.event.get():
            if event.type == QUIT or event.type == KEYUP:
                self.state_manager.pop_state()

    def enter(self):
        self.logger.info('Enter: Help')

    def exit(self):
        self.logger.info('Exit: Help')
