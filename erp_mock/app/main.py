"""
API REST del ERP Mock.
Simula un sistema de gestión escolar con endpoints para
consultar alumnos, responsables, cuotas y confirmar pagos.
"""
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, date
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import init_db, close_db, get_db
from app.schemas import (
    AlumnoResponse, AlumnoDetalleResponse,
    ResponsableConAlumnosResponse,
    CuotaResponse, CuotaDetalleResponse,
    ConfirmarPagoRequest, ConfirmarPagoResponse,
    HealthResponse, ErrorResponse
)
from app import crud
from app.webhooks import notify_pago_confirmado

# ============== LOGGING ==============

def setup_logging():
    """Configura logging estructurado (JSON)."""
    log_format = (
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
        '"module": "%(module)s", "message": "%(message)s"}'
    )
    
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)]
    )


setup_logging()
logger = logging.getLogger(__name__)


# ============== LIFESPAN ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Maneja el ciclo de vida de la aplicación.
    Inicializa BD al arrancar, cierra conexiones al parar.
    """
    logger.info("Iniciando ERP Mock API...")
    await init_db()
    logger.info("ERP Mock API iniciada correctamente")
    
    yield
    
    logger.info("Deteniendo ERP Mock API...")
    await close_db()
    logger.info("ERP Mock API detenida")


# ============== APP ==============

app = FastAPI(
    title="ERP Mock API",
    description="API REST que simula un sistema de gestión escolar",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configurar CORS para desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== EXCEPTION HANDLERS ==============

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Maneja excepciones HTTP de forma estructurada."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": f"ERR_{exc.status_code}"}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Maneja excepciones no controladas."""
    logger.error(f"Error no controlado: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor", "error_code": "ERR_500"}
    )


# ============== HEALTH ==============

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health Check"
)
async def health_check():
    """
    Verifica el estado del servicio.
    Retorna información básica de salud.
    """
    return HealthResponse(
        status="healthy",
        service="erp_mock",
        timestamp=datetime.utcnow(),
        database="connected"
    )


# ============== ALUMNOS ==============

