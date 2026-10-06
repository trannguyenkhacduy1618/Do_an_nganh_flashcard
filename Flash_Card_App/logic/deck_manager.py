class DeckManager:

    def __init__(self, json_repo):
        self.repo = json_repo

    def get_decks(self):
        return self.repo.get_decks()

    def create_deck(self, name):

        # Prevent duplicate deck name
        if self.repo.deck_exists(name):
            return None


        deck = {
            "id": self.repo.next_deck_id(),
            "name": name,
            "cards": []
        }


        self.repo.add_deck(deck)

        return deck

    def get_deck(self, deck_id):
        return self.repo.get_deck(deck_id)

    def card_count(self, deck):
        return len(deck.get("cards", []))
    def delete_deck(self, deck_name):

        self.repo.delete_deck(
            deck_name
        )
    def rename_deck(self, old_name, new_name):

        # Same name is valid
        if old_name == new_name:
            return True


        # New name already exists
        if self.repo.deck_exists(new_name):
            return False


        return self.repo.rename_deck(
            old_name,
            new_name
        )

    # =================================================================
    # TỪ ĐIỂN DÙNG CHUNG (Browser_Extension/dict.json)
    # =================================================================

    def import_from_dict(self, dict_data, deck_name="Từ điển"):
        """Nạp từ điển chung vào app dưới dạng một deck.

        Từ điển chung là "bộ đệm tra cứu tự lớn dần": extension tra Google
        Translate rồi ghi kết quả vào Browser_Extension/dict.json. Hàm này đọc
        file đó và biến mỗi từ thành 1 thẻ trong deck, để từ vựng lưu từ
        extension hiện ra trong app.

        Chỉ THÊM từ chưa có, không sửa/xoá thẻ cũ -> gọi lại nhiều lần vẫn an
        toàn, và tiến độ học trong test.db không bị mất.

        Trả về (số thẻ mới, tổng số thẻ trong deck, tên deck).
        """
        if not isinstance(dict_data, dict) or not dict_data:
            return 0, 0, deck_name

        deck = self.get_deck_by_name(deck_name)
        if deck is None:
            deck = self.create_deck(deck_name)
            if deck is None:
                return 0, 0, deck_name
            # create_deck trả về dict mới nhưng ta cần bản có tham chiếu tươi
            deck = self.get_deck_by_name(deck_name)

        cards = deck.setdefault("cards", [])

        existing = {
            card.get("question")
            for card in cards
            if isinstance(card, dict)
        }

        added = 0
        for word, entry in dict_data.items():
            if not isinstance(word, str) or not word.strip():
                continue
            if word in existing:
                continue

            ipa = ""
            meaning = ""
            definitions = []
            synonyms = []
            examples = []

            if isinstance(entry, dict):
                ipa = (entry.get("ipa") or "").strip()
                meaning = (entry.get("meaning") or "").strip()
                # Các trường mở rộng (dict cũ không có -> mặc định rỗng)
                if isinstance(entry.get("definitions"), list):
                    for block in entry["definitions"]:
                        if not isinstance(block, dict):
                            continue
                        pos = (block.get("pos") or "").strip()
                        texts = [
                            str(d).strip()
                            for d in (block.get("definitions") or [])
                            if str(d).strip()
                        ]
                        if texts:
                            definitions.append({"pos": pos, "definitions": texts})
                if isinstance(entry.get("synonyms"), list):
                    synonyms = [str(s).strip() for s in entry["synonyms"] if str(s).strip()]
                if isinstance(entry.get("examples"), list):
                    examples = [str(e).strip() for e in entry["examples"] if str(e).strip()]
            elif isinstance(entry, str):
                meaning = entry.strip()

            # Bỏ qua bản ghi rác (Google trả rỗng hoặc nghĩa chỉ có dấu "-").
            # Nếu không lọc, dict bị lỗi sẽ tạo ra thẻ vô nghĩa trong app.
            if not ipa and meaning in ("", "-") and not definitions:
                continue

            # Giữ "answer" dạng chuỗi như cũ để mọi màn hình hiện tại vẫn chạy,
            # đồng thời lưu thêm các trường có cấu trúc cho StudyView hiển thị.
            if ipa and meaning:
                answer = f"{ipa}\n{meaning}"
            else:
                answer = ipa or meaning or "(chưa có nghĩa)"

            card = {
                "id": self.repo.next_card_id(deck),
                "question": word,
                "answer": answer,
                # Đánh dấu nguồn để lần sau không nhập trùng
                "source": "dict",
            }

            # Chỉ ghi các khoá mở rộng khi thật sự có dữ liệu, để file json
            # của thẻ nhập tay không bị phình thêm khoá rỗng.
            if definitions:
                card["definitions"] = definitions
            if synonyms:
                card["synonyms"] = synonyms
            if examples:
                card["examples"] = examples

            cards.append(card)
            existing.add(word)
            added += 1

        if added:
            self.repo.update_deck(deck)

        return added, len(cards), deck_name

    def get_deck_by_name(self, name):
        return self.repo.get_deck_by_name(name)