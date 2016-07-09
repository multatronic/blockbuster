import pygame
import sys
import logging
from pygame.locals import *
from random import randrange

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------TERMINOLOGY---------------------
# TILE = A non-moving 'slot' on the game board, either black or colored in.
# BOARD = A two-dimensional array of Tiles, describing the entire game space
# BLOCK = A moving non-black rectangle. Turns into a tile when it stops moving (see fixate_blocks_on_board()).
# PIECE = A collection of blocks which are controlled by the player
# ---------------------------------------------------

VERSION_NUMBER = '0.1.6'
FAST_FORWARD_MODE = False
DEBUG_MODE = False
GAME_OVER = False
GAME_PAUSED = False

DISPLAY = None
CLOCK = pygame.time.Clock()
FPS = 60

SCORE = 0
LEVEL = 1
POINTS_PER_BLOCK = 5
UPDATE_SPEED = 500  # update board every x milliseconds
MULIGANS = 0  # number of times the player can generate a new 'next' piece (see also: spawn_new_piece())

PIECE_POSITION = None  # top left coordinate of current piece array on the board
BOARD = []
PREVIEW_WINDOW = []

# we declare a few lists here which will store references to various tiles/blocks/rows/columns
# (otherwise we would have to scan the entire board every time we need to update something)
FALLING_BLOCKS = []  # blocks which are falling, but not part of a controlled piece
CONTROLLED_BLOCKS = []  # blocks which are part of a controlled piece (falling, but can also move left/right)
FADING_TILES = []  # tiles which are in the act of fading out (e.g. part of a color streak)
TILES_TO_BE_RESET = []  # board tiles which will be reset (e.g. part of a color streak, fully faded out)
BLOCKS_TO_BE_FIXATED = []  # list of blocks which have stopped moving and will be fixated on the board
DIRTY_ROWS = []  # list of rows which need to be checked for matches
DIRTY_COLUMNS = []  # list of columns which need to be checked for matches

# layout variables
BLOCK_SIZE = 20  # block size in pixels
BOARD_HEIGHT = 20  # board height in blocks
BOARD_WIDTH = 16  # board width in blocks
PREVIEW_HEIGHT = 3  # preview window height in blocks
PREVIEW_WIDTH = 3  # preview window widht in blocks
MARGIN_LEFT = 10  # space between left board border and window border
MARGIN_TOP = 10  # space between top board border and window border
MARGIN_BOTTOM = 10  # space between bottom board border and window border
MARGIN_RIGHT = PREVIEW_WIDTH * BLOCK_SIZE  # space between right preview window border and window border
WINDOW_HEIGHT = (BLOCK_SIZE * BOARD_HEIGHT) + MARGIN_BOTTOM + MARGIN_TOP
WINDOW_WIDTH = (BLOCK_SIZE * (BOARD_WIDTH + PREVIEW_WIDTH)) + MARGIN_LEFT + MARGIN_RIGHT
PREVIEW_WINDOW_OFFSET = MARGIN_LEFT + (BOARD_WIDTH * BLOCK_SIZE) + 20
BIG_FONT, SMALL_FONT = None, None
CURRENT_FADEOUT_VALUE = 2  # current width of the fadeout rectangle

HIGH_SCORES = []
LOWEST_HIGH_SCORE = None
LAST_BARRICADE_LEVEL = 0  # the last level when a barricade was spawned


BLACK = (0, 0, 0)
COLORS = [
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255),
    (255, 255, 0)
]

TEMPLATES = (
    (
        (0, 1, 1),
        (0, 1, 0),
        (0, 1, 0)
    ),
    (
        (0, 1, 0),
        (1, 1, 1)
    ),
    (
        (1, 1, 0),
        (0, 1, 1)
    ),
    (
        (1, 1),
        (1, 1)
    )
)

# the colorized template is a copy of a single template from the list above
# where every 1 has been replaced with a color value

# when a piece is rotated, what is actually happening is that this matrix is
# rotated, and the CONTROLLED_BLOCKS array is emptied and regenerated
COLORIZED_TEMPLATE = []
NEXT_COLORIZED_TEMPLATE = []


