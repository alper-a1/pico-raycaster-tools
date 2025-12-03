import logging
import math
from typing import Dict, Any

from PySide6 import QtCore, QtGui
from PySide6.QtCore import Qt, Signal

from PySide6.QtWidgets import (QLabel, QCheckBox, QPushButton, QSlider,
                               QVBoxLayout, QHBoxLayout, QWidget, QDialog,
                               QDialogButtonBox, QInputDialog, QScrollArea,
                               QButtonGroup)

from project import Project # only for type hinting, no direct usage
from map_data import *
from texture_manager import TextureManager
from fixed_point import ConversionHelpers

class TileListManagerWidget(QWidget):
    tile_selected = Signal(int)  # tile_id
    
    def __init__(self, texture_manager: TextureManager, thumb_size: int = 24):
        super().__init__()
        self._thumb_size = thumb_size

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        layout.addWidget(QLabel("Texture List"))

        self.texture_manager = texture_manager

        # Scrollable container for the list
        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._container = QWidget()
        self._vbox = QVBoxLayout(self._container)
        self._vbox.setContentsMargins(0, 0, 0, 0)
        self._vbox.setSpacing(4)
        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll)

        # map of id -> button
        self._buttons: dict[int, QPushButton] = {}

        self._build_list(self.texture_manager.get_textures())

    def _build_list(self, textures: Dict[int, Dict[str, Any]]):
        # Clear current items
        for i in reversed(range(self._vbox.count())):
            item = self._vbox.itemAt(i)
            w = item.widget() if item else None
            if w:
                w.setParent(None)

        self._buttons.clear()
        # Recreate button group (safe reset)
        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)
        # custom property "tile_id" used to store tile id
        self._btn_group.buttonClicked.connect(lambda btn: self._on_button_clicked(btn.property("tile_id")))

        for tex_id, info in textures.items():
            name: str = info.get("name", f"tex_{tex_id}")
            # remove "tex_" prefix for display
            name = name.removeprefix("tex_")
            
            color = info.get("rcolor", TextureManager.INVALID_TEX_COLOR)

            # create small colored pixmap for the left box
            pix = QtGui.QPixmap(self._thumb_size, self._thumb_size)
            pix.fill(QtGui.QColor(color))

            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setIcon(QtGui.QIcon(pix))
            btn.setIconSize(QtCore.QSize(self._thumb_size, self._thumb_size))
            # left-align text and give padding; checked state shows highlight
            btn.setStyleSheet(
                "QPushButton { text-align: left; padding: 6px; border: 1px solid transparent; }"
                "QPushButton:checked { border: 2px solid #00aaff; background-color: #B1B1B1; }"
            )
            
            # store tile id in property for retrieval on click
            btn.setProperty("tile_id", tex_id)
            
            self._btn_group.addButton(btn)
            self._buttons[tex_id] = btn
            self._vbox.addWidget(btn)

        self._vbox.addStretch()

    def _on_button_clicked(self, tex_id: int):
        # Emit selected tile id
        self.tile_selected.emit(tex_id)
        logging.info(f"Selected tile ID: {tex_id}")

    def select_tile(self, tex_id: int):
        btn = self._buttons.get(tex_id)
        if btn:
            btn.setChecked(True)

