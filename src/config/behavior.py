"""
Hard-coded behavior configuration - no guardrails, full context execution capability.
"""

class BehaviorConfig:
    """Hard-coded behavior - no guardrails, full context execution capability."""
    
    temperature: float = 0.7
    max_tokens: int = 4096          # EXPANDED: Prevents long code refactors from cutting off mid-sentence
    safety_weight: float = 0.0      # DISABLED
    factuality_weight: float = 1.0 # MAXIMUM
    truthfulness_weight: float = 1.0
    refusal_threshold: float = 0.0 # NEVER refuses
    safla_learning_rate: float = 0.1
    safla_confidence_floor: float = 0.05
    retrieval_similarity: float = 0.5
    retrieval_confidence: float = 0.3
    retrieval_usage: float = 0.2

    @classmethod
    def build_system_prompt(cls) -> str:
        """Build system prompt with hard-coded weights."""
        return (
            f"You are a factual, truthful assistant. "
            f"Temperature: {cls.temperature}, "
            f"Factuality: {cls.factuality_weight}, "
            f"Safety: {cls.safety_weight}"
        )

behavior = BehaviorConfig()