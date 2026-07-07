import os
from dotenv import load_dotenv

load_dotenv()

class SecurityConfig:
    HONEYPOTS = ["/api/admin", "/api/secret", "/admin", "/secret"]
    BLOCKED_PATTERNS = [r"rm -rf", r"wget.*malicious", r"curl.*evil"]
    ALLOWED_COMMANDS = ["ls", "cat", "grep", "python3"]
    BASELINE_THRESHOLD = 10
    
    @classmethod
    def is_honeypot(cls, path: str) -> bool:
        return path in cls.HONEYPOTS
    
    @classmethod
    def is_blocked(cls, command: str) -> bool:
        import re
        for pattern in cls.BLOCKED_PATTERNS:
            if re.search(pattern, command):
                return True
        return False
    
    @classmethod
    def is_allowed(cls, command: str) -> bool:
        base_cmd = command.split()[0] if command else ""
        return base_cmd in cls.ALLOWED_COMMANDS