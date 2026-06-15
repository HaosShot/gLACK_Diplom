import sys
import time
import threading
import subprocess
import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
from datetime import datetime

import numpy as np
import sounddevice as sd
import whisper

from config import (
    WHISPER_MODEL, SAMPLE_RATE, RECORD_SECONDS,
    SILENCE_THRESH, LANGUAGE, PLATFORM, LLM_MODEL
)
from agent import Agent
from tools import TOOLS, set_logger
import custom_commands as cc

_ui    = None
_agent = Agent()

def log(msg, level="info"):
    t      = datetime.now().strftime("%H:%M:%S")
    prefix = {"info": "·", "ok": "✓", "err": "✗", "hear": "▶"}.get(level, "·")
    line   = f"[{t}] {prefix}  {msg}"
    print(line)
    if _ui:
        _ui.append_log(line, level)

set_logger(log)
cc.set_logger(log)

def start_ollama():
    try:
        # Проверяем, доступна ли Ollama уже
        import urllib.request
        urllib.request.urlopen("http://localhost:11434", timeout=1)
        log("ollama уже запущена", "ok")
        return
    except Exception:
        pass

    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(2)
        log("ollama запущен", "ok")
    except Exception as e:
        log(f"ollama ошибка: {e}", "err")


def record_audio():
    audio = sd.rec(
        int(RECORD_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32"
    )
    sd.wait()
    return audio.flatten()

def transcribe(model, audio):
    return model.transcribe(audio, language=LANGUAGE, fp16=False)["text"].strip()


def execute(text: str):
    log(f'"{text}"', "hear")
    if _ui:
        _ui.set_status("думаю...")

    if cc.try_execute(text):
        if _ui:
            _ui.set_status("готов")
        return

    cmd       = _agent.think(text)
    tool_name = cmd.get("tool")
    args      = cmd.get("args", {})

    if not tool_name:
        log("не понял команду", "err")
        if _ui:
            _ui.set_status("готов")
        return

    if tool_name == "custom":
        trigger = args.get("trigger", text)
        if not cc.try_execute(trigger):
            log(f"своя команда не найдена: {trigger}", "err")
        if _ui:
            _ui.set_status("готов")
        return

    if tool_name not in TOOLS:
        log(f"неизвестный инструмент: {tool_name}", "err")
        if _ui:
            _ui.set_status("готов")
        return

    log(f"выполняю: {tool_name} {args if args else ''}", "info")
    try:
        TOOLS[tool_name](args)
    except Exception as e:
        log(f"ошибка: {e}", "err")

    if _ui:
        _ui.set_status("готов")

BG        = "#0d1117"
BG2       = "#161b22"
BG3       = "#1c2128"
ACCENT    = "#58a6ff"
GREEN     = "#3fb950"
RED       = "#f85149"
GRAY      = "#8b949e"
BORDER    = "#30363d"
FG        = "#e6edf3"
FONT_MONO = ("Consolas", 10) if PLATFORM == "windows" else ("Monospace", 10)
FONT_UI   = ("Segoe UI", 10) if PLATFORM == "windows" else ("Sans", 10)
FONT_SM   = ("Segoe UI", 9)  if PLATFORM == "windows" else ("Sans", 9)

LEVEL_COLORS = {"ok": GREEN, "err": RED, "hear": ACCENT, "info": GRAY}

def _btn(parent, text, command, color=ACCENT, fg=BG, **kw):

    kw.setdefault("font", FONT_UI)
    kw.setdefault("padx", 10)
    kw.setdefault("pady", 4)

    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=color,
        fg=fg,
        relief="flat",
        bd=0,
        cursor="hand2",
        activebackground=ACCENT,
        activeforeground=BG,
        **kw
    )

def _entry(parent, **kw):
    return tk.Entry(
        parent, bg=BG2, fg=FG, font=FONT_UI,
        insertbackground=FG, relief="flat", bd=0,
        highlightthickness=1,
        highlightcolor=ACCENT, highlightbackground=BORDER,
        **kw
    )

def _label(parent, text, **kw):
    return tk.Label(parent, text=text, bg=BG3, fg=GRAY, font=FONT_SM, anchor="w", **kw)


