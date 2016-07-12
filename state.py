from globals import *

class State:
    def __init__(self, renderer, logger, state_manager):
        self.renderer = renderer
        self.state_manager = state_manager
        self.logger = logger

    def update(self, elapsed_time):
        self.logger.info('state run called')

    def enter(self):
        self.logger.info('state enter called')

    def exit(self):
        self.logger.info('state exit called')


class StateManager:
    def __init__(self, logger):
        self.logger = logger
        self.state_stack = []

    def get_active_state(self):
        stack_length = len(self.state_stack)
        if not stack_length:
            return None
        return self.state_stack[stack_length - 1]

    def push_state(self, state):
        self.state_stack.append(state)
        state.enter()

    def pop_state(self):
        active_state = self.get_active_state()
        if active_state:
            active_state.exit()
            self.state_stack.pop()

    def replace_state(self, state):
        self.pop_state()
        self.push_state(state)

    def update(self, elapsed_time):
        active_state = self.get_active_state()
        if active_state:
            active_state.update(elapsed_time)
