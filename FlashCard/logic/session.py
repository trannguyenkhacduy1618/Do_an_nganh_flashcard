from dataclasses import dataclass, field


@dataclass
class SessionState:
    cards: list = field(default_factory=list)
    current_card: dict | None = None
    answer_visible: bool = False
