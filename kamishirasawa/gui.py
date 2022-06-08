import os
import random
import typing
from abc import ABC, abstractmethod
from enum import Enum, auto

from PyQt6.QtCore import QRunnable, Qt, QThreadPool, QSize
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (QButtonGroup, QComboBox, QFileDialog, QGridLayout,
                             QHBoxLayout, QLabel, QLineEdit, QMainWindow,
                             QPushButton, QRadioButton, QTableWidget,
                             QVBoxLayout, QWidget, QTableWidgetItem, QHeaderView)

from utils import ObservableFlag

import lang_utils
from games import FlashcardGame
from keine import DBAlreadyAttachedError, DBParseError, Keine
from tts import tts
from utils import Event


class MetaQAbstractWidget(type(QWidget), type(ABC)):
    pass

class QAbstractWidget(QWidget, ABC, metaclass=MetaQAbstractWidget):
    pass

class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget = None, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self.setWindowTitle("Keine")
        self.resize(400, 400)
        self.keine = Keine()
        
        self.place_menubar()
        self.attached_dbs = set()
                
        self.workspace = QWidget()
        self.setCentralWidget(self.workspace)
        layout = QVBoxLayout(self.workspace)
        
        layout.addWidget(DBManager(self, self.keine), 1)
        
        self.destroyed.connect(self.keine.close_all_dbs)
        
    def place_menubar(self):
        menubar = self.menuBar()
        
        filemenu = menubar.addMenu("File")
        attach = filemenu.addAction("Attach DB")
        attach.setShortcut("Ctrl+Shift+A")
        attach.triggered.connect(lambda: self.attach_db_dialog(disconnect))
        
        disconnect = filemenu.addAction("Disconnect all DBs")
        disconnect.triggered.connect(lambda: self.disconnect_all_dbs(disconnect))
        disconnect.setDisabled(True)
        disconnect_disable_func = lambda *_: disconnect.setDisabled(not self.keine.dbs or bool(self.keine.dbs_lock))
        self.keine.on_dbs_changed(disconnect_disable_func)
        self.keine.dbs_lock.add_on_write(disconnect_disable_func)
        
        filemenu.addSeparator()
        quit = filemenu.addAction("Quit")
        quit.triggered.connect(self.close)
        quit.setShortcut("Ctrl+Q")

        learnmenu = menubar.addMenu("Learn")
        attach = learnmenu.addAction("Hiragana")
        
    def attach_db_dialog(self, disconnect_action = QAction):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Attach DB",
            os.path.dirname(__file__),
            "Kamishirasawa DB files (*.kamidb);;All files (*.*)")
        
        if len(paths) == 1:
            path = paths[0]
            if not path:
                self.statusBar().showMessage(f"Cancelled DB attachment.")
                return
            
            try:
                self.keine.attach_db(path)
                self.statusBar().showMessage(f"Attached '{os.path.basename(path)}'.")
            except DBAlreadyAttachedError:
                self.statusBar().showMessage(f"DB '{os.path.basename(path)}' is already attached.")
            except DBParseError:
                self.statusBar().showMessage(f"Failed to parse '{os.path.basename(path)}'.")
                
        else:
            successfully_attached = []
            already_attached = []
            failed = []
            for path in paths:
                try:
                    self.keine.attach_db(path)
                    successfully_attached.append(path)
                                    
                except DBParseError:
                    failed.append(path)
                except DBAlreadyAttachedError:
                    already_attached.append(path)
                
            message = f"Attached {len(successfully_attached)} DBs"
            if already_attached:
                message += f", {len(already_attached)} were already attached"
            if failed:
                message += f", could not parse{len(failed)} DBs"
            message += "."
            self.statusBar().showMessage(message)
                
            
            
        disconnect_action.setDisabled(False)
            
    def disconnect_all_dbs(self, disconnect_action = QAction):
        if self.keine.dbs:
            self.keine.close_all_dbs()
            self.statusBar().showMessage(f"Disconnected all DBs.")
            disconnect_action.setDisabled(True)
        else:
            self.statusBar().showMessage(f"No DBs are attached.")