class Tile:
    """A tile represents a slot on the board"""

    def __init__(self, x, y, rect_offset=(0, 0)):
        self.color = BLACK
        self.column = x
        self.row = y
        self.rect = pygame.Rect(rect_offset[0] + MARGIN_LEFT + (BLOCK_SIZE * x),
                                rect_offset[1] + MARGIN_TOP + (BLOCK_SIZE * y), BLOCK_SIZE, BLOCK_SIZE)


def add_block_descriptor(block_list, color, column, row):
    '''Add a block descriptor to a block_list (e.g register a falling block).'''
    block_list.append({
        'color': color,
        'column': column,
        'row': row
    })


def is_in_block_list(block_list, coordinate):
    '''Determine wether a coordinate is found within a given list of block descriptors.'''
    result = False
    for block in block_list:
        if block['column'] == coordinate[0] and block['row'] == coordinate[1]:
            result = True
            break
    return result


def is_to_be_fixated(coordinate):
    '''Is coordinate a part of the list of blocks to be fixated?'''
    return is_in_block_list(BLOCKS_TO_BE_FIXATED, coordinate)


def is_piece_block(coordinate):
    '''Is coordinate a part of the list of blocks that are controlled by the player?'''
    return is_in_block_list(CONTROLLED_BLOCKS, coordinate)


def is_falling_block(coordinate):
    '''Is coordinate a part of the list of blocks that are falling?'''
    return is_in_block_list(FALLING_BLOCKS, coordinate)


def is_within_bounds(coordinate):
    '''Is coordinate within the bounds of the game board?'''
    return 0 <= coordinate[0] < BOARD_WIDTH and 0 <= coordinate[1] < BOARD_HEIGHT


def fixate_blocks_on_board():
    '''Fixate a block on the board (i.e. transform it to a tile when it has stopped moving).'''
    global BOARD, BLOCKS_TO_BE_FIXATED
    for block in BLOCKS_TO_BE_FIXATED:
        BOARD[block['column']][block['row']].color = block['color']
    BLOCKS_TO_BE_FIXATED = []


def detach_tile_from_board(tile):
    '''Detach a tile from the board (i.e. change a Tile to a falling block).'''
    global FALLING_BLOCKS
    if not is_falling_block((tile.column, tile.row)):
        add_block_descriptor(FALLING_BLOCKS, tile.color, tile.column, tile.row)
    tile.color = BLACK


def rotate_matrix(matrix):
    '''Rotate a matrix 90 degrees clockwist by transposing it + reversing the columns.'''
    matrix[:] = [[column[i] for column in reversed(matrix)] for i in range(len(matrix[0]))]


def is_vacant_tile(coordinate):
    '''Is the coordinate an empty slot on the board?'''
    # within playing field?
    if not is_within_bounds(coordinate):
        return False

    # empty tile?
    return BOARD[coordinate[0]][coordinate[1]].color == BLACK


def load_high_scores():
    '''Load the high score entries from disk.'''
    global HIGH_SCORES, LOWEST_HIGH_SCORE
    HIGH_SCORES = []
    try:
        with open('scores', 'r') as file:
            for line in file:
                HIGH_SCORES.append(line.split('-'))
    except FileNotFoundError:
        logger.info('No high score file was found')

    # we write the high scores out to disk sorted from highest to lowest
    if len(HIGH_SCORES):
        LOWEST_HIGH_SCORE = HIGH_SCORES[len(HIGH_SCORES) - 1][0]


def save_high_scores():
    '''Write the high scores to disk.'''
    global SCORE, LEVEL, HIGH_SCORES
    # add our entry to the list and sort it from highest to lowest
    HIGH_SCORES.append([SCORE, LEVEL])
    HIGH_SCORES.sort(key=lambda x: int(x[0]), reverse=True)

    # now write the scores to a file
    with open('scores', 'w') as file:
        for entry in HIGH_SCORES:
            record = '{0}-{1}'.format(entry[0], entry[1])
            file.write(record)


