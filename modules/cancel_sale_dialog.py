# -*- coding: utf-8 -*-
# modules/cancel_sale_dialog.py
import sqlite3
from PyQt5.QtWidgets import (
    QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
    QFrame, QLineEdit, QMessageBox, QComboBox, QGridLayout
)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt, QDate,  QDateTime
from database.db import get_connection
from .custom_dialogs import FramelessDialog

class CancelSaleDialog(FramelessDialog):
    """
    Diálogo para cancelar uma venda do CAIXA ATUAL.
    Lê motivos de cancelamento da tabela 'motivos_cancelamento'.
    """
    def __init__(self, current_caixa_id, terminal_id, pos_controller, parent=None):
        super().__init__(parent, title="Cancelar Venda")
        
        self.caixa_id = current_caixa_id
        self.terminal_id = terminal_id
        self.controller = pos_controller
        self.venda_encontrada = None 
        
        self.setFixedSize(450, 380) # Aumentei um pouco a altura
        
        self._build_ui()
        self._load_reasons()
        
        self.ok_button.setText("Confirmar Cancelamento")
        self.cancel_button.setText("Fechar")
        self.ok_button.setEnabled(False) 

        self.button_box.accepted.disconnect() 
        self.button_box.accepted.connect(self._confirm_cancellation)
        self.search_input.setFocus()

    def _build_ui(self):
        # Layout de Busca
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Digite o Nº da Venda...")
        self.search_input.setStyleSheet("font-size: 14px; padding: 5px;")
        self.search_input.returnPressed.connect(self._search_sale)
        
        self.btn_buscar = QPushButton("Buscar")
        self.btn_buscar.setStyleSheet("background-color: #0078d7; color: white; padding: 6px;")
        self.btn_buscar.clicked.connect(self._search_sale)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.btn_buscar)
        self.content_layout.addLayout(search_layout)
        
        # Área de Detalhes (Resultado)
        self.details_frame = QFrame()
        self.details_frame.setStyleSheet("background-color: white; border: 1px solid #ddd; border-radius: 5px;")
        details_layout = QGridLayout(self.details_frame)
        
        self.lbl_status = QLabel("Aguardando busca...")
        self.lbl_status.setStyleSheet("font-weight: bold; color: #555;")
        
        self.lbl_valor = QLabel("Valor: R$ 0,00")
        self.lbl_cliente = QLabel("Cliente: -")
        self.lbl_data = QLabel("Data: -") # Novo Label
        
        details_layout.addWidget(self.lbl_status, 0, 0, 1, 2)
        details_layout.addWidget(self.lbl_valor, 1, 0)
        details_layout.addWidget(self.lbl_data, 1, 1) # Posição da data
        details_layout.addWidget(self.lbl_cliente, 2, 0, 1, 2) # Cliente ocupa a linha de baixo
        
        self.content_layout.addWidget(self.details_frame)
        
        # Motivo
        self.content_layout.addWidget(QLabel("Selecione o Motivo do Cancelamento:", objectName="dialog_label"))
        self.reason_combo = QComboBox()
        self.content_layout.addWidget(self.reason_combo)

    def _load_reasons(self):
        """Carrega os motivos da tabela global do sistema."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, descricao FROM motivos_cancelamento WHERE ativo = 1 ORDER BY descricao")
            motivos = cur.fetchall()
            
            self.reason_combo.addItem("Selecione...", None)
            if not motivos:
                self.reason_combo.addItem("Erro de Digitação (Padrão)", 0)
                
            for m in motivos:
                self.reason_combo.addItem(m['descricao'], m['id'])
                
        except Exception as e:
            print(f"Erro ao carregar motivos: {e}")
        finally:
            conn.close()

    def _search_sale(self):
        numero_venda_str = self.search_input.text().strip()
        if not numero_venda_str.isdigit():
            QMessageBox.warning(self, "Inválido", "Digite apenas números.")
            return
            
        numero_venda = int(numero_venda_str)
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            # --- CORREÇÃO: Adicionado v.data_venda ao SELECT ---
            cur.execute("""
                SELECT v.id, v.total_final, v.status, v.data_venda, c.nome_razao
                FROM vendas v
                JOIN clientes c ON v.cliente_id = c.id
                WHERE v.numero_venda_terminal = ? 
                  AND v.terminal_id = ? 
                  AND v.caixa_id = ?
            """, (numero_venda, self.terminal_id, self.caixa_id))
            
            venda = cur.fetchone()
            
            if venda:
                self.venda_encontrada = dict(venda) # Converte para dict para podermos usar depois
                
                self.lbl_valor.setText(f"Valor: R$ {venda['total_final']:.2f}")
                self.lbl_cliente.setText(f"Cliente: {venda['nome_razao']}")
                
                # Formata a data para exibição
                try:
                    data_obj = QDateTime.fromString(venda['data_venda'], "yyyy-MM-dd HH:mm:ss")
                    self.lbl_data.setText(f"Data: {data_obj.toString('dd/MM/yyyy HH:mm')}")
                except:
                    self.lbl_data.setText(f"Data: {venda['data_venda']}")

                if venda['status'] == 'CANCELADA':
                    self.lbl_status.setText("ERRO: Venda já cancelada!")
                    self.lbl_status.setStyleSheet("color: #e74c3c; font-weight: bold;")
                    self.ok_button.setEnabled(False)
                else:
                    self.lbl_status.setText("Venda Encontrada")
                    self.lbl_status.setStyleSheet("color: #27AE60; font-weight: bold;")
                    self.ok_button.setEnabled(True)
            else:
                self.venda_encontrada = None
                self.lbl_status.setText("Venda não encontrada neste caixa.")
                self.lbl_status.setStyleSheet("color: #e74c3c; font-weight: bold;")
                self.lbl_valor.setText("Valor: -")
                self.lbl_cliente.setText("Cliente: -")
                self.lbl_data.setText("Data: -")
                self.ok_button.setEnabled(False)
                
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao buscar venda: {e}")
        finally:
            conn.close()

    def _confirm_cancellation(self):
        if not self.venda_encontrada: return
        
        motivo = self.reason_combo.currentText()
        if self.reason_combo.currentIndex() == 0: 
             QMessageBox.warning(self, "Motivo", "Selecione um motivo para o cancelamento.")
             return
             
        reply = QMessageBox.question(self, "Confirmar Cancelamento",
            f"Tem certeza que deseja CANCELAR a venda de R$ {self.venda_encontrada['total_final']:.2f}?\n\n"
            "Essa ação irá estornar o estoque e o financeiro.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
        if reply == QMessageBox.Yes:
            # Chama o controller para realizar o estorno no DB
            result = self.controller.cancel_sale(self.venda_encontrada['id'], motivo)
            
            if result['success']:
                # NÃO mostramos mensagem de sucesso aqui, pois o sales_form vai mostrar 
                # após imprimir o comprovante. Apenas fechamos o diálogo retornando Accepted.
                self.accept()
            else:
                QMessageBox.critical(self, "Erro", f"Falha ao cancelar: {result['error']}")