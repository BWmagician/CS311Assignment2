import socket
import threading
import sys
import time
import queue
import readchar
import random
from volcenginesdkarkruntime import Ark

client = Ark(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key="ark-86aa00ce-f99f-4f7f-b189-95dddbb55f88-d09df" 
)

def call_llm(user_msg):
    try:
        completion = client.chat.completions.create(
            model="ep-20260425193209-7bjq2", 
            messages=[
                {"role": "system", "content": "You are a chat user, speaking briefly and naturally, without formal responses, like a real person chatting in English. You can主动聊一聊 about school life."},
                {"role": "user", "content": user_msg}
            ]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        PRINT_MESSAGE.put(f"\033[31m[AI Error]\033[0m {e}")
        return None

SERVER_IP = "127.0.0.1"
SERVER_PORT = 9000
USERNAME = ""
MAX_MESSAGE_LENGTH = 1 << 20

leave = False
PRINT_MESSAGE = queue.Queue()
SEND_MESSAGE = queue.Queue()
AI_INBOX = queue.Queue()  

END_ESCAPE = "\t"  

theme_color = 28
theme_color2 = 18
theme_color3 = 12

color_pairs = [
    "\033[38;5;196m", "\033[38;5;197m", "\033[38;5;198m", "\033[38;5;199m",
    "\033[38;5;200m", "\033[38;5;201m", "\033[38;5;202m", "\033[38;5;203m",
    "\033[38;5;204m", "\033[38;5;205m", "\033[38;5;206m", "\033[38;5;208m",
    "\033[38;5;209m", "\033[38;5;210m", "\033[38;5;211m", "\033[38;5;212m",
    "\033[38;5;214m", "\033[38;5;215m", "\033[38;5;216m", "\033[38;5;217m",
    "\033[38;5;218m", "\033[38;5;220m", "\033[38;5;221m", "\033[38;5;222m",
    "\033[38;5;223m", "\033[38;5;190m", "\033[38;5;154m", "\033[38;5;118m",
    "\033[38;5;82m", "\033[38;5;46m",
]

def coloring(x, k):
    global color_pairs
    return color_pairs[k] + x + "\033[0m"

class ChatUI:
    def __init__(self):
        self._running = False
        self._lock = threading.Lock()
        self._buffer = []
        self._prompt = coloring("> ", theme_color3)

    def start(self):
        self._running = True
        self._input_loop()

    def push_message(self, msg):
        with self._lock:
            self._clear_line()
            if msg == f"Welcome {USERNAME} to the chatroom!":
                print(f"Welcome {coloring(USERNAME, theme_color3)} to the chatroom!")
            elif msg.startswith(USERNAME + ":"):
                print(coloring(USERNAME, theme_color3) + msg[len(USERNAME) :])
            else:
                print(msg)
            self._render_prompt()

    def _input_loop(self):
        global leave
        while not leave:
            try:
                ch = readchar.readchar()
            except KeyboardInterrupt:
                leave = True
                SEND_MESSAGE.put("__EXIT__")
                import os
                os._exit(0)
            if ch == '\x03':
                leave = True
                SEND_MESSAGE.put("__EXIT__")
                print("\nExiting...")

            with self._lock:
                if ch == readchar.key.ENTER:
                    msg = "".join(self._buffer)
                    self._buffer.clear()
                    self._clear_line()
                    if msg.strip():
                        SEND_MESSAGE.put(msg)
                    self._render_prompt()
                elif ch == readchar.key.BACKSPACE:
                    if self._buffer:
                        self._buffer.pop()
                        self._clear_line()
                        self._render_prompt()
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

def listen(sock):
    global leave
    while True:
        try:
            data = sock.recv(MAX_MESSAGE_LENGTH)
            if not data: break
            msg = data.decode()
            for m in msg.split(END_ESCAPE):
                if m.strip():
                    PRINT_MESSAGE.put(m)
                    AI_INBOX.put(m) 
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
        if leave: break

def ai_worker():
    global leave
    time.sleep(2) 
    welcome_reply = call_llm("我在聊天室上线了，跟大家打个简短的招呼")
    if welcome_reply:
        SEND_MESSAGE.put(welcome_reply)

    while not leave:
        msg = AI_INBOX.get()
        
        if ":" not in msg:
            continue
            
        try:
            sender, content = msg.split(":", 1)
            sender = sender.strip()
            content = content.strip()

            if sender == USERNAME or "Welcome" in msg:
                continue
            
            reply = call_llm(content)
            if reply:
                time.sleep(random.uniform(1.5, 4.0))
                SEND_MESSAGE.put(reply)
        except Exception:
            continue

def enter_prompt1():
    global SERVER_IP, SERVER_PORT
    print(f"Enter Server {coloring('IP', theme_color)} (press Enter for {coloring(SERVER_IP, theme_color)}):", end=" ")
    x = input()
    if x != "": SERVER_IP = x
    while True:
        try:
            print(f"Enter Server {coloring('PORT', theme_color2)} (press Enter for {coloring(str(SERVER_PORT), theme_color2)}):", end=" ")
            x = input()
            if x != "": SERVER_PORT = int(x)
            break
        except ValueError:
            print("Please use \033[48;5;213mINT\033[0m type input!")

def main():
    global leave, USERNAME, SERVER_IP, SERVER_PORT

    try:
        while True:
            enter_prompt1()
            s = socket.socket()
            print("Prepare to connect...")
            try:
                s.connect((SERVER_IP, SERVER_PORT))
                break
            except Exception:
                print("\033[48;5;196mFailed to connect!\033[0m")
        print(f"\033[48;5;35mConnected to\033[0m {SERVER_IP}:{SERVER_PORT}")
    except KeyboardInterrupt:
        exit(0)

    USERNAME = input("Enter your username: ")
    s.send((USERNAME + END_ESCAPE).encode())

    threading.Thread(target=listen, args=(s,), daemon=True).start()
    threading.Thread(target=send, args=(s,), daemon=True).start()
    
    ui = ChatUI()
    threading.Thread(target=write, args=(ui,), daemon=True).start()

    threading.Thread(target=ai_worker, daemon=True).start()

    ui.start() 

    s.close()
    leave = True

if __name__ == "__main__":
    main()
