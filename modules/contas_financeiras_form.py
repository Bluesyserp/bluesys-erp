# -*- coding: utf-8 -*-
# modules/contas_financeiras_form.py
import sqlite3
import logging # <-- NOVO
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QGridLayout, QFrame, QTableWidget, QHeaderView, 
    QTableWidgetItem, QAbstractItemView, QStackedWidget, QComboBox,
    QCheckBox
)
from PyQt5.QtCore import Qt
from database.db import get_connection

class ContasFinanceirasForm(QWidget):
    """
    Formulário para CRUD de Contas Financeiras (Disponíveis).
    Req. #1 do Módulo Financeiro.
    """
    def __init__(self, user_id, **kwargs):
        super().__init__()
        self.user_id = user_id
        self.current_conta_id = None
        self.setWindowTitle("Cadastro de Contas Financeiras (Disponíveis)")
        
        # --- NOVO: Logger ---
        self.logger = logging.getLogger(__name__)
        
        self.company_map = {} # {id_empresa: razao_social}
        
        # Tipos de conta baseados na sua especificação
        self.tipos_conta = [
            "PDV / Caixa Operador",
            "Cofre da loja",
            "Conta Bancária",
            "Carteira de Cartões",
            "Carteira PIX",
            "Carteira Digital",
            "Vale / Adiantamentos",
            "Devedores Diversos",
            "Credores Diversos"
        ]
        
        self._setup_styles()
        self._build_ui()
        self._connect_signals()
        
        self.set_mode(0) # Começa na lista

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
            
            QLineEdit, QComboBox, QTextEdit, QDoubleSpinBox {
                border: 1px solid #c0c0d0; border-radius: 5px; 
                padding: 6px; background-color: white; font-size: 13px;
            }
            QCheckBox { border: none; padding: 6px 0px; }
            QPushButton {
                background-color: #0078d7; color: white; border-radius: 6px;
                padding: 8px 15px; font-weight: bold;
            }
            QPushButton:hover { background-color: #005fa3; }
            QPushButton#deleteButton { background-color: #e74c3c; }
            QPushButton#deleteButton:hover { background-color: #c0392b; }
            QPushButton#cancelButton { background-color: #95A5A6; }
            QPushButton#cancelButton:hover { background-color: #7F8C8D; }
        """)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        
        # --- 1. PAINEL DE BUSCA E NAVEGAÇÃO ---
        self.search_panel = QWidget()
        search_layout = QHBoxLayout(self.search_panel)
        search_layout.setContentsMargins(0, 10, 0, 10)
        self.btn_novo = QPushButton("Nova Conta")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Pesquisar por Nome da Conta...")
        self.btn_pesquisar = QPushButton("Pesquisar")
        
        search_layout.addWidget(self.btn_novo)
        search_layout.addStretch()
        search_layout.addWidget(self.search_input, 1) 
        search_layout.addWidget(self.btn_pesquisar)
        
        # --- 2. STACKED WIDGET (Tabela / Formulário) ---
        self.stack = QStackedWidget()
        
        # --- Tela 0: Tabela de Contas ---
        self.table_widget = QWidget()
        table_layout = QVBoxLayout(self.table_widget)
        table_layout.setContentsMargins(0,0,0,0)
        self.contas_table = QTableWidget()
        self.contas_table.setColumnCount(5)
        self.contas_table.setHorizontalHeaderLabels(["ID", "Nome da Conta", "Tipo", "Saldo Atual", "Empresa"])
        self.contas_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.contas_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.contas_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.contas_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.contas_table.setColumnHidden(0, True)
        table_layout.addWidget(self.contas_table)
        
        # --- Tela 1: Formulário de Cadastro ---
        self.form_panel = QFrame()
        self.form_panel.setObjectName("form_panel")
        form_layout = QVBoxLayout(self.form_panel)
        self.form_title = QLabel("Cadastro de Conta Financeira", objectName="form_title")
        form_layout.addWidget(self.form_title)
        
        form_grid = QGridLayout()
        form_grid.setSpacing(10)
        
        self.empresa_combo = QComboBox()
        self.nome_input = QLineEdit()
        self.tipo_conta_combo = QComboBox()
        self.tipo_conta_combo.addItems(self.tipos_conta)
        self.saldo_inicial_input = QLineEdit("0,00")
        # Validador de moeda (simplificado)
        self.saldo_inicial_input.setStyleSheet("text-align: right;")
        
        self.permite_transf_pdv_check = QCheckBox("Permitir receber transferências automáticas do PDV (Ex: Cofre)")
        self.status_check = QCheckBox("Conta Ativa")
        self.status_check.setChecked(True)
        
        form_grid.addWidget(QLabel("Empresa: *", objectName="required"), 0, 0)
        form_grid.addWidget(self.empresa_combo, 0, 1)
        form_grid.addWidget(QLabel("Nome da Conta: *", objectName="required"), 1, 0)
        form_grid.addWidget(self.nome_input, 1, 1)
        form_grid.addWidget(QLabel("Tipo de Conta: *", objectName="required"), 2, 0)
        form_grid.addWidget(self.tipo_conta_combo, 2, 1)
        form_grid.addWidget(QLabel("Saldo Inicial (R$):"), 3, 0)
        form_grid.addWidget(self.saldo_inicial_input, 3, 1)
        
        form_grid.addWidget(self.permite_transf_pdv_check, 4, 1)
        form_grid.addWidget(self.status_check, 5, 1)
        
        form_grid.setColumnStretch(1, 1)
        form_layout.addLayout(form_grid)
        form_layout.addStretch()
        
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

    def set_mode(self, mode):
        """Alterna entre o modo Tabela (0) e Formulário (1)."""
        if mode == 0:
            self.stack.setCurrentIndex(0)
            self.search_panel.setVisible(True)
            self.load_contas() 
        else:
            self._load_empresas_combobox()
            self.stack.setCurrentIndex(1)
            self.search_panel.setVisible(False)

    def _connect_signals(self):
        self.btn_novo.clicked.connect(self.show_new_form)
        self.btn_salvar.clicked.connect(self.save_conta)
        self.btn_excluir.clicked.connect(self.delete_conta)
        self.btn_cancelar.clicked.connect(self.cancel_action)
        self.btn_pesquisar.clicked.connect(self.load_contas)
        self.search_input.returnPressed.connect(self.load_contas)
        self.contas_table.itemDoubleClicked.connect(self._load_conta_for_edit)

    def _load_empresas_combobox(self):
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
            
            if self.empresa_combo.findData(1) >= 0:
                self.empresa_combo.setCurrentIndex(self.empresa_combo.findData(1))
        except Exception as e:
            self.logger.error(f"Erro ao carregar empresas: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao carregar empresas: {e}")
        finally:
            conn.close()
            
    def load_contas(self):
        """Carrega/Busca contas financeiras e preenche a tabela."""
        self.contas_table.setRowCount(0)
        search_term = self.search_input.text().strip()
        
        conn = get_connection()
        try:
            if not self.company_map:
                cur_emp = conn.cursor()
                cur_emp.execute("SELECT id, razao_social FROM empresas")
                for emp in cur_emp.fetchall():
                    self.company_map[emp['id']] = emp['razao_social']

            cur = conn.cursor()
            query = "SELECT * FROM contas_financeiras"
            params = []
            
            if search_term:
                query += " WHERE (nome LIKE ?)"
                params.append(f"%{search_term}%")
            
            query += " ORDER BY nome"
            cur.execute(query, tuple(params))
            
            rows = cur.fetchall()
            for row in rows:
                idx = self.contas_table.rowCount()
                self.contas_table.insertRow(idx)
                
                empresa_nome = self.company_map.get(row['empresa_id'], "Empresa Desconhecida")
                
                self.contas_table.setItem(idx, 0, QTableWidgetItem(str(row['id'])))
                self.contas_table.setItem(idx, 1, QTableWidgetItem(row['nome']))
                self.contas_table.setItem(idx, 2, QTableWidgetItem(row['tipo']))
                self.contas_table.setItem(idx, 3, QTableWidgetItem(f"R$ {row['saldo_atual']:.2f}"))
                self.contas_table.setItem(idx, 4, QTableWidgetItem(empresa_nome))
        
        except Exception as e:
            self.logger.error(f"Erro ao carregar contas: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao carregar contas: {e}")
        finally:
            conn.close()

    def _load_conta_for_edit(self, item):
        """Carrega os dados da conta selecionada no formulário."""
        row = item.row()
        conta_id = int(self.contas_table.item(row, 0).text())
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM contas_financeiras WHERE id = ?", (conta_id,))
            data = cur.fetchone()
            if not data:
                QMessageBox.critical(self, "Erro", "Conta não encontrada.")
                return

            self.clear_form()
            self.set_mode(1) 
            
            self.current_conta_id = conta_id
            self.form_title.setText(f"Editando Conta: {data['nome']}")
            
            index = self.empresa_combo.findData(data['empresa_id'])
            if index >= 0: self.empresa_combo.setCurrentIndex(index)
            
            self.nome_input.setText(data['nome'])
            self.tipo_conta_combo.setCurrentText(data['tipo'])
            
            # Ao editar, o saldo inicial não é mais editável (apenas o saldo atual via movimentações)
            self.saldo_inicial_input.setText(f"{data['saldo_inicial']:.2f}".replace('.',','))
            self.saldo_inicial_input.setReadOnly(True)
            self.saldo_inicial_input.setToolTip("O Saldo Inicial só pode ser definido na criação da conta.")
            
            self.permite_transf_pdv_check.setChecked(bool(data['permite_transferencia_pdv']))
            self.status_check.setChecked(bool(data['active']))
            
            self.btn_excluir.setEnabled(True)
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar dados da conta: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao carregar dados da conta: {e}")
        finally:
            conn.close()

    def show_new_form(self):
        self.clear_form()
        self.set_mode(1) 
        self.nome_input.setFocus()
        self.form_title.setText("Nova Conta Financeira")

    def cancel_action(self):
        self.clear_form()
        self.set_mode(0) 

    def clear_form(self):
        self.current_conta_id = None
        self.empresa_combo.setCurrentIndex(0)
        self.nome_input.clear()
        self.tipo_conta_combo.setCurrentIndex(0)
        self.saldo_inicial_input.setText("0,00")
        self.saldo_inicial_input.setReadOnly(False)
        self.saldo_inicial_input.setToolTip("")
        self.permite_transf_pdv_check.setChecked(False)
        self.status_check.setChecked(True)
        
        self.btn_excluir.setEnabled(False)
        self.form_title.setText("Cadastro de Conta Financeira")

    def _validate_fields(self):
        if self.empresa_combo.currentData() is None:
            return False, "Empresa"
        if not self.nome_input.text().strip():
            return False, "Nome da Conta"
        return True, ""

    def save_conta(self):
        valido, campo = self._validate_fields()
        if not valido:
            QMessageBox.warning(self, "Campo Obrigatório", f"O campo '{campo}' é obrigatório.")
            return

        try:
            saldo_inicial = float(self.saldo_inicial_input.text().replace(',', '.'))
        except ValueError:
            QMessageBox.warning(self, "Valor Inválido", "O Saldo Inicial é inválido.")
            return

        data = {
            "empresa_id": self.empresa_combo.currentData(),
            "nome": self.nome_input.text().strip(),
            "tipo": self.tipo_conta_combo.currentText(),
            "permite_transferencia_pdv": 1 if self.permite_transf_pdv_check.isChecked() else 0,
            "active": 1 if self.status_check.isChecked() else 0
        }
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            if self.current_conta_id:
                # UPDATE (Não altera saldos, só dados cadastrais)
                data["id"] = self.current_conta_id
                query = """
                    UPDATE contas_financeiras 
                    SET empresa_id = :empresa_id, nome = :nome, tipo = :tipo, 
                        permite_transferencia_pdv = :permite_transferencia_pdv, active = :active 
                    WHERE id = :id
                """
                msg = "Conta atualizada!"
                action_verb = "ATUALIZOU"
            else:
                # INSERT (Define saldos iniciais)
                data["saldo_inicial"] = saldo_inicial
                data["saldo_atual"] = saldo_inicial
                
                fields = ", ".join(data.keys())
                placeholders = ", ".join([f":{k}" for k in data.keys()])
                query = f"INSERT INTO contas_financeiras ({fields}) VALUES ({placeholders})"
                msg = "Conta salva!"
                action_verb = "CRIOU"
            
            cur.execute(query, data)
            conn.commit()
            
            # --- LOG ADICIONADO ---
            self.logger.info(f"Usuário {self.user_id} {action_verb} conta financeira: '{data['nome']}' (Tipo: {data['tipo']}).")
            
            QMessageBox.information(self, "Sucesso", msg)
            self.set_mode(0)

        except sqlite3.IntegrityError as e:
            QMessageBox.critical(self, "Erro", f"Erro de integridade: {e}")
        except Exception as e:
            self.logger.error(f"Erro ao salvar conta: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao salvar conta: {e}")
        finally:
            conn.close()
            
    def delete_conta(self):
        if not self.current_conta_id:
            QMessageBox.warning(self, "Erro", "Nenhuma conta selecionada.")
            return
            
        conn = get_connection()
        try:
            cur = conn.cursor()
            
            # Verifica se a conta está em uso
            cur.execute("SELECT id FROM movimentacoes_contas WHERE conta_id = ?", (self.current_conta_id,))
            mov_em_uso = cur.fetchone()
            if mov_em_uso:
                QMessageBox.critical(self, "Erro", "Não é possível excluir. Esta conta já possui movimentações financeiras.")
                return

            reply = QMessageBox.question(self, "Confirmação",
                f"Tem certeza que deseja excluir a conta '{self.nome_input.text()}'?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                
            if reply == QMessageBox.No:
                return
            
            cur.execute("DELETE FROM contas_financeiras WHERE id = ?", (self.current_conta_id,))
            conn.commit()
            
            # --- LOG ADICIONADO ---
            self.logger.info(f"Usuário {self.user_id} EXCLUIU conta financeira ID {self.current_conta_id} ('{self.nome_input.text()}').")
            
            QMessageBox.information(self, "Sucesso", "Conta excluída.")
            self.set_mode(0)
            
        except Exception as e:
            self.logger.error(f"Erro ao excluir conta: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao excluir conta: {e}")
        finally:
            conn.close()