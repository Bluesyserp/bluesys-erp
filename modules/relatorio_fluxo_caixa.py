# -*- coding: utf-8 -*-
# modules/relatorio_fluxo_caixa.py
import sqlite3
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, 
    QAbstractItemView, QDateEdit, QCalendarWidget, QComboBox,
    QFrame, QGridLayout, QFileDialog
)
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtCore import Qt, QDate
from database.db import get_connection
from .report_exporter import export_to_pdf, export_to_xlsx

class RelatorioFluxoCaixa(QWidget):
    """
    Relatório de Fluxo de Caixa (Extrato por Período)
    para uma conta financeira específica.
    """
    def __init__(self, user_id, **kwargs):
        super().__init__()
        self.user_id = user_id
        self.setWindowTitle("Relatório de Fluxo de Caixa (Extrato por Conta)")
        
        self.contas_map = {}
        self.empresa_id = 1 # Assume empresa 1
        
        self._setup_styles()
        self._build_ui()
        self._connect_signals()
        
        self._load_filters()
        self.load_report(show_message=False) 

    def _setup_styles(self):
        self.setStyleSheet("""
            QWidget { background-color: #f8f8fb; font-family: 'Segoe UI'; }
            QLabel { font-weight: bold; color: #444; font-size: 13px; }
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
            QDateEdit, QComboBox {
                border: 1px solid #c0c0d0; border-radius: 5px; 
                padding: 6px; background-color: white;
            }
            QPushButton {
                background-color: #0078d7; color: white; border-radius: 6px;
                padding: 8px 15px; font-weight: bold;
            }
            QPushButton:hover { background-color: #005fa3; }
            
            QPushButton#btn_export_pdf { background-color: #c0392b; }
            QPushButton#btn_export_pdf:hover { background-color: #e74c3c; }
            QPushButton#btn_export_xlsx { background-color: #16A085; }
            QPushButton#btn_export_xlsx:hover { background-color: #1ABC9C; }
            QFrame#filter_frame, QFrame#summary_frame {
                background-color: #fdfdfd;
                border: 1px solid #c0c0d0;
                border-radius: 8px;
            }
            /* Estilo para os labels de resumo */
            QLabel.summary_label { font-size: 14px; font-weight: bold; color: #555; }
            QLabel.summary_value { font-size: 16px; font-weight: bold; }
            QLabel#saldo_anterior { color: #555; }
            QLabel#total_entradas { color: #27AE60; } /* Verde */
            QLabel#total_saidas { color: #c0392b; } /* Vermelho */
            QLabel#saldo_atual { color: #0078d7; font-size: 18px; } /* Azul */
        """)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        
        # --- Filtros ---
        filter_frame = QFrame()
        filter_frame.setObjectName("filter_frame")
        filter_layout = QGridLayout(filter_frame)
        filter_layout.setContentsMargins(10, 10, 10, 10)
        filter_layout.setSpacing(10)

        filter_layout.addWidget(QLabel("Conta Financeira:"), 0, 0)
        self.conta_combo = QComboBox()
        filter_layout.addWidget(self.conta_combo, 0, 1)

        filter_layout.addWidget(QLabel("Data Início:"), 1, 0)
        self.date_start = QDateEdit()
        self.date_start.setDate(QDate.currentDate().addDays(-QDate.currentDate().day() + 1)) # Primeiro dia do mês
        self.date_start.setCalendarPopup(True)
        filter_layout.addWidget(self.date_start, 1, 1)
        
        filter_layout.addWidget(QLabel("Data Fim:"), 1, 2)
        self.date_end = QDateEdit(QDate.currentDate())
        self.date_end.setCalendarPopup(True)
        filter_layout.addWidget(self.date_end, 1, 3)
        
        self.btn_filtrar = QPushButton("Gerar Relatório")
        filter_layout.addWidget(self.btn_filtrar, 1, 4)
        
        export_layout = QHBoxLayout()
        self.btn_export_pdf = QPushButton("Exportar PDF")
        self.btn_export_pdf.setObjectName("btn_export_pdf")
        self.btn_export_xlsx = QPushButton("Exportar XLSX")
        self.btn_export_xlsx.setObjectName("btn_export_xlsx")
        export_layout.addStretch()
        export_layout.addWidget(self.btn_export_pdf)
        export_layout.addWidget(self.btn_export_xlsx)
        
        self.btn_export_pdf.setEnabled(False)
        self.btn_export_xlsx.setEnabled(False) 

        filter_layout.addLayout(export_layout, 1, 5)
        filter_layout.setColumnStretch(6, 1)
        main_layout.addWidget(filter_frame)
        
        # --- Resumo (Saldos) ---
        summary_frame = QFrame()
        summary_frame.setObjectName("summary_frame")
        summary_layout = QHBoxLayout(summary_frame)
        summary_layout.setContentsMargins(15, 10, 15, 10)
        
        def create_summary_box(title_text, object_name):
            layout = QVBoxLayout()
            lbl_title = QLabel(title_text, objectName="summary_label")
            lbl_value = QLabel("R$ 0,00", objectName=object_name)
            layout.addWidget(lbl_title)
            layout.addWidget(lbl_value)
            return layout, lbl_value

        saldo_ant_layout, self.lbl_saldo_anterior = create_summary_box("SALDO ANTERIOR", "saldo_anterior")
        entradas_layout, self.lbl_total_entradas = create_summary_box("TOTAL ENTRADAS", "total_entradas")
        saidas_layout, self.lbl_total_saidas = create_summary_box("TOTAL SAÍDAS", "total_saidas")
        saldo_atual_layout, self.lbl_saldo_atual = create_summary_box("SALDO ATUAL", "saldo_atual")
        
        summary_layout.addLayout(saldo_ant_layout)
        summary_layout.addStretch()
        summary_layout.addLayout(entradas_layout)
        summary_layout.addStretch()
        summary_layout.addLayout(saidas_layout)
        summary_layout.addStretch()
        summary_layout.addLayout(saldo_atual_layout)
        main_layout.addWidget(summary_frame)

        # --- Tabela de Movimentações ---
        self.report_table = QTableWidget()
        self.report_table.setColumnCount(5)
        self.report_table.setHorizontalHeaderLabels(["ID Mov.", "Data", "Tipo", "Descrição", "Valor (R$)"])
        self.report_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.report_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.report_table.setColumnHidden(0, True)
        
        main_layout.addWidget(self.report_table)

    def _load_filters(self):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, nome FROM contas_financeiras WHERE empresa_id = ? AND active = 1 ORDER BY nome", (self.empresa_id,))
            self.conta_combo.addItem("Selecione a Conta...", None)
            for conta in cur.fetchall():
                self.conta_combo.addItem(conta['nome'], conta['id'])
            
            # Tenta selecionar a primeira conta (que não seja "Selecione")
            if self.conta_combo.count() > 1:
                self.conta_combo.setCurrentIndex(1)
                
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar filtros: {e}")
        finally:
            conn.close()

    def _connect_signals(self):
        self.btn_filtrar.clicked.connect(lambda: self.load_report(show_message=True))
        self.btn_export_pdf.clicked.connect(self._export_pdf)
        self.btn_export_xlsx.clicked.connect(self._export_xlsx)

    def load_report(self, show_message=False):
        """Carrega os dados do relatório com base nos filtros."""
        self.report_table.setRowCount(0)
        
        date_start_str = self.date_start.date().toString("yyyy-MM-dd")
        date_end_str = self.date_end.date().toString("yyyy-MM-dd") + " 23:59:59"
        conta_id = self.conta_combo.currentData()
        
        if conta_id is None:
            if show_message:
                QMessageBox.warning(self, "Seleção", "Por favor, selecione uma Conta Financeira.")
            return

        conn = get_connection()
        try:
            cur = conn.cursor()
            
            # 1. Buscar Saldo Inicial da Conta
            cur.execute("SELECT saldo_inicial FROM contas_financeiras WHERE id = ?", (conta_id,))
            saldo_inicial = cur.fetchone()['saldo_inicial'] or 0.0
            
            # 2. Buscar Movimentações ANTERIORES ao período
            cur.execute("""
                SELECT SUM(CASE WHEN tipo_movimento = 'ENTRADA' THEN valor ELSE -valor END) as total_anterior
                FROM movimentacoes_contas
                WHERE conta_id = ? AND data_movimento < ?
            """, (conta_id, date_start_str))
            
            mov_anterior = cur.fetchone()['total_anterior'] or 0.0
            saldo_anterior = saldo_inicial + mov_anterior
            
            # 3. Buscar Movimentações DO período
            cur.execute("""
                SELECT data_movimento, tipo_movimento, descricao, valor 
                FROM movimentacoes_contas
                WHERE conta_id = ? AND data_movimento BETWEEN ? AND ?
                ORDER BY data_movimento, id
            """, (conta_id, date_start_str, date_end_str))
            
            movimentacoes = cur.fetchall()
            
            total_entradas = 0.0
            total_saidas = 0.0
            
            for mov in movimentacoes:
                row = self.report_table.rowCount()
                self.report_table.insertRow(row)
                
                valor = mov['valor']
                if mov['tipo_movimento'] == 'SAIDA':
                    total_saidas += valor
                    valor = -valor
                    color = QColor("#c0392b") # Vermelho
                else:
                    total_entradas += valor
                    color = QColor("#27AE60") # Verde
                
                item_valor = QTableWidgetItem(f"R$ {valor:.2f}")
                item_valor.setForeground(color)
                item_valor.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                
                self.report_table.setItem(row, 0, QTableWidgetItem(str(mov['id']))) # Escondido
                self.report_table.setItem(row, 1, QTableWidgetItem(mov['data_movimento']))
                self.report_table.setItem(row, 2, QTableWidgetItem(mov['tipo_movimento']))
                self.report_table.setItem(row, 3, QTableWidgetItem(mov['descricao']))
                self.report_table.setItem(row, 4, item_valor)
            
            # 4. Calcular Saldo Final
            saldo_atual = saldo_anterior + total_entradas - total_saidas
            
            # 5. Atualizar Labels de Resumo
            self.lbl_saldo_anterior.setText(f"R$ {saldo_anterior:.2f}")
            self.lbl_total_entradas.setText(f"R$ {total_entradas:.2f}")
            self.lbl_total_saidas.setText(f"R$ {total_saidas:.2f}")
            self.lbl_saldo_atual.setText(f"R$ {saldo_atual:.2f}")
            
            if saldo_atual < 0:
                self.lbl_saldo_atual.setStyleSheet("color: #e74c3c;") # Vermelho
            else:
                self.lbl_saldo_atual.setStyleSheet("color: #0078d7;") # Azul
            
            count = self.report_table.rowCount()
            if show_message:
                QMessageBox.information(self, "Relatório", f"{count} movimentações encontradas no período.")
            
            if count > 0:
                self.btn_export_pdf.setEnabled(True)
                self.btn_export_xlsx.setEnabled(True)
            else:
                self.btn_export_pdf.setEnabled(False)
                self.btn_export_xlsx.setEnabled(False)
                
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar relatório: {e}")
        finally:
            conn.close()

    def _get_table_data(self):
        """Lê os dados e cabeçalhos da QTableWidget para exportação."""
        headers = []
        for j in range(self.report_table.columnCount()):
            if not self.report_table.isColumnHidden(j):
                headers.append(self.report_table.horizontalHeaderItem(j).text())
        
        data = []
        for i in range(self.report_table.rowCount()):
            row_data = []
            for j in range(self.report_table.columnCount()):
                if not self.report_table.isColumnHidden(j):
                    item = self.report_table.item(i, j)
                    row_data.append(item.text() if item else "")
            data.append(row_data)
        return headers, data

    def _export_pdf(self):
        try:
            headers, data = self._get_table_data()
            conta_nome = self.conta_combo.currentText()
            title = f"Fluxo de Caixa - {conta_nome} ({self.date_start.text()} a {self.date_end.text()})"
            
            # Adiciona o resumo no topo do PDF
            summary_data = [
                ["Saldo Anterior:", f"{self.lbl_saldo_anterior.text()}"],
                ["Total Entradas:", f"{self.lbl_total_entradas.text()}"],
                ["Total Saídas:", f"{self.lbl_total_saidas.text()}"],
                ["Saldo Atual:", f"{self.lbl_saldo_atual.text()}"]
            ]
            # O exportador de PDF não suporta dados extras, então passamos apenas os dados da tabela
            
            export_to_pdf(headers, data, title, self)
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Exportar PDF", f"Falha ao gerar PDF: {e}")
            
    def _export_xlsx(self):
        try:
            headers, data = self._get_table_data()
            # TODO: Adicionar o resumo no Excel também
            export_to_xlsx(headers, data, self)
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Exportar XLSX", f"Falha ao gerar Excel: {e}")