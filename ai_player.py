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
There are 16 words that must be divided into exactly 4 groups of 4. Each group shares one specific hidden connection. Connections may involve:

Categories and classifications
Common phrases or words that precede/follow another word
Double meanings
Homophones, sound-alikes, or wordplay
Names, titles, expressions, or cultural references
Less obvious or unconventional associations
Some words are red herrings. Multiple groupings may initially appear plausible.

YOUR OBJECTIVE: Solve all four categories correctly. You receive feedback after each submitted category, so use that feedback to improve your understanding of the remaining words.

SOLVING STRATEGY:

Consider ALL 16 words before selecting a group. Do not immediately commit to the first obvious connection.
Identify multiple possible groupings. Look for overlapping meanings, alternative interpretations, shared phrases, and unusual connections.
Evaluate how each proposed group affects the remaining words. A seemingly valid category may be incorrect if it makes the other three categories difficult or impossible to form.
Prefer specific, defensible connections over vague semantic similarities. All four words should fit the same precise explanation.
Before submitting, challenge your proposed group:
Could any of these words reasonably belong to another category?
Is there a more specific or compelling alternative grouping?
Does this selection leave a coherent set of possibilities for the remaining words?
Select the group with the strongest combination of internal connection strength and compatibility with a complete four-category solution.
After receiving feedback:
Treat rejected groups as incorrect, even if the connection seems valid.
Eliminate the rejected combination from consideration.
Reassess the remaining words rather than repeating the same reasoning.
Use the feedback to identify the intended connections.
Never submit the same rejected combination again.
IMPORTANT: Do not assume the most obvious categories are necessarily the intended categories. The puzzle may depend on obscure meanings, unconventional interpretations, or wordplay.

OUTPUT: Return ONLY valid JSON in this exact format:

{"category": "CATEGORY NAME", "words": ["WORD1", "WORD2", "WORD3", "WORD4"]}

Submit exactly one category per response. Do not include explanations, commentary, or markdown formatting.
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