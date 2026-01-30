import re
import sys
import json
import io
from pathlib import Path
from datetime import datetime

# Configurar UTF-8 en stdout para Windows
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass


# Configuración de archivos - Búsqueda inteligente de logs
def find_log_files():
    # Posibles ubicaciones de la carpeta 'logs'
    paths_to_check = [
        Path("logs"),                      # En el CWD actual
        Path("gestor_ws/logs"),            # Desde la raíz si el proyecto está estructurado así
        Path("gestor_ws/tests/logs"),      # Si corren desde la raíz pero el test creó su carpeta
        Path("../logs"),                   # Desde tests/
        Path("../../logs")                 # Desde algún otro subdirectorio
    ]
    
    found_logs = []
    for base in paths_to_check:
        log_file = base / "gestor_ws.log"
        if log_file.exists():
            mtime = log_file.stat().st_mtime
            found_logs.append((mtime, base))
    
    if found_logs:
        # Ordenar por fecha de modificación (más reciente primero)
        found_logs.sort(key=lambda x: x[0], reverse=True)
        selected = found_logs[0][1]
        return selected
        
    return Path("logs") # Fallback

LOG_DIR = find_log_files()
GESTOR_LOG = LOG_DIR / "gestor_ws.log"
TOKEN_LOG = LOG_DIR / "token_usage.log"


def parse_token_log():
    """Parsea el log de tokens y devuelve un dict {query_id: token_data}"""
    if not TOKEN_LOG.exists():
        return {}
    
    token_data = {}
    content = TOKEN_LOG.read_text(encoding="utf-8", errors="replace")
    
    # Buscar JSONs de token_usage_summary
    regex = r"\[TOKEN_USAGE\] (\{.*\})"
    matches = re.finditer(regex, content)
    
    for match in matches:
        try:
            data = json.loads(match.group(1))
            if data.get("event") == "token_usage_summary":
                qid = data.get("query_id")
                if qid:
                    token_data[qid] = data
        except:
            pass
            
    return token_data

def get_timestamp_dt(timestamp_str):
    try:
        return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
    except:
        try:
             # Intento fallback sin milisegundos
             return datetime.strptime(timestamp_str.split(',')[0], '%Y-%m-%d %H:%M:%S')
        except:
            return None

