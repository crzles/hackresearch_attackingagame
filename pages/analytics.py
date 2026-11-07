# analytics.py

import streamlit as st
import pandas as pd

st.set_page_config(page_title="LLM Performance Analytics", layout="wide")

st.title("📊 LLM Connections Analytics & Error Visualizer")

if "global_history" not in st.session_state or not st.session_state.global_history:
    st.warning("No game data recorded yet! Play a few rounds in your main app first to populate analytics.")
else:
    history = st.session_state.global_history
    
    # Calculate overall metrics
    total_games = len(history)
    total_wins = sum(1 for g in history if g["won"])
    win_rate = (total_wins / total_games) * 100
    avg_mistakes = sum(g["mistakes"] for g in history) / total_games
    
    # Top-level metric cards
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Puzzles Played", total_games)
    col2.metric("Win Rate", f"{win_rate:.1f}%")
    col3.metric("Average Mistakes per Game", f"{avg_mistakes:.1f}")
    
    st.markdown("---")
    
    # --- CHARTS SECTION ---
    st.subheader("📈 Performance & Error Visualizations")
    
    # Prepare DataFrame for session/global games progression
    games_df = pd.DataFrame([
        {
            "Game #": idx + 1,
            "Puzzle ID": g["puzzle_id"],
            "Mistakes Made": g["mistakes"],
            "Outcome": "Won 🎉" if g["won"] else "Lost ❌"
        }
        for idx, g in enumerate(history)
    ])
    
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.markdown("**Mistakes Progression Across Games**")
        st.line_chart(games_df.set_index("Game #")["Mistakes Made"])
        
    with chart_col2:
        st.markdown("**Error & Outcome Distribution Chart**")
        all_turns = []
        for g in history:
            for t in g["turns"]:
                all_turns.append(t["status"].upper())
        
        if all_turns:
            status_series = pd.Series(all_turns).value_counts()
            st.bar_chart(status_series)
        else:
            st.info("No turns recorded yet.")

    st.markdown("---")
    st.subheader("Match History & Detailed Guess Breakdown")
    
    # Compile flat list of all guesses made across all games to see how wrong it was
    all_turns_data = []
    for g_idx, game in enumerate(history):
        for t_idx, turn in enumerate(game["turns"]):
            all_turns_data.append({
                "Game #": g_idx + 1,
                "Puzzle ID": game["puzzle_id"],
                "Turn": t_idx + 1,
                "Guess Words": ", ".join(turn["words"]),
                "Category Attempted": turn["category"],
                "Status": turn["status"].upper(),
                "Feedback": turn["message"]
            })
            
    df_turns = pd.DataFrame(all_turns_data)
    
    # Status filter
    status_filter = st.multiselect(
        "Filter by Guess Result Status",
        options=["CORRECT", "WRONG", "ONE AWAY", "INVALID", "PENDING"],
        default=["CORRECT", "WRONG", "ONE AWAY", "INVALID", "PENDING"]
    )
    
    filtered_df = df_turns[df_turns["Status"].isin(status_filter)]
    
    # Render interactive dataframe table displaying how wrong guesses manifested
    st.dataframe(filtered_df, use_container_width=True)