# modules/fiscal_location_form.py
import sqlite3
import requests
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QGridLayout, QFrame, QTableWidget, QHeaderView, 
    QTableWidgetItem, QAbstractItemView, QStackedWidget, QComboBox,
    QCheckBox, QFileDialog, QTabWidget, QSpinBox
)
from PyQt5.QtCore import Qt
from database.db import get_connection

class FiscalLocationForm(QWidget):
    """
    Formulário para CRUD de Locais de Escrituração (Filiais/Lojas).
    """
    def __init__(self, user_id, **kwargs):
        super().__init__()
        self.user_id = user_id
        self.current_location_id = None
        self.setWindowTitle("Cadastro de Locais de Escrituração")
        
        self.company_map = {} # Dicionário para {id_empresa: razao_social}
        
        self._setup_styles()
        self._build_ui()
        self._connect_signals()
        
        self.set_mode(0) 

    def _setup_styles(self):
        self.setStyleSheet("""
            QWidget { background-color: #f8f8fb; font-family: 'Segoe UI'; }
            QLabel { font-weight: bold; color: #444; }
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
            
            QLineEdit, QComboBox, QCheckBox, QSpinBox {
                border: 1px solid #c0c0d0; border-radius: 5px; 
                padding: 6px; background-color: white;
            }
            QCheckBox { border: none; }
            QPushButton {
                background-color: #0078d7; color: white; border-radius: 6px;
                padding: 8px 15px; font-weight: bold;
            }
            QPushButton:hover { background-color: #005fa3; }
            QPushButton#deleteButton { background-color: #e74c3c; }
            QPushButton#deleteButton:hover { background-color: #c0392b; }
            QPushButton#btn_browse { 
                background-color: #95A5A6; 
                padding: 6px 10px; 
                font-size: 12px;
            }
            QPushButton#btn_browse:hover { background-color: #7F8C8D; }
        """)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        
        # --- 1. PAINEL DE BUSCA E NAVEGAÇÃO ---
        self.search_panel = QWidget()
        search_layout = QHBoxLayout(self.search_panel)
        search_layout.setContentsMargins(0, 10, 0, 10)
        self.btn_novo = QPushButton("Novo Local")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Pesquisar por Nome do Local ou CNPJ...")
        self.btn_pesquisar = QPushButton("Pesquisar")
        
        search_layout.addWidget(self.btn_novo)
        search_layout.addStretch()
        search_layout.addWidget(self.search_input, 1) 
        search_layout.addWidget(self.btn_pesquisar)
        
        # --- 2. STACKED WIDGET (Tabela / Formulário) ---
        self.stack = QStackedWidget()
        
        # --- Tela 0: Tabela de Locais ---
        self.table_widget = QWidget()
        table_layout = QVBoxLayout(self.table_widget)
        table_layout.setContentsMargins(0,0,0,0)
        self.location_table = QTableWidget()
        self.location_table.setColumnCount(4)
        self.location_table.setHorizontalHeaderLabels(["ID", "Nome do Local", "CNPJ", "Empresa (Matriz)"])
        self.location_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.location_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.location_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.location_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.location_table.setColumnHidden(0, True)
        table_layout.addWidget(self.location_table)
        
        # --- Tela 1: Formulário de Cadastro ---
        self.form_panel = QFrame()
        self.form_panel.setObjectName("form_panel")
        form_layout = QVBoxLayout(self.form_panel)
        self.form_title = QLabel("Cadastro de Local de Escrituração", objectName="form_title")
        form_layout.addWidget(self.form_title)
        
        # --- Widgets do Formulário ---
        self.empresa_combo = QComboBox()
        self.nome_local_input = QLineEdit()
        self.codigo_interno_input = QLineEdit()
        self.cnpj_input = QLineEdit()
        self.cnpj_input.setInputMask("99.999.999/9999-99")
        self.ie_input = QLineEdit()
        self.tipo_local_combo = QComboBox()
        self.tipo_local_combo.addItems(["1 - Matriz", "2 - Filial", "3 - Centro de Distribuição"])
        self.status_combo = QComboBox()
        self.status_combo.addItems(["1 - Ativo", "2 - Inativo"])
        
        self.end_logradouro_input = QLineEdit()
        self.end_numero_input = QLineEdit()
        self.end_complemento_input = QLineEdit()
        self.end_bairro_input = QLineEdit()
        self.end_cep_input = QLineEdit()
        self.end_cep_input.setInputMask("99999-999")
        self.end_municipio_input = QLineEdit()
        self.end_uf_input = QLineEdit()
        self.end_uf_input.setMaxLength(2)
        
        self.responsavel_op_input = QLineEdit()
        
        # Config Fiscal
        self.herdar_config_check = QCheckBox("Herdar configurações fiscais (CSC, Certificado, Ambiente) da Empresa Matriz")
        self.herdar_config_check.setChecked(True)
        self.ambiente_combo = QComboBox()
        self.ambiente_combo.addItems(["2 - Homologação", "1 - Produção"])
        self.csc_input = QLineEdit()
        self.csc_id_input = QLineEdit()
        self.csc_id_input.setMaxLength(8)
        self.csc_validade_input = QLineEdit()
        self.csc_validade_input.setInputMask("99/99/9999")
        
        self.certificado_path_input = QLineEdit()
        self.certificado_path_input.setReadOnly(True)
        self.btn_browse_cert = QPushButton("Procurar...")
        self.btn_browse_cert.setObjectName("btn_browse")
        self.certificado_senha_input = QLineEdit()
        self.certificado_senha_input.setEchoMode(QLineEdit.Password)
        
        self.notificar_venc_cert_check = QCheckBox("Notificar vencimento do certificado")
        self.certificado_validade_input = QLineEdit()
        self.certificado_validade_input.setInputMask("9999-99-99")
        self.certificado_validade_input.setPlaceholderText("AAAA-MM-DD")
        self.notificar_venc_dias_input = QSpinBox()
        self.notificar_venc_dias_input.setRange(1, 90)
        self.notificar_venc_dias_input.setValue(30)
        
        # --- Layout em Abas ---
        self.tabs = QTabWidget()
        tab_geral = QWidget()
        tab_endereco = QWidget()
        tab_fiscal = QWidget()
        
        self.tabs.addTab(tab_geral, "Geral")
        self.tabs.addTab(tab_endereco, "Endereço")
        self.tabs.addTab(tab_fiscal, "Fiscal (DFe)")
        form_layout.addWidget(self.tabs)
        
        # --- Aba Geral ---
        layout_geral = QGridLayout(tab_geral)
        layout_geral.addWidget(QLabel("Empresa (Matriz): *", objectName="required"), 0, 0)
        layout_geral.addWidget(self.empresa_combo, 0, 1)
        layout_geral.addWidget(QLabel("Nome do Local: *", objectName="required"), 1, 0)
        layout_geral.addWidget(self.nome_local_input, 1, 1)
        layout_geral.addWidget(QLabel("CNPJ (Se diferente):"), 2, 0)
        layout_geral.addWidget(self.cnpj_input, 2, 1)
        layout_geral.addWidget(QLabel("Inscrição Estadual:"), 3, 0)
        layout_geral.addWidget(self.ie_input, 3, 1)
        layout_geral.addWidget(QLabel("Código Interno:"), 4, 0)
        layout_geral.addWidget(self.codigo_interno_input, 4, 1)
        layout_geral.addWidget(QLabel("Tipo de Local:"), 5, 0)
        layout_geral.addWidget(self.tipo_local_combo, 5, 1)
        layout_geral.addWidget(QLabel("Responsável Operacional:"), 6, 0)
        layout_geral.addWidget(self.responsavel_op_input, 6, 1)
        layout_geral.addWidget(QLabel("Status:"), 7, 0)
        layout_geral.addWidget(self.status_combo, 7, 1)
        layout_geral.setColumnStretch(1, 1)
        layout_geral.setRowStretch(8, 1)
        
        # --- Aba Endereço ---
        layout_end = QGridLayout(tab_endereco)
        layout_end.addWidget(QLabel("CEP:"), 0, 0)
        layout_end.addWidget(self.end_cep_input, 0, 1)
        layout_end.addWidget(QLabel("Logradouro:"), 1, 0)
        layout_end.addWidget(self.end_logradouro_input, 1, 1)
        layout_end.addWidget(QLabel("Número:"), 2, 0)
        layout_end.addWidget(self.end_numero_input, 2, 1)
        layout_end.addWidget(QLabel("Complemento:"), 3, 0)
        layout_end.addWidget(self.end_complemento_input, 3, 1)
        layout_end.addWidget(QLabel("Bairro:"), 4, 0)
        layout_end.addWidget(self.end_bairro_input, 4, 1)
        layout_end.addWidget(QLabel("Município:"), 5, 0)
        layout_end.addWidget(self.end_municipio_input, 5, 1)
        layout_end.addWidget(QLabel("UF:"), 6, 0)
        layout_end.addWidget(self.end_uf_input, 6, 1)
        layout_end.setColumnStretch(1, 1)
        layout_end.setRowStretch(7, 1)
        
        # --- Aba Fiscal (ATUALIZADA) ---
        layout_fiscal = QGridLayout(tab_fiscal)
        layout_fiscal.setSpacing(10)
        layout_fiscal.addWidget(self.herdar_config_check, 0, 0, 1, 4)
        
        # Frame para os campos que serão ocultados
        self.fiscal_config_frame = QFrame() 
        layout_fiscal_group = QGridLayout(self.fiscal_config_frame)
        layout_fiscal_group.setContentsMargins(0, 5, 0, 0)
        layout_fiscal_group.setSpacing(10)
        
        layout_fiscal_group.addWidget(QLabel("Ambiente Emissão:"), 0, 0)
        layout_fiscal_group.addWidget(self.ambiente_combo, 0, 1, 1, 6)

        # Layout em linha para CSC
        layout_fiscal_group.addWidget(QLabel("CSC (Token):"), 1, 0)
        layout_fiscal_group.addWidget(self.csc_input, 1, 1, 1, 2)
        layout_fiscal_group.addWidget(QLabel("CSC ID:"), 1, 3)
        self.csc_id_input.setMaximumWidth(100)
        layout_fiscal_group.addWidget(self.csc_id_input, 1, 4)
        layout_fiscal_group.addWidget(QLabel("Validade CSC:"), 1, 5)
        self.csc_validade_input.setMaximumWidth(120)
        layout_fiscal_group.addWidget(self.csc_validade_input, 1, 6)
        
        layout_cert = QHBoxLayout()
        layout_cert.setContentsMargins(0,0,0,0)
        layout_cert.addWidget(self.certificado_path_input, 1)
        layout_cert.addWidget(self.btn_browse_cert)
        layout_fiscal_group.addWidget(QLabel("Certificado Digital:"), 2, 0)
        layout_fiscal_group.addLayout(layout_cert, 2, 1, 1, 6)
        
        layout_fiscal_group.addWidget(QLabel("Senha do Certificado:"), 3, 0)
        layout_fiscal_group.addWidget(self.certificado_senha_input, 3, 1, 1, 2)
        
        layout_fiscal_group.addWidget(QLabel("Validade Certificado:"), 4, 0)
        self.certificado_validade_input.setMaximumWidth(120)
        layout_fiscal_group.addWidget(self.certificado_validade_input, 4, 1)
        
        notify_layout = QHBoxLayout()
        notify_layout.setContentsMargins(0,0,0,0)
        notify_layout.addWidget(self.notificar_venc_cert_check)
        notify_layout.addWidget(QLabel("Notificar com:"))
        self.notificar_venc_dias_input.setMaximumWidth(80)
        notify_layout.addWidget(self.notificar_venc_dias_input)
        notify_layout.addWidget(QLabel("dias de antecedência"))
        notify_layout.addStretch()
        layout_fiscal_group.addLayout(notify_layout, 5, 1, 1, 6)
        
        layout_fiscal_group.setRowStretch(6, 1)
        layout_fiscal_group.setColumnStretch(1, 1)
        layout_fiscal_group.setColumnStretch(2, 1)
        layout_fiscal_group.setColumnStretch(4, 1)
        layout_fiscal_group.setColumnStretch(6, 1)
        
        layout_fiscal.addWidget(self.fiscal_config_frame, 1, 0, 1, 4)
        layout_fiscal.setRowStretch(2, 1)
        
        # Botões do formulário
        form_btn_layout = QHBoxLayout()
        form_btn_layout.addStretch()
        self.btn_salvar = QPushButton("Salvar")
        self.btn_excluir = QPushButton("Excluir")
        self.btn_excluir.setObjectName("deleteButton")
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setStyleSheet("background-color: #95A5A6;")
        form_btn_layout.addWidget(self.btn_cancelar)
        form_btn_layout.addWidget(self.btn_excluir)
        form_btn_layout.addWidget(self.btn_salvar)
        form_layout.addLayout(form_btn_layout)
        
        self.stack.addWidget(self.table_widget)
        self.stack.addWidget(self.form_panel)
        
        main_layout.addWidget(self.search_panel)
        main_layout.addWidget(self.stack, 1)

    def set_mode(self, mode):
        """Alterna entre o modo Tabela (0) e Formulário (1)."""
        if mode == 0:
            self.stack.setCurrentIndex(0)
            self.search_panel.setVisible(True)
            self.load_locations() 
        else:
            self._load_empresas_combobox() # Recarrega as empresas
            self.stack.setCurrentIndex(1)
            self.search_panel.setVisible(False)
            self._toggle_fiscal_frame(self.herdar_config_check.isChecked())

    def _connect_signals(self):
        self.btn_novo.clicked.connect(self.show_new_form)
        self.btn_salvar.clicked.connect(self.save_location)
        self.btn_excluir.clicked.connect(self.delete_location)
        self.btn_cancelar.clicked.connect(self.cancel_action)
        self.btn_pesquisar.clicked.connect(self.load_locations)
        self.search_input.returnPressed.connect(self.load_locations)
        self.location_table.itemDoubleClicked.connect(self._load_location_for_edit)
        self.btn_browse_cert.clicked.connect(self._browse_certificate)
        self.herdar_config_check.toggled.connect(self._toggle_fiscal_frame)

    def _toggle_fiscal_frame(self, checked):
        """Esconde ou mostra o frame fiscal baseado na herança."""
        self.fiscal_config_frame.setVisible(not checked)

    def _browse_certificate(self):
        file, _ = QFileDialog.getOpenFileName(self, "Selecione o Certificado", "", "Certificados (*.pfx *.p12)")
        if file:
            self.certificado_path_input.setText(file)

    def _load_empresas_combobox(self):
        """Carrega a lista de empresas no QComboBox."""
        self.empresa_combo.clear()
        self.company_map.clear()
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, razao_social FROM empresas WHERE status = 1 ORDER BY razao_social")
            empresas = cur.fetchall()
            
            self.empresa_combo.addItem("Selecione uma empresa...", None)
            if not empresas:
                self.empresa_combo.setEnabled(False)
                return

            self.empresa_combo.setEnabled(True)
            for empresa in empresas:
                self.empresa_combo.addItem(empresa['razao_social'], empresa['id'])
                self.company_map[empresa['id']] = empresa['razao_social']
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar empresas: {e}")
        finally:
            conn.close()

    def show_new_form(self):
        self.clear_form()
        self.set_mode(1) 
        self.nome_local_input.setFocus()
        self.form_title.setText("Novo Local de Escrituração")

    def cancel_action(self):
        self.clear_form()
        self.set_mode(0) 

    def clear_form(self):
        self.current_location_id = None
        self.empresa_combo.setCurrentIndex(0)
        self.nome_local_input.clear()
        self.codigo_interno_input.clear()
        self.cnpj_input.clear()
        self.ie_input.clear()
        self.tipo_local_combo.setCurrentIndex(0)
        self.responsavel_op_input.clear()
        self.status_combo.setCurrentIndex(0)
        
        self.end_logradouro_input.clear()
        self.end_numero_input.clear()
        self.end_complemento_input.clear()
        self.end_bairro_input.clear()
        self.end_cep_input.clear()
        self.end_municipio_input.clear()
        self.end_uf_input.clear()
        
        self.herdar_config_check.setChecked(True)
        self.ambiente_combo.setCurrentIndex(0)
        self.csc_input.clear()
        self.csc_id_input.clear()
        self.csc_validade_input.clear()
        self.certificado_path_input.clear()
        self.certificado_senha_input.clear()
        self.certificado_validade_input.clear()
        self.notificar_venc_cert_check.setChecked(False)
        self.notificar_venc_dias_input.setValue(30)
        
        self.btn_excluir.setEnabled(False)
        self.form_title.setText("Cadastro de Local de Escrituração")

    def load_locations(self):
        """Carrega/Busca locais e preenche a tabela."""
        self.location_table.setRowCount(0)
        search_term = self.search_input.text().strip()
        
        conn = get_connection()
        try:
            if not self.company_map:
                self._load_empresas_combobox()

            cur = conn.cursor()
            query = "SELECT id, nome_local, cnpj, empresa_id FROM locais_escrituracao"
            params = []
            
            if search_term:
                query += " WHERE (nome_local LIKE ? OR cnpj LIKE ?)"
                params.extend([f"%{search_term}%", f"%{search_term}%"])
            
            query += " ORDER BY nome_local"
            cur.execute(query, tuple(params))
            
            rows = cur.fetchall()
            for row in rows:
                idx = self.location_table.rowCount()
                self.location_table.insertRow(idx)
                
                empresa_nome = self.company_map.get(row['empresa_id'], "Empresa Desconhecida")
                
                self.location_table.setItem(idx, 0, QTableWidgetItem(str(row['id'])))
                self.location_table.setItem(idx, 1, QTableWidgetItem(row['nome_local']))
                self.location_table.setItem(idx, 2, QTableWidgetItem(row['cnpj']))
                self.location_table.setItem(idx, 3, QTableWidgetItem(empresa_nome))
        
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar locais: {e}")
        finally:
            conn.close()

    def _load_location_for_edit(self, item):
        """Carrega os dados do local selecionado no formulário."""
        row = item.row()
        location_id = int(self.location_table.item(row, 0).text())
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM locais_escrituracao WHERE id = ?", (location_id,))
            data = cur.fetchone()
            if not data:
                QMessageBox.critical(self, "Erro", "Local não encontrado.")
                return

            self.clear_form()
            self._load_empresas_combobox()
            self.set_mode(1) 
            
            self.current_location_id = location_id
            self.form_title.setText(f"Editando Local: {data['nome_local']}")
            
            index = self.empresa_combo.findData(data['empresa_id'])
            if index >= 0: self.empresa_combo.setCurrentIndex(index)
            
            self.nome_local_input.setText(data['nome_local'])
            self.codigo_interno_input.setText(data['codigo_interno'])
            self.cnpj_input.setText(data['cnpj'])
            self.ie_input.setText(data['inscricao_estadual'])
            self.tipo_local_combo.setCurrentIndex(data['tipo_local'] - 1 if data['tipo_local'] else 0)
            self.responsavel_op_input.setText(data['responsavel_operacional'])
            self.status_combo.setCurrentIndex(0 if data['status'] == 1 else 1)
            
            self.end_logradouro_input.setText(data['end_logradouro'])
            self.end_numero_input.setText(data['end_numero'])
            self.end_complemento_input.setText(data['end_complemento'])
            self.end_bairro_input.setText(data['end_bairro'])
            self.end_cep_input.setText(data['end_cep'])
            self.end_municipio_input.setText(data['end_municipio'])
            self.end_uf_input.setText(data['end_uf'])
            
            self.herdar_config_check.setChecked(bool(data['herdar_config_empresa']))
            self.ambiente_combo.setCurrentIndex(0 if data['ambiente'] == 2 else 1)
            self.csc_input.setText(data['csc'])
            self.csc_id_input.setText(data['csc_id'])
            self.csc_validade_input.setText(data['csc_validade'])
            self.certificado_path_input.setText(data['certificado_path'])
            
            self.certificado_validade_input.setText(data['certificado_validade'])
            self.notificar_venc_cert_check.setChecked(bool(data['notificar_venc_cert']))
            self.notificar_venc_dias_input.setValue(data['notificar_venc_dias'] or 30)

            self.btn_excluir.setEnabled(True)
            self._toggle_fiscal_frame(self.herdar_config_check.isChecked())
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar dados do local: {e}")
        finally:
            conn.close()

    def _validate_fields(self):
        if self.empresa_combo.currentData() is None:
            return False, "Empresa (Matriz)"
        if not self.nome_local_input.text().strip():
            return False, "Nome do Local"
        cnpj = self.cnpj_input.text().replace('.', '').replace('/', '').replace('-', '')
        if cnpj and len(cnpj) != 14:
            return False, "CNPJ (inválido)"
        return True, ""

    def save_location(self):
        valido, campo = self._validate_fields()
        if not valido:
            QMessageBox.warning(self, "Campo Inválido", f"O campo '{campo}' é obrigatório ou inválido.")
            return

        data = {
            "empresa_id": self.empresa_combo.currentData(),
            "nome_local": self.nome_local_input.text().strip(),
            "codigo_interno": self.codigo_interno_input.text().strip(),
            "cnpj": self.cnpj_input.text().strip(),
            "inscricao_estadual": self.ie_input.text().strip(),
            "end_logradouro": self.end_logradouro_input.text().strip(),
            "end_numero": self.end_numero_input.text().strip(),
            "end_complemento": self.end_complemento_input.text().strip(),
            "end_bairro": self.end_bairro_input.text().strip(),
            "end_cep": self.end_cep_input.text().strip(),
            "end_municipio": self.end_municipio_input.text().strip(),
            "end_uf": self.end_uf_input.text().strip(),
            "responsavel_operacional": self.responsavel_op_input.text().strip(),
            "tipo_local": self.tipo_local_combo.currentIndex() + 1,
            "status": 1 if self.status_combo.currentIndex() == 0 else 2,
            "herdar_config_empresa": 1 if self.herdar_config_check.isChecked() else 0,
            "ambiente": 2 if self.ambiente_combo.currentIndex() == 0 else 1,
            "csc": self.csc_input.text().strip(),
            "csc_id": self.csc_id_input.text().strip(),
            "csc_validade": self.csc_validade_input.text().strip(),
            "certificado_path": self.certificado_path_input.text().strip(),
            "certificado_validade": self.certificado_validade_input.text().strip() or None,
            "notificar_venc_cert": 1 if self.notificar_venc_cert_check.isChecked() else 0,
            "notificar_venc_dias": self.notificar_venc_dias_input.value()
        }

        if self.certificado_senha_input.text():
             data["certificado_senha"] = self.certificado_senha_input.text()
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            if self.current_location_id:
                # UPDATE
                data["id"] = self.current_location_id
                fields_to_update = [f"{key} = :{key}" for key in data.keys() if key != 'id']
                query = f"UPDATE locais_escrituracao SET {', '.join(fields_to_update)} WHERE id = :id"
                params = data
                msg = "Local de Escrituração atualizado!"
            else:
                # INSERT
                fields = ", ".join(data.keys())
                placeholders = ", ".join([f":{k}" for k in data.keys()])
                query = f"INSERT INTO locais_escrituracao ({fields}) VALUES ({placeholders})"
                params = data
                msg = "Local de Escrituração salvo!"
            
            cur.execute(query, params)
            conn.commit()
            QMessageBox.information(self, "Sucesso", msg)
            self.set_mode(0)

        except sqlite3.IntegrityError as e:
            QMessageBox.critical(self, "Erro", f"Erro de integridade (CNPJ duplicado?): {e}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar local: {e}")
        finally:
            conn.close()
            
    def delete_location(self):
        if not self.current_location_id:
            QMessageBox.warning(self, "Erro", "Nenhum local selecionado.")
            return

        reply = QMessageBox.question(self, "Confirmação",
            "Atenção: Excluir este local irá remover TODOS os terminais de caixa vinculados a ele.\n\n"
            "Tem certeza que deseja continuar?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
        if reply == QMessageBox.No:
            return
            
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM locais_escrituracao WHERE id = ?", (self.current_location_id,))
            conn.commit()
            QMessageBox.information(self, "Sucesso", "Local e seus dados vinculados foram excluídos.")
            self.set_mode(0)
        except sqlite3.IntegrityError as e:
             QMessageBox.critical(self, "Erro de Integridade", 
                "Não foi possível excluir este local pois ele possui vendas associadas.\n"
                "Para excluir, primeiro remova os registros de vendas vinculados.")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao excluir local: {e}")
        finally:
            conn.close()