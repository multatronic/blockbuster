import pygame
import logging
from renderer import *
from game_state import *
from globals import *
from state import *

def save_high_scores():
    '''Write the high scores to disk.'''
    global SCORE, LEVEL, HIGH_SCORES
    # add our entry to the list and sort it from highest to lowest
    HIGH_SCORES.append([SCORE, LEVEL])
    HIGH_SCORES.sort(key=lambda x: int(x[0]), reverse=True)

    # now write the scores to a file
    with open('scores', 'w') as file:
        for entry in HIGH_SCORES:
            record = '{0}-{1}\n'.format(entry[0], entry[1])
            file.write(record)

def load_high_scores():
    '''Load the high score entries from disk.'''
    result = []
    try:
        with open('scores', 'r') as file:
            for line in file:
                result.append(line.split('-'))
    except FileNotFoundError:
        logger.info('No high score file was found')

    return result

pygame.init()
logging.basicConfig(level=logging.INFO)

clock = pygame.time.Clock()
logger = logging.getLogger(__name__)
renderer = Renderer(logger)
stateManager = StateManager(logger, renderer)

high_scores = load_high_scores()

stateManager.push_state(GameState(high_scores))

while stateManager.update(clock.get_time()):
    renderer.update()
    clock.tick(FPS)

pygame.quit()
sys.exit(0)