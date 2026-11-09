"""Global settings for the AI Racing Simulator."""

# Window
WIDTH = 1000
HEIGHT = 700
FPS = 60
TITLE = "AI Racing Simulator"

# Colors (R, G, B)
BACKGROUND = (40, 40, 40)
GRASS_COLOR = (46, 125, 50)
ROAD_COLOR = (66, 68, 74)
LINE_COLOR = (255, 255, 255)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (225, 40, 50)
GREEN = (60, 200, 80)
ORANGE = (245, 140, 30)
YELLOW = (250, 205, 40)
BLUE = (40, 120, 240)
PURPLE = (160, 70, 220)
CYAN = (40, 200, 220)

# Track: a closed spline through these points (clockwise on screen).
# The first point is the start/finish line and the car drives to the right.
TRACK_POINTS = [
    (520, 130), (720, 125), (860, 165), (925, 260), (905, 370),
    (800, 430), (700, 410), (635, 440), (600, 500), (570, 565),
    (470, 600), (330, 595), (210, 565), (130, 500), (100, 400),
    (140, 295), (240, 215), (340, 160), (430, 130),
]
ROAD_HALF_WIDTH = 65          # road is 104 px wide
TRACK_STEP = 4                # distance between sampled centre-line points
CURB_ANGLE = 14               # degrees of turn that earns curbs

# Waypoints / checkpoints (Phase 3 will turn the waypoints into a graph)
NUM_WAYPOINTS = 64
CHECKPOINT_STEP = 8           # every 8th waypoint is a lap checkpoint
CHECKPOINT_RADIUS = 70        # how close a car must get to "hit" one
WAYPOINT_REACH_DISTANCE = 55  # AI switches to the next waypoint this close
LANE_OFFSET = 20              # grid / AI lane offset from the centre line

# Car
CAR_LENGTH = 44
CAR_WIDTH = 22
CAR_COLOR = RED
CAR_START_X = 400
CAR_START_Y = 110
CAR_START_ANGLE = 0

CAR_ACCELERATION = 0.15   # speed gained per frame while throttle is held
CAR_BRAKE_POWER = 0.30    # speed lost per frame while braking
CAR_FRICTION = 0.05       # speed lost per frame when coasting
CAR_MAX_SPEED = 5.5       # forward limit (pixels per frame)
CAR_MAX_REVERSE = 2.0     # reverse limit
CAR_TURN_SPEED = 3.2      # max degrees turned per frame

# Fuel
FUEL_MAX = 100.0
FUEL_USE_PER_FRAME = 0.05  # at full throttle

# Collisions
CAR_COLLISION_RADIUS = 16     # cars are treated as circles for car-vs-car hits
CAR_COLLISION_DAMPING = 0.85  # speed kept after a car-vs-car bump
WALL_BOUNCE = 0.3             # fraction of speed returned (reversed) off a wall

# Race
NUM_LAPS = 3
NUM_AI_CARS = 4               # up to 5 fit on the starting grid
COUNTDOWN_SECONDS = 3
AI_COLORS = [BLUE, YELLOW, PURPLE, ORANGE, CYAN]
AI_SPEED_FACTOR = 0.95        # all AI cars are identical, so route quality decides the race
AI_STRATEGIES = ["astar", "ga", "bfs", "baseline"]  # how each AI opponent plans (and drives): astar, hc, ga, bfs, baseline

# Search graph (ai/search.py): every waypoint station has several lanes
SEARCH_LANE_OFFSETS = [-36, -18, 0, 18, 36]   # pixels left (-) / right (+) of the centre line
SEARCH_LANE_CHANGE_PENALTY = 4.0              # extra cost per lane stepped (steering effort)

# Effects / HUD
SKID_SPEED = 3.8              # steering hard above this speed leaves skid marks
HUD_SPEED_SCALE = 30          # pixels/frame -> displayed km/h

# Driving style of an AI car. These numbers are the "genes" that ai/optimization.py tunes.
AI_DEFAULT_STYLE = {
    "top_speed": 1.0,       # fraction of the car's max speed it aims for on straights
    "acceleration": 1.0,    # how hard the throttle is pressed when below target speed
    "braking": 1.0,         # how hard the brake is pressed when above target speed
    "brake_margin": 0.5,    # how far above target speed before it brakes (px/frame)
    "corner_speed": 0.45,   # fraction of target speed kept in the sharpest corners
    "steering": 1 / 15,     # steering response (steer per degree of heading error)
    "lookahead": WAYPOINT_REACH_DISTANCE,  # distance at which it aims for the next waypoint
}
"""Global settings for the AI Racing Simulator."""

# Window
WIDTH = 1000
HEIGHT = 700
FPS = 60
TITLE = "AI Racing Simulator"

# Colors (R, G, B)
BACKGROUND = (40, 40, 40)
GRASS_COLOR = (46, 125, 50)
ROAD_COLOR = (66, 68, 74)
LINE_COLOR = (255, 255, 255)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (225, 40, 50)
GREEN = (60, 200, 80)
ORANGE = (245, 140, 30)
YELLOW = (250, 205, 40)
BLUE = (40, 120, 240)
PURPLE = (160, 70, 220)
CYAN = (40, 200, 220)

