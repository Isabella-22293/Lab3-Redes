
# Lab 3 – Algoritmos de Enrutamiento

## Estructura
- `dijkstra.py`: algoritmo y utilidades de grafo.
- `message.py`: formateo/validación del paquete JSON.
- `node.py`: clase `Node` con hilos `forwarding` y `routing`.
- `run_node.py`: script CLI para lanzar un nodo.
- `configs/topo-example.json`: topología de ejemplo (para Dijkstra).
- `configs/names-example.json`: mapeo nombre→host:puerto para pruebas locales.
- `tests/send_message.py`: utilitario para enviar un mensaje DATA.

## Requisitos
- Python 3.9+

## Cómo correr (local)
Terminal 1:
```bash
python run_node.py --name A --proto dijkstra --topo configs/topo-example.json --names configs/names-example.json
```

Terminal 2:
```bash
python run_node.py --name B --proto dijkstra --topo configs/topo-example.json --names configs/names-example.json
```

Terminal 3:
```bash
python run_node.py --name C --proto dijkstra --topo configs/topo-example.json --names configs/names-example.json
```

Enviar un mensaje desde A → C:
```bash
python tests/send_message.py --from A --to C --names configs/names-example.json
```

Deberías ver en consola el *forwarding* pasando por B (si A–C no son vecinos directos).
