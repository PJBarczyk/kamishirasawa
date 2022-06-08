import itertools
import os
import random
import typing
from abc import ABC, abstractmethod
from enum import Enum, auto

from PyQt6.QtCore import QRunnable, Qt, QThreadPool
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QFileDialog,
                             QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                             QLineEdit, QMainWindow, QPushButton, QRadioButton,
                             QTableWidget, QTableWidgetItem, QVBoxLayout,
                             QWidget)
from lang_utils import to_hiragana

import lang_utils
import utils
from games import FlashcardGame, Voc
from keine import DB, DBAlreadyAttachedError, DBParseError, Keine
from tts import tts


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
        layout.addWidget(HiraganaTestSetup(self), 1)
        
        self.statusbar = self.statusBar()
        
        self.destroyed.connect(self.keine.close_all_dbs)
        
    def place_menubar(self):
        menubar = self.menuBar()
        
        filemenu = menubar.addMenu("File")
        attach = filemenu.addAction("Attach DB")
        attach.setShortcut("Ctrl+Shift+A")
        attach.triggered.connect(lambda: self.attach_db_dialog(disconnect))
        
        create = filemenu.addAction("Create a new DB")
        create.setShortcut("Ctrl+Shift+N")
        create.triggered.connect(lambda: self.create_db_dialog(disconnect))

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

    DB_FILE_FILTER = "Kamishirasawa DB files (*.kamidb);;All files (*.*)"
        
    def attach_db_dialog(self, disconnect_action = QAction):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Attach DB",
            os.path.dirname(__file__),
            self.DB_FILE_FILTER)
        
        if len(paths) == 1:
            path = paths[0]
            if not path:
                self.statusbar.showMessage(f"Cancelled DB attachment.")
                return
            
            try:
                self.keine.attach_db(path)
                self.statusbar.showMessage(f"Attached '{os.path.basename(path)}'.")
            except DBAlreadyAttachedError:
                self.statusbar.showMessage(f"DB '{os.path.basename(path)}' is already attached.")
            except DBParseError:
                self.statusbar.showMessage(f"Failed to parse '{os.path.basename(path)}'.")
                
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
            self.statusbar.showMessage(message)
                
            
            
        disconnect_action.setDisabled(False)

    def create_db_dialog(self, disconnect_action = QAction):

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Create DB",
            os.path.dirname(__file__),
            self.DB_FILE_FILTER)

        if path:
            try:
                self.keine.create_db(path)
            except:
                self.statusbar.showMessage(f"Failed to create the DB.")

    def disconnect_all_dbs(self, disconnect_action = QAction):
        if self.keine.dbs:
            self.keine.close_all_dbs()
            self.statusbar.showMessage(f"Disconnected all DBs.")
            disconnect_action.setDisabled(True)
        else:
            self.statusbar.showMessage(f"No DBs are attached.")

