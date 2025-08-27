import json
from pathlib import Path

def _load_json(path: str, expected_type: str) -> dict:
    """
    Carga un archivo JSON y valida que tenga el tipo esperado.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"El archivo {path} no existe")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if data.get('type') != expected_type:
        raise ValueError(f"Archivo inválido: se esperaba type='{expected_type}' y se obtuvo '{data.get('type')}'")

    return data.get('config', {})

def load_topo(path: str) -> dict:
    """
    Carga un archivo de topología de red.
    Retorna un diccionario con la configuración.
    """
    return _load_json(path, expected_type='topo')

def load_names(path: str) -> dict:
    """
    Carga un archivo de nombres de nodos.
    Retorna un diccionario con la configuración.
    """
    return _load_json(path, expected_type='names')