@app.get(
    "/api/v1/alumnos/{alumno_id}",
    response_model=AlumnoDetalleResponse,
    tags=["Alumnos"],
    summary="Obtener datos de un alumno",
    responses={404: {"model": ErrorResponse}}
)
async def get_alumno(
    alumno_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene los datos de un alumno específico por su ID.
    Incluye información de los responsables a cargo.
    """
    alumno = await crud.get_alumno_by_id(db, alumno_id, include_responsables=True)
    
    if not alumno:
        raise HTTPException(
            status_code=404,
            detail=f"Alumno con ID {alumno_id} no encontrado"
        )
    
    return alumno


@app.get(
    "/api/v1/alumnos/{alumno_id}/cuotas",
    response_model=List[CuotaResponse],
    tags=["Alumnos"],
    summary="Obtener cuotas de un alumno",
    responses={404: {"model": ErrorResponse}}
)
async def get_alumno_cuotas(
    alumno_id: str,
    estado: Optional[str] = Query(
        None,
        description="Filtrar por estado: pendiente, pagada, vencida"
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene las cuotas de un alumno específico.
    Opcionalmente filtra por estado de la cuota.
    """
    # Verificar que el alumno existe
    alumno = await crud.get_alumno_by_id(db, alumno_id)
    if not alumno:
        raise HTTPException(
            status_code=404,
            detail=f"Alumno con ID {alumno_id} no encontrado"
        )
    
    cuotas = await crud.get_cuotas_alumno(db, alumno_id, estado)
    return cuotas


# ============== RESPONSABLES ==============

@app.get(
    "/api/v1/responsables/by-whatsapp/{whatsapp}",
    response_model=ResponsableConAlumnosResponse,
    tags=["Responsables"],
    summary="Buscar responsable por WhatsApp",
    responses={404: {"model": ErrorResponse}}
)
async def get_responsable_by_whatsapp(
    whatsapp: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Busca un responsable (padre/madre/tutor) por su número de WhatsApp.
    Retorna los datos del responsable y los alumnos a su cargo.
    
    El número debe incluir código de país (ej: +5491112345001).
    """
    responsable = await crud.get_responsable_by_whatsapp(db, whatsapp)
    
    if not responsable:
        raise HTTPException(
            status_code=404,
            detail=f"Responsable con WhatsApp {whatsapp} no encontrado"
        )
    
    return responsable


# ============== CUOTAS ==============

@app.get(
    "/api/v1/cuotas/{cuota_id}",
    response_model=CuotaDetalleResponse,
    tags=["Cuotas"],
    summary="Obtener detalle de una cuota",
    responses={404: {"model": ErrorResponse}}
)
async def get_cuota(
    cuota_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene el detalle completo de una cuota específica.
    Incluye información del alumno y plan de pago asociado.
    """
    cuota = await crud.get_cuota_by_id(
        db, cuota_id, 
        include_alumno=True, 
        include_plan=True
    )
    
    if not cuota:
        raise HTTPException(
            status_code=404,
            detail=f"Cuota con ID {cuota_id} no encontrada"
        )
    
    return cuota


@app.get(
    "/api/v1/cuotas",
    response_model=List[CuotaResponse],
    tags=["Cuotas"],
    summary="Listar cuotas con filtros"
)
async def list_cuotas(
    estado: Optional[str] = Query(
        None,
        description="Filtrar por estado: pendiente, pagada, vencida"
    ),
    vencimiento_desde: Optional[date] = Query(
        None,
        description="Filtrar cuotas con vencimiento desde esta fecha (YYYY-MM-DD)"
    ),
    vencimiento_hasta: Optional[date] = Query(
        None,
        description="Filtrar cuotas con vencimiento hasta esta fecha (YYYY-MM-DD)"
    ),
    limit: int = Query(100, ge=1, le=500, description="Máximo de resultados"),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista cuotas con filtros opcionales.
    Permite filtrar por estado y rango de fechas de vencimiento.
    """
    cuotas = await crud.get_cuotas_filtradas(
        db,
        estado=estado,
        vencimiento_desde=vencimiento_desde,
        vencimiento_hasta=vencimiento_hasta,
        limit=limit
    )
    
    return cuotas


# ============== PAGOS ==============

@app.post(
    "/api/v1/pagos/confirmar",
    response_model=ConfirmarPagoResponse,
    tags=["Pagos"],
    summary="Confirmar un pago",
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse}
    }
)
async def confirmar_pago(
    pago_data: ConfirmarPagoRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Confirma el pago de una cuota.
    
    Esta operación:
    1. Registra el pago en la base de datos
    2. Actualiza el estado de la cuota a "pagada"
    3. Envía un webhook al servicio Gestor WS (en background)
    
    El webhook se envía de forma asíncrona para no bloquear la respuesta.
    """
    # Crear pago y actualizar cuota
    pago, cuota = await crud.crear_pago(db, pago_data)
    
    if not cuota:
        raise HTTPException(
            status_code=404,
            detail=f"Cuota con ID {pago_data.cuota_id} no encontrada"
        )
    
    if not pago:
        raise HTTPException(
            status_code=400,
            detail=f"La cuota {pago_data.cuota_id} ya está pagada"
        )
    
    # Enviar webhook en background
    background_tasks.add_task(
        notify_pago_confirmado,
        cuota_id=cuota.id,
        alumno_id=cuota.alumno_id,
        monto=pago.monto,
        fecha_pago=pago.fecha_pago
    )
    
    logger.info(
        f"Pago confirmado exitosamente",
        extra={
            "pago_id": pago.id,
            "cuota_id": cuota.id,
            "monto": float(pago.monto)
        }
    )
    
    return ConfirmarPagoResponse(
        success=True,
        message="Pago confirmado exitosamente",
        pago=pago,
        cuota=cuota
    )


# ============== ROOT ==============

@app.get("/", include_in_schema=False)
async def root():
    """Redirecciona a la documentación."""
    return {
        "service": "ERP Mock API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

