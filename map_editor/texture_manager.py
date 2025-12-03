import json
import logging
from pathlib import Path
from typing import Dict, List, Union, Any
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox


class TextureManager(QObject):
    """
    Manages loading and providing texture information.
    Textures are loaded from a JSON file in the assets directory.
    Each texture has an ID, name, and representative color  (rcolor).
    ONLY loads textures.json -- TODO: dynamic file loading?
    """
    
    INVALID_TEX_COLOR = "#FF00FF"  # bright magenta for missing textures
    FILE_LOAD_FAILED = -1
    FILE_LOAD_SUCCEEDED = 0
    
    def __init__(self, assets_path: Path):
        super().__init__()
        self.assets_path = assets_path
        
        self._tex_file_version: int
        self._texture_count: int 
        self._textures: Dict[int, Dict[str, Union[str, int]]] = {} # texture_id: {Representitive Color: hex, name: name}
        
        self.load_textures()
        
    def load_textures(self) -> int:
        """
        Loads texture information from the textures.json file in the assets directory.
        Each texture entry should contain an ID, name, and representative color (rcolor).
        Note that each texture has two variants (normal and shaded), so the texture count is halved.
        
        @param
        @return: FILE_LOAD_SUCCEEDED on success, FILE_LOAD_FAILED on failure.
        """
        tex_info_path = Path.joinpath(self.assets_path, "textures.json")

        if not tex_info_path.exists():
            logging.error(f"Texture info file not found: {tex_info_path}")
            QMessageBox.critical(None, "Error", f"Texture info file not found: {tex_info_path}")
            return self.FILE_LOAD_FAILED    
    
        with open(tex_info_path, "r") as f: 
            raw_data = json.load(f)
            
            # div by 2 since each texture has 2 variants (normal and shaded)
            self._texture_count = raw_data.get("texture_count") // 2 
            
            # -1 indicated unknown version / corrupted file
            self._tex_file_version = raw_data.get("version", -1)
            
            tex_dicts: List[Dict[str, Any]] = raw_data.get("textures")
            
            if tex_dicts is None:
                logging.error(f"No textures data in texture info file. File version: {self._tex_file_version}. -1 indicates corrupted file.")
                QMessageBox.critical(None, "Error", "No textures found in texture info file")
                return self.FILE_LOAD_FAILED
            
            # process each texture entry, assuming format: {id: int, name: str, rcolor: str}
            for tex in tex_dicts:
                tex_id = tex.get("id", -1)
                # tex_id = 0 is empty space so increment by 1 to start from 1
                # this means every EVEN id is a shaded variant
                tex_id += 1 
                
                name = tex.get("name", "ERROR_NO_NAME")
                color_rgb565: str = tex.get("rcolor", self.INVALID_TEX_COLOR)
                
                if not color_rgb565.startswith("#"):
                    # convert to standard hex color
                    color_rgb565 = color_rgb565.removeprefix("0x") 
                    color_val565 = int(color_rgb565, 16) & 0xFFFF # mask just in case
                    
                    r5 = (color_val565 >> 11) & 0x1F
                    g6 = (color_val565 >> 5) & 0x3F
                    b5 =  color_val565 & 0x1F
                    
                    r8 = (r5 << 3) | (r5 >> 2)
                    g8 = (g6 << 2) | (g6 >> 4)
                    b8 = (b5 << 3) | (b5 >> 2)
                    color = f"#{r8:02X}{g8:02X}{b8:02X}"
                else:
                    # tex.get returns "#000000"
                    color = color_rgb565
                
                if tex_id != -1:
                    self._textures[tex_id] = {"name": name, "rcolor": color}
                    
        logging.info(f"Loaded {self._texture_count} textures from {tex_info_path}, file version {self._tex_file_version}")
        return self.FILE_LOAD_SUCCEEDED
        
    def get_textures(self, exclude_shaded: bool = True) -> Dict[int, Dict[str, Union[str, int]]]:
        """
        Returns the loaded textures.

        @param exclude_shaded: If True, excludes shaded texture variants
        @return: Dictionary of texture ID to texture
        """
        
        # sort by texture ID
        sorted_textures = sorted(self._textures.items(), key=lambda item: item[0])

        if exclude_shaded:
            filtered = {tid: info for tid, info in sorted_textures if "shaded" not in str(info.get("name"))}
        else:
            filtered = {tid: info for tid, info in sorted_textures}
        
        return filtered