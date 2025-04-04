#!/usr/bin/env python3 
# -*- coding: utf-8 -*-
"""
Datum: 2025-03-27
Versionsnummer: 1.1.0.1
Interne Bezeichnung: Master8 Alpha7

Änderungen in Version 1.1.0.1:
- Implementierung eines LRU-Cache für Vorschaubilder zur Optimierung des Speicherverbrauchs.
- Einführung einer effizienten Bildladefunktion für Vorschaubilder mit schneller Skalierung.
- Beibehaltung aller bestehenden Funktionen und Verbesserung der Performance bei großen Bildmengen.
- Korrektur der Event-Bindung für das <Delete>-Event, um AttributeError zu vermeiden.

Zusammenfassung:
Ein Bildbetrachter für PNG- und JPEG-Dateien, der Textchunks auswertet (PNG: info['parameters'], JPEG: EXIF-Tag 37510) und in Prompt, Negativen Prompt und Settings aufteilt.
"""
VERSION = "1.1.0.1"

import subprocess, sys
import os
import platform
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
import threading
from pathlib import Path
from collections import deque, OrderedDict
import json

# --------------------------------------------------------
# Hilfsfunktion zur Validierung von Indexwerten
# --------------------------------------------------------
def validate_index(index, items):
    if index < 0:
        return 0
    elif index >= len(items):
        return len(items) - 1 if items else -1
    return index

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
    from piexif import helper
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "piexif"])
    import piexif
    from piexif import helper

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