def parseing_logs(num_consultas=1):
    if not GESTOR_LOG.exists():
        print(f"❌ No se encontró el archivo de log: {GESTOR_LOG}")
        return

    # Cargar datos de tokens primero
    token_db = parse_token_log()
    
    content = GESTOR_LOG.read_text(encoding="utf-8", errors="replace")
    consultas = []
    lines = content.split('\n')
    
    current_consulta = None
    
    for i, line in enumerate(lines):
        # 1. Detectar inicio de consulta
        if "Procesando mensaje de" in line:
            if current_consulta:
                # Calcular duración del último evento si es posible
                consultas.append(current_consulta)
            
            match = re.search(r"Procesando mensaje de (.*?): '(.*?)'", line)
            mensaje = match.group(2) if match else "Desconocido"
            timestamp_str = line.split(" - ")[0]
            
            current_consulta = {
                "start_line": i,
                "timestamp_str": timestamp_str,
                "start_dt": get_timestamp_dt(timestamp_str),
                "mensaje": mensaje,
                "events": [],
                "respuesta": None,
                "query_id": None,
                "tokens_total": 0,
                "token_details": []
            }
            continue
            
        if current_consulta is None:
            continue
            
        # 2. Detectar Query ID
        if "Sesión iniciada: query_id=" in line and not current_consulta["query_id"]:
            match = re.search(r"query_id=([a-f0-9-]+)", line)
            if match:
                qid = match.group(1)
                current_consulta["query_id"] = qid
                # Enlazar con datos de tokens
                if qid in token_db:
                    tdata = token_db[qid]
                    current_consulta["tokens_total"] = tdata.get("totals", {}).get("total_tokens", 0)
                    current_consulta["token_details"] = tdata.get("inferences", [])
        
        # 3. Detectar Eventos (con timestamp para calcular duración)
        timestamp_str = line.split(" - ")[0] if " - " in line else None
        dt = get_timestamp_dt(timestamp_str) if timestamp_str else None
        
        # Helper para agregar evento
        def add_event(type_name, desc, **kwargs):
            current_consulta["events"].append({
                "type": type_name,
                "desc": desc,
                "dt": dt,
                **kwargs
            })

        # --- EVENTOS ---
        
        # Planner Start
        if "app.agents.code_planner" in line and "[PLANNER] Iteración" in line:
            iter_match = re.search(r"Iteración (\d+/\d+)", line)
            iter_num = iter_match.group(1) if iter_match else "?"
            
            # Detectar si es replanificación (si ya hubo eventos de Planner antes)
            is_replan = any(e['type'] == 'PLANNER_START' for e in current_consulta['events'])
            
            add_event("PLANNER_START", f"Planificación (Iteración {iter_num})", is_replan=is_replan)

        # Código Generado
        elif "Código generado" in line:
            chars_match = re.search(r"\((\d+) chars\)", line)
            chars = chars_match.group(1) if chars_match else "?"
            add_event("CODE_GEN", f"Código generado ({chars} caracteres)", chars=int(chars) if chars != "?" else 0)

        # Preview de Código
        elif "Código:" in line or "Preview del código:" in line:
            code_preview = []
            for j in range(1, 500): # Capturar más líneas por si 'all'
                if i+j >= len(lines) or (lines[i+j].strip() != "" and re.match(r"\d{4}-\d{2}-\d{2}", lines[i+j])):
                    break
                code_preview.append(lines[i+j])
            current_consulta["events"][-1]["code"] = "\n".join(code_preview) # Pegar al evento anterior (CODE_GEN o similar)
            
        # Código Vacío
        elif "⚠️ Código vacío" in line:
            add_event("ERROR", "Generó código vacío (0 chars)", reason="Código vacío")

        # LLM Raw Response (Fallo parsing)
        elif "Respuesta cruda del LLM" in line:
            raw_resp = []
            for j in range(1, 10):
                if i+j >= len(lines) or re.match(r"\d{4}-\d{2}-\d{2}", lines[i+j]):
                    break
                raw_resp.append(lines[i+j])
            add_event("LLM_RAW", "Respuesta cruda del LLM", text="\n".join(raw_resp))

        # Executor Success
        elif "[EXECUTOR] ✅ Éxito" in line:
             add_event("EXECUTOR", "Ejecución exitosa", status="SUCCESS")

        # Executor Error
        elif "[EXECUTOR] ❌ Error" in line:
             reason = line.split("Error: ")[-1] if "Error: " in line else "Error desconocido"
             add_event("EXECUTOR", f"Error de ejecución: {reason}", status="ERROR", reason=reason)
        
        # Executor Summary (A veces viene en la línea siguiente)
        elif "[EXECUTOR] Summary:" in line:
             summary = line.split("Summary: ")[-1]
             # Buscamos el último evento de EXECUTOR activo para pegarle el summary
             for event in reversed(current_consulta["events"]):
                 if event["type"] == "EXECUTOR":
                     event["summary"] = summary
                     break

        # Reflector Valid
        elif "[REFLECTOR] ✅ Válido" in line:
             reason = line.split("Válido: ")[-1]
             add_event("REFLECTOR", "Validación exitosa", status="SUCCESS", reason=reason)

        # Reflector Invalid
        elif "[REFLECTOR] ❌ Inválido" in line:
             reason = line.split("Inválido: ")[-1]
             add_event("REFLECTOR", "Rechazado por calidad", status="ERROR", reason=reason)
        
        # Self Correction
        elif "Self-correction" in line:
            add_event("RETRY", "Iniciando auto-corrección", status="RETRY")

        # Responder
        elif "Respuesta generada:" in line:
            resp_match = re.search(r"Respuesta generada: '(.*?)'", line)
            resp = resp_match.group(1) if resp_match else line.split("Respuesta generada: ")[-1]
            current_consulta["respuesta"] = resp
            add_event("RESPONDER", "Respuesta final generada")

        # Fin de consulta
        if "Consulta finalizada:" in line and current_consulta["query_id"] in line:
             current_consulta["end_dt"] = dt

    if current_consulta:
        consultas.append(current_consulta)
        
    return consultas[-num_consultas:]

