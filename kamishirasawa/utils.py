from typing import Any, Callable, Iterable

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
        for arg in args:
            if isinstance(arg, Callable):
                print("Ivoked error with Callable as a parameter. Didn't you mean to use the '+=' operator?")
                break
        for callable in self.__callables:
            try:
                callable(*args, **kwargs)
            except RuntimeError:
                pass
            
class ObservableFlag:
    def __init__(self, value=None) -> None:
        self.__value = value
        self.__on_write_callables = set[Callable[[bool], Any]]()
    
    @property
    def value(self):
        return self.__value
    
    @value.setter
    def value(self, value):
        self.set_value(value)
            
    def set_value(self, value):
        self.__value = value
        for callable in self.__on_write_callables:
            callable(value)
            
    def add_on_write(self, callable: Callable[[bool], Any]):
        self.__on_write_callables.add(callable)
            
    def remove_on_write(self, callable: Callable[[bool], Any]):
        self.__on_write_callables.remove(callable)

    def __bool__(self):
        return self.__value
    
    
def multi_split(s: str, seps: Iterable[str]):
    list_of_splits = [s]
    for sep in seps:
        list_of_splits = [s for ss in list_of_splits for s in ss.split(sep)]
    return list_of_splits