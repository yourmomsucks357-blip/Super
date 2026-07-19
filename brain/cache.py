import json
import os

class APCache:
    def __init__(self, file_path="data/cache.json"):
        self.file_path = file_path
        self.cache = {}
        self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    self.cache = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.cache = {}

    def _save(self):
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, 'w') as f:
            json.dump(self.cache, f, indent=2)

    def get(self, key):
        return self.cache.get(key)

    def set(self, key, value):
        self.cache[key] = value
        self._save()

    def delete(self, key):
        if key in self.cache:
            del self.cache[key]
            self._save()

    def clear(self):
        self.cache = {}
        self._save()