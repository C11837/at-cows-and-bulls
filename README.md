# 🐂 Cows & Bulls

A fully interactive **Cows & Bulls** number-guessing game built with [Streamlit](https://streamlit.io) and managed by [uv](https://github.com/astral-sh/uv).

---

## How to Play

**Cows & Bulls** is a classic code-breaking game where one side picks a secret number and the other tries to guess it.

- Guess a number with the configured digit count (e.g. `1234` for 4 digits). All digits must be **unique**.
- After each guess you receive feedback:
  - 🐂 **Bull** — correct digit in the correct position.
  - 🐄 **Cow** — correct digit in the wrong position.
- Keep guessing until you score all Bulls (win) or exhaust your attempts (loss).
- A **hint** (one per round, free) unlocks after 4 failed attempts — it reveals one digit from the secret without revealing its position.

### Game Modes

| Mode | Description |
|---|---|
| **Computer vs User** | The app generates a secret number; one player guesses it. |
| **User vs User** | 2–10 players take turns. During the **setup phase** each player secretly enters the number that the next player will have to guess (device is passed around). Players then guess in rotation until everyone has either won or run out of attempts. |

---

## Prerequisites

- Python **≥ 3.11**
- [uv](https://github.com/astral-sh/uv) — install with:
  ```bash
  # macOS / Linux
  curl -Ls https://astral.sh/uv/install.sh | sh

  # Windows (PowerShell)
  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

---

## Setup & Run

```bash
uv run streamlit run app.py
```

That's it. `uv` will create a virtual environment and install all dependencies automatically on first run.

---

## Features

| Feature | Details |
|---|---|
| Game modes | Computer vs User · User vs User (2–10 players) |
| Room system | Create or join rooms via a 6-char code |
| Digit settings | 2 / 3 / 4 unique digits |
| Attempt limits | 5 / 7 / 10 attempts per round |
| Hint system | Free hint after 4 failed attempts (one per round) |
| Guess history | Styled HTML table with per-row animations (flash on bull/cow, shake on miss) |
| Progress bar | Colour shifts green → orange → red as attempts run down |
| Leaderboard | End-of-game rankings by wins, then fewest total attempts; shows best round and hints used |
| CSV export | Download full guess history (per-player log in User vs User) |
| Dark UI | GitHub-inspired dark theme (navy background, gold accents) |

---

## Screenshots

> _(Add screenshots here after running the app)_

---

## Project Structure

```
cows-and-bulls/
├── app.py           # Single-file Streamlit application
├── main.py          # Minimal CLI entry-point (placeholder)
├── pyproject.toml   # uv project manifest (requires streamlit ≥ 1.55.0)
└── README.md
```
