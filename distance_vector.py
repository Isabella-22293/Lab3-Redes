import threading
import time
from utils import make_packet, decode_message
from redis_client import publish

INF = 10**9

class DistanceVectorNode:
    """
    Nodo que implementa el algoritmo de enrutamiento por vector de distancias.
    """

    def __init__(self, node_id, redis_conn, pubsub, neighbors, names):
        self.node_id = node_id
        self.r = redis_conn
        self.pubsub = pubsub
        self.neighbors = neighbors
        self.names = names

        # Tabla de ruteo: destino -> (costo, siguiente_salto)
        self.table = {node_id: (0, node_id)}
        for n in neighbors:
            self.table[n] = (1, n)

        self.pubsub.subscribe(self.node_id)
        self.lock = threading.Lock()

    def listen_loop(self):
        """
        Escucha mensajes entrantes y los maneja en hilos separados.
        """
        for msg in self.pubsub.listen():
            if msg['type'] != 'message':
                continue
            pkt = decode_message(msg['data'])
            threading.Thread(target=self.handle_packet, args=(pkt,), daemon=True).start()

    def handle_packet(self, pkt: dict):
        """
        Procesa mensajes entrantes y tablas de distancias.
        """
        ptype = pkt.get('type')

        if ptype == 'dv_table':
            self._process_dv(pkt)
            return

        if ptype == 'message':
            dest = pkt['to']
            if dest == self.node_id:
                print(f"[{self.node_id}] Mensaje RECIBIDO: {pkt['payload']}")
                return

            with self.lock:
                entry = self.table.get(dest)
                if not entry:
                    print(f"[{self.node_id}] No conozco ruta a {dest}")
                    return
                next_hop = entry[1]

            forward = dict(pkt)
            forward['from'] = self.node_id
            publish(self.r, next_hop, forward)
            print(f"[{self.node_id}] Reenviado a {next_hop} para destino {dest}")

    def _process_dv(self, pkt: dict):
        """
        Procesa tablas de distancias recibidas de vecinos.
        """
        sender = pkt['from']
        received_table = pkt['payload']
        updated = False

        with self.lock:
            cost_to_sender = self.table.get(sender, (INF, None))[0]
            for dest, cost in received_table.items():
                new_cost = cost_to_sender + int(cost)
                old_cost = self.table.get(dest, (INF, None))[0]
                if new_cost < old_cost:
                    self.table[dest] = (new_cost, sender)
                    updated = True

        if updated:
            print(f"[{self.node_id}] Tabla actualizada: {self.table}")

    def send_message(self, dest: str, text: str):
        """
        Envía un mensaje según la tabla de distancias.
        """
        pkt = make_packet('message', self.node_id, dest, text, hops=0)

        with self.lock:
            entry = self.table.get(dest)
            if not entry:
                print(f"[{self.node_id}] No hay ruta conocida a {dest}")
                return
            next_hop = entry[1]

        forward = dict(pkt)
        forward['from'] = self.node_id
        publish(self.r, next_hop, forward)
        print(f"[{self.node_id}] Enviando a {dest} vía {next_hop}")

    def periodic_tasks(self):
        """
        Publica periódicamente la tabla de distancias a los vecinos.
        """
        while True:
            payload = {k: v[0] for k, v in self.table.items()}
            pkt = make_packet('dv_table', self.node_id, 'all', payload, hops=0)
            for n in self.neighbors:
                publish(self.r, n, pkt)
            time.sleep(5)

    def debug_print(self):
        """
        Imprime la tabla de ruteo actual.
        """
        print(f"[{self.node_id}] Tabla: {self.table}")
