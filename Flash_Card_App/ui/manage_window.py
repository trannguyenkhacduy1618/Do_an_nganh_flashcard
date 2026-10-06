import tkinter as tk
from tkinter import messagebox, simpledialog

from ui.theme import *


class ManageWindow(tk.Toplevel):

    def __init__(
        self,
        parent,
        deck_manager,
        refresh_callback
    ):

        super().__init__(parent)

        self.deck_manager = deck_manager
        self.refresh_callback = refresh_callback

        self.title(
            "Manage Decks"
        )

        self.geometry(
            "450x450"
        )

        self.resizable(
            False,
            False
        )

        self.build_ui()

        self.load_decks()


    # =====================================================
    # UI
    # =====================================================

    def build_ui(self):

        tk.Label(
            self,
            text="Manage Decks",
            font=(
                "Segoe UI",
                16,
                "bold"
            )
        ).pack(
            pady=15
        )


        # -----------------------------
        # Buttons
        # -----------------------------

        button_frame = tk.Frame(
            self
        )

        button_frame.pack(
            pady=5
        )


        tk.Button(
            button_frame,
            text="Create",
            width=12,
            command=self.create_deck
        ).pack(
            side=tk.LEFT,
            padx=5
        )


        tk.Button(
            button_frame,
            text="Rename",
            width=12,
            command=self.rename_deck
        ).pack(
            side=tk.LEFT,
            padx=5
        )


        tk.Button(
            button_frame,
            text="Delete",
            width=12,
            command=self.delete_deck
        ).pack(
            side=tk.LEFT,
            padx=5
        )


        # -----------------------------
        # Deck list
        # -----------------------------

        self.listbox = tk.Listbox(
            self,
            height=12,
            width=45
        )

        self.listbox.pack(
            padx=20,
            pady=15
        )


        # -----------------------------
        # Statistics
        # -----------------------------

        self.info_label = tk.Label(
            self,
            text="",
            font=(
                "Segoe UI",
                11
            )
        )

        self.info_label.pack(
            pady=10
        )


        self.listbox.bind(
            "<<ListboxSelect>>",
            self.show_info
        )


    # =====================================================
    # Load decks
    # =====================================================

    def load_decks(self):

        self.listbox.delete(
            0,
            tk.END
        )

        decks = (
            self.deck_manager
            .get_decks()
        )


        for deck in decks:

            self.listbox.insert(
                tk.END,
                deck["name"]
            )


    # =====================================================
    # Create
    # =====================================================

    def create_deck(self):

        name = simpledialog.askstring(
            "Create Deck",
            "Deck name:",
            parent=self
        )


        if not name:
            return


        deck = self.deck_manager.create_deck(
            name
        )


        if deck is None:

            messagebox.showwarning(
                "Duplicate Deck",
                f"Deck '{name}' already exists.",
                parent=self
            )

            return


        self.load_decks()

        self.refresh_callback()



    # =====================================================
    # Rename
    # =====================================================

    def rename_deck(self):

        selected = (
            self.listbox.curselection()
        )


        if not selected:
            return


        old_name = (
            self.listbox.get(
                selected[0]
            )
        )


        new_name = simpledialog.askstring(
            "Rename Deck",
            "New name:",
            initialvalue=old_name,
            parent=self
        )


        if not new_name:
            return


        success = self.deck_manager.rename_deck(
            old_name,
            new_name
        )


        if not success:

            messagebox.showwarning(
                "Duplicate Deck",
                f"Deck '{new_name}' already exists.",
                parent=self
            )

            return


        self.load_decks()

        self.refresh_callback()



    # =====================================================
    # Delete
    # =====================================================

    def delete_deck(self):

        selected = (
            self.listbox.curselection()
        )


        if not selected:
            return


        deck_name = (
            self.listbox.get(
                selected[0]
            )
        )


        confirm = messagebox.askyesno(
            "Delete Deck",
            f"Delete '{deck_name}'?\n\nThis cannot be undone.",
            parent=self
        )


        if not confirm:
            return


        self.deck_manager.delete_deck(
            deck_name
        )


        # reload list
        self.load_decks()

        # refresh main deck view
        self.refresh_callback()



    # =====================================================
    # Show information
    # =====================================================

    def show_info(self,event=None):

        selected = (
            self.listbox.curselection()
        )


        if not selected:
            return


        name = (
            self.listbox.get(
                selected[0]
            )
        )


        decks = (
            self.deck_manager
            .get_decks()
        )


        for deck in decks:

            if deck["name"] == name:

                total = len(
                    deck.get(
                        "cards",
                        []
                    )
                )


                self.info_label.config(
                    text=(
                        f"Deck: {name}\n"
                        f"Total cards: {total}"
                    )
                )

                break