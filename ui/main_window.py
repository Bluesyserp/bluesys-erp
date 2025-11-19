# -*- coding: utf-8 -*-
# ui/main_window.py
import os
import json
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QFrame, QMessageBox,
    QScrollArea, QSpacerItem, QSizePolicy, 
    QSystemTrayIcon, QMenu, QAction, QApplication, QDialog
)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import (
    Qt, QPoint, QPropertyAnimation, QParallelAnimationGroup, 
    QAbstractAnimation, pyqtSignal, QSize
)

# --- 1. IMPORTAÇÕES DE MÓDULOS (ATUALIZADAS) ---

# Módulos Padrão (Ativos)
from modules.admin_form import AdminForm
from modules.sales_form import SalesForm
from modules.customer_form import CustomerForm
from modules.company_form import CompanyForm 
from modules.fiscal_location_form import FiscalLocationForm 
from modules.terminal_form import TerminalForm 
from modules.relatorio_vendas_caixa import RelatorioVendasCaixa 
from modules.relatorio_vendas_produto import RelatorioVendasProduto
from modules.consulta_prevendas import ConsultaPreVendas
# --- NOVO: Motivos de Cancelamento ---
from modules.motivos_cancelamento_form import MotivosCancelamentoForm

# --- MÓDULOS DE CADASTRO ---
from modules.category_form import CategoryForm
from modules.depositos_form import DepositosForm 
from modules.product_base_form import ProductBaseForm 
from modules.pricing_manager import PricingManagerForm 
from modules.fornecedores_form import FornecedoresForm

# --- MÓDULOS FINANCEIROS ---
from modules.financeiro_form import FinanceiroForm
from modules.contas_financeiras_form import ContasFinanceirasForm
from modules.categorias_financeiras_form import CategoriasFinanceirasForm
from modules.centros_custo_form import CentrosCustoForm
from modules.relatorio_dre_form import RelatorioDREForm
from modules.relatorio_fluxo_caixa import RelatorioFluxoCaixa
# --- ATALHO HOME ---
from modules.lancamento_dialog import LancamentoDialog


# --- DUMMY CLASS (Placeholder) ---
class DummyModule(QWidget):
    """Placeholder simples para módulos não implementados."""
    form_closed = pyqtSignal()
    edit_product_requested = pyqtSignal(int)
    
    def __init__(self, user_id, title="Módulo em Desenvolvimento", **kwargs): 
        super().__init__()
        self.setWindowTitle(title)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(QLabel(f"--- {title} ---\n\nEsta tela está em desenvolvimento."))


