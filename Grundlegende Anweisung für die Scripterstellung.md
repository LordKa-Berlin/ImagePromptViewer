Grundlegende Anweisung für die Scripterstellung an dich die du dir merken sollst für die Zusammenarbeit mit mir
Schreibe immer einen Header in dem Script mit Datum,und einer Versionsnummer
Erhöhe die Versionsnummer bei jeder Änderung die du im Script machst
verwende für die Versionsnummer immer eine variable
Wenn wir eine grundlegende Änderung machen berücksichtige das bei der vergabe der Versionsnummer
zeige die Versionsnummer im Formular an, wenn ein Formular angezeigt wird
schreibe eine Zusammenfassung im Header, was das Script macht, passe diese Beschreibung, wenn notwendig, bei jeder Änderung an.
Füge beschreibungen in den Code ein, damit ich nachvollziehen kann was das Script macht.
Füge in dem Formular die Funktion (Kontrollkästchen) Allways on Top ein, setze den Wert so, dass die Standardeinstelllung auf false steht
Zeige in dem Formular dezent die Versionsnummer an.

Farbdesign Beschreibung
Hintergrundfarbe des Formulars: #1F1F1F (Dunkles Grau)
Button-Hintergrundfarbe: #FFA500 (Orange)
Button-Schriftfarbe: #000000 (Schwarz)
Label- und Textfeld-Schriftfarbe: #FFA500 (Orange)
Textfeld-Hintergrundfarbe: #000000 (Schwarz)

füge bei  jedem vollständigen Script das du erstellst im Nachgang die Anweisung für git (alles was notwendig ist dammit die version nach git aktualisiert wird mi ein) inklusive einer Commitanweisung (änderungen kurz zusammengeasst) mit ein


Merke dir folgende Angaben!
# GIT-UMGEBUNGSKONFIGURATION

## GitHub Benutzername:
LordKa-Berlin

## Repository 1:
- Name: ImagePromptViewer
- Remote URL: https://github.com/LordKa-Berlin/ImagePromptViewer.git
- Lokaler Pfad: C:\Users\lordk\OneDrive\#Lordka\#SCRIPTE\PYTHON\ImagePromptViewer
- Aktueller Haupt-Branch: main (zuvor: master)
- Zusätzlicher Branch: entwicklung

## Repository 2:
- Name: Python-Tools
- Remote URL: https://github.com/LordKa-Berlin/Python-Tools.git
- Lokaler Pfad: C:\Users\lordk\OneDrive\#Lordka\#SCRIPTE\PYTHON\Python-Tools
- Aktueller Haupt-Branch: main

## Visual Studio Code:
- GitLens Erweiterung: installiert
- Git-Integration: aktiv
- Editor: Visual Studio Code

## Sonstige Informationen:
- Git-Remote-Name: origin (Standard)
- Branch `main` wurde erfolgreich als Standard gesetzt

Die Git-Anweisungen bitte als ausführbaren Code in einem separaten Codeblock



 Hier ist der aktuelle Code, analysiere ihn und verwende ihn als Grundlage für alle weiteren Aktionen! Achte darauf, dass du keine bestehenden Funktionen, Buttons oder Ähnliches aus dem Projekt entfernst, integriere die zusätzlichen Anforderungen, sodass alle anderen Funktionalitäten erhalten bleiben!!!:




### Zusammenfassung des Skripts: ImagePromptCleaner

#### Allgemeine Beschreibung
Das Skript `ImagePromptCleaner` ist ein Python-Programm, das als Bildbetrachter und Metadaten-Viewer für PNG- und JPEG-Dateien dient. Es liest eingebettete Textinformationen aus Bilddateien (Prompt, Negative Prompt, Settings) und bietet eine grafische Benutzeroberfläche (GUI) zur Anzeige, Navigation, Filterung und Verwaltung von Bildern in einem Ordner. Das Programm ist dynamisch an verschiedene Bildschirmgrößen anpassbar, unterstützt Drag-and-Drop und speichert Verlaufsdaten in einer JSON-Datei.

#### Hauptfunktionen des Skripts
Das Skript bietet folgende Kernfunktionalitäten:

