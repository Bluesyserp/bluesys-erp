# -*- coding: utf-8 -*-
# modules/baixa_lancamento_dialog.py
import sqlite3
from PyQt5.QtWidgets import (
    QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QGridLayout, QFrame, QComboBox, 
    QDateEdit, QDoubleSpinBox, QLineEdit
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QDate
from database.db import get_connection
from .custom_dialogs import FramelessDialog # Reutiliza o diálogo sem bordas

class BaixaLancamentoDialog(FramelessDialog):
    """
    Diálogo para Baixar (Pagar/Receber) um Lançamento Financeiro.
    """
    def __init__(self, user_id, empresa_id, lancamento_data, parent=None):
        super().__init__(parent, title="Baixar Lançamento Financeiro")
        
        self.user_id = user_id
        self.empresa_id = empresa_id
        self.lancamento_data = lancamento_data
        
        self.contas_map = {} # {id: nome}
        
        self.setFixedSize(450, 400) # Tamanho
        
        self._build_ui()
        self._load_contas_combo()
        self._populate_fields()
        
        self.ok_button.setText("Confirmar Baixa")
        self.cancel_button.setText("Cancelar")
        
    def _build_ui(self):
        grid = QGridLayout()
        grid.setSpacing(10)
        
        # --- Dados do Lançamento (Informativo) ---
        grid.addWidget(QLabel("<b>DADOS DO LANÇAMENTO</b>"), 0, 0, 1, 2)
        
        grid.addWidget(QLabel("Descrição:"), 1, 0)
        desc_label = QLineEdit(self.lancamento_data['descricao'])
        desc_label.setReadOnly(True)
        grid.addWidget(desc_label, 1, 1)

        grid.addWidget(QLabel("Valor Previsto (R$):"), 2, 0)
        valor_prev_label = QLineEdit(f"{self.lancamento_data['valor_previsto']:.2f}")
        valor_prev_label.setReadOnly(True)
        valor_prev_label.setStyleSheet("font-weight: bold; text-align: right;")
        grid.addWidget(valor_prev_label, 2, 1)

        # --- Dados da Baixa (Editável) ---
        grid.addWidget(QLabel("<b>DADOS DA BAIXA (PAGAMENTO)</b>"), 3, 0, 1, 2)

        grid.addWidget(QLabel("Conta Financeira: *"), 4, 0)
        self.conta_combo = QComboBox()
        self.conta_combo.setPlaceholderText("Selecione a conta (Ex: Banco, Cofre)...")
        grid.addWidget(self.conta_combo, 4, 1)
        
        grid.addWidget(QLabel("Data Pagamento: *"), 5, 0)
        self.data_pagamento_input = QDateEdit(QDate.currentDate())
        self.data_pagamento_input.setCalendarPopup(True)
        grid.addWidget(self.data_pagamento_input, 5, 1)

        grid.addWidget(QLabel("Valor Pago (R$): *"), 6, 0)
        self.valor_pago_spin = QDoubleSpinBox()
        self.valor_pago_spin.setRange(0.01, 9999999.99)
        self.valor_pago_spin.setAlignment(Qt.AlignRight)
        self.valor_pago_spin.setFont(QFont("Segoe UI", 11, QFont.Bold))
        grid.addWidget(self.valor_pago_spin, 6, 1)
        
        grid.addWidget(QLabel("Juros/Acréscimos (R$):"), 7, 0)
        self.juros_spin = QDoubleSpinBox()
        self.juros_spin.setRange(0.00, 999999.99)
        self.juros_spin.setAlignment(Qt.AlignRight)
        grid.addWidget(self.juros_spin, 7, 1)
        
        grid.addWidget(QLabel("Desconto (R$):"), 8, 0)
        self.desconto_spin = QDoubleSpinBox()
        self.desconto_spin.setRange(0.00, 999999.99)
        self.desconto_spin.setAlignment(Qt.AlignRight)
        grid.addWidget(self.desconto_spin, 8, 1)

        # Adiciona o grid ao layout de conteúdo (da classe base)
        self.content_layout.addLayout(grid)
        self.content_layout.addStretch()

    def _load_contas_combo(self):
        """Carrega o combo com as contas financeiras (exceto PDVs)."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            
            # Carrega contas da empresa que NÃO sejam do tipo PDV
            cur.execute("""
                SELECT id, nome, tipo FROM contas_financeiras 
                WHERE empresa_id = ? AND active = 1 AND tipo != 'PDV / Caixa Operador'
                ORDER BY nome
            """, (self.empresa_id,))
            
            contas = cur.fetchall()
            
            self.conta_combo.addItem("Selecione a conta...", None)
            if not contas:
                self.conta_combo.setEnabled(False)
                return

            for conta in contas:
                self.contas_map[conta['id']] = conta['nome']
                self.conta_combo.addItem(f"{conta['nome']} ({conta['tipo']})", conta['id'])
                
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Carregar Contas", f"Erro: {e}")
        finally:
            conn.close()
            
    def _populate_fields(self):
        """Preenche o valor a pagar com o saldo restante."""
        saldo_restante = self.lancamento_data['valor_previsto'] - (self.lancamento_data.get('valor_pago', 0.0) or 0.0)
        self.valor_pago_spin.setValue(saldo_restante)

    def get_data(self):
        """Valida e retorna os dados da baixa."""
        
        conta_id = self.conta_combo.currentData()
        if conta_id is None:
            QMessageBox.warning(self, "Campo Obrigatório", "Selecione a Conta Financeira.")
            return None
            
        valor_pago = self.valor_pago_spin.value()
        if valor_pago <= 0:
            QMessageBox.warning(self, "Valor Inválido", "O Valor Pago deve ser maior que zero.")
            return None
            
        # Calcula o saldo restante (o que faltava pagar)
        saldo_restante = self.lancamento_data['valor_previsto'] - (self.lancamento_data.get('valor_pago', 0.0) or 0.0)
        saldo_restante = round(saldo_restante, 2)
        
        # Verifica se o usuário está tentando pagar a mais (sem juros)
        if valor_pago > saldo_restante and self.juros_spin.value() == 0:
             reply = QMessageBox.question(self, "Valor Maior",
                f"O valor pago (R$ {valor_pago:.2f}) é maior que o saldo devedor (R$ {saldo_restante:.2f}).\n"
                "Deseja lançar a diferença como JUROS?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
             
             if reply == QMessageBox.Yes:
                 self.juros_spin.setValue(round(valor_pago - saldo_restante, 2))
             else:
                 return None # Cancela a baixa
        
        # Verifica se está pagando a menos
        is_baixa_parcial = (valor_pago + self.desconto_spin.value() - self.juros_spin.value()) < saldo_restante
        
        if is_baixa_parcial:
            reply = QMessageBox.question(self, "Baixa Parcial",
                "O valor informado não quita o lançamento. Deseja realizar uma BAIXA PARCIAL?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return None

        return {
            "conta_id": conta_id,
            "data_pagamento": self.data_pagamento_input.date().toString("yyyy-MM-dd"),
            "valor_pago": valor_pago,
            "juros": self.juros_spin.value(),
            "desconto": self.desconto_spin.value(),
            "is_baixa_parcial": is_baixa_parcial
        }