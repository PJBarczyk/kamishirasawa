import os
import langdetect
from playsound import playsound, PlaysoundException
import tempfile
import gtts


JA_FALLBACK = {"zh-cn", "ko"}

def tts(text: str, lang: str = None):
    try:
        with tempfile.NamedTemporaryFile(dir="", suffix='.mp3', delete=False) as file:
            if not lang:
                lang = langdetect.detect(text)
                if lang in JA_FALLBACK: 
                    # Korean and Chinese use the same characters as Japanese
                    # If one of these is detected, lang is set to Japanese
                    lang = "ja"
                else:
                    # Short words written in latin alphabet are hard to accurately parse without context
                    # As the app uses English, it's assumed that any non-Japanese script is written in English
                    lang = "en"                
            gtts.gTTS(text, lang=lang, slow=True).write_to_fp(file)
            
        playsound(file.name)
        
    except PlaysoundException:
        pass
    
    finally:
        os.remove(file.name)
        