import os
import langdetect
from playsound import playsound, PlaysoundException
import tempfile
import gtts


def tts(text: str, lang: str = None):
    try:
        with tempfile.NamedTemporaryFile(dir="", suffix='.mp3', delete=False) as file:
            gtts.gTTS(text, lang=lang if lang else langdetect.detect(text), slow=True).write_to_fp(file)
            
        playsound(file.name)
        
    except PlaysoundException:
        pass
    
    finally:
        os.remove(file.name)
        