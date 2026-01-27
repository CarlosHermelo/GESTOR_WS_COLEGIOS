"""
Script para consultar logs de token usage.
Muestra los logs de consumo de tokens de forma legible.
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


def parse_token_log_line(line: str) -> Optional[dict]:
    """
    Parsea una línea de log que contiene token usage.
    
    Args:
        line: Línea del log
    
    Returns:
        dict con datos parseados o None si no es un log de tokens
    """
    if "TOKEN_USAGE" not in line:
        return None
    
    # Buscar el JSON en la línea
    try:
        # El formato es: [timestamp] - module - INFO - [TOKEN_USAGE] {json}
        json_start = line.find("{")
        if json_start == -1:
            return None
        
        json_str = line[json_start:]
        data = json.loads(json_str)
        return data
    except (json.JSONDecodeError, ValueError):
        return None


def consultar_logs(
    log_file: Optional[Path] = None,
    whatsapp: Optional[str] = None,
    query_id: Optional[str] = None,
    limit: int = 10
):
    """
    Consulta logs de token usage.
    
    Args:
        log_file: Archivo de log (default: logs/token_usage.log)
        whatsapp: Filtrar por WhatsApp
        query_id: Filtrar por query_id
        limit: Límite de resultados
    """
    if log_file is None:
        log_file = Path("logs") / "token_usage.log"
    
    if not log_file.exists():
        print(f"❌ No se encontró el archivo de log: {log_file}")
        print(f"   Los logs se generan cuando ejecutás el agente.")
        return
    
    print(f"📊 Consultando logs de tokens desde: {log_file}")
    print("=" * 80)
    
    logs_encontrados = []
    
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            data = parse_token_log_line(line)
            if not data:
                continue
            
            # Aplicar filtros
            if whatsapp and data.get("whatsapp") != whatsapp:
                continue
            if query_id and data.get("query_id") != query_id:
                continue
            
            logs_encontrados.append(data)
    
    # Ordenar por timestamp (más recientes primero)
    logs_encontrados.sort(
        key=lambda x: x.get("start_time", ""),
        reverse=True
    )
    
    # Limitar resultados
    logs_encontrados = logs_encontrados[:limit]
    
    if not logs_encontrados:
        print("No se encontraron logs de tokens con los filtros especificados.")
        return
    
    print(f"\n📋 Encontrados {len(logs_encontrados)} registros:\n")
    
    for i, log_data in enumerate(logs_encontrados, 1):
        print(f"\n{'='*80}")
        print(f"REGISTRO #{i}")
        print(f"{'='*80}")
        print(f"Query ID: {log_data.get('query_id', 'N/A')}")
        print(f"WhatsApp: {log_data.get('whatsapp', 'N/A')}")
        print(f"Mensaje: {log_data.get('mensaje', 'N/A')[:100]}...")
        print(f"Provider: {log_data.get('provider', 'N/A')}")
        print(f"Model: {log_data.get('model', 'N/A')}")
        print(f"Start Time: {log_data.get('start_time', 'N/A')}")
        print(f"End Time: {log_data.get('end_time', 'N/A')}")
        
        if log_data.get("duration_seconds"):
            print(f"Duración: {log_data['duration_seconds']:.2f} segundos")
        
        print(f"\nInferencias: {log_data.get('inference_count', 0)}")
        
        # Detalle por inferencia
        inferences = log_data.get("inferences", [])
        if inferences:
            print("\nDetalle por inferencia:")
            for j, inf in enumerate(inferences, 1):
                print(
                    f"  [{j}] {inf.get('node_name', 'N/A')} "
                    f"({inf.get('inference_type', 'N/A')}): "
                    f"{inf.get('total_tokens', 0):,} tokens "
                    f"(prompt: {inf.get('prompt_tokens', 0):,}, "
                    f"completion: {inf.get('completion_tokens', 0):,})"
                )
        
        # Totales
        totals = log_data.get("totals", {})
        print(f"\nTOTALES:")
        print(f"  Prompt tokens: {totals.get('prompt_tokens', 0):,}")
        print(f"  Completion tokens: {totals.get('completion_tokens', 0):,}")
        print(f"  Total tokens: {totals.get('total_tokens', 0):,}")


def main():
    """Función principal."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Consulta logs de consumo de tokens"
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Archivo de log (default: logs/token_usage.log)"
    )
    parser.add_argument(
        "--whatsapp",
        type=str,
        help="Filtrar por número de WhatsApp"
    )
    parser.add_argument(
        "--query-id",
        type=str,
        help="Filtrar por query_id"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Límite de resultados (default: 10)"
    )
    
    args = parser.parse_args()
    
    log_file = Path(args.file) if args.file else None
    
    consultar_logs(
        log_file=log_file,
        whatsapp=args.whatsapp,
        query_id=args.query_id,
        limit=args.limit
    )


if __name__ == "__main__":
    main()
