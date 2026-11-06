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
RED = (220, 50, 50)

# Track
ROAD_WIDTH = 150

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