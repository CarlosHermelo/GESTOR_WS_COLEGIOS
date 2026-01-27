"""
Endpoints de la API.
"""
from app.api.webhooks_erp import router as webhooks_erp_router
from app.api.webhooks_whatsapp import router as webhooks_whatsapp_router
from app.api.admin import router as admin_router

__all__ = [
    "webhooks_erp_router",
    "webhooks_whatsapp_router",
    "admin_router"
]



