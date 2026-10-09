import sqlite3
from datetime import date
class Database:
    def __init__(self, db_file):
        self.db_file = db_file

    def connect(self):
        return sqlite3.connect(self.db_file)

    def initialize(self):
        with self.connect() as conn:
            conn.execute("""
                    CREATE TABLE IF NOT EXISTS card_progress (
                    question TEXT PRIMARY KEY,
                    difficulty INTEGER,
                    day_to_review TEXT
                )
            """)
            conn.commit()

    def save_progress(self, question, difficulty, day_to_review):
        with self.connect() as conn:
            conn.execute("""
                INSERT INTO card_progress
                    (question, difficulty, day_to_review)
                VALUES (?, ?, ?)
                ON CONFLICT(question)
                DO UPDATE SET
                    difficulty = excluded.difficulty,
                    day_to_review = excluded.day_to_review
            """, (
                question,
                difficulty,
                day_to_review
            ))

    def get_progress(self, question):
        with self.connect() as conn:
            row = conn.execute("""
                SELECT difficulty, day_to_review
                FROM card_progress
                WHERE question = ?
            """, (question,)).fetchone()

        if not row:
            return None

        return {
            "difficulty": row[0],
            "day_to_review": row[1]
        }


    def get_all_progress(self):
        with self.connect() as conn:
            rows = conn.execute("""
                SELECT question, difficulty, day_to_review
                FROM card_progress
            """).fetchall()

        progress = {}

        for row in rows:
            progress[row[0]] = {
                "difficulty": row[1],
                "day_to_review": row[2]
            }

        return progress
    def delete_progress(self, question):
        with self.connect() as conn:
            conn.execute(
                """
                DELETE FROM card_progress
                WHERE question = ?
                """,
                (question,)
            )
    def edit_card_question(self, old_question, new_question):
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE card_progress
                SET question = ?
                WHERE question = ?
                """,
                (new_question, old_question)
            )

    def get_new_or_due_cards(self):
        today = date.today().isoformat()

        with self.connect() as conn:
            rows = conn.execute("""
                SELECT question, difficulty, day_to_review
                FROM card_progress
                WHERE day_to_review IS NULL OR day_to_review <= ?
            """, (today,)).fetchall()

        cards = []

        for row in rows:
            cards.append({
                "question": row[0],
                "difficulty": row[1],
                "day_to_review": row[2]
            })

        return cards