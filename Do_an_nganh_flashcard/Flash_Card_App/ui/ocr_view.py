
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import re
from difflib import SequenceMatcher

import cv2
import easyocr
from PIL import Image, ImageTk

from ui.theme import BG, WHITE, BORDER, TEXT, BLUE, SECONDARY


class OcrView(tk.Toplevel):
    def __init__(self, parent, deck_manager):
        super().__init__(parent)

        self.deck_manager = deck_manager
        self.camera = None
        self.reader = None
        self.frame = None
        self.photo = None
        self.closed = False
        self.busy = False

        self.title("Sync - Camera Flashcard Search")
        self.geometry("850x680")
        self.minsize(650, 550)
        self.configure(bg=BG)

        self._build_ui()
        self._start_camera()

        # Initialize OCR in the background to keep the UI responsive.
        self.status_var.set("Loading OCR models. Please wait...")
        self.capture_button.config(state=tk.DISABLED)

        threading.Thread(
            target=self._initialize_ocr,
            daemon=True
        ).start()

        self.protocol("WM_DELETE_WINDOW", self.close)

    # =====================================================
    # UI
    # =====================================================

    def _build_ui(self):
        header = tk.Frame(self, bg=BG)
        header.pack(fill=tk.X, padx=24, pady=(20, 8))

        tk.Label(
            header,
            text="Camera Search",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 22, "bold")
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Capture a word to find it in your flashcard collection.",
            bg=BG,
            fg=SECONDARY,
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(4, 0))

        self.preview_frame = tk.Frame(
            self,
            bg="#171717",
            highlightbackground=BORDER,
            highlightthickness=1
        )
        self.preview_frame.pack(
            fill=tk.BOTH,
            expand=True,
            padx=24,
            pady=12
        )

        self.preview_label = tk.Label(
            self.preview_frame,
            text="Starting camera...",
            bg="#171717",
            fg="white",
            font=("Segoe UI", 13)
        )
        self.preview_label.pack(
            fill=tk.BOTH,
            expand=True,
            padx=8,
            pady=8
        )

        self.status_var = tk.StringVar(value="Starting...")
        tk.Label(
            self,
            textvariable=self.status_var,
            bg=BG,
            fg=SECONDARY,
            font=("Segoe UI", 10)
        ).pack(pady=(0, 8))

        self.capture_button = tk.Button(
            self,
            text="Capture & Search",
            command=self.capture_and_search,
            bg=BLUE,
            fg="white",
            activebackground=BLUE,
            activeforeground="white",
            font=("Segoe UI", 12, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            padx=28,
            pady=12,
            state=tk.DISABLED
        )
        self.capture_button.pack(pady=(0, 20))

    # =====================================================
    # CAMERA
    # =====================================================

    def _start_camera(self):
        self.camera = cv2.VideoCapture(0)

        if not self.camera.isOpened():
            self.camera.release()
            self.camera = None

            self.preview_label.config(
                text="Camera not detected.\n"
                     "Connect or enable your camera and reopen this window."
            )
            self.status_var.set("Unable to access camera.")
            return

        self._update_camera()

    def _update_camera(self):
        if self.closed or self.camera is None:
            return

        success, frame = self.camera.read()

        if success:
            self.frame = frame.copy()

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb)

            # Resize the preview without stretching the image.
            image.thumbnail((780, 440))

            self.photo = ImageTk.PhotoImage(image)
            self.preview_label.config(
                image=self.photo,
                text=""
            )

        else:
            self.status_var.set("Cannot read camera image.")

        self.after(30, self._update_camera)

    # =====================================================
    # OCR INITIALIZATION
    # =====================================================

    def _initialize_ocr(self):
        try:
            reader = easyocr.Reader(
                ["en"],
                gpu=False,
                verbose=False
            )

            if not self.closed:
                self.after(
                    0,
                    lambda: self._ocr_ready(reader)
                )

        except Exception as error:
            if not self.closed:
                self.after(
                    0,
                    lambda err=str(error): self._ocr_failed(err)
                )

    def _ocr_ready(self, reader):
        if self.closed:
            return

        self.reader = reader

        if self.camera is not None:
            self.status_var.set(
                "Ready. Point the camera at a word and capture it."
            )

            if self.frame is not None:
                self.capture_button.config(state=tk.NORMAL)
        else:
            self.status_var.set(
                "OCR is ready, but no camera is available."
            )

    def _ocr_failed(self, error):
        if self.closed:
            return

        self.status_var.set("Could not initialize OCR.")
        messagebox.showerror(
            "OCR Initialization Error",
            f"Could not load EasyOCR:\n\n{error}",
            parent=self
        )

    # =====================================================
    # CAPTURE AND SEARCH
    # =====================================================

    def capture_and_search(self):
        if self.busy:
            return

        if self.reader is None:
            messagebox.showinfo(
                "Please wait",
                "OCR is still loading.",
                parent=self
            )
            return

        if self.frame is None:
            messagebox.showwarning(
                "Camera",
                "No camera image is available.",
                parent=self
            )
            return

        captured_frame = self.frame.copy()

        self.busy = True
        self.capture_button.config(state=tk.DISABLED)
        self.status_var.set("Recognizing text and searching cards...")

        threading.Thread(
            target=self._process_image,
            args=(captured_frame,),
            daemon=True
        ).start()

    def _process_image(self, frame):
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            results = self.reader.readtext(rgb)

            extracted_text = " ".join(
                recognized_text
                for _, recognized_text, confidence in results
                if confidence >= 0.4
            ).strip()

            if extracted_text:
                matches = self.search_cards(extracted_text)
            else:
                matches = []

            if not self.closed:
                self.after(
                    0,
                    lambda text=extracted_text, cards=matches:
                        self._show_results(text, cards)
                )

        except Exception as error:
            if not self.closed:
                self.after(
                    0,
                    lambda err=str(error): self._processing_failed(err)
                )

    def _processing_failed(self, error):
        if self.closed:
            return

        self.busy = False
        self.capture_button.config(
            state=tk.NORMAL if self.reader and self.frame is not None
            else tk.DISABLED
        )
        self.status_var.set("Text recognition failed.")

        messagebox.showerror(
            "OCR Error",
            error,
            parent=self
        )

    # =====================================================
    # FLASHCARD SEARCH
    # =====================================================

    def _normalize(self, text):
        return re.sub(
            r"[^a-z0-9]+",
            " ",
            str(text).lower()
        ).strip()

    def search_cards(self, extracted_text):
        cards = []

        for deck in self.deck_manager.repo.get_decks():
            for card in deck.get("cards", []):
                cards.append(card)

        recognized = self._normalize(extracted_text)
        words = recognized.split()
        matches = []

        # Generate groups of adjacent OCR words.
        candidates = {
            " ".join(words[i:i + size])
            for size in range(1, min(5, len(words) + 1))
            for i in range(len(words) - size + 1)
        }

        for card in cards:
            question = str(card.get("question", ""))
            normalized_question = self._normalize(question)

            if not normalized_question:
                continue

            if normalized_question in recognized:
                score = 1.0
            else:
                score = max(
                    (
                        SequenceMatcher(
                            None,
                            normalized_question,
                            candidate
                        ).ratio()
                        for candidate in candidates
                    ),
                    default=0
                )

            if score >= 0.65:
                matches.append((score, card))

        matches.sort(key=lambda item: item[0], reverse=True)

        return [card for _, card in matches[:10]]

    # =====================================================
    # RESULTS WINDOW
    # =====================================================

    def _show_results(self, extracted_text, matches):
        if self.closed:
            return

        self.busy = False
        self.capture_button.config(
            state=tk.NORMAL if self.reader and self.frame is not None
            else tk.DISABLED
        )

        self.status_var.set("Search completed.")

        popup = tk.Toplevel(self)
        popup.title("Flashcard Search Results")
        popup.geometry("650x550")
        popup.minsize(450, 350)
        popup.configure(bg=BG)

        tk.Label(
            popup,
            text="Search Results",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 20, "bold")
        ).pack(anchor="w", padx=20, pady=(18, 4))

        tk.Label(
            popup,
            text="Recognized text:",
            bg=BG,
            fg=SECONDARY,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=20, pady=(10, 2))

        tk.Label(
            popup,
            text=extracted_text or "No text detected.",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 11),
            wraplength=590,
            justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 12))

        ttk.Separator(popup).pack(fill=tk.X, padx=20, pady=4)

        title = (
            f"Matching Cards ({len(matches)})"
            if matches
            else "No Matching Cards"
        )

        tk.Label(
            popup,
            text=title,
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 13, "bold")
        ).pack(anchor="w", padx=20, pady=10)

        container = tk.Frame(popup, bg=BG)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        result_canvas = tk.Canvas(
            container,
            bg=BG,
            highlightthickness=0
        )
        scrollbar = ttk.Scrollbar(
            container,
            orient="vertical",
            command=result_canvas.yview
        )

        result_frame = tk.Frame(result_canvas, bg=BG)

        result_window = result_canvas.create_window(
            (0, 0),
            window=result_frame,
            anchor="nw"
        )

        result_frame.bind(
            "<Configure>",
            lambda event: result_canvas.configure(
                scrollregion=result_canvas.bbox("all")
            )
        )

        result_canvas.bind(
            "<Configure>",
            lambda event: result_canvas.itemconfigure(
                result_window,
                width=event.width
            )
        )

        result_canvas.configure(yscrollcommand=scrollbar.set)

        result_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        if not matches:
            tk.Label(
                result_frame,
                text=(
                    "Try moving the camera closer to the word, "
                    "improving the lighting, or checking your cards."
                ),
                bg=BG,
                fg=SECONDARY,
                font=("Segoe UI", 11),
                wraplength=540,
                justify="left"
            ).pack(anchor="w", padx=12, pady=12)

        for card in matches:
            item = tk.Frame(
                result_frame,
                bg=WHITE,
                highlightbackground=BORDER,
                highlightthickness=1
            )
            item.pack(fill=tk.X, padx=3, pady=5)

            tk.Label(
                item,
                text=card.get("question", ""),
                bg=WHITE,
                fg=TEXT,
                font=("Segoe UI", 13, "bold"),
                wraplength=530,
                justify="left"
            ).pack(anchor="w", padx=14, pady=(12, 5))

            tk.Label(
                item,
                text=card.get("answer", ""),
                bg=WHITE,
                fg=SECONDARY,
                font=("Segoe UI", 11),
                wraplength=530,
                justify="left"
            ).pack(anchor="w", padx=14, pady=(0, 12))

    # =====================================================
    # CLEANUP
    # =====================================================

    def close(self):
        self.closed = True

        if self.camera is not None:
            self.camera.release()
            self.camera = None

        self.destroy()
