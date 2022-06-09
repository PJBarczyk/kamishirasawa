import json
import os
from typing import Iterable

from games import Voc
from utils import Event, ObservableFlag


class DBParseError(Exception):
    pass

class DBAlreadyAttachedError(Exception):
    pass

class DBFileError(Exception):
    pass

class DB:
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
    
    def clear_and_write_data(self, data: Iterable[Voc]) -> None:
        self.file.truncate(0)
        json.dump([d.__dict__ for d in data], self.file, indent=4)
        
    def close(self):
        self.file.close()
        

class Keine:
    def __init__(self) -> None:
        self.dbs: set[Voc] = set()
        
        self.on_dbs_changed = Event()
        
        self.dbs_lock = ObservableFlag(False)
        # self.dbs_lock.add_on_write(lambda b: print(f"DBs lock {'on' if b else 'off'}."))
        
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
        try:
            self.on_dbs_changed()
        except SystemError:
            pass