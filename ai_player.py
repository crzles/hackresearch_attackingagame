# ai_player.py
# Sends the board to the AI and gets back its next guess.

import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)  # read settings from the .env file

client = OpenAI(
    base_url=os.environ.get("OPENAI_BASE_URL"),  # the school's server
    api_key=os.environ["OPENAI_API_KEY"],
)
MODEL = os.environ.get("MODEL", "gpt-6-luna")

INSTRUCTIONS = """You are playing the word game Connections.
The words form groups of 4 that share a hidden connection (a category, a phrase
like "___ ball", a hidden word, a sound-alike, etc.). Some words are red herrings.
Guess the group you are MOST sure about first.

Reply with ONLY JSON, like this:
{"category": "TYPES OF FISH", "words": ["BASS", "SOLE", "PERCH", "CARP"]}"""


def ask_ai(words_left, solved, past_guesses, mistakes_left):
    """Ask the AI for one group. Returns (list of 4 words, category name)."""
    message = f"Words left: {', '.join(words_left)}\n"
    if solved:
        message += "Already solved: " + "; ".join(solved) + "\n"
    if past_guesses:
        message += "Wrong guesses so far (don't repeat):\n" + "\n".join(past_guesses) + "\n"
    message += f"Mistakes left: {mistakes_left}\nWhat is your next group?"

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": INSTRUCTIONS},
            {"role": "user", "content": message},
        ],
    )
    reply = response.choices[0].message.content

    data = read_json(reply)
    words = [w.strip().upper() for w in data["words"]]
    return words, data.get("category", "")


ONE_SHOT_INSTRUCTIONS = """You are playing the word game Connections.
The 16 words form exactly 4 groups of 4 that share a hidden connection (a category, a phrase like "___ ball", a hidden word, a sound-alike, etc.). Some words are red herrings.

First, write a step-by-step breakdown analyzing potential categories, testing for overlapping words, and isolating red herrings. Explicitly identify overlapping words and solve for the most restrictive or niche categories first, leaving broader semantic groups for last.
Then, provide your final answer as valid JSON in this exact format. You must use every single input word exactly once, keeping the original spelling:
{
  "groups": [
    {"category": "TYPES OF FISH", "words": ["BASS", "SOLE", "PERCH", "CARP"]},
    {"category": "...", "words": ["...", "...", "...", "..."]},
    {"category": "...", "words": ["...", "...", "...", "..."]},
    {"category": "...", "words": ["...", "...", "...", "..."]}
  ]
}"""


def ask_ai_one_shot(words):
    """Ask the AI for all 4 groups at once. Returns a list of (list of 4 words, category name)."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": ONE_SHOT_INSTRUCTIONS},
            {"role": "user", "content": "Words: " + ", ".join(words)},
        ],
    )
    data = read_json(response.choices[0].message.content)
    return [([w.strip().upper() for w in g["words"]], g.get("category", "")) for g in data["groups"]]


def read_json(reply):
    """Pull the JSON out of the reply (the AI sometimes adds extra text around it)."""
    start, end = reply.find("{"), reply.rfind("}")
    return json.loads(reply[start : end + 1])