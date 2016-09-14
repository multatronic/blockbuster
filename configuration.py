from globals import *
from pygame import *
from math import floor

class ConfigurationManager:
    def __init__(self, logger):
        self.logger = logger
        self.settings = {}
        self.controls = {}

        self.consts = {
            'version_number': '1.0',
            'fps': 60,
            'black': (0, 0, 0),
            'white': (255, 255, 255),
            'recently_resized': False,
            'music_settings_adjusted': False
        }
        self.load_settings()
        self.load_controls()

    def determine_size_variables(self):
        self.consts['block_size'] = floor(self.get('window_size')[0] / 22.5)
        self.consts['block_border_size'] = floor(self.get('block_size') / 20)
        self.consts['margin_left'] = self.consts['block_size'] / 2
        self.consts['margin_top'] = self.consts['margin_left']

    def save_settings(self):
        """Write the settings to disk."""
        with open('settings', 'w') as file:
            # Sort so the settings don't jump around when visiting the control page
            sorted_keys = sorted(self.settings.keys())
            for key in sorted_keys:
                record = '{0}|{1}\n'.format(key, self.settings[key][1])
                file.write(record)

    # Load the settings from disk.
    def load_settings(self):
        self.settings = {
            'background_music': [['Loop', 'Play once', "Off"], 0],
            'window_size': [[[450, 420], [900, 840]], 1]
        }

        try:
            with open('settings', 'r') as file:
                for line in file:
                    split_line = line.split('|')
                    self.settings[split_line[0]][1] = int(split_line[1])
        except FileNotFoundError:
            self.logger.info('No settings file was found, using default settings.')

        finally:
            self.determine_size_variables()

    def save_controls(self):
        """Write the controls to disk."""
        # now write the scores to a file
        with open('controls', 'w') as file:
            # Sort so the settings don't jump around when visiting the control page
            sorted_keys = sorted(self.controls.keys())
            for key in sorted_keys:
                record = '{0}|{1}\n'.format(key, self.controls[key])
                file.write(record)

    def load_controls(self):
        # Load the controls from disk.
        self.controls = {}
        try:
            with open('controls', 'r') as file:
                for line in file:
                    split_line = line.split('|')
                    self.controls[split_line[0]] = int(split_line[1])
        except FileNotFoundError:
            self.logger.info('No controls file was found, generating default.')
            self.controls = {
                'back_button': K_ESCAPE,
                'pause_button': K_p,
                'move_left': K_LEFT,
                'move_right': K_RIGHT,
                'rotate': K_UP,
                'fast_forward': K_DOWN,
                'swap_piece': K_RCTRL,
                'select_menu_option': K_RETURN
            }

    def get_controls(self):
        return self.controls

    def get_settings(self):
        return self.settings

    def get_setting(self, setting_key):
        setting = self.settings[setting_key]
        if setting:
            selected_setting_index = setting[1]
            return setting[0][selected_setting_index]
        return None

    def select_next_setting(self, setting_key):
        selected_setting = self.settings[setting_key]
        available_option_count = len(selected_setting[0])
        # Increase the selected option index, wrapping around to 0
        selected_setting[1] = (selected_setting[1] + 1) % available_option_count

    def set_key(self, action, key):
        self.controls[action] = key

    def get_key(self, key):
        return self.controls[key]

    def set_const(self, key, value):
        self.consts[key] = value

    def get_const(self, key):
        return self.consts[key]

    def get(self, key):
        if key in self.controls:
            return self.controls[key]
        elif key in self.consts:
            return self.consts[key]
        elif key in self.settings:
            return self.get_setting(key)
        else:
            return None