# --- CLASSE INTERNA PARA O MENU CASCATA (Inalterada) ---
class CollapsibleMenu(QFrame):
    def __init__(self, title, accent_color, hover_color, parent=None):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.sub_buttons = []
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)

        self.toggle_btn = QPushButton(title)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        
        self.toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent_color}; 
                color: white; 
                border: 1px solid #000;
                border-bottom: 2px solid #101020;
                padding: 10px; text-align: left; font-size: 14px;
                border-radius: 6px;
            }}
            QPushButton:hover {{ 
                background-color: {hover_color};
            }}
        """)
        
        self.toggle_btn.clicked.connect(self.toggle)
        main_layout.addWidget(self.toggle_btn)

        self.content_area = QFrame()
        self.content_area.setContentsMargins(0, 0, 0, 0)
        self.content_area.setStyleSheet("background-color: transparent; border: none;")
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(10, 0, 0, 0) 
        self.content_layout.setSpacing(2)
        
        main_layout.addWidget(self.content_area)

        self.animation = QPropertyAnimation(self.content_area, b"maximumHeight")
        self.animation.setDuration(200) 
        
        self.content_area.setMaximumHeight(0)
        self.is_expanded = False

    def add_sub_button(self, text, on_click_func):
        """Adiciona um sub-botão ao menu."""
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(on_click_func)
        
        btn.setStyleSheet("""
            QPushButton {
                background-color: #3e3e5e; 
                color: #f0f0f0; padding: 8px; font-size: 13px;
                text-align: left; border-radius: 5px;
                border-bottom: 1px solid #2a2a4a;
            }
            QPushButton:hover {
                background-color: #4f4f7a;
            }
        """)
        
        self.content_layout.addWidget(btn)
        self.sub_buttons.append(btn)
        
    def toggle(self):
        """Expande ou recolhe o menu."""
        if self.is_expanded:
            self.animation.setStartValue(self.content_area.height())
            self.animation.setEndValue(0)
            self.is_expanded = False
        else:
            self.animation.setStartValue(0)
            height = self.content_layout.sizeHint().height()
            self.animation.setEndValue(height)
            self.is_expanded = True
            
        self.animation.start()


class MainWindow(QMainWindow):
    def __init__(self, user_id, module_permissions, form_permissions, theme_color, login_window=None):
        super().__init__()
        
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.old_pos = None
        self.is_logging_out = False 
        
        self.is_quitting_flag = False

        self.setWindowTitle("BlueSys ERP")
        self.setGeometry(100, 100, 1200, 700)
        
        self.current_user_id = user_id
        self.user_permissions = module_permissions
        self.form_permissions = form_permissions
        self.theme_color = theme_color
        self.login_window = login_window 
        
        self._setup_styles()
        
        self.modules = {} 
        self.current_content_widget = None

        self._build_ui()
        
        # Lógica de Início Inteligente
        if self.form_permissions.get("form_financeiro", False):
            self._set_module_content("financeiro_dashboard", FinanceiroForm)
        else:
            self._set_initial_content()

    def _setup_styles(self):
        self.accent_color = self.theme_color if self.theme_color else "#0078d7"
        
        if len(self.accent_color) == 7:
            try:
                r = int(self.accent_color[1:3], 16) - 20
                g = int(self.accent_color[3:5], 16) - 20
                b = int(self.accent_color[5:7], 16) - 20
                self.hover_color = f"#{max(r,0):02x}{max(g,0):02x}{max(b,0):02x}"
            except: self.hover_color = "#3c3c5c"
        else: self.hover_color = "#3c3c5c"

        self.setStyleSheet(f"""
            QMainWindow {{ background-color: #f5f5f5; }}
            
            QFrame#sidebar QPushButton {{
                background-color: {self.accent_color}; 
                color: white; 
                border: 1px solid #000;
                border-bottom: 2px solid #101020;
                padding: 10px; text-align: left; font-size: 14px;
                border-radius: 6px;
            }}
            QFrame#sidebar QPushButton:hover {{ 
                background-color: {self.hover_color};
            }} 
            
            QFrame#sidebar {{
                background-color: #1e1e2f; min-width: 230px; max-width: 250px;
                border-right: 2px solid #2b2b3d;
            }}
            QScrollArea#sidebar_scroll_area {{
                background-color: #1e1e2f; border: none;
            }}
            QWidget#sidebar_scroll_widget {{
                background-color: #1e1e2f;
            }}
            
            QPushButton#logoutButton {{
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 10px;
                text-align: left;
                border-radius: 6px;
                border: 1px solid #c0392b;
            }}
            QPushButton#logoutButton:hover {{
                background-color: #c0392b;
            }}
            QPushButton#logoutButton QLabel {{
                background-color: transparent;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border: none;
            }}
            
            #content_area {{ background-color: #f5f5f5; border-left: none; }}
            QFrame#custom_title_bar {{
                background-color: #f5f5f5; height: 30px;
            }}
            QLabel#version_label {{
                color: #888; font-weight: bold; padding-right: 15px;
            }}
            QPushButton#main_title_btn {{
                background-color: transparent; color: #333;
                font-family: "Arial"; font-weight: bold; font-size: 14px;
                border: none; max-width: 30px; max-height: 30px;
            }}
            QPushButton#main_title_btn:hover {{ background-color: #e0e0e0; }}
            QPushButton#main_close_btn {{
                background-color: transparent; color: #333;
                font-family: "Arial"; font-weight: bold; font-size: 14px;
                border: none; max-width: 30px; max-height: 30px;
            }}
            QPushButton#main_close_btn:hover {{
                background-color: #e81123; color: white;
            }}
            
            /* --- ESTILOS PARA O PAINEL RÁPIDO --- */
            QPushButton#shortcut_btn {{
                background-color: #ffffff;
                color: #333; 
                border: 1px solid #c0c0d0;
                font-size: 16px;
                font-weight: bold;
                padding: 20px;
                border-radius: 8px;
                min-height: 100px;
            }}
            QPushButton#shortcut_btn:hover {{
                background-color: #f0f0f0;
                border-color: #0078d7;
            }}
            QLabel#welcome_title {{
                font-size: 24px; color: #333; 
                margin-top: 15px; font-weight: bold;
            }}
            QLabel#logo_label {{
                max-height: 400px; /* Limita o tamanho do logo */
            }}
        """)

    def _build_ui(self):
        """Monta a estrutura principal da janela."""
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        
        sidebar_scroll_area = QScrollArea()
        sidebar_scroll_area.setObjectName("sidebar_scroll_area")
        sidebar_scroll_area.setWidgetResizable(True)
        sidebar_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        sidebar_scroll_widget = QWidget() 
        sidebar_scroll_widget.setObjectName("sidebar_scroll_widget")
        
        sidebar_layout = QVBoxLayout(sidebar_scroll_widget) 
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(5)
        
        sidebar_scroll_area.setWidget(sidebar_scroll_widget)
        
        sidebar_main_layout = QVBoxLayout(self.sidebar)
        sidebar_main_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_main_layout.addWidget(sidebar_scroll_area)
        
        def create_std_button(text, action):
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(action)
            return btn
        
        sidebar_layout.addWidget(create_std_button("Painel Rápido (Home)", lambda: self._set_initial_content()))
        
        if self.user_permissions.get("mod_cadastros", False):
            
            menu_cadastros = CollapsibleMenu("Cadastros", self.accent_color, self.hover_color)
            has_cadastro_item = False
            
            if self.form_permissions.get("form_category", False):
                menu_cadastros.add_sub_button("Cadastro de Classes", lambda: self._set_module_content("categorias", CategoryForm))
                has_cadastro_item = True
            
            if self.form_permissions.get("form_product", False):
                menu_cadastros.add_sub_button("Cadastro de Produtos", lambda: self._set_module_content("produtos_cadastro", ProductBaseForm, start_mode='new'))
                has_cadastro_item = True
            
            if self.form_permissions.get("form_product_list", False):
                menu_cadastros.add_sub_button("Consulta de Produtos", lambda: self._set_module_content("produtos_consulta", ProductBaseForm))
                has_cadastro_item = True
            
            if self.form_permissions.get("form_customer", False):
                menu_cadastros.add_sub_button("Clientes", lambda: self._set_module_content("clientes", CustomerForm))
                has_cadastro_item = True

            if self.form_permissions.get("form_fornecedor", False):
                menu_cadastros.add_sub_button("Fornecedores", lambda: self._set_module_content("fornecedores", FornecedoresForm))
                has_cadastro_item = True
            
            if has_cadastro_item:
                sidebar_layout.addWidget(menu_cadastros)
        
        if self.user_permissions.get("mod_empresa_config", False):
            menu_configs = CollapsibleMenu("Config. Empresa", self.accent_color, self.hover_color)
            has_config_item = False
            
            if self.form_permissions.get("form_empresas", False):
                menu_configs.add_sub_button("Cadastro de Empresas", lambda: self._set_module_content("form_empresas", CompanyForm))
                has_config_item = True
            
            if self.form_permissions.get("form_locais_escrituracao", False):
                menu_configs.add_sub_button("Cadastro de Locais de Escrituração", lambda: self._set_module_content("form_locais_escrituracao", FiscalLocationForm))
                has_config_item = True
                
            if self.form_permissions.get("form_pricing_manager", False): 
                 menu_configs.add_sub_button("Gestão de Preços (CNPJ)", lambda: self._set_module_content("pricing_manager", PricingManagerForm))
                 has_config_item = True
            
            if self.form_permissions.get("form_depositos", False):
                menu_configs.add_sub_button("Locais de Estoque (Depósitos)", lambda: self._set_module_content("depositos", DepositosForm))
                has_config_item = True
            
            if has_config_item:
                sidebar_layout.addWidget(menu_configs)

        if self.user_permissions.get("mod_comercial", False):
            menu_comercial = CollapsibleMenu("Comercial", self.accent_color, self.hover_color)
            has_comercial_item = False
            if self.form_permissions.get("form_sales", False):
                menu_comercial.add_sub_button("Ponto de Venda (PDV)", lambda: self._set_module_content("vendas", SalesForm))
                has_comercial_item = True
            if self.form_permissions.get("consulta_prevendas", False):
                menu_comercial.add_sub_button("Consulta de Pré-Vendas", lambda: self._set_module_content("consulta_prevendas", ConsultaPreVendas))
                has_comercial_item = True
            if self.form_permissions.get("form_terminais_pdv", False):
                menu_comercial.add_sub_button("Config. Terminais (PDV)", lambda: self._set_module_content("form_terminais_pdv", TerminalForm))
                has_comercial_item = True
            
            # --- NOVO: Motivos de Cancelamento ---
            if self.form_permissions.get("form_motivos_cancelamento", False):
                menu_comercial.add_sub_button("Motivos de Cancelamento", lambda: self._set_module_content("motivos_cancelamento", MotivosCancelamentoForm))
                has_comercial_item = True
            # --- FIM NOVO ---

            if self.form_permissions.get("relatorio_vendas_caixa", False):
                menu_comercial.add_sub_button("Relatório: Vendas por Caixa", lambda: self._set_module_content("relatorio_vendas_caixa", RelatorioVendasCaixa))
                has_comercial_item = True
            if self.form_permissions.get("relatorio_vendas_produto", False):
                menu_comercial.add_sub_button("Relatório: Vendas por Produto", lambda: self._set_module_content("relatorio_vendas_produto", RelatorioVendasProduto))
                has_comercial_item = True
            if has_comercial_item:
                sidebar_layout.addWidget(menu_comercial)

        if self.user_permissions.get("mod_contabil", False):
            sidebar_layout.addWidget(create_std_button("Contábil", lambda: self._set_module_content("contabil", DummyModule, title="Módulo Contábil")))
        if self.user_permissions.get("mod_dp", False):
            sidebar_layout.addWidget(create_std_button("DP", lambda: self._set_module_content("dp", DummyModule, title="Módulo DP")))
        
        if self.user_permissions.get("mod_financeiro", False):
            menu_financeiro = CollapsibleMenu("Financeiro", self.accent_color, self.hover_color)
            has_financeiro_item = False
            
            if self.form_permissions.get("form_financeiro", False):
                menu_financeiro.add_sub_button("Dashboard Financeiro", lambda: self._set_module_content("financeiro_dashboard", FinanceiroForm))
                has_financeiro_item = True
            if self.form_permissions.get("form_contas_financeiras", False):
                menu_financeiro.add_sub_button("Cadastro de Contas (Disponíveis)", lambda: self._set_module_content("contas_financeiras", ContasFinanceirasForm))
                has_financeiro_item = True
            if self.form_permissions.get("form_categorias_financeiras", False):
                menu_financeiro.add_sub_button("Plano de Contas (Categorias)", lambda: self._set_module_content("categorias_financeiras", CategoriasFinanceirasForm))
                has_financeiro_item = True
            if self.form_permissions.get("form_centros_de_custo", False):
                menu_financeiro.add_sub_button("Centros de Custo", lambda: self._set_module_content("centros_de_custo", CentrosCustoForm))
                has_financeiro_item = True
            if self.form_permissions.get("form_relatorio_dre", False):
                menu_financeiro.add_sub_button("Relatório DRE", lambda: self._set_module_content("relatorio_dre", RelatorioDREForm))
                has_financeiro_item = True
            if self.form_permissions.get("form_relatorio_fluxo_caixa", False):
                menu_financeiro.add_sub_button("Relatório Fluxo de Caixa", lambda: self._set_module_content("relatorio_fluxo_caixa", RelatorioFluxoCaixa))
                has_financeiro_item = True
            
            if has_financeiro_item:
                sidebar_layout.addWidget(menu_financeiro)
            else:
                sidebar_layout.addWidget(create_std_button("Financeiro", lambda: self._set_module_content("financeiro", DummyModule, title="Módulo Financeiro")))
        
        if self.user_permissions.get("mod_fiscal", False):
            sidebar_layout.addWidget(create_std_button("Fiscal", lambda: self._set_module_content("fiscal", DummyModule, title="Módulo Fiscal")))
        if self.user_permissions.get("mod_logistica", False):
            sidebar_layout.addWidget(create_std_button("Logística", lambda: self._set_module_content("logistica", DummyModule, title="Módulo Logística")))
        if self.user_permissions.get("mod_operacao", False):
            sidebar_layout.addWidget(create_std_button("Operação", lambda: self._set_module_content("mod_operacao", DummyModule, title="Módulo Operação"))) 
        if self.user_permissions.get("mod_relatorios", False):
            sidebar_layout.addWidget(create_std_button("Relatórios", lambda: self._set_module_content("mod_relatorios", DummyModule, title="Módulo Relatórios")))
        
        if self.user_permissions.get("mod_administracao", False) and self.form_permissions.get("form_admin", False):
            sidebar_layout.addWidget(create_std_button("Administração", lambda: self._set_module_content("admin", AdminForm)))
        
        sidebar_layout.addStretch() 
        
        self.logout_btn = QPushButton()
        self.logout_btn.setObjectName("logoutButton")
        self.logout_btn.setCursor(Qt.PointingHandCursor)
        
        logout_layout = QHBoxLayout(self.logout_btn)
        logout_layout.setContentsMargins(0, 0, 0, 0)
        logout_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        logout_layout.setSpacing(5) 
        
        logout_icon_label = QLabel()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        logout_icon_path = os.path.join(base_dir, "..", "assets", "logout.png")
        if os.path.exists(logout_icon_path):
            pixmap = QPixmap(logout_icon_path)
            logout_icon_label.setPixmap(pixmap.scaled(QSize(60, 60), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        logout_text_label = QLabel("Logout")
        
        logout_layout.addSpacerItem(QSpacerItem(5, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)) 
        logout_layout.addWidget(logout_icon_label)
        logout_layout.addWidget(logout_text_label)
        logout_layout.addStretch()
        
        self.logout_btn.clicked.connect(self._prompt_logout)
        sidebar_layout.addWidget(self.logout_btn)

        self.content_area = QWidget() 
        self.content_area.setObjectName("content_area")
        self.content_layout = QVBoxLayout(self.content_area) 
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_layout.setSpacing(0) 
        
        self.custom_title_bar = QFrame()
        self.custom_title_bar.setObjectName("custom_title_bar")
        title_bar_layout = QHBoxLayout(self.custom_title_bar)
        title_bar_layout.setContentsMargins(0, 0, 5, 0)
        title_bar_layout.addStretch() 
        self.version_label = QLabel("BlueSys ERP v1.0.0")
        self.version_label.setObjectName("version_label")
        title_bar_layout.addWidget(self.version_label, 0, Qt.AlignRight)
        
        self.btn_minimize_main = QPushButton("_")
        self.btn_minimize_main.setObjectName("main_title_btn")
        self.btn_minimize_main.setToolTip("Minimizar")
        self.btn_minimize_main.clicked.connect(self.hide) 
        
        self.btn_maximize_main = QPushButton("☐")
        self.btn_maximize_main.setObjectName("main_title_btn")
        self.btn_maximize_main.setToolTip("Maximizar")
        self.btn_maximize_main.clicked.connect(self.toggle_maximize)
        
        self.btn_close_main = QPushButton("X")
        self.btn_close_main.setObjectName("main_close_btn")
        self.btn_close_main.setToolTip("Fechar")
        self.btn_close_main.clicked.connect(self.close) 
        
        title_bar_layout.addWidget(self.btn_minimize_main)
        title_bar_layout.addWidget(self.btn_maximize_main)
        title_bar_layout.addWidget(self.btn_close_main)
        
        self.content_layout.addWidget(self.custom_title_bar)
        self.content_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft) 

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content_area, 1) 
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def toggle_maximize(self):
        if self.isFullScreen():
            self.showNormal()
            self.btn_maximize_main.setText("☐")
        else:
            self.showFullScreen()
            self.btn_maximize_main.setText("❐")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.sidebar.isVisible() and event.pos().x() <= self.sidebar.width():
                 self.old_pos = event.globalPos()
            elif event.pos().y() <= self.custom_title_bar.height():
                 self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.old_pos and event.buttons() == Qt.LeftButton:
            delta = QPoint(event.globalPos() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            "Encerrar sessão",
            "Deseja realmente encerrar a sessão e voltar à tela de login?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.login_window:
                self.login_window.show_again()
                self.login_window.main_window = None
            event.accept()
            self.deleteLater()
        else:
            event.ignore()
    
    def _prompt_logout(self):
        if self.is_logging_out:
            return

        reply = QMessageBox.question(self, "Logout",
                                     "Tem certeza que deseja fazer logout do sistema?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            if self.login_window:
                self.is_logging_out = True 
                self.login_window.show_again() 
                self.close() 
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível retornar à tela de login. Reinicie o aplicativo.")
                self.is_logging_out = True
                self.close()

    def _set_initial_content(self):
        self.sidebar.setVisible(True)
        
        if self.current_content_widget:
            if hasattr(self.current_content_widget, 'caixaStateChanged'):
                try: self.current_content_widget.caixaStateChanged.disconnect(self.toggle_kiosk_mode)
                except TypeError: pass
            if hasattr(self.current_content_widget, 'toggleMenuRequested'):
                try: self.current_content_widget.toggleMenuRequested.disconnect(self.toggle_sidebar_visibility)
                except TypeError: pass
            if hasattr(self.current_content_widget, 'form_closed'):
                try: self.current_content_widget.form_closed.disconnect(self._handle_form_closure)
                except TypeError: pass
            if hasattr(self.current_content_widget, 'edit_product_requested'):
                try: self.current_content_widget.edit_product_requested.disconnect(self._open_product_for_edit)
                except TypeError: pass
            
            self.content_layout.removeWidget(self.current_content_widget)
            self.current_content_widget.hide()
            self.current_content_widget = None

        initial_widget = QWidget()
        initial_layout = QVBoxLayout(initial_widget)
        initial_layout.setAlignment(Qt.AlignCenter)
        initial_layout.setContentsMargins(50, 20, 50, 20)
        initial_layout.setSpacing(20)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.abspath(os.path.join(base_dir, "..", "assets", "logo.png"))
        logo_label = QLabel()
        logo_label.setObjectName("logo_label") 
        logo_label.setAlignment(Qt.AlignCenter)

        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                logo_label.setPixmap(
                    pixmap.scaled(750, 450, Qt.KeepAspectRatio, Qt.SmoothTransformation) 
                )
            else:
                logo_label.setText("❌ Erro: imagem inválida.")
        else:
            logo_label.setText("❌ Logo não encontrada.")
        
        initial_layout.addWidget(logo_label, 1) 

        welcome_label = QLabel("Bem-vindo ao BlueSys ERP")
        welcome_label.setObjectName("welcome_title")
        welcome_label.setAlignment(Qt.AlignCenter)
        initial_layout.addWidget(welcome_label)
        
        shortcut_layout = QHBoxLayout()
        shortcut_layout.setSpacing(20)
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        btn_pdv = QPushButton("Abrir Ponto de Venda (PDV)")
        btn_pdv.setObjectName("shortcut_btn")
        pdv_icon_path = os.path.abspath(os.path.join(base_dir, "..", "assets", "pdv.png")) 
        if os.path.exists(pdv_icon_path):
            btn_pdv.setIcon(QIcon(pdv_icon_path))
            btn_pdv.setIconSize(QSize(48, 48))
        btn_pdv.clicked.connect(lambda: self._set_module_content("vendas", SalesForm))
        
        btn_financeiro = QPushButton("Dashboard Financeiro")
        btn_financeiro.setObjectName("shortcut_btn")
        fin_icon_path = os.path.abspath(os.path.join(base_dir, "..", "assets", "financeiro.png")) 
        if os.path.exists(fin_icon_path):
            btn_financeiro.setIcon(QIcon(fin_icon_path))
            btn_financeiro.setIconSize(QSize(48, 48))
        btn_financeiro.clicked.connect(lambda: self._set_module_content("financeiro_dashboard", FinanceiroForm))
        
        btn_novo_lanc = QPushButton("Novo Lançamento")
        btn_novo_lanc.setObjectName("shortcut_btn")
        btn_novo_lanc.setStyleSheet("background-color: #f0f9f2; border-color: #2ECC71;") 
        btn_novo_lanc.clicked.connect(self._open_new_lancamento_dialog_from_home)
        
        shortcut_layout.addWidget(btn_pdv)
        shortcut_layout.addWidget(btn_financeiro)
        shortcut_layout.addWidget(btn_novo_lanc)
        
        if not self.form_permissions.get("form_sales", False):
            btn_pdv.hide()
        if not self.form_permissions.get("form_financeiro", False):
            btn_financeiro.hide()
            btn_novo_lanc.hide()
        
        initial_layout.addLayout(shortcut_layout)
        initial_layout.addStretch(1)
        
        self.content_layout.addWidget(initial_widget, 1)
        self.current_content_widget = initial_widget
        self.setWindowTitle("BlueSys ERP")
        print("Painel Rápido (Home) definido.")
    
    def _open_new_lancamento_dialog_from_home(self):
        dialog = LancamentoDialog(self.current_user_id, 1, self)
        if dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "Sucesso", "Lançamento criado com sucesso!")
            if self.current_content_widget and isinstance(self.current_content_widget, FinanceiroForm):
                self.current_content_widget.load_dashboard_data()
                self.current_content_widget.load_lancamentos()

    def _set_module_content(self, module_key, module_class, **kwargs):
        if module_key != "vendas":
            self.sidebar.setVisible(True)
        
        if self.current_content_widget:
            if hasattr(self.current_content_widget, 'caixaStateChanged'):
                try: self.current_content_widget.caixaStateChanged.disconnect(self.toggle_kiosk_mode)
                except TypeError: pass
            if hasattr(self.current_content_widget, 'toggleMenuRequested'):
                try: self.current_content_widget.toggleMenuRequested.disconnect(self.toggle_sidebar_visibility)
                except TypeError: pass
            if hasattr(self.current_content_widget, 'form_closed'):
                try: self.current_content_widget.form_closed.disconnect(self._handle_form_closure)
                except TypeError: pass
            if hasattr(self.current_content_widget, 'edit_product_requested'):
                try: self.current_content_widget.edit_product_requested.disconnect(self._open_product_for_edit)
                except TypeError: pass

            self.content_layout.removeWidget(self.current_content_widget)
            self.current_content_widget.hide()
            self.current_content_widget = None

        try:
            print(f"Criando nova instância para o módulo: {module_key} com kwargs: {kwargs}")
            
            if module_class is DummyModule:
                module_widget = module_class(self.current_user_id, title=kwargs.get('title', 'Módulo em Desenvolvimento'))
            else:
                module_widget = module_class(self.current_user_id, **kwargs)
                
            self.modules[module_key] = module_widget
            
            if module_key == "vendas":
                module_widget.caixaStateChanged.connect(self.toggle_kiosk_mode)
                module_widget.toggleMenuRequested.connect(self.toggle_sidebar_visibility)
            
            if hasattr(module_widget, 'form_closed'):
                module_widget.form_closed.connect(self._handle_form_closure)
            
            self.content_layout.addWidget(module_widget, 1)
            module_widget.show()
            self.current_content_widget = module_widget
            self.setWindowTitle(f"BlueSys ERP - {module_widget.windowTitle()}")
            
            print(f"Módulo '{module_key}' carregado.")

        except TypeError as e:
            print(f"Erro ao carregar módulo {module_key}: {e}")
            QMessageBox.critical(self, "Erro de Módulo",
                f"Não foi possível carregar o módulo {module_key}.\n"
                f"O construtor do módulo pode estar incorreto: {e}")
            self._set_initial_content()
            
    def _open_product_for_edit(self, product_id):
        print(f"Recebido pedido para editar produto ID: {product_id}")
        self._set_module_content(
            "produtos", 
            ProductBaseForm, 
            product_id_to_load=product_id 
        )

    def _handle_form_closure(self):
        if self.current_content_widget:
            self.content_layout.removeWidget(self.current_content_widget)
            self.current_content_widget.hide()
            self.current_content_widget = None
        self._set_initial_content()

    def toggle_kiosk_mode(self, is_caixa_open):
        self.sidebar.setVisible(not is_caixa_open)

    def toggle_sidebar_visibility(self):
        self.sidebar.setVisible(not self.sidebar.isVisible())

    def show_normal_and_raise(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()