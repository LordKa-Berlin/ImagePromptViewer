#!/usr/bin/env python3  
# -*- coding: utf-8 -*-
"""
Datum: 2025-03-31
Versionsnummer: 1.2.1.a
Interne Bezeichnung: Master8 Alpha9

Änderungen in Version 1.2.1.a:
- Ersetzen der bisherigen Prompt-Filter-Checkbuttons durch ein Radio-Button-Widget mit den vier Modi:
  "All words", "Any word", "Exclude", "None of the words".
- Integration zusätzlicher Datum- und File Size Filter im Filter-Settings-Formular.
- Die Filterlogik in apply_filters() wurde angepasst, sodass nun alle aktiven Filterbedingungen (inkl. der Einstellungen aus dem Filter Settings Formular und des Hauptformulars) logisch UND-verknüpft werden.
- Der Reset All Button setzt nun alle Filter, auch die Filter Combo im Hauptformular, zurück.
- Im Filter Settings Formular wurde ein Schließen-Button eingefügt.
- Der Filter Settings Button im Hauptformular wurde dynamisch an die Monitorauflösung angepasst.
- Hinweis: Created by Lordka.
  
Zusammenfassung:
Ein Bildbetrachter für PNG- und JPEG-Dateien, der Textchunks auswertet (PNG: info['parameters'], JPEG: EXIF-Tag 37510) und in Prompt, Negative Prompt und Settings aufteilt. Neu: Erweiterte Filterfunktionen, die sowohl über das Filter Combo-Feld im Hauptformular als auch über die erweiterten Einstellungen im Filter Settings Fenster angewendet werden.
"""

VERSION = "1.2.1.a"
HISTORY_FILE = "ImagePromptViewer-History.json"

import subprocess, sys, os, re, platform
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
TEXT_BG_COLOR = "#000000"  # Textfeld-Hintergrundfarbe
TEXT_FG_COLOR = "#FFA500"
HIGHLIGHT_COLOR = "#FF5555"
BUTTON_BG_COLOR = "#FFA500"
BUTTON_FG_COLOR = "#000000"

SCALE_OPTIONS = ["Default", "25%", "50%", "75%"]
DEFAULT_SCALE = "Default"
IMAGE_EXTENSIONS = (".png", ".PNG", ".jpg", ".JPG", ".jpeg", ".JPEG")

def get_datetime_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def copy_to_clipboard(widget, text):
    widget.clipboard_clear()
    widget.clipboard_append(text)
    widget.update()

def load_image_with_cache(file_path, cache_dict, cache_limit):
    if file_path in cache_dict:
        cache_dict.move_to_end(file_path)
        return cache_dict[file_path]
    try:
        img = Image.open(file_path)
        cache_dict[file_path] = img
        if len(cache_dict) > cache_limit:
            cache_dict.popitem(last=False)  # ältestes Bild entfernen
        return img
    except Exception as e:
        print(f"Fehler beim Laden von {file_path}: {e}")
        return None

# Neue Funktion: Vergleicht Text und Keyword – optional als ganzes Wort
def match_keyword(text, keyword, whole_word):
    if whole_word:
        return re.search(r'\b' + re.escape(keyword) + r'\b', text) is not None
    else:
        return keyword in text

# ---------------------------------------------------------------------
# extract_text_chunks()-Routine (Integration von PromptSlicer + Prüfung des File-Headers)
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
# Restlicher Code (unverändert bis auf sichtbare Texte und erweiterte Filterlogik)
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

