import tkinter as tk


class CardView:
    def __init__(self, root, on_show_answer):
        self.root = root
        self.bg_color = "#202124"
        self.card_color = "#303134"
        self.text_color = "#ffffff"

        self.card_frame = tk.Frame(self.root, bg=self.card_color)
        self.card_frame.pack(fill="both", expand=True, padx=40, pady=20)

        self.question_label = tk.Label(
            self.card_frame,
            text="",
            font=("Arial", 24, "bold"),
            fg=self.text_color,
            bg=self.card_color,
            wraplength=680,
            justify="center",
        )
        self.question_label.pack(expand=True, padx=40, pady=(40, 10))

        self.answer_label = tk.Label(
            self.card_frame,
            text="",
            font=("Arial", 17),
            fg="#dddddd",
            bg=self.card_color,
            wraplength=680,
            justify="center",
        )
        self.answer_label.pack(expand=True, padx=40, pady=10)

        self.show_button = tk.Button(
            self.root,
            text="Show Answer",
            font=("Arial", 14, "bold"),
            fg=self.text_color,
            bg="#3c4043",
            activebackground="#5f6368",
            activeforeground=self.text_color,
            relief="flat",
            padx=30,
            pady=10,
            command=on_show_answer,
        )
        self.show_button.pack(pady=(0, 15))

    def set_question(self, text):
        self.question_label.config(text=text)

    def set_answer(self, text):
        self.answer_label.config(text=text)

    def hide_show_button(self):
        self.show_button.pack_forget()

    def show_show_button(self):
        self.show_button.pack(pady=(0, 15))
        self.show_button.config(state="normal", text="Show Answer")
