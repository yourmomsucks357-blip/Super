from .cache import APCache
from .math import MathEngine

class PrimaryBrain:
    def compute(self, input_data):
        # Primary computation logic
        return f"Primary: {input_data}"

class SecondaryBrain:
    def __init__(self):
        self.cache = APCache()
        self.math = MathEngine()

    def get(self, key):
        return self.cache.get(key)

    def solve_math(self, expression):
        return self.math.solve(expression)

class DualBrain:
    def __init__(self):
        self.primary = PrimaryBrain()
        self.secondary = SecondaryBrain()

    def process(self, input_data):
        cached = self.secondary.get(input_data)
        if cached:
            return cached
        return self.primary.compute(input_data)