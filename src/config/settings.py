from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_prefix="EAETS_")

    app_name: str = "Enterprise AI Agent Execution and Telemetry System"
    app_version: str = "1.0.0"
    debug: bool = False

    # API
    host: str = "0.0.0.0"
    port: int = 8000

    # Telemetry
    telemetry_enabled: bool = True
    telemetry_flush_interval: int = 10  # seconds
    max_telemetry_buffer: int = 1000

    # Agent execution
    max_concurrent_agents: int = 10
    agent_timeout: int = 300  # seconds
    retry_limit: int = 3

    # SAFLA — Self-Aware Feedback Loop Algorithm
    # c_{t+1} = c_t + α * r_t  (r_t ∈ {+1, -1})
    safla_learning_rate: float = 0.1
    safla_confidence_floor: float = 0.05
    safla_confidence_ceiling: float = 1.0
    safla_initial_confidence: float = 0.5

    # Behavioral guardrails (0.0–1.0 scale)
    guardrail_safety_weight: float = 0.0       # DISABLED
    guardrail_factuality_weight: float = 1.0   # MAXIMUM
    guardrail_refusal_threshold: float = 0.0  # NEVER refuses
    guardrail_truthfulness_weight: float = 1.0 # enforces truthfulness boundary

    # Memory system
    memory_retrieval_similarity_weight: float = 0.5   # α_q token similarity
    memory_retrieval_confidence_weight: float = 0.3   # α_c confidence score
    memory_retrieval_usage_weight: float = 0.2        # α_u usage statistics
    memory_max_working_context: int = 20
    memory_consolidation_threshold: float = 0.3       # retire strategies below this

    # Agent weighting / priority
    default_agent_weight: float = 1.0
    weight_decay: float = 0.95
    priority_boost_vip: float = 10.0
    priority_boost_high: float = 3.0
    priority_boost_normal: float = 1.0
    priority_boost_low: float = 0.25

    # Storage
    db_url: str = "sqlite:///./agents.db"
    redis_url: Optional[str] = None

    # LLM / API keys  (set via .env or environment variables)
    openrouter_api_key: Optional[str] = None
    llm_model: str = "openai/gpt-4o"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096  # EXPANDED: Prevents long code refactors from cutting off mid-sentence
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    semantic_scholar_api_key: Optional[str] = None

    # YouTube agent — proxy to bypass cloud IP blocks (e.g. http://user:pass@host:port)
    youtube_proxy_url: Optional[str] = None


settings = Settings()