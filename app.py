import random
import string
import csv
import io
import time
import streamlit as st

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_DIGIT_COUNT = 2
DIGIT_OPTIONS = [2, 3, 4]
DEFAULT_MAX_ATTEMPTS = 7
ATTEMPT_OPTIONS = [5, 7, 10]
ROOM_CODE_LENGTH = 6
MIN_PLAYERS = 2
MAX_PLAYERS = 10
HINT_UNLOCK_AFTER = 4      # hint becomes available after this many failed attempts
TIMER_SECONDS = 60

COLOR_BG = "#0d1117"
COLOR_ACCENT = "#f0a500"
COLOR_CARD = "#161b22"
COLOR_BORDER = "#30363d"
COLOR_TEXT = "#e6edf3"
COLOR_GREEN = "#3fb950"
COLOR_YELLOW = "#d29922"
COLOR_RED = "#f85149"
COLOR_ORANGE = "#e3693a"

# ---------------------------------------------------------------------------
# CSS injection
# ---------------------------------------------------------------------------
DARK_CSS = f"""
<style>
  html, body, [data-testid="stApp"] {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT};
    font-family: 'Segoe UI', sans-serif;
  }}
  [data-testid="stSidebar"] {{
    background-color: {COLOR_CARD} !important;
    border-right: 1px solid {COLOR_BORDER};
  }}
  .stButton > button {{
    background-color: {COLOR_ACCENT};
    color: {COLOR_BG};
    border: none;
    border-radius: 6px;
    font-weight: 700;
    padding: 0.4rem 1.2rem;
    transition: opacity 0.2s;
  }}
  .stButton > button:hover {{ opacity: 0.85; }}
  .stTextInput > div > div > input {{
    background-color: {COLOR_CARD};
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
  }}
  .room-code {{
    font-size: 1.8rem;
    font-weight: 800;
    color: {COLOR_ACCENT};
    letter-spacing: 0.25rem;
    text-align: center;
    padding: 0.5rem 0;
  }}
  .banner-win {{
    background: linear-gradient(135deg, #1a3a1a, #0d2a0d);
    border: 2px solid {COLOR_GREEN};
    border-radius: 10px;
    padding: 1rem 1.5rem;
    text-align: center;
    font-size: 1.4rem;
    font-weight: 700;
    color: {COLOR_GREEN};
    margin: 1rem 0;
  }}
  .banner-loss {{
    background: linear-gradient(135deg, #3a1a1a, #2a0d0d);
    border: 2px solid {COLOR_RED};
    border-radius: 10px;
    padding: 1rem 1.5rem;
    text-align: center;
    font-size: 1.4rem;
    font-weight: 700;
    color: {COLOR_RED};
    margin: 1rem 0;
  }}
  .hint-box {{
    background-color: {COLOR_CARD};
    border: 1px solid {COLOR_ACCENT};
    border-radius: 8px;
    padding: 0.5rem 1rem;
    color: {COLOR_ACCENT};
    margin: 0.5rem 0;
  }}
  .guess-table {{
    width: 100%;
    border-collapse: collapse;
    margin: 0.5rem 0;
    font-size: 0.95rem;
  }}
  .guess-table th {{
    background-color: {COLOR_CARD};
    color: {COLOR_ACCENT};
    padding: 0.5rem 0.75rem;
    text-align: center;
    border-bottom: 2px solid {COLOR_BORDER};
  }}
  .guess-table td {{
    padding: 0.45rem 0.75rem;
    text-align: center;
    border-bottom: 1px solid {COLOR_BORDER};
  }}
  .guess-table tr:nth-child(even) td {{ background-color: #0f1318; }}
  .bull-cell {{ color: {COLOR_GREEN}; font-weight: 700; }}
  .cow-cell {{ color: {COLOR_YELLOW}; font-weight: 700; }}
  .zero-cell {{ color: {COLOR_RED}; }}

  @keyframes bull-flash {{
    0%   {{ background-color: transparent; }}
    30%  {{ background-color: rgba(63,185,80,0.35); }}
    100% {{ background-color: transparent; }}
  }}
  @keyframes cow-flash {{
    0%   {{ background-color: transparent; }}
    30%  {{ background-color: rgba(210,153,34,0.35); }}
    100% {{ background-color: transparent; }}
  }}
  @keyframes row-shake {{
    0%, 100% {{ transform: translateX(0); }}
    20%      {{ transform: translateX(-6px); }}
    40%      {{ transform: translateX(6px); }}
    60%      {{ transform: translateX(-4px); }}
    80%      {{ transform: translateX(4px); }}
  }}
  .animate-bull {{ animation: bull-flash 1s ease forwards; }}
  .animate-cow  {{ animation: cow-flash 1s ease forwards; }}
  .animate-zero {{ animation: row-shake 0.5s ease forwards; }}

  @media (max-width: 600px) {{
    .room-code {{ font-size: 1.3rem; }}
    .guess-table {{ font-size: 0.82rem; }}
  }}
</style>
"""


