import socket
import threading
import sys
import time
import queue
import msvcrt   # ✅ Windows 输入

SERVER_IP = "127.0.0.1"
SERVER_PORT = 9000
MAX_MESSAGE_LENGTH = 1 << 20

leave = False
PRINT_MESSAGE = queue.Queue()
SEND_MESSAGE = queue.Queue()

END_ESCAPE = "\t"   # 消息分隔符


# ================= UI =================
class ChatUI:
    def __init__(self):
        self._running = False
        self._lock = threading.Lock()
        self._buffer = []
        self._prompt = "> "

    def start(self):
        self._running = True

        # 输入线程
        threading.Thread(target=self._input_loop, daemon=True).start()

        self._render_prompt()

        while self._running:
            time.sleep(0.05)

    def stop(self):
        self._running = False

    def push_message(self, msg):
        with self._lock:
            self._clear_line()
            print(msg)
            self._render_prompt()

    def _input_loop(self):
        while self._running:
            ch = msvcrt.getch()

            try:
                ch = ch.decode()
            except:
                continue

            with self._lock:
                # Enter
                if ch == "\r":
                    msg = "".join(self._buffer)
                    self._buffer.clear()

                    self._clear_line()

                    if msg.strip():
                        SEND_MESSAGE.put(msg)

                    self._render_prompt()

                # Backspace
                elif ch == "\x08":
                    if self._buffer:
                        self._buffer.pop()
                        self._render_prompt()

                # Ctrl+C
                elif ch == "\x03":
                    self.stop()
                    SEND_MESSAGE.put("__EXIT__")
                    break

                # 普通字符
                else:
                    self._buffer.append(ch)
                    sys.stdout.write(ch)
                    sys.stdout.flush()

    def _clear_line(self):
        sys.stdout.write("\r\033[K")

    def _render_prompt(self):
        sys.stdout.write("\r")
        sys.stdout.write(self._prompt + "".join(self._buffer))
        sys.stdout.flush()


# ================= 网络 =================

def importantPrint(x):
    print("\n" + len(x) * "*")
    print(x)
    print(len(x) * "*" + "\n")


def listen(sock):
    global leave
    while True:
        try:
            data = sock.recv(MAX_MESSAGE_LENGTH)
            if not data:
                break

            msg = data.decode()

            # 按协议拆分
            for m in msg.split(END_ESCAPE):
                if m.strip():
                    PRINT_MESSAGE.put(m)

        except:
            break

    leave = True
    PRINT_MESSAGE.put("Disconnected from server.")


def send(sock):
    global leave
    while True:
        msg = SEND_MESSAGE.get()
        try:
            sock.send((msg + END_ESCAPE).encode())
        except:
            break


def write(ui):
    global leave
    while True:
        msg = PRINT_MESSAGE.get()
        ui.push_message(msg)

        if leave:
            break


# ================= 主程序 =================

def main():
    global leave

    s = socket.socket()
    print("Prepare to connect...")

    s.connect((SERVER_IP, SERVER_PORT))

    importantPrint(f"Connected to server {SERVER_IP}:{SERVER_PORT}")

    # 输入用户名
    username = input("Enter your username: ")
    s.send((username + END_ESCAPE).encode())

    # 启动线程
    threading.Thread(target=listen, args=(s,), daemon=True).start()
    threading.Thread(target=send, args=(s,), daemon=True).start()

    ui = ChatUI()
    threading.Thread(target=write, args=(ui,), daemon=True).start()

    ui.start()

    time.sleep(0.5)
    s.close()


if __name__ == "__main__":
    main()