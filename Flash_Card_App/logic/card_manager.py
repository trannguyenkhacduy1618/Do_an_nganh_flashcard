from datetime import date, timedelta

class CardManager:
    def __init__(self, json_repo, database):
        self.repo = json_repo
        self.db = database

    def get_cards(self, deck_id):
        deck = self.repo.get_deck(deck_id)
        return deck.get("cards", []) if deck else []

    
    def add_card(self, deck_id, question, answer):
        deck = self.repo.get_deck(deck_id)

        if not deck:
            return None

        card = {
            "id": self.repo.next_card_id(deck),
            "question": question,
            "answer": answer
        }

        deck.setdefault("cards", []).append(card)

        self.repo.update_deck(deck)

        self.db.save_progress(
            card["question"],
            None,
            None
        )

        return card
    def review_card(self, card, difficulty):
        intervals = {
            1: 0,
            2: 1,
            3: 3,
            4: 7
        }

        days = intervals.get(difficulty, 1)

        review_date = (
            date.today() +
            timedelta(days=days)
        )

        self.db.save_progress(
            card["question"],
            difficulty,
            review_date.isoformat()
        )
    def delete_card(self, deck_id, card_id):
        deck = self.repo.get_deck(deck_id)

        if not deck:
            return False

        cards = deck.get("cards", [])

        new_cards = [
            card for card in cards
            if card["id"] != card_id
        ]

        if len(new_cards) == len(cards):
            return False

        deck["cards"] = new_cards

        self.repo.update_deck(deck)
    
        # Remove review data from SQLite
        self.db.delete_progress(card_id)

        return True
