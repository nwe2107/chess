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
BG = (38, 38, 42)
LIGHT = (235, 235, 235)
DARK = (70, 70, 75)
ACCENT = (220, 40, 40)
HILITE = (255, 215, 0)

# Absolute path to assets (avoids “working directory” issues)
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(HERE, "assets")

# ---------- Board setup ----------
def start_position():
    e = [None] * 8
    b = [e[:] for _ in range(8)]
    b[0] = ["br", "bn", "bb", "bq", "bk", "bb", "bn", "br"]
    b[1] = ["bp"] * 8
    b[6] = ["wp"] * 8
    b[7] = ["wr", "wn", "wb", "wq", "wk", "wb", "wn", "wr"]
    return b

# ---------- Pygame init ----------
pygame.init()
screen = pygame.display.set_mode((WIN_W, WIN_H))
pygame.display.set_caption("Chess – Dual Boards (Images)")
title_font = pygame.font.SysFont(None, 30, bold=True)
turn_font  = pygame.font.SysFont(None, 28, bold=True)

# ---------- Load piece images ----------
def load_images(square_size):
    pieces = {}
    codes = ["bp","br","bn","bb","bq","bk","wp","wr","wn","wb","wq","wk"]
    for code in codes:
        path = os.path.join(ASSETS_DIR, f"{code}.png")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing piece image: {path}")
        img = pygame.image.load(path).convert_alpha()
        img = pygame.transform.smoothscale(img, (square_size, square_size))
        pieces[code] = img
    return pieces

PIECES = load_images(SQ)

board = start_position()
selected = None
turn = "w"        # 'w' or 'b'
LEFT_ANCHOR  = (PADDING, TOP_BANNER)
RIGHT_ANCHOR = (PADDING + W_BOARD + GAP_BETWEEN, TOP_BANNER)

# ---------- Draw helpers ----------
def draw_board(anchor, flipped=False):
    ax, ay = anchor
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            rr = r if not flipped else (BOARD_SIZE - 1 - r)
            cc = c if not flipped else (BOARD_SIZE - 1 - c)
            color = LIGHT if (rr + cc) % 2 == 0 else DARK
            rect = pygame.Rect(ax + c * SQ, ay + r * SQ, SQ, SQ)
            pygame.draw.rect(screen, color, rect)
            if selected is not None:
                sr, sc = selected
                if (rr, cc) == (sr, sc):
                    pygame.draw.rect(screen, HILITE, rect, width=3)

def draw_pieces(anchor, flipped=False):
    ax, ay = anchor
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            rr = r if not flipped else (BOARD_SIZE - 1 - r)
            cc = c if not flipped else (BOARD_SIZE - 1 - c)
            code = board[rr][cc]
            if code:
                img = PIECES[code]
                screen.blit(img, (ax + c * SQ, ay + r * SQ))

def draw_banners():
    screen.blit(title_font.render("YOU ARE WHITE", True, ACCENT), (LEFT_ANCHOR[0], 10))
    screen.blit(title_font.render("YOU ARE BLACK", True, ACCENT), (RIGHT_ANCHOR[0], 10))
    left_turn  = turn == "w"
    screen.blit(turn_font.render("YOUR TURN" if left_turn else "THEIR TURN", True, ACCENT),
                (LEFT_ANCHOR[0], TOP_BANNER + H_BOARD + 8))
    screen.blit(turn_font.render("THEIR TURN" if left_turn else "YOUR TURN", True, ACCENT),
                (RIGHT_ANCHOR[0], TOP_BANNER + H_BOARD + 8))

def board_from_mouse(pos):
    mx, my = pos
    lx, ly = LEFT_ANCHOR
    if lx <= mx < lx + W_BOARD and ly <= my < ly + H_BOARD:
        return ((my - ly) // SQ, (mx - lx) // SQ)                     # white view
    rx, ry = RIGHT_ANCHOR
    if rx <= mx < rx + W_BOARD and ry <= my < ry + H_BOARD:
        # flip back to canonical coords
        r = (my - ry) // SQ
        c = (mx - rx) // SQ
        return (BOARD_SIZE - 1 - r, BOARD_SIZE - 1 - c)
    return None

def side_of(code): return code[0] if code else None

def try_move(src, dst):
    global turn
    sr, sc = src; dr, dc = dst
    piece = board[sr][sc]
    if not piece or side_of(piece) != turn or src == dst:
        return False
    board[dr][dc] = piece
    board[sr][sc] = None
    turn = "b" if turn == "w" else "w"
    return True

# ---------- Main loop ----------
def main():
    global selected
    clock = pygame.time.Clock()
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_q, pygame.K_ESCAPE):
                pygame.quit(); sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                sq = board_from_mouse(e.pos)
                if sq is not None:
                    if selected is None:
                        r, c = sq
                        if board[r][c] and side_of(board[r][c]) == turn:
                            selected = (r, c)
                    else:
                        if try_move(selected, sq):
                            selected = None
                        else:
                            r, c = sq
                            if board[r][c] and side_of(board[r][c]) == turn:
                                selected = (r, c)

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