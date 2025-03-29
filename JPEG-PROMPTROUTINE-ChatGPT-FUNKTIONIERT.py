import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import os
import re
from datetime import datetime
import piexif
from piexif import helper

# Globale Variablen
VERSION = "v1.0.0"
last_debug_info = ""    # Debug-Log (ohne Zeitstempel in den Zeilen)
last_full_block = ""    # Originaltext (alles nach "UNICODE")

def extract_prompt_data(file_path):
    global last_debug_info, last_full_block

    # Zuerst versuchen wir, EXIF-Daten (UserComment) auszulesen.
    try:
        exif_dict = piexif.load(file_path)
        user_comment_bytes = exif_dict.get("Exif", {}).get(piexif.ExifIFD.UserComment)
        if user_comment_bytes:
            full_text = helper.UserComment.load(user_comment_bytes)
        else:
            with open(file_path, "rb") as f:
                full_text = f.read().decode("utf-8", errors="ignore")
    except Exception as e:
        last_debug_info = f"❌ Fehler beim Auslesen der EXIF-Daten: {e}"
        last_full_block = ""
        return None, None, None

    debug_lines = []
    debug_lines.append(f"Version: {VERSION}")

    # Falls vorhanden, verwenden wir den Teil nach "UNICODE"
    idx_unicode = full_text.find("UNICODE")
    if idx_unicode != -1:
        text_block = full_text[idx_unicode + len("UNICODE"):]
        debug_lines.append(f"✅ 'UNICODE' gefunden an Index: {idx_unicode}")
    else:
        text_block = full_text
        debug_lines.append("ℹ️ 'UNICODE' nicht gefunden; verwende gesamten Text")

    last_full_block = text_block
    preview_length = 20000
    debug_lines.append("🔎 Original block (gekürzt, erste {} Zeichen):\n{}".format(preview_length, text_block[:preview_length]))

    # Normalisieren: Alle Leerzeichenfolgen werden zu einem einzelnen Space
    normalized = re.sub(r'\s+', ' ', text_block).strip()
    debug_lines.append("\n🔧 Normalized text (gekürzt, erste 2000 Zeichen):\n" + normalized[:2000] + "\n...")

    # Marker definieren – exakte Schreibweise
    marker_neg = "Negative prompt:"
    marker_steps = "Steps:"

    # Suche marker case-insensitiv im normalized Text:
    neg_match = re.search(r'Negative\s*prompt\s*:', normalized, flags=re.IGNORECASE)
    steps_match = re.search(r'Steps\s*:', normalized, flags=re.IGNORECASE)
    idx_neg = neg_match.start() if neg_match else -1
    idx_steps = steps_match.start() if steps_match else -1

    debug_lines.append(f"\n🔍 Marker '{marker_neg}' gefunden bei Index: {idx_neg}")
    debug_lines.append(f"🔍 Marker '{marker_steps}' gefunden bei Index: {idx_steps}")

    if idx_neg == -1 or idx_steps == -1:
        last_debug_info = "\n".join(debug_lines)
        return None, None, None

    # Aufteilen:
    # Prompt: Alles bis zum Marker "Negative prompt:" (Marker NICHT enthalten)
    prompt_section = normalized[:idx_neg].strip()
    # Negative Prompt: Ab dem Ende des Markers "Negative prompt:" bis vor "Steps:" (Marker NICHT enthalten)
    negative_section = normalized[idx_neg + len(marker_neg): idx_steps].strip()
    # Settings: Ab "Steps:" (Marker inklusive) bis zum Ende
    settings_section = normalized[idx_steps:].strip()

    debug_lines.append("\n✅ Extraktion erfolgreich!")
    debug_lines.append(f"📄 Prompt (kurz): {prompt_section[:100]}")
    debug_lines.append(f"📄 Negative Prompt (kurz): {negative_section[:100]}")
    debug_lines.append(f"📄 Settings (kurz): {settings_section[:100]}")

    last_debug_info = "\n".join(debug_lines)
    return prompt_section, negative_section, settings_section

def open_image():
    file_path = filedialog.askopenfilename(filetypes=[("JPEG Dateien", "*.jpg;*.jpeg")])
    if not file_path:
        return

    prompt, negative, settings = extract_prompt_data(file_path)
    if not prompt and not negative and not settings:
        messagebox.showwarning("Keine Daten gefunden", "Es konnten keine Prompt-Informationen extrahiert werden.")
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
        # Dateinamen mit Datum und Uhrzeit anhängen, sodass Logs nicht überschrieben werden
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_path_debug = os.path.join(os.path.dirname(__file__), f"debug_log_{timestamp}.txt")
        try:
            with open(file_path_debug, "w", encoding="utf-8") as f:
                f.write("===== Debug-Information =====\n")
                f.write(last_debug_info + "\n\n")
                f.write("===== Kompletter 'block' nach UNICODE =====\n")
                f.write(last_full_block + "\n")
            messagebox.showinfo("Erfolg", f"Debug-Information wurde gespeichert in:\n{file_path_debug}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern: {e}")

    save_button = tk.Button(debug_window, text="Save Debug to File", command=save_debug_to_file,
                            bg="#FFA500", fg="black", font=("Arial", 10, "bold"))
    save_button.pack(pady=5)

    full_block_label = tk.Label(debug_window, text="Kompletter Text nach UNICODE:", bg="#1F1F1F", fg="#FFA500")
    full_block_label.pack()

    full_block_text = scrolledtext.ScrolledText(debug_window, wrap="word", bg="black", fg="#FFA500")
    full_block_text.insert(tk.END, last_full_block)
    full_block_text.pack(fill="both", expand=True, padx=10, pady=5)

# Haupt-GUI erstellen
root = tk.Tk()
root.title(f"🧠 Stable Diffusion Prompt Extractor (JPEG) - {VERSION}")
root.geometry("900x700")
root.configure(bg="#1F1F1F")

# Versionsanzeige
version_label = tk.Label(root, text=f"Version: {VERSION}", bg="#1F1F1F", fg="#FFA500", font=("Arial", 10))
version_label.pack(anchor="ne", padx=10, pady=5)

tk.Button(root, text="📂 JPEG auswählen", command=open_image,
          bg="#FFA500", fg="black", font=("Arial", 12, "bold")).pack(pady=10)

tk.Button(root, text="🛠️ Debug anzeigen", command=show_debug_info,
          bg="#444444", fg="#FFA500", font=("Arial", 10)).pack(pady=5)

tk.Label(root, text="Prompt:", bg="#1F1F1F", fg="#FFA500", anchor="w").pack(fill="x", padx=10)
prompt_field = scrolledtext.ScrolledText(root, height=6, bg="black", fg="#FFA500", wrap="word")
prompt_field.pack(fill="both", padx=10, pady=5)

tk.Label(root, text="Negative Prompt:", bg="#1F1F1F", fg="#FFA500", anchor="w").pack(fill="x", padx=10)
negative_field = scrolledtext.ScrolledText(root, height=6, bg="black", fg="#FFA500", wrap="word")
negative_field.pack(fill="both", padx=10, pady=5)

tk.Label(root, text="Settings:", bg="#1F1F1F", fg="#FFA500", anchor="w").pack(fill="x", padx=10)
settings_field = scrolledtext.ScrolledText(root, height=6, bg="black", fg="#FFA500", wrap="word")
settings_field.pack(fill="both", padx=10, pady=5)

root.mainloop()
