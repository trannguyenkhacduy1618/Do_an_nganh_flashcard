import json
from pathlib import Path


class JsonRepository:

    def __init__(self, folder="decks"):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)

    def _get_path(self, deck_name):
        return self.folder / f"{deck_name}.json"

    def _read_file(self, path):
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return None

    def _write_file(self, path, data):
        with path.open("w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=4
            )

    def get_decks(self):
        decks = []

        for path in self.folder.glob("*.json"):
            data = self._read_file(path)

            if data:
                decks.append(data)

        return decks

    def get_deck(self, deck_id):
        for deck in self.get_decks():
            if deck["id"] == deck_id:
                return deck

        return None

    def get_deck_by_name(self, name):
        path = self._get_path(name)

        if not path.exists():
            return None

        return self._read_file(path)

    def add_deck(self, deck):
        path = self._get_path(deck["name"])

        self._write_file(path, deck)

    def update_deck(self, deck):
        path = self._get_path(deck["name"])

        self._write_file(path, deck)

    def next_deck_id(self):
        decks = self.get_decks()

        ids = [
            deck["id"]
            for deck in decks
            if "id" in deck
        ]

        return max(ids, default=0) + 1

    def next_card_id(self, deck):
        ids = [
            card["id"]
            for card in deck.get("cards", [])
        ]

        return max(ids, default=0) + 1
    def delete_deck(self, deck_name):

        path = self._get_path(deck_name)

        if path.exists():
            path.unlink()
    def rename_deck(self, old_name, new_name):

        # Same name, do nothing
        if old_name == new_name:
            return True


        old_path = self._get_path(old_name)
        new_path = self._get_path(new_name)


        if not old_path.exists():
            return False


        data = self._read_file(
            old_path
        )

        data["name"] = new_name


        self._write_file(
            new_path,
            data
        )


        old_path.unlink()

        return True
    def deck_exists(self, name):

        path = self._get_path(name)

        return path.exists()