def inject_css() -> None:
    st.markdown(DARK_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Pure game logic
# ---------------------------------------------------------------------------

def generate_secret(digit_count: int) -> str:
    """Return a string of `digit_count` unique digits."""
    digits = random.sample("0123456789", digit_count)
    # Avoid a leading zero so the guess display stays consistent
    if digits[0] == "0":
        non_zero = [d for d in digits if d != "0"]
        if non_zero:
            idx = digits.index(non_zero[0])
            digits[0], digits[idx] = digits[idx], digits[0]
    return "".join(digits)


def score_guess(secret: str, guess: str) -> tuple[int, int]:
    """Return (bulls, cows) for a guess against a secret."""
    bulls = sum(s == g for s, g in zip(secret, guess))
    cows = sum(g in secret for g in guess) - bulls
    return bulls, cows


def is_valid_guess(guess: str, digit_count: int) -> tuple[bool, str]:
    """Return (valid, error_message). Empty error_message means valid."""
    if len(guess) != digit_count:
        return False, f"Guess must be exactly {digit_count} digit(s)."
    if not guess.isdigit():
        return False, "Only numeric digits are allowed."
    if len(set(guess)) != digit_count:
        return False, "All digits must be unique — no repeats."
    return True, ""


def generate_room_code() -> str:
    """Return a 6-character alphanumeric room code."""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=ROOM_CODE_LENGTH))


def get_hint(secret: str, history: list[dict]) -> str:
    """Reveal one digit from the secret that hasn't been placed correctly yet."""
    guessed_bulls = {}
    for entry in history:
        guess_str = entry["guess"]
        for pos, digit in enumerate(guess_str):
            if digit == secret[pos]:
                guessed_bulls[pos] = digit
    # Pick a position not yet solved
    unsolved = [pos for pos in range(len(secret)) if pos not in guessed_bulls]
    if not unsolved:
        return f"One of the digits is: {secret[0]}"
    pos = random.choice(unsolved)
    return f"The number contains the digit  {secret[pos]}  (position not revealed)."


# ---------------------------------------------------------------------------
# Progress bar
# ---------------------------------------------------------------------------

