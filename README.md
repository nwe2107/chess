# Chess Dual-Board GUI
A small Python/pygame chess GUI that shows the same game from the White and Black perspectives side by side, uses `python-chess` for the rules engine, and records finished games to a local SQLite database for a simple scoreboard.

## Features
- Two synchronized boards (White view on the left, Black view on the right) with move highlights and legal-move dots.
- Keyboard shortcuts to reset, quit, and toggle an in-app scoreboard overlay.
- Optional name entry when a game ends; results are stored in `results.db` for top-players and recent-games views.
- Uses PNG piece art from `assets/` with automatic scaling.

## Requirements
- Python 3 (any modern 3.x should work).
- `pip` to install Python packages.
- A desktop environment where pygame can open a window (SDL display).

Project dependencies are listed in `requirements.txt`:
- `python-chess`
- `pygame`
- `chess` (light helper library; kept for compatibility with earlier installs)

## Setup
1) Download the code (clone the repo or unzip the folder) to your machine.  
2) From the project root, create and activate a virtual environment (optional but recommended):
```
python3 -m venv .venv
source .venv/bin/activate
```
On Windows, activate with `.venv\Scripts\activate`.
3) Install dependencies:
```
pip install -r requirements.txt
```

## Run
From the project root, launch the GUI:
```
python chess_engine.py
```

The first run will create `results.db` in the same directory if it does not exist.

## Controls and gameplay
- Click a piece, then click a highlighted destination to move; last move squares stay outlined.
- `R` resets to a fresh starting position.
- `S` toggles the scoreboard overlay (close with `S`, `Esc`, or the on-screen X).
- `Q` or `Esc` quits the app.
- When a game ends by checkmate or stalemate, a modal prompts for winner/loser names; `Tab` switches fields, `Enter` saves, `Esc` cancels.

## Data and assets
- Piece PNGs live in `assets/` and are loaded automatically.
- Finished-game records are stored in `results.db`. Delete this file to clear history.

## Repo layout
- `chess_engine.py` — pygame UI and chess logic.
- `assets/` — piece sprites.
- `results.db` — SQLite database created at runtime.
- `requirements.txt` — Python dependencies.
