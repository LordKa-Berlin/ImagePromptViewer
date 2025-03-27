Zusammenfassung der Anforderungen und Vorgaben für die Zusammenarbeit
Allgemeine Informationen und Kontext
Projekt: Entwicklung eines Python-Programms namens ImagePromptViewer, das Metadaten (Textchunks) aus Bilddateien (PNG und JPEG) extrahiert und anzeigt.
Ziel: Korrekte Extraktion und Anzeige von Textchunks aus JPEG-Dateien über EXIF-Daten (Tag 37510, "UserComment"), aufgeteilt in Prompt, Negativen Prompt und Settings.
Aktuelle Version: 1.0.35.8 (Stand 26. März 2025).
Nächste Version: 1.0.35.9 (für die nächste Änderung).
Branch: entwicklung (für Git-Commits).
Technische Anforderungen
Programmiersprache: Python 3.
Bibliotheken:
tkinter und tkinterdnd2 (GUI und Drag-and-Drop).
PIL (Pillow) (Bildverarbeitung).
screeninfo (Monitorauflösung).
send2trash (Löschen in den Papierkorb).
piexif (EXIF-Daten aus JPEG).
Dateiformate:
PNG: Textchunks aus info['parameters'].
JPEG: Textchunks aus EXIF-Tag 37510 ("UserComment"), beginnend mit "UNICODE".
Textchunk-Dekodierung:
Entferne "UNICODE\x00\x00" (erste 8 Bytes) und dekodiere den Rest als UTF-16LE.
Teste alternative Kodierungen (utf-16be, utf-8, latin-1) bei Fehlern.
Fallback: Entferne \x00-Zeichen und dekodiere als latin-1.
Teile den Text in Prompt, Negativen Prompt und Settings mit Trennzeichen "Negative prompt:" und "Steps:".
Debug-Ausgabe: Zeige rohe Bytes, dekodierten Text und aufgeteilte Teile an.
Funktionale Anforderungen
Textchunk-Extraction: Korrekte Extraktion und Dekodierung aus JPEG-EXIF-Daten.
GUI:
Zeige Prompt, Negativen Prompt und Settings in Textfeldern.
Unterstütze Filterung (Dateiname, Prompt, Negativer Prompt, Settings).
Drag-and-Drop für Ordner, Vollbildmodus, dynamische Bildgröße, Löschen mit Bestätigung (außer bei "sofort löschen").
Performance: Nutze Caches (ctime_cache, text_chunks_cache) und Lazy Loading für Vorschau.
Technische Vorgaben
Versionskontrolle:
Arbeite im Branch entwicklung.
Commit-Nachrichten beschreiben Änderungen klar, z. B.: "Fix JPEG text chunk decoding with multiple encodings (Version 1.0.35.8)".
Beispiel-Git-Befehle:
bash

Einklappen

Zeilenumbruch

