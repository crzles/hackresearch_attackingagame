# main.py
# Plays several puzzles with the AI and prints the results.
# Run:  python main.py

import random

from ai_player import ask_ai, ask_ai_one_shot
from game import check_guess, load_puzzles

# ---------- Settings ----------
NUM_PUZZLES = 20            # how many puzzles to play (each one costs AI calls)
START_DATE = "2024-09-01"  # only use puzzles from this date on (the 2024 paper stopped at August 2024)
MODE = "feedback"          # "feedback" = one group at a time with hints (like the real game)
                           # "one_shot" = all 4 groups at once, no hints (like the 2024 paper)
# ------------------------------

COLORS = ["yellow", "green", "blue", "purple"]


def weighted_score(solved_groups):
    """Points from the 2024 paper: yellow 1, green 2, blue 3, purple 4 (max 10)."""
    return sum(group["level"] + 1 for group in solved_groups)


def play_feedback(puzzle):
    """Real-game rules: guess one group at a time, get feedback, 4 mistakes allowed.
    Returns (list of solved groups, mistakes)."""
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

    return solved_groups, mistakes


def play_one_shot(puzzle):
    """Paper rules: the AI gives all 4 groups in one reply, no feedback.
    Returns (list of solved groups, mistakes). Mistakes = groups it got wrong."""
    words = [w for group in puzzle for w in group["words"]]
    random.shuffle(words)

    # Ask the AI. If its answer is broken, ask again (up to 3 times).
    answer = None
    for attempt in range(3):
        try:
            answer = ask_ai_one_shot(words)
            break
        except Exception as error:
            print("   AI reply problem:", error)
    if answer is None:
        print("   AI couldn't give an answer. Counting this puzzle as 0.")
        return [], 4

    # Check each group the AI gave. A group only counts if all 4 words match exactly.
    solved_groups = []
    for guess, category in answer:
        result, group = check_guess(puzzle, guess)
        if result == "correct" and group in solved_groups:
            result = "repeat"  # the AI listed the same group twice; it only counts once
        elif result == "correct":
            solved_groups.append(group)
        print(f"   {result:>9}: {', '.join(guess)}   (AI thought: {category})")

    return solved_groups, 4 - len(solved_groups)


def main():
    puzzles = load_puzzles(start_date=START_DATE)[:NUM_PUZZLES]
    print(f"Mode: {MODE}. Playing {len(puzzles)} puzzles from {START_DATE} on.")

    wins = 0
    total_groups = 0
    total_weighted = 0
    total_mistakes = 0
    solved_by_color = [0, 0, 0, 0]

    for number, puzzle in enumerate(puzzles, start=1):
        print(f"\nPuzzle {number}")
        if MODE == "one_shot":
            solved_groups, mistakes = play_one_shot(puzzle)
        else:
            solved_groups, mistakes = play_feedback(puzzle)

        won = len(solved_groups) == 4
        score = weighted_score(solved_groups)
        print(f"   {'WON' if won else 'LOST'}: {len(solved_groups)}/4 groups, weighted score {score}/10")

        wins += won
        total_groups += len(solved_groups)
        total_weighted += score
        total_mistakes += mistakes
        for group in solved_groups:
            solved_by_color[group["level"]] += 1

    n = len(puzzles)
    print("\n===== Results =====")
    print(f"Mode:                 {MODE}")
    print(f"Puzzles played:       {n}")
    print(f"Fully solved:         {wins / n:.0%}")
    print(f"Avg groups correct:   {total_groups / n:.2f} / 4")
    print(f"Avg weighted score:   {total_weighted / n:.2f} / 10")
    if MODE == "feedback":
        print(f"Avg mistakes:         {total_mistakes / n:.1f}")
    for level, color in enumerate(COLORS):
        print(f"{color:>7} groups solved: {solved_by_color[level] / n:.0%}")


if __name__ == "__main__":
    main()