# Track: a closed spline through these points (clockwise on screen).
# The first point is the start/finish line and the car drives to the right.
TRACK_POINTS = [
    (520, 130), (720, 125), (860, 165), (925, 260), (905, 370),
    (800, 430), (700, 410), (635, 440), (600, 500), (570, 565),
    (470, 600), (330, 595), (210, 565), (130, 500), (100, 400),
    (140, 295), (240, 215), (340, 160), (430, 130),
]
ROAD_HALF_WIDTH = 65          # road is 104 px wide
TRACK_STEP = 4                # distance between sampled centre-line points
CURB_ANGLE = 14               # degrees of turn that earns curbs

# Waypoints / checkpoints (Phase 3 will turn the waypoints into a graph)
NUM_WAYPOINTS = 64
CHECKPOINT_STEP = 8           # every 8th waypoint is a lap checkpoint
CHECKPOINT_RADIUS = 70        # how close a car must get to "hit" one
WAYPOINT_REACH_DISTANCE = 55  # AI switches to the next waypoint this close
LANE_OFFSET = 20              # grid / AI lane offset from the centre line

# Car
CAR_LENGTH = 44
CAR_WIDTH = 22
CAR_COLOR = RED
CAR_START_X = 400
CAR_START_Y = 110
CAR_START_ANGLE = 0

CAR_ACCELERATION = 0.15   # speed gained per frame while throttle is held
CAR_BRAKE_POWER = 0.30    # speed lost per frame while braking
CAR_FRICTION = 0.05       # speed lost per frame when coasting
CAR_MAX_SPEED = 5.5       # forward limit (pixels per frame)
CAR_MAX_REVERSE = 2.0     # reverse limit
CAR_TURN_SPEED = 3.2      # max degrees turned per frame

# Fuel
FUEL_MAX = 100.0
FUEL_USE_PER_FRAME = 0.05  # at full throttle

# Collisions
CAR_COLLISION_RADIUS = 16     # cars are treated as circles for car-vs-car hits
CAR_COLLISION_DAMPING = 0.85  # speed kept after a car-vs-car bump
WALL_BOUNCE = 0.3             # fraction of speed returned (reversed) off a wall

# Race
NUM_LAPS = 3
NUM_AI_CARS = 4               # up to 5 fit on the starting grid
COUNTDOWN_SECONDS = 3
AI_COLORS = [BLUE, YELLOW, PURPLE, ORANGE, CYAN]
AI_SPEED_FACTOR = 0.95        # all AI cars are identical, so route quality decides the race
AI_STRATEGIES = ["astar", "ga", "bfs", "baseline"]  # how each AI opponent plans (and drives): astar, hc, ga, bfs, baseline

# Search graph (ai/search.py): every waypoint station has several lanes
SEARCH_LANE_OFFSETS = [-36, -18, 0, 18, 36]   # pixels left (-) / right (+) of the centre line
SEARCH_LANE_CHANGE_PENALTY = 4.0              # extra cost per lane stepped (steering effort)

# Effects / HUD
SKID_SPEED = 3.8              # steering hard above this speed leaves skid marks
HUD_SPEED_SCALE = 30          # pixels/frame -> displayed km/h

# Driving style of an AI car. These numbers are the "genes" that ai/optimization.py tunes.
AI_DEFAULT_STYLE = {
    "top_speed": 1.0,       # fraction of the car's max speed it aims for on straights
    "acceleration": 1.0,    # how hard the throttle is pressed when below target speed
    "braking": 1.0,         # how hard the brake is pressed when above target speed
    "brake_margin": 0.5,    # how far above target speed before it brakes (px/frame)
    "corner_speed": 0.45,   # fraction of target speed kept in the sharpest corners
    "steering": 1 / 15,     # steering response (steer per degree of heading error)
    "lookahead": WAYPOINT_REACH_DISTANCE,  # distance at which it aims for the next waypoint
}

# Optimization (ai/optimization.py)
OPT_EVALUATIONS = 600         # lap simulations each algorithm may run
OPT_TIME_LIMIT = 25           # seconds before a simulated lap counts as unfinished
OPT_WALL_PENALTY = 1.0        # seconds added to the fitness per wall hit
OPT_DNF_PENALTY = 20.0        # seconds added when the lap is not finished

# Pit-stop scheduling (ai/csp.py)
TYRE_MAX_WEAR = 100.0         # tyre wear at which a tyre is destroyed
PIT_BAYS = 3                  # pit boxes (a stop uses one bay for one lap slot)
PIT_MAX_STOPS_PER_LAP = 2     # pit crews: stops allowed in the same lap
PIT_TYRE_SETS = 16            # tyre sets in stock = stops allowed in the whole race
PIT_SAFETY_MARGIN = 0.10      # fuel / tyre life always kept in reserve (fraction)
PIT_DEMO_LAPS = 15            # race length used by the CSP demo and evaluation
# Optimization (ai/optimization.py)
OPT_EVALUATIONS = 600         # lap simulations each algorithm may run
OPT_TIME_LIMIT = 25           # seconds before a simulated lap counts as unfinished
OPT_WALL_PENALTY = 1.0        # seconds added to the fitness per wall hit
OPT_DNF_PENALTY = 20.0        # seconds added when the lap is not finished