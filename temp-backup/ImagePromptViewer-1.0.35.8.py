#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Datum: 2025-03-27
Versionsnummer: 1.0.35.8
Interne Bezeichnung: Master 3 Alpha 1

Änderungen in Version 1.0.35.8:
- Korrektur der JPEG-Textchunk-Dekodierung aus EXIF-Tag 37510 ('UserComment'):
  - Präzises Überspringen der ersten 8 Bytes ('UNICODE\x00\x00') mit strikter UTF-16LE-Dekodierung.
  - Entfernung von 'errors=ignore' für genauere Fehldiagnose.
  - Verbesserte Debug-Ausgabe mit Anzeige der ersten dekodierten Zeichen.
  - Fallbacks nur bei Fehlschlag von UTF-16LE (UTF-16BE, UTF-8, Latin-1).
- Beibehaltung der PNG-Unterstützung für info['parameters'].

Zusammenfassung:
Ein Bildbetrachter für PNG- und JPEG-Dateien, der Textchunks auswertet (PNG: info['parameters'], JPEG: EXIF-Tag 37510) und in Prompt, Negativen Prompt und Settings aufteilt.
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

VERSION = "1.0.35.8"

BG_COLOR = "#1F1F1F"
BTN_BG_COLOR = "#FFA500"
BTN_FG_COLOR = "#000000"
TEXT_BG_COLOR = "#333333"
TEXT_FG_COLOR = "#FFA500"
HIGHLIGHT_COLOR = "#FF5555"

SCALE_OPTIONS = ["Default", "25%", "50%", "75%"]
DEFAULT_SCALE = "Default"
IMAGE_EXTENSIONS = (".png", ".PNG", ".jpg", ".JPG", ".jpeg", ".JPEG")

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
    
    info = img.info
    full_text = ""
    param_key = None
    debug_info = []
    is_jpeg = img_path.lower().endswith((".jpg", ".jpeg"))

    if is_jpeg:
        try:
            exif_dict = piexif.load(img_path)
            user_comment = exif_dict.get("Exif", {}).get(piexif.ExifIFD.UserComment)
            if user_comment and isinstance(user_comment, bytes):
                debug_info.append(f"Debug: Rohe Bytes von UserComment: {user_comment[:50].hex()}...")
                if user_comment.startswith(b"UNICODE\x00\x00"):
                    text_bytes = user_comment[8:]  # Präzises Überspringen der ersten 8 Bytes
                    try:
                        full_text = text_bytes.decode("utf-16le")  # Strikte Dekodierung
                        debug_info.append(f"Debug: Erfolgreiche Dekodierung mit UTF-16LE: {repr(full_text)[:100]}...")
                        debug_info.append(f"Debug: Erste 10 Zeichen: {repr(full_text[:10])}")
                        param_key = "EXIF-Exif-37510"
                    except UnicodeDecodeError as e:
                        debug_info.append(f"Debug: UTF-16LE fehlgeschlagen: {e}")
                        encodings = [
                            ("utf-16be", "UTF-16BE"),
                            ("utf-8", "UTF-8"),
                            ("latin-1", "Latin-1")
                        ]
                        for encoding, name in encodings:
                            try:
                                full_text = text_bytes.decode(encoding, errors="strict")
                                debug_info.append(f"Debug: Erfolgreiche Dekodierung mit {name}: {repr(full_text)[:100]}...")
                                debug_info.append(f"Debug: Erste 10 Zeichen: {repr(full_text[:10])}")
                                param_key = f"EXIF-Exif-37510 ({name})"
                                break
                            except UnicodeDecodeError:
                                debug_info.append(f"Debug: {name} fehlgeschlagen.")
                        else:
                            cleaned_bytes = text_bytes.replace(b"\x00", b"")
                            full_text = cleaned_bytes.decode("latin-1")
                            debug_info.append(f"Debug: Fallback (Latin-1 nach \x00-Entfernung): {repr(full_text)[:100]}...")
                            debug_info.append(f"Debug: Erste 10 Zeichen: {repr(full_text[:10])}")
                            param_key = "EXIF-Exif-37510 (Fallback)"
                else:
                    full_text = user_comment.decode("latin-1")
                    debug_info.append(f"Debug: Kein UNICODE-Präfix, dekodiert als Latin-1: {repr(full_text)[:100]}...")
                    debug_info.append(f"Debug: Erste 10 Zeichen: {repr(full_text[:10])}")
                    param_key = "EXIF-Exif-37510 (No UNICODE)"
            if not full_text:
                debug_info.append("Debug: Kein UserComment-Tag gefunden oder kein Byte-Daten.")
        except Exception as e:
            debug_info.append(f"Debug: Fehler beim Auslesen der EXIF-Daten: {e}")
    else:
        for key, value in info.items():
            if "parameters" in key.lower():
                param_key = key
                full_text = str(value)
                debug_info.append(f"Debug: PNG-Text aus {param_key}: {repr(full_text)[:100]}...")
                debug_info.append(f"Debug: Erste 10 Zeichen: {repr(full_text[:10])}")
                break
    
    if not full_text:
        debug_info.append(f"Debug: Kein Schlüssel mit {'UNICODE' if is_jpeg else 'parameters'} gefunden.")
        if hasattr(ImageManagerForm, 'instance'):
            ImageManagerForm.instance.debug_info = "\n".join(debug_info)
        return "", "", ""
    
    idx_neg = full_text.find("Negative prompt:")
    idx_steps = full_text.find("Steps:")

    if idx_neg != -1:
        prompt = full_text[:idx_neg].strip()
    elif idx_steps != -1:
        prompt = full_text[:idx_steps].strip()
    else:
        prompt = full_text.strip()

    if idx_neg != -1:
        if idx_steps != -1 and idx_steps > idx_neg:
            negativ = full_text[idx_neg + len("Negative prompt:"):idx_steps].strip()
        else:
            negativ = full_text[idx_neg + len("Negative prompt:"):].strip()
    else:
        negativ = ""

    if idx_steps != -1:
        settings = full_text[idx_steps + len("Steps:"):].strip()
    else:
        settings = ""

    debug_info.extend([
        f"Debug: Prompt: {repr(prompt)[:50]}...",
        f"Debug: Negativ: {repr(negativ)[:50]}...",
        f"Debug: Settings: {repr(settings)[:50]}..."
    ])

    if hasattr(ImageManagerForm, 'instance'):
        ImageManagerForm.instance.debug_info = "\n".join(debug_info)
    
    return prompt, negativ, settings

