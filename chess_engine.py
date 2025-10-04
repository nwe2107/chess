#!/usr/bin/env python3
import os, sys
import pygame
import chess
import sqlite3
from datetime import datetime


# -------------------- Config --------------------
COORD_PAD = 18   # space around each board for file/rank labels
BOARD_SIZE = 8
SQ = 72
PADDING = 18
GAP_BETWEEN = 28
TOP_BANNER = 42
BOTTOM_BANNER = 84

W_BOARD = BOARD_SIZE * SQ + 2 * COORD_PAD
H_BOARD = BOARD_SIZE * SQ + 2 * COORD_PAD
WIN_W = (PADDING * 2) + W_BOARD + GAP_BETWEEN + W_BOARD
WIN_H = TOP_BANNER + H_BOARD + BOTTOM_BANNER

# Colors
BG     = (38, 38, 42)
LIGHT  = (235, 235, 235)
DARK   = (70, 70, 75)
ACCENT = (220, 40, 40)
HILITE = (255, 215, 0)
DOT    = (255, 100, 60)
OVERLAY_BG = (0, 0, 0, 170)   # translucent black
PANEL_BG   = (245, 245, 245)
PANEL_EDGE = (30, 30, 30)

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(HERE, "assets")
DB_PATH = os.path.join(HERE, "results.db")

# -------------------- Pygame init --------------------
pygame.init()
screen = pygame.display.set_mode((WIN_W, WIN_H))
pygame.display.set_caption("Chess – Dual Boards (engine + GUI)")
title_font = pygame.font.SysFont(None, 30, bold=True)
turn_font  = pygame.font.SysFont(None, 28, bold=True)
banner_font = pygame.font.SysFont(None, 36, bold=True)
check_font  = pygame.font.SysFont(None, 30, bold=True)
coord_font  = pygame.font.SysFont(None, 16, bold=True)
COORD_COLOR = (200, 200, 200)

LEFT_ANCHOR  = (PADDING, TOP_BANNER)
RIGHT_ANCHOR = (PADDING + W_BOARD + GAP_BETWEEN, TOP_BANNER)

# -------------------- Engine state --------------------
board = chess.Board()
selected_sq = None
legal_targets = set()
last_move = None
game_over = False
left_banner  = ""  # shows YOU WON / YOU LOST / DRAW
right_banner = ""

# -------------------- UI state --------------------
show_scoreboard = False
last_close_rect = None

# -------------------- Assets --------------------
def load_images(square_size):
    """Load piece images. Mapping is explicit to avoid mix-ups."""
    pieces = {}
    code_by_type = {
        chess.PAWN:   "p",
        chess.KNIGHT: "n",
        chess.BISHOP: "b",
        chess.ROOK:   "r",
        chess.QUEEN:  "q",
        chess.KING:   "k",
    }
    for ptype, letter in code_by_type.items():
        for color in (chess.WHITE, chess.BLACK):
            prefix = "w" if color == chess.WHITE else "b"
            code = f"{prefix}{letter}"
            path = os.path.join(ASSETS_DIR, f"{code}.png")
            img = None
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.smoothscale(img, (square_size, square_size))
            pieces[(ptype, color)] = img
    return pieces

PIECES = load_images(SQ)

# -------------------- Helpers: square <-> rc --------------------
def square_from_rc_white_view(r, c):
    return chess.square(c, 7 - r)

def square_from_rc_black_view(r, c):
    return chess.square(7 - c, r)

def rc_from_square_for_white_view(sq):
    f = chess.square_file(sq)
    r = chess.square_rank(sq)
    return (7 - r, f)

def rc_from_square_for_black_view(sq):
    f = chess.square_file(sq)
    r = chess.square_rank(sq)
    return (r, 7 - f)

