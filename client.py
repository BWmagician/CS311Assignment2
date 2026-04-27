import socket
import threading
import sys
import time
import queue
import readchar
import os

debug = False
SERVER_IP = "127.0.0.1"
SERVER_PORT = 9000
USERNAME = ""
MAX_MESSAGE_LENGTH = 1 << 20

leave = False
PRINT_MESSAGE = queue.Queue()
SEND_MESSAGE = queue.Queue()
MESSAGE_ESCAPE = "*"
CODE_ESCAPE = "_"
END_ESCAPE = "\t"  # end sign of a message
ACK_INTERVAL = 4  # send ack per 4 seconds
TIMEOUT_LIMIT = 10
EXIT_CODE = 0  # 0=ctrl+c 1=abnormal exit


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
            print()  # add a empty line after each push
            self._render_prompt()  # rerender the user line

    def _input_loop(self):
        global leave
        global EXIT_CODE
        while not leave:
            try:
                ch = readchar.readchar()
            except KeyboardInterrupt:
                leave = True
                SEND_MESSAGE.put("__EXIT__")  # tell server I'm leaving
                EXIT_CODE = 0
                break

            if ch == "\x03":  # Ctrl+C
                leave = True
                SEND_MESSAGE.put("__EXIT__")
                print("\nExiting...")
                EXIT_CODE = 0
                break

            with self._lock:
                if ch == "\x03":
                    leave = True
                    SEND_MESSAGE.put("__EXIT__")  # tell server I'm leaving
                    break

                elif ch == readchar.key.ENTER:
                    if not self._buffer:  # nothing to sumbit
                        continue

                    msg = "".join(self._buffer)

                    self._clear_line()  # based on buffer
                    self._buffer.clear()

                    if msg.strip():
                        SEND_MESSAGE.put(MESSAGE_ESCAPE + msg)

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

        if debug:
            print("\033[48;5;136mDEBUG\033[0m Leaving UI")

    def _clear_line(self):
        col = os.get_terminal_size().columns
        clear_len = 2 + len(self._buffer)

        sys.stdout.write("\r\033[K")  # 清除该行

        for i in range(-1 + (clear_len // col) + 1 if ((clear_len % col) > 0) else 0):
            sys.stdout.write("\033[A")  # 光标上移一行
            sys.stdout.write("\r\033[K")  # 清除该行

        # print(
        #     "len is:",
        #     (clear_len // col) + 1 if ((clear_len % col) > 0) else 0,
        #     clear_len,
        #     col,
        # )

        # sys.stdout.write(
        #     "\r\033[K" * ((clear_len // col) + ((clear_len % col) > 0))
        # )  # clear a line

    def _render_prompt(self):
        sys.stdout.write("\r")
        sys.stdout.write(self._prompt + "".join(self._buffer))
        sys.stdout.flush()


def listen(sock):
    global leave
    global debug
    sock.settimeout(TIMEOUT_LIMIT)
    while True:
        global EXIT_CODE
        try:
            data = sock.recv(MAX_MESSAGE_LENGTH)
        except socket.timeout:
            leave = True
            EXIT_CODE = 2  # server is dead
            break

        if not data:
            break

        data = data.decode()

        if debug:
            PRINT_MESSAGE.put("\033[48;5;136mDEBUG\033[0m " + data)

        for msg in data.split(END_ESCAPE):
            if msg == "":
                continue

            escape = msg[0:1]  # extract the first character

            if escape == CODE_ESCAPE:
                if msg == "__KICK__":  # which means the server has kick client off
                    leave = True
                    print("You are offline now. Quiting the chatroom..")
                    EXIT_CODE = 1
                    exit(0)
                if msg == "__ACK__":
                    if debug:
                        PRINT_MESSAGE.put(
                            "\033[48;5;136mDEBUG\033[0m Recieved online ACK from server"
                        )

            elif escape == MESSAGE_ESCAPE:
                msg = msg[1:]
                # split by end signal
                for m in msg.split(END_ESCAPE):
                    if m.strip():
                        PRINT_MESSAGE.put(m)
            else:
                if debug:
                    PRINT_MESSAGE.put(
                        "\033[48;5;136mDEBUG\033[0m \033[48;5;196mMessage Corrupted\033[0m Received: "
                        + msg
                    )

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


def onlineACK(sock):
    while True:
        try:
            sock.send(("__ACK__").encode())
        except:
            break
        time.sleep(ACK_INTERVAL)


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
    global EXIT_CODE

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
        print("\033[48;5;213mCtrl+C\033[0m captured! Quit the chatroom.")
        exit(0)

    # username
    try:
        while True:
            USERNAME = ""
            while USERNAME == "":  # in case of empty name
                USERNAME = input("Enter your username: ")

            data = ""
            while (
                data != "__NAMEACCEPTED__" and data != "__NAMEREJECTED__"
            ):  # in case of corruption and TLE
                ## Send name to the server
                s.send(USERNAME.encode())
                try:
                    s.settimeout(2.0)  # in case of TLE
                    data = s.recv(1024).decode()
                except socket.timeout:
                    s.settimeout(None)  # calcel the special timeout limit
                    if debug:
                        print(
                            "\033[48;5;136mDEBUG\033[0m Timeout when receiving the name"
                        )
                if debug:
                    print(
                        "\033[48;5;136mDEBUG\033[0m Retransmission of name, received: "
                        + data
                    )
            s.settimeout(None)  # calcel the special timeout limit

            if data == "__NAMEACCEPTED__":
                break

            print(
                "Please enter your name again. This problem might occur because there is the same name in the chatroom."
            )

    except KeyboardInterrupt:
        print()
        print("\033[48;5;213mCtrl+C\033[0m captured! Quit the chatroom.")
        exit(0)

    threading.Thread(target=listen, args=(s,), daemon=True).start()
    threading.Thread(target=send, args=(s,), daemon=True).start()
    threading.Thread(target=onlineACK, args=(s,), daemon=True).start()

    ui = ChatUI()
    threading.Thread(target=write, args=(ui,), daemon=True).start()

    ui.start()  # main thraed

    if EXIT_CODE == 0:  # normal exit
        print("\033[48;5;213mCtrl+C\033[0m captured! Quit the chatroom!")
    elif EXIT_CODE == 1:  # server kicks you off
        print("You are now quiting the chatroom because the server kicks you off.")
    elif EXIT_CODE == 2:
        print("You are now quiting the chatroom because the server is dead.")

    s.close()
    leave = True


if __name__ == "__main__":
    main()
