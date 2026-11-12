
import tkinter as tk
from tkinter import ttk
from pynput import keyboard
import threading

# ---------- SETTINGS ----------
DEFAULT_TOGGLE_KEY = "f6"
DEFAULT_REPEAT_KEY = "space"
DEFAULT_INTERVAL = 100
MIN_INTERVAL = 10

# ---------- STATE ----------
running = threading.Event()
shutdown = threading.Event()
state_lock = threading.Lock()

state = {
    "toggle_key": DEFAULT_TOGGLE_KEY,
    "repeat_key": DEFAULT_REPEAT_KEY,
    "capturing": None,
    "pressed": set(),
}

press_count = 0


def key_name(key):
    if isinstance(key, keyboard.Key):
        return key.name.lower()

    char = getattr(key, "char", None)
    if char:
        return char.lower()

    return str(key).lower()


def key_from_name(name):
    special = getattr(keyboard.Key, name, None)
    if special is not None:
        return special

    if len(name) == 1:
        return name

    raise ValueError(
        "Unsupported key. Try Space, Enter, F6, or a letter."
    )


def update_status():
    if running.is_set():
        status_label.config(text="RUNNING", foreground="green")
        toggle_button.config(text="Stop")
    else:
        status_label.config(text="STOPPED", foreground="red")
        toggle_button.config(text="Start")


def toggle_running():
    if running.is_set():
        running.clear()
    else:
        running.set()

    update_status()


def stop_running():
    running.clear()
    update_status()


def choose_key(which):
    with state_lock:
        state["capturing"] = which
        state["pressed"].clear()

    message_label.config(text="Press the key you want to use...")
    toggle_key_button.config(state="disabled")
    repeat_key_button.config(state="disabled")


def save_chosen_key(which, name):
    with state_lock:
        state[f"{which}_key"] = name
        state["capturing"] = None
        state["pressed"].clear()

    if which == "toggle":
        toggle_key_label.config(text=name.upper())
    else:
        repeat_key_label.config(text=name.upper())

    toggle_key_button.config(state="normal")
    repeat_key_button.config(state="normal")
    message_label.config(text="Key setting updated.")


def on_press(key):
    name = key_name(key)

    with state_lock:
        if name in state["pressed"]:
            return
        state["pressed"].add(name)

        capturing = state["capturing"]

        if capturing:
            selected = name
        else:
            selected = None
            toggle_key = state["toggle_key"]

    if selected is not None:
        root.after(
            0,
            lambda w=capturing, n=selected: save_chosen_key(w, n)
        )
        return

    if name == "esc":
        root.after(0, stop_running)
    elif name == toggle_key:
        root.after(0, toggle_running)


def on_release(key):
    with state_lock:
        state["pressed"].discard(key_name(key))


def repeat_worker():
    global press_count

    while not shutdown.is_set():
        if not running.wait(timeout=0.05):
            continue

        with state_lock:
            repeat_name = state["repeat_key"]

        try:
            key = key_from_name(repeat_name)
            keyboard_controller.press(key)
            keyboard_controller.release(key)

            press_count += 1
            root.after(
                0,
                lambda n=press_count: count_label.config(text=str(n))
            )

        except Exception as error:
            print("Key press error:", error)
            root.after(0, stop_running)
            continue

        try:
            interval = int(interval_entry.get())
        except (ValueError, tk.TclError):
            interval = DEFAULT_INTERVAL

        interval = max(MIN_INTERVAL, min(interval, 60000))

        # Wait in short intervals so Stop responds quickly.
        remaining = interval / 1000
        while remaining > 0 and running.is_set() and not shutdown.is_set():
            wait_time = min(remaining, 0.02)
            if shutdown.wait(wait_time):
                break
            remaining -= wait_time


def on_close():
    shutdown.set()
    running.clear()
    listener.stop()
    root.destroy()


# ---------- INTERFACE ----------
root = tk.Tk()
root.title("Keyboard Auto Presser")
root.geometry("390x410")
root.resizable(False, False)

tk.Label(
    root,
    text="Keyboard Auto Presser",
    font=("Arial", 18, "bold")
).pack(pady=15)

tk.Label(root, text="Toggle key (start / stop):").pack()

toggle_key_label = tk.Label(
    root, text=DEFAULT_TOGGLE_KEY.upper(),
    font=("Arial", 12, "bold")
)
toggle_key_label.pack()

toggle_key_button = ttk.Button(
    root,
    text="Choose toggle key",
    command=lambda: choose_key("toggle")
)
toggle_key_button.pack(pady=5)

tk.Label(root, text="Key to repeatedly press:").pack(pady=(10, 0))

repeat_key_label = tk.Label(
    root, text=DEFAULT_REPEAT_KEY.upper(),
    font=("Arial", 12, "bold")
)
repeat_key_label.pack()

repeat_key_button = ttk.Button(
    root,
    text="Choose key to repeat",
    command=lambda: choose_key("repeat")
)
repeat_key_button.pack(pady=5)

tk.Label(root, text="Interval in milliseconds:").pack(pady=(10, 0))

interval_entry = ttk.Entry(root, justify="center", width=12)
interval_entry.insert(0, str(DEFAULT_INTERVAL))
interval_entry.pack(pady=5)

toggle_button = ttk.Button(
    root, text="Start", command=toggle_running
)
toggle_button.pack(pady=10)

status_label = tk.Label(
    root, text="STOPPED",
    font=("Arial", 12, "bold"), foreground="red"
)
status_label.pack()

count_label = tk.Label(root, text="Key presses: 0")
count_label.pack(pady=5)

message_label = tk.Label(
    root, text="F6 starts/stops; Escape stops.",
    wraplength=350
)
message_label.pack(pady=5)

keyboard_controller = keyboard.Controller()

worker = threading.Thread(target=repeat_worker, daemon=True)
worker.start()

listener = keyboard.Listener(
    on_press=on_press,
    on_release=on_release
)
listener.start()

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
