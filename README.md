# Connections AI

An AI that plays NYT-style Connections, built for the "Attacking a Game" hackathon prompt (AI path).

## Files

| File | What it does |
|---|---|
| `game.py` | Game rules: board, guesses, "one away" feedback, 4-mistake limit |
| `llm_solver.py` | Claude solver: asks for one group at a time, feeds back results, retries on invalid replies |
| `evaluate.py` | Runs the solver on many puzzles and prints win rate, mistakes, and success by color |
| `puzzles.json` | Two original sample puzzles in the expected format |
| `test_game.py` | Tests for the game logic (no API key needed) |

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env          # Windows: copy .env.example .env
# open .env and paste your API key
python -m pytest -q           # check the game logic
python evaluate.py            # run the solver on puzzles.json
python evaluate.py kaggle -n 20   # run on 20 real puzzles from Kaggle
```

Each teammate creates their own `.env` with their own key. `.env` is in `.gitignore`, so it never gets committed.
Change the model with `CONNECTIONS_MODEL` in `.env` (default `claude-sonnet-5-5`).

## Puzzle format

```json
[{"id": "1", "groups": [{"category": "Fish", "words": ["BASS","SOLE","PERCH","CARP"], "level": 0}, ...]}]
```

`level` goes from 0 (yellow, easiest) to 3 (purple, hardest). If you download a dataset of past puzzles, convert it to this shape (or edit `load_puzzles` in `game.py`).

## Next steps

1. Load a real dataset of past puzzles and run `evaluate.py -n 50`.
2. Add an embeddings baseline solver with the same `play(game)` interface.
3. Add a hybrid solver (LLM suggests candidates, scoring picks the safest).
4. Build the demo UI (FastAPI + simple frontend) that shows the AI solving step by step.
