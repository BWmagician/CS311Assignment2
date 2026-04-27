import socket
import threading

clients = []
debug = True
CODE_ESCAPE = "_"
MESSAGE_ESCAPE = "*"


def broadcast(msg, sender):
    msg = msg.encode()
    global clients
    global debug
    for c, name in clients:
        if c != sender:
            try:
                ##############DEBUG#############
                if debug:
                    print(
                        "\033[48;5;136mDEBUG\033[0m Send "
                        + msg.decode()
                        + " to "
                        + name
                    )
                ##############DEBUG#############
                c.send(msg)
            except:
                ##############DEBUG#############
                if debug:
                    print("\033[48;5;136mDEBUG\033[0m " + msg.decode())
                ##############DEBUG#############
                c.close()
                clients.remove((c, name))


def handle(conn):
    global debug
    global clients
    name = conn.recv(1024).decode().strip()
    clients.append((conn, name))
    print("{} has joined the chatroom.".format(name))
    broadcast("{}{} has joined the chatroom!".format(MESSAGE_ESCAPE, name), conn)
    conn.send(f"{MESSAGE_ESCAPE}Welcome {name} to the chatroom!".encode())
    while True:
        try:
            data = conn.recv(1024).strip()
        except socket.timeout:  # say the client is offline, kick it off automatically
            conn.send("__KICK__")
            break
        if not data:
            break
        msg = data.decode()
        if msg[0:1] == CODE_ESCAPE:  # code escape _
            if msg == "__EXIT__":
                print("{} has left the chatroom.".format(name))
                broadcast("{} has left the chatroom!".format(name), conn)
                break

            ## DEBUG
            if msg == "__ACK__":
                if debug:
                    print(f"\033[48;5;136mDEBUG\033[0m Recieved online ACK from {name}")

        elif msg[0:1] == MESSAGE_ESCAPE:  # message escape *
            msg = msg[1:]  # drop the escape
            print("[*] {}: {}".format(name, msg))
            s = "{}{}: {}".format(MESSAGE_ESCAPE, name, msg)

            if debug:
                print("\033[48;5;136mDEBUG\033[0m " + s)

            broadcast(s, conn)
            conn.send(s.encode())
        else:
            print("\033[48;5;196mMessage Corrupted.\033[0m. Received: " + msg)
    conn.close()
    clients.remove((conn, name))


s = socket.socket()
s.bind(("127.0.0.1", 9000))
s.listen(10)
print("waiting for client...")
while True:
    conn, addr = s.accept()
    print("connected:", addr)
    t = threading.Thread(target=handle, args=(conn,))
    t.start()
s.close()