class DBManager(QWidget):
    list_attribute_delimiters = [",", ";"]
    
    def __init__(self, parent: QWidget, keine: Keine, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        
        self.keine = keine
        self.selected_db = None
        self.keine.on_dbs_changed += self.update_db_selector
        self.keine.on_dbs_changed += lambda: self.db_edit_widget.setEnabled(len(self.keine.dbs) > 0)
        
        layout = QVBoxLayout(self)
        
        self.place_db_selection_widget()
        self.place_save_changes_widget()
        self.place_table()
        self.redraw_voc_table()
        
        self.db_edit_widget = QWidget(self)
        edit_layout = QHBoxLayout(self.db_edit_widget)
        self.db_delete_voc = QPushButton(text="Remove selected")
        self.db_delete_voc.clicked.connect(self.remove_item)
        self.db_add_voc = QPushButton(text="Add new")
        self.db_add_voc.clicked.connect(self.add_item)
        edit_layout.addWidget(self.db_delete_voc)        
        edit_layout.addWidget(self.db_add_voc)
        self.db_edit_widget.setDisabled(True)
        
        layout.addWidget(self.db_edit_widget)
        
        
        self.update_db_selector()
        
    def place_db_selection_widget(self):
        self.db_selection_widget = QWidget(self)
        selection_layout = QHBoxLayout(self.db_selection_widget)
        
        self.db_combobox = QComboBox(self.db_selection_widget)
        self.db_combobox.currentIndexChanged.connect(self.on_selected_db_changed)
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
        self.voc_table.itemClicked.connect(self.on_item_selected)
        self.voc_table.itemChanged.connect(self.on_item_changed)

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
                    self.db_combobox.addItem(db.path[commonpath_length + 1:], db)
                    if db == last_db:
                        current_index = i
                        
                self.db_combobox.setCurrentIndex(current_index)
                self.db_selection_widget.setDisabled(False)
    
    def on_selected_db_changed(self, index: typing.SupportsIndex):
        self.selected_db: DB = self.db_combobox.itemData(index, Qt.ItemDataRole.UserRole)
        self.redraw_voc_table()

    def remove_item(self):
        rows = {x.row() for x in self.voc_table.selectedIndexes()}
        if rows:
            self.keine.dbs_lock.value = True
            for row in rows:
                self.voc_table.removeRow(row)
            self.save_changes_widget.setEnabled(True)

    def add_item(self):
        self.keine.dbs_lock.value = True
        count = self.voc_table.rowCount()
        self.voc_table.setRowCount(count + 1)
        self.set_voc(count, Voc("-", ["-"], ["-"]))
        self.voc_table.scrollToBottom()
        self.save_changes_widget.setEnabled(True)

    def on_item_selected(self, item: QTableWidgetItem):
        print(f"Selected '{item.text()}'({item.row()}, {item.column()})")
        self.last_selected_text = item.text()
                
    def on_item_changed(self, item: QTableWidgetItem):
        text = item.text().strip()
      
        self.voc_table.blockSignals(True)
        try:
            match item.column():
                case 0:
                    if not text:
                        raise ValueError("Field 'Word' cannot be empty")
                    data = text
                case 1:
                    meanings = list({s.strip().lower(): None for s in utils.multi_split(text, self.list_attribute_delimiters) if s})
                    if not meanings:
                        raise ValueError("Field 'Meaning' cannot be empty")
                    text = (self.list_attribute_delimiters[0] + " ").join(meanings)
                    data = meanings
                case 2:
                    categories = list({s.strip().upper(): None for s in utils.multi_split(text, self.list_attribute_delimiters) if s})
                    text = (self.list_attribute_delimiters[0] + " ").join(categories)
                    data = categories

            item.setText(text)
            item.setData(Qt.ItemDataRole.UserRole, data)
            self.keine.dbs_lock.value = True
            
        except ValueError as e:
            self.parent.statusbar.showMessage(". ".join(e.args))
            item.setText(self.last_selected_text)
        
        self.voc_table.blockSignals(False)
            
    def set_voc(self, row: int, voc: Voc):
        delimiter = self.list_attribute_delimiters[0]
        for column, (text, data) in enumerate([(voc.word, voc.word),
                                                (delimiter.join(voc.meaning), voc.meaning),
                                                (delimiter.join(voc.categories), voc.categories)]):
            item = QTableWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, data)
            self.voc_table.setItem(row, column, item)

    def redraw_voc_table(self):  
        self.voc_table.model().blockSignals(True)
        self.voc_table.clearContents()
        self.voc_table.setColumnCount(3)
        
        self.voc_table.setHorizontalHeaderLabels(["Word", "Meaning", "Categories"])
        header = self.voc_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
        
        if self.selected_db:
            vocs = self.selected_db.read_data()
            
            self.voc_table.setRowCount(len(vocs))
            for row, voc in enumerate(vocs):
                self.set_voc(row, voc)
            self.voc_table.resizeRowsToContents()
        else:
            self.voc_table.setRowCount(0)

        self.voc_table.model().blockSignals(False)
        self.voc_table.model().layoutChanged.emit()
        
    def save_changes(self):
        assert self.keine.dbs_lock
        
        vocs = []
        for row in range(self.voc_table.rowCount()):
            [word, meaning, categories] = [self.voc_table.item(row, column).data(Qt.ItemDataRole.UserRole) for column in range(3)]
            print(word, meaning, categories)
            vocs.append(Voc(word, meaning, categories))
            
        self.selected_db.clear_and_write_data(vocs)
        
        self.redraw_voc_table()
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
    @property
    def minor_checkboxes(self):
        return self.vowel_checkboxes + self.consonant_checkboxes
    
    def __init__(self, parent: QWidget =  None, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        
        self.layout = QHBoxLayout(self)
        
        self.place_matrix()
        
        self.selected_hiragana = {}
        
        
    def place_matrix(self):
        self.matrix = QWidget(self)
        self.layout.addWidget(self.matrix)
        self.matrix.layout = QGridLayout(self.matrix)
        
        vowels = ['a', 'i', 'u', 'e', 'o']
        consonants = ['', 'k', 's', 't', 'n', 'h', 'm', 'y', 'r', 'w']
        
        excluded = {"yi", "ye", "wu"}
        exception_dict = {
            "si": "shi",
            "hu": "fu",
            "ti": "chi",
            "tu": "tsu",
        }
        
        alignment = Qt.AlignmentFlag.AlignCenter
        
        self.global_checkbox = QCheckBox()
        self.global_checkbox.setTristate(True)
        def global_checkbox_next_state():
            match self.global_checkbox.checkState():
                case Qt.CheckState.Checked:
                    self.global_checkbox.setCheckState(Qt.CheckState.Unchecked)
                case Qt.CheckState.Unchecked | Qt.CheckState.PartiallyChecked:
                    self.global_checkbox.setCheckState(Qt.CheckState.Checked)
        self.global_checkbox.nextCheckState = global_checkbox_next_state
        self.global_checkbox.stateChanged.connect(self.on_global_checkbox_changed)
        self.matrix.layout.addWidget(self.global_checkbox, 0, 0, alignment)
        
        self.vowel_checkboxes: list[QCheckBox] = []
        self.consonant_checkboxes: list[QCheckBox] = []
        
        
        for row, vowel in enumerate(vowels, start=1):
            checkbox = QCheckBox()
            checkbox.row = row
            self.vowel_checkboxes.append(checkbox)
            self.matrix.layout.addWidget(checkbox, row, 0, alignment)
            
        for column, consonant in enumerate(consonants, start=1):
            checkbox = QCheckBox()
            checkbox.column = column
            self.consonant_checkboxes.append(checkbox)
            self.matrix.layout.addWidget(checkbox, 0, column, alignment)
            
        def romaji_hiragana_label(romaji: str) -> QLabel:
            label = QLabel()
            label.hiragana = lang_utils.to_hiragana(romaji)
            label.romaji = romaji
            label.setText(f"{label.hiragana}\n{label.romaji}")
            label.setAlignment(alignment)
            return label
            
        for (row, vowel), (column, consonant) in itertools.product(enumerate(vowels, start=1), enumerate(consonants, start=1)):          
            if (syllable := consonant + vowel) in excluded:
                continue
            syllable = exception_dict.get(syllable, syllable)
            self.matrix.layout.addWidget(romaji_hiragana_label(syllable), row, column, alignment)
            
        n_column = len(consonants) + 1
        checkbox = QCheckBox()
        checkbox.column = n_column
        self.consonant_checkboxes.append(checkbox)
        self.matrix.layout.addWidget(checkbox, 0, n_column, alignment)
        self.matrix.layout.addWidget(romaji_hiragana_label('n'), 1, n_column, alignment)
        
        for checkbox in self.minor_checkboxes:
            checkbox.stateChanged.connect(self.on_minor_checkbox_changed)
        
    def on_global_checkbox_changed(self):
        if self.global_checkbox.checkState() == Qt.CheckState.PartiallyChecked:
            return
        
        state = Qt.CheckState.Checked if self.global_checkbox.isChecked() else Qt.CheckState.Unchecked
        
        for ch in self.minor_checkboxes:
            ch.blockSignals(False)
            ch.setCheckState(state)
            ch.blockSignals(False)
        
        self.on_selection_changed()
    
    def on_minor_checkbox_changed(self):
        self.global_checkbox.blockSignals(True)
        
        checks = [ch.isChecked() for ch in self.minor_checkboxes]
        
        if all(checks):
            self.global_checkbox.setCheckState(Qt.CheckState.Checked)
        elif any(checks):
            self.global_checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
        else:
            self.global_checkbox.setCheckState(Qt.CheckState.Unchecked)
            
        self.global_checkbox.blockSignals(False)
        self.on_selection_changed()
        
    def on_selection_changed(self):
        
        rows = [ch.row for ch in self.vowel_checkboxes if ch.isChecked()]
        columns = [ch.column for ch in self.consonant_checkboxes[:-1] if ch.isChecked()]
        
        selected_hiragana = set()
        for row, column in itertools.product(rows, columns):
            try:
                label = self.matrix.layout.itemAtPosition(row, column).widget()
                selected_hiragana.add(label.hiragana)
            except:
                pass
        
        if self.vowel_checkboxes[-1].isChecked():
            selected_hiragana.add(to_hiragana('n'))
                       