import socket
import threading
import sys
import time
import queue
import msvcrt
import random

from volcenginesdkarkruntime import Ark
import os

client = Ark(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key="ark-86aa00ce-f99f-4f7f-b189-95dddbb55f88-d09df"
)


def call_llm(user_msg):
    try:
        completion = client.chat.completions.create(
            model="ep-20260425193209-7bjq2",
            messages=[
                {"role": "system", "content": "你是一个聊天用户，说话简短自然，不要正式回答"},
                {"role": "user", "content": user_msg}
            ]
        )

        return completion.choices[0].message.content.strip()

    except Exception as e:
        PRINT_MESSAGE.put(f"[AI error] {e}")
        return None


# ===================== 基础配置 =====================

SERVER_IP = "127.0.0.1"
SERVER_PORT = 9000
MAX_MESSAGE_LENGTH = 1 << 20

END_ESCAPE = "\t"

leave = False

PRINT_MESSAGE = queue.Queue()
AI_MESSAGE = queue.Queue()
SEND_MESSAGE = queue.Queue()

USERNAME = ""


# ===================== UI =====================

class ChatUI:
    def __init__(self):
        self._running = False
        self._lock = threading.Lock()
        self._buffer = []
        self._prompt = "> "

    def start(self):
        self._running = True
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

                # Ctrl+C（唯一退出方式）
                elif ch == "\x03":
                    global leave
                    leave = True
                    SEND_MESSAGE.put("__EXIT__")  # 通知发送线程
                    self.stop()
                    return

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


# ===================== 网络 =====================

def listen(sock):
    global leave

    while not leave:
        try:
            data = sock.recv(MAX_MESSAGE_LENGTH)
            if not data:
                break

            msg = data.decode()

            for m in msg.split(END_ESCAPE):
                if m.strip():
                    PRINT_MESSAGE.put(m)
                    AI_MESSAGE.put(m)

        except:
            break

    leave = True
    PRINT_MESSAGE.put("Disconnected from server.")


def send(sock):
    global leave

    while not leave:
        msg = SEND_MESSAGE.get()

        if msg == "__EXIT__":
            try:
                sock.close()
            except:
                pass
            break

        try:
            sock.send((msg + END_ESCAPE).encode())
        except:
            break


def write(ui):
    global leave

    while not leave:
        msg = PRINT_MESSAGE.get()
        ui.push_message(msg)


# ===================== AI线程 =====================

def ai_worker():
    global leave

    print("[AI THREAD STARTED]")

    while not leave:
        msg = AI_MESSAGE.get()

        if ":" not in msg:
            continue

        try:
            sender, content = msg.split(":", 1)
        except:
            continue

        sender = sender.strip()
        content = content.strip()

        if sender == USERNAME:
            continue

        if not content:
            continue

        reply = call_llm(content)

        if reply:
            time.sleep(random.uniform(1.0, 2.5))
            SEND_MESSAGE.put(reply)


# ===================== 主程序 =====================

def main():
    global USERNAME, leave

    s = socket.socket()
    print("Connecting...")

    s.connect((SERVER_IP, SERVER_PORT))
    print("Connected.")

    USERNAME = input("Enter username: ")
    s.send((USERNAME + END_ESCAPE).encode())

    threading.Thread(target=listen, args=(s,), daemon=True).start()
    threading.Thread(target=send, args=(s,), daemon=True).start()

    ui = ChatUI()
    threading.Thread(target=write, args=(ui,), daemon=True).start()
    threading.Thread(target=ai_worker, daemon=True).start()

    try:
        ui.start()
    except KeyboardInterrupt:
        leave = True
        try:
            s.close()
        except:
            pass


if __name__ == "__main__":
    main()