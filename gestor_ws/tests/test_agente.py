"""
Script de prueba para el Agente Autónomo (Code Planner).

Ejecutar desde gestor_ws:
    python -m tests.test_agente

O modo interactivo:
    python -m tests.test_agente --interactivo
"""
import asyncio
import logging
from datetime import datetime

# Configurar logging ANTES de importar el resto
from app.logging_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)


import os
import json

async def test_agente():
    """Ejecuta pruebas del agente autónomo."""
    from app.agents.agente_autonomo import get_agente_autonomo
    
    print("\n" + "=" * 70)
    print("🤖 AGENTE AUTÓNOMO JERÁRQUICO - Suite de Pruebas")
    print("=" * 70)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    agente = get_agente_autonomo()
    
    # Cargar casos de prueba desde archivo externo
    base_path = os.path.dirname(__file__)
    data_path = os.path.join(base_path, "test_agente", "test_data_larga.txt")
    
    try:
        if os.path.exists(data_path):
            with open(data_path, "r", encoding="utf-8") as f:
                test_cases = json.load(f)
            print(f"📂 Casos de prueba cargados REALMENTE desde: {data_path}")
        else:
            print(f"⚠️ No se encontró el archivo de datos en {data_path}, usando fallback.")
            test_cases = [
                {
                    "categoria": "Fallback - Estado de cuenta",
                    "mensaje": "Hola, tengo deuda?",
                    "celular": "+5491112345001",
                    "esperado": "Estado de cuenta"
                }
            ]
    except Exception as e:
        print(f"❌ Error cargando {data_path}: {e}")
        return False
    
    # Número de WhatsApp por defecto (si no viene en el test case)
    default_phone = "+5491112345001"
    
    # Limitar casos de prueba si se pasa argumento
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
            print(f"⚠️ Limitando ejecución a los primeros {limit} casos.")
            test_cases = test_cases[:limit]
        except ValueError:
            pass

    # Ejecutar pruebas
    resultados = []
    
    for i, test in enumerate(test_cases, 1):
        # Determinar teléfono para este test
        phone = test.get("celular", default_phone)
        
        print(f"\n{'─' * 70}")
        print(f"📌 TEST {i}/{len(test_cases)}: {test['categoria']}")
        print(f"{'─' * 70}")
        print(f"📱 PHONE: {phone}")
        print(f"📥 INPUT: {test['mensaje']}")
        print(f"🎯 ESPERADO: {test['esperado']}")
        print("─" * 40)
        
        try:
            # Usar procesar_sin_checkpoint para el Code Planner
            respuesta = await agente.procesar_sin_checkpoint(phone, test["mensaje"])
            
            print(f"📤 OUTPUT:")
            print(f"   {respuesta.replace(chr(10), chr(10) + '   ')}")
            
            resultados.append({
                "test": test["categoria"],
                "exito": True,
                "respuesta": respuesta
            })
            
        except Exception as e:
            import traceback
            print(f"❌ ERROR: {e}")
            traceback.print_exc()
            resultados.append({
                "test": test["categoria"],
                "exito": False,
                "error": str(e)
            })
    
    # Resumen
    print("\n" + "=" * 70)
    print("📊 RESUMEN DE PRUEBAS")
    print("=" * 70)
    exitosos = sum(1 for r in resultados if r["exito"])
    print(f"✅ Exitosos: {exitosos}/{len(resultados)}")
    print(f"❌ Fallidos: {len(resultados) - exitosos}/{len(resultados)}")
    
    return exitosos == len(resultados)


async def test_interactivo():
    """Modo interactivo para probar consultas manualmente."""
    from app.agents.agente_autonomo import get_agente_autonomo
    
    print("\n" + "=" * 70)
    print("🤖 MODO INTERACTIVO - Agente Autónomo")
    print("=" * 70)
    print("Escribe tu consulta y presiona Enter.")
    print("Escribe 'salir' para terminar.\n")
    
    agente = get_agente_autonomo()
    phone = "+5491199999999"  # Número de prueba
    
    while True:
        try:
            consulta = input("📝 Tu consulta: ").strip()
            
            if consulta.lower() in ["salir", "exit", "q"]:
                print("\n👋 ¡Hasta luego!")
                break
            
            if not consulta:
                continue
            
            print("\n⏳ Procesando...")
            respuesta = await agente.procesar_sin_checkpoint(phone, consulta)
            
            print(f"\n🤖 Respuesta:")
            print(f"   {respuesta.replace(chr(10), chr(10) + '   ')}")
            print()
            
        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


import sys

if __name__ == "__main__":
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactivo":
        asyncio.run(test_interactivo())
    else:
        asyncio.run(test_agente())
