#!/usr/bin/env python3
import os, sys
import pygame
import chess

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
DOT    = (255, 100, 60)

# Paths
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(HERE, "assets")

# ---------- Pygame init ----------
pygame.init()
screen = pygame.display.set_mode((WIN_W, WIN_H))
pygame.display.set_caption("Chess – Dual Boards (python-chess)")
title_font = pygame.font.SysFont(None, 30, bold=True)
turn_font  = pygame.font.SysFont(None, 28, bold=True)
piece_font = pygame.font.SysFont(None, int(SQ * 0.7), bold=True)

LEFT_ANCHOR  = (PADDING, TOP_BANNER)
RIGHT_ANCHOR = (PADDING + W_BOARD + GAP_BETWEEN, TOP_BANNER)

# ---------- Engine ----------
board = chess.Board()   # python-chess engine state
selected_sq = None      # a chess square index, e.g., chess.E2
legal_targets_from_selected = set()
last_move = None

# ---------- Assets ----------
LETTER = {
    chess.PAWN:   ("P", "p"),
    chess.ROOK:   ("R", "r"),
    chess.KNIGHT: ("N", "n"),
    chess.BISHOP: ("B", "b"),
    chess.QUEEN:  ("Q", "q"),
    chess.KING:   ("K", "k"),
}

def load_images(square_size):
    pieces = {}

    # correct mapping from python-chess piece_type → single-letter code
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

# ---------- Square mapping helpers ----------
def square_from_rc_white_view(r, c):
    """Top-left is a8. r=0..7, c=0..7 -> chess.square file=c, rank=7-r"""
    return chess.square(c, 7 - r)

def square_from_rc_black_view(r, c):
    """Top-left on right board is h1. r=0..7, c=0..7 -> flip to canonical"""
    return chess.square(7 - c, r)

def rc_from_square_for_white_view(sq):
    """chess square -> row/col for left board"""
    file = chess.square_file(sq)
    rank = chess.square_rank(sq)
    return (7 - rank, file)

def rc_from_square_for_black_view(sq):
    """chess square -> row/col for right board (black perspective)"""
    file = chess.square_file(sq)
    rank = chess.square_rank(sq)
    # invert both
    return (rank, 7 - file)

