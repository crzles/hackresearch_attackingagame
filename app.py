import streamlit as st
from game import load_puzzles, Game
from llm_solver import LLMSolver

st.set_page_config(page_title="Connections LLM Visualizer", layout="wide")

st.title("🧩 Connections LLM Decision Visualizer")

# Sidebar for controls
with st.sidebar:
    st.header("Settings")
    puzzle_path = st.text_input("Puzzle file / source", value="puzzles.json")
    max_puzzles = st.number_input("Max puzzles", value=1, min_value=1)
    
    if st.button("Load Puzzles"):
        st.session_state.puzzles = load_puzzles(puzzle_path)[:max_puzzles]
        st.session_state.puzzle_idx = 0
        st.session_state.game = None
        st.session_state.solver = None
        st.success("Loaded puzzles!")

# Initialize session state
if "game" not in st.session_state:
    st.session_state.game = None

if "puzzles" in st.session_state and st.session_state.puzzles:
    p = st.session_state.puzzles[st.session_state.puzzle_idx]
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"Puzzle ID: {p.id}")
        
        if st.button("Start / Reset Game") or st.session_state.game is None:
            st.session_state.game = Game(p)
            st.session_state.solver = LLMSolver()
            st.session_state.turns_history = []
            st.rerun()
            
        game = st.session_state.game
        solver = st.session_state.solver
        
        # Display Board / Remaining Words
        st.markdown("### Current Board Words")
        cols = st.columns(4)
        for i, word in enumerate(game.remaining_words):
            cols[i % 4].markdown(f"<div style='padding:10px; border:1px solid #ccc; text-align:center; border-radius:5px;'><b>{word}</b></div>", unsafe_allow_html=True)
            
        # Display Solved Groups
        if game.solved:
            st.markdown("### Solved Groups")
            for g in game.solved:
                st.success(f"**{g.category}**: {', '.join(g.words)}")

    with col2:
        st.markdown("### Stats & Controls")
        st.metric("Mistakes Left", game.mistakes_left)
        st.metric("Game Status", "Won 🎉" if game.won else ("Lost ❌" if game.over else "In Progress ⏳"))
        
        if not game.over:
            if st.button("Run Next LLM Turn"):
                try:
                    # Get next guess using solver
                    data = solver.next_guess(game, [])
                    result = game.guess(data["words"])
                    
                    st.session_state.turns_history.append({
                        "words": data["words"],
                        "category": data.get("category"),
                        "reasoning": data.get("reasoning"),
                        "status": result.status,
                        "message": result.message
                    })
                    st.rerun()
                except Exception as e:
                    st.error(f"Error during LLM call: {e}")

    # Display LLM Decision History
    if "turns_history" in st.session_state and st.session_state.turns_history:
        st.markdown("---")
        st.subheader("LLM Decision Stream")
        for turn in reversed(st.session_state.turns_history):
            with st.expander(f"Guess: {', '.join(turn['words'])} [{turn['status'].upper()}]"):
                st.write(f"**Category Idea:** {turn['category']}")
                st.write(f"**Reasoning:** {turn['reasoning']}")
                st.write(f"**Feedback:** {turn['message']}")