class ImageManagerForm(TkinterDnD.Tk):
    instance = None

    def __init__(self):
        super().__init__()
        ImageManagerForm.instance = self
        self.title(f"ImagePromptViewer (Version {VERSION} - Created by Lordka.)")
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
        self.image_cache = OrderedDict()
        self.cache_limit = 50  # Anzahl zwischengespeicherter Bilder
        self.current_index = -1
        self.fs_current_index = -1
        self.search_subfolders_var = tk.BooleanVar(value=False)
        self.sort_order = "DESC"
        self.preview_images = {}
        self.fullscreen_win = None
        self.debug_info = ""
        self.filter_history = deque(maxlen=10)
        self.folder_history = []
        self.filter_history_list = []
        history_data = load_history()
        self.folder_history = history_data.get("folder_history", [])
        self.filter_history_list = history_data.get("filter_history", [])

        self.ctime_cache = {}
        self.text_chunks_cache = {}

        self.delete_immediately_main_var = tk.BooleanVar(value=False)
        self.delete_immediately_fs_var = tk.BooleanVar(value=False)

        self.filter_var = tk.StringVar()
        self.filter_filename_var = tk.BooleanVar(value=False)
        self.filter_prompt_var = tk.BooleanVar(value=True)
        self.filter_negativ_var = tk.BooleanVar(value=False)
        self.filter_settings_var = tk.BooleanVar(value=False)
        # Neues Kontrollfeld: Whole Word
        self.whole_word_var = tk.BooleanVar(value=False)

        self.bind("<KeyPress-Right>", lambda e: self.show_next_image())
        self.bind("<KeyPress-Left>", lambda e: self.show_previous_image())
        self.bind("<F11>", lambda e: self.safe_close_fullscreen())
        self.bind("<Delete>", self.handle_delete_key)

        self.setup_ui()
        self.update_scaling()

    def update_scaling(self):
        window_x = self.winfo_x()
        window_y = self.winfo_y()
        self.selected_monitor = None
        for monitor in self.monitor_list:
            if (monitor.x <= window_x < monitor.x + monitor.width and
                monitor.y <= window_y < monitor.y + monitor.height):
                self.selected_monitor = monitor
                break
        if not self.selected_monitor:
            self.selected_monitor = self.monitor_list[0]

        self.scaling_factor = get_scaling_factor(self.selected_monitor)
        self.main_font_size = get_font_size(self.selected_monitor)
        self.button_padding = get_button_padding(self.selected_monitor)

        window_width, window_height = get_window_size(self.selected_monitor)
        self.geometry(f"{window_width}x{window_height}")

        self.update_ui()

    def on_window_move(self, event):
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
        for widget in self.winfo_children():
            widget.destroy()

        header_font = ("Arial", self.main_font_size)
        header_text = f"ImagePromptViewer\nVersion: {VERSION} - Created by Lordka."
        self.header_label = tk.Label(self, text=header_text, fg=TEXT_FG_COLOR, bg=BG_COLOR,
                                     font=header_font, justify="left")
        self.header_label.pack(anchor="w", padx=self.button_padding, pady=self.button_padding)

        status_font = ("Arial", self.main_font_size)
        self.status_text = ScrolledText(self, height=2, bg=BG_COLOR, fg=TEXT_FG_COLOR, font=status_font)
        self.status_text.pack(fill="x", padx=self.button_padding, pady=self.button_padding)
        self.status("Form started.")

        self.always_on_top_var = tk.BooleanVar(value=False)
        self.top_checkbox = tk.Checkbutton(self, text="Always on Top", variable=self.always_on_top_var,
                                           command=self.update_topmost, fg=TEXT_FG_COLOR,
                                           bg=BG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size))
        self.top_checkbox.place(relx=1.0, y=self.button_padding, anchor="ne")

        self.debug_button = tk.Button(self, text="Debug", command=self.show_debug_info,
                                      bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size), width=6)
        self.debug_button.place(relx=0.85, y=self.button_padding, anchor="ne")

        self.info_button = tk.Button(self, text="?", command=self.show_info,
                                     bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size), width=2)
        self.info_button.place(relx=0.90, y=self.button_padding, anchor="ne")

        small_info_font = ("Arial", int(self.main_font_size * 0.9))
        self.image_info_label = tk.Label(self, text="", fg=TEXT_FG_COLOR, bg=BG_COLOR,
                                         font=small_info_font, justify="left")
        self.image_info_label.pack(side="top", anchor="w", pady=self.button_padding)

        filter_frame = tk.Frame(self, bg=BG_COLOR)
        filter_frame.pack(fill="x", padx=self.button_padding, pady=self.button_padding)
        self.filter_button = tk.Button(filter_frame, text="Filter", command=self.apply_filter,
                                       bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size), width=6)
        self.filter_button.pack(side="left", padx=self.button_padding)
        
        style = ttk.Style()
        combo_font_size = int(self.main_font_size * 2.2)
        style.configure("Custom.TCombobox", font=("Arial", combo_font_size))
        folder_combo_font_size = int(self.main_font_size * 0.9)
        style.configure("Folder.TCombobox", font=("Arial", folder_combo_font_size))
        self.filter_combo = ttk.Combobox(filter_frame, textvariable=self.filter_var, style="Custom.TCombobox", width=25)
        self.filter_combo['values'] = self.filter_history_list
        self.filter_combo.pack(side="left", padx=self.button_padding)
        self.filter_combo.bind("<Return>", lambda e: self.apply_filter())
        self.clear_button = tk.Button(filter_frame, text="Clear", command=self.clear_filter,
                                      bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size), width=5)
        self.clear_button.pack(side="left", padx=self.button_padding)
        self.filter_settings_button = tk.Button(
            filter_frame, text="Filter Settings", command=self.open_filter_settings,
            bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", int(self.main_font_size * 0.9))
        )
        self.filter_settings_button.pack(side="left", padx=self.button_padding)

        # Neues Kontrollfeld: Whole Word (vor Filename)
        self.whole_word_cb = tk.Checkbutton(filter_frame, text="Whole Word", variable=self.whole_word_var,
                                             fg=TEXT_FG_COLOR, bg=BG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size))
        self.whole_word_cb.pack(side="left", padx=self.button_padding)

        self.filter_filename_cb = tk.Checkbutton(filter_frame, text="Filename", variable=self.filter_filename_var, command=self.apply_filter,
                                                 fg=TEXT_FG_COLOR, bg=BG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size))
        self.filter_filename_cb.pack(side="left", padx=self.button_padding)
        self.filter_prompt_cb = tk.Checkbutton(filter_frame, text="Prompt", variable=self.filter_prompt_var, command=self.apply_filter,
                                               fg=TEXT_FG_COLOR, bg=BG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size))
        self.filter_prompt_cb.pack(side="left", padx=self.button_padding)
        self.filter_negativ_cb = tk.Checkbutton(filter_frame, text="Negative Prompt", variable=self.filter_negativ_var, command=self.apply_filter,
                                                fg=TEXT_FG_COLOR, bg=BG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size))
        self.filter_negativ_cb.pack(side="left", padx=self.button_padding)
        self.filter_settings_cb = tk.Checkbutton(filter_frame, text="Settings", variable=self.filter_settings_var, command=self.apply_filter,
                                                 fg=TEXT_FG_COLOR, bg=BG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size))
        self.filter_settings_cb.pack(side="left", padx=self.button_padding)
        
        self.image_counter_frame = tk.Frame(filter_frame, bg=BG_COLOR)
        self.image_counter_frame.pack(side="left", padx=self.button_padding)
        self.image_counter_label = tk.Label(self.image_counter_frame, text="Folder: 0 images filtered ", fg=TEXT_FG_COLOR, bg=BG_COLOR, font=("Arial", self.main_font_size))
        self.image_counter_label.pack(side="left")
        self.filtered_counter_label = tk.Label(self.image_counter_frame, text="0", fg="red", bg=BG_COLOR, font=("Arial", self.main_font_size))
        self.filtered_counter_label.pack(side="left")
        self.image_counter_suffix_label = tk.Label(self.image_counter_frame, text=" images", fg=TEXT_FG_COLOR, bg=BG_COLOR, font=("Arial", self.main_font_size))
        self.image_counter_suffix_label.pack(side="left")

        folder_frame = tk.Frame(self, bg=BG_COLOR)
        folder_frame.pack(fill="x", padx=self.button_padding, pady=self.button_padding)
        folder_label = tk.Label(folder_frame, text="Folder path:", fg=TEXT_FG_COLOR, bg=BG_COLOR, font=("Arial", self.main_font_size))
        folder_label.pack(side="left", padx=self.button_padding)
        self.folder_path_var = tk.StringVar()
        visible_chars = max(20, int(25 * self.scaling_factor))
        self.folder_combo = ttk.Combobox(folder_frame, textvariable=self.folder_path_var,
                                         values=self.folder_history, width=visible_chars,
                                         style="Folder.TCombobox")
        self.folder_combo.set("")
        self.folder_combo.pack(side="left", padx=self.button_padding)
        self.folder_combo.bind("<<ComboboxSelected>>", lambda e: threading.Thread(
            target=self.load_folder_async, args=(self.folder_path_var.get(),), daemon=True).start())
        self.choose_folder_button = tk.Button(folder_frame, text="Select folder", command=self.choose_folder,
                                              bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        self.choose_folder_button.pack(side="left", padx=self.button_padding)
        self.select_image_button = tk.Button(folder_frame, text="Select image", command=self.select_image_from_folder,
                                             bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        self.select_image_button.pack(side="left", padx=self.button_padding)
        self.open_image_button = tk.Button(folder_frame, text="View image", command=self.open_image_in_system,
                                           bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        self.open_image_button.pack(side="left", padx=self.button_padding)
        self.delete_button_main = tk.Button(folder_frame, text="Delete image", command=self.delete_current_image,
                                            bg=BTN_BG_COLOR if not self.delete_immediately_main_var.get() else "red", fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        self.delete_button_main.pack(side="right", padx=self.button_padding)
        self.delete_immediately_main_cb = tk.Checkbutton(folder_frame, text="delete immediately", variable=self.delete_immediately_main_var,
                                                         command=self.update_delete_button_color_main, fg=TEXT_FG_COLOR,
                                                         bg=BG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size))
        self.delete_immediately_main_cb.pack(side="right", padx=self.button_padding)

        subfolder_frame = tk.Frame(self, bg=BG_COLOR)
        subfolder_frame.pack(fill="x", padx=self.button_padding, pady=self.button_padding)
        self.subfolder_cb = tk.Checkbutton(subfolder_frame, text="Search subfolders", variable=self.search_subfolders_var,
                                           fg=TEXT_FG_COLOR, bg=BG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size))
        self.subfolder_cb.pack(side="left", padx=self.button_padding)
        self.sort_button = tk.Button(subfolder_frame, text="ASC" if self.sort_order == "DESC" else "DESC",
                                     command=self.toggle_sort_order, bg=BTN_BG_COLOR, fg=BTN_FG_COLOR,
                                     font=("Arial", self.main_font_size), width=5)
        self.sort_button.pack(side="left", padx=self.button_padding)

        self.image_frame = tk.Frame(self, bg=BG_COLOR)
        self.image_frame.pack(fill="both", expand=True, padx=self.button_padding, pady=self.button_padding)
        self.image_label = tk.Label(self.image_frame, bg=BG_COLOR)
        self.image_label.grid(row=0, column=0, padx=self.button_padding, pady=self.button_padding, sticky="nsew")
        self.image_label.bind("<Button-1>", lambda e: self.show_fullscreen())
        self.image_label.bind("<MouseWheel>", self.on_image_mousewheel)
        self.drop_canvas = tk.Canvas(self.image_frame, width=int(150 * self.scaling_factor), height=int(112 * self.scaling_factor),
                                     bg="#555555", highlightthickness=2, highlightbackground="white")
        self.drop_canvas.create_text(int(75 * self.scaling_factor), int(56 * self.scaling_factor),
                                     text="Drop Image Here", fill="white", font=("Arial", self.main_font_size))
        self.drop_canvas.grid(row=0, column=1, padx=self.button_padding, pady=self.button_padding, sticky="e")
        self.drop_canvas.drop_target_register(DND_FILES)
        self.drop_canvas.dnd_bind('<<Drop>>', self.handle_drop)
        self.image_frame.grid_columnconfigure(0, weight=1)
        self.image_frame.grid_columnconfigure(1, weight=0)

        nav_frame = tk.Frame(self, bg=BG_COLOR)
        nav_frame.pack(pady=self.button_padding)
        self.back_button = tk.Button(nav_frame, text="Back", command=self.show_previous_image,
                                     bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size), width=10)
        self.back_button.pack(side="left", padx=self.button_padding)
        self.next_button = tk.Button(nav_frame, text="Next", command=self.show_next_image,
                                     bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size), width=10)
        self.next_button.pack(side="left", padx=self.button_padding)

        controls_frame = tk.Frame(self, bg=BG_COLOR)
        controls_frame.pack(pady=self.button_padding)
        self.scale_var = tk.StringVar(value=DEFAULT_SCALE)
        self.scale_dropdown = tk.OptionMenu(controls_frame, self.scale_var, *SCALE_OPTIONS, command=lambda value: self.rescale_image(value))
        self.scale_dropdown.configure(bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", int(self.main_font_size + 2 * self.scaling_factor)))
        self.scale_dropdown.pack(side="left", padx=self.button_padding)
        self.fullscreen_button = tk.Button(controls_frame, text="Fullscreen", command=self.show_fullscreen,
                                           bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        self.fullscreen_button.pack(side="left", padx=self.button_padding)
        if len(self.monitor_list) > 1:
            self.monitor_choice = tk.StringVar()
            monitor_names = [f"Monitor {i}: {mon.width}x{mon.height}" for i, mon in enumerate(self.monitor_list)]
            self.monitor_choice.set(monitor_names[0])
            self.monitor_menu = tk.OptionMenu(controls_frame, self.monitor_choice, *monitor_names,
                                              command=self.update_fullscreen_monitor)
            self.monitor_menu.configure(bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", int(self.main_font_size + 2 * self.scaling_factor)))
            self.monitor_menu.pack(side="left", padx=self.button_padding)

        textchunks_frame = tk.Frame(self, bg=BG_COLOR)
        textchunks_frame.pack(fill="x", padx=self.button_padding, pady=self.button_padding)
        self.prompt_text = ScrolledText(textchunks_frame, height=8, bg=TEXT_BG_COLOR,
                                        fg=TEXT_FG_COLOR, font=("Arial", self.main_font_size))
        self.prompt_text.grid(row=0, column=0, padx=self.button_padding, pady=self.button_padding, sticky="nsew")
        self.copy_prompt_button = tk.Button(textchunks_frame, text="copy Prompt",
                                            command=lambda: copy_to_clipboard(self, self.prompt_text.get("1.0", tk.END)),
                                            bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        self.copy_prompt_button.grid(row=1, column=0, padx=self.button_padding, pady=self.button_padding)
        self.negativ_text = ScrolledText(textchunks_frame, height=8, bg=TEXT_BG_COLOR,
                                         fg=TEXT_FG_COLOR, font=("Arial", self.main_font_size))
        self.negativ_text.grid(row=0, column=1, padx=self.button_padding, pady=self.button_padding, sticky="nsew")
        self.copy_negativ_button = tk.Button(textchunks_frame, text="copy Negative",
                                             command=lambda: copy_to_clipboard(self, self.negativ_text.get("1.0", tk.END)),
                                             bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        self.copy_negativ_button.grid(row=1, column=1, padx=self.button_padding, pady=self.button_padding)
        self.settings_text = ScrolledText(textchunks_frame, height=8, bg=TEXT_BG_COLOR,
                                          fg=TEXT_FG_COLOR, font=("Arial", self.main_font_size))
        self.settings_text.grid(row=0, column=2, padx=self.button_padding, pady=self.button_padding, sticky="nsew")
        self.copy_settings_button = tk.Button(textchunks_frame, text="copy Settings",
                                              command=lambda: copy_to_clipboard(self, self.settings_text.get("1.0", tk.END)),
                                              bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        self.copy_settings_button.grid(row=1, column=2, padx=self.button_padding, pady=self.button_padding)
        for i in range(3):
            textchunks_frame.grid_columnconfigure(i, weight=1)
    
        self.load_list_button = tk.Button(self, text="Load folder list", command=self.toggle_folder_list,
                                        bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        self.load_list_button.pack(pady=self.button_padding)

        self.preview_frame = tk.Frame(self, bg=BG_COLOR)
        self.preview_canvas = tk.Canvas(self.preview_frame, bg=BG_COLOR, highlightthickness=0)
        self.preview_canvas.pack(side="left", fill="both", expand=True)
        self.preview_scrollbar = tk.Scrollbar(self.preview_frame, orient="vertical", command=self.preview_canvas.yview)
        self.preview_scrollbar.pack(side="right", fill="y")
        self.preview_canvas.configure(yscrollcommand=self.preview_scrollbar.set)
        self.preview_inner_frame = tk.Frame(self.preview_canvas, bg=BG_COLOR)
        self.preview_canvas.create_window((0, 0), window=self.preview_inner_frame, anchor="nw")
        self.preview_inner_frame.bind("<Configure>", lambda event: self.preview_canvas.configure(
            scrollregion=self.preview_canvas.bbox("all")
        ))
        self.preview_canvas.bind("<Enter>", lambda e: self.preview_canvas.bind_all("<MouseWheel>", self.on_preview_mousewheel))
        self.preview_canvas.bind("<Leave>", lambda e: self.preview_canvas.unbind_all("<MouseWheel>"))
        self.preview_items = []

        self.status("Form loaded.")

    def open_filter_settings(self):
        if hasattr(self, 'filter_settings_window') and self.filter_settings_window.winfo_exists():
            self.filter_settings_window.lift()
            return

        self.filter_settings_window = tk.Toplevel(self)
        self.filter_settings_window.title("Filter Settings")
        self.filter_settings_window.configure(bg=BG_COLOR)
        self.filter_settings_window.geometry("400x600")

        # --- Prompt Filter Section (Radio-Buttons) ---
        prompt_frame = tk.LabelFrame(self.filter_settings_window, text="Prompt Filter", fg=TEXT_FG_COLOR, bg=BG_COLOR, font=("Arial", int(self.main_font_size * 1.2), "bold"))
        prompt_frame.pack(fill="x", padx=10, pady=5)
        self.prompt_filter_mode = tk.StringVar(value="all")
        modes = [
            ("All words must match", "all"),
            ("Any word", "any"),
            ("Exclude word", "exclude"),
            ("None of the words", "none")
        ]
        for text, mode in modes:
            tk.Radiobutton(prompt_frame, text=text, variable=self.prompt_filter_mode, value=mode,
                           bg=BG_COLOR, fg=TEXT_FG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size)).pack(anchor="w", padx=10)

        # --- Date Filter Section ---
        date_frame = tk.LabelFrame(self.filter_settings_window, text="Date Filter", fg=TEXT_FG_COLOR, bg=BG_COLOR, font=("Arial", int(self.main_font_size * 1.2), "bold"))
        date_frame.pack(fill="x", padx=10, pady=5)
        self.date_between = tk.BooleanVar()
        self.date_not_older_than = tk.BooleanVar()
        self.date_older_than = tk.BooleanVar()
        self.date_this_week = tk.BooleanVar()
        self.date_two_weeks = tk.BooleanVar()
        self.date_four_weeks = tk.BooleanVar()
        self.date_one_month = tk.BooleanVar()
        self.date_one_year = tk.BooleanVar()
        tk.Checkbutton(date_frame, text="Between two dates", variable=self.date_between,
                       bg=BG_COLOR, fg=TEXT_FG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size)).pack(anchor="w", padx=10)
        tk.Checkbutton(date_frame, text="Not older than X days", variable=self.date_not_older_than,
                       bg=BG_COLOR, fg=TEXT_FG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size)).pack(anchor="w", padx=10)
        tk.Checkbutton(date_frame, text="Older than X days", variable=self.date_older_than,
                       bg=BG_COLOR, fg=TEXT_FG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size)).pack(anchor="w", padx=10)
        tk.Checkbutton(date_frame, text="Created this week", variable=self.date_this_week,
                       bg=BG_COLOR, fg=TEXT_FG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size)).pack(anchor="w", padx=10)
        tk.Checkbutton(date_frame, text="Within 2 weeks", variable=self.date_two_weeks,
                       bg=BG_COLOR, fg=TEXT_FG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size)).pack(anchor="w", padx=10)
        tk.Checkbutton(date_frame, text="Within 4 weeks", variable=self.date_four_weeks,
                       bg=BG_COLOR, fg=TEXT_FG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size)).pack(anchor="w", padx=10)
        tk.Checkbutton(date_frame, text="Within 1 month", variable=self.date_one_month,
                       bg=BG_COLOR, fg=TEXT_FG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size)).pack(anchor="w", padx=10)
        tk.Checkbutton(date_frame, text="Within 1 year", variable=self.date_one_year,
                       bg=BG_COLOR, fg=TEXT_FG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size)).pack(anchor="w", padx=10)

        # --- File Size Filter Section ---
        size_frame = tk.LabelFrame(self.filter_settings_window, text="File Size (KB)", fg=TEXT_FG_COLOR, bg=BG_COLOR, font=("Arial", int(self.main_font_size * 1.2), "bold"))
        size_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(size_frame, text="Min:", bg=BG_COLOR, fg=TEXT_FG_COLOR, font=("Arial", self.main_font_size)).grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.entry_min_size = tk.Entry(size_frame, bg="#000000", fg=TEXT_FG_COLOR, insertbackground=TEXT_FG_COLOR, width=10)
        self.entry_min_size.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(size_frame, text="Max:", bg=BG_COLOR, fg=TEXT_FG_COLOR, font=("Arial", self.main_font_size)).grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.entry_max_size = tk.Entry(size_frame, bg="#000000", fg=TEXT_FG_COLOR, insertbackground=TEXT_FG_COLOR, width=10)
        self.entry_max_size.grid(row=1, column=1, padx=5, pady=5)

        # --- Buttons unten (Apply, Clear, Reset All, Close) ---
        button_frame = tk.Frame(self.filter_settings_window, bg=BG_COLOR)
        button_frame.pack(fill="x", pady=15)
        apply_btn = tk.Button(button_frame, text="Apply Filter", command=self.apply_filters,
                              bg=BUTTON_BG_COLOR, fg=BUTTON_FG_COLOR, font=("Arial", self.main_font_size))
        apply_btn.pack(side="left", padx=(20, 10))
        clear_btn = tk.Button(button_frame, text="Clear", command=self.clear_filter_inputs,
                              bg=BUTTON_BG_COLOR, fg=BUTTON_FG_COLOR, font=("Arial", self.main_font_size))
        clear_btn.pack(side="left", padx=(10, 10))
        reset_btn = tk.Button(button_frame, text="Reset All", command=self.reset_all_filters,
                              bg=BUTTON_BG_COLOR, fg=BUTTON_FG_COLOR, font=("Arial", self.main_font_size))
        reset_btn.pack(side="left", padx=(10, 10))
        close_btn = tk.Button(button_frame, text="Close", command=self.filter_settings_window.destroy,
                              bg=BUTTON_BG_COLOR, fg=BUTTON_FG_COLOR, font=("Arial", self.main_font_size))
        close_btn.pack(side="right", padx=(10, 20))

        self.filter_settings_window.resizable(False, False)

    def clear_filter_inputs(self):
        if hasattr(self, 'prompt_filter_mode'):
            self.prompt_filter_mode.set("all")
        for var in [self.date_between, self.date_not_older_than, self.date_older_than, 
                    self.date_this_week, self.date_two_weeks, self.date_four_weeks, 
                    self.date_one_month, self.date_one_year]:
            var.set(False)
        if hasattr(self, 'entry_min_size'):
            self.entry_min_size.delete(0, tk.END)
        if hasattr(self, 'entry_max_size'):
            self.entry_max_size.delete(0, tk.END)

    def reset_all_filters(self):
        self.filter_var.set("")
        self.filter_filename_var.set(False)
        self.filter_prompt_var.set(True)
        self.filter_negativ_var.set(False)
        self.filter_settings_var.set(False)
        self.whole_word_var.set(False)
        self.clear_filter_inputs()
        self.apply_filters()

    def apply_filters(self):
        # Alle aktiven Filterkriterien müssen erfüllt sein.
        filter_text_raw = self.filter_var.get().strip().lower()
        keywords = [f.strip() for f in filter_text_raw.split(",") if f.strip()] if filter_text_raw else []
        self.filtered_images = []
        for file_path in self.folder_images:
            passes = True
            filename = os.path.basename(file_path).lower()
            if file_path not in self.text_chunks_cache:
                self.text_chunks_cache[file_path] = extract_text_chunks(file_path)
            prompt, negativ, settings = self.text_chunks_cache[file_path]
            # Prompt Filter (Modus aus Filter Settings, Whole Word berücksichtigen)
            if self.filter_prompt_var.get():
                prompt_lower = prompt.lower()
                mode = self.prompt_filter_mode.get()
                if mode == "all":
                    for keyword in keywords:
                        if not match_keyword(prompt_lower, keyword, self.whole_word_var.get()):
                            passes = False
                            break
                elif mode == "any":
                    if not any(match_keyword(prompt_lower, keyword, self.whole_word_var.get()) for keyword in keywords):
                        passes = False
                elif mode in ("exclude", "none"):
                    if any(match_keyword(prompt_lower, keyword, self.whole_word_var.get()) for keyword in keywords):
                        passes = False
            # Filename Filter
            if passes and self.filter_filename_var.get():
                if not any(match_keyword(filename, keyword, self.whole_word_var.get()) for keyword in keywords):
                    passes = False
            # Negative Prompt Filter
            if passes and self.filter_negativ_var.get():
                if not any(match_keyword(negativ.lower(), keyword, self.whole_word_var.get()) for keyword in keywords):
                    passes = False
            # Settings Filter
            if passes and self.filter_settings_var.get():
                if not any(match_keyword(settings.lower(), keyword, self.whole_word_var.get()) for keyword in keywords):
                    passes = False
            # File Size Filter
            if passes and ((hasattr(self, "entry_min_size") and self.entry_min_size.get().strip()) or 
                           (hasattr(self, "entry_max_size") and self.entry_max_size.get().strip())):
                try:
                    file_size_kb = os.path.getsize(file_path) / 1024
                except Exception:
                    file_size_kb = 0
                if self.entry_min_size.get().strip():
                    if file_size_kb < int(self.entry_min_size.get().strip()):
                        passes = False
                if passes and self.entry_max_size.get().strip():
                    if file_size_kb > int(self.entry_max_size.get().strip()):
                        passes = False
            # Date Filter: Alle aktiven Datumskriterien müssen erfüllt sein.
            if passes:
                now_ts = datetime.now().timestamp()
                try:
                    ctime = os.path.getctime(file_path)
                except Exception:
                    ctime = 0
                if self.date_this_week.get():
                    if (now_ts - ctime) > 7 * 24 * 3600:
                        passes = False
                if passes and self.date_two_weeks.get():
                    if (now_ts - ctime) > 14 * 24 * 3600:
                        passes = False
                if passes and self.date_four_weeks.get():
                    if (now_ts - ctime) > 28 * 24 * 3600:
                        passes = False
                if passes and self.date_one_month.get():
                    if (now_ts - ctime) > 30 * 24 * 3600:
                        passes = False
                if passes and self.date_one_year.get():
                    if (now_ts - ctime) > 365 * 24 * 3600:
                        passes = False
            if passes:
                self.filtered_images.append(file_path)
        if not self.filtered_images and self.folder_images:
            self.filtered_images.append(self.folder_images[0])
        if self.current_index != -1 and hasattr(self, 'current_image_path') and self.current_image_path in self.filtered_images:
            self.current_index = self.filtered_images.index(self.current_image_path)
        else:
            self.current_index = 0 if self.filtered_images else -1
            self.current_index = validate_index(self.current_index, self.filtered_images)
            if self.current_index != -1:
                self.display_image_safe_async(self.filtered_images[self.current_index])
                self.extract_and_display_text_chunks(self.filtered_images[self.current_index])
        self.populate_preview_table_lazy()
        total_images = len(self.folder_images)
        filtered_images = len(self.filtered_images)
        self.image_counter_label.config(text=f"Folder: {total_images} images filtered ")
        self.filtered_counter_label.config(text=f"{filtered_images}")
        self.image_counter_suffix_label.config(text=" images")
        self.status(f"Filter applied: {filtered_images} images found.")

    # (Die übrigen Methoden bleiben unverändert.)
    # ...
    
if __name__ == "__main__":
    app = ImageManagerForm()
    app.mainloop()