# -------------------- Draw functions --------------------
def draw_board(anchor, flipped=False):
    ax, ay = anchor
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            rr = r if not flipped else (BOARD_SIZE - 1 - r)
            cc = c if not flipped else (BOARD_SIZE - 1 - c)
            color = LIGHT if (rr + cc) % 2 == 0 else DARK
            rect = pygame.Rect(ax + c * SQ + COORD_PAD, ay + r * SQ + COORD_PAD, SQ, SQ)
            pygame.draw.rect(screen, color, rect)

    # last move highlight
    if last_move:
        for sq in (last_move.from_square, last_move.to_square):
            rr, cc = (rc_from_square_for_white_view(sq) if not flipped
                      else rc_from_square_for_black_view(sq))
            rect = pygame.Rect(ax + COORD_PAD + cc * SQ, ay + COORD_PAD + rr * SQ, SQ, SQ)
            pygame.draw.rect(screen, HILITE, rect, width=3)

    # selected
    if selected_sq is not None:
        rr, cc = (rc_from_square_for_white_view(selected_sq) if not flipped
                  else rc_from_square_for_black_view(selected_sq))
        rect = pygame.Rect(ax + COORD_PAD + cc * SQ, ay + COORD_PAD + rr * SQ, SQ, SQ)
        pygame.draw.rect(screen, HILITE, rect, width=4)

    # legal targets dots
    if selected_sq is not None and legal_targets:
        for tsq in legal_targets:
            rr, cc = (rc_from_square_for_white_view(tsq) if not flipped
                      else rc_from_square_for_black_view(tsq))
            cx = ax + COORD_PAD + cc * SQ + SQ // 2
            cy = ay + COORD_PAD + rr * SQ + SQ // 2
            pygame.draw.circle(screen, DOT, (cx, cy), max(6, SQ // 10))


def draw_pieces(anchor, flipped=False):
    ax, ay = anchor
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if not piece:
            continue
        rr, cc = (rc_from_square_for_white_view(sq) if not flipped
                  else rc_from_square_for_black_view(sq))
        x = ax + COORD_PAD + cc * SQ
        y = ay + COORD_PAD + rr * SQ
        img = PIECES[(piece.piece_type, piece.color)]
        if img:
            screen.blit(img, (x, y))
        else:
            # very small fallback
            letter = "PNBRQK"[piece.piece_type-1]
            color = (20,20,20) if piece.color else (240,240,240)
            surf = turn_font.render(letter, True, color)
            rect = surf.get_rect(center=(x+SQ//2, y+SQ//2))
            screen.blit(surf, rect)

def draw_coords(anchor, flipped=False):
    """Draw file letters along the bottom edge squares and rank numbers on the left edge squares,
    respecting the board orientation (flipped for black). Labels are drawn inside the edge squares
    so we don't need extra window padding."""
    ax, ay = anchor

    files = "abcdefgh" if not flipped else "hgfedcba"
    ranks = "87654321" if not flipped else "12345678"

    # Files (below the bottom row)
    for c in range(8):
        ch = files[c].upper()
        surf = coord_font.render(ch, True, COORD_COLOR)
        rect = surf.get_rect(center=(ax + COORD_PAD + c * SQ + SQ//2,
                                     ay + H_BOARD - COORD_PAD//2))
        screen.blit(surf, rect)

    # Ranks (left of the left column)
    for r in range(8):
        ch = ranks[r]
        surf = coord_font.render(ch, True, COORD_COLOR)
        rect = surf.get_rect(center=(ax + COORD_PAD//2,
                                     ay + COORD_PAD + r * SQ + SQ//2))
        screen.blit(surf, rect)

def draw_banners():
    # titles
    screen.blit(title_font.render("YOU ARE WHITE", True, ACCENT), (LEFT_ANCHOR[0], 10))
    screen.blit(title_font.render("YOU ARE BLACK", True, ACCENT), (RIGHT_ANCHOR[0], 10))

    if not game_over:
        # normal turn banners
        left_turn = (board.turn == chess.WHITE)
        screen.blit(turn_font.render("YOUR TURN" if left_turn else "THEIR TURN", True, ACCENT),
                    (LEFT_ANCHOR[0], TOP_BANNER + H_BOARD + 8))
        screen.blit(turn_font.render("THEIR TURN" if left_turn else "YOUR TURN", True, ACCENT),
                    (RIGHT_ANCHOR[0], TOP_BANNER + H_BOARD + 8))
    else:
        # show outcome banners per side
        if left_banner:
            screen.blit(turn_font.render(left_banner, True, ACCENT),
                        (LEFT_ANCHOR[0], TOP_BANNER + H_BOARD + 8))
        if right_banner:
            screen.blit(turn_font.render(right_banner, True, ACCENT),
                        (RIGHT_ANCHOR[0], TOP_BANNER + H_BOARD + 8))

    # CHECK warning (only if game not over)
    if board.is_check() and not game_over:
        if board.turn == chess.WHITE:
            pos = (LEFT_ANCHOR[0] + 180,  TOP_BANNER - 32)
        else:
            pos = (RIGHT_ANCHOR[0] + 180, TOP_BANNER - 32)
        screen.blit(check_font.render("- CHECK!", True, ACCENT), pos)

    # Always show keystroke hints centered at the bottom
    hint = turn_font.render("Press Q to quit    |    Press R to reset board    |    Press S to scoreboard", True, (180, 180, 180))
    screen.blit(hint, (WIN_W // 2 - hint.get_width() // 2, WIN_H - 24))



# -------------------- Input helpers --------------------
def board_click_to_square(pos):
    mx, my = pos
    lx, ly = LEFT_ANCHOR
    if lx <= mx < lx + W_BOARD and ly <= my < ly + H_BOARD:
        c = (mx - lx - COORD_PAD) // SQ
        r = (my - ly - COORD_PAD) // SQ
        return square_from_rc_white_view(r, c)
    rx, ry = RIGHT_ANCHOR
    if rx <= mx < rx + W_BOARD and ry <= my < ry + H_BOARD:
        c = (mx - rx - COORD_PAD) // SQ
        r = (my - ry - COORD_PAD) // SQ
        return square_from_rc_black_view(r, c)
    return None

def update_legal_targets():
    global legal_targets
    legal_targets = set()
    if selected_sq is None: return
    for mv in board.legal_moves:
        if mv.from_square == selected_sq:
            legal_targets.add(mv.to_square)

# -------------------- db helpers --------------------

def db_init():
    with sqlite3.connect(DB_PATH) as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS results (
          id          INTEGER PRIMARY KEY,
          ts          TEXT NOT NULL,          -- ISO timestamp
          result      TEXT NOT NULL,          -- CHECKMATE/STALEMATE/RESIGN/...
          winner_col  TEXT,                   -- 'White'/'Black' or NULL on draw
          loser_col   TEXT,                   -- 'Black'/'White' or NULL on draw
          winner_name TEXT,
          loser_name  TEXT,
          move_count  INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_results_players ON results(winner_name, loser_name);
        CREATE INDEX IF NOT EXISTS idx_results_ts ON results(ts);
        """)

def db_insert(ts, result, winner_col, loser_col, winner_name, loser_name, move_count):
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            """INSERT INTO results
               (ts, result, winner_col, loser_col, winner_name, loser_name, move_count)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (ts, result, winner_col, loser_col, winner_name, loser_name, move_count)
        )

def db_fetch_recent(limit=12):
    with sqlite3.connect(DB_PATH) as con:
        return con.execute(
            "SELECT ts, result, winner_col, loser_col, winner_name, loser_name, move_count "
            "FROM results ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()

def db_fetch_top(limit=8):
    with sqlite3.connect(DB_PATH) as con:
        return con.execute(
            "SELECT winner_name, COUNT(*) AS wins "
            "FROM results WHERE winner_name IS NOT NULL "
            "GROUP BY winner_name ORDER BY wins DESC, winner_name ASC LIMIT ?", (limit,)
        ).fetchall()


# -------------------- Result prompt and scoreboard --------------------
def prompt_save_result(result_label, winner_color):
    """
    Modal prompt to enter winner & loser names, then save to SQLite.
    Controls: type text • TAB switches field • ENTER saves • ESC cancels
    """
    panel_w, panel_h = 560, 220
    rect = pygame.Rect((WIN_W - panel_w)//2, (WIN_H - panel_h)//2, panel_w, panel_h)
    field_w, field_h = 360, 40
    gap_y = 64

    winner_text, loser_text = "", ""
    active = 0  # 0 winner, 1 loser
    who_won = "White" if winner_color is chess.WHITE else ("Black" if winner_color is chess.BLACK else "—")
    title = banner_font.render(f"Result: {result_label}", True, (20,20,20))
    sub   = turn_font.render(f"Winner: {who_won}", True, (20,20,20))

    while True:
        overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA); overlay.fill((0,0,0,160))
        screen.blit(overlay, (0,0))

        pygame.draw.rect(screen, (245,245,245), rect, border_radius=12)
        pygame.draw.rect(screen, (40,40,40), rect, width=3, border_radius=12)
        screen.blit(title, (rect.centerx - title.get_width()//2, rect.y + 12))
        screen.blit(sub,   (rect.centerx - sub.get_width()//2,   rect.y + 54))

        win_label = turn_font.render("Winner name:", True, (30,30,30))
        screen.blit(win_label, (rect.x + 22, rect.y + 96))
        win_box = pygame.Rect(rect.x + 170, rect.y + 92, field_w, field_h)
        pygame.draw.rect(screen, (255,255,255), win_box, border_radius=8)
        pygame.draw.rect(screen, (230,80,80) if active==0 else (120,120,120), win_box, width=2, border_radius=8)
        screen.blit(turn_font.render(winner_text, True, (30,30,30)), (win_box.x + 10, win_box.y + 8))

        lose_label = turn_font.render("Loser name:", True, (30,30,30))
        screen.blit(lose_label, (rect.x + 22, rect.y + 96 + gap_y))
        lose_box = pygame.Rect(rect.x + 170, rect.y + 92 + gap_y, field_w, field_h)
        pygame.draw.rect(screen, (255,255,255), lose_box, border_radius=8)
        pygame.draw.rect(screen, (230,80,80) if active==1 else (120,120,120), lose_box, width=2, border_radius=8)
        screen.blit(turn_font.render(loser_text, True, (30,30,30)), (lose_box.x + 10, lose_box.y + 8))

        foot = coord_font.render("TAB switch • ENTER save • ESC cancel", True, (60,60,60))
        screen.blit(foot, (rect.centerx - foot.get_width()//2, rect.bottom - 26))

        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: return
                if e.key == pygame.K_TAB: active = 1 - active
                elif e.key == pygame.K_RETURN:
                    ts = datetime.now().isoformat(timespec="seconds")
                    winner_col = "White" if winner_color is chess.WHITE else ("Black" if winner_color is chess.BLACK else None)
                    loser_col  = "Black" if winner_color is chess.WHITE else ("White" if winner_color is chess.BLACK else None)
                    db_insert(ts, result_label, winner_col, loser_col,
                              winner_text.strip() or None, loser_text.strip() or None,
                              len(board.move_stack))
                    return
                elif e.key == pygame.K_BACKSPACE:
                    if active==0 and winner_text: winner_text = winner_text[:-1]
                    elif active==1 and loser_text: loser_text = loser_text[:-1]
                else:
                    ch = e.unicode
                    if ch and 32 <= ord(ch) <= 126:
                        if active==0 and len(winner_text) < 30: winner_text += ch
                        elif active==1 and len(loser_text) < 30: loser_text += ch


def draw_scoreboard():
    """Top overlay showing Top Players + Recent Games. Returns the close button rect."""
    global last_close_rect
    panel_h = int(WIN_H * 0.68)
    rect = pygame.Rect(12, 8, WIN_W - 24, panel_h)

    pygame.draw.rect(screen, (245,245,245), rect, border_radius=14)
    pygame.draw.rect(screen, (40,40,40), rect, width=3, border_radius=14)

    title = banner_font.render("Scoreboard", True, (20,20,20))
    screen.blit(title, (rect.x + 16, rect.y + 10))

    close_rect = pygame.Rect(rect.right - 46, rect.y + 10, 36, 28)
    pygame.draw.rect(screen, (230,80,80), close_rect, border_radius=6)
    xlbl = turn_font.render("X", True, (255,255,255))
    screen.blit(xlbl, (close_rect.centerx - xlbl.get_width()//2, close_rect.centery - xlbl.get_height()//2))
    last_close_rect = close_rect

    recent = db_fetch_recent(12)
    top    = db_fetch_top(10)

    left_x  = rect.x + 20
    right_x = rect.centerx + 20
    y0 = rect.y + 54

    h1 = turn_font.render("Top Players (wins)", True, (20,20,20))
    screen.blit(h1, (left_x, y0))
    y = y0 + 8 + h1.get_height()
    row_font = pygame.font.SysFont(None, 22)
    if top:
        for i, (name, wins) in enumerate(top):
            line = f"{i+1:>2}. {name or '(unknown)'} — {wins}"
            screen.blit(row_font.render(line, True, (30,30,30)), (left_x, y + i*24))
    else:
        screen.blit(row_font.render("(no wins yet)", True, (120,120,120)), (left_x, y))

    h2 = turn_font.render("Recent Games", True, (20,20,20))
    screen.blit(h2, (right_x, y0))
    y2 = y0 + 8 + h2.get_height()

    small = pygame.font.SysFont(None, 20)
    if recent:
        for i, (ts, result, wcol, lcol, wname, lname, moves) in enumerate(recent):
            label = f"{ts}  •  {result}"
            if wcol:
                label += f"  •  {wcol} ({wname or '?'}) beat {lcol} ({lname or '?'})"
            else:
                label += "  •  Draw"
            label += f"  •  {moves} moves"
            screen.blit(small.render(label, True, (40,40,40)), (right_x, y2 + i*22))
    else:
        screen.blit(small.render("(no games yet)", True, (120,120,120)), (right_x, y2))

    return close_rect

# -------------------- Promotion Picker --------------------
def choose_promotion(color):
    """Modal overlay to pick Q/R/B/N. Returns a chess.* constant."""
    # build small panel with 4 buttons showing piece PNGs
    piece_types = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
    codes = {chess.QUEEN:"q", chess.ROOK:"r", chess.BISHOP:"b", chess.KNIGHT:"n"}
    prefix = "w" if color == chess.WHITE else "b"

    # panel geometry
    panel_w, panel_h = 420, 140
    rect = pygame.Rect((WIN_W - panel_w)//2, (WIN_H - panel_h)//2, panel_w, panel_h)
    btn_w, btn_h = 80, 80
    gap = 20
    btns = []
    x0 = rect.x + (panel_w - (4*btn_w + 3*gap))//2
    y0 = rect.y + (panel_h - btn_h)//2

    # pre-render buttons
    buttons = []
    for i,ptype in enumerate(piece_types):
        code = f"{prefix}{codes[ptype]}"
        img = PIECES.get((ptype, color))
        if img is None:
            # tiny fallback: letter
            img = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
            letter = "QRBN"[i]
            s = banner_font.render(letter, True, (30,30,30))
            img.blit(s, (SQ//2 - s.get_width()//2, SQ//2 - s.get_height()//2))
        scaled = pygame.transform.smoothscale(img, (btn_w, btn_h))
        rect_btn = pygame.Rect(x0 + i*(btn_w + gap), y0, btn_w, btn_h)
        buttons.append((ptype, scaled, rect_btn))

    # modal event loop
    while True:
        # overlay
        overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        overlay.fill(OVERLAY_BG)
        screen.blit(overlay, (0,0))

        pygame.draw.rect(screen, PANEL_BG, rect, border_radius=12)
        pygame.draw.rect(screen, PANEL_EDGE, rect, width=3, border_radius=12)

        title = banner_font.render("Promote pawn to…", True, (20,20,20))
        screen.blit(title, (rect.centerx - title.get_width()//2, rect.y + 10))

        for ptype, surf, rbtn in buttons:
            screen.blit(surf, rbtn.topleft)
            pygame.draw.rect(screen, (50,50,50), rbtn, width=2, border_radius=8)

        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_q):
                return chess.QUEEN  # default if cancelled
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for ptype, _, rbtn in buttons:
                    if rbtn.collidepoint(e.pos):
                        return ptype

# -------------------- Move execution --------------------
def attempt_move(src_sq, dst_sq):
    """Make a legal move; if promotion is needed, open the picker."""
    global last_move
    move = chess.Move(src_sq, dst_sq)

    # If plain move is illegal, but a promotion could make it legal:
    if move not in board.legal_moves:
        piece = board.piece_at(src_sq)
        if piece and piece.piece_type == chess.PAWN:
            rank = chess.square_rank(dst_sq)
            if (piece.color == chess.WHITE and rank == 7) or (piece.color == chess.BLACK and rank == 0):
                promo = choose_promotion(piece.color)
                move = chess.Move(src_sq, dst_sq, promotion=promo)

    if move in board.legal_moves:
        board.push(move)
        last_move = move
        return True
    return False

def update_game_state_after_move():
    """Check checkmate/stalemate and set banners accordingly."""
    global game_over, left_banner, right_banner
    if board.is_checkmate():
        if board.turn == chess.WHITE:
            left_banner, right_banner = "YOU LOST – CHECKMATE", "YOU WON – CHECKMATE"
            winner = chess.BLACK
        else:
            left_banner, right_banner = "YOU WON – CHECKMATE", "YOU LOST – CHECKMATE"
            winner = chess.WHITE
        game_over = True
        prompt_save_result("CHECKMATE", winner)
    elif board.is_stalemate():
        left_banner = right_banner = "DRAW – STALEMATE"
        game_over = True
        prompt_save_result("STALEMATE", None)

# -------------------- Main loop --------------------
def main():
    global selected_sq, legal_targets, board, game_over, left_banner, right_banner, show_scoreboard, last_close_rect
    clock = pygame.time.Clock()

    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_q, pygame.K_ESCAPE):
                    pygame.quit(); sys.exit()
                if e.key == pygame.K_r:  # quick reset
                    board = chess.Board()
                    selected_sq = None
                    legal_targets = set()
                    game_over = False
                    left_banner = right_banner = ""
                if e.key == pygame.K_s:
                    show_scoreboard = not show_scoreboard
                    continue
                if show_scoreboard and e.key == pygame.K_ESCAPE:
                    show_scoreboard = False
                    continue

            if show_scoreboard and e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if last_close_rect and last_close_rect.collidepoint(e.pos):
                    show_scoreboard = False
                continue

            if not game_over and e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                sq = board_click_to_square(e.pos)
                if sq is None:
                    continue
                piece = board.piece_at(sq)

                if selected_sq is None:
                    if piece and piece.color == board.turn:
                        selected_sq = sq
                        update_legal_targets()
                else:
                    if sq in legal_targets and attempt_move(selected_sq, sq):
                        selected_sq = None
                        legal_targets = set()
                        update_game_state_after_move()
                    else:
                        # re-select your own piece
                        if piece and piece.color == board.turn:
                            selected_sq = sq
                            update_legal_targets()

        # draw
        screen.fill(BG)
        draw_board(LEFT_ANCHOR, flipped=False)
        draw_board(RIGHT_ANCHOR, flipped=True)
        draw_pieces(LEFT_ANCHOR, flipped=False)
        draw_pieces(RIGHT_ANCHOR, flipped=True)
        draw_coords(LEFT_ANCHOR, flipped=False)
        draw_coords(RIGHT_ANCHOR, flipped=True)
        draw_banners()
        if show_scoreboard:
            last_close_rect = draw_scoreboard()


        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    db_init()

    main()