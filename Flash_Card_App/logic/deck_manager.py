class DeckManager:

    def __init__(self, json_repo):
        self.repo = json_repo

    def get_decks(self):
        return self.repo.get_decks()

    def create_deck(self, name):

        deck = {
            "id": self.repo.next_deck_id(),
            "name": name,
            "cards": []
        }

        self.repo.add_deck(deck)

        return deck

    def get_deck(self, deck_id):
        return self.repo.get_deck(deck_id)

    def card_count(self, deck):
        return len(deck.get("cards", []))