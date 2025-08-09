import pygame
import numpy as np
import random
import heapq

# Initialize Pygame
pygame.init()
WIDTH, HEIGHT = 900, 700
TILE_SIZE = 10
GRID_WIDTH, GRID_HEIGHT = WIDTH // TILE_SIZE, HEIGHT // TILE_SIZE

screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# Generate a random map with 30% water
map_grid = np.random.choice(["land", "water"], size=(GRID_WIDTH, GRID_HEIGHT), p=[0.9, 0.1])

# Store land positions for fast lookup
land_positions = np.array(np.where(map_grid == "land")).T

# Set timer for vegetation spawning every 10 seconds
VEG_SPAWN_EVENT = pygame.USEREVENT + 1
pygame.time.set_timer(VEG_SPAWN_EVENT, 10 * 1000)  # 10 seconds (1000 ms per second)

MAX_VEG_COUNT = 100  # Limit for vegetation to prevent overflow

def draw_map():
    """Draws the entire map once for better performance."""
    land_color = (34, 139, 34)
    water_color = (0, 0, 255)
    for (x, y) in land_positions:
        pygame.draw.rect(screen, land_color, (x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))
    for x in range(GRID_WIDTH):
        for y in range(GRID_HEIGHT):
            if map_grid[x, y] == "water":
                pygame.draw.rect(screen, water_color, (x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))

# -------------------------
# A* PATHFINDING FUNCTION
# -------------------------
def astar(start, goal, grid):
    """Finds path from start to goal using A* algorithm, avoiding water tiles."""
    def heuristic(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])  # Manhattan distance

    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}

    while open_set:
        current = heapq.heappop(open_set)[1]
        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path

        for dx, dy in [(0,1),(1,0),(0,-1),(-1,0)]:
            neighbor = (current[0] + dx, current[1] + dy)
            if 0 <= neighbor[0] < GRID_WIDTH and 0 <= neighbor[1] < GRID_HEIGHT:
                if grid[neighbor[0], neighbor[1]] == "water":  # Can't walk on water
                    continue
                tentative_g_score = g_score[current] + 1
                if tentative_g_score < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                    if neighbor not in [i[1] for i in open_set]:
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))
    return []  # No path found

# -------------------------
# END OF ASTAR ADDITION
# -------------------------

class Veg:
    def __init__(self, v_x, v_y):
        self.v_x, self.v_y = v_x, v_y
        self.status = "alive"

    def draw(self):
        if self.status == "alive":
            pygame.draw.circle(screen, (255, 0, 0),
                               (self.v_x * TILE_SIZE + TILE_SIZE // 2,
                                self.v_y * TILE_SIZE + TILE_SIZE // 2), 5)

class Creature:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.thirst = 100
        self.hunger= 0
        self.target_veg = [()]
        self.path = []
        self.status = ""
        self.stuck_counter = 0
        self.last_pos = (x, y)
        # initialize adjacent_tiles
        self.adjacent_tiles = [(self.x + dx, self.y + dy) for dx in range(-2, 3) for dy in range(-2, 3)]

    def update_adjacent_tiles(self):
        """Recompute adjacent tiles each time creature moves/checks."""
        self.adjacent_tiles = [
            (self.x + dx, self.y + dy)
            for dx in range(-2, 3)
            for dy in range(-2, 3)
            if 0 <= self.x + dx < GRID_WIDTH and 0 <= self.y + dy < GRID_HEIGHT
        ]

    def find_closest_veg(self):
        """Finds the closest vegetation. Returns True if there is veg in adjacent tiles (within radius)."""
        # Refresh adjacency
        self.update_adjacent_tiles()

        closest = None
        min_dist = float('inf')
        # scan all veg to find closest; also check if any are inside adjacent_tiles
        for v in vege:
            if v.status != "alive":
                continue
            vx, vy = v.v_x, v.v_y
            # if a veg coord is in adjacent tiles -> immediate detection
            if (vx, vy) in self.adjacent_tiles:
                self.target = v
                print("found adjacent veg at", (vx, vy))
                return True
            else:
                return False
    def wander_randomly(self):
        if (self.x, self.y) == self.last_pos:
            self.stuck_counter += 1
        else:
            self.stuck_counter = 0
            self.last_pos = (self.x, self.y)
            self.path.append(self.last_pos)

        if self.stuck_counter < 10:
            dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0),(1, 1), (1, -1), (-1, 1), (-1, -1)])
            new_x, new_y = self.x + dx, self.y + dy
            if 0 <= new_x < GRID_WIDTH and 0 <= new_y < GRID_HEIGHT and map_grid[new_x, new_y] != "water":
             self.x, self.y = new_x, new_y
             hunger=-2
             thirst=-3
             if hunger<20 or thirst<40:
                 self.seek_target()


    def seek_target(self):
        """Find closest veg or water and set path using A*."""
        if self.hunger < 20:
            if not self.status:
                self.status = "hungry"
            if self.find_closest_veg():
                self.path = astar((self.x, self.y), self.target_veg, map_grid)
        if self.thirst < 40:
            if not self.status:
                self.status = "thirsty"

        # Later you can add thirst logic hereA
        # if self.thirst < X: ... find water ...


    def follow_path(self):
        """Follow the path from A*."""
        if self.path:
            next_step = self.path.pop(0)
            self.x, self.y = next_step


    def drink_water(self):
        """Replenish thirst if water is nearby."""
        # ensure adjacency is up to date
        self.update_adjacent_tiles()
        if self.thirst < 40:
            if any(0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT and map_grid[x, y] == "water"
                   for x, y in self.adjacent_tiles):
                self.thirst += 20
                print("drinking")
                self.status = "Drinking"
            else:
                self.thirst -= 1
        else:
            self.thirst -= 1

    def draw(self):
        """Draws the creature and status text."""
        pygame.draw.circle(screen, (0, 255, 0),
                           (self.x * TILE_SIZE + TILE_SIZE // 2, self.y * TILE_SIZE + TILE_SIZE // 2), 5)
        font = pygame.font.Font(None, 16)
        text = font.render(self.status, True, (255, 255, 255))
        screen.blit(text, (self.x * TILE_SIZE, self.y * TILE_SIZE - 10))

# Initialize simulation
creatures = [Creature(*random.choice(land_positions)) for _ in range(5)]
vege = [Veg(*random.choice(land_positions)) for _ in range(50)]

# Game loop
running = True
while running:
    screen.fill((0, 0, 0))
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == VEG_SPAWN_EVENT and len(vege) < MAX_VEG_COUNT:
            vege.append(Veg(*random.choice(land_positions)))

    draw_map()
    creatures = [c for c in creatures if c.thirst > 0]

    for c in creatures:
        c.status = ""  # reset status at start of frame
        c.wander_randomly()
        c.drink_water()
        c.draw()

    for v in vege:
        v.draw()

    pygame.display.flip()
    clock.tick(2)

pygame.quit()

