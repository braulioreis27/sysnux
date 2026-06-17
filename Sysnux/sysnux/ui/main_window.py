from functools import partial
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QStackedWidget, QLabel, QScrollArea, QCheckBox, QGroupBox,
    QProgressBar, QFrame, QRadioButton, QButtonGroup, QMessageBox,
    QSizePolicy
)
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont, QPixmap

from sysnux import __version__
from sysnux.utils.runner import TaskRunner, check_internet, run_command
from sysnux.modules import system as sys_module
from sysnux.modules.system import collect_system_info, verificar_update
from sysnux.modules import optimizations, packages, gpu, tools
from sysnux.ui.widgets.output_console import OutputConsole

PAGES = [
    ("🏠", "Dashboard", "home"),
    ("🚀", "Setup Completo", "setup"),
    ("⚡", "Otimizações", "optimizations"),
    ("🎨", "Estilo & Codecs", "customization"),
    ("🎮", "Drivers GPU", "gpu"),
    ("🌐", "Navegadores", "browsers"),
    ("📦", "Desenvolvimento", "dev"),
    ("📦", "Flatpak / Snap", "packages"),
    ("🧹", "Limpeza", "cleanup"),
    ("🛡️", "Segurança", "security"),
    ("🌐", "Diagnóstico Rede", "network"),
    ("🔧", "Ferramentas TI", "tools"),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sysnux - Pós-formatação Linux")
        self.setMinimumSize(1100, 720)
        self.resize(1280, 800)
        self._current_runner = None
        self._task_queue = []
        self._is_running = False
        self._cancelling = False

        self._setup_style()
        self._setup_ui()
        self._load_dashboard()

    def _setup_style(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #252526; }
            QLabel { color: #d4d4d4; }
            QCheckBox {
                color: #d4d4d4;
                spacing: 10px;
                font-size: 13px;
                padding: 3px 0;
            }
            QCheckBox::indicator {
                width: 22px;
                height: 22px;
                border-radius: 4px;
                border: 2px solid #6e6e6e;
                background-color: #1e1e1e;
            }
            QCheckBox::indicator:checked {
                background-color: #4ec9b0;
                border: 2px solid #4ec9b0;
            }
            QCheckBox::indicator:hover {
                border: 2px solid #569cd6;
            }
            QCheckBox::indicator:checked:hover {
                border: 2px solid #3da890;
            }
            QRadioButton {
                color: #d4d4d4;
                spacing: 10px;
                font-size: 13px;
                padding: 3px 0;
            }
            QRadioButton::indicator {
                width: 22px;
                height: 22px;
                border-radius: 11px;
                border: 2px solid #6e6e6e;
                background-color: #1e1e1e;
            }
            QRadioButton::indicator:checked {
                background-color: #4ec9b0;
                border: 2px solid #4ec9b0;
            }
            QRadioButton::indicator:hover {
                border: 2px solid #569cd6;
            }
            QRadioButton::indicator:checked:hover {
                border: 2px solid #3da890;
            }
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1177bb; }
            QPushButton:pressed { background-color: #094771; }
            QPushButton:disabled { background-color: #3c3c3c; color: #6e6e6e; }
            QGroupBox {
                color: #d4d4d4;
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #569cd6;
                border-radius: 6px;
                margin-top: 12px;
                padding: 16px 8px 8px 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: #569cd6;
            }
            QProgressBar {
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                text-align: center;
                color: white;
                background-color: #1e1e1e;
                height: 22px;
            }
            QProgressBar::chunk {
                background-color: #4ec9b0;
                border-radius: 3px;
            }
            QListWidget {
                background-color: #1e1e1e;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                color: #d4d4d4;
                font-size: 13px;
            }
            QListWidget::item { padding: 6px; }
            QListWidget::item:selected { background-color: #094771; }
            QScrollBar:vertical {
                background: #1e1e1e;
                width: 10px;
            }
            QScrollBar::handle:vertical {
                background: #424242;
                border-radius: 5px;
                min-height: 20px;
            }
        """)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        title_bar = self._create_title_bar()
        right_layout.addWidget(title_bar)

        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(16, 12, 16, 12)

        self.stacked = QStackedWidget()
        self.pages = {}
        self._create_all_pages()

        console_header = QHBoxLayout()
        console_label = QLabel("📋 Console de Saída")
        console_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        console_label.setStyleSheet("color: #4ec9b0;")

        self.btn_clear = QPushButton("Limpar")
        self.btn_clear.setFixedWidth(100)
        self.btn_clear.setStyleSheet("background-color: #5a5a5a;")
        self.btn_clear.clicked.connect(self._clear_console)

        self.btn_execute = QPushButton("▶ Executar")
        self.btn_execute.setFixedWidth(130)
        self.btn_execute.setStyleSheet("background-color: #4ec9b0; color: #1e1e1e; font-weight: bold;")
        self.btn_execute.clicked.connect(self._execute)

        self.btn_cancel = QPushButton("■ Cancelar")
        self.btn_cancel.setFixedWidth(130)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #c53030;
                color: white;
                font-weight: bold;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e05353;
            }
            QPushButton:disabled {
                background-color: #5a1a1a;
                color: #9a5a5a;
            }
            QPushButton:pressed {
                background-color: #8b2020;
            }
        """)
        self.btn_cancel.clicked.connect(self._cancel)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setValue(0)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_clear)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_execute)
        btn_layout.addWidget(self.btn_cancel)

        self.console = OutputConsole()
        self.console.setMinimumHeight(160)

        content_layout.addWidget(self.stacked, 1)
        content_layout.addLayout(console_header)
        content_layout.addLayout(btn_layout)
        content_layout.addWidget(self.progress)
        content_layout.addWidget(self.console, 0)

        right_layout.addWidget(content_area, 1)
        main_layout.addWidget(right_panel, 1)

    def _create_title_bar(self):
        bar = QFrame()
        bar.setFixedHeight(44)
        bar.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-bottom: 1px solid #3c3c3c;
            }
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 8, 0)

        title = QLabel("Sysnux — Pós-formatação Profissional")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #569cd6; border: none;")
        layout.addWidget(title)
        layout.addStretch()

        btn_minimize = QPushButton("─")
        btn_minimize.setFixedSize(36, 28)
        btn_minimize.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #cccccc;
                border: none;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #3c3c3c; color: white; }
        """)
        btn_minimize.clicked.connect(self.showMinimized)

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(36, 28)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #cccccc;
                border: none;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #f44747; color: white; }
        """)
        self.btn_close.clicked.connect(self._confirm_close)

        layout.addWidget(btn_minimize)
        layout.addWidget(self.btn_close)
        return bar

    def _confirm_close(self):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle("Sysnux - Sair")
        msg.setText("Deseja realmente sair do Sysnux?")
        msg.setInformativeText("Todas as operações em andamento serão interrompidas.")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        msg.button(QMessageBox.StandardButton.Yes).setText("Sim, sair")
        msg.button(QMessageBox.StandardButton.No).setText("Cancelar")
        if msg.exec() == QMessageBox.StandardButton.Yes:
            self.close()

    def closeEvent(self, event):
        if self._is_running:
            self._cancel()
        event.accept()

    def _create_sidebar(self):
        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-right: 1px solid #3c3c3c;
            }
        """)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, 12, 8, 12)

        logo_label = QLabel()
        logo_pixmap = QPixmap()
        logo_paths = [
            "logo/logo.png",
            "sysnux/assets/logo.png",
        ]
        for path in logo_paths:
            if logo_pixmap.load(path):
                break
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaledToWidth(180))
            logo_label.setStyleSheet("padding: 4px 0 12px 0;")
        else:
            logo_label.setText("Sysnux")
            logo_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            logo_label.setStyleSheet("color: #569cd6; padding: 8px 0 16px 8px;")

        layout.addWidget(logo_label)

        self.sidebar_buttons = []
        for i, (icon, name, key) in enumerate(PAGES):
            btn = QPushButton(f"  {icon}  {name}")
            btn.setFixedHeight(40)
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    background-color: transparent;
                    color: #cccccc;
                    font-size: 13px;
                    border-radius: 4px;
                    padding-left: 8px;
                }
                QPushButton:hover {
                    background-color: #2a2d2e;
                    color: white;
                }
            """)
            btn.clicked.connect(partial(self._switch_page, i))
            layout.addWidget(btn)
            self.sidebar_buttons.append(btn)

        layout.addStretch()

        self.status_label = QLabel(f"v{__version__} · Linux")
        self.status_label.setStyleSheet("color: #6e6e6e; font-size: 11px; padding: 8px;")
        layout.addWidget(self.status_label)

        return sidebar

    def _create_all_pages(self):
        pages = [
            ("home", self._create_dashboard_page()),
            ("setup", self._create_setup_page()),
            ("optimizations", self._create_optimizations_page()),
            ("customization", self._create_customization_page()),
            ("gpu", self._create_gpu_page()),
            ("browsers", self._create_browsers_page()),
            ("dev", self._create_dev_page()),
            ("packages", self._create_packages_page()),
            ("cleanup", self._create_cleanup_page()),
            ("security", self._create_security_page()),
            ("network", self._create_network_page()),
            ("tools", self._create_tools_page()),
        ]
        for key, widget in pages:
            scroll = QScrollArea()
            scroll.setWidget(widget)
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
            self.pages[key] = widget
            self.stacked.addWidget(scroll)

    def _switch_page(self, index):
        self.stacked.setCurrentIndex(index)
        for i, btn in enumerate(self.sidebar_buttons):
            if i == index:
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        background-color: #094771;
                        color: white;
                        font-size: 13px;
                        border-radius: 4px;
                        padding-left: 8px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        background-color: transparent;
                        color: #cccccc;
                        font-size: 13px;
                        border-radius: 4px;
                        padding-left: 8px;
                    }
                """)

    def _page_widget(self, title):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #569cd6; padding-bottom: 8px;")
        layout.addWidget(title_label)
        return widget, layout

    def _create_dashboard_page(self):
        widget, layout = self._page_widget("📊 Dashboard do Sistema")
        self.dashboard_info = QLabel()
        self.dashboard_info.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 16px;
                font-family: 'Monospace';
                font-size: 13px;
                line-height: 1.6;
            }
        """)
        self.dashboard_info.setWordWrap(True)
        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Atualizar")
        refresh_btn.setFixedWidth(130)
        refresh_btn.clicked.connect(self._load_dashboard)
        check_upd_btn = QPushButton("📥 Verificar Atualização")
        check_upd_btn.setFixedWidth(180)
        check_upd_btn.clicked.connect(self._check_update)
        btn_row.addWidget(refresh_btn)
        btn_row.addWidget(check_upd_btn)
        btn_row.addStretch()
        layout.addWidget(self.dashboard_info)
        layout.addLayout(btn_row)
        layout.addStretch()
        return widget

    def _load_dashboard(self):
        info = collect_system_info()
        text = f"""
    Versão      : v{__version__}
    Hostname    : {info['hostname']}
    Sistema     : {info['distro']}
    Kernel      : {info['kernel']}
    Uptime      : {info['uptime']}
    IP          : {info['ip']}
    GPU         : {', '.join(info['gpu'])}
    Tipo        : {info['tipo']}

    CPU         : {info['cpu'].get('model', 'N/A')} ({info['cpu'].get('cores', '?')} núcleos)
    Memória     : {info['memory'].get('total', 'N/A')} (disp: {info['memory'].get('available', 'N/A')})
    Internet    : {"✅ OK" if check_internet() else "❌ Sem conexão"}
        """
        self.dashboard_info.setText(text)
        self.status_label.setText(f"v{__version__} · Linux")

    def _check_update(self):
        self.console.write("[INFO] Verificando atualizações no GitHub...")
        has_update, latest, url = verificar_update()
        if not latest:
            self.console.write("[AVISO] Não foi possível verificar atualizações (sem internet ou GitHub indisponível)")
            return
        if has_update:
            self.console.write(f"[INFO] ⬆ NOVA VERSÃO disponível: {latest}")
            self.console.write(f"[INFO] Baixe em: {url}")
            self.status_label.setText(f"⬆ {latest} disponível!")
            self.status_label.setStyleSheet("color: #f0ad4e; font-size: 11px; font-weight: bold; padding: 8px;")
        else:
            self.console.write(f"[OK] Você já está na versão mais recente ({__version__})")

    def _create_setup_page(self):
        widget, layout = self._page_widget("🚀 Setup Completo")
        desc = QLabel("Execute a configuração completa do sistema pós-formatação.")
        desc.setStyleSheet("color: #a0a0a0; padding-bottom: 12px;")
        layout.addWidget(desc)

        self.setup_checks = {}
        tasks = [
            ("locale", "🌐  Configurar locale pt-BR"),
            ("firewall", "🛡️  Configurar UFW (firewall)"),
            ("tlp", "🔋  TLP (otimização notebook)"),
            ("zram", "💾  ZRAM + earlyOOM"),
            ("kernel", "⚡  Otimizações de kernel (BBR, swappiness)"),
            ("ssd", "💽  Otimizações SSD (fstrim, noatime)"),
            ("grub", "🖥️  Configurar GRUB"),
            ("codecs", "🎵  Codecs multimídia e fontes"),
            ("temas", "🎨  Temas Papirus + Orchis"),
            ("timeshift", "⏱️  Timeshift (snapshot)"),
            ("upgrade", "📦  Upgrade completo do sistema"),
            ("cleanup", "🧹  Limpeza geral"),
        ]
        for key, label in tasks:
            cb = QCheckBox(label)
            cb.setChecked(True)
            layout.addWidget(cb)
            self.setup_checks[key] = cb

        layout.addStretch()
        return widget

    def _create_optimizations_page(self):
        widget, layout = self._page_widget("⚡ Otimizações do Sistema")
        self.opt_checks = {}
        tasks = [
            ("locale", "🌐  Configurar locale pt-BR"),
            ("firewall", "🛡️  Configurar UFW (firewall)"),
            ("tlp", "🔋  TLP (otimização notebook)"),
            ("zram", "💾  ZRAM + earlyOOM"),
            ("kernel", "⚡  Kernel (BBR, swappiness, buffers)"),
            ("ssd", "💽  SSD (fstrim, scheduler, noatime)"),
            ("grub", "🖥️  GRUB (timeout, splash)"),
        ]
        for key, label in tasks:
            cb = QCheckBox(label)
            cb.setChecked(True)
            layout.addWidget(cb)
            self.opt_checks[key] = cb

        layout.addStretch()
        return widget

    def _create_customization_page(self):
        widget, layout = self._page_widget("🎨 Estilo & Codecs")
        self.cust_checks = {}
        tasks = [
            ("codecs", "🎵  Codecs restritos + fontes Microsoft"),
            ("temas", "🎨  Temas Papirus + Orchis"),
            ("hidpi", "🖥️  Configurar HiDPI (se detectado)"),
        ]
        for key, label in tasks:
            cb = QCheckBox(label)
            cb.setChecked(True)
            layout.addWidget(cb)
            self.cust_checks[key] = cb

        layout.addStretch()
        return widget

    def _create_gpu_page(self):
        widget, layout = self._page_widget("🎮 Drivers de Vídeo (GPU)")
        desc = QLabel("Selecione as opções para cada GPU detectada.")
        desc.setStyleSheet("color: #a0a0a0; padding-bottom: 12px;")
        layout.addWidget(desc)

        gpu_group = QGroupBox("NVIDIA")
        nv_layout = QVBoxLayout()
        self.nv_radio = QButtonGroup(self)
        for i, text in enumerate(["Pular", "NVIDIA 535 (Estável)", "NVIDIA 550 (Recente)", "NVIDIA 535 + CUDA"]):
            rb = QRadioButton(text)
            if i == 0:
                rb.setChecked(True)
            self.nv_radio.addButton(rb, i)
            nv_layout.addWidget(rb)
        gpu_group.setLayout(nv_layout)
        layout.addWidget(gpu_group)

        amd_group = QGroupBox("AMD")
        amd_layout = QVBoxLayout()
        self.amd_radio = QButtonGroup(self)
        for i, text in enumerate(["Pular", "Mesa Vulkan (Recomendado)"]):
            rb = QRadioButton(text)
            if i == 0:
                rb.setChecked(True)
            self.amd_radio.addButton(rb, i)
            amd_layout.addWidget(rb)
        amd_group.setLayout(amd_layout)
        layout.addWidget(amd_group)

        intel_group = QGroupBox("Intel")
        intel_layout = QVBoxLayout()
        self.intel_radio = QButtonGroup(self)
        for i, text in enumerate(["Pular", "Intel Media Driver"]):
            rb = QRadioButton(text)
            if i == 0:
                rb.setChecked(True)
            self.intel_radio.addButton(rb, i)
            intel_layout.addWidget(rb)
        intel_group.setLayout(intel_layout)
        layout.addWidget(intel_group)

        layout.addStretch()
        return widget

    def _create_browsers_page(self):
        widget, layout = self._page_widget("🌐 Instalar Navegadores")
        self.browser_checks = {}
        browsers = [
            ("chrome", "Google Chrome Estável"),
            ("chrome_beta", "Google Chrome Beta"),
            ("firefox", "Mozilla Firefox (PPA)"),
            ("brave", "Brave Browser"),
            ("edge", "Microsoft Edge"),
            ("vivaldi", "Vivaldi"),
            ("opera", "Opera"),
        ]
        for key, label in browsers:
            cb = QCheckBox(f"  {label}")
            layout.addWidget(cb)
            self.browser_checks[key] = cb

        layout.addStretch()
        return widget

    def _create_dev_page(self):
        widget, layout = self._page_widget("📦 Ferramentas de Desenvolvimento")
        self.dev_checks = {}
        tasks = [
            ("basics", "Git + build-essential"),
            ("python311", "Python 3.11 (PPA deadsnakes)"),
            ("nodejs", "Node.js + npm (LTS via NodeSource)"),
            ("ghostty", "Ghostty Terminal"),
            ("opencode", "Opencode CLI"),
            ("docker", "Docker"),
        ]
        for key, label in tasks:
            cb = QCheckBox(f"  {label}")
            cb.setChecked(True)
            layout.addWidget(cb)
            self.dev_checks[key] = cb

        layout.addStretch()
        return widget

    def _create_packages_page(self):
        widget, layout = self._page_widget("📦 Gerenciar Flatpak / Snap")
        self.pkg_checks = {}
        tasks = [
            ("flatpak", "Instalar Flatpak + Flathub"),
            ("flatpak_update", "Atualizar Flatpaks"),
            ("flatpak_remove", "Remover Flatpak (apps + serviço)"),
            ("snap", "Instalar Snap (snapd)"),
            ("snap_update", "Atualizar Snaps"),
            ("snap_remove", "Remover Snap (snaps + serviço)"),
        ]
        for key, label in tasks:
            cb = QCheckBox(f"  {label}")
            if "remove" not in key:
                cb.setChecked(True)
            layout.addWidget(cb)
            self.pkg_checks[key] = cb

        layout.addStretch()
        return widget

    def _create_cleanup_page(self):
        widget, layout = self._page_widget("🧹 Limpeza e Manutenção")
        desc = QLabel("Selecione as operações de limpeza:")
        desc.setStyleSheet("color: #a0a0a0; padding-bottom: 12px;")
        layout.addWidget(desc)

        self.clean_checks = {}
        tasks = [
            ("basic", "Limpeza básica (autoclean, autoremove)"),
            ("deep", "Limpeza profunda (purge, pacotes órfãos)"),
            ("kernels", "Remover kernels antigos"),
            ("cache", "Limpar cache de pacotes"),
            ("logs", "Limpar logs antigos (+7 dias)"),
            ("thumbnails", "Remover miniaturas e lixeiras"),
        ]
        for key, label in tasks:
            cb = QCheckBox(f"  {label}")
            cb.setChecked(True)
            layout.addWidget(cb)
            self.clean_checks[key] = cb

        layout.addStretch()
        return widget

    def _create_security_page(self):
        widget, layout = self._page_widget("🛡️ Segurança e Auditoria")
        self.sec_checks = {}
        tasks = [
            ("rootkit", "Varredura de Rootkit (rkhunter)"),
            ("lynis", "Auditoria de Segurança (lynis)"),
            ("debsums", "Verificar integridade de pacotes"),
        ]
        for key, label in tasks:
            cb = QCheckBox(f"  {label}")
            cb.setChecked(True)
            layout.addWidget(cb)
            self.sec_checks[key] = cb

        layout.addStretch()
        return widget

    def _create_network_page(self):
        widget, layout = self._page_widget("🌐 Diagnóstico de Rede")
        self.net_checks = {}
        tasks = [
            ("info", "Informações completas de rede"),
            ("ping", "Teste de conectividade (ping)"),
            ("dns", "Análise de DNS"),
            ("ports", "Portas em escuta"),
            ("speed", "Teste de velocidade"),
            ("firewall", "Firewall e regras"),
        ]
        for key, label in tasks:
            cb = QCheckBox(f"  {label}")
            cb.setChecked(True)
            layout.addWidget(cb)
            self.net_checks[key] = cb

        layout.addStretch()
        return widget

    def _create_tools_page(self):
        widget, layout = self._page_widget("🔧 Ferramentas do Profissional de TI")
        self.tools_checks = {}
        tasks = [
            ("diagnostico", "Diagnóstico completo de hardware"),
            ("usb_pci", "Listar dispositivos USB/PCI"),
            ("dmi_bios", "Informações DMI/BIOS (dmidecode)"),
            ("smart", "Teste SMART (saúde dos discos)"),
            ("memoria", "Teste de memória RAM"),
            ("stress", "CPU Stress Test"),
            ("disco", "Benchmark de disco"),
            ("boot", "Análise de boot (systemd-analyze)"),
            ("bateria", "Saúde da bateria"),
            ("relatorio", "Gerar relatório completo"),
            ("install_tools", "Instalar TODAS ferramentas de diagnóstico"),
        ]
        for key, label in tasks:
            cb = QCheckBox(f"  {label}")
            layout.addWidget(cb)
            self.tools_checks[key] = cb

        layout.addStretch()
        return widget

    def _execute(self):
        if self._is_running:
            return

        current_idx = self.stacked.currentIndex()
        current_key = PAGES[current_idx][2]

        self.console.write(f"\n[INFO] Iniciando: {PAGES[current_idx][1]}...")
        self.console.write("=" * 50)

        tasks = self._get_tasks_for_page(current_key)

        if not tasks:
            self.console.write("[AVISO] Nenhuma tarefa selecionada.")
            return

        self._task_queue = tasks
        self._cancelling = False
        self._is_running = True

        self.progress.setVisible(True)
        self.progress.setMaximum(len(tasks))
        self.progress.setValue(0)
        self.btn_execute.setEnabled(False)
        self.btn_cancel.setEnabled(True)

        self._run_next_task()

    def _get_tasks_for_page(self, key):
        task_map = {
            "setup": self._get_setup_tasks,
            "optimizations": self._get_optimization_tasks,
            "customization": self._get_customization_tasks,
            "gpu": self._get_gpu_tasks,
            "browsers": self._get_browser_tasks,
            "dev": self._get_dev_tasks,
            "packages": self._get_package_tasks,
            "cleanup": self._get_cleanup_tasks,
            "security": self._get_security_tasks,
            "network": self._get_network_tasks,
            "tools": self._get_tools_tasks,
        }
        getter = task_map.get(key)
        if getter:
            return getter()
        return []

    def _get_setup_tasks(self):
        tasks = []
        checks = self.setup_checks
        if checks.get("locale") and checks["locale"].isChecked():
            tasks.append(("Locale", optimizations.configurar_locale))
        if checks.get("firewall") and checks["firewall"].isChecked():
            tasks.append(("Firewall", optimizations.configurar_firewall))
        if checks.get("tlp") and checks["tlp"].isChecked():
            tasks.append(("TLP", optimizations.configurar_tlp))
        if checks.get("zram") and checks["zram"].isChecked():
            tasks.append(("ZRAM", optimizations.configurar_zram))
        if checks.get("kernel") and checks["kernel"].isChecked():
            tasks.append(("Kernel", optimizations.otimizar_kernel))
        if checks.get("ssd") and checks["ssd"].isChecked():
            tasks.append(("SSD", optimizations.otimizar_ssd))
        if checks.get("grub") and checks["grub"].isChecked():
            tasks.append(("GRUB", optimizations.configurar_grub))
        if checks.get("codecs") and checks["codecs"].isChecked():
            tasks.append(("Codecs", packages.instalar_codecs_fontes))
        if checks.get("temas") and checks["temas"].isChecked():
            tasks.append(("Temas", packages.instalar_temas))
        if checks.get("timeshift") and checks["timeshift"].isChecked():
            tasks.append(("Timeshift", packages.configurar_timeshift))
        if checks.get("upgrade") and checks["upgrade"].isChecked():
            tasks.append(("Upgrade", packages.realizar_upgrade))
        if checks.get("cleanup") and checks["cleanup"].isChecked():
            tasks.append(("Limpeza", optimizations.limpar_sistema))
        return tasks

    def _get_optimization_tasks(self):
        tasks = []
        checks = self.opt_checks
        if checks.get("locale") and checks["locale"].isChecked():
            tasks.append(("Locale", optimizations.configurar_locale))
        if checks.get("firewall") and checks["firewall"].isChecked():
            tasks.append(("Firewall", optimizations.configurar_firewall))
        if checks.get("tlp") and checks["tlp"].isChecked():
            tasks.append(("TLP", optimizations.configurar_tlp))
        if checks.get("zram") and checks["zram"].isChecked():
            tasks.append(("ZRAM", optimizations.configurar_zram))
        if checks.get("kernel") and checks["kernel"].isChecked():
            tasks.append(("Kernel", optimizations.otimizar_kernel))
        if checks.get("ssd") and checks["ssd"].isChecked():
            tasks.append(("SSD", optimizations.otimizar_ssd))
        if checks.get("grub") and checks["grub"].isChecked():
            tasks.append(("GRUB", optimizations.configurar_grub))
        return tasks

    def _get_customization_tasks(self):
        tasks = []
        checks = self.cust_checks
        if checks.get("codecs") and checks["codecs"].isChecked():
            tasks.append(("Codecs", packages.instalar_codecs_fontes))
        if checks.get("temas") and checks["temas"].isChecked():
            tasks.append(("Temas", packages.instalar_temas))
        if checks.get("hidpi") and checks["hidpi"].isChecked():
            tasks.append(("HiDPI", packages.configurar_hidpi))
        return tasks

    def _get_gpu_tasks(self):
        tasks = []
        nv_id = self.nv_radio.checkedId()
        amd_id = self.amd_radio.checkedId()
        intel_id = self.intel_radio.checkedId()
        args = (str(nv_id), str(amd_id), str(intel_id))
        tasks.append(("GPU Drivers", gpu.menu_drivers_gpu, args))
        return tasks

    def _get_browser_tasks(self):
        tasks = []
        browser_map = {
            "chrome": ("Chrome", packages.instalar_chrome),
            "chrome_beta": ("Chrome Beta", packages.instalar_chrome_beta),
            "firefox": ("Firefox", packages.instalar_firefox),
            "brave": ("Brave", packages.instalar_brave),
            "edge": ("Edge", packages.instalar_edge),
            "vivaldi": ("Vivaldi", packages.instalar_vivaldi),
            "opera": ("Opera", packages.instalar_opera),
        }
        for key, (name, func) in browser_map.items():
            if self.browser_checks.get(key) and self.browser_checks[key].isChecked():
                tasks.append((name, func))
        return tasks

    def _get_dev_tasks(self):
        tasks = []
        if self.dev_checks.get("basics") and self.dev_checks["basics"].isChecked():
            def install_basics():
                yield "[INFO] Instalando Git e build-essential..."
                ok, _ = packages.apt_install("git build-essential")
                yield f"{'[OK]' if ok else '[FALHA]'} Git + build-essential"
            tasks.append(("Git/Build", install_basics))
        if self.dev_checks.get("python311") and self.dev_checks["python311"].isChecked():
            tasks.append(("Python 3.11", packages.instalar_python311))
        if self.dev_checks.get("nodejs") and self.dev_checks["nodejs"].isChecked():
            tasks.append(("Node.js", packages.instalar_nodejs))
        if self.dev_checks.get("ghostty") and self.dev_checks["ghostty"].isChecked():
            tasks.append(("Ghostty", packages.instalar_ghostty))
        if self.dev_checks.get("opencode") and self.dev_checks["opencode"].isChecked():
            tasks.append(("Opencode", packages.instalar_opencode))
        if self.dev_checks.get("docker") and self.dev_checks["docker"].isChecked():
            def install_docker():
                yield "[INFO] Instalando Docker..."
                ok, _ = packages.apt_install("docker.io")
                yield f"{'[OK]' if ok else '[FALHA]'} Docker"
                run_command("systemctl enable --now docker 2>/dev/null || true")
                yield "[OK] Docker ativado"
            tasks.append(("Docker", install_docker))
        return tasks

    def _get_package_tasks(self):
        tasks = []
        if self.pkg_checks.get("flatpak") and self.pkg_checks["flatpak"].isChecked():
            tasks.append(("Flatpak", packages.instalar_flatpak_suporte))
        if self.pkg_checks.get("flatpak_update") and self.pkg_checks["flatpak_update"].isChecked():
            tasks.append(("Flatpak Update", packages.atualizar_flatpaks))
        if self.pkg_checks.get("flatpak_remove") and self.pkg_checks["flatpak_remove"].isChecked():
            tasks.append(("Flatpak Remove", packages.remover_flatpak))
        if self.pkg_checks.get("snap") and self.pkg_checks["snap"].isChecked():
            tasks.append(("Snap", packages.instalar_snap_suporte))
        if self.pkg_checks.get("snap_update") and self.pkg_checks["snap_update"].isChecked():
            tasks.append(("Snap Update", packages.atualizar_snaps))
        if self.pkg_checks.get("snap_remove") and self.pkg_checks["snap_remove"].isChecked():
            tasks.append(("Snap Remove", packages.remover_snap))
        return tasks

    def _get_cleanup_tasks(self):
        tasks = []
        checks = self.clean_checks
        if checks.get("basic") and checks["basic"].isChecked():
            def basic_clean():
                yield "[INFO] Limpeza básica..."
                run_command("apt-get autoclean -y")
                yield "[OK] autoclean"
                run_command("apt-get autoremove -y")
                yield "[OK] autoremove"
            tasks.append(("Limpeza Básica", basic_clean))
        if checks.get("deep") and checks["deep"].isChecked():
            def deep_clean():
                yield "[INFO] Limpeza profunda..."
                run_command("apt-get autoremove --purge -y")
                run_command("dpkg -l | awk '/^rc/ {print $2}' | xargs -r dpkg --purge 2>/dev/null || true")
                ok, out = run_command("command -v deborphan 2>/dev/null")
                if ok:
                    run_command("deborphan | xargs -r apt-get remove --purge -y 2>/dev/null || true")
                    yield "[OK] Pacotes órfãos removidos (deborphan)"
                yield "[OK] Purge concluído"
            tasks.append(("Limpeza Profunda", deep_clean))
        if checks.get("kernels") and checks["kernels"].isChecked():
            def clean_kernels():
                yield "[INFO] Removendo kernels antigos..."
                ok, out = run_command("uname -r")
                atual = out.strip() if ok else ""
                atual_ver = sys_module.get_kernel_version(atual)
                ok2, out2 = run_command("dpkg -l 'linux-image-*' 'linux-headers-*' 'linux-modules-*' 2>/dev/null | grep '^ii' | awk '{print $2, $3}'")
                if ok2 and out2:
                    for line in out2.strip().split("\n"):
                        parts = line.split()
                        if len(parts) >= 2:
                            ver = sys_module.get_kernel_version(parts[1])
                            if ver != atual_ver:
                                run_command(f"apt-get purge -y {parts[0]} 2>/dev/null || true")
                                yield f"[OK] Removido: {parts[0]}"
                    run_command("update-grub 2>/dev/null || true")
                    yield "[OK] GRUB atualizado"
                else:
                    yield "[INFO] Nenhum kernel antigo encontrado"
            tasks.append(("Kernels", clean_kernels))
        if checks.get("cache") and checks["cache"].isChecked():
            def clean_cache():
                yield "[INFO] Limpando cache..."
                run_command("apt-get clean")
                yield "[OK] Cache limpo"
            tasks.append(("Cache", clean_cache))
        if checks.get("logs") and checks["logs"].isChecked():
            def clean_logs():
                yield "[INFO] Limpando logs..."
                run_command("journalctl --vacuum-time=7d 2>/dev/null || true")
                run_command("find /var/log -type f -name '*.log' -mtime +7 -delete 2>/dev/null || true")
                yield "[OK] Logs limpos"
            tasks.append(("Logs", clean_logs))
        if checks.get("thumbnails") and checks["thumbnails"].isChecked():
            def clean_thumbs():
                yield "[INFO] Removendo miniaturas..."
                run_command("rm -rf /home/*/.cache/thumbnails/* 2>/dev/null || true")
                run_command("rm -rf /root/.cache/thumbnails/* 2>/dev/null || true")
                yield "[OK] Miniaturas removidas"
            tasks.append(("Miniaturas", clean_thumbs))
        return tasks

    def _get_security_tasks(self):
        tasks = []
        checks = self.sec_checks
        if checks.get("rootkit") and checks["rootkit"].isChecked():
            tasks.append(("Rootkit", tools.varredura_rootkit))
        if checks.get("lynis") and checks["lynis"].isChecked():
            def run_lynis():
                yield "[INFO] Auditoria Lynis..."
                run_command("apt-get install -y lynis 2>/dev/null")
                ok, out = run_command("lynis audit system --quick 2>/dev/null | tail -15")
                if ok and out:
                    for line in out.strip().split("\n"):
                        yield f"  {line}"
                yield "[SUCESSO] Auditoria concluída"
            tasks.append(("Lynis", run_lynis))
        if checks.get("debsums") and checks["debsums"].isChecked():
            def check_debsums():
                yield "[INFO] Verificando integridade dos pacotes..."
                run_command("apt-get install -y debsums 2>/dev/null")
                ok, out = run_command("debsums -s 2>/dev/null")
                if ok and out.strip():
                    yield f"[ERRO] {len(out.strip().split(chr(10)))} pacote(s) corrompido(s)"
                    for line in out.strip().split("\n")[:10]:
                        yield f"  {line}"
                else:
                    yield "[OK] Nenhum pacote corrompido"
            tasks.append(("Debsums", check_debsums))
        return tasks

    def _get_network_tasks(self):
        tasks = []
        checks = self.net_checks
        if checks.get("info") and checks["info"].isChecked():
            tasks.append(("Info Rede", tools.analise_rede))
        if checks.get("ping") and checks["ping"].isChecked():
            def ping_test():
                yield "[INFO] Teste de ping..."
                ok, out = run_command("ping -c 5 -W 3 8.8.8.8 2>&1")
                if ok and out:
                    for line in out.strip().split("\n"):
                        yield f"  {line}"
            tasks.append(("Ping", ping_test))
        if checks.get("dns") and checks["dns"].isChecked():
            def dns_test():
                yield "[INFO] Consulta DNS..."
                for cmd, label in [
                    ("dig +short A google.com", "A (IPv4)"),
                    ("dig +short MX google.com", "MX"),
                    ("dig +short NS google.com", "NS"),
                ]:
                    ok, out = run_command(cmd + " 2>/dev/null")
                    yield f"  {label}: {out.strip() if out else 'falhou'}"
            tasks.append(("DNS", dns_test))
        if checks.get("ports") and checks["ports"].isChecked():
            def ports_scan():
                yield "[INFO] Portas em escuta..."
                ok, out = run_command("ss -tlnp 2>/dev/null | head -20")
                if ok and out:
                    for line in out.strip().split("\n"):
                        yield f"  {line}"
            tasks.append(("Portas", ports_scan))
        if checks.get("speed") and checks["speed"].isChecked():
            def speed_test():
                yield "[INFO] Teste de velocidade..."
                run_command("apt-get install -y speedtest-cli 2>/dev/null")
                ok, out = run_command("speedtest-cli --simple 2>/dev/null")
                if ok and out:
                    for line in out.strip().split("\n"):
                        yield f"  {line}"
                else:
                    yield "[FALHA] Teste de velocidade indisponível"
            tasks.append(("Speed Test", speed_test))
        if checks.get("firewall") and checks["firewall"].isChecked():
            def firewall_check():
                yield "[INFO] Verificando firewall..."
                ok, out = run_command("ufw status verbose 2>/dev/null")
                if ok and out:
                    yield f"  UFW: {out}"
                ok, out = run_command("iptables -L -n -v 2>/dev/null | head -20")
                if ok and out:
                    for line in out.strip().split("\n"):
                        yield f"  {line}"
            tasks.append(("Firewall", firewall_check))
        return tasks

    def _get_tools_tasks(self):
        tasks = []
        checks = self.tools_checks
        if checks.get("diagnostico") and checks["diagnostico"].isChecked():
            tasks.append(("Hardware", tools.diagnostico_hardware))
        if checks.get("usb_pci") and checks["usb_pci"].isChecked():
            tasks.append(("USB/PCI", tools.listar_dispositivos_usb_pci))
        if checks.get("dmi_bios") and checks["dmi_bios"].isChecked():
            tasks.append(("DMI/BIOS", tools.info_dmi_bios))
        if checks.get("smart") and checks["smart"].isChecked():
            tasks.append(("SMART", tools.teste_smart))
        if checks.get("memoria") and checks["memoria"].isChecked():
            tasks.append(("RAM", tools.teste_memoria))
        if checks.get("stress") and checks["stress"].isChecked():
            tasks.append(("Stress CPU", tools.stress_cpu))
        if checks.get("disco") and checks["disco"].isChecked():
            tasks.append(("Benchmark", tools.benchmark_disco))
        if checks.get("boot") and checks["boot"].isChecked():
            tasks.append(("Boot", tools.analise_boot))
        if checks.get("bateria") and checks["bateria"].isChecked():
            tasks.append(("Bateria", tools.saude_bateria))
        if checks.get("relatorio") and checks["relatorio"].isChecked():
            tasks.append(("Relatório", tools.gerar_relatorio))
        if checks.get("install_tools") and checks["install_tools"].isChecked():
            tasks.append(("Instalar Tools", tools.instalar_ferramentas_ti))
        return tasks

    def _run_next_task(self):
        if self._cancelling or not self._task_queue:
            if not self._cancelling:
                self._finish_execution(True, "Todas as tarefas concluídas")
            return

        name, func, *extra = self._task_queue.pop(0)
        args = extra[0] if extra else ()

        total = self.progress.maximum()
        done = total - len(self._task_queue) - 1
        self.progress.setValue(max(0, done))

        self.console.write(f"\n{'=' * 50}")
        self.console.write(f"[INFO] ▶ Executando: {name}")
        self.console.write(f"{'=' * 50}")

        def task_wrapper():
            if isinstance(args, tuple) and args:
                yield from func(*args)
            else:
                yield from func()

        self._current_runner = TaskRunner(task_wrapper)
        self._current_runner.output.connect(self._on_task_output)
        self._current_runner.finished.connect(self._on_task_done)
        self._current_runner.start()

    def _on_task_output(self, text):
        self.console.write(text)

    def _on_task_done(self, success, message):
        if success:
            self.console.write(f"[SUCESSO] {message}")
        else:
            self.console.write(f"[FALHA] {message}")
        QTimer.singleShot(100, self._run_next_task)

    def _finish_execution(self, success, message):
        self.progress.setVisible(False)
        self.btn_execute.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self._is_running = False
        self._current_runner = None
        if success:
            self.console.write(f"\n[SUCESSO] ✅ {message}")
        else:
            self.console.write(f"\n{'=' * 50}")
            self.console.write(f"[INFO] {message}")

    def _cancel(self):
        if self._cancelling:
            return
        self._cancelling = True
        if self._current_runner and self._current_runner.isRunning():
            self._current_runner.cancel()
            self.console.write("[AVISO] Operação cancelada pelo usuário.")
        self._task_queue = []
        self._finish_execution(False, "Cancelado")

    def _clear_console(self):
        self.console.clear_output()
