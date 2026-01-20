"""
Script de prueba para el Agente Autónomo Jerárquico.

Ejecutar desde la raíz del proyecto:
    python -m app.agents.test_agente

O directamente:
    cd gestor_ws && python -m app.agents.test_agente
"""
import asyncio
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_agente():
    """Ejecuta pruebas del agente autónomo."""
    from app.agents.agente_autonomo import get_agente_autonomo
    
    print("\n" + "=" * 70)
    print("🤖 AGENTE AUTÓNOMO JERÁRQUICO - Suite de Pruebas")
    print("=" * 70)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    agente = get_agente_autonomo()
    
    
    
    # Casos de prueba
    test_cases = [
        {
            "categoria": "TRIPLE - Financiero + Institucional ",
            "mensaje": "Fui al colegio a las 6 de la mañana y no habia nadie en el colegio para que me atiendan Quiero tener un estrevista con el director Hermelo ",
            "esperado": "Estado de cuenta + horario de administración"
        },
    ]
    
    
    """
    # Casos de prueba
    test_cases = [
        {
            "categoria": "SALUDO",
            "mensaje": "Hola!",
            "esperado": "Respuesta de bienvenida"
        },
        {
            "categoria": "FINANCIERO - Estado de cuenta",
            "mensaje": "Cuánto debo?",
            "esperado": "Estado de cuenta con cuotas pendientes"
        },
        {
            "categoria": "FINANCIERO - Link de pago",
            "mensaje": "Necesito el link para pagar la cuota de marzo",
            "esperado": "Link de pago o instrucciones"
        },
        {
            "categoria": "ADMINISTRATIVO - Plan de pagos",
            "mensaje": "Quiero solicitar un plan de pagos porque no puedo pagar todo junto",
            "esperado": "Creación de ticket de plan de pagos"
        },
        {
            "categoria": "ADMINISTRATIVO - Reclamo",
            "mensaje": "Tengo un reclamo, me cobraron de más en la cuota de febrero",
            "esperado": "Creación de ticket de reclamo"
        },
        {
            "categoria": "INSTITUCIONAL - Horarios",
            "mensaje": "¿A qué hora empiezan las clases de primaria?",
            "esperado": "Información de horarios"
        },
        {
            "categoria": "INSTITUCIONAL - Calendario",
            "mensaje": "¿Cuándo empiezan las clases este año?",
            "esperado": "Fecha de inicio de clases"
        },
        {
            "categoria": "INSTITUCIONAL - Autoridades",
            "mensaje": "¿Quién es el director del colegio?",
            "esperado": "Nombre del director"
        },
        {
            "categoria": "MIXTO - Financiero + Institucional",
            "mensaje": "Debo cuotas? Y de paso, qué horario tiene administración?",
            "esperado": "Estado de cuenta + horario de administración"
        },
        {
            "categoria": "TRIPLE - Financiero + Institucional ",
            "mensaje": "Debo cuotas? Y de paso, qué horario tiene administración? Y qué autoridades hay?",
            "esperado": "Estado de cuenta + horario de administración"
        },
    ]
    """
    # Número de WhatsApp de prueba
    phone = "+5491112345001"
    
    # Ejecutar pruebas
    resultados = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'─' * 70}")
        print(f"📌 TEST {i}/{len(test_cases)}: {test['categoria']}")
        print(f"{'─' * 70}")
        print(f"📥 INPUT: {test['mensaje']}")
        print(f"🎯 ESPERADO: {test['esperado']}")
        print("─" * 40)
        
        try:
            # Usar versión sin checkpoint para testing simple
            respuesta = await agente.procesar_sin_checkpoint(phone, test["mensaje"])
            
            print(f"📤 OUTPUT:")
            print(f"   {respuesta.replace(chr(10), chr(10) + '   ')}")
            
            resultados.append({
                "test": test["categoria"],
                "exito": True,
                "respuesta": respuesta[:100] + "..." if len(respuesta) > 100 else respuesta
            })
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
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
    fallidos = len(resultados) - exitosos
    
    print(f"✅ Exitosos: {exitosos}/{len(resultados)}")
    print(f"❌ Fallidos: {fallidos}/{len(resultados)}")
    
    if fallidos > 0:
        print("\n⚠️ Pruebas fallidas:")
        for r in resultados:
            if not r["exito"]:
                print(f"   • {r['test']}: {r.get('error', 'Error desconocido')}")
    
    print("\n" + "=" * 70)
    print("🏁 Pruebas completadas")
    print("=" * 70 + "\n")
    
    return exitosos == len(resultados)


async def test_interactivo():
    """Modo interactivo para probar el agente."""
    from app.agents.agente_autonomo import get_agente_autonomo
    
    print("\n" + "=" * 70)
    print("🤖 AGENTE AUTÓNOMO - Modo Interactivo")
    print("=" * 70)
    print("Escribe tu mensaje y presiona Enter.")
    print("Escribe 'salir' o 'exit' para terminar.")
    print("=" * 70 + "\n")
    
    agente = get_agente_autonomo()
    phone = "+5491112345001"
    
    while True:
        try:
            mensaje = input("👤 Tú: ").strip()
            
            if not mensaje:
                continue
            
            if mensaje.lower() in ["salir", "exit", "quit", "q"]:
                print("\n👋 ¡Hasta luego!")
                break
            
            print("⏳ Procesando...")
            respuesta = await agente.procesar_sin_checkpoint(phone, mensaje)
            
            print(f"\n🤖 Agente: {respuesta}\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactivo":
        asyncio.run(test_interactivo())
    else:
        asyncio.run(test_agente())
