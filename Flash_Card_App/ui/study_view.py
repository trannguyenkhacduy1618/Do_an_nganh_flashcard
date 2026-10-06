import tkinter as tk
from datetime import date

from ui.theme import *

class StudyView(tk.Frame):
    """Màn hình học thẻ.

    Giữ nguyên bố cục và luồng học (Show Answer -> Again/Hard/Good/Easy).
    Phần hiển thị thêm: khi lật thẻ, ngoài "answer" còn hiện các dữ liệu phong
    phú do extension lấy từ Google (từ loại, định nghĩa, từ đồng nghĩa, ví dụ)
    nếu thẻ có - giúp học trực quan hơn.

    Các trường này nằm trong file json của deck, ví dụ:
        {
          "id": 1, "question": "volunteer", "answer": "- tình nguyện viên",
          "definitions": [{"pos": "Danh từ", "definitions": ["a person who..."]}],
          "synonyms": ["subject", "participant"],
          "examples": ["it never paid to volunteer information"]
        }
    """

    def __init__(
        self, parent, deck, cards, card_manager, on_back
    ):
        super().__init__(parent, bg=BG)
        self.deck = deck
        self.cards = cards
        self.card_manager = card_manager
        self.on_back = on_back
        self.index = 0
        self.answer_visible = False

        self._build()

    # =================================================================
    # UI
    # =================================================================

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
        ).pack(pady=(10, 6))

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

        # --- Mặt trước: câu hỏi ---
        self.question_label = tk.Label(
            self.card_frame,
            text="",
            bg=WHITE,
            fg=TEXT,
            font=("Segoe UI", 18),
            wraplength=600,
            justify="center"
        )

        # --- Phiên âm (hiện cùng câu hỏi) ---
        self.ipa_label = tk.Label(
            self.card_frame,
            text="",
            bg=WHITE,
            fg=BLUE,
            font=("Consolas", 12),
            justify="center"
        )

        # --- Mặt sau: nghĩa chính + phần phong phú ---
        self.answer_label = tk.Label(
            self.card_frame,
            text="",
            bg=WHITE,
            fg="#444444",
            font=("Segoe UI", 14),
            wraplength=600,
            justify="center"
        )

        # Khung cuộn cho phần chi tiết (định nghĩa/đồng nghĩa/ví dụ)
        self.detail_wrap = tk.Frame(self.card_frame, bg=WHITE)
        self.detail_canvas = tk.Canvas(
            self.detail_wrap, bg=WHITE, highlightthickness=0
        )
        self.detail_scroll = tk.Scrollbar(
            self.detail_wrap, orient=tk.VERTICAL, command=self.detail_canvas.yview
        )
        self.detail_inner = tk.Frame(self.detail_canvas, bg=WHITE)

        self.detail_canvas.configure(yscrollcommand=self.detail_scroll.set)
        self.detail_window = self.detail_canvas.create_window(
            (0, 0), window=self.detail_inner, anchor="nw"
        )
        self.detail_inner.bind(
            "<Configure>",
            lambda e: self.detail_canvas.configure(
                scrollregion=self.detail_canvas.bbox("all")
            )
        )
        self.detail_canvas.bind(
            "<Configure>",
            lambda e: self.detail_canvas.itemconfig(
                self.detail_window, width=e.width
            )
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

    # =================================================================
    # NẠP THẺ
    # =================================================================

    def load_card(self):
        if not self.cards:
            return

        if self.index >= len(self.cards):
            self.index = 0

        card = self.cards[self.index]
        self.question_label.config(text=card["question"])

        # Phiên âm lấy từ các trường mở rộng, nếu có
        self.ipa_label.config(text=self._extract_ipa(card))

        self.answer_label.config(text="")
        self.answer_visible = False

        self.question_label.pack(fill=tk.BOTH, expand=True, padx=40, pady=(45, 4))
        if self._extract_ipa(card):
            self.ipa_label.pack(pady=(0, 15))

        self.answer_label.pack_forget()
        self.detail_wrap.pack_forget()
        self.answer_frame.pack_forget()
        self.show_button.pack(pady=20)
        self.progress.config(
            text=f"Card {self.index + 1} / {len(self.cards)}"
        )

    def _extract_ipa(self, card):
        """Lấy phiên âm: ưu tiên trường riêng, nếu không thì tách từ answer."""
        ipa = (card.get("ipa") or "").strip()
        if ipa:
            return ipa

        # Thẻ cũ chỉ có answer dạng "/ipa/\n- nghĩa"
        first = (card.get("answer") or "").split("\n", 1)[0].strip()
        if first.startswith("/") and first.endswith("/") and len(first) > 2:
            return first

        return ""

    # =================================================================
    # LẬT THẺ
    # =================================================================

    def show_answer(self):
        card = self.cards[self.index]

        # Thu gọn câu hỏi để nhường chỗ cho phần chi tiết
        self.question_label.pack_configure(
            fill=tk.NONE, expand=False, pady=(22, 4)
        )

        self.answer_label.config(text=self._clean_answer(card))
        self.answer_label.pack(fill=tk.X, padx=30, pady=(0, 8))

        self._build_details(card)

        self.show_button.pack_forget()
        self.answer_frame.pack(pady=15)
        self.answer_visible = True

    def _clean_answer(self, card):
        """Bỏ dòng phiên âm ở đầu answer nếu đã hiển thị riêng ở trên."""
        answer = (card.get("answer") or "").strip()
        ipa = self._extract_ipa(card)
        if not ipa:
            return answer

        lines = answer.split("\n")
        if lines and lines[0].strip() == ipa:
            return "\n".join(lines[1:]).strip()
        return answer

    # =================================================================
    # PHẦN CHI TIẾT (định nghĩa / từ đồng nghĩa / ví dụ)
    # =================================================================

    def _build_details(self, card):
        for widget in self.detail_inner.winfo_children():
            widget.destroy()

        definitions = card.get("definitions") or []
        synonyms = card.get("synonyms") or []
        examples = card.get("examples") or []

        has_content = False

        # --- Định nghĩa theo từ loại ---
        for block in definitions:
            if not isinstance(block, dict):
                continue
            pos = (block.get("pos") or "").strip()
            texts = block.get("definitions") or []
            if not texts:
                continue

            has_content = True
            self._add_section_header("Định nghĩa" + (f" · {pos}" if pos else ""))
            for text in texts:
                self._add_bullet(str(text))

        # --- Từ đồng nghĩa (dạng chip) ---
        if synonyms:
            has_content = True
            self._add_section_header("Từ đồng nghĩa")
            self._add_chips([str(s) for s in synonyms])

        # --- Ví dụ ---
        if examples:
            has_content = True
            self._add_section_header("Ví dụ")
            for text in examples:
                self._add_bullet(str(text), italic=True)

        if not has_content:
            self.detail_wrap.pack_forget()
            return

        self.detail_wrap.pack(fill=tk.BOTH, expand=True, padx=30, pady=(0, 10))
        tk.Frame(self.detail_wrap, bg=BORDER, height=1).pack(fill=tk.X, pady=(0, 6))
        self.detail_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.detail_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.detail_canvas.yview_moveto(0)

    def _add_section_header(self, text):
        tk.Label(
            self.detail_inner,
            text=text.upper(),
            bg=WHITE,
            fg=SECONDARY,
            font=("Segoe UI", 9, "bold"),
            anchor="w"
        ).pack(fill=tk.X, pady=(10, 4))

    def _add_bullet(self, text, italic=False):
        row = tk.Frame(self.detail_inner, bg=WHITE)
        row.pack(fill=tk.X, pady=1)

        tk.Label(
            row,
            text="•",
            bg=WHITE,
            fg=BLUE,
            font=("Segoe UI", 11, "bold")
        ).pack(side=tk.LEFT, anchor="n", padx=(2, 6))

        tk.Label(
            row,
            text=text,
            bg=WHITE,
            fg="#374151",
            font=("Segoe UI", 11, "italic") if italic else ("Segoe UI", 11),
            wraplength=520,
            justify="left",
            anchor="w"
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _add_chips(self, items):
        """Hiển thị danh sách dưới dạng chip, tự xuống dòng khi hết chỗ."""
        wrap = tk.Frame(self.detail_inner, bg=WHITE)
        wrap.pack(fill=tk.X, pady=2)

        row = None
        row_budget = 0

        for item in items:
            if not item:
                continue
            # Ước lượng độ rộng để ngắt dòng (~9px mỗi ký tự + padding)
            width = len(item) * 9 + 26
            if row is None or row_budget + width > 520:
                row = tk.Frame(wrap, bg=WHITE)
                row.pack(fill=tk.X, anchor="w", pady=2)
                row_budget = 0

            chip = tk.Frame(
                row, bg="#eef2ff", highlightbackground="#c7d2fe",
                highlightthickness=1
            )
            chip.pack(side=tk.LEFT, padx=(0, 6))

            tk.Label(
                chip,
                text=item,
                bg="#eef2ff",
                fg="#1d4ed8",
                font=("Segoe UI", 10),
                padx=9,
                pady=3
            ).pack()

            row_budget += width

    # =================================================================
    # TRẢ LỜI
    # =================================================================

    def answer(self, difficulty):
        card = self.cards[self.index]
        self.card_manager.review_card(card, difficulty)

        self.index += 1
        if self.index >= len(self.cards):
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
