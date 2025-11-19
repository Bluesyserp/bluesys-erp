# modules/sales_form.py
import json
import sqlite3
import re
import os
import socket 
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QGridLayout, QFrame, QTableWidget, QTableWidgetItem, 
    QHeaderView, QAbstractItemView, QDialog,
    QStackedWidget, QShortcut 
)
from PyQt5.QtGui import QFont, QKeySequence, QPixmap
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from database.db import get_connection

# --- Importações dos Diálogos ---
from .payment_dialog import PaymentDialog
from .open_cash_dialog import OpenCashDialog
from .customer_quick_dialog import CustomerQuickDialog
from .product_search_dialog import ProductSearchDialog 
from .custom_dialogs import CustomInputDialog, CustomComboDialog 
from .authorization_dialog import AuthorizationDialog
from .close_cash_dialog import CloseCashDialog
from .z_report_view import ZReportView
from .cash_movement_dialog import CashMovementDialog
from .finalize_sale_dialog import FinalizeSaleDialog
from .sales_functions_dialog import SalesFunctionsDialog
from .cancel_sale_dialog import CancelSaleDialog

# --- Importações dos Módulos de Lógica ---
from .printing_service import generate_and_print_receipt, generate_and_print_cancellation_receipt
from .pos_controller import PosController 

