import tkinter as tk
from ui.theme import *

class DeckView(tk.Frame):
    def __init__(self, parent, deck_manager, on_open_deck):
        super().__init__(parent, bg=BG)
        self.deck_manager = deck_manager
        self.on_open_deck = on_open_deck

        card = tk.Frame(
            self,
            bg=WHITE,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        card.pack(fill=tk.X, pady=55)

        header = tk.Frame(card, bg=WHITE)
        header.pack(fill=tk.X, padx=18, pady=(18, 8))

        for text, width in [
            ("Deck", 35), ("New", 9), ("Learn", 13), ("Due", 9)
        ]:
            tk.Label(
                header,
                text=text,
                bg=WHITE,
                fg=TEXT,
                font=("Segoe UI", 11, "bold"),
                width=width,
                anchor="w" if text == "Deck" else "center"
            ).pack(side=tk.LEFT)

        tk.Frame(card, bg=BORDER, height=1).pack(
            fill=tk.X, padx=18
        )

        for deck in self.deck_manager.get_decks():
            self._add_deck_row(card, deck)

    def _add_deck_row(self, parent, deck):
        row = tk.Frame(parent, bg=WHITE, height=40)
        row.pack(fill=tk.X, padx=18, pady=2)
        row.pack_propagate(False)

        name = tk.Label(
            row,
            text=deck["name"],
            bg=WHITE,
            fg=BLUE,
            font=("Segoe UI", 11),
            width=35,
            anchor="w",
            cursor="hand2"
        )
        name.pack(side=tk.LEFT)

        cards = deck.get("cards", [])
        values = [0, 0, len(cards)]

        for value in values:
            tk.Label(
                row,
                text=str(value),
                bg=WHITE,
                fg="#999999",
                font=("Segoe UI", 10),
                width=15
            ).pack(side=tk.LEFT)

        gear = tk.Label(
            row,
            text="⚙",
            bg=WHITE,
            fg="#777777",
            font=("Segoe UI", 15),
            width=4,
            cursor="hand2"
        )
        gear.pack(side=tk.LEFT)

        for widget in (row, name, gear):
            widget.bind(
                "<Double-Button-1>",
                lambda e, d=deck: self.on_open_deck(d)
            )
