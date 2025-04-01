#!/usr/bin/env python3 
# -*- coding: utf-8 -*-
"""
Datum: 2025-03-27
Versionsnummer: 1.0.36.3a
Interne Bezeichnung: Master8 Alpha5

Änderungen in Version 1.0.36.2:
- Anpassung der Textchunk-Aufteilung: "Steps:" wird jetzt im Settings-Feld beibehalten, anstatt es auszuschließen.
- Erweiterte Debug-Ausgabe: Anzeige von Betriebssystem, Python-Version, Monitorauflösung und Fehlerdetails im Debug-Fenster.
- Beibehaltung aller bestehenden Funktionen ohne Änderung, außer den notwendigen Anpassungen.
- Integration der neuen Routine zur Extraktion von Prompt-Daten aus JPEG-Dateien (PromptSlicer) und Korrektur von falsch benannten PNGs.
 
Zusammenfassung:
Ein Bildbetrachter für PNG- und JPEG-Dateien, der Textchunks auswertet (PNG: info['parameters'], JPEG: EXIF-Tag 37510) und in Prompt, Negativen Prompt und Settings aufteilt.
"""

import subprocess, sys
import os
import platform
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
    from piexif import helper
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "piexif"])
    import piexif
    from piexif import helper

VERSION = "1.0.36.3a"

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
# Neue extract_text_chunks()-Routine (Integration von PromptSlicer + Prüfung des File-Headers)
# ---------------------------------------------------------------------
def extract_text_chunks(img_path):
    # Öffne das Bild und überprüfe den Dateityp
    try:
        img = Image.open(img_path)
    except Exception as e:
        messagebox.showerror("Fehler", f"Fehler beim Öffnen des Bildes:\n{e}")
        return "", "", ""
    
    # Prüfe den Header: Falls die Datei mit der PNG-Signatur beginnt, behandle sie als PNG,
    # auch wenn die Endung .jpeg lautet.
    is_jpeg = img_path.lower().endswith((".jpg", ".jpeg"))
    with open(img_path, "rb") as f:
        header = f.read(8)
    if header.startswith(b'\x89PNG'):
        is_jpeg = False

    full_text = ""
    param_key = None
    debug_info = []
    
    if is_jpeg:
        # Extrahiere EXIF-Daten für JPEG
        try:
            exif_dict = piexif.load(img_path)
            user_comment = exif_dict.get("Exif", {}).get(piexif.ExifIFD.UserComment)
            if user_comment and isinstance(user_comment, bytes):
                debug_info.append(f"Debug: Rohe Bytes von UserComment: {user_comment[:50].hex()}...")
                if user_comment.startswith(b'UNICODE\x00\x00'):
                    try:
                        full_text = helper.UserComment.load(user_comment)
                        debug_info.append("Debug: Dekodierung mit piexif.helper erfolgreich.")
                        param_key = "EXIF-Exif-37510"
                    except Exception as e:
                        debug_info.append(f"Debug: piexif.helper Fehlermeldung: {e}")
                        full_text = user_comment[8:].decode("utf-16le", errors="ignore")
                        param_key = "EXIF-Exif-37510 (Fallback UTF-16LE)"
                else:
                    full_text = user_comment.decode("latin-1", errors="ignore")
                    debug_info.append("Debug: Kein UNICODE-Präfix, dekodiert als Latin-1.")
                    param_key = "EXIF-Exif-37510 (No UNICODE)"
            if not full_text:
                debug_info.append("Debug: Kein UserComment-Tag gefunden oder kein Byte-Daten.")
        except Exception as e:
            debug_info.append(f"Debug: Fehler beim Auslesen der EXIF-Daten: {e}")
    else:
        # Extrahiere Text aus PNG (oder falsch benannten PNG-Dateien)
        for key, value in img.info.items():
            if "parameters" in key.lower():
                param_key = key
                full_text = str(value)
                debug_info.append(f"Debug: PNG-Text aus {param_key}: {repr(full_text)[:100]}...")
                break

        # Fallback, falls kein "parameters"-Key gefunden wurde
        if not full_text:
            for key, value in img.info.items():
                if "prompt" in key.lower() or "metadata" in key.lower() or "description" in key.lower():
                    param_key = key
                    full_text = str(value)
                    debug_info.append(f"Debug: PNG-Text aus Fallback {param_key}: {repr(full_text)[:100]}...")
                    break
    
    if not full_text:
        debug_info.append(f"Debug: Kein Schlüssel mit {'UNICODE' if is_jpeg else 'parameters/fallback'} gefunden.")
        if hasattr(ImageManagerForm, 'instance'):
            ImageManagerForm.instance.debug_info = "\n".join(debug_info)
        return "", "", ""
    
    # Normalisieren: Reduziere alle Leerzeichenfolgen auf einen einzelnen Space
    normalized = ' '.join(full_text.split())
    debug_info.append(f"Debug: Normalized text: {repr(normalized)[:100]}...")
    
    # --- Neue Erweiterung: Unterstützung der neuen Marker ---
    # Prüfe, ob der Text die neuen Marker enthält: "prompt":, "negativePrompt":, "steps":
    normalized_lower = normalized.lower()
    if ('"prompt":' in normalized_lower and 
        '"negativeprompt":' in normalized_lower and 
        '"steps":' in normalized_lower):
        idx_prompt_new = normalized_lower.find('"prompt":')
        idx_negative_new = normalized_lower.find('"negativeprompt":')
        idx_steps_new = normalized_lower.find('"steps":')
        # Extrahiere die Inhalte zwischen den neuen Markern
        prompt_new = normalized[idx_prompt_new + len('"prompt":'): idx_negative_new].strip().strip('",')
        negativ_new = normalized[idx_negative_new + len('"negativeprompt":'): idx_steps_new].strip().strip('",')
        settings_new = normalized[idx_steps_new + len('"steps":'):].strip().strip('",')
        debug_info.extend([
            f"Debug (New Markers): Prompt: {repr(prompt_new)[:50]}...",
            f"Debug (New Markers): Negativ: {repr(negativ_new)[:50]}...",
            f"Debug (New Markers): Settings: {repr(settings_new)[:50]}..."
        ])
        if hasattr(ImageManagerForm, 'instance'):
            ImageManagerForm.instance.debug_info = "\n".join(debug_info)
        return prompt_new, negativ_new, settings_new
    # --- Ende Neue Erweiterung ---
    
    # Alte Marker: "Negative prompt:" und "Steps:"
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
            # Der Marker "Negative prompt:" wird NICHT übernommen
            negativ = normalized[idx_neg + len("Negative prompt:"): idx_steps].strip()
        else:
            negativ = normalized[idx_neg + len("Negative prompt:"):].strip()
    else:
        negativ = ""
    
    if idx_steps != -1:
        # Settings: Alles ab "Steps:" (Marker bleibt enthalten)
        settings = normalized[idx_steps:].strip()
    else:
        settings = ""
    
    debug_info.extend([
        f"Debug (Old Markers): Prompt: {repr(prompt)[:50]}...",
        f"Debug (Old Markers): Negativ: {repr(negativ)[:50]}...",
        f"Debug (Old Markers): Settings: {repr(settings)[:50]}..."
    ])
    
    if hasattr(ImageManagerForm, 'instance'):
        ImageManagerForm.instance.debug_info = "\n".join(debug_info)
    
    return prompt, negativ, settings
