"""LLM solver: asks Claude for one group at a time and feeds back the game's response."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

import anthropic
from dotenv import load_dotenv

from game import Game

load_dotenv()  # reads ANTHROPIC_API_KEY (and CONNECTIONS_MODEL) from a .env file if present

MODEL = os.environ.get("CONNECTIONS_MODEL", "claude-sonnet-5-5")
MAX_INVALID_RETRIES = 2

SYSTEM_PROMPT = """You are an expert player of the word game Connections.
There are 16 words that form 4 groups of 4. Each group shares a hidden connection.
Connections can be meanings, categories, wordplay (hidden words, homophones,
anagrams), or phrases like "___ ball". Watch for red herrings: some words fit
more than one group.

Strategy: submit the group you are MOST confident about first. If a guess was
"one away", exactly one of those 4 words is wrong; swap one out.

Reply with ONLY a JSON object, no other text:
{"reasoning": "<short explanation>", "category": "<the connection>", "words": ["W1","W2","W3","W4"]}"""


@dataclass
class Turn:
    words: list[str]
    category: str
    reasoning: str
    status: str


def _build_prompt(game: Game, notes: list[str]) -> str:
    lines = [f"Remaining words: {', '.join(game.remaining_words)}"]
    if game.solved:
        lines.append("Already solved:")
        lines += [f"  - {g.category}: {', '.join(sorted(g.words))}" for g in game.solved]
    past = [(g, s) for g, s in game.history if s != "correct"]
    if past:
        lines.append("Previous incorrect guesses (do not repeat these):")
        lines += [f"  - {', '.join(sorted(g))} -> {s.replace('_', ' ')}" for g, s in past]
    lines.append(f"Mistakes left: {game.mistakes_left}")
    lines += notes
    lines.append("Give your next guess.")
    return "\n".join(lines)


def _parse(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON in reply: {text[:200]}")
    data = json.loads(match.group(0))
    if not isinstance(data.get("words"), list):
        raise ValueError("Reply is missing a 'words' list")
    return data


class LLMSolver:
    def __init__(self, model: str = MODEL, client: anthropic.Anthropic | None = None):
        self.model = model
        self.client = client or anthropic.Anthropic()  # reads ANTHROPIC_API_KEY

    def next_guess(self, game: Game, notes: list[str]) -> dict:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_prompt(game, notes)}],
        )
        return _parse(response.content[0].text)

    def play(self, game: Game, verbose: bool = True) -> list[Turn]:
        turns: list[Turn] = []
        while not game.over:
            notes: list[str] = []
            for _ in range(MAX_INVALID_RETRIES + 1):
                try:
                    data = self.next_guess(game, notes)
                except (ValueError, json.JSONDecodeError) as e:
                    notes = [f"Your last reply could not be read ({e}). Reply with JSON only."]
                    continue
                result = game.guess(data["words"])
                if result.status not in ("invalid", "repeat"):
                    break
                # Invalid guesses don't cost a mistake; tell the model and retry.
                notes = [f"That guess was rejected: {result.message} Try again."]
            else:
                if verbose:
                    print("  Solver kept giving invalid guesses; stopping.")
                break

            turn = Turn(
                words=[w.upper() for w in data["words"]],
                category=data.get("category", ""),
                reasoning=data.get("reasoning", ""),
                status=result.status,
            )
            turns.append(turn)
            if verbose:
                print(f"  [{result.status:>8}] {', '.join(turn.words)}  ({turn.category})")
        return turns
