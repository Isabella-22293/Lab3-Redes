import threading
import time
import heapq
from utils import make_packet, decode_message
from redis_client import publish

class LinkStateNode:
    def __init__(self, node_id, redis_conn, pubsub, neighbors, names):
        self.node_id = node_id
        self.r = redis_conn
        self.pubsub = pubsub
        self.neighbors = neighbors
        self.names = names

        self.lsdb = {}
        self.seq = 0

        self.pubsub.subscribe(self.node_id)
        self.lock = threading.Lock()

    def listen_loop(self):
        for msg in self.pubsub.listen():
            if msg['type'] != 'message':
                continue
            pkt = decode_message(msg['data'])
            threading.Thread(target=self.handle_packet, args=(pkt,), daemon=True).start()

    def handle_packet(self, pkt):
        ptype = pkt.get('type')
        if ptype == 'lsa':
            self._process_lsa(pkt)
            return
        if ptype == 'message':
            # route usando dijkstra
            dest = pkt['to']
            if dest == self.node_id:
                print(f"[{self.node_id}] Mensaje RECIBIDO: {pkt['payload']}")
                return
            next_hop = self._dijkstra_next_hop(dest)
            if not next_hop:
                print(f"[{self.node_id}] No ruta a {dest}")
                return
            forward = dict(pkt)
            forward['from'] = self.node_id
            publish(self.r, next_hop, forward)
            print(f"[{self.node_id}] Reenviado a {next_hop} para destino {dest}")

    def _process_lsa(self, pkt):
        origin = pkt['from']
        seq = int(pkt['headers'][0].get('seq', 0)) if pkt.get('headers') else 0
        neighbors = pkt.get('payload', [])
        with self.lock:
            cur = self.lsdb.get(origin)
            if (cur is None) or (seq > cur[0]):
                self.lsdb[origin] = (seq, neighbors)
                for n in self.neighbors:
                    if n == pkt.get('from'):
                        continue
                    forward = dict(pkt)
                    forward['from'] = self.node_id
                    publish(self.r, n, forward)
                print(f"[{self.node_id}] LSA actualizado de {origin}: seq={seq} neighbors={neighbors}")

    def send_message(self, dest, text):
        next_hop = self._dijkstra_next_hop(dest)
        if not next_hop:
            print(f"[{self.node_id}] No ruta a {dest}")
            return
        pkt = make_packet('message', self.node_id, dest, text, hops=0)
        pkt['from'] = self.node_id
        publish(self.r, next_hop, pkt)
        print(f"[{self.node_id}] Enviando a {dest} via {next_hop}")

    def periodic_tasks(self):
        while True:
            self.seq += 1
            pkt = make_packet('lsa', self.node_id, 'all', self.neighbors, hops=0, headers=[{'seq': str(self.seq)}])
            for n in self.neighbors:
                publish(self.r, n, pkt)
            time.sleep(5)

    def _build_graph(self):
        g = {}
        with self.lock:
            for origin, (seq, neigh) in self.lsdb.items():
                g[origin] = list(neigh)
            g.setdefault(self.node_id, list(self.neighbors))
        return g

    def _dijkstra_next_hop(self, dest):
        g = self._build_graph()
        if dest not in g:
            return None
        dist = {n: float('inf') for n in g}
        prev = {n: None for n in g}
        dist[self.node_id] = 0
        pq = [(0, self.node_id)]
        while pq:
            d,u = heapq.heappop(pq)
            if d>dist[u]:
                continue
            if u==dest:
                break
            for v in g.get(u, []):
                nd = d+1
                if nd < dist.get(v, float('inf')):
                    dist[v]=nd
                    prev[v]=u
                    heapq.heappush(pq,(nd,v))
        if dist[dest]==float('inf'):
            return None
        cur = dest
        prev_node = prev[cur]
        if prev_node is None:
            return None
        while prev_node != self.node_id:
            cur = prev_node
            prev_node = prev[cur]
            if prev_node is None:
                break
        return cur

    def debug_print(self):
        print('LSDB:', self.lsdb)
