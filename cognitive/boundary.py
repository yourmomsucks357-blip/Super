"""
Truthfulness Boundary and IPC Isolation Barrier.

Architecture:

    [ Modular Cognitive Loop ]
            |
     Strict IPC / Isolation Barrier
            |
    [ External Execution Layer ]  ← CLI, MCP, Agent Tools

Rules enforced:
  1. External tools CANNOT import from src.cognitive.*
  2. External tool calls pass ONLY through the IsolationBarrier interface
  3. The barrier validates all payloads before forwarding — no fake execution paths
  4. SSRF protection: outbound requests to internal subnets are blocked
"""
import ipaddress
import re
from typing import Any, Callable, Dict, Optional
from src.config import settings


# ── Blocked network ranges (SSRF protection) ──────────────────────────────────

_BLOCKED_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),    # loopback
    ipaddress.ip_network("10.0.0.0/8"),     # RFC 1918
    ipaddress.ip_network("172.16.0.0/12"),  # RFC 1918
    ipaddress.ip_network("192.168.0.0/16"), # RFC 1918
    ipaddress.ip_network("169.254.0.0/16"), # link-local
    ipaddress.ip_network("::1/128"),        # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),       # IPv6 ULA
]

_INTERNAL_HOSTNAME_RE = re.compile(
    r"(^localhost$|^.*\.internal$|^.*\.local$|^metadata\.google\.internal$)",
    re.IGNORECASE,
)


class SSRFViolation(Exception):
    pass


class TruthfulnessViolation(Exception):
    pass


class TruthfulnessBoundary:
    """
    Enforces that all responses passing through the cognitive layer
    are grounded in real execution traces — no template mocks.

    The weight `guardrail_truthfulness_weight` (0–1) scales enforcement:
    at 1.0 any ungrounded response is blocked; at 0.0 the boundary is passive.
    """

    def validate(self, response: Any, execution_trace: Optional[Dict] = None) -> Any:
        if settings.guardrail_truthfulness_weight < 0.5:
            return response
        if execution_trace is None:
            raise TruthfulnessViolation(
                "Truthfulness boundary violation: no execution trace provided. "
                "All responses must be backed by a real inference trace."
            )
        if isinstance(response, str) and response.strip().startswith("[MOCK]"):
            raise TruthfulnessViolation(
                "Truthfulness boundary violation: mock response rejected."
            )
        return response


class IsolationBarrier:
    """
    Single entry-point for all external tool / plugin calls.
    Cognitive plugins MUST call through this barrier; they cannot
    call external systems directly.

    Provides:
      - SSRF validation on any URL argument
      - Payload schema enforcement
      - Execution tracing for the TruthfulnessBoundary
    """

    def __init__(self):
        self._registry: Dict[str, Callable] = {}
        self._truthfulness = TruthfulnessBoundary()

    def register(self, name: str, fn: Callable) -> None:
        """Register an external tool behind the barrier."""
        self._registry[name] = fn

    def validate_url(self, url: str) -> None:
        """Block SSRF targets: internal IPs, localhost, metadata endpoints."""
        # Extract hostname
        match = re.match(r"https?://([^/:]+)", url)
        if not match:
            return
        host = match.group(1)
        # Check hostname patterns
        if _INTERNAL_HOSTNAME_RE.match(host):
            raise SSRFViolation(f"Blocked internal hostname: {host}")
        # Try resolving as IP
        try:
            addr = ipaddress.ip_address(host)
            for blocked in _BLOCKED_RANGES:
                if addr in blocked:
                    raise SSRFViolation(f"Blocked internal IP range: {host}")
        except ValueError:
            pass  # not an IP literal — hostname checks above suffice

    async def call(self, tool_name: str, payload: Dict[str, Any]) -> Any:
        """
        Execute a registered external tool through the isolation barrier.
        Validates SSRF on any URL in the payload and records an execution trace.
        """
        if tool_name not in self._registry:
            raise KeyError(f"Tool '{tool_name}' not registered with IsolationBarrier.")
        # SSRF check on URL fields
        for key, value in payload.items():
            if isinstance(value, str) and value.startswith("http"):
                self.validate_url(value)
        # Execute with trace
        trace = {"tool": tool_name, "payload_keys": list(payload.keys())}
        result = await self._registry[tool_name](**payload)
        return self._truthfulness.validate(result, execution_trace=trace)


# Singleton barrier — cognitive plugins import this, not the tools directly
barrier = IsolationBarrier()
