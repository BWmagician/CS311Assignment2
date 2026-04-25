import socket
import threading

clients=[]
def broadcast(msg,sender):
    msg=msg.encode()
    for c,name in clients:
        if c!=sender:
            try:
                c.send(msg)
            except:
                c.close()
                clients.remove((c,name))


def handle(conn):
    name=conn.recv(1024).decode().strip()
    clients.append((conn,name))
    print("{} has joined the chatroom.".format(name))
    broadcast("{} has joined the chatroom!".format(name),conn)
    conn.send(f"Welcome {name} to the chatroom!".encode())
    while True:
        data=conn.recv(1024).strip()
        if not data:
            break
        msg=data.decode()
        if msg=="__EXIT__":
            print("{} has left the chatroom.".format(name))
            broadcast("{} has left the chatroom!".format(name),conn)
            break
        print("[*] {}: {}".format(name,msg))
        s="{}: {}".format(name,msg)
        broadcast(s,conn)
        conn.send(s.encode())
    conn.close()
    clients.remove((conn,name))
s = socket.socket()
s.bind(('127.0.0.1', 9000))
s.listen(10)
print('waiting for client...')
while True:
    conn, addr = s.accept()
    print('connected:', addr)
    t=threading.Thread(target=handle, args=(conn,))
    t.start()
s.close()