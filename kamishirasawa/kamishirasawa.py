import json
import os
from dataclasses import dataclass
from typing import Iterable, Set

from utils import Event, ObservableFlag


@dataclass
class Voc:
    # A voc is a piece of vocabulary, described as a word in Japanese
    # combined with a list of meaning and assigned to none, one or more categories
    
    word: str
    meaning: list[str]
    categories: list[str]
    
    def __post_init__(self):
        self.meaning = list({s.casefold().strip() for s in self.meaning})
        self.categories = list({s.upper().strip() for s in self.categories})
    
    @classmethod
    def get_from_json(cls, path: str) -> list:        
        with open(path, "r") as file:
            return json.load(file, object_hook=lambda kwargs: cls(**kwargs))
        
    def __hash__(self) -> int:
        return hash(self.word)


class DBParseError(Exception):
    pass

class DBAlreadyAttachedError(Exception):
    pass

class DBFileError(Exception):
    pass

class DB:
    # DB represents a file containing vocs, structured as JSON
    def __init__(self, path) -> None:
        try:
            self.file = open(path, 'a+')
            self.path = os.path.normpath(path)
            
        except AttributeError as e:
            self.close()
            raise DBParseError(" .".join(e.args))
        
    def read_data(self) -> Iterable[Voc]:
        self.file.seek(0)
        return json.load(self.file, object_hook=lambda kwargs: Voc(**kwargs))
    
    # Truncates the file and writes given vocs
    def clear_and_write_data(self, data: Iterable[Voc]) -> None:
        self.file.truncate(0)
        json.dump([d.__dict__ for d in data], self.file, indent=4)
        
    def close(self):
        self.file.close()
        

class Kamishirasawa:
    """A main runtime object handling DB operations"""
    def __init__(self) -> None:
        self.dbs: Set[DB] = set()
        
        self.on_dbs_changed = Event()
        
        self.dbs_lock = ObservableFlag(False)
        
    def attach_db(self, path) -> None:
        if os.path.normpath(path) in {db.path for db in self.dbs}:
            raise DBAlreadyAttachedError("DB is already attached.")
        
        db = DB(path)
        try:
            db.read_data()
            
            self.dbs.add(db)
            self.on_dbs_changed()
        except Exception as e:
            db.close()
            raise DBParseError(*e.args)

    def create_db(self, path: str):
        try:
            db = DB(path)
            db.clear_and_write_data([])
            self.dbs.add(db)
            self.on_dbs_changed()
        except Exception as e:
            db.close()
            raise DBFileError(*e.args)

    def detach_db(self, db: DB) -> None:
        db.close()
        self.dbs.remove(db)
        self.on_dbs_changed()
        
    def close_all_dbs(self) -> None:
        for db in self.dbs:
            db.close()
        self.dbs.clear()
        self.on_dbs_changed()
