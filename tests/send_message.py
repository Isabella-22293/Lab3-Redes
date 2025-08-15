
import argparse, json, socket
from message import make_packet

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def send(names, to_name, pkt):
    host, port = names[to_name].split(":")
    addr = (host, int(port))
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(addr)
    s.sendall((json.dumps(pkt) + "\n").encode("utf-8"))
    s.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="from_", required=True, help="Origen (nombre de nodo)")
    ap.add_argument("--to", dest="to", required=True, help="Destino (nombre de nodo)")
    ap.add_argument("--names", required=True, help="Ruta a names-*.json")
    args = ap.parse_args()

    names = load_json(args.names)["config"]
    pkt = make_packet("dijkstra", "message", args.from_, args.to, 8, {"text": "Hola desde tests/send_message.py"})
    # Se envía el paquete inicial al nodo origen
    send(names, args.from_, pkt)

if __name__ == "__main__":
    main()
