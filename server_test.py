import socket
import threading
import time

namebook = []
clients = []
debug = False
CODE_ESCAPE = "_"
MESSAGE_ESCAPE = "*"
END_ESCAPE = "\t"
ACK_INTERVAL = 4
TIMEOUT_LIMIT = 10


def onlineACK(sock):
    while True:
        try:
            sock.send(("__ACK__" + END_ESCAPE).encode())
        except:
            break
        time.sleep(ACK_INTERVAL)


def broadcast(msg, sender):
    msg = msg.encode()
    global clients
    global debug
    global namebook
    for c, name in clients:
        if c != sender:
            try:
                if debug:
                    print(
                        "\033[48;5;136mDEBUG\033[0m Send "
                        + msg.decode()
                        + " to "
                        + name
                    )
                c.send(msg)
            except:
                if debug:
                    print("\033[48;5;136mDEBUG\033[0m " + msg.decode())
                c.close()
                clients.remove((c, name))
                namebook.remove(name)


def handle(conn):
    global debug
    global clients
    global namebook

    while True:
        name = conn.recv(1024).decode().strip()
        if debug:
            print(
                f"\033[48;5;136mDEBUG\033[0m Received a name called \033[34m{name}\033[0m"
            )
        if name not in namebook:
            conn.send(("__NAMEACCEPTED__").encode())
            if debug:
                print("\033[48;5;136mDEBUG\033[0m Send ACCEPTANCE to the client")
            namebook.append(name)
            break
        else:
            if debug:
                print("\033[48;5;136mDEBUG\033[0m The namebook is", namebook)
            conn.send(("__NAMEREJECTED__").encode())

    threading.Thread(target=onlineACK, args=(conn,)).start()

    # conn.send(("__KICK__" + END_ESCAPE).encode())

    conn.settimeout(TIMEOUT_LIMIT)  # set a time limit
    clients.append((conn, name))
    print("{} has joined the chatroom.".format(name))
    broadcast("{}{} has joined the chatroom!".format(MESSAGE_ESCAPE, name), conn)
    conn.send(f"{MESSAGE_ESCAPE}Welcome {name} to the chatroom!{END_ESCAPE}".encode())
    while True:
        try:
            data = conn.recv(1024).strip()
        except socket.timeout:  # say the client is offline, kick it off automatically
            if debug:
                print("\033[48;5;136mDEBUG\033[0m  Send __KICK__ to " + name)
            conn.send(("__KICK__" + END_ESCAPE).decode())
            break
        if not data:
            break
        msg = data.decode()
        if msg[0:1] == CODE_ESCAPE:  # code escape _
            if msg == "__EXIT__":
                print("{} has left the chatroom.".format(name))
                broadcast(
                    "{} has left the chatroom!{}".format(
                        MESSAGE_ESCAPE + name, END_ESCAPE
                    ),
                    conn,
                )
                break

            ## DEBUG
            if msg == "__ACK__":
                if debug:
                    print(f"\033[48;5;136mDEBUG\033[0m Recieved online ACK from {name}")

        elif msg[0:1] == MESSAGE_ESCAPE:  # message escape *
            msg = msg[1:]  # drop the header escape
            print("[*] {}: {}".format(name, msg))
            s = "{}{}: {}".format(MESSAGE_ESCAPE, name, msg + END_ESCAPE)

            if debug:
                print("\033[48;5;136mDEBUG\033[0m " + s)

            broadcast(s, conn)
            conn.send(s.encode())
        else:
            print("\033[48;5;196mMessage Corrupted\033[0m Received: " + msg)
    conn.close()
    clients.remove((conn, name))
    namebook.remove(name)
    if debug:
        print("\033[48;5;136mDEBUG\033[0m Remove " + name + " from the name book")


s = socket.socket()
s.bind(("127.0.0.1", 9000))
s.listen(10)
print("waiting for client...")
while True:
    conn, addr = s.accept()
    print("connected:", addr)
    threading.Thread(target=handle, args=(conn,)).start()

s.close()
