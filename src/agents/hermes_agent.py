import os
import json
import subprocess
from typing import Any, Dict, List
import httpx
from .base import BaseAgent, AgentContext
from .registry import AgentRegistry


@AgentRegistry.register("assistant")
class HermesCodingAgent(BaseAgent):
    def __init__(self, agent_id: str = None, name: str = None):
        super().__init__(agent_id, name)
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        self.config_path = os.path.join(self.base_dir, "config/model-controller.json")
        self.load_config()

    def load_config(self) -> None:
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.cfg = json.load(f)

    async def execute(self, context: AgentContext, prompt: str = "", tool: str = None, **kwargs) -> Any:
        if tool == "file_read":
            return self.file_read(kwargs.get("file_path", ""))
        if tool == "file_write":
            return self.file_write(kwargs.get("file_path", ""), kwargs.get("content", ""))
        if tool == "terminal":
            return self.terminal(kwargs.get("command", ""), kwargs.get("args", []))
        
        return await self.chat(prompt, kwargs.get("memory_files", []))

    async def chat(self, prompt: str, memory_files: List[str]) -> Dict[str, str]:
        sys_path = os.path.join(self.base_dir, self.cfg["systemPromptPath"])
        rules_path = os.path.join(self.base_dir, self.cfg["projectRulesPath"])
        
        with open(sys_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()
        with open(rules_path, "r", encoding="utf-8") as f:
            project_rules = f.read()

        memory_content = self.load_project_memory(memory_files)
        full_prompt = f"{project_rules}

{memory_content}

{prompt}"

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.cfg['baseUrl']}/v1/chat/completions",
                json={
                    "model": self.cfg["modelName"],
                    "temperature": self.cfg["temperature"],
                    "top_p": self.cfg["top_p"],
                    "max_tokens": self.cfg["max_tokens"],
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": full_prompt}
                    ]
                }
            )
            response.raise_for_status()
            data = response.json()
            return {"response": data["choices"][0]["message"]["content"]}

    def safe_resolve(self, base_root: str, file_path: str) -> str:
        resolved_base = os.path.abspath(os.path.join(self.base_dir, base_root))
        resolved_target = os.path.abspath(os.path.join(resolved_base, file_path))
        if resolved_target == resolved_base or resolved_target.startswith(resolved_base + os.sep):
            return resolved_target
        raise ValueError("Invalid file path / Path traversal detected")

    def load_project_memory(self, requested_files: List[str]) -> str:
        memory_content = ""
        allowed_extensions = {".md", ".txt", ".json", ".ts", ".tsx", ".js", ".prisma"}
        blocked_filenames = {".env", ".env.local", ".env.production"}
        blocked_extensions = {".pem", ".key", ".p12", ".sqlite", ".db"}
        memory_root = self.cfg["projectMemoryRoot"]

        for file in requested_files:
            _, ext = os.path.splitext(file)
            if ext not in allowed_extensions:
                continue
            basename = os.path.basename(file)
            if basename in blocked_filenames or ext in blocked_extensions:
                continue

            try:
                file_path = self.safe_resolve(memory_root, file)
                if os.path.exists(file_path):
                    if os.path.getsize(file_path) <= 1024 * 1024:
                        with open(file_path, "r", encoding="utf-8") as f:
                            memory_content += f.read() + "

"
            except ValueError:
                continue
        return memory_content

    def file_read(self, file_path: str) -> Dict[str, Any]:
        if "file_read" not in self.cfg["allowedTools"]:
            return {"error": "File read not allowed"}
        
        try:
            allowed_path = self.safe_resolve(self.cfg["repoRoot"], file_path)
        except ValueError as e:
            return {"error": str(e)}

        if not os.path.exists(allowed_path):
            return {"error": "File not found"}

        blocked_filenames = {".env", ".env.local", ".env.production"}
        blocked_extensions = {".pem", ".key", ".p12", ".sqlite", ".db"}
        allowed_extensions = {".md", ".txt", ".json", ".ts", ".tsx", ".js", ".prisma"}
        basename = os.path.basename(allowed_path)
        _, extname = os.path.splitext(allowed_path)

        if basename in blocked_filenames or extname in blocked_extensions:
            return {"error": "File read not allowed"}
        if extname not in allowed_extensions:
            return {"error": "File extension not allowed"}

        with open(allowed_path, "r", encoding="utf-8") as f:
            return {"content": f.read()}

    def file_write(self, file_path: str, content: str) -> Dict[str, Any]:
        if "file_write" not in self.cfg["allowedTools"]:
            return {"error": "File write not allowed"}

        try:
            allowed_path = self.safe_resolve(self.cfg["repoRoot"], file_path)
        except ValueError as e:
            return {"error": str(e)}

        normalized_path = file_path.replace("\", "/").lstrip("./")
        frontend_paths = ["frontend/", "client/", "web/", "app/", "pages/", "components/", "src/frontend/"]
        if not self.cfg["allowFrontendFiles"] and any(normalized_path.startswith(p) for p in frontend_paths):
            return {"error": "Frontend file write not allowed"}

        blocked_filenames = {".env", ".env.local", ".env.production"}
        blocked_extensions = {".pem", ".key", ".p12", ".sqlite", ".db"}
        allowed_extensions = {".md", ".txt", ".json", ".ts", ".tsx", ".js", ".prisma"}
        basename = os.path.basename(allowed_path)
        _, extname = os.path.splitext(allowed_path)

        if basename in blocked_filenames or extname in blocked_extensions:
            return {"error": "File write not allowed"}
        if extname not in allowed_extensions:
            return {"error": "File extension not allowed"}

        os.makedirs(os.path.dirname(allowed_path), exist_ok=True)
        with open(allowed_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True}

    def terminal(self, command: str, args: List[str]) -> Dict[str, Any]:
        if "terminal" not in self.cfg["allowedTools"]:
            return {"error": "Terminal not allowed"}

        rules = self.cfg["allowedTerminalCommands"].get(command)
        if not rules:
            return {"error": "Command not allowed"}

        is_allowed = False
        for rule in rules:
            rule_args = rule["args"]
            prefix_matches = len(rule_args) <= len(args) and all(args[i] == rule_args[i] for i in range(len(rule_args)))
            if not prefix_matches:
                continue
            if rule["allowExtraArgs"] or len(rule_args) == len(args):
                is_allowed = True
                break

        if not is_allowed:
            return {"error": "Command arguments not allowed"}

        try:
            resolved_root = self.safe_resolve(self.cfg["repoRoot"], "")
            res = subprocess.run(
                [command] + args,
                cwd=resolved_root,
                capture_output=True,
                text=True,
                shell=False
            )
            return {"stdout": res.stdout, "stderr": res.stderr, "exitCode": res.returncode}
        except Exception as e:
            return {"error": f"Command execution failed: {str(e)}"}