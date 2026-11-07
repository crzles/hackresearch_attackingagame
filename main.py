# main.py
# Plays several puzzles with the AI and prints the results.
# Run:  python main.py

import random

from ai_player import ask_ai
from game import check_guess, load_puzzles

NUM_PUZZLES = 5  # how many puzzles to play (each one costs several AI calls)
COLORS = ["yellow", "green", "blue", "purple"]


def play(puzzle):
    """Play one puzzle. Returns (won, mistakes, list of solved groups)."""
    words_left = [w for group in puzzle for w in group["words"]]
    random.shuffle(words_left)
    solved_groups = []
    past_guesses = []  # text like "BASS, CARP, PIANO, SOLE -> one away" to show the AI
    tried = []         # the same wrong guesses as sorted word lists, to catch repeats
    mistakes = 0

    while mistakes < 4 and len(solved_groups) < 4:
        solved_text = [f"{g['name']}: {', '.join(g['words'])}" for g in solved_groups]

        # Ask the AI. If its answer is broken or not allowed, ask again (up to 3 times).
        guess = None
        for attempt in range(3):
            try:
                words, category = ask_ai(words_left, solved_text, past_guesses, 4 - mistakes)
            except Exception as error:
                print("   AI reply problem:", error)
                continue
            on_board = all(w in words_left for w in words)
            already_tried = sorted(words) in tried
            if len(set(words)) == 4 and on_board and not already_tried:
                guess = words
                break
        if guess is None:
            print("   AI couldn't give a valid guess. Stopping this puzzle.")
            break

        result, group = check_guess(puzzle, guess)
        print(f"   {result:>9}: {', '.join(guess)}   (AI thought: {category})")

        if result == "correct":
            solved_groups.append(group)
            words_left = [w for w in words_left if w not in group["words"]]
        else:
            mistakes += 1
            tried.append(sorted(guess))
            past_guesses.append(f"{', '.join(sorted(guess))} -> {result}")

    won = len(solved_groups) == 4
    return won, mistakes, solved_groups


def main():
    puzzles = load_puzzles()[-NUM_PUZZLES:]
    wins = 0
    total_mistakes = 0
    solved_by_color = [0, 0, 0, 0]

    for number, puzzle in enumerate(puzzles, start=1):
        print(f"\nPuzzle {number}")
        won, mistakes, solved_groups = play(puzzle)
        print("   WON" if won else "   LOST", f"with {mistakes} mistakes")

        wins += won
        total_mistakes += mistakes
        for group in solved_groups:
            solved_by_color[group["level"]] += 1

    n = len(puzzles)
    print("\n===== Results =====")
    print(f"Puzzles played: {n}")
    print(f"Win rate:       {wins / n:.0%}")
    print(f"Avg mistakes:   {total_mistakes / n:.1f}")
    for level, color in enumerate(COLORS):
        print(f"{color:>7} groups solved: {solved_by_color[level] / n:.0%}")


if __name__ == "__main__":
    main()
