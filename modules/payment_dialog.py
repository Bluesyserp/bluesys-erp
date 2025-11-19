# modules/payment_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QWidget, QLabel, QLineEdit, QPushButton, 
    QVBoxLayout, QHBoxLayout, QFrame, QGridLayout,
    QMessageBox, QDoubleSpinBox, QApplication
)
from PyQt5.QtGui import QFont, QDoubleValidator
from PyQt5.QtCore import Qt, QLocale, QPoint
from .pos_auth_dialog import PosAuthDialog 
from .custom_dialogs import CustomComboDialog, CustomIntDialog

class PaymentDialog(QDialog):
    
    def __init__(self, subtotal, desconto_total, total_final, parent=None):
        super().__init__(parent)
        
        self.subtotal = subtotal
        self.desconto_total = desconto_total
        self.total_a_pagar = total_final
        self.valor_pago = 0.0
        self.troco = 0.0
        self.pagamentos = [] 
        self.old_pos = None 

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(700, 500)
        self.setModal(True)
        
        locale = QLocale(QLocale.Portuguese, QLocale.Brazil)
        self.validator = QDoubleValidator(0.00, 99999.99, 2)
        self.validator.setLocale(locale)
        self.validator.setNotation(QDoubleValidator.StandardNotation)
        
        self._setup_styles()
        self._build_ui()
        self._update_totals()
        
        self.valor_dinheiro_input.setFocus() 
        
        # Centraliza esta janela
        if parent:
            parent_global_center = parent.mapToGlobal(parent.rect().center())
            self.move(parent_global_center - self.rect().center())
    
    def _setup_styles(self):
        self.setStyleSheet("""
            QDialog { background-color: transparent; }
            QFrame#main_frame {
                background-color: #f0f4f8; border-radius: 8px; border: 1px solid #c0c0d0;
            }
            QLabel { font-size: 14px; color: #555; }
            QFrame#header_frame { 
                background-color: #f8f8fb; border-top-left-radius: 8px;
                border-top-right-radius: 8px; border-bottom: 1px solid #ddd;
                max-height: 35px;
            }
            QLabel#header_title {
                font-size: 14px; font-weight: bold; color: #333; padding-left: 10px;
            }
            QPushButton#close_btn {
                background: transparent; border: none; font-family: "Arial"; 
                font-weight: bold; font-size: 14px; max-width: 30px; max-height: 30px;
            }
            QPushButton#close_btn:hover { background-color: #e81123; color: white; }
            QFrame#summary_panel { background-color: #e0e8f0; }
            QLabel.summary_label {
                font-size: 16px; font-weight: normal; color: #333; padding-left: 10px;
            }
            QLabel.summary_value {
                font-size: 16px; font-weight: bold; color: #333; padding-right: 10px;
            }
            QLabel#total_label { font-size: 18px; font-weight: bold; color: #333; }
            QLabel#total_value { font-size: 48px; font-weight: bold; color: #1e1e2f; }
            QPushButton#payment_method {
                padding: 20px; font-size: 16px; font-weight: bold; text-align: left;
                background-color: white; border: 1px solid #ccc;
                border-radius: 8px; color: #333;
            }
            QPushButton#payment_method:hover { background-color: #f0f0f0; }
            QPushButton#btn_dinheiro { background-color: #2ECC71; color: white; }
            QPushButton#btn_dinheiro:hover { background-color: #27AE60; }
            QPushButton#btn_cartao { background-color: #3498DB; color: white; }
            QPushButton#btn_cartao:hover { background-color: #2980B9; }
            QPushButton#btn_outros { background-color: #E67E22; color: white; }
            QPushButton#btn_outros:hover { background-color: #D35400; }
            QFrame#totals_frame { background-color: white; border-top: 1px solid #ddd; }
            QLabel.valor_label { font-size: 14px; color: #777; }
            QLabel.valor_display { font-size: 24px; font-weight: bold; color: #333; }
            QLabel#valor_troco { font-size: 24px; font-weight: bold; color: #c0392b; }
            QLabel#valor_saldo_a_pagar { font-size: 24px; font-weight: bold; color: #0078d7; }
            QPushButton#btn_confirmar {
                background-color: #0078d7; color: white; padding: 10px; 
                font-size: 14px; font-weight: bold;
            }
            QPushButton#btn_confirmar:disabled { background-color: #aaa; }
            QPushButton#btn_cancelar {
                background-color: #e74c3c; color: white; padding: 10px; 
                font-size: 14px; font-weight: bold;
            }
        """)


    def _build_ui(self):
        main_frame = QFrame(self)
        main_frame.setObjectName("main_frame")
        
        layout = QVBoxLayout(main_frame) 
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Cabeçalho (Recriado) ---
        self.header_frame = QFrame()
        self.header_frame.setObjectName("header_frame")
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(10, 0, 5, 0)
        header_layout.addWidget(QLabel("Finalizar Venda", objectName="header_title"))
        header_layout.addStretch()
        self.close_button = QPushButton("X") 
        self.close_button.setObjectName("close_btn")
        self.close_button.clicked.connect(self.reject) 
        header_layout.addWidget(self.close_button)
        layout.addWidget(self.header_frame)

        # --- Painel de Resumo ---
        summary_panel = QFrame()
        summary_panel.setObjectName("summary_panel")
        summary_layout = QHBoxLayout(summary_panel)
        summary_layout.setContentsMargins(20, 20, 20, 20)
        
        left_summary_layout = QGridLayout()
        left_summary_layout.addWidget(QLabel("R$ SUB TOTAL", objectName="summary_label"), 0, 0)
        self.lbl_subtotal = QLabel(f"{self.subtotal:.2f}", objectName="summary_value")
        left_summary_layout.addWidget(self.lbl_subtotal, 0, 1, Qt.AlignRight)
        left_summary_layout.addWidget(QLabel("R$ DESCONTOS TOTAIS", objectName="summary_label"), 1, 0)
        self.lbl_desconto_total = QLabel(f"-{self.desconto_total:.2f}", objectName="summary_value")
        left_summary_layout.addWidget(self.lbl_desconto_total, 1, 1, Qt.AlignRight)
        left_summary_layout.setRowStretch(2, 1) 
        
        right_summary_layout = QVBoxLayout()
        right_summary_layout.addStretch()
        right_summary_layout.addWidget(QLabel("R$ TOTAL A PAGAR", objectName="total_label"), 0, Qt.AlignRight)
        self.lbl_total_a_pagar_grande = QLabel(f"{self.total_a_pagar:.2f}", objectName="total_value")
        right_summary_layout.addWidget(self.lbl_total_a_pagar_grande, 0, Qt.AlignRight)
        right_summary_layout.addStretch()

        summary_layout.addLayout(left_summary_layout, 1)
        summary_layout.addLayout(right_summary_layout, 1)
        layout.addWidget(summary_panel)
        
        # --- Área Principal (Branca) ---
        main_content = QWidget()
        main_content_layout = QVBoxLayout(main_content)
        main_content_layout.setContentsMargins(20, 20, 20, 20)
        
        # Botões de Pagamento
        payment_layout = QHBoxLayout()
        payment_layout.setSpacing(15)
        self.btn_dinheiro = QPushButton("DINHEIRO (F6)")
        self.btn_dinheiro.setObjectName("btn_dinheiro")
        
        self.btn_dinheiro.clicked.connect(
            lambda: self.add_payment("Dinheiro", self.valor_dinheiro_input.text())
        )
        
        self.btn_cartao = QPushButton("CARTÃO (F7)")
        self.btn_cartao.setObjectName("btn_cartao")
        self.btn_cartao.clicked.connect(self._prompt_card_payment) 
        
        self.btn_doc = QPushButton("DOC. CRÉDITO (F8)")
        self.btn_doc.setObjectName("payment_method")
        self.btn_doc.clicked.connect(lambda: self.add_payment("Doc. Crédito"))
        
        self.btn_outros = QPushButton("OUTROS (F9)")
        self.btn_outros.setObjectName("btn_outros")
        self.btn_outros.clicked.connect(lambda: self.add_payment("Outros"))
        
        payment_layout.addWidget(self.btn_dinheiro, 1)
        payment_layout.addWidget(self.btn_cartao, 1)
        payment_layout.addWidget(self.btn_doc, 1)
        payment_layout.addWidget(self.btn_outros, 1)
        main_content_layout.addLayout(payment_layout)
        
        # Campo de Valor (para Dinheiro)
        self.valor_dinheiro_input = QLineEdit()
        self.valor_dinheiro_input.setPlaceholderText("Digite o valor e pressione ENTER...")
        self.valor_dinheiro_input.setValidator(self.validator)
        self.valor_dinheiro_input.setFont(QFont("Arial", 16))
        self.valor_dinheiro_input.returnPressed.connect(lambda: self.add_payment("Dinheiro", self.valor_dinheiro_input.text()))
        main_content_layout.addWidget(self.valor_dinheiro_input)
        
        main_content_layout.addStretch()
        layout.addWidget(main_content, 1)

        # --- Totais Finais (Rodapé) ---
        totals_frame = QFrame()
        totals_frame.setObjectName("totals_frame")
        totals_layout = QGridLayout(totals_frame)
        totals_layout.setContentsMargins(20, 10, 20, 10)
        
        totals_layout.addWidget(QLabel("R$ TOTAL A PAGAR", objectName="valor_label"), 0, 0)
        self.lbl_total_final = QLabel(f"R$ {self.total_a_pagar:.2f}", objectName="valor_display")
        totals_layout.addWidget(self.lbl_total_final, 1, 0)

        totals_layout.addWidget(QLabel("R$ VALOR PAGO", objectName="valor_label"), 0, 1)
        self.lbl_valor_pago = QLabel("R$ 0,00", objectName="valor_display")
        totals_layout.addWidget(self.lbl_valor_pago, 1, 1)

        totals_layout.addWidget(QLabel("R$ SALDO A PAGAR", objectName="valor_label"), 0, 2)
        self.lbl_saldo_a_pagar = QLabel(f"R$ {self.total_a_pagar:.2f}", objectName="valor_saldo_a_pagar") 
        totals_layout.addWidget(self.lbl_saldo_a_pagar, 1, 2)

        totals_layout.addWidget(QLabel("R$ TROCO", objectName="valor_label"), 0, 3)
        self.lbl_troco = QLabel("R$ 0,00", objectName="valor_troco")
        totals_layout.addWidget(self.lbl_troco, 1, 3)
        layout.addWidget(totals_frame)

        # --- Botões de Ação Finais ---
        action_layout = QHBoxLayout()
        action_layout.setContentsMargins(10, 10, 10, 10)
        action_layout.addWidget(QLabel("Vendedor: (FIXME)"), 0, Qt.AlignLeft)
        action_layout.addStretch()
        
        self.btn_cancelar = QPushButton("Cancelar (Esc)")
        self.btn_cancelar.setObjectName("btn_cancelar")
        self.btn_cancelar.clicked.connect(self.reject)
        
        self.btn_confirmar = QPushButton("Confirmar (ENTER)")
        self.btn_confirmar.setObjectName("btn_confirmar")
        self.btn_confirmar.clicked.connect(self.accept)
        
        action_layout.addWidget(self.btn_cancelar)
        action_layout.addWidget(self.btn_confirmar)
        layout.addLayout(action_layout)
        
        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0,0,0,0)
        dialog_layout.addWidget(main_frame)

    def _get_saldo_restante(self):
        """Calcula o valor que ainda falta pagar."""
        saldo = round(self.total_a_pagar - self.valor_pago, 2)
        return saldo if saldo > 0 else 0.0

    def add_payment(self, forma, valor_digitado=None, extra_data=None):
        """
        Adiciona um pagamento à lista.
        valor_digitado pode ser None, "" ou "30,00"
        """
        saldo_restante = self._get_saldo_restante()
        
        valor = 0.0
        # Se valor_digitado NÃO é None E NÃO é uma string vazia/só com espaços
        if valor_digitado and valor_digitado.strip(): 
            try:
                valor = float(valor_digitado.replace(',', '.'))
                if valor <= 0.009: # Se digitou "0" ou um valor inválido
                    self.valor_dinheiro_input.clear()
                    self.valor_dinheiro_input.setFocus()
                    return
            except ValueError:
                valor = 0.0 # Valor inválido, não faz nada
                return
        else: # Se não digitou valor (ex: F8, F9), assume o valor total restante
            if saldo_restante <= 0:
                return # Não adiciona pagamento se já estiver pago
            valor = saldo_restante

        # Prepara o dicionário de pagamento
        payment_data = {"forma": forma, "valor": valor}
        if extra_data:
            payment_data.update(extra_data) 

        self.pagamentos.append(payment_data)
        self.valor_pago += valor
        self._update_totals()
        
        if not valor_digitado and forma in ["Doc. Crédito", "Outros"]:
            self.btn_confirmar.setFocus()
        else:
            self.valor_dinheiro_input.setFocus()

    # --- FUNÇÃO CORRIGIDA ---
    def _prompt_card_payment(self):
        """Pergunta o tipo de pagamento de cartão (Débito/Crédito, Parcelas, TEF/POS)."""
        saldo_restante = self._get_saldo_restante()
        if saldo_restante <= 0:
            return

        # --- INÍCIO DA CORREÇÃO ---
        # 1. Define o valor a pagar (Pega do campo ou usa o saldo)
        valor_a_pagar = saldo_restante # Padrão
        valor_no_campo_str = self.valor_dinheiro_input.text().strip().replace(',', '.')
        
        if valor_no_campo_str: # Verifica se o campo não está vazio
            try:
                valor_manual = float(valor_no_campo_str)
                if valor_manual > 0.009:
                    # Se o valor digitado for maior que o saldo, usa o saldo
                    valor_a_pagar = min(valor_manual, saldo_restante)
            except ValueError:
                pass # Ignora texto inválido e usa o saldo_restante
        # --- FIM DA CORREÇÃO ---

        extra_data = {} # Dicionário para guardar os dados
        
        # 2. Pergunta Débito ou Crédito
        tipo_cartao_options = ["Crédito", "Débito"]
        dialog_tipo = CustomComboDialog(self, "Tipo de Cartão", 
                                        "O pagamento será em Débito ou Crédito?", 
                                        tipo_cartao_options)
        
        if dialog_tipo.exec_() != QDialog.Accepted:
            self.valor_dinheiro_input.setFocus() 
            return
        tipo_cartao = dialog_tipo.get_selected_item()
        extra_data['tipo_cartao'] = tipo_cartao

        # 3. Pergunta Parcelas (se for Crédito)
        if tipo_cartao == "Crédito":
            dialog_parc = CustomIntDialog(self, "Parcelamento", 
                                          "Número de parcelas:", 1, 1, 12, 1)
            if dialog_parc.exec_() != QDialog.Accepted:
                self.valor_dinheiro_input.setFocus() 
                return
            extra_data['parcelas'] = dialog_parc.get_value()
        else:
            extra_data['parcelas'] = 1

        # 4. Pergunta TEF ou POS
        tipo_pgto_options = ["POS (Maquininha)", "TEF (Integrado)"]
        dialog_pgto = CustomComboDialog(self, "Tipo de Pagamento", 
                                        "Selecione o tipo de pagamento com cartão:", 
                                        tipo_pgto_options)
        if dialog_pgto.exec_() != QDialog.Accepted:
            self.valor_dinheiro_input.setFocus() 
            return
        
        tipo_pgto = dialog_pgto.get_selected_item()
            
        if tipo_pgto == "TEF (Integrado)":
            QMessageBox.information(self, "Não Implementado", 
                "A integração TEF ainda não está disponível.")
            self.valor_dinheiro_input.setFocus() 
            return
            
        if tipo_pgto == "POS (Maquininha)":
            extra_data['tipo_pagamento'] = "POS"
            
            # --- CORREÇÃO: Passa o valor_a_pagar (calculado) em vez do saldo_restante
            dialog_pos = PosAuthDialog(valor_a_pagar, self)
            
            if dialog_pos.exec_() == QDialog.Accepted:
                valor, nsu, doc = dialog_pos.get_data()
                extra_data['nsu'] = nsu
                extra_data['doc'] = doc
                
                self.add_payment(forma="Cartão", 
                                 valor_digitado=str(valor).replace('.',','), 
                                 extra_data=extra_data)
            else:
                self.valor_dinheiro_input.setFocus()
    # --- FIM DA FUNÇÃO CORRIGIDA ---

    def _update_totals(self):
        """Atualiza todos os labels de valor (REGRA DE NEGÓCIO)."""
        saldo_restante = self._get_saldo_restante()
        troco = 0.0
        
        if saldo_restante <= 0:
            troco = self.valor_pago - self.total_a_pagar
            troco = round(troco, 2) if troco > 0 else 0.0
            
        self.lbl_valor_pago.setText(f"R$ {self.valor_pago:.2f}")
        self.lbl_saldo_a_pagar.setText(f"R$ {saldo_restante:.2f}")
        self.lbl_troco.setText(f"R$ {troco:.2f}")
        
        self.btn_confirmar.setEnabled(saldo_restante <= 0)
        self.troco = troco 
        
        self.valor_dinheiro_input.blockSignals(True)
        if saldo_restante > 0:
            self.valor_dinheiro_input.setText(f"{saldo_restante:.2f}".replace('.', ','))
            self.valor_dinheiro_input.selectAll()
        else:
            self.valor_dinheiro_input.clear()
            self.btn_confirmar.setFocus()
        self.valor_dinheiro_input.blockSignals(False)

    def get_payments(self):
        """Retorna a lista de pagamentos para o SalesForm."""
        return self.pagamentos
        
    def get_troco(self):
        """Retorna o valor do troco."""
        return self.troco

    def keyPressEvent(self, event):
        """ Sobrescrito para capturar F-Keys. """
        key = event.key()
        
        saldo_restante = self._get_saldo_restante()

        if saldo_restante <= 0:
            if key == Qt.Key_Return or key == Qt.Key_Enter:
                self.accept()
            elif key == Qt.Key_Escape:
                self.reject()
            else:
                super().keyPressEvent(event)
            return

        # Lógica de pagamento (enquanto ainda há saldo)
        if key == Qt.Key_F6:
            # F6 (Dinheiro) deve usar o valor do input, se houver
            valor_no_campo = self.valor_dinheiro_input.text()
            self.add_payment("Dinheiro", valor_no_campo if valor_no_campo.strip() else None)
        elif key == Qt.Key_F7:
            self._prompt_card_payment()
        elif key == Qt.Key_F8:
            self.add_payment("Doc. Crédito") # Paga o valor total restante
        elif key == Qt.Key_F9:
            self.add_payment("Outros") # Paga o valor total restante
        elif key == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.header_frame.geometry().contains(event.pos()):
                self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.old_pos and event.buttons() == Qt.LeftButton:
            delta = QPoint(event.globalPos() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.old_pos = None