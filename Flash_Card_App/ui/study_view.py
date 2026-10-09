import tkinter as tk
from datetime import date

from ui.theme import *

class StudyView(tk.Frame):
    def __init__(
        self, parent, deck, cards, card_manager, on_back
    ):
        super().__init__(parent, bg=BG)
        self.deck = deck
        self.cards = list(cards)
        self.card_manager = card_manager
        self.on_back = on_back
        self.card_index = 0
        self.card_finished = 0
        self.answer_visible = False

        self._build()

    def _build(self):
        tk.Button(
            self,
            text="< Decks",
            command=self.on_back,
            relief=tk.FLAT,
            bg=BG,
            fg=BLUE,
            font=("Segoe UI", 11)
        ).pack(anchor="w", pady=(15, 5))

        tk.Label(
            self,
            text=self.deck["name"],
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 20, "bold")
        ).pack(pady=(10, 20))

        self.progress = tk.Label(
            self,
            bg=BG,
            fg=SECONDARY,
            font=("Segoe UI", 10)
        )
        self.progress.pack()

        self.card_frame = tk.Frame(
            self,
            bg=WHITE,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        self.card_frame.pack(
            fill=tk.BOTH,
            expand=True,
            padx=25,
            pady=20
        )

        self.question_label = tk.Label(
            self.card_frame,
            text="",
            bg=WHITE,
            fg=TEXT,
            font=("Segoe UI", 18),
            wraplength=600,
            justify="center"
        )
        self.question_label.pack(
            fill=tk.BOTH,
            expand=True,
            padx=40,
            pady=(45, 15)
        )

        self.answer_label = tk.Label(
            self.card_frame,
            text="",
            bg=WHITE,
            fg="#444444",
            font=("Segoe UI", 14),
            wraplength=600,
            justify="center"
        )

        self.show_button = tk.Button(
            self.card_frame,
            text="Show Answer",
            command=self.show_answer,
            font=("Segoe UI", 11, "bold"),
            padx=25,
            pady=8
        )
        self.show_button.pack(pady=20)

        self.answer_frame = tk.Frame(self.card_frame, bg=WHITE)

        for value, label in [
            (1, "Again"), (2, "Hard"), (3, "Good"), (4, "Easy")
        ]:
            tk.Button(
                self.answer_frame,
                text=label,
                command=lambda v=value: self.answer(v),
                font=("Segoe UI", 10, "bold"),
                padx=12,
                pady=7
            ).pack(side=tk.LEFT, padx=4)

        self.load_card()

    def is_it_new_or_due_card(self, card):
        progress = self.card_manager.db.get_progress(card["question"])
        if not progress:
            return True  # New card

        day_to_review = progress["day_to_review"]
        if not day_to_review:
            return True  # No review date set, treat as new

        today = date.today().isoformat()
        return today >= day_to_review  # Due card if today is on or after the review date
    def load_card(self):
        card = self.cards[self.card_index]
        if not self.is_it_new_or_due_card(card):
            self.card_index += 1
            if self.card_index >= len(self.cards):
                self._finished()
            else:
                self.load_card()
            return

        self.question_label.config(text=card["question"])
        self.answer_label.pack_forget()
        self.show_button.pack(pady=20)
        self.answer_frame.pack_forget()
        self.answer_visible = False
        
        self.progress.config(
            text=f"Cards left : {len(self.cards) - self.card_index}"
        )

    def show_answer(self):
        card = self.cards[self.card_index]
        self.answer_label.config(text=card["answer"])
        self.answer_label.pack(
            fill=tk.X, padx=30, pady=15
        )
        self.show_button.pack_forget()
        self.answer_frame.pack(pady=15)
        self.answer_visible = True

    def answer(self, difficulty):
        card = self.cards[self.card_index]
        self.card_manager.review_card(card, difficulty)

        if difficulty == 1:
            self.cards.append(card)

        self.card_index += 1

        if self.card_index >= len(self.cards):
            self._finished()
        else:
            self.load_card()

    def _finished(self):
        for widget in self.card_frame.winfo_children():
            widget.destroy()

        tk.Label(
            self.card_frame,
            text="Session complete!",
            bg=WHITE,
            fg=TEXT,
            font=("Segoe UI", 20, "bold")
        ).pack(expand=True)

        tk.Button(
            self.card_frame,
            text="Back to Decks",
            command=self.on_back,
            font=("Segoe UI", 11),
            padx=20,
            pady=8
        ).pack(pady=25)
