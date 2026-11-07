# Connections AI

An AI that plays NYT Connections, for the "Attacking a Game" hackathon prompt.

## Files

- `game.py` loads puzzles from Kaggle and checks if a guess is correct, one away, or wrong.
- `ai_player.py` sends the board to the AI and reads back its guess.
- `main.py` plays the puzzles and prints the results.

## Setup

```bash
pip install -r requirements.txt
copy .env.example .env      # Mac: cp .env.example .env
# open .env and paste your school API key
python main.py
```

Change how many puzzles it plays with `NUM_PUZZLES` at the top of `main.py`.