class GlackUI:
    def __init__(self, root):
        self.root       = root
        self.whisper    = None
        self._listening = False

        self.root.title("GLACK")
        self.root.configure(bg=BG)
        self.root.geometry("740x560")
        self.root.minsize(560, 420)

        self._build()

    def _build(self):
        header = tk.Frame(self.root, bg=BG, pady=10)
        header.pack(fill="x", padx=16)

        tk.Label(
            header, text="GLACK", bg=BG, fg=ACCENT,
            font=("Consolas", 20, "bold")
        ).pack(side="left")

        self._status_var = tk.StringVar(value="загрузка...")
        tk.Label(
            header, textvariable=self._status_var,
            bg=BG, fg=GRAY, font=FONT_MONO
        ).pack(side="right")

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", padx=16)

        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Glack.TNotebook",
            background=BG, borderwidth=0, tabmargins=0
        )
        style.configure(
            "Glack.TNotebook.Tab",
            background=BG2, foreground=GRAY,
            padding=[14, 6], font=FONT_UI,
            borderwidth=0
        )
        style.map(
            "Glack.TNotebook.Tab",
            background=[("selected", BG3)],
            foreground=[("selected", FG)],
        )

        self._nb = ttk.Notebook(self.root, style="Glack.TNotebook")
        self._nb.pack(fill="both", expand=True, padx=16, pady=8)

        tab1 = tk.Frame(self._nb, bg=BG)
        self._nb.add(tab1, text="  Ассистент  ")
        self._build_assistant_tab(tab1)

        # вкладка 2 — свои команды
        tab2 = tk.Frame(self._nb, bg=BG3)
        self._nb.add(tab2, text="  Команды  ")
        self._build_commands_tab(tab2)


    def _build_assistant_tab(self, parent):
        self._log = scrolledtext.ScrolledText(
            parent, bg=BG2, fg=FG, font=FONT_MONO,
            bd=0, relief="flat", state="disabled",
            wrap="word", padx=10, pady=8,
        )
        self._log.pack(fill="both", expand=True, pady=(0, 8))

        for level, color in LEVEL_COLORS.items():
            self._log.tag_config(level, foreground=color)
        self._log.tag_config("ts", foreground="#444c56")

        bottom = tk.Frame(parent, bg=BG, pady=6)
        bottom.pack(fill="x")

        self._entry = _entry(bottom)
        self._entry.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 8))
        self._entry.bind("<Return>", self._on_send)
        self._entry.focus()

        _btn(bottom, "→", self._on_send, font=("Consolas", 13, "bold"),
             padx=14, pady=5).pack(side="left")

        self._mic_btn = tk.Button(
            bottom, text="🎙", font=("", 15),
            bg=BG2, fg=FG, relief="flat", bd=0,
            padx=10, pady=5, cursor="hand2",
            activebackground=BORDER,
            command=self._on_mic,
        )
        self._mic_btn.pack(side="left", padx=(6, 0))

    def _build_commands_tab(self, parent):
        form = tk.Frame(parent, bg=BG3, pady=12, padx=16)
        form.pack(fill="x")

        tk.Label(
            form, text="Новая команда", bg=BG3, fg=FG,
            font=("Consolas", 12, "bold")
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        fields = [
            ("Фраза-триггер",  "например: открой стим"),
            ("Описание",       "например: запускает Steam"),
        ]
        self._f_trigger = self._form_row(form, 1, *fields[0])
        self._f_desc    = self._form_row(form, 2, *fields[1])

        _label(form, "Тип действия").grid(row=3, column=0, sticky="w", pady=(6, 2))

        self._action_var = tk.StringVar(value="launch")
        action_frame = tk.Frame(form, bg=BG3)
        action_frame.grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 6))

        actions = [
            ("launch",  "Запустить exe / программу"),
            ("url",     "Открыть сайт"),
            ("type",    "Напечатать текст"),
            ("hotkey",  "Нажать клавиши (ctrl+s)"),
        ]
        for val, lbl in actions:
            tk.Radiobutton(
                action_frame, text=lbl, variable=self._action_var, value=val,
                bg=BG3, fg=FG, selectcolor=BG2,
                activebackground=BG3, activeforeground=FG,
                font=FONT_SM, command=self._on_action_change
            ).pack(side="left", padx=(0, 16))

        self._value_label = _label(form, "Путь к exe")
        self._value_label.grid(row=5, column=0, sticky="w", pady=(4, 2))

        self._f_value = _entry(form)
        self._f_value.grid(row=6, column=0, columnspan=2, sticky="ew", ipady=5)
        form.columnconfigure(0, weight=1)

        self._hint_var = tk.StringVar(value='например: C:\\Program Files\\Steam\\steam.exe  или просто  steam')
        tk.Label(
            form, textvariable=self._hint_var,
            bg=BG3, fg="#444c56", font=FONT_SM, anchor="w"
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(2, 8))

        btn_row = tk.Frame(form, bg=BG3)
        btn_row.grid(row=8, column=0, columnspan=2, sticky="w")

        _btn(btn_row, "＋ Добавить", self._on_add_command).pack(side="left", padx=(0, 8))
        _btn(btn_row, "Очистить", self._clear_form, color=BG2, fg=GRAY).pack(side="left")

        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(0, 8))

        list_header = tk.Frame(parent, bg=BG3)
        list_header.pack(fill="x", padx=16)

        tk.Label(
            list_header, text="Сохранённые команды",
            bg=BG3, fg=FG, font=("Consolas", 11, "bold")
        ).pack(side="left")

        _btn(list_header, "↻", self._refresh_list,
             color=BG2, fg=GRAY, padx=6).pack(side="right")

        list_frame = tk.Frame(parent, bg=BG3)
        list_frame.pack(fill="both", expand=True, padx=16, pady=(6, 8))

        scrollbar = tk.Scrollbar(list_frame, bg=BG2, troughcolor=BG2, bd=0)
        scrollbar.pack(side="right", fill="y")

        self._cmd_list = tk.Listbox(
            list_frame,
            bg=BG2, fg=FG, font=FONT_MONO,
            selectbackground=ACCENT, selectforeground=BG,
            relief="flat", bd=0,
            highlightthickness=0,
            yscrollcommand=scrollbar.set
        )
        self._cmd_list.pack(fill="both", expand=True)
        scrollbar.config(command=self._cmd_list.yview)
        self._cmd_list.bind("<Double-Button-1>", self._on_select_command)

        del_frame = tk.Frame(parent, bg=BG3, pady=6)
        del_frame.pack(fill="x", padx=16)

        _btn(
            del_frame, "🗑 Удалить выбранную",
            self._on_delete_command, color="#3d1a1a", fg=RED
        ).pack(side="left")

        tk.Label(
            del_frame,
            text="двойной клик — загрузить в форму",
            bg=BG3, fg="#444c56", font=FONT_SM
        ).pack(side="right")

        self._refresh_list()

    def _form_row(self, parent, row, label, placeholder):
        _label(parent, label).grid(row=row*2-1, column=0, sticky="w", pady=(6, 2))
        e = _entry(parent)
        e.insert(0, placeholder)
        e.config(fg="#444c56")
        e.bind("<FocusIn>",  lambda ev, en=e, ph=placeholder: self._clear_ph(ev, en, ph))
        e.bind("<FocusOut>", lambda ev, en=e, ph=placeholder: self._restore_ph(ev, en, ph))
        e.grid(row=row*2, column=0, columnspan=2, sticky="ew", ipady=5)
        parent.columnconfigure(0, weight=1)
        return e

    def _clear_ph(self, event, entry, placeholder):
        if entry.get() == placeholder:
            entry.delete(0, "end")
            entry.config(fg=FG)

    def _restore_ph(self, event, entry, placeholder):
        if not entry.get():
            entry.insert(0, placeholder)
            entry.config(fg="#444c56")

    def _on_action_change(self):
        action = self._action_var.get()
        hints = {
            "launch": ("Путь к exe или команда",
                       "C:\\Program Files\\Steam\\steam.exe  или просто  steam"),
            "url":    ("URL сайта",
                       "https://store.steampowered.com"),
            "type":   ("Текст для печати",
                       "привет! как дела?"),
            "hotkey": ("Комбинация клавиш",
                       "ctrl+shift+esc"),
        }
        label, hint = hints.get(action, ("Значение", ""))
        self._value_label.config(text=label)
        self._hint_var.set(f"например: {hint}")

    def _clear_form(self):
        for e, ph in [
            (self._f_trigger, "например: открой стим"),
            (self._f_desc,    "например: запускает Steam"),
            (self._f_value,   ""),
        ]:
            e.delete(0, "end")
            if ph:
                e.insert(0, ph)
                e.config(fg="#444c56")
        self._action_var.set("launch")
        self._on_action_change()

    def _get_field(self, entry, placeholder):
        val = entry.get().strip()
        return "" if val == placeholder else val

    def _on_add_command(self):
        trigger = self._get_field(self._f_trigger, "например: открой стим")
        desc    = self._get_field(self._f_desc,    "например: запускает Steam")
        action  = self._action_var.get()
        value   = self._f_value.get().strip()

        if not trigger:
            messagebox.showwarning("GLACK", "Укажи фразу-триггер")
            return
        if not value:
            messagebox.showwarning("GLACK", "Укажи значение (путь, ссылку или текст)")
            return

        cc.add_command(trigger, action, value, desc)
        self._refresh_list()
        self._clear_form()
        log(f"добавлена команда: «{trigger}»", "ok")

    def _on_delete_command(self):
        sel = self._cmd_list.curselection()
        if not sel:
            messagebox.showinfo("GLACK", "Выбери команду из списка")
            return
        line    = self._cmd_list.get(sel[0])
        trigger = line.split("»")[0].replace("«", "").strip()
        if messagebox.askyesno("GLACK", f"Удалить команду «{trigger}»?"):
            cc.delete_command(trigger)
            self._refresh_list()

    def _on_select_command(self, _event):
        sel = self._cmd_list.curselection()
        if not sel:
            return
        line    = self._cmd_list.get(sel[0])
        trigger = line.split("»")[0].replace("«", "").strip()
        commands = cc.load_commands()
        if trigger not in commands:
            return
        cmd = commands[trigger]

        self._f_trigger.delete(0, "end")
        self._f_trigger.insert(0, trigger)
        self._f_trigger.config(fg=FG)

        self._f_desc.delete(0, "end")
        self._f_desc.insert(0, cmd.get("description", ""))
        self._f_desc.config(fg=FG)

        self._action_var.set(cmd.get("action", "launch"))
        self._on_action_change()

        self._f_value.delete(0, "end")
        self._f_value.insert(0, cmd.get("value", ""))

    def _refresh_list(self):
        commands = cc.load_commands()
        self._cmd_list.delete(0, "end")

        ACTION_ICONS = {
            "launch": "🚀",
            "url":    "🌐",
            "type":   "⌨",
            "hotkey": "⌨",
        }

        if not commands:
            self._cmd_list.insert("end", "  нет сохранённых команд")
            return

        for trigger, data in commands.items():
            icon = ACTION_ICONS.get(data.get("action", ""), "•")
            desc = data.get("description") or data.get("value", "")
            if len(desc) > 50:
                desc = desc[:47] + "..."
            self._cmd_list.insert("end", f"  «{trigger}»  {icon}  {desc}")



    def append_log(self, line, level="info"):
        self.root.after(0, self._do_append, line, level)

    def _do_append(self, line, level):
        self._log.configure(state="normal")
        if line.startswith("[") and "]" in line:
            end = line.index("]") + 1
            self._log.insert("end", line[:end], "ts")
            self._log.insert("end", line[end:] + "\n", level)
        else:
            self._log.insert("end", line + "\n", level)
        self._log.configure(state="disabled")
        self._log.see("end")

    def set_status(self, text):
        self.root.after(0, lambda: self._status_var.set(text))

    def set_mic_active(self, active: bool):
        def _set():
            if active:
                self._mic_btn.configure(bg=RED, fg="white")
                self.set_status("● слушаю...")
            else:
                self._mic_btn.configure(bg=BG2, fg=FG)
                self.set_status("готов")
        self.root.after(0, _set)

    def _on_send(self, _event=None):
        text = self._entry.get().strip()
        if not text:
            return
        self._entry.delete(0, "end")
        if not self.whisper:
            self.append_log("загрузка ещё не завершена...", "err")
            return
        threading.Thread(target=execute, args=(text,), daemon=True).start()

    def _on_mic(self):
        if not self.whisper:
            self.append_log("загрузка ещё не завершена...", "err")
            return
        if self._listening:
            return
        threading.Thread(target=self._voice_once, daemon=True).start()

    def _voice_once(self):
        self._listening = True
        self.set_mic_active(True)
        try:
            audio = record_audio()
            rms   = np.sqrt(np.mean(audio ** 2))
            if rms < SILENCE_THRESH:
                self.append_log("тишина — попробуй ещё раз", "info")
                return
            self.set_status("распознаю...")
            text = transcribe(self.whisper, audio)
            if text and len(text.strip()) > 1:
                execute(text)
            else:
                self.append_log("не удалось распознать", "err")
        except Exception as e:
            self.append_log(f"ошибка микрофона: {e}", "err")
        finally:
            self._listening = False
            self.set_mic_active(False)



def _load(ui):
    global _ui
    _ui = ui

    ui.set_status("запуск ollama...")
    start_ollama()

    ui.set_status("загрузка Whisper...")
    log("загружаю Whisper...")
    ui.whisper = whisper.load_model(WHISPER_MODEL)
    log("Whisper готов", "ok")

    ui.set_status("прогрев LLM...")
    log("прогреваю модель...")
    try:
        import ollama as _ollama
        _ollama.chat(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": "hi"}],
            options={"num_predict": 5}
        )
        log("LLM готов", "ok")
    except Exception as e:
        log(f"LLM не отвечает: {e}", "err")
        log(f"убедись что запущен: ollama pull {LLM_MODEL}", "info")

   
    commands = cc.load_commands()
    if commands:
        log(f"загружено своих команд: {len(commands)}", "ok")

    ui.set_status("готов")
    log("готов — говори или пиши", "ok")



def main():
    root = tk.Tk()
    ui   = GlackUI(root)
    threading.Thread(target=_load, args=(ui,), daemon=True).start()
    root.mainloop()

if __name__ == "__main__":
    main()