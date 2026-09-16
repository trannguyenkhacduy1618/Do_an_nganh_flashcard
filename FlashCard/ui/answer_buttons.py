import tkinter as tk


class AnswerButtons:
    def __init__(self, root, on_answer):
        self.root = root
        self.bg_color = "#202124"
        self.again_color = "#d93025"
        self.hard_color = "#f29900"
        self.good_color = "#1e8e3e"
        self.easy_color = "#1a73e8"

        self.answer_frame = tk.Frame(self.root, bg=self.bg_color)

        self.again_button = self.create_button("Again", self.again_color, lambda: on_answer("again"))
        self.hard_button = self.create_button("Hard", self.hard_color, lambda: on_answer("hard"))
        self.good_button = self.create_button("Good", self.good_color, lambda: on_answer("good"))
        self.easy_button = self.create_button("Easy", self.easy_color, lambda: on_answer("easy"))

    def create_button(self, text, color, command):
        button = tk.Button(
            self.answer_frame,
            text=text,
            font=("Arial", 12, "bold"),
            fg="white",
            bg=color,
            activebackground=color,
            activeforeground="white",
            relief="flat",
            height=2,
            command=command,
        )
        button.pack(side="left", fill="x", expand=True, padx=5)
        return button

    def hide(self):
        self.answer_frame.pack_forget()

    def show(self):
        self.answer_frame.pack(fill="x", padx=30, pady=(0, 20))

    def disable(self):
        for button in (self.again_button, self.hard_button, self.good_button, self.easy_button):
            button.config(state="disabled")

    def enable(self):
        for button in (self.again_button, self.hard_button, self.good_button, self.easy_button):
            button.config(state="normal")
