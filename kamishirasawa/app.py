import itertools
import logging
import random
import sys
import typing
from abc import ABC, abstractmethod
from enum import Enum, auto
from glob import glob
from random import sample

from PyQt6.QtCore import QRunnable, Qt, QThreadPool
from PyQt6.QtGui import QAction, QFontDatabase, QIcon
from PyQt6.QtWidgets import (QApplication, QButtonGroup, QGridLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QRadioButton, QSizePolicy, QVBoxLayout, QWidget)

import lang_utils
from games import FlashcardGame, JaToEnGame, Voc
from tts import tts

app = QApplication(sys.argv)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s-%(levelname)s-%(message)s',
)

for font in glob("fonts/*.?tf"):
    QFontDatabase.addApplicationFont(font)
    
app.setStyleSheet("QWidget{font-size: 12px;}")

class MetaQAbstractWidget(type(QWidget), type(ABC)):
    pass

class QAbstractWidget(QWidget, ABC, metaclass=MetaQAbstractWidget):
    pass

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
        self.__text = ""
        self.mode = mode
        
        layout = QGridLayout(self)
        layout.setSpacing(0)
        
        self.setStyleSheet(f"""
                           QLabel{{font-size: {self.base_font_size}pt; font-family: {self.font_family}}}
                           """)  
        
    def text(self) -> str:
        return self.__text
        
    def setText(self, text: str) -> None:
        self.__text = text
        
        for i in reversed(range(self.layout().count())):
            self.layout().itemAt(i).widget().setParent(None)
        
        match self.mode:
            case self.Mode.ORIGINAL:
                self.layout().addWidget(QLabel(text=text))
                
            case self.Mode.FURIGANA:
                if not lang_utils.contains_kanji(text):
                    self.layout().addWidget(QLabel(text=lang_utils.to_romaji(text)))
                else:
                    for column, (og, hira) in enumerate(lang_utils.furigana(text)):
                        if hira:
                            label = QLabel(text=hira)
                            label.setStyleSheet(f"QLabel{{font-size: {self.furigana_font_size}px;}}")
                            self.layout().addWidget(label, 0, column, alignment=Qt.AlignmentFlag.AlignCenter)
                        
                        self.layout().addWidget(QLabel(text=og), 1, column, alignment=Qt.AlignmentFlag.AlignCenter)                            
            
            case self.Mode.ROMAJI:
                self.layout().addWidget(QLabel(text=lang_utils.to_romaji(text)))
                
    def setMode(self, mode: Mode) -> None:
        self.mode = mode
        self.setText(self.__text)
        
class TTSButton(QPushButton):    
    class TTSRunnable(QRunnable):
        def __init__(self, text: str, lang: str, widget: QWidget) -> None:
            super().__init__()
            self.text = text
            self.lang = lang
            self.widget = widget
            
        def run(self) -> None:
            tts(self.text, self.lang)
            self.widget.setDisabled(False)
    
    icon: QIcon = QIcon("icons/speaker.png")
    
    def __init__(self, text_supplier: typing.Callable[[], str], **kwargs):
        super().__init__(**kwargs)
        self.text_supplier = text_supplier
        self.setIcon(self.icon)
        self.setFixedSize(32, 32)
        self.clicked.connect(self.__on_clicked)
        
    def __on_clicked(self) -> None:
        self.setDisabled(True)
        QThreadPool.globalInstance().start(self.TTSRunnable(text=self.text_supplier(), lang="ja", widget=self))
        

