from glob import glob
import logging
import sys
from enum import Enum, auto

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QFont, QFontDatabase
from PyQt6.QtWidgets import (QApplication, QButtonGroup, QCheckBox,
                             QFormLayout, QGridLayout, QHBoxLayout, QLabel,
                             QLineEdit, QListWidget, QListWidgetItem, QMenu,
                             QPushButton, QRadioButton, QToolBar, QVBoxLayout,
                             QWidget)

from games import JaToEnMemoryTest, MemoryTest, Voc
from tts import tts
import kanakanji

app = QApplication(sys.argv)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s-%(levelname)s-%(message)s',
)

for font in glob("fonts/*.?tf"):
    QFontDatabase.addApplicationFont(font)
    
app.setStyleSheet("QWidget{font-size: 12px;}")

class KanjiKanaLabel(QWidget):
    class Mode(Enum):
        ORIGINAL = auto()
        FURIGANA = auto()
        ROMAJI = auto()
        
    base_font_size = 20
    furigana_font_size = 20
    font_family = "Noto Sans JP Black"
            
    def __init__(self, parent: QWidget = None, mode: Mode = Mode.ORIGINAL) -> None:
        super().__init__(parent)
        
        self.text = ""
        self.mode = mode
        
        layout = QGridLayout(self)
        layout.setSpacing(0)
        
        self.setStyleSheet(f"""
                           QLabel{{font-size: {self.base_font_size}pt; font-family: {self.font_family}}}
                           """)  
        
    def setText(self, text: str) -> None:
        self.text = text
        
        for i in reversed(range(self.layout().count())):
            self.layout().itemAt(i).widget().setParent(None)
        
        match self.mode:
            case self.Mode.ORIGINAL:
                self.layout().addWidget(QLabel(text=text))
                
            case self.Mode.FURIGANA:
                if not kanakanji.contains_kanji(text):
                    self.layout().addWidget(QLabel(text=kanakanji.to_romaji(text)))
                else:
                    for column, (og, hira) in enumerate(kanakanji.furigana(text)):
                        if hira:
                            label = QLabel(text=hira)
                            label.setStyleSheet(f"QLabel{{font-size: {self.furigana_font_size}px;}}")
                            self.layout().addWidget(label, 0, column, alignment=Qt.AlignmentFlag.AlignCenter)
                        
                        self.layout().addWidget(QLabel(text=og), 1, column, alignment=Qt.AlignmentFlag.AlignCenter)                            
            
            case self.Mode.ROMAJI:
                self.layout().addWidget(QLabel(text=kanakanji.to_romaji(text)))
                
    def setMode(self, mode: Mode) -> None:
        self.mode = mode
        self.setText(self.text)
    

class MemoryTestWidget(QWidget):
    class State(Enum):
        READING_ANSWER = auto()
        GIVING_FEEDBACK = auto()
    
    def __init__(self, memory_test: MemoryTest, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        
        self.memory_test = memory_test
        self.state = self.State.READING_ANSWER
        
        self.display_settings = QButtonGroup()
        r1 = QRadioButton(text="Kanji/Kana")
        r1.setChecked(True)
        r1.toggled.connect(lambda: self.question_label.setMode(KanjiKanaLabel.Mode.ORIGINAL))
        r2 = QRadioButton(text="Furigana")
        r2.toggled.connect(lambda: self.question_label.setMode(KanjiKanaLabel.Mode.FURIGANA))
        r3 = QRadioButton(text="Romaji")
        r3.toggled.connect(lambda: self.question_label.setMode(KanjiKanaLabel.Mode.ROMAJI))
        self.display_settings.addButton(r1)
        self.display_settings.addButton(r2)
        self.display_settings.addButton(r3)
        
        self.question_label = KanjiKanaLabel()
        self.question_label.setText(memory_test.question)
        self.answer_input = QLineEdit()
        self.feedback_label = QLabel()
        
        self.confirm_button = QPushButton(text="Check")
        self.confirm_button.clicked.connect(lambda: self.on_confirm_pressed())
        
        self.confirm_action = QAction()
        self.confirm_action.setShortcut("Return")
        self.confirm_action.triggered.connect(lambda: self.on_confirm_pressed())
        self.addAction(self.confirm_action)
        
        layout = QVBoxLayout(self)
        layout.addWidget(r1, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(r2, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(r3, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.question_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.answer_input, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.feedback_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.confirm_button, alignment=Qt.AlignmentFlag.AlignCenter)
        
    def on_confirm_pressed(self):
        match self.state:
            case self.State.READING_ANSWER:                
                self.state = self.State.GIVING_FEEDBACK
                
                self.answer_input.setDisabled(True)
                self.confirm_button.setText("Next")
                
                if self.memory_test.check_answer(self.answer_input.text()):
                    self.feedback_label.setText("<b>Correct!</b>")
                    self.memory_test.mark_as_correct()
                
                else:
                    self.feedback_label.setText(
                        f"{'<b>Wrong!</b> ' if self.feedback_label.text() else ''}Should  be: {self.memory_test.answer}")
                    self.memory_test.mark_as_incorrect()
                    
            case self.State.GIVING_FEEDBACK:
                
                self.state = self.State.READING_ANSWER
                
                self.question_label.setText(self.memory_test.question)
                self.answer_input.setDisabled(False)
                self.answer_input.setText("")
                self.answer_input.setFocus()
                self.feedback_label.setText("")
                self.confirm_button.setText("Check")


window = QWidget()
window.setWindowTitle("Kamishirasawa")
window.setGeometry(700, 400, 300, 200)

vocs = [voc for voc in Voc.get_from_json("kanji_by_grade.json") if voc.grade == 1]
test = JaToEnMemoryTest(vocs, 3, 6)

layout = QHBoxLayout(window)
layout.addWidget(MemoryTestWidget(memory_test=test))

window.show()

sys.exit(app.exec())
