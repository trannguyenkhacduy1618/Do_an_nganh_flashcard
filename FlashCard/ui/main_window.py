import tkinter as tk

from ui.answer_buttons import AnswerButtons
from ui.card_view import CardView


class MainWindow:
    def __init__(self, root, on_reset_session, on_show_answer, on_answer_card):
        self.root = root
        self.bg_color = "#202124"
        self.secondary_text = "#aaaaaa"

        top_frame = tk.Frame(root, bg=self.bg_color)
        top_frame.pack(fill="x", padx=20, pady=(15, 5))

        self.progress_label = tk.Label(
            top_frame,
            text="",
            font=("Arial", 12),
            fg=self.secondary_text,
            bg=self.bg_color,
        )
        self.progress_label.pack(side="left")

        reset_button = tk.Button(
            top_frame,
            text="Reset",
            font=("Arial", 10),
            fg="#ffffff",
            bg="#3c4043",
            activebackground="#5f6368",
            activeforeground="#ffffff",
            relief="flat",
            padx=15,
            pady=5,
            command=on_reset_session,
        )
        reset_button.pack(side="right")

        self.card_view = CardView(root, on_show_answer)
        self.answer_buttons = AnswerButtons(root, on_answer_card)
        self.answer_buttons.hide()

    def update_progress(self, text):
        self.progress_label.config(text=text)

    def set_question(self, text):
        self.card_view.set_question(text)

    def set_answer(self, text):
        self.card_view.set_answer(text)

    def hide_show_button(self):
        self.card_view.hide_show_button()

    def show_show_button(self):
        self.card_view.show_show_button()

    def hide_answer_buttons(self):
        self.answer_buttons.hide()

    def show_answer_buttons(self):
        self.answer_buttons.show()

    def disable_answer_buttons(self):
        self.answer_buttons.disable()

    def enable_answer_buttons(self):
        self.answer_buttons.enable()
