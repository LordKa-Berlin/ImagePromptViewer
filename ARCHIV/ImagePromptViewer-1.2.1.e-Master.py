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

# Neue Funktion: Keywordvergleich, optional als ganzes Wort
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
        # Neues Kontrollfeld: Whole Word (Default: False)
        self.whole_word_var = tk.BooleanVar(value=False)
        # Filtervariablen bereits in der Hauptanwendung initialisieren
        self.prompt_filter_mode = tk.StringVar(value="all")
        self.date_between = tk.BooleanVar(value=False)
        self.date_not_older_than = tk.BooleanVar(value=False)
        self.date_older_than = tk.BooleanVar(value=False)
        self.date_this_week = tk.BooleanVar(value=False)
        self.date_two_weeks = tk.BooleanVar(value=False)
        self.date_four_weeks = tk.BooleanVar(value=False)
        self.date_one_month = tk.BooleanVar(value=False)
        self.date_one_year = tk.BooleanVar(value=False)

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
        self.filter_settings_button = tk.Button(filter_frame,text="Filter Settings",command=self.open_filter_settings,
                                                bg=BTN_BG_COLOR,fg=BTN_FG_COLOR,font=("Arial", self.main_font_size))

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
        # Verwende die bereits initialisierte Variable self.prompt_filter_mode
        tk.Radiobutton(prompt_frame, text="All words must match", variable=self.prompt_filter_mode, value="all",
                       bg=BG_COLOR, fg=TEXT_FG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size)).pack(anchor="w", padx=10)
        tk.Radiobutton(prompt_frame, text="Any word", variable=self.prompt_filter_mode, value="any",
                       bg=BG_COLOR, fg=TEXT_FG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size)).pack(anchor="w", padx=10)
        tk.Radiobutton(prompt_frame, text="Exclude word", variable=self.prompt_filter_mode, value="exclude",
                       bg=BG_COLOR, fg=TEXT_FG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size)).pack(anchor="w", padx=10)
        tk.Radiobutton(prompt_frame, text="None of the words", variable=self.prompt_filter_mode, value="none",
                       bg=BG_COLOR, fg=TEXT_FG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size)).pack(anchor="w", padx=10)

        # --- Date Filter Section ---
        date_frame = tk.LabelFrame(self.filter_settings_window, text="Date Filter", fg=TEXT_FG_COLOR, bg=BG_COLOR, font=("Arial", int(self.main_font_size * 1.2), "bold"))
        date_frame.pack(fill="x", padx=10, pady=5)
        # Verwende die bereits initialisierten Datum-Variablen
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
            # Prompt Filter (unter Berücksichtigung von Modus und Whole Word)
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
            # Datumfilter: Alle aktiven Datumskriterien müssen erfüllt sein.
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

    # Die übrigen Methoden bleiben unverändert...
    # (Die restlichen Methoden, z.B. update_ui, load_folder_async, on_folder_loaded, handle_drop, choose_folder, etc. – unverändert übernommen)

    def update_ui(self):
        header_font = ("Arial", self.main_font_size)
        if hasattr(self, 'header_label'):
            self.header_label.config(font=header_font)
        status_font = ("Arial", self.main_font_size)
        if hasattr(self, 'status_text'):
            self.status_text.config(font=status_font)
        if hasattr(self, 'top_checkbox'):
            self.top_checkbox.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'debug_button'):
            self.debug_button.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'info_button'):
            self.info_button.config(font=("Arial", self.main_font_size))
        small_info_font = ("Arial", int(self.main_font_size * 0.9))
        if hasattr(self, 'image_info_label'):
            self.image_info_label.config(font=small_info_font)
        if hasattr(self, 'filter_button'):
            self.filter_button.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'clear_button'):
            self.clear_button.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'filter_filename_cb'):
            self.filter_filename_cb.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'filter_prompt_cb'):
            self.filter_prompt_cb.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'filter_negativ_cb'):
            self.filter_negativ_cb.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'filter_settings_cb'):
            self.filter_settings_cb.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'image_counter_label'):
            self.image_counter_label.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'filtered_counter_label'):
            self.filtered_counter_label.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'image_counter_suffix_label'):
            self.image_counter_suffix_label.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'folder_entry'):
            self.folder_entry.config(font=("Arial", self.main_font_size), width=int(50 * self.scaling_factor))
        if hasattr(self, 'choose_folder_button'):
            self.choose_folder_button.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'select_image_button'):
            self.select_image_button.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'open_image_button'):
            self.open_image_button.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'delete_button_main'):
            self.delete_button_main.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'delete_immediately_main_cb'):
            self.delete_immediately_main_cb.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'subfolder_cb'):
            self.subfolder_cb.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'sort_button'):
            self.sort_button.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'prompt_text'):
            self.prompt_text.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'negativ_text'):
            self.negativ_text.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'settings_text'):
            self.settings_text.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'copy_prompt_button'):
            self.copy_prompt_button.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'copy_negativ_button'):
            self.copy_negativ_button.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'copy_settings_button'):
            self.copy_settings_button.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'back_button'):
            self.back_button.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'next_button'):
            self.next_button.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'scale_dropdown'):
            self.scale_dropdown.config(font=("Arial", int(self.main_font_size + 2 * self.scaling_factor)))
        if hasattr(self, 'fullscreen_button'):
            self.fullscreen_button.config(font=("Arial", self.main_font_size))
        if hasattr(self, 'monitor_menu'):
            self.monitor_menu.config(font=("Arial", int(self.main_font_size + 2 * self.scaling_factor)))
        if hasattr(self, 'drop_canvas'):
            self.drop_canvas.config(width=int(150 * self.scaling_factor), height=int(112 * self.scaling_factor))
            self.drop_canvas.delete("all")
            self.drop_canvas.create_text(int(75 * self.scaling_factor), int(56 * self.scaling_factor),
                                         text="Drop Image Here", fill="white", font=("Arial", self.main_font_size))

    def handle_delete_key(self, event):
        if self.fullscreen_win and self.fullscreen_win.winfo_exists():
            self.fs_delete_current_image()
        else:
            self.delete_current_image()

    def update_delete_button_color_main(self):
        if self.delete_immediately_main_var.get():
            self.delete_button_main.config(bg="red")
        else:
            self.delete_button_main.config(bg=BTN_BG_COLOR)

    def update_delete_button_color_fs(self):
        if self.delete_immediately_fs_var.get():
            self.fs_delete_button.config(bg="red")
        else:
            self.fs_delete_button.config(bg=BTN_BG_COLOR)

    def update_fullscreen_monitor(self, choice):
        for i, mon in enumerate(self.monitor_list):
            if choice.startswith(f"Monitor {i}:"):
                self.fullscreen_monitor = mon
                break
        self.status(f"Fullscreen monitor changed to: {choice}")

    def toggle_sort_order(self):
        if self.sort_order == "ASC":
            self.sort_order = "DESC"
            self.sort_button.config(text="ASC")
        else:
            self.sort_order = "ASC"
            self.sort_button.config(text="DESC")
        
        if self.folder_images:
            self.folder_images.sort(key=lambda x: self.ctime_cache[x], reverse=(self.sort_order == "DESC"))
            if self.filtered_images:
                self.filtered_images.sort(key=lambda x: self.ctime_cache[x], reverse=(self.sort_order == "DESC"))
            if self.filtered_images:
                self.current_index = 0
                self.display_image_safe_async(self.filtered_images[self.current_index])
                self.extract_and_display_text_chunks(self.filtered_images[self.current_index])
            self.status(f"Sort order changed to: {self.sort_order}")

    def status(self, message):
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete("1.0", tk.END)
        self.status_text.insert(tk.END, f"{get_datetime_str()}: {message}")
        self.status_text.config(state=tk.DISABLED)

    def show_debug_info(self):
        if hasattr(self, "current_image_path") and self.current_image_path:
            bildname = os.path.basename(self.current_image_path)
        else:
            bildname = "No image selected"
        extraction_method = (
            "Text chunk extraction is performed with: extract_text_chunks()\n"
            "- For JPEG: Search in EXIF tag 'UserComment'.\n"
            "  • If the data starts with 'UNICODE\\x00\\x00', helper.UserComment.load is used.\n"
            "  • In case of errors or missing prefix, a fallback (UTF-16LE or Latin-1 decoding) is applied.\n"
            "- For PNG: First, look for a key in img.info that contains 'parameters'.\n"
            "  • If not found, fallback to alternative keys like 'prompt', 'metadata', or 'description'.\n"
            "- New marker support: If the normalized text contains the markers \"prompt\":, \"negativePrompt\":, and \"steps\":,\n"
            "  these are used to split into Prompt, Negative Prompt, and Settings."
        )
        os_info = f"Operating system: {platform.system()} {platform.release()}"
        python_version = f"Python version: {sys.version.split()[0]}"
        monitor_info = f"Current monitor resolution: {self.selected_monitor.width}x{self.selected_monitor.height}"
        cache_info = f"Image cache: {len(self.image_cache)} items\n"
        if self.image_cache:
            cache_paths = '\n'.join(list(self.image_cache.keys())[-5:])
            cache_info += f"Last cached images:\n{cache_paths}\n"
        else:
            cache_info += "No images currently cached.\n"
        updated_debug = (
            f"Image name: {bildname}\n\n"
            f"{extraction_method}\n\n"
            f"System information:\n"
            f"{os_info}\n"
            f"{python_version}\n"
            f"{monitor_info}\n\n"
            f"{cache_info}\n"
            f"Debug details:\n"
            f"{self.debug_info if self.debug_info else 'No debug information available.'}"
        )
        debug_win = tk.Toplevel(self)
        debug_win.title("Debug Information")
        debug_win.configure(bg=BG_COLOR)
        debug_text = ScrolledText(debug_win, width=80, height=20, bg=BG_COLOR, fg=TEXT_FG_COLOR, font=("Arial", self.main_font_size))
        debug_text.insert(tk.END, updated_debug)
        debug_text.config(state=tk.DISABLED)
        debug_text.pack(padx=self.button_padding, pady=self.button_padding)
        copy_btn = tk.Button(debug_win, text="Copy", command=lambda: copy_to_clipboard(self, updated_debug),
                            bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        copy_btn.pack(side="left", padx=self.button_padding, pady=self.button_padding)
        close_btn = tk.Button(debug_win, text="Close", command=debug_win.destroy,
                            bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        close_btn.pack(side="right", padx=self.button_padding, pady=self.button_padding)
        def clear_image_cache():
            self.image_cache.clear()
            self.status("Image cache cleared.")
            messagebox.showinfo("Cache", "Image cache has been cleared.")
        clear_cache_btn = tk.Button(debug_win, text="Clear Cache", command=clear_image_cache,
                                    bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        clear_cache_btn.pack(side="left", padx=self.button_padding, pady=self.button_padding)

    def update_topmost(self):
        self.attributes("-topmost", self.always_on_top_var.get())

    def on_preview_mousewheel(self, event):
        self.preview_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.update_preview_visible()

    def on_image_mousewheel(self, event):
        if event.delta > 0:
            self.show_previous_image()
        elif event.delta < 0:
            self.show_next_image()

    def clear_filter(self):
        self.filter_var.set("")
        self.apply_filter()

    def apply_filter(self):
        # Hier wird apply_filters() aufgerufen, um alle Kriterien anzuwenden.
        self.apply_filters()

    def highlight_text(self, text_widget, text, filter_text_raw):
        text_widget.delete("1.0", tk.END)
        text_widget.insert("1.0", text)
        text_widget.tag_remove("highlight", "1.0", tk.END)
        if not filter_text_raw:
            return
        keywords = [f.strip().lower() for f in filter_text_raw.split(",") if f.strip()]
        text_lower = text.lower()
        for keyword in keywords:
            start_pos = 0
            while True:
                pos = text_lower.find(keyword, start_pos)
                if pos == -1:
                    break
                start = f"1.0 + {pos} chars"
                end = f"1.0 + {pos + len(keyword)} chars"
                text_widget.tag_add("highlight", start, end)
                start_pos = pos + len(keyword)
        text_widget.tag_config("highlight", foreground=HIGHLIGHT_COLOR)

    def load_folder_async(self, folder, file_path=None):
        self.status("Loading folder in background...")
        self.folder_images = []
        self.ctime_cache.clear()
        self.text_chunks_cache.clear()
        self.abort_loading = False

        def check_abort():
            return self.abort_loading

        def on_key(event):
            if event.keysym == 'Escape':
                self.abort_loading = True
                self.status("Loading aborted by user.")
        self.bind("<KeyPress>", on_key)
        image_paths = []
        if self.search_subfolders_var.get():
            image_paths = list(Path(folder).rglob("*"))
        else:
            image_paths = [Path(folder) / f for f in os.listdir(folder)]
        total = len(image_paths)
        for idx, p in enumerate(image_paths):
            if check_abort():
                break
            if p.suffix.lower() in IMAGE_EXTENSIONS:
                norm_path = os.path.normpath(str(p))
                self.folder_images.append(norm_path)
                self.ctime_cache[norm_path] = os.path.getctime(norm_path)
            if idx % 50 == 0 or idx == total - 1:
                percent = int((idx+1) / total * 100)
                self.status(f"Reading files... {idx+1}/{total} ({percent}%)")
        self.unbind("<KeyPress>")
        self.folder_images.sort(key=lambda x: self.ctime_cache[x], reverse=(self.sort_order == "DESC"))
        self.after(0, lambda: self.on_folder_loaded(folder, file_path))

    def on_folder_loaded(self, folder, file_path):
        if self.folder_images:
            if file_path:
                file_path = os.path.normpath(file_path)
                self.status(f"Debug: Selected path: {file_path}")
                self.status(f"Debug: First path in folder_images: {self.folder_images[0] if self.folder_images else 'Empty'}")
            if file_path and file_path in self.folder_images:
                self.current_index = self.folder_images.index(file_path)
                self.status(f"Debug: Image found, Index: {self.current_index}")
            else:
                self.current_index = 0 if len(self.folder_images) > 0 else -1
                if file_path:
                    self.status(f"Debug: Image not found in folder_images, setting index to {self.current_index}")
            if self.current_index != -1:
                self.display_image_safe_async(self.folder_images[self.current_index], default_scale=True)
                self.extract_and_display_text_chunks(self.folder_images[self.current_index])
            self.apply_filter()
            self.status(f"Folder loaded: {folder} ({len(self.folder_images)} images, {len(self.filtered_images)} filtered)")
        else:
            self.status("No images found in the selected folder.")

    def handle_drop(self, event):
        file_path = event.data.strip("{}")
        if os.path.isfile(file_path) and file_path.lower().endswith(IMAGE_EXTENSIONS):
            folder = os.path.dirname(file_path)
            self.folder_path_var.set(folder)
            threading.Thread(target=self.load_folder_async, args=(folder, file_path), daemon=True).start()

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Select folder")
        if folder:
            self.folder_path_var.set(folder)
            threading.Thread(target=self.load_folder_async, args=(folder,), daemon=True).start()
            if folder not in self.folder_history:
                self.folder_history.insert(0, folder)
                self.folder_history = self.folder_history[:10]
                self.folder_combo['values'] = self.folder_history
                save_history(self.folder_history, list(self.filter_history))

    def select_image_from_folder(self):
        file_path = filedialog.askopenfilename(title="Select image", filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if file_path:
            folder = os.path.dirname(file_path)
            self.folder_path_var.set(folder)
            threading.Thread(target=self.load_folder_async, args=(folder, file_path), daemon=True).start()

    def show_info(self):
        info_win = tk.Toplevel(self)
        info_win.title("Information")
        info_win.configure(bg=BG_COLOR)
        info_text = (
            "ImagePromptViewer - User Guide:\n\n"
            "Overview:\n"
            "This program serves as an image viewer for PNG and JPEG images, reading embedded texts. PNGs use info['parameters'] and JPEGs use the EXIF tag 'UserComment' (with UNICODE prefix) to split the text into Prompt, Negative Prompt, and Settings.\n\n"
            "Main Functions:\n"
            "- Image Display and Navigation\n"
            "- Filtering with a single Prompt field and extended Filter Settings (Prompt mode, Date Filter, File Size Filter)\n"
            "- Folder and Image Selection\n"
            "- Deletion with optional immediate deletion\n"
            "- Fullscreen Mode with additional controls\n\n"
            "Usage Tips:\n"
            "  • Use the filter options to search specifically for image content.\n"
            "  • All active filter criteria are combined (logical AND).\n\n"
            "Enjoy working with ImagePromptViewer!"
        )
        st = ScrolledText(info_win, width=80, height=20, bg=BG_COLOR, fg=TEXT_FG_COLOR, font=("Arial", self.main_font_size))
        st.insert(tk.END, info_text)
        st.config(state=tk.DISABLED)
        st.pack(padx=self.button_padding, pady=self.button_padding)
        close_btn = tk.Button(info_win, text="Close", command=info_win.destroy,
                              bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        close_btn.pack(pady=self.button_padding)

    def populate_preview_table_lazy(self):
        for widget in self.preview_inner_frame.winfo_children():
            widget.destroy()
        self.preview_items = []
        for i, file_path in enumerate(self.filtered_images):
            frame = tk.Frame(self.preview_inner_frame, bg=BG_COLOR, bd=1, relief="solid")
            frame.grid(row=i, column=0, sticky="ew", padx=2, pady=2)
            tk.Label(frame, text=os.path.basename(file_path), fg=TEXT_FG_COLOR, bg=BG_COLOR, font=("Arial", self.main_font_size)).pack(side="left", padx=self.button_padding)
            frame.bind("<Button-1>", lambda e, idx=i: self.on_preview_click(idx))
            self.preview_items.append(frame)
        self.update_preview_visible()

    def toggle_folder_list(self):
        if self.preview_frame.winfo_ismapped():
            self.preview_frame.pack_forget()
            self.load_list_button.config(text="Load folder list")
        else:
            self.preview_frame.pack(fill="both", padx=self.button_padding, pady=self.button_padding, expand=True)
            self.populate_preview_table_lazy()
            self.load_list_button.config(text="Hide folder list")

    def update_preview_visible(self):
        canvas_height = self.preview_canvas.winfo_height()
        scroll_region = self.preview_canvas.bbox("all")
        if not scroll_region:
            return
        y_top = self.preview_canvas.canvasy(0)
        y_bottom = y_top + canvas_height
        visible_start = max(0, int(y_top // (int(100 * self.scaling_factor) + 4)))
        visible_end = min(len(self.filtered_images), int(y_bottom // (int(100 * self.scaling_factor) + 4)) + 1)
        for i in range(visible_start, visible_end):
            frame = self.preview_items[i]
            if not frame.winfo_children() or len(frame.winfo_children()) == 1:
                file_path = self.filtered_images[i]
                try:
                    img = load_image_with_cache(file_path, self.image_cache, self.cache_limit)
                    if img:
                        thumb = img.copy()
                        thumb.thumbnail((int(100 * self.scaling_factor), int(100 * self.scaling_factor)))
                        tk_img = ImageTk.PhotoImage(thumb)
                        self.preview_images[file_path] = tk_img
                    else:
                        tk_img = None
                except Exception:
                    tk_img = None
                if tk_img:
                    img_label = tk.Label(frame, image=tk_img, bg=BG_COLOR)
                    img_label.image = tk_img
                    img_label.pack(side="left", before=frame.winfo_children()[0])
                    img_label.bind("<Button-1>", lambda e, idx=i: self.on_preview_click(idx))

    def on_preview_click(self, index):
        if 0 <= index < len(self.filtered_images):
            self.current_index = index
            self.display_image_safe_async(self.filtered_images[self.current_index])
            self.extract_and_display_text_chunks(self.filtered_images[self.current_index])

    def display_image(self, file_path, default_scale=False):
        self.current_image = load_image_with_cache(file_path, self.image_cache, self.cache_limit)
        self.current_image_path = file_path
        if not self.current_image:
            self.status(f"Fehler beim Laden von Bild: {file_path}")
            return

    def display_image_safe_async(self, file_path, default_scale=False):
        def task():
            img = load_image_with_cache(file_path, self.image_cache, self.cache_limit)
            if img:
                self.current_image = img
                self.current_image_path = file_path
                self.after(0, lambda: self._finalize_display_image(file_path, default_scale))
            else:
                self.status(f"Fehler beim Laden von Bild: {file_path}")
        threading.Thread(target=task, daemon=True).start()

    def _finalize_display_image(self, file_path, default_scale=False):
        self.image_frame.update_idletasks()
        avail_width = self.image_frame.winfo_width() - 2 * self.button_padding
        avail_height = self.image_frame.winfo_height() - 2 * self.button_padding
        if avail_width < 10 or avail_height < 10:
            avail_width = 800
            avail_height = 600
        orig_width, orig_height = self.current_image.size
        if default_scale or (self.scale_var.get() == "Default"):
            default_scale_factor = get_default_image_scale(self.scaling_factor)
        else:
            default_scale_factor = int(self.scale_var.get().replace("%", "")) / 100
        new_width = int(orig_width * default_scale_factor)
        new_height = int(orig_height * default_scale_factor)
        max_width = int(avail_width * 0.8)
        max_height = int(avail_height * 0.8)
        width_factor = max_width / orig_width
        height_factor = max_height / orig_height
        fit_factor = min(width_factor, height_factor)
        if fit_factor < default_scale_factor:
            new_width = int(orig_width * fit_factor)
            new_height = int(orig_height * fit_factor)
        self.resized_image = self.current_image.resize((new_width, new_height), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(self.resized_image)
        self.image_label.config(image=self.tk_image)
        self.status(f"Image loaded: {os.path.basename(file_path)}")
        try:
            ctime = self.ctime_cache[file_path]
            created_str = datetime.fromtimestamp(ctime).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            created_str = "Unknown"
        info_text = f"Filename: {os.path.basename(file_path)}\nPath: {file_path}\nCreated: {created_str}"
        self.image_info_label.config(text=info_text)
        self.image_frame.update_idletasks()
        avail_width = self.image_frame.winfo_width() - 2 * self.button_padding
        avail_height = self.image_frame.winfo_height() - 2 * self.button_padding
        if avail_width < 10 or avail_height < 10:
            avail_width = 800
            avail_height = 600
        orig_width, orig_height = self.current_image.size
        if default_scale or (self.scale_var.get() == "Default"):
            default_scale_factor = get_default_image_scale(self.scaling_factor)
        else:
            default_scale_factor = int(self.scale_var.get().replace("%", "")) / 100
        new_width = int(orig_width * default_scale_factor)
        new_height = int(orig_height * default_scale_factor)
        max_width = int(avail_width * 0.8)
        max_height = int(avail_height * 0.8)
        width_factor = max_width / orig_width
        height_factor = max_height / orig_height
        fit_factor = min(width_factor, height_factor)
        if fit_factor < default_scale_factor:
            new_width = int(orig_width * fit_factor)
            new_height = int(orig_height * fit_factor)
        self.resized_image = self.current_image.resize((new_width, new_height), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(self.resized_image)
        self.image_label.config(image=self.tk_image)
        self.current_image_path = file_path
        self.status(f"Image loaded: {os.path.basename(file_path)}")
        try:
            ctime = self.ctime_cache[file_path]
            created_str = datetime.fromtimestamp(ctime).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            created_str = "Unknown"
        info_text = f"Filename: {os.path.basename(file_path)}\nPath: {file_path}\nCreated: {created_str}"
        self.image_info_label.config(text=info_text)

    def rescale_image(self, value):
        if self.current_image:
            self.display_image(self.current_image_path)

    def extract_and_display_text_chunks(self, file_path):
        if file_path not in self.text_chunks_cache:
            self.text_chunks_cache[file_path] = extract_text_chunks(file_path)
        prompt, negativ, settings = self.text_chunks_cache[file_path]
        filter_text = self.filter_var.get()
        self.highlight_text(self.prompt_text, prompt, filter_text)
        self.highlight_text(self.negativ_text, negativ, filter_text)
        self.highlight_text(self.settings_text, settings, filter_text)

    def show_next_image(self): 
        if self.filtered_images:
            self.current_index += 1
            self.current_index = validate_index(self.current_index, self.filtered_images)
            self.display_image_safe_async(self.filtered_images[self.current_index])
            self.extract_and_display_text_chunks(self.filtered_images[self.current_index])

    def show_previous_image(self):
        if self.filtered_images:
            self.current_index -= 1
            self.current_index = validate_index(self.current_index, self.filtered_images)
            self.display_image_safe_async(self.filtered_images[self.current_index])
            self.extract_and_display_text_chunks(self.filtered_images[self.current_index])

    def delete_current_image(self):
        if not hasattr(self, "current_image_path") or not self.current_image_path:
            self.status("No image selected to delete.")
            return
        normalized_path = os.path.normpath(self.current_image_path)
        if not os.path.exists(normalized_path):
            self.status("File not found.")
            return
        def continue_after_delete():
            try:
                delete_index = self.filtered_images.index(normalized_path)
                next_index = delete_index
                if next_index >= len(self.filtered_images) - 1:
                    next_index = len(self.filtered_images) - 2
                if next_index < 0:
                    next_index = 0
                send2trash(normalized_path)
                self.folder_images.remove(normalized_path)
                self.ctime_cache.pop(normalized_path, None)
                self.text_chunks_cache.pop(normalized_path, None)
                self.preview_images.pop(normalized_path, None)
                self.apply_filter()
                if self.filtered_images:
                    self.current_index = next_index
                    self.display_image_safe_async(self.filtered_images[self.current_index])
                    self.extract_and_display_text_chunks(self.filtered_images[self.current_index])
                else:
                    self.current_index = -1
                    self.status("No images remaining.")
            except Exception as e:
                self.status(f"Error deleting: {e}")
        if self.delete_immediately_main_var.get():
            continue_after_delete()
        else:
            confirm = messagebox.askyesno("Delete image", f"Do you want to delete the image '{os.path.basename(normalized_path)}'?")
            if confirm:
                continue_after_delete()

    def show_fullscreen(self):
        if not hasattr(self, "current_image_path") or not self.current_image_path:
            self.status("No image available for fullscreen.")
            return
        if self.current_index != -1 and self.current_index < len(self.filtered_images):
            self.fs_current_index = self.current_index
            self.fs_image_path = self.filtered_images[self.fs_current_index]
        else:
            self.status("No valid image index for fullscreen mode.")
            return
        if self.fullscreen_win and self.fullscreen_win.winfo_exists():
            self.safe_close_fullscreen(update_main=False)
        if not hasattr(self, "current_image") or not self.current_image:
            self.status("No image available for fullscreen.")
            return
        self.fs_current_index = self.current_index
        self.fs_image_path = self.filtered_images[self.fs_current_index]
        try:
            self.fs_image = load_image_with_cache(self.fs_image_path, self.image_cache, self.cache_limit)
        except Exception as e:
            self.status(f"Error in fullscreen: {e}")
            return
        self.fullscreen_win = tk.Toplevel(self)
        self.fullscreen_win.configure(bg=BG_COLOR)
        mon = self.fullscreen_monitor
        self.fullscreen_win.geometry(f"{mon.width}x{mon.height}+{mon.x}+{mon.y}")
        self.fullscreen_win.overrideredirect(True)
        self.fullscreen_win.bind("<Escape>", lambda e: self.safe_close_fullscreen())
        self.fullscreen_win.bind("<F11>", lambda e: self.safe_close_fullscreen())
        self.fullscreen_win.bind("<Right>", lambda e: self.fs_show_next())
        self.fullscreen_win.bind("<Left>", lambda e: self.fs_show_previous())
        self.fullscreen_win.bind("<Control-MouseWheel>", self.fullscreen_zoom)
        self.fullscreen_win.bind("<Delete>", lambda e: self.fs_delete_current_image())
        self.fullscreen_win.focus_force()
        self.fs_text_focus = False
        info_font_size = int(self.main_font_size * 0.9)
        self.fs_info_label = tk.Label(self.fullscreen_win, text="", fg=TEXT_FG_COLOR, bg=BG_COLOR,
                                      font=("Arial", info_font_size))
        self.fs_info_label.pack(side="top", anchor="n", pady=self.button_padding)
        self.update_fs_info_fullscreen()
        top_buttons = tk.Frame(self.fullscreen_win, bg=BG_COLOR)
        top_buttons.pack(anchor="nw", padx=self.button_padding, pady=self.button_padding)
        self.fs_delete_button = tk.Button(top_buttons, text="Delete image", command=self.fs_delete_current_image,
                                          bg="red" if self.delete_immediately_fs_var.get() else BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        self.fs_delete_button.pack(side="left", padx=self.button_padding)
        self.delete_immediately_fs_cb = tk.Checkbutton(top_buttons, text="delete immediately", variable=self.delete_immediately_fs_var,
                                                       command=self.update_delete_button_color_fs, fg=TEXT_FG_COLOR,
                                                       bg=BG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size))
        self.delete_immediately_fs_cb.pack(side="left", padx=self.button_padding)
        self.fs_close_button = tk.Button(top_buttons, text="Close", command=self.safe_close_fullscreen,
                                         bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        self.fs_close_button.pack(side="left", padx=self.button_padding)
        btn_fs_open = tk.Button(top_buttons, text="View image", command=self.open_image_fs,
                                bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        btn_fs_open.pack(side="left", padx=self.button_padding)
        btn_fs_copy_name = tk.Button(top_buttons, text="Copy image name", command=self.copy_filename_fs,
                                     bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        btn_fs_copy_name.pack(side="left", padx=self.button_padding)
        btn_fs_copy_path = tk.Button(top_buttons, text="Copy image path", command=self.copy_full_path_fs,
                                     bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        btn_fs_copy_path.pack(side="left", padx=self.button_padding)
        self.prompt_toggle = tk.Button(self.fullscreen_win, text="Hide prompt", command=self.toggle_fs_prompt,
                                       bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        self.prompt_toggle.pack(anchor="ne", padx=self.button_padding, pady=self.button_padding)
        self.fullscreen_win.bind("p", lambda e: self.toggle_fs_prompt())
        self.fs_text_frame = tk.Frame(self.fullscreen_win, bg=BG_COLOR)
        self.fs_text_frame.grid_propagate(False)
        self.fs_text_frame.pack(side="right", fill="both", expand=True, padx=self.button_padding, pady=self.button_padding)
        self.fs_text_visible = True
        self.fs_image_label = tk.Label(self.fullscreen_win, bg=BG_COLOR)
        self.fs_image_label.pack(side="left", fill="both", expand=True)
        self.fs_image_label.bind("<Button-1>", lambda e: self.safe_close_fullscreen())
        self.fs_image_label.bind("<MouseWheel>", self.fullscreen_mousewheel_image)
        self.update_fs_image()
        self.update_fs_texts()

    def safe_close_fullscreen(self, update_main=True):
        try:
            if self.fullscreen_win and self.fullscreen_win.winfo_exists():
                self.fullscreen_win.destroy()
                self.fullscreen_win = None
            self.focus_force()
            if update_main and hasattr(self, "fs_image_path") and self.fs_image_path in self.filtered_images:
                self.current_index = validate_index(self.filtered_images.index(self.fs_image_path), self.filtered_images)
                self.display_image_safe_async(self.fs_image_path)
                self.extract_and_display_text_chunks(self.fs_image_path)
        except tk.TclError:
            pass

    def show_preview_table(self):
        if not self.preview_frame.winfo_ismapped():
            self.preview_frame.pack(fill="both", padx=self.button_padding, pady=self.button_padding, expand=True)
        self.populate_preview_table_lazy()

    def update_fs_info_fullscreen(self):
        if not hasattr(self, "fs_image_path") or not self.fs_image_path:
            self.fs_info_label.config(text="No image selected")
            return
        try:
            ctime = self.ctime_cache[self.fs_image_path]
            created_str = datetime.fromtimestamp(ctime).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            created_str = "Unknown"
        try:
            dimensions = f"{self.fs_image.width}x{self.fs_image.height}"
        except Exception:
            dimensions = "Unknown"
        info = (f"Filename: {os.path.basename(self.fs_image_path)}\n"
                f"Path: {self.fs_image_path}\n"
                f"Created: {created_str}\n"
                f"Resolution: {dimensions}")
        if len(self.filtered_images) < len(self.folder_images):
            info += "\nFILTER ACTIVE!"
        self.fs_info_label.config(text=info)

    def update_fs_image(self):
        try:
            self.fullscreen_win.update_idletasks()
            avail_w = self.fs_image_label.winfo_width()
            avail_h = self.fs_image_label.winfo_height()
            if avail_w < 10 or avail_h < 10:
                self.fullscreen_win.after(100, self.update_fs_image)
                return
            orig_w, orig_h = self.fs_image.size
            factor = min(avail_w / orig_w, avail_h / orig_h)
        except Exception:
            return
        new_w = int(orig_w * factor)
        new_h = int(orig_h * factor)
        fs_resized = self.fs_image.resize((new_w, new_h), Image.LANCZOS)
        self.fs_tk_image = ImageTk.PhotoImage(fs_resized)
        self.fs_image_label.config(image=self.fs_tk_image)
        self.update_fs_info_fullscreen()

    def fullscreen_zoom(self, event):
        try:
            factor = 1.1 if event.delta > 0 else 0.9
            orig = Image.open(self.fs_image_path)
            new_w = int(orig.width * factor)
            new_h = int(orig.height * factor)
            self.fs_image = orig.resize((new_w, new_h))
            self.update_fs_image()
        except tk.TclError:
            pass

    def fullscreen_mousewheel_image(self, event):
        if event.delta > 0:
            self.fs_show_previous()
        elif event.delta < 0:
            self.fs_show_next()

    def fullscreen_mousewheel_text(self, event, text_widget):
        text_widget.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def fs_show_next(self):
        if self.filtered_images:
            self.fs_current_index += 1
            self.fs_current_index = validate_index(self.fs_current_index, self.filtered_images)
            self.fs_image_path = self.filtered_images[self.fs_current_index]
            try:
                self.fs_image = Image.open(self.fs_image_path)
            except Exception as e:
                self.status(f"Error in fullscreen: {e}")
                return
            self.update_fs_image()
            self.update_fs_info_fullscreen()
            self.update_fs_texts()

    def fs_show_previous(self):
        if self.filtered_images:
            self.fs_current_index -= 1
            self.fs_current_index = validate_index(self.fs_current_index, self.filtered_images)
            self.fs_image_path = self.filtered_images[self.fs_current_index]
            try:
                self.fs_image = Image.open(self.fs_image_path)
            except Exception as e:
                self.status(f"Error in fullscreen: {e}")
                return
            self.update_fs_image()
            self.update_fs_info_fullscreen()
            self.update_fs_texts()

    def toggle_fs_prompt(self):
        if self.fs_text_visible:
            self.fs_text_frame.pack_forget()
            self.fs_text_visible = False
            self.prompt_toggle.config(text="Show prompt")
        else:
            self.fs_text_frame.pack(side="right", fill="both", expand=True, padx=self.button_padding, pady=self.button_padding)
            self.fs_text_visible = True
            self.prompt_toggle.config(text="Hide prompt")
            self.update_fs_texts()
        self.fullscreen_win.after(100, self.update_fs_image)

    def fs_delete_current_image(self):
        if not hasattr(self, "fs_image_path") or not self.fs_image_path:
            self.status("No image selected to delete.")
            return
        normalized_path = os.path.normpath(self.fs_image_path)
        if not os.path.exists(normalized_path):
            self.status("File not found.")
            return
        def continue_after_delete():
            try:
                delete_index = self.filtered_images.index(normalized_path)
                send2trash(normalized_path)
                self.folder_images.remove(normalized_path)
                self.ctime_cache.pop(normalized_path, None)
                self.text_chunks_cache.pop(normalized_path, None)
                self.preview_images.pop(normalized_path, None)
                self.apply_filter()
                if len(self.filtered_images) == 0:
                    self.safe_close_fullscreen()
                    return
                next_index = delete_index
                self.fs_current_index = validate_index(next_index, self.filtered_images)
                self.fs_image_path = self.filtered_images[self.fs_current_index]
                self.fs_image = Image.open(self.fs_image_path)
                self.update_fs_image()
                self.update_fs_info_fullscreen()
                self.update_fs_texts()
            except Exception as e:
                self.status(f"Error deleting: {e}")
        if self.delete_immediately_fs_var.get():
            continue_after_delete()
        else:
            confirm = messagebox.askyesno("Delete image", f"Do you want to delete the image '{os.path.basename(normalized_path)}'?")
            if confirm:
                continue_after_delete()

    def open_image_in_system(self):
        if hasattr(self, "current_image_path") and self.current_image_path:
            if os.name == "nt":
                os.startfile(self.current_image_path)
            else:
                os.system(f'xdg-open "{self.current_image_path}"')
        else:
            self.status("No image selected.")

    def open_image_fs(self):
        if hasattr(self, "fs_image_path") and self.fs_image_path:
            if os.name == "nt":
                os.startfile(self.fs_image_path)
            else:
                os.system(f'xdg-open "{self.fs_image_path}"')
        else:
            self.status("No image available to open.")

    def copy_filename_fs(self):
        if hasattr(self, "fs_image_path") and self.fs_image_path:
            filename = os.path.basename(self.fs_image_path)
            copy_to_clipboard(self, filename)
            self.status("Image name copied.")
        else:
            self.status("No image selected.")

    def copy_full_path_fs(self):
        if hasattr(self, "fs_image_path") and self.fs_image_path:
            copy_to_clipboard(self, self.fs_image_path)
            self.status("Image path copied.")
        else:
            self.status("No image selected.")

    def update_fs_texts(self):
        for widget in self.fs_text_frame.winfo_children():
            widget.destroy()
        if self.fs_image_path not in self.text_chunks_cache:
            self.text_chunks_cache[self.fs_image_path] = extract_text_chunks(self.fs_image_path)
        prompt, negativ, settings = self.text_chunks_cache[self.fs_image_path]
        filter_text = self.filter_var.get()
        fs_prompt_text = ScrolledText(self.fs_text_frame, height=8, bg=TEXT_BG_COLOR,
                                      fg=TEXT_FG_COLOR, font=("Arial", self.main_font_size))
        fs_prompt_text.grid(row=0, column=0, padx=self.button_padding, pady=self.button_padding, sticky="nsew")
        self.highlight_text(fs_prompt_text, prompt, filter_text)
        fs_prompt_text.bind("<MouseWheel>", lambda e: self.fullscreen_mousewheel_text(e, fs_prompt_text))
        tk.Button(self.fs_text_frame, text="copy Prompt",
                  command=lambda: copy_to_clipboard(self, fs_prompt_text.get("1.0", tk.END)),
                  bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size)).grid(row=1, column=0, padx=self.button_padding)
        fs_negativ_text = ScrolledText(self.fs_text_frame, height=8, bg=TEXT_BG_COLOR,
                                       fg=TEXT_FG_COLOR, font=("Arial", self.main_font_size))
        fs_negativ_text.grid(row=0, column=1, padx=self.button_padding, pady=self.button_padding, sticky="nsew")
        self.highlight_text(fs_negativ_text, negativ, filter_text)
        fs_negativ_text.bind("<MouseWheel>", lambda e: self.fullscreen_mousewheel_text(e, fs_negativ_text))
        tk.Button(self.fs_text_frame, text="copy Negative",
                  command=lambda: copy_to_clipboard(self, fs_negativ_text.get("1.0", tk.END)),
                  bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size)).grid(row=1, column=1, padx=self.button_padding)
        fs_settings_text = ScrolledText(self.fs_text_frame, height=4, bg=TEXT_BG_COLOR,
                                        fg=TEXT_FG_COLOR, font=("Arial", self.main_font_size))
        fs_settings_text.grid(row=2, column=0, columnspan=2, padx=self.button_padding, pady=self.button_padding, sticky="nsew")
        self.highlight_text(fs_settings_text, settings, filter_text)
        fs_settings_text.bind("<MouseWheel>", lambda e: self.fullscreen_mousewheel_text(e, fs_settings_text))
        tk.Button(self.fs_text_frame, text="copy Settings",
                  command=lambda: copy_to_clipboard(self, fs_settings_text.get("1.0", tk.END)),
                  bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size)).grid(row=3, column=0, columnspan=2, padx=self.button_padding)
        for i in range(2):
            self.fs_text_frame.grid_columnconfigure(i, weight=1)
        self.fs_text_frame.grid_rowconfigure(0, weight=1)
        self.fs_text_frame.grid_rowconfigure(2, weight=0)

import json

def save_history(folder_list, filter_list):
    data = {
        "folder_history": folder_list[:10],
        "filter_history": filter_list[:10]
    }
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Fehler beim Speichern der History: {e}")

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Fehler beim Laden der History: {e}")
    return {"folder_history": [], "filter_history": []}

if __name__ == "__main__":
    app = ImageManagerForm()
    app.mainloop()
