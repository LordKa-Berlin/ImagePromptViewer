import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import os
import re
from datetime import datetime
import piexif
from piexif import helper

# Globale Variablen
VERSION = "v1.0.0"
last_debug_info = ""    # Debug-Log
last_full_block = ""    # Vollständiger Text (aus EXIF oder Datei)

# Marker-Definitionen (mit Leerzeichen zwischen jedem Zeichen, wie gewünscht)
MARKER_START = '" i n p u t s " : { " t e x t " : "'
MARKER_END = '" p a r s e r " :'

def extract_prompt_data(file_path):
    """
    Liest aus den EXIF-Daten (UserComment) oder – falls nicht vorhanden –
    aus dem kompletten Dateiinhalt. Sucht nach zwei Vorkommen von MARKER_START
    und jeweils dem darauffolgenden MARKER_END.
    
    Gibt ein Tupel (prompt_text, negative_text, settings_text) zurück.
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

    # Debug: Ausschnitt des Textes (ersten 2000 Zeichen)
    preview_length = 2000
    debug_lines.append(f"🔎 Auszug aus dem gelesenen Text (ersten {preview_length} Zeichen):\n"
                       + full_text[:preview_length] + "\n...")

    # ========== EXTRAKTION ==========
    prompt_text = ""
    negative_text = ""
    settings_text = ""  # bleibt leer

    # 1. Vorkommen von MARKER_START
    first_start_idx = full_text.find(MARKER_START)
    if first_start_idx != -1:
        debug_lines.append(f"✅ Erstes Vorkommen von MARKER_START gefunden bei Index {first_start_idx}.")
        first_end_idx = full_text.find(MARKER_END, first_start_idx + len(MARKER_START))
        if first_end_idx != -1:
            prompt_text = full_text[first_start_idx + len(MARKER_START):first_end_idx]
            debug_lines.append("✅ Text für das Prompt-Feld extrahiert.")
        else:
            debug_lines.append("⚠️ MARKER_END wurde nach dem ersten MARKER_START nicht gefunden.")
    else:
        debug_lines.append("⚠️ Kein erstes Vorkommen von MARKER_START gefunden.")

    # 2. Vorkommen von MARKER_START (Suche ab dem Ende des ersten Fundes)
    if first_start_idx != -1:
        second_start_idx = full_text.find(MARKER_START, first_start_idx + len(MARKER_START))
    else:
        second_start_idx = -1

    if second_start_idx != -1:
        debug_lines.append(f"✅ Zweites Vorkommen von MARKER_START gefunden bei Index {second_start_idx}.")
        second_end_idx = full_text.find(MARKER_END, second_start_idx + len(MARKER_START))
        if second_end_idx != -1:
            negative_text = full_text[second_start_idx + len(MARKER_START):second_end_idx]
            debug_lines.append("✅ Text für das Negative Prompt-Feld extrahiert.")
        else:
            debug_lines.append("⚠️ MARKER_END wurde nach dem zweiten MARKER_START nicht gefunden.")
    else:
        debug_lines.append("⚠️ Kein zweites Vorkommen von MARKER_START gefunden.")

    # Debug-Info final
    debug_lines.append("\n===== Ergebnis der Extraktion =====")
    debug_lines.append(f"Prompt: (ersten 100 Zeichen) {prompt_text[:100]}")
    debug_lines.append(f"Negativ: (ersten 100 Zeichen) {negative_text[:100]}")
    debug_lines.append(f"Settings: (leer)")

    last_debug_info = "\n".join(debug_lines)

    # Wenn beide Strings leer sind, geben wir None zurück, damit im GUI eine Warnung erscheint
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
