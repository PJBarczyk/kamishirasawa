from collections import defaultdict
from typing import Dict, Tuple
import pykakasi
import romkan

convert = pykakasi.Kakasi().convert

def convert_concat(text: str) -> Dict[str, str]:
    concatenated = defaultdict(lambda: "")
    for d in convert(text):
        for k, v in d.items():
            concatenated[k] += v
            
    return concatenated

def to_hiragana(text: str) -> str:
    return romkan.to_hiragana(text)

def to_romaji(text: str) -> str:
    return " ".join([x["hepburn"] for x in convert(text)])

def contains_kanji(text: str):
    converted = convert_concat(text)
    return text not in {converted["hira"], converted["kana"]}

def furigana(text: str) -> Tuple[str, str]:
    tuples = []
    
    for d in convert(text):
        orig, hira, kata = d["orig"], d["hira"], d["kana"]
        if orig in {hira, kata}:
            tuples.append((orig, None))
            
        else:            
            for i, (orig_char, hira_char) in enumerate(zip(reversed(orig), reversed(hira))):
                if orig_char != hira_char:
                    break
            
            tuples.append((orig[-i:], hira[-i:]))
            tuples.append((hira[:-i], None))
    
    return tuples