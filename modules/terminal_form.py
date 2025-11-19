# modules/terminal_form.py
import sqlite3
import socket 
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QGridLayout, QFrame, QTableWidget, QHeaderView, 
    QTableWidgetItem, QAbstractItemView, QStackedWidget, QComboBox,
    QCheckBox, QFileDialog, QTabWidget, QSpinBox
)
from PyQt5.QtCore import Qt
from database.db import get_connection

class TerminalForm(QWidget):
    """
    Formulário para CRUD de Terminais de Caixa (PDV).
    """
    def __init__(self, user_id, **kwargs):
        super().__init__()
        self.user_id = user_id
        self.current_terminal_id = None
        self.setWindowTitle("Cadastro de Terminais (PDV)")
        
        self.company_map = {} # {id_empresa: sqlite3.Row}
        self.location_map = {} # {id_local: (nome_local, empresa_id, cnpj)}
        self.deposito_map = {}   # {id: nome}
        self.contas_map = {}     # {id: nome}
        
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
            QLineEdit[readOnly=true] { background-color: #f0f0f0; }
            QCheckBox { border: none; }
            QPushButton {
                background-color: #0078d7; color: white; border-radius: 6px;
                padding: 8px 15px; font-weight: bold;
            }
            QPushButton:hover { background-color: #005fa3; }
            QPushButton#deleteButton { background-color: #e74c3c; }
            QPushButton#deleteButton:hover { background-color: #c0392b; }
            QPushButton#btn_detect_host {
                background-color: #f39c12;
                padding: 6px 10px;
                font-size: 12px;
            }
            QPushButton#btn_detect_host:hover { background-color: #e67e22; }
        """)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        
        self.search_panel = QWidget()
        search_layout = QHBoxLayout(self.search_panel)
        search_layout.setContentsMargins(0, 10, 0, 10)
        self.btn_novo = QPushButton("Novo Terminal")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Pesquisar por Nome do Terminal...")
        self.btn_pesquisar = QPushButton("Pesquisar")
        
        search_layout.addWidget(self.btn_novo)
        search_layout.addStretch()
        search_layout.addWidget(self.search_input, 1) 
        search_layout.addWidget(self.btn_pesquisar)
        
        self.stack = QStackedWidget()
        
        self.table_widget = QWidget()
        table_layout = QVBoxLayout(self.table_widget)
        table_layout.setContentsMargins(0,0,0,0)
        self.terminal_table = QTableWidget()
        self.terminal_table.setColumnCount(5)
        self.terminal_table.setHorizontalHeaderLabels(["ID", "Nome do Terminal", "Tipo", "Local de Escrituração", "CNPJ Base"])
        self.terminal_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.terminal_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.terminal_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.terminal_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.terminal_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.terminal_table.setColumnHidden(0, True)
        table_layout.addWidget(self.terminal_table)
        
        self.form_panel = QFrame()
        self.form_panel.setObjectName("form_panel")
        form_layout = QVBoxLayout(self.form_panel)
        self.form_title = QLabel("Cadastro de Terminal (PDV)", objectName="form_title")
        form_layout.addWidget(self.form_title)
        
        self.empresa_combo = QComboBox()
        self.local_combo = QComboBox()
        self.lbl_cnpj_vinculo = QLineEdit() 
        self.lbl_cnpj_vinculo.setReadOnly(True)
        self.lbl_cnpj_vinculo.setPlaceholderText("CNPJ do Local de Escrituração")
        
        self.deposito_combo = QComboBox()
        
        # --- CAMPOS FINANCEIROS ATUALIZADOS ---
        self.conta_pdv_combo = QComboBox()
        # self.conta_cofre_combo foi removido
        self.conta_dest_dinheiro_combo = QComboBox()
        self.conta_dest_cartao_combo = QComboBox()
        self.conta_dest_pix_combo = QComboBox()
        self.conta_dest_outros_combo = QComboBox()
        # --- FIM DA ATUALIZAÇÃO ---
        
        self.nome_terminal_input = QLineEdit()
        self.codigo_interno_input = QLineEdit()
        self.tipo_terminal_combo = QComboBox()
        self.tipo_terminal_combo.addItems(["PDV (Caixa de Venda)", "Pré-Venda", "Servidor de Pré-Venda"])
        self.modo_operacao_combo = QComboBox()
        self.modo_operacao_combo.addItems(["Local", "Online", "Híbrido"])
        self.status_combo = QComboBox()
        self.status_combo.addItems(["1 - Ativo", "2 - Inativo"])
        
        self.hostname_input = QLineEdit()
        self.hostname_input.setPlaceholderText("Ex: DESKTOP-CAIXA1")
        self.btn_detect_host = QPushButton("Detectar Esta Máquina")
        self.btn_detect_host.setObjectName("btn_detect_host")
        
        self.servidor_prevenda_input = QLineEdit()
        
        self.habilita_nao_fiscal_check = QCheckBox("Habilitar Vendas Não-Fiscais (F9)")
        self.habilita_nao_fiscal_check.setChecked(True)
        
        self.serie_fiscal_input = QSpinBox()
        self.serie_fiscal_input.setRange(1, 999)
        self.proximo_numero_venda_input = QSpinBox()
        self.proximo_numero_venda_input.setRange(1, 999999999)
        
        self.lbl_ambiente_herdado = QLineEdit(readOnly=True)
        self.lbl_ambiente_herdado.setText("Herdado (Homologação)")
        self.lbl_csc_herdado = QLineEdit(readOnly=True)
        self.lbl_csc_herdado.setPlaceholderText("(Herdado do Local)")
        
        self.impressora_nome_input = QLineEdit()
        self.impressora_modelo_input = QLineEdit()
        self.impressora_porta_input = QLineEdit()
        self.impressora_porta_input.setPlaceholderText("Ex: COM3, USB001, 192.168.0.50:9100")
        self.impressora_tipo_combo = QComboBox()
        self.impressora_tipo_combo.addItems(["USB", "Serial", "IP", "Bluetooth"])
        self.impressora_largura_combo = QComboBox()
        self.impressora_largura_combo.addItems(["80mm", "58mm"])
        
        self.tabs = QTabWidget()
        tab_geral = QWidget()
        tab_fiscal = QWidget()
        tab_impressora = QWidget()
        
        self.tabs.addTab(tab_geral, "Geral e Vínculos")
        self.tabs.addTab(tab_fiscal, "Configuração Fiscal (NFC-e)")
        self.tabs.addTab(tab_impressora, "Impressora")
        form_layout.addWidget(self.tabs)
        
        # --- Layout Aba Geral (ATUALIZADO) ---
        layout_geral = QGridLayout(tab_geral)
        layout_geral.addWidget(QLabel("Empresa (Matriz): *", objectName="required"), 0, 0)
        layout_geral.addWidget(self.empresa_combo, 0, 1)
        
        layout_geral.addWidget(QLabel("Local de Escrituração: *", objectName="required"), 1, 0)
        layout_geral.addWidget(self.local_combo, 1, 1)
        
        layout_geral.addWidget(QLabel("CNPJ de Vínculo (Loja):"), 2, 0)
        layout_geral.addWidget(self.lbl_cnpj_vinculo, 2, 1)
        
        layout_geral.addWidget(QLabel("Depósito Padrão (Estoque): *", objectName="required"), 3, 0)
        layout_geral.addWidget(self.deposito_combo, 3, 1)
        
        line_fin = QFrame(); line_fin.setFrameShape(QFrame.HLine); line_fin.setFrameShadow(QFrame.Sunken)
        layout_geral.addWidget(line_fin, 4, 0, 1, 2)
        
        # --- NOVOS CAMPOS FINANCEIROS ---
        layout_geral.addWidget(QLabel("Conta Financeira (PDV): *", objectName="required"), 5, 0)
        layout_geral.addWidget(self.conta_pdv_combo, 5, 1)
        layout_geral.addWidget(QLabel("Destino Dinheiro: *", objectName="required"), 6, 0)
        layout_geral.addWidget(self.conta_dest_dinheiro_combo, 6, 1)
        layout_geral.addWidget(QLabel("Destino Cartão: *", objectName="required"), 7, 0)
        layout_geral.addWidget(self.conta_dest_cartao_combo, 7, 1)
        layout_geral.addWidget(QLabel("Destino PIX: *", objectName="required"), 8, 0)
        layout_geral.addWidget(self.conta_dest_pix_combo, 8, 1)
        layout_geral.addWidget(QLabel("Destino Outros: *", objectName="required"), 9, 0)
        layout_geral.addWidget(self.conta_dest_outros_combo, 9, 1)
        # --- FIM DAS ADIÇÕES ---
        
        line = QFrame(); line.setFrameShape(QFrame.HLine); line.setFrameShadow(QFrame.Sunken)
        layout_geral.addWidget(line, 10, 0, 1, 2) # Index 10

        layout_geral.addWidget(QLabel("Nome do Terminal: *", objectName="required"), 11, 0)
        layout_geral.addWidget(self.nome_terminal_input, 11, 1)
        
        hostname_layout = QHBoxLayout()
        hostname_layout.setContentsMargins(0,0,0,0)
        hostname_layout.addWidget(self.hostname_input, 1)
        hostname_layout.addWidget(self.btn_detect_host)
        layout_geral.addWidget(QLabel("Vincular à Máquina (Hostname): *"), 12, 0)
        layout_geral.addLayout(hostname_layout, 12, 1)

        layout_geral.addWidget(QLabel("Código Interno:"), 13, 0)
        layout_geral.addWidget(self.codigo_interno_input, 13, 1)
        layout_geral.addWidget(QLabel("Tipo de Terminal:"), 14, 0)
        layout_geral.addWidget(self.tipo_terminal_combo, 14, 1)
        layout_geral.addWidget(QLabel("Modo de Operação:"), 15, 0)
        layout_geral.addWidget(self.modo_operacao_combo, 15, 1)
        layout_geral.addWidget(QLabel("IP Servidor Pré-Venda:"), 16, 0)
        layout_geral.addWidget(self.servidor_prevenda_input, 16, 1)
        layout_geral.addWidget(QLabel("Status:"), 17, 0)
        layout_geral.addWidget(self.status_combo, 17, 1)
        
        layout_geral.addWidget(self.habilita_nao_fiscal_check, 18, 1)
        
        layout_geral.setColumnStretch(1, 1)
        layout_geral.setRowStretch(19, 1) # Index 19
        
        # --- Abas Fiscais e Impressora (Inalteradas) ---
        layout_fiscal = QGridLayout(tab_fiscal)
        layout_fiscal.addWidget(QLabel("Série Fiscal (NFC-e):"), 0, 0)
        layout_fiscal.addWidget(self.serie_fiscal_input, 0, 1)
        layout_fiscal.addWidget(QLabel("Próximo Nº NFC-e:"), 1, 0)
        layout_fiscal.addWidget(self.proximo_numero_venda_input, 1, 1)
        layout_fiscal.addWidget(QLabel("Ambiente Emissão:"), 0, 2)
        layout_fiscal.addWidget(self.lbl_ambiente_herdado, 0, 3) 
        layout_fiscal.addWidget(QLabel("CSC (Herdado do Local):"), 1, 2)
        layout_fiscal.addWidget(self.lbl_csc_herdado, 1, 3)
        layout_fiscal.setColumnStretch(1, 1)
        layout_fiscal.setColumnStretch(3, 1)
        layout_fiscal.setRowStretch(4, 1)
        
        layout_imp = QGridLayout(tab_impressora)
        layout_imp.addWidget(QLabel("Nome da Impressora:"), 0, 0)
        layout_imp.addWidget(self.impressora_nome_input, 0, 1)
        layout_imp.addWidget(QLabel("Modelo:"), 1, 0)
        layout_imp.addWidget(self.impressora_modelo_input, 1, 1)
        layout_imp.addWidget(QLabel("Tipo de Conexão:"), 2, 0)
        layout_imp.addWidget(self.impressora_tipo_combo, 2, 1)
        layout_imp.addWidget(QLabel("Endereço/Porta:"), 3, 0)
        layout_imp.addWidget(self.impressora_porta_input, 3, 1)
        layout_imp.addWidget(QLabel("Largura do Papel:"), 4, 0)
        layout_imp.addWidget(self.impressora_largura_combo, 4, 1)
        layout_imp.setColumnStretch(1, 1)
        layout_imp.setRowStretch(5, 1)
        
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
        if mode == 0:
            self.stack.setCurrentIndex(0)
            self.search_panel.setVisible(True)
            self.load_terminals() 
        else:
            self._load_empresas_combobox() 
            self.stack.setCurrentIndex(1)
            self.search_panel.setVisible(False)

    def _connect_signals(self):
        self.btn_novo.clicked.connect(self.show_new_form)
        self.btn_salvar.clicked.connect(self.save_terminal)
        self.btn_excluir.clicked.connect(self.delete_terminal)
        self.btn_cancelar.clicked.connect(self.cancel_action)
        self.btn_pesquisar.clicked.connect(self.load_terminals)
        self.search_input.returnPressed.connect(self.load_terminals)
        self.terminal_table.itemDoubleClicked.connect(self._load_terminal_for_edit)
        
        self.empresa_combo.currentIndexChanged.connect(self._on_empresa_changed)
        self.local_combo.currentIndexChanged.connect(self._on_local_changed)
        self.btn_detect_host.clicked.connect(self._detect_hostname)

    def _detect_hostname(self):
        try:
            hostname = socket.gethostname()
            self.hostname_input.setText(hostname)
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível detectar o hostname: {e}")

    def _load_empresas_combobox(self):
        self.empresa_combo.clear()
        self.company_map.clear()
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, razao_social, cnpj FROM empresas WHERE status = 1 ORDER BY razao_social")
            empresas = cur.fetchall()
            
            self.empresa_combo.addItem("Selecione uma empresa...", None)
            if not empresas:
                self.empresa_combo.setEnabled(False)
                return

            self.empresa_combo.setEnabled(True)
            for empresa in empresas:
                self.empresa_combo.addItem(empresa['razao_social'], empresa['id'])
                self.company_map[empresa['id']] = empresa 
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar empresas: {e}")
        finally:
            conn.close()

    # --- MÉTODO ATUALIZADO ---
    def _on_empresa_changed(self, index):
        self.local_combo.clear()
        self.deposito_combo.clear()
        self.conta_pdv_combo.clear()
        self.conta_dest_dinheiro_combo.clear()
        self.conta_dest_cartao_combo.clear()
        self.conta_dest_pix_combo.clear()
        self.conta_dest_outros_combo.clear()
        
        self.location_map.clear()
        self.deposito_map.clear()
        self.contas_map.clear()
        
        self.lbl_ambiente_herdado.setText("(Selecione um local)")
        self.lbl_csc_herdado.clear()
        
        empresa_id = self.empresa_combo.itemData(index)
        if empresa_id is None:
            self.local_combo.addItem("Selecione uma empresa", None)
            self.deposito_combo.addItem("Selecione uma empresa", None)
            self.conta_pdv_combo.addItem("Selecione uma empresa", None)
            self.conta_dest_dinheiro_combo.addItem("Selecione uma empresa", None)
            self.conta_dest_cartao_combo.addItem("Selecione uma empresa", None)
            self.conta_dest_pix_combo.addItem("Selecione uma empresa", None)
            self.conta_dest_outros_combo.addItem("Selecione uma empresa", None)
            
            self.local_combo.setEnabled(False)
            self.deposito_combo.setEnabled(False)
            self.conta_pdv_combo.setEnabled(False)
            self.conta_dest_dinheiro_combo.setEnabled(False)
            self.conta_dest_cartao_combo.setEnabled(False)
            self.conta_dest_pix_combo.setEnabled(False)
            self.conta_dest_outros_combo.setEnabled(False)
            return

        self._load_locais_combobox(empresa_id)
        self._load_depositos_combobox(empresa_id)
        self._load_contas_financeiras_combobox(empresa_id)

    def _load_locais_combobox(self, empresa_id):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, nome_local, empresa_id, cnpj FROM locais_escrituracao WHERE empresa_id = ? AND status = 1 ORDER BY nome_local", (empresa_id,))
            locais = cur.fetchall()
            
            self.local_combo.addItem("Selecione um local...", None)
            if not locais:
                self.local_combo.setEnabled(False)
                return
                
            self.local_combo.setEnabled(True)
            for local in locais:
                self.local_combo.addItem(local['nome_local'], local['id'])
                self.location_map[local['id']] = (local['nome_local'], local['empresa_id'], local['cnpj'])
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar locais de escrituração: {e}")
        finally:
            conn.close()

    def _load_depositos_combobox(self, empresa_id):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, nome FROM depositos WHERE empresa_id = ? ORDER BY nome", (empresa_id,))
            depositos = cur.fetchall()
            
            self.deposito_combo.addItem("Selecione um depósito...", None)
            if not depositos:
                self.deposito_combo.setEnabled(False)
                return
                
            self.deposito_combo.setEnabled(True)
            for dep in depositos:
                self.deposito_combo.addItem(dep['nome'], dep['id'])
                self.deposito_map[dep['id']] = dep['nome']
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar depósitos: {e}")
        finally:
            conn.close()
    
    # --- MÉTODO ATUALIZADO ---
    def _load_contas_financeiras_combobox(self, empresa_id):
        """Carrega os combos de contas financeiras (PDV e Cofre)."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, nome, tipo, permite_transferencia_pdv FROM contas_financeiras WHERE empresa_id = ? AND active = 1 ORDER BY nome", (empresa_id,))
            contas = cur.fetchall()
            
            # Limpa todos os combos
            combos = [
                self.conta_pdv_combo, self.conta_dest_dinheiro_combo, 
                self.conta_dest_cartao_combo, self.conta_dest_pix_combo, 
                self.conta_dest_outros_combo
            ]
            for combo in combos:
                combo.clear()
                combo.addItem("Selecione...", None)
            
            self.contas_map.clear()
            
            if not contas:
                for combo in combos: combo.setEnabled(False)
                return
                
            for combo in combos: combo.setEnabled(True)
            
            for conta in contas:
                self.contas_map[conta['id']] = conta['nome']
                
                # Conta PDV (só pode ser do tipo PDV)
                if conta['tipo'] == "PDV / Caixa Operador":
                    self.conta_pdv_combo.addItem(conta['nome'], conta['id'])
                    
                # Contas Destino (podem ser Cofre, Banco, Carteiras, etc.)
                if conta['permite_transferencia_pdv'] == 1:
                    label = f"{conta['nome']} ({conta['tipo']})"
                    self.conta_dest_dinheiro_combo.addItem(label, conta['id'])
                    self.conta_dest_cartao_combo.addItem(label, conta['id'])
                    self.conta_dest_pix_combo.addItem(label, conta['id'])
                    self.conta_dest_outros_combo.addItem(label, conta['id'])

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar contas financeiras: {e}")
        finally:
            conn.close()
    
    def _on_local_changed(self, index):
        local_id = self.local_combo.itemData(index)
        self.lbl_cnpj_vinculo.clear()
        
        if local_id is None:
            return
            
        local_info = self.location_map.get(local_id)
        if local_info:
            local_cnpj = local_info[2]
            if local_cnpj:
                 self.lbl_cnpj_vinculo.setText(local_cnpj)
            else:
                empresa_id = local_info[1]
                empresa_data = self.company_map.get(empresa_id)
                if empresa_data and empresa_data['cnpj']:
                     self.lbl_cnpj_vinculo.setText(empresa_data['cnpj'])
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM locais_escrituracao WHERE id = ?", (local_id,))
            local_data = cur.fetchone()
            
            if not local_data: return
                
            if local_data['herdar_config_empresa']:
                cur.execute("SELECT ambiente, csc, csc_id FROM empresas WHERE id = ?", (local_data['empresa_id'],))
                data = cur.fetchone()
            else:
                data = local_data
                
            ambiente_txt = "Produção" if data['ambiente'] == 1 else "Homologação"
            self.lbl_ambiente_herdado.setText(f"Herdado ({ambiente_txt})")
            self.lbl_csc_herdado.setText(f"{data['csc']} (ID: {data['csc_id']})")
            
        except Exception as e:
             QMessageBox.critical(self, "Erro", f"Erro ao carregar dados fiscais do local: {e}")
        finally:
            conn.close()

    def show_new_form(self):
        self.clear_form()
        self.set_mode(1) 
        self.nome_terminal_input.setFocus()
        self.form_title.setText("Novo Terminal (PDV)")

    def cancel_action(self):
        self.clear_form()
        self.set_mode(0) 

    def clear_form(self):
        self.current_terminal_id = None
        self.empresa_combo.setCurrentIndex(0)
        self.local_combo.clear()
        self.lbl_cnpj_vinculo.clear()
        self.deposito_combo.clear()
        
        # --- NOVO ---
        self.conta_pdv_combo.clear()
        self.conta_dest_dinheiro_combo.clear()
        self.conta_dest_cartao_combo.clear()
        self.conta_dest_pix_combo.clear()
        self.conta_dest_outros_combo.clear()
        
        self.nome_terminal_input.clear()
        self.codigo_interno_input.clear()
        self.hostname_input.clear()
        self.tipo_terminal_combo.setCurrentIndex(0)
        self.modo_operacao_combo.setCurrentIndex(0)
        self.servidor_prevenda_input.clear()
        self.status_combo.setCurrentIndex(0)
        self.habilita_nao_fiscal_check.setChecked(True)
        
        self.serie_fiscal_input.setValue(1)
        self.proximo_numero_venda_input.setValue(1)
        
        self.impressora_nome_input.clear()
        self.impressora_modelo_input.clear()
        self.impressora_porta_input.clear()
        self.impressora_tipo_combo.setCurrentIndex(0)
        self.impressora_largura_combo.setCurrentIndex(0)
        
        self.lbl_ambiente_herdado.setText("(Selecione um local)")
        self.lbl_csc_herdado.clear()
        
        self.btn_excluir.setEnabled(False)
        self.form_title.setText("Cadastro de Terminal (PDV)")

    def load_terminals(self):
        self.terminal_table.setRowCount(0)
        search_term = self.search_input.text().strip()
        
        conn = get_connection()
        try:
            if not self.company_map: self._load_empresas_combobox()
            
            cur_loc = conn.cursor()
            cur_loc.execute("SELECT id, nome_local, empresa_id, cnpj FROM locais_escrituracao")
            all_locations = cur_loc.fetchall()
            self.location_map = {loc['id']: (loc['nome_local'], loc['empresa_id'], loc['cnpj']) for loc in all_locations}
            
            cur = conn.cursor()
            query = "SELECT id, nome_terminal, tipo_terminal, local_id FROM terminais_pdv"
            params = []
            
            if search_term:
                query += " WHERE (nome_terminal LIKE ?)"
                params.append(f"%{search_term}%")
            
            query += " ORDER BY nome_terminal"
            cur.execute(query, tuple(params))
            
            rows = cur.fetchall()
            for row in rows:
                idx = self.terminal_table.rowCount()
                self.terminal_table.insertRow(idx)
                
                local_id = row['local_id']
                local_info = self.location_map.get(local_id, ("-", None, None))
                local_nome = local_info[0]
                empresa_id = local_info[1]
                local_cnpj = local_info[2]
                
                empresa_data = self.company_map.get(empresa_id)
                empresa_nome = empresa_data['razao_social'] if empresa_data else "-"
                empresa_cnpj = empresa_data['cnpj'] if empresa_data else "-"
                
                tipo_map = {1: "PDV (Caixa)", 2: "Pré-Venda", 3: "Servidor"}
                tipo_terminal_txt = tipo_map.get(row['tipo_terminal'], "Desconhecido")
                
                self.terminal_table.setItem(idx, 0, QTableWidgetItem(str(row['id'])))
                self.terminal_table.setItem(idx, 1, QTableWidgetItem(row['nome_terminal']))
                self.terminal_table.setItem(idx, 2, QTableWidgetItem(tipo_terminal_txt))
                self.terminal_table.setItem(idx, 3, QTableWidgetItem(local_nome))
                self.terminal_table.setItem(idx, 4, QTableWidgetItem(local_cnpj or empresa_cnpj))
        
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar terminais: {e}")
        finally:
            conn.close()

    def _load_terminal_for_edit(self, item):
        row = item.row()
        terminal_id = int(self.terminal_table.item(row, 0).text())
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM terminais_pdv WHERE id = ?", (terminal_id,))
            data = cur.fetchone()
            if not data:
                QMessageBox.critical(self, "Erro", "Terminal não encontrado.")
                return

            self.clear_form()
            self._load_empresas_combobox()
            self.set_mode(1) 
            
            self.current_terminal_id = terminal_id
            self.form_title.setText(f"Editando Terminal: {data['nome_terminal']}")
            
            empresa_id = data['empresa_id']
            if empresa_id:
                index_empresa = self.empresa_combo.findData(empresa_id)
                if index_empresa >= 0:
                    self.empresa_combo.setCurrentIndex(index_empresa)
                    # _on_empresa_changed é chamado, carregando locais, depósitos e contas
            
            local_id = data['local_id']
            index_local = self.local_combo.findData(local_id)
            if index_local >= 0:
                self.local_combo.setCurrentIndex(index_local)

            deposito_id = data['deposito_id_padrao']
            index_dep = self.deposito_combo.findData(deposito_id)
            if index_dep >= 0:
                self.deposito_combo.setCurrentIndex(index_dep)
                
            # --- NOVO: Carrega Contas Financeiras ---
            conta_pdv_id = data['conta_financeira_id']
            index_pdv = self.conta_pdv_combo.findData(conta_pdv_id)
            if index_pdv >= 0:
                self.conta_pdv_combo.setCurrentIndex(index_pdv)

            # Carrega os 4 destinos
            conta_dest_dinheiro_id = data['conta_destino_dinheiro_id']
            index_din = self.conta_dest_dinheiro_combo.findData(conta_dest_dinheiro_id)
            if index_din >= 0:
                self.conta_dest_dinheiro_combo.setCurrentIndex(index_din)

            conta_dest_cartao_id = data['conta_destino_cartao_id']
            index_car = self.conta_dest_cartao_combo.findData(conta_dest_cartao_id)
            if index_car >= 0:
                self.conta_dest_cartao_combo.setCurrentIndex(index_car)
                
            conta_dest_pix_id = data['conta_destino_pix_id']
            index_pix = self.conta_dest_pix_combo.findData(conta_dest_pix_id)
            if index_pix >= 0:
                self.conta_dest_pix_combo.setCurrentIndex(index_pix)
                
            conta_dest_outros_id = data['conta_destino_outros_id']
            index_out = self.conta_dest_outros_combo.findData(conta_dest_outros_id)
            if index_out >= 0:
                self.conta_dest_outros_combo.setCurrentIndex(index_out)
            # --- FIM NOVO ---
            
            # Aba Geral
            self.nome_terminal_input.setText(data['nome_terminal'])
            self.hostname_input.setText(data['hostname'])
            self.codigo_interno_input.setText(data['codigo_interno'])
            self.tipo_terminal_combo.setCurrentIndex(data['tipo_terminal'] - 1 if data['tipo_terminal'] else 0)
            self.modo_operacao_combo.setCurrentIndex(data['modo_operacao'] - 1 if data['modo_operacao'] else 0)
            self.servidor_prevenda_input.setText(data['servidor_pre_venda'])
            self.status_combo.setCurrentIndex(0 if data['status'] == 1 else 1)
            self.habilita_nao_fiscal_check.setChecked(bool(data['habilita_nao_fiscal']))
            
            # Aba Fiscal
            self.serie_fiscal_input.setValue(data['serie_fiscal'] or 1)
            self.proximo_numero_venda_input.setValue(data['numero_nfe_atual'] or 1)
            
            # Aba Impressora
            self.impressora_nome_input.setText(data['impressora_nome'])
            self.impressora_modelo_input.setText(data['impressora_modelo'])
            self.impressora_porta_input.setText(data['impressora_endereco_conexao'])
            self.impressora_tipo_combo.setCurrentIndex(data['impressora_tipo_conexao'] - 1 if data['impressora_tipo_conexao'] else 0)
            self.impressora_largura_combo.setCurrentIndex(0 if data['impressora_largura_papel'] == 80 else 1)
            
            self.btn_excluir.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar dados do terminal: {e}")
        finally:
            conn.close()

    def _validate_fields(self):
        if self.empresa_combo.currentData() is None:
            return False, "Empresa (Matriz)"
        if self.local_combo.currentData() is None:
            return False, "Local de Escrituração"
        if not self.lbl_cnpj_vinculo.text().strip():
             return False, "CNPJ de Vínculo (Loja)"
        if self.deposito_combo.currentData() is None:
            return False, "Depósito Padrão"
        # --- NOVO ---
        if self.conta_pdv_combo.currentData() is None:
            return False, "Conta Financeira (PDV)"
        if self.conta_dest_dinheiro_combo.currentData() is None:
            return False, "Conta Destino (Dinheiro)"
        if self.conta_dest_cartao_combo.currentData() is None:
            return False, "Conta Destino (Cartão)"
        if self.conta_dest_pix_combo.currentData() is None:
            return False, "Conta Destino (PIX)"
        if self.conta_dest_outros_combo.currentData() is None:
            return False, "Conta Destino (Outros)"
        # --- FIM NOVO ---
        if not self.nome_terminal_input.text().strip():
            return False, "Nome do Terminal"
        if not self.hostname_input.text().strip():
            return False, "Hostname"
        return True, ""

    def save_terminal(self):
        valido, campo = self._validate_fields()
        if not valido:
            QMessageBox.warning(self, "Campo Obrigatório", f"O campo '{campo}' é obrigatório.")
            return

        local_id = self.local_combo.currentData()
        empresa_id = self.empresa_combo.currentData()
        
        data = {
            "local_id": local_id,
            "empresa_id": empresa_id,
            "deposito_id_padrao": self.deposito_combo.currentData(),
            
            # --- NOVOS CAMPOS ---
            "conta_financeira_id": self.conta_pdv_combo.currentData(),
            "conta_destino_dinheiro_id": self.conta_dest_dinheiro_combo.currentData(),
            "conta_destino_cartao_id": self.conta_dest_cartao_combo.currentData(),
            "conta_destino_pix_id": self.conta_dest_pix_combo.currentData(),
            "conta_destino_outros_id": self.conta_dest_outros_combo.currentData(),
            # --- FIM NOVO ---
            
            "nome_terminal": self.nome_terminal_input.text().strip(),
            "hostname": self.hostname_input.text().strip(),
            "codigo_interno": self.codigo_interno_input.text().strip(),
            "tipo_terminal": self.tipo_terminal_combo.currentIndex() + 1,
            "modo_operacao": self.modo_operacao_combo.currentIndex() + 1,
            "servidor_pre_venda": self.servidor_prevenda_input.text().strip(),
            "status": 1 if self.status_combo.currentIndex() == 0 else 2,
            "habilita_nao_fiscal": 1 if self.habilita_nao_fiscal_check.isChecked() else 0,
            
            "serie_fiscal": self.serie_fiscal_input.value(),
            "numero_nfe_atual": self.proximo_numero_venda_input.value(),
            
            "impressora_nome": self.impressora_nome_input.text().strip(),
            "impressora_modelo": self.impressora_modelo_input.text().strip(),
            "impressora_endereco_conexao": self.impressora_porta_input.text().strip(),
            "impressora_tipo_conexao": self.impressora_tipo_combo.currentIndex() + 1,
            "impressora_largura_papel": 80 if self.impressora_largura_combo.currentIndex() == 0 else 58,
        }
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            if self.current_terminal_id:
                # UPDATE
                data["id"] = self.current_terminal_id
                fields_to_update = [f"{key} = :{key}" for key in data.keys() if key != 'id']
                query = f"UPDATE terminais_pdv SET {', '.join(fields_to_update)} WHERE id = :id"
                params = data
                msg = "Terminal atualizado com sucesso!"
            else:
                # INSERT
                fields = ", ".join(data.keys())
                placeholders = ", ".join([f":{k}" for k in data.keys()])
                query = f"INSERT INTO terminais_pdv ({fields}) VALUES ({placeholders})"
                params = data
                msg = "Terminal salvo com sucesso!"
            
            cur.execute(query, params)
            conn.commit()
            QMessageBox.information(self, "Sucesso", msg)
            self.set_mode(0)

        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed: terminais_pdv.hostname" in str(e):
                QMessageBox.critical(self, "Erro", "Este Hostname (Nome da Máquina) já está em uso por outro terminal.")
            else:
                QMessageBox.critical(self, "Erro", f"Erro de integridade: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar terminal: {e}")
        finally:
            conn.close()
            
    def delete_terminal(self):
        # (Inalterado)
        if not self.current_terminal_id:
            QMessageBox.warning(self, "Erro", "Nenhum terminal selecionado.")
            return

        reply = QMessageBox.question(self, "Confirmação",
            "Atenção: Excluir este terminal é irreversível e pode afetar relatórios de vendas passadas.\n\n"
            "Tem certeza que deseja continuar?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
        if reply == QMessageBox.No:
            return
            
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM terminais_pdv WHERE id = ?", (self.current_terminal_id,))
            conn.commit()
            QMessageBox.information(self, "Sucesso", "Terminal excluído com sucesso.")
            self.set_mode(0)
        except sqlite3.IntegrityError as e:
             QMessageBox.critical(self, "Erro de Integridade", 
                "Não foi possível excluir este terminal pois ele possui vendas ou sessões de caixa associadas.\n")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao excluir terminal: {e}")
        finally:
            conn.close()