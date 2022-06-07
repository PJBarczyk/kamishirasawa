from typing import Callable


class Event:
    def __init__(self) -> None:
        self.__callables = set[Callable]()
    
    def __iadd__(self, callable: Callable):
        self.__callables.add(callable)
        return self
        
    def __isub__(self, callable: Callable):
        self.__callables.remove(callable)
        return self
        
    def __call__(self, *args, **kwargs):
        for callable in self.__callables:
            callable(*args, **kwargs)
            

class Keine:
    def __init__(self) -> None:
        self.dbs = set()
        
        self.on_dbs_changed = Event()
        
    def add_db(self, path) -> None:
        db = DB(path)
        self.dbs.add(db)
        self.on_dbs_changed()
        
    def close_all_dbs(self) -> None:
        for db in self.dbs:
            db.close()

class DB:
    def __init__(self, path) -> None:
        self.file = open(path, 'r+')
        self.path = path
        
    def close(self):
        self.file.close()