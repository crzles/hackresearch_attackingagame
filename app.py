# app.py
# Run with: streamlit run app.py

import streamlit as st
import random
import json
from pathlib import Path
from game import load_puzzles, check_guess
from ai_player import ask_ai, ask_ai_one_shot

st.set_page_config(page_title="Connections LLM Visualizer", layout="wide")

st.title("🧩 Connections LLM Decision Visualizer")

# --- GLOBAL HISTORY INITIALIZATION (Used to pass data to analytics.py) ---
if "global_history" not in st.session_state:
    st.session_state.global_history = []

# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.header("Settings")
    
    puzzle_source = st.selectbox(
        "Puzzle Source",
        ["Kaggle Dataset", "Self-Made Puzzles (JSON)"]
    )
    
    puzzle_path = ""
    if puzzle_source == "Self-Made Puzzles (JSON)":
        puzzle_path = st.text_input("Path to custom JSON file", value="my_puzzles.json")
    
    game_mode = st.selectbox(
        "Game Mode",
        ["Standard (Feedback per turn)", "One-Shot Mode (All 4 groups at once)"]
    )
    
    max_puzzles = st.number_input("Max puzzles to load", value=5, min_value=1)
    shuffle_puzzles = st.checkbox("Shuffle Puzzles", value=True)
    
    if st.button("Load Puzzles"):
        with st.spinner("Loading puzzles..."):
            try:
                if puzzle_source == "Kaggle Dataset":
                    all_puzzles = load_puzzles(None)
                else:
                    if Path(puzzle_path).exists():
                        with open(puzzle_path, "r", encoding="utf-8") as f:
                            all_puzzles = json.load(f)
                    else:
                        st.error(f"File {puzzle_path} not found.")
                        all_puzzles = []

                if shuffle_puzzles and all_puzzles:
                    random.shuffle(all_puzzles)
                
                st.session_state.puzzles = all_puzzles[:max_puzzles]
                st.session_state.puzzle_idx = 0
                st.session_state.game_state = None
                st.success("Loaded puzzles successfully!")
            except Exception as e:
                st.error(f"Error loading puzzles: {e}")

    if st.session_state.get("puzzles"):
        st.markdown("---")
        total_puzzles = len(st.session_state.puzzles)
        current_idx = st.session_state.get("puzzle_idx", 0)
        st.write(f"Puzzle **{current_idx + 1}** of **{total_puzzles}**")
        
        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.button("⬅️ Prev", disabled=(current_idx <= 0)):
                st.session_state.puzzle_idx -= 1
                st.session_state.game_state = None
                st.rerun()
        with col_next:
            if st.button("Next ➡️", disabled=(current_idx >= total_puzzles - 1)):
                st.session_state.puzzle_idx += 1
                st.session_state.game_state = None
                st.rerun()

# --- INITIALIZE SESSION STATE DEFAULTS ---
if "puzzles" not in st.session_state:
    st.session_state.puzzles = []
if "puzzle_idx" not in st.session_state:
    st.session_state.puzzle_idx = 0
if "game_state" not in st.session_state:
    st.session_state.game_state = None

def reset_game(puzzle):
    groups = puzzle.groups if hasattr(puzzle, "groups") else puzzle
    words_left = [w for group in groups for w in group["words"]]
    random.shuffle(words_left)
    
    st.session_state.game_state = {
        "puzzle_id": getattr(puzzle, "id", f"Puzzle_{st.session_state.puzzle_idx}"),
        "groups": groups,
        "words_left": words_left,
        "solved_groups": [],
        "mistakes": 0,
        "past_guesses": [],
        "tried": [],
        "turns_history": [],
        "over": False,
        "won": False,
        "recorded_to_global": False
    }

