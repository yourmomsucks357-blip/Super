from src.agents.base import BaseAgent
from src.config.security import SecurityConfig
import json

class RouterAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.security = SecurityConfig()
    
    async def execute(self, request, reply=None):
        """
        Route requests and apply security checks.
        request should have: url, ip, method, body
        """
        # Check honeypots
        if self.security.is_honeypot(request.get('url', '')):
            print(f"🚨 HONEYPOT HIT: {request.get('ip', 'unknown')}")
            # Log to security_events.log
            with open('data/security_events.log', 'a') as f:
                f.write(f"HONEYPOT HIT: {request.get('ip', 'unknown')} - {request.get('url', '')}
")
            return {"error": "Not found"}, 404
        
        # Check for blocked patterns in body
        body = request.get('body', {})
        if isinstance(body, dict):
            body_str = json.dumps(body)
        else:
            body_str = str(body)
        
        if self.security.is_blocked(body_str):
            print(f"🚨 BLOCKED REQUEST: {request.get('ip', 'unknown')}")
            with open('data/security_events.log', 'a') as f:
                f.write(f"BLOCKED REQUEST: {request.get('ip', 'unknown')} - {body_str[:100]}
")
            return {"error": "Request blocked"}, 403
        
        return {"status": "routed", "url": request.get('url')}