class DBManager(QWidget):
    def __init__(self, parent: QWidget, keine: Keine, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        
        self.keine = keine
        self.dbs = set()
        self.keine.on_dbs_changed += self.update_db_selector
        
        layout = QVBoxLayout(self)
        
        self.place_db_selection_widget()
        self.place_save_changes_widget()
        self.place_table()
        self.redraw_voc_table()
        
        self.db_edit_widget = QWidget(self)
        edit_layout = QHBoxLayout(self.db_edit_widget)
        self.db_delete_voc = QPushButton(text="Remove selected")
        self.db_add_voc = QPushButton(text="Add new")
        edit_layout.addWidget(self.db_delete_voc)        
        edit_layout.addWidget(self.db_add_voc)
        
        layout.addWidget(self.db_edit_widget)
        
        
        self.update_db_selector()
        
    def place_db_selection_widget(self):
        self.db_selection_widget = QWidget(self)
        selection_layout = QHBoxLayout(self.db_selection_widget)
        
        self.db_combobox = QComboBox(self.db_selection_widget)
        self.db_combobox.currentIndexChanged.connect(self.redraw_voc_table)
        detach_button = QPushButton(icon=QIcon("./icons/detach.png"))
        detach_button.setFixedSize(32, 32)
        detach_button.clicked.connect(lambda: self.keine.detach_db(self.db_combobox.currentData()))
        
        selection_layout.addWidget(self.db_combobox, 1)
        selection_layout.addWidget(detach_button, 0)
        self.layout().addWidget(self.db_selection_widget)
        
        self.keine.dbs_lock.add_on_write(lambda b: self.db_selection_widget.setDisabled(b))
        
        
    def place_save_changes_widget(self):
        self.save_changes_widget = QWidget()
        save_changes_layout = QHBoxLayout(self.save_changes_widget)
        
        self.revert_changes_button = QPushButton("Revert changes")
        self.revert_changes_button.clicked.connect(self.revert_changes)
        self.save_changes_button = QPushButton("Save changes")
        self.save_changes_button.clicked.connect(self.save_changes)
        
        save_changes_layout.addWidget(self.revert_changes_button)
        save_changes_layout.addWidget(self.save_changes_button)
        self.layout().addWidget(self.save_changes_widget)
        
        self.keine.dbs_lock.add_on_write(lambda b: self.save_changes_widget.setDisabled(not b))
        self.save_changes_widget.setDisabled(True)
        
        
    def place_table(self):
        self.voc_table = QTableWidget()
        self.voc_table.setColumnCount(3)
        self.voc_table.itemActivated.connect(self.on_item_selected)
        self.voc_table.itemChanged.connect(self.on_item_changed)
        
        self.voc_table.setHorizontalHeaderLabels(["Word", "Meaning", "Categories"])
        header = self.voc_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        self.layout().addWidget(self.voc_table)
        
    def update_db_selector(self):
        last_db = self.db_combobox.currentData()
        self.db_combobox.clear()
        
        match list(self.keine.dbs):
            case []:
                self.db_selection_widget.setDisabled(True)
            case [db]:
                self.db_combobox.addItem(os.path.basename(db.path), db)
                self.db_selection_widget.setDisabled(False)
                self.db_combobox.setCurrentIndex(0)

            case dbs:
                commonpath_length = len(os.path.commonpath([db.path for db in dbs]))
                current_index = 0
                for i, db in enumerate(dbs):
                    print(f"{db = }")
                    self.db_combobox.addItem(db.path[commonpath_length + 1:], db)
                    if db == last_db:
                        current_index = i
                        
                self.db_combobox.setCurrentIndex(current_index)
                self.db_selection_widget.setDisabled(False)      
        
    def on_item_selected(self, item: QTableWidgetItem):
        pass
                
    def on_item_changed(self, item: QTableWidgetItem):
        item.setText(item.text().strip())
        
        def validate(self, item: QTableWidgetItem):
            text = item.text()
            match item.column():
                case 0:
                    return bool(text)
                case 1:
                    pass
                case 2:
                    pass
            
                
    def redraw_voc_table(self):  
        self.voc_table.clearContents()
        self.voc_table.blockSignals(True)
        header = self.voc_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
        
        if self.db_combobox.currentIndex() != -1:
            vocs = self.db_combobox.currentData().vocs
            
            self.voc_table.setRowCount(len(vocs))
            for row, voc in enumerate(vocs):
                for column, x in enumerate([voc.word, ", ".join(voc.meaning), ", ".join(voc.categories)]):
                    item = QTableWidgetItem(x)
                    self.voc_table.setItem(row, column, item)
            
            self.voc_table.resizeColumnsToContents()
            self.voc_table.resizeRowsToContents()
        else:
            self.voc_table.setRowCount(0)

        self.voc_table.blockSignals(False)
        
    def save_changes(self):
        assert self.keine.dbs_lock
        
        self.voc_table.items()
        
        self.keine.dbs_lock.value = False
        
    def revert_changes(self):
        assert self.keine.dbs_lock
        
        self.redraw_voc_table()
        
        self.keine.dbs_lock.value = False

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
    
    icon_path: str = "icons/speaker.png"
    
    def __init__(self, text_supplier: typing.Callable[[], str], **kwargs):
        super().__init__(**kwargs)
        self.text_supplier = text_supplier
        self.setIcon(QIcon(self.icon_path))
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
                
                
class HiraganaTestSetup(QWidget):
    def __init__(self, parent: QWidget =  None, *args, **kwargs) -> None:
        
        super().__init__(parent, *args, **kwargs)
    