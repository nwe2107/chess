#!/usr/bin/env python3
import sys, os
import pygame

# ---------- Config ----------
BOARD_SIZE = 8
SQ = 72
PADDING = 18
GAP_BETWEEN = 28
TOP_BANNER = 42
BOTTOM_BANNER = 42

W_BOARD = BOARD_SIZE * SQ
H_BOARD = BOARD_SIZE * SQ
WIN_W = (PADDING * 2) + W_BOARD + GAP_BETWEEN + W_BOARD
WIN_H = TOP_BANNER + H_BOARD + BOTTOM_BANNER

# Colors
BG     = (38, 38, 42)
LIGHT  = (235, 235, 235)
DARK   = (70, 70, 75)
ACCENT = (220, 40, 40)
HILITE = (255, 215, 0)
BAD    = (230, 80, 80)

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(HERE, "assets")

# ---------- Helpers over our board representation ----------
# Board is 8x8 array of codes like "wp","bq", or None.
# Row 0 is top (Black back rank). Row 7 is bottom (White back rank).
# White pawns move "up" (row -1). Black pawns move "down" (row +1).

def start_position():
    e = [None]*8
    b = [e[:] for _ in range(8)]
    b[0] = ["br", "bn", "bb", "bq", "bk", "bb", "bn", "br"]
    b[1] = ["bp"] * 8
    b[6] = ["wp"] * 8
    b[7] = ["wr", "wn", "wb", "wq", "wk", "wb", "wn", "wr"]
    return b

def side_of(code):  # 'w' or 'b'
    return code[0] if code else None

def kind_of(code):  # 'p','r','n','b','q','k'
    return code[1] if code else None

def in_bounds(r,c):
    return 0 <= r < 8 and 0 <= c < 8

def is_path_clear(board, r0, c0, r1, c1):
    """For sliding pieces (rook/bishop/queen): ensure no blockers between src and dst."""
    dr = (r1 - r0)
    dc = (c1 - c0)
    step_r = 0 if dr == 0 else (1 if dr > 0 else -1)
    step_c = 0 if dc == 0 else (1 if dc > 0 else -1)
    r, c = r0 + step_r, c0 + step_c
    while (r, c) != (r1, c1):
        if board[r][c] is not None:
            return False
        r += step_r
        c += step_c
    return True

def legal_move_basic(board, src, dst):
    """Basic piece movement rules (no checks, no castling, no en passant)."""
    sr, sc = src
    dr, dc = dst
    if not in_bounds(dr, dc): return False
    piece = board[sr][sc]
    if piece is None: return False

    us = side_of(piece)
    them_piece = board[dr][dc]
    if them_piece and side_of(them_piece) == us:
        return False  # can't capture own piece

    k = kind_of(piece)

    # Deltas
    rr = dr - sr
    cc = dc - sc
    abs_r = abs(rr)
    abs_c = abs(cc)

    if k == 'n':  # Knight
        return (abs_r, abs_c) in {(1,2),(2,1)}

    if k == 'k':  # King
        return max(abs_r, abs_c) == 1

    if k == 'r':  # Rook
        if rr != 0 and cc != 0: return False
        return is_path_clear(board, sr, sc, dr, dc)

    if k == 'b':  # Bishop
        if abs_r != abs_c: return False
        return is_path_clear(board, sr, sc, dr, dc)

    if k == 'q':  # Queen
        if rr == 0 or cc == 0 or abs_r == abs_c:
            return is_path_clear(board, sr, sc, dr, dc)
        return False

    if k == 'p':  # Pawn
        dir_ = -1 if us == 'w' else 1  # white moves up (-1), black moves down (+1)
        start_row = 6 if us == 'w' else 1

        # forward move (no capture)
        if cc == 0:
            # one step
            if rr == dir_ and board[dr][dc] is None:
                return True
            # two steps from start
            if sr == start_row and rr == 2*dir_:
                mid = sr + dir_
                if board[mid][dc] is None and board[dr][dc] is None:
                    return True
            return False

        # diagonal capture
        if abs_c == 1 and rr == dir_:
            return them_piece is not None  # capture only if enemy present

        return False

    return False

# ---------- Pygame drawing / UI ----------
pygame.init()
screen = pygame.display.set_mode((WIN_W, WIN_H))
pygame.display.set_caption("Chess – Dual Boards (Light Rules)")
title_font = pygame.font.SysFont(None, 30, bold=True)
turn_font  = pygame.font.SysFont(None, 28, bold=True)

def load_images(square_size):
    pieces = {}
    codes = ["bp","br","bn","bb","bq","bk","wp","wr","wn","wb","wq","wk"]
    for code in codes:
        path = os.path.join(ASSETS_DIR, f"{code}.png")
        if not os.path.exists(path):
            pieces[code] = None
            continue
        img = pygame.image.load(path).convert_alpha()
        img = pygame.transform.smoothscale(img, (square_size, square_size))
        pieces[code] = img
    return pieces

PIECES = load_images(SQ)

board = start_position()
selected = None
turn = 'w'  # 'w' or 'b'

