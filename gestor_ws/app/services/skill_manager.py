import os
import yaml
import logging
import asyncio
import subprocess
import json
import sys
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

class SkillManager:
    """
    Gestor de Skills. Escanea, carga y ejecuta skills definidos en .agent/skills
    """
    
    def __init__(self, skills_dir: str = ".agent/skills"):
        # Asumimos que la ruta es relativa al root del proyecto
        self.project_root = Path(os.getcwd())
        self.skills_dir = self.project_root / skills_dir
        self.skills: Dict[str, Dict[str, Any]] = {}
        self._load_skills()

    def _load_skills(self):
        """Escanea el directorio de skills y carga los metadatos."""
        if not self.skills_dir.exists():
            logger.warning(f"Directorio de skills no encontrado: {self.skills_dir}")
            return

        logger.info(f"Escaneando skills en: {self.skills_dir}")
        
        for item in self.skills_dir.iterdir():
            if item.is_dir():
                skill_file = item / "SKILL.md"
                if skill_file.exists():
                    try:
                        self._parse_skill_file(skill_file, item.name)
                    except Exception as e:
                        logger.error(f"Error cargando skill {item.name}: {e}")

    def _parse_skill_file(self, file_path: Path, dir_name: str):
        """Parsea el frontmatter YAML de SKILL.md."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extraer frontmatter (entre --- y ---)
        if content.startswith("---"):
            try:
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    yaml_content = parts[1]
                    metadata = yaml.safe_load(yaml_content)
                    
                    skill_name = metadata.get("name", dir_name)
                    self.skills[skill_name] = {
                        "path": file_path.parent,
                        "metadata": metadata
                    }
                    logger.info(f"Skill cargada: {skill_name}")
            except Exception as e:
                logger.error(f"Error parseando frontmatter de {file_path}: {e}")
        else:
            logger.warning(f"{file_path} no tiene frontmatter válido.")

    def get_skill(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """Obtiene la configuración de una skill."""
        return self.skills.get(skill_name)

    async def execute_skill(self, skill_name: str, script_name: str, args: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Ejecuta un script de una skill.
        
        Args:
            skill_name: Nombre de la skill (ej: whatsapp-emulator)
            script_name: Nombre del script (ej: send_message.py)
            args: Diccionario de argumentos para el script (key: value) se transforman en --key "value"
        
        Returns:
            Dict con el resultado (stdout parseado como JSON si es posible, o raw output)
        """
        skill = self.get_skill(skill_name)
        if not skill:
            raise ValueError(f"Skill no encontrada: {skill_name}")

        script_path = skill["path"] / "scripts" / script_name
        if not script_path.exists():
            raise ValueError(f"Script no encontrado: {script_path}")

        # Construir comando usando el ejecutable actual de Python
        # Esto asegura que se usen las librerías del entorno virtual activo
        cmd = [sys.executable, str(script_path)]
        
        if args:
            for key, value in args.items():
                if value is not None:
                    cmd.append(f"--{key}")
                    cmd.append(str(value))

        logger.info(f"Ejecutando skill {skill_name}: {' '.join(cmd)}")

        try:
            # Ejecutar proceso
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            stdout_str = stdout.decode().strip()
            stderr_str = stderr.decode().strip()

            if process.returncode != 0:
                logger.error(f"Error ejecutando skill {skill_name}: {stderr_str}")
                return {"success": False, "error": stderr_str, "details": stdout_str}

            # Intentar parsear JSON del stdout
            try:
                # Buscar el último bloque JSON válido si hay logs previos
                lines = stdout_str.split('\n')
                json_result = None
                for line in reversed(lines):
                    try:
                        json_result = json.loads(line)
                        break
                    except json.JSONDecodeError:
                        continue
                
                if json_result:
                    return json_result
                else:
                    return {"success": True, "output": stdout_str}
                    
            except Exception:
                return {"success": True, "output": stdout_str}

        except Exception as e:
            logger.error(f"Excepción ejecutando skill: {e}")
            return {"success": False, "error": str(e)}

# Singleton instance
_skill_manager = None

def get_skill_manager() -> SkillManager:
    global _skill_manager
    if _skill_manager is None:
        _skill_manager = SkillManager()
    return _skill_manager
