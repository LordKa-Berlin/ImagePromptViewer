- TAG 20250327
Datum: 2025-03-27
Versionsnummer: 1.0.35.7
Interne Bezeichnung: Master8 Alpha3

Führe bitte folgende Korrektur durch: 1. beim Filtern des Textfeldes Settings war der marker "Steps:"
 bisher susgeschlossen beim übergeben an das Textfeld, ändere das Script so, das die Zeichenkette "Steps:" aus dem Text Chunk auch mit in das feld Settings übernommen wird. 2. Frage? ist es möglich das du in dem Debug fenster mehr informationen anzeigen lässt, betriebssystem, Version, aktuelle Monitorauflösung, und die fehlermeldungen Meldungen die normmaler weise in dem terminal von Visual Code angezeigt werden? Hier ist der aktuelle Code auf den du aufbauen sollst. Es ist sehr wichtig, das du nur die Notwendigen Funktionen bearbeitest. Alle anderen Funktionen MÜSSEN erhalten bleiben, damit sie auch weiterhin genau so funktionieren wie sie es in der version tuen!

 Ich möchte dich auf folgendes hinweisen:
 in jpeg dateien sind die marker nach denen du suchen musst zum separieren des Prompt-Textes folgende: "UNICODE" alles was danach kommt ist Prompt bis Negativ prompt: ( N e g a t i v e   p r o m p t :)  bis zu dem marker "Steps:" (S t e p s : ) wichtig zu wissen, dieses mal gehört der marker S t e p s :  mit zum extrahierenden Text, da er ein Teil der Generator Settings ist die in dem Chunk abgelegt sind.


 ####################################
 Chat GPT deep Research zu dem Thema:

 Extraktion eingebetteter Stable-Diffusion-Prompt-Daten aus JPEG
Problem: Stable-Diffusion-WebUIs (z.B. AUTOMATIC1111) betten bei JPEG-Ausgaben die Prompt-Daten oft in die Bilddatei ein – typischerweise im EXIF-Abschnitt UserComment als Unicode-Text​
GITHUB.COM
. In einem Hex- oder Textdump der JPEG-Datei wirkt dieser Text zerstückelt (jedes Zeichen getrennt durch Leerzeichen oder Nullbytes, erkennbar am Prefix "UNICODE"). Der Inhalt umfasst den eigentlichen Prompt, gefolgt vom Marker "Negative prompt:" und anschließend dem negativen Prompt, der wiederum vor dem nächsten Marker "Steps:" endet​
GITHUB.COM
. Ziel ist es, diesen eingebetteten Text zuverlässig auszulesen, die drei Abschnitte (Prompt, negativer Prompt, Einstellungen) zu trennen und in einem Tkinter-Formular anzuzeigen – und zwar mit korrekter Dekodierung (Zusammenfügen der getrennten Zeichen) und Beibehaltung der Original-Groß/Kleinschreibung sowie Leerzeichen.
Auslesen der eingebetteten Prompt-Daten (EXIF-Metadaten)
Der sicherste Weg ist, die EXIF-Metadaten der JPEG-Datei per Python auszulesen, anstatt im Binärstrom manuell nach Byte-Offsets zu suchen. Das Stable-Diffusion-WebUI speichert den Prompt-Text im EXIF-Tag UserComment (0x9286) mit Unicode-Kodierung​
GITHUB.COM
. Wir können dieses Tag mit einer EXIF-Bibliothek auslesen und dekodieren. Ein bewährtes Modul dafür ist piexif, das sowohl das Lesen als auch das Dekodieren von UserComment unterstützt. Beispielschritte in Python:
EXIF laden: Mit piexif.load("bild.jpg") laden wir alle EXIF-Tags in ein Dictionary.
UserComment auslesen: Im geladenen Dict findet sich der Eintrag exif_dict["Exif"][piexif.ExifIFD.UserComment], welcher die rohen Bytes des UserComment-Tags enthält​
GITHUB.COM
.
Dekodieren: Diese Bytes können wir mit piexif.helper.UserComment.load(...) in einen lesbaren Unicode-String umwandeln​
GITHUB.COM
. piexif.helper.UserComment.load erkennt den "UNICODE\0"-Prefix und wandelt die Folgebytes korrekt von UTF-16 (oder UCS-2) in normalen Text um. Dadurch werden die „entstückelten“ Zeichen automatisch richtig zusammengesetzt (z.B. aus "m a s t e r p i e c e" wird "masterpiece").
Ein Beispielcode könnte so aussehen:
python
Kopieren
import piexif
from piexif import helper

