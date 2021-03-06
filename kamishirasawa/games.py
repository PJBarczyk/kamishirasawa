import math
import random
from abc import ABC, abstractmethod, abstractproperty
from collections import defaultdict
from typing import Any, Iterable

import lang_utils
from kamishirasawa import Voc


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
        self.active.insert(new_pos, flashcard)
    
    def mark_as_correct(self) -> None:
        self.passes_done_dict[self._current] = self.passes_done_dict[self._current] + 1
              
        
        if (passes := self.passes_done_dict[self._current]) < self.passes_per_flashcard:
            # The flashcard is not yet memorized, we put in back into the deck
            self.__insert_flashcard(self.active.pop(0), passes)            
        
        else:
            # The flashcard is memorized, we throw it onto passed pile
            self.passed.append(self.active.pop(0))
            
    def mark_as_incorrect(self) -> None:
        # As a penalty, user will have to answer one more extra time correctly
        self.passes_done_dict[self._current] = max(0, self.passes_done_dict[self._current] - 1)
        passes_done = self.passes_done_dict[self._current]
        self.__insert_flashcard(self.active.pop(0), passes_done)
        
    
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
    def answer(self) -> str:
        return self._answer_of(self._current)
        
    @abstractmethod
    def _answer_of(self, flashcard: Any):
        ...
       
    def sample_incorrect_answers(self, k) -> list[str]:
        """Returns a list of formatted, incorrect answers."""
        # First, will pick from active, then from passed
        sample = random.sample(self.active[1:], min(len(self.active) - 1, k))
        
        if len(sample) < k:  # Not enough flashcards in active deck
            k_left = k - len(sample)
            sample += random.sample(self.passed, min(len(self.passed), k_left))
            
            if len(sample) < k:  # Game contains less cards than set choice count
                sample = random.choices(self.active + self.passed, k=k)

        return [self._answer_of(flashcard) for flashcard in sample]
            

class JaToEnGame(FlashcardGame):
    """A flashcard game based on vocs, where user is given a question in Japanese
    and is required to answer in English"""
    def check_answer(self, answer: str) -> bool:
        return answer.casefold() in self._current.meaning or answer == self.answer
    
    @property
    def question(self) -> str:
        return self._current.word
    
    def _answer_of(self, flashcard: Any):
        return ", ".join(flashcard.meaning)
    
class EnToJaGame(FlashcardGame):
    """A flashcard game based on vocs, where user is given a question in English
    and is required to answer in Japanese."""
    def check_answer(self, answer: str) -> bool:
        return answer in {lang_utils.to_romaji(self._current.word), 
                          lang_utils.to_hiragana(self._current.word), 
                          self._current.word}
    
    @property
    def question(self) -> str:
        return ", ".join(self._current.meaning)
    
    def _answer_of(self, flashcard: Any):
        return flashcard.word
