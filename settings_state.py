import state

import pygame
import sys
# import logging
from pygame.locals import *
from globals import *

class SettingsState(state.State):
    def save_settings(self):
        """Write the settings to disk."""
        self.config.save_settings()

    def __init__(self):
        super().__init__()
        self.highlighted_setting = 0
        # Translate the settings into human readable format
        self.translated_settings = []
        self.showing_entry_menu = False
        self.show_invalid_key_message = False

    def translate_keys(self):
        """Prepare the controls dictionary for rendering (e.g. sorting and removing underscores)."""
        self.translated_settings = []
        for setting, options in self.config.get_settings().items():
            entry = []
            translated_setting = setting.replace('_', ' ')
            selected_option = options[1]
            entry.append(translated_setting)
            settings_text = options[0][selected_option]

            entry.append(settings_text)
            entry.append(setting)  # Keep the original action to map back to the control dictionary.
            self.translated_settings.append(entry)
        self.translated_settings.sort(key=lambda x: x[0])

    def render(self):
        # blank out the screen with blocks, but a splash screen on top of it
        self.renderer.draw_block_background()
        splash_rect = self.renderer.draw_splash_background()


        if self.showing_entry_menu:
            self.renderer.draw_centered_text('Press any key.', render_surface=splash_rect)
            if self.show_invalid_key_message:
                self.renderer.draw_centered_text('This key is already assigned!', (0, 50), render_surface=splash_rect)
        else:
            text_surfaces = self.renderer.draw_text_table(splash_rect, ('', ''), self.translated_settings)

            # Add the selected option cursor as a prefix
            # (done here to prevent the centering code from sliding the options around when a prefix is added)
            text_rect_to_prefix = text_surfaces[self.highlighted_setting]
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
                if event.key == self.config.get_key('select_menu_option'):
                    # Determine the selected setting and number of available options
                    selected_setting_name = self.translated_settings[self.highlighted_setting][2]

                    self.config.select_next_setting(selected_setting_name)

                    if selected_setting_name == 'window_size':
                        self.config.set_const('recently_resized', True)
                        self.renderer.resize()
                    elif selected_setting_name == 'background_music':
                        self.config.set_const('music_settings_adjusted', True)

                    self.translate_keys()
                elif event.key == K_DOWN:
                    # increase selected option with wrap around
                    self.highlighted_setting = (self.highlighted_setting + 1) % len(self.translated_settings)
                elif event.key == K_UP:
                    # decrease selected option with wrap around
                    self.highlighted_setting -= 1
                    if self.highlighted_setting < 0:
                        self.highlighted_setting = len(self.translated_settings) - 1
                elif event.key == self.config.get_key('back_button'):
                    self.state_manager.pop_state()

    def enter(self):
        self.logger.info('Enter: Settings')
        self.translate_keys()

    def exit(self):
        self.logger.info('Exit: Settings')
        self.save_settings()
