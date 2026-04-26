import socket
import threading
import sys
import time
import queue
import readchar

SERVER_IP = "127.0.0.1"
SERVER_PORT = 9000
USERNAME = ""
MAX_MESSAGE_LENGTH = 1 << 20

leave = False
PRINT_MESSAGE = queue.Queue()
SEND_MESSAGE = queue.Queue()

END_ESCAPE = "\t"  # end sign of a message

theme_color = 28  # preferred color
theme_color2 = 18  # preferred color 2
theme_color3 = 12  # preferred color 3

color_pairs = [
    "\033[38;5;196m",  # vivid red
    "\033[38;5;197m",  # strong red
    "\033[38;5;198m",  # deep pink-red
    "\033[38;5;199m",  # pinkish red
    "\033[38;5;200m",  # magenta-red
    "\033[38;5;201m",  # bright magenta
    "\033[38;5;202m",  # red-orange
    "\033[38;5;203m",  # warm orange-red
    "\033[38;5;204m",  # coral
    "\033[38;5;205m",  # pink-orange
    "\033[38;5;206m",  # light magenta-pink
    "\033[38;5;208m",  # pure orange
    "\033[38;5;209m",  # light orange
    "\033[38;5;210m",  # peach
    "\033[38;5;211m",  # soft pink
    "\033[38;5;212m",  # pale pink
    "\033[38;5;214m",  # golden orange
    "\033[38;5;215m",  # warm golden
    "\033[38;5;216m",  # sand
    "\033[38;5;217m",  # light salmon
    "\033[38;5;218m",  # pastel pink
    "\033[38;5;220m",  # yellow
    "\033[38;5;221m",  # light yellow
    "\033[38;5;222m",  # pale yellow
    "\033[38;5;223m",  # cream
    "\033[38;5;190m",  # yellow-green
    "\033[38;5;154m",  # light green
    "\033[38;5;118m",  # bright green
    "\033[38;5;82m",  # vivid green
    "\033[38;5;46m",  # pure green
]


def coloring(x, k):
    global color_pairs
    return color_pairs[k] + x + "\033[0m"


# ================= UI =================
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
            self._clear_line()  # clear the user line
            if msg == f"Welcome {USERNAME} to the chatroom!":
                print(f"Welcome {coloring(USERNAME, theme_color3)} to the chatroom!")
            elif msg[: len(USERNAME)] == USERNAME:
                print(coloring(USERNAME, theme_color3) + msg[len(USERNAME) :])
            else:
                print(msg)
            self._render_prompt()  # rerender the user line

    def _input_loop(self):
        global leave
        while not leave:
            try:
                ch = readchar.readchar()
            except KeyboardInterrupt:
                leave = True
                SEND_MESSAGE.put("__EXIT__")  # tell server I'm leaving

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

                # normal characters
                else:
                    self._buffer.append(ch)
                    sys.stdout.write(ch)
                    sys.stdout.flush()
        print("READCHAR break")

    def _clear_line(self):
        sys.stdout.write("\r\033[K")  # clear a line

    def _render_prompt(self):
        sys.stdout.write("\r")
        sys.stdout.write(self._prompt + "".join(self._buffer))
        sys.stdout.flush()


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

            # split by end signal
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


def enter_prompt1():
    global SERVER_IP
    global SERVER_PORT
    global theme_color
    global theme_color2
    print(
        f"Enter Server {coloring('IP', theme_color)} (press Enter to use default configuration {coloring(SERVER_IP, theme_color)}):",
        end=" ",
    )
    x = input()
    if x != "":
        SERVER_IP = x
    while True:
        try:
            print(
                f"Enter Server {coloring('PORT', theme_color2)} (press Enter to use default configuration {coloring(str(SERVER_PORT), theme_color2)}):",
                end=" ",
            )
            x = input()
            if x != "":
                SERVER_PORT = int(x)
            break
        except ValueError:
            print("Please use \033[48;5;213mINT\033[0m type input!")
    print(
        f"Your setting now is {coloring(SERVER_IP, theme_color)}:{coloring(str(SERVER_PORT), theme_color2)}"
    )


def main():

    global leave
    global theme_color
    global theme_color2
    global SERVER_IP
    global SERVER_PORT
    global USERNAME

    try:
        while True:
            SERVER_IP = "127.0.0.1"
            SERVER_PORT = 9000
            enter_prompt1()

            s = socket.socket()
            print("Prepare to connect...")

            try:
                s.connect((SERVER_IP, SERVER_PORT))
                break
            except ConnectionRefusedError:
                print("\033[48;5;196mFailed to connect to server!\033[0m")
            except (OSError, OverflowError, ValueError):
                print("\033[48;5;196mWrong format!\033[0m")

        print(
            f"\033[48;5;35mConnected to server\033[0m {coloring(SERVER_IP, theme_color)}:{coloring(str(SERVER_PORT), theme_color2)}"
        )
    except KeyboardInterrupt:
        print()
        print("\033[48;5;213mCtrl+C\033[0m captured! Quit the code。")
        exit(0)

    # username
    USERNAME = input("Enter your username: ")
    s.send((USERNAME + END_ESCAPE).encode())

    threading.Thread(target=listen, args=(s,), daemon=True).start()
    threading.Thread(target=send, args=(s,), daemon=True).start()

    ui = ChatUI()
    threading.Thread(target=write, args=(ui,), daemon=True).start()

    ui.start()  # main thraed

    s.close()
    leave = True


if __name__ == "__main__":
    main()
