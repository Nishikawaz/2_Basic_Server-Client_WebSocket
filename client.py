import socket
import threading
import time 

# Configuración global
IP = "127.0.0.1"
PORT = 6869
BUFFER = 1024
DELAY = 3

# Socket actual del cliente (Con global se gestionan cambios a la variable de scope mayor)
socket_client = None

# Variable bandera para saber si se da el cierre al programa
closing = False

# Configuración del username
NAME = input("Username: ")

# Función de conexión del cliente
def client_connect():
    global socket_client

    while socket_client is None and not closing:
        # Se trabaja sobre una variable local y recién se publica en la global
        # DESPUÉS de que connect() haya salido bien. Si se asignara antes, el hilo
        # principal vería socket_client != None y llamaría a sendall() sobre un
        # socket todavía sin conectar.
        nuevo_socket = None
        try:
            nuevo_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            nuevo_socket.connect((IP, PORT))
            socket_client = nuevo_socket
            print(f"[SISTEMA] Conectado al server: \nIP:{IP} \nPORT:{PORT}")
            return socket_client
        # ConnectionRefusedError es subclase de OSError, así que un solo handler alcanza
        except OSError:
            # Cerrar el socket fallido: sin esto cada reintento filtra un descriptor
            if nuevo_socket is not None:
                nuevo_socket.close()
            if not closing:
                print(f"[SISTEMA] No se pudo conectar. Reintentando en {DELAY} segundos")
                time.sleep(DELAY)

# Función de desconexión del cliente
def client_disconnect():
    global socket_client

    # Si NO es indicado como None (inicialmente) lo desconecta
    if socket_client is not None:
        try:
            socket_client.close()
        except OSError:
            print(f"Error al cerrar la conexión del cliente")

        socket_client = None

# Función de recepción de mensajes
def receive_messages():
    global socket_client

    while True:
        if closing: # Si se está cerrando, sale del loop. Así se entiende que el hilo muere
            break
        if socket_client is None: # Si no hay conexión activa, trata de conectarse siempre y cuando no quiera cerrarse
            client_connect()
            continue
        try:
            message = socket_client.recv(BUFFER)
            if not message:
                raise ConnectionError # Forzamos una excepción porque llega vacío
            print(message.decode("utf-8"))
        except (ConnectionError, OSError):
            if closing: # Si closing True, desconexión directa. 
                break
            print("[SISTEMA] Se perdió la conexión con el server")
            client_disconnect() # Desconexión forzada
            time.sleep(DELAY)

# Función de mecánica principal del lado del cliente:
# 1) Hilo receptor: Hilo secundario de escucha/recibe mensajes del server
# 2) Hilo de Loop de envío: Lectura de inputs para mandarlos
def client_ON(): # El hilo se procesa implícitamente al hacer la ejecución de esta función
    global closing

    receiving_thread = threading.Thread(target=receive_messages, daemon=True) # Si muere el hilo principal, muere el secundario (para no dejarlo colgado)
    receiving_thread.start()

    while True: # Ya que aplica while true, nunca terminaría la verificación sin el daemon=True
        try:
            text = input() # Bloqueante, entonces se debe aplicar un hilo secundario
            if socket_client is None:
                print("Sin conexión")
                continue
            message = f"{NAME}: {text}".encode("utf-8")
            socket_client.sendall(message)

        except OSError:
            if not closing:
                print("Error al enviar el mensaje")
            client_disconnect()
        except KeyboardInterrupt:
            print("Cliente desconectado manualmente")

            closing = True # Indica desconexión a todos los hilos (global para ambos hilos)
            client_disconnect()
            receiving_thread.join(timeout=1) # Tiempo de espera del hilo secundario
            break

# Se "corre" el cliente
client_ON()