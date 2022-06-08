from abc import ABC, abstractmethod, abstractproperty
from collections import defaultdict
from copy import copy
from dataclasses import dataclass
import json
import math
import os
import random
from typing import Any, Iterable, Sequence

@dataclass
class Voc:
    word: str
    meaning: list[str]
    categories: list[str]
    
    @classmethod
    def get_from_json(cls, path: str) -> list:        
        with open(path, "r") as file:
            return json.load(file, object_hook=lambda kwargs: cls(**kwargs))
        
    def __hash__(self) -> int:
        return hash(self.word)


class FlashcardGame(ABC):    
    def __init__(self, flashcards: Iterable[Any], passes_per_flashcard: int) -> None:
        assert any(flashcards)
        assert passes_per_flashcard >= 1

        self.active, self.passed = list(flashcards), []
        random.shuffle(self.active)
        
        self.total_count = len(self.active)
        self.passes_per_flashcard = passes_per_flashcard
        
        self.passes_done_dict = defaultdict(lambda: 0)
    
    @abstractmethod
    def check_answer(self, answer: str) -> bool:
        ...
        
    def __insert_flashcard(self, flashcard: Any, passes: int) -> None:
        assert 0 <= passes < self.passes_per_flashcard
        
        new_pos = int(max(0, len(self.active) * math.exp(passes + 1 - self.passes_per_flashcard)))
        print(f"Put flashcard with {passes}/{self.passes_per_flashcard} into place {new_pos}/{len(self.active)}.")
        self.active.insert(new_pos, flashcard)
    
    def mark_as_correct(self) -> None:
        self.passes_done_dict[self._current] = self.passes_done_dict[self._current] + 1
              
        if (passes := self.passes_done_dict[self._current]) < self.passes_per_flashcard:
            self.__insert_flashcard(self.active.pop(0), passes)            
        
        else:
            self.passed.append(self.active.pop(0))
            
    def mark_as_incorrect(self) -> None:
        self.passes_done_dict[self._current] = max(0, self.passes_done_dict[self._current] - 1)
        self.__insert_flashcard(self.active.pop(0), self.passes_done_dict[self._current])   
        
    
    @property
    def is_done(self) -> bool:
        return not self.active
    
    @property
    def _current(self) -> Voc:
        return self.active[0]
    
    @property
    @abstractproperty
    def question(self) -> str:
        ...
      
    @property
    def formatted_answer(self) -> str:
        return self._formatted_answer_of(self._current)
        
    @abstractmethod
    def _formatted_answer_of(self, flashcard: Any):
        ...
       
    def sample_incorrect_answers(self, k) -> list[str]:
        sample = random.sample(self.active[1:], min(len(self.active) - 1, k))
        
        if len(sample) < k:  # Not enough flashcards in active deck
            k_left = k - len(sample)
            sample += random.sample(self.passed, min(len(self.passed), k_left))
            
            if len(sample) < k:  # Game contains less cards than set choice count
                sample = random.choices(self.active + self.passed, k=k)

        return [self._formatted_answer_of(flashcard) for flashcard in sample]
            

class JaToEnGame(FlashcardGame):
    def check_answer(self, answer: str) -> bool:
        return answer in self._current.meaning or answer == self.formatted_answer
    
    @property
    def question(self) -> str:
        return self._current.word
    
    def _formatted_answer_of(self, flashcard: Any):
        return ", ".join(flashcard.meaning)

class TupleFlashcardGame(FlashcardGame):
    def check_answer(self, answer: str) -> bool:
        return answer == self._current[1]

    @property
    def question(self) -> str:
        return self._current[0]
    
    def _formatted_answer_of(self, flashcard: Any):
        return flashcard[1]
        