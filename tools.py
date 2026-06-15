import os
import re
import sys
import time
import tempfile
import subprocess
import webbrowser

import mss
import psutil
import pyperclip
import pyautogui
import requests
import ollama

from PIL import Image
from urllib.parse import quote_plus
from config import PLATFORM, VISION_MODEL

pyautogui.FAILSAFE = False

_log = print

def set_logger(fn):
    global _log
    _log = fn

def log(msg, level="ok"):
    _log(msg, level)



def _capture_screen():
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        shot    = sct.grab(monitor)
        img     = Image.frombytes("RGB", shot.size, shot.rgb)
        path    = os.path.join(tempfile.gettempdir(), "glack_screen.png")
        img.save(path)
        return path

def _launch(cmd):
    if PLATFORM == "windows":
        subprocess.Popen(cmd, shell=True)
    else:
        subprocess.Popen([cmd])

def _get_window(title):
    try:
        import pygetwindow as gw
        wins = gw.getWindowsWithTitle(title)
        return wins[0] if wins else None
    except Exception:
        return None



def open_browser(args=None):
    webbrowser.open("https://google.com")
    log("браузер открыт")

def google_search(args):
    q = args.get("query", "")
    webbrowser.open(f"https://google.com/search?q={quote_plus(q)}")
    log(f"google: {q}")

def youtube_search(args):
    q = args.get("query", "")
    webbrowser.open(f"https://youtube.com/results?search_query={quote_plus(q)}")
    log(f"youtube поиск: {q}")

def youtube_open_first(args):

    q = args.get("query", "")
    if not q:
        log("пустой запрос", "err")
        return

    log(f"ищу первое видео: {q}", "info")

    try:
        url     = f"https://www.youtube.com/results?search_query={quote_plus(q)}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "ru-RU,ru;q=0.9",
        }
        html = requests.get(url, headers=headers, timeout=8).text

        ids = re.findall(r'"videoId"\s*:\s*"([a-zA-Z0-9_-]{11})"', html)

        seen = set()
        unique_ids = []
        for vid in ids:
            if vid not in seen:
                seen.add(vid)
                unique_ids.append(vid)

        if unique_ids:
            video_url = f"https://www.youtube.com/watch?v={unique_ids[0]}"
            webbrowser.open(video_url)
            log(f"открыто видео: {video_url}")
        else:
            log("не нашёл видео, открываю поиск", "info")
            youtube_search(args)

    except requests.exceptions.Timeout:
        log("таймаут, открываю поиск", "err")
        youtube_search(args)
    except Exception as e:
        log(f"youtube ошибка: {e}", "err")
        youtube_search(args)

def open_site(args):
    site = args.get("site", "").lower()
    sites = {
        "youtube":  "https://youtube.com",        "ютуб":     "https://youtube.com",
        "github":   "https://github.com",          "гитхаб":   "https://github.com",
        "telegram": "https://web.telegram.org",    "телеграм": "https://web.telegram.org",
        "vk":       "https://vk.com",              "вк":       "https://vk.com",
        "вконтакте":"https://vk.com",
        "chatgpt":  "https://chat.openai.com",     "чатгпт":   "https://chat.openai.com",
        "яндекс":   "https://yandex.ru",           "yandex":   "https://yandex.ru",
        "reddit":   "https://reddit.com",          "реддит":   "https://reddit.com",
        "twitch":   "https://twitch.tv",           "твич":     "https://twitch.tv",
        "habr":     "https://habr.com",            "хабр":     "https://habr.com",
        "stackoverflow": "https://stackoverflow.com",
        "spotify":  "https://open.spotify.com",    "спотифай": "https://open.spotify.com",
        "netflix":  "https://netflix.com",         "нетфликс": "https://netflix.com",
    }
    for key, url in sites.items():
        if key in site:
            webbrowser.open(url)
            log(f"открыт {key}")
            return
    webbrowser.open(f"https://google.com/search?q={quote_plus(site)}")
    log(f"поиск: {site}")

def open_notepad(args=None):
    _launch("notepad" if PLATFORM == "windows" else "gedit")
    log("блокнот открыт")

def open_calculator(args=None):
    _launch("calc" if PLATFORM == "windows" else "gnome-calculator")
    log("калькулятор открыт")

def open_terminal(args=None):
    _launch("cmd" if PLATFORM == "windows" else "gnome-terminal")
    log("терминал открыт")

def open_explorer(args=None):
    _launch("explorer" if PLATFORM == "windows" else "nautilus")
    log("проводник открыт")


