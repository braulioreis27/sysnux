import os
import subprocess
from PySide6.QtCore import QThread, Signal


def is_root():
    return os.geteuid() == 0


def run_command(command, timeout=None):
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output.strip()
    except subprocess.TimeoutExpired:
        return False, "Comando excedeu o tempo limite"
    except Exception as e:
        return False, str(e)


def check_internet():
    for host in ["8.8.8.8", "1.1.1.1"]:
        success, _ = run_command(f"ping -c 1 -W 2 {host}", timeout=5)
        if success:
            return True
    return False


class TaskRunner(QThread):
    output = Signal(str)
    progress = Signal(int)
    finished = Signal(bool, str)

    def __init__(self, task_func, *args, **kwargs):
        super().__init__()
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs
        self._cancelled = False
        self._had_failure = False

    def run(self):
        try:
            for item in self.task_func(*self.args, **self.kwargs):
                if self._cancelled:
                    self.finished.emit(False, "Cancelado pelo usuário")
                    return
                if isinstance(item, int):
                    self.progress.emit(item)
                else:
                    text = str(item)
                    if text.startswith("[FALHA]") or text.startswith("[ERRO]"):
                        self._had_failure = True
                    self.output.emit(text)
            if self._had_failure:
                self.finished.emit(False, "Algumas tarefas falharam")
            else:
                self.finished.emit(True, "Concluído com sucesso")
        except Exception as e:
            self.finished.emit(False, f"Erro: {e}")

    def cancel(self):
        self._cancelled = True
