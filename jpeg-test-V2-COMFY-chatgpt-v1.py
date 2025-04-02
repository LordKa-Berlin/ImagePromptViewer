import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import os
import re
from datetime import datetime
import piexif
from piexif import helper
import json  # falls du später den JSON-String parsen möchtest

# Globale Variablen
VERSION = "v1.0.0"
last_debug_info = ""    # Debug-Log
last_full_block = ""    # Vollständiger Text (EXIF oder Datei)

# Angepasste Marker (entsprechen dem tatsächlichen JSON-Aufbau)
MARKER_START = '"inputs":{"text":"'
MARKER_END = '"parser":'

def extract_prompt_data(file_path):
    """
    Liest aus den EXIF-Daten (UserComment) oder – falls nicht vorhanden –
    aus dem kompletten Dateiinhalt. Sucht mittels Regex nach allen Vorkommen
    von MARKER_START bis MARKER_END. Das erste gefundene Segment wird in das
    Prompt-Feld eingefügt, das zweite in das Negative Prompt-Feld.
    """
    global last_debug_info, last_full_block

    debug_lines = []
    debug_lines.append(f"Version: {VERSION}")
    debug_lines.append(f"Dateipfad: {file_path}")

    # Versuche EXIF-Daten auszulesen
    try:
        exif_dict = piexif.load(file_path)
        user_comment_bytes = exif_dict.get("Exif", {}).get(piexif.ExifIFD.UserComment)
        if user_comment_bytes:
            full_text = helper.UserComment.load(user_comment_bytes)
            debug_lines.append("✅ EXIF-UserComment erfolgreich ausgelesen.")
        else:
            # Fallback: ganze Datei einlesen
            with open(file_path, "rb") as f:
                full_text = f.read().decode("utf-8", errors="ignore")
            debug_lines.append("ℹ️ Kein EXIF-UserComment gefunden. Lese gesamten Dateiinhalt.")
    except Exception as e:
        last_debug_info = f"❌ Fehler beim Auslesen der EXIF-Daten: {e}"
        last_full_block = ""
        return None, None, None

    last_full_block = full_text

    # Debug: Auszug aus dem gelesenen Text (ersten 2000 Zeichen)
    preview_length = 2000
    debug_lines.append(f"🔎 Auszug aus dem gelesenen Text (ersten {preview_length} Zeichen):\n"
                       + full_text[:preview_length] + "\n...")

    # Verwende Regex, um alle Vorkommen zwischen MARKER_START und MARKER_END zu finden
    pattern = re.escape(MARKER_START) + r'(.*?)' + re.escape(MARKER_END)
    matches = re.findall(pattern, full_text, flags=re.DOTALL)
    debug_lines.append(f"🔍 Anzahl gefundener Textsegmente: {len(matches)}")

    prompt_text = ""
    negative_text = ""
    settings_text = ""  # bleibt leer

    if len(matches) >= 1:
        prompt_text = matches[0]
        debug_lines.append("✅ Erster Textabschnitt (Prompt) extrahiert.")
    else:
        debug_lines.append("⚠️ Erster Marker nicht gefunden.")

    if len(matches) >= 2:
        negative_text = matches[1]
        debug_lines.append("✅ Zweiter Textabschnitt (Negative Prompt) extrahiert.")
    else:
        debug_lines.append("⚠️ Zweiter Marker nicht gefunden.")

    debug_lines.append("\n===== Ergebnis der Extraktion =====")
    debug_lines.append(f"Prompt: (ersten 100 Zeichen) {prompt_text[:100]}")
    debug_lines.append(f"Negativ: (ersten 100 Zeichen) {negative_text[:100]}")
    debug_lines.append("Settings: (leer)")

    last_debug_info = "\n".join(debug_lines)

    # Falls beide Segmente nicht gefunden wurden, gebe None zurück
    if not prompt_text and not negative_text:
        return None, None, None

    return prompt_text, negative_text, settings_text


def open_image():
    file_path = filedialog.askopenfilename(filetypes=[("JPEG Dateien", "*.jpg;*.jpeg")])
    if not file_path:
        return

    prompt, negative, settings = extract_prompt_data(file_path)
    if not prompt and not negative and not settings:
        messagebox.showwarning("Keine Daten gefunden", "Es konnten keine passenden Textsegmente extrahiert werden.")
        return

    prompt_field.delete("1.0", tk.END)
    prompt_field.insert(tk.END, prompt)

    negative_field.delete("1.0", tk.END)
    negative_field.insert(tk.END, negative)

    settings_field.delete("1.0", tk.END)
    settings_field.insert(tk.END, settings)


