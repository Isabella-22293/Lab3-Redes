import json, time, socket
from node import Node

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_addr_book(names_config):
    return {k: (v.split(":")[0], int(v.split(":")[1])) for k, v in names_config.items()}

def send_packet_to_node(addr, pkt):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(2.0)
        s.connect(addr)
        s.sendall((json.dumps(pkt) + "\n").encode("utf-8"))

def main():
    names = load_json("configs/names-example.json")["config"]
    topo = load_json("configs/topo-example.json")
    addr_book = build_addr_book(names)

    print("==> Levantando nodos (Dijkstra)")
    nodes = {}
    for name in names.keys():
        n = Node(name, addr_book, proto="dijkstra", topo=topo)
        n.start()
        nodes[name] = n

    time.sleep(1.0)

    pkt = {
        "proto": "dijkstra",
        "type": "message",
        "from": "A",
        "to": "C",
        "ttl": 8,
        "headers": [],
        "payload": "Mensaje de prueba Dijkstra"
    }
    print("==> Enviando mensaje Dijkstra desde A a C")
    send_packet_to_node(addr_book["A"], pkt)

    time.sleep(2.0)
    for n in nodes.values():
        n.stop()
    time.sleep(1.0)

    print("==> Levantando nodos (Flooding)")
    nodes = {}
    for name in names.keys():
        n = Node(name, addr_book, proto="flooding", topo=topo)
        n.start()
        nodes[name] = n

    time.sleep(1.0)

    pkt2 = {
        "proto": "flooding",
        "type": "message",
        "from": "A",
        "to": "C",
        "ttl": 8,
        "headers": [],
        "payload": "Mensaje de prueba Flooding"
    }
    print("==> Enviando mensaje Flooding desde A a C")
    send_packet_to_node(addr_book["A"], pkt2)

    time.sleep(2.0)
    for n in nodes.values():
        n.stop()

if __name__ == "__main__":
    main()