1. **Bildanzeige und Navigation**
   - Lädt und zeigt PNG- und JPEG-Bilder aus einem ausgewählten Ordner an.
   - Ermöglicht Navigation zwischen Bildern mit "Next" und "Back" Buttons sowie Pfeiltasten (`<Left>`, `<Right>`).
   - Unterstützt Vollbildmodus (`F11`) mit zusätzlichen Steuerungen wie Zoom (Ctrl+Mausrad) und Textanzeige ein-/ausblenden.
   - Skaliert Bilder dynamisch basierend auf Bildschirmgröße oder Benutzerwahl ("Default", "25%", "50%", "75%").

2. **Metadatenextraktion**
   - Extrahiert Textinformationen aus Bild-Metadaten mit mehreren Logiken (`extract_text_chunks`):
     - **Logik 1 (JSON)**: Parst JSON-Daten für "prompt", "negativePrompt", "steps" oder "CLIPTextEncode"/"KSampler" Strukturen.
     - **Logik 2 (Marker)**: Teilt Text bei `"prompt":`, `"negativePrompt":`, `"steps":`.
     - **Logik 3 (ComfyUI-Workflow)**: Regex-Suche nach `"inputs":{"text":"` bis `"parser":`.
     - **Logik 4 (Civitai/ComfyUI)**: Spezielle Marker mit Unicode-Escapes (`"p r o m p t \u0022 : \u0022"`, etc.).
     - **Logik 5 (Fallback)**: Traditionelle Marker "Negative prompt:", "Steps:".
   - Zeigt extrahierte Texte in drei separaten Feldern: Prompt, Negative Prompt, Settings.

3. **Filterung**
   - Bietet umfassende Filteroptionen im Hauptfenster:
     - **Prompt-Filter**: "All words must match", "Any word", "Exclude word", "None of the words".
     - **Dateifilter**: Nach Erstellungsdatum (z. B. "This week", "Within 1 year", benutzerdefinierte Eingaben: "Not older than", "Older than", "Between dates").
     - **Dateigrößenfilter**: Min/Max in KB.
   - Filtert Bilder basierend auf Dateiname, Prompt, Negative Prompt oder Settings.
   - Kombiniert alle aktiven Filterkriterien (logisches UND).
   - Speichert Filterverlauf in `ImagePromptViewer-History.json`.

4. **Bildverwaltung**
   - Ermöglicht Löschen von Bildern (in den Papierkorb via `send2trash`) mit optionaler sofortiger Löschung (`Delete`-Taste oder Button).
   - Öffnet Bilder im System-Viewer.
   - Kopiert Dateinamen oder Pfade in die Zwischenablage (im Vollbildmodus).

5. **Benutzeroberfläche und Interaktion**
   - **Hauptfenster**: Zweispaltiges Layout mit Filterpanel (links) und Bildanzeige/Steuerung (rechts).
   - **Vorschau**: Zeigt eine scrollbare Liste mit Thumbnails und Dateinamen der gefilterten Bilder.
   - **Text-Highlighting**: Markiert Filter-Keywords (rot), Lora-Tags `<...>` (weiß) und Gewichtungen `(...)` (hellblau), wenn aktiviert.
   - **Drag-and-Drop**: Akzeptiert Bilddateien zum Laden eines Ordners.
   - **Always on Top**: Optional über Checkbox aktivierbar.
   - **Debug-Fenster**: Zeigt Extraktionsdetails, Systeminfo und Cache-Status.

6. **Dynamische Anpassung**
   - Passt Fenstergröße und Schriftgrößen an die Monitorauflösung an (70% Breite, 85% Höhe).
   - Unterstützt mehrere Monitore mit Wahlmöglichkeit im Vollbildmodus.

#### Wichtige integrierte Funktionen
- **`validate_index`**: Stellt sicher, dass Bildindizes gültig bleiben.
- **`get_datetime_str`**: Liefert formatierten Zeitstempel.
- **`copy_to_clipboard`**: Kopiert Text in die Zwischenablage.
- **`load_image_with_cache`**: Lädt Bilder mit Cache (max. 50 Einträge).
- **`match_keyword`**: Prüft Keyword-Übereinstimmung (ganze Wörter oder Teilstrings).
- **`extract_text_chunks`**: Kernfunktion zur Metadatenextraktion mit fünf Logiken.
- **`get_window_size`, `get_scaling_factor`, `get_default_image_scale`, `get_font_size`, `get_button_padding`**: Dynamische UI-Anpassung.
- **`apply_filters`**: Wendet alle Filterkriterien an und aktualisiert die Bildliste.
- **`highlight_text`**: Markiert Textabschnitte basierend auf Filtern, Lora-Tags und Gewichtungen.
- **`refresh_all_text_highlights`**: Aktualisiert Highlighting in allen Textfeldern.
- **`load_folder_async`**: Lädt Bilder asynchron mit Fortschrittsanzeige.
- **`display_image_safe_async`**: Zeigt Bilder thread-sicher an.
- **`show_fullscreen`**: Öffnet Vollbildmodus mit zusätzlichen Steuerungen.
- **`update_fs_texts`**: Aktualisiert Textfelder im Vollbildmodus.
- **`save_history`, `load_history`**: Verwaltet Verlaufsdaten.

