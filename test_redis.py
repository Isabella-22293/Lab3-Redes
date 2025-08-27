from redis_client import get_redis, publish, get_pubsub
import threading

def listen():
    r = get_redis()
    ps = get_pubsub(r)
    ps.subscribe("test_channel")
    print("Escuchando en test_channel...")
    for msg in ps.listen():
        if msg["type"] == "message":
            print("Recibido:", msg["data"].decode())

def main():
    # Inicia un hilo para escuchar
    t = threading.Thread(target=listen, daemon=True)
    t.start()

    r = get_redis()
    # Enviar mensaje de prueba
    publish(r, "test_channel", {"msg": "Hola desde nodo"})
    print("Mensaje publicado en test_channel")

if __name__ == "__main__":
    main()
