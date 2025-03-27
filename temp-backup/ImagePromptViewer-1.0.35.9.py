#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Datum: 2025-03-27
Versionsnummer: 1.0.35.9
Interne Bezeichnung: Master 8

Änderungen in Version 1.0.35.9:
- Verbesserte Dekodierung von JPEG-Textchunks aus EXIF-Tag 37510 ('UserComment'):
  - Präzises Überspringen der ersten 8 Bytes ('UNICODE\x00\x00').
  - Primäre Dekodierung als UTF-16LE, basierend auf Notepad++-Analyse.
  - Fallbacks auf UTF-16BE, UTF-8, Latin-1 mit Entfernung von \x00-Zeichen.
- Erweiterte Debug-Ausgabe:
  - Rohe Bytes des Textchunks als Hex-Werte.
  - Verwendete Kodierung und dekodierter Text vor Aufteilung.
  - Aufgeteilte Teile (Prompt, Negativer Prompt, Settings).
- Entfernung von PNG-spezifischer Logik zur Fokussierung auf JPEG-Problemlösung.

Zusammenfassung:
Ein Bildbetrachter für JPEG-Dateien, der Textchunks aus EXIF-Daten (Tag 37510) extrahiert und in Prompt, Negativen Prompt und Settings aufteilt.
"""

import subprocess, sys
import os
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
import threading
from pathlib import Path
from collections import deque

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tkinterdnd2"])
    from tkinterdnd2 import TkinterDnD, DND_FILES

try:
    from PIL import Image, ImageTk
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image, ImageTk

try:
    from screeninfo import get_monitors
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "screeninfo"])
    from screeninfo import get_monitors

try:
    from send2trash import send2trash
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "send2trash"])
    from send2trash import send2trash

try:
    import piexif
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "piexif"])
    import piexif

VERSION = "1.0.35.9"

BG_COLOR = "#1F1F1F"
BTN_BG_COLOR = "#FFA500"
BTN_FG_COLOR = "#000000"
TEXT_BG_COLOR = "#333333"
TEXT_FG_COLOR = "#FFA500"
HIGHLIGHT_COLOR = "#FF5555"

SCALE_OPTIONS = ["Default", "25%", "50%", "75%"]
DEFAULT_SCALE = "Default"
IMAGE_EXTENSIONS = (".jpg", ".JPG", ".jpeg", ".JPEG")  # Fokus auf JPEG

def get_datetime_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def copy_to_clipboard(widget, text):
    widget.clipboard_clear()
    widget.clipboard_append(text)
    widget.update()

def extract_text_chunks(img_path):
    try:
        img = Image.open(img_path)
    except Exception as e:
        messagebox.showerror("Fehler", f"Fehler beim Öffnen des Bildes:\n{e}")
        return "", "", ""
    
    is_jpeg = img_path.lower().endswith((".jpg", ".jpeg"))
    if not is_jpeg:
        return "", "", ""  # Nur JPEG wird unterstützt in dieser Version

    full_text = ""
    debug_info = []
    try:
        exif_dict = piexif.load(img_path)
        user_comment = exif_dict.get("Exif", {}).get(piexif.ExifIFD.UserComment)
        if user_comment and isinstance(user_comment, bytes):
            debug_info.append(f"Debug: Rohe Bytes von UserComment: {user_comment[:50].hex()}...")
            if user_comment.startswith(b"UNICODE\x00\x00"):
                text_bytes = user_comment[8:]  # Überspringe genau die ersten 8 Bytes
                encodings = [
                    ("utf-16le", "UTF-16LE"),
                    ("utf-16be", "UTF-16BE"),
                    ("utf-8", "UTF-8"),
                    ("latin-1", "Latin-1")
                ]
                for encoding, name in encodings:
                    try:
                        full_text = text_bytes.decode(encoding, errors="strict")
                        debug_info.append(f"Debug: Erfolgreiche Dekodierung mit {name}: {repr(full_text)[:100]}...")
                        break
                    except UnicodeDecodeError:
                        debug_info.append(f"Debug: {name} fehlgeschlagen.")
                else:
                    # Fallback: Entferne \x00 und dekodiere als Latin-1
                    cleaned_bytes = text_bytes.replace(b"\x00", b"")
                    full_text = cleaned_bytes.decode("latin-1", errors="ignore")
                    debug_info.append(f"Debug: Fallback (Latin-1 nach \x00-Entfernung): {repr(full_text)[:100]}...")
            else:
                full_text = user_comment.decode("latin-1", errors="ignore")
                debug_info.append(f"Debug: Kein UNICODE-Präfix, dekodiert als Latin-1: {repr(full_text)[:100]}...")
        else:
            debug_info.append("Debug: Kein UserComment-Tag gefunden oder kein Byte-Daten.")
    except Exception as e:
        debug_info.append(f"Debug: Fehler beim Auslesen der EXIF-Daten: {e}")

    if not full_text:
        debug_info.append("Debug: Kein Textchunk gefunden.")
        if hasattr(ImageManagerForm, 'instance'):
            ImageManagerForm.instance.debug_info = "\n".join(debug_info)
        return "", "", ""

    # Aufteilung in Prompt, Negativer Prompt und Settings
    idx_neg = full_text.find("Negative prompt:")
    idx_steps = full_text.find("Steps:")

    prompt = full_text[:idx_neg].strip() if idx_neg != -1 else (full_text[:idx_steps].strip() if idx_steps != -1 else full_text.strip())
    negativ = full_text[idx_neg + len("Negative prompt:"):idx_steps].strip() if idx_neg != -1 and idx_steps > idx_neg else (full_text[idx_neg + len("Negative prompt:"):].strip() if idx_neg != -1 else "")
    settings = full_text[idx_steps + len("Steps:"):].strip() if idx_steps != -1 else ""

    debug_info.extend([
        f"Debug: Prompt: {repr(prompt)[:50]}...",
        f"Debug: Negativ: {repr(negativ)[:50]}...",
        f"Debug: Settings: {repr(settings)[:50]}..."
    ])

    if hasattr(ImageManagerForm, 'instance'):
        ImageManagerForm.instance.debug_info = "\n".join(debug_info)

    return prompt, negativ, settings

# Rest des Codes bleibt größtenteils unverändert, hier nur der relevante Ausschnitt
class ImageManagerForm(TkinterDnD.Tk):
    instance = None

    def __init__(self):
        super().__init__()
        ImageManagerForm.instance = self
        self.title(f"ImagePromptViewer (Version {VERSION})")
        self.configure(bg=BG_COLOR)
        # ... (Rest der Initialisierung bleibt gleich)
        self.setup_ui()

    def setup_ui(self):
        # ... (Vorhandene UI-Setup-Funktion, angepasst an deine Farbvorgaben)
        for widget in self.winfo_children():
            widget.destroy()

        self.always_on_top_var = tk.BooleanVar(value=False)
        self.top_checkbox = tk.Checkbutton(self, text="Always on Top", variable=self.always_on_top_var,
                                           command=self.update_topmost, fg=TEXT_FG_COLOR,
                                           bg=BG_COLOR, selectcolor=BG_COLOR)
        self.top_checkbox.pack(pady=5)

        self.image_label = tk.Label(self, bg=BG_COLOR)
        self.image_label.pack(pady=10)

        self.prompt_text = ScrolledText(self, height=4, bg="#000000", fg=TEXT_FG_COLOR)
        self.prompt_text.pack(pady=2)
        self.negativ_text = ScrolledText(self, height=4, bg="#000000", fg=TEXT_FG_COLOR)
        self.negativ_text.pack(pady=2)
        self.settings_text = ScrolledText(self, height=4, bg="#000000", fg=TEXT_FG_COLOR)
        self.settings_text.pack(pady=2)

        self.load_button = tk.Button(self, text="JPEG Laden", command=self.load_jpeg,
                                     bg=BTN_BG_COLOR, fg=BTN_FG_COLOR)
        self.load_button.pack(pady=10)

        self.debug_button = tk.Button(self, text="Debug", command=self.show_debug_info,
                                      bg=BTN_BG_COLOR, fg=BTN_FG_COLOR)
        self.debug_button.pack(pady=5)

        self.version_label = tk.Label(self, text=f"Version: {VERSION}", fg=TEXT_FG_COLOR, bg=BG_COLOR, font=("Arial", 8))
        self.version_label.pack(side=tk.BOTTOM, pady=5)

    def update_topmost(self):
        self.attributes("-topmost", self.always_on_top_var.get())

    def load_jpeg(self):
        file_path = filedialog.askopenfilename(filetypes=[("JPEG Files", "*.jpg *.jpeg")])
        if file_path:
            img = Image.open(file_path)
            photo = ImageTk.PhotoImage(img)
            self.image_label.config(image=photo)
            self.image_label.image = photo
            prompt, negativ, settings = extract_text_chunks(file_path)
            self.prompt_text.delete("1.0", tk.END)
            self.negativ_text.delete("1.0", tk.END)
            self.settings_text.delete("1.0", tk.END)
            self.prompt_text.insert(tk.END, prompt)
            self.negativ_text.insert(tk.END, negativ)
            self.settings_text.insert(tk.END, settings)

    def show_debug_info(self):
        debug_win = tk.Toplevel(self)
        debug_win.title("Debug Information")
        debug_text = ScrolledText(debug_win, width=80, height=20, bg=BG_COLOR, fg=TEXT_FG_COLOR)
        debug_text.insert(tk.END, self.debug_info if self.debug_info else "Keine Debug-Informationen verfügbar.")
        debug_text.config(state=tk.DISABLED)
        debug_text.pack()

# Rest des Codes (z. B. mainloop) bleibt erhalten
if __name__ == "__main__":
    app = ImageManagerForm()
    app.mainloop()