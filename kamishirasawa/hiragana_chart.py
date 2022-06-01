import sys
from tts import tts
import romkan
import pykakasi

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QApplication, QCheckBox, QGridLayout, QHBoxLayout,
                             QLabel, QVBoxLayout, QWidget, QPushButton)

app = QApplication(sys.argv)


window = QWidget()
window.setWindowTitle("Hiragana chart")
window.setGeometry(100, 100, 280, 80)

# vowels = ["a", "i", "u", "e", "o"]  
# consonants = ["", "k", "s", "", "", "", "", "", "", ]
# excluded_syllables = {"yi", "ye", "wu"}

# with dpg.table(header_row=False):
#     for _ in vowels:
#         dpg.add_table_column(width_fixed=True)
        
#     vowels = ["a", "i", "u", "e", "o"]
#     consonants = ["", "k", "s", "t", "n", "h", "m", "y", "r", "w"]
#     excluded_syllables = {"yi", "ye", "wu"}
    
#     def add_hiragana_text(romaji):
#         dpg.add_button(
#             width=100,
#             height=50,
#             label=f"{romaji*3}\n{romkan.to_hiragana(romaji)}",
#             callback=lambda: tts(romkan.to_hiragana(romaji), "ja"),
#         )
    
#     for consonant in consonants:
#         with dpg.table_row():
#             for vowel in vowels:
#                 syllable = consonant + vowel
#                 if syllable not in excluded_syllables:
#                     add_hiragana_text(syllable)
#                 else:
#                     dpg.add_table_cell()
        
#     with dpg.table_row():
#         add_hiragana_text("n")

layout = QGridLayout()

vowels = ["a", "i", "u", "e", "o"]
consonants = ["", "k", "s", "t", "n", "h", "m", "y", "r", "w"]
excluded_syllables = {"yi", "ye", "wu"}

for i, vowel in enumerate([""] + vowels):
    for j, consonant in enumerate([""] + consonants):
        if i == 0 and j == 0:
            continue
        if i == 0:
            widget = QCheckBox()
        elif j == 0:
            widget = QCheckBox()
        else:            
            if (syllable := consonant + vowel) not in excluded_syllables:
                widget = QLabel(f"{syllable}\n{romkan.to_hiragana(syllable)}")
                widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
        layout.addWidget(widget, i, j)
        


window.setLayout(layout)

window.show()
sys.exit(app.exec())
