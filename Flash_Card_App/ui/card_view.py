import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from ui.theme import *
from datetime import date, timedelta
import webbrowser


class CardView(tk.Frame):

    def __init__(
        self,
        parent,
        deck_manager,
        database,
        card_manager
    ):
        super().__init__(parent, bg=BG)

        self.deck_manager = deck_manager
        self.database = database
        self.card_manager = card_manager

        self.all_cards = []
        self.selected_card = None
        self.detail_fields = {}

        self.build_ui()
        self.load_cards()

        self.bind_all(
            "<Control-Delete>",
            self.delete_selected_card
        )

        self.bind_all(
            "<Control-s>",
            self.save_card_changes
        )

    # =========================================================
    # BUILD UI
    # =========================================================

    def build_ui(self):

        main = tk.Frame(self, bg=BG)
        main.pack(fill=tk.BOTH, expand=True)

        main.grid_columnconfigure(0, minsize=180, weight=0)
        main.grid_columnconfigure(1, minsize=350, weight=1)
        main.grid_columnconfigure(2, minsize=360, weight=0)
        main.grid_rowconfigure(0, weight=1)

        # =====================================================
        # LEFT PANEL
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

        self.left_panel.grid_propagate(False)

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

        self.filter_menu["values"] = ["", ""]

        # =====================================================
        # MIDDLE PANEL
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

        columns = (
            "card_name",
            "due",
            "deck"
        )

        style = ttk.Style()

        style.configure(
            "Treeview",
            font=("Segoe UI", 11),
            rowheight=35
        )

        style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 10, "bold")
        )

        self.card_tree = ttk.Treeview(
            self.middle_panel,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

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

        self.card_tree.bind(
            "<Double-1>",
            self.on_due_double_click
        )

        # =====================================================
        # RIGHT PANEL
        # =====================================================

        self.right_panel = tk.Frame(
            main,
            bg=WHITE,
            width=360,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        self.right_panel.grid(
            row=0,
            column=2,
            sticky="nsew"
        )

        self.right_panel.grid_propagate(False)

        self.right_panel.grid_rowconfigure(0, weight=1)
        self.right_panel.grid_columnconfigure(0, weight=1)

        # Scrollable detail panel

        self.detail_canvas = tk.Canvas(
            self.right_panel,
            bg=WHITE,
            highlightthickness=0
        )

        detail_scrollbar = ttk.Scrollbar(
            self.right_panel,
            orient=tk.VERTICAL,
            command=self.detail_canvas.yview
        )

        self.detail_canvas.configure(
            yscrollcommand=detail_scrollbar.set
        )

        self.detail_canvas.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        detail_scrollbar.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        self.detail_frame = tk.Frame(
            self.detail_canvas,
            bg=WHITE
        )

        self.detail_window = self.detail_canvas.create_window(
            (0, 0),
            window=self.detail_frame,
            anchor="nw"
        )

        self.detail_frame.bind(
            "<Configure>",
            lambda event: self.detail_canvas.configure(
                scrollregion=self.detail_canvas.bbox("all")
            )
        )

        self.detail_canvas.bind(
            "<Configure>",
            lambda event: self.detail_canvas.itemconfigure(
                self.detail_window,
                width=event.width
            )
        )

        # =====================================================
        # EDITABLE FIELDS
        # =====================================================

        self.create_text_field(
            "question",
            "Word",
            height=3,
            font=("Segoe UI", 16, "bold")
        )

        self.create_text_field(
            "answer",
            "Definition",
            height=5
        )

        self.create_text_field(
            "pronunciation",
            "Pronunciation",
            height=2
        )

        self.create_text_field(
            "part_of_speech",
            "Part of Speech",
            height=2
        )

        self.create_text_field(
            "example_text",
            "Example (English)",
            height=3
        )

        self.create_text_field(
            "example_translation",
            "Example Translation",
            height=3
        )

        self.create_text_field(
            "how_it_works",
            "How It Works",
            height=5
        )

        self.create_text_field(
            "applications",
            "Applications (one per line)",
            height=4
        )

        self.create_text_field(
            "related_terms",
            "Related Terms (one per line)",
            height=4
        )

        self.create_text_field(
            "common_mistakes",
            "Common Mistakes (one per line)",
            height=4
        )

        self.create_text_field(
            "images",
            "Image URLs (one per line: title | URL)",
            height=4
        )
        self.create_text_field(
            "link_urls",
            "Link URLs (one per line)",
            height=4
        )

        # Clickable links
        self.add_detail_label(
            "Clickable Links",
            self.detail_frame
        )

        self.clickable_links_frame = tk.Frame(
            self.detail_frame,
            bg=WHITE
        )

        self.clickable_links_frame.pack(
            fill=tk.X,
            padx=15,
            pady=(0, 10)
        )
        
        
        # =====================================================
        # SAVE BUTTON
        # =====================================================

        self.save_button = tk.Button(
            self.detail_frame,
            text="Save Changes",
            command=self.save_card_changes,
            bg=BLUE,
            fg=WHITE,
            activebackground=BLUE,
            activeforeground=WHITE,
            relief=tk.FLAT,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=15,
            pady=8
        )

        self.save_button.pack(
            fill=tk.X,
            padx=15,
            pady=(10, 20)
        )

    # =========================================================
    # FIELD CREATION
    # =========================================================

    def add_detail_label(self, title, parent=None):

        if parent is None:
            parent = self.detail_frame

        tk.Label(
            parent,
            text=title,
            bg=WHITE,
            fg=SECONDARY,
            font=("Segoe UI", 9, "bold")
        ).pack(
            anchor="w",
            padx=15,
            pady=(15, 5)
        )

    def create_text_field(
        self,
        key,
        title,
        height=3,
        font=("Segoe UI", 10)
    ):

        self.add_detail_label(
            title,
            self.detail_frame
        )

        text_widget = tk.Text(
            self.detail_frame,
            height=height,
            wrap=tk.WORD,
            font=font,
            bg=WHITE,
            fg=TEXT,
            relief=tk.SOLID,
            borderwidth=1,
            padx=8,
            pady=8
        )

        text_widget.pack(
            fill=tk.X,
            padx=15,
            pady=(0, 5)
        )

        self.detail_fields[key] = text_widget

    # =========================================================
    # LOAD CARDS
    # =========================================================

    def load_cards(self):

        self.all_cards.clear()

        progress = self.database.get_all_progress()

        decks = self.deck_manager.get_decks()

        deck_names = []

        for deck in decks:

            deck_name = deck["name"]
            deck_names.append(deck_name)

            for card in deck.get("cards", []):

                question = card.get("question", "")

                card_progress = progress.get(
                    question,
                    {}
                )

                self.all_cards.append({
                    "id": card["id"],
                    "question": question,
                    "answer": card.get("answer", ""),
                    "deck": deck_name,
                    "deck_id": deck["id"],
                    "day_to_review": card_progress.get(
                        "day_to_review"
                    ),
                    "details": card
                })

        self.deck_filter["values"] = [
            "All Decks"
        ] + deck_names

        if self.deck_var.get() not in self.deck_filter["values"]:
            self.deck_var.set("All Decks")

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

        for item in self.card_tree.get_children():
            self.card_tree.delete(item)

        selected_deck = self.deck_var.get()

        for card in self.all_cards:

            if (
                selected_deck
                and selected_deck != "All Decks"
                and card["deck"] != selected_deck
            ):
                continue

            due = card.get("day_to_review") or "-"

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
    # CARD SELECTION
    # =========================================================

    def on_card_selected(self, event=None):

        selection = self.card_tree.selection()

        if not selection:
            return

        card = self.find_card_by_tree_id(selection[0])

        if card:
            self.selected_card = card
            self.show_card_details(card)

    # =========================================================
    # TREE ID
    # =========================================================

    def make_tree_id(self, card):

        return f"{card['deck_id']}_{card['id']}"

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

    # =========================================================
    # CLEAR DETAILS
    # =========================================================

    def clear_card_details(self):

        self.selected_card = None

        for widget in self.detail_fields.values():
            widget.delete("1.0", tk.END)

        for widget in self.clickable_links_frame.winfo_children():
            widget.destroy()

        self.detail_canvas.yview_moveto(0)

    # =========================================================
    # GET / SET FIELD
    # =========================================================

    def set_field(self, key, value):

        widget = self.detail_fields[key]

        widget.delete("1.0", tk.END)

        if value is not None:
            widget.insert("1.0", str(value))

    def get_field(self, key):

        return self.detail_fields[key].get(
            "1.0",
            "end-1c"
        ).strip()

    def list_to_text(self, value):

        if not isinstance(value, list):
            return str(value or "")

        return "\n".join(
            str(item) for item in value
        )

    # =========================================================
    # DISPLAY CARD DETAILS
    # =========================================================

    def show_card_details(self, card):

        details = card.get("details", {})

        self.set_field(
            "question",
            details.get("question", "")
        )

        self.set_field(
            "answer",
            details.get("answer", "")
        )

        self.set_field(
            "pronunciation",
            details.get("pronunciation", "")
        )

        self.set_field(
            "part_of_speech",
            details.get("part_of_speech", "")
        )

        # Example

        example = details.get("example", {})

        if isinstance(example, dict):

            example_text = example.get("text", "")
            example_translation = example.get("translation", "")

        elif isinstance(example, str):

            example_text = example
            example_translation = ""

        else:

            example_text = ""
            example_translation = ""

        self.set_field("example_text", example_text)

        self.set_field(
            "example_translation",
            example_translation
        )

        # Other fields

        self.set_field(
            "how_it_works",
            details.get("how_it_works", "")
        )

        self.set_field(
            "applications",
            self.list_to_text(details.get("applications", []))
        )

        self.set_field(
            "related_terms",
            self.list_to_text(details.get("related_terms", []))
        )

        self.set_field(
            "common_mistakes",
            self.list_to_text(details.get("common_mistakes", []))
        )

        # Images

        images = details.get(
            "images",
            details.get("image_urls", [])
        )

        image_lines = []

        if isinstance(images, list):

            for image in images:

                if isinstance(image, str):
                    image_lines.append(image)

                elif isinstance(image, dict):

                    title = image.get("title", "Image")
                    url = image.get("url", "")

                    if url:
                        image_lines.append(
                            f"{title} | {url}"
                        )

        self.set_field(
            "images",
            "\n".join(image_lines)
        )

        link_urls = details.get(
            "link_urls",
            details.get("links", [])
        )

        if isinstance(link_urls, list):
            link_urls = [
                item.get("url", "") if isinstance(item, dict) else str(item)
                for item in link_urls
            ]

        self.set_field(
            "link_urls",
            self.list_to_text(link_urls)
        )

        self.update_clickable_links()

        self.detail_canvas.yview_moveto(0)

    # =========================================================
    # IMAGE URL LINKS
    # =========================================================

    def parse_image_lines(self):

        lines = self.get_field("images").splitlines()

        images = []

        for line in lines:

            line = line.strip()

            if not line:
                continue

            if "|" in line:

                title, url = line.split("|", 1)

                title = title.strip()
                url = url.strip()

            else:

                title = "Image"
                url = line

            if url:
                images.append({
                    "title": title or "Image",
                    "url": url
                })

        return images

    def parse_url_lines(self, key):

        return [
            line.strip()
            for line in self.get_field(key).splitlines()
            if line.strip()
        ]

    def update_clickable_links(self):

        for widget in self.clickable_links_frame.winfo_children():
            widget.destroy()

        images = self.parse_image_lines()
        links = self.parse_url_lines("link_urls")
        clickable_links = [
            (image["title"], image["url"])
            for image in images
        ] + [
            ("Link", url)
            for url in links
        ]

        if not clickable_links:

            tk.Label(
                self.clickable_links_frame,
                text="No clickable links",
                bg=WHITE,
                fg=SECONDARY,
                font=("Segoe UI", 9)
            ).pack(anchor="w")

            return

        for title, url in clickable_links:

            link = tk.Label(
                self.clickable_links_frame,
                text=f"{title}: {url}",
                bg=WHITE,
                fg="#0563C1",
                font=("Segoe UI", 9, "underline"),
                cursor="hand2",
                anchor="w",
                justify=tk.LEFT,
                wraplength=300
            )

            link.pack(
                anchor="w",
                fill=tk.X,
                pady=3
            )

            link.bind(
                "<Button-1>",
                lambda event, target=url: self.open_url(target)
            )

    def open_url(self, url):

        if not url.startswith(("http://", "https://")):

            messagebox.showwarning(
                "Invalid URL",
                "The URL must start with http:// or https://",
                parent=self
            )

            return

        webbrowser.open(url)

    # =========================================================
    # SAVE ALL CARD CHANGES
    # =========================================================

    def save_card_changes(self, event=None):

        if not self.selected_card:
            return "break"

        selected = self.selected_card

        new_question = self.get_field("question")
        new_answer = self.get_field("answer")

        if not new_question:

            messagebox.showwarning(
                "Invalid Card",
                "Word cannot be empty.",
                parent=self
            )

            return "break"

        try:

            deck = self.deck_manager.repo.get_deck(
                selected["deck_id"]
            )

            if not deck:
                raise Exception("Deck not found.")

            target_card = None

            for card in deck.get("cards", []):

                if card["id"] == selected["id"]:
                    target_card = card
                    break

            if target_card is None:
                raise Exception("Card not found.")

            old_question = target_card.get("question", "")

            # Update basic fields

            target_card["question"] = new_question
            target_card["answer"] = new_answer

            # Update additional fields

            target_card["pronunciation"] = self.get_field(
                "pronunciation"
            )

            target_card["part_of_speech"] = self.get_field(
                "part_of_speech"
            )

            # Example

            target_card["example"] = {
                "text": self.get_field("example_text"),
                "translation": self.get_field(
                    "example_translation"
                )
            }

            # Other fields

            target_card["how_it_works"] = self.get_field(
                "how_it_works"
            )

            target_card["applications"] = [
                item.strip()
                for item in self.get_field("applications").splitlines()
                if item.strip()
            ]

            target_card["related_terms"] = [
                item.strip()
                for item in self.get_field("related_terms").splitlines()
                if item.strip()
            ]

            target_card["common_mistakes"] = [
                item.strip()
                for item in self.get_field("common_mistakes").splitlines()
                if item.strip()
            ]

            # Image URLs

            target_card["images"] = self.parse_image_lines()
            target_card["link_urls"] = self.parse_url_lines(
                "link_urls"
            )

            # Update SQLite key if question changed

            if old_question != new_question:

                self.database.edit_card_question(
                    old_question,
                    new_question
                )

            # Save JSON

            self.deck_manager.repo.update_deck(deck)

            # Refresh list and restore selection

            tree_id = self.make_tree_id(selected)

            self.load_cards()

            if self.card_tree.exists(tree_id):

                self.card_tree.selection_set(tree_id)
                self.card_tree.focus(tree_id)

                self.selected_card = self.find_card_by_tree_id(
                    tree_id
                )

                if self.selected_card:
                    self.show_card_details(self.selected_card)

            messagebox.showinfo(
                "Saved",
                "Card information updated successfully.",
                parent=self
            )

        except Exception as error:

            messagebox.showerror(
                "Save Error",
                f"Could not save card:\n{error}",
                parent=self
            )

        return "break"

    # =========================================================
    # DELETE CARD
    # =========================================================

    def delete_selected_card(self, event=None):

        if not self.selected_card:
            return "break"

        card = self.selected_card

        confirm = messagebox.askyesno(
            "Delete Card",
            f"Delete '{card['question']}'?\n\n"
            "This cannot be undone.",
            parent=self
        )

        if not confirm:
            return "break"

        success = self.card_manager.delete_card(
            card["deck_id"],
            card["id"]
        )

        if success:
            self.load_cards()

        return "break"

    # =========================================================
    # SCHEDULE REVIEW
    # =========================================================

    def on_due_double_click(self, event):

        column = self.card_tree.identify_column(event.x)

        if column != "#2":
            return

        row_id = self.card_tree.identify_row(event.y)

        if not row_id:
            return

        card = self.find_card_by_tree_id(row_id)

        if not card:
            return

        days = simpledialog.askinteger(
            "Schedule Review",
            "How many days until the next review?\n(0 = today)",
            parent=self,
            minvalue=0
        )

        if days is None:
            return

        try:

            review_date = self.card_manager.schedule_card(
                card["question"],
                days
            )

            self.load_cards()

            messagebox.showinfo(
                "Review Scheduled",
                f"Next review: {review_date}",
                parent=self
            )

        except Exception as error:

            messagebox.showerror(
                "Error",
                f"Could not update review date:\n{error}",
                parent=self
            )