from typing import Literal, Optional
from pydantic import BaseModel, Field
import os


class AIModelConfig(BaseModel):
    provider: Literal["mock", "openai", "gemini", "anthropic"] = Field(
        default="mock",
        description="AI Provider backend (mock, openai, gemini, anthropic)"
    )
    model_name: str = Field(
        default="gpt-4o-mini",
        description="Model identifier"
    )
    max_tokens: int = Field(
        default=1024,
        ge=64,
        le=8192,
        description="Maximum response tokens"
    )
    temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Sampling temperature (lower = more deterministic for structured actions)"
    )
    timeout_seconds: int = Field(
        default=15,
        ge=1,
        le=60,
        description="Timeout for AI provider calls in seconds"
    )
    enable_ai_assistant: bool = Field(
        default=True,
        description="Global feature flag for AI assistant features"
    )
    enable_action_auto_confirm_for_safe_reads: bool = Field(
        default=True,
        description="Whether safe read-only queries bypass confirmation modal"
    )
    cost_per_1k_input_tokens: float = Field(
        default=0.00015,
        description="Estimated cost in USD per 1K input tokens"
    )
    cost_per_1k_output_tokens: float = Field(
        default=0.0006,
        description="Estimated cost in USD per 1K output tokens"
    )


def get_ai_config() -> AIModelConfig:
    """
    Constructs and returns the active AI configuration from environment variables or safe defaults.
    """
    provider_env = os.getenv("AI_PROVIDER", "mock").lower()
    if provider_env not in ["mock", "openai", "gemini", "anthropic"]:
        provider_env = "mock"

    model_env = os.getenv("AI_MODEL_NAME", "gpt-4o-mini" if provider_env == "openai" else "gemini-1.5-flash" if provider_env == "gemini" else "ozhzo-mock-v1")
    enable_env = os.getenv("ENABLE_AI_ASSISTANT", "true").lower() in ("true", "1", "yes")

    return AIModelConfig(
        provider=provider_env,
        model_name=model_env,
        enable_ai_assistant=enable_env
    )
