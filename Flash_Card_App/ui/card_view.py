import tkinter as tk
from tkinter import ttk

from ui.theme import *


class CardView(tk.Frame):

    def __init__(
        self,
        parent,
        deck_manager,
        database
    ):
        super().__init__(
            parent,
            bg=BG
        )

        self.deck_manager = deck_manager
        self.database = database

        # All cards loaded from JSON
        self.all_cards = []

        # Currently selected card
        self.selected_card = None

        self.build_ui()
        self.load_cards()

    # =========================================================
    # UI
    # =========================================================

    def build_ui(self):

        # -----------------------------------------------------
        # Main container
        # -----------------------------------------------------

        main = tk.Frame(
            self,
            bg=BG
        )

        main.pack(
            fill=tk.BOTH,
            expand=True
        )
        style = ttk.Style()
        

        # IMPORTANT:
        # Use grid instead of pack so the three panels have
        # controlled/fixed widths.

        main.grid_columnconfigure(
            0,
            minsize=180,
            weight=0
        )

        main.grid_columnconfigure(
            1,
            minsize=350,
            weight=1
        )

        main.grid_columnconfigure(
            2,
            minsize=300,
            weight=0
        )

        main.grid_rowconfigure(
            0,
            weight=1,
            minsize=50
        )

        # =====================================================
        # LEFT PANEL
        # Fixed width
        # =====================================================

        self.left_panel = tk.Frame(
            main,
            bg=WHITE,
            width=180,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        self.left_panel.grid(
            row=0,
            column=0,
            sticky="ns"
        )

        # Prevent children from changing panel width
        self.left_panel.grid_propagate(False)

        # -----------------------------------------------------
        # Filter title
        # -----------------------------------------------------

        tk.Label(
            self.left_panel,
            text="Filter",
            bg=WHITE,
            fg=TEXT,
            font=("Segoe UI", 15, "bold")
        ).pack(
            anchor="w",
            padx=15,
            pady=(20, 10)
        )

        # =====================================================
        # Deck filter
        # =====================================================

        tk.Label(
            self.left_panel,
            text="Deck",
            bg=WHITE,
            fg=SECONDARY,
            font=("Segoe UI", 12)
        ).pack(
            anchor="w",
            padx=15,
            pady=(5, 3)
        )

        self.deck_var = tk.StringVar()

        self.deck_filter = ttk.Combobox(
            self.left_panel,
            textvariable=self.deck_var,
            state="readonly"
        )

        self.deck_filter.pack(
            padx=15,
            fill=tk.X
        )

        self.deck_filter.bind(
            "<<ComboboxSelected>>",
            self.on_filter_changed
        )

        # =====================================================
        # Second filter
        # Leave unnamed
        # =====================================================

        self.filter_var = tk.StringVar()

        self.filter_menu = ttk.Combobox(
            self.left_panel,
            textvariable=self.filter_var,
            state="readonly"
        )

        self.filter_menu.pack(
            padx=15,
            pady=(10, 0),
            fill=tk.X
        )

        self.filter_menu["values"] = [
            "",
            ""
        ]

        # =====================================================
        # MIDDLE PANEL
        # Flexible width
        # =====================================================

        self.middle_panel = tk.Frame(
            main,
            bg=WHITE,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        self.middle_panel.grid(
            row=0,
            column=1,
            sticky="nsew"
        )

        # -----------------------------------------------------
        # Card list
        # -----------------------------------------------------

        columns = (
            "card_name",
            "due",
            "deck"
        )

        self.card_tree = ttk.Treeview(
            self.middle_panel,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        # -----------------------------------------------------
        # CARD NAME
        # -----------------------------------------------------

        self.card_tree.heading(
            "card_name",
            text="CARD NAME"
        )

        self.card_tree.column(
            "card_name",
            width=180,
            minwidth=140,
            stretch=True,
            anchor="w"
        )

        # -----------------------------------------------------
        # DUE
        # -----------------------------------------------------

        self.card_tree.heading(
            "due",
            text="DUE"
        )

        self.card_tree.column(
            "due",
            width=110,
            minwidth=100,
            stretch=False,
            anchor="center"
        )

        # -----------------------------------------------------
        # DECK
        # -----------------------------------------------------

        self.card_tree.heading(
            "deck",
            text="DECK"
        )

        self.card_tree.column(
            "deck",
            width=130,
            minwidth=100,
            stretch=True,
            anchor="center"
        )

        # -----------------------------------------------------
        # Scrollbar
        # -----------------------------------------------------

        self.card_tree.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True
        )

        scrollbar = ttk.Scrollbar(
            self.middle_panel,
            orient=tk.VERTICAL,
            command=self.card_tree.yview
        )

        scrollbar.pack(
            side=tk.RIGHT,
            fill=tk.Y
        )

        self.card_tree.configure(
            yscrollcommand=scrollbar.set
        )

        self.card_tree.bind(
            "<<TreeviewSelect>>",
            self.on_card_selected
        )

        # =====================================================
        # RIGHT PANEL
        # Fixed width
        # =====================================================

        self.right_panel = tk.Frame(
            main,
            bg=WHITE,
            width=300,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        self.right_panel.grid(
            row=0,
            column=2,
            sticky="ns"
        )

        # Prevent word/definition from changing panel width
        self.right_panel.grid_propagate(False)

        # =====================================================
        # WORD
        # =====================================================

        tk.Label(
            self.right_panel,
            text="Word",
            bg=WHITE,
            fg=SECONDARY,
            font=("Segoe UI", 12)
        ).pack(
            anchor="w",
            padx=20,
            pady=(25, 5)
        )

        self.word_label = tk.Label(
            self.right_panel,
            text="",
            bg=WHITE,
            fg=TEXT,
            font=("Segoe UI", 18, "bold"),

            # Fixed width wrapping
            width=28,

            wraplength=250,
            justify="left",
            anchor="nw"
        )

        self.word_label.pack(
            anchor="nw",
            padx=20,
            pady=(0, 25)
        )

        # =====================================================
        # Separator
        # =====================================================

        tk.Frame(
            self.right_panel,
            bg=BORDER,
            height=1
        ).pack(
            fill=tk.X,
            padx=20
        )

        # =====================================================
        # DEFINITION
        # =====================================================

        tk.Label(
            self.right_panel,
            text="Definition",
            bg=WHITE,
            fg=SECONDARY,
            font=("Segoe UI", 15, "bold")
        ).pack(
            anchor="w",
            padx=20,
            pady=(25, 5)
        )

        self.definition_label = tk.Label(
            self.right_panel,
            text="",
            bg=WHITE,
            fg=TEXT,
            font=("Segoe UI", 12),

            # Fixed width
            width=32,

            wraplength=250,
            justify="left",
            anchor="nw"
        )

        self.definition_label.pack(
            anchor="nw",
            padx=20
        )

    # =========================================================
    # LOAD CARDS
    # =========================================================

    def load_cards(self):

        self.all_cards.clear()

        # ---------------------------------------------
        # Review information comes from SQLite
        # ---------------------------------------------

        progress = self.database.get_all_progress()

        # ---------------------------------------------
        # Card information comes from JSON
        # ---------------------------------------------

        decks = self.deck_manager.get_decks()

        deck_names = []

        for deck in decks:

            deck_name = deck["name"]

            deck_names.append(
                deck_name
            )

            for card in deck.get("cards", []):

                card_progress = progress.get(
                    card["question"],
                    {}
                )

                day_to_review = card_progress.get(
                    "day_to_review"
                )

                self.all_cards.append({
                    "id": card["id"],
                    "question": card.get("question", ""),
                    "answer": card.get("answer", ""),
                    "deck": deck_name,
                    "deck_id": deck["id"],
                    "day_to_review": day_to_review
                })

        # ---------------------------------------------
        # Update deck filter
        # ---------------------------------------------

        self.deck_filter["values"] = [
            "All Decks"
        ] + deck_names

        self.deck_var.set(
            "All Decks"
        )

        self.refresh_card_list()

    # =========================================================
    # FILTER
    # =========================================================

    def on_filter_changed(self, event=None):

        self.refresh_card_list()

    # =========================================================
    # REFRESH CARD LIST
    # =========================================================

    def refresh_card_list(self):

        # Remove existing rows

        for item in self.card_tree.get_children():

            self.card_tree.delete(
                item
            )

        selected_deck = self.deck_var.get()

        for card in self.all_cards:

            # -----------------------------------------
            # Filter by deck
            # -----------------------------------------

            if (
                selected_deck
                and selected_deck != "All Decks"
                and card["deck"] != selected_deck
            ):
                continue

            due = card.get(
                "day_to_review"
            )

            if not due:
                due = "-"

            # -----------------------------------------
            # CARD NAME instead of ID
            # -----------------------------------------

            self.card_tree.insert(
                "",
                tk.END,
                iid=self.make_tree_id(card),
                values=(
                    card["question"],
                    due,
                    card["deck"]
                )
            )

        self.clear_card_details()

    # =========================================================
    # CARD SELECTED
    # =========================================================

    def on_card_selected(self, event=None):

        selection = self.card_tree.selection()

        if not selection:
            return

        tree_id = selection[0]

        card = self.find_card_by_tree_id(
            tree_id
        )

        if not card:
            return

        self.selected_card = card

        self.show_card_details(
            card
        )

    # =========================================================
    # RIGHT PANEL
    # =========================================================

    def show_card_details(self, card):

        self.word_label.config(
            text=card["question"]
        )

        self.definition_label.config(
            text=card["answer"]
        )

    def clear_card_details(self):

        self.selected_card = None

        self.word_label.config(
            text=""
        )

        self.definition_label.config(
            text=""
        )

    # =========================================================
    # TREE ID
    # =========================================================

    def make_tree_id(self, card):

        return (
            f"{card['deck_id']}_"
            f"{card['id']}"
        )

    # =========================================================
    # FIND CARD
    # =========================================================

    def find_card_by_tree_id(self, tree_id):

        for card in self.all_cards:

            if self.make_tree_id(card) == tree_id:

                selected_deck = self.deck_var.get()

                if (
                    selected_deck
                    and selected_deck != "All Decks"
                    and card["deck"] != selected_deck
                ):
                    continue

                return card

        return None