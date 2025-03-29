# ImagePromptViewer

**Version:** 1.0.36.3a  
**Interne Bezeichnung:** Master8 Alpha5  
**Stand:** 27. März 2025

## 🧩 Beschreibung

**ImagePromptViewer** ist ein leistungsfähiger Bildbetrachter für `.png`- und `.jpg`/`.jpeg`-Dateien, der eingebettete Prompt-Informationen ausliest. Die Software extrahiert automatisch Prompt, Negative Prompt und Settings aus:

- PNGs (`info['parameters']`, ggf. auch `prompt`, `metadata`, `description`)
- JPEGs (EXIF-Tag `UserComment` mit optionalem `UNICODE`-Präfix)

Diese Informationen werden übersichtlich dargestellt und können nach verschiedenen Kriterien gefiltert werden.

## ✨ Features

- Anzeige eingebetteter Prompt-Daten in übersichtlichen Textfeldern
- Filterfunktion (Prompt, Negativ Prompt, Settings, Dateiname)
- Unterstützt Drag & Drop für Einzelbilder (lädt ganzen Ordner)
- Vorschau der Bildliste und Navigation (Pfeiltasten, Mausrad)
- Vollbildmodus mit Textanzeige und -kopierfunktion
- Dynamisches UI-Scaling je nach Monitorauflösung
- Löschen von Bildern (mit oder ohne Bestätigung)
- Always-on-Top Funktion (umschaltbar)
- Debug-Fenster mit System- und Fehlerdiagnose
- Unterstützung von Unterordnern und Sortierung

## 📁 Voraussetzungen

- Python 3.8 oder höher
- Automatische Installation der folgenden Pakete:
  - `tkinterdnd2`
  - `Pillow`
  - `piexif`
  - `screeninfo`
  - `send2trash`

## ▶️ Starten

```bash
python ImagePromptViewer.py

💡 Bedienungshinweise
Mausrad oder Pfeiltasten: Vor-/Zurücknavigation

Drag & Drop: Ein Bild ziehen lädt automatisch den Ordner

F11 oder ESC im Vollbild: Schließen

Filter: Text eingeben und Suchfelder auswählen (z. B. Prompt)

Debug-Fenster: Zeigt OS, Python-Version, Auflösung, Fehler

Always on Top: Fenster bleibt im Vordergrund

Vollbildmodus: Mit Vollbild-Button starten – inkl. Copy-Funktion

🔐 Lizenz
Dieses Projekt ist lizenziert unter der
Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)
➡️ Mehr erfahre