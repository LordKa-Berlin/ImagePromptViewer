Ich übergebe dir hier eine Definition in der 5 Logiken enthalten sind, die Text Chunks aus Bildern extrahieren sollen um diese Textinhalte dann später im Hauptformular
in den Textfeldern Prompt Negativ und Settings einzufügen. Das Problem ist,das zur Zeit wohl eine andere Logik die Prompt textfelder füllt, weil sie eine routine implementiert hat, das wenn nicht extrahieren kann, fülle kompletten Promt in Textfeld, oder so ähnlich. somit kommt Logik 5 gar nicht zum einatz wie es scheint.
Baue die Definition bitte so um, das alle definitionen einen success wert zurück geben, true wenn in Prompt und Negativ ein String erfolgreich extrahiert wurde, nur einer reicht nicht! Wenn True dann übergibt den inhalt an prompt, negativ und settings, wenn success auf false steht, dann soll die nächste Logik ihre Auswertung beginnen.


def extract_text_chunks(img_path):
    try:
        img = Image.open(img_path)
    except Exception as e:
        messagebox.showerror("Error", f"Error opening image:\n{e}")
        return "", "", ""
    
    is_jpeg = img_path.lower().endswith((".jpg", ".jpeg"))
    with open(img_path, "rb") as f:
        header = f.read(8)
    if header.startswith(b'\x89PNG'):
        is_jpeg = False

    full_text = ""
    param_key = None
    debug_info = []
    
    if is_jpeg:
        try:
            exif_dict = piexif.load(img_path)
            user_comment = exif_dict.get("Exif", {}).get(piexif.ExifIFD.UserComment)
            if user_comment and isinstance(user_comment, bytes):
                debug_info.append(f"Debug: Raw bytes from UserComment: {user_comment[:50].hex()}...")
                if user_comment.startswith(b'UNICODE\x00\x00'):
                    try:
                        full_text = helper.UserComment.load(user_comment)
                        debug_info.append("Debug: Decoding with piexif.helper successful.")
                        param_key = "EXIF-Exif-37510"
                    except Exception as e:
                        debug_info.append(f"Debug: piexif.helper error: {e}")
                        full_text = user_comment[8:].decode("utf-16le", errors="ignore")
                        param_key = "EXIF-Exif-37510 (Fallback UTF-16LE)"
                else:
                    full_text = user_comment.decode("latin-1", errors="ignore")
                    debug_info.append("Debug: No UNICODE prefix, decoded as Latin-1.")
                    param_key = "EXIF-Exif-37510 (No UNICODE)"
            if not full_text:
                debug_info.append("Debug: No UserComment tag found or no byte data.")
        except Exception as e:
            debug_info.append(f"Debug: Error reading EXIF data: {e}")
    else:
        for key, value in img.info.items():
            if "parameters" in key.lower():
                param_key = key
                full_text = str(value)
                debug_info.append(f"Debug: PNG text from {param_key}: {repr(full_text)[:100]}...")
                break
        if not full_text:
            for key, value in img.info.items():
                if "prompt" in key.lower() or "metadata" in key.lower() or "description" in key.lower():
                    param_key = key
                    full_text = str(value)
                    debug_info.append(f"Debug: PNG text from fallback {param_key}: {repr(full_text)[:100]}...")
                    break
    
    if not full_text:
        debug_info.append(f"Debug: No key with {'UNICODE' if is_jpeg else 'parameters/fallback'} found.")
        if hasattr(ImageManagerForm, 'instance'):
            ImageManagerForm.instance.debug_info = "\n".join(debug_info)
        return "", "", ""
    
    # Speichere den Originaltext für alle Logiken
    original_text = full_text
    
    # LOGIK 4: Civitai/ComfyUI Format mit speziellen Markern und Unicode-Escapes
    try:
        debug_info.append("Debug: Checking Logik 4 (Civitai/ComfyUI Format)...")
        
        # Definiere die Marker
        marker1 = "p r o m p t \\u 0 0 2 2 : \\u 0 0 2 2"
        marker2 = "n e g a t i v e P r o m p t \\u 0 0 2 2 : \\u 0 0 2 2"
        marker3 = "s t e p s"
        
        # Erst prüfen, ob alle Marker vorhanden sind
        if marker1 in original_text and marker2 in original_text:
            debug_info.append("Debug: Logik 4 - All markers found")
            
            # Prompt Text extrahieren
            start_prompt = original_text.find(marker1) + len(marker1)
            end_prompt = original_text.find(marker2)
            if start_prompt != -1 and end_prompt != -1:
                prompt_text = original_text[start_prompt:end_prompt].strip()
                # Die Zeichenkette "s a f e _ p o s ," entfernen
                safe_pos_pattern = "s a f e _ p o s ,"
                while safe_pos_pattern in prompt_text:
                    prompt_text = prompt_text.replace(safe_pos_pattern, "", 1).strip()
                debug_info.append(f"Debug (Logik 4): Prompt: {repr(prompt_text)[:50]}...")
                
                # Negative Prompt Text extrahieren
                start_negative = end_prompt + len(marker2)
                # Suche nach dem steps-Marker nach dem negativen Prompt
                pos_steps = original_text.find(marker3, start_negative)
                if pos_steps != -1:
                    negative_text = original_text[start_negative:pos_steps].strip()
                    # Die Zeichenkette "s a f e _ n e g ," entfernen
                    safe_neg_pattern = "s a f e _ n e g ,"
                    while safe_neg_pattern in negative_text:
                        negative_text = negative_text.replace(safe_neg_pattern, "", 1).strip()
                    debug_info.append(f"Debug (Logik 4): Negative: {repr(negative_text)[:50]}...")
                    
                    # Settings Text extrahieren (alles ab steps)
                    settings_text = original_text[pos_steps:].strip()
                    debug_info.append(f"Debug (Logik 4): Settings: {repr(settings_text)[:50]}...")
                    
                    debug_info.append("Debug: USING Logik 4 extraction")
                    if hasattr(ImageManagerForm, 'instance'):
                        ImageManagerForm.instance.debug_info = "\n".join(debug_info)
                    
                    return prompt_text, negative_text, settings_text
                else:
                    debug_info.append("Debug: Logik 4 - steps marker not found")
            else:
                debug_info.append("Debug: Logik 4 - prompt markers not properly found")
        else:
            debug_info.append("Debug: Logik 4 - required markers not found")
    except Exception as e:
        debug_info.append(f"Debug: Logik 4 extraction failed: {e}")
    
    # LOGIK 3: ComfyUI-Workflow mit Regex
    try:
        import re  # Sicherstellen, dass re importiert ist
        
        debug_info.append("Debug: Checking Logik 3 (ComfyUI-Workflow)...")
        
        MARKER_START = '"inputs":{"text":"'
        MARKER_END = '"parser":'
        
        pattern = re.escape(MARKER_START) + r'(.*?)' + re.escape(MARKER_END)
        matches = re.findall(pattern, original_text, flags=re.DOTALL)
        
        if matches:
            debug_info.append(f"Debug: Found {len(matches)} matches with ComfyUI markers.")
            
            prompt_regex = ""
            if len(matches) >= 1:
                prompt_regex = matches[0]
                debug_info.append(f"Debug (ComfyUI): First segment found (Prompt): {repr(prompt_regex)[:50]}...")
            
            negativ_regex = ""
            if len(matches) >= 2:
                negativ_regex = matches[1]
                debug_info.append(f"Debug (ComfyUI): Second segment found (Negative): {repr(negativ_regex)[:50]}...")
            
            # Wenn mit Regex etwas gefunden wurde, Ergebnisse zurückgeben
            if prompt_regex or negativ_regex:
                settings_regex = ""  # Settings bleibt leer
                debug_info.append("Debug: USING ComfyUI marker extraction")
                
                if hasattr(ImageManagerForm, 'instance'):
                    ImageManagerForm.instance.debug_info = "\n".join(debug_info)
                    
                return prompt_regex, negativ_regex, settings_regex
            else:
                debug_info.append("Debug: ComfyUI markers found but no valid content extracted")
    except Exception as e:
        debug_info.append(f"Debug: ComfyUI marker extraction failed: {e}")
    
    # Normalisieren für die restlichen Logiken
    normalized = ' '.join(original_text.split())
    debug_info.append(f"Debug: Normalized text: {repr(normalized)[:100]}...")
    
    # Logik 1: JSON-Parsing
    try:
        debug_info.append("Debug: Checking Logik 1 (JSON)...")
        
        data_dict = json.loads(original_text)
        if "models" in data_dict and isinstance(data_dict["models"], list):
            models = data_dict["models"]
            prompt_json = ""
            negative_json = ""
            steps_json = ""
            for model in models:
                if isinstance(model, dict):
                    if "prompt" in model:
                        prompt_json = model["prompt"]
                    if "negativePrompt" in model:
                        negative_json = model["negativePrompt"]
                    if "steps" in model:
                        idx_steps_in_normalized = normalized.find('"steps":')
                        if idx_steps_in_normalized != -1:
                            steps_json = normalized[idx_steps_in_normalized:]
                        else:
                            steps_json = str(model["steps"])
            if prompt_json or negative_json or steps_json:
                debug_info.append("Debug: JSON parsing successful (models).")
                debug_info.append(f"Debug (Prompt): {repr(prompt_json)[:50]}...")
                debug_info.append(f"Debug (Negative Prompt): {repr(negative_json)[:50]}...")
                debug_info.append(f"Debug (Settings): {repr(steps_json)[:100]}...")
                debug_info.append("Debug: USING JSON parsing (models)")
                if hasattr(ImageManagerForm, 'instance'):
                    ImageManagerForm.instance.debug_info = "\n".join(debug_info)
                return str(prompt_json), str(negative_json), steps_json

        prompt_json = data_dict.get("prompt", "")
        negative_json = data_dict.get("negativePrompt", "")
        idx_steps_in_normalized = normalized.find('"steps":')
        if idx_steps_in_normalized != -1:
            settings_text = normalized[idx_steps_in_normalized:]
        else:
            settings_text = str(data_dict.get("steps", ""))
        if not (prompt_json or negative_json):
            for key, value in data_dict.items():
                if isinstance(value, dict):
                    if value.get("class_type", "").lower() == "cliptextencode":
                        text_val = value.get("inputs", {}).get("text", "")
                        if not prompt_json:
                            prompt_json = text_val
                        elif not negative_json:
                            negative_json = text_val

        if not settings_text:
            for key, value in data_dict.items():
                if isinstance(value, dict):
                    if value.get("class_type", "").lower() == "ksampler":
                        steps_val = value.get("inputs", {}).get("steps", "")
                        if steps_val:
                            settings_text = '"steps": ' + str(steps_val)
                            break
                        
        if prompt_json or negative_json or settings_text:
            debug_info.append("Debug: JSON parsing successful (direct).")
            debug_info.append(f"Debug (Prompt): {repr(prompt_json)[:50]}...")
            debug_info.append(f"Debug (Negative Prompt): {repr(negative_json)[:50]}...")
            debug_info.append(f"Debug (Settings): {repr(settings_text)[:100]}...")
            debug_info.append("Debug: USING JSON parsing (direct)")
            if hasattr(ImageManagerForm, 'instance'):
                ImageManagerForm.instance.debug_info = "\n".join(debug_info)
            return str(prompt_json), str(negative_json), settings_text
    except Exception as e:
        debug_info.append(f"Debug: JSON parsing failed: {e}")
    
    # Logik 2: Suche nach Markern im normalisierten Text
    debug_info.append("Debug: Checking Logik 2 (Marker)...")
    
    normalized_lower = normalized.lower()
    if ('"prompt":' in normalized_lower and 
        '"negativeprompt":' in normalized_lower and 
        '"steps":' in normalized_lower):
        idx_prompt_new = normalized_lower.find('"prompt":')
        idx_negative_new = normalized_lower.find('"negativeprompt":')
        idx_steps_new = normalized_lower.find('"steps":')
        prompt_new = normalized[idx_prompt_new + len('"prompt":'): idx_negative_new].strip().strip('",')
        negativ_new = normalized[idx_negative_new + len('"negativeprompt":'): idx_steps_new].strip().strip('",')
        settings_new = normalized[idx_steps_new + len('"steps":'):].strip().strip('",')
        debug_info.extend([
            f"Debug (New Markers): Prompt: {repr(prompt_new)[:50]}...",
            f"Debug (New Markers): Negative Prompt: {repr(negativ_new)[:50]}...",
            f"Debug (New Markers): Settings: {repr(settings_new)[:50]}..."
        ])
        debug_info.append("Debug: USING New Markers extraction")
        if hasattr(ImageManagerForm, 'instance'):
            ImageManagerForm.instance.debug_info = "\n".join(debug_info)
        return prompt_new, negativ_new, settings_new
    
    # Logik 5 (Fallback): Traditionelle Marker "Negative prompt:" und "Steps:"
    debug_info.append("Debug: Checking Logik 5 (Traditional Markers)...")
    
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
            negativ = normalized[idx_neg + len("Negative prompt:"): idx_steps].strip()
        else:
            negativ = normalized[idx_neg + len("Negative prompt:"):].strip()
    else:
        negativ = ""
    
    if idx_steps != -1:
        settings = normalized[idx_steps:].strip()
    else:
        settings = ""
    
    debug_info.extend([
        f"Debug (Old Markers): Prompt: {repr(prompt)[:50]}...",
        f"Debug (Old Markers): Negative Prompt: {repr(negativ)[:50]}...",
        f"Debug (Old Markers): Settings: {repr(settings)[:50]}..."
    ])
    debug_info.append("Debug: USING Old Markers extraction (fallback)")
    
    if hasattr(ImageManagerForm, 'instance'):
        ImageManagerForm.instance.debug_info = "\n".join(debug_info)
    
    return prompt, negativ, settings



