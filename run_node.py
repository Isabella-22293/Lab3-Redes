
import argparse, json
from node import Node

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="Nombre del nodo (ej. A)")
    ap.add_argument("--proto", default="dijkstra", choices=["dijkstra","flooding","lsr","dvr"])
    ap.add_argument("--topo", required=False, help="Ruta a topo-*.json")
    ap.add_argument("--names", required=True, help="Ruta a names-*.json")
    args = ap.parse_args()

    topo = load_json(args.topo) if args.topo else None
    names = load_json(args.names)["config"]
    # Convertir "127.0.0.1:5000" a (host,port)
    addr_book = {k: (v.split(":")[0], int(v.split(":")[1])) for k, v in names.items()}

    n = Node(args.name, addr_book, args.proto, topo)
    n.start()
    n.join()

if __name__ == "__main__":
    main()
