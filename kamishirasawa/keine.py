import json
import os


from games import Voc
from utils import Event

class Keine:
    def __init__(self) -> None:
        self.dbs: set[Voc] = set()
        
        self.on_dbs_changed = Event()
        
    def attach_db(self, path) -> None:
        if os.path.normpath(path) in {db.path for db in self.dbs}:
            raise DBAlreadyAttachedError("DB is already attached.")
        
        db = DB(path)
        self.dbs.add(db)
        self.on_dbs_changed()
        
    def detach_db(self, db) -> None:
        self.dbs.remove(db)
        self.on_dbs_changed()
        
    def close_all_dbs(self) -> None:
        for db in self.dbs:
            db.close()
        self.dbs.clear()
        self.on_dbs_changed()

class DBParseError(Exception):
    pass

class DBAlreadyAttachedError(Exception):
    pass

class DB:
    def __init__(self, path) -> None:
        try:
            self.file = open(path, 'r+')
            self.path = os.path.normpath(path)
            self.vocs: set[Voc] = json.load(self.file, object_hook=lambda kwargs: Voc(**kwargs))
            
        except AttributeError as e:
            self.close()
            raise DBParseError(" .".join(e.args))
        
    def close(self):
        self.file.close()