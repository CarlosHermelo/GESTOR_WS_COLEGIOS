"""
Interface abstracta para clientes ERP.
Define el contrato que deben cumplir todos los adaptadores ERP.
"""
from abc import ABC, abstractmethod
from typing import Optional


class ERPClientInterface(ABC):
    """
    Interface para comunicación con el ERP.
    Todos los adaptadores ERP deben implementar estos métodos.
    """
    
    @abstractmethod
    async def get_alumno(self, alumno_id: str) -> dict:
        """
        Obtiene datos de un alumno por su ID.
        
        Args:
            alumno_id: ID del alumno en el ERP
            
        Returns:
            dict: Datos del alumno incluyendo responsables
        """
        pass
    
    @abstractmethod
    async def get_alumno_cuotas(
        self, 
        alumno_id: str, 
        estado: Optional[str] = None
    ) -> list[dict]:
        """
        Obtiene cuotas de un alumno.
        
        Args:
            alumno_id: ID del alumno
            estado: Filtro opcional (pendiente, pagada, vencida)
            
        Returns:
            list[dict]: Lista de cuotas
        """
        pass
    
    @abstractmethod
    async def get_responsable_by_whatsapp(self, whatsapp: str) -> dict:
        """
        Busca responsable por número de WhatsApp.
        
        Args:
            whatsapp: Número de WhatsApp con código de país
            
        Returns:
            dict: Datos del responsable con sus alumnos
        """
        pass
    
    @abstractmethod
    async def get_cuota(self, cuota_id: str) -> dict:
        """
        Obtiene detalle de una cuota específica.
        
        Args:
            cuota_id: ID de la cuota
            
        Returns:
            dict: Datos de la cuota
        """
        pass
    
    @abstractmethod
    async def confirmar_pago(
        self,
        cuota_id: str,
        monto: float,
        metodo: str,
        referencia: str
    ) -> dict:
        """
        Confirma un pago en el ERP.
        
        Args:
            cuota_id: ID de la cuota a pagar
            monto: Monto pagado
            metodo: Método de pago (transferencia, efectivo, etc.)
            referencia: Referencia del pago
            
        Returns:
            dict: Respuesta del ERP con confirmación
        """
        pass
    
    @abstractmethod
    async def get_cuotas_por_vencer(self, dias: int = 7) -> list[dict]:
        """
        Obtiene cuotas que vencen en los próximos N días.
        
        Args:
            dias: Cantidad de días a futuro
            
        Returns:
            list[dict]: Lista de cuotas próximas a vencer
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Verifica conectividad con el ERP.
        
        Returns:
            bool: True si el ERP responde correctamente
        """
        pass



