import pygame
import logging
from renderer import *
from main_menu_state import *
from globals import *
from state import *

pygame.init()
logging.basicConfig(level=logging.INFO)

clock = pygame.time.Clock()
logger = logging.getLogger(__name__)
renderer = Renderer(logger)
stateManager = StateManager(logger, renderer)

stateManager.push_state(MainMenuState())

while stateManager.update(clock.get_time()):
    renderer.update()
    clock.tick(FPS)

pygame.quit()
sys.exit(0)