#### Was das Skript können soll
Das Skript soll:
- Bilder (PNG/JPEG) aus einem Ordner laden und anzeigen, inklusive Unterordner (optional).
- Metadaten aus Bildern extrahieren und in Prompt, Negative Prompt und Settings aufteilen.
- Bilder nach Textinhalt, Dateigröße und Erstellungsdatum filtern.
- Eine benutzerfreundliche GUI mit Navigation, Vollbildmodus und Vorschau bereitstellen.
- Bilder löschen, öffnen und deren Informationen kopieren.
- Textabschnitte hervorheben (Filter, Lora, Gewichtungen).
- Sich dynamisch an Bildschirmgrößen anpassen und Benutzerinteraktionen (z. B. Drag-and-Drop) unterstützen.
- Debug-Informationen und Verlaufsdaten persistent speichern.

Diese Funktionen machen das Skript zu einem vielseitigen Werkzeug für die Verwaltung und Analyse von Bildern mit Metadaten, insbesondere für kreative Anwendungen wie KI-generierte Inhalte.




### Zusammenfassung des Skripts: ImagePromptCleaner

#### Allgemeine Beschreibung
Das Skript `ImagePromptCleaner` ist ein Python-Programm, das als Bildbetrachter und Metadaten-Viewer für PNG- und JPEG-Dateien dient. Es liest eingebettete Textinformationen aus Bilddateien (Prompt, Negative Prompt, Settings) und bietet eine grafische Benutzeroberfläche (GUI) zur Anzeige, Navigation, Filterung und Verwaltung von Bildern in einem Ordner. Das Programm ist dynamisch an verschiedene Bildschirmgrößen anpassbar, unterstützt Drag-and-Drop und speichert Verlaufsdaten in einer JSON-Datei.

#### Hauptfunktionen des Skripts
Das Skript bietet folgende Kernfunktionalitäten:

1. **Bildanzeige und Navigation**
   - Lädt und zeigt PNG- und JPEG-Bilder aus einem ausgewählten Ordner an.
   - Ermöglicht Navigation zwischen Bildern mit "Next" und "Back" Buttons sowie Pfeiltasten (`<Left>`, `<Right>`).
   - Unterstützt Vollbildmodus (`F11`) mit zusätzlichen Steuerungen wie Zoom (Ctrl+Mausrad) und Textanzeige ein-/ausblenden.
   - Skaliert Bilder dynamisch basierend auf Bildschirmgröße oder Benutzerwahl ("Default", "25%", "50%", "75%").

2. **Metadatenextraktion**
   - Extrahiert Textinformationen aus Bild-Metadaten mit mehreren Logiken (`extract_text_chunks`):
     - **Logik 1 (JSON)**: Parst JSON-Daten für "prompt", "negativePrompt", "steps" oder "CLIPTextEncode"/"KSampler" Strukturen.
     - **Logik 2 (Marker)**: Teilt Text bei `"prompt":`, `"negativePrompt":`, `"steps":`.
     - **Logik 3 (ComfyUI-Workflow)**: Regex-Suche nach `"inputs":{"text":"` bis `"parser":`.
     - **Logik 4 (Civitai/ComfyUI)**: Spezielle Marker mit Unicode-Escapes (`"p r o m p t \u0022 : \u0022"`, etc.).
     - **Logik 5 (Fallback)**: Traditionelle Marker "Negative prompt:", "Steps:".
   - Zeigt extrahierte Texte in drei separaten Feldern: Prompt, Negative Prompt, Settings.

