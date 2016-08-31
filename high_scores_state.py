import state

import pygame
import sys
# import logging
from pygame.locals import *
from globals import *

class HighScoresState(state.State):
    def save_high_scores(self):
        """Write the high scores to disk."""
        # add our entry to the list and sort it from highest to lowest
        if len(self.new_high_score):
            self.new_high_score.append(self.entered_name.rstrip())  # strip newlines, whitespace, etc

        self.high_scores.append(self.new_high_score)
        self.high_scores.sort(key=lambda x: int(x[0]), reverse=True)  # sort by score

        # now write the scores to a file
        with open('scores', 'w') as file:
            for entry in self.high_scores:
                record = '{0}|{1}|{2}\n'.format(entry[0], entry[1], entry[2])
                file.write(record)

    def __init__(self, high_scores=[], new_high_score=[]):
        super().__init__()
        self.high_scores = high_scores
        self.new_high_score = new_high_score
        self.showing_entry_menu = len(self.new_high_score) > 0
        self.entered_name = ''

    def render(self):
        # blank out the screen with blocks, but a splash screen on top of it
        self.renderer.draw_block_background()
        splash_rect = self.renderer.draw_splash_background()

        if self.showing_entry_menu:
            self.renderer.draw_text('name: ' + self.entered_name)
        else:
            if len(self.high_scores):
                self.renderer.draw_text_table(splash_rect, ('SCORE', 'LEVEL', 'PLAYER'), self.high_scores)
            else:
                self.renderer.draw_centered_text('no scores yet, be the first!', surface=splash_rect)

    def exit_state(self):
        self.state_manager.pop_state()

    def update(self, elapsed_time):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.state_manager.clear_stack()
            elif event.type == KEYUP:
                if not self.showing_entry_menu:
                    self.state_manager.pop_state()
                elif event.key == K_RETURN:
                    # fire the callback related to the currently selected option
                    self.save_high_scores()
                    self.showing_entry_menu = False
                elif event.key <= 122 and event.key != 13:
                    if event.key == K_BACKSPACE:
                        self.entered_name = self.entered_name[0:-1]
                    else:
                        self.entered_name += chr(event.key)

    def enter(self):
        self.logger.info('Enter: HighScores')

    def exit(self):
        self.logger.info('Exit: HighScores')