def show_debug_info():
    if not last_debug_info:
        messagebox.showinfo("Debug Info", "Noch keine Datei analysiert.")
        return

    debug_window = tk.Toplevel(root)
    debug_window.title("🛠️ Debug-Information")
    debug_window.geometry("900x700")
    debug_window.configure(bg="#1F1F1F")

    debug_text = scrolledtext.ScrolledText(debug_window, wrap="word", bg="black", fg="#FFA500")
    debug_text.insert(tk.END, last_debug_info)
    debug_text.pack(fill="both", expand=True)

    def copy_to_clipboard():
        debug_window.clipboard_clear()
        debug_window.clipboard_append(last_debug_info)
        messagebox.showinfo("Kopiert", "Debug-Information wurde in die Zwischenablage kopiert.")

    copy_button = tk.Button(debug_window, text="Copy Debug", command=copy_to_clipboard,
                            bg="#FFA500", fg="black", font=("Arial", 10, "bold"))
    copy_button.pack(pady=5)

    def save_debug_to_file():
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_path_debug = os.path.join(os.path.dirname(__file__), f"debug_log_{timestamp}.txt")
        try:
            with open(file_path_debug, "w", encoding="utf-8") as f:
                f.write("===== Debug-Information =====\n")
                f.write(last_debug_info + "\n\n")
                f.write("===== Vollständiger Text aus EXIF/File =====\n")
                f.write(last_full_block + "\n")
            messagebox.showinfo("Erfolg", f"Debug-Information wurde gespeichert in:\n{file_path_debug}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern: {e}")

    save_button = tk.Button(debug_window, text="Save Debug to File", command=save_debug_to_file,
                            bg="#FFA500", fg="black", font=("Arial", 10, "bold"))
    save_button.pack(pady=5)

    full_block_label = tk.Label(debug_window, text="Vollständiger Text (EXIF oder Datei):", bg="#1F1F1F", fg="#FFA500")
    full_block_label.pack()

    full_block_text = scrolledtext.ScrolledText(debug_window, wrap="word", bg="black", fg="#FFA500")
    full_block_text.insert(tk.END, last_full_block)
    full_block_text.pack(fill="both", expand=True, padx=10, pady=5)


# Haupt-GUI erstellen
root = tk.Tk()
root.title(f"🧠 Metadaten-Extractor (JPEG) - {VERSION}")
root.geometry("900x700")
root.configure(bg="#1F1F1F")

# Versionsanzeige
version_label = tk.Label(root, text=f"Version: {VERSION}", bg="#1F1F1F", fg="#FFA500", font=("Arial", 10))
version_label.pack(anchor="ne", padx=10, pady=5)

tk.Button(root, text="📂 JPEG auswählen", command=open_image,
          bg="#FFA500", fg="black", font=("Arial", 12, "bold")).pack(pady=10)

tk.Button(root, text="🛠️ Debug anzeigen", command=show_debug_info,
          bg="#444444", fg="#FFA500", font=("Arial", 10)).pack(pady=5)

# Prompt-Feld
tk.Label(root, text="Prompt:", bg="#1F1F1F", fg="#FFA500", anchor="w").pack(fill="x", padx=10)
prompt_field = scrolledtext.ScrolledText(root, height=6, bg="black", fg="#FFA500", wrap="word")
prompt_field.pack(fill="both", padx=10, pady=5)

# Negative Prompt-Feld
tk.Label(root, text="Negative Prompt:", bg="#1F1F1F", fg="#FFA500", anchor="w").pack(fill="x", padx=10)
negative_field = scrolledtext.ScrolledText(root, height=6, bg="black", fg="#FFA500", wrap="word")
negative_field.pack(fill="both", padx=10, pady=5)

# Settings-Feld (bleibt leer)
tk.Label(root, text="Settings:", bg="#1F1F1F", fg="#FFA500", anchor="w").pack(fill="x", padx=10)
settings_field = scrolledtext.ScrolledText(root, height=6, bg="black", fg="#FFA500", wrap="word")
settings_field.pack(fill="both", padx=10, pady=5)

root.mainloop()
