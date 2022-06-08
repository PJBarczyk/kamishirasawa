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