"""Run a solver over a set of puzzles and report stats.

Usage:
    python evaluate.py                    # all puzzles in puzzles.json
    python evaluate.py my_data.json -n 50 # first 50 puzzles from another file
    python evaluate.py kaggle -n 50       # download the Kaggle dataset and run 50 puzzles
    python evaluate.py path/to/data.csv   # a CSV you already downloaded
"""

from __future__ import annotations

import argparse
from collections import Counter

from game import LEVEL_NAMES, Game, load_puzzles
from llm_solver import LLMSolver


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="puzzles.json")
    parser.add_argument("-n", type=int, default=None, help="max puzzles to run")
    parser.add_argument("--seed", type=int, default=0, help="shuffle seed for word order")
    args = parser.parse_args()

    puzzles = load_puzzles(args.path)[: args.n]
    solver = LLMSolver()

    wins, total_mistakes = 0, 0
    solved_by_level: Counter[int] = Counter()

    for p in puzzles:
        print(f"\nPuzzle {p.id}")
        game = Game(p, seed=args.seed)
        solver.play(game)
        wins += game.won
        total_mistakes += game.mistakes
        for g in game.solved:
            solved_by_level[g.level] += 1
        print(f"  -> {'WON' if game.won else 'LOST'} with {game.mistakes} mistakes")

    n = len(puzzles)
    print("\n=== Results ===")
    print(f"Puzzles:        {n}")
    print(f"Win rate:       {wins / n:.0%}")
    print(f"Avg mistakes:   {total_mistakes / n:.2f}")
    for level, name in LEVEL_NAMES.items():
        print(f"{name:>7} solved: {solved_by_level[level] / n:.0%}")


if __name__ == "__main__":
    main()
