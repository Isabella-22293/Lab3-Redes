from __future__ import annotations
import json
import socket
import threading
import time
import queue
from typing import Dict, Tuple, Any, Optional
from dijkstra import Graph, dijkstra, build_next_hop
from message import make_packet


class Node:
    def __init__(self, name: str, addr_book: Dict[str, Tuple[str, int]], proto: str, topo: Optional[Dict[str, Any]] = None):
        # Identificación y configuración
        self.name = name
        self.addr_book = addr_book
        self.proto = proto
        self.topo_raw = topo

        # Grafo de topología
        self.graph = Graph.from_topology(topo) if topo else None
        self.next_hop: Dict[str, str] = {}

        # Comunicación
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind(self.addr_book[self.name])
        self.server_sock.listen(16)

        # Control de hilos y eventos
        self.stop_event = threading.Event()
        self.incoming_q: "queue.Queue[Dict[str, Any]]" = queue.Queue()

    # ----------------------------------------------------------------------
    # INICIO / PARADA DEL NODO
    # ----------------------------------------------------------------------
    def start(self):
        """Inicia los hilos principales: routing, forwarding y accept."""
        self._routing_thread = threading.Thread(target=self.routing_loop, daemon=True)
        self._forwarding_thread = threading.Thread(target=self.forwarding_loop, daemon=True)
        self._accept_thread = threading.Thread(target=self.accept_loop, daemon=True)

        self._routing_thread.start()
        self._forwarding_thread.start()
        self._accept_thread.start()

    def join(self):
        """Mantiene el nodo activo hasta interrupción manual."""
        try:
            while not self.stop_event.is_set():
                time.sleep(0.2)
        except KeyboardInterrupt:
            print("[CTRL-C] Deteniendo nodo...")
            self.stop()

    def stop(self):
        """Detiene el nodo y cierra el socket."""
        self.stop_event.set()
        try:
            self.server_sock.close()
        except Exception:
            pass

    # ----------------------------------------------------------------------
    # RECEPCIÓN DE CONEXIONES
    # ----------------------------------------------------------------------
    def accept_loop(self):
        """Hilo encargado de recibir paquetes entrantes."""
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
                while True:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk

                # Procesar cada línea recibida
                for line in data.splitlines():
                    try:
                        pkt = json.loads(line.decode("utf-8"))
                        self.incoming_q.put(pkt)
                    except json.JSONDecodeError:
                        print(f"[{self.name}] Paquete inválido recibido.")

    # ----------------------------------------------------------------------
    # FORWARDING LOOP
    # ----------------------------------------------------------------------
    def forwarding_loop(self):
        """Procesa la cola de paquetes entrantes y actúa según el tipo."""
        while not self.stop_event.is_set():
            try:
                pkt = self.incoming_q.get(timeout=0.5)
            except queue.Empty:
                continue

            # Validar TTL
            pkt["ttl"] = int(pkt.get("ttl", 0))
            if pkt["ttl"] <= 0:
                print(f"[{self.name}] TTL agotado, descartando paquete: {pkt}")
                continue

            ptype = pkt.get("type")
            to = pkt.get("to")

            # Mensaje directo para este nodo
            if to == self.name and ptype == "message":
                print(f"[{self.name}] 📩 MENSAJE: {pkt['payload']} (de {pkt['from']})")
                continue

            # Actualización de topología
            if ptype == "info":
                topo = pkt.get("payload", {}).get("topology")
                if topo:
                    print(f"[{self.name}] 🔄 Actualizando topología...")
                    self.topo_raw = topo
                    self.graph = Graph.from_topology(self.topo_raw)
                    self.recompute_table()
                self.flood(pkt)
                continue

            # Mensajes HELLO
            if ptype == "hello":
                print(f"[{self.name}] 👋 HELLO desde {pkt['from']}")
                echo = make_packet(self.proto, "echo", self.name, pkt["from"], 8, {"ts": time.time()})
                self.send_packet(echo, next_hop=pkt["from"])
                continue

            # Reenvío normal
            self.forward(pkt)

    # ----------------------------------------------------------------------
    # ROUTING LOOP
    # ----------------------------------------------------------------------
    def routing_loop(self):
        """Recalcula tablas y envía HELLO periódicamente."""
        time.sleep(0.5)

        # Inicialización para dijkstra
        if self.proto == "dijkstra" and self.graph is not None:
            self.recompute_table()
            self.send_hello_to_neighbors()

        # Recalcular tablas periódicamente
        while not self.stop_event.is_set():
            if self.proto == "dijkstra" and self.graph is not None:
                self.recompute_table()
            time.sleep(2.0)

    # ----------------------------------------------------------------------
    # TABLAS DE RUTEO Y VECINOS
    # ----------------------------------------------------------------------
    def recompute_table(self):
        """Recalcula la tabla de ruteo usando Dijkstra."""
        dist, prev = dijkstra(self.graph, self.name)
        self.next_hop = build_next_hop(prev, self.name)
        print(f"[{self.name}] 🗺️ Tabla de ruteo: {self.next_hop}")

    def neighbors(self):
        """Obtiene los vecinos inmediatos de este nodo."""
        if self.graph and self.topo_raw:
            return self.topo_raw.get("config", {}).get(self.name, [])
        return []

    # ----------------------------------------------------------------------
    # ENVÍO DE PAQUETES
    # ----------------------------------------------------------------------
    def connect(self, neighbor_name: str) -> socket.socket:
        """Abre una conexión con un vecino."""
        addr = self.addr_book[neighbor_name]
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.0)
        s.connect(addr)
        return s

    def send_packet(self, pkt: Dict[str, Any], *, next_hop: str):
        """Envía un paquete al siguiente salto."""
        if next_hop not in self.addr_book:
            print(f"[{self.name}] ⚠️ No conozco a {next_hop}")
            return

        addr = self.addr_book[next_hop]
        try:
            with self.connect(next_hop) as s:
                s.sendall((json.dumps(pkt) + "\n").encode("utf-8"))
        except Exception as e:
            print(f"[{self.name}] ❌ Error enviando a {next_hop} ({addr}): {e}")

    def forward(self, pkt: Dict[str, Any]):
        """Reenvía un paquete hacia su destino."""
        pkt["ttl"] = int(pkt.get("ttl", 8)) - 1
        dst = pkt.get("to")
        nh = self.next_hop.get(dst)

        if nh is None:
            print(f"[{self.name}] ❌ Sin ruta a {dst}, aplicando flooding...")
            self.flood(pkt)
            return

        if nh == self.name:
            print(f"[{self.name}] ⚠️ Next-hop soy yo, descartando paquete.")
            return

        print(f"[{self.name}] 🚀 Forward → {dst} via {nh}")
        self.send_packet(pkt, next_hop=nh)

    def flood(self, pkt: Dict[str, Any]):
        """Difunde un paquete a todos los vecinos no visitados."""
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
                cp = json.loads(json.dumps(pkt))  # Clonar el paquete
                cp["ttl"] = int(cp.get("ttl", 8)) - 1
                if cp["ttl"] <= 0:
                    continue
                print(f"[{self.name}] 🌊 FLOOD → {nb}")
                self.send_packet(cp, next_hop=nb)

    def send_hello_to_neighbors(self):
        """Envía mensajes HELLO a todos los vecinos inmediatos."""
        for nb in self.neighbors():
            pkt = make_packet(self.proto, "hello", self.name, nb, 8, {"ts": time.time()})
            try:
                self.send_packet(pkt, next_hop=nb)
            except Exception as e:
                print(f"[{self.name}] ❌ Error enviando HELLO a {nb}: {e}")
