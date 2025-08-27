import threading
import time
from utils import make_packet, decode_message
from redis_client import publish

class FloodingNode:
    def __init__(self, node_id, redis_conn, pubsub, neighbors, names):
        self.node_id = node_id
        self.r = redis_conn
        self.pubsub = pubsub
        self.neighbors = neighbors
        self.names = names
        self.seen = set()  # track message ids to avoid loops

        # subscribirse a mi canal
        self.pubsub.subscribe(self.node_id)

    def listen_loop(self):
        for msg in self.pubsub.listen():
            if msg['type'] != 'message':
                continue
            pkt = decode_message(msg['data'])
            threading.Thread(target=self.handle_packet, args=(pkt,), daemon=True).start()

    def handle_packet(self, pkt):
        mid = (pkt.get('from'), pkt.get('ts'))
        if mid in self.seen:
            return
        self.seen.add(mid)

        pkt['hops'] = pkt.get('hops', 0) + 1
        print(f"[{self.node_id}] Recibido {pkt['type']} de {pkt['from']} -> to {pkt['to']} hops {pkt['hops']}")

        # Si es para mi, procesar
        if pkt['to'] == self.node_id:
            print(f"[{self.node_id}] Mensaje DESTINO: {pkt['payload']}")
            return

        if any(h.get('ttl') for h in pkt.get('headers', [])):
            for h in pkt['headers']:
                if 'ttl' in h:
                    ttl = int(h['ttl'])
                    if ttl <= 0:
                        return
                    h['ttl'] = str(ttl - 1)

        # Reenviar a todos los vecinos excepto al que lo envió
        for n in self.neighbors:
            if n == pkt.get('from'):
                continue
            forward = dict(pkt)
            forward['from'] = self.node_id
            try:
                publish(self.r, n, forward)
                print(f"[{self.node_id}] Reenviado a {n}")
            except Exception as e:
                print(f"Error publicando a {n}: {e}")

    def send_message(self, dest, text):
        pkt = make_packet('message', self.node_id, dest, text, hops=0, headers=[{'ttl': '10'}])
        # En flooding se publican todos los vecinos
        for n in self.neighbors:
            publish(self.r, n, pkt)
        print(f"[{self.node_id}] Enviando mensaje '{text}' a {dest} vía flooding")

    def periodic_tasks(self):
        # flooding no requiere tareas periódicas, pero mantiene hilo vivo
        while True:
            time.sleep(5)

    def debug_print(self):
        print('Seen messages:', list(self.seen)[:10])

