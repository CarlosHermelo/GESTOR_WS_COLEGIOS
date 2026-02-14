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
    
    # Limitador de casos
    limit = None
    compact_mode = False
    
    # Parse args manual
    args = sys.argv[1:]
    for arg in args:
        if arg == "--resume":
            compact_mode = True
        elif arg.isdigit():
            limit = int(arg)
            
    if compact_mode:
        # Silenciar logs para que no ensucien el resumen
        import logging
        loggers_to_silence = [
            "app", 
            "langchain",
            "langgraph",
            "google",
            "httpx",
            "openai"
        ]
        for name in loggers_to_silence:
            logging.getLogger(name).setLevel(logging.ERROR)
        # Root logger also to ERROR
        logging.getLogger().setLevel(logging.ERROR)
            
    if limit:
        print(f"⚠️ Limitando ejecución a los primeros {limit} casos.")
        test_cases = test_cases[:limit]

    # Ejecutar pruebas
    resultados = []
    
    print("\n" + "=" * 80)
    print(f"🚀 INICIANDO EJECUCIÓN {'(MODO RESUMIDO)' if compact_mode else '(MODO VERBORRÁGICO)'}")
    print("=" * 80)
    
    for i, test in enumerate(test_cases, 1):
        # Determinar teléfono para este test
        phone = test.get("celular", default_phone)
        
        if not compact_mode:
            print(f"\n{'─' * 70}")
            print(f"📌 TEST {i}/{len(test_cases)}: {test['categoria']}")
            print(f"{'─' * 70}")
            print(f"📱 PHONE: {phone}")
            print(f"📥 INPUT: {test['mensaje']}")
            print(f"🎯 ESPERADO: {test['esperado']}")
            print("─" * 40)
        
        start_time = datetime.now()
        try:
            # Usar procesar (que ahora devuelve el estado completo si modificamos el agente, 
            # pero el agente devuelve string. Necesitamos acceder al estado interno o instrumentar el return.
            # ESTRATEGIA: El AgenteAutonomo oculta el estado. 
            # Vamos a modificar AgenteAutonomo para exponer el estado O 
            # usar una función interna de test que use el CodePlanner directamente.)
            
            # Para testear métricas internas, lo mejor es usar el code_planner directamente aquí.
            from app.agents.code_planner import get_code_planner_agent, create_empty_code_planner_state
            
            planner_agent = get_code_planner_agent()
            
            # Cargar contexto mock
            user_context = {"phone": phone, "responsable_id": "mock", "alumnos": []} 
            
            # Estado inicial
            state = create_empty_code_planner_state(
                phone_number=phone,
                mensaje=test["mensaje"],
                user_context=user_context
            )
            
            # Ejecutar grafo
            graph = planner_agent.get_graph()
            final_state = await graph.ainvoke(state)
            
            respuesta = final_state.get("final_response", "Sin respuesta")
            metrics = final_state.get("metrics", {})
            
            total_duration = (datetime.now() - start_time).total_seconds()
            
            if not compact_mode:
                print(f"📤 OUTPUT:")
                print(f"   {respuesta.replace(chr(10), chr(10) + '   ')}")
            else:
                # MODO RESUMIDO
                msg_preview = (test["mensaje"][:47] + "...") if len(test["mensaje"]) > 50 else test["mensaje"]
                print(f"\nPregunta {i}: \"{msg_preview}\"")
                
                # Mapa de nodos a nombres amigables
                node_map = {
                    "planner": "Planner",
                    "executor": "Executor", 
                    "reflector": "Reflector",
                    "responder": "Responder"
                }
                
                # Orden de visualización
                order = ["planner", "executor", "reflector", "responder"]
                
                for node_key in order:
                    if node_key in metrics:
                        m = metrics[node_key]
                        lat = m.get("latency", 0)
                        tok = m.get("tokens", 0)
                        
                        icon = "🐢" if lat > 5 else "⚡"
                        label_desc = "LLM" if tok > 0 or node_key != "executor" else "Code"
                        desc = f"{label_desc}: {int(tok)} tokens" if tok > 0 else f"{label_desc} Exec"
                        
                        print(f"[{node_map.get(node_key, node_key).ljust(10)}] {desc.ljust(20)} | {icon} {lat:.2f}s latencia")

                print(f"{'Total:'.ljust(33)} | ⏱️  {total_duration:.2f}s total")

            resultados.append({
                "test": test["categoria"],
                "exito": True,
                "respuesta": respuesta
            })
            
        except Exception as e:
            import traceback
            if not compact_mode:
                print(f"❌ ERROR: {e}")
                traceback.print_exc()
            else:
                print(f"\nPregunta {i}: ❌ ERROR - {e}")
                
            resultados.append({
                "test": test["categoria"],
                "exito": False,
                "error": str(e)
            })
    
    # Resumen Final
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
