from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtGui import QTextCursor, QTextCharFormat, QColor, QFont


class OutputConsole(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Monospace", 10))
        self.setMaximumBlockCount(10000)
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 8px;
            }
        """)

    def write(self, text):
        fmt = QTextCharFormat()
        fmt.setForeground(self._detect_color(text))
        self.mergeCurrentCharFormat(fmt)
        self.appendPlainText(text)
        self.moveCursor(QTextCursor.MoveOperation.End)
        default_fmt = QTextCharFormat()
        default_fmt.setForeground(QColor("#d4d4d4"))
        self.mergeCurrentCharFormat(default_fmt)
        self.repaint()

    def write_lines(self, lines):
        for line in lines:
            self.write(line)

    def clear_output(self):
        self.clear()

    def _detect_color(self, text):
        if text.startswith("[ERRO]") or text.startswith("[FALHA]"):
            return QColor("#f44747")
        elif text.startswith("[AVISO]"):
            return QColor("#cca700")
        elif text.startswith("[OK]") or text.startswith("[SUCESSO]"):
            return QColor("#4ec9b0")
        elif text.startswith("[INFO]"):
            return QColor("#569cd6")
        elif text.startswith("==="):
            return QColor("#c586c0")
        else:
            return QColor("#d4d4d4")