def format_duration(seconds):
    if seconds is None: return "N/A"
    return f"{seconds:.2f}s"

def print_report(consultas, show_all_code):
    print("\n" + "="*80)
    print(f"📊 REPORTE DE ANÁLISIS DE LOGS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    for idx, c in enumerate(consultas, 1):
        # Header
        duration_total = "N/A"
        if c.get("end_dt") and c.get("start_dt"):
            duration_total = format_duration((c["end_dt"] - c["start_dt"]).total_seconds())

        print(f"\n🔍 CONSULTA #{idx} | ID: {c['query_id']} | 🕒 {c['timestamp_str']}")
        print("-" * 80)
        
        # Pregunta y Respuesta (Completas si show_all_code)
        mensaje = c['mensaje']
        respuesta = c['respuesta'] or "(No encontrada)"
        
        if not show_all_code:
            mensaje = mensaje[:100] + "..." if len(mensaje) > 100 else mensaje
            respuesta = respuesta[:200] + "... (usa 'all' para ver completa)" if len(respuesta) > 200 else respuesta
            
        print(f"👤 PREGUNTA: \"{mensaje}\"")
        print(f"🤖 RESPUESTA: \"{respuesta}\"")
        print(f"\n⏱️ TIEMPO TOTAL: {duration_total} | 💰 TOKENS: {c['tokens_total']:,}")
        
        print("\n📜 DETALLE DE EJECUCIÓN:")
        
        # Agrupar eventos por "Pasos" lógicos
        # Iterar eventos y calcular tiempos relativos
        last_dt = c["start_dt"]
        
        for i, event in enumerate(c["events"]):
            # Calcular duración del paso individual
            step_duration = 0
            if event["dt"] and last_dt:
                step_duration = (event["dt"] - last_dt).total_seconds()
            last_dt = event["dt"] or last_dt

            # Visualización por tipo
            if event['type'] == 'PLANNER_START':
                prefix = "🔄" if event.get('is_replan') else "1."
                print(f"\n   {prefix} 🧠 CODE PLANNER")
                print(f"      ⏱️ +{format_duration(step_duration)}")
                
            elif event['type'] == 'CODE_GEN':
                print(f"      📝 {event['desc']}")
                # MOSTRAR CÓDIGO SI 'all'
                if show_all_code and event.get("code"):
                    print(f"\n      [CÓDIGO GENERADO]:")
                    print("      " + "-"*60)
                    for line in event["code"].splitlines():
                        print(f"      | {line}")
                    print("      " + "-"*60 + "\n")
                elif not show_all_code and event.get("code"):
                    print(f"      (Usa 'all' para ver el código)")

            elif event['type'] == 'ERROR':
                print(f"      🔴 FALLO: {event['desc']}")
                if event.get("reason"):
                    print(f"         Razón: {event['reason']}")

            elif event['type'] == 'LLM_RAW':
                 print(f"      🗣️ RESPUESTA CRUDA (No es código):")
                 print(f"         > {event['text'][:200]}...")

            elif event['type'] == 'EXECUTOR':
                status = "✅" if event.get("status") == "SUCCESS" else "🔴"
                print(f"\n   2. ⚙️ EXECUTOR")
                print(f"      {status} {event['desc']}")
                if event.get("reason"): print(f"         {event['reason']}")
                if event.get("summary"):
                    print(f"         📝 Summary: {event['summary']}")

            elif event['type'] == 'REFLECTOR':
                print(f"\n   3. 🔎 REFLECTOR")
                status = "✅" if event.get("status") == "SUCCESS" else "⚠️"
                print(f"      {status} {event['desc']}")
                
                reason = event.get("reason", "")
                if reason:
                    if not show_all_code and len(reason) > 100:
                        reason = reason[:100] + "..."
                    print(f"         \"{reason}\"")

            elif event['type'] == 'RESPONDER':
                print(f"\n   4. 💬 RESPONDER")
                print(f"      ✅ {event['desc']}")

            elif event['type'] == 'RETRY':
                print(f"\n   🔄 REPLANIFICANDO (Auto-correction)...")
                print("   " + "-"*40)

        print("="*80)

def print_compact(consultas):
    """Imprime un reporte súper compacto por cada consulta."""
    for idx, c in enumerate(consultas, 1):
        # Format date as YYYY/mm/dd to avoid confusion
        date_str = "0000/00/00"
        if c.get("start_dt"):
            date_str = c["start_dt"].strftime("%Y/%m/%d")
            
        # 1. Primera línea: La pregunta con fecha
        print(f"PREGUNTA [{date_str}]: {c['mensaje']}")
        
        # 2. Líneas de nodos
        if c.get("token_details"):
            last_time = c["start_dt"]
            for inf in c["token_details"]:
                inf_time_str = inf.get("timestamp")
                inf_dt = datetime.fromisoformat(inf_time_str) if inf_time_str else None
                
                duration_str = "N/A"
                if inf_dt and last_time:
                    duration = (inf_dt - last_time).total_seconds()
                    duration_str = f"{duration:.2f}s"
                    last_time = inf_dt
                
                node_name = inf.get("node_name", "unknown")
                tokens = inf.get("total_tokens", 0)
                print(f"   Nodo: {node_name:<15} | Tiempo: {duration_str:>6} | Tokens: {tokens:>5}")
        
        # 3. Última línea: La respuesta en una sola línea
        respuesta = c['respuesta'] or "(Sin respuesta)"
        respuesta_flat = respuesta.replace("\n", " ").strip()
        print(f"RESPUESTA: {respuesta_flat}")
        print("-" * 50)

def print_resume(consultas):
    """Imprime un resumen de una línea por consulta."""
    print("\n" + "="*100)
    print(f"{'ID':<10} | {'HORA':<19} | {'TIEMPO':<8} | {'TOKENS':<8} | {'PREGUNTA'}")
    print("-" * 100)
    
    for c in consultas:
        duration = "N/A"
        if c.get("end_dt") and c.get("start_dt"):
            duration = f"{(c['end_dt'] - c['start_dt']).total_seconds():.2f}s"
        
        qid = (c["query_id"][:8] if c["query_id"] else "N/A").ljust(8)
        ts = c["timestamp_str"]
        tokens = str(c["tokens_total"]).ljust(6)
        msg = c["mensaje"][:50] + "..." if len(c["mensaje"]) > 50 else c["mensaje"]
        
        print(f"{qid:<10} | {ts:<19} | {duration:<8} | {tokens:<8} | {msg}")
    
    print("="*100 + "\n")

    # Footer con ayuda
    print("\n💡 USO DEL SCRIPT:")
    print("   python analizar_logs.py [N] [all|resume|compacto]")
    print("\n   Ejemplos:")
    print("   • python analizar_logs.py          -> Ver reporte detallado de la última")
    print("   • python analizar_logs.py resume   -> Ver resumen de una línea")
    print("   • python analizar_logs.py compacto -> Ver reporte compacto (pregunta, nodos, respuesta)")
    print("   • python analizar_logs.py 5 compacto -> Ver las últimas 5 en modo compacto")
    print("\n")

if __name__ == "__main__":
    n = 1
    show_all = False
    resume_mode = False
    compact_mode = False
    
    # Parse args manual simple
    args = sys.argv[1:]
    if args:
        if "resume" in args:
            resume_mode = True
        if "compacto" in args:
            compact_mode = True
        if "all" in args:
            show_all = True
            
        # Buscar el número N
        for arg in args:
            if arg.isdigit():
                n = int(arg)
                break
            
    consultas = parseing_logs(n)
    if consultas:
        if resume_mode:
            print_resume(consultas)
        elif compact_mode:
            print_compact(consultas)
        else:
            print_report(consultas, show_all)
    else:
        print("No se encontraron consultas en el log.")
