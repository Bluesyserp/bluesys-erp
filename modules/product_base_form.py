# modules/product_base_form.py
# -*- coding: utf-8 -*-
import sqlite3
import csv
import os 
import re
import logging # <-- NOVO
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QGridLayout, QFrame, QTableWidget, QHeaderView, 
    QTableWidgetItem, QAbstractItemView, QStackedWidget, QComboBox,
    QCheckBox, QTextEdit, QCompleter, QTabWidget, QDoubleSpinBox,
    QFileDialog, QDialog, QTextBrowser, QScrollArea,
    QDateEdit 
)
from PyQt5.QtCore import Qt, QLocale, QStringListModel, QDate, QSize 
from PyQt5.QtGui import QDoubleValidator, QPixmap 
from database.db import get_connection

class ProductBaseForm(QWidget):
    """
    Formulário de Cadastro Básico de Produtos (Modelo Simples).
    """
    def __init__(self, user_id, **kwargs):
        super().__init__()
        self.user_id = user_id
        self.current_product_id = None
        self.setWindowTitle("Cadastro Básico de Produtos")
        
        # --- NOVO: Logger ---
        self.logger = logging.getLogger(__name__)
        
        self.company_map = {} 
        self.category_map = {} 
        self.fornecedor_map = {} # {Nome: ID}
        self.fornecedor_completer_model = QStringListModel()
        self.tabela_preco_map = {} # {ID: Nome}
        
        self._setup_validators()
        self._setup_styles()
        self._build_ui()
        self._connect_signals()
        
        start_mode = kwargs.get('start_mode', 'consulta') 
        if start_mode == 'new':
            self.show_new_form()
        else:
            self.set_mode(0) 

    def _setup_validators(self):
        locale = QLocale(QLocale.Portuguese, QLocale.Brazil)
        self.weight_validator = QDoubleValidator(0.00, 99999.99, 3)
        self.weight_validator.setLocale(locale)
        self.weight_validator.setNotation(QDoubleValidator.StandardNotation)
        
    def _setup_styles(self):
        self.setStyleSheet("""
            QWidget { background-color: #f8f8fb; font-family: 'Segoe UI'; }
            QLabel { font-weight: bold; color: #444; font-size: 13px; }
            QLabel.required::after { content: " *"; color: #e74c3c; }
            QTableWidget {
                border: 1px solid #c0c0d0;
                selection-background-color: #0078d7;
                font-size: 14px;
            }
            QHeaderView::section {
                background-color: #e8e8e8; padding: 8px;
                border: 1px solid #c0c0d0;
                font-weight: bold; font-size: 14px;
            }
            QFrame#form_panel {
                background-color: #fdfdfd;
                border: 1px solid #c0c0d0;
                border-radius: 8px;
            }
            QLabel#form_title {
                font-size: 16px; font-weight: bold; color: #005fa3;
                padding: 5px; border-bottom: 1px solid #eee;
            }
            QTabWidget::pane { border-top: 1px solid #c0c0d0; background: #fdfdfd; }
            QTabBar::tab { background: #e0e0e0; padding: 8px 20px; }
            QTabBar::tab:selected { background: #fdfdfd; border: 1px solid #c0c0d0; border-bottom: none; }
            
            QLineEdit, QComboBox, QTextEdit, QDoubleSpinBox, QDateEdit {
                border: 1px solid #c0c0d0; border-radius: 5px; 
                padding: 6px; background-color: white; font-size: 13px;
            }
            QLineEdit:readOnly { background-color: #f0f0f0; }
            
            QPushButton {
                background-color: #0078d7; color: white; border-radius: 6px;
                padding: 8px 15px; font-weight: bold;
            }
            QPushButton:hover { background-color: #005fa3; }
            QPushButton#deleteButton { background-color: #e74c3c; }
            QPushButton#deleteButton:hover { background-color: #c0392b; }
            QPushButton#cancelButton { background-color: #95A5A6; }
            QPushButton#cancelButton:hover { background-color: #7F8C8D; }
            QPushButton#btn_browse_img {
                background-color: #7f8c8d;
                padding: 6px 10px;
                font-size: 12px;
            }
            QPushButton#btn_browse_img:hover { background-color: #627071; }
            
            QLabel#image_preview {
                border: 1px solid #c0c0d0;
                background-color: #fdfdfd;
                border-radius: 5px;
                min-height: 150px;
                min-width: 150px;
                max-width: 150px;
                max-height: 150px;
            }
        """)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        
        self.search_panel = QWidget()
        search_layout = QHBoxLayout(self.search_panel)
        search_layout.setContentsMargins(0, 10, 0, 10)
        self.btn_novo = QPushButton("Novo Produto")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Pesquisar por Nome, Marca ou Código Interno...")
        self.btn_pesquisar = QPushButton("Pesquisar")
        
        search_layout.addWidget(self.btn_novo)
        search_layout.addStretch()
        search_layout.addWidget(self.search_input, 1) 
        search_layout.addWidget(self.btn_pesquisar)
        
        self.stack = QStackedWidget()
        
        self.table_widget = QWidget()
        table_layout = QVBoxLayout(self.table_widget)
        table_layout.setContentsMargins(0,0,0,0)
        self.product_table = QTableWidget()
        self.product_table.setColumnCount(6)
        self.product_table.setHorizontalHeaderLabels(["ID", "Cód. Interno", "Nome do Produto", "Unidade", "Marca", "Ativo"])
        self.product_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.product_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.product_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.product_table.setColumnHidden(0, True)
        table_layout.addWidget(self.product_table)
        
        self.form_panel = QFrame()
        self.form_panel.setObjectName("form_panel")
        form_layout = QVBoxLayout(self.form_panel)
        self.form_title = QLabel("Cadastro de Produto", objectName="form_title")
        form_layout.addWidget(self.form_title)
        
        self.tabs = QTabWidget()
        self.tab_geral = QWidget()
        self.tab_codigos = QWidget()
        self.tab_preco_rapido = QWidget()
        
        self.tabs.addTab(self.tab_geral, "1. Dados Gerais")
        self.tabs.addTab(self.tab_codigos, "2. Códigos Alternativos (GTIN/EAN)")
        self.tabs.addTab(self.tab_preco_rapido, "3. Precificação Rápida")
        form_layout.addWidget(self.tabs)
        
        self._build_tab_geral()
        self._build_tab_codigos()
        self._build_tab_preco_rapido()
        
        # Botões do formulário
        form_btn_layout = QHBoxLayout()
        form_btn_layout.addStretch()
        self.btn_salvar = QPushButton("Salvar")
        self.btn_excluir = QPushButton("Excluir")
        self.btn_excluir.setObjectName("deleteButton")
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setObjectName("cancelButton")
        form_btn_layout.addWidget(self.btn_cancelar)
        form_btn_layout.addWidget(self.btn_excluir)
        form_btn_layout.addWidget(self.btn_salvar)
        form_layout.addLayout(form_btn_layout)
        
        self.stack.addWidget(self.table_widget)
        self.stack.addWidget(self.form_panel)
        
        main_layout.addWidget(self.search_panel)
        main_layout.addWidget(self.stack, 1)

    def _build_tab_geral(self):
        """Constrói a aba principal 'Dados Gerais'."""
        form_grid = QGridLayout(self.tab_geral)
        form_grid.setSpacing(10)
        
        # Widgets
        self.empresa_combo = QComboBox()
        self.categoria_combo = QComboBox()
        self.fornecedor_combo = QLineEdit() 
        self.fornecedor_completer = QCompleter(self.fornecedor_completer_model)
        self.fornecedor_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.fornecedor_completer.setFilterMode(Qt.MatchContains)
        self.fornecedor_combo.setCompleter(self.fornecedor_completer)
        
        self.nome_input = QLineEdit()
        self.codigo_interno_input = QLineEdit()
        self.codigo_interno_input.setReadOnly(True) 
        
        self.ean_input = QLineEdit()
        self.unidade_input = QLineEdit("UN")
        self.marca_input = QLineEdit()
        self.modelo_input = QLineEdit()
        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems(["PRODUTO", "SERVICO", "KIT", "COMBO"])
        self.peso_kg_input = QLineEdit("0,000")
        self.peso_kg_input.setValidator(self.weight_validator)
        self.descricao_input = QTextEdit()
        self.descricao_input.setFixedHeight(80)
        self.status_check = QCheckBox("Ativo")
        self.status_check.setChecked(True)
        
        self.validade_input = QDateEdit()
        self.validade_input.setCalendarPopup(True)
        self.validade_input.setSpecialValueText(" ") 
        self.validade_input.setDate(QDate()) 
        self.validade_input.setDisplayFormat("dd/MM/yyyy")
        
        self.imagem_path_input = QLineEdit()
        self.imagem_path_input.setReadOnly(True)
        self.imagem_path_input.setPlaceholderText("Selecione um arquivo de imagem...")
        self.btn_browse_image = QPushButton("Procurar...")
        self.btn_browse_image.setObjectName("btn_browse_img")
        
        self.imagem_preview_label = QLabel("Sem Imagem")
        self.imagem_preview_label.setObjectName("image_preview")
        self.imagem_preview_label.setAlignment(Qt.AlignCenter)
        
        # Layout
        form_grid.addWidget(QLabel("Empresa: *", objectName="required"), 0, 0)
        form_grid.addWidget(self.empresa_combo, 0, 1, 1, 3)
        form_grid.addWidget(QLabel("Nome do Produto: *", objectName="required"), 1, 0)
        form_grid.addWidget(self.nome_input, 1, 1, 1, 3)
        
        form_grid.addWidget(QLabel("Cód. Interno: *", objectName="required"), 2, 0)
        form_grid.addWidget(self.codigo_interno_input, 2, 1)
        form_grid.addWidget(QLabel("EAN (Principal):"), 2, 2)
        form_grid.addWidget(self.ean_input, 2, 3)

        form_grid.addWidget(QLabel("Unidade:"), 3, 0)
        form_grid.addWidget(self.unidade_input, 3, 1)
        form_grid.addWidget(QLabel("Tipo:"), 3, 2)
        form_grid.addWidget(self.tipo_combo, 3, 3)
        
        form_grid.addWidget(QLabel("Marca:"), 4, 0)
        form_grid.addWidget(self.marca_input, 4, 1)
        form_grid.addWidget(QLabel("Modelo:"), 4, 2)
        form_grid.addWidget(self.modelo_input, 4, 3)
        
        form_grid.addWidget(QLabel("Classe (Categoria):"), 5, 0) 
        form_grid.addWidget(self.categoria_combo, 5, 1)
        form_grid.addWidget(QLabel("Fornecedor Principal:"), 5, 2) 
        form_grid.addWidget(self.fornecedor_combo, 5, 3)
        
        form_grid.addWidget(QLabel("Peso (Kg):"), 6, 0)
        form_grid.addWidget(self.peso_kg_input, 6, 1)
        form_grid.addWidget(QLabel("Data de Validade:"), 6, 2)
        form_grid.addWidget(self.validade_input, 6, 3)
        
        form_grid.addWidget(self.status_check, 7, 3, Qt.AlignRight)
        
        form_grid.addWidget(QLabel("Descrição Curta/Longa:"), 8, 0, Qt.AlignTop)
        form_grid.addWidget(self.descricao_input, 8, 1, 1, 3)
        
        # Layout da Imagem (Corrigido)
        img_path_layout = QHBoxLayout()
        img_path_layout.setContentsMargins(0,0,0,0)
        img_path_layout.addWidget(self.imagem_path_input, 1)
        img_path_layout.addWidget(self.btn_browse_image)
        
        form_grid.addWidget(QLabel("Anexo de Imagem:"), 9, 0, Qt.AlignTop)
        form_grid.addLayout(img_path_layout, 9, 1, 1, 2) 
        form_grid.addWidget(self.imagem_preview_label, 9, 3, 1, 1, Qt.AlignCenter) 
        
        form_grid.setColumnStretch(1, 1)
        form_grid.setColumnStretch(3, 1)
        form_grid.setRowStretch(10, 1) 

    def _build_tab_codigos(self):
        # (Inalterado)
        layout = QVBoxLayout(self.tab_codigos)
        layout.setContentsMargins(10, 15, 10, 10)
        
        layout.addWidget(QLabel("Adicione códigos alternativos (GTIN-13, GTIN-14, Cód. Fornecedor, etc.)"))
        layout.addWidget(QLabel("O PDV poderá buscar o produto por qualquer um destes códigos."))
        
        self.codigos_table = QTableWidget()
        self.codigos_table.setColumnCount(3)
        self.codigos_table.setHorizontalHeaderLabels(["ID Cód.", "Tipo de Código", "Código"])
        self.codigos_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.codigos_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.codigos_table.setColumnHidden(0, True)
        layout.addWidget(self.codigos_table, 1)
        
        add_layout = QHBoxLayout()
        self.tipo_codigo_combo = QComboBox()
        self.tipo_codigo_combo.addItems(["GTIN-13", "GTIN-14", "Cód. Fornecedor", "Cód. Antigo"])
        self.novo_codigo_input = QLineEdit()
        self.novo_codigo_input.setPlaceholderText("Insira o código...")
        self.btn_add_codigo = QPushButton("Adicionar Código")
        
        add_layout.addWidget(QLabel("Tipo:"))
        add_layout.addWidget(self.tipo_codigo_combo)
        add_layout.addWidget(QLabel("Código:"))
        add_layout.addWidget(self.novo_codigo_input, 1)
        add_layout.addWidget(self.btn_add_codigo)
        layout.addLayout(add_layout)
        
        self.btn_remove_codigo = QPushButton("Remover Código Selecionado")
        self.btn_remove_codigo.setObjectName("deleteButton")
        layout.addWidget(self.btn_remove_codigo, 0, Qt.AlignRight)

    def _build_tab_preco_rapido(self):
        # (Inalterado)
        layout = QVBoxLayout(self.tab_preco_rapido)
        layout.setContentsMargins(10, 15, 10, 10)
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Aplicar preço na Tabela:"))
        self.preco_tabela_combo = QComboBox()
        header_layout.addWidget(self.preco_tabela_combo, 1)
        layout.addLayout(header_layout)
        
        grid = QGridLayout()
        grid.setSpacing(10)
        
        locale = QLocale(QLocale.Portuguese, QLocale.Brazil)
        self.preco_custo_spin = QDoubleSpinBox()
        self.preco_custo_spin.setRange(0.0, 999999.99)
        self.preco_custo_spin.setLocale(locale)
        self.preco_venda_spin = QDoubleSpinBox()
        self.preco_venda_spin.setRange(0.0, 999999.99)
        self.preco_venda_spin.setLocale(locale)
        self.margem_label = QLabel("Margem: 0.00 %")
        
        grid.addWidget(QLabel("Preço de Custo (R$):"), 0, 0)
        grid.addWidget(self.preco_custo_spin, 0, 1)
        grid.addWidget(QLabel("Preço de Venda (R$):"), 1, 0)
        grid.addWidget(self.preco_venda_spin, 1, 1)
        grid.addWidget(self.margem_label, 2, 1)
        
        layout.addLayout(grid)
        layout.addStretch()
        
        self.btn_salvar_preco_rapido = QPushButton("Salvar Preço Rápido")
        self.btn_salvar_preco_rapido.setStyleSheet("background-color: #2ECC71;")
        layout.addWidget(self.btn_salvar_preco_rapido, 0, Qt.AlignRight)

    def _connect_signals(self):
        self.btn_novo.clicked.connect(self.show_new_form)
        self.btn_salvar.clicked.connect(self.save_product)
        self.btn_excluir.clicked.connect(self.delete_product)
        self.btn_cancelar.clicked.connect(self.cancel_action)
        self.btn_pesquisar.clicked.connect(self.load_products)
        self.search_input.returnPressed.connect(self.load_products)
        self.product_table.itemDoubleClicked.connect(self._load_product_for_edit)
        
        self.btn_add_codigo.clicked.connect(self._add_codigo_alternativo)
        self.btn_remove_codigo.clicked.connect(self._remove_codigo_alternativo)
        
        self.preco_custo_spin.valueChanged.connect(self._update_margem_preco_rapido)
        self.preco_venda_spin.valueChanged.connect(self._update_margem_preco_rapido)
        self.btn_salvar_preco_rapido.clicked.connect(self._save_preco_rapido)
        
        self.btn_browse_image.clicked.connect(self._browse_image)

    def _load_comboboxes(self):
        # (Inalterado)
        self.empresa_combo.clear()
        self.categoria_combo.clear()
        self.fornecedor_combo.clear()
        self.preco_tabela_combo.clear()
        
        self.company_map.clear()
        self.category_map.clear()
        self.fornecedor_map.clear()
        self.tabela_preco_map.clear()
        
        fornecedor_list = []
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            
            cur.execute("SELECT id, razao_social FROM empresas WHERE status = 1 ORDER BY razao_social")
            empresas = cur.fetchall()
            self.empresa_combo.addItem("Selecione uma empresa...", None)
            for empresa in empresas:
                self.empresa_combo.addItem(empresa['razao_social'], empresa['id'])
                self.company_map[empresa['id']] = empresa['razao_social']
            
            cur.execute("SELECT id, name FROM categorias WHERE active = 1 ORDER BY name")
            categorias = cur.fetchall()
            self.categoria_combo.addItem("Sem Classe", None) # Data None
            for cat in categorias:
                self.categoria_combo.addItem(cat['name'], cat['id'])
                self.category_map[cat['id']] = cat['name']
                
            cur.execute("SELECT id, nome FROM fornecedores ORDER BY nome")
            fornecedores = cur.fetchall()
            for forn in fornecedores:
                fornecedor_list.append(forn['nome'])
                self.fornecedor_map[forn['nome']] = forn['id']
            self.fornecedor_completer_model.setStringList(fornecedor_list)
            
            cur.execute("SELECT id, nome_tabela, identificador_loja FROM tabelas_preco WHERE active = 1 ORDER BY nome_tabela")
            tabelas = cur.fetchall()
            self.preco_tabela_combo.addItem("Selecione uma Tabela...", None)
            for tab in tabelas:
                self.preco_tabela_combo.addItem(f"{tab['nome_tabela']} ({tab['identificador_loja']})", tab['id'])
                self.tabela_preco_map[tab['id']] = tab['nome_tabela']
            
            if self.empresa_combo.findData(1) >= 0:
                self.empresa_combo.setCurrentIndex(self.empresa_combo.findData(1))
            if self.preco_tabela_combo.findData(1) >= 0:
                self.preco_tabela_combo.setCurrentIndex(self.preco_tabela_combo.findData(1))
                    
        except Exception as e:
            self.logger.error(f"Erro ao carregar dados de comboboxes: {e}")
            QMessageBox.critical(self, "Erro", f"Erro ao carregar dados: {e}")
        finally:
            conn.close()
            
    def set_mode(self, mode):
        # (Inalterado)
        if mode == 0:
            self.stack.setCurrentIndex(0)
            self.search_panel.setVisible(True)
            self.load_products() 
        else:
            self._load_comboboxes()
            self.stack.setCurrentIndex(1)
            self.search_panel.setVisible(False)
            self.tabs.setTabEnabled(1, False)
            self.tabs.setTabEnabled(2, False)

    def show_new_form(self):
        self.clear_form()
        self.set_mode(1) 
        
        self._generate_sku() 
        
        self.nome_input.setFocus()
        self.form_title.setText("Novo Produto")

    def cancel_action(self):
        # (Inalterado)
        self.clear_form()
        self.set_mode(0) 

    def clear_form(self):
        # (Atualizado com os novos campos e correções)
        self.current_product_id = None
        self.empresa_combo.setCurrentIndex(0)
        self.categoria_combo.setCurrentIndex(0)
        self.fornecedor_combo.clear()
        
        self.nome_input.clear()
        self.codigo_interno_input.clear()
        self.codigo_interno_input.setReadOnly(True) 
        
        self.ean_input.clear()
        self.unidade_input.setText("UN")
        self.marca_input.clear()
        self.modelo_input.clear()
        self.tipo_combo.setCurrentIndex(0)
        self.peso_kg_input.setText("0,000")
        self.descricao_input.clear()
        self.status_check.setChecked(True)
        
        self.validade_input.setDate(QDate()) 
        self.imagem_path_input.clear()
        self._load_image_preview(None)
        
        self.codigos_table.setRowCount(0)
        self.preco_tabela_combo.setCurrentIndex(0)
        self.preco_custo_spin.setValue(0.0)
        self.preco_venda_spin.setValue(0.0)
        
        self.tabs.setTabEnabled(1, False)
        self.tabs.setTabEnabled(2, False)
        self.tabs.setCurrentIndex(0)
        
        self.btn_excluir.setEnabled(False)
        self.form_title.setText("Cadastro de Produto Básico")

    def load_products(self):
        # (Inalterado)
        self.product_table.setRowCount(0)
        search_term = self.search_input.text().strip()
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            query = """
                SELECT p.id, p.nome, p.codigo_interno, p.unidade, p.marca, p.active
                FROM produtos p
            """
            params = []
            
            if search_term:
                query += " WHERE (p.nome LIKE ? OR p.marca LIKE ? OR p.codigo_interno LIKE ?)"
                params.extend([f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"])
            
            query += " ORDER BY p.nome"
            cur.execute(query, tuple(params))
            
            rows = cur.fetchall()
            for row in rows:
                idx = self.product_table.rowCount()
                self.product_table.insertRow(idx)
                self.product_table.setItem(idx, 0, QTableWidgetItem(str(row['id'])))
                self.product_table.setItem(idx, 1, QTableWidgetItem(row['codigo_interno'] or "-"))
                self.product_table.setItem(idx, 2, QTableWidgetItem(row['nome']))
                self.product_table.setItem(idx, 3, QTableWidgetItem(row['unidade'] or "-"))
                self.product_table.setItem(idx, 4, QTableWidgetItem(row['marca'] or "-"))
                self.product_table.setItem(idx, 5, QTableWidgetItem("Sim" if row['active'] else "Não"))
        
        except Exception as e:
            self.logger.error(f"Erro ao carregar produtos: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao carregar produtos: {e}")
        finally:
            conn.close()

    def _load_product_for_edit(self, item):
        # (Atualizado com a correção do .get e do log)
        row = item.row()
        product_id = int(self.product_table.item(row, 0).text())
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM produtos WHERE id = ?", (product_id,))
            data = cur.fetchone()
            if not data:
                QMessageBox.critical(self, "Erro", "Produto não encontrado.")
                return

            self.clear_form()
            self.set_mode(1) 
            
            self.current_product_id = product_id
            self.form_title.setText(f"Editando Produto: {data['nome']}")
            
            self.empresa_combo.setCurrentIndex(self.empresa_combo.findData(data['empresa_id']) or 0)
            self.categoria_combo.setCurrentIndex(self.categoria_combo.findData(data['categoria_id']) or 0)
            
            for nome, id_forn in self.fornecedor_map.items():
                if id_forn == data['id_fornecedor']:
                    self.fornecedor_combo.setText(nome)
                    break
            
            self.nome_input.setText(data['nome'])
            self.codigo_interno_input.setText(data['codigo_interno'])
            self.codigo_interno_input.setReadOnly(True) 
            
            self.ean_input.setText(data['ean'])
            self.unidade_input.setText(data['unidade'])
            self.marca_input.setText(data['marca'])
            self.modelo_input.setText(data['modelo'])
            self.tipo_combo.setCurrentText(data['tipo'] or "PRODUTO")
            self.peso_kg_input.setText(f"{data['peso_kg'] or 0.0:.3f}".replace('.', ','))
            self.descricao_input.setText(data['descricao'])
            self.status_check.setChecked(bool(data['active']))
            
            # --- Acesso correto ao dicionário (sem .get()) ---
            data_validade = data['data_validade']
            if data_validade:
                self.validade_input.setDate(QDate.fromString(data_validade, "yyyy-MM-dd"))
            else:
                self.validade_input.setDate(QDate()) 
                
            img_path = data['caminho_imagem']
            self.imagem_path_input.setText(img_path)
            self._load_image_preview(img_path)
            
            self.btn_excluir.setEnabled(True)
            self.tabs.setTabEnabled(1, True)
            self.tabs.setTabEnabled(2, True)
            
            self._load_codigos_alternativos()
            self._load_preco_rapido()
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar dados do produto: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao carregar dados do produto: {e}")
        finally:
            conn.close()

    def _generate_sku(self):
        # (Inalterado)
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE sequencias SET valor = valor + 1 WHERE nome = 'COD_INTERNO'")
            if cur.rowcount == 0:
                cur.execute("INSERT INTO sequencias (nome, valor, prefixo) VALUES ('COD_INTERNO', 203000, '')")
                novo_sku = "203000"
            else:
                cur.execute("SELECT valor FROM sequencias WHERE nome = 'COD_INTERNO'")
                novo_sku = str(cur.fetchone()['valor'])
                
            conn.commit()
            self.codigo_interno_input.setText(novo_sku)
        except Exception as e:
            self.logger.error(f"Erro ao gerar SKU: {e}")
            conn.rollback()
            QMessageBox.critical(self, "Erro de DB", f"Falha ao gerar Cód. Interno: {e}")
        finally:
            conn.close()

    def _load_codigos_alternativos(self):
        # (Inalterado)
        self.codigos_table.setRowCount(0)
        if not self.current_product_id: return
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, tipo, codigo FROM produto_codigos_alternativos WHERE id_produto = ?", (self.current_product_id,))
            for row in cur.fetchall():
                idx = self.codigos_table.rowCount()
                self.codigos_table.insertRow(idx)
                self.codigos_table.setItem(idx, 0, QTableWidgetItem(str(row['id'])))
                self.codigos_table.setItem(idx, 1, QTableWidgetItem(row['tipo']))
                self.codigos_table.setItem(idx, 2, QTableWidgetItem(row['codigo']))
        except Exception as e:
            self.logger.error(f"Erro ao carregar códigos: {e}")
            QMessageBox.critical(self, "Erro", f"Erro ao carregar códigos alternativos: {e}")
        finally:
            conn.close()

    def _add_codigo_alternativo(self):
        # (Inalterado)
        tipo = self.tipo_codigo_combo.currentText()
        codigo = self.novo_codigo_input.text().strip()
        
        if not codigo:
            QMessageBox.warning(self, "Erro", "O campo 'Código' não pode estar vazio.")
            return

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO produto_codigos_alternativos (id_produto, tipo, codigo) VALUES (?, ?, ?)",
                (self.current_product_id, tipo, codigo)
            )
            conn.commit()
            self._load_codigos_alternativos()
            self.novo_codigo_input.clear()
        except sqlite3.IntegrityError:
            QMessageBox.critical(self, "Erro", "Este código já existe (UNIQUE constraint).")
        except Exception as e:
            self.logger.error(f"Erro ao salvar código: {e}")
            QMessageBox.critical(self, "Erro", f"Erro ao salvar código alternativo: {e}")
        finally:
            conn.close()

    def _remove_codigo_alternativo(self):
        # (Inalterado)
        row = self.codigos_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Seleção", "Selecione um código na tabela para remover.")
            return
            
        codigo_id = int(self.codigos_table.item(row, 0).text())
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM produto_codigos_alternativos WHERE id = ?", (codigo_id,))
            conn.commit()
            self._load_codigos_alternativos()
        except Exception as e:
            self.logger.error(f"Erro ao remover código: {e}")
            QMessageBox.critical(self, "Erro", f"Erro ao remover código: {e}")
        finally:
            conn.close()

    def _load_preco_rapido(self):
        # (Inalterado)
        tabela_id = self.preco_tabela_combo.currentData()
        if tabela_id is None or self.current_product_id is None:
            self.preco_custo_spin.setValue(0.0)
            self.preco_venda_spin.setValue(0.0)
            return

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT preco_vendadecimal, preco_custodecimal 
                FROM produto_tabela_preco 
                WHERE id_produto = ? AND id_tabela = ?
            """, (self.current_product_id, tabela_id))
            
            data = cur.fetchone()
            if data:
                self.preco_custo_spin.setValue(data['preco_custodecimal'] or 0.0)
                self.preco_venda_spin.setValue(data['preco_vendadecimal'] or 0.0)
            else:
                self.preco_custo_spin.setValue(0.0)
                self.preco_venda_spin.setValue(0.0)
        except Exception as e:
            self.logger.error(f"Erro ao carregar preço rápido: {e}")
            QMessageBox.critical(self, "Erro", f"Erro ao carregar preço rápido: {e}")
        finally:
            conn.close()

    def _update_margem_preco_rapido(self):
        # (Inalterado)
        custo = self.preco_custo_spin.value()
        venda = self.preco_venda_spin.value()
        margem = 0.0
        if custo > 0:
            margem = ((venda - custo) / custo) * 100.0
        elif venda > 0:
            margem = 100.0
        
        self.margem_label.setText(f"Margem: {margem:.2f} %")

    def _save_preco_rapido(self):
        # (Atualizado com log)
        tabela_id = self.preco_tabela_combo.currentData()
        if tabela_id is None or self.current_product_id is None:
            QMessageBox.warning(self, "Erro", "Selecione um produto e uma tabela de preço primeiro.")
            return

        custo = self.preco_custo_spin.value()
        venda = self.preco_venda_spin.value()
        margem = 0.0
        if custo > 0:
            margem = ((venda - custo) / custo) * 100.0
        elif venda > 0:
            margem = 100.0
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO produto_tabela_preco 
                (id_produto, id_tabela, preco_vendadecimal, preco_custodecimal, margemdecimal, data_ultima_atualizacao)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id_produto, id_tabela) DO UPDATE SET
                    preco_vendadecimal = excluded.preco_vendadecimal,
                    preco_custodecimal = excluded.preco_custodecimal,
                    margemdecimal = excluded.margemdecimal,
                    data_ultima_atualizacao = excluded.data_ultima_atualizacao
            """, (self.current_product_id, tabela_id, venda, custo, margem))
            
            conn.commit()
            
            # --- LOG ADICIONADO ---
            self.logger.info(f"Usuário {self.user_id} atualizou preço rápido: Produto {self.current_product_id}, Venda: {venda}, Custo: {custo}.")
            
            QMessageBox.information(self, "Sucesso", "Preço rápido salvo para esta tabela!")
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Erro ao salvar preço rápido: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao salvar preço rápido: {e}")
        finally:
            conn.close()

    def _validate_fields(self):
        # (Inalterado)
        if self.empresa_combo.currentData() is None:
            return False, "Empresa"
        if not self.nome_input.text().strip():
            return False, "Nome do Produto"
        if not self.codigo_interno_input.text().strip():
            return False, "Código Interno"
        if not self.unidade_input.text().strip():
            return False, "Unidade"
        return True, ""

    def save_product(self):
        # (Atualizado com log)
        valido, campo = self._validate_fields()
        if not valido:
            QMessageBox.warning(self, "Campo Obrigatório", f"O campo '{campo}' é obrigatório.")
            return

        categoria_id = self.categoria_combo.currentData()
        
        nome_fornecedor = self.fornecedor_combo.text()
        id_fornecedor = self.fornecedor_map.get(nome_fornecedor, None)
        
        if categoria_id == 0 or categoria_id == "": categoria_id = None
        if id_fornecedor == 0 or id_fornecedor == "": id_fornecedor = None

        data = {
            "empresa_id": self.empresa_combo.currentData(),
            "categoria_id": categoria_id,
            "id_fornecedor": id_fornecedor,
            "nome": self.nome_input.text().strip(),
            "codigo_interno": self.codigo_interno_input.text().strip(),
            "ean": self.ean_input.text().strip() or None,
            "unidade": self.unidade_input.text().strip(),
            "marca": self.marca_input.text().strip() or None,
            "modelo": self.modelo_input.text().strip() or None,
            "tipo": self.tipo_combo.currentText(),
            "peso_kg": float(self.peso_kg_input.text().replace(',', '.') or 0.0),
            "descricao": self.descricao_input.toPlainText().strip() or None,
            "active": 1 if self.status_check.isChecked() else 0,
            
            "data_validade": self.validade_input.date().toString("yyyy-MM-dd") if self.validade_input.date().isValid() else None,
            "caminho_imagem": self.imagem_path_input.text().strip() or None,
        }
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            if self.current_product_id:
                # UPDATE
                data["id"] = self.current_product_id
                fields_to_update = [f"{key} = :{key}" for key in data.keys() if key != 'id']
                query = f"UPDATE produtos SET {', '.join(fields_to_update)} WHERE id = :id"
                msg = "Produto atualizado com sucesso!"
                action_verb = "ATUALIZOU"
                
                cur.execute(query, data)
                
            else:
                # INSERT
                fields = ", ".join(data.keys())
                placeholders = ", ".join([f":{k}" for k in data.keys()])
                query = f"INSERT INTO produtos ({fields}) VALUES ({placeholders})"
                msg = "Produto salvo com sucesso!"
                action_verb = "CRIOU"
                
                cur.execute(query, data)
                self.current_product_id = cur.lastrowid 
            
            # Salva preço (se preenchido)
            tabela_id = self.preco_tabela_combo.currentData()
            venda = self.preco_venda_spin.value()
            
            if tabela_id is not None and (venda > 0 or self.preco_custo_spin.value() > 0): 
                custo = self.preco_custo_spin.value()
                margem = 0.0
                if custo > 0:
                    margem = ((venda - custo) / custo) * 100.0
                elif venda > 0:
                    margem = 100.0
                
                cur.execute("""
                    INSERT INTO produto_tabela_preco 
                    (id_produto, id_tabela, preco_vendadecimal, preco_custodecimal, margemdecimal, data_ultima_atualizacao)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(id_produto, id_tabela) DO UPDATE SET
                        preco_vendadecimal = excluded.preco_vendadecimal,
                        preco_custodecimal = excluded.preco_custodecimal,
                        margemdecimal = excluded.margemdecimal,
                        data_ultima_atualizacao = excluded.data_ultima_atualizacao
                """, (self.current_product_id, tabela_id, venda, custo, margem))
                
                msg += "\nPreço rápido salvo com sucesso!"
            
            conn.commit()
            
            # --- LOG ADICIONADO ---
            self.logger.info(f"Usuário {self.user_id} {action_verb} produto: '{data['nome']}' (Cód: {data['codigo_interno']}).")
            
            QMessageBox.information(self, "Sucesso", msg)
            
            if not self.codigo_interno_input.isReadOnly(): 
                self._reload_form_after_save(self.current_product_id)
            else:
                self.set_mode(0) 

        except sqlite3.IntegrityError as e:
            QMessageBox.critical(self, "Erro", f"Erro de integridade (Código Interno ou EAN duplicado?): {e}")
            if not self.current_product_id:
                self._rollback_sku(self.codigo_interno_input.text())
        except Exception as e:
            self.logger.error(f"Erro ao salvar produto: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao salvar produto: {e}")
        finally:
            conn.close()
    
    def _rollback_sku(self, sku_value):
        # (Inalterado)
        if not sku_value:
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("UPDATE sequencias SET valor = valor - 1 WHERE nome = 'COD_INTERNO' AND valor = ?", (sku_value,))
            conn.commit()
        except Exception as e:
            self.logger.error(f"Erro ao reverter SKU {sku_value}: {e}")
        finally:
            if conn:
                conn.close()

    def _reload_form_after_save(self, product_id):
        # (Inalterado)
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM produtos WHERE id = ?", (product_id,))
            data = cur.fetchone()
            if not data:
                self.cancel_action()
                return

            self.form_title.setText(f"Editando Produto: {data['nome']}")
            self.codigo_interno_input.setReadOnly(True)
            self.btn_excluir.setEnabled(True)
            self.tabs.setTabEnabled(1, True)
            self.tabs.setTabEnabled(2, True)
            
            self._load_codigos_alternativos()
            self._load_preco_rapido()
            
        except Exception as e:
            self.logger.error(f"Erro ao recarregar dados: {e}")
            QMessageBox.critical(self, "Erro", f"Erro ao recarregar dados do produto: {e}")
        finally:
            conn.close()

    def delete_product(self):
        # (Atualizado com log)
        if not self.current_product_id:
            QMessageBox.warning(self, "Erro", "Nenhum produto selecionado.")
            return

        reply = QMessageBox.question(self, "Confirmação",
            "Atenção: Excluir este produto irá remover TODAS as informações de preço, estoque e códigos alternativos vinculados.\n\n"
            "Tem certeza que deseja continuar?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
        if reply == QMessageBox.No:
            return
            
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM produtos WHERE id = ?", (self.current_product_id,))
            conn.commit()
            
            # --- LOG ADICIONADO ---
            self.logger.info(f"Usuário {self.user_id} EXCLUIU produto ID {self.current_product_id} ('{self.nome_input.text()}').")
            
            QMessageBox.information(self, "Sucesso", "Produto excluído com sucesso.")
            self.set_mode(0)
        except sqlite3.IntegrityError as e:
             QMessageBox.critical(self, "Erro de Integridade", 
                "Não é possível excluir. O produto está em uso por vendas ou outras entidades.")
        except Exception as e:
            self.logger.error(f"Erro ao excluir produto: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao excluir produto: {e}")
        finally:
            conn.close()
            
    # --- NOVOS MÉTODOS PARA IMAGEM ---
    def _browse_image(self):
        """Abre um diálogo para selecionar um arquivo de imagem."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Selecionar Imagem do Produto", 
            "", 
            "Imagens (*.png *.jpg *.jpeg *.bmp)"
        )
        
        if file_path:
            self.imagem_path_input.setText(file_path)
            self._load_image_preview(file_path)

    def _load_image_preview(self, file_path):
        """Carrega a imagem no QLabel de preview."""
        if file_path and os.path.exists(file_path):
            pixmap = QPixmap(file_path)
            if pixmap.isNull():
                self.imagem_preview_label.setText("Imagem Inválida")
                self.imagem_preview_label.setPixmap(QPixmap()) # Limpa
            else:
                self.imagem_preview_label.setText("") # Limpa texto
                self.imagem_preview_label.setPixmap(
                    pixmap.scaled(
                        self.imagem_preview_label.size(), 
                        Qt.KeepAspectRatio, 
                        Qt.SmoothTransformation
                    )
                )
        else:
            self.imagem_preview_label.setPixmap(QPixmap()) # Limpa
            self.imagem_preview_label.setText("Sem Imagem")