#!/usr/bin/env python3
"""
Sysnux - Ferramenta profissional de pós-formatação e manutenção para Linux
"""

import os
import sys
import subprocess

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt

from sysnux import __version__, __app_name__
from sysnux.utils.runner import is_root
from sysnux.utils.logging import setup_logging
from sysnux.ui.main_window import MainWindow


def check_root_and_relaunch():
    if is_root():
        return True

    app = QApplication.instance() or QApplication(sys.argv)

    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setWindowTitle("Sysnux - Privilégios Necessários")
    msg.setText(
        "Esta ferramenta requer privilégios de administrador (root) "
        "para executar a maioria das operações do sistema."
    )
    msg.setInformativeText(
        "Deseja reiniciar com privilégios elevados?\n\n"
        "O sistema solicitará sua senha via PolKit (pkexec)."
    )
    msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    msg.setDefaultButton(QMessageBox.StandardButton.Yes)
    msg.button(QMessageBox.StandardButton.Yes).setText("Sim, elevar privilégios")
    msg.button(QMessageBox.StandardButton.No).setText("Não, encerrar")

    result = msg.exec()

    if result == QMessageBox.StandardButton.Yes:
        script_path = os.path.abspath(__file__)
        display = os.environ.get("DISPLAY", ":0")
        xauth = os.environ.get("XAUTHORITY", os.path.expanduser("~/.Xauthority"))
        wayland = os.environ.get("WAYLAND_DISPLAY", "")
        xdg_runtime = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")

        cmd = [
            "pkexec", "env",
            f"DISPLAY={display}",
            f"XAUTHORITY={xauth}",
            f"XDG_RUNTIME_DIR={xdg_runtime}",
        ]
        if wayland:
            cmd.append(f"WAYLAND_DISPLAY={wayland}")

        venv_python = os.path.join(os.path.dirname(os.path.dirname(script_path)), "venv", "bin", "python3")
        if os.path.exists(venv_python):
            cmd.append(venv_python)
        else:
            cmd.append(sys.executable)
        cmd.append(script_path)

        subprocess.run(cmd)
        sys.exit(0)

    sys.exit(1)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)
    app.setStyle("Fusion")

    palette = app.palette()
    palette.setColor(app.palette().ColorRole.Window, Qt.GlobalColor.black)
    app.setPalette(palette)

    setup_logging()

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    if check_root_and_relaunch():
        main()
