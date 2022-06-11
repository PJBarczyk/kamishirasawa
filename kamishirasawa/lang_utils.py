import random
from collections import defaultdict
from typing import Dict, Iterable, Tuple

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

def furigana(text: str) -> Iterable[Tuple[str, str]]:
    """Returns an iterable of tuples (kanji sequence, hiragana spelling) or (kana/latin, None)"""
    
    tuples = []
    
    for d in convert(text):
        orig, hira, kata = d["orig"], d["hira"], d["kana"]
        if orig in {hira, kata}:
            tuples.append((orig, None))
            
        else:
            i = -1            
            for i, (orig_char, hira_char) in enumerate(zip(reversed(orig), reversed(hira))):
                if orig_char != hira_char:
                    break
                
            if i != -1:
                tuples.append((orig[-i:], hira[-i:]))
                tuples.append((hira[:-i], None))
    
    return tuples

class kaomoji:
    @staticmethod
    def joy():
        """Random joyful kaomoji."""
        return random.choice([
            "＼(≧▽≦)／",
            "☆*:.｡.o(≧▽≦)o.｡.:*☆",
            "٩(◕‿◕｡)۶",
            "(⌒▽⌒)☆",
            "☆ ～('▽^人)",
            "°˖✧◝(⁰▿⁰)◜✧˖°",
            "(*￣▽￣)b",
            "ヽ(>∀<☆)ノ",
            "(´｡• ω •｡`)",
        ])
