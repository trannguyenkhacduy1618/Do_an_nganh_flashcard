
import tkinter as tk
from tkinter import ttk
from datetime import date, datetime, timedelta
import calendar

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import MaxNLocator, MultipleLocator

from ui.theme import *


class StatsView(tk.Frame):
    def __init__(self, parent, deck_manager, database):
        super().__init__(parent, bg=BG)

        self.deck_manager = deck_manager
        self.database = database

        today = date.today()
        self.month = today.month
        self.year = today.year
        self.period_var = tk.StringVar(value="Week")

        self._build_ui()
        self.refresh_stats()

    # =========================================================
    # SCROLLABLE, RESPONSIVE PAGE
    # =========================================================

    def _build_ui(self):
        self.canvas = tk.Canvas(
            self,
            bg=BG,
            highlightthickness=0
        )

        self.scrollbar = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self.canvas.yview
        )

        self.canvas.configure(
            yscrollcommand=self.scrollbar.set
        )

        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.page = tk.Frame(self.canvas, bg=BG)

        self.page_window = self.canvas.create_window(
            (0, 0),
            window=self.page,
            anchor="nw"
        )

        self.page.bind(
            "<Configure>",
            self._update_scroll_region
        )

        self.canvas.bind(
            "<Configure>",
            self._resize_page
        )

        # Mouse-wheel scrolling while the pointer is over the page.
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

        self._build_content()

    def _update_scroll_region(self, event=None):
        self.canvas.configure(
            scrollregion=self.canvas.bbox("all")
        )

    def _resize_page(self, event):
        # Make content follow the current window width.
        self.canvas.itemconfigure(
            self.page_window,
            width=event.width
        )

    def _bind_mousewheel(self, event=None):
        self.canvas.bind_all(
            "<MouseWheel>",
            self._on_mousewheel
        )

    def _unbind_mousewheel(self, event=None):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(
            int(-event.delta / 120),
            "units"
        )

    # =========================================================
    # PAGE CONTENT
    # =========================================================

    def _build_content(self):
        self.page.grid_columnconfigure(0, weight=1)

        tk.Label(
            self.page,
            text="Statistics",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 22, "bold")
        ).grid(
            row=0, column=0,
            sticky="w",
            padx=20, pady=(20, 12)
        )

        # Today's statistics
        self.today_frame = tk.Frame(self.page, bg=BG)
        self.today_frame.grid(
            row=1, column=0,
            sticky="ew",
            padx=12, pady=(0, 12)
        )

        for col in range(3):
            self.today_frame.grid_columnconfigure(
                col, weight=1, uniform="today"
            )

        self.today_labels = {}

        for col, (key, title) in enumerate([
            ("reviews", "Reviews Today"),
            ("unique", "Cards Studied Today"),
            ("total", "Total Cards")
        ]):
            box = tk.Frame(
                self.today_frame,
                bg=WHITE,
                highlightbackground=BORDER,
                highlightthickness=1
            )
            box.grid(
                row=0, column=col,
                sticky="nsew",
                padx=5, pady=3
            )

            tk.Label(
                box,
                text=title,
                bg=WHITE,
                fg=SECONDARY,
                font=("Segoe UI", 10)
            ).pack(anchor="w", padx=14, pady=(12, 2))

            value = tk.Label(
                box,
                text="0",
                bg=WHITE,
                fg=TEXT,
                font=("Segoe UI", 22, "bold")
            )
            value.pack(anchor="w", padx=14, pady=(0, 12))

            self.today_labels[key] = value

        # Study history
        history_box = tk.Frame(
            self.page,
            bg=WHITE,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        history_box.grid(
            row=2, column=0,
            sticky="ew",
            padx=17, pady=(0, 12)
        )
        history_box.grid_columnconfigure(0, weight=1)

        toolbar = tk.Frame(history_box, bg=WHITE)
        toolbar.pack(fill=tk.X, padx=14, pady=12)

        tk.Label(
            toolbar,
            text="Study History",
            bg=WHITE,
            fg=TEXT,
            font=("Segoe UI", 14, "bold")
        ).pack(side=tk.LEFT)

        ttk.Combobox(
            toolbar,
            textvariable=self.period_var,
            values=("Day", "Week", "Month", "Year"),
            state="readonly",
            width=10
        ).pack(side=tk.RIGHT)

        self.period_var.trace_add(
            "write",
            lambda *_: self.draw_history()
        )

        self.history_figure = Figure(
            figsize=(9, 3.5),
            dpi=100,
            constrained_layout=True
        )
        self.history_ax = self.history_figure.add_subplot(111)

        self.history_canvas = FigureCanvasTkAgg(
            self.history_figure,
            master=history_box
        )
        self.history_canvas.get_tk_widget().pack(
            fill=tk.BOTH,
            expand=True,
            padx=8, pady=(0, 10)
        )

        # Bottom section: calendar and distribution
        bottom = tk.Frame(self.page, bg=BG)
        bottom.grid(
            row=3, column=0,
            sticky="ew",
            padx=12, pady=(0, 20)
        )

        bottom.grid_columnconfigure(0, weight=1, uniform="bottom")
        bottom.grid_columnconfigure(1, weight=2, uniform="bottom")

        self.calendar_frame = tk.Frame(
            bottom,
            bg=WHITE,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        self.calendar_frame.grid(
            row=0, column=0,
            sticky="nsew",
            padx=5
        )

        self.pie_frame = tk.Frame(
            bottom,
            bg=WHITE,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        self.pie_frame.grid(
            row=0, column=1,
            sticky="nsew",
            padx=5
        )

        self.draw_calendar()
        self.draw_pie()

    # =========================================================
    # DATA
    # =========================================================

    def get_all_cards(self):
        cards = []

        for deck in self.deck_manager.repo.get_decks():
            for card in deck.get("cards", []):
                cards.append(card)

        return cards

    def refresh_stats(self):
        stats = self.database.get_today_stats()

        self.today_labels["reviews"].config(
            text=str(stats["reviews"])
        )
        self.today_labels["unique"].config(
            text=str(stats["unique_cards"])
        )
        self.today_labels["total"].config(
            text=str(len(self.get_all_cards()))
        )

        self.draw_history()
        self.draw_calendar()
        self.draw_pie()

    # =========================================================
    # STUDY HISTORY GRAPH
    # =========================================================

    def draw_history(self):
        today = date.today()
        period = self.period_var.get()

        if period == "Day":
            labels = [f"{hour:02d}:00" for hour in range(24)]

            with self.database.connect() as conn:
                rows = conn.execute("""
                    SELECT strftime('%H', reviewed_at), COUNT(*)
                    FROM review_history
                    WHERE DATE(reviewed_at) = ?
                    GROUP BY strftime('%H', reviewed_at)
                """, (today.isoformat(),)).fetchall()

            data = {str(hour).zfill(2): 0 for hour in range(24)}
            data.update({row[0]: row[1] for row in rows})
            values = [data[f"{hour:02d}"] for hour in range(24)]

        elif period == "Week":
            start = today - timedelta(days=6)
            dates = [
                start + timedelta(days=i)
                for i in range(7)
            ]
            labels = [d.strftime("%a") for d in dates]

            data = self.database.get_review_counts(
                start.isoformat(), today.isoformat()
            )
            values = [
                data.get(d.isoformat(), 0)
                for d in dates
            ]

        elif period == "Month":
            start = today - timedelta(days=29)
            dates = [
                start + timedelta(days=i)
                for i in range(30)
            ]
            labels = [d.strftime("%d %b") for d in dates]

            data = self.database.get_review_counts(
                start.isoformat(), today.isoformat()
            )
            values = [
                data.get(d.isoformat(), 0)
                for d in dates
            ]

        else:
            start = today.replace(month=1, day=1)
            dates = [
                date(today.year, month, 1)
                for month in range(1, 13)
            ]
            labels = [d.strftime("%b") for d in dates]

            data = self.database.get_review_counts(
                start.isoformat(), today.isoformat()
            )
            values = [
                sum(
                    count
                    for day, count in data.items()
                    if int(day[5:7]) == d.month
                )
                for d in dates
            ]

        self.history_ax.clear()
        self.history_ax.bar(labels, values)

        self.history_ax.set_ylabel("Reviews")
        self.history_ax.set_title(
            f"Cards reviewed per {period.lower()}"
        )

        # Force integer ticks: 0, 1, 2, 3...
        self.history_ax.yaxis.set_major_locator(
            MaxNLocator(integer=True, min_n_ticks=1)
        )
        self.history_ax.yaxis.set_major_locator(
            MultipleLocator(1)
        )
        self.history_ax.set_ylim(
            bottom=0,
            top=max(values, default=0) + 1
        )

        self.history_ax.tick_params(
            axis="x",
            labelrotation=35
        )

        self.history_figure.tight_layout()
        self.history_canvas.draw_idle()

    # =========================================================
    # STUDY CALENDAR
    # =========================================================

    def draw_calendar(self):
        for widget in self.calendar_frame.winfo_children():
            widget.destroy()

        header = tk.Frame(self.calendar_frame, bg=WHITE)
        header.pack(fill=tk.X, padx=8, pady=8)

        tk.Button(
            header,
            text="<",
            command=self.previous_month
        ).pack(side=tk.LEFT)

        tk.Label(
            header,
            text=f"{calendar.month_name[self.month]} {self.year}",
            bg=WHITE,
            fg=TEXT,
            font=("Segoe UI", 12, "bold")
        ).pack(side=tk.LEFT, expand=True)

        tk.Button(
            header,
            text=">",
            command=self.next_month
        ).pack(side=tk.RIGHT)

        grid = tk.Frame(self.calendar_frame, bg=WHITE)
        grid.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)

        for col, name in enumerate(
            ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")
        ):
            tk.Label(
                grid,
                text=name,
                bg=WHITE,
                fg=SECONDARY,
                font=("Segoe UI", 9, "bold")
            ).grid(
                row=0, column=col,
                sticky="nsew",
                padx=1, pady=3
            )

        last_day = calendar.monthrange(
            self.year, self.month
        )[1]

        start = date(self.year, self.month, 1).isoformat()
        end = date(self.year, self.month, last_day).isoformat()

        studied_days = self.database.get_study_days(start, end)
        weeks = calendar.monthcalendar(self.year, self.month)

        for row, week in enumerate(weeks, start=1):
            for col, day in enumerate(week):
                if day == 0:
                    continue

                current = date(self.year, self.month, day)
                studied = current.isoformat() in studied_days

                tk.Label(
                    grid,
                    text=str(day),
                    bg="#CDEFD8" if studied else WHITE,
                    fg=TEXT,
                    font=("Segoe UI", 10, "bold" if studied else "normal"),
                    padx=3, pady=5
                ).grid(
                    row=row, column=col,
                    sticky="nsew",
                    padx=1, pady=1
                )

        for col in range(7):
            grid.grid_columnconfigure(col, weight=1)

        tk.Label(
            self.calendar_frame,
            text="Green = studied",
            bg=WHITE,
            fg=SECONDARY,
            font=("Segoe UI", 9)
        ).pack(anchor="w", padx=12, pady=(0, 10))

    def previous_month(self):
        if self.month == 1:
            self.month = 12
            self.year -= 1
        else:
            self.month -= 1

        self.draw_calendar()

    def next_month(self):
        if self.month == 12:
            self.month = 1
            self.year += 1
        else:
            self.month += 1

        self.draw_calendar()

    # =========================================================
    # CARD DISTRIBUTION
    # =========================================================


    def draw_pie(self):
        for widget in self.pie_frame.winfo_children():
            widget.destroy()

        tk.Label(
            self.pie_frame,
            text="Card Distribution",
            bg=WHITE,
            fg=TEXT,
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", padx=15, pady=(12, 0))

        cards = self.get_all_cards()
        progress = self.database.get_all_progress()
        today = date.today()

        counts = {
            "New": 0,
            "Learning": 0,
            "Due": 0
        }

        for card in cards:
            question = card.get("question", "")
            state = progress.get(question)

            # No review date means New
            if not state or not state.get("day_to_review"):
                counts["New"] += 1
                continue

            try:
                due = datetime.strptime(
                    state["day_to_review"][:10],
                    "%Y-%m-%d"
                ).date()
            except (ValueError, TypeError):
                counts["New"] += 1
                continue

            if due == today:
                counts["Due"] += 1
            else:
                counts["Learning"] += 1

        # Legend on the left, pie chart on the right
        content = tk.Frame(self.pie_frame, bg=WHITE)
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        legend = tk.Frame(content, bg=WHITE)
        legend.pack(side=tk.LEFT, fill=tk.Y, padx=(5, 0), pady=15)

        categories = [
            ("New", "#4C78A8", "No review date"),
            ("Learning", "#F2CF5B", "Review date is not today"),
            ("Due", "#59A14F", "Review date is today")
        ]

        for name, color, meaning in categories:
            row = tk.Frame(legend, bg=WHITE)
            row.pack(anchor="w", pady=9)

            tk.Label(
                row,
                text=" ",
                bg=color,
                width=2
            ).pack(side=tk.LEFT, padx=(0, 7))

            tk.Label(
                row,
                text=f"{name}: {counts[name]}\n{meaning}",
                bg=WHITE,
                fg=TEXT,
                justify="left",
                font=("Segoe UI", 10)
            ).pack(side=tk.LEFT)

        figure = Figure(
            figsize=(5.5, 4.2),
            dpi=100,
            constrained_layout=True
        )
        ax = figure.add_subplot(111)

        values = [
            counts["New"],
            counts["Learning"],
            counts["Due"]
        ]
        colors = [item[1] for item in categories]

        if sum(values) == 0:
            ax.text(
                0.5, 0.5,
                "No cards",
                ha="center", va="center",
                fontsize=14
            )
            ax.axis("off")
        else:
            ax.pie(
                values,
                colors=colors,
                startangle=90,
                autopct=lambda pct: f"{pct:.0f}%" if pct > 0 else "",
                pctdistance=0.68,
                radius=1.15,
                textprops={"fontsize": 11}
            )
            ax.axis("equal")

        chart = FigureCanvasTkAgg(figure, master=content)
        chart.get_tk_widget().pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True
        )

        chart.draw_idle()
