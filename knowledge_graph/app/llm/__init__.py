"""
LLM Factory - Mismo que Fase 2.
Soporta OpenAI y Google Gemini.
"""
from app.llm.factory import get_llm, validate_llm_config, get_provider_info
from app.llm.base import LLMInterface

__all__ = ["get_llm", "validate_llm_config", "get_provider_info", "LLMInterface"]