# Der Rest des Codes bleibt unverändert, nur die extract_text_chunks-Funktion wurde angepasst.
# Hier wird der restliche Code aus deinem Original übernommen...

class ImageManagerForm(TkinterDnD.Tk):
    instance = None

    def __init__(self):
        super().__init__()
        ImageManagerForm.instance = self
        self.title(f"ImagePromptViewer (Version {VERSION})")
        self.configure(bg=BG_COLOR)
        
        self.monitor_list = get_monitors()
        self.selected_monitor = self.monitor_list[0]
        self.fullscreen_monitor = self.selected_monitor

        self.scaling_factor = get_scaling_factor(self.selected_monitor)
        self.main_font_size = get_font_size(self.selected_monitor)
        self.button_padding = get_button_padding(self.selected_monitor)

        window_width, window_height = get_window_size(self.selected_monitor)
        self.geometry(f"{window_width}x{window_height}")
        self.resizable(True, True)
        self.attributes("-topmost", False)

        self.bind("<Configure>", self.on_window_move)

        self.folder_images = []
        self.filtered_images = []
        self.current_index = -1
        self.search_subfolders_var = tk.BooleanVar(value=False)
        self.sort_order = "DESC"
        self.preview_images = {}
        self.fullscreen_win = None
        self.debug_info = ""
        self.filter_history = deque(maxlen=10)

        self.ctime_cache = {}
        self.text_chunks_cache = {}

        self.delete_immediately_main_var = tk.BooleanVar(value=False)
        self.delete_immediately_fs_var = tk.BooleanVar(value=False)

        self.filter_var = tk.StringVar()
        self.filter_filename_var = tk.BooleanVar(value=False)
        self.filter_prompt_var = tk.BooleanVar(value=True)
        self.filter_negativ_var = tk.BooleanVar(value=False)
        self.filter_settings_var = tk.BooleanVar(value=False)

        self.bind("<KeyPress-Right>", lambda e: self.show_next_image())
        self.bind("<KeyPress-Left>", lambda e: self.show_previous_image())
        self.bind("<F11>", lambda e: self.safe_close_fullscreen())
        self.bind("<Delete>", self.handle_delete_key)

        self.setup_ui()
        self.update_scaling()

    # Der restliche Code (update_scaling, setup_ui, etc.) bleibt wie im Original und wird hier nicht wiederholt...

if __name__ == "__main__":
    app = ImageManagerForm()
    app.mainloop()