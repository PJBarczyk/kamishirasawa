from typing import Any, Callable

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
