"""Core game logic for a Connections-style puzzle.

A puzzle has 16 words split into 4 groups of 4. The player guesses 4 words at a
time. Feedback is "correct", "one_away" (3 of 4 belong together), or "wrong".
The player loses after 4 mistakes.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

MAX_MISTAKES = 4
LEVEL_NAMES = {0: "yellow", 1: "green", 2: "blue", 3: "purple"}


@dataclass(frozen=True)
class Group:
    category: str
    words: frozenset[str]
    level: int  # 0 = easiest (yellow) ... 3 = hardest (purple)


@dataclass
class Puzzle:
    id: str
    groups: list[Group]

    @property
    def words(self) -> list[str]:
        return [w for g in self.groups for w in g.words]

    @classmethod
    def from_dict(cls, d: dict) -> "Puzzle":
        groups = [
            Group(
                category=g["category"],
                words=frozenset(w.upper() for w in g["words"]),
                level=g.get("level", i),
            )
            for i, g in enumerate(d["groups"])
        ]
        puzzle = cls(id=str(d.get("id", "")), groups=groups)
        puzzle.validate()
        return puzzle

    def validate(self) -> None:
        if len(self.groups) != 4:
            raise ValueError(f"Puzzle {self.id}: needs 4 groups, has {len(self.groups)}")
        for g in self.groups:
            if len(g.words) != 4:
                raise ValueError(f"Puzzle {self.id}: group '{g.category}' needs 4 words")
        if len(set(self.words)) != 16:
            raise ValueError(f"Puzzle {self.id}: words must be 16 unique words")


KAGGLE_DATASET = "eric27n/the-new-york-times-connections"


def download_kaggle_dataset() -> Path:
    """Download the Kaggle Connections dataset and return the path to its CSV."""
    import kagglehub

    folder = Path(kagglehub.dataset_download(KAGGLE_DATASET))
    csvs = sorted(folder.rglob("*.csv"))
    if not csvs:
        raise FileNotFoundError(f"No CSV found in {folder}")
    return csvs[0]


def load_puzzles(path: str | Path) -> list[Puzzle]:
    """Load puzzles from a .json file (this project's format) or a .csv from Kaggle.

    Pass "kaggle" to download the Kaggle dataset automatically.
    Pass a folder to use the first CSV inside it (e.g. the path kagglehub prints).
    """
    if str(path) == "kaggle":
        path = download_kaggle_dataset()
    path = Path(path)
    if path.is_dir():
        path = sorted(path.rglob("*.csv"))[0]

    if path.suffix.lower() == ".csv":
        return _load_kaggle_csv(path)

    data = json.loads(path.read_text())
    return [Puzzle.from_dict(d) for d in data]


def _load_kaggle_csv(path: Path) -> list[Puzzle]:
    """Read the one-row-per-word CSV (Game ID, Puzzle Date, Word, Group Name, Group Level, ...)."""
    import csv
    from collections import defaultdict

    # games[game_id][(level, group_name)] -> list of words
    games: dict[str, dict[tuple[int, str], list[str]]] = defaultdict(lambda: defaultdict(list))
    dates: dict[str, str] = {}

    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            game_id = row["Game ID"].strip()
            word = (row["Word"] or "").strip().upper()
            key = (int(float(row["Group Level"])), row["Group Name"].strip())
            games[game_id][key].append(word)
            dates[game_id] = row.get("Puzzle Date", "")

    puzzles, skipped = [], 0
    for game_id in sorted(games, key=lambda g: int(g) if g.isdigit() else g):
        groups = [
            {"category": name, "words": words, "level": level}
            for (level, name), words in sorted(games[game_id].items())
        ]
        try:
            puzzles.append(Puzzle.from_dict({"id": f"{game_id} ({dates[game_id]})", "groups": groups}))
        except ValueError:
            skipped += 1  # a few rows in public datasets have missing or duplicate words

    if skipped:
        print(f"Skipped {skipped} malformed puzzle(s) from {path.name}")
    return puzzles


@dataclass
class GuessResult:
    status: str  # "correct" | "one_away" | "wrong" | "invalid" | "repeat"
    group: Group | None = None
    message: str = ""


@dataclass
class Game:
    puzzle: Puzzle
    seed: int | None = None
    mistakes: int = 0
    solved: list[Group] = field(default_factory=list)
    history: list[tuple[frozenset[str], str]] = field(default_factory=list)
    _order: list[str] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        self._order = self.puzzle.words
        random.Random(self.seed).shuffle(self._order)

    @property
    def remaining_words(self) -> list[str]:
        solved_words = {w for g in self.solved for w in g.words}
        return [w for w in self._order if w not in solved_words]

    @property
    def mistakes_left(self) -> int:
        return MAX_MISTAKES - self.mistakes

    @property
    def won(self) -> bool:
        return len(self.solved) == 4

    @property
    def over(self) -> bool:
        return self.won or self.mistakes >= MAX_MISTAKES

    def guess(self, words: list[str] | set[str]) -> GuessResult:
        if self.over:
            return GuessResult("invalid", message="Game is already over.")

        guess = frozenset(w.strip().upper() for w in words)
        remaining = set(self.remaining_words)

        if len(guess) != 4:
            return GuessResult("invalid", message="Guess must be exactly 4 different words.")
        if not guess <= remaining:
            bad = sorted(guess - remaining)
            return GuessResult("invalid", message=f"Not on the board: {', '.join(bad)}")
        if any(guess == past for past, _ in self.history):
            return GuessResult("repeat", message="You already tried that exact guess.")

        for g in self.puzzle.groups:
            if g in self.solved:
                continue
            overlap = len(guess & g.words)
            if overlap == 4:
                self.solved.append(g)
                self.history.append((guess, "correct"))
                return GuessResult("correct", group=g, message=f"Correct: {g.category}")
            if overlap == 3:
                self.mistakes += 1
                self.history.append((guess, "one_away"))
                return GuessResult("one_away", message="One away!")

        self.mistakes += 1
        self.history.append((guess, "wrong"))
        return GuessResult("wrong", message="Wrong.")
