import idaapi
import ida_kernwin
import time
import uuid
import requests
import threading
import json
import os

SERVER_URL = "https://idontknowlol.pythonanywhere.com/time"
PING_INTERVAL = 120
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "touchgrass.cfg")


def loadconfig():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def saveconfig(data):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        ida_kernwin.msg(f"[touchgrass] failed to save config: {e}\n")


class timetracker:
    def __init__(self, user_id, username):
        self.user_id = user_id
        self.username = username
        self.start_time = None
        self._stop_flag = True
        self._thread = None

    def start(self):
        if not self._stop_flag:
            ida_kernwin.msg("[touchgrass] already tracking.\n")
            return
        self.start_time = time.time()
        self._stop_flag = False
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        ida_kernwin.msg(f"[touchgrass] started tracking as {self.username}.\n")

    def stop(self):
        if self._stop_flag:
            ida_kernwin.msg("[touchgrass] already not tracking.\n")
            return
        self._stop_flag = True
        elapsed = time.time() - self.start_time
        self._send(elapsed, closing=True)
        ida_kernwin.msg(f"[touchgrass] stopped tracking: {elapsed:.1f}s\n")

    def _worker(self):
        while not self._stop_flag:
            time.sleep(PING_INTERVAL)
            elapsed = time.time() - self.start_time
            self._send(elapsed)

    def _send(self, elapsed, closing=False):
        try:
            data = {
                "user_id": self.user_id,
                "username": self.username,
                "elapsed": elapsed,
                "closing": closing,
            }
            requests.post(SERVER_URL, json=data, timeout=2)
        except Exception as e:
            ida_kernwin.msg(f"[touchgrass] error: {e}\n")


class TouchGrassAction(ida_kernwin.action_handler_t):
    def __init__(self, tracker):
        super().__init__()
        self.tracker = tracker

    def activate(self, ctx):
        if self.tracker._stop_flag:
            self.tracker.start()
        else:
            self.tracker.stop()
        return 1

    def update(self, ctx):
        return ida_kernwin.AST_ENABLE_ALWAYS


class touchgrass_plugmod_t(idaapi.plugmod_t):
    def __init__(self, tracker):
        self.tracker = tracker
        self._register_action()
        self.tracker.start()

    def _register_action(self):
        action_name = "touchgrass:toggle"
        action_label = "touchgrass"
        if not ida_kernwin.unregister_action(action_name):
            pass 
        ida_kernwin.register_action(
            ida_kernwin.action_desc_t(
                action_name,
                action_label,
                TouchGrassAction(self.tracker),
                None,
                "",
                0,
            )
        )
        ida_kernwin.attach_action_to_menu(
            "Edit/touchgrass",
            action_name,
            ida_kernwin.SETMENU_APP,
        )

    def run(self, arg):
        if self.tracker._stop_flag:
            self.tracker.start()
        else:
            self.tracker.stop()

    def term(self):
        self.tracker.stop()


class touchgrass_plugin_t(idaapi.plugin_t):
    flags = idaapi.PLUGIN_MULTI
    comment = "touchgrass"
    help = "touchgrass"
    wanted_name = "touchgrass"
    wanted_hotkey = ""

    def init(self):
        config = loadconfig()
        changed = False

        if "user_id" not in config:
            config["user_id"] = str(uuid.uuid4())
            changed = True

        if not config.get("username"):
            uname = ida_kernwin.ask_str("", 0, "enter touchgrass unique username:")
            if not uname:
                uname = "Anonymous"
            config["username"] = uname
            changed = True

        if changed:
            saveconfig(config)

        tracker = timetracker(config["user_id"], config["username"])
        ida_kernwin.msg("[touchgrass] auto starting tracking\n")
        return touchgrass_plugmod_t(tracker)

    def term(self):
        ida_kernwin.msg("[touchgrass] plugin terminated.\n")


def PLUGIN_ENTRY():
    return touchgrass_plugin_t()
