# app.py
# Run with: streamlit run app.py

import streamlit as st
import random
from game import load_puzzles, check_guess
from ai_player import ask_ai

st.set_page_config(page_title="Connections LLM Visualizer", layout="wide")

st.title("🧩 Connections LLM Decision Visualizer")

# Sidebar for controls
with st.sidebar:
    st.header("Settings")
    puzzle_path = st.text_input("Puzzle file / source (leave blank for Kaggle)", value="")
    max_puzzles = st.number_input("Max puzzles", value=1, min_value=1)
    
    if st.button("Load Puzzles"):
        with st.spinner("Loading puzzles..."):
            path = puzzle_path if puzzle_path.strip() else None
            st.session_state.puzzles = load_puzzles(path)[:max_puzzles]
            st.session_state.puzzle_idx = 0
            st.session_state.game_state = None
            st.success("Loaded puzzles successfully!")

# Initialize session state defaults
if "puzzles" not in st.session_state:
    st.session_state.puzzles = []
if "puzzle_idx" not in st.session_state:
    st.session_state.puzzle_idx = 0
if "game_state" not in st.session_state:
    st.session_state.game_state = None

def reset_game(puzzle):
    words_left = [w for group in puzzle for w in group["words"]]
    random.shuffle(words_left)
    st.session_state.game_state = {
        "words_left": words_left,
        "solved_groups": [],
        "mistakes": 0,
        "past_guesses": [],
        "tried": [],
        "turns_history": [],
        "over": False,
        "won": False
    }

if st.session_state.puzzles:
    puzzle = st.session_state.puzzles[st.session_state.puzzle_idx]
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"Puzzle Index: {st.session_state.puzzle_idx}")
        
        if st.button("Start / Reset Game") or st.session_state.game_state is None:
            reset_game(puzzle)
            st.rerun()
            
        state = st.session_state.game_state
        
        # Display Board / Remaining Words
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
            
        # Display Solved Groups
        if state["solved_groups"]:
            st.markdown("### Solved Groups")
            for g in state["solved_groups"]:
                st.success(f"**{g['name']}**: {', '.join(g['words'])}")

    with col2:
        state = st.session_state.game_state
        mistakes_left = 4 - state["mistakes"]
        
        st.markdown("### Stats & Controls")
        st.metric("Mistakes Left", mistakes_left)
        
        status_text = "Won 🎉" if state["won"] else ("Lost ❌" if state["over"] else "In Progress ⏳")
        st.metric("Game Status", status_text)
        
        if not state["over"]:
            if st.button("Run Next LLM Turn", type="primary"):
                try:
                    solved_text = [f"{g['name']}: {', '.join(g['words'])}" for g in state["solved_groups"]]
                    
                    # Call your existing ask_ai function from ai_player.py
                    words, category = ask_ai(
                        state["words_left"], 
                        solved_text, 
                        state["past_guesses"], 
                        mistakes_left
                    )
                    
                    # Validate selection against current board and tries
                    on_board = all(w in state["words_left"] for w in words)
                    already_tried = sorted(words) in state["tried"]
                    
                    if len(set(words)) == 4 and on_board and not already_tried:
                        result, group = check_guess(puzzle, words)
                        
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
                    st.rerun()
                except Exception as e:
                    st.error(f"Error during LLM call: {e}")

    # Display LLM Decision History
    if state["turns_history"]:
        st.markdown("---")
        st.subheader("LLM Decision Stream")
        for turn in reversed(state["turns_history"]):
            badge = "🟢" if turn['status'] == "correct" else ("🟡" if turn['status'] == "one away" else "🔴" if turn['status'] == "wrong" else "⚠️")
            with st.expander(f"{badge} Guess: {', '.join(turn['words'])} [{turn['status'].upper()}]"):
                st.write(f"**Category Idea:** {turn['category']}")
                st.write(f"**Feedback:** {turn['message']}")
else:
    st.info("👈 Use the sidebar to load your puzzles and begin!")