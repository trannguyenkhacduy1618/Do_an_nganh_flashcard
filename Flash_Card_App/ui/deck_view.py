import tkinter as tk
from datetime import date, datetime

from ui.theme import *


class DeckView(tk.Frame):

    def __init__(
        self,
        parent,
        deck_manager,
        database,
        on_open_deck
    ):
        super().__init__(
            parent,
            bg=BG
        )

        self.deck_manager = deck_manager
        self.database = database
        self.on_open_deck = on_open_deck

        self.build_ui()
        self.load_decks()

    # =====================================================
    # UI
    # =====================================================

    def build_ui(self):

        # Center container
        self.container = tk.Frame(
            self,
            bg=BG
        )

        self.container.pack(
            fill=tk.BOTH,
            expand=True
        )

        # Keep the table centered horizontally
        self.container.grid_columnconfigure(
            0,
            weight=1
        )

        self.container.grid_columnconfigure(
            1,
            weight=0
        )

        self.container.grid_columnconfigure(
            2,
            weight=1
        )

        self.card = tk.Frame(
            self.container,
            bg=WHITE,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        self.card.grid(
            row=0,
            column=1,
            sticky="n",
            pady=55
        )

        # Header
        header = tk.Frame(
            self.card,
            bg=WHITE
        )

        header.pack(
            fill=tk.X,
            padx=18,
            pady=(18, 8)
        )

        columns = [
            ("Deck", 35),
            ("New", 9),
            ("Learn", 13),
            ("Due", 9)
        ]

        for text, width in columns:

            tk.Label(
                header,
                text=text,
                bg=WHITE,
                fg=TEXT,
                font=("Segoe UI", 11, "bold"),
                width=width,
                anchor="w" if text == "Deck" else "center"
            ).pack(
                side=tk.LEFT
            )

        tk.Frame(
            self.card,
            bg=BORDER,
            height=1
        ).pack(
            fill=tk.X,
            padx=18
        )

    # =====================================================
    # Load decks
    # =====================================================

    def load_decks(self):

        # Remove old rows
        for widget in self.card.winfo_children():

            if widget != self.card.winfo_children()[0]:
                widget.destroy()

        decks = self.deck_manager.get_decks()

        for deck in decks:

            self._add_deck_row(
                self.card,
                deck
            )

    # =====================================================
    # Calculate deck statistics
    # =====================================================

    def get_deck_stats(self, deck):

        progress = self.database.get_all_progress()

        new_count = 0
        learning_count = 0
        due_count = 0

        today = date.today()

        for card in deck.get("cards", []):

            question = card.get(
                "question",
                ""
            )

            card_progress = progress.get(
                question
            )

            # No review record / no review date
            if not card_progress:
                new_count += 1
                continue

            review_date = card_progress.get(
                "day_to_review"
            )

            # Never reviewed
            if not review_date:
                new_count += 1
                continue

            try:

                review_day = datetime.strptime(
                    review_date,
                    "%Y-%m-%d"
                ).date()

            except ValueError:

                # Invalid date -> treat as new
                new_count += 1
                continue

            # Due today or overdue
            if review_day <= today:
                due_count += 1

            # Future review date
            else:
                learning_count += 1

        return (
            new_count,
            learning_count,
            due_count
        )

    # =====================================================
    # Add deck row
    # =====================================================

    def _add_deck_row(
        self,
        parent,
        deck
    ):

        row = tk.Frame(
            parent,
            bg=WHITE,
            height=40
        )

        row.pack(
            fill=tk.X,
            padx=18,
            pady=2
        )

        row.pack_propagate(
            False
        )

        # -----------------------------
        # Deck name
        # -----------------------------

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

        name.pack(
            side=tk.LEFT
        )

        # -----------------------------
        # Statistics
        # -----------------------------

        new_count, learning_count, due_count = (
            self.get_deck_stats(deck)
        )

        values = [
            new_count,
            learning_count,
            due_count
        ]

        for value in values:

            tk.Label(
                row,
                text=str(value),
                bg=WHITE,
                fg="#999999",
                font=("Segoe UI", 10),
                width=15
            ).pack(
                side=tk.LEFT
            )

        # -----------------------------
        # Gear
        # -----------------------------

        gear = tk.Label(
            row,
            text="⚙",
            bg=WHITE,
            fg="#777777",
            font=("Segoe UI", 15),
            width=4,
            cursor="hand2"
        )

        gear.pack(
            side=tk.LEFT
        )

        # -----------------------------
        # Open deck
        # -----------------------------

        for widget in (
            row,
            name,
            gear
        ):

            widget.bind(
                "<Double-Button-1>",
                lambda e, d=deck:
                    self.on_open_deck(d)
            )