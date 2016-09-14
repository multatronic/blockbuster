import pygame
from globals import *
from math import ceil
from random import randrange, random

class Renderer:
    def __init__(self, logger, config):
        self.config = config
        self.background_block_grid = []
        self.colors = [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255)
        ]

        self.resize()

    def update(self):
        pygame.display.update()

    def resize(self):
        pygame.display.set_caption('BLOCK BUSTER (v%s)' % self.config.get_const('version_number'))
        self.display = pygame.display.set_mode(self.config.get_setting('window_size'))
        self.config.determine_size_variables()
        if self.background_block_grid:
            self.background_block_grid = []

        if self.config.get('window_size')[0] == 450:
            self.big_font = pygame.font.Font(None, 30)
            self.small_font = pygame.font.Font(None, 20)
        else:
            self.big_font = pygame.font.Font(None, 60)
            self.small_font = pygame.font.Font(None, 40)

    def fill(self, color):
        self.display.fill(color)

    def draw_rect(self, rect, color, border_width=0):
        if border_width == 0:  # filled rectangles can use the fill function which  can be hardware accelerated
            self.display.fill(color, rect)
        else:
            pygame.draw.rect(self.display, color, rect, border_width)

    def draw_block(self, rect, color):
        self.draw_rect(rect, color)  # fill a colored rect
        self.draw_rect(rect, self.config.get_const('black'), self.config.get('block_border_size'))  # draw a black border on it

    # todo generate rects once instead of for every draw call
    def draw_block_background(self):
        # initialize a background block grid if none is present
        if not len(self.background_block_grid):
            window_size = self.config.get('window_size')
            block_size = self.config.get('block_size')

            number_of_columns = ceil(window_size[0] / block_size)
            number_of_rows = ceil(window_size[1] / block_size)

            current_position = [0, 0]
            for row in range(number_of_rows):
                color_row = self.pick_random_colors(number_of_columns)
                self.background_block_grid.append([])
                for current_color in color_row:
                    rect = pygame.Rect(current_position, (block_size, block_size))
                    self.background_block_grid[row].append({
                        'color': current_color,
                        'rect': rect,
                        'obfuscated': False
                    })
                    current_position[0] += block_size
                current_position[0] = 0
                current_position[1] += block_size

        for row in self.background_block_grid:
            for block in row:
                if not block['obfuscated']:
                    self.draw_block(block['rect'], block['color'])

    def draw_splash_background(self, outer_margin=30, inner_margin=10, border_color=(255, 255, 255)):
        window_size = self.config.get('window_size')
        width = window_size[0] - outer_margin
        height = window_size[1] - outer_margin
        background_rect = pygame.Rect((0, 0), (width, height))
        background_rect.center = (window_size[0] / 2, window_size[1] / 2)
        expanded_area = pygame.Rect(background_rect)
        expanded_area.width += inner_margin
        expanded_area.height += inner_margin
        expanded_area.center = background_rect.center

        self.draw_rect(background_rect, self.config.get('black'))
        self.draw_rect(background_rect, border_color, 3)
        self.draw_rect(expanded_area, border_color, 3)

        # If we have a background block grid, mark the obscured blocks
        if len(self.background_block_grid):
            for row in self.background_block_grid:
                for block_desc in row:
                    if background_rect.contains(block_desc['rect']):
                        block_desc['obfuscated'] = True
        return background_rect

    def get_distance_from_center(self, position=(0, 0), surface=None):
        if surface is None:
            surface = self.display.get_rect()
        center = surface.center
        result = [0, 0]
        result[0] = center[0] - position[0]
        result[1] = center[1] - position[1]
        return result

    # todo generate surface once and store it instead of doing it every update tick
    def draw_centered_text(self, text, offset=(0, 0), small=False, render_surface=None):
        """Draw some text (small or large) on screen."""

        text_surfaces = []

        # Turn single string into list of strings.
        if isinstance(text, str):
            text = [text]

        # Generate the text surfaces, keeping track of how much vertical and horizontal space it occupies.
        total_text_dimensions = [0, 0]
        for line in text:
            if small:
                current_surface = self.small_font.render(line, True, (200, 200, 200))
            else:
                current_surface = self.big_font.render(line, True, (200, 200, 200))

            text_surfaces.append(current_surface)
            text_rect = current_surface.get_rect()

            total_text_dimensions[1] += text_rect.height
            if text_rect.width > total_text_dimensions[0]:
                total_text_dimensions[0] = text_rect.width

        # If no surface to center on was passed, use the entire display.
        if render_surface is None:
            render_surface = self.display.get_rect()

        # Determine the starting point by finding the surface center and
        # offsetting vertically by half the text height .
        surface_center_x = (render_surface.width / 2) + render_surface.left
        surface_center_y = (render_surface.height / 2) + render_surface.top
        total_text_height_half = total_text_dimensions[1] / 2

        text_position = [surface_center_x + offset[0],
                         (surface_center_y - total_text_height_half) + offset[1]]

        result = []
        # Render each line, adjusting the vertical text position.
        for text_to_render in text_surfaces:
            text_rect = text_to_render.get_rect()
            text_rect.center = text_position
            text_position[1] += text_rect.height
            result.append(text_rect)
            self.display.blit(text_to_render, text_rect)

        return result

    def draw_text_table(self, table_area=None, headers=(), entries=()):
        """Draw a table of text on screen."""
        if table_area is None:
            table_area = pygame.Rect((0, 0), self.config.get('window_size'))

        line_rects = []
        number_of_columns = 0

        # calculate the height of the rows (max entry height + margin)
        row_height = 0
        row_margin = 20
        if len(headers):
            row_height = self.big_font.size(headers[0])[1]
            number_of_columns = len(headers)
        elif len(entries):
            number_of_columns = len(entries[0])
            row_height = self.small_font.size(entries[0][0])[1]

        # calculate the width of the columns (width / number_of_columns)
        column_width = table_area.width / number_of_columns
        column_width_half = column_width / 2

        row_height += row_margin
        row_height_half = row_height / 2

        current_draw_position = [column_width_half, row_height_half]
        remaining_vertical_space = table_area.height

        # render the headers
        for header in headers:
            header = str(header)
            text_size = self.big_font.size(header)
            # determine the offset needed to center the text
            text_width_offset = text_size[0] / 2

            # subtract row from remaining vertical space during rendering of first header
            if current_draw_position[0] == column_width_half:
                remaining_vertical_space -= row_height

            # center the text by offsetting the draw position
            offset_position = current_draw_position[:]
            offset_position[0] -= text_width_offset
            self.draw_text(header, offset_position)

            current_draw_position[0] += column_width

        # render the table entries
        header_count = len(headers)
        for entry in entries:
            # reset the draw cursor
            current_draw_position[0] = column_width_half
            current_draw_position[1] += row_height

            # Construct a rect enclosing the entire line (we return this to allow the caller to do formatting).
            line_rects.append(pygame.Rect(current_draw_position[0], current_draw_position[1],
                                          column_width * len(entry), row_height))

            for index, column_entry in enumerate(entry):
                # If headers were supplied we want to truncate columns that
                # were not given a header.
                if header_count and index >= header_count:
                    break

                column_entry = str(column_entry)
                text_size = self.small_font.size(column_entry)
                text_width_offset = text_size[0] / 2

                # Offset the current draw position to center the text.
                offset_draw_position = current_draw_position[:]
                offset_draw_position[0] -= text_width_offset

                if remaining_vertical_space >= self.small_font.size(column_entry)[1]:
                    self.draw_text(column_entry, offset_draw_position, True)
                current_draw_position[0] += column_width
            current_draw_position[0] += row_height
            remaining_vertical_space -= row_height
        return line_rects


    def draw_text(self, text, position=None, small=False):
        '''Draw some text (small or large) on screen.'''
        text_surface = None

        if small:
            text_surface = self.small_font.render(text.rstrip(), True, (200, 200, 200))
        else:
            text_surface = self.big_font.render(text.rstrip(), True, (200, 200, 200))

        text_rect = text_surface.get_rect()

        # if no position was given, center text on board
        if position is None:
            position = [MARGIN_LEFT + ((BLOCK_SIZE * BOARD_WIDTH) / 2), MARGIN_TOP + ((BLOCK_SIZE * BOARD_HEIGHT) / 2)]
            position[0] -= text_surface.get_width() / 2
            position[1] -= text_surface.get_height() / 2

        text_rect.topleft = position
        self.display.blit(text_surface, text_rect)
        return text_rect

    def pick_random_colors(self, amount=1, allow_streaks=True):
        """Generate an array of random colors (we placed this function in renderer because we also want to use
            it to draw backgrounds."""
        # global COLORS
        # select a few random colors
        result = []

        latest_color = None
        color_streak_count = 0
        for i in range(amount):
            color_accepted = False
            while not color_accepted:
                random_color = self.colors[randrange(0, len(self.colors))]

                # 5 percent chance of getting the white color
                if allow_streaks and random() <= 0.05:
                    random_color = self.config.get_const('white')

                if random_color != latest_color:
                    color_streak_count = 0
                    latest_color = random_color
                else:
                    color_streak_count += 1

                if allow_streaks or color_streak_count < 3:
                    result.append(random_color)
                    color_accepted = True
        return result