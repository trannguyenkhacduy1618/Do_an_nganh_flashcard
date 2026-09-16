import random

from flashcards import FLASHCARDS
from logic.session import SessionState


class FlashcardManager:
    def __init__(self):
        self.original_cards = FLASHCARDS.copy()
        self.state = SessionState()
        self.reset_session()

    def reset_session(self):
        self.state.cards = self.original_cards.copy()
        random.shuffle(self.state.cards)
        self.state.current_card = None
        self.state.answer_visible = False

    def get_current_card(self):
        if not self.state.cards:
            return None
        self.state.current_card = self.state.cards[0]
        self.state.answer_visible = False
        return self.state.current_card

    def reveal_answer(self):
        self.state.answer_visible = True
        return self.state.current_card

    def answer_current(self, difficulty):
        if self.state.current_card is None or not self.state.answer_visible:
            return False

        self.state.cards.pop(0)

        if difficulty == "again":
            position = min(2, len(self.state.cards))
            self.state.cards.insert(position, self.state.current_card)
        elif difficulty == "hard":
            position = min(4, len(self.state.cards))
            self.state.cards.insert(position, self.state.current_card)

        self.state.current_card = None
        self.state.answer_visible = False
        return True

    def remaining_cards(self):
        return len(self.state.cards)

    def total_cards(self):
        return len(self.original_cards)

    def completed_cards(self):
        return self.total_cards() - self.remaining_cards()
