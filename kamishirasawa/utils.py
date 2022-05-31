from collections import defaultdict
from typing import Dict, Tuple
import pykakasi

convert = pykakasi.Kakasi().convert

def convert_concat(text: str) -> Dict[str, str]:
    concatenated = defaultdict(lambda: "")
    for d in convert(text):
        for k, v in d.items():
            concatenated[k] += v
            
    return concatenated

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
            rev_orig_chars, rev_hira_chars = list(reversed(orig)), list(reversed(hira))
            
            common_hira = ""
            while True:
                orig_char, hira_char = rev_orig_chars[0], rev_hira_chars[0]
                
                if orig_char != hira_char:
                    break
                else:
                    rev_orig_chars.pop(0)
                    rev_hira_chars.pop(0)
                    common_hira = hira_char + common_hira
                    
            tuples.append(("".join(reversed(rev_orig_chars)), 
                           "".join(reversed(rev_hira_chars))))
            tuples.append((common_hira, None))
    
    return tuples