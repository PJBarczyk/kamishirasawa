from collections import namedtuple
import json
from kamishirasawa.games import Voc

with open("./kanji_by_grade.json", 'r') as infile, open("./kanji_by_grade.kamidb", 'w') as outfile:
    outfile.truncate()
    vocs: list[Voc] = json.load(infile, object_hook= lambda d: Voc(**d))
    Voc2 = namedtuple("Voc2", "word meaning categories")
    voc2s = [Voc2(v.word, v.meaning, ["Kyouiku kanji", f"{v.grade}th grade"])._asdict() for v in vocs]
    json.dump(voc2s, outfile, indent=4)