def render_progress_bar(attempts_used: int, max_attempts: int) -> None:
    remaining = max_attempts - attempts_used
    fraction = remaining / max_attempts
    if fraction > 0.5:
        bar_color = COLOR_GREEN
    elif fraction > 0.25:
        bar_color = COLOR_ORANGE
    else:
        bar_color = COLOR_RED
    pct = int(fraction * 100)
    html = f"""
    <div style="margin:0.5rem 0 1rem;">
      <div style="font-size:0.8rem; color:{COLOR_TEXT}; margin-bottom:4px;">
        Attempts remaining: <b>{remaining}</b> / {max_attempts}
      </div>
      <div style="background:{COLOR_BORDER}; border-radius:6px; height:10px;">
        <div style="width:{pct}%; background:{bar_color}; height:10px;
                    border-radius:6px; transition:width 0.4s;"></div>
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Guess history table
# ---------------------------------------------------------------------------

def render_history(history: list[dict], digit_count: int) -> None:
    if not history:
        return
    rows_html = ""
    for entry in history:
        bulls = entry["bulls"]
        cows = entry["cows"]
        if bulls == digit_count:
            row_class = "animate-bull"
        elif bulls == 0 and cows == 0:
            row_class = "animate-zero"
        else:
            row_class = ""
        bull_class = "bull-cell" if bulls > 0 else "zero-cell"
        cow_class = "cow-cell" if cows > 0 else "zero-cell"
        rows_html += (
            f'<tr class="{row_class}">'
            f'<td>{entry["attempt"]}</td>'
            f'<td><b>{entry["guess"]}</b></td>'
            f'<td class="{bull_class}">{bulls} 🐂</td>'
            f'<td class="{cow_class}">{cows} 🐄</td>'
            f"</tr>"
        )
    html = f"""
    <table class="guess-table">
      <thead>
        <tr>
          <th>#</th><th>Guess</th><th>Bulls</th><th>Cows</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
    """
    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def build_csv(history: list[dict]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["attempt", "guess", "bulls", "cows"])
    writer.writeheader()
    writer.writerows(history)
    return output.getvalue()


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------

def rooms() -> dict:
    if "rooms" not in st.session_state:
        st.session_state["rooms"] = {}
    return st.session_state["rooms"]


def current_room() -> dict | None:
    code = st.session_state.get("active_room")
    if code and code in rooms():
        return rooms()[code]
    return None


def init_computer_room(code: str, digit_count: int, max_attempts: int) -> dict:
    return {
        "code": code,
        "mode": "computer",
        "digit_count": digit_count,
        "max_attempts": max_attempts,
        "phase": "play",
        "secret": generate_secret(digit_count),
        "history": [],
        "status": "active",      # active | won | lost
        "hint_used": False,
        "scoreboard": {"Human": {"wins": 0, "total_attempts": 0, "fastest": None}},
    }


def init_user_room(
    code: str, digit_count: int, max_attempts: int, player_names: list[str]
) -> dict:
    scoreboard = {
        name: {"wins": 0, "total_attempts": 0, "fastest": None, "hints": 0}
        for name in player_names
    }
    secrets = {name: None for name in player_names}
    histories = {name: [] for name in player_names}
    return {
        "code": code,
        "mode": "user",
        "digit_count": digit_count,
        "max_attempts": max_attempts,
        "phase": "setup",        # setup | play | finished
        "players": player_names,
        "setup_index": 0,        # which player is currently setting their secret
        "current_player_index": 0,
        "secrets": secrets,
        "histories": histories,
        "statuses": {name: "active" for name in player_names},
        "hint_used": {name: False for name in player_names},
        "scoreboard": scoreboard,
    }


def record_win(room: dict, player_name: str, attempts_used: int) -> None:
    sb = room["scoreboard"][player_name]
    sb["wins"] += 1
    sb["total_attempts"] += attempts_used
    if sb["fastest"] is None or attempts_used < sb["fastest"]:
        sb["fastest"] = attempts_used


def record_loss(room: dict, player_name: str, attempts_used: int) -> None:
    sb = room["scoreboard"][player_name]
    sb["total_attempts"] += attempts_used


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar(room: dict | None) -> None:
    with st.sidebar:
        st.markdown(f"## 🐂 Cows & Bulls")
        st.divider()

        if room:
            st.markdown(f"**Room Code**")
            st.markdown(
                f'<div class="room-code">{room["code"]}</div>',
                unsafe_allow_html=True,
            )
            st.divider()

            mode_label = (
                "💻 Computer vs User"
                if room["mode"] == "computer"
                else "👥 User vs User"
            )
            st.markdown(f"**Mode:** {mode_label}")
            st.markdown(f"**Digits:** {room['digit_count']}")
            st.markdown(f"**Max Attempts:** {room['max_attempts']}")
            st.divider()

            st.markdown("**Scoreboard**")
            for player, stats in room["scoreboard"].items():
                fastest = stats["fastest"] if stats["fastest"] else "—"
                st.markdown(
                    f"- **{player}** — Wins: {stats['wins']} | "
                    f"Attempts: {stats['total_attempts']} | "
                    f"Best: {fastest}"
                )
            st.divider()

            with st.expander("📖 Rules & Legend"):
                st.markdown(
                    f"""
**Cows & Bulls Rules**
- Guess a {room['digit_count']}-digit number with all unique digits.
- 🐂 **Bull** = right digit, right position.
- 🐄 **Cow** = right digit, wrong position.
- Win by scoring all Bulls!

**Hint:** unlocks after {HINT_UNLOCK_AFTER} failed attempts (one per round).
                    """
                )

            if st.button("🔄 Reset / New Game"):
                st.session_state.pop("active_room", None)
                st.rerun()
        else:
            with st.expander("📖 How to Play"):
                st.markdown(
                    """
