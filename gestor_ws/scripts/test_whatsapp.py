#!/usr/bin/env python3
"""
Script para probar mensajes de WhatsApp simulados.

Uso:
    python scripts/test_whatsapp.py "+5491112345005" "Cuánto debo?"
    python scripts/test_whatsapp.py "+5491112345005" "Necesito un plan de pagos"
"""
import asyncio
import sys
import httpx
import json


API_URL = "http://localhost:8000"


async def send_test_message(phone: str, text: str) -> dict:
    """Envía un mensaje de prueba al webhook."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{API_URL}/webhook/whatsapp/test",
            json={
                "from_number": phone,
                "text": text
            }
        )
        return response.json()


async def send_real_message(phone: str, text: str) -> dict:
    """Envía un mensaje al webhook principal (con envío simulado)."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{API_URL}/webhook/whatsapp",
            json={
                "from_number": phone,
                "text": text
            }
        )
        return response.json()


async def check_health() -> bool:
    """Verifica que la API esté disponible."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{API_URL}/health")
            data = response.json()
            print(f"✅ API disponible")
            print(f"   LLM: {data.get('llm', {}).get('provider')} / {data.get('llm', {}).get('model')}")
            return True
    except Exception as e:
        print(f"❌ API no disponible: {e}")
        return False


def print_response(result: dict):
    """Imprime la respuesta de forma legible."""
    print("\n" + "="*60)
    print("RESULTADO")
    print("="*60)
    
    if result.get("status") == "ok":
        print(f"📱 De: {result.get('from', 'N/A')}")
        print(f"💬 Mensaje: {result.get('message', 'N/A')}")
        print(f"🔀 Ruta: {result.get('route_info', {}).get('route', 'N/A')}")
        print(f"🤖 Agente: {result.get('agente', 'N/A')}")
        print(f"\n📤 RESPUESTA:")
        print("-"*60)
        print(result.get('respuesta', 'Sin respuesta'))
        print("-"*60)
        
        # Info de ruteo
        route_info = result.get('route_info', {})
        if route_info.get('matched_keywords'):
            matched = route_info['matched_keywords']
            if any(matched.values()):
                print(f"\n🔍 Keywords detectados:")
                for tipo, kws in matched.items():
                    if kws:
                        print(f"   {tipo}: {kws}")
    else:
        print(f"❌ Error: {result.get('error', 'Error desconocido')}")
    
    print("="*60 + "\n")


async def interactive_mode():
    """Modo interactivo para enviar múltiples mensajes."""
    print("\n🎮 Modo interactivo")
    print("Escribe mensajes para probar. Escribe 'salir' para terminar.\n")
    
    phone = input("Número de WhatsApp (ej: +5491112345005): ").strip()
    if not phone:
        phone = "+5491112345005"
    
    print(f"\nUsando número: {phone}")
    print("-"*40)
    
    while True:
        try:
            text = input("\n💬 Tu mensaje: ").strip()
            
            if text.lower() in ['salir', 'exit', 'quit', 'q']:
                print("👋 ¡Hasta luego!")
                break
            
            if not text:
                continue
            
            print("⏳ Procesando...")
            result = await send_test_message(phone, text)
            print_response(result)
            
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


async def main():
    """Función principal."""
    print("="*60)
    print("🧪 TEST DE MENSAJES WHATSAPP - GESTOR WS")
    print("="*60)
    
    # Verificar API
    if not await check_health():
        print("\n⚠️ Asegúrate de que la API esté corriendo:")
        print("   docker-compose up -d")
        print("   o")
        print("   uvicorn app.main:app --reload")
        return
    
    # Modo según argumentos
    if len(sys.argv) >= 3:
        phone = sys.argv[1]
        text = " ".join(sys.argv[2:])
        
        print(f"\n📱 Enviando mensaje...")
        print(f"   A: {phone}")
        print(f"   Mensaje: {text}")
        
        result = await send_test_message(phone, text)
        print_response(result)
        
    elif len(sys.argv) == 2 and sys.argv[1] == "-i":
        await interactive_mode()
        
    else:
        print("\n📖 USO:")
        print("   python scripts/test_whatsapp.py <numero> <mensaje>")
        print("   python scripts/test_whatsapp.py -i  (modo interactivo)")
        print("\n📝 EJEMPLOS:")
        print('   python scripts/test_whatsapp.py "+5491112345005" "Cuánto debo?"')
        print('   python scripts/test_whatsapp.py "+5491112345005" "Hola"')
        print('   python scripts/test_whatsapp.py "+5491112345005" "Necesito un plan de pagos"')
        print('   python scripts/test_whatsapp.py "+5491112345005" "Tengo un reclamo"')
        
        print("\n🎮 Iniciando modo interactivo...")
        await interactive_mode()


if __name__ == "__main__":
    asyncio.run(main())



