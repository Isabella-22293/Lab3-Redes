import json

def load_topo(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if data.get('type') != 'topo':
        raise ValueError('Archivo topo inválido')
    return data['config']

def load_names(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if data.get('type') != 'names':
        raise ValueError('Archivo names inválido')
    return data['config']
