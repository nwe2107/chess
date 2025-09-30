import pygame
import sys

# --- Constants ---
BOARD_SIZE = 8
SQUARE_SIZE = 64
MARGIN = 20
WINDOW_WIDTH = 2 * (BOARD_SIZE * SQUARE_SIZE + MARGIN)
WINDOW_HEIGHT = BOARD_SIZE * SQUARE_SIZE + 2 * MARGIN

# Colors
WHITE = (245, 245, 245)
BLACK = (30, 30, 30)
RED = (220, 40, 40)

# --- Initialize ---
pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Chess Game - Dual Boards")
font = pygame.font.SysFont("monospace", 20, bold=True)

# Load piece images (You’ll need PNGs for all chess pieces)
def load_images():
    pieces = {}
    pieces_names = ["bp", "br", "bn", "bb", "bq", "bk",
                    "wp", "wr", "wn", "wb", "wq", "wk"]
    for name in pieces_names:
        img = pygame.image.load(f"assets/{name}.png")  # put images in /assets
        img = pygame.transform.scale(img, (SQUARE_SIZE, SQUARE_SIZE))
        pieces[name] = img
    return pieces

pieces = load_images()

# --- Draw Functions ---
def draw_board(x_offset, flipped=False):
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            color = WHITE if (row + col) % 2 == 0 else BLACK
            rect = pygame.Rect(
                x_offset + col * SQUARE_SIZE,
                MARGIN + row * SQUARE_SIZE,
                SQUARE_SIZE, SQUARE_SIZE
            )
            pygame.draw.rect(screen, color, rect)

def draw_labels():
    label_white = font.render("YOU ARE WHITE", True, RED)
    label_black = font.render("YOU ARE BLACK", True, RED)
    screen.blit(label_white, (50, 0))
    screen.blit(label_black, (WINDOW_WIDTH // 2 + 50, 0))

# --- Main Loop ---
def main():
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        screen.fill((50, 50, 50))

        # Draw two boards
        draw_board(MARGIN, flipped=False)
        draw_board(WINDOW_WIDTH // 2 + MARGIN, flipped=True)

        # Labels
        draw_labels()

        pygame.display.flip()
        clock.tick(30)

if __name__ == "__main__":
    main()