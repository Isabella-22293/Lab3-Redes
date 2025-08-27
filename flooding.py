import threading
import time
from utils import make_packet, decode_message
from redis_client import publish

class FloodingNode:
    """
    Nodo que implementa el algoritmo de flooding para enviar mensajes.
    """

    def __init__(self, node_id, redis_conn, pubsub, neighbors, names):
        self.node_id = node_id
        self.r = redis_conn
        self.pubsub = pubsub
        self.neighbors = neighbors
        self.names = names
        self.seen = set()  # Mensajes ya procesados

        self.pubsub.subscribe(self.node_id)

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
        Procesa y reenvía mensajes entrantes evitando bucles.
        """
        mid = (pkt.get('from'), pkt.get('ts'))
        if mid in self.seen:
            return
        self.seen.add(mid)

        pkt['hops'] = pkt.get('hops', 0) + 1
        print(f"[{self.node_id}] Recibido {pkt['type']} de {pkt['from']} -> {pkt['to']} (hops={pkt['hops']})")

        # Si el mensaje es para mí, lo mostramos
        if pkt['to'] == self.node_id:
            print(f"[{self.node_id}] Mensaje DESTINO: {pkt['payload']}")
            return

        # Control de TTL si existe
        for h in pkt.get('headers', []):
            if 'ttl' in h:
                ttl = int(h['ttl'])
                if ttl <= 0:
                    return
                h['ttl'] = str(ttl - 1)

        # Reenviar a todos los vecinos excepto al emisor
        for n in self.neighbors:
            if n == pkt.get('from'):
                continue
            forward = dict(pkt)
            forward['from'] = self.node_id
            try:
                publish(self.r, n, forward)
                print(f"[{self.node_id}] Reenviado a {n}")
            except Exception as e:
                print(f"[{self.node_id}] Error publicando a {n}: {e}")

    def send_message(self, dest: str, text: str):
        """
        Envía un mensaje usando flooding.
        """
        pkt = make_packet('message', self.node_id, dest, text, hops=0, headers=[{'ttl': '10'}])
        for n in self.neighbors:
            publish(self.r, n, pkt)
        print(f"[{self.node_id}] Enviando mensaje '{text}' a {dest} vía flooding")

    def periodic_tasks(self):
        """
        Flooding no requiere tareas periódicas, mantiene vivo el hilo.
        """
        while True:
            time.sleep(5)

    def debug_print(self):
        """
        Imprime los mensajes vistos (primeros 10).
        """
        print(f"[{self.node_id}] Seen messages: {list(self.seen)[:10]}")
