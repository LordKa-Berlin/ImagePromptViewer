#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Datum: 2025-03-25
Versionsnummer: 1.0.31.9
Interne Bezeichnung: Master 3 Alpha 1

Beschreibung:
ImagePromptViewer – Bildverwaltung und -anzeige für PNG-Dateien mit Textchunk-Analyse.
Liest PNG-Bilder ein und extrahiert Prompt, Negativ Prompt und Settings aus dem Text-Chunk.
Haupt- und Vollbildansicht mit Navigation, Kopierfunktionen und Bildöffnung im Systembetrachter.
Dynamische Anpassung an Monitorauflösung für Schriftgrößen, Buttons und Formulargröße.

Änderungen in Version 1.0.31.9:
- Debug-Informationen aus Statuszeile entfernt, neuer "Debug"-Button neben "?" hinzugefügt, der ein Fenster mit Debug-Info und "Copy"-Button öffnet.
- Bildinfo im Hauptformular angepasst: Dateiname über Pfad, um Platz zu sparen.
- Bildzähler hinter "Settings"-Kontrollkästchen hinzugefügt, zeigt die Anzahl der aktuell angezeigten Bilder.
- Kontrollkästchen "Settings" zum Filter-Frame hinzugefügt, um auch im Settings-Feld zu filtern.
- "Clear"-Button hinter dem Filter-Suchfeld eingefügt, um das Filterfeld zu leeren.
- Hinweis "FILTER AKTIV!" in der Vollbildansicht zur Bildinfo hinzugefügt, wenn die Liste gefiltert ist.
- Funktion extract_png_text_chunks mit detaillierten Kommentaren versehen und als unveränderlich markiert.
- Scroll-Problem in Vollbildansicht behoben: Scrollen im Textfeld möglich, wenn Mauszeiger darüber.
- Filter-Textfeld und Kontrollfelder über Ordnerpfad hinzugefügt.
- Filterlogik implementiert: Filtert Bilder basierend auf Eingabe im Filterfeld und ausgewählten Kontrollfeldern.
- Fehlerbehebung beim Löschen von Bildern mit korrekter Pfadbehandlung.
- Positionierung der Buttons "Bild löschen" und "Bild anzeigen" angepasst.
- Kontrollfeld "sofort löschen" hinzugefügt, um den Löschvorgang zu steuern.
- Verknüpfung der "Entf"-Taste mit dem "Bild löschen" Button.
- Sicherstellung, dass der "Bild löschen" Button rot bleibt, wenn "sofort löschen" aktiviert ist.
"""

import subprocess, sys
import os
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import threading
from pathlib import Path

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

VERSION = "1.0.31.9"

BG_COLOR = "#1F1F1F"
BTN_BG_COLOR = "#FFA500"
BTN_FG_COLOR = "#000000"
TEXT_BG_COLOR = "#333333"
TEXT_FG_COLOR = "#FFA500"

SCALE_OPTIONS = ["Default", "25%", "50%", "75%"]
DEFAULT_SCALE = "Default"
IMAGE_EXTENSIONS = (".png", ".PNG")

def get_datetime_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def copy_to_clipboard(widget, text):
    widget.clipboard_clear()
    widget.clipboard_append(text)
    widget.update()

# Funktion darf nicht verändert werden!
def extract_png_text_chunks(png_path):
    """
    Extrahiert Prompt, Negativ Prompt und Settings aus dem Textchunk eines PNG-Bildes.
    Diese Funktion ist auf die spezifische Struktur der Textchunks abgestimmt und darf nicht verändert werden,
    da sie die korrekte Aufteilung der Felder sicherstellt.

    Funktionsweise:
    1. Öffnet das PNG-Bild und liest die Metadaten (info) aus.
    2. Sucht nach einem Schlüssel (z. B. "tEXtparameters"), der "parameters" enthält, und verwendet dessen Wert als full_text.
    3. Bestimmt den Startpunkt nach "parameters" oder am Anfang des Werts, falls "parameters" nur im Schlüssel steht.
    4. Sucht die Trennstellen "Negative prompt:" und "Steps:" (case-sensitive).
    5. Teilt den Text in drei Teile:
       - Prompt: Vom Start bis "Negative prompt:" (oder "Steps:" oder Ende, falls keine Trennstellen).
       - Negativ Prompt: Von "Negative prompt:" bis "Steps:" (oder Ende, falls kein "Steps:").
       - Settings: Von "Steps:" bis zum Ende.
    6. Gibt die drei Teile als Tuple zurück und speichert Debugging-Informationen in einer Instanzvariable.

    Parameter:
    - png_path: Pfad zur PNG-Datei.

    Rückgabe:
    - Tuple (prompt, negativ, settings) mit den extrahierten Textteilen.
    """
    try:
        img = Image.open(png_path)
    except Exception as e:
        messagebox.showerror("Fehler", f"Fehler beim Öffnen des Bildes:\n{e}")
        return "", "", ""
    
    info = img.info
    # Suche nach einem Schlüssel, der "parameters" enthält
    param_key = None
    full_text = ""
    for key, value in info.items():
        if "parameters" in key.lower():
            param_key = key
            full_text = str(value)
            break
    
    if not full_text:
        if hasattr(ImageManagerForm, 'instance'):
            ImageManagerForm.instance.debug_info = "Debug: Kein Schlüssel mit 'parameters' gefunden."
        return "", "", ""
    
    # Debugging-Informationen speichern
    debug_info = f"Debug: Text aus {param_key}: {repr(full_text)[:100]}...\n"
    
    # Bestimme Startpunkt nach "parameters" oder am Anfang des Werts
    idx_params = full_text.find("parameters")
    start = idx_params + len("parameters") if idx_params != -1 else 0
    idx_neg = full_text.find("Negative prompt:", start)
    idx_steps = full_text.find("Steps:", start)
    
    # Extrahiere Prompt
    if idx_neg != -1:
        prompt = full_text[start:idx_neg].strip()
    elif idx_steps != -1:
        prompt = full_text[start:idx_steps].strip()
    else:
        prompt = full_text[start:].strip()
    
    # Extrahiere Negativ Prompt
    if idx_neg != -1:
        if idx_steps != -1 and idx_steps > idx_neg:
            negativ = full_text[idx_neg + len("Negative prompt:"):idx_steps].strip()
        else:
            negativ = full_text[idx_neg + len("Negative prompt:"):].strip()
    else:
        negativ = ""
    
    # Extrahiere Settings
    if idx_steps != -1:
        settings = full_text[idx_steps + len("Steps:"):].strip()
    else:
        settings = ""
    
    # Debugging-Informationen speichern
    if hasattr(ImageManagerForm, 'instance'):
        ImageManagerForm.instance.debug_info = (
            debug_info +
            f"Debug: Prompt: {prompt[:50]}...\n" +
            f"Debug: Negativ: {negativ[:50]}...\n" +
            f"Debug: Settings: {settings[:50]}..."
        )
    
    return prompt, negativ, settings

def get_scaling_factor(monitor):
    base_height = 1080
    factor = monitor.height / base_height
    return max(0.8, min(1.5, factor))

def get_font_size(monitor, base_size=12):
    factor = get_scaling_factor(monitor)
    return max(10, min(16, int(base_size * factor)))

def get_button_padding(monitor):
    factor = get_scaling_factor(monitor)
    return int(5 * factor)

class ImageManagerForm(TkinterDnD.Tk):
    instance = None  # Klassenattribut zur Speicherung der Instanz

    def __init__(self):
        super().__init__()
        ImageManagerForm.instance = self  # Instanz speichern für Debugging
        self.title(f"ImagePromptViewer (Version {VERSION})")
        self.configure(bg=BG_COLOR)
        
        self.monitor_list = get_monitors()
        self.selected_monitor = self.monitor_list[0]
        self.scaling_factor = get_scaling_factor(self.selected_monitor)
        self.main_font_size = get_font_size(self.selected_monitor)
        self.button_padding = get_button_padding(self.selected_monitor)

        base_width, base_height = 1200, 1120
        window_width = int(base_width * self.scaling_factor)
        window_height = int(base_height * self.scaling_factor)
        self.geometry(f"{window_width}x{window_height}")
        self.resizable(True, True)
        self.attributes("-topmost", False)

        self.folder_images = []
        self.filtered_images = []  # Gefilterte Liste der Bilder
        self.current_index = -1
        self.search_subfolders_var = tk.BooleanVar(value=False)
        self.preview_images = {}
        self.fullscreen_win = None
        self.debug_info = ""  # Speicher für Debug-Informationen

        self.delete_immediately_main_var = tk.BooleanVar(value=False)
        self.delete_immediately_fs_var = tk.BooleanVar(value=False)

        # Filter-Variablen
        self.filter_var = tk.StringVar()
        self.filter_filename_var = tk.BooleanVar(value=True)  # Standardmäßig aktiviert
        self.filter_prompt_var = tk.BooleanVar(value=False)
        self.filter_negativ_var = tk.BooleanVar(value=False)
        self.filter_settings_var = tk.BooleanVar(value=False)

        self.bind("<KeyPress-Right>", lambda e: self.show_next_image())
        self.bind("<KeyPress-Left>", lambda e: self.show_previous_image())
        self.bind("<F11>", lambda e: self.safe_close_fullscreen())
        self.bind("<Delete>", self.handle_delete_key)

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

        # Filter-Frame über dem Ordnerpfad
        filter_frame = tk.Frame(self, bg=BG_COLOR)
        filter_frame.pack(fill="x", padx=self.button_padding, pady=self.button_padding)
        tk.Label(filter_frame, text="Filter:", fg=TEXT_FG_COLOR, bg=BG_COLOR, font=("Arial", self.main_font_size)).pack(side="left", padx=self.button_padding)
        self.filter_entry = tk.Entry(filter_frame, textvariable=self.filter_var, fg=TEXT_FG_COLOR, bg=TEXT_BG_COLOR, font=("Arial", self.main_font_size), width=20)
        self.filter_entry.pack(side="left", padx=self.button_padding)
        self.filter_entry.bind("<KeyRelease>", lambda e: self.apply_filter())
        tk.Button(filter_frame, text="Clear", command=self.clear_filter,
                  bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size), width=5).pack(side="left", padx=self.button_padding)
        tk.Checkbutton(filter_frame, text="Dateiname", variable=self.filter_filename_var, command=self.apply_filter,
                       fg=TEXT_FG_COLOR, bg=BG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size)).pack(side="left", padx=self.button_padding)
        tk.Checkbutton(filter_frame, text="Prompt", variable=self.filter_prompt_var, command=self.apply_filter,
                       fg=TEXT_FG_COLOR, bg=BG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size)).pack(side="left", padx=self.button_padding)
        tk.Checkbutton(filter_frame, text="Negativ Prompt", variable=self.filter_negativ_var, command=self.apply_filter,
                       fg=TEXT_FG_COLOR, bg=BG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size)).pack(side="left", padx=self.button_padding)
        tk.Checkbutton(filter_frame, text="Settings", variable=self.filter_settings_var, command=self.apply_filter,
                       fg=TEXT_FG_COLOR, bg=BG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size)).pack(side="left", padx=self.button_padding)
        self.image_counter_label = tk.Label(filter_frame, text="0 Bilder", fg=TEXT_FG_COLOR, bg=BG_COLOR, font=("Arial", self.main_font_size))
        self.image_counter_label.pack(side="left", padx=self.button_padding)

        folder_frame = tk.Frame(self, bg=BG_COLOR)
        folder_frame.pack(fill="x", padx=self.button_padding, pady=self.button_padding)
        folder_label = tk.Label(folder_frame, text="Ordnerpfad:", fg=TEXT_FG_COLOR, bg=BG_COLOR, font=("Arial", self.main_font_size))
        folder_label.pack(side="left", padx=self.button_padding)
        self.folder_path_var = tk.StringVar()
        self.folder_entry = tk.Entry(folder_frame, textvariable=self.folder_path_var,
                                     fg=TEXT_FG_COLOR, bg=TEXT_BG_COLOR, font=("Arial", self.main_font_size), width=50)
        self.folder_entry.pack(side="left", padx=self.button_padding)
        tk.Button(folder_frame, text="Ordner auswählen", command=self.choose_folder,
                  bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size)).pack(side="left", padx=self.button_padding)
        tk.Button(folder_frame, text="Bild auswählen", command=self.select_image_from_folder,
                  bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size)).pack(side="left", padx=self.button_padding)
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
        tk.Checkbutton(subfolder_frame, text="Unterordner durchsuchen", variable=self.search_subfolders_var,
                       fg=TEXT_FG_COLOR, bg=BG_COLOR, selectcolor=BG_COLOR, font=("Arial", self.main_font_size)).pack(side="left", padx=self.button_padding)

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
        self.scale_dropdown = tk.OptionMenu(controls_frame, self.scale_var, *SCALE_OPTIONS, command=self.rescale_image)
        self.scale_dropdown.configure(bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size + 2))
        self.scale_dropdown.pack(side="left", padx=self.button_padding)
        tk.Button(controls_frame, text="Vollbild", command=self.show_fullscreen,
                  bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size)).pack(side="left", padx=self.button_padding)
        if len(self.monitor_list) > 1:
            self.monitor_choice = tk.StringVar()
            monitor_names = [f"Monitor {i}: {mon.width}x{mon.height}" for i, mon in enumerate(self.monitor_list)]
            self.monitor_choice.set(monitor_names[0])
            self.monitor_menu = tk.OptionMenu(controls_frame, self.monitor_choice, *monitor_names,
                                              command=self.update_selected_monitor)
            self.monitor_menu.configure(bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size + 2))
            self.monitor_menu.pack(side="left", padx=self.button_padding)

        textchunks_frame = tk.Frame(self, bg=BG_COLOR)
        textchunks_frame.pack(fill="x", padx=self.button_padding, pady=self.button_padding)
        self.prompt_text = ScrolledText(textchunks_frame, height=8, bg=TEXT_BG_COLOR,
                                        fg=TEXT_FG_COLOR, font=("Arial", self.main_font_size))
        self.prompt_text.grid(row=0, column=0, padx=self.button_padding, pady=self.button_padding, sticky="nsew")
        tk.Button(textchunks_frame, text="copy Prompt",
                  command=lambda: copy_to_clipboard(self, self.prompt_text.get("1.0", tk.END)),
                  bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size)).grid(row=1, column=0, padx=self.button_padding, pady=self.button_padding)
        self.negativ_text = ScrolledText(textchunks_frame, height=8, bg=TEXT_BG_COLOR,
                                         fg=TEXT_FG_COLOR, font=("Arial", self.main_font_size))
        self.negativ_text.grid(row=0, column=1, padx=self.button_padding, pady=self.button_padding, sticky="nsew")
        tk.Button(textchunks_frame, text="copy Negativ",
                  command=lambda: copy_to_clipboard(self, self.negativ_text.get("1.0", tk.END)),
                  bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size)).grid(row=1, column=1, padx=self.button_padding, pady=self.button_padding)
        self.settings_text = ScrolledText(textchunks_frame, height=8, bg=TEXT_BG_COLOR,
                                          fg=TEXT_FG_COLOR, font=("Arial", self.main_font_size))
        self.settings_text.grid(row=0, column=2, padx=self.button_padding, pady=self.button_padding, sticky="nsew")
        tk.Button(textchunks_frame, text="copy Settings",
                  command=lambda: copy_to_clipboard(self, self.settings_text.get("1.0", tk.END)),
                  bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size)).grid(row=1, column=2, padx=self.button_padding, pady=self.button_padding)
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

    def update_selected_monitor(self, choice):
        for i, mon in enumerate(self.monitor_list):
            if choice.startswith(f"Monitor {i}:"):
                self.selected_monitor = mon
                break
        self.scaling_factor = get_scaling_factor(self.selected_monitor)
        self.main_font_size = get_font_size(self.selected_monitor)
        self.button_padding = get_button_padding(self.selected_monitor)
        self.status(f"Monitor gewechselt auf: {choice}")

    def status(self, message):
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete("1.0", tk.END)
        self.status_text.insert(tk.END, f"{get_datetime_str()}: {message}")
        self.status_text.config(state=tk.DISABLED)

    def show_debug_info(self):
        debug_win = tk.Toplevel(self)
        debug_win.title("Debug Information")
        debug_win.configure(bg=BG_COLOR)
        debug_text = ScrolledText(debug_win, width=80, height=20, bg=BG_COLOR, fg=TEXT_FG_COLOR, font=("Arial", self.main_font_size))
        debug_text.insert(tk.END, self.debug_info if self.debug_info else "Keine Debug-Informationen verfügbar.")
        debug_text.config(state=tk.DISABLED)
        debug_text.pack(padx=self.button_padding, pady=self.button_padding)
        copy_btn = tk.Button(debug_win, text="Copy", command=lambda: copy_to_clipboard(self, self.debug_info),
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
        """Löscht das Filterfeld und wendet den Filter neu an."""
        self.filter_var.set("")
        self.apply_filter()

    def apply_filter(self):
        """Filtert die Bilder basierend auf dem Filter-Text und den ausgewählten Kontrollfeldern."""
        filter_text = self.filter_var.get().lower()
        self.filtered_images = []
        
        if not filter_text:
            self.filtered_images = self.folder_images.copy()
        else:
            for file_path in self.folder_images:
                include = False
                filename = os.path.basename(file_path).lower()
                prompt, negativ, settings = extract_png_text_chunks(file_path)
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

        self.current_index = -1 if not self.filtered_images else 0
        self.populate_preview_table_lazy()
        if self.filtered_images:
            self.display_image(self.filtered_images[self.current_index])
            self.extract_and_display_text_chunks(self.filtered_images[self.current_index])
        self.image_counter_label.config(text=f"{len(self.filtered_images)} Bilder")
        self.status(f"Filter angewendet: {len(self.filtered_images)} Bilder gefunden.")

    def load_folder_async(self, folder, file_path=None):
        self.status("Lade Ordner im Hintergrund...")
        self.folder_images = []
        if self.search_subfolders_var.get():
            self.folder_images = [str(p) for p in Path(folder).rglob("*.png")]
        else:
            self.folder_images = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(".png")]
        self.folder_images.sort()
        self.after(0, lambda: self.on_folder_loaded(folder, file_path))

    def on_folder_loaded(self, folder, file_path):
        if self.folder_images:
            self.apply_filter()  # Filter anwenden, nachdem der Ordner geladen wurde
            if file_path and file_path in self.filtered_images:
                self.current_index = self.filtered_images.index(file_path)
            else:
                self.current_index = 0 if self.filtered_images else -1
            if self.current_index != -1:
                self.display_image(self.filtered_images[self.current_index], default_scale=True)
                self.extract_and_display_text_chunks(self.filtered_images[self.current_index])
            self.status(f"Ordner geladen: {folder} ({len(self.folder_images)} Bilder, {len(self.filtered_images)} gefiltert)")
        else:
            self.status("Keine PNG-Bilder im ausgewählten Ordner gefunden.")

    def handle_drop(self, event):
        file_path = event.data.strip("{}")
        if os.path.isfile(file_path):
            folder = os.path.dirname(file_path)
            self.folder_path_var.set(folder)
            threading.Thread(target=self.load_folder_async, args=(folder, file_path), daemon=True).start()

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Ordner auswählen")
        if folder:
            self.folder_path_var.set(folder)
            threading.Thread(target=self.load_folder_async, args=(folder,), daemon=True).start()

    def select_image_from_folder(self):
        file_path = filedialog.askopenfilename(title="Bild auswählen", filetypes=[("PNG Images", "*.png")])
        if file_path:
            folder = os.path.dirname(file_path)
            self.folder_path_var.set(folder)
            threading.Thread(target=self.load_folder_async, args=(folder, file_path), daemon=True).start()

    def show_info(self):
        info_win = tk.Toplevel(self)
        info_win.title("Information")
        info_win.configure(bg=BG_COLOR)
        info_text = (
            "ImagePromptViewer - Übersicht:\n\n"
            "Liest PNG-Bilder (info['parameters']) und teilt den Text in Prompt, Negativ, Settings.\n"
            "Vollbildmodus zeigt alle drei Felder, Settings unten fest (4 Zeilen).\n"
            "Die Bildinfo in der Vollbildansicht passt sich dynamisch an.\n"
            "Schriftgrößen und Layout passen sich an die Monitorauflösung an.\n"
            "Mausrad über dem Bild im Hauptfenster navigiert vor/zurück.\n"
            "Drop eines Bildes lädt automatisch den gesamten Ordner.\n"
            "Optimierung: Asynchrones Laden und Lazy Loading der Vorschau.\n"
            "Filter: Filtert Bilder nach Dateiname, Prompt, Negativ Prompt und Settings.\n"
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
        if default_scale or (self.scale_var.get() == "Default"):
            w, h = self.current_image.size
            max_size = int(300 * self.scaling_factor)
            if w >= h:
                new_width = max_size
                new_height = int(h * max_size / w)
            else:
                new_height = max_size
                new_width = int(w * max_size / h)
        else:
            scale = int(self.scale_var.get().replace("%", ""))
            new_width = int(self.current_image.width * scale / 100)
            new_height = int(self.current_image.height * scale / 100)
        self.resized_image = self.current_image.resize((new_width, new_height))
        self.tk_image = ImageTk.PhotoImage(self.resized_image)
        self.image_label.config(image=self.tk_image)
        self.current_image_path = file_path
        self.status(f"Bild geladen: {os.path.basename(file_path)}")
        try:
            ctime = os.path.getctime(file_path)
            created_str = datetime.fromtimestamp(ctime).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            created_str = "Unbekannt"
        info_text = f"Dateiname: {os.path.basename(file_path)}\nPfad: {file_path}\nErstellt: {created_str}"
        self.image_info_label.config(text=info_text)

    def rescale_image(self, value):
        if self.current_image:
            self.display_image(self.current_image_path)

    def extract_and_display_text_chunks(self, file_path):
        prompt, negativ, settings = extract_png_text_chunks(file_path)
        self.prompt_text.delete("1.0", tk.END)
        self.prompt_text.insert("1.0", prompt)
        self.negativ_text.delete("1.0", tk.END)
        self.negativ_text.insert("1.0", negativ)
        self.settings_text.delete("1.0", tk.END)
        self.settings_text.insert("1.0", settings)

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
        mon = self.selected_monitor
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
        self.fs_image_label.bind("<MouseWheel>", self.fullscreen_mousewheel_image)  # Separates Binding für das Bild
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
            ctime = os.path.getctime(self.fs_image_path)
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
        prompt, negativ, settings = extract_png_text_chunks(self.fs_image_path)
        fs_prompt_text = ScrolledText(self.fs_text_frame, height=8, bg=TEXT_BG_COLOR,
                                      fg=TEXT_FG_COLOR, font=("Arial", self.main_font_size))
        fs_prompt_text.insert("1.0", prompt)
        fs_prompt_text.grid(row=0, column=0, padx=self.button_padding, pady=self.button_padding, sticky="nsew")
        fs_prompt_text.bind("<MouseWheel>", lambda e: self.fullscreen_mousewheel_text(e, fs_prompt_text))
        tk.Button(self.fs_text_frame, text="copy Prompt",
                  command=lambda: copy_to_clipboard(self, fs_prompt_text.get("1.0", tk.END)),
                  bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size)).grid(row=1, column=0, padx=self.button_padding)
        fs_negativ_text = ScrolledText(self.fs_text_frame, height=8, bg=TEXT_BG_COLOR,
                                       fg=TEXT_FG_COLOR, font=("Arial", self.main_font_size))
        fs_negativ_text.insert("1.0", negativ)
        fs_negativ_text.grid(row=0, column=1, padx=self.button_padding, pady=self.button_padding, sticky="nsew")
        fs_negativ_text.bind("<MouseWheel>", lambda e: self.fullscreen_mousewheel_text(e, fs_negativ_text))
        tk.Button(self.fs_text_frame, text="copy Negativ",
                  command=lambda: copy_to_clipboard(self, fs_negativ_text.get("1.0", tk.END)),
                  bg=BTN_BG_COLOR, fg=BTN_FG_COLOR, font=("Arial", self.main_font_size)).grid(row=1, column=1, padx=self.button_padding)
        fs_settings_text = ScrolledText(self.fs_text_frame, height=4, bg=TEXT_BG_COLOR,
                                        fg=TEXT_FG_COLOR, font=("Arial", self.main_font_size))
        fs_settings_text.insert("1.0", settings)
        fs_settings_text.grid(row=2, column=0, columnspan=2, padx=self.button_padding, pady=self.button_padding, sticky="nsew")
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