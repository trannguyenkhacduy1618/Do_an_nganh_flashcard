import tkinter as tk
from ui.main_window import MainWindow
from data.json_repository import JsonRepository
from data.database import Database
from logic.deck_manager import DeckManager
from logic.card_manager import CardManager


def main():
    DB_FILE = "anki_app.db"
    json_repo = JsonRepository("decks")
    database = Database(DB_FILE)
    database.initialize()

    deck_manager = DeckManager(json_repo)
    card_manager = CardManager(json_repo, database)

    root = tk.Tk()
    root.title("User 1 - Anki")
    root.geometry("820x760")
    root.minsize(300, 500)


    app = MainWindow(root, deck_manager, card_manager, database)
    root.mainloop()

if __name__ == "__main__":
    main()