# JPEG-Bild laden und EXIF-Daten extrahieren
exif_dict = piexif.load("pfad/zum/bild.jpg")
user_comment_bytes = exif_dict.get("Exif", {}).get(piexif.ExifIFD.UserComment)

prompt_text = ""
if user_comment_bytes:
    try:
        prompt_text = helper.UserComment.load(user_comment_bytes)
    except Exception as e:
        prompt_text = user_comment_bytes.decode('utf-16', errors='ignore')
        # Fallback: Direktdekodierung als UTF-16, falls piexif nicht verfügbar
Dieser Code lädt den EXIF-Block und dekodiert das UserComment. Nach dem Aufruf enthält prompt_text den gesamten eingebetteten Prompt-String in normal lesbarer Form. Zum Beispiel könnte prompt_text so aussehen (in einer Zeile oder mehreren Zeilen):
yaml
Kopieren
masterpiece, best quality, a tree with a bird  
Negative prompt: low quality, blurry  
Steps: 40, Sampler: Euler a, CFG scale: 7, Seed: 123456789, Size: 512x512
(Je nach Stable-Diffusion-Version kann der Format leicht variieren, aber die Marker "Negative prompt:" und "Steps:" sind enthalten​
GITHUB.COM
.) Warum piexif? Dieses Modul berücksichtigt die EXIF-Kodierung automatisch. Das WebUI verwendet intern ebenfalls piexif zum Schreiben und Lesen der Prompt-Parameter​
GITHUB.COM
, was zuverlässig die Zerlegung in Einzelzeichen vermeidet. Alternativ kann man Pillow (PIL.Image) mit _getexif() nutzen, erhält aber das UserComment oft als Byte-Array und müsste selbst dekodieren. piexif.helper.UserComment.load erspart dieses manuelle Zusammenführen.
Aufteilen in Prompt, negativen Prompt und Einstellungen
Sobald der volle Prompt-Text vorliegt, können wir ihn anhand der bekannten Marker in die drei benötigten Teile trennen:
Prompt: Alles ab Start (nach "UNICODE") bis vor dem Marker "Negative prompt:".
Negativer Prompt: Von inklusive "Negative prompt:" bis vor dem Marker "Steps:".
Generator-Einstellungen: Von inklusive "Steps:" bis zum Ende des Textblocks.
In Python lässt sich das z.B. so umsetzen:
python
Kopieren
text = prompt_text  # der aus EXIF geladene vollständige Prompt-String

marker_neg = "Negative prompt:"
marker_steps = "Steps:"

idx_neg = text.find(marker_neg)
idx_steps = text.find(marker_steps)

if idx_neg != -1 and idx_steps != -1:
    prompt_section   = text[:idx_neg].rstrip()
    negative_section = text[idx_neg:idx_steps].strip()
    settings_section = text[idx_steps:].strip()
else:
    # Falls Marker nicht gefunden wurden, entsprechendes Handling (z.B. alles als Prompt behandeln)
    prompt_section   = text
    negative_section = ""
    settings_section = ""
Hier suchen wir nach den Indexstellen der Teilstrings. idx_neg markiert den Beginn von "Negative prompt:", idx_steps den von "Steps:". Dann wird per Slicing jeder Abschnitt extrahiert.
prompt_section enthält den reinen Prompt (ohne den Negativ-Prompt-Teil).
negative_section beginnt mit "Negative prompt:" und enthält den negativen Prompt-Text.
settings_section beginnt mit "Steps:" und enthält alle folgenden Einstellungen (Schritte, Sampler, Seed etc.). Wir behalten den "Steps:"‐Marker im Text, da er Teil der Parameterangaben ist.
Hinweis: Wir verwenden str.find() und Slicing, was die Groß-/Kleinschreibung und Abstände 1:1 berücksichtigt. Achten Sie darauf, nichts am Text zu verändern, was die Leerzeichen beeinflusst. Im obigen Beispiel wird nur strip()/rstrip() verwendet, um eventuell führende oder abschließende Zeilenumbrüche zu entfernen – die inhaltlichen Leerzeichen innerhalb des Textes bleiben unverändert. Falls Ihr Prompt-Text z.B. Zeilenumbrüche enthält, können Sie diese bei Bedarf erhalten oder entfernen je nach Anzeigeanforderung.
Anzeige im Tkinter-Formular
Nachdem die drei Teilstrings gewonnen sind, können Sie sie in ein Tkinter-Formular einfügen. Je nach Länge ist ein mehrzeiliges Textfeld (tk.Text) geeignet, vor allem für Prompt und negativen Prompt, während die Einstellungen evtl. in ein einzelnes Feld passen. Ein mögliches Vorgehen:
python
Kopieren
import tkinter as tk

