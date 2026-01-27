"""
TrackedLLM - Wrapper que intercepta llamadas LLM para tracking de tokens.
"""
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult, ChatGeneration

from app.services.token_tracker import token_tracker
from app.config import settings

logger = logging.getLogger(__name__)


class TrackedLLM(BaseChatModel):
    """
    Wrapper que envuelve un LLM base y captura tokens automáticamente.
    
    Intercepta ainvoke() e invoke() para registrar tokens en TokenTracker.
    """
    
    def __init__(
        self,
        llm: BaseChatModel,
        node_name: str,
        inference_type: str = "general"
    ):
        """
        Inicializa el wrapper.
        
        Args:
            llm: LLM base a envolver
            node_name: Nombre del nodo (ej: "manager", "financiero_planificar")
            inference_type: Tipo de inferencia (ej: "planning", "synthesis")
        """
        # Llamar a super().__init__() sin argumentos para BaseChatModel
        super().__init__()
        # Asignar atributos usando object.__setattr__ para evitar validación de Pydantic
        object.__setattr__(self, 'llm', llm)
        object.__setattr__(self, 'node_name', node_name)
        object.__setattr__(self, 'inference_type', inference_type)
        
        # Extraer provider y model del LLM base
        object.__setattr__(self, 'provider', settings.LLM_PROVIDER)
        object.__setattr__(self, 'model', settings.LLM_MODEL)
    
    @property
    def _llm_type(self) -> str:
        """Tipo del LLM (delegado al LLM base)."""
        return self.llm._llm_type
    
    def _extract_token_usage(
        self,
        response: Any
    ) -> tuple[int, int, int]:
        """
        Extrae tokens de la respuesta del LLM.
        
        Args:
            response: Respuesta del LLM (AIMessage o similar)
        
        Returns:
            tuple: (prompt_tokens, completion_tokens, total_tokens)
        """
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        
        # Intentar extraer de response_metadata (OpenAI)
        if hasattr(response, 'response_metadata'):
            metadata = response.response_metadata or {}
            
            # OpenAI format
            token_usage = metadata.get("token_usage")
            if token_usage:
                prompt_tokens = token_usage.get("prompt_tokens", 0)
                completion_tokens = token_usage.get("completion_tokens", 0)
                total_tokens = token_usage.get("total_tokens", 0)
            
            # Google format (usage_metadata)
            usage_metadata = metadata.get("usage_metadata")
            if usage_metadata and not total_tokens:
                prompt_tokens = usage_metadata.get("prompt_token_count", 0)
                completion_tokens = usage_metadata.get("candidates_token_count", 0)
                total_tokens = usage_metadata.get("total_token_count", 0)
        
        # Si no hay metadata, intentar calcular con tiktoken (fallback)
        if total_tokens == 0:
            try:
                import tiktoken
                
                # Obtener encoding según el modelo
                model_name = self.model.lower()
                if "gpt-4" in model_name or "gpt-3.5" in model_name:
                    encoding = tiktoken.encoding_for_model(model_name)
                elif "gemini" in model_name:
                    # Gemini usa cl100k_base (mismo que GPT-3.5)
                    encoding = tiktoken.get_encoding("cl100k_base")
                else:
                    # Default
                    encoding = tiktoken.get_encoding("cl100k_base")
                
                # Calcular tokens del prompt (si está disponible)
                if hasattr(response, 'content'):
                    # Solo podemos calcular completion tokens
                    completion_text = response.content or ""
                    completion_tokens = len(encoding.encode(completion_text))
                    total_tokens = completion_tokens
                    # Prompt tokens no se pueden calcular sin el prompt original
                    prompt_tokens = 0
                    
            except ImportError:
                logger.warning(
                    "[TOKEN_TRACKER] tiktoken no disponible, no se pueden calcular tokens"
                )
            except Exception as e:
                logger.warning(
                    f"[TOKEN_TRACKER] Error calculando tokens con tiktoken: {e}"
                )
        
        return prompt_tokens, completion_tokens, total_tokens
    
    async def ainvoke(
        self,
        input: List[BaseMessage] | str,
        config: Optional[Any] = None,
        **kwargs: Any
    ) -> Any:
        """
        Invoca el LLM de forma asíncrona y registra tokens.
        
        Args:
            input: Mensajes o texto de entrada
            config: Configuración opcional
            **kwargs: Argumentos adicionales
        
        Returns:
            Respuesta del LLM
        """
        # Invocar LLM base
        response = await self.llm.ainvoke(input, config=config, **kwargs)
        
        # Extraer tokens
        prompt_tokens, completion_tokens, total_tokens = self._extract_token_usage(response)
        
        # Registrar en tracker
        if total_tokens > 0:
            token_tracker.record_inference(
                node_name=self.node_name,
                inference_type=self.inference_type,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                metadata={
                    "provider": self.provider,
                    "model": self.model,
                    "method": "ainvoke"
                }
            )
        else:
            logger.debug(
                f"[TOKEN_TRACKER] No se pudieron extraer tokens de {self.node_name}"
            )
        
        return response
    
    def invoke(
        self,
        input: List[BaseMessage] | str,
        config: Optional[Any] = None,
        **kwargs: Any
    ) -> Any:
        """
        Invoca el LLM de forma síncrona y registra tokens.
        
        Args:
            input: Mensajes o texto de entrada
            config: Configuración opcional
            **kwargs: Argumentos adicionales
        
        Returns:
            Respuesta del LLM
        """
        # Invocar LLM base
        response = self.llm.invoke(input, config=config, **kwargs)
        
        # Extraer tokens
        prompt_tokens, completion_tokens, total_tokens = self._extract_token_usage(response)
        
        # Registrar en tracker
        if total_tokens > 0:
            token_tracker.record_inference(
                node_name=self.node_name,
                inference_type=self.inference_type,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                metadata={
                    "provider": self.provider,
                    "model": self.model,
                    "method": "invoke"
                }
            )
        else:
            logger.debug(
                f"[TOKEN_TRACKER] No se pudieron extraer tokens de {self.node_name}"
            )
        
        return response
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any
    ) -> Any:
        """
        Método interno de generación (delegado al LLM base).
        """
        return self.llm._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
    
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any
    ) -> Any:
        """
        Método interno de generación asíncrona (delegado al LLM base).
        """
        return await self.llm._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)
    
    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """Parámetros identificadores (delegado al LLM base)."""
        return self.llm._identifying_params
