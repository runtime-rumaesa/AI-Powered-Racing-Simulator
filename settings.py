"""Global settings for the AI Racing Simulator."""

import pygame

# --- Display & Window Settings ---
WIDTH = 1000
HEIGHT = 700
FPS = 60
TITLE = "AI Racing Simulator"

# --- Color Palette (RGB Format) ---
BACKGROUND = (40, 40, 40)
GRASS_COLOR = (46, 125, 50)
ROAD_COLOR = (66, 68, 74)
LINE_COLOR = (255, 255, 255)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (120, 120, 120)
DARK_GRAY = (40, 40, 40)
RED = (225, 40, 50)
GREEN = (60, 200, 80)
ORANGE = (245, 140, 30)
YELLOW = (250, 205, 40)
BLUE = (40, 120, 240)
PURPLE = (160, 70, 220)
CYAN = (40, 200, 220)

# --- Track Geometry & Spline Parameters ---
# Closed spline through these points (clockwise on screen).
# The first point is the start/finish line and the car drives to the right.
TRACK_POINTS = [
    (520, 130), (720, 125), (860, 165), (925, 260), (905, 370),
    (800, 430), (700, 410), (635, 440), (600, 500), (570, 565),
    (470, 600), (330, 595), (210, 565), (130, 500), (100, 400),
    (140, 295), (240, 215), (340, 160), (430, 130),
]
ROAD_HALF_WIDTH = 65          # Road is 130 px wide total
TRACK_WIDTH = ROAD_HALF_WIDTH * 2
TRACK_STEP = 4                # Distance between sampled centre-line points
CURB_ANGLE = 14               # Degrees of turn that earns curbs

# Waypoints & Checkpoints
NUM_WAYPOINTS = 64
CHECKPOINT_STEP = 8           # Every 8th waypoint is a lap checkpoint
CHECKPOINT_RADIUS = 70        # Distance threshold to clear a checkpoint
WAYPOINT_REACH_DISTANCE = 55  # AI switches to the next waypoint inside this radius
LANE_OFFSET = 20              # Grid / AI lane offset from the centre line

# --- Car Dynamics & Physics ---
CAR_LENGTH = 44
CAR_WIDTH = 22
CAR_COLOR = RED
CAR_START_X = 400
CAR_START_Y = 110
CAR_START_ANGLE = 0

CAR_ACCELERATION = 0.15   # Speed gained per frame while throttle is held
CAR_BRAKE_POWER = 0.30    # Speed lost per frame while braking
CAR_FRICTION = 0.05       # Speed lost per frame when coasting
CAR_MAX_SPEED = 5.5       # Forward limit (pixels per frame)
CAR_MAX_REVERSE = 2.0     # Reverse limit
CAR_TURN_SPEED = 3.2      # Max degrees turned per frame

# --- Fuel & Consumables ---
FUEL_MAX = 100.0
FUEL_USE_PER_FRAME = 0.05  # Fuel consumed per frame at full throttle

# --- Collisions & Damping ---
CAR_COLLISION_RADIUS = 16     # Bounding circle radius for car-vs-car impacts
CAR_COLLISION_DAMPING = 0.85  # Momentum retention after a car bump
WALL_BOUNCE = 0.3             # Bounce-back speed fraction off track boundaries

# --- Race Setup & AI Controls ---
NUM_LAPS = 3
TOTAL_LAPS = NUM_LAPS
NUM_AI_CARS = 4               # Up to 5 fit on starting grid
COUNTDOWN_SECONDS = 3
AI_COLORS = [BLUE, YELLOW, PURPLE, ORANGE, CYAN]
AI_SPEED_FACTOR = 0.95        # Equalizer scaling for AI speed envelope
AI_STRATEGIES = ["astar", "ga", "bfs", "baseline"]

# --- AI Search Graph (ai/search.py) ---
SEARCH_LANE_OFFSETS = [-36, -18, 0, 18, 36]   # Lateral pixel offsets across track width
SEARCH_LANE_CHANGE_PENALTY = 4.0              # Cost penalty per lane step (steering effort)

# --- HUD & Render Visual Effects ---
SKID_SPEED = 3.8              # Minimum drift velocity for skid mark spawning
HUD_SPEED_SCALE = 30          # Conversion scalar (px/frame -> displayed km/h)

# --- AI Optimization Genes (ai/optimization.py) ---
AI_DEFAULT_STYLE = {
    "top_speed": 1.0,       # Straightaway speed target fraction
    "acceleration": 1.0,    # Throttle intensity when below target speed
    "braking": 1.0,         # Braking intensity when above target speed
    "brake_margin": 0.5,    # Speed overshoot margin before braking (px/frame)
    "corner_speed": 0.45,   # Speed target fraction maintained in sharp turns
    "steering": 1 / 15,     # Steering sensitivity per degree of heading error
    "lookahead": WAYPOINT_REACH_DISTANCE,  # Target steering lookahead distance
}

OPT_EVALUATIONS = 600         # Lap simulations executed per tuning run
OPT_TIME_LIMIT = 25           # Timeout threshold for unfinished laps (seconds)
OPT_WALL_PENALTY = 1.0        # Lap fitness penalty per wall contact (seconds)
OPT_DNF_PENALTY = 20.0        # Fitness penalty for incomplete laps (seconds)

# --- Constraint Satisfaction Pit Scheduler (ai/csp.py) ---
TYRE_MAX_WEAR = 100.0         # Critical wear point causing tyre destruction
PIT_BAYS = 3                  # Active pit boxes available per lap
PIT_MAX_STOPS_PER_LAP = 2     # Maximum simultaneous servicing stops allowed
PIT_TYRE_SETS = 16            # Total fresh tyre inventory available for race
PIT_SAFETY_MARGIN = 0.10      # Reserved threshold before mandatory pit stop
PIT_DEMO_LAPS = 15            # Laps simulated during CSP demonstration runs