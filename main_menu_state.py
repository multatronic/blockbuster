import state

import pygame
import sys
# import logging
from pygame.locals import *
from globals import *
from game_state import *
from how_to_play_state import *


class MainMenuState(state.State):
    def load_high_scores(self):
        '''Load the high score entries from disk.'''
        result = []
        try:
            with open('scores', 'r') as file:
                for line in file:
                    result.append(line.split('-'))
        except FileNotFoundError:
            self.logger.info('No high score file was found')
        return result

    def __init__(self):
        super().__init__()
        self.selected_option = 0
        self.high_scores = []
        self.menu_options = [
            ['start game', self.start_game],
            ['what do?', self.show_help],
            ['high scores', self.show_scores],
            ['exit', self.stop_game]
        ]
        self.showing_menu = False
        self.active_game = None

    def render(self):
        if self.active_game is not None and not self.showing_menu:
            self.active_game.render()
        else:
            # blank out the screen
            self.renderer.fill(BLACK)

            # draw the preview window
            option_offset = WINDOW_HEIGHT / 2 - 100
            for index in range(0, len(self.menu_options)):
                text_to_render = self.menu_options[index][0]
                if index == self.selected_option:
                    text_to_render = '> ' + text_to_render
                option_offset += self.renderer.draw_centered_text(text_to_render, option_offset).get_height()

    def start_game(self):
        self.menu_options = [
            ['continue', self.continue_game],
            ['restart', self.restart_game],
            ['what do?', self.show_help],
            ['high scores', self.show_scores],
            ['exit', self.stop_game]
        ]
        self.set_up_game()

    def show_menu(self):
        self.showing_menu = True

    def continue_game(self):
        self.showing_menu = False

    def set_up_game(self):
        if self.active_game:
            self.active_game.exit()

        substate = GameState(self.high_scores)
        substate.inject_services(self.renderer, self.logger, self)
        substate.enter()
        self.active_game = substate

    def restart_game(self):
        self.logger.info('restart game')
        self.set_up_game()
        self.showing_menu = False

    def show_help(self):
        self.state_manager.push_state(HowToPlayState())

    def show_scores(self):
        self.state_manager.pop_state()

    def stop_game(self):
        self.state_manager.pop_state()

    def update(self, elapsed_time):
        if self.active_game is not None and not self.showing_menu:
            self.active_game.update(elapsed_time)
        else:
            for event in pygame.event.get():
                if event.type == QUIT:
                    self.state_manager.pop_state()
                elif event.type == KEYUP:
                    if event.key == K_ESCAPE:
                        self.state_manager.pop_state()
                    elif event.key == K_DOWN:
                        self.selected_option = (self.selected_option + 1) % len(self.menu_options)
                    elif event.key == K_UP:
                        self.selected_option -= 1
                        if self.selected_option < 0:
                            self.selected_option = len(self.menu_options) - 1
                    elif event.key == K_RETURN:
                        # fire the callback related to the currently selected option
                        self.menu_options[self.selected_option][1]()

    def enter(self):
        self.logger.info('Enter: MainMenu')
        self.high_scores = self.load_high_scores()

    def exit(self):
        self.logger.info('Exit: MainMenu')
