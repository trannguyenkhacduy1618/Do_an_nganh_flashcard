import tkinter as tk

from logic.flashcard_manager import FlashcardManager
from ui.main_window import MainWindow


class FlashcardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Flashcards")
        self.root.geometry("800x600")
        self.root.minsize(600, 450)
        self.root.configure(bg="#202124")

        self.manager = FlashcardManager()

        self.window = MainWindow(
            self.root,
            on_reset_session=self.reset_session,
            on_show_answer=self.show_answer,
            on_answer_card=self.answer_card,
        )

        self.show_next_card()

        self.root.bind("<space>", self.space_pressed)
        self.root.bind("<Key-1>", lambda event: self.answer_card("again"))
        self.root.bind("<Key-2>", lambda event: self.answer_card("hard"))
        self.root.bind("<Key-3>", lambda event: self.answer_card("good"))
        self.root.bind("<Key-4>", lambda event: self.answer_card("easy"))

    @property
    def current_card(self):
        return self.manager.state.current_card

    @property
    def answer_visible(self):
        return self.manager.state.answer_visible

    def reset_session(self):
        self.manager.reset_session()
        self.show_next_card()

    def show_next_card(self):
        if self.manager.remaining_cards() == 0:
            self.window.set_question(" Session Complete!")
            self.window.set_answer("You finished all the cards.")
            self.window.update_progress("0 cards remaining")
            self.window.hide_show_button()
            self.window.hide_answer_buttons()
            self.window.disable_answer_buttons()
            return

        current_card = self.manager.get_current_card()
        if current_card is None:
            return

        self.window.set_question(current_card["question"])
        self.window.set_answer("")

        remaining = self.manager.remaining_cards()
        total = self.manager.total_cards()
        completed = self.manager.completed_cards()
        self.window.update_progress(f"Card {completed + 1} / {total}     •     {remaining} remaining")

        self.window.show_show_button()
        self.window.hide_answer_buttons()
        self.window.disable_answer_buttons()

    def show_answer(self):
        if self.current_card is None:
            return

        self.manager.reveal_answer()
        self.window.set_answer(self.current_card["answer"])
        self.window.hide_show_button()
        self.window.show_answer_buttons()
        self.window.enable_answer_buttons()

    def answer_card(self, difficulty):
        if self.current_card is None:
            return

        if not self.answer_visible:
            return

        if self.manager.answer_current(difficulty):
            self.show_next_card()

    def space_pressed(self, event):
        if not self.answer_visible:
            self.show_answer()