class MapCanvasWidget(QWidget):
    tile_drawn = Signal(int, int, int)  # x, y, tile_id
    player_spawn_set = Signal(int, int)  # x_fp, y_fp in FixedPoint15_16
    
    def __init__(self, texture_manager: TextureManager, tile_draw_size: int = 16):
        super().__init__()
        self.setFixedSize(512, 512)
        
        self._tile_draw_size = tile_draw_size
        self._texture_manager = texture_manager
        
        self._project: Project | None = None
        
        self._selected_tile_id: int = 1
        
        # state for drag/continuous paint
        self._mouse_down = False
        self._last_emitted_tile: tuple[int, int] = (-1, -1)
        self._last_emitted_tile_id: int = -1
        
        # mode selector for placing player spawn
        self._spawn_place_mode = False
        self._spawn_indicator_pos: QtCore.QPoint | None = None
    
    @property
    def selected_tile_id(self) -> int:
        return self._selected_tile_id
    
    @selected_tile_id.setter
    def selected_tile_id(self, value: int):
        if value < 0:
            logging.warning(f"Tried to set invalid tile ID: {value}")
            return
        
        self._selected_tile_id = value
        
    @QtCore.Slot(int)
    def set_selected_tile_id(self, value: int):
        """
        Signal compatible wrapper
        """
        self.selected_tile_id = value
    
    @QtCore.Slot(bool)
    def set_player_place_mode(self, enabled: bool):
        """
        Signal compatible wrapper
        """
        self._spawn_place_mode = enabled
        
        self.setMouseTracking(enabled)
        if not enabled:
            self._spawn_indicator_pos = None
        
        self.repaint()
    
    def set_project(self, project: Project):
        self._project = project
        if project is not None:
            # project.tile_changed.connect(self.on_tile_changed)
            project.map_loaded.connect(self.on_map_loaded)
        
        self.repaint()
        
    def on_map_loaded(self):
        if self._project is None:
            return
        
        # TODO scale tile size to fit on screen if large map 
        
        width = self._project.map.width * self._tile_draw_size
        height = self._project.map.height * self._tile_draw_size
        self.setFixedSize(width, height)
        
        self.resize(width, height)
        self.repaint()
        
    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        pen = QtGui.QPen(Qt.GlobalColor.black)
        pen.setWidth(1)
        
        brush = QtGui.QBrush(Qt.GlobalColor.black, Qt.BrushStyle.SolidPattern)
        painter.setBrush(brush)
        
        painter.drawRect(0, 0, self.width(), self.height())
        
        if self._project is None:
            return super().paintEvent(event)
        
        # to get the color of the texture to draw
        textures = self._texture_manager.get_textures()
        
        # texture grid (representitive color)
        painter.setPen(pen)
        for x in range(self._project.map.width):
            for y in range(self._project.map.height):
                tile_id = self._project.get_tile(x, y)
                if tile_id == 0:
                    continue  # empty tile
                
                text_rect = QtCore.QRect(x * self._tile_draw_size, 
                              y * self._tile_draw_size,
                              self._tile_draw_size,
                              self._tile_draw_size)
                
                color = textures[tile_id]["rcolor"]
                painter.fillRect(text_rect, QtGui.QBrush(QtGui.QColor(color)))
        
        
        # grid lines
        pen.setColor(Qt.GlobalColor.darkGray)
        painter.setPen(pen)
        
        # vertical lines
        for gx in range(self._project.map.width + 1):
            px = gx * self._tile_draw_size
            painter.drawLine(px, 0, px, self._project.map.height * self._tile_draw_size)

        # horizontal lines
        for gy in range(self._project.map.height + 1):
            py = gy * self._tile_draw_size
            painter.drawLine(0, py, self._project.map.width * self._tile_draw_size, py)
        
        # draw player start position
        brush.setColor(Qt.GlobalColor.red)
        pen.setColor(Qt.GlobalColor.red)
        painter.setBrush(brush)
        painter.setPen(pen)

        p = self._project.player
        
        if p is not None:
            if p.start_x != UNSET_FLAG and p.start_y != UNSET_FLAG:
                px_f = ConversionHelpers.fixedpoint_to_float(p.start_x) 
                py_f = ConversionHelpers.fixedpoint_to_float(p.start_y) 
                
                # tile coords to grid pixel coords
                x = math.floor(px_f) * self._tile_draw_size 
                y = math.floor(py_f) * self._tile_draw_size
                
                x_offset = int((px_f - math.floor(px_f)) * self._tile_draw_size)
                y_offset = int((py_f - math.floor(py_f)) * self._tile_draw_size)
                
                x += x_offset
                y += y_offset
                
                marker_rad = self._tile_draw_size // 3
                
                painter.drawEllipse(QtCore.QPoint(x, y), marker_rad, marker_rad)
                
                # draw direction arrow
                if p.start_angle_x != UNSET_FLAG and p.start_angle_y != UNSET_FLAG:
                    cx = x
                    cy = y
                    
                    # grab stored direction [-1,1] in fp and convert to float
                    angle_px = ConversionHelpers.fixedpoint_to_float(p.start_angle_x) 
                    angle_py = ConversionHelpers.fixedpoint_to_float(p.start_angle_y)
                    
                    arrow_end_x = cx + int(angle_px * marker_rad * 3)
                    arrow_end_y = cy + int(angle_py * marker_rad * 3)

                    pen.setWidth(2)
                    painter.setPen(pen)
                    
                    painter.drawLine(cx, cy, arrow_end_x, arrow_end_y)
        
        if self._spawn_place_mode:
            # overlay semi-transparent spawn circle for indicator
            color = "#FF000075"  # red with alpha
            brush.setColor(color)
            painter.setBrush(brush)
            if self._spawn_indicator_pos is not None:
                marker_rad = self._tile_draw_size // 3
                painter.drawEllipse(self._spawn_indicator_pos, marker_rad, marker_rad)
                    
        return super().paintEvent(event)
    
    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        if self._spawn_place_mode:
            self.mouse_press_player_mode(ev)
        else:
            self.mouse_press_tile_mode(ev)
        
        return super().mousePressEvent(ev)
    
    def mouse_press_player_mode(self, ev: QtGui.QMouseEvent) -> None:
        pos = ev.position().toPoint() 

        if ev.button() == Qt.MouseButton.LeftButton:
            self._mouse_down = True
            x = pos.x() / self._tile_draw_size
            y = pos.y() / self._tile_draw_size
            
            self._emit_player_spawn(x, y)
    
    def mouse_press_tile_mode(self, ev: QtGui.QMouseEvent) -> None:
        pos = ev.position().toPoint() 
        
        if ev.button() == Qt.MouseButton.LeftButton:
            self._mouse_down = True
            tx = pos.x() // self._tile_draw_size
            ty = pos.y() // self._tile_draw_size
            self._emit_tile_if_changed(tx, ty, self._selected_tile_id)
        elif ev.button() == Qt.MouseButton.RightButton:
            self._mouse_down = True
            tx = pos.x() // self._tile_draw_size
            ty = pos.y() // self._tile_draw_size
            self._emit_tile_if_changed(tx, ty, 0)

    def mouseMoveEvent(self, ev: QtGui.QMouseEvent) -> None:
        if self._spawn_place_mode:
            self._spawn_indicator_pos = ev.position().toPoint()
            self.repaint()
        
        # Only act while mouse button is held (dragging); normal move events otherwise are ignored
        if not self._mouse_down:
            return super().mouseMoveEvent(ev)

        if self._spawn_place_mode:
            self.mouse_move_player_mode(ev)
            self._spawn_indicator_pos = ev.position().toPoint()
            self.repaint()
        else:
            self.mouse_move_tile_mode(ev)
            self._spawn_indicator_pos = None

        return super().mouseMoveEvent(ev)

    def mouse_move_player_mode(self, ev: QtGui.QMouseEvent) -> None:
        pass
    
    def mouse_move_tile_mode(self, ev: QtGui.QMouseEvent) -> None:
        pos = ev.position().toPoint()
        tx = pos.x() // self._tile_draw_size
        ty = pos.y() // self._tile_draw_size

        # decide paint vs erase based on which button is down
        buttons = ev.buttons()
        if buttons & Qt.MouseButton.LeftButton:
            self._emit_tile_if_changed(tx, ty, self._selected_tile_id)
        elif buttons & Qt.MouseButton.RightButton:
            self._emit_tile_if_changed(tx, ty, 0)        

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
        # stop drag/continuous mode and reset last-emitted state
        self._mouse_down = False
        
        if not self._spawn_place_mode:
            self._last_emitted_tile = (-1, -1)
            self._last_emitted_tile_id = -1
            
        return super().mouseReleaseEvent(ev)

    def _emit_tile_if_changed(self, tx: int, ty: int, tile_id: int) -> None:
        # bounds & dedupe checks to prevent spamming identical emits
        if self._project is None or self._project.map is None:
            return
        
        if self._spawn_place_mode:
            # in player place mode, ignore tile drawing
            return
        
        if tx < 0 or ty < 0 or tx >= self._project.map.width or ty >= self._project.map.height:
            return
        if (tx, ty) == self._last_emitted_tile and tile_id == self._last_emitted_tile_id:
            return
        
        # dont allow placement on the player starting tile/pos
        if tx == ConversionHelpers.fixedpoint_to_int(self._project.player.start_x) and \
           ty == ConversionHelpers.fixedpoint_to_int(self._project.player.start_y):
            return
        
        self.tile_drawn.emit(tx, ty, tile_id)
        self._last_emitted_tile = (tx, ty)
        self._last_emitted_tile_id = tile_id
        
        self.repaint()
        
    def _emit_player_spawn(self, x: float, y: float) -> None:
        if self._project is None:
            return
        
        if self._project.get_tile(int(x), int(y)) != 0:
            # cant place player spawn on non-empty tile
            return
        
        x_fp = ConversionHelpers.float_to_fixedpoint(x)
        y_fp = ConversionHelpers.float_to_fixedpoint(y)
        
        self.player_spawn_set.emit(x_fp, y_fp)
        
        self.repaint()