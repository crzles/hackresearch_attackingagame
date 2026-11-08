# game.py
# Loads Connections puzzles from Kaggle and checks guesses.

import csv
from pathlib import Path

import kagglehub


def load_puzzles(csv_path=None, start_date=None):
    """Return a list of puzzles, oldest first.

    start_date: optional, like "2024-09-01". Only puzzles on or after this date are kept.

    Each puzzle is a list of 4 groups, and each group looks like:
        {"name": "WET WEATHER", "level": 0, "words": ["SNOW", "HAIL", "RAIN", "SLEET"]}
    level 0 = yellow (easiest), 1 = green, 2 = blue, 3 = purple (hardest)
    """
    # Download the dataset the first time (later runs reuse the saved copy).
    if csv_path is None:
        folder = kagglehub.dataset_download("eric27n/the-new-york-times-connections")
        csv_path = list(Path(folder).glob("**/*.csv"))[0]

    # The CSV has one row per word. Collect the words into games and groups.
    games = {}  # games[game_id][group_name] = {"name":..., "level":..., "words": [...]}
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            # Skip puzzles before the start date. Dates look like "2024-09-01",
            # so comparing them as text works.
            if start_date and row["Puzzle Date"] < start_date:
                continue

            game_id = row["Game ID"]
            group_name = row["Group Name"]
            word = row["Word"].strip().upper()

            if game_id not in games:
                games[game_id] = {}
            if group_name not in games[game_id]:
                games[game_id][group_name] = {
                    "name": group_name,
                    "level": int(float(row["Group Level"])),
                    "words": [],
                }
            games[game_id][group_name]["words"].append(word)

    # Keep only complete puzzles: 4 groups of 4 words, 16 different words.
    puzzles = []
    for groups in games.values():
        groups = list(groups.values())
        all_words = [w for g in groups for w in g["words"]]
        if len(groups) == 4 and len(all_words) == 16 and len(set(all_words)) == 16:
            puzzles.append(groups)
    return puzzles


def check_guess(puzzle, guess):
    """Compare a guess (4 words) to the puzzle's groups.

    Returns ("correct", group), ("one away", None), or ("wrong", None).
    """
    guess_upper = {w.strip().upper() for w in guess}
    for group in puzzle:
        group_upper = {w.strip().upper() for w in group["words"]}
        matches = len(guess_upper & group_upper)
        if matches == 4:
            return "correct", group
        if matches == 3:
            return "one away", None
    return "wrong", None