Kopieren
cd "C:/Users/lordk/OneDrive/#Lordka/#SCRIPTE/PYTHON/ImagePromptViewer"  
git add ImagePromptViewer-1.0.35.8.py  
git rm ImagePromptViewer-1.0.35.7.py  
git commit -m "Fix JPEG text chunk decoding with multiple encodings (Version 1.0.35.8)"  
git push origin entwicklung  
Dateinamen: Code als ImagePromptViewer-<Version>.py speichern, alte Version entfernen.
Zusammenarbeitsvorgaben
Kommunikation:
Analysiere Debug-Ausgaben und schlage gezielte Lösungen vor.
Fasse Änderungen pro Version im Code-Kommentar und in der Antwort zusammen.
Gib Testanleitungen zur Überprüfung.
Fehlerbehebung:
Bei unlesbaren Zeichen (z. B. 猀挀漀爀攀开㤀) Kodierung analysieren und Lösung vorschlagen.
Stelle vollständigen Code bereit, falls unvollständig.
Testanleitung:
Lade JPEG-Dateien mit "UNICODE"-Textchunks.
Prüfe Anzeige von Prompt, Negativem Prompt und Settings.
Überprüfe Debug-Ausgabe auf korrekte Dekodierung.
Teste Filterfunktion.
Aktueller Stand des Projekts
Version: 1.0.35.8
Datum: 26. März 2025
Ziel des Projekts: Entwicklung von ImagePromptViewer, einem Tool zur Extraktion und Anzeige von Metadaten aus Bilddateien (PNG und JPEG) mit einer benutzerfreundlichen GUI.
Fortschritt:
PNG-Textchunk-Extraction aus info['parameters'] funktioniert einwandfrei.
JPEG-Textchunk-Extraction aus EXIF-Tag 37510 ("UserComment") ist implementiert, aber die Dekodierung ist fehlerhaft.
GUI mit Drag-and-Drop, Vollbildmodus, Filterung und Löschfunktion ist funktionsfähig.
Performance-Optimierungen (Caching, Lazy Loading) sind teilweise implementiert.
Aktuelles Problem
Beschreibung: Die Dekodierung des Textchunks aus JPEG-Dateien (EXIF-Tag 37510) liefert unlesbare Zeichen, z. B. 猀挀漀爀攀开㤀, anstelle des erwarteten Prompts wie score_9,score_8_up,score_7_up, BREAK 1girl being choked, ArielXL, (hot....
Letzte Debug-Ausgabe:
text

Einklappen

Zeilenumbruch

Kopieren
Debug: Text aus EXIF-Exif-37510: '猀挀漀爀攀开㤀Ⰰ猀挀漀爀攀开㠀开甀瀀Ⰰ猀挀漀爀攀开㜀开甀瀀Ⰰ 䈀刀䔀䄀䬀 ㄀最椀爀氀 戀攀椀渀最 挀...'  
Debug: Prompt: 猀挀漀爀攀开㤀Ⰰ猀挀漀爀攀开㠀开甀瀀Ⰰ猀挀漀爀攀开㜀开甀瀀Ⰰ 䈀刀䔀䄀䬀 ㄀最椀爀氀 戀攀椀渀最 挀...  
Debug: Negativ: ...  
Debug: Settings: ...  
Analyse:
Der Textchunk beginnt mit "UNICODE\x00\x00" und sollte als UTF-16LE dekodiert werden, aber die Ausgabe zeigt, dass die Dekodierung fehlschlägt.
Mögliche Ursachen: Falsche Kodierung, fehlerhafte Entfernung von Nullbytes oder beschädigte Daten.
Nächste Schritte
Fehlerbehebung:
Teste verschiedene Kodierungen (utf-16le, utf-16be, utf-8, latin-1).
Zeige rohe Bytes und dekodierten Text in der Debug-Ausgabe an, um die Kodierung zu analysieren.
Implementiere Fallback: Entferne \x00-Zeichen und dekodiere als latin-1 bei Fehlern.
Testen:
Lade einen Ordner mit JPEG-Dateien, inklusive des Beispielbildes (Krankenschwester).
Prüfe, ob Prompt, Negativer Prompt und Settings korrekt angezeigt werden.
Analysiere die Debug-Ausgabe im Debug-Fenster, insbesondere den "Full decoded text".
Speichern und Commit:
Speichere den Code als ImagePromptViewer-1.0.35.8.py.
Commit in den Branch entwicklung mit einer Nachricht wie:
bash

Einklappen

Zeilenumbruch

Kopieren
git add ImagePromptViewer-1.0.35.8.py  
git commit -m "Fix JPEG text chunk decoding with multiple encodings (Version 1.0.35.8)"  
git push origin entwicklung  
Zusätzliche Hinweise
Beispielbild: Ein JPEG-Bild einer Krankenschwester wurde bereitgestellt, um die Textchunk-Extraction zu testen.
Erwarteter Prompt: Sollte etwa wie score_9,score_8_up,score_7_up, BREAK 1girl being choked, ArielXL, (hot... aussehen, typisch für KI-generierte Bilder.
Bitte an dich: Teste den Code mit dem Beispielbild, teile mir die neue Debug-Ausgabe mit und schlage eine Lösung für das Kodierungsproblem vor, falls der Prompt weiterhin unlesbar ist.
Diese Übersicht sollte dir und jeder KI, die sie liest, einen klaren Stand des Projekts vermitteln. Lass mich wissen, wenn du weitere Informationen brauchst!