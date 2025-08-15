
# Lab 3 – Algoritmos de Enrutamiento (Prototipo)
Avances solicitados:
1) **Dijkstra** funcional para construir tabla de ruteo a partir de la topología.
2) **Infraestructura** de sockets + hilos en paralelo: *forwarding* y *routing*, con formato de mensaje tipo JSON.

> Probado localmente en una sola máquina usando TCP sockets (fase 1).

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

## Notas
- Este prototipo cumple el formato de mensaje del enunciado (`proto`, `type`, `from`, `to`, `ttl`, `headers`, `payload`).
- Los hilos corren en paralelo: `forwarding_loop()` escucha y reenvía; `routing_loop()` inicializa tabla y atiende INFO.
- TTL se decrementa en cada salto; si llega a 0 se descarta.
- El *routing* con Dijkstra reconstruye tabla ante cambio de topología (si recarga archivo o si llega INFO).
- Queda listo para integrar Flooding/LSR/DV y reemplazar transportes por XMPP en la fase 2.
