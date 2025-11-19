# -*- coding: utf-8 -*-
# modules/edit_lancamento_dialog.py
import sqlite3
from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QGridLayout, QFrame, QComboBox, QTextEdit,
    QDateEdit, QDoubleSpinBox
)
from PyQt5.QtGui import QFont, QDoubleValidator
from PyQt5.QtCore import Qt, QDate, QLocale
from database.db import get_connection
from .custom_dialogs import FramelessDialog # Reutiliza o diálogo sem bordas

class EditLancamentoDialog(FramelessDialog):
    """
    Diálogo para EDITAR um Lançamento Financeiro (parcela) existente.
    """
    def __init__(self, user_id, empresa_id, lancamento_data, parent=None):
        super().__init__(parent, title="Editar Lançamento Financeiro")
        
        self.user_id = user_id
        self.empresa_id = empresa_id
        self.lancamento_data = lancamento_data
        self.lancamento_id = lancamento_data['id']
        
        self.categorias_map = {}
        self.centros_custo_map = {}
        
        self.setFixedSize(450, 350) # Tamanho
        
        self._setup_validators()
        self._build_ui()
        self._load_combos()
        self._populate_fields()
        
        self.ok_button.setText("Salvar Alterações")
        self.cancel_button.setText("Cancelar")
        
    def _setup_validators(self):
        locale = QLocale(QLocale.Portuguese, QLocale.Brazil)
        self.valor_validator = QDoubleValidator(0.01, 9999999.99, 2)
        self.valor_validator.setLocale(locale)
        self.valor_validator.setNotation(QDoubleValidator.StandardNotation)
        
    def _build_ui(self):
        grid = QGridLayout()
        grid.setSpacing(10)
        
        grid.addWidget(QLabel("<b>DADOS DO LANÇAMENTO</b>"), 0, 0, 1, 2)
        
        grid.addWidget(QLabel("Descrição: *"), 1, 0)
        self.descricao_input = QLineEdit()
        grid.addWidget(self.descricao_input, 1, 1)

        grid.addWidget(QLabel("Valor Previsto (R$): *"), 2, 0)
        self.valor_previsto_input = QLineEdit("0,00")
        self.valor_previsto_input.setValidator(self.valor_validator)
        self.valor_previsto_input.setAlignment(Qt.AlignRight)
        self.valor_previsto_input.setFont(QFont("Segoe UI", 11, QFont.Bold))
        grid.addWidget(self.valor_previsto_input, 2, 1)
        
        grid.addWidget(QLabel("Vencimento: *"), 3, 0)
        self.data_vencimento_input = QDateEdit(QDate.currentDate())
        self.data_vencimento_input.setCalendarPopup(True)
        grid.addWidget(self.data_vencimento_input, 3, 1)

        grid.addWidget(QLabel("Categoria: *"), 4, 0)
        self.categoria_combo = QComboBox()
        self.categoria_combo.setPlaceholderText("Selecione o plano de contas...")
        grid.addWidget(self.categoria_combo, 4, 1)
        
        grid.addWidget(QLabel("Centro de Custo:"), 5, 0)
        self.centro_custo_combo = QComboBox()
        self.centro_custo_combo.setPlaceholderText("(Opcional)")
        grid.addWidget(self.centro_custo_combo, 5, 1)
        
        # Adiciona o grid ao layout de conteúdo (da classe base)
        self.content_layout.addLayout(grid)
        self.content_layout.addStretch()

    def _load_combos(self):
        """Carrega os combos de categorias e centros de custo."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            
            # 1. Categorias (Plano de Contas)
            tipo_lancamento = self.lancamento_data['tipo'] # 'A PAGAR' ou 'A RECEBER'
            tipo_categoria = 'DESPESA' if tipo_lancamento == 'A PAGAR' else 'RECEITA'
            
            cur.execute("SELECT id, nome, tipo, parent_id FROM categorias_financeiras WHERE tipo = ? ORDER BY nome", (tipo_categoria,))
            categorias_raw = cur.fetchall()
            
            cat_map = {c['id']: (c['nome'], c['parent_id']) for c in categorias_raw}
            
            self.categoria_combo.addItem("Selecione a Categoria...", None)
            for cat in categorias_raw:
                nome_completo = cat['nome']
                parent_id = cat['parent_id']
                while parent_id:
                    parent_data = cat_map.get(parent_id)
                    if parent_data:
                        nome_completo = f"{parent_data[0]} -> {nome_completo}"
                        parent_id = parent_data[1]
                    else:
                        parent_id = None
                        
                self.categorias_map[cat['id']] = nome_completo
                self.categoria_combo.addItem(nome_completo, cat['id'])

            # 2. Centros de Custo
            cur.execute("SELECT id, nome FROM centros_de_custo WHERE empresa_id = ? ORDER BY nome", (self.empresa_id,))
            self.centro_custo_combo.addItem("Nenhum", None)
            for cc in cur.fetchall():
                self.centros_custo_map[cc['id']] = cc['nome']
                self.centro_custo_combo.addItem(cc['nome'], cc['id'])
                
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Carregar Dados", f"Erro: {e}")
        finally:
            conn.close()
            
    def _populate_fields(self):
        """Preenche os campos com os dados do lançamento a ser editado."""
        try:
            self.descricao_input.setText(self.lancamento_data['descricao'])
            
            valor_prev_str = f"{self.lancamento_data['valor_previsto']:.2f}".replace('.', ',')
            self.valor_previsto_input.setText(valor_prev_str)
            
            vencimento_date = QDate.fromString(self.lancamento_data['data_vencimento'], "yyyy-MM-dd")
            self.data_vencimento_input.setDate(vencimento_date)
            
            # Seleciona Categoria
            cat_id = self.lancamento_data.get('categoria_id')
            if cat_id:
                cat_index = self.categoria_combo.findData(cat_id)
                if cat_index > -1:
                    self.categoria_combo.setCurrentIndex(cat_index)
                    
            # Seleciona Centro de Custo
            cc_id = self.lancamento_data.get('centro_custo_id')
            if cc_id:
                cc_index = self.centro_custo_combo.findData(cc_id)
                if cc_index > -1:
                    self.centro_custo_combo.setCurrentIndex(cc_index)
            else:
                self.centro_custo_combo.setCurrentIndex(0) # "Nenhum"
                
        except Exception as e:
             QMessageBox.critical(self, "Erro ao Preencher", f"Não foi possível carregar os dados: {e}")
             self.reject()

    def get_data(self):
        """Valida e retorna os dados atualizados."""
        
        # 1. Validação
        descricao = self.descricao_input.text().strip()
        if not descricao:
            QMessageBox.warning(self, "Campo Obrigatório", "O campo 'Descrição' é obrigatório.")
            return None
            
        categoria_id = self.categoria_combo.currentData()
        if categoria_id is None:
            QMessageBox.warning(self, "Campo Obrigatório", "O campo 'Categoria' é obrigatório.")
            return None
            
        try:
            valor_previsto = float(self.valor_previsto_input.text().replace(',', '.'))
            if valor_previsto < 0.01: raise ValueError()
        except ValueError:
             QMessageBox.warning(self, "Valor Inválido", "O 'Valor Previsto' é inválido.")
             return None
        
        # 2. Retorno dos dados
        return {
            "descricao": descricao,
            "valor_previsto": valor_previsto,
            "data_vencimento": self.data_vencimento_input.date().toString("yyyy-MM-dd"),
            "categoria_id": categoria_id,
            "centro_custo_id": self.centro_custo_combo.currentData() # Pode ser None
        }