3. **Filterung**
   - Bietet umfassende Filteroptionen im Hauptfenster:
     - **Prompt-Filter**: "All words must match", "Any word", "Exclude word", "None of the words".
     - **Dateifilter**: Nach Erstellungsdatum (z. B. "This week", "Within 1 year", benutzerdefinierte Eingaben: "Not older than", "Older than", "Between dates").
     - **Dateigrößenfilter**: Min/Max in KB.
   - Filtert Bilder basierend auf Dateiname, Prompt, Negative Prompt oder Settings.
   - Kombiniert alle aktiven Filterkriterien (logisches UND).
   - Speichert Filterverlauf in `ImagePromptViewer-History.json`.

4. **Bildverwaltung**
   - Ermöglicht Löschen von Bildern (in den Papierkorb via `send2trash`) mit optionaler sofortiger Löschung (`Delete`-Taste oder Button).
   - Öffnet Bilder im System-Viewer.
   - Kopiert Dateinamen oder Pfade in die Zwischenablage (im Vollbildmodus).

5. **Benutzeroberfläche und Interaktion**
   - **Hauptfenster**: Zweispaltiges Layout mit Filterpanel (links) und Bildanzeige/Steuerung (rechts).
   - **Vorschau**: Zeigt eine scrollbare Liste mit Thumbnails und Dateinamen der gefilterten Bilder.
   - **Text-Highlighting**: Markiert Filter-Keywords (rot), Lora-Tags `<...>` (weiß) und Gewichtungen `(...)` (hellblau), wenn aktiviert.
   - **Drag-and-Drop**: Akzeptiert Bilddateien zum Laden eines Ordners.
   - **Always on Top**: Optional über Checkbox aktivierbar.
   - **Debug-Fenster**: Zeigt Extraktionsdetails, Systeminfo und Cache-Status.

6. **Dynamische Anpassung**
   - Passt Fenstergröße und Schriftgrößen an die Monitorauflösung an (70% Breite, 85% Höhe).
   - Unterstützt mehrere Monitore mit Wahlmöglichkeit im Vollbildmodus.

#### Wichtige integrierte Funktionen
- **`validate_index`**: Stellt sicher, dass Bildindizes gültig bleiben.
- **`get_datetime_str`**: Liefert formatierten Zeitstempel.
- **`copy_to_clipboard`**: Kopiert Text in die Zwischenablage.
- **`load_image_with_cache`**: Lädt Bilder mit Cache (max. 50 Einträge).
- **`match_keyword`**: Prüft Keyword-Übereinstimmung (ganze Wörter oder Teilstrings).
- **`extract_text_chunks`**: Kernfunktion zur Metadatenextraktion mit fünf Logiken.
- **`get_window_size`, `get_scaling_factor`, `get_default_image_scale`, `get_font_size`, `get_button_padding`**: Dynamische UI-Anpassung.
- **`apply_filters`**: Wendet alle Filterkriterien an und aktualisiert die Bildliste.
- **`highlight_text`**: Markiert Textabschnitte basierend auf Filtern, Lora-Tags und Gewichtungen.
- **`refresh_all_text_highlights`**: Aktualisiert Highlighting in allen Textfeldern.
- **`load_folder_async`**: Lädt Bilder asynchron mit Fortschrittsanzeige.
- **`display_image_safe_async`**: Zeigt Bilder thread-sicher an.
- **`show_fullscreen`**: Öffnet Vollbildmodus mit zusätzlichen Steuerungen.
- **`update_fs_texts`**: Aktualisiert Textfelder im Vollbildmodus.
- **`save_history`, `load_history`**: Verwaltet Verlaufsdaten.

#### Was das Skript können soll
Das Skript soll:
- Bilder (PNG/JPEG) aus einem Ordner laden und anzeigen, inklusive Unterordner (optional).
- Metadaten aus Bildern extrahieren und in Prompt, Negative Prompt und Settings aufteilen.
- Bilder nach Textinhalt, Dateigröße und Erstellungsdatum filtern.
- Eine benutzerfreundliche GUI mit Navigation, Vollbildmodus und Vorschau bereitstellen.
- Bilder löschen, öffnen und deren Informationen kopieren.
- Textabschnitte hervorheben (Filter, Lora, Gewichtungen).
- Sich dynamisch an Bildschirmgrößen anpassen und Benutzerinteraktionen (z. B. Drag-and-Drop) unterstützen.
- Debug-Informationen und Verlaufsdaten persistent speichern.

Diese Funktionen machen das Skript zu einem vielseitigen Werkzeug für die Verwaltung und Analyse von Bildern mit Metadaten, insbesondere für kreative Anwendungen wie KI-generierte Inhalte.