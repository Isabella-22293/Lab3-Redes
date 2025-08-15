
from __future__ import annotations
import json, socket, threading, time, queue
from typing import Dict, Tuple, Any
from dijkstra import Graph, dijkstra, build_next_hop
from message import make_packet

class Node:
    def __init__(self, name: str, addr_book: Dict[str, Tuple[str, int]], proto: str, topo: Dict[str, Any]|None):
        self.name = name
        self.addr_book = addr_book  # nombre -> (host, port)
        self.proto = proto
        self.topo_raw = topo
        self.graph = Graph.from_topology(topo) if topo else None
        self.next_hop: Dict[str, str] = {}
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind(self.addr_book[self.name])
        self.server_sock.listen(16)
        self.stop_event = threading.Event()
        self.incoming_q: "queue.Queue[Dict[str, Any]]" = queue.Queue()

    # Hilos
    def start(self):
        self._routing_thread = threading.Thread(target=self.routing_loop, daemon=True)
        self._forwarding_thread = threading.Thread(target=self.forwarding_loop, daemon=True)
        self._accept_thread = threading.Thread(target=self.accept_loop, daemon=True)
        self._routing_thread.start()
        self._forwarding_thread.start()
        self._accept_thread.start()

    def join(self):
        try:
            while not self.stop_event.is_set():
                time.sleep(0.2)
        except KeyboardInterrupt:
            print("[CTRL-C] Deteniendo...")
            self.stop_event.set()

    # Acepta conexiones entrantes y encola paquetes
    def accept_loop(self):
        print(f"[{self.name}] Escuchando en {self.addr_book[self.name]}")
        while not self.stop_event.is_set():
            try:
                self.server_sock.settimeout(1.0)
                conn, _ = self.server_sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with conn:
                data = b""
                # lectura sencilla: una línea por paquete
                while True:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                for line in data.splitlines():
                    try:
                        pkt = json.loads(line.decode("utf-8"))
                        self.incoming_q.put(pkt)
                    except Exception as e:
                        print(f"[{self.name}] Paquete inválido: {e}")

    # Procesa paquetes: DATA, INFO, HELLO, etc.
    def forwarding_loop(self):
        while not self.stop_event.is_set():
            try:
                pkt = self.incoming_q.get(timeout=0.5)
            except queue.Empty:
                continue
            # TTL
            ttl = int(pkt.get("ttl", 0))
            if ttl <= 0:
                print(f"[{self.name}] TTL agotado, descarta: {pkt}")
                continue

            ptype = pkt.get("type")
            to = pkt.get("to")
            if to == self.name and ptype == "message":
                print(f"[{self.name}] MENSAJE PARA MI: {pkt['payload']} (de {pkt['from']})")
                continue

            if ptype == "info":
                topo = pkt.get("payload", {}).get("topology")
                if topo:
                    print(f"[{self.name}] INFO: actualizando topología...")
                    self.topo_raw = topo
                    self.graph = Graph.from_topology(self.topo_raw)
                    self.recompute_table()
                self.flood(pkt)
                continue

            if ptype == "hello":
                print(f"[{self.name}] HELLO desde {pkt['from']}")
                echo = make_packet(self.proto, "echo", self.name, pkt["from"], 8, {"ts": time.time()})
                self.send_packet(echo, next_hop=pkt["from"])  # envío directo al vecino
                continue

            # DATA / routing normal
            self.forward(pkt)

    def routing_loop(self):
        # Inicializa tabla de ruteo
        time.sleep(0.5)
        if self.proto == "dijkstra" and self.graph is not None:
            self.recompute_table()
        while not self.stop_event.is_set():
            time.sleep(2.0) 

    def recompute_table(self):
        dist, prev = dijkstra(self.graph, self.name)
        self.next_hop = build_next_hop(prev, self.name)
        print(f"[{self.name}] Tabla de ruteo (next-hop): {self.next_hop}")

    def neighbors(self):
        if self.graph and self.topo_raw:
            return self.topo_raw.get("config", {}).get(self.name, [])
        return []

    def connect(self, neighbor_name: str):
        addr = self.addr_book[neighbor_name]
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.0)
        s.connect(addr)
        return s

    def send_packet(self, pkt, *, next_hop: str):
        if next_hop not in self.addr_book:
            print(f"[{self.name}] No conozco a {next_hop} en address book")
            return
        try:
            with self.connect(next_hop) as s:
                s.sendall((json.dumps(pkt) + "\n").encode("utf-8"))
        except Exception as e:
            print(f"[{self.name}] Error enviando a {next_hop}: {e}")

    def forward(self, pkt):
        # Reduce TTL
        pkt["ttl"] = int(pkt.get("ttl", 8)) - 1
        dst = pkt.get("to")
        nh = self.next_hop.get(dst)
        if nh is None:
            print(f"[{self.name}] Sin ruta a {dst}, intento flooding a vecinos...")
            self.flood(pkt)
            return
        if nh == self.name:
            print(f"[{self.name}] next-hop soy yo? descarta/break loop")
            return
        print(f"[{self.name}] Forward → {dst} via {nh}")
        self.send_packet(pkt, next_hop=nh)

    def flood(self, pkt):
        headers = pkt.get("headers") or [{}]
        if not isinstance(headers, list) or not headers:
            headers = [{}]
        seen = set(headers[0].get("seen", []))
        if self.name in seen:
            return
        seen.add(self.name)
        headers[0]["seen"] = list(seen)
        pkt["headers"] = headers
        for nb in self.neighbors():
            if nb not in seen:
                cp = json.loads(json.dumps(pkt))
                cp["ttl"] = int(cp.get("ttl", 8)) - 1
                if cp["ttl"] <= 0:
                    continue
                print(f"[{self.name}] FLOOD → {nb}")
                self.send_packet(cp, next_hop=nb)