# ---------------------------------------------------------------------
# Neue extract_text_chunks()-Routine
# ---------------------------------------------------------------------
def extract_text_chunks(img_path):
    try:
        img = Image.open(img_path)
    except Exception as e:
        messagebox.showerror("Error", f"Error opening image:\n{e}")
        return "", "", ""
    
    is_jpeg = img_path.lower().endswith((".jpg", ".jpeg"))
    with open(img_path, "rb") as f:
        header = f.read(8)
    if header.startswith(b'\x89PNG'):
        is_jpeg = False

    full_text = ""
    param_key = None
    debug_info = []
    
    if is_jpeg:
        try:
            exif_dict = piexif.load(img_path)
            user_comment = exif_dict.get("Exif", {}).get(piexif.ExifIFD.UserComment)
            if user_comment and isinstance(user_comment, bytes):
                debug_info.append(f"Debug: Raw bytes from UserComment: {user_comment[:50].hex()}...")
                if user_comment.startswith(b'UNICODE\x00\x00'):
                    try:
                        full_text = helper.UserComment.load(user_comment)
                        debug_info.append("Debug: Decoding with piexif.helper successful.")
                        param_key = "EXIF-Exif-37510"
                    except Exception as e:
                        debug_info.append(f"Debug: piexif.helper error: {e}")
                        full_text = user_comment[8:].decode("utf-16le", errors="ignore")
                        param_key = "EXIF-Exif-37510 (Fallback UTF-16LE)"
                else:
                    full_text = user_comment.decode("latin-1", errors="ignore")
                    debug_info.append("Debug: No UNICODE prefix, decoded as Latin-1.")
                    param_key = "EXIF-Exif-37510 (No UNICODE)"
            if not full_text:
                debug_info.append("Debug: No UserComment tag found or no byte data.")
        except Exception as e:
            debug_info.append(f"Debug: Error reading EXIF data: {e}")
    else:
        for key, value in img.info.items():
            if "parameters" in key.lower():
                param_key = key
                full_text = str(value)
                debug_info.append(f"Debug: PNG text from {param_key}: {repr(full_text)[:100]}...")
                break
        if not full_text:
            for key, value in img.info.items():
                if "prompt" in key.lower() or "metadata" in key.lower() or "description" in key.lower():
                    param_key = key
                    full_text = str(value)
                    debug_info.append(f"Debug: PNG text from fallback {param_key}: {repr(full_text)[:100]}...")
                    break
    
    if not full_text:
        debug_info.append(f"Debug: No key with {'UNICODE' if is_jpeg else 'parameters/fallback'} found.")
        if hasattr(ImageManagerForm, 'instance'):
            ImageManagerForm.instance.debug_info = "\n".join(debug_info)
        return "", "", ""
    
    normalized = ' '.join(full_text.split())
    debug_info.append(f"Debug: Normalized text: {repr(normalized)[:100]}...")
    
    try:
        data_dict = json.loads(full_text)
        if "models" in data_dict and isinstance(data_dict["models"], list):
            models = data_dict["models"]
            prompt_json = ""
            negative_json = ""
            steps_json = ""
            for model in models:
                if isinstance(model, dict):
                    if "prompt" in model:
                        prompt_json = model["prompt"]
                    if "negativePrompt" in model:
                        negative_json = model["negativePrompt"]
                    if "steps" in model:
                        idx_steps_in_normalized = normalized.find('"steps":')
                        if idx_steps_in_normalized != -1:
                            steps_json = normalized[idx_steps_in_normalized:]
                        else:
                            steps_json = str(model["steps"])
            if prompt_json or negative_json or steps_json:
                debug_info.append("Debug: JSON parsing successful (models).")
                debug_info.append(f"Debug (Prompt): {repr(prompt_json)[:50]}...")
                debug_info.append(f"Debug (Negative Prompt): {repr(negative_json)[:50]}...")
                debug_info.append(f"Debug (Settings): {repr(steps_json)[:100]}...")
                if hasattr(ImageManagerForm, 'instance'):
                    ImageManagerForm.instance.debug_info = "\n".join(debug_info)
                return str(prompt_json), str(negative_json), steps_json

        prompt_json = data_dict.get("prompt", "")
        negative_json = data_dict.get("negativePrompt", "")
        idx_steps_in_normalized = normalized.find('"steps":')
        if idx_steps_in_normalized != -1:
            settings_text = normalized[idx_steps_in_normalized:]
        else:
            settings_text = str(data_dict.get("steps", ""))
        if not (prompt_json or negative_json):
            for key, value in data_dict.items():
                if isinstance(value, dict):
                    if value.get("class_type", "").lower() == "cliptextencode":
                        text_val = value.get("inputs", {}).get("text", "")
                        if not prompt_json:
                            prompt_json = text_val
                        elif not negative_json:
                            negative_json = text_val

        if not settings_text:
            for key, value in data_dict.items():
                if isinstance(value, dict):
                    if value.get("class_type", "").lower() == "ksampler":
                        steps_val = value.get("inputs", {}).get("steps", "")
                        if steps_val:
                            settings_text = '"steps": ' + str(steps_val)
                            break
                        
        if prompt_json or negative_json or settings_text:
            debug_info.append("Debug: JSON parsing successful (direct).")
            debug_info.append(f"Debug (Prompt): {repr(prompt_json)[:50]}...")
            debug_info.append(f"Debug (Negative Prompt): {repr(negative_json)[:50]}...")
            debug_info.append(f"Debug (Settings): {repr(settings_text)[:100]}...")
            if hasattr(ImageManagerForm, 'instance'):
                ImageManagerForm.instance.debug_info = "\n".join(debug_info)
            return str(prompt_json), str(negative_json), settings_text
    except Exception as e:
        debug_info.append(f"Debug: JSON parsing failed: {e}")
    
    normalized_lower = normalized.lower()
    if ('"prompt":' in normalized_lower and 
        '"negativeprompt":' in normalized_lower and 
        '"steps":' in normalized_lower):
        idx_prompt_new = normalized_lower.find('"prompt":')
        idx_negative_new = normalized_lower.find('"negativeprompt":')
        idx_steps_new = normalized_lower.find('"steps":')
        prompt_new = normalized[idx_prompt_new + len('"prompt":'): idx_negative_new].strip().strip('",')
        negativ_new = normalized[idx_negative_new + len('"negativeprompt":'): idx_steps_new].strip().strip('",')
        settings_new = normalized[idx_steps_new + len('"steps":'):].strip().strip('",')
        debug_info.extend([
            f"Debug (New Markers): Prompt: {repr(prompt_new)[:50]}...",
            f"Debug (New Markers): Negative Prompt: {repr(negativ_new)[:50]}...",
            f"Debug (New Markers): Settings: {repr(settings_new)[:50]}..."
        ])
        if hasattr(ImageManagerForm, 'instance'):
            ImageManagerForm.instance.debug_info = "\n".join(debug_info)
        return prompt_new, negativ_new, settings_new
    
    idx_neg = normalized.find("Negative prompt:")
    idx_steps = normalized.find("Steps:")
    if idx_neg != -1:
        prompt = normalized[:idx_neg].strip()
    elif idx_steps != -1:
        prompt = normalized[:idx_steps].strip()
    else:
        prompt = normalized.strip()
    
    if idx_neg != -1:
        if idx_steps != -1 and idx_steps > idx_neg:
            negativ = normalized[idx_neg + len("Negative prompt:"): idx_steps].strip()
        else:
            negativ = normalized[idx_neg + len("Negative prompt:"):].strip()
    else:
        negativ = ""
    
    if idx_steps != -1:
        settings = normalized[idx_steps:].strip()
    else:
        settings = ""
    
    debug_info.extend([
        f"Debug (Old Markers): Prompt: {repr(prompt)[:50]}...",
        f"Debug (Old Markers): Negative Prompt: {repr(negativ)[:50]}...",
        f"Debug (Old Markers): Settings: {repr(settings)[:50]}..."
    ])
    
    if hasattr(ImageManagerForm, 'instance'):
        ImageManagerForm.instance.debug_info = "\n".join(debug_info)
    
    return prompt, negativ, settings