class SalesForm(QWidget):
    caixaStateChanged = pyqtSignal(bool)
    toggleMenuRequested = pyqtSignal()

    def __init__(self, user_id):
        super().__init__() 
        
        self.user_id = user_id
        self.setWindowTitle("Ponto de Venda (PDV)")
        
        self.controller = PosController(user_id)
        
        self.cart_items = [] 
        self.current_cliente_id = 1
        self.current_cliente_nome = "CONSUMIDOR FINAL"
        
        self.subtotal = 0.0
        self.desconto_itens = 0.0
        self.desconto_geral = 0.0
        self.total_final = 0.0
        self.sale_started = False
        self.prevenda_origem_id_para_conversao = None
        
        self.nome_terminal = self.controller.nome_terminal
        is_terminal_valid = self.controller.is_terminal_valid
        
        self._setup_styles()
        self._build_ui() 
        self._apply_field_permissions()
        self._setup_shortcuts()
        
        if not is_terminal_valid:
            self.show_terminal_error(
                f"Este terminal (Hostname: {socket.gethostname()}) não está cadastrado ou está inativo.\n\n"
                "Acesse (Config. Empresa -> Config. Terminais (PDV)) e vincule esta máquina."
            )
            self.setEnabled(False)
        elif not self.controller.user_field_permissions.get("pode_abrir_caixa", "Negado") == "Total":
            self.show_terminal_error("Acesso Negado. Você não tem permissão para operar o caixa.")
            self.setEnabled(False)

    def show_terminal_error(self, message):
        error_box = QMessageBox(self)
        error_box.setIcon(QMessageBox.Critical)
        error_box.setWindowTitle("Erro de Terminal")
        error_box.setText(message)
        error_box.setStandardButtons(QMessageBox.Ok)
        error_box.exec_()
        self.setEnabled(False) 

    def _setup_shortcuts(self):
        self.sc_f2 = QShortcut(QKeySequence("F2"), self)
        self.sc_f3 = QShortcut(QKeySequence("F3"), self)
        self.sc_f4 = QShortcut(QKeySequence("F4"), self)
        self.sc_f5 = QShortcut(QKeySequence("F5"), self) 
        
        # F6 e F7 removidos da tela principal (agora dentro de F5 - Funções)
        
        self.sc_f8 = QShortcut(QKeySequence("F8"), self)
        self.sc_f9 = QShortcut(QKeySequence("F9"), self)   # Atalho direto para Nao-Fiscal (opcional)
        self.sc_f10 = QShortcut(QKeySequence("F10"), self) # Finalizar (Abre Dialog)
        self.sc_f11 = QShortcut(QKeySequence("F11"), self)
        self.sc_f12 = QShortcut(QKeySequence("F12"), self)
        self.sc_esc = QShortcut(QKeySequence("Esc"), self)
        self.sc_ctrl_f8 = QShortcut(QKeySequence("Ctrl+F8"), self)

        if self.controller.habilita_nao_fiscal:
            self.sc_load_prevenda = QShortcut(QKeySequence("#"), self)
            self.sc_load_prevenda.activated.connect(lambda: self.product_search.setText("#"))

        self.sc_f2.activated.connect(self.btn_change_customer.click)
        self.sc_f3.activated.connect(self.btn_buscar_produto.click)
        self.sc_f4.activated.connect(self.btn_excluir_item.click)
        self.sc_f5.activated.connect(self.btn_funcoes.click)
        
        self.sc_f8.activated.connect(self.btn_cancelar.click)
        
        # F10 agora chama o prompt de finalização (que abre o diálogo F9/F10)
        self.sc_f10.activated.connect(self._prompt_finalize_type)
        
        self.sc_f11.activated.connect(self.btn_abrir_fechar_caixa.click)
        self.sc_f12.activated.connect(self.toggleMenuRequested.emit)
        self.sc_esc.activated.connect(self.btn_cancelar.click)
        self.sc_ctrl_f8.activated.connect(self._prompt_cancel_finalized_sale)
        
        f1_label_text = "Cód. Barras/Atender (#) (F1):" if self.controller.habilita_nao_fiscal else "Cód. Barras (F1):"
        f1_label = QLabel(f1_label_text, objectName="search_label")
        f1_label.setBuddy(self.product_search)
        self.search_layout.addWidget(f1_label, 0, 0) 

    def _set_main_shortcuts_enabled(self, enabled):
        self.sc_f2.setEnabled(enabled)
        self.sc_f3.setEnabled(enabled)
        self.sc_f4.setEnabled(enabled)
        self.sc_f5.setEnabled(enabled)
        self.sc_f8.setEnabled(enabled)
        self.sc_f9.setEnabled(enabled)
        self.sc_f10.setEnabled(enabled)
        self.sc_f11.setEnabled(enabled)
        self.sc_f12.setEnabled(enabled)
        self.sc_esc.setEnabled(enabled)
        self.sc_ctrl_f8.setEnabled(enabled) 
        
        if enabled:
            self.product_search.setFocus()
        
    def showEvent(self, event):
        super().showEvent(event)
        if not self.isEnabled(): return
        
        if self.controller.is_terminal_valid:
            if self.controller.tabela_id_ativa is None:
                self.show_terminal_error(
                    "Erro de Precificação:\n\n"
                    f"Nenhuma Tabela de Preço ATIVA vinculada ao CNPJ {self.controller.identificador_loja} "
                    "foi encontrada.\n\nConfigure a Tabela em (Config. Empresa -> Gestão de Preços)."
                )
                self.setEnabled(False)
                return
                
            if self.controller.deposito_id_padrao is None:
                self.show_terminal_error(
                    "Erro de Estoque:\n\n"
                    "Nenhum Depósito Padrão foi vinculado a este terminal.\n\n"
                    "Acesse (Config. Empresa -> Config. Terminais (PDV)) e vincule um depósito."
                )
                self.setEnabled(False)
                return
            
            self.controller.check_caixa_status()
            if self.controller.current_caixa_id:
                self.set_caixa_aberto(self.controller.current_caixa_id)
            else:
                self.set_caixa_fechado()

    def set_caixa_fechado(self):
        self.controller.current_caixa_id = None
        self.stack.setCurrentIndex(0) 
        self.btn_abrir_fechar_caixa.setText("Abrir Caixa (F11)") 
        self.btn_abrir_fechar_caixa.setStyleSheet("background-color: #2ECC71;")
        self.set_venda_botoes_enabled(False) 
        self.caixaStateChanged.emit(False) 
        self._set_main_shortcuts_enabled(True) 

    def set_caixa_aberto(self, caixa_id):
        self.controller.current_caixa_id = caixa_id
        self.stack.setCurrentIndex(1) 
        self.cart_stack.setCurrentIndex(0) 
        self.btn_abrir_fechar_caixa.setText("Fechar Caixa (F11)") 
        self.btn_abrir_fechar_caixa.setStyleSheet("background-color: #95A5A6;")
        self.set_venda_botoes_enabled(True) 
        self.start_new_sale_flow()
        self.caixaStateChanged.emit(True) 
        self._set_main_shortcuts_enabled(True) 
        
    def set_venda_botoes_enabled(self, enabled):
        self.btn_change_customer.setEnabled(enabled)
        self.btn_buscar_produto.setEnabled(enabled)
        self.btn_funcoes.setEnabled(enabled)
        self.btn_excluir_item.setEnabled(enabled) 
        self.btn_finalizar_venda.setEnabled(enabled) # Botão único F10
        self.btn_cancelar.setEnabled(enabled)
        self.product_search.setEnabled(enabled)
        self.btn_abrir_fechar_caixa.setEnabled(True) 
        self.btn_cancelar_finalizada.setEnabled(enabled)
        
        self.btn_buscar_produto.setText("Buscar Produto (F3)")
        self.btn_buscar_produto.setToolTip("Abre o diálogo de busca de produtos por nome.")
        
        self._apply_field_permissions()

    def _setup_styles(self):
        self.setStyleSheet("""
            QWidget { background-color: #f8f8fb; font-family: 'Segoe UI'; }
            QFrame#closed_panel { background-color: white; border: 1px solid #c0c0d0; border-radius: 8px; }
            QLabel#caixa_fechado_label { font-size: 32px; font-weight: bold; color: #e74c3c; }
            QFrame#caixa_livre_panel { background-color: transparent; border: none; }
            QLabel#caixa_livre_label { font-size: 32px; font-weight: bold; color: #0078d7; }
            QFrame#search_panel, QFrame#customer_panel { background-color: white; border: 1px solid #c0c0d0; border-radius: 8px; }
            QLabel#search_label { font-size: 16px; font-weight: bold; color: #555; }
            QLineEdit#product_search { padding: 10px; font-size: 18px; font-weight: bold; border: 1px solid #c0c0d0; border-radius: 5px; }
            QLineEdit#product_search:focus { border: 2px solid #0078d7; }
            QLabel#product_name_display { font-size: 24px; font-weight: bold; color: #0078d7; padding-left: 10px; }
            QLabel#customer_display { font-size: 14px; font-weight: bold; color: #333; }
            QLabel#terminal_display { font-size: 12px; font-weight: bold; color: #7F8C8D; border: 1px solid #ddd; background-color: #f0f0f0; padding: 5px; border-radius: 5px; max-height: 25px; }
            QTableWidget { border: 1px solid #c0c0d0; selection-background-color: #0078d7; selection-color: white; gridline-color: #d0d0d0; font-size: 14px; }
            QTableWidget::item { padding: 8px; }
            QHeaderView::section { background-color: #e8e8e8; padding: 8px; border: 1px solid #c0c0d0; font-weight: bold; font-size: 14px; }
            QFrame#total_panel { background-color: white; border: 1px solid #c0c0d0; border-radius: 8px; }
            QLabel.total_calc_label { font-size: 16px; font-weight: normal; color: #555; }
            QLabel.total_calc_value { font-size: 16px; font-weight: bold; color: #333; }
            QLabel.total_calc_desconto { font-size: 16px; font-weight: bold; color: #e74c3c; }
            QLabel#total_final_label { font-size: 20px; font-weight: bold; color: #333; border-top: 1px solid #eee; padding-top: 10px; }
            QLabel#total_final_value { font-size: 40px; font-weight: bold; color: #0078d7; padding-top: 5px; }
            QLabel#product_image_display { border: 1px solid #c0c0d0; background-color: white; border-radius: 8px; min-height: 200px; }
            QPushButton { background-color: #0078d7; color: white; border-radius: 6px; padding: 12px 20px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background-color: #005fa3; }
            QPushButton#btn_cancelar, QPushButton#btn_excluir_item, QPushButton#btn_cancelar_finalizada { background-color: #e74c3c; }
            QPushButton#btn_cancelar:hover, QPushButton#btn_excluir_item:hover, QPushButton#btn_cancelar_finalizada:hover { background-color: #c0392b; }
            QPushButton#btn_funcoes { background-color: #f39c12; }
            QPushButton#btn_funcoes:hover { background-color: #e67e22; }
            
            QPushButton#btn_finalizar_venda { background-color: #2ECC71; }
            QPushButton#btn_finalizar_venda:hover { background-color: #27AE60; }
            
            QPushButton#btn_abrir_fechar_caixa, QPushButton#btn_toggle_menu { background-color: #95A5A6; }
            QPushButton#btn_abrir_fechar_caixa:hover, QPushButton#btn_toggle_menu:hover { background-color: #7F8C8D; }
            QPushButton:disabled { background-color: #aaa; color: #eee; }
        """)

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        
        self.stack = QStackedWidget()
        
        self.closed_widget = QFrame()
        self.closed_widget.setObjectName("closed_panel")
        closed_layout = QVBoxLayout(self.closed_widget)
        closed_layout.setAlignment(Qt.AlignCenter)
        self.label_caixa_status = QLabel("CAIXA FECHADO")
        self.label_caixa_status.setObjectName("caixa_fechado_label")
        closed_layout.addWidget(self.label_caixa_status, 0, Qt.AlignCenter)
        self.stack.addWidget(self.closed_widget)
        
        self.pdv_widget = QWidget()
        pdv_layout = QHBoxLayout(self.pdv_widget)
        
        left_layout = QVBoxLayout()
        
        customer_panel = QFrame()
        customer_panel.setObjectName("customer_panel")
        cust_layout = QHBoxLayout(customer_panel)
        
        self.terminal_display = QLabel(f"Terminal: {self.nome_terminal}")
        self.terminal_display.setObjectName("terminal_display")
        cust_layout.addWidget(self.terminal_display)
        cust_layout.addStretch(1) 
        
        self.customer_display = QLabel("Cliente: CONSUMIDOR FINAL")
        self.customer_display.setObjectName("customer_display")
        cust_layout.addWidget(self.customer_display)
        cust_layout.addStretch(1)
        
        self.btn_change_customer = QPushButton("Identificar Cliente (F2)")
        self.btn_change_customer.clicked.connect(self.identify_customer)
        cust_layout.addWidget(self.btn_change_customer)
        left_layout.addWidget(customer_panel)
        
        search_panel = QFrame()
        search_panel.setObjectName("search_panel")
        self.search_layout = QGridLayout(search_panel)
        self.search_layout.setContentsMargins(20, 20, 20, 20)
        
        self.product_search = QLineEdit()
        self.product_search.setObjectName("product_search")
        self.product_search.returnPressed.connect(self.search_product)
        self.search_layout.addWidget(self.product_search, 1, 0, 1, 2)
        
        self.product_name_display = QLabel("Aguardando produto...")
        self.product_name_display.setObjectName("product_name_display")
        self.product_name_display.setAlignment(Qt.AlignCenter)
        self.search_layout.addWidget(self.product_name_display, 0, 2, 2, 1)
        self.search_layout.setColumnStretch(2, 1)
        left_layout.addWidget(search_panel)

        self.cart_stack = QStackedWidget()
        
        caixa_livre_panel = QFrame()
        caixa_livre_panel.setObjectName("caixa_livre_panel")
        caixa_livre_layout = QVBoxLayout(caixa_livre_panel)
        caixa_livre_layout.setAlignment(Qt.AlignCenter)
        caixa_livre_label = QLabel("CAIXA LIVRE")
        caixa_livre_label.setObjectName("caixa_livre_label")
        caixa_livre_layout.addWidget(caixa_livre_label)
        self.cart_stack.addWidget(caixa_livre_panel)

        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(6)
        self.cart_table.setHorizontalHeaderLabels(["Código", "Descrição", "Qtd.", "Preço Unit.", "Desconto", "Total Item"])
        self.cart_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.cart_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.cart_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.cart_table.itemSelectionChanged.connect(self._on_cart_item_selected) 
        self.cart_stack.addWidget(self.cart_table)
        
        left_layout.addWidget(self.cart_stack, 1)
        
        pdv_layout.addLayout(left_layout, 3)
        self.stack.addWidget(self.pdv_widget)
        
        # --- Coluna Direita (Limpa e Organizada) ---
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(10, 0, 0, 0)
        
        total_panel = QFrame()
        total_panel.setObjectName("total_panel")
        total_layout = QGridLayout(total_panel)
        total_layout.setContentsMargins(15, 15, 15, 15)
        
        total_layout.addWidget(QLabel("Subtotal (Bruto)", objectName="total_calc_label"), 0, 0)
        self.lbl_total_bruto = QLabel("R$ 0,00", objectName="total_calc_value")
        total_layout.addWidget(self.lbl_total_bruto, 0, 1, Qt.AlignRight)
        
        total_layout.addWidget(QLabel("Descontos", objectName="total_calc_label"), 1, 0)
        self.lbl_total_descontos = QLabel("- R$ 0,00", objectName="total_calc_desconto")
        total_layout.addWidget(self.lbl_total_descontos, 1, 1, Qt.AlignRight)
        
        total_layout.addWidget(QLabel("TOTAL A PAGAR", objectName="total_final_label"), 2, 0, 1, 2)
        self.total_display = QLabel("R$ 0,00")
        self.total_display.setObjectName("total_final_value")
        total_layout.addWidget(self.total_display, 3, 0, 1, 2, Qt.AlignCenter)
        
        right_layout.addWidget(total_panel)
        
        self.product_image_display = QLabel("Sem Imagem")
        self.product_image_display.setObjectName("product_image_display")
        self.product_image_display.setAlignment(Qt.AlignCenter)
        self.product_image_display.setScaledContents(True)
        right_layout.addWidget(self.product_image_display, 1)
        
        self.btn_toggle_menu = QPushButton("Menu (F12)")
        self.btn_toggle_menu.setObjectName("btn_toggle_menu")
        self.btn_toggle_menu.clicked.connect(self.toggleMenuRequested.emit)
        
        self.btn_abrir_fechar_caixa = QPushButton("Abrir Caixa (F11)")
        self.btn_abrir_fechar_caixa.setObjectName("btn_abrir_fechar_caixa")
        self.btn_abrir_fechar_caixa.clicked.connect(self._toggle_cash_state) 

        self.btn_buscar_produto = QPushButton("Buscar Produto (F3)")
        self.btn_buscar_produto.clicked.connect(self._open_product_search)
        
        self.btn_excluir_item = QPushButton("Excluir Item (F4)")
        self.btn_excluir_item.setObjectName("btn_excluir_item") 
        self.btn_excluir_item.clicked.connect(self.delete_cart_item)
        
        # Botão de Funções (Agrupa F5, F6, F7)
        self.btn_funcoes = QPushButton("Funções (F5)")
        self.btn_funcoes.setObjectName("btn_funcoes")
        self.btn_funcoes.clicked.connect(self._show_funcoes_dialog)
        
        self.btn_cancelar = QPushButton("Cancelar Operação (F8)")
        self.btn_cancelar.setObjectName("btn_cancelar")
        self.btn_cancelar.clicked.connect(self.clear_sale)
        
        self.btn_cancelar_finalizada = QPushButton("Cancelar Venda (Ctrl+F8)")
        self.btn_cancelar_finalizada.setObjectName("btn_cancelar_finalizada")
        self.btn_cancelar_finalizada.clicked.connect(self._prompt_cancel_finalized_sale)

        # Botão ÚNICO de Finalizar (Abre o Dialog)
        self.btn_finalizar_venda = QPushButton("Finalizar Venda (F10)")
        self.btn_finalizar_venda.setObjectName("btn_finalizar_venda")
        self.btn_finalizar_venda.clicked.connect(self._prompt_finalize_type)
        
        # --- ORDEM ATUALIZADA ---
        right_layout.addWidget(self.btn_toggle_menu)
        right_layout.addWidget(self.btn_abrir_fechar_caixa)
        right_layout.addWidget(self.btn_buscar_produto)
        right_layout.addWidget(self.btn_excluir_item)
        right_layout.addWidget(self.btn_funcoes) 
        right_layout.addWidget(self.btn_cancelar)
        right_layout.addWidget(self.btn_cancelar_finalizada)
        right_layout.addWidget(self.btn_finalizar_venda) 

        main_layout.addWidget(self.stack, 3)
        main_layout.addLayout(right_layout, 1)

    def _show_funcoes_dialog(self):
        can_move_cash = (
            self.controller.user_field_permissions.get("pode_fazer_sangria", False) == "Total" or
            self.controller.user_field_permissions.get("pode_fazer_suprimento", False) == "Total"
        )
        
        permissions = {
            "pode_desconto_item": self.controller.user_field_permissions.get("pode_desconto_item", False) == "Total",
            "pode_desconto_venda": self.controller.user_field_permissions.get("pode_desconto_venda", False) == "Total",
            "pode_mov_caixa": can_move_cash
        }
        
        dialog = SalesFunctionsDialog(self, permissions)
        
        if dialog.exec_() == QDialog.Accepted:
            result = dialog.get_result()
            
            if result == 'DESCONTO_ITEM':
                self.apply_item_discount()
            elif result == 'DESCONTO_VENDA':
                self.apply_general_discount()
            elif result == 'MOV_CAIXA':
                self._prompt_cash_movement()
        
        self.product_search.setFocus()

    def _toggle_cash_state(self):
        if self.controller.current_caixa_id:
            self._prompt_close_cash()
        else:
            self._prompt_open_cash()
            
    def _prompt_open_cash(self):
        dialog = OpenCashDialog(self.nome_terminal, self)
        if dialog.exec_() == QDialog.Accepted:
            valor_inicial = dialog.get_value()
            conn = get_connection()
            try:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO caixa_sessoes (user_id, valor_inicial, status, terminal_id) 
                    VALUES (?, ?, 'ABERTO', ?)
                """, (self.user_id, valor_inicial, self.controller.terminal_id))
                
                new_caixa_id = cur.lastrowid
                conn.commit()
                self.set_caixa_aberto(new_caixa_id)
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Não foi possível abrir o caixa: {e}")
            finally:
                conn.close()

    def _prompt_close_cash(self):
        if not self.controller.current_caixa_id:
            return

        current_user_has_perm = self.controller.user_field_permissions.get("pode_fechar_caixa", False) == "Total"
        
        if not current_user_has_perm:
            QMessageBox.warning(self, "Acesso Negado", "Você não tem permissão para fechar o caixa. Solicitando supervisor...")
            auth_dialog = AuthorizationDialog(self, "pode_fechar_caixa")
            if auth_dialog.exec_() != QDialog.Accepted:
                return 

        reply = QMessageBox.question(self, "Fechar Caixa",
                                     "Deseja realmente encerrar o terminal de caixa?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.No:
            return

        self._set_main_shortcuts_enabled(False)
        
        conferencia_data = None
        autorizador_id = None
        
        try:
            conf_dialog = CloseCashDialog(self.controller.current_caixa_id, self.nome_terminal, self)
            
            if conf_dialog.exec_() != QDialog.Accepted:
                self._set_main_shortcuts_enabled(True)
                return 

            conferencia_data = conf_dialog.get_data()
            diferenca = conferencia_data["diferenca"]
            
            if abs(diferenca) > 0.01:
                user_has_divergence_perm = self.controller.user_field_permissions.get("pode_fechar_com_divergencia", False) == "Total"
                
                if not user_has_divergence_perm:
                    auth_diverg_dialog = AuthorizationDialog(self, "pode_fechar_com_divergencia")
                    QMessageBox.warning(self, "Divergência Encontrada",
                                        f"Diferença de {diferenca:.2f} encontrada.\n\n"
                                        "É necessária autorização de um supervisor para continuar.")
                    
                    if auth_diverg_dialog.exec_() != QDialog.Accepted:
                        self._set_main_shortcuts_enabled(True)
                        return
                        
                    autorizador_id = auth_diverg_dialog.get_authorized_id()
                else:
                    reply_div = QMessageBox.question(self, "Divergência Encontrada",
                                f"Diferença de {diferenca:.2f} encontrada. Deseja continuar mesmo assim?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                    if reply_div == QMessageBox.No:
                        self._set_main_shortcuts_enabled(True)
                        return
                    autorizador_id = self.user_id
            
            report_dialog = ZReportView(
                caixa_id=self.controller.current_caixa_id,
                terminal_id=self.controller.terminal_id,
                conferencia_data=conferencia_data,
                parent=self
            )
            report_dialog.exec_()
            
            result = self.controller.finalize_cash_closing(conferencia_data, autorizador_id)
            
            if result['success']:
                 self._post_closing_actions(conferencia_data)
            else:
                 QMessageBox.critical(self, "Erro de Fechamento", result['error'])

        except Exception as e:
            QMessageBox.critical(self, "Erro Crítico", f"Erro ao processar fechamento: {e}")
        finally:
            if self.controller.current_caixa_id:
                self._set_main_shortcuts_enabled(True)

    def _post_closing_actions(self, data):
        QMessageBox.information(self, "Caixa Fechado", 
            f"Caixa encerrado com sucesso.\n\n"
            f"Valor Calculado: R$ {data['calculado']:.2f}\n"
            f"Valor Informado: R$ {data['informado']:.2f}\n"
            f"Diferença: R$ {data['diferenca']:.2f}")
            
        self.clear_sale(force_clear=True)
        self.set_caixa_fechado()
                
    def start_new_sale_flow(self):
        self.sale_started = False
        self.current_cliente_id = 1
        self.current_cliente_nome = "CONSUMIDOR FINAL"
        self.prevenda_origem_id_para_conversao = None
        self.update_cliente_display()
        self.product_search.setFocus()

    def identify_customer(self):
        dialog = CustomInputDialog(self, "Identificar Cliente", "Informe o CPF/CNPJ do cliente:")
        if dialog.exec_() == QDialog.Accepted:
            cpf_cnpj = dialog.get_text()
            if cpf_cnpj:
                conn = get_connection()
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT id, nome_razao FROM clientes WHERE cpf = ? OR cnpj = ?", (cpf_cnpj, cpf_cnpj))
                    cliente = cur.fetchone()
                    if cliente:
                        self.current_cliente_id = cliente['id']
                        self.current_cliente_nome = cliente['nome_razao']
                        self.update_cliente_display()
                    else:
                        self._prompt_new_customer(cpf_cnpj)
                except Exception as e:
                    QMessageBox.critical(self, "Erro", f"Erro ao buscar cliente: {e}")
                finally:
                    conn.close()

    def _prompt_new_customer(self, cpf_cnpj):
        reply = QMessageBox.question(self, "Cliente Não Encontrado",
                                     f"O CPF/CNPJ '{cpf_cnpj}' não foi encontrado.\nDeseja cadastrar um novo cliente?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        
        if reply == QMessageBox.Yes:
            customer_dialog = CustomerQuickDialog(user_id=self.user_id, start_cpf=cpf_cnpj, parent=self)
            
            if customer_dialog.exec_() == QDialog.Accepted:
                new_id, new_name = customer_dialog.get_new_customer_data()
                if new_id:
                    self.current_cliente_id = new_id
                    self.current_cliente_nome = new_name
                    self.update_cliente_display()
        
    def update_cliente_display(self):
        self.customer_display.setText(f"Cliente: {self.current_cliente_nome}")
        self.product_search.setFocus()

    def _load_product_image_by_id(self, produto_id):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT caminho_imagem FROM produtos WHERE id = ?", (produto_id,))
            data = cur.fetchone()
            
            if data and data['caminho_imagem']:
                self._load_product_image(data['caminho_imagem'])
            else:
                self._load_product_image(None)
                
        except Exception as e:
            print(f"Erro ao buscar imagem do produto: {e}")
            self._load_product_image(None)
        finally:
            if conn:
                conn.close()

    def _load_product_image(self, image_path):
        if image_path and os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            self.product_image_display.setPixmap(
                pixmap.scaled(self.product_image_display.size(), 
                              Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            self.product_image_display.setText("Sem Imagem")
            self.product_image_display.setAlignment(Qt.AlignCenter)

    def _on_cart_item_selected(self):
        row = self.cart_table.currentRow()
        if row < 0 or row >= len(self.cart_items):
            return
        item_data = self.cart_items[row]
        self._load_product_image_by_id(item_data['produto_id'])

    def search_product(self):
        if not self.sale_started:
            if self.current_cliente_id == 1:
                reply = QMessageBox.question(self, "Identificar Cliente",
                                             "Deseja identificar o cliente (CPF/CNPJ) para esta venda?",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self.identify_customer()
                    return
            self.sale_started = True
        
        term = self.product_search.text().strip()
        if not term: return
        
        if self.controller.tabela_id_ativa is None:
            QMessageBox.critical(self, "Erro", "Tabela de Preço Ativa não encontrada.")
            return

        if term.startswith("#"):
            if not self.controller.habilita_nao_fiscal:
                QMessageBox.warning(self, "Ação Indisponível", "Este terminal não está configurado para carregar vendas não-fiscais.")
                self.product_search.clear()
                return
            if not self.controller.user_field_permissions.get("pode_carregar_prevenda", False) == "Total":
                 QMessageBox.warning(self, "Acesso Negado", "Você não tem permissão para carregar vendas não-fiscais.")
                 self.product_search.clear()
                 return
            try:
                numero_venda = int(term[1:])
                self._load_nao_fiscal(numero_venda)
            except ValueError:
                self.product_name_display.setText("❌ ID de Venda inválido")
                self.product_search.selectAll()
            return
        
        quantidade = 1.0
        codigo = term
        
        if "*" in term:
            parts = term.split("*")
            if len(parts) == 2 and parts[0].replace(',', '.').replace('.', '', 1).isdigit():
                try:
                    quantidade = float(parts[0].replace(',', '.'))
                    codigo = parts[1]
                except ValueError:
                    self.product_name_display.setText("❌ Multiplicador inválido")
                    self.product_search.selectAll()
                    return
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            query = """
                SELECT 
                    p.id as produto_id, 
                    p.ean, 
                    p.codigo_interno, 
                    p.nome as descricao,
                    p.unidade,
                    ptp.preco_vendadecimal as preco_venda
                FROM produtos p
                LEFT JOIN produto_tabela_preco ptp ON p.id = ptp.id_produto
                LEFT JOIN produto_codigos_alternativos pca ON p.id = pca.id_produto
                WHERE 
                    (
                        p.ean = ? OR p.codigo_interno = ?
                        OR pca.codigo = ?
                    )
                    AND p.active = 1
                    AND ptp.id_tabela = ?
                GROUP BY p.id 
                LIMIT 1
            """
            
            cur.execute(query, (codigo, codigo, codigo, self.controller.tabela_id_ativa))
            produto_data = cur.fetchone()
            
            if not produto_data:
                self.product_name_display.setText("❌ PRODUTO NÃO ENCONTRADO")
                self.product_search.selectAll()
                return
            
            if produto_data['preco_venda'] is None or produto_data['preco_venda'] < 0.01:
                self.product_name_display.setText(f"❌ {produto_data['descricao']} (Sem Preço)")
                self.product_search.selectAll()
                return
                
            self.add_item_to_cart(dict(produto_data), quantidade)
            self._load_product_image_by_id(produto_data['produto_id']) 
            
        except Exception as e:
            QMessageBox.critical(self, "Erro de Banco de Dados", f"Erro ao buscar produto: {e}")
        finally:
            conn.close()
            self.product_search.clear()

    def _load_nao_fiscal(self, numero_venda):
        self.clear_sale(force_clear=True) 
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM vendas 
                WHERE numero_venda_terminal = ? 
                AND tipo_documento = 'NAO_FISCAL'
                AND terminal_id = ?
            """, (numero_venda, self.controller.terminal_id))
            
            venda = cur.fetchone()
            
            if not venda:
                self.product_name_display.setText(f"❌ Venda Não-Fiscal #{numero_venda} não encontrada.")
                self.product_search.selectAll()
                return

            self.current_cliente_id = venda['cliente_id']
            self.desconto_geral = venda['desconto_geral']
            self.prevenda_origem_id_para_conversao = venda['id']
            
            cur.execute("SELECT nome_razao FROM clientes WHERE id = ?", (self.current_cliente_id,))
            cliente = cur.fetchone()
            self.current_cliente_nome = cliente['nome_razao'] if cliente else "CONSUMIDOR FINAL"
            self.update_cliente_display()
            
            cur.execute("SELECT * FROM vendas_itens WHERE venda_id = ?", (venda['id'],))
            itens = cur.fetchall()
            
            for item in itens:
                item_data = {
                    "produto_id": item['produto_id'],
                    "codigo_barras": item['codigo_barras'],
                    "descricao": item['descricao'],
                    "quantidade": item['quantidade'],
                    "preco_unitario": item['preco_unitario'],
                    "desconto_item": item['desconto_item']
                }
                self.cart_items.append(item_data)
                
            self._update_cart_table()
            self._update_totals()
            self.cart_stack.setCurrentIndex(1)
            self.product_name_display.setText(f"Venda {numero_venda} carregada. Pressione F10 para emitir.")
            self.product_search.clear()

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar Venda Não-Fiscal: {e}")
        finally:
            conn.close()

    def _open_product_search(self):
        if not self.sale_started:
            self.sale_started = True

        dialog = ProductSearchDialog(self.controller.tabela_id_ativa, self)
        
        if dialog.exec_() == QDialog.Accepted:
            produto_id, quantidade = dialog.get_selection()
            
            if produto_id:
                conn = get_connection()
                try:
                    cur = conn.cursor()
                    query = """
                        SELECT 
                            p.id as produto_id, p.ean, p.codigo_interno, p.nome as descricao, p.unidade,
                            ptp.preco_vendadecimal as preco_venda
                        FROM produtos p
                        LEFT JOIN produto_tabela_preco ptp ON p.id = ptp.id_produto
                        WHERE p.id = ? AND ptp.id_tabela = ?
                    """
                    cur.execute(query, (produto_id, self.controller.tabela_id_ativa))
                    produto_data = cur.fetchone()
                    
                    if produto_data and produto_data['preco_venda'] is not None and produto_data['preco_venda'] >= 0.01:
                        self.add_item_to_cart(dict(produto_data), quantidade)
                        self._load_product_image_by_id(produto_data['produto_id'])
                    else:
                        QMessageBox.warning(self, "Erro", "Produto não encontrado ou sem preço na lista padrão.")
                        
                except Exception as e:
                    QMessageBox.critical(self, "Erro", f"Erro ao buscar produto por ID: {e}")
                finally:
                    conn.close()
        
        self.product_search.setFocus()
   
    def add_item_to_cart(self, produto_data, quantidade):
        item_data = {
            "produto_id": produto_data['produto_id'],
            "codigo_barras": produto_data['ean'] or produto_data['codigo_interno'],
            "descricao": produto_data['descricao'],
            "quantidade": quantidade,
            "preco_unitario": produto_data['preco_venda'],
            "desconto_item": 0.0
        }
        self.cart_items.append(item_data)
        self.product_name_display.setText(f"{quantidade}x {produto_data['descricao']}")
        self._update_cart_table()
        self._update_totals()
        self.cart_stack.setCurrentIndex(1) 

    def _update_cart_table(self):
        self.cart_table.setRowCount(0)
        for item in self.cart_items:
            row = self.cart_table.rowCount()
            self.cart_table.insertRow(row)
            total_item = (item['preco_unitario'] * item['quantidade']) - item['desconto_item']
            qtd_str = f"{item['quantidade']:.2f}"
            preco_str = f"R$ {item['preco_unitario']:.2f}"
            desc_str = f"R$ {item['desconto_item']:.2f}"
            total_str = f"R$ {total_item:.2f}"
            self.cart_table.setItem(row, 0, QTableWidgetItem(item['codigo_barras']))
            self.cart_table.setItem(row, 1, QTableWidgetItem(item['descricao']))
            self.cart_table.setItem(row, 2, QTableWidgetItem(qtd_str))
            self.cart_table.setItem(row, 3, QTableWidgetItem(preco_str))
            self.cart_table.setItem(row, 4, QTableWidgetItem(desc_str))
            self.cart_table.setItem(row, 5, QTableWidgetItem(total_str))
            
        self.cart_table.scrollToBottom()
        if self.cart_table.rowCount() > 0:
            self.cart_table.selectRow(self.cart_table.rowCount() - 1)

    def _update_totals(self):
        self.subtotal = 0.0
        self.desconto_itens = 0.0
        for item in self.cart_items:
            self.subtotal += item['preco_unitario'] * item['quantidade']
            self.desconto_itens += item['desconto_item']
        total_descontos = self.desconto_itens + self.desconto_geral
        self.total_final = (self.subtotal - total_descontos)
        self.lbl_total_bruto.setText(f"R$ {self.subtotal:.2f}")
        self.lbl_total_descontos.setText(f"- R$ {total_descontos:.2f}")
        self.total_display.setText(f"R$ {self.total_final:.2f}")

    def _get_discount_input(self, title, label):
        tipo_options = ["Valor (R$)", "Percentual (%)"]
        
        dialog_tipo = CustomComboDialog(self, title, "Tipo de Desconto:", tipo_options)
        if dialog_tipo.exec_() == QDialog.Accepted:
            tipo = dialog_tipo.get_selected_item()
            
            dialog_valor = CustomInputDialog(self, title, f"{label} em {tipo}:", "0,00")
            if dialog_valor.exec_() == QDialog.Accepted:
                valor_str = dialog_valor.get_text()
                try:
                    valor = abs(float(valor_str.replace(',', '.')))
                    return tipo, valor
                except ValueError:
                    QMessageBox.warning(self, "Erro", "Valor inválido.")
        return None, None

    def apply_item_discount(self):
        if not self.controller.user_field_permissions.get("pode_desconto_item", False) == "Total":
            QMessageBox.warning(self, "Acesso Negado", "Você não tem permissão para dar desconto em itens. Solicitando supervisor...")
            auth_dialog = AuthorizationDialog(self, "pode_desconto_item")
            if auth_dialog.exec_() != QDialog.Accepted:
                return
        
        row = self.cart_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Erro", "Selecione um item no carrinho primeiro.")
            return
            
        item = self.cart_items[row]
        tipo, valor = self._get_discount_input("Desconto no Item", f"Desconto para '{item['descricao']}'")
        
        if tipo and valor is not None:
            desconto_calculado = 0.0
            percentual_calculado = 0.0
            item_subtotal = item['preco_unitario'] * item['quantidade']
            
            if item_subtotal == 0:
                QMessageBox.warning(self, "Erro", "Não é possível aplicar desconto em item com valor zero.")
                return

            if tipo == "Valor (R$)":
                desconto_calculado = valor
                percentual_calculado = (desconto_calculado / item_subtotal) * 100
            elif tipo == "Percentual (%)":
                desconto_calculado = item_subtotal * (valor / 100)
                percentual_calculado = valor
                
            if percentual_calculado > self.controller.limite_desconto:
                QMessageBox.warning(self, "Limite Excedido", 
                                    f"O desconto informado ({percentual_calculado:.2f}%) excede o seu limite ({self.controller.limite_desconto}%).\n"
                                    "Solicitando supervisor...")
                
                auth_dialog = AuthorizationDialog(self, "pode_desconto_item")
                if auth_dialog.exec_() != QDialog.Accepted:
                    return 

            if desconto_calculado > item_subtotal:
                QMessageBox.warning(self, "Erro", "O desconto não pode ser maior que o total do item.")
                return
                
            item['desconto_item'] = desconto_calculado
            self._update_cart_table()
            self._update_totals()

    def apply_general_discount(self):
        if not self.controller.user_field_permissions.get("pode_desconto_venda", False) == "Total":
            QMessageBox.warning(self, "Acesso Negado", "Você não tem permissão para dar desconto na venda. Solicitando supervisor...")
            auth_dialog = AuthorizationDialog(self, "pode_desconto_venda")
            if auth_dialog.exec_() != QDialog.Accepted:
                return
        
        tipo, valor = self._get_discount_input("Desconto na Venda", "Valor do Desconto")
        
        if tipo and valor is not None:
            desconto_calculado = 0.0
            percentual_calculado = 0.0
            
            if self.subtotal == 0:
                QMessageBox.warning(self, "Erro", "Não é possível aplicar desconto em uma venda com valor zero.")
                return

            if tipo == "Percentual (%)":
                desconto_calculado = self.subtotal * (valor / 100)
                percentual_calculado = valor
            else: # Valor R$
                desconto_calculado = valor
                percentual_calculado = (desconto_calculado / self.subtotal) * 100
                
            if percentual_calculado > self.controller.limite_desconto:
                QMessageBox.warning(self, "Limite Excedido", 
                                    f"O desconto informado ({percentual_calculado:.2f}%) excede o seu limite ({self.controller.limite_desconto}%).\n"
                                    "Solicitando supervisor...")
                
                auth_dialog = AuthorizationDialog(self, "pode_desconto_venda")
                if auth_dialog.exec_() != QDialog.Accepted:
                    return
                
            if (desconto_calculado + self.desconto_itens) > self.subtotal:
                QMessageBox.warning(self, "Erro", "O desconto total não pode ser maior que o subtotal da venda.")
                self.desconto_geral = 0.0
            else:
                self.desconto_geral = desconto_calculado
            self._update_totals()

    def _prompt_cash_movement(self):
        if not self.controller.current_caixa_id:
            QMessageBox.warning(self, "Caixa Fechado", "Você deve abrir o caixa para fazer uma movimentação.")
            return

        dialog = CashMovementDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
            
        data = dialog.get_data()
        if not data:
            return 

        perm_key = "pode_fazer_sangria" if data['tipo'] == 'SANGRIA' else "pode_fazer_suprimento"
        autorizador_id = None
        
        if not self.controller.user_field_permissions.get(perm_key, False) == "Total":
            QMessageBox.warning(self, "Acesso Negado", f"Você não tem permissão para realizar {data['tipo']}. Solicitando supervisor...")
            auth_dialog = AuthorizationDialog(self, perm_key)
            if auth_dialog.exec_() != QDialog.Accepted:
                return 
            autorizador_id = auth_dialog.get_authorized_id()

        result = self.controller.add_cash_movement(
            tipo=data['tipo'],
            valor=data['valor'],
            motivo=data['motivo'],
            autorizador_id=autorizador_id
        )
        
        if result['success']:
            QMessageBox.information(self, "Sucesso", f"{data['tipo']} de R$ {data['valor']:.2f} registrada com sucesso.")
        else:
            QMessageBox.critical(self, "Erro no DB", result['error'])

    def delete_cart_item(self):
        if not self.controller.user_field_permissions.get("pode_excluir_item", False) == "Total":
            QMessageBox.warning(self, "Acesso Negado", "Você não tem permissão para excluir itens da venda.")
            return
        row = self.cart_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Erro", "Selecione um item para excluir.")
            return
        item = self.cart_items[row]
        reply = QMessageBox.question(self, "Excluir Item",
                                     f"Tem certeza que deseja excluir o item '{item['descricao']}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            del self.cart_items[row]
            if self.desconto_geral > 0:
                QMessageBox.information(self, "Aviso", "O desconto geral da venda foi removido, pois um item foi excluído.")
                self.desconto_geral = 0.0
            self._update_cart_table()
            self._update_totals()
            if not self.cart_items:
                self.cart_stack.setCurrentIndex(0)
                self.product_image_display.setText("Sem Imagem")
            else:
                if row > 0:
                    self.cart_table.selectRow(row - 1)
                elif self.cart_table.rowCount() > 0:
                    self.cart_table.selectRow(0)

    # --- Ação de Cancelar Venda Finalizada ---
    def _prompt_cancel_finalized_sale(self):
        """Abre o diálogo para buscar e cancelar uma venda já finalizada."""
        if self.controller.current_caixa_id is None:
            QMessageBox.warning(self, "Erro", "O caixa deve estar aberto para cancelar uma venda do dia.")
            return

        if self.controller.user_field_permissions.get("btn_cancelar", False) != "Total":
            QMessageBox.warning(self, "Acesso Negado", "Você não tem permissão para cancelar vendas finalizadas. Solicitando supervisor...")
            auth_dialog = AuthorizationDialog(self, "btn_cancelar")
            if auth_dialog.exec_() != QDialog.Accepted:
                return

        dialog = CancelSaleDialog(
            current_caixa_id=self.controller.current_caixa_id,
            terminal_id=self.controller.terminal_id,
            pos_controller=self.controller,
            parent=self
        )

        if dialog.exec_() == QDialog.Accepted:
            # --- IMPRESSÃO DO COMPROVANTE DE CANCELAMENTO ---
            venda_data = dialog.venda_encontrada
            motivo = dialog.reason_combo.currentText()
            
            receipt_result = self.controller.get_receipt_data_for_venda(venda_data['id'])
            
            if receipt_result['success']:
                final_data = receipt_result['data']
                # Garante que a data_venda venha corretamente
                if 'data_venda' not in final_data:
                     final_data['data_venda'] = venda_data.get('data_venda', 'Data N/A')

                final_data['user_id'] = self.user_id 
                
                generate_and_print_cancellation_receipt(final_data, motivo)
                
                QMessageBox.information(self, "Cancelamento", "Venda cancelada e comprovante impresso com sucesso!")
            else:
                 QMessageBox.warning(self, "Aviso", "Venda cancelada, mas houve erro ao buscar dados para impressão.")

    def clear_sale(self, force_clear=False):
        if not self.cart_items and not force_clear:
            self.start_new_sale_flow()
            return
        reply = QMessageBox.Yes
        if not force_clear:
             reply = QMessageBox.question(self, "Cancelar Venda",
                                         "Tem certeza que deseja limpar todos os itens do carrinho (Cancelar a venda atual)?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.cart_items = []
            self.desconto_geral = 0.0
            self._update_cart_table()
            self._update_totals()
            self.product_name_display.setText("Aguardando produto...")
            self.product_image_display.setText("Sem Imagem")
            self.cart_stack.setCurrentIndex(0)
            if not force_clear: 
                self.start_new_sale_flow()

    def open_payment_dialog(self, tipo_documento):
        if not self.cart_items:
            QMessageBox.warning(self, "Venda Vazia", "Adicione pelo menos um produto ao carrinho.")
            return
            
        self._update_totals()
        self._set_main_shortcuts_enabled(False)
        
        try:
            dialog = PaymentDialog(
                subtotal=self.subtotal, 
                desconto_total=(self.desconto_itens + self.desconto_geral),
                total_final=self.total_final, 
                parent=self
            )
            
            result = dialog.exec_() 
            
            if result == QDialog.Accepted:
                pagamentos = dialog.get_payments()
                troco = dialog.get_troco()
                self._finalize_sale(pagamentos, troco, tipo_documento)
            else:
                print("Pagamento cancelado.")
                self.product_search.setFocus()
        
        except Exception as e:
            print(f"ERRO CRÍTICO no PaymentDialog: {e}")
            QMessageBox.critical(self, "Erro no Pagamento", 
                                 f"Ocorreu um erro inesperado ao processar o pagamento:\n{e}")
            
        finally:
            self._set_main_shortcuts_enabled(True)

    # --- AQUI É A LÓGICA DO NOVO BOTÃO F10 ---
    def _prompt_finalize_type(self):
        if not self.cart_items:
            QMessageBox.warning(self, "Venda Vazia", "Adicione pelo menos um produto ao carrinho.")
            return

        self._update_totals()
        
        # Se for uma pré-venda que está sendo convertida, prioriza a lógica de conversão fiscal
        if self.prevenda_origem_id_para_conversao:
            if not self.controller.user_field_permissions.get("pode_converter_fiscal", False) == "Total":
                 QMessageBox.warning(self, "Acesso Negado", "Você não tem permissão para converter esta venda em Fiscal.")
                 auth_dialog = AuthorizationDialog(self, "pode_converter_fiscal")
                 if auth_dialog.exec_() != QDialog.Accepted:
                     return
            self._convert_sale_to_fiscal()
            return

        can_finish_fiscal = self.controller.user_field_permissions.get("pode_finalizar_fiscal", False) == "Total"
        can_finish_nao_fiscal = self.controller.user_field_permissions.get("pode_finalizar_nao_fiscal", False) == "Total"
        habilita_nao_fiscal = self.controller.habilita_nao_fiscal and can_finish_nao_fiscal

        # Se só pode um, vai direto
        if not habilita_nao_fiscal and can_finish_fiscal:
            self.open_payment_dialog('FISCAL')
            return
        if not can_finish_fiscal and not habilita_nao_fiscal:
            QMessageBox.warning(self, "Acesso Negado", "Você não tem permissão para finalizar vendas.")
            return

        # Se pode ambos, abre o diálogo de escolha
        dialog = FinalizeSaleDialog(self, habilita_nao_fiscal=habilita_nao_fiscal, is_prevenda=False)
        if dialog.exec_() == QDialog.Accepted:
            tipo_doc = dialog.get_result()
            if tipo_doc == 'FISCAL':
                if can_finish_fiscal: self.open_payment_dialog('FISCAL')
                else: QMessageBox.warning(self, "Acesso Negado", "Você não tem permissão para finalizar Vendas Fiscais.")
            elif tipo_doc == 'NAO_FISCAL':
                self.open_payment_dialog('NAO_FISCAL')
        self.product_search.setFocus()

    # --- MÉTODOS INTERNOS CHAMADOS PELOS ATALHOS DIRETOS ---
    def _finalize_sale_fiscal(self): self._prompt_finalize_type() 
    def _finalize_sale_nao_fiscal(self): self._prompt_finalize_type() 

    def _finalize_sale(self, pagamentos, troco, tipo_documento):
        result = self.controller.finalize_sale(
            cart_items=self.cart_items,
            pagamentos=pagamentos,
            troco=troco,
            subtotal=self.subtotal,
            desconto_itens=self.desconto_itens,
            desconto_geral=self.desconto_geral,
            total_final=self.total_final,
            current_cliente_id=self.current_cliente_id,
            tipo_documento=tipo_documento
        )
        
        if result['success']:
            sale_number = result['sale_number']
            receipt_data = result['receipt_data']
            
            QMessageBox.information(self, "Sucesso", f"Venda Nº {sale_number} finalizada com sucesso!")

            try:
                generate_and_print_receipt(receipt_data)
            except Exception as e_print:
                QMessageBox.warning(self, "Erro de Impressão", 
                    f"A venda foi salva (Nº {sale_number}), mas falhou ao gerar o cupom.\n\n"
                    f"Erro: {e_print}")

            self.clear_sale(force_clear=True)
            self.start_new_sale_flow()
            
        else:
            QMessageBox.critical(self, "Erro de Banco de Dados", f"Não foi possível salvar a venda: {result['error']}")

    def _convert_sale_to_fiscal(self):
        if not self.prevenda_origem_id_para_conversao:
            return

        venda_id = self.prevenda_origem_id_para_conversao
        
        result = self.controller.convert_to_fiscal(venda_id)
        
        if result['success']:
            new_sale_number = result['new_sale_number']
            QMessageBox.information(self, "Sucesso", f"Venda convertida para Fiscal.\nNovo Nº Fiscal: {new_sale_number}")

            try:
                receipt_data_result = self.controller.get_receipt_data_for_venda(venda_id)
                
                if receipt_data_result['success']:
                    receipt_data = receipt_data_result['data']
                    receipt_data['numero_venda_terminal'] = new_sale_number
                    receipt_data['tipo_documento'] = 'FISCAL'
                    
                    generate_and_print_receipt(receipt_data)
                else:
                    QMessageBox.warning(self, "Erro de Impressão", receipt_data_result['error'])
            except Exception as e_print:
                 QMessageBox.warning(self, "Erro de Impressão", 
                    f"A venda foi convertida, mas falhou ao gerar o cupom fiscal.\n\n"
                    f"Erro: {e_print}")

            self.clear_sale(force_clear=True)
            self.start_new_sale_flow()
        else:
            QMessageBox.critical(self, "Erro de Conversão", f"Não foi possível converter a venda: {result['error']}")
            
    def _apply_field_permissions(self):
        if not self.controller.habilita_nao_fiscal:
            pass 
        
        widget_map = {
            "pode_finalizar_fiscal": self.btn_finalizar_venda, # Unificado
            "pode_finalizar_nao_fiscal": self.btn_finalizar_venda, # Unificado
            "btn_cancelar": self.btn_cancelar,
            "pode_desconto_item": self.btn_funcoes, 
            "pode_desconto_venda": self.btn_funcoes,
            "btn_buscar_produto": self.btn_buscar_produto,
            "pode_excluir_item": self.btn_excluir_item,
            "btn_cancelar_finalizada": self.btn_cancelar_finalizada, 
        }
        
        for key, widget in widget_map.items():
            permissao = self.controller.user_field_permissions.get(key, "Negado")
            
            if permissao != "Total":
                widget.setEnabled(False)
        
        can_move_cash = (
            self.controller.user_field_permissions.get("pode_fazer_sangria", False) == "Total" or
            self.controller.user_field_permissions.get("pode_fazer_suprimento", False) == "Total"
        )
        
        # Botão Funções habilita se qualquer função interna for permitida
        has_any_func = can_move_cash or widget_map["pode_desconto_item"].isEnabled() or widget_map["pode_desconto_venda"].isEnabled()
        self.btn_funcoes.setEnabled(has_any_func)
        
        can_open = self.controller.user_field_permissions.get("pode_abrir_caixa", False) == "Total"
        can_close = self.controller.user_field_permissions.get("pode_fechar_caixa", False) == "Total"
        
        if not can_open and not can_close:
             self.btn_abrir_fechar_caixa.setEnabled(False)
        elif (self.controller.current_caixa_id is not None) and not can_close:
             self.btn_abrir_fechar_caixa.setEnabled(False)
        elif (self.controller.current_caixa_id is None) and not can_open:
             self.btn_abrir_fechar_caixa.setEnabled(False)
        else:
             self.btn_abrir_fechar_caixa.setEnabled(True)