"""
Interface base para proveedores LLM.
"""
from abc import ABC, abstractmethod
from typing import Any


class LLMInterface(ABC):
    """Interface común para todos los proveedores LLM."""
    
    @abstractmethod
    def get_llm(self) -> Any:
        """Retorna instancia del LLM configurado."""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Valida que las credenciales estén configuradas."""
        pass

