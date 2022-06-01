from abc import ABC, abstractmethod, abstractproperty
from collections import defaultdict
from copy import copy
from dataclasses import dataclass
import json
import os
import random
from typing import Any, Iterable

@dataclass
class Voc:
    word: str
    meaning: list[str]
    grade: int | None
    categories: list[str]
    
    def __post_init__(self) -> None:
        self.grade = int(self.grade) if self.grade else None
    
    @classmethod
    def get_from_json(cls, path: str) -> list:        
        with open(path, "r") as file:
            return json.load(file, object_hook=lambda kwargs: cls(**kwargs))
        
    def __hash__(self) -> int:
        return hash(self.word)


class FlashcardGame(ABC):
    def __init__(self, flashcards: Iterable[Any], passes_per_flashcard: int, active_count: int) -> None:
        assert any(flashcards)
        assert passes_per_flashcard >= 1
        assert active_count >= 1

        flashcards = list(copy(flashcards))
        random.shuffle(flashcards)
        self.active, self.queued = flashcards[:active_count], flashcards[active_count:]
        
        self.passes_left_dict = defaultdict(lambda: passes_per_flashcard)
    
    @abstractmethod
    def check_answer(self, answer: str) -> bool:
        ...
    
    def mark_as_correct(self) -> None:
        self.passes_left_dict[self._current] -= 1
        
        if self.passes_left_dict[self._current]:
            flashcard = self.active.pop(0)
            
            length = len(self.active)
            index = random.randint(length // 2, length)
            self.active.insert(index, flashcard)
        
        else:
            self.active[0] = self.queued.pop()
            
    def mark_as_incorrect(self) -> None:
        flashcard = self.active.pop(0)
        
        length = len(self.active)
        index = random.randint(min(1, length), length // 2)
        self.active.insert(index, flashcard)
    
    @property
    def is_done(self) -> bool:
        return any(self.active)
    
    @property
    def _current(self) -> Voc:
        return self.active[0]
    
    @property
    @abstractproperty
    def question(self) -> str:
        ...
    
    @property
    @abstractproperty
    def answer(self) -> str:
        ...


class JaToEnGame(FlashcardGame):
    def check_answer(self, answer: str) -> bool:
        return answer in self._current.meaning
    
    @property
    def question(self) -> str:
        return self._current.word
    
    @property
    def answer(self) -> str:
        return ", ".join(self._current.meaning)