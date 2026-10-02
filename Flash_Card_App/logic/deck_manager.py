class DeckManager:

    def __init__(self, json_repo):
        self.repo = json_repo

    def get_decks(self):
        return self.repo.get_decks()

    def create_deck(self, name):

        # Prevent duplicate deck name
        if self.repo.deck_exists(name):
            return None


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
    def delete_deck(self, deck_name):

        self.repo.delete_deck(
            deck_name
        )
    def rename_deck(self, old_name, new_name):

        # Same name is valid
        if old_name == new_name:
            return True


        # New name already exists
        if self.repo.deck_exists(new_name):
            return False


        return self.repo.rename_deck(
            old_name,
            new_name
        )