# ---------- UI helpers ----------
def draw_board(anchor, flipped=False):
    ax, ay = anchor
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            rr = r if not flipped else (BOARD_SIZE - 1 - r)
            cc = c if not flipped else (BOARD_SIZE - 1 - c)
            color = LIGHT if (rr + cc) % 2 == 0 else DARK
            rect = pygame.Rect(ax + c * SQ, ay + r * SQ, SQ, SQ)
            pygame.draw.rect(screen, color, rect)

    # highlight last move (both views)
    if last_move:
        for sq in (last_move.from_square, last_move.to_square):
            rr, cc = (rc_from_square_for_white_view(sq) if not flipped
                      else rc_from_square_for_black_view(sq))
            rect = pygame.Rect(ax + cc * SQ, ay + rr * SQ, SQ, SQ)
            pygame.draw.rect(screen, HILITE, rect, width=3)

    # highlight selected
    if selected_sq is not None:
        rr, cc = (rc_from_square_for_white_view(selected_sq) if not flipped
                  else rc_from_square_for_black_view(selected_sq))
        rect = pygame.Rect(ax + cc * SQ, ay + rr * SQ, SQ, SQ)
        pygame.draw.rect(screen, HILITE, rect, width=4)

    # draw dots for legal targets from selected
    if selected_sq is not None and legal_targets_from_selected:
        for tsq in legal_targets_from_selected:
            rr, cc = (rc_from_square_for_white_view(tsq) if not flipped
                      else rc_from_square_for_black_view(tsq))
            cx = ax + cc * SQ + SQ // 2
            cy = ay + rr * SQ + SQ // 2
            pygame.draw.circle(screen, DOT, (cx, cy), max(6, SQ // 10))

def draw_pieces(anchor, flipped=False):
    ax, ay = anchor
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if not piece:
            continue
        rr, cc = (rc_from_square_for_white_view(sq) if not flipped
                  else rc_from_square_for_black_view(sq))
        x = ax + cc * SQ
        y = ay + rr * SQ
        img = PIECES[(piece.piece_type, piece.color)]
        if img:
            screen.blit(img, (x, y))
        else:
            # fallback: draw letter
            letter = LETTER[piece.piece_type][0 if piece.color == chess.WHITE else 1]
            surf = piece_font.render(letter, True, (20, 20, 20) if piece.color else (235, 235, 235))
            rect = surf.get_rect(center=(x + SQ//2, y + SQ//2))
            screen.blit(surf, rect)

def draw_banners():
    screen.blit(title_font.render("YOU ARE WHITE", True, ACCENT), (LEFT_ANCHOR[0], 10))
    screen.blit(title_font.render("YOU ARE BLACK", True, ACCENT), (RIGHT_ANCHOR[0], 10))
    left_turn = board.turn == chess.WHITE
    screen.blit(turn_font.render("YOUR TURN" if left_turn else "THEIR TURN", True, ACCENT),
                (LEFT_ANCHOR[0], TOP_BANNER + H_BOARD + 8))
    screen.blit(turn_font.render("THEIR TURN" if left_turn else "YOUR TURN", True, ACCENT),
                (RIGHT_ANCHOR[0], TOP_BANNER + H_BOARD + 8))

def board_click_to_square(pos):
    """Translate mouse pos to a chess square (canonical coords)."""
    mx, my = pos
    lx, ly = LEFT_ANCHOR
    if lx <= mx < lx + W_BOARD and ly <= my < ly + H_BOARD:
        c = (mx - lx) // SQ
        r = (my - ly) // SQ
        return square_from_rc_white_view(r, c)
    rx, ry = RIGHT_ANCHOR
    if rx <= mx < rx + W_BOARD and ry <= my < ry + H_BOARD:
        c = (mx - rx) // SQ
        r = (my - ry) // SQ
        return square_from_rc_black_view(r, c)
    return None

def update_legal_targets_from_selected():
    global legal_targets_from_selected
    legal_targets_from_selected = set()
    if selected_sq is None:
        return
    for mv in board.legal_moves:
        if mv.from_square == selected_sq:
            legal_targets_from_selected.add(mv.to_square)

def make_move(src_sq, dst_sq):
    """Attempt a legal move from src -> dst (handles castling automatically)."""
    global last_move
    # Promotion: auto queen if pawn reaches last rank
    move = chess.Move(src_sq, dst_sq)
    if move not in board.legal_moves:
        # try with promotion to queen
        piece = board.piece_at(src_sq)
        if piece and piece.piece_type == chess.PAWN:
            rank = chess.square_rank(dst_sq)
            if (piece.color == chess.WHITE and rank == 7) or (piece.color == chess.BLACK and rank == 0):
                move = chess.Move(src_sq, dst_sq, promotion=chess.QUEEN)

    if move in board.legal_moves:
        board.push(move)
        last_move = move
        return True
    return False

# ---------- Main loop ----------
def main():
    global selected_sq
    clock = pygame.time.Clock()

    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_q, pygame.K_ESCAPE):
                pygame.quit(); sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                sq = board_click_to_square(e.pos)
                if sq is None:
                    continue
                piece = board.piece_at(sq)

                if selected_sq is None:
                    # select a piece that belongs to the side to move
                    if piece and piece.color == board.turn:
                        selected_sq = sq
                        update_legal_targets_from_selected()
                else:
                    # if clicked a legal target -> try to move
                    if sq in legal_targets_from_selected and make_move(selected_sq, sq):
                        selected_sq = None
                        update_legal_targets_from_selected()
                    else:
                        # re-select if we clicked our own piece; otherwise keep selection
                        if piece and piece.color == board.turn:
                            selected_sq = sq
                            update_legal_targets_from_selected()

        # ---- Draw ----
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