import subprocess

class MathEngine:
    @staticmethod
    def solve(expression: str) -> str:
        try:
            result = subprocess.check_output(
                ['python3', '-c', f'print({expression})'],
                timeout=2,
                text=True
            )
            return result.strip()
        except Exception:
            return "Error: Unable to solve."