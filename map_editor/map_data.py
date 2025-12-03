from dataclasses import dataclass

UNSET_FLAG = -1
MAX_MAP_WIDTH = 255
MAX_MAP_HEIGHT = 255

@dataclass
class PlayerData:
    start_x: int  # FixedPoint15_16
    start_y: int  # FixedPoint15_16
    start_angle_x: int  # FixedPoint15_16
    start_angle_y: int  # FixedPoint15_16
    
    def __init__(self, start_x: int | None = None, start_y: int | None = None,
                 start_angle_x: int | None = None, start_angle_y: int | None = None):
        """
        Initialize player data with optional start positions and angles.
        If any parameter is None, it is set to UNSET_FLAG.
        """
        self.start_x = start_x if start_x is not None else UNSET_FLAG
        self.start_y = start_y if start_y is not None else UNSET_FLAG
        self.start_angle_x = start_angle_x if start_angle_x is not None else UNSET_FLAG
        self.start_angle_y = start_angle_y if start_angle_y is not None else UNSET_FLAG
    
@dataclass
class MapData:
    width: int  # uint8
    height: int  # uint8
    tiles: list[int]  # list of uint8 tile indices (col-major)
    
    def __init__(self, width: int | None = None, height: int | None = None, tiles: list[int] | None = None):
        """
        Initialize map data with optional width, height, and tile list.
        If width or height is None, it is set to UNSET_FLAG.
        If tiles is None, it is initialized as an empty list.
        """
        self.width = width if width is not None else UNSET_FLAG
        self.height = height if height is not None else UNSET_FLAG
        self.tiles = tiles if tiles is not None else []