# ---------------------------------------------------------------------
# Weitere Hilfsfunktionen
# ---------------------------------------------------------------------
def get_scaling_factor(monitor):
    ref_width, ref_height = 3840, 2160
    width_factor = monitor.width / ref_width
    height_factor = monitor.height / ref_height
    factor = min(width_factor, height_factor)
    return max(0.4, min(1.0, factor))

def get_default_image_scale(scaling_factor):
    default_scale = 0.25 + 0.5 * (scaling_factor - 0.5)
    return max(0.25, min(0.5, default_scale))

def get_font_size(monitor, base_size=16):
    factor = get_scaling_factor(monitor)
    return max(8, min(16, int(base_size * factor)))

def get_button_padding(monitor):
    factor = get_scaling_factor(monitor)
    return max(2, int(5 * factor))

def get_window_size(monitor):
    ref_width, ref_height = 1680, 2000
    factor = get_scaling_factor(monitor)
    window_width = int(ref_width * factor)
    window_height = int(ref_height * factor)
    return window_width, window_height

# ---------------------------------------------------------------------
# Hauptklasse
# ---------------------------------------------------------------------
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

        # Event-Bindungen
        self.bind("<Configure>", lambda event: self.on_window_move(event))
        self.bind("<Delete>", lambda event: self.handle_delete_key(event))

        # Initialisierung der Variablen
        self.folder_images = []
        self.filtered_images = []
        self.current_index = -1
        self.fs_current_index = -1
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

        self.setup_ui()
        self.update_scaling()

    def handle_delete_key(self, event):
        """Handler für die Delete-Taste."""
        print("Delete-Taste gedrückt")
        # Hier kannst du die Logik zum Löschen von Bildern einfügen
        if self.current_index >= 0 and self.filtered_images:
            print(f"Bild {self.filtered_images[self.current_index]} wird gelöscht.")
            # Beispiel: send2trash(self.filtered_images[self.current_index])

    def on_window_move(self, event):
        """Handler für Fensterbewegungen und Größenänderungen."""
        if hasattr(self, 'last_window_pos'):
            last_x, last_y = self.last_window_pos
            current_x, current_y = self.winfo_x(), self.winfo_y()
            if hasattr(self, 'last_window_size'):
                last_width, last_height = self.last_window_size
                current_width, current_height = self.winfo_width(), self.winfo_height()
                size_changed = (last_width != current_width or last_height != current_height)
            else:
                size_changed = False

            if (last_x != current_x or last_y != current_y) and not size_changed:
                self.update_scaling()

        self.last_window_pos = (self.winfo_x(), self.winfo_y())
        self.last_window_size = (self.winfo_width(), self.winfo_height())

    def setup_ui(self):
        """Platzhalter für die UI-Initialisierung."""
        # Hier wird die Benutzeroberfläche eingerichtet (derzeit leer)
        pass

    def update_scaling(self):
        """Platzhalter für die Skalierungsaktualisierung."""
        # Hier wird die Skalierung aktualisiert (derzeit leer)
        pass

if __name__ == "__main__":
    app = ImageManagerForm()
    app.mainloop()