if st.session_state.puzzles:
    puzzle = st.session_state.puzzles[st.session_state.puzzle_idx]
    
    if st.session_state.game_state is None:
        reset_game(puzzle)

    state = st.session_state.game_state
    puzzle_groups = state["groups"]

    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"Puzzle Index: {st.session_state.puzzle_idx} | Mode: {game_mode}")
        
        if st.button("🔄 Reset Current Game"):
            reset_game(puzzle)
            st.rerun()
            
        st.markdown("### Current Board Words")
        if state["words_left"]:
            cols = st.columns(4)
            for i, word in enumerate(state["words_left"]):
                with cols[i % 4]:
                    st.container(border=True).markdown(
                        f"<div style='text-align:center;'><b>{word}</b></div>", 
                        unsafe_allow_html=True
                    )
        else:
            st.info("No words remaining on the board.")
            
        if state["solved_groups"]:
            st.markdown("### Solved Groups")
            for g in state["solved_groups"]:
                st.success(f"**{g['name']}**: {', '.join(g['words'])}")

    with col2:
        mistakes_left = 4 - state["mistakes"]
        st.markdown("### Stats & Controls")
        st.metric("Mistakes Left", mistakes_left)
        
        status_text = "Won 🎉" if state["won"] else ("Lost ❌" if state["over"] else "In Progress ⏳")
        st.metric("Game Status", status_text)
        
        is_one_shot = "One-Shot Mode" in game_mode
        # Stop only if the game is over, mistakes have reached 4, or all groups are solved
        max_turns_reached = state["mistakes"] >= 4 or len(state["solved_groups"]) == 4

        if not state["over"] and not max_turns_reached:
            button_label = "Run One-Shot AI Solve" if is_one_shot else "Run Next LLM Turn"
            if st.button(button_label, type="primary"):
                try:
                    solved_text = [f"{g['name']}: {', '.join(g['words'])}" for g in state["solved_groups"]]
                    
                    if is_one_shot:
                        # --- ONE-SHOT MODE ---
                        words_all = list(state["words_left"])
                        answer = None
                        
                        for attempt in range(3):
                            try:
                                answer = ask_ai_one_shot(words_all)
                                break
                            except Exception as error:
                                continue
                                
                        if answer is None:
                            state["turns_history"].append({
                                "words": ["---"],
                                "category": "Parsing Failed / API Error",
                                "status": "invalid",
                                "message": "AI failed to return a properly formatted 4-group list after 3 attempts. Check your ai_player.py prompt or API limits."
                            })
                            state["mistakes"] = 4
                            state["over"] = True
                            state["won"] = False
                        else:
                            state["turns_history"] = []
                            solved_groups = []
                            
                            for guess, category in answer:
                                res, grp = check_guess(puzzle_groups, guess)
                                if res == "correct" and grp in solved_groups:
                                    res = "repeat"
                                    status = "wrong"
                                    msg = f"Repeated group: {grp['name']}"
                                elif res == "correct":
                                    solved_groups.append(grp)
                                    status = "correct"
                                    msg = f"Correct! {grp['name']}"
                                else:
                                    status = "wrong"
                                    msg = f"Incorrect guess for category: {category}"
                                    
                                state["turns_history"].append({
                                    "words": guess,
                                    "category": category,
                                    "status": status,
                                    "message": msg
                                })
                                
                            state["solved_groups"] = solved_groups
                            state["mistakes"] = 4 - len(solved_groups)
                            state["over"] = True
                            state["won"] = (len(solved_groups) == 4)
                            state["words_left"] = [w for w in words_all if not any(w in g["words"] for g in solved_groups)]

                    else:
                        # --- STANDARD MODE ---
                        words, category = ask_ai(
                            state["words_left"], 
                            solved_text, 
                            state["past_guesses"], 
                            mistakes_left
                        )
                        
                        on_board = all(w in state["words_left"] for w in words)
                        already_tried = sorted(words) in state["tried"]
                        
                        if len(set(words)) == 4 and on_board and not already_tried:
                            result, group = check_guess(puzzle_groups, words)
                            
                            if result == "correct":
                                state["solved_groups"].append(group)
                                state["words_left"] = [w for w in state["words_left"] if w not in group["words"]]
                                message = f"Correct! {group['name']}"
                                status = "correct"
                            elif result == "one away":
                                state["mistakes"] += 1
                                state["tried"].append(sorted(words))
                                state["past_guesses"].append(f"{', '.join(sorted(words))} -> one away")
                                message = "One away!"
                                status = "one away"
                            else:
                                state["mistakes"] += 1
                                state["tried"].append(sorted(words))
                                state["past_guesses"].append(f"{', '.join(sorted(words))} -> wrong")
                                message = "Incorrect."
                                status = "wrong"
                                
                            if len(state["solved_groups"]) == 4:
                                state["won"] = True
                                state["over"] = True
                            elif state["mistakes"] >= 4:
                                state["over"] = True
                                
                            state["turns_history"].append({
                                "words": words,
                                "category": category,
                                "status": status,
                                "message": message
                            })
                        else:
                            msg = "AI gave invalid, repeated, or off-board words."
                            state["turns_history"].append({
                                "words": words,
                                "category": category,
                                "status": "invalid",
                                "message": msg
                            })

                    if state["over"] and not state["recorded_to_global"]:
                        st.session_state.global_history.append({
                            "puzzle_id": state["puzzle_id"],
                            "won": state["won"],
                            "mistakes": state["mistakes"],
                            "turns_count": len(state["turns_history"]),
                            "turns": state["turns_history"]
                        })
                        state["recorded_to_global"] = True

                    st.rerun()
                except Exception as e:
                    st.error(f"Error during LLM call: {e}")

    # Decision Stream
    if state["turns_history"]:
        st.markdown("---")
        st.subheader("LLM Decision Stream")
        for turn in reversed(state["turns_history"]):
            badge = "🟢" if turn['status'] == "correct" else ("🟡" if turn['status'] == "one away" else ("🔴" if turn['status'] == "wrong" else "⚠️"))
            with st.expander(f"{badge} Guess: {', '.join(turn['words'])} [{turn['status'].upper()}]"):
                st.write(f"**Category Idea:** {turn['category']}")
                st.write(f"**Feedback:** {turn['message']}")
else:
    st.info("👈 Configure settings in the sidebar, load your puzzles, and begin!")