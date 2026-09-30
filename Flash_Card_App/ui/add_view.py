import tkinter as tk
from tkinter import ttk, messagebox

from ui.theme import *

class AddView(tk.Frame):
    def __init__(
        self, parent, deck_manager, card_manager,
        on_done, selected_deck=None
    ):
        super().__init__(parent, bg=BG)
        self.deck_manager = deck_manager
        self.card_manager = card_manager
        self.on_done = on_done
        self.selected_deck = selected_deck

        tk.Label(
            self,
            text="Add",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 20, "bold")
        ).pack(anchor="w", pady=(30, 20))

        form = tk.Frame(
            self,
            bg=WHITE,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        form.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(
            form, text="Deck",
            bg=WHITE, fg=TEXT,
            font=("Segoe UI", 11, "bold")
        ).grid(row=0, column=0, sticky="w", padx=25, pady=(25, 8))

        self.deck_var = tk.StringVar()
        decks = self.deck_manager.get_decks()
        self.deck_map = {d["name"]: d for d in decks}

        combo = ttk.Combobox(
            form,
            textvariable=self.deck_var,
            values=list(self.deck_map.keys()),
            state="readonly",
            width=42
        )
        combo.grid(row=1, column=0, padx=25, pady=(0, 20))

        if selected_deck:
            self.deck_var.set(selected_deck["name"])
        elif decks:
            self.deck_var.set(decks[0]["name"])

        tk.Label(
            form, text="Question",
            bg=WHITE, fg=TEXT,
            font=("Segoe UI", 11, "bold")
        ).grid(row=2, column=0, sticky="w", padx=25, pady=8)

        self.question = tk.Text(form, height=5, width=60, font=("Segoe UI", 11))
        self.question.grid(row=3, column=0, padx=25, pady=(0, 18))

        tk.Label(
            form, text="Answer",
            bg=WHITE, fg=TEXT,
            font=("Segoe UI", 11, "bold")
        ).grid(row=4, column=0, sticky="w", padx=25, pady=8)

        self.answer = tk.Text(form, height=5, width=60, font=("Segoe UI", 11))
        self.answer.grid(row=5, column=0, padx=25, pady=(0, 25))

        tk.Button(
            self,
            text="Add Card",
            command=self.add_card,
            font=("Segoe UI", 11, "bold"),
            padx=24, pady=9
        ).pack(anchor="e", padx=10, pady=15)

    def add_card(self):
        name = self.deck_var.get()
        question = self.question.get("1.0", tk.END).strip()
        answer = self.answer.get("1.0", tk.END).strip()

        if not name:
            messagebox.showwarning("Add Card", "Please select a deck.")
            return

        if not question or not answer:
            messagebox.showwarning(
                "Add Card",
                "Question and answer cannot be empty."
            )
            return

        deck = self.deck_map[name]
        self.card_manager.add_card(deck["id"], question, answer)

        self.question.delete("1.0", tk.END)
        self.answer.delete("1.0", tk.END)

        messagebox.showinfo("Add Card", "Card added.")
