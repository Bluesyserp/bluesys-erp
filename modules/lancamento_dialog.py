# -*- coding: utf-8 -*-
# modules/lancamento_dialog.py
import sqlite3
import logging # <-- NOVO
from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QGridLayout, QFrame, QComboBox, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QDateEdit, QDoubleSpinBox, QSpinBox, QDialogButtonBox
)
from PyQt5.QtGui import QFont, QDoubleValidator
from PyQt5.QtCore import Qt, QDate, QLocale
from database.db import get_connection
from .custom_dialogs import FramelessDialog # Reutiliza o diálogo sem bordas
from datetime import datetime
from dateutil.relativedelta import relativedelta

class LancamentoDialog(FramelessDialog):
    """
    Diálogo completo para criar um novo Título Financeiro e seus
    Lançamentos (parcelas).
    """
    def __init__(self, user_id, empresa_id, parent=None):
        super().__init__(parent, title="Novo Lançamento Financeiro")
        
        self.user_id = user_id
        self.empresa_id = empresa_id
        self.setFixedSize(700, 550) # Tamanho maior
        
        # --- NOVO: Logger ---
        self.logger = logging.getLogger(__name__)
        
        # Mapas para carregar os combos
        self.clientes_map = {}
        self.fornecedores_map = {}
        self.categorias_map = {}
        self.centros_custo_map = {}
        
        self._setup_validators()
        self._build_ui()
        self._connect_signals()
        
        # Carrega todos os comboboxes
        self._load_combos()
        
        self.ok_button.setText("Salvar Lançamento")
        self.cancel_button.setText("Cancelar")
        
    def _setup_validators(self):
        locale = QLocale(QLocale.Portuguese, QLocale.Brazil)
        self.valor_validator = QDoubleValidator(0.01, 9999999.99, 2)
        self.valor_validator.setLocale(locale)
        self.valor_validator.setNotation(QDoubleValidator.StandardNotation)
        
    def _build_ui(self):
        # Layout principal (Grid)
        grid = QGridLayout()
        grid.setSpacing(10)
        
        # --- Lado Esquerdo: Dados do Título ---
        grid.addWidget(QLabel("<b>DADOS DO TÍTULO</b>"), 0, 0, 1, 2)
        
        grid.addWidget(QLabel("Tipo: *"), 1, 0)
        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems(["A PAGAR (Despesa)", "A RECEBER (Receita)"])
        grid.addWidget(self.tipo_combo, 1, 1)

        grid.addWidget(QLabel("Parceiro: *"), 2, 0)
        self.parceiro_combo = QComboBox()
        self.parceiro_combo.setPlaceholderText("Selecione um Cliente ou Fornecedor...")
        grid.addWidget(self.parceiro_combo, 2, 1)

        grid.addWidget(QLabel("Categoria: *"), 3, 0)
        self.categoria_combo = QComboBox()
        self.categoria_combo.setPlaceholderText("Selecione o plano de contas...")
        grid.addWidget(self.categoria_combo, 3, 1)
        
        grid.addWidget(QLabel("Centro de Custo:"), 4, 0)
        self.centro_custo_combo = QComboBox()
        self.centro_custo_combo.setPlaceholderText("(Opcional)")
        grid.addWidget(self.centro_custo_combo, 4, 1)
        
        grid.addWidget(QLabel("Descrição: *"), 5, 0)
        self.descricao_input = QLineEdit()
        self.descricao_input.setPlaceholderText("Ex: Boleto Aluguel, Compra de Mercadoria")
        grid.addWidget(self.descricao_input, 5, 1)
        
        grid.addWidget(QLabel("Nº Documento:"), 6, 0)
        self.documento_input = QLineEdit()
        self.documento_input.setPlaceholderText("Ex: N° da Nota ou Boleto")
        grid.addWidget(self.documento_input, 6, 1)
        
        grid.addWidget(QLabel("Valor Total (R$): *"), 7, 0)
        self.valor_total_input = QLineEdit("0,00")
        self.valor_total_input.setValidator(self.valor_validator)
        self.valor_total_input.setAlignment(Qt.AlignRight)
        self.valor_total_input.setFont(QFont("Segoe UI", 11, QFont.Bold))
        grid.addWidget(self.valor_total_input, 7, 1)
        
        grid.addWidget(QLabel("Data Emissão:"), 8, 0)
        self.data_emissao_input = QDateEdit(QDate.currentDate())
        self.data_emissao_input.setCalendarPopup(True)
        grid.addWidget(self.data_emissao_input, 8, 1)
        
        grid.addWidget(QLabel("Data Competência:"), 9, 0)
        self.data_competencia_input = QDateEdit(QDate.currentDate())
        self.data_competencia_input.setCalendarPopup(True)
        grid.addWidget(self.data_competencia_input, 9, 1)

        # --- Lado Direito: Parcelamento ---
        grid.addWidget(QLabel("<b>PARCELAMENTO</b>"), 0, 2, 1, 2)
        
        grid.addWidget(QLabel("Nº de Parcelas:"), 1, 2)
        self.parcelas_spin = QSpinBox()
        self.parcelas_spin.setRange(1, 120)
        self.parcelas_spin.setValue(1)
        grid.addWidget(self.parcelas_spin, 1, 3)
        
        grid.addWidget(QLabel("1º Vencimento:"), 2, 2)
        self.data_vencimento_input = QDateEdit(QDate.currentDate())
        self.data_vencimento_input.setCalendarPopup(True)
        grid.addWidget(self.data_vencimento_input, 2, 3)
        
        self.btn_gerar_parcelas = QPushButton("Gerar Parcelas")
        self.btn_gerar_parcelas.setStyleSheet("background-color: #2ECC71;")
        grid.addWidget(self.btn_gerar_parcelas, 3, 2, 1, 2)
        
        self.parcelas_table = QTableWidget()
        self.parcelas_table.setColumnCount(2)
        self.parcelas_table.setHorizontalHeaderLabels(["Vencimento", "Valor (R$)"])
        self.parcelas_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.parcelas_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        grid.addWidget(self.parcelas_table, 4, 2, 6, 2) # Ocupa 6 linhas

        # Adiciona o grid ao layout de conteúdo (da classe base)
        self.content_layout.addLayout(grid)

    def _connect_signals(self):
        self.tipo_combo.currentIndexChanged.connect(self._load_parceiros)
        self.btn_gerar_parcelas.clicked.connect(self._generate_parcelas)
        # Conecta o botão OK (da classe base) para salvar
        self.button_box.accepted.disconnect() # Remove o accept() padrão
        self.button_box.accepted.connect(self.save_lancamento)

    def _load_combos(self):
        """Carrega todos os combos do formulário"""
        conn = get_connection()
        try:
            cur = conn.cursor()
            
            # 1. Categorias (Plano de Contas)
            cur.execute("SELECT id, nome, tipo, parent_id FROM categorias_financeiras ORDER BY nome")
            categorias_raw = cur.fetchall()
            
            # Constrói mapa de pais
            cat_map = {c['id']: (c['nome'], c['parent_id'], c['tipo']) for c in categorias_raw}
            
            self.categoria_combo.addItem("Selecione a Categoria...", None)
            for cat in categorias_raw:
                nome_completo = cat['nome']
                tipo = cat['tipo']
                
                # Monta o nome hierárquico (Ex: Despesa -> Custo Fixo -> Aluguel)
                parent_id = cat['parent_id']
                while parent_id:
                    parent_data = cat_map.get(parent_id)
                    if parent_data:
                        nome_completo = f"{parent_data[0]} -> {nome_completo}"
                        parent_id = parent_data[1]
                    else:
                        parent_id = None
                        
                self.categorias_map[cat['id']] = (nome_completo, tipo)
                self.categoria_combo.addItem(f"({tipo}) {nome_completo}", cat['id'])

            # 2. Centros de Custo
            cur.execute("SELECT id, nome FROM centros_de_custo WHERE empresa_id = ? ORDER BY nome", (self.empresa_id,))
            self.centro_custo_combo.addItem("Nenhum", None)
            for cc in cur.fetchall():
                self.centros_custo_map[cc['id']] = cc['nome']
                self.centro_custo_combo.addItem(cc['nome'], cc['id'])
                
            # 3. Fornecedores (para Contas a Pagar)
            cur.execute("SELECT id, nome FROM fornecedores ORDER BY nome")
            for f in cur.fetchall():
                self.fornecedores_map[f['id']] = f['nome']
                
            # 4. Clientes (para Contas a Receber)
            cur.execute("SELECT id, nome_razao FROM clientes ORDER BY nome_razao")
            for c in cur.fetchall():
                self.clientes_map[c['id']] = c['nome_razao']

        except Exception as e:
            QMessageBox.critical(self, "Erro ao Carregar Dados", f"Erro: {e}")
        finally:
            conn.close()
        
        # Carrega o combo de parceiros (inicia com 'A PAGAR')
        self._load_parceiros()
        
    def _load_parceiros(self):
        """Atualiza o combo 'Parceiro' baseado no Tipo (Pagar/Receber)"""
        self.parceiro_combo.clear()
        
        if self.tipo_combo.currentText() == "A PAGAR (Despesa)":
            self.parceiro_combo.addItem("Selecione um Fornecedor...", None)
            for id_f, nome in self.fornecedores_map.items():
                self.parceiro_combo.addItem(f"[F] {nome}", id_f)
        else: # A RECEBER
            self.parceiro_combo.addItem("Selecione um Cliente...", None)
            for id_c, nome in self.clientes_map.items():
                self.parceiro_combo.addItem(f"[C] {nome}", id_c)

    def _generate_parcelas(self):
        """Calcula e exibe as parcelas na tabela."""
        try:
            valor_total_str = self.valor_total_input.text().replace(',', '.')
            valor_total = float(valor_total_str)
            num_parcelas = self.parcelas_spin.value()
            
            if valor_total < 0.01:
                QMessageBox.warning(self, "Erro", "O Valor Total deve ser maior que zero.")
                return
            
            self.parcelas_table.setRowCount(0)
            
            valor_base_parcela = round(valor_total / num_parcelas, 2)
            diferenca_arredondamento = round(valor_total - (valor_base_parcela * num_parcelas), 2)
            
            data_vencimento = self.data_vencimento_input.date()

            for i in range(num_parcelas):
                row = self.parcelas_table.rowCount()
                self.parcelas_table.insertRow(row)
                
                # Vencimento (a cada 30 dias / 1 mês)
                vencimento_parcela = data_vencimento.addMonths(i)
                item_venc = QTableWidgetItem(vencimento_parcela.toString("yyyy-MM-dd"))
                self.parcelas_table.setItem(row, 0, item_venc)
                
                # Valor
                valor_parcela = valor_base_parcela
                if i == 0: # Adiciona a diferença na primeira parcela
                    valor_parcela += diferenca_arredondamento
                    
                item_valor = QTableWidgetItem(f"{valor_parcela:.2f}")
                item_valor.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.parcelas_table.setItem(row, 1, item_valor)

        except Exception as e:
            QMessageBox.critical(self, "Erro ao Gerar Parcelas", f"Erro: {e}")

    def save_lancamento(self):
        """Valida e salva o Título e seus Lançamentos (Parcelas)."""
        
        # 1. Validação dos Campos do Título
        tipo_str = "A PAGAR" if self.tipo_combo.currentIndex() == 0 else "A RECEBER"
        parceiro_id = self.parceiro_combo.currentData()
        categoria_id = self.categoria_combo.currentData()
        centro_custo_id = self.centro_custo_combo.currentData()
        descricao = self.descricao_input.text().strip()
        valor_total_str = self.valor_total_input.text().replace(',', '.')
        
        if not all([parceiro_id, categoria_id, descricao, valor_total_str]):
            QMessageBox.warning(self, "Campos Obrigatórios", "Verifique os campos: Tipo, Parceiro, Categoria, Descrição e Valor Total.")
            return

        try:
            valor_total = float(valor_total_str)
            if valor_total < 0.01: raise ValueError()
        except ValueError:
             QMessageBox.warning(self, "Valor Inválido", "O Valor Total é inválido.")
             return
        
        # 2. Validação das Parcelas
        if self.parcelas_table.rowCount() == 0:
            QMessageBox.warning(self, "Parcelas", "Clique em 'Gerar Parcelas' antes de salvar.")
            return
            
        valor_soma_parcelas = 0.0
        parcelas_data = []
        try:
            for row in range(self.parcelas_table.rowCount()):
                vencimento = self.parcelas_table.item(row, 0).text()
                valor_str = self.parcelas_table.item(row, 1).text().replace(',', '.')
                valor = float(valor_str)
                valor_soma_parcelas += valor
                parcelas_data.append((vencimento, valor))
        except Exception:
             QMessageBox.critical(self, "Erro na Tabela", "Valores inválidos na tabela de parcelas.")
             return
             
        # 3. Verifica se a soma das parcelas bate com o total
        if abs(round(valor_total - valor_soma_parcelas, 2)) > 0.01:
             QMessageBox.critical(self, "Erro de Soma", 
                f"O Valor Total (R$ {valor_total:.2f}) não bate com a soma das parcelas (R$ {valor_soma_parcelas:.2f}).\n"
                "Gere as parcelas novamente.")
             return

        # 4. Preparar Dados do Título
        titulo_data = {
            "empresa_id": self.empresa_id,
            "tipo": tipo_str,
            "cliente_id": parceiro_id if tipo_str == 'A RECEBER' else None,
            "fornecedor_id": parceiro_id if tipo_str == 'A PAGAR' else None,
            "categoria_id": categoria_id,
            "centro_custo_id": centro_custo_id,
            "data_emissao": self.data_emissao_input.date().toString("yyyy-MM-dd"),
            "data_competencia": self.data_competencia_input.date().toString("yyyy-MM-dd"),
            "numero_documento": self.documento_input.text().strip() or None,
            "descricao": descricao,
            "valor_total": valor_total,
            "status": "PENDENTE"
        }

        # 5. Salvar no Banco de Dados (Transação)
        conn = get_connection()
        try:
            cur = conn.cursor()
            conn.execute("BEGIN")
            
            # A. Salva o Título (Capa)
            fields = ", ".join(titulo_data.keys())
            placeholders = ", ".join([f":{k}" for k in titulo_data.keys()])
            query_titulo = f"INSERT INTO titulos_financeiros ({fields}) VALUES ({placeholders})"
            cur.execute(query_titulo, titulo_data)
            
            titulo_id = cur.lastrowid
            
            # B. Salva os Lançamentos (Parcelas)
            query_lancamento = """
                INSERT INTO lancamentos_financeiros
                (titulo_id, tipo, categoria_id, centro_custo_id, descricao, 
                 valor_previsto, data_vencimento, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDENTE')
            """
            
            for i, (vencimento, valor) in enumerate(parcelas_data):
                desc_parcela = f"{descricao} [Parc. {i+1}/{len(parcelas_data)}]"
                cur.execute(query_lancamento, (
                    titulo_id, tipo_str, categoria_id, centro_custo_id, 
                    desc_parcela, valor, vencimento
                ))
            
            conn.commit()
            
            # --- LOG ADICIONADO ---
            self.logger.info(f"Usuário ID {self.user_id} criou novo Título Financeiro. ID: {titulo_id}, Tipo: {tipo_str}, Valor: {valor_total:.2f}, Parcelas: {len(parcelas_data)}.")
            
            QMessageBox.information(self, "Sucesso", "Lançamento financeiro salvo com sucesso.")
            self.accept() # Fecha o diálogo

        except Exception as e:
            conn.rollback()
            # --- LOG ADICIONADO ---
            self.logger.error(f"FALHA ao criar Título (User ID {self.user_id}, Valor: {valor_total}). Erro: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro ao Salvar", f"Não foi possível salvar o lançamento: {e}")
        finally:
            conn.close()