LEFT_ANCHOR  = (PADDING, TOP_BANNER)
RIGHT_ANCHOR = (PADDING + W_BOARD + GAP_BETWEEN, TOP_BANNER)

def draw_board(anchor, flipped=False):
    ax, ay = anchor
    for r in range(8):
        for c in range(8):
            rr = r if not flipped else (7 - r)
            cc = c if not flipped else (7 - c)
            color = LIGHT if (rr + cc) % 2 == 0 else DARK
            rect = pygame.Rect(ax + c*SQ, ay + r*SQ, SQ, SQ)
            pygame.draw.rect(screen, color, rect)

            # selected highlight (show on both views)
            if selected is not None:
                sr, sc = selected
                if (rr, cc) == (sr, sc):
                    pygame.draw.rect(screen, HILITE, rect, width=3)

def draw_pieces(anchor, flipped=False):
    ax, ay = anchor
    for r in range(8):
        for c in range(8):
            rr = r if not flipped else (7 - r)
            cc = c if not flipped else (7 - c)
            code = board[rr][cc]
            if not code: continue
            img = PIECES.get(code)
            if img:
                screen.blit(img, (ax + c*SQ, ay + r*SQ))
            else:
                # fallback letters
                color = (20,20,20) if side_of(code) == 'b' else (240,240,240)
                glyph = code[1].upper() if side_of(code) == 'w' else code[1]
                f = pygame.font.SysFont(None, int(SQ*0.7), bold=True)
                surf = f.render(glyph, True, color)
                rect = surf.get_rect(center=(ax + c*SQ + SQ//2, ay + r*SQ + SQ//2))
                screen.blit(surf, rect)

def draw_banners():
    screen.blit(title_font.render("YOU ARE WHITE", True, ACCENT), (LEFT_ANCHOR[0], 10))
    screen.blit(title_font.render("YOU ARE BLACK", True, ACCENT), (RIGHT_ANCHOR[0], 10))
    left_turn = (turn == 'w')
    screen.blit(turn_font.render("YOUR TURN" if left_turn else "THEIR TURN", True, ACCENT),
                (LEFT_ANCHOR[0], TOP_BANNER + H_BOARD + 8))
    screen.blit(turn_font.render("THEIR TURN" if left_turn else "YOUR TURN", True, ACCENT),
                (RIGHT_ANCHOR[0], TOP_BANNER + H_BOARD + 8))

def board_from_mouse(pos):
    """Return canonical (row, col) (white-at-bottom perspective) from mouse pos.
       NOTE: Source selection is restricted by side/board (see below)."""
    mx, my = pos
    lx, ly = LEFT_ANCHOR
    if lx <= mx < lx + W_BOARD and ly <= my < ly + H_BOARD:
        # white perspective
        c = (mx - lx) // SQ
        r = (my - ly) // SQ
        return (r, c), 'left'
    rx, ry = RIGHT_ANCHOR
    if rx <= mx < rx + W_BOARD and ry <= my < ry + H_BOARD:
        # black perspective: flip back to canonical
        c = (mx - rx) // SQ
        r = (my - ry) // SQ
        return (7 - r, 7 - c), 'right'
    return None, None

def main():
    global selected, turn
    clock = pygame.time.Clock()

    # optional: brief instructions in console
    print("Light rules version: no check/castling/en-passant. Pawns move/capture correctly. Turn-based.")
    print("Restriction: When it's White's turn, you must select on the LEFT board; for Black, on the RIGHT board.")

    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_q, pygame.K_ESCAPE):
                pygame.quit(); sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                (sq, which) = board_from_mouse(e.pos)
                if sq is None:
                    continue
                r, c = sq

                if selected is None:
                    # --- Selection phase ---
                    code = board[r][c]
                    if not code:   # empty
                        continue
                    # must select your own color
                    if side_of(code) != turn:
                        continue
                    # must select on your side's board
                    if (turn == 'w' and which != 'left') or (turn == 'b' and which != 'right'):
                        continue
                    selected = (r, c)
                else:
                    # --- Move attempt ---
                    sr, sc = selected
                    if (r, c) == (sr, sc):
                        selected = None
                        continue

                    if legal_move_basic(board, (sr, sc), (r, c)):
                        # execute
                        moving = board[sr][sc]
                        board[r][c] = moving
                        board[sr][sc] = None
                        selected = None
                        # swap turn
                        turn = 'b' if turn == 'w' else 'w'
                    else:
                        # allow re-select if clicking own piece of side to move on correct board
                        code = board[r][c]
                        if code and side_of(code) == turn and ((turn=='w' and which=='left') or (turn=='b' and which=='right')):
                            selected = (r, c)
                        # else keep the current selection

        screen.fill(BG)
        draw_board(LEFT_ANCHOR, flipped=False)
        draw_board(RIGHT_ANCHOR, flipped=True)
        draw_pieces(LEFT_ANCHOR, flipped=False)
        draw_pieces(RIGHT_ANCHOR, flipped=True)
        draw_banners()
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()