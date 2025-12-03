from PySide6.QtCore import QObject, Signal
from pathlib import Path
import logging

from map_data import *
from xip_utils import export_map_to_xip

class Project(QObject):
    map_changed = Signal()
    map_loaded = Signal()
    dirty_changed = Signal(bool)  # dirty flag changed
    map_saved = Signal(str) # error message or empty if success (currently unused)
    
    def __init__(self, assets_path: Path):
        super().__init__()
        self.map: MapData = MapData()
        self.player: PlayerData = PlayerData()
        
        self._assets_path = assets_path
        # unsaved changes flag
        self._dirty = False
        
    @property
    def dirty(self) -> bool:
        return self._dirty
    
    @dirty.setter
    def dirty(self, value: bool):
        self._dirty = value
        self.dirty_changed.emit(value)
        
    def new_map(self, width: int, height: int):
        logging.info(f"Creating new map with size {width}x{height}")
        
        # new empty map 
        self.map = MapData(width=width, height=height, tiles=[0] * (width * height))
        self.dirty = True
        self.map_loaded.emit()
        
    def in_bounds(self, x: int, y: int) -> bool:
        if self.map is None:
            return False
        return 0 <= x < self.map.width and 0 <= y < self.map.height
    
    def _coord_to_index(self, x: int, y: int) -> int:
        assert self.map is not None
        return y + self.map.height * x  # col major storage
    
    def get_tile(self, x: int, y: int) -> int:
        if self.map is None or not self.in_bounds(x, y):
            return -1
        return self.map.tiles[self._coord_to_index(x, y)] 
        
    def set_tile(self, x: int, y: int, tile_id: int):
        if self.map is None or not self.in_bounds(x, y):
            return
        
        index = self._coord_to_index(x, y)
        self.map.tiles[index] = tile_id
        
        self.dirty = True
        self.map_changed.emit()
        
    def set_player_start_pos(self, start_x: int, start_y: int) -> None:
        """
        Set player start position in FixedPoint15_16 format.
        
        @param start_x: FixedPoint15_16 x coordinate of player start position
        @param start_y: FixedPoint15_16 y coordinate of player start position
        """
        self.player.start_x = start_x
        self.player.start_y = start_y
    
        self.dirty = True
        
    def set_player_start_angle(self, start_angle_x: int, start_angle_y: int) -> None:
        """
        Set player start angle in FixedPoint15_16 format.
        
        @param start_angle_x: FixedPoint15_16 x component of direction vector
        @param start_angle_y: FixedPoint15_16 y component of direction vector
        """
        
        self.player.start_angle_x = start_angle_x
        self.player.start_angle_y = start_angle_y
    
        self.dirty = True
        
    def _validate_map_before_save(self) -> list[str]:
        error_msgs = []
        
        if self.map is None or self.player is None:
            msg = "No map or player data to save."
            error_msgs.append(msg)    
        
        if self.map.width == UNSET_FLAG or self.map.height == UNSET_FLAG:
            msg = "Map has zero width or height, cannot save."
            error_msgs.append(msg)
        
        if self.map.width > MAX_MAP_WIDTH or self.map.height > MAX_MAP_HEIGHT:
            msg = f"Map dimensions exceed maximum size of {MAX_MAP_WIDTH}x{MAX_MAP_HEIGHT}."
            error_msgs.append(msg)
        
        if len(self.map.tiles) != self.map.width * self.map.height:
            msg = "Map tile data size does not match width and height."
            error_msgs.append(msg)
        
        if len(self.map.tiles) == 0:
            msg = "Map has no tile data to save."
            error_msgs.append(msg)
        
        if self.player.start_x == UNSET_FLAG and self.player.start_y == UNSET_FLAG:
            msg = "Player start position is not set."
            error_msgs.append(msg)
        
        if self.player.start_angle_x == UNSET_FLAG and self.player.start_angle_y == UNSET_FLAG:
            msg = "Player start angle is not set."
            error_msgs.append(msg)
        
        for msg in error_msgs:  
            logging.error(msg)
            
        return error_msgs
        
    def save_map(self, filename: str):
        error_msgs = self._validate_map_before_save()
        
        if error_msgs:
            # unused signal for now, but TODO: could be used to show errors in UI
            self.map_saved.emit("\n".join(error_msgs))
            return

        
        # TODO
        # currently hardcoded name due to asm linker .incbin limitations, possible future improvement
        # where the map editor can generate .xip files with arbitrary names and the engine can load them dynamically.
        # for now, engine expects and loads ONLY "mapdata.xip" and "textures.xip"
        filename = "mapdata.xip"
        
        path = Path.joinpath(self._assets_path, filename)
        
        # needs to be .xip for the linker .incbin and enginer support
        if not path.suffix.lower() == ".xip":
            logging.warning(f"Filename '{filename}' does not have .xip extension, adding it automatically.")
            path = path.with_suffix(".xip")
        
        logging.info(f"Exporting map to {path}")
    
        export_map_to_xip(path, self.player, self.map)
        
        self.dirty = False
        self.map_saved.emit("")  # success
        
    