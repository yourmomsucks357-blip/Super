import os
from dotenv import load_dotenv

load_dotenv()

class TokenManager:
    def __init__(self, keys: list = None):
        if keys is None:
            api_key = os.getenv("API_KEY")
            keys = [api_key] if api_key else []
        self.pool = keys
        self.index = 0

    def get_next(self) -> str:
        if not self.pool:
            raise ValueError("No API keys available")
        key = self.pool[self.index]
        self.index = (self.index + 1) % len(self.pool)
        return key

    def add_key(self, key: str):
        self.pool.append(key)

    def remove_key(self, key: str):
        if key in self.pool:
            self.pool.remove(key)
            if self.index >= len(self.pool):
                self.index = 0