**Cows & Bulls** is a classic code-breaking game.
- Create or join a room to start.
- Guess the secret number.
- 🐂 Bull = right digit & position.
- 🐄 Cow = right digit, wrong position.
                    """
                )


# ---------------------------------------------------------------------------
# Home screen
# ---------------------------------------------------------------------------

def home_screen() -> None:
    st.markdown(
        f"<h1 style='text-align:center; color:{COLOR_ACCENT};'>🐂 Cows & Bulls</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center; color:#8b949e;'>A classic number-guessing game</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    col_create, col_join = st.columns(2)

    with col_create:
        st.subheader("Create Room")
        mode = st.selectbox("Game Mode", ["Computer vs User", "User vs User"], key="home_mode")
        digit_count = st.selectbox("Digit Count", DIGIT_OPTIONS, index=0, key="home_digits")
        max_attempts = st.selectbox("Max Attempts", ATTEMPT_OPTIONS, index=1, key="home_attempts")

        if mode == "User vs User":
            num_players = st.number_input(
                "Number of Players",
                min_value=MIN_PLAYERS,
                max_value=MAX_PLAYERS,
                value=MIN_PLAYERS,
                step=1,
                key="home_num_players",
            )
            player_names = []
            for i in range(int(num_players)):
                name = st.text_input(
                    f"Player {i + 1} Name",
                    value=f"Player {i + 1}",
                    key=f"home_player_{i}",
                )
                player_names.append(name.strip() or f"Player {i + 1}")
        else:
            player_names = []

        if st.button("Create Room", key="btn_create"):
            code = generate_room_code()
            if mode == "Computer vs User":
                room = init_computer_room(code, digit_count, max_attempts)
            else:
                room = init_user_room(code, digit_count, max_attempts, player_names)
            rooms()[code] = room
            st.session_state["active_room"] = code
            st.rerun()

    with col_join:
        st.subheader("Join Room")
        join_code = st.text_input(
            "Room Code",
            max_chars=ROOM_CODE_LENGTH,
            key="home_join_code",
            placeholder="e.g. A3K9BZ",
        ).strip().upper()
        if st.button("Join Room", key="btn_join"):
            if join_code in rooms():
                st.session_state["active_room"] = join_code
                st.rerun()
            else:
                st.error("Room not found. Check the code and try again.")


# ---------------------------------------------------------------------------
# Computer vs User game screen
# ---------------------------------------------------------------------------

def computer_game_screen(room: dict) -> None:
    st.markdown(
        f"<h2 style='color:{COLOR_ACCENT};'>💻 Computer vs You</h2>",
        unsafe_allow_html=True,
    )

    history = room["history"]
    status = room["status"]
    secret = room["secret"]
    max_attempts = room["max_attempts"]
    digit_count = room["digit_count"]
    attempts_used = len(history)

    render_progress_bar(attempts_used, max_attempts)
    render_history(history, digit_count)

    if status == "won":
        st.markdown(
            f'<div class="banner-win">🎉 You cracked it in {attempts_used} attempt(s)! '
            f'The number was <b>{secret}</b>.</div>',
            unsafe_allow_html=True,
        )
        st.balloons()
        _computer_game_footer(room, history)
        return

    if status == "lost":
        st.markdown(
            f'<div class="banner-loss">💀 Out of attempts! '
            f'The secret was <b>{secret}</b>.</div>',
            unsafe_allow_html=True,
        )
        _computer_game_footer(room, history)
        return

    # Hint availability
    if attempts_used >= HINT_UNLOCK_AFTER and not room["hint_used"]:
        if st.button("💡 Use Hint (free, one per round)"):
            hint_text = get_hint(secret, history)
            room["hint_used"] = True
            st.session_state["pending_hint"] = hint_text
            st.rerun()

    if st.session_state.get("pending_hint") and room["hint_used"]:
        st.markdown(
            f'<div class="hint-box">💡 Hint: {st.session_state["pending_hint"]}</div>',
            unsafe_allow_html=True,
        )

    guess_input = st.text_input(
        f"Your {digit_count}-digit guess:",
        max_chars=digit_count,
        key=f"computer_guess_{attempts_used}",
        placeholder="e.g. " + "".join(str(d) for d in range(digit_count)),
    )

    if st.button("Submit Guess", key="btn_computer_submit"):
        valid, err = is_valid_guess(guess_input, digit_count)
        if not valid:
            st.warning(err)
        else:
            bulls, cows = score_guess(secret, guess_input)
            history.append(
                {"attempt": attempts_used + 1, "guess": guess_input, "bulls": bulls, "cows": cows}
            )
            if bulls == digit_count:
                room["status"] = "won"
                record_win(room, "Human", len(history))
                st.session_state.pop("pending_hint", None)
            elif len(history) >= max_attempts:
                room["status"] = "lost"
                record_loss(room, "Human", len(history))
                st.session_state.pop("pending_hint", None)
            st.rerun()


def _computer_game_footer(room: dict, history: list[dict]) -> None:
    st.divider()
    csv_data = build_csv(history)
    st.download_button(
        label="📥 Download Guess History (CSV)",
        data=csv_data,
        file_name="cows_bulls_history.csv",
        mime="text/csv",
    )
    if st.button("🔁 Play Again (same room)"):
        room["history"] = []
        room["status"] = "active"
        room["secret"] = generate_secret(room["digit_count"])
        room["hint_used"] = False
        st.session_state.pop("pending_hint", None)
        st.rerun()


# ---------------------------------------------------------------------------
# User vs User — setup phase
# ---------------------------------------------------------------------------

def user_setup_screen(room: dict) -> None:
    players = room["players"]
    setup_idx = room["setup_index"]
    digit_count = room["digit_count"]

    # Who is setting the secret for whom?
    # Player i sets the secret that Player (i+1) % n will need to guess.
    setter = players[setup_idx]
    receiver = players[(setup_idx + 1) % len(players)]

    st.markdown(
        f"<h2 style='color:{COLOR_ACCENT};'>👥 Setup Phase</h2>",
        unsafe_allow_html=True,
    )
    st.info(
        f"**{setter}** — enter a {digit_count}-digit secret number for **{receiver}** to guess.\n\n"
        "Hand the device to them afterwards and click Confirm."
    )

    secret_input = st.text_input(
        "Secret number (hidden):",
        type="password",
        max_chars=digit_count,
        key=f"setup_secret_{setup_idx}",
    )

    if st.button("Confirm & Hand Over", key=f"btn_setup_{setup_idx}"):
        valid, err = is_valid_guess(secret_input, digit_count)
        if not valid:
            st.warning(err)
        else:
            room["secrets"][receiver] = secret_input
            room["setup_index"] += 1
            if room["setup_index"] >= len(players):
                room["phase"] = "play"
            st.rerun()

    st.markdown(
        f"<small style='color:#8b949e;'>Setup progress: {setup_idx}/{len(players)}</small>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# User vs User — play phase
# ---------------------------------------------------------------------------

def user_play_screen(room: dict) -> None:
    players = room["players"]
    current_idx = room["current_player_index"]
    current_player = players[current_idx]
    digit_count = room["digit_count"]
    max_attempts = room["max_attempts"]

    history = room["histories"][current_player]
    status = room["statuses"][current_player]
    secret = room["secrets"][current_player]
    attempts_used = len(history)

    st.markdown(
        f"<h2 style='color:{COLOR_ACCENT};'>👥 {current_player}'s Turn</h2>",
        unsafe_allow_html=True,
    )

    render_progress_bar(attempts_used, max_attempts)
    render_history(history, digit_count)

    if status == "won":
        st.markdown(
            f'<div class="banner-win">🎉 {current_player} cracked it in {attempts_used} attempt(s)!</div>',
            unsafe_allow_html=True,
        )
        st.balloons()
    elif status == "lost":
        st.markdown(
            f'<div class="banner-loss">💀 {current_player} is out! Secret was <b>{secret}</b>.</div>',
            unsafe_allow_html=True,
        )

    if status == "active":
        # Hint
        hint_key = f"pending_hint_{current_player}"
        if attempts_used >= HINT_UNLOCK_AFTER and not room["hint_used"][current_player]:
            if st.button(f"💡 Use Hint for {current_player}"):
                hint_text = get_hint(secret, history)
                room["hint_used"][current_player] = True
                room["scoreboard"][current_player]["hints"] = (
                    room["scoreboard"][current_player].get("hints", 0) + 1
                )
                st.session_state[hint_key] = hint_text
                st.rerun()

        if st.session_state.get(hint_key) and room["hint_used"][current_player]:
            st.markdown(
                f'<div class="hint-box">💡 {st.session_state[hint_key]}</div>',
                unsafe_allow_html=True,
            )

        guess_input = st.text_input(
            f"{current_player} — enter {digit_count}-digit guess:",
            max_chars=digit_count,
            key=f"user_guess_{current_player}_{attempts_used}",
        )

        if st.button("Submit Guess", key=f"btn_user_submit_{current_idx}_{attempts_used}"):
            valid, err = is_valid_guess(guess_input, digit_count)
            if not valid:
                st.warning(err)
            else:
                bulls, cows = score_guess(secret, guess_input)
                history.append(
                    {"attempt": attempts_used + 1, "guess": guess_input, "bulls": bulls, "cows": cows}
                )
                if bulls == digit_count:
                    room["statuses"][current_player] = "won"
                    record_win(room, current_player, len(history))
                    st.session_state.pop(hint_key, None)
                elif len(history) >= max_attempts:
                    room["statuses"][current_player] = "lost"
                    record_loss(room, current_player, len(history))
                    st.session_state.pop(hint_key, None)
                st.rerun()

    all_done = all(s != "active" for s in room["statuses"].values())

    if all_done:
        room["phase"] = "finished"
        st.rerun()
    else:
        # Advance to next active player
        if status != "active" and st.button("➡️ Next Player"):
            _advance_player(room)
            st.rerun()
        elif status == "active":
            pass  # stay on current player's turn


def _advance_player(room: dict) -> None:
    players = room["players"]
    n = len(players)
    start = room["current_player_index"]
    for offset in range(1, n + 1):
        idx = (start + offset) % n
        if room["statuses"][players[idx]] == "active":
            room["current_player_index"] = idx
            return


# ---------------------------------------------------------------------------
# User vs User — finished / leaderboard
# ---------------------------------------------------------------------------

def user_finished_screen(room: dict) -> None:
    st.markdown(
        f"<h2 style='color:{COLOR_ACCENT};'>🏆 Game Over — Leaderboard</h2>",
        unsafe_allow_html=True,
    )

    board = room["scoreboard"]
    ranked = sorted(
        board.items(),
        key=lambda kv: (-kv[1]["wins"], kv[1]["total_attempts"]),
    )

    rows_html = ""
    for rank, (player, stats) in enumerate(ranked, start=1):
        fastest = stats["fastest"] if stats["fastest"] else "—"
        hints = stats.get("hints", 0)
        status_icon = "🏅" if rank == 1 else ""
        rows_html += (
            f"<tr>"
            f"<td>{rank} {status_icon}</td>"
            f"<td><b>{player}</b></td>"
            f"<td>{stats['wins']}</td>"
            f"<td>{stats['total_attempts']}</td>"
            f"<td>{fastest}</td>"
            f"<td>{hints}</td>"
            f"</tr>"
        )

    html = f"""
    <table class="guess-table">
      <thead>
        <tr>
          <th>Rank</th><th>Player</th><th>Wins</th>
          <th>Total Attempts</th><th>Best Round</th><th>Hints Used</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
    """
    st.markdown(html, unsafe_allow_html=True)

    # Export all histories
    all_rows = []
    for player in room["players"]:
        for entry in room["histories"][player]:
            all_rows.append({
                "player": player,
                "attempt": entry["attempt"],
                "guess": entry["guess"],
                "bulls": entry["bulls"],
                "cows": entry["cows"],
            })

    if all_rows:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["player", "attempt", "guess", "bulls", "cows"])
        writer.writeheader()
        writer.writerows(all_rows)
        st.download_button(
            label="📥 Download Full Game Log (CSV)",
            data=output.getvalue(),
            file_name="cows_bulls_full_log.csv",
            mime="text/csv",
        )


# ---------------------------------------------------------------------------
# Main game screen dispatcher
# ---------------------------------------------------------------------------

def game_screen(room: dict) -> None:
    mode = room["mode"]
    if mode == "computer":
        computer_game_screen(room)
    elif mode == "user":
        phase = room["phase"]
        if phase == "setup":
            user_setup_screen(room)
        elif phase == "play":
            user_play_screen(room)
        elif phase == "finished":
            user_finished_screen(room)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="Cows & Bulls",
        page_icon="🐂",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_css()

    room = current_room()
    render_sidebar(room)

    if room is None:
        home_screen()
    else:
        game_screen(room)


if __name__ == "__main__":
    main()