root = tk.Tk()
root.title("Stable Diffusion Prompt Viewer")

# Textfelder für Prompt, Negativ-Prompt, Einstellungen
txt_prompt = tk.Text(root, height=5, width=60)
txt_neg    = tk.Text(root, height=5, width=60)
txt_set    = tk.Text(root, height=4, width=60)

txt_prompt.insert("1.0", prompt_section)
txt_neg.insert("1.0", negative_section)
txt_set.insert("1.0", settings_section)

# Optional: Labels zur Kennzeichnung
tk.Label(root, text="Prompt:").pack()
txt_prompt.pack()
tk.Label(root, text="Negativer Prompt:").pack()
txt_neg.pack()
tk.Label(root, text="Generierungs-Einstellungen:").pack()
txt_set.pack()

root.mainloop()
In diesem Formular werden die ausgelesenen Strings direkt eingefügt. Durch die vorherige korrekte Dekodierung erscheinen Umlaute, Leerzeichen und Groß-/Kleinschreibung genau wie ursprünglich eingegeben. Die Marker "Negative prompt:" und "Steps:" bleiben im Text des jeweiligen Feldes sichtbar, was kontextuelle Klarheit schafft. (Alternativ könnten Sie die Labels im GUI verwenden und nur den reinen negativen Prompt ohne den Wörter "Negative prompt:" einfügen, je nach gewünschter Darstellung.) Zusammenfassung: Mit einer EXIF-Bibliothek wie piexif lassen sich die in JPEG eingebetteten Stable-Diffusion-Prompts sicher und verlustfrei extrahieren. Die Funktion piexif.helper.UserComment.load wandelt den durch "UNICODE" gekennzeichneten Byte-Block direkt in einen lesbaren String um​
GITHUB.COM
. Anschließend ermöglichen Python-Stringmethoden das Aufteilen anhand der eindeutigen Marker (Negative prompt: und Steps:)​
GITHUB.COM
. Schließlich können die drei Segmente (Prompt, negativer Prompt, Einstellungen) unverändert in Tkinter-Widgets angezeigt werden. Diese Vorgehensweise stellt sicher, dass alle Zeichen korrekt decodiert sind und keine manuelle “Entschlüsselung” der Leerzeichen-Sequenzen nötig ist. Quellen: Die empfohlene Methode orientiert sich an der Implementierung des AUTOMATIC1111-WebUI, das Prompt-Parameter als Unicode-UserComment in JPEG speichert​
GITHUB.COM
 und beim Auslesen entsprechend dekodiert​
GITHUB.COM
. Die Aufteilung in Prompt/Negative/Settings entspricht dem üblichen Format der Stable-Diffusion-Metadaten​
GITHUB.COM
.
##################################################### Zusammenfassung von Chatgpt
EXIF-UserComment auslesen – mithilfe von piexif (und piexif.helper), um den eingebetteten Prompt-Text korrekt zu dekodieren

Falls der Text den Marker "UNICODE" enthält, wird alles ab diesem Marker als Ausgangstext verwendet

Der Text wird mit der Funktion unspace_letters (und anschließend mit einer Normalisierung mittels Regex) verarbeitet, sodass Einzel-Leerzeichen zwischen Buchstaben entfernt werden – so erscheinen beispielsweise aus

css
Kopieren
N e g a t i v e   p r o m p t :
nun "Negative prompt:"

Anschließend werden anhand der Marker

"Negative prompt:"

"Steps:"
der Text in drei Abschnitte geteilt:

Prompt: vom Anfang bis vor "Negative prompt:"

Negativer Prompt: von "Negative prompt:" bis vor "Steps:"

Einstellungen: ab "Steps:" (inklusive, da dieser Marker Teil der Einstellungen ist)

Die drei Textsegmente werden in jeweils eigenen Textfeldern in einem Tkinter-Formular angezeigt

###############################################################