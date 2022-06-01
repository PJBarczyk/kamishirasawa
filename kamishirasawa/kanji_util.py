from collections import namedtuple
import json
import pykakasi

Voc = namedtuple("Voc", "kana meaning categories grade")

vocs: list[Voc] = []

with open("kanji_by_grade.tsv", "r", encoding="utf8") as file:
    for line in file.readlines():
        [grade, kana, meaning] = line.strip().split("\t")
        meaning = meaning.split(", ")
        
        vocs.append(Voc(kana, meaning, [], grade))

with open("kanji_by_grade.json", "w", encoding="utf8") as file:
    file.truncate()
    json.dump([v._asdict() for v in vocs], file, indent=4)