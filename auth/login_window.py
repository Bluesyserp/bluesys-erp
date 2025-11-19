# auth/login_window.py
import json
import sqlite3
import os 
import logging # <-- NOVO: Biblioteca de Log
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFrame,
    QSpacerItem, QSizePolicy, QHBoxLayout, QStackedLayout, QGraphicsOpacityEffect,
    QSystemTrayIcon, QMenu, QAction, QApplication
)
from PyQt5.QtGui import QFont, QPixmap, QIcon
from PyQt5.QtCore import (
    Qt, QPoint, QTimer, QPropertyAnimation, QEasingCurve
)

from ui.main_window import MainWindow
from database.db import get_connection
from config.version import APP_VERSION, APP_NAME

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        # --- NOVO: Inicializa o Logger ---
        self.logger = logging.getLogger(__name__)
        
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.old_pos = None 

        self.setWindowTitle("BlueSys ERP - Login")
        self.setFixedSize(900, 600) 
        self.main_window = None
        
        # Flag de controle de fechamento
        self.is_quitting_flag = False
        
        # --- Slideshow ---
        self.image_paths = []
        self._load_image_paths()
        
        if not self.image_paths:
            print("Aviso: Nenhuma imagem encontrada em assets/slideshow/. O slideshow não funcionará.")
            
        self.current_image_index = 0
        self.top_label = None
        self.bottom_label = None
        
        self._setup_styles()
        self._build_ui()
        
        # Inicializa o ícone da bandeja
        self._setup_tray_icon()
        
        # Inicia o slideshow se houver imagens
        if len(self.image_paths) > 1:
            self.image_timer = QTimer(self)
            self.image_timer.setInterval(5000) # 5 segundos por imagem
            self.image_timer.timeout.connect(self.next_image)
            self.image_timer.start()

    def _load_image_paths(self):
        """Carrega os caminhos das imagens da pasta assets/slideshow."""
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            slideshow_dir = os.path.abspath(os.path.join(base_dir, "..", "assets", "slideshow"))
            
            if not os.path.exists(slideshow_dir):
                os.makedirs(slideshow_dir)
                return

            valid_extensions = ('.png', '.jpg', '.jpeg')
            for f in sorted(os.listdir(slideshow_dir)):
                if f.lower().endswith(valid_extensions):
                    self.image_paths.append(os.path.join(slideshow_dir, f))
                    
        except Exception as e:
            # Usa o logger se disponível, senão print
            if hasattr(self, 'logger'):
                self.logger.error(f"Erro ao carregar imagens do slideshow: {e}")
            else:
                print(f"Erro ao carregar imagens do slideshow: {e}")

    def _setup_styles(self):
        """Estilo de 'split-screen' (sem o border-image)."""
        self.setStyleSheet(f"""
            QWidget#LoginWindow {{ background-color: transparent; }}
            QFrame#left_pane {{
                background-color: #1e1e2f;
                border-top-left-radius: 12px;
                border-bottom-left-radius: 12px;
            }}
            QFrame#right_pane {{
                background-color: #f8f8fb;
                border-top-right-radius: 12px;
                border-bottom-right-radius: 12px;
            }}
            QLabel.slideshow_image {{
                background-color: #f8f8fb;
                border-top-right-radius: 12px;
                border-bottom-right-radius: 12px;
            }}
            QPushButton#title_bar_btn {{
                background-color: transparent; color: #f8f8fb;
                font-family: "Arial"; font-weight: bold; font-size: 14px;
                border: none; max-width: 30px; max-height: 30px;
            }}
            QPushButton#title_bar_btn:hover {{ background-color: #3e3e5e; }}
            QPushButton#close_btn {{
                background-color: transparent; color: #f8f8fb;
                font-family: "Arial"; font-weight: bold; font-size: 14px;
                border: none; max-width: 30px; max-height: 30px;
            }}
            QPushButton#close_btn:hover {{ background-color: #e81123; }}
            QLabel#logo {{ max-width: 250px; min-height: 100px; }}
            QLabel#logo_placeholder {{
                font-size: 14px; font-weight: bold;
                color: #c0392b; background-color: #2e2e4e;
                border: 2px dashed #555; border-radius: 10px;
                min-height: 100px; padding: 10px;
            }}
            QLabel#title {{
                font-size: 24px; font-weight: bold;
                color: #ffffff; padding-top: 10px;
            }}
            QLabel {{
                color: #aaa; font-size: 12px;
                font-weight: bold; padding-left: 5px;
            }}
            QLineEdit {{
                border: 1px solid #3e3e5e;
                border-radius: 6px; padding: 10px;
                background-color: #2e2e4e;
                font-size: 14px; color: #ffffff;
            }}
            QLineEdit:focus {{ border: 1px solid #0078d7; }}
            QPushButton#login_btn {{
                background-color: #0078d7; color: white;
                border-radius: 6px; padding: 10px;
                font-weight: bold; font-size: 14px;
            }}
            QPushButton#login_btn:hover {{ background-color: #005fa3; }}
            QLabel#version_label {{
                color: #FFFFFF; font-size: 11px;
                font-weight: bold; background-color: transparent;
                padding-left: 30px; padding-bottom: 5px;
            }}
        """)

    def _build_ui(self):
        """Cria a interface de login com layout dividido."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setObjectName("LoginWindow")

        # --- PAINEL ESQUERDO (Formulário) ---
        self.left_pane = QFrame()
        self.left_pane.setObjectName("left_pane")
        left_layout = QVBoxLayout(self.left_pane)
        left_layout.setContentsMargins(10, 5, 10, 10)

        # Barra de Título
        title_bar_layout = QHBoxLayout()
        title_bar_layout.setContentsMargins(0, 0, 0, 0)
        title_bar_layout.addStretch()
        self.btn_minimize = QPushButton("_")
        self.btn_minimize.setObjectName("title_bar_btn")
        self.btn_minimize.clicked.connect(self.hide) 
        self.btn_close = QPushButton("X")
        self.btn_close.setObjectName("close_btn")
        self.btn_close.clicked.connect(self.close) 
        title_bar_layout.addWidget(self.btn_minimize)
        title_bar_layout.addWidget(self.btn_close)
        left_layout.addLayout(title_bar_layout)
        left_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Layout do Formulário
        form_layout = QVBoxLayout()
        form_layout.setContentsMargins(30, 0, 30, 0)
        form_layout.setSpacing(10)
        
        logo_label = QLabel()
        logo_label.setObjectName("logo")
        logo_label.setAlignment(Qt.AlignCenter)
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            path1 = os.path.abspath(os.path.join(base_dir, "..", "assets", "logo.png"))
            logo_path = None
            if os.path.exists(path1): logo_path = path1
            
            if logo_path:
                pixmap = QPixmap(logo_path)
                if not pixmap.isNull():
                    logo_label.setPixmap(pixmap.scaledToWidth(250, Qt.SmoothTransformation))
                else:
                    logo_label.setText("Erro: Logo corrompida."); logo_label.setObjectName("logo_placeholder")
            else:
                logo_label.setText(f"Logo não encontrada.\n(assets/logo.png)"); logo_label.setObjectName("logo_placeholder")
        except Exception as e:
            logo_label.setText(f"Erro ao carregar a logo:\n{e}"); logo_label.setObjectName("logo_placeholder")
        form_layout.addWidget(logo_label, 0, Qt.AlignCenter)
        
        title = QLabel("Login")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        form_layout.addWidget(title, 0, Qt.AlignCenter)
        form_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Minimum))
        
        form_layout.addWidget(QLabel("USUÁRIO"))
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Digite seu usuário")
        form_layout.addWidget(self.user_input)
        form_layout.addWidget(QLabel("SENHA"))
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Digite sua senha")
        self.pass_input.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(self.pass_input)
        form_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Minimum))
        
        login_btn = QPushButton("Entrar")
        login_btn.setObjectName("login_btn")
        login_btn.clicked.connect(self.check_login)
        form_layout.addWidget(login_btn)
        
        left_layout.addLayout(form_layout)
        left_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        version_label = QLabel("BlueSys ERP v1.0.0")
        version_label.setObjectName("version_label")
        left_layout.addWidget(version_label, 0, Qt.AlignLeft | Qt.AlignBottom)

        # --- PAINEL DIREITO (Slideshow) ---
        self.right_pane = QFrame()
        self.right_pane.setObjectName("right_pane")
        
        # Usamos QStackedLayout para sobrepor os QLabels
        self.right_layout = QStackedLayout(self.right_pane)  
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Criamos os dois QLabels para o cross-fade
        self.image_label_1 = QLabel()
        self.image_label_1.setObjectName("slideshow_image")
        self.image_label_2 = QLabel()
        self.image_label_2.setObjectName("slideshow_image")
        
        # Carrega as imagens iniciais
        if self.image_paths:
            pixmap1 = QPixmap(self.image_paths[0])
            if not pixmap1.isNull():
                self.image_label_1.setPixmap(pixmap1.scaled(
                    self.right_pane.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
            self.image_label_1.setAlignment(Qt.AlignCenter)
            
            if len(self.image_paths) > 1:
                pixmap2 = QPixmap(self.image_paths[1])
                if not pixmap2.isNull():
                    self.image_label_2.setPixmap(pixmap2.scaled(
                        self.right_pane.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
                self.image_label_2.setAlignment(Qt.AlignCenter)
        
        self.right_layout.addWidget(self.image_label_1)
        self.right_layout.addWidget(self.image_label_2)
        
        # Define quem está em cima e quem está embaixo
        self.top_label = self.image_label_1
        self.bottom_label = self.image_label_2
        
        # Garantir que ambos tenham QGraphicsOpacityEffect inicial para evitar None
        self.top_opacity_effect = QGraphicsOpacityEffect()
        self.top_opacity_effect.setOpacity(1.0)  # top visível
        self.top_label.setGraphicsEffect(self.top_opacity_effect)

        self.bottom_opacity_effect = QGraphicsOpacityEffect()
        self.bottom_opacity_effect.setOpacity(0.0) # bottom invisível
        self.bottom_label.setGraphicsEffect(self.bottom_opacity_effect)
        self.bottom_label.show()  # precisa estar visível para animação
        
        self.right_layout.setCurrentWidget(self.top_label)

        # --- MONTAGEM FINAL ---
        main_layout.addWidget(self.left_pane, 40)
        main_layout.addWidget(self.right_pane, 60)
        
        self.user_input.returnPressed.connect(self.check_login)
        self.pass_input.returnPressed.connect(self.check_login)

    def next_image(self):
        """Inicia a animação de fade para a próxima imagem."""
        if not self.image_paths or len(self.image_paths) <= 1:
            return  # nada a fazer

        # Calcula o próximo índice
        next_index = (self.current_image_index + 1) % len(self.image_paths)
        
        # Define a imagem no label que está *embaixo* (invisível)
        try:
            pixmap = QPixmap(self.image_paths[next_index])
            if not pixmap.isNull():
                self.bottom_label.setPixmap(pixmap.scaled(
                    self.right_pane.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
            self.bottom_label.setAlignment(Qt.AlignCenter)
        except Exception as e:
            self.logger.error(f"Erro ao carregar imagem do slideshow: {e}")
            return

        # Coloca o bottom como corrente (irá aparecer por cima)
        try:
            self.right_layout.setCurrentWidget(self.bottom_label)
        except Exception:
            pass

        # Anima o efeito de opacidade do bottom (de 0.0 para 1.0)
        if self.bottom_label.graphicsEffect() is None:
            self.bottom_opacity_effect = QGraphicsOpacityEffect()
            self.bottom_opacity_effect.setOpacity(0.0)
            self.bottom_label.setGraphicsEffect(self.bottom_opacity_effect)
        else:
            self.bottom_opacity_effect = self.bottom_label.graphicsEffect()

        self.fade_in_animation = QPropertyAnimation(self.bottom_opacity_effect, b"opacity")
        self.fade_in_animation.setDuration(1000) # 1 segundo de fade
        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)
        self.fade_in_animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        self.fade_in_animation.finished.connect(self.swap_labels)
        self.fade_in_animation.start()
        
        self.current_image_index = next_index

    def swap_labels(self):
        """Chamado quando a animação termina. Prepara o próximo fade."""
        if not self.top_label:
            return

        ge = self.top_label.graphicsEffect()
        if ge is not None and hasattr(ge, "setOpacity"):
            try:
                ge.setOpacity(0.0)
            except Exception:
                new_eff = QGraphicsOpacityEffect()
                new_eff.setOpacity(0.0)
                self.top_label.setGraphicsEffect(new_eff)
        else:
            new_eff = QGraphicsOpacityEffect()
            new_eff.setOpacity(0.0)
            self.top_label.setGraphicsEffect(new_eff)

        temp = self.top_label
        self.top_label = self.bottom_label
        self.bottom_label = temp

        try:
            self.top_label.setGraphicsEffect(None)
        except Exception:
            pass

        self.bottom_opacity_effect = QGraphicsOpacityEffect()
        self.bottom_opacity_effect.setOpacity(0.0)
        self.bottom_label.setGraphicsEffect(self.bottom_opacity_effect)

    # --- Métodos de Mover a Janela ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.left_pane.geometry().contains(event.pos()):
                self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.old_pos and event.buttons() == Qt.LeftButton:
            delta = QPoint(event.globalPos() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    # --- Método de Login com AUDITORIA ---
    def check_login(self):
        user = self.user_input.text().strip()
        password = self.pass_input.text().strip()

        if not user or not password:
            QMessageBox.warning(self, "Erro", "Usuário e senha são obrigatórios.")
            return

        conn = get_connection()
        cur = conn.cursor()

        try:
            cur.execute("SELECT * FROM usuarios WHERE username = ? AND is_active = 1", (user,))
            user_data = cur.fetchone()

            if user_data and user_data["password_text"] == password:
                user_id = user_data["id"]
                theme_color = user_data["theme_color"]

                cur.execute("SELECT * FROM permissoes WHERE user_id = ?", (user_id,))
                perms_data = cur.fetchone()

                if perms_data and perms_data["modulos"] and perms_data["formularios"]:
                    
                    # --- LOG ADICIONADO ---
                    self.logger.info(f"Login efetuado com sucesso. Usuário: {user} (ID: {user_id})")
                    
                    module_permissions = json.loads(perms_data["modulos"])
                    form_permissions = json.loads(perms_data["formularios"])

                    if self.main_window and self.main_window.isVisible():
                        self.main_window.activateWindow()
                        return

                    self.hide()
                    self.main_window = MainWindow(
                        user_id,
                        module_permissions,
                        form_permissions,
                        theme_color,
                        login_window=self
                    )
                    self.main_window.show()
                else:
                    # --- LOG ADICIONADO ---
                    self.logger.warning(f"Tentativa de login falhou. Usuário {user} autenticou, mas não tem permissões configuradas.")
                    
                    QMessageBox.critical(
                        self,
                        "Erro Crítico",
                        "Usuário autenticado, mas sem permissões de módulo/formulário definidas."
                    )

            else:
                # --- LOG ADICIONADO ---
                self.logger.warning(f"Tentativa de login falhou. Usuário: {user} - Senha incorreta ou usuário não encontrado.")
                
                QMessageBox.warning(self, "Erro", "Usuário ou senha inválidos!")

        except Exception as e:
            self.logger.critical(f"Erro crítico de banco de dados durante o login: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro de Banco de Dados", f"Erro ao tentar logar: {e}")
        finally:
            conn.close()

    def show_again(self):
        """Chamado pela MainWindow para reexibir o login após o logout."""
        self.user_input.clear()
        self.pass_input.clear()
        # Limpa a referência
        self.main_window = None
        self.show()
        self.user_input.setFocus()

    # --- MÉTODOS DE BANDEJA ---
    def _setup_tray_icon(self):
        # (Verifica suporte e carrega ícone)
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
            
        base_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.normpath(os.path.join(base_dir, "..", "assets", "bandeja_1.ico"))
        
        icon = QIcon(icon_path)
        if icon.isNull():
            return

        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("BlueSys ERP")
        
        self.tray_menu = QMenu(self)
        
        show_action = QAction("Restaurar BlueSys", self)
        show_action.triggered.connect(self.show_active_window)
        self.tray_menu.addAction(show_action)
        
        self.tray_menu.addSeparator()
        
        quit_action = QAction("Encerrar Sistema", self)
        quit_action.triggered.connect(self.quit_application)
        self.tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()
        
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show_active_window()

    def show_active_window(self):
        # Se a main_window existe E não está no processo de logout
        if self.main_window and not self.main_window.is_logging_out:
            self.main_window.show_normal_and_raise()
        else:
            self.showNormal()
            self.activateWindow()
            self.raise_()

    def quit_application(self):
        reply = QMessageBox.question(
            self,
            "Encerrar Sistema",
            "Deseja realmente fechar o BlueSys ERP?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.logger.info("Encerrando aplicação via Bandeja do Sistema.")
            self.is_quitting_flag = True 
            if hasattr(self, 'tray_icon'):
                self.tray_icon.hide()
                
            if self.main_window:
                self.main_window.is_quitting_flag = True 
                self.main_window.close()
                
            self.close() 
            QApplication.instance().quit() 

    def closeEvent(self, event):
        """Intercepta o 'X' da tela de login."""
        if self.is_quitting_flag:
            event.accept()
        else:
            event.ignore()
            self.hide()
            if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
                 self.tray_icon.showMessage(
                    "BlueSys ERP",
                    "O sistema continua em execução.",
                    QSystemTrayIcon.Information,
                    2000
                )