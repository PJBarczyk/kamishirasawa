import itertools
import os
import random
import typing
from abc import ABC, abstractmethod
from enum import Enum, auto

from PyQt6.QtCore import QRunnable, Qt, QThreadPool
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QFileDialog,
                             QFormLayout, QFrame, QGridLayout, QHBoxLayout,
                             QHeaderView, QLabel, QLineEdit, QMainWindow, QSizePolicy,
                             QPushButton, QRadioButton, QSpinBox, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)

import lang_utils
import utils
from games import FlashcardGame, Voc, JaToEnGame, EnToJaGame
from keine import DB, DBAlreadyAttachedError, DBParseError, Keine
from tts import tts
import csv

class MetaQAbstractWidget(type(QWidget), type(ABC)):
    pass

class QAbstractWidget(QWidget, ABC, metaclass=MetaQAbstractWidget):
    pass

class HSeparator(QFrame):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setFrameShape(QFrame.Shape.HLine)

class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget = None, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self.setWindowTitle("Keine")
        self.resize(400, 400)
        self.keine = Keine()
        
        self.place_menubar()
        self.place_welcome_widget()
        self.statusbar = self.statusBar()
        
        self.destroyed.connect(self.keine.close_all_dbs)
        
    def place_welcome_widget(self) -> None:
        welcome_widget = QWidget(self)
        welcome_widget.layout = QVBoxLayout(welcome_widget)
        welcome_message = f"""<b>Welcome to Kamishirasawa!</b><br><br>
        {lang_utils.kaomoji.joy()}<br><br>

        Attach some DBs or create a new DB<br>
        using <b>File</b> menu or open <b>DB manager</b>!<br><br>
        
        With DBs attached, you can practice<br>
        vocabulary in <b>Play/From DBs</b> playmode.<br><br>
        
        If you wish to learn hiragana,<br>
        use <b>Play/Hiragana</b> playmode.<br>
        No DBs needed!"""
        label = QLabel()
        label.setText(welcome_message)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_widget.layout.addWidget(label)
        self.replace_central_widget(welcome_widget)
        
    def place_menubar(self):
        menubar = self.menuBar()
        
        filemenu = menubar.addMenu("File")
        
        attach = filemenu.addAction("Attach DB")
        attach.setShortcut("Ctrl+Shift+A")
        attach.triggered.connect(self.attach_db_dialog)
        self.keine.dbs_lock.add_on_write(lambda b: attach.setDisabled(b))
        
        create = filemenu.addAction("Create a new DB")
        create.setShortcut("Ctrl+Shift+N")
        create.triggered.connect(self.create_db_dialog)
        self.keine.dbs_lock.add_on_write(lambda b: create.setDisabled(b))

        disconnect = filemenu.addAction("Disconnect all DBs")
        disconnect.triggered.connect(self.disconnect_all_dbs)
        disconnect.setDisabled(True)
        def disconnect_disable_func(*_):
            disconnect.setDisabled(not self.keine.dbs or self.keine.dbs_lock.value)

        self.keine.on_dbs_changed += disconnect_disable_func
        self.keine.dbs_lock.add_on_write(disconnect_disable_func)
        
        filemenu.addSeparator()
        open_db_manager = filemenu.addAction("DB manager")
        open_db_manager.triggered.connect(lambda: self.replace_central_widget(DBManager(self)))
        self.keine.dbs_lock.add_on_write(lambda b: open_db_manager.setDisabled(b))
        
        filemenu.addSeparator()
        quit = filemenu.addAction("Quit")
        quit.triggered.connect(self.close)
        quit.setShortcut("Ctrl+Q")

        self.learnmenu = menubar.addMenu("Learn")
        self.keine.dbs_lock.add_on_write(lambda b: self.learnmenu.setDisabled(b))
        
        from_dbs = self.learnmenu.addAction("From DBs")
        # from_dbs.setDisabled(True)
        # self.keine.on_dbs_changed += (lambda: from_dbs.setDisabled(not self.keine.dbs))
        from_dbs.triggered.connect(lambda: self.replace_central_widget(DBGameSetupWidget(self)))
        
        hiragana = self.learnmenu.addAction("Hiragana")
        hiragana.triggered.connect(lambda: self.replace_central_widget(HiraganaTestSetupWidget(self)))
        

    DB_FILE_FILTER = "Kamishirasawa DB files (*.kamidb);;All files (*.*)"
        
    def attach_db_dialog(self):
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
            except DBParseError as e:
                raise e
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

    def create_db_dialog(self):
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

    def disconnect_all_dbs(self):
        if self.keine.dbs:
            self.keine.close_all_dbs()
            self.statusbar.showMessage(f"Disconnected all DBs.")
        else:
            self.statusbar.showMessage(f"No DBs are attached.")

    def replace_central_widget(self, widget: QWidget) -> None:
        try:
            self.centralWidget().deleteLater()
            self.centralWidget().setParent(None)
        except:
            pass
        self.setCentralWidget(widget)

