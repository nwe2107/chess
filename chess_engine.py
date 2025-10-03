#!/usr/bin/env python3
import os, sys
import pygame
import chess

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
    hint = turn_font.render("Press Q to quit    |    Press R to reset board", True, (180, 180, 180))
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
        # side to move is mated
        if board.turn == chess.WHITE:
            # White to move but mated -> Black delivered mate
            left_banner  = "YOU LOST – CHECKMATE"
            right_banner = "YOU WON – CHECKMATE"
        else:
            left_banner  = "YOU WON – CHECKMATE"
            right_banner = "YOU LOST – CHECKMATE"
        game_over = True
    elif board.is_stalemate():
        left_banner = right_banner = "DRAW – STALEMATE"
        game_over = True

# -------------------- Main loop --------------------
def main():
    global selected_sq, legal_targets, board, game_over, left_banner, right_banner
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


        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()