def increase_score(increase=0):
    '''Increase the player score and adjust difficulty.'''
    global MULIGANS, SCORE, LEVEL, UPDATE_SPEED
    SCORE += increase
    SCORE += MULIGANS * 5
    LEVEL = (SCORE // 200) + 1
    UPDATE_SPEED = 500 - ((LEVEL // 5) * 25)
    if UPDATE_SPEED < 200:
        UPDATE_SPEED = 200


# todo generate surface once and store it instead of doing it every update tick
def draw_text(text, position=None, small=False):
    '''Draw some text (small or large) on screen.'''
    text_surface = SMALL_FONT.render(text, True, (200, 200, 200)) if small else \
        BIG_FONT.render(text, True, (200, 200, 200))
    text_rect = text_surface.get_rect()

    # if no position was given, center text on board
    if position is None:
        position = [MARGIN_LEFT + ((BLOCK_SIZE * BOARD_WIDTH) / 2), MARGIN_TOP + ((BLOCK_SIZE * BOARD_HEIGHT) / 2)]
        position[0] -= text_surface.get_width() / 2
        position[1] -= text_surface.get_height() / 2

    text_rect.topleft = position
    DISPLAY.blit(text_surface, text_rect)


def increase_fadeout_value(last_tick):
    global CURRENT_FADEOUT_VALUE, FADING_TILES, TILES_TO_BE_RESET, DISPLAY

    if len(FADING_TILES):
        if CURRENT_FADEOUT_VALUE >= BLOCK_SIZE:
            CURRENT_FADEOUT_VALUE = 0
            TILES_TO_BE_RESET += FADING_TILES
            FADING_TILES = []
            remove_marked_tiles()

        CURRENT_FADEOUT_VALUE += (last_tick / 1000) * 4


def remove_marked_tiles():
    global POINTS_PER_BLOCK, TILES_TO_BE_RESET
    columns_to_adjust = {}

    score_increase = 0
    # blank out the tiles and remember what column they are in. Also remember the lowest row
    # (= highest coordinate) in this column where a tile was blanked out.
    for tile in TILES_TO_BE_RESET:
        score_increase += POINTS_PER_BLOCK

        tile.color = BLACK
        if tile.column not in columns_to_adjust or columns_to_adjust[tile.column] < tile.row:
            columns_to_adjust[tile.column] = tile.row

    TILES_TO_BE_RESET = []

    # put all the blocks above this one on the list of moving blocks
    # (provided it's not already on there)
    for column in columns_to_adjust:
        for row in range(0, columns_to_adjust[column]):
            dest_tile = BOARD[column][row]
            if dest_tile.color != BLACK:
                detach_tile_from_board(dest_tile)
    if score_increase:
        increase_score(score_increase)


def move_piece(direction=(1, 0)):
    all_tiles_available = True

    # first pass: check if the tiles we want to move to are all available
    for block in CONTROLLED_BLOCKS:
        # check if the tile we want to move to is available
        desired_coordinate = (block['column'] + direction[0], block['row'])
        if not is_vacant_tile(desired_coordinate) or is_falling_block(desired_coordinate):
            all_tiles_available = False
            break

    # second pass: actually move the blocks
    if all_tiles_available:
        PIECE_POSITION[0] += direction[0]

        for block in CONTROLLED_BLOCKS:
            block['column'] += direction[0]


def spawn_area_available(template=None):
    global COLORIZED_TEMPLATE
    if template is None:
        template = COLORIZED_TEMPLATE

    all_tiles_available = True
    for row in range(PIECE_POSITION[1], PIECE_POSITION[1] + len(template)):
        for column in range(PIECE_POSITION[0], PIECE_POSITION[0] + len(template[0])):
            # check if the tile we want to move to is available
            desired_coordinate = (column, row)
            if not is_vacant_tile(desired_coordinate) or is_falling_block(desired_coordinate):
                all_tiles_available = False
                break
    return all_tiles_available


def spawn_barricade():
    global BOARD_WIDTH, FALLING_BLOCKS, LEVEL
    number_of_rows = 1 + (LEVEL // 20)  # add an extra barricade row every 20 levels

    for row in range(number_of_rows):
        # generate an array of random colors as wide as the game board
        chosen_colors = pick_random_colors(BOARD_WIDTH)
        for column in range(BOARD_WIDTH):
            add_block_descriptor(FALLING_BLOCKS, chosen_colors[column], column, row)


def spawn_new_piece():
    global GAME_OVER, COLORIZED_TEMPLATE, NEXT_COLORIZED_TEMPLATE, PIECE_POSITION, MULIGANS
    COLORIZED_TEMPLATE = list(NEXT_COLORIZED_TEMPLATE)
    PIECE_POSITION = [6, 0]
    if spawn_area_available():
        generate_next_colorized_template()
        generate_controlled_blocks_from_colorized_template()
        MULIGANS = 5  # reset muligans
    else:
        save_high_scores()
        GAME_OVER = True


def rotate_piece():
    global COLORIZED_TEMPLATE
    rotated_matrix = list(COLORIZED_TEMPLATE)
    rotate_matrix(rotated_matrix)

    if spawn_area_available(rotated_matrix):
        COLORIZED_TEMPLATE = rotated_matrix
        generate_controlled_blocks_from_colorized_template()


def pick_random_colors(amount=1, allow_duplicates=True):
    global COLORS
    # select a few random colors
    result = []

    for i in range(amount):
        color_accepted = False
        while not color_accepted:
            random_color = COLORS[randrange(0, len(COLORS))]
            if allow_duplicates or random_color not in result:
                result.append(random_color)
                color_accepted = True

    return result


def generate_next_colorized_template():
    global NEXT_COLORIZED_TEMPLATE, PIECE_POSITION
    NEXT_COLORIZED_TEMPLATE = []

    piece_template_index = randrange(0, len(TEMPLATES))

    # select a few random colors, allowing duplicates
    chosen_colors = pick_random_colors(1 + (LEVEL // 5))

    for row in PREVIEW_WINDOW:
        for column in row:
            column.color = BLACK

    for row in range(len(TEMPLATES[piece_template_index])):
        NEXT_COLORIZED_TEMPLATE.append([])
        for column in range(len(TEMPLATES[piece_template_index][row])):
            generated_color = BLACK
            if TEMPLATES[piece_template_index][row][column] == 1:
                generated_color = chosen_colors[randrange(0, len(chosen_colors))]
            NEXT_COLORIZED_TEMPLATE[row].append(generated_color)
            PREVIEW_WINDOW[column][row].color = generated_color


def generate_controlled_blocks_from_colorized_template():
    global PIECE_POSITION, COLORIZED_TEMPLATE, CONTROLLED_BLOCKS

    # make sure we're not controlling any leftovers
    CONTROLLED_BLOCKS = []

    spawn_coord = list(PIECE_POSITION)

    number_of_rows = len(COLORIZED_TEMPLATE)
    number_of_columns = len(COLORIZED_TEMPLATE[0])

    for row in range(number_of_rows):
        for column in range(number_of_columns):
            if COLORIZED_TEMPLATE[row][column] != BLACK and is_vacant_tile(spawn_coord):
                add_block_descriptor(CONTROLLED_BLOCKS, COLORIZED_TEMPLATE[row][column],
                                     spawn_coord[0], spawn_coord[1])

            spawn_coord[0] += 1
        spawn_coord[1] += 1
        spawn_coord[0] = PIECE_POSITION[0]


def draw_board_border():
    global DISPLAY, BOARD_HEIGHT, BOARD_WIDTH, MARGIN_LEFT, MARGIN_BOTTOM, MARGIN_TOP
    pygame.draw.rect(DISPLAY, (100, 100, 100), (MARGIN_LEFT, MARGIN_TOP, (BOARD_WIDTH * BLOCK_SIZE),
                     (BOARD_HEIGHT * BLOCK_SIZE)), 5)


# todo: set tile color only once, then just draw the rect
def render_preview_window():
    global NEXT_COLORIZED_TEMPLATE
    for row in range(len(PREVIEW_WINDOW)):
        for column in range(len(PREVIEW_WINDOW[0])):
                block = PREVIEW_WINDOW[row][column]
                pygame.draw.rect(DISPLAY, block.color, block.rect)
                pygame.draw.rect(DISPLAY, BLACK, block.rect, 1)


def render_fadeout():
    global FADING_TILES, DISPLAY
    fadeout_rect = pygame.Rect(0, 0, CURRENT_FADEOUT_VALUE, CURRENT_FADEOUT_VALUE)
    for tile in FADING_TILES:
        fadeout_rect.center = tile.rect.center
        DISPLAY.fill(BLACK, fadeout_rect)


def render():
    global DISPLAY, GAME_OVER

    DISPLAY.fill(BLACK)

    draw_board_border()

    render_preview_window()

    def render_block(block_to_render):
        rect = BOARD[block_to_render['column']][block_to_render['row']].rect
        pygame.draw.rect(DISPLAY, block_to_render['color'], rect)  # draw the colored piece
        pygame.draw.rect(DISPLAY, BLACK, rect, 1)  # draw a little black border

    # draw static tiles
    for row in BOARD:
        for tile in row:
            pygame.draw.rect(DISPLAY, tile.color, tile.rect)  # draw the colored piece
            pygame.draw.rect(DISPLAY, BLACK, tile.rect, 1)  # draw a little black border

    # draw falling and controller blocks
    for block in FALLING_BLOCKS:
        render_block(block)

    for block in CONTROLLED_BLOCKS:
        render_block(block)

    if DEBUG_MODE and is_within_bounds(PIECE_POSITION):
        spawn_tile = BOARD[PIECE_POSITION[0]][PIECE_POSITION[1]]
        pygame.draw.rect(DISPLAY, (255, 255, 255), spawn_tile.rect, 2)

    if GAME_OVER:
        draw_text('GAME OVER')
    elif GAME_PAUSED:
        draw_text('PAUSED')

    draw_stats()
    render_fadeout()
    pygame.display.update()


def stop_game():
    pygame.quit()
    sys.exit(0)

def mark_matches(index=0, vertical=True):
    global BOARD
    current_color = None
    current_streak = []
    # marked_tiles = []

    def flush_streak():
        global TILES_TO_BE_RESET, FADING_TILES
        nonlocal current_streak
        if len(current_streak) > 3:
            FADING_TILES += current_streak
        current_streak = []

    # sweep from top to bottom or left to right
    range_to_check = range(BOARD_HEIGHT) if vertical else range(BOARD_WIDTH)

    for current in range_to_check:
        tile_to_check = BOARD[index][current] if vertical else BOARD[current][index]

        # check if it's the last piece in a row or column (which always breaks the streak)
        is_last = (current == BOARD_HEIGHT - 1) if vertical else (current == BOARD_WIDTH - 1)

        if tile_to_check.color != BLACK:
            if current_color is None or current_color != tile_to_check.color:  # color does not match the previous one
                flush_streak()
                current_color = tile_to_check.color
            current_streak.append(tile_to_check)

            if is_last:  # last tile - flush whatever we have in the streak buffer
                flush_streak()
        else:  # the current tile is black
            flush_streak()


def sort_blocks_vertically(block_list):
    return sorted(block_list, key=lambda x: x['row'], reverse=True)


def move_blocks_down(block_list):
    global DIRTY_COLUMNS, DIRTY_ROWS, BLOCKS_TO_BE_FIXATED
    sorted_list = sort_blocks_vertically(block_list)
    # sorted_block_list = sort_blocks_vertically(block_list)
    collision_occured = False
    for block in sorted_list:
        destination = (block['column'], block['row'] + 1)
        if is_vacant_tile(destination) and not is_to_be_fixated(destination):
            block['row'] += 1
        else:
            collision_occured = True
            BLOCKS_TO_BE_FIXATED.append(block)
            block['stopped'] = True
            if block['row'] not in DIRTY_ROWS:
                DIRTY_ROWS.append(block['row'])
            if block['column'] not in DIRTY_COLUMNS:
                DIRTY_COLUMNS.append(block['column'])

    # slice out the blocks which were not stopped
    block_list[:] = [block for block in block_list if 'stopped' not in block]
    return collision_occured


def update_board():
    # 1: update falling blocks
    global TILES_TO_BE_RESET, FALLING_BLOCKS, CONTROLLED_BLOCKS, DIRTY_COLUMNS, DIRTY_ROWS, BLOCKS_TO_BE_FIXATED

    move_blocks_down(FALLING_BLOCKS)

    # if the controlled piece collided with anything add it to the falling blocks
    # move the controlled piece down, and check if it collided with anything
    # (we'll want to stop controlling them in that case)
    piece_collision = move_blocks_down(CONTROLLED_BLOCKS)
    PIECE_POSITION[1] += 1

    # list and stop controlling it
    if piece_collision:
        FALLING_BLOCKS += CONTROLLED_BLOCKS
        CONTROLLED_BLOCKS = []

    # fixate the blocks which have stopped moving
    fixate_blocks_on_board()

    # when things have stopped moving, mark matching block groups and remove them
    if not len(FALLING_BLOCKS):
        for row in DIRTY_ROWS:
            mark_matches(row, False)

        for column in DIRTY_COLUMNS:
            mark_matches(column)

        DIRTY_COLUMNS = []
        DIRTY_ROWS = []

    remove_marked_tiles()


def draw_stats():
    global SCORE, LEVEL, PREVIEW_WINDOW_OFFSET, MULIGANS, HIGHEST_HIGH_SCORE
    top_margin = MARGIN_TOP + (PREVIEW_HEIGHT * BLOCK_SIZE) + 10
    draw_text('level: %s' % LEVEL, (PREVIEW_WINDOW_OFFSET, top_margin), True)
    draw_text('score: %s' % SCORE, (PREVIEW_WINDOW_OFFSET, top_margin + 15), True)
    draw_text('speed: %ss' % (UPDATE_SPEED / 1000), (PREVIEW_WINDOW_OFFSET, top_margin + 30), True)
    draw_text('mulligans: %s' % MULIGANS, (PREVIEW_WINDOW_OFFSET, top_margin + 45), True)


def main():
    global VERSION_NUMBER, DISPLAY, PREVIEW_WINDOW, BOARD, DEBUG_MODE, GAME_PAUSED,\
        FAST_FORWARD_MODE, UPDATE_SPEED, BIG_FONT, SMALL_FONT, PREVIEW_WINDOW_OFFSET, MULIGANS, LAST_BARRICADE_LEVEL

    last_update = 0
    pygame.init()

    load_high_scores()
    pygame.display.set_caption('BLOCK BUSTER (v%s)' % VERSION_NUMBER)
    BIG_FONT = pygame.font.Font(None, 30)
    SMALL_FONT = pygame.font.Font(None, 20)

    DISPLAY = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    BOARD = [[Tile(x, y) for y in range(BOARD_HEIGHT)] for x in range(BOARD_WIDTH)]

    PREVIEW_WINDOW = [[Tile(x, y, (PREVIEW_WINDOW_OFFSET, 0)) for y in range(PREVIEW_HEIGHT)]
                      for x in range(PREVIEW_HEIGHT)]
    generate_next_colorized_template()

    while True:
        for event in pygame.event.get():
            if event.type == QUIT:
                stop_game()
            elif event.type == KEYDOWN:
                if GAME_OVER:
                    stop_game()
                elif event.key == K_DOWN:
                    FAST_FORWARD_MODE = True
            elif event.type == KEYUP:
                if event.key == K_DOWN:
                    FAST_FORWARD_MODE = False
                elif event.key == K_LEFT:
                    move_piece((-1, 0))
                elif event.key == K_RIGHT:
                    move_piece((1, 0))
                elif event.key == K_UP:
                    rotate_piece()
                elif event.key == K_ESCAPE:
                    stop_game()
                elif event.key == K_p:
                    GAME_PAUSED = not GAME_PAUSED
                elif event.key == K_RCTRL:
                    if MULIGANS > 0:
                        MULIGANS -= 1
                        generate_next_colorized_template()
                elif event.key == K_d:
                    DEBUG_MODE = not DEBUG_MODE

        # if nothing is moving on the board either spawn a new piece or a barricade (depending on the current level)
        if not (len(FALLING_BLOCKS) or len(CONTROLLED_BLOCKS)):
            if LEVEL - LAST_BARRICADE_LEVEL == 5:
                LAST_BARRICADE_LEVEL = LEVEL
                spawn_barricade()
            else:
                spawn_new_piece()

        if not GAME_PAUSED:
            increase_fadeout_value(last_update)

            update_required = last_update >= UPDATE_SPEED or (FAST_FORWARD_MODE and last_update >= 15)
            if not len(FADING_TILES) and update_required:
                update_board()
                last_update = 0

            last_update += CLOCK.get_time()

        render()
        CLOCK.tick(FPS)

if __name__ == '__main__':
    main()