class DBManager(QWidget):
    list_attribute_delimiters = [",", ";"]
    
    def __init__(self, parent: QMainWindow, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.keine = parent.keine
        self.selected_db = None
        self.keine.on_dbs_changed += self.update_db_selector
        self.keine.on_dbs_changed += lambda: self.db_edit_widget.setEnabled(len(self.keine.dbs) > 0)
        
        self.layout = QVBoxLayout(self)
        
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
        self.db_tsv_voc = QPushButton(text="Load from TSV")
        self.db_tsv_voc.clicked.connect(self.load_tsv)
        edit_layout.addWidget(self.db_delete_voc)        
        edit_layout.addWidget(self.db_add_voc)
        edit_layout.addWidget(self.db_tsv_voc)
        
        self.db_edit_widget.setEnabled(len(self.keine.dbs) > 0)
        
        self.layout.addWidget(self.db_edit_widget)

        self.update_db_selector()
        
    def place_db_selection_widget(self):
        self.db_selection_widget = QWidget(self)
        self.db_selection_widget.layout = QHBoxLayout(self.db_selection_widget)
        
        self.db_combobox = QComboBox(self.db_selection_widget)
        self.db_combobox.currentIndexChanged.connect(self.on_selected_db_changed)
        
        self.db_selection_widget.attach_button = QPushButton(icon=QIcon("./icons/attach.png"))
        self.db_selection_widget.attach_button.setFixedSize(32, 32)
        self.db_selection_widget.attach_button.clicked.connect(self.parent.attach_db_dialog)
        self.db_selection_widget.create_button = QPushButton(icon=QIcon("./icons/create.png"))
        self.db_selection_widget.create_button.setFixedSize(32, 32)
        self.db_selection_widget.create_button.clicked.connect(self.parent.create_db_dialog)
        self.db_selection_widget.detach_button = QPushButton(icon=QIcon("./icons/detach.png"))
        self.db_selection_widget.detach_button.setFixedSize(32, 32)
        self.db_selection_widget.detach_button.clicked.connect(lambda: self.keine.detach_db(self.db_combobox.currentData()))
        
        self.db_selection_widget.layout.addWidget(self.db_combobox, 1)
        self.db_selection_widget.layout.addWidget(self.db_selection_widget.attach_button, 0)
        self.db_selection_widget.layout.addWidget(self.db_selection_widget.create_button, 0)
        self.db_selection_widget.layout.addWidget(self.db_selection_widget.detach_button, 0)
        self.layout.addWidget(self.db_selection_widget)
        
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
        self.layout.addWidget(self.save_changes_widget)
        
        self.keine.dbs_lock.add_on_write(lambda b: self.save_changes_widget.setDisabled(not b))
        self.save_changes_widget.setDisabled(True)
        
    def place_table(self):
        self.voc_table = QTableWidget()
        self.voc_table.setColumnCount(3)
        self.voc_table.itemClicked.connect(self.on_item_selected)
        self.voc_table.itemChanged.connect(self.on_item_changed)

        self.layout.addWidget(self.voc_table)
        
    def update_db_selector(self):
        last_db = self.db_combobox.currentData()
        self.db_combobox.clear()
        
        selection_layout = self.db_selection_widget.layout
        
        match list(self.keine.dbs):
            case []:
                for child in (selection_layout.itemAt(i).widget() for i in range(selection_layout.count())):
                    child.setDisabled(child not in {self.db_selection_widget.attach_button, self.db_selection_widget.create_button})
                    
            case [db]:
                self.db_combobox.addItem(os.path.basename(db.path), db)
                for child in (selection_layout.itemAt(i).widget() for i in range(selection_layout.count())):
                    child.setDisabled(False)
                self.db_combobox.setCurrentIndex(0)

            case dbs:
                commonpath_length = len(os.path.commonpath([db.path for db in dbs]))
                current_index = 0
                for i, db in enumerate(dbs):
                    self.db_combobox.addItem(db.path[commonpath_length + 1:], db)
                    if db == last_db:
                        current_index = i
                        
                self.db_combobox.setCurrentIndex(current_index)
                for child in (selection_layout.itemAt(i).widget() for i in range(selection_layout.count())):
                    child.setDisabled(False)
        
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

    def load_tsv(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Attach DB",
            os.path.dirname(__file__),
            "TSV files (*.tsv);;CSV files(*.csv);;All files (*.*)")
        if path:
            try:
                with open(path, 'rt') as file:
                    items = list(csv.reader(file, delimiter='\t'))
                    self.voc_table.model().blockSignals(True)
                    count = self.voc_table.rowCount()
                    self.voc_table.setRowCount(count + len(items))
                    delim = self.list_attribute_delimiters[0]
                    for row, (word, meanings, cats) in enumerate(items):
                        self.set_voc(row + count, Voc(
                            word,
                            utils.multi_split(meanings, delim),
                            utils.multi_split(cats, delim)
                        ))
                    self.voc_table.model().blockSignals(False)
                    self.voc_table.model().layoutChanged.emit()

                    self.keine.dbs_lock.value = True
                    self.save_changes_widget.setEnabled(True)
                self.parent.statusbar.showMessage("File loaded")

            except:
                self.parent.statusbar.showMessage("Failed to load file")

    def on_item_selected(self, item: QTableWidgetItem):
        # print(f"Selected '{item.text()}'({item.row()}, {item.column()})")
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
            # print(word, meaning, categories)
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
                    self.layout().addWidget(QLabel(text=text))
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
        def __init__(self, text: str, widget: QWidget) -> None:
            super().__init__()
            self.text = text
            self.widget = widget
            
        def run(self) -> None:
            tts(self.text)
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
        QThreadPool.globalInstance().start(self.TTSRunnable(text=self.text_supplier(), widget=self))
    

class FlashcardGameWidget(QAbstractWidget):
    class State(Enum):
        READING_ANSWER = auto()
        GIVING_FEEDBACK = auto()
        
    class DisplayMode(Enum):
        ORIGINAL = auto()
        FURIGANA = auto()
        ROMAJI = auto()
    
    def __init__(self, parent: QWidget, game: FlashcardGame, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        
        self.parent = parent
        self.game = game
        self.state = self.State.READING_ANSWER
        self.display_mode_changed = utils.Event()
        
        self.display_settings = QButtonGroup()
        r1 = QRadioButton(text="Kanji/Kana")
        r1.setChecked(True)
        r1.toggled.connect(lambda: self.display_mode_changed(self.DisplayMode.ORIGINAL))
        r2 = QRadioButton(text="Furigana")
        r2.toggled.connect(lambda: self.display_mode_changed(self.DisplayMode.FURIGANA))
        r3 = QRadioButton(text="Romaji")
        r3.toggled.connect(lambda: self.display_mode_changed(self.DisplayMode.ROMAJI))
        self.display_settings.addButton(r1)
        self.display_settings.addButton(r2)
        self.display_settings.addButton(r3)
        
        def update_kanjikana_label(display_mode: self.DisplayMode):
            match display_mode:
                case self.DisplayMode.ORIGINAL:
                    self.question_label.setMode(KanjiKanaLabel.Mode.ORIGINAL)
                    
                case self.DisplayMode.FURIGANA:
                    self.question_label.setMode(KanjiKanaLabel.Mode.FURIGANA)
                    
                case self.DisplayMode.ROMAJI:
                    self.question_label.setMode(KanjiKanaLabel.Mode.ROMAJI)
        self.display_mode_changed += update_kanjikana_label
        
        self.question_label = KanjiKanaLabel()
        self.question_label.setText(game.question)
        self.tts_button = TTSButton(self.question_label.text)
        question_widget = QWidget()
        question_widget_layout = QHBoxLayout(question_widget)
        question_widget_layout.addWidget(self.question_label)   
        question_widget_layout.addWidget(self.tts_button)
        
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(r1, alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout.addWidget(r2, alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout.addWidget(r3, alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout.addWidget(question_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.create_input_widget(), alignment=Qt.AlignmentFlag.AlignCenter)
                
    @abstractmethod
    def create_input_widget(self) -> QWidget:
        ...
                
    def on_correct_answer(self) -> None:
        self.game.mark_as_correct()
    
    def on_incorrect_answer(self) -> None:
        self.game.mark_as_incorrect()

    def on_new_question(self) -> None:
        self.question_label.setText(self.game.question)
   
    def finish(self) -> None:
        label = QLabel(f"That's all! Congrats'!\n{lang_utils.kaomoji.joy()}")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.parent.replace_central_widget(label)
    
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
                if self.game.is_done:
                    self.finish()
                
                self.state = self.State.READING_ANSWER
                
                self.answer_input.setDisabled(False)
                self.answer_input.setText("")
                self.answer_input.setFocus()
                self.feedback_label.setText("")
                self.confirm_button.setText("Check")
                
                self.on_new_question()
                  
class ChoiceFlashcardGameWidget(FlashcardGameWidget):
    def __init__(self, parent: QWidget, game: FlashcardGame, choices: int, *args, **kwargs) -> None:
        assert choices >= 2
        self.choices = choices
        
        super().__init__(parent, game, *args, **kwargs)
        
    def create_input_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.feedback_label = QLabel()
        layout.addWidget(self.feedback_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.answer_buttons = [QPushButton() for _ in range(self.choices)]
        self.answer_button_actions = []
        
        def connect(button: QPushButton, action: QAction):
            button.clicked.connect(lambda: self.give_answer(button.answer))
            if action:
                action.triggered.connect(lambda: self.give_answer(button.answer))
                
        def add_display_mode_chagned_callback(button: QPushButton):
            def update_button_text(display_mode: self.DisplayMode):
                match display_mode:
                    case self.DisplayMode.ORIGINAL:
                        button.setText(button.answer)
                        
                    case self.DisplayMode.FURIGANA:
                        text = ""
                        for orig, hira in lang_utils.furigana(button.answer):
                            text += hira if hira else orig
                            
                        button.setText(text)
                        
                    case self.DisplayMode.ROMAJI:
                        button.setText(lang_utils.to_romaji(button.answer))
                        
            self.display_mode_changed += update_button_text
        
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
            add_display_mode_chagned_callback(button)
            
        self.set_choices()
        
        return widget
        
    def set_choices(self) -> None:
        available_answers = [self.game.formatted_answer] + self.game.sample_incorrect_answers(self.choices - 1)
        random.shuffle(available_answers)
        
        for button, answer in zip(self.answer_buttons, available_answers):
            button.setText(answer)   
            button.answer = answer          
    
    def give_answer(self, answer: str) -> None:        
        match self.state:
            case self.State.READING_ANSWER:                
                self.state = self.State.GIVING_FEEDBACK
                
                for button in self.answer_buttons:
                    button.setDisabled(not self.game.check_answer(button.answer))
                
                if self.game.check_answer(answer):
                    self.feedback_label.setText("<b>Correct!</b>")
                    self.on_correct_answer()
                
                else:
                    self.feedback_label.setText(
                        f"<b>Wrong!</b> Should be: {self.game.formatted_answer}")
                    self.on_incorrect_answer()
                    
                    
            case self.State.GIVING_FEEDBACK:
                if self.game.is_done:
                    self.finish()
                    return
                
                self.state = self.State.READING_ANSWER
                
                for button in self.answer_buttons:
                    button.setDisabled(False)
                self.set_choices()
                    
                self.feedback_label.setText("")
                
                self.on_new_question()

class VocTestSetupWidget(QWidget):
    def __init__(self, vocs: typing.Iterable, parent: QWidget, *args, **kwargs) -> None:
        super().__init__(parent=parent, *args, **kwargs)
        self.parent = parent
        self.main_window = parent.parent
        self.layout = QFormLayout(self)
        self.vocs = vocs
        
        self.total_flashcards_label = QLabel()
        self.layout.addRow("Total flashcards:", self.total_flashcards_label)
        
        self.passes_spinbox = QSpinBox(self)
        self.passes_spinbox.setMinimum(1)
        self.layout.addRow("Correct guesses needed:", self.passes_spinbox)
        
        self.place_mode_select_widget()
        self.place_gamemode_select_widget()
        
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.play)
        self.layout.addRow(self.play_button)
        
        self.update()
        
    def update(self):
        total_flashcards = len(self.vocs)
        
        self.total_flashcards_label.setText(str(total_flashcards))
        self.play_button.setDisabled(not bool(total_flashcards))
        
    def place_mode_select_widget(self):
        mode_select = QWidget(self)
        mode_select.layout = QVBoxLayout(mode_select)
        self.layout.addRow("Mode", mode_select)
        
        ja_to_en_radio_button = QRadioButton("Question in Japanese,\nanswer in English")
        ja_to_en_radio_button.game_cls = JaToEnGame
        mode_select.layout.addWidget(ja_to_en_radio_button)
        
        en_to_ja_radio_button = QRadioButton("Question in English,\nanswer in Japanese")
        en_to_ja_radio_button.game_cls = EnToJaGame
        mode_select.layout.addWidget(en_to_ja_radio_button)
        
        register_toggled_callback = lambda rb: rb.toggled.connect(lambda: [setattr(self, "game_cls", rb.game_cls), print(self.game_cls)])
        for rb in (ja_to_en_radio_button, en_to_ja_radio_button):
            register_toggled_callback(rb)
            
        ja_to_en_radio_button.toggle()
        
    def place_gamemode_select_widget(self):
        gamemode_select = QWidget(self)
        gamemode_select.layout = QVBoxLayout(gamemode_select)
        self.layout.addRow("Gamemode", gamemode_select)
        
        choice_radio_button = QRadioButton("Choice")
        choice_radio_button.game_widget_type = ChoiceFlashcardGameWidget
        gamemode_select.layout.addWidget(choice_radio_button)
        
        text_input_radio_button = QRadioButton("Text input")
        text_input_radio_button.game_widget_type = TextInputFlashcardGameWidget
        gamemode_select.layout.addWidget(text_input_radio_button)
        
        register_toggled_callback = lambda rb: rb.toggled.connect(lambda: self.on_gamemode_selected(rb.game_widget_type))
        for rb in (choice_radio_button, text_input_radio_button):
            register_toggled_callback(rb)
        
        self.choices_spinbox = QSpinBox()
        self.choices_spinbox.setMinimum(2)
        self.choices_spinbox.setMaximum(10)
        self.choices_spinbox.label = QLabel("Choices per question", self)
        self.layout.addRow(self.choices_spinbox.label, self.choices_spinbox)
        
        choice_radio_button.setChecked(True)
        
    def on_gamemode_selected(self, game_widget_type):
        self.game_widget_type = game_widget_type
        
        # Hide gamemode-specific widgets:
        self.choices_spinbox.setVisible(game_widget_type == ChoiceFlashcardGameWidget) 
        self.choices_spinbox.label.setVisible(game_widget_type == ChoiceFlashcardGameWidget)
        
    def get_game_widget(self, game: FlashcardGame) -> QWidget:
        parent = self.parent.parent
        
        if self.game_widget_type is TextInputFlashcardGameWidget:
            return TextInputFlashcardGameWidget(parent, game)
        if self.game_widget_type is ChoiceFlashcardGameWidget:
            return ChoiceFlashcardGameWidget(parent, game, choices=self.choices_spinbox.value())
    
    def play(self):
        print(self.game_cls)
        game_widget = self.get_game_widget(self.game_cls(self.vocs, passes_per_flashcard=self.passes_spinbox.value()))
        self.main_window.replace_central_widget(game_widget)

class DBGameSetupWidget(QWidget):
    
    NO_CATEGORIES = "Non categorised"
    ALL_CATEGORIES = "All"
    
    def __init__(self, parent: MainWindow, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        
        self.parent = parent
        self.layout = QVBoxLayout(self)
        self.selected_vocs = []
        
        self.place_category_select()
        self.layout.addStretch()
        self.game_setup_widget = VocTestSetupWidget(self.selected_vocs, self)
        self.layout.addWidget(self.game_setup_widget)
        
        # Update categories, when
        self.parent.keine.on_dbs_changed += self.update_categories
        self.update_categories()
        
    def update_categories(self):
        print(self.parent.keine.dbs)
        # Find the set of all categories present in attached DBs
        categories = set()
        for db in self.parent.keine.dbs:
            for voc in db.read_data():
                match voc.categories:
                    case []:
                        categories.add(self.NO_CATEGORIES)
                    case [*cats]:
                        categories |= set(cats)
                        
        # Delete all widgets from category_select but the first two ('All' checkbox and separator)
        self.category_checkboxes.clear()
        layout: QVBoxLayout = self.category_select.layout
        for widget in reversed([layout.itemAt(i).widget() for i in range(2, layout.count())]):
            widget.setParent(None)
            
        # Populate the layout
        for category in sorted(categories, key=lambda x: (x == self.NO_CATEGORIES, x)): # Ensure that NO_CATEGORIES is at the top
            checkbox = QCheckBox(text=category)
            checkbox.category = category
            layout.addWidget(checkbox)
            self.category_checkboxes.append(checkbox)
            checkbox.stateChanged.connect(lambda *_: self.on_selected_categories_changed())
            
        self.on_selected_categories_changed()
        
    def place_category_select(self):
        self.category_select = QWidget()
        self.category_select.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.layout.addWidget(self.category_select)
        self.category_select.layout = QVBoxLayout(self.category_select)
        
        self.category_checkboxes: list[QCheckBox] = []
        
        # Place ALL_CATEGORIES checkbox, functioning as 'all/some/none' checkbox
        self.all_categories_checkbox = QCheckBox(self.ALL_CATEGORIES)
        self.all_categories_checkbox.setTristate(True)
        def all_categories_checkbox_next_state():
            match self.all_categories_checkbox.checkState():
                case Qt.CheckState.Checked:
                    self.all_categories_checkbox.setCheckState(Qt.CheckState.Unchecked)
                case Qt.CheckState.Unchecked | Qt.CheckState.PartiallyChecked:
                    self.all_categories_checkbox.setCheckState(Qt.CheckState.Checked)
        self.all_categories_checkbox.nextCheckState = all_categories_checkbox_next_state
        self.all_categories_checkbox.clicked.connect(lambda b: [ch.setChecked(b) for ch in self.category_checkboxes])
        
        self.category_select.layout.addWidget(self.all_categories_checkbox)
        self.category_select.layout.addWidget(HSeparator())
        
        
    def on_selected_categories_changed(self):
        selected_categories = {ch.category for ch in self.category_checkboxes if ch.isChecked()}
        
        # Fill selected_vocs with Vocs from attached DBs belonging to at least one of the selected categories
        self.selected_vocs.clear()
        for db in self.parent.keine.dbs:
            for voc in db.read_data():
                match voc.categories:
                    case [] if self.parent.NO_CATEGORIES in selected_categories:
                        self.selected_vocs.append(voc)
                    case [*cats] if set.intersection(set(cats), selected_categories):
                        self.selected_vocs.append(voc)
        
        # Update the tristate all_categories_checkbox
        checks = [ch.isChecked() for ch in self.category_checkboxes]
        if all(checks):
            self.all_categories_checkbox.setCheckState(Qt.CheckState.Checked)
        elif any(checks):
            self.all_categories_checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
        else:
            self.all_categories_checkbox.setCheckState(Qt.CheckState.Unchecked)
            
        self.game_setup_widget.update()
                          
class HiraganaTestSetupWidget(QWidget):
    
    @property
    def minor_checkboxes(self): # all checkboxes but the 'All' chkeckbox
        return self.vowel_checkboxes + self.consonant_checkboxes
    
    def __init__(self, parent: QWidget =  None, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.vocs = set()
        
        self.layout = QVBoxLayout(self)
        
        self.place_matrix()
        
        self.game_setup_widget = VocTestSetupWidget(self.vocs, self)
        
        self.layout.addWidget(self.game_setup_widget)
        
        
    def place_matrix(self):
        self.matrix = QWidget(self)
        self.layout.addWidget(self.matrix)
        self.matrix.layout = QGridLayout(self.matrix)
        
        # Generate algorithmicly the hiragana syllables        
        vowels = ['a', 'i', 'u', 'e', 'o']
        consonants = ['', 'k', 's', 't', 'n', 'h', 'm', 'y', 'r', 'w']
        
        excluded = {"yi", "ye", "wi", "wu", "we"}
        exception_dict = {
            "si": "shi",
            "hu": "fu",
            "ti": "chi",
            "tu": "tsu",
        }
        
        alignment = Qt.AlignmentFlag.AlignCenter
        
        # Place the 'all/some/none' checkbox in the corner
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
        
        # Place consonant checkbox row
        for row, vowel in enumerate(vowels, start=1):
            checkbox = QCheckBox()
            checkbox.row = row
            self.vowel_checkboxes.append(checkbox)
            self.matrix.layout.addWidget(checkbox, row, 0, alignment)
        
        # Place vowel checkbox column   
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
            
        # Populate the matrix
        for (row, vowel), (column, consonant) in itertools.product(enumerate(vowels, start=1), enumerate(consonants, start=1)):          
            if (syllable := consonant + vowel) in excluded:
                continue
            syllable = exception_dict.get(syllable, syllable)
            self.matrix.layout.addWidget(romaji_hiragana_label(syllable), row, column, alignment)
            
        # Place 'n' consonant checkbox and label, as it is not tied to any vowel
        n_column = len(consonants) + 1
        checkbox = QCheckBox()
        checkbox.column = n_column
        self.consonant_checkboxes.append(checkbox)
        self.matrix.layout.addWidget(checkbox, 0, n_column, alignment)
        self.matrix.layout.addWidget(romaji_hiragana_label('n'), 1, n_column, alignment)
        
        # Assign callbacks
        for checkbox in self.minor_checkboxes:
            checkbox.stateChanged.connect(self.on_minor_checkbox_changed)
        
    def on_global_checkbox_changed(self):
        if self.global_checkbox.checkState() == Qt.CheckState.PartiallyChecked:
            return
        
        state = Qt.CheckState.Checked if self.global_checkbox.isChecked() else Qt.CheckState.Unchecked
        
        # Set minor checkboxes state to that of global_checkbox
        for ch in self.minor_checkboxes:
            ch.blockSignals(False)
            ch.setCheckState(state)
            ch.blockSignals(False)
        
        self.on_selection_changed()
    
    def on_minor_checkbox_changed(self):
        self.global_checkbox.blockSignals(True) # stop 'on_global_checkbox_changed' from firing
        
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
        # Select syllables from layout depending on selected checkboxes
        rows = [ch.row for ch in self.vowel_checkboxes if ch.isChecked()]
        columns = [ch.column for ch in self.consonant_checkboxes[:-1] if ch.isChecked()]
        
        self.vocs.clear()
        for row, column in itertools.product(rows, columns):
            try:
                label = self.matrix.layout.itemAtPosition(row, column).widget()
                self.vocs.add(Voc(label.hiragana, [label.romaji], []))
            except:
                pass
        # Add 'n' syllable, not affected by vowel selection
        if self.consonant_checkboxes[-1].isChecked():
                self.vocs.add(Voc(lang_utils.to_hiragana("n"), ["n"], []))
            
        self.game_setup_widget.update()
                       