import logging, sys


from PySide6.QtWidgets import QApplication

from ui.main_window import MapEditorMainWindow

logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stdout)], 
                    format="%(asctime)s %(levelname)s: %(message)s")

def main():
    logging.info("Starting map editor")
    app = QApplication()
    win = MapEditorMainWindow()
    
    win.show()
    
    return app.exec()

if __name__ == "__main__":
    main()
