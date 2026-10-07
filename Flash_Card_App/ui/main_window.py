from doctest import master
import tkinter as tk
from tkinter import Label, Label, Toplevel, messagebox, simpledialog

from ui.card_view import CardView
from ui.theme import *
from ui.deck_view import DeckView
from ui.add_view import AddView
from ui.study_view import StudyView

class MainWindow:
    def __init__(self, root, deck_manager, card_manager,database):
        self.root = root
        self.deck_manager = deck_manager
        self.card_manager = card_manager
        self.database = database

        self.root.configure(bg=BG)

        self.current_view = None
        self.selected_deck = None

        self._build_menu()
        self._build_navigation()
        self._build_content()
        self._build_bottom()

        self.show_decks()

    def _build_menu(self):
        menu = tk.Menu(self.root)
        self.root.config(menu=menu)

    def _build_navigation(self):
        nav = tk.Frame(self.root, bg=BG)
        nav.pack(pady=(8, 12))

        self.nav_buttons = {}
        for name, command in [
            ("Decks", self.show_decks),
            ("Add Card", self.show_add),
            ("Manage Decks", self.open_manage_window),
            ("Browse", self.show_browse),
            ("Stats", self.blank_action),
            ("Sync", self.blank_action),
        ]:
            btn = tk.Button(
                nav,
                text=name,
                command=command,
                relief=tk.FLAT,
                bd=0,
                bg=WHITE,
                activebackground=WHITE,
                font=("Segoe UI", 13, "bold"),
                padx=20,
                pady=7,
                cursor="hand2"
            )
            btn.pack(side=tk.LEFT)
            self.nav_buttons[name] = btn

    def _build_content(self):
        self.content = tk.Frame(
            self.root,
            bg=BG,
            highlightthickness=0
        )
        self.content.pack(
            fill=tk.BOTH,
            expand=True,
            padx=70,
            pady=10
        )

    def _build_bottom(self):
        bottom = tk.Frame(self.root, bg=WHITE, height=62)
        bottom.pack(side=tk.BOTTOM, fill=tk.X)
        bottom.pack_propagate(False)

        tk.Button(
            bottom, text="Get Shared",
            command=self.blank_action,
            font=("Segoe UI", 10),
            padx=16, pady=7
        ).pack(side=tk.LEFT, padx=(245, 8), pady=12)

        tk.Button(
            bottom, text="Create Deck",
            command=self.create_deck,
            font=("Segoe UI", 10),
            padx=16, pady=7
        ).pack(side=tk.LEFT, padx=8, pady=12)

        tk.Button(
            bottom, text="Import File",
            command=self.blank_action,
            font=("Segoe UI", 10),
            padx=16, pady=7
        ).pack(side=tk.LEFT, padx=8, pady=12)

    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def show_decks(self):
        self.clear_content()
        self.current_view = DeckView(
            self.content,
            self.deck_manager,
            self.open_deck
        )
        self.current_view.pack(fill=tk.BOTH, expand=True)

    def show_add(self):
        self.clear_content()
        self.current_view = AddView(
            self.content,
            self.deck_manager,
            self.card_manager,
            self.show_decks
        )
        self.current_view.pack(fill=tk.BOTH, expand=True)

    def open_deck(self, deck):
        cards = self.card_manager.get_cards(deck["id"])
        if not cards:
            self.show_add_for_deck(deck)
            return

        self.selected_deck = deck
        self.clear_content()
        self.current_view = StudyView(
            self.content,
            deck,
            cards,
            self.card_manager,
            self.show_decks
        )
        self.current_view.pack(fill=tk.BOTH, expand=True)

    def show_add_for_deck(self, deck):
        self.clear_content()
        self.current_view = AddView(
            self.content,
            self.deck_manager,
            self.card_manager,
            self.show_decks,
            selected_deck=deck
        )
        self.current_view.pack(fill=tk.BOTH, expand=True)

    def create_deck(self):
        name = simpledialog.askstring(
            "Create Deck",
            "Deck name:",
            parent=self.root
        )
        if name and name.strip():
            self.deck_manager.create_deck(name.strip())
            self.show_decks()

    def blank_action(self):
        pass

    #newly added
    def show_browse(self):

        self.clear_content()

        self.current_view = CardView(
            self.content,
            self.deck_manager,
            self.database,
            self.card_manager
        )

        self.current_view.pack(
            fill=tk.BOTH,
            expand=True
        )
    def open_manage_window(self):

        from ui.manage_window import ManageWindow

        ManageWindow(
            self.root,
            self.deck_manager,
            self.show_decks
        )