import state

import pygame
import sys
# import logging
from pygame.locals import *
from random import randrange, random
from high_scores_state import HighScoresState
from globals import *

# -----------------------------------------------------TERMINOLOGY------------------------------------------------------
# TILE = A non-moving 'slot' on the game board, holds pygame.rect information
# BOARD = A two-dimensional array of Tiles, describing the entire game space
# COLOR_GRID = A copy of the board, which holds color information - this is used to check for groupings of colors
# BLOCK (DESCRIPTOR) = A small dictionary object containing a row, column and color.
# PIECE = A collection of blocks which are controlled by the player
# ----------------------------------------------------------------------------------------------------------------------


class GameState(state.State):
    class Tile:
        """A tile represents a slot on the board"""
        def __init__(self, x, y, rect_offset=(0, 0), config=None):
            block_size = config.get('block_size')
            self.column = x
            self.row = y
            self.rect = pygame.Rect(rect_offset[0] + config.get('margin_left') + (block_size * x),
                                    rect_offset[1] + config.get('margin_top') + (block_size * y), block_size,
                                    block_size)

    def __init__(self, high_scores):
        super().__init__()
        self.templates = [
            [
                (0, 1, 1),
                (0, 1, 0),
                (0, 1, 0)
            ],
            [
                (0, 1, 0),
                (1, 1, 1)
            ],
            [
                (1, 1, 0),
                (0, 1, 1)
            ],
            [
                (1, 1),
                (1, 1)
            ]
        ]

        self.points_per_block = 5
        self.board_height = 20  # board height in blocks
        self.board_width = 16  # board width in blocks
        self.preview_height = 3  # preview window height in blocks
        self.preview_width = 3  # preview window width in blocks


        self.fast_forward_mode = False
        self.debug_mode = False
        self.game_over = False
        self.game_paused = False
        self.music_paused = False
        self.last_update = 0

        self.color_grid = []


        self.score = 0
        self.level = 1
        self.update_speed = 500  # update board every x milliseconds
        self.muligans = 0  # number of times the player can generate a new 'next' piece (see also: spawn_new_piece())
        self.piece_position = [6, 0]

        # we declare a few lists here which will store references to various tiles/blocks/rows/columns
        # (otherwise we would have to scan the entire board every time we need to update something)
        self.fixated_blocks = []  # blocks which are not moving
        self.falling_blocks = []  # blocks which are falling, but not part of a controlled piece
        self.controlled_blocks = []  # blocks which are part of a user-controlled piece
        self.fading_tiles = []  # tiles which are in the act of fading out (e.g. part of a color streak)
        self.tiles_to_be_reset = []  # board tiles which will be reset (e.g. part of a color streak, fully faded out)
        self.blocks_to_be_fixated = []  # list of blocks which have stopped moving and will be fixated on the board
        self.dirty_rows = []  # list of rows which need to be checked for matches
        self.dirty_columns = []  # list of columns which need to be checked for matches
        self.dirty_diag_ne = []  # coordinates which will be checked diagonally in north-east direction
        self.dirty_diag_nw = []  # coordinates which will be checked diagonally in north-west direction

        self.current_fadeout_value = 2  # current width of the fadeout rectangle
        self.high_scores = high_scores
        self.lowest_high_score = None
        self.last_barricade_level = 0  # the last level when a barricade was spawned
        self.number_of_spawned_pieces = 0

        for score in self.high_scores:
            as_int = int(score[0])
            if self.lowest_high_score == None or as_int < self.lowest_high_score:
                self.lowest_high_score = as_int

        # the colorized template is a copy of a single template
        # where every 1 has been replaced with a color value

        # when a piece is rotated, what is actually happening is that this matrix is
        # rotated, and the self.controlled_blocks array is emptied and regenerated
        self.colorized_template = []
        self.next_colorized_template = []

    def add_block_descriptor(self, block_list, color, column, row):
        """Add a block descriptor to a block_list (e.g register a falling block)."""
        block_list.append({
            'color': color,
            'column': column,
            'row': row
        })

    def migrate_block(self, from_block_list, to_block_list, block):
        to_block_list.append(block)
        self.remove_from_block_list(from_block_list, block)

    def find_fixated_blocks_above_point(self, coordinate):
        result = []
        for block in self.fixated_blocks:
            if block['column'] == coordinate[0] and block['row'] < coordinate[1]:
                result.append(block)
        return result

    def remove_from_block_list(self, block_list, block_to_remove):
        for block in list(block_list):
            if block['column'] == block_to_remove['column'] and block['row'] == block_to_remove['row']:
                block_list.remove(block)
                break

    def is_in_block_list(self, block_list, coordinate):
        """Determine wether a coordinate is found within a given list of block descriptors."""
        result = False
        for block in block_list:
            if block['column'] == coordinate[0] and block['row'] == coordinate[1]:
                result = True
                break
        return result

    def is_piece_block(self, coordinate):
        '''Is coordinate a part of the list of blocks that are controlled by the player?'''
        return self.is_in_block_list(self.controlled_blocks, coordinate)


    def is_falling_block(self, coordinate):
        '''Is coordinate a part of the list of blocks that are falling?'''
        return self.is_in_block_list(self.falling_blocks, coordinate)

    def is_fixated_block(self, coordinate):
        '''Is coordinate a part of the list of blocks that are fixated?'''
        return self.is_in_block_list(self.fixated_blocks, coordinate)

    def is_within_bounds(self, coordinate):
        '''Is coordinate within the bounds of the game board?'''
        return 0 <= coordinate[0] < self.board_width and 0 <= coordinate[1] < self.board_height


    def detach_block(self, block):
        '''Detach a block (i.e. change it from a fixated block to a falling block).'''
        if not self.is_falling_block((block['column'], block['row'])):
            self.migrate_block(self.fixated_blocks, self.falling_blocks, block)

    def rotate_matrix(self, matrix):
        '''Rotate a matrix 90 degrees clockwist by transposing it + reversing the columns.'''
        matrix[:] = [[column[i] for column in reversed(matrix)] for i in range(len(matrix[0]))]


    def is_vacant_tile(self, coordinate):
        '''Is the coordinate an empty slot on the board?'''
        # within playing field?
        if not self.is_within_bounds(coordinate):
            return False

        # empty tile?
        return not self.is_in_block_list(self.fixated_blocks, coordinate)

    def find_furthest_diagonal_point(self, starting_point, direction):
        current = starting_point[:]
        last_valid_coordinate = None
        in_bounds = self.is_within_bounds(current)
        while in_bounds:
            last_valid_coordinate = current[:]
            current[0] += direction[0]
            current[1] += direction[1]
            in_bounds = self.is_within_bounds(current)
        return last_valid_coordinate

    def increase_fadeout_value(self, last_tick):
        if self.current_fadeout_value >= self.config.get('block_size'):
            self.current_fadeout_value = 0
            self.tiles_to_be_reset = list(self.fading_tiles)
            self.fading_tiles.clear()
            self.remove_marked_tiles()

        growth_factor = 3
        if self.config.get('window_size')[0] == 900:
            growth_factor *= 2
        self.current_fadeout_value += (last_tick / 1000) * growth_factor

    def increase_score(self, increase=0):
        '''Increase the player score and adjust difficulty.'''
        self.score += increase
        self.score += self.muligans * 5

    def remove_marked_tiles(self):
        lowest_vacated_slots = {}

        score_increase = 0
        # blank out the tiles and remember what column they are in. Also remember the lowest row
        # (= highest coordinate) in this column where a tile was blanked out.
        for block in self.tiles_to_be_reset:
            score_increase += self.points_per_block
            column = block['column']
            row = block['row']
            if column not in lowest_vacated_slots or lowest_vacated_slots[column] < row:
                lowest_vacated_slots[column] = row

        self.tiles_to_be_reset.clear()

        # put all the blocks above this one on the list of moving blocks
        # (provided it's not already on there)
        for column in lowest_vacated_slots:
            row = lowest_vacated_slots[column]
            blocks_above = self.find_fixated_blocks_above_point((column, row))
            for block in blocks_above:
                self.detach_block(block)

        if score_increase:
            self.increase_score(score_increase)


    def move_piece(self, direction=(1, 0)):
        all_tiles_available = True

        # first pass: check if the tiles we want to move to are all available
        for block in self.controlled_blocks:
            # check if the tile we want to move to is available
            desired_coordinate = (block['column'] + direction[0], block['row'])
            if not self.is_vacant_tile(desired_coordinate) or self.is_falling_block(desired_coordinate):
                all_tiles_available = False
                break

        # second pass: actually move the blocks
        if all_tiles_available:
            self.piece_position[0] += direction[0]

            for block in self.controlled_blocks:
                block['column'] += direction[0]


    def spawn_area_available(self, template=None):
        if template is None:
            template = self.colorized_template

        all_tiles_available = True
        for row in range(self.piece_position[1], self.piece_position[1] + len(template)):
            for column in range(self.piece_position[0], self.piece_position[0] + len(template[0])):
                # check if the tile we want to move to is available
                desired_coordinate = (column, row)
                if not self.is_vacant_tile(desired_coordinate) or self.is_falling_block(desired_coordinate):
                    all_tiles_available = False
                    break
        return all_tiles_available

    def spawn_barricade(self, rows=None):
        if len(self.falling_blocks) or len(self.controlled_blocks):
            return

        self.fast_forward_mode = False
        number_of_rows = 2 + (self.level // 50) if rows is None else rows  # add an extra barricade row every 50 levels

        for row in range(number_of_rows):
            # generate an array of random colors as wide as the game board
            chosen_colors = self.renderer.pick_random_colors(self.board_width, False)
            for column in range(self.board_width):
                self.add_block_descriptor(self.falling_blocks, chosen_colors[column], column, row)

        self.last_barricade_level = self.level


    def spawn_new_piece(self):
        self.colorized_template = list(self.next_colorized_template)
        self.piece_position = [6, 0]
        if self.spawn_area_available():
            self.generate_next_colorized_template()
            self.generate_controlled_blocks_from_colorized_template()
            self.muligans = 5  # reset muligans
            self.fast_forward_mode = False
        else:
            # self.save_high_scores()
            self.game_over = True
            if self.lowest_high_score is None or self.lowest_high_score <= self.score:
                self.state_manager.show_score_entry(self.high_scores, [self.score, self.level])

    def rotate_piece(self):
        # global self.colorized_template
        rotated_matrix = list(self.colorized_template)
        if not len(rotated_matrix):
            return
        self.rotate_matrix(rotated_matrix)

        if self.spawn_area_available(rotated_matrix):
            self.colorized_template = rotated_matrix
            self.generate_controlled_blocks_from_colorized_template()

    def generate_next_colorized_template(self):
        self.next_colorized_template = []

        piece_template_index = randrange(0, len(self.templates))

        # select a few random colors, allowing duplicates
        chosen_colors = self.renderer.pick_random_colors(1 + (self.level // 10))

        for row in self.preview_window:
            for column in row:
                column.color = self.config.get_const('black')

        for row in range(len(self.templates[piece_template_index])):
            self.next_colorized_template.append([])
            for column in range(len(self.templates[piece_template_index][row])):
                generated_color = self.config.get_const('black')
                if self.templates[piece_template_index][row][column] == 1:
                    generated_color = chosen_colors[randrange(0, len(chosen_colors))]
                self.next_colorized_template[row].append(generated_color)
                self.preview_window[column][row].color = generated_color


    def generate_controlled_blocks_from_colorized_template(self):
        # make sure we're not controlling any leftovers
        self.controlled_blocks = []

        spawn_coord = list(self.piece_position)

        number_of_rows = len(self.colorized_template)
        number_of_columns = len(self.colorized_template[0])

        for row in range(number_of_rows):
            for column in range(number_of_columns):
                if self.colorized_template[row][column] != self.config.get_const('black') and \
                        self.is_vacant_tile(spawn_coord):
                    self.add_block_descriptor(self.controlled_blocks, self.colorized_template[row][column],
                                         spawn_coord[0], spawn_coord[1])

                spawn_coord[0] += 1
            spawn_coord[1] += 1
            spawn_coord[0] = self.piece_position[0]

        # increase the current level based on the number of spawned pieces
        self.number_of_spawned_pieces += 1
        self.level = (self.number_of_spawned_pieces // 20) + 1
        self.update_speed = 500 - ((self.level // 3) * 50)
        if self.update_speed < 200:
            self.update_speed = 200

    def move_blocks_down(self, block_list):
        # sort the block vertically
        sorted_list = sorted(block_list, key=lambda x: x['row'], reverse=True)

        collision_occured = False
        for block in sorted_list:
            destination = (block['column'], block['row'] + 1)
            if self.is_vacant_tile(destination):  # and not self.is_to_be_fixated(destination):
                block['row'] += 1
            else:
                collision_occured = True
                # self.blocks_to_be_fixated.append(block)
                self.fixated_blocks.append(block)
                # block['stopped'] = True

                # collect the furthest points on the board which are diagonal to this one
                block_coordinate = [block['column'], block['row']]
                diag_point_south_west = self.find_furthest_diagonal_point(block_coordinate, (-1, 1))
                diag_point_south_east = self.find_furthest_diagonal_point(block_coordinate, (1, 1))

                # piggy backing off block functions here, but we're not interested in the color
                if not self.is_in_block_list(self.dirty_diag_ne, diag_point_south_west):
                    self.add_block_descriptor(self.dirty_diag_ne, self.config.get_const('black'),
                                              diag_point_south_west[0], diag_point_south_west[1])

                if not self.is_in_block_list(self.dirty_diag_nw, diag_point_south_east):
                    self.add_block_descriptor(self.dirty_diag_nw, self.config.get_const('black'),
                                              diag_point_south_east[0], diag_point_south_east[1])

                if block['row'] not in self.dirty_rows:
                    self.dirty_rows.append(block['row'])

                if block['column'] not in self.dirty_columns:
                    self.dirty_columns.append(block['column'])

                block_list.remove(block)

        return collision_occured

    def mark_matches(self, starting_point=0, direction=(1, 0)):
        """Check for grouping of four in a given direction."""
        current_streak = []
        # remember the last checked tile in case we need to use it as a starting point
        # for a reverse sweep
        last_tile_checked = None

        def flush_streak(current_color):
            nonlocal current_streak
            if len(current_streak) > 3 and current_color is not None:
                for block in current_streak:
                    if not self.is_in_block_list(self.fading_tiles, (block['column'], block['row'])):
                        self.migrate_block(self.fixated_blocks, self.fading_tiles, block)

            current_streak = []

        def run_scan(scan_starting_point, scan_direction):
            nonlocal last_tile_checked
            current_streak_color = None
            wildcard_encountered = False

            coordinate_to_check = list(scan_starting_point)
            in_bounds = self.is_within_bounds(coordinate_to_check)

            while in_bounds:
                tile_to_check = self.color_grid[coordinate_to_check[0]][coordinate_to_check[1]]
                last_tile_checked = coordinate_to_check[:]

                if tile_to_check != self.config.get_const('black'):
                    if tile_to_check != self.config.get_const('white'):
                        if current_streak_color is None:
                            current_streak_color = tile_to_check
                        elif current_streak_color != tile_to_check:
                            flush_streak(current_streak_color)
                            current_streak_color = tile_to_check
                    else:
                        wildcard_encountered = True

                    self.add_block_descriptor(current_streak, tile_to_check, coordinate_to_check[0], coordinate_to_check[1])

                else:  # the current tile is black, so whatever streak we had has ended
                    flush_streak(current_streak_color)
                    current_streak_color = None

                coordinate_to_check[0] += scan_direction[0]
                coordinate_to_check[1] += scan_direction[1]
                in_bounds = self.is_within_bounds(coordinate_to_check)

            flush_streak(current_streak_color)  # we've gone out of bounds, flush whatever was left in the streak buffer
            return wildcard_encountered

        # run the requested scan, if we encounter a wildcard run it again in the opposite direction
        # so that we capture all possible match groupings
        if run_scan(starting_point, direction):
            reversed_direction = list(direction)
            reversed_direction[0] *= -1
            reversed_direction[1] *= -1
            run_scan(last_tile_checked, reversed_direction)

    def render(self):
        def render_block_descriptor(block_to_render):
            rect = self.board[block_to_render['column']][block_to_render['row']].rect
            self.renderer.draw_block(rect, block_to_render['color'])

        # blank out the screen
        self.renderer.fill(self.config.get_const('black'))

        # draw the preview window
        for row in range(len(self.preview_window)):
            for column in range(len(self.preview_window[0])):
                    block = self.preview_window[row][column]
                    self.renderer.draw_block(block.rect, block.color)

        for block in self.fixated_blocks:
            render_block_descriptor(block)

        # draw falling and controller blocks
        for block in self.falling_blocks:
            render_block_descriptor(block)

        for block in self.controlled_blocks:
            render_block_descriptor(block)

        for block in self.fading_tiles:
            render_block_descriptor(block)

        # render fadeout rectangles
        fadeout_rect = pygame.Rect(0, 0, self.current_fadeout_value, self.current_fadeout_value)
        for block in self.fading_tiles:
            fadeout_rect.center = self.board[block['column']][block['row']].rect.center
            self.renderer.draw_rect(fadeout_rect, self.config.get_const('black'))

        # draw the board border (grey, 5 pixels thick)
        self.renderer.draw_rect(self.board_border, (100, 100, 100), 5)

        # render stats
        offset_growth = 15
        if self.config.get('window_size')[0] == 900:
            offset_growth = 30

        top_margin = self.config.get('margin_top') + (self.preview_height * self.config.get('block_size')) + 10
        self.renderer.draw_text('level: %s' % self.level, (self.preview_window_offset, top_margin), True)
        self.renderer.draw_text('score: %s' % self.score, (self.preview_window_offset, top_margin + offset_growth), True)
        self.renderer.draw_text('speed: %ss' % (self.update_speed / 1000), (self.preview_window_offset, top_margin + (offset_growth * 2)), True)
        self.renderer.draw_text('swaps left: %s' % self.muligans, (self.preview_window_offset, top_margin + (offset_growth * 3)), True)

        if self.game_over:
            self.renderer.draw_text('GAME OVER')
        elif self.game_paused:
            self.renderer.draw_text('PAUSED')

    def update_board(self):
        # 1: update falling blocks
        self.move_blocks_down(self.falling_blocks)

        # if the controlled piece collided with anything add it to the falling blocks
        # move the controlled piece down, and check if it collided with anything
        # (we'll want to stop controlling them in that case)
        piece_collision = self.move_blocks_down(self.controlled_blocks)
        self.piece_position[1] += 1

        # list and stop controlling it
        if piece_collision:
            self.falling_blocks += self.controlled_blocks
            self.controlled_blocks.clear()

        # when things have stopped moving, mark matching block groups and remove them
        # the mark matches function will automatically perform a scan in the opposite direction
        # if it encounters a wildcard block (because this block may be part of several colors group at the same time)
        if not len(self.falling_blocks):
            self.collect_color_matches()

        self.remove_marked_tiles()

    def collect_color_matches(self):
            self.color_grid = [[self.config.get_const('black') for row in range(self.board_height)] for column in range(self.board_width)]

            # now fill in the fixated colors
            for block in self.fixated_blocks:
                self.color_grid[block['column']][block['row']] = block['color']

            for block in self.dirty_diag_ne:  # sweep from bottom to top left
                self.mark_matches([block['column'], block['row']], (1, -1))

            for block in self.dirty_diag_nw:  # sweep from bottom to top right
                self.mark_matches([block['column'], block['row']], (-1, -1))

            for row in self.dirty_rows:
                self.mark_matches([0, row], (1, 0))  # sweep from left to right

            for column in self.dirty_columns:
                self.mark_matches([column, 0], (0, 1))  # sweep from top to bottom

            self.dirty_diag_ne = []
            self.dirty_diag_nw = []
            self.dirty_columns = []
            self.dirty_rows = []

    def update(self, elapsed_time):
        # Resize the game screen or adjust the music settings if applicable
        if self.config.get('recently_resized'):
            self.set_up_game()
            self.config.set_const('recently_resized', False)
        if self.config.get('music_settings_adjusted'):
            self.check_music_settings()
            self.config.set_const('music_settings_adjusted', False)

        for event in pygame.event.get():
            if event.type == QUIT:
                self.state_manager.stop_game()
            elif event.type == KEYDOWN:
                if event.key == self.config.get_key('fast_forward'):
                    self.fast_forward_mode = True
            elif event.type == KEYUP:
                if self.game_over:
                    self.state_manager.shut_down_game()
                elif event.key == self.config.get_key('fast_forward'):
                    self.fast_forward_mode = False
                elif event.key == self.config.get_key('move_left'):
                    self.move_piece((-1, 0))
                elif event.key == self.config.get_key('move_right'):
                    self.move_piece((1, 0))
                elif event.key == self.config.get_key('rotate'):
                    self.rotate_piece()
                elif event.key == self.config.get_key('back_button'):
                    self.pause_music()
                    self.state_manager.show_menu()
                elif event.key == self.config.get_key('pause_button'):
                    self.game_paused = not self.game_paused
                elif event.key == self.config.get_key('swap_piece'):
                    if self.muligans > 0:
                        self.muligans -= 1
                        self.generate_next_colorized_template()
                elif event.key == K_d:
                    self.debug_mode = not self.debug_mode

        # if nothing is moving on the board either spawn a new piece or a barricade (depending on the current level)
        if not (len(self.falling_blocks) or len(self.controlled_blocks)):
            if self.level - self.last_barricade_level == 4:
                self.spawn_barricade()
            else:
                self.spawn_new_piece()

        if not self.game_paused:
            update_required = self.last_update >= self.update_speed or (self.fast_forward_mode and self.last_update >= 15)

            if len(self.fading_tiles):
                self.increase_fadeout_value(self.last_update)
            elif update_required:
                self.update_board()
                self.last_update = 0

            self.last_update += elapsed_time

    def enter(self):
        self.logger.info('Enter: GameState')
        self.set_up_game()

    def set_up_game(self):
        self.logger.info('Setting up the game.')
        pygame.mixer.music.load('assets/Odyssey.ogg')
        self.determine_size_variables()
        self.check_music_settings()
        self.generate_next_colorized_template()
        self.spawn_barricade(3)
        self.music_paused = False

    def check_music_settings(self):
        if self.config.get('background_music') != 'Off':
            if self.config.get('background_music') == 'loop':
                self.start_music()
            else:
                self.start_music(False)
        else:
            self.stop_music()

    def determine_size_variables(self):
        margin_left = self.config.get('margin_left')
        margin_top = self.config.get('margin_top')

        self.preview_window_offset = margin_left + (self.board_width * self.config.get('block_size')) + (margin_left * 2)
        self.block_size = self.config.get('block_size')

        self.board = [[GameState.Tile(x, y, config=self.config) for y in range(self.board_height)] for x in range(self.board_width)]
        self.preview_window = [[GameState.Tile(x, y, (self.preview_window_offset, 0), self.config) for y in
                                range(self.preview_height)] for x in range(self.preview_height)]

        self.board_border = pygame.Rect(margin_left, margin_top, (self.board_width * self.block_size),
                                        (self.board_height * self.block_size))


    def stop_music(self):
        self.music_paused = True
        pygame.mixer.music.stop()

    def start_music(self, loop=False):
        self.music_paused = False
        if loop:
            pygame.mixer.music.play(-1)
        else:
            pygame.mixer.music.play()


    def unpause_music(self):
        self.music_paused = False
        pygame.mixer.music.unpause()

    def pause_music(self):
        self.music_paused = True
        pygame.mixer.music.pause()

    def toggle_music(self):
        if self.music_paused:
            self.unpause_music()
        else:
            self.pause_music()

    def exit(self):
        self.logger.info('Exit: GameState')
