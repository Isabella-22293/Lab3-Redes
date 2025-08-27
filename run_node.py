import argparse
import threading
from redis_client import get_redis, get_pubsub, publish
from config_loader import load_topo, load_names
from flooding import FloodingNode
from distance_vector import DistanceVectorNode
from link_state import LinkStateNode

ALGO_MAP = {
    "flooding": FloodingNode,
    "dv": DistanceVectorNode,
    "linkstate": LinkStateNode,
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, help="ID del nodo")
    parser.add_argument("--topo", required=True, help="Archivo topo-*.json")
    parser.add_argument("--names", required=True, help="Archivo names-*.json")
    parser.add_argument("--algo", default="flooding", choices=list(ALGO_MAP.keys()))
    args = parser.parse_args()

    topo = load_topo(args.topo)
    names = load_names(args.names)

    if args.name not in topo:
        print(f"ERROR: nodo {args.name} no encontrado en la topología")
        return

    r = get_redis()
    pubsub = get_pubsub(r)
    neighbors = topo[args.name]
    node_class = ALGO_MAP[args.algo]

    node = node_class(
        node_id=args.name,
        redis_conn=r,
        pubsub=pubsub,
        neighbors=neighbors,
        names=names,
    )

    threading.Thread(target=node.listen_loop, daemon=True).start()
    threading.Thread(target=node.periodic_tasks, daemon=True).start()

    print(f"Nodo {args.name} corriendo algoritmo {args.algo}. Vecinos: {neighbors}")

    try:
        while True:
            cmd = input().strip()
            if cmd == "exit":
                break
            if cmd.startswith("send "):
                parts = cmd.split(" ", 2)
                if len(parts) < 3:
                    print("Uso: send <dest> <mensaje>")
                    continue
                dest, msg = parts[1], parts[2]
                node.send_message(dest, msg)
            elif cmd == "peers":
                print("Neighbors:", neighbors)
            elif cmd == "table":
                node.debug_print()
            else:
                print("Comandos: send <dest> <msg>, peers, table, exit")
    except KeyboardInterrupt:
        print("Saliendo...")

if __name__ == "__main__":
    main()
