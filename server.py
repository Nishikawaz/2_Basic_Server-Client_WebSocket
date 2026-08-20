import socket
import select

IP = "127.0.0.1"
PORT = 6869
BUFFER = 1024
SOCKETS = [] 

# Función de configuración del server
def setup_server(ip, port):
    try:
        socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Ignora el TimeWait del SO 
        socket_server.bind((ip, port))
        socket_server.listen()
        socket_server.setblocking(False) # Si no hay nada, lanza excepción (no bloquea para esperar)
        print(f"[SISTEMA] Servidor configurado y en modo escucha \nIP: {ip} \nPORT: {port}")
        return socket_server
    except OSError as e:
        print(f"Error al configurar servidor: {e}")
        exit(1)

# Función en donde se acepta a un cliente luego de haber configurado el server
def accept_client(socket_server):
    try:
        (socket_client, client_address) = socket_server.accept()
        socket_client.setblocking(False) # Si no hay nada, lanza excepción (no bloquea para esperar)
        SOCKETS.append(socket_client)
        print(f"[SERVER] Nueva conexión: {client_address[0]}:{client_address[1]}")
    except Exception as e:
        print(f"Error al aceptar conexión: {e}")

# Función de desconexión
def disconnect(socket_client):
    if socket_client in SOCKETS:
        SOCKETS.remove(socket_client)
    try:
        socket_client.close()
    except:
        pass
    print(f"[SERVER] Cliente desconectado")

# Función de mensaje masivo/broadcast
def broadcast(message, socket_sender, socket_server):
    # Se itera sobre una COPIA de la lista: disconnect() hace SOCKETS.remove(),
    # y mutar la lista mientras se la recorre saltea elementos silenciosamente.
    for sock in list(SOCKETS):
        # No enviar al remitente ni al propio socket del servidor
        if sock != socket_sender and sock != socket_server:
            try:
                # sendall y no send: send() puede escribir menos bytes de los pedidos
                # y dejar el mensaje truncado del lado del receptor.
                sock.sendall(message)
            except OSError:
                disconnect(sock)

# Función de gestión de acciones del cliente
def client_management(socket_client, socket_server):
    try: 
        message = socket_client.recv(BUFFER)
        if not message:
            disconnect(socket_client) # Si no le llegan mensajes, lo desconecta
            return

        # Intenta decodificar solo para el log, pero manejar el error si falla
        try:
            print(f"[LOG] {message.decode('utf-8').strip()}")
        except:
            print(f"[LOG] Mensaje recibido (formato no UTF-8)")
            
        broadcast(message, socket_client, socket_server)
        
    except Exception:
        disconnect(socket_client)

# Función de mecánica principal de manejo del servidor
def server_on(socket_server):
    SOCKETS.append(socket_server) # Se añade el server a la lista de Sockets a ser evaluados en la lista
    print("[SISTEMA] El protocolo de comunicación se ha instanciado")

    try:
        while True:
            # Select monitorea qué socket tiene datos para leer
            ready, _, _ = select.select(SOCKETS, [], [])
            for sock in ready:
                if sock == socket_server:
                    accept_client(socket_server) # Si el socket evaluado de la lista es el server: se encarga de aceptar clientes
                else:
                    client_management(sock, socket_server) # Si el socket evaluado es un cliente, envía mensajes o gestiona la esconexión

    except KeyboardInterrupt:
        print("\n[SISTEMA] Apagando el servidor de forma manual")
    finally:
        for sock in list(SOCKETS):
            sock.close()
        SOCKETS.clear()


# Se inicializa el server
if __name__ == "__main__":
    socket_server = setup_server(IP, PORT)
    server_on(socket_server)