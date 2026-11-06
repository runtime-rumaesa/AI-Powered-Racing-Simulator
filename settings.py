"""Global settings for the AI Racing Simulator."""

# Window
WIDTH = 800
HEIGHT = 600
FPS = 60
TITLE = "AI Racing Simulator"

# Colors (R, G, B)
BACKGROUND = (40, 40, 40)
GRASS_COLOR = (34, 139, 34)
ROAD_COLOR = (70, 70, 70)
LINE_COLOR = (255, 255, 255)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 50, 50)
GREEN = (60, 200, 80)
ORANGE = (240, 150, 30)
YELLOW = (240, 200, 40)
BLUE = (50, 100, 220)
PURPLE = (160, 60, 200)

# Track: the road is the ring between two ellipses
ROAD_WIDTH = 150                  # (legacy, the ellipse track doesn't use it)
TRACK_CENTER = (400, 300)
OUTER_A, OUTER_B = 320, 240       # outer ellipse half-width / half-height
INNER_A, INNER_B = 180, 140       # inner ellipse half-width / half-height
MID_A = (OUTER_A + INNER_A) // 2  # middle of the road (racing line)
MID_B = (OUTER_B + INNER_B) // 2
FINISH_LINE_X = 400

# Waypoints / checkpoints (Phase 3 will turn the waypoints into a graph)
NUM_WAYPOINTS = 32
CHECKPOINT_STEP = 4               # every 4th waypoint is a lap checkpoint
CHECKPOINT_RADIUS = 80            # how close a car must get to "hit" one
WAYPOINT_REACH_DISTANCE = 50      # AI switches to the next waypoint this close

# Car
CAR_LENGTH = 40
CAR_WIDTH = 20
CAR_COLOR = RED
CAR_START_X = 400
CAR_START_Y = 110
CAR_START_ANGLE = 0       # degrees; 0 = facing right (clockwise lap)

CAR_ACCELERATION = 0.15   # speed gained per frame while throttle is held
CAR_BRAKE_POWER = 0.30    # speed lost per frame while braking
CAR_FRICTION = 0.05       # speed lost per frame when coasting
CAR_MAX_SPEED = 5.0       # forward limit (pixels per frame)
CAR_MAX_REVERSE = 2.0     # reverse limit
CAR_TURN_SPEED = 3.0      # max degrees turned per frame

# Fuel
FUEL_MAX = 100.0
FUEL_USE_PER_FRAME = 0.05  # at full throttle

# Collisions
CAR_COLLISION_RADIUS = 15     # cars are treated as circles for car-vs-car hits
CAR_COLLISION_DAMPING = 0.85  # speed kept after a car-vs-car bump
WALL_BOUNCE = 0.3             # fraction of speed returned (reversed) off a wall

# Race
NUM_LAPS = 3
NUM_AI_CARS = 3               # up to 5 fit on the starting grid
COUNTDOWN_SECONDS = 3
AI_COLORS = [BLUE, YELLOW, PURPLE, ORANGE, GREEN]
AI_SPEED_FACTORS = [0.95, 0.90, 0.85, 0.80, 0.75]  # fraction of player top speed

# HUD
HUD_SPEED_SCALE = 30          # pixels/frame -> displayed km/h