def type_text(args):
    text = args.get("text", "")
    if not text:
        return

    log(f'пишу: "{text}"')

    time.sleep(0.35)
    pyperclip.copy(text)
    time.sleep(0.1)

    # Вставляем
    if PLATFORM == "mac":
        pyautogui.hotkey("command", "v")
    else:
        pyautogui.hotkey("ctrl", "v")

def press_enter(args=None):
    time.sleep(0.1)
    pyautogui.press("enter")
    log("enter")

def press_backspace(args=None):
    time.sleep(0.1)
    pyautogui.press("backspace")
    log("backspace")

def press_escape(args=None):
    time.sleep(0.1)
    pyautogui.press("escape")
    log("escape")

def press_tab(args=None):
    time.sleep(0.1)
    pyautogui.press("tab")
    log("tab")

def clear_field(args=None):
    time.sleep(0.1)
    if PLATFORM == "mac":
        pyautogui.hotkey("command", "a")
    else:
        pyautogui.hotkey("ctrl", "a")
    time.sleep(0.05)
    pyautogui.press("delete")
    log("поле очищено")

def hotkey(args):
    keys = args.get("keys", [])
    if keys:
        time.sleep(0.1)
        pyautogui.hotkey(*keys)
        log(f"hotkey: {'+'.join(keys)}")

def select_all(args=None):
    hotkey({"keys": ["command", "a"] if PLATFORM == "mac" else ["ctrl", "a"]})

def undo(args=None):
    hotkey({"keys": ["command", "z"] if PLATFORM == "mac" else ["ctrl", "z"]})

def redo(args=None):
    hotkey({"keys": ["command", "y"] if PLATFORM == "mac" else ["ctrl", "y"]})

def save_file(args=None):
    hotkey({"keys": ["command", "s"] if PLATFORM == "mac" else ["ctrl", "s"]})


def copy_to_clipboard(args):
    pyperclip.copy(args.get("text", ""))
    log("скопировано в буфер")

def paste_clipboard(args=None):
    time.sleep(0.1)
    if PLATFORM == "mac":
        pyautogui.hotkey("command", "v")
    else:
        pyautogui.hotkey("ctrl", "v")
    log("вставлено из буфера")

def get_clipboard(args=None):
    text = pyperclip.paste()
    log(f"буфер: {text[:80]}")
    return text

def mouse_move(args):
    x, y = int(args.get("x", 0)), int(args.get("y", 0))
    pyautogui.moveTo(x, y, duration=0.25)
    log(f"мышь → {x},{y}")

def mouse_click(args=None):
    pyautogui.click()
    log("клик")

def mouse_double_click(args=None):
    pyautogui.doubleClick()
    log("двойной клик")

def mouse_right_click(args=None):
    pyautogui.rightClick()
    log("правый клик")

def mouse_scroll(args=None):
    amount = int((args or {}).get("amount", -3))
    pyautogui.scroll(amount)
    log(f"скролл {amount}")


def focus_window(args):
    w = _get_window(args.get("title", ""))
    if w:
        w.activate()
        log(f"фокус: {args.get('title')}")
    else:
        log("окно не найдено", "err")

def close_window(args):
    w = _get_window(args.get("title", ""))
    if w:
        w.close()
        log(f"закрыто: {args.get('title')}")
    else:
        log("окно не найдено", "err")

def minimize_window(args):
    w = _get_window(args.get("title", ""))
    if w:
        w.minimize()
        log(f"свёрнуто: {args.get('title')}")
    else:
        log("окно не найдено", "err")

def maximize_window(args):
    w = _get_window(args.get("title", ""))
    if w:
        w.maximize()
        log(f"развёрнуто: {args.get('title')}")
    else:
        log("окно не найдено", "err")


def browser_close_tab(args=None):
    hotkey({"keys": ["ctrl", "w"]})
    log("вкладка закрыта")

def browser_new_tab(args=None):
    hotkey({"keys": ["ctrl", "t"]})
    log("новая вкладка")

def browser_refresh(args=None):
    pyautogui.press("f5")
    log("страница обновлена")

def browser_next_tab(args=None):
    hotkey({"keys": ["ctrl", "tab"]})
    log("следующая вкладка")

def browser_prev_tab(args=None):
    hotkey({"keys": ["ctrl", "shift", "tab"]})
    log("предыдущая вкладка")

def browser_address_bar(args=None):
    hotkey({"keys": ["ctrl", "l"]})
    log("адресная строка")

