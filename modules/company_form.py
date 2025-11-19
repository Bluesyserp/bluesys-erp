# modules/company_form.py
import sqlite3
import requests
import json
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QGridLayout, QFrame, QTableWidget, QHeaderView, 
    QTableWidgetItem, QAbstractItemView, QStackedWidget, QComboBox,
    QCheckBox, QFileDialog, QTabWidget, QSpinBox
)
from PyQt5.QtCore import Qt
from database.db import get_connection

class CompanyForm(QWidget):
    """
    Formulário completo para CRUD de Empresas (Matriz).
    """
    def __init__(self, user_id, **kwargs):
        super().__init__()
        
        # --- ATUALIZAÇÃO DA API ---
        self.API_TOKEN = "22896|Bxa6LMJ6uAIerPz7pxBcjmKNxMCUFiZn" 
        # --- FIM DA ATUALIZAÇÃO ---
        
        self.user_id = user_id
        self.current_company_id = None
        self.setWindowTitle("Cadastro de Empresas")
        
        self._setup_styles()
        self._build_ui()
        self._connect_signals()
        
        self.set_mode(0) 

    def _setup_styles(self):
        # (CSS Inalterado)
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
            QPushButton#btn_buscar_cnpj {
                background-color: #2ECC71; /* Verde */
                font-size: 12px;
                padding: 6px 10px;
                max-width: 100px;
            }
            QPushButton#btn_buscar_cnpj:hover { background-color: #27AE60; }
        """)

    def _build_ui(self):
        # (Função inalterada - Omitida por brevidade)
        main_layout = QVBoxLayout(self)
        self.search_panel = QWidget()
        search_layout = QHBoxLayout(self.search_panel)
        search_layout.setContentsMargins(0, 10, 0, 10)
        self.btn_novo = QPushButton("Nova Empresa")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Pesquisar por Razão Social ou CNPJ...")
        self.btn_pesquisar = QPushButton("Pesquisar")
        search_layout.addWidget(self.btn_novo)
        search_layout.addStretch()
        search_layout.addWidget(self.search_input, 1) 
        search_layout.addWidget(self.btn_pesquisar)
        self.stack = QStackedWidget()
        self.table_widget = QWidget()
        table_layout = QVBoxLayout(self.table_widget)
        table_layout.setContentsMargins(0,0,0,0)
        self.company_table = QTableWidget()
        self.company_table.setColumnCount(4)
        self.company_table.setHorizontalHeaderLabels(["ID", "Razão Social", "Nome Fantasia", "CNPJ"])
        self.company_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.company_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.company_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.company_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.company_table.setColumnHidden(0, True)
        table_layout.addWidget(self.company_table)
        self.form_panel = QFrame()
        self.form_panel.setObjectName("form_panel")
        form_layout = QVBoxLayout(self.form_panel)
        self.form_title = QLabel("Cadastro de Empresa", objectName="form_title")
        form_layout.addWidget(self.form_title)
        self.razao_social_input = QLineEdit()
        self.nome_fantasia_input = QLineEdit()
        self.cnpj_input = QLineEdit()
        self.cnpj_input.setInputMask("99.999.999/9999-99")
        self.btn_buscar_cnpj = QPushButton("Buscar Dados") 
        self.btn_buscar_cnpj.setObjectName("btn_buscar_cnpj")
        self.ie_input = QLineEdit()
        self.im_input = QLineEdit()
        self.regime_tributario_combo = QComboBox()
        self.regime_tributario_combo.addItems([
            "Simples Nacional", "Lucro Presumido", "Lucro Real", "MEI"
        ])
        self.crt_combo = QComboBox()
        self.crt_combo.addItems([
            "1 – Simples Nacional", 
            "2 – Simples Nacional (excesso de sublimite)", 
            "3 – Regime Normal"
        ])
        self.end_logradouro_input = QLineEdit()
        self.end_numero_input = QLineEdit()
        self.end_complemento_input = QLineEdit()
        self.end_bairro_input = QLineEdit()
        self.end_cep_input = QLineEdit()
        self.end_cep_input.setInputMask("99999-999")
        self.end_municipio_input = QLineEdit()
        self.end_uf_input = QLineEdit()
        self.end_uf_input.setMaxLength(2)
        self.telefone_input = QLineEdit()
        self.email_input = QLineEdit()
        self.responsavel_input = QLineEdit()
        self.cpf_responsavel_input = QLineEdit()
        self.cpf_responsavel_input.setInputMask("999.999.999-99")
        self.certificado_path_input = QLineEdit()
        self.certificado_path_input.setReadOnly(True)
        self.btn_browse_cert = QPushButton("Procurar...")
        self.btn_browse_cert.setObjectName("btn_browse")
        self.certificado_senha_input = QLineEdit()
        self.certificado_senha_input.setEchoMode(QLineEdit.Password)
        self.csc_input = QLineEdit()
        self.csc_id_input = QLineEdit()
        self.csc_id_input.setMaxLength(8)
        self.csc_validade_input = QLineEdit()
        self.csc_validade_input.setInputMask("99/99/9999")
        self.ambiente_combo = QComboBox()
        self.ambiente_combo.addItems(["2 - Homologação", "1 - Produção"])
        self.notificar_venc_cert_check = QCheckBox("Notificar vencimento do certificado")
        self.certificado_validade_input = QLineEdit()
        self.certificado_validade_input.setInputMask("9999-99-99")
        self.certificado_validade_input.setPlaceholderText("AAAA-MM-DD")
        self.notificar_venc_dias_input = QSpinBox()
        self.notificar_venc_dias_input.setRange(1, 90)
        self.notificar_venc_dias_input.setValue(30)
        self.status_combo = QComboBox()
        self.status_combo.addItems(["1 - Ativa", "2 - Inativa"])
        self.tabs = QTabWidget()
        tab_geral = QWidget()
        tab_endereco = QWidget()
        tab_fiscal = QWidget()
        self.tabs.addTab(tab_geral, "Geral")
        self.tabs.addTab(tab_endereco, "Endereço")
        self.tabs.addTab(tab_fiscal, "Fiscal (DFe)")
        form_layout.addWidget(self.tabs)
        layout_geral = QGridLayout(tab_geral)
        layout_geral.addWidget(QLabel("Razão Social: *", objectName="required"), 0, 0)
        layout_geral.addWidget(self.razao_social_input, 0, 1)
        layout_geral.addWidget(QLabel("Nome Fantasia:"), 1, 0)
        layout_geral.addWidget(self.nome_fantasia_input, 1, 1)
        cnpj_layout = QHBoxLayout()
        cnpj_layout.setContentsMargins(0,0,0,0)
        cnpj_layout.addWidget(self.cnpj_input, 1) 
        cnpj_layout.addWidget(self.btn_buscar_cnpj)
        layout_geral.addWidget(QLabel("CNPJ: *", objectName="required"), 2, 0)
        layout_geral.addLayout(cnpj_layout, 2, 1)
        layout_geral.addWidget(QLabel("Inscrição Estadual:"), 3, 0)
        layout_geral.addWidget(self.ie_input, 3, 1)
        layout_geral.addWidget(QLabel("Inscrição Municipal:"), 4, 0)
        layout_geral.addWidget(self.im_input, 4, 1)
        layout_geral.addWidget(QLabel("Telefone:"), 5, 0)
        layout_geral.addWidget(self.telefone_input, 5, 1)
        layout_geral.addWidget(QLabel("Email:"), 6, 0)
        layout_geral.addWidget(self.email_input, 6, 1)
        layout_geral.addWidget(QLabel("Responsável Legal:"), 7, 0)
        layout_geral.addWidget(self.responsavel_input, 7, 1)
        layout_geral.addWidget(QLabel("CPF do Responsável:"), 8, 0)
        layout_geral.addWidget(self.cpf_responsavel_input, 8, 1)
        layout_geral.addWidget(QLabel("Status:"), 9, 0)
        layout_geral.addWidget(self.status_combo, 9, 1)
        layout_geral.setColumnStretch(1, 1)
        layout_geral.setRowStretch(10, 1)
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
        layout_fiscal = QGridLayout(tab_fiscal)
        layout_fiscal.setSpacing(10)
        layout_fiscal.addWidget(QLabel("Regime Tributário:"), 0, 0)
        layout_fiscal.addWidget(self.regime_tributario_combo, 0, 1, 1, 6)
        layout_fiscal.addWidget(QLabel("CRT:"), 1, 0)
        layout_fiscal.addWidget(self.crt_combo, 1, 1, 1, 6)
        layout_fiscal.addWidget(QLabel("Ambiente Emissão:"), 2, 0)
        layout_fiscal.addWidget(self.ambiente_combo, 2, 1, 1, 6)
        layout_fiscal.addWidget(QLabel("CSC (Token):"), 3, 0)
        layout_fiscal.addWidget(self.csc_input, 3, 1, 1, 2)
        layout_fiscal.addWidget(QLabel("CSC ID:"), 3, 3)
        self.csc_id_input.setMaximumWidth(100)
        layout_fiscal.addWidget(self.csc_id_input, 3, 4)
        layout_fiscal.addWidget(QLabel("Validade CSC:"), 3, 5)
        self.csc_validade_input.setMaximumWidth(120)
        layout_fiscal.addWidget(self.csc_validade_input, 3, 6)
        layout_cert = QHBoxLayout()
        layout_cert.setContentsMargins(0,0,0,0)
        layout_cert.addWidget(self.certificado_path_input, 1)
        layout_cert.addWidget(self.btn_browse_cert)
        layout_fiscal.addWidget(QLabel("Certificado Digital:"), 4, 0)
        layout_fiscal.addLayout(layout_cert, 4, 1, 1, 6)
        layout_fiscal.addWidget(QLabel("Senha do Certificado:"), 5, 0)
        layout_fiscal.addWidget(self.certificado_senha_input, 5, 1, 1, 2)
        layout_fiscal.addWidget(QLabel("Validade Certificado:"), 6, 0)
        self.certificado_validade_input.setMaximumWidth(120)
        layout_fiscal.addWidget(self.certificado_validade_input, 6, 1)
        notify_layout = QHBoxLayout()
        notify_layout.setContentsMargins(0,0,0,0)
        notify_layout.addWidget(self.notificar_venc_cert_check)
        notify_layout.addWidget(QLabel("Notificar com:"))
        self.notificar_venc_dias_input.setMaximumWidth(80)
        notify_layout.addWidget(self.notificar_venc_dias_input)
        notify_layout.addWidget(QLabel("dias de antecedência"))
        notify_layout.addStretch()
        layout_fiscal.addLayout(notify_layout, 7, 1, 1, 6)
        layout_fiscal.setRowStretch(8, 1) 
        layout_fiscal.setColumnStretch(1, 1)
        layout_fiscal.setColumnStretch(2, 1)
        layout_fiscal.setColumnStretch(4, 1)
        layout_fiscal.setColumnStretch(6, 1)
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
        # (Função inalterada)
        if mode == 0:
            self.stack.setCurrentIndex(0)
            self.search_panel.setVisible(True)
            self.load_companies() 
        else:
            self.stack.setCurrentIndex(1)
            self.search_panel.setVisible(False)

    def _connect_signals(self):
        # (Função inalterada - Sinal do novo botão adicionado)
        self.btn_novo.clicked.connect(self.show_new_form)
        self.btn_salvar.clicked.connect(self.save_company)
        self.btn_excluir.clicked.connect(self.delete_company)
        self.btn_cancelar.clicked.connect(self.cancel_action)
        self.btn_pesquisar.clicked.connect(self.load_companies)
        self.search_input.returnPressed.connect(self.load_companies)
        self.company_table.itemDoubleClicked.connect(self._load_company_for_edit)
        self.btn_browse_cert.clicked.connect(self._browse_certificate)
        self.btn_buscar_cnpj.clicked.connect(self.search_document) 

    def _browse_certificate(self):
        # (Função inalterada)
        file, _ = QFileDialog.getOpenFileName(self, "Selecione o Certificado", "", "Certificados (*.pfx *.p12)")
        if file:
            self.certificado_path_input.setText(file)

    def show_new_form(self):
        # (Função inalterada)
        self.clear_form()
        self.set_mode(1) 
        self.razao_social_input.setFocus()
        self.form_title.setText("Nova Empresa")

    def cancel_action(self):
        # (Função inalterada)
        self.clear_form()
        self.set_mode(0) 

    def clear_form(self):
        # (Função inalterada - Novos campos adicionados)
        self.current_company_id = None
        self.razao_social_input.clear()
        self.nome_fantasia_input.clear()
        self.cnpj_input.clear()
        self.ie_input.clear()
        self.im_input.clear()
        self.regime_tributario_combo.setCurrentIndex(0)
        self.crt_combo.setCurrentIndex(0)
        self.end_logradouro_input.clear()
        self.end_numero_input.clear()
        self.end_complemento_input.clear()
        self.end_bairro_input.clear()
        self.end_cep_input.clear()
        self.end_municipio_input.clear()
        self.end_uf_input.clear()
        self.telefone_input.clear()
        self.email_input.clear()
        self.responsavel_input.clear()
        self.cpf_responsavel_input.clear()
        self.certificado_path_input.clear()
        self.certificado_senha_input.clear()
        self.csc_input.clear()
        self.csc_id_input.clear()
        self.csc_validade_input.clear() 
        self.ambiente_combo.setCurrentIndex(0)
        self.status_combo.setCurrentIndex(0)
        self.notificar_venc_cert_check.setChecked(False)
        self.certificado_validade_input.clear()
        self.notificar_venc_dias_input.setValue(30)
        self.btn_excluir.setEnabled(False)
        self.form_title.setText("Cadastro de Empresa")

    def load_companies(self):
        # (Função inalterada)
        self.company_table.setRowCount(0)
        search_term = self.search_input.text().strip()
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            query = "SELECT id, razao_social, nome_fantasia, cnpj FROM empresas"
            params = []
            
            if search_term:
                query += " WHERE (razao_social LIKE ? OR cnpj LIKE ? OR nome_fantasia LIKE ?)"
                params.extend([f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"])
            
            query += " ORDER BY razao_social"
            cur.execute(query, tuple(params))
            
            empresas = cur.fetchall()
            for empresa in empresas:
                row = self.company_table.rowCount()
                self.company_table.insertRow(row)
                self.company_table.setItem(row, 0, QTableWidgetItem(str(empresa['id'])))
                self.company_table.setItem(row, 1, QTableWidgetItem(empresa['razao_social']))
                self.company_table.setItem(row, 2, QTableWidgetItem(empresa['nome_fantasia']))
                self.company_table.setItem(row, 3, QTableWidgetItem(empresa['cnpj']))
        
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar empresas: {e}")
        finally:
            conn.close()

    def _load_company_for_edit(self, item):
        # (Função inalterada - Novos campos adicionados)
        row = item.row()
        company_id = int(self.company_table.item(row, 0).text())
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM empresas WHERE id = ?", (company_id,))
            data = cur.fetchone()
            if not data:
                QMessageBox.critical(self, "Erro", "Empresa não encontrada.")
                return

            self.clear_form()
            self.current_company_id = company_id
            self.form_title.setText(f"Editando Empresa: {data['nome_fantasia'] or data['razao_social']}")
            
            self.razao_social_input.setText(data['razao_social'])
            self.nome_fantasia_input.setText(data['nome_fantasia'])
            self.cnpj_input.setText(data['cnpj'])
            self.ie_input.setText(data['inscricao_estadual'])
            self.im_input.setText(data['inscricao_municipal'])
            self.regime_tributario_combo.setCurrentIndex(data['regime_tributario'] or 0)
            self.crt_combo.setCurrentIndex(data['crt'] - 1 if data['crt'] else 0)
            
            self.end_logradouro_input.setText(data['end_logradouro'])
            self.end_numero_input.setText(data['end_numero'])
            self.end_complemento_input.setText(data['end_complemento'])
            self.end_bairro_input.setText(data['end_bairro'])
            self.end_cep_input.setText(data['end_cep'])
            self.end_municipio_input.setText(data['end_municipio'])
            self.end_uf_input.setText(data['end_uf'])
            
            self.telefone_input.setText(data['telefone'])
            self.email_input.setText(data['email'])
            self.responsavel_input.setText(data['responsavel_legal'])
            self.cpf_responsavel_input.setText(data['cpf_responsavel'])
            
            self.certificado_path_input.setText(data['certificado_path'])
            self.csc_input.setText(data['csc'])
            self.csc_id_input.setText(data['csc_id'])
            self.csc_validade_input.setText(data['csc_validade']) 
            self.ambiente_combo.setCurrentIndex(0 if data['ambiente'] == 2 else 1)
            self.status_combo.setCurrentIndex(0 if data['status'] == 1 else 1) 
            
            self.certificado_validade_input.setText(data['certificado_validade'])
            self.notificar_venc_cert_check.setChecked(bool(data['notificar_venc_cert']))
            self.notificar_venc_dias_input.setValue(data['notificar_venc_dias'] or 30)
            
            self.btn_excluir.setEnabled(True)
            self.set_mode(1)
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar dados da empresa: {e}")
        finally:
            conn.close()

    def _validate_fields(self):
        # (Função inalterada)
        if not self.razao_social_input.text().strip():
            return False, "Razão Social"
        cnpj_limpo = self.cnpj_input.text().replace('.', '').replace('/', '').replace('-', '')
        if not cnpj_limpo or len(cnpj_limpo) != 14:
            return False, "CNPJ"
        return True, ""

    def save_company(self):
        # (Função inalterada - Novos campos adicionados)
        valido, campo = self._validate_fields()
        if not valido:
            QMessageBox.warning(self, "Campo Inválido", f"O campo '{campo}' é obrigatório ou inválido.")
            return

        data = {
            "razao_social": self.razao_social_input.text().strip(),
            "nome_fantasia": self.nome_fantasia_input.text().strip(),
            "cnpj": self.cnpj_input.text().strip(),
            "inscricao_estadual": self.ie_input.text().strip(),
            "inscricao_municipal": self.im_input.text().strip(),
            "regime_tributario": self.regime_tributario_combo.currentIndex(),
            "crt": self.crt_combo.currentIndex() + 1,
            "end_logradouro": self.end_logradouro_input.text().strip(),
            "end_numero": self.end_numero_input.text().strip(),
            "end_complemento": self.end_complemento_input.text().strip(),
            "end_bairro": self.end_bairro_input.text().strip(),
            "end_cep": self.end_cep_input.text().strip(),
            "end_municipio": self.end_municipio_input.text().strip(),
            "end_uf": self.end_uf_input.text().strip(),
            "telefone": self.telefone_input.text().strip(),
            "email": self.email_input.text().strip(),
            "responsavel_legal": self.responsavel_input.text().strip(),
            "cpf_responsavel": self.cpf_responsavel_input.text().strip(),
            "certificado_path": self.certificado_path_input.text().strip(),
            "csc": self.csc_input.text().strip(),
            "csc_id": self.csc_id_input.text().strip(),
            "csc_validade": self.csc_validade_input.text().strip(),
            "ambiente": 2 if self.ambiente_combo.currentIndex() == 0 else 1,
            "status": 1 if self.status_combo.currentIndex() == 0 else 2,
            "certificado_validade": self.certificado_validade_input.text().strip() or None, 
            "notificar_venc_cert": 1 if self.notificar_venc_cert_check.isChecked() else 0,
            "notificar_venc_dias": self.notificar_venc_dias_input.value()
        }
        
        if self.certificado_senha_input.text():
             data["certificado_senha"] = self.certificado_senha_input.text()

        conn = get_connection()
        try:
            cur = conn.cursor()
            if self.current_company_id:
                # UPDATE
                data["id"] = self.current_company_id
                
                fields_to_update = [f"{key} = :{key}" for key in data.keys() if key != 'id']
                query = f"UPDATE empresas SET {', '.join(fields_to_update)} WHERE id = :id"
                params = data
                msg = "Empresa atualizada com sucesso!"
            else:
                # INSERT
                fields = ", ".join(data.keys())
                placeholders = ", ".join([f":{k}" for k in data.keys()])
                query = f"INSERT INTO empresas ({fields}) VALUES ({placeholders})"
                params = data
                msg = "Empresa salva com sucesso!"
            
            cur.execute(query, params)
            conn.commit()
            QMessageBox.information(self, "Sucesso", msg)
            self.set_mode(0)

        except sqlite3.IntegrityError:
            QMessageBox.critical(self, "Erro", "Este CNPJ já existe no banco de dados.")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar empresa: {e}")
        finally:
            conn.close()
            
    def delete_company(self):
        # (Função inalterada)
        if not self.current_company_id:
            QMessageBox.warning(self, "Erro", "Nenhuma empresa selecionada.")
            return
        reply = QMessageBox.question(self, "Confirmação",
            "Atenção: Excluir esta empresa irá remover TODOS os locais de escrituração "
            "e terminais de caixa vinculados a ela.\n\n"
            "Tem certeza que deseja continuar?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No:
            return
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM empresas WHERE id = ?", (self.current_company_id,))
            conn.commit()
            QMessageBox.information(self, "Sucesso", "Empresa e seus dados vinculados foram excluídos.")
            self.set_mode(0)
        except sqlite3.IntegrityError as e:
             QMessageBox.critical(self, "Erro de Integridade", 
                "Não foi possível excluir esta empresa pois ela possui vendas associadas.\n"
                "Para excluir, primeiro remova os registros de vendas vinculados.")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao excluir empresa: {e}")
        finally:
            conn.close()

    # --- MÉTODOS ATUALIZADOS PARA A API INVERTEXTO ---

    def search_document(self):
        """Inicia a busca pelo CNPJ digitado."""
        if self.API_TOKEN == "COLE_SEU_TOKEN_AQUI":
            QMessageBox.critical(self, "Erro de API", 
                "O Token da API 'invertexto' não foi configurado no arquivo 'company_form.py'.")
            return
            
        cnpj = self.cnpj_input.text().strip().replace(".", "").replace("/", "").replace("-", "")
        if not cnpj:
            QMessageBox.warning(self, "Campo Vazio", "Digite um CNPJ no campo 'CNPJ' para buscar os dados.")
            return
        
        self._search_cnpj(cnpj)

    def _search_cnpj(self, cnpj):
        """Executa a busca do CNPJ na API invertexto."""
        if len(cnpj) != 14:
            QMessageBox.warning(self, "CNPJ Inválido", "O CNPJ deve conter 14 dígitos.")
            return

        try:
            # --- URL ATUALIZADA ---
            url = f"https://api.invertexto.com/v1/cnpj/{cnpj}?token={self.API_TOKEN}"
            response = requests.get(url, timeout=5) 
            response.raise_for_status() 
            
            data = response.json()
            if not data or data.get("status") == "erro":
                QMessageBox.warning(self, "Erro", f"API da invertexto retornou um erro: {data.get('message', 'CNPJ não encontrado')}")
                return

            nome = data.get("razao_social", "N/A")
            fantasia = data.get("nome_fantasia", "N/A")
            end = data.get("endereco", {}).get("logradouro", "")
            num = data.get("endereco", {}).get("numero", "")
            
            confirm_text = (
                f"<b>Empresa Encontrada:</b>\n"
                f"<b>Razão Social:</b> {nome}\n"
                f"<b>Nome Fantasia:</b> {fantasia}\n"
                f"<b>Endereço:</b> {end}, {num}\n\n"
                f"Deseja importar esses dados para o cadastro?"
            )
            
            reply = QMessageBox.question(self, "Confirmar Importação",
                                         confirm_text,
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

            if reply == QMessageBox.Yes:
                self._populate_form_with_cnpj_data(data)

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                QMessageBox.warning(self, "Não Encontrado", f"O CNPJ '{cnpj}' não foi encontrado na base de dados.")
            elif e.response.status_code == 401:
                QMessageBox.critical(self, "Erro de API", "Token da API 'invertexto' é inválido ou expirou.")
            else:
                QMessageBox.critical(self, "Erro de API", f"Erro ao consultar o CNPJ: {e}")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Rede", f"Não foi possível consultar o CNPJ (timeout?): {e}")

    def _populate_form_with_cnpj_data(self, data):
        """Preenche os campos do formulário com os dados da API."""
        
        self.razao_social_input.setText(data.get("razao_social", ""))
        self.nome_fantasia_input.setText(data.get("nome_fantasia", ""))
        self.ie_input.setText(data.get("ie", ""))
        
        # Regime Tributário
        simples = data.get("simples_nacional", {})
        if simples.get("optante_mei", False):
            self.regime_tributario_combo.setCurrentText("MEI")
            self.crt_combo.setCurrentIndex(0) # 1 – Simples Nacional
        elif simples.get("optante_simples", False):
            self.regime_tributario_combo.setCurrentText("Simples Nacional")
            self.crt_combo.setCurrentIndex(0) # 1 – Simples Nacional
        
        # Status
        if data.get("situacao_cadastral", "Inativa") == "Ativa":
            self.status_combo.setCurrentIndex(0) # 1 - Ativa
        else:
            self.status_combo.setCurrentIndex(1) # 2 - Inativa
        
        # Endereço
        end = data.get("endereco", {})
        self.end_logradouro_input.setText(end.get("logradouro", ""))
        self.end_numero_input.setText(end.get("numero", ""))
        self.end_complemento_input.setText(end.get("complemento", ""))
        self.end_bairro_input.setText(end.get("bairro", ""))
        cep = end.get("cep", "").replace(".", "")
        self.end_cep_input.setText(cep)
        self.end_municipio_input.setText(end.get("cidade", ""))
        self.end_uf_input.setText(end.get("uf", ""))
        
        # Contato
        self.telefone_input.setText(data.get("telefone", ""))
        self.email_input.setText(data.get("email", ""))
        
        # Foca na próxima aba
        self.tabs.setCurrentIndex(1)