class FlashcardGameWidget(QAbstractWidget):
    class State(Enum):
        READING_ANSWER = auto()
        GIVING_FEEDBACK = auto()
    
    def __init__(self, game: FlashcardGame, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        
        self.game = game
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
        self.question_label.setText(game.question)
        self.tts_button = TTSButton(self.question_label.text)
        question_widget = QWidget()
        question_widget_layout = QHBoxLayout(question_widget)
        question_widget_layout.addWidget(self.question_label)   
        question_widget_layout.addWidget(self.tts_button)
        
        layout = QVBoxLayout(self)
        layout.addWidget(r1, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(r2, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(r3, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(question_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.create_input_widget(), alignment=Qt.AlignmentFlag.AlignCenter)
                
    @abstractmethod
    def create_input_widget(self) -> QWidget:
        ...
                
    def on_correct_answer(self) -> None:
        self.game.mark_as_correct()
    
    def on_incorrect_answer(self) -> None:
        self.game.mark_as_incorrect()

    def on_new_question(self) -> None:
        self.question_label.setText(self.game.question)
        
class TextInputFlashcardGameWidget(FlashcardGameWidget):
    def create_input_widget(self) -> QWidget:
        input_widget = QWidget()
        
        self.answer_input = QLineEdit()
        self.feedback_label = QLabel()
        
        self.confirm_button = QPushButton(text="Check")
        self.confirm_button.clicked.connect(lambda: self.on_confirm_pressed())
        
        self.confirm_action = QAction()
        self.confirm_action.setShortcut("Return")
        self.confirm_action.triggered.connect(lambda: self.on_confirm_pressed())
        self.addAction(self.confirm_action)
        
        layout = QVBoxLayout(input_widget)
        layout.addWidget(self.answer_input, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.feedback_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.confirm_button, alignment=Qt.AlignmentFlag.AlignCenter)
        
        return input_widget
    
    def on_confirm_pressed(self):
        match self.state:
            case self.State.READING_ANSWER:                
                self.state = self.State.GIVING_FEEDBACK
                
                self.answer_input.setDisabled(True)
                self.confirm_button.setText("Next")
                
                if self.game.check_answer(self.answer_input.text()):
                    self.feedback_label.setText("<b>Correct!</b>")
                    self.on_correct_answer()
                
                else:
                    self.feedback_label.setText(
                        f"{'<b>Wrong!</b> ' if self.feedback_label.text() else ''}Should be: {self.game.formatted_answer}")
                    self.on_incorrect_answer()
                    
            case self.State.GIVING_FEEDBACK:
                self.state = self.State.READING_ANSWER
                
                self.answer_input.setDisabled(False)
                self.answer_input.setText("")
                self.answer_input.setFocus()
                self.feedback_label.setText("")
                self.confirm_button.setText("Check")
                
                self.on_new_question()
                
class ChoiceFlashcardGameWidget(FlashcardGameWidget):
    def __init__(self, game: FlashcardGame, choices: int, *args, **kwargs) -> None:
        assert choices >= 2
        self.choices = choices
        
        super().__init__(game, *args, **kwargs)
        
    def create_input_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.feedback_label = QLabel()
        layout.addWidget(self.feedback_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.answer_buttons = [QPushButton() for _ in range(self.choices)]
        self.answer_button_actions = []
        
        def connect(button: QPushButton, action: QAction):
            button.clicked.connect(lambda: self.give_answer(button.text()))
            if action:
                action.triggered.connect(lambda: self.give_answer(button.text()))
        
        keys_iter = iter([str(n) for n in [*range(1, 10)] + [0]])
        for button in self.answer_buttons:
            layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
            
            try:
                action = QAction()
                action.setShortcut(next(keys_iter))
                button.addAction(action)
                self.answer_button_actions.append(action)
            except:
                action = None
            
            connect(button, action)
            
        self.set_choices()
        
        return widget
        
    def set_choices(self) -> None:
        available_answers = [self.game.formatted_answer] + self.game.sample_incorrect_answers(self.choices - 1)
        random.shuffle(available_answers)
        
        for button, answer in zip(self.answer_buttons, available_answers):
            button.setText(answer)             
    
    def give_answer(self, answer: str) -> None:        
        match self.state:
            case self.State.READING_ANSWER:                
                self.state = self.State.GIVING_FEEDBACK
                
                for button in self.answer_buttons:
                    button.setDisabled(not self.game.check_answer(button.text()))
                
                if self.game.check_answer(answer):
                    self.feedback_label.setText("<b>Correct!</b>")
                    self.on_correct_answer()
                
                else:
                    self.feedback_label.setText(
                        f"<b>Wrong!</b> Should be: {self.game.formatted_answer}")
                    self.on_incorrect_answer()
                    
                    
            case self.State.GIVING_FEEDBACK:
                self.state = self.State.READING_ANSWER
                
                for button in self.answer_buttons:
                    button.setDisabled(False)
                self.set_choices()
                    
                self.feedback_label.setText("")
                
                self.on_new_question()
        


window = QWidget()
window.setWindowTitle("Kamishirasawa")
window.setGeometry(700, 400, 300, 200)

vocs = [voc for voc in Voc.get_from_json("kanji_by_grade.json") if voc.grade == 1]
test = JaToEnGame(vocs, 5)

layout = QHBoxLayout(window)
layout.addWidget(ChoiceFlashcardGameWidget(game=test, choices=3))

window.show()

sys.exit(app.exec())
