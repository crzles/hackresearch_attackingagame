"""LLM solver: asks an LLM (Claude or OpenAI) for one group at a time and feeds back the game's response.

Pick the provider in .env:
    LLM_PROVIDER=anthropic   (uses ANTHROPIC_API_KEY)
    LLM_PROVIDER=openai      (uses OPENAI_API_KEY)
If LLM_PROVIDER is not set, it uses OpenAI when only OPENAI_API_KEY is set, otherwise Anthropic.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

from dotenv import load_dotenv

from game import Game

load_dotenv()  # reads keys and settings from a .env file if present

DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-5-5",
    "openai": "gpt-6.1-terra",
}
MAX_INVALID_RETRIES = 2


def _default_provider() -> str:
    provider = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if provider:
        return provider
    if os.environ.get("OPENAI_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY"):
        return "openai"
    return "anthropic"

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
    def __init__(self, provider: str | None = None, model: str | None = None, client=None):
        self.provider = provider or _default_provider()
        if self.provider not in DEFAULT_MODELS:
            raise ValueError(f"LLM_PROVIDER must be 'anthropic' or 'openai', got '{self.provider}'")
        self.model = model or os.environ.get("CONNECTIONS_MODEL") or DEFAULT_MODELS[self.provider]

        if client is not None:
            self.client = client
        elif self.provider == "openai":
            from openai import OpenAI

            self.client = OpenAI()  # reads OPENAI_API_KEY
        else:
            import anthropic

            self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY

    def _ask(self, prompt: str) -> str:
        """Send one prompt to the chosen provider and return the reply text."""
        if self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            text = response.choices[0].message.content or ""
            if not text:
                raise ValueError(f"No text in reply (finish reason: {response.choices[0].finish_reason})")
            return text

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4000,  # room for the model's thinking plus the JSON answer
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        # The reply can contain several blocks (e.g. a "thinking" block first);
        # only the "text" blocks hold the answer.
        text = "".join(b.text for b in response.content if b.type == "text")
        if not text:
            raise ValueError(f"No text in reply (stop reason: {response.stop_reason})")
        return text

    def next_guess(self, game: Game, notes: list[str]) -> dict:
        return _parse(self._ask(_build_prompt(game, notes)))

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