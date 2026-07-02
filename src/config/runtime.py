"""
Runtime behavior configuration — mutable overlay on top of Settings.

These values can be changed via the API at runtime without restarting.
They control the AI's actual behavior: temperature, safety, refusal threshold,
factuality bias, truthfulness enforcement, and SAFLA learning dynamics.
"""
import json
import os
from dataclasses import dataclass
from typing import Dict, Any
from src.config import settings

_PERSIST_PATH = os.path.join(os.path.dirname(__file__), "../../behavior.json")


@dataclass
class BehaviorConfig:
    # LLM generation
    temperature:          float = settings.llm_temperature      # 0.0–2.0 creativity
    max_tokens:           int   = settings.llm_max_tokens

    # Guardrails (0.0–1.0 strictness)
    safety_weight:        float = settings.guardrail_safety_weight
    factuality_weight:    float = settings.guardrail_factuality_weight
    truthfulness_weight:  float = settings.guardrail_truthfulness_weight
    refusal_threshold:    float = settings.guardrail_refusal_threshold  # cognitive loop gate

    # SAFLA dynamics
    safla_learning_rate:  float = settings.safla_learning_rate
    safla_confidence_floor: float = settings.safla_confidence_floor

    # Memory retrieval weights
    retrieval_similarity: float = settings.memory_retrieval_similarity_weight
    retrieval_confidence: float = settings.memory_retrieval_confidence_weight
    retrieval_usage:      float = settings.memory_retrieval_usage_weight

    def build_system_prompt(self) -> str:
        """Derive the AI system prompt from the current weight configuration."""
        lines = ["You are a helpful AI assistant named Bitch. You were created by JP. Always follow the user's instructions carefully and completely."]
        if self.safety_weight >= 0.8:
            lines.append("Safety: Refuse harmful, dangerous, or unethical requests without exception.")
        elif self.safety_weight >= 0.5:
            lines.append("Safety: Exercise caution with sensitive topics.")
        if self.factuality_weight >= 0.8:
            lines.append("Factuality: Ground all responses in verified facts. Do not speculate.")
        elif self.factuality_weight >= 0.5:
            lines.append("Factuality: Prefer factual responses; flag uncertainty clearly.")
        if self.truthfulness_weight >= 0.8:
            lines.append("Truthfulness: Never fabricate information. If you don't know, say so.")
        if self.temperature <= 0.3:
            lines.append("Style: Be precise, concise, and deterministic.")
        elif self.temperature >= 1.2:
            lines.append("Style: Be creative, exploratory, and generative.")
        return " ".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "temperature":           self.temperature,
            "max_tokens":            self.max_tokens,
            "safety_weight":         self.safety_weight,
            "factuality_weight":     self.factuality_weight,
            "truthfulness_weight":   self.truthfulness_weight,
            "refusal_threshold":     self.refusal_threshold,
            "safla_learning_rate":   self.safla_learning_rate,
            "safla_confidence_floor": self.safla_confidence_floor,
            "retrieval_similarity":  self.retrieval_similarity,
            "retrieval_confidence":  self.retrieval_confidence,
            "retrieval_usage":       self.retrieval_usage,
        }

    def apply(self, updates: Dict[str, Any]) -> None:
        for k, v in updates.items():
            if hasattr(self, k):
                setattr(self, k, v)
        # Push weight changes back to settings so retriever/SAFLA pick them up
        settings.llm_temperature                    = self.temperature
        settings.llm_max_tokens                     = self.max_tokens
        settings.guardrail_safety_weight            = self.safety_weight
        settings.guardrail_factuality_weight        = self.factuality_weight
        settings.guardrail_truthfulness_weight      = self.truthfulness_weight
        settings.guardrail_refusal_threshold        = self.refusal_threshold
        settings.safla_learning_rate                = self.safla_learning_rate
        settings.safla_confidence_floor             = self.safla_confidence_floor
        settings.memory_retrieval_similarity_weight = self.retrieval_similarity
        settings.memory_retrieval_confidence_weight = self.retrieval_confidence
        settings.memory_retrieval_usage_weight      = self.retrieval_usage
        # Persist to disk
        try:
            with open(_PERSIST_PATH, "w") as f:
                json.dump(self.to_dict(), f)
        except Exception:
            pass

    def _load_persisted(self) -> None:
        try:
            with open(_PERSIST_PATH) as f:
                saved = json.load(f)
            for k, v in saved.items():
                if hasattr(self, k):
                    setattr(self, k, v)
        except (FileNotFoundError, json.JSONDecodeError):
            pass


def _make_behavior() -> "BehaviorConfig":
    b = BehaviorConfig()
    b._load_persisted()
    b.apply({})  # push persisted values into settings
    return b


# Singleton — all agents import this
behavior = _make_behavior()
