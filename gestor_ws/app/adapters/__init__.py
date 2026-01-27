"""
Adaptadores para integración con sistemas externos (ERP).
"""
from app.adapters.erp_interface import ERPClientInterface
from app.adapters.mock_erp_adapter import MockERPAdapter, get_erp_client

__all__ = ["ERPClientInterface", "MockERPAdapter", "get_erp_client"]



