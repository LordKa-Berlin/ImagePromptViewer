import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox

# Extraktion aus JPEG-Inhalt mit deinen benannten Markern
def extract_prompt_data(file_path):
    with open(file_path, "rb") as f:
        data = f.read()

    try:
        full_text = data.decode("utf-8", errors="ignore")
    except:
        return None, None, None

    start_index = full_text.find("UNICODE")
    if start_index == -1:
        return None, None, None

    block = full_text[start_index + len("UNICODE"):]
    neg_index = block.find("N e g a t i v e   p r o m p t :")
    steps_index = block.find("S t e p s :")

    if neg_index == -1 or steps_index == -1:
        return None, None, None

    prompt_raw = block[:neg_index]
    negative_raw = block[neg_index:steps_index]
    settings_raw = block[steps_index:]

    # Entferne Leerzeichen zwischen Buchstaben
    def clean(text):
        return ''.join(
            [c for i, c in enumerate(text) if i == 0 or text[i - 1] != ' ' or not c.isalpha()]
        ).strip()

    return clean(prompt_raw), clean(negative_raw), clean(settings_raw)

# Bildauswahl und Datenanzeige
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

# GUI
root = tk.Tk()
root.title("🧠 Stable Diffusion Prompt Extractor (JPEG)")
root.geometry("900x650")
root.configure(bg="#1F1F1F")

tk.Button(root, text="📂 JPEG auswählen", command=open_image,
          bg="#FFA500", fg="black", font=("Arial", 12, "bold")).pack(pady=10)

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