# ---------------------------------------------------------------------
# Restlicher Code (unverändert)
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
        header_text = f"ImagePromptViewer\nVersion: {VERSION}"
        self.header_label = tk.Label(self, text=header_text, fg=TEXT_FG_COLOR, bg=BG_COLOR,
                                     font=header_font, justify="left")
        self.header_label.pack(anchor="w", padx=self.button_padding, pady=self.button_padding)

        status_font = ("Arial", self.main_font_size)
        self.status_text = ScrolledText(self, height=2, bg=BG_COLOR, fg=TEXT_FG_COLOR, font=status_font)
        self.status_text.pack(fill="x", padx=self.button_padding, pady=self.button_padding)
        self.status("Formular gestartet.")

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
        
        # Erstelle einen neuen Style für die Combobox
        style = ttk.Style()
        style.configure("Custom.TCombobox", font=("Arial", 16))  # Schriftgröße hier z.B. 16

        # Beim Erstellen der Combobox den neuen Style anwenden
        self.filter_combo = ttk.Combobox(filter_frame, textvariable=self.filter_var, style="Custom.TCombobox", width=20)
        self.filter_combo.pack(side="left", padx=self.button_padding)

        self.filter_combo = ttk.Combobox(filter_frame, textvariable=self.filter_var, font=("Arial", self.main_font_size), width=20)
        self.filter_combo.pack(side="left", padx=self.button_padding)
        self.filter_combo.bind("<Return>", lambda e: self.apply_filter())
        self.clear_button = tk.Button(filter_frame, text="Clear", command=self.clear_filter,
                                      bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size), width=5)
        self.clear_button.pack(side="left", padx=self.button_padding)
        self.filter_filename_cb = tk.Checkbutton(filter_frame, text="Dateiname", variable=self.filter_filename_var, command=self.apply_filter,
                                                 fg=TEXT_FG_COLOR, bg=BG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size))
        self.filter_filename_cb.pack(side="left", padx=self.button_padding)
        self.filter_prompt_cb = tk.Checkbutton(filter_frame, text="Prompt", variable=self.filter_prompt_var, command=self.apply_filter,
                                               fg=TEXT_FG_COLOR, bg=BG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size))
        self.filter_prompt_cb.pack(side="left", padx=self.button_padding)
        self.filter_negativ_cb = tk.Checkbutton(filter_frame, text="Negativ Prompt", variable=self.filter_negativ_var, command=self.apply_filter,
                                                fg=TEXT_FG_COLOR, bg=BG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size))
        self.filter_negativ_cb.pack(side="left", padx=self.button_padding)
        self.filter_settings_cb = tk.Checkbutton(filter_frame, text="Settings", variable=self.filter_settings_var, command=self.apply_filter,
                                                 fg=TEXT_FG_COLOR, bg=BG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size))
        self.filter_settings_cb.pack(side="left", padx=self.button_padding)
        
        self.image_counter_frame = tk.Frame(filter_frame, bg=BG_COLOR)
        self.image_counter_frame.pack(side="left", padx=self.button_padding)
        self.image_counter_label = tk.Label(self.image_counter_frame, text="Ordner: 0 Bilder gefiltert ", fg=TEXT_FG_COLOR, bg=BG_COLOR, font=("Arial", self.main_font_size))
        self.image_counter_label.pack(side="left")
        self.filtered_counter_label = tk.Label(self.image_counter_frame, text="0", fg="red", bg=BG_COLOR, font=("Arial", self.main_font_size))
        self.filtered_counter_label.pack(side="left")
        self.image_counter_suffix_label = tk.Label(self.image_counter_frame, text=" Bilder", fg=TEXT_FG_COLOR, bg=BG_COLOR, font=("Arial", self.main_font_size))
        self.image_counter_suffix_label.pack(side="left")

        folder_frame = tk.Frame(self, bg=BG_COLOR)
        folder_frame.pack(fill="x", padx=self.button_padding, pady=self.button_padding)
        folder_label = tk.Label(folder_frame, text="Ordnerpfad:", fg=TEXT_FG_COLOR, bg=BG_COLOR, font=("Arial", self.main_font_size))
        folder_label.pack(side="left", padx=self.button_padding)
        self.folder_path_var = tk.StringVar()
        self.folder_entry = tk.Entry(folder_frame, textvariable=self.folder_path_var,
                                     fg=TEXT_FG_COLOR, bg=TEXT_BG_COLOR, font=("Arial", self.main_font_size), width=int(50 * self.scaling_factor))
        self.folder_entry.pack(side="left", padx=self.button_padding)
        self.choose_folder_button = tk.Button(folder_frame, text="Ordner auswählen", command=self.choose_folder,
                                              bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        self.choose_folder_button.pack(side="left", padx=self.button_padding)
        self.select_image_button = tk.Button(folder_frame, text="Bild auswählen", command=self.select_image_from_folder,
                                             bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        self.select_image_button.pack(side="left", padx=self.button_padding)
        self.open_image_button = tk.Button(folder_frame, text="Bild anzeigen", command=self.open_image_in_system,
                                           bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        self.open_image_button.pack(side="left", padx=self.button_padding)
        self.delete_button_main = tk.Button(folder_frame, text="Bild löschen", command=self.delete_current_image,
                                            bg=BTN_BG_COLOR if not self.delete_immediately_main_var.get() else "red", fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        self.delete_button_main.pack(side="right", padx=self.button_padding)
        self.delete_immediately_main_cb = tk.Checkbutton(folder_frame, text="sofort löschen", variable=self.delete_immediately_main_var,
                                                         command=self.update_delete_button_color_main, fg=TEXT_FG_COLOR,
                                                         bg=BG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size))
        self.delete_immediately_main_cb.pack(side="right", padx=self.button_padding)

        subfolder_frame = tk.Frame(self, bg=BG_COLOR)
        subfolder_frame.pack(fill="x", padx=self.button_padding, pady=self.button_padding)
        self.subfolder_cb = tk.Checkbutton(subfolder_frame, text="Unterordner durchsuchen", variable=self.search_subfolders_var,
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
        self.back_button = tk.Button(nav_frame, text="zurück", command=self.show_previous_image,
                                     bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size), width=10)
        self.back_button.pack(side="left", padx=self.button_padding)
        self.next_button = tk.Button(nav_frame, text="weiter", command=self.show_next_image,
                                     bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size), width=10)
        self.next_button.pack(side="left", padx=self.button_padding)

        controls_frame = tk.Frame(self, bg=BG_COLOR)
        controls_frame.pack(pady=self.button_padding)
        self.scale_var = tk.StringVar(value=DEFAULT_SCALE)
        self.scale_dropdown = tk.OptionMenu(controls_frame, self.scale_var, *SCALE_OPTIONS, command=lambda value: self.rescale_image(value))
        self.scale_dropdown.configure(bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", int(self.main_font_size + 2 * self.scaling_factor)))
        self.scale_dropdown.pack(side="left", padx=self.button_padding)
        self.fullscreen_button = tk.Button(controls_frame, text="Vollbild", command=self.show_fullscreen,
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
        self.copy_negativ_button = tk.Button(textchunks_frame, text="copy Negativ",
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

        self.preview_frame = tk.Frame(self, bg=BG_COLOR)
        self.preview_frame.pack(fill="both", padx=self.button_padding, pady=self.button_padding, expand=True)
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

        self.status("Formular geladen.")

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
        if hasattr(self, 'filter_combo'):
            self.filter_combo.config(font=("Arial", self.main_font_size))
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
        self.status(f"Vollbild-Monitor gewechselt auf: {choice}")

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
                self.display_image(self.filtered_images[self.current_index])
                self.extract_and_display_text_chunks(self.filtered_images[self.current_index])
            self.status(f"Sortierung geändert zu: {self.sort_order}")

    def status(self, message):
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete("1.0", tk.END)
        self.status_text.insert(tk.END, f"{get_datetime_str()}: {message}")
        self.status_text.config(state=tk.DISABLED)

    def show_debug_info(self):
        # Erweiterte Debug-Informationen anzeigen
        debug_win = tk.Toplevel(self)
        debug_win.title("Debug Information")
        debug_win.configure(bg=BG_COLOR)
        debug_text = ScrolledText(debug_win, width=80, height=20, bg=BG_COLOR, fg=TEXT_FG_COLOR, font=("Arial", self.main_font_size))
        
        # Systeminformationen sammeln
        os_info = f"Betriebssystem: {platform.system()} {platform.release()}"
        python_version = f"Python-Version: {sys.version.split()[0]}"
        monitor_info = f"Aktuelle Monitorauflösung: {self.selected_monitor.width}x{self.selected_monitor.height}"
        
        # Zusammenstellen der Debug-Ausgabe
        debug_content = (
            f"Systeminformationen:\n"
            f"{os_info}\n"
            f"{python_version}\n"
            f"{monitor_info}\n\n"
            f"Debug-Details:\n"
            f"{self.debug_info if self.debug_info else 'Keine Debug-Informationen verfügbar.'}"
        )
        
        debug_text.insert(tk.END, debug_content)
        debug_text.config(state=tk.DISABLED)
        debug_text.pack(padx=self.button_padding, pady=self.button_padding)
        
        copy_btn = tk.Button(debug_win, text="Copy", command=lambda: copy_to_clipboard(self, debug_content),
                             bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        copy_btn.pack(side="left", padx=self.button_padding, pady=self.button_padding)
        close_btn = tk.Button(debug_win, text="Schließen", command=debug_win.destroy,
                              bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        close_btn.pack(side="right", padx=self.button_padding, pady=self.button_padding)

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
        filter_text = self.filter_var.get().lower()
        if filter_text and filter_text not in self.filter_history:
            self.filter_history.append(filter_text)
            self.filter_combo['values'] = list(reversed(self.filter_history))
        self.filtered_images = []
        
        if not filter_text:
            self.filtered_images = self.folder_images.copy()
        else:
            for file_path in self.folder_images:
                include = False
                filename = os.path.basename(file_path).lower()
                if file_path not in self.text_chunks_cache:
                    self.text_chunks_cache[file_path] = extract_text_chunks(file_path)
                prompt, negativ, settings = self.text_chunks_cache[file_path]
                prompt = prompt.lower()
                negativ = negativ.lower()
                settings = settings.lower()

                if self.filter_filename_var.get() and filter_text in filename:
                    include = True
                if self.filter_prompt_var.get() and filter_text in prompt:
                    include = True
                if self.filter_negativ_var.get() and filter_text in negativ:
                    include = True
                if self.filter_settings_var.get() and filter_text in settings:
                    include = True

                if include:
                    self.filtered_images.append(file_path)

        if self.filtered_images:
            self.filtered_images.sort(key=lambda x: self.ctime_cache[x], reverse=(self.sort_order == "DESC"))

        if self.current_index != -1 and hasattr(self, 'current_image_path') and self.current_image_path in self.filtered_images:
            self.current_index = self.filtered_images.index(self.current_image_path)
        else:
            self.current_index = 0 if self.filtered_images else -1
            if self.current_index != -1:
                self.display_image(self.filtered_images[self.current_index])
                self.extract_and_display_text_chunks(self.filtered_images[self.current_index])

        self.populate_preview_table_lazy()
        total_images = len(self.folder_images)
        filtered_images = len(self.filtered_images)
        self.image_counter_label.config(text=f"Ordner: {total_images} Bilder gefiltert ")
        self.filtered_counter_label.config(text=f"{filtered_images}")
        self.image_counter_suffix_label.config(text=" Bilder")
        self.status(f"Filter angewendet: {len(self.filtered_images)} Bilder gefunden.")

    def highlight_text(self, text_widget, text, filter_text):
        text_widget.delete("1.0", tk.END)
        text_widget.insert("1.0", text)
        if filter_text:
            filter_text = filter_text.lower()
            text_lower = text.lower()
            start_pos = 0
            while True:
                pos = text_lower.find(filter_text, start_pos)
                if pos == -1:
                    break
                start = f"1.0 + {pos} chars"
                end = f"1.0 + {pos + len(filter_text)} chars"
                text_widget.tag_add("highlight", start, end)
                start_pos = pos + len(filter_text)
            text_widget.tag_config("highlight", foreground=HIGHLIGHT_COLOR)

    def load_folder_async(self, folder, file_path=None):
        self.status("Lade Ordner im Hintergrund...")
        self.folder_images = []
        self.ctime_cache.clear()
        self.text_chunks_cache.clear()
        if self.search_subfolders_var.get():
            self.folder_images = [os.path.normpath(str(p)) for p in Path(folder).rglob("*") if p.suffix.lower() in IMAGE_EXTENSIONS]
        else:
            self.folder_images = [os.path.normpath(os.path.join(folder, f)) for f in os.listdir(folder) if f.lower().endswith(IMAGE_EXTENSIONS)]
        
        for img_path in self.folder_images:
            self.ctime_cache[img_path] = os.path.getctime(img_path)
        
        self.folder_images.sort(key=lambda x: self.ctime_cache[x], reverse=(self.sort_order == "DESC"))
        self.after(0, lambda: self.on_folder_loaded(folder, file_path))

    def on_folder_loaded(self, folder, file_path):
        if self.folder_images:
            if file_path:
                file_path = os.path.normpath(file_path)
                self.status(f"Debug: Ausgewählter Pfad: {file_path}")
                self.status(f"Debug: Erster Pfad in folder_images: {self.folder_images[0] if self.folder_images else 'Leer'}")
            
            if file_path and file_path in self.folder_images:
                self.current_index = self.folder_images.index(file_path)
                self.status(f"Debug: Bild gefunden, Index: {self.current_index}")
            else:
                self.current_index = 0 if len(self.folder_images) > 0 else -1
                if file_path:
                    self.status(f"Debug: Bild nicht in folder_images gefunden, setze Index auf {self.current_index}")

            if self.current_index != -1:
                self.display_image(self.folder_images[self.current_index], default_scale=True)
                self.extract_and_display_text_chunks(self.folder_images[self.current_index])
            
            self.apply_filter()
            self.status(f"Ordner geladen: {folder} ({len(self.folder_images)} Bilder, {len(self.filtered_images)} gefiltert)")
        else:
            self.status("Keine Bilder im ausgewählten Ordner gefunden.")

    def handle_drop(self, event):
        file_path = event.data.strip("{}")
        if os.path.isfile(file_path) and file_path.lower().endswith(IMAGE_EXTENSIONS):
            folder = os.path.dirname(file_path)
            self.folder_path_var.set(folder)
            threading.Thread(target=self.load_folder_async, args=(folder, file_path), daemon=True).start()

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Ordner auswählen")
        if folder:
            self.folder_path_var.set(folder)
            threading.Thread(target=self.load_folder_async, args=(folder,), daemon=True).start()

    def select_image_from_folder(self):
        file_path = filedialog.askopenfilename(title="Bild auswählen", filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if file_path:
            folder = os.path.dirname(file_path)
            self.folder_path_var.set(folder)
            threading.Thread(target=self.load_folder_async, args=(folder, file_path), daemon=True).start()

    def show_info(self):
        info_win = tk.Toplevel(self)
        info_win.title("Information")
        info_win.configure(bg=BG_COLOR)
        info_text = (
            "ImagePromptViewer - Gebrauchsanweisung:\n\n"
            "Überblick:\n"
            "Dieses Programm dient als Bildbetrachter für PNG- und JPEG-Bilder, der eingebettete Texte ausliest. PNGs nutzen info['parameters'] und JPEGs den EXIF-Tag 'UserComment' (mit UNICODE-Präfix), um den Text in Prompt, Negativ Prompt und Settings aufzuteilen.\n\n"
            "Hauptfunktionen:\n"
            "- Bildanzeige und Navigation:\n"
            "  • Das aktuelle Bild wird im Hauptfenster angezeigt.\n"
            "  • Mit den Pfeiltasten oder dem Mausrad können Sie vor- und zurücknavigieren.\n"
            "  • Ein per Drag & Drop eingefügtes Bild lädt automatisch den gesamten Ordner.\n\n"
            "- Filterung:\n"
            "  • Geben Sie einen Suchbegriff ein und wählen Sie mittels der Checkboxen, ob Dateiname, Prompt, Negativ Prompt oder Settings durchsucht werden sollen.\n"
            "  • Klicken Sie auf 'Filter', um den Suchbegriff anzuwenden, oder auf 'Clear', um den Filter zu entfernen.\n\n"
            "- Ordner- und Bildauswahl:\n"
            "  • 'Ordner auswählen' öffnet einen Dialog zur Auswahl eines Bildordners.\n"
            "  • 'Bild auswählen' erlaubt die direkte Auswahl einer Bilddatei, wobei der zugehörige Ordner geladen wird.\n"
            "  • 'Bild anzeigen' öffnet das aktuell ausgewählte Bild im Standard-Systembetrachter.\n\n"
            "- Löschen:\n"
            "  • 'Bild löschen' verschiebt das aktuell angezeigte Bild in den Papierkorb.\n"
            "  • Mit dem 'sofort löschen'-Kontrollkästchen (Button wechselt zu Rot, wenn aktiv) wird das Bild ohne Rückfrage gelöscht.\n\n"
            "- Vollbildmodus:\n"
            "  • Über den 'Vollbild'-Button wird das Bild im Vollbildmodus angezeigt, inklusive Textfeldern für Prompt, Negativ Prompt und Settings.\n"
            "  • Weitere Buttons im Vollbildmodus ermöglichen das Kopieren des Bildnamens oder -pfads, das Löschen des Bildes sowie das Ein- bzw. Ausblenden des Prompt-Bereichs.\n\n"
            "- Weitere Funktionen:\n"
            "  • Die 'Always on Top'-Option sorgt dafür, dass das Fenster immer im Vordergrund bleibt (Standard: deaktiviert).\n"
            "  • Der 'Debug'-Button öffnet ein Fenster mit erweiterten System- und Debug-Informationen (Betriebssystem, Python-Version, Monitorauflösung etc.).\n"
            "  • Schriftgrößen und Layout passen sich dynamisch der Monitorauflösung an.\n\n"
            "Bedienungshinweise:\n"
            "  • Nutzen Sie die Navigation per Mausrad oder Pfeiltasten über dem Bild.\n"
            "  • Ziehen Sie ein Bild in den markierten Bereich ('Drop Image Here'), um den zugehörigen Ordner zu laden.\n"
            "  • Verwenden Sie die Filteroptionen, um gezielt nach Bildinhalten zu suchen.\n\n"
            "Viel Spaß beim Arbeiten mit ImagePromptViewer!"
        )

        st = ScrolledText(info_win, width=80, height=20, bg=BG_COLOR, fg=TEXT_FG_COLOR, font=("Arial", self.main_font_size))
        st.insert(tk.END, info_text)
        st.config(state=tk.DISABLED)
        st.pack(padx=self.button_padding, pady=self.button_padding)
        close_btn = tk.Button(info_win, text="Schließen", command=info_win.destroy,
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
                if file_path not in self.preview_images:
                    try:
                        img = Image.open(file_path)
                        img.thumbnail((int(100 * self.scaling_factor), int(100 * self.scaling_factor)))
                        tk_img = ImageTk.PhotoImage(img)
                        self.preview_images[file_path] = tk_img
                    except Exception:
                        tk_img = None
                else:
                    tk_img = self.preview_images[file_path]
                if tk_img:
                    img_label = tk.Label(frame, image=tk_img, bg=BG_COLOR)
                    img_label.image = tk_img
                    img_label.pack(side="left", before=frame.winfo_children()[0])
                    img_label.bind("<Button-1>", lambda e, idx=i: self.on_preview_click(idx))

    def on_preview_click(self, index):
        if 0 <= index < len(self.filtered_images):
            self.current_index = index
            self.display_image(self.filtered_images[self.current_index])
            self.extract_and_display_text_chunks(self.filtered_images[self.current_index])

    def display_image(self, file_path, default_scale=False):
        try:
            self.current_image = Image.open(file_path)
        except Exception as e:
            self.status(f"Fehler beim Öffnen des Bildes: {e}")
            return
        
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
        self.status(f"Bild geladen: {os.path.basename(file_path)}")
        try:
            ctime = self.ctime_cache[file_path]
            created_str = datetime.fromtimestamp(ctime).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            created_str = "Unbekannt"
        info_text = f"Dateiname: {os.path.basename(file_path)}\nPfad: {file_path}\nErstellt: {created_str}"
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
        if self.filtered_images and self.current_index < len(self.filtered_images) - 1:
            self.current_index += 1
            self.display_image(self.filtered_images[self.current_index])
            self.extract_and_display_text_chunks(self.filtered_images[self.current_index])

    def show_previous_image(self):
        if self.filtered_images and self.current_index > 0:
            self.current_index -= 1
            self.display_image(self.filtered_images[self.current_index])
            self.extract_and_display_text_chunks(self.filtered_images[self.current_index])

    def delete_current_image(self):
        if not hasattr(self, "current_image_path") or not self.current_image_path:
            self.status("Kein Bild zum Löschen ausgewählt.")
            return
        normalized_path = os.path.normpath(self.current_image_path)
        if not os.path.exists(normalized_path):
            self.status("Datei nicht gefunden.")
            return
        if self.delete_immediately_main_var.get():
            try:
                send2trash(normalized_path)
                self.folder_images.pop(self.folder_images.index(normalized_path))
                if normalized_path in self.ctime_cache:
                    del self.ctime_cache[normalized_path]
                if normalized_path in self.text_chunks_cache:
                    del self.text_chunks_cache[normalized_path]
                if normalized_path in self.preview_images:
                    del self.preview_images[normalized_path]
                self.apply_filter()
                self.status("Bild in den Papierkorb verschoben.")
                if self.current_index >= len(self.filtered_images):
                    self.current_index = len(self.filtered_images) - 1
                if self.filtered_images:
                    self.display_image(self.filtered_images[self.current_index])
                    self.extract_and_display_text_chunks(self.filtered_images[self.current_index])
            except Exception as e:
                self.status(f"Fehler beim Löschen: {e}")
        else:
            confirm = messagebox.askyesno("Bild löschen", f"Möchten Sie das Bild '{os.path.basename(normalized_path)}' löschen?")
            if confirm:
                try:
                    send2trash(normalized_path)
                    self.folder_images.pop(self.folder_images.index(normalized_path))
                    if normalized_path in self.ctime_cache:
                        del self.ctime_cache[normalized_path]
                    if normalized_path in self.text_chunks_cache:
                        del self.text_chunks_cache[normalized_path]
                    if normalized_path in self.preview_images:
                        del self.preview_images[normalized_path]
                    self.apply_filter()
                    self.status("Bild in den Papierkorb verschoben.")
                    if self.current_index >= len(self.filtered_images):
                        self.current_index = len(self.filtered_images) - 1
                    if self.filtered_images:
                        self.display_image(self.filtered_images[self.current_index])
                        self.extract_and_display_text_chunks(self.filtered_images[self.current_index])
                except Exception as e:
                    self.status(f"Fehler beim Löschen: {e}")

    def show_fullscreen(self):
        if not hasattr(self, "current_image") or not self.current_image:
            self.status("Kein Bild zum Vollbild verfügbar.")
            return
        self.fs_image_path = self.filtered_images[self.current_index]
        try:
            self.fs_image = Image.open(self.fs_image_path)
        except Exception as e:
            self.status(f"Fehler im Vollbild: {e}")
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
        self.fs_text_focus = False

        info_font_size = int(self.main_font_size * 0.9)
        self.fs_info_label = tk.Label(self.fullscreen_win, text="", fg=TEXT_FG_COLOR, bg=BG_COLOR,
                                      font=("Arial", info_font_size))
        self.fs_info_label.pack(side="top", anchor="n", pady=self.button_padding)
        self.update_fs_info_fullscreen()

        top_buttons = tk.Frame(self.fullscreen_win, bg=BG_COLOR)
        top_buttons.pack(anchor="nw", padx=self.button_padding, pady=self.button_padding)
        self.fs_delete_button = tk.Button(top_buttons, text="Bild löschen", command=self.fs_delete_current_image,
                                          bg="red" if self.delete_immediately_fs_var.get() else BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        self.fs_delete_button.pack(side="left", padx=self.button_padding)
        self.delete_immediately_fs_cb = tk.Checkbutton(top_buttons, text="sofort löschen", variable=self.delete_immediately_fs_var,
                                                       command=self.update_delete_button_color_fs, fg=TEXT_FG_COLOR,
                                                       bg=BG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size))
        self.delete_immediately_fs_cb.pack(side="left", padx=self.button_padding)
        self.fs_close_button = tk.Button(top_buttons, text="Schließen", command=self.safe_close_fullscreen,
                                         bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        self.fs_close_button.pack(side="left", padx=self.button_padding)
        btn_fs_open = tk.Button(top_buttons, text="Bild anzeigen", command=self.open_image_fs,
                                bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        btn_fs_open.pack(side="left", padx=self.button_padding)
        btn_fs_copy_name = tk.Button(top_buttons, text="Bildname kopieren", command=self.copy_filename_fs,
                                     bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        btn_fs_copy_name.pack(side="left", padx=self.button_padding)
        btn_fs_copy_path = tk.Button(top_buttons, text="Bild-Pfad kopieren", command=self.copy_full_path_fs,
                                     bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size))
        btn_fs_copy_path.pack(side="left", padx=self.button_padding)

        self.prompt_toggle = tk.Button(self.fullscreen_win, text="Prompt ausblenden", command=self.toggle_fs_prompt,
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

    def safe_close_fullscreen(self):
        try:
            if self.fullscreen_win and self.fullscreen_win.winfo_exists():
                self.fullscreen_win.destroy()
            if hasattr(self, "fs_image_path") and self.fs_image_path in self.filtered_images:
                self.current_index = self.filtered_images.index(self.fs_image_path)
                self.display_image(self.fs_image_path)
                self.extract_and_display_text_chunks(self.fs_image_path)
        except tk.TclError:
            pass

    def update_fs_info_fullscreen(self):
        if not hasattr(self, "fs_image_path") or not self.fs_image_path:
            self.fs_info_label.config(text="Kein Bild ausgewählt")
            return
        try:
            ctime = self.ctime_cache[self.fs_image_path]
            created_str = datetime.fromtimestamp(ctime).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            created_str = "Unbekannt"
        try:
            dimensions = f"{self.fs_image.width}x{self.fs_image.height}"
        except Exception:
            dimensions = "Unbekannt"
        info = (f"Dateiname: {os.path.basename(self.fs_image_path)}\n"
                f"Pfad: {self.fs_image_path}\n"
                f"Erstellt: {created_str}\n"
                f"Auflösung: {dimensions}")
        if len(self.filtered_images) < len(self.folder_images):
            info += "\nFILTER AKTIV!"
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
        if self.filtered_images and self.current_index < len(self.filtered_images) - 1:
            self.current_index += 1
            self.fs_image_path = self.filtered_images[self.current_index]
            try:
                self.fs_image = Image.open(self.fs_image_path)
            except Exception as e:
                self.status(f"Fehler im Vollbild: {e}")
                return
            self.update_fs_image()
            self.update_fs_info_fullscreen()
            self.update_fs_texts()

    def fs_show_previous(self):
        if self.filtered_images and self.current_index > 0:
            self.current_index -= 1
            self.fs_image_path = self.filtered_images[self.current_index]
            try:
                self.fs_image = Image.open(self.fs_image_path)
            except Exception as e:
                self.status(f"Fehler im Vollbild: {e}")
                return
            self.update_fs_image()
            self.update_fs_info_fullscreen()
            self.update_fs_texts()

    def toggle_fs_prompt(self):
        if self.fs_text_visible:
            self.fs_text_frame.pack_forget()
            self.fs_text_visible = False
            self.prompt_toggle.config(text="Prompt anzeigen")
        else:
            self.fs_text_frame.pack(side="right", fill="both", expand=True, padx=self.button_padding, pady=self.button_padding)
            self.fs_text_visible = True
            self.prompt_toggle.config(text="Prompt ausblenden")
            self.update_fs_texts()
        self.fullscreen_win.after(100, self.update_fs_image)

    def fs_delete_current_image(self):
        if not hasattr(self, "fs_image_path") or not self.fs_image_path:
            self.status("Kein Bild zum Löschen ausgewählt.")
            return
        normalized_path = os.path.normpath(self.fs_image_path)
        if not os.path.exists(normalized_path):
            self.status("Datei nicht gefunden.")
            return
        if self.delete_immediately_fs_var.get():
            try:
                send2trash(normalized_path)
                self.folder_images.pop(self.folder_images.index(normalized_path))
                if normalized_path in self.ctime_cache:
                    del self.ctime_cache[normalized_path]
                if normalized_path in self.text_chunks_cache:
                    del self.text_chunks_cache[normalized_path]
                if normalized_path in self.preview_images:
                    del self.preview_images[normalized_path]
                self.apply_filter()
                self.status("Bild in den Papierkorb verschoben.")
                if self.current_index >= len(self.filtered_images):
                    self.current_index = len(self.filtered_images) - 1
                if self.filtered_images:
                    self.fs_image_path = self.filtered_images[self.current_index]
                    self.fs_image = Image.open(self.fs_image_path)
                    self.update_fs_image()
                    self.update_fs_info_fullscreen()
                    self.update_fs_texts()
            except Exception as e:
                self.status(f"Fehler beim Löschen: {e}")
        else:
            confirm = messagebox.askyesno("Bild löschen", f"Möchten Sie das Bild '{os.path.basename(normalized_path)}' löschen?")
            if confirm:
                try:
                    send2trash(normalized_path)
                    self.folder_images.pop(self.folder_images.index(normalized_path))
                    if normalized_path in self.ctime_cache:
                        del self.ctime_cache[normalized_path]
                    if normalized_path in self.text_chunks_cache:
                        del self.text_chunks_cache[normalized_path]
                    if normalized_path in self.preview_images:
                        del self.preview_images[normalized_path]
                    self.apply_filter()
                    self.status("Bild in den Papierkorb verschoben.")
                    if self.current_index >= len(self.filtered_images):
                        self.current_index = len(self.filtered_images) - 1
                    if self.filtered_images:
                        self.fs_image_path = self.filtered_images[self.current_index]
                        self.fs_image = Image.open(self.fs_image_path)
                        self.update_fs_image()
                        self.update_fs_info_fullscreen()
                        self.update_fs_texts()
                except Exception as e:
                    self.status(f"Fehler beim Löschen: {e}")

    def open_image_in_system(self):
        if hasattr(self, "current_image_path") and self.current_image_path:
            if os.name == "nt":
                os.startfile(self.current_image_path)
            else:
                os.system(f'xdg-open "{self.current_image_path}"')
        else:
            self.status("Kein Bild ausgewählt.")

    def open_image_fs(self):
        if hasattr(self, "fs_image_path") and self.fs_image_path:
            if os.name == "nt":
                os.startfile(self.fs_image_path)
            else:
                os.system(f'xdg-open "{self.fs_image_path}"')
        else:
            self.status("Kein Bild zum Öffnen vorhanden.")

    def copy_filename_fs(self):
        if hasattr(self, "fs_image_path") and self.fs_image_path:
            filename = os.path.basename(self.fs_image_path)
            copy_to_clipboard(self, filename)
            self.status("Bildname kopiert.")
        else:
            self.status("Kein Bild ausgewählt.")

    def copy_full_path_fs(self):
        if hasattr(self, "fs_image_path") and self.fs_image_path:
            copy_to_clipboard(self, self.fs_image_path)
            self.status("Bild-Pfad kopiert.")
        else:
            self.status("Kein Bild ausgewählt.")

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
        tk.Button(self.fs_text_frame, text="copy Negativ",
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

if __name__ == "__main__":
    app = ImageManagerForm()
    app.mainloop()
