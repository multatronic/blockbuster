import pygame, sys
import logging
from renderer import *
from main_menu_state import MainMenuState
from configuration import ConfigurationManager
from state import StateManager

pygame.init()
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)
configuration = ConfigurationManager(logger)
clock = pygame.time.Clock()
renderer = Renderer(logger, configuration)
stateManager = StateManager(logger, renderer, configuration)

stateManager.push_state(MainMenuState())
while stateManager.update(clock.get_time()):
    renderer.update()
    clock.tick(configuration.get('fps'))

pygame.quit()
sys.exit(0)
