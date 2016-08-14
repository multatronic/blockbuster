from globals import *

class State:
    def __init__(self):
        self.renderer = None
        self.state_manager = None
        self.logger = None

    def inject_services(self, renderer, logger, state_manager):
        self.renderer = renderer
        self.state_manager = state_manager
        self.logger = logger

    def render(self):
        self.logger.info('state render called')

    def update(self, elapsed_time):
        self.logger.info('state run called')

    def enter(self):
        self.logger.info('state enter called')

    def exit(self):
        self.logger.info('state exit called')


class StateManager:
    def __init__(self, logger, renderer):
        self.logger = logger
        self.renderer = renderer
        self.state_stack = []

    def get_active_state(self):
        stack_length = len(self.state_stack)
        if not stack_length:
            return None
        return self.state_stack[stack_length - 1]

    def push_state(self, state):
        state.inject_services(self.renderer, self.logger, self)
        self.state_stack.append(state)
        state.enter()

    def clear_stack(self):
        while self.get_active_state():
            self.pop_state()

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
            active_state.render()
            return True
        else:
            return False
