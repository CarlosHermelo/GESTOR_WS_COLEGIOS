"""
Modelos SQLAlchemy para el ERP Mock.
Define la estructura de las tablas de la base de datos.
"""
from sqlalchemy import (
    Column, String, Boolean, Date, Integer, 
    Numeric, Text, ForeignKey, TIMESTAMP, Table
)
from sqlalchemy.orm import relationship, DeclarativeBase
from datetime import datetime


class Base(DeclarativeBase):
    """Clase base para todos los modelos."""
    pass


class Responsable(Base):
    """
    Modelo para responsables (padres, madres, tutores).
    Cada responsable puede tener múltiples alumnos a cargo.
    """
    __tablename__ = "erp_responsables"
    
    id = Column(String(50), primary_key=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    whatsapp = Column(String(20), unique=True, nullable=False)
    email = Column(String(200), nullable=True)
    tipo = Column(String(20), nullable=True)  # padre, madre, tutor
    
    # Relación muchos a muchos con alumnos
    alumnos = relationship(
        "Alumno",
        secondary="erp_responsabilidad",
        back_populates="responsables"
    )


class Alumno(Base):
    """
    Modelo para alumnos del colegio.
    Cada alumno puede tener múltiples responsables y cuotas.
    """
    __tablename__ = "erp_alumnos"
    
    id = Column(String(50), primary_key=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    fecha_nacimiento = Column(Date, nullable=True)
    grado = Column(String(50), nullable=True)
    activo = Column(Boolean, default=True)
    
    # Relación muchos a muchos con responsables
    responsables = relationship(
        "Responsable",
        secondary="erp_responsabilidad",
        back_populates="alumnos"
    )
    
    # Relación uno a muchos con cuotas
    cuotas = relationship("Cuota", back_populates="alumno")


class Responsabilidad(Base):
    """
    Tabla intermedia para la relación muchos a muchos
    entre responsables y alumnos.
    """
    __tablename__ = "erp_responsabilidad"
    
    responsable_id = Column(
        String(50), 
        ForeignKey("erp_responsables.id"), 
        primary_key=True
    )
    alumno_id = Column(
        String(50), 
        ForeignKey("erp_alumnos.id"), 
        primary_key=True
    )


class PlanPago(Base):
    """
    Modelo para planes de pago.
    Define la estructura de cuotas para un período.
    """
    __tablename__ = "erp_planes_pago"
    
    id = Column(String(50), primary_key=True)
    nombre = Column(String(100), nullable=True)
    cantidad_cuotas = Column(Integer, nullable=True)
    monto_cuota = Column(Numeric(10, 2), nullable=True)
    anio = Column(Integer, nullable=True)
    
    # Relación uno a muchos con cuotas
    cuotas = relationship("Cuota", back_populates="plan_pago")


class Cuota(Base):
    """
    Modelo para cuotas individuales.
    Representa un pago pendiente o realizado de un alumno.
    """
    __tablename__ = "erp_cuotas"
    
    id = Column(String(50), primary_key=True)
    alumno_id = Column(String(50), ForeignKey("erp_alumnos.id"), nullable=False)
    plan_pago_id = Column(String(50), ForeignKey("erp_planes_pago.id"), nullable=True)
    numero_cuota = Column(Integer, nullable=True)
    monto = Column(Numeric(10, 2), nullable=False)
    fecha_vencimiento = Column(Date, nullable=False)
    estado = Column(String(20), nullable=True)  # pendiente, pagada, vencida
    link_pago = Column(Text, nullable=True)
    fecha_pago = Column(TIMESTAMP, nullable=True)
    
    # Relaciones
    alumno = relationship("Alumno", back_populates="cuotas")
    plan_pago = relationship("PlanPago", back_populates="cuotas")
    pagos = relationship("Pago", back_populates="cuota")


class Pago(Base):
    """
    Modelo para registrar pagos realizados.
    Cada pago corresponde a una cuota específica.
    """
    __tablename__ = "erp_pagos"
    
    id = Column(String(50), primary_key=True)
    cuota_id = Column(String(50), ForeignKey("erp_cuotas.id"), nullable=False)
    monto = Column(Numeric(10, 2), nullable=False)
    fecha_pago = Column(TIMESTAMP, nullable=False)
    metodo_pago = Column(String(50), nullable=True)
    referencia = Column(String(100), nullable=True)
    
    # Relación con cuota
    cuota = relationship("Cuota", back_populates="pagos")

