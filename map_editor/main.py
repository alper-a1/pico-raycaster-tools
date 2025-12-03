import logging, sys
import argparse, os
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ui.main_window import MapEditorMainWindow

logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stdout)], 
                    format="%(asctime)s %(levelname)s: %(message)s")

def main(argv=None):
    # Require --project-directory; allow unknown args (Qt may supply its own)
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--project-directory', dest='project_directory', required=True,
                        help='absolute path to project directory (required)')
    args, _ = parser.parse_known_args(argv if argv is not None else sys.argv[1:])
    project_dir = args.project_directory

    # Normalize to a canonical absolute path (expand ~, resolve symlinks, remove redundant separators)
    project_dir = os.path.normpath(os.path.realpath(os.path.abspath(os.path.expanduser(project_dir))))

    if not os.path.isdir(project_dir):
        logging.error("Provided project-directory is not a directory: %s", project_dir)
        return 1
    logging.info("Using project directory: %s", project_dir)
    os.chdir(project_dir)

    logging.info("Starting map editor")
    app = QApplication()
    win = MapEditorMainWindow(Path(project_dir))
    
    win.show()
    
    return app.exec()

if __name__ == "__main__":
    main()
