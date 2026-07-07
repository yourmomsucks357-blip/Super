import json
import os

class Learner:
    @staticmethod
    def train(dataset_path: str, brain):
        """Train the brain from a JSONL dataset file."""
        if not os.path.exists(dataset_path):
            print(f"Dataset file not found: {dataset_path}")
            return
        
        with open(dataset_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    prompt = entry.get('prompt', '')
                    response = entry.get('response', '')
                    if prompt and response:
                        brain.learn(prompt, response)
                except json.JSONDecodeError:
                    print(f"Skipping malformed line: {line}")
                    continue

    @staticmethod
    def train_from_dict(data: dict, brain):
        """Train the brain from a dictionary."""
        for prompt, response in data.items():
            brain.learn(prompt, response)