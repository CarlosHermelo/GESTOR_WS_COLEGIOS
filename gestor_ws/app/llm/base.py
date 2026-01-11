"""
Interface base para proveedores LLM.
Define el contrato que deben cumplir todos los providers.
"""
from abc import ABC, abstractmethod
from langchain_core.language_models import BaseChatModel


class LLMInterface(ABC):
    """Interface común para todos los proveedores LLM."""
    
    @abstractmethod
    def get_llm(self) -> BaseChatModel:
        """
        Retorna instancia del LLM configurado.
        
        Returns:
            BaseChatModel: Instancia del modelo de lenguaje
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """
        Valida que las credenciales estén configuradas.
        
        Returns:
            bool: True si la configuración es válida
            
        Raises:
            ValueError: Si falta alguna configuración requerida
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nombre del proveedor para logging."""
        pass

