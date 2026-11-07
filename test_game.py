"""Tests for the game logic (no API key needed). Run: python -m pytest -q"""

from game import Game, load_puzzles

PUZZLE = load_puzzles("puzzles.json")[0]


def test_correct_guess():
    game = Game(PUZZLE, seed=1)
    result = game.guess(["bass", "sole", "perch", "carp"])
    assert result.status == "correct"
    assert len(game.remaining_words) == 12
    assert game.mistakes == 0


def test_one_away_and_wrong():
    game = Game(PUZZLE, seed=1)
    assert game.guess(["BASS", "SOLE", "PERCH", "PIANO"]).status == "one_away"
    assert game.guess(["BASS", "POKER", "PIANO", "FOOT"]).status == "wrong"
    assert game.mistakes == 2


def test_invalid_and_repeat_cost_nothing():
    game = Game(PUZZLE, seed=1)
    assert game.guess(["BASS", "SOLE", "PERCH"]).status == "invalid"
    assert game.guess(["BASS", "SOLE", "PERCH", "BANANA"]).status == "invalid"
    game.guess(["BASS", "POKER", "PIANO", "FOOT"])
    assert game.guess(["FOOT", "PIANO", "POKER", "BASS"]).status == "repeat"
    assert game.mistakes == 1


def test_lose_after_four_mistakes():
    game = Game(PUZZLE, seed=1)
    wrong = [
        ["BASS", "POKER", "PIANO", "FOOT"],
        ["SOLE", "BRIDGE", "LOCK", "BASKET"],
        ["PERCH", "HEARTS", "KEYBOARD", "SNOW"],
        ["CARP", "RUMMY", "MAP", "EYE"],
    ]
    for w in wrong:
        game.guess(w)
    assert game.over and not game.won


def test_win():
    game = Game(PUZZLE, seed=1)
    for g in PUZZLE.groups:
        game.guess(list(g.words))
    assert game.won and game.over
