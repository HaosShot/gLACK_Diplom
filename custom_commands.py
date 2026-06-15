import json
import os
import subprocess
import webbrowser
import time
import pyperclip
import pyautogui

from config import PLATFORM

COMMANDS_FILE = os.path.join(os.path.dirname(__file__), "custom_commands.json")

_log = print

def set_logger(fn):
    global _log
    _log = fn

def log(msg, level="ok"):
    _log(msg, level)


def load_commands() -> dict:
    if not os.path.exists(COMMANDS_FILE):
        return {}
    try:
        with open(COMMANDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_commands(commands: dict):
    with open(COMMANDS_FILE, "w", encoding="utf-8") as f:
        json.dump(commands, f, ensure_ascii=False, indent=2)

def add_command(trigger: str, action: str, value: str, description: str = ""):
    commands = load_commands()
    commands[trigger.lower().strip()] = {
        "description": description,
        "action":      action,
        "value":       value,
    }
    save_commands(commands)
    log(f"команда сохранена: «{trigger}»")

def delete_command(trigger: str):
    commands = load_commands()
    key = trigger.lower().strip()
    if key in commands:
        del commands[key]
        save_commands(commands)
        log(f"команда удалена: «{trigger}»")
        return True
    return False


def try_execute(text: str) -> bool:
    commands = load_commands()
    t = text.lower().strip()

    matched = None
    for trigger in commands:
        if t == trigger or trigger in t:
            matched = trigger
            break

    if not matched:
        return False

    cmd    = commands[matched]
    action = cmd.get("action", "")
    value  = cmd.get("value", "")

    log(f"своя команда: «{matched}» → {action}", "ok")

    if action == "launch":
        _do_launch(value)
    elif action == "url":
        webbrowser.open(value)
        log(f"открыто: {value}")
    elif action == "type":
        _do_type(value)
    elif action == "hotkey":
        _do_hotkey(value)
    else:
        log(f"неизвестный action: {action}", "err")

    return True

def _do_launch(value: str):
    try:
        if PLATFORM == "windows":
            subprocess.Popen(value, shell=True)
        else:
            subprocess.Popen(value.split())
        log(f"запущено: {value}")
    except Exception as e:
        log(f"ошибка запуска: {e}", "err")

def _do_type(value: str):
    time.sleep(0.4)
    pyperclip.copy(value)
    time.sleep(0.1)
    if PLATFORM == "mac":
        pyautogui.hotkey("command", "v")
    else:
        pyautogui.hotkey("ctrl", "v")
    log(f'напечатано: "{value}"')

def _do_hotkey(value: str):
    keys = [k.strip() for k in value.lower().split("+")]
    pyautogui.hotkey(*keys)
    log(f"hotkey: {value}")


def get_prompt_block() -> str:
    commands = load_commands()
    if not commands:
        return ""

    lines = ["CUSTOM USER COMMANDS (use tool 'custom' with trigger):"]
    for trigger, data in commands.items():
        desc = data.get("description") or data.get("action", "")
        lines.append(f'- "{trigger}" — {desc}')

    lines.append('Example: User: открой стим')
    lines.append('{"tool": "custom", "args": {"trigger": "открой стим"}}')
    return "\n".join(lines)