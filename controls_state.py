import state

import pygame
import sys
# import logging
from pygame.locals import *
from globals import *

class ControlsState(state.State):
    def __init__(self):
        super().__init__()
        self.highlighted_control = 0
        self.translated_controls = []
        self.showing_entry_menu = False
        self.show_invalid_key_message = False

    def translate_keys(self):
        """Prepare the controls dictionary for rendering (e.g. sorting and removing underscores)."""
        self.translated_controls = []
        for action, key in self.config.get_controls().items():
            entry = []
            translated_action = action.replace('_', ' ')
            translated_key = pygame.key.name(int(key))
            entry.append(translated_action)
            entry.append(translated_key)
            entry.append(action)  # Keep the original action to map back to the control dictionary.
            self.translated_controls.append(entry)
        self.translated_controls.sort(key=lambda x: x[0])

    def render(self):
        # blank out the screen with blocks, but a splash screen on top of it
        self.renderer.draw_block_background()
        splash_rect = self.renderer.draw_splash_background()

        if self.showing_entry_menu:
            self.renderer.draw_centered_text('Press any key.', render_surface=splash_rect)
            if self.show_invalid_key_message:
                self.renderer.draw_centered_text('This key is already assigned!', (0, 50), render_surface=splash_rect)
        else:
            text_surfaces = self.renderer.draw_text_table(splash_rect, ('ACTION', 'KEY'), self.translated_controls)

            # Add the selected option cursor as a prefix
            # (done here to prevent the centering code from sliding the options around when a prefix is added)
            text_rect_to_prefix = text_surfaces[self.highlighted_control]
            prefix_offset = list(text_rect_to_prefix.center)
            prefix_offset[0] = 30
            prefix_offset[1] -= text_rect_to_prefix.height / 2
            self.renderer.draw_text('>', prefix_offset)

    def exit_state(self):
        self.state_manager.pop_state()

    def update(self, elapsed_time):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.state_manager.clear_stack()
            elif event.type == KEYUP:
                if self.showing_entry_menu:
                    if event.key == K_ESCAPE:
                        self.showing_entry_menu = False
                        self.show_invalid_key_message = False
                    else:
                        # Look up the selected key.
                        selected_action = self.translated_controls[self.highlighted_control][2]

                        key_already_bound = False
                        for action, key in self.config.get_controls().items():
                            if selected_action != action and key == event.key:
                                key_already_bound = True
                                break

                        if not key_already_bound:
                            # Set it as the new control.
                            self.config.set_key(selected_action, event.key)
                            self.config.save_controls()
                            self.translate_keys()
                            self.showing_entry_menu = False
                            self.show_invalid_key_message = False
                        else:
                            self.show_invalid_key_message = True

                elif event.key == K_RETURN:
                    self.showing_entry_menu = True
                elif event.key == K_DOWN:
                    # increase selected option with wrap around
                    self.highlighted_control = (self.highlighted_control + 1) % len(self.translated_controls)
                elif event.key == K_UP:
                    # decrease selected option with wrap around
                    self.highlighted_control -= 1
                    if self.highlighted_control < 0:
                        self.highlighted_control = len(self.translated_controls) - 1
                elif not self.showing_entry_menu:
                    self.state_manager.pop_state()

    def enter(self):
        self.logger.info('Enter: Controls')
        # Translate the controls into human readable format
        self.translate_keys()

    def exit(self):
        self.logger.info('Exit: Controls')
