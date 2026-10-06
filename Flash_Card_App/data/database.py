import sqlite3

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

    def get_progress(self, card_id):
        with self.connect() as conn:
            row = conn.execute("""
                SELECT difficulty, day_to_review
                FROM card_progress
                WHERE id = ?
            """, (card_id,)).fetchone()

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