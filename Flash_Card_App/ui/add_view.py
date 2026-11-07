
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

        # Page title
        tk.Label(
            self,
            text="Add",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 20, "bold")
        ).pack(anchor="w", padx=35, pady=(25, 15))

        # Scrollable area
        container = tk.Frame(self, bg=BG)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.canvas = tk.Canvas(
            container,
            bg=BG,
            highlightthickness=0
        )

        scrollbar = ttk.Scrollbar(
            container,
            orient="vertical",
            command=self.canvas.yview
        )

        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Content frame inside canvas
        self.form = tk.Frame(
            self.canvas,
            bg=WHITE,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.form,
            anchor="nw"
        )

        self.form.bind("<Configure>", self.update_scroll_region)
        self.canvas.bind("<Configure>", self.resize_form)

        self.form.grid_columnconfigure(0, weight=1)

        self.build_form()

        # Mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)

    def update_scroll_region(self, event=None):
        self.canvas.configure(
            scrollregion=self.canvas.bbox("all")
        )

    def resize_form(self, event):
        self.canvas.itemconfigure(
            self.canvas_window,
            width=event.width
        )

    def on_mousewheel(self, event):
        self.canvas.yview_scroll(
            int(-1 * (event.delta / 120)),
            "units"
        )

    def build_form(self):
        row = 0

        # Helper for labels
        def add_label(label, current_row):
            tk.Label(
                self.form,
                text=label,
                bg=WHITE,
                fg=TEXT,
                font=("Segoe UI", 11, "bold")
            ).grid(
                row=current_row,
                column=0,
                sticky="w",
                padx=30,
                pady=(12, 5)
            )

        # Helper for text inputs
        def add_text_field(label, height=3):
            nonlocal row

            add_label(label, row)
            row += 1

            widget = tk.Text(
                self.form,
                height=height,
                font=("Segoe UI", 10),
                wrap=tk.WORD,
                relief=tk.SOLID,
                borderwidth=1,
                padx=8,
                pady=6
            )

            widget.grid(
                row=row,
                column=0,
                sticky="ew",
                padx=30,
                pady=(0, 10)
            )

            row += 1
            return widget

        # Deck selection
        add_label("Deck", row)
        row += 1

        self.deck_var = tk.StringVar()

        decks = self.deck_manager.get_decks()
        self.deck_map = {d["name"]: d for d in decks}

        self.combo = ttk.Combobox(
            self.form,
            textvariable=self.deck_var,
            values=list(self.deck_map.keys()),
            state="readonly",
            font=("Segoe UI", 10),
            width=40
        )

        self.combo.grid(
            row=row,
            column=0,
            sticky="w",
            padx=30,
            pady=(0, 15)
        )
        row += 1

        if self.selected_deck:
            self.deck_var.set(self.selected_deck["name"])
        elif decks:
            self.deck_var.set(decks[0]["name"])

        # Basic information
        self.question = add_text_field("Question", 4)
        self.answer = add_text_field("Answer", 4)

        # Additional information
        self.pronunciation = add_text_field("Pronunciation", 2)
        self.part_of_speech = add_text_field("Part of Speech", 2)

        self.example_text = add_text_field(
            "Example (English)", 3
        )

        self.example_translation = add_text_field(
            "Example Translation", 3
        )

        self.how_it_works = add_text_field(
            "How It Works", 4
        )

        self.applications = add_text_field(
            "Applications (one per line)", 4
        )

        self.related_terms = add_text_field(
            "Related Terms (one per line)", 3
        )

        self.common_mistakes = add_text_field(
            "Common Mistakes (one per line)", 4
        )

        self.image_urls = add_text_field(
            "Image URLs (one URL per line)", 3
        )
        self.link_urls = add_text_field(
            "Link URLs (one URL per line)", 3
        )
        

        # Add button
        self.add_button = tk.Button(
            self.form,
            text="Add Card",
            command=self.add_card,
            bg=BLUE,
            fg=WHITE,
            activebackground=BLUE,
            activeforeground=WHITE,
            font=("Segoe UI", 11, "bold"),
            padx=25,
            pady=10,
            relief=tk.FLAT,
            cursor="hand2"
        )

        self.add_button.grid(
            row=row,
            column=0,
            sticky="e",
            padx=30,
            pady=25
        )

    def add_card(self):
        name = self.deck_var.get()

        question = self.question.get("1.0", tk.END).strip()
        answer = self.answer.get("1.0", tk.END).strip()

        if not name:
            messagebox.showwarning(
                "Add Card",
                "Please select a deck."
            )
            return

        if not question or not answer:
            messagebox.showwarning(
                "Add Card",
                "Question and answer cannot be empty."
            )
            return

        # Read text fields
        def get_text(widget):
            return widget.get("1.0", tk.END).strip()

        # Read multiline fields as lists
        def get_list(widget):
            return [
                item.strip()
                for item in get_text(widget).splitlines()
                if item.strip()
            ]

        deck = self.deck_map[name]

        # Save card
        card = self.card_manager.add_card(
            deck_id=deck["id"],
            question=question,
            answer=answer,

            pronunciation=get_text(self.pronunciation),
            part_of_speech=get_text(self.part_of_speech),

            example_text=get_text(self.example_text),
            example_translation=get_text(
                self.example_translation
            ),

            how_it_works=get_text(self.how_it_works),

            applications=get_list(self.applications),
            related_terms=get_list(self.related_terms),
            common_mistakes=get_list(self.common_mistakes),
            image_urls=get_list(self.image_urls),
            link_urls=get_list(self.link_urls)
        )

        if not card:
            messagebox.showerror(
                "Add Card",
                "Failed to add card."
            )
            return

        # Clear all fields
        widgets = [
            self.question,
            self.answer,
            self.pronunciation,
            self.part_of_speech,
            self.example_text,
            self.example_translation,
            self.how_it_works,
            self.applications,
            self.related_terms,
            self.common_mistakes,
            self.image_urls,
            self.link_urls
        ]

        for widget in widgets:
            widget.delete("1.0", tk.END)

        messagebox.showinfo(
            "Add Card",
            "Card added successfully."
        )

        self.on_done()