def browser_back(args=None):
    hotkey({"keys": ["alt", "left"]})
    log("назад")

def browser_forward(args=None):
    hotkey({"keys": ["alt", "right"]})
    log("вперёд")



def show_desktop(args=None):
    if PLATFORM == "windows":
        hotkey({"keys": ["win", "d"]})
    elif PLATFORM == "mac":
        hotkey({"keys": ["command", "mission_control"]})
    else:
        hotkey({"keys": ["super", "d"]})
    log("рабочий стол")

def switch_window(args=None):
    hotkey({"keys": ["alt", "tab"]})
    log("переключение окна")

def close_active_window(args=None):
    hotkey({"keys": ["alt", "f4"]})
    log("активное окно закрыто")

def toggle_fullscreen(args=None):
    pyautogui.press("f11")
    log("полный экран вкл/выкл")

def snap_window_left(args=None):
    hotkey({"keys": ["win", "left"]})
    log("окно влево")

def snap_window_right(args=None):
    hotkey({"keys": ["win", "right"]})
    log("окно вправо")



def volume_up(args=None):   pyautogui.press("volumeup");   log("громкость +")
def volume_down(args=None): pyautogui.press("volumedown"); log("громкость -")
def volume_mute(args=None): pyautogui.press("volumemute"); log("звук вкл/выкл")

def take_screenshot(args=None):
    path = _capture_screen()
    log(f"скриншот: {path}")
    return path

def list_processes(args=None):
    names  = sorted({p.info["name"] for p in psutil.process_iter(["name"]) if p.info["name"]})
    result = ", ".join(names[:50])
    log(f"процессы: {result[:100]}...")
    return result

def analyze_screen(args=None):
    question = (args or {}).get("question", "что на экране?")
    try:
        path     = _capture_screen()
        response = ollama.chat(
            model=VISION_MODEL,
            messages=[{"role": "user", "content": question, "images": [path]}]
        )
        answer = response["message"]["content"]
        log(f"vision: {answer[:120]}")
        return answer
    except Exception as e:
        log(f"vision ошибка: {e}", "err")
        return str(e)


TOOLS = {
    # браузер — сайты и поиск
    "open_browser":         open_browser,
    "google_search":        google_search,
    "youtube_search":       youtube_search,
    "youtube_open_first":   youtube_open_first,
    "open_site":            open_site,

    # браузер — вкладки и навигация
    "browser_close_tab":    browser_close_tab,
    "browser_new_tab":      browser_new_tab,
    "browser_refresh":      browser_refresh,
    "browser_next_tab":     browser_next_tab,
    "browser_prev_tab":     browser_prev_tab,
    "browser_address_bar":  browser_address_bar,
    "browser_back":         browser_back,
    "browser_forward":      browser_forward,

    # приложения
    "open_notepad":         open_notepad,
    "open_calculator":      open_calculator,
    "open_terminal":        open_terminal,
    "open_explorer":        open_explorer,

    # печать
    "type_text":            type_text,
    "press_enter":          press_enter,
    "press_backspace":      press_backspace,
    "press_escape":         press_escape,
    "press_tab":            press_tab,
    "clear_field":          clear_field,
    "select_all":           select_all,
    "hotkey":               hotkey,
    "undo":                 undo,
    "redo":                 redo,
    "save_file":            save_file,

    # буфер обмена
    "copy_to_clipboard":    copy_to_clipboard,
    "paste_clipboard":      paste_clipboard,
    "get_clipboard":        get_clipboard,

    # мышь
    "mouse_move":           mouse_move,
    "mouse_click":          mouse_click,
    "mouse_double_click":   mouse_double_click,
    "mouse_right_click":    mouse_right_click,
    "mouse_scroll":         mouse_scroll,

    # окна и рабочий стол
    "focus_window":         focus_window,
    "close_window":         close_window,
    "minimize_window":      minimize_window,
    "maximize_window":      maximize_window,
    "show_desktop":         show_desktop,
    "switch_window":        switch_window,
    "close_active_window":  close_active_window,
    "toggle_fullscreen":    toggle_fullscreen,
    "snap_window_left":     snap_window_left,
    "snap_window_right":    snap_window_right,

    # система
    "volume_up":            volume_up,
    "volume_down":          volume_down,
    "volume_mute":          volume_mute,
    "take_screenshot":      take_screenshot,
    "list_processes":       list_processes,
    "analyze_screen":       analyze_screen,
}