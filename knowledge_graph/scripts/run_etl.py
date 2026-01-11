#!/usr/bin/env python3
"""
Script para ejecutar ETL manualmente.
"""
import asyncio
import argparse
import logging
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.neo4j_client import get_neo4j_client
from app.etl.sync_from_erp import ETLFromERP
from app.etl.sync_from_gestor import ETLFromGestor
from app.etl.llm_enrichment import LLMEnrichment
from app.llm.factory import validate_llm_config
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_etl(
    sync_erp: bool = True,
    sync_gestor: bool = True,
    enrich_llm: bool = True
):
    """Ejecuta el proceso ETL."""
    
    print("=" * 60)
    print("ETL - KNOWLEDGE GRAPH")
    print("=" * 60)
    print(f"Neo4j: {settings.NEO4J_URI}")
    print(f"ERP Mock: {settings.MOCK_ERP_URL}")
    print(f"LLM: {settings.LLM_PROVIDER}/{settings.LLM_MODEL}")
    print()
    print(f"Sincronizar ERP: {'Sí' if sync_erp else 'No'}")
    print(f"Sincronizar Gestor: {'Sí' if sync_gestor else 'No'}")
    print(f"Enriquecer con LLM: {'Sí' if enrich_llm else 'No'}")
    print()
    
    results = {
        "erp": {},
        "gestor": {},
        "llm": {}
    }
    
    try:
        # Validar LLM si se va a usar
        if enrich_llm:
            print("🤖 Validando configuración LLM...")
            validate_llm_config()
            print()
        
        # Obtener cliente Neo4j
        neo4j = await get_neo4j_client()
        
        # 1. Sincronizar desde ERP
        if sync_erp:
            print("=" * 40)
            print("FASE 1: SINCRONIZACIÓN DESDE ERP")
            print("=" * 40)
            etl_erp = ETLFromERP(neo4j)
            results["erp"] = await etl_erp.sync_all()
            print()
        
        # 2. Sincronizar desde Gestor WS
        if sync_gestor:
            print("=" * 40)
            print("FASE 2: SINCRONIZACIÓN DESDE GESTOR WS")
            print("=" * 40)
            etl_gestor = ETLFromGestor(neo4j)
            results["gestor"] = await etl_gestor.sync_all()
            print()
        
        # 3. Enriquecer con LLM
        if enrich_llm:
            print("=" * 40)
            print("FASE 3: ENRIQUECIMIENTO CON LLM")
            print("=" * 40)
            enrichment = LLMEnrichment(neo4j)
            results["llm"] = await enrichment.enrich_all()
            print()
        
        # Resumen
        print("=" * 60)
        print("RESUMEN ETL")
        print("=" * 60)
        
        if sync_erp:
            print(f"ERP:")
            for k, v in results["erp"].items():
                print(f"   {k}: {v}")
        
        if sync_gestor:
            print(f"Gestor WS:")
            for k, v in results["gestor"].items():
                print(f"   {k}: {v}")
        
        if enrich_llm:
            print(f"LLM Enrichment:")
            for k, v in results["llm"].items():
                print(f"   {k}: {v}")
        
        print()
        print("=" * 60)
        print("✅ ETL COMPLETADO")
        print("=" * 60)
        
        return results
        
    except Exception as e:
        print(f"❌ Error en ETL: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(description="Ejecutar ETL del Knowledge Graph")
    parser.add_argument(
        "--no-erp",
        action="store_true",
        help="No sincronizar desde ERP"
    )
    parser.add_argument(
        "--no-gestor",
        action="store_true",
        help="No sincronizar desde Gestor WS"
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="No enriquecer con LLM"
    )
    parser.add_argument(
        "--only-erp",
        action="store_true",
        help="Solo sincronizar ERP"
    )
    parser.add_argument(
        "--only-llm",
        action="store_true",
        help="Solo enriquecer con LLM"
    )
    
    args = parser.parse_args()
    
    sync_erp = not args.no_erp
    sync_gestor = not args.no_gestor
    enrich_llm = not args.no_llm
    
    if args.only_erp:
        sync_erp = True
        sync_gestor = False
        enrich_llm = False
    
    if args.only_llm:
        sync_erp = False
        sync_gestor = False
        enrich_llm = True
    
    asyncio.run(run_etl(
        sync_erp=sync_erp,
        sync_gestor=sync_gestor,
        enrich_llm=enrich_llm
    ))


if __name__ == "__main__":
    main()

