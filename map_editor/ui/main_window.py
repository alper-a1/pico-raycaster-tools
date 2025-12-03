from pathlib import Path
import math

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QLabel,
    QVBoxLayout, QHBoxLayout,
    QStatusBar,
    QSpinBox,
    QCheckBox, 
    QPushButton,
    QMessageBox,
    QFileDialog,
)

from ui.custom_widgets import MapCanvasWidget, TileListManagerWidget
from project import Project
from texture_manager import TextureManager
from fixed_point import ConversionHelpers
from xip_utils import import_map_from_xip

class MapEditorMainWindow(QMainWindow):
    # map_size_changed = Signal(int, int) # width, height
    
    def __init__(self):
        super().__init__()
        self.project_root = Path(__file__).resolve().parents[3] # pico-raycaster root
        self.setWindowTitle("pico-raycaster — Map Editor")
        self.resize(1000, 700)

        # Project handle
        assets_path = Path.joinpath(self.project_root, "assets")
        self.project = Project(assets_path)
        # TEMP
        # self.project.player.start_x = int(10.5 * (1 << 16))  # 10.5 in FixedPoint15_16
        # self.project.player.start_y = int(10.252 * (1 << 16))  # 10.252 in FixedPoint15_16

        # Texture manager instance
        texture_manager = TextureManager(assets_path)

        self.map_canvas = MapCanvasWidget(texture_manager)
        self.map_canvas.set_project(self.project)
        
        # min / max map size
        self.map_height_sb = QSpinBox()
        self.map_height_sb.setRange(16, 255)
        self.map_width_sb = QSpinBox()
        self.map_width_sb.setRange(16, 255)
        
        # initialize with default map size
        self.project.new_map(self.map_width_sb.value(), self.map_height_sb.value())
        
        # texture manager
        self.tile_list_widget = TileListManagerWidget(texture_manager)
        
        save_map_btn = QPushButton("Save Map")
        load_map_btn = QPushButton("Load Map")
        
        # place player start position checkbox
        place_player_start_cb = QCheckBox("Place Player Start Pos")
        place_player_start_cb.setChecked(False)
        
        # player start angle
        self.player_angle_sb = QSpinBox()
        self.player_angle_sb.setValue(0)
        self.player_angle_sb.setRange(0, 359)
        self.player_angle_sb.setSuffix("°")
        self.player_angle_sb.setWrapping(True)
        self.player_angle_sb.setAccelerated(True)

        
        # =====================
        # Signals
        # =====================
        
        self.player_angle_sb.valueChanged.connect(self.update_player_start_angle)
        self.update_player_start_angle(self.player_angle_sb.value())
        
        place_player_start_cb.toggled.connect(self.map_canvas.set_player_place_mode)
        
        save_map_btn.clicked.connect(self.project.save_map)
        load_map_btn.clicked.connect(self.load_map)
        
        self.map_canvas.tile_drawn.connect(self.project.set_tile)
        self.map_canvas.player_spawn_set.connect(self.project.set_player_start_pos)
        
        self.project.map_changed.connect(self.map_canvas.repaint)
        
        # connect signals for map size changing (DOES NOT PRESERVE TILES)
        self.map_width_sb.valueChanged.connect(lambda val: self.project.new_map(val, self.map_height_sb.value()))
        self.map_height_sb.valueChanged.connect(lambda val: self.project.new_map(self.map_width_sb.value(), val))
        
        self.tile_list_widget.tile_selected.connect(self.map_canvas.set_selected_tile_id)
        # now that signal is connected, select first tile
        self.tile_list_widget.select_tile(1)  
        
        # =====================
        # Layout
        # =====================

        central = QWidget()
        h_layout = QHBoxLayout(central)
        h_layout.setContentsMargins(6, 6, 6, 6)
        h_layout.setSpacing(8)

        # Left: canvas area (takes 2/3 of space)
        canvas_container = QWidget()
        canvas_layout = QVBoxLayout(canvas_container)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.addWidget(self.map_canvas)
        h_layout.addWidget(canvas_container, stretch=2)

        # Right: controls sidebar (vertical list)
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(6, 6, 6, 6)
        sidebar_layout.setSpacing(8)

        title = QLabel("Map Editor — controls")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(title)

        sidebar_layout.addWidget(QLabel("Left Click: Draw Tile"))
        sidebar_layout.addWidget(QLabel("Right Click: Delete Tile"))
        
        sidebar_layout.addWidget(QLabel("Map Width"))
        sidebar_layout.addWidget(self.map_width_sb)

        sidebar_layout.addWidget(QLabel("Map Height"))
        sidebar_layout.addWidget(self.map_height_sb)
        
        sidebar_layout.addWidget(place_player_start_cb)
        sidebar_layout.addWidget(QLabel("Player Start Angle"))
        sidebar_layout.addWidget(self.player_angle_sb)
        # sidebar_layout.addSpacing(10)
        
        sidebar_layout.addWidget(self.tile_list_widget)

        # add other controls here (tool selection, save/load buttons, etc.)
        sidebar_layout.addStretch()  # push controls to top
        
        sidebar_layout.addWidget(load_map_btn)
        sidebar_layout.addWidget(save_map_btn)
        
        
        h_layout.addWidget(sidebar, stretch=1)

        self.setCentralWidget(central)
        # Status bar
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage(f"Project: {self.project_root}")

    def update_player_start_angle(self, angle_deg: int):
        rad = math.radians(angle_deg)
        x = math.cos(rad)
        y = math.sin(rad)
        
        x_fp = ConversionHelpers.float_to_fixedpoint(x)
        y_fp = ConversionHelpers.float_to_fixedpoint(y)
        
        self.project.set_player_start_angle(x_fp, y_fp)
        self.map_canvas.repaint()

    def load_map(self):
        # TODO Implement the logic to load a map file
        result = QFileDialog.getOpenFileName(self, "Load Map", str(self.project_root), "XIP Files (*.xip)")
        path = result[0]
        
        if path == "":
            return
        
        import_map_from_xip(Path(path), self.project)
        
        # after loading we need to set all relevant UI state
        self.map_canvas.repaint()
        
        # convert the loaded fixed-point angle to degrees for the spinbox
        fp_angle_x = self.project.player.start_angle_x
        fp_angle_y = self.project.player.start_angle_y
        
        angle_x = ConversionHelpers.fixedpoint_to_float(fp_angle_x)
        angle_y = ConversionHelpers.fixedpoint_to_float(fp_angle_y)
        
        angle_deg = int(math.degrees(math.atan2(angle_y, angle_x))) % 360
        
        self.player_angle_sb.setValue(angle_deg)
        
        # set map size spinboxes
        self.map_height_sb.setValue(self.project.map.height)
        self.map_width_sb.setValue(self.project.map.width)
    
    def closeEvent(self, event):
        if not self.project.dirty:
            event.accept()
            return
        
        # prompt to save changes
        reply = QMessageBox.question(self, "Unsaved Changes", 
                                     "You have unsaved changes. Do you want to save before exiting?",
                                     buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                                     defaultButton=QMessageBox.StandardButton.Yes)

        if reply == QMessageBox.StandardButton.Yes:
            self.project.save_map("mapdata.xip")  # TODO: hardcoded name -- see project.py comments
            event.accept()
        elif reply == QMessageBox.StandardButton.Cancel:
            event.ignore()
            