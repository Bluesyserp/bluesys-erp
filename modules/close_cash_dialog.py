# modules/close_cash_dialog.py
import sqlite3
from PyQt5.QtWidgets import (
    QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout,
    QMessageBox, QDoubleSpinBox
)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt, QPoint
from database.db import get_connection

class CloseCashDialog(QDialog):
    def __init__(self, caixa_id, terminal_name, parent=None):
        super().__init__(parent)
        self.caixa_id = caixa_id
        self.terminal_name = terminal_name
        self.old_pos = None
        
        self.expected_totals = {}  # {'Dinheiro': 100.0, 'Pix': 50.0}
        self.informed_totals = {}  # {'Dinheiro': 0.0, 'Pix': 0.0}
        self.differences = {}      # {'Dinheiro': -100.0, 'Pix': -50.0}

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(600, 450) # Aumentei um pouco a altura
        self.setModal(True)
        
        self._setup_styles()
        self._build_ui()
        self._load_expected_values()
        
        if parent:
            parent_global_center = parent.mapToGlobal(parent.rect().center())
            self.move(parent_global_center - self.rect().center())

    def _setup_styles(self):
        self.setStyleSheet("""
            QDialog { background-color: transparent; }
            QFrame#main_frame {
                background-color: #f8f8fb; border-radius: 8px; border: 1px solid #c0c0d0;
            }
            QFrame#title_bar {
                background-color: #e0e8f0; border-top-left-radius: 8px;
                border-top-right-radius: 8px; border-bottom: 1px solid #c0c0d0;
                height: 35px;
            }
            QLabel#title_label { font-size: 14px; font-weight: bold; color: #333; }
            QLabel.total_label { font-size: 16px; font-weight: bold; color: #555; }
            QLabel.total_value { font-size: 16px; font-weight: bold; color: #0078d7; }
            QLabel.total_diff_ok { color: #2ECC71; }
            QLabel.total_diff_bad { color: #e74c3c; }
            QLabel.total_diff_surplus { color: #0078d7; }
            
            QLabel#info_cancelado { font-size: 12px; color: #e74c3c; font-weight: bold; }

            QTableWidget {
                border: 1px solid #c0c0d0;
                selection-background-color: #0078d7; font-size: 14px;
            }
            QHeaderView::section {
                background-color: #e8e8e8; padding: 8px;
                border: 1px solid #c0c0d0; font-weight: bold; font-size: 14px;
            }

            QDoubleSpinBox {
                border: 1px solid #c0c0d0; border-radius: 6px; 
                padding: 6px; background-color: white; 
                font-size: 14px; font-weight: bold;
                color: #333333;
                selection-background-color: #0078d7;
                selection-color: #FFFFFF;
            }
            QDoubleSpinBox:disabled {
                background-color: #f2f2f2;
                color: #888888;
            }

            QPushButton#btn_confirmar { background-color: #0078d7; color: white; padding: 8px 15px; }
            QPushButton#btn_cancelar { background-color: #e74c3c; color: white; padding: 8px 15px; }
        """)

    def _build_ui(self):
        main_frame = QFrame(self)
        main_frame.setObjectName("main_frame")
        layout = QVBoxLayout(main_frame)
        layout.setContentsMargins(1, 1, 1, 10)

        # Barra de título
        self.title_bar = QFrame()
        self.title_bar.setObjectName("title_bar")
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 0, 10, 0)
        self.title_label = QLabel(f"Conferência de Fechamento - Terminal: {self.terminal_name}", objectName="title_label")
        title_layout.addWidget(self.title_label)
        layout.addWidget(self.title_bar)

        # Tabela
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Pagamento", "Valor Registrado", "Valor Informado", "Diferença"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        # Totais
        total_frame = QFrame()
        total_layout = QGridLayout(total_frame)
        
        # --- NOVO: Label Informativo de Cancelamentos ---
        self.lbl_info_cancelado = QLabel("Total Cancelado: R$ 0,00", objectName="info_cancelado")
        total_layout.addWidget(self.lbl_info_cancelado, 0, 0, 1, 2, Qt.AlignLeft)
        
        total_layout.addWidget(QLabel("TOTAL REGISTRADO:", objectName="total_label"), 1, 0)
        self.lbl_total_registrado = QLabel("R$ 0,00", objectName="total_value")
        total_layout.addWidget(self.lbl_total_registrado, 1, 1, Qt.AlignRight)
        
        total_layout.addWidget(QLabel("TOTAL INFORMADO:", objectName="total_label"), 2, 0)
        self.lbl_total_informado = QLabel("R$ 0,00", objectName="total_value")
        total_layout.addWidget(self.lbl_total_informado, 2, 1, Qt.AlignRight)
        
        total_layout.addWidget(QLabel("DIFERENÇA TOTAL:", objectName="total_label"), 3, 0)
        self.lbl_total_diferenca = QLabel("R$ 0,00", objectName="total_value")
        total_layout.addWidget(self.lbl_total_diferenca, 3, 1, Qt.AlignRight)
        
        layout.addWidget(total_frame)

        # Botões
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_cancelar = QPushButton("Cancelar (Esc)")
        self.btn_cancelar.setObjectName("btn_cancelar")
        self.btn_cancelar.clicked.connect(self.reject)
        self.btn_confirmar = QPushButton("Confirmar Fechamento (F10)")
        self.btn_confirmar.setObjectName("btn_confirmar")
        self.btn_confirmar.setShortcut("F10")
        self.btn_confirmar.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_cancelar)
        btn_layout.addWidget(self.btn_confirmar)
        layout.addLayout(btn_layout)

        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addWidget(main_frame)

    def _load_expected_values(self):
        """Busca no DB os valores que o sistema espera (Valor Registrado)."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            
            # 1. Busca Totais de Vendas por Pagamento (SOMENTE FINALIZADAS)
            # --- CORREÇÃO: Filtra vendas CANCELADAS para não cobrar do operador ---
            query_vendas = """
                SELECT vp.forma, SUM(vp.valor) as total_forma
                FROM vendas_pagamentos vp
                JOIN vendas v ON vp.venda_id = v.id
                WHERE v.caixa_id = ? AND v.status = 'FINALIZADA'
                GROUP BY vp.forma
            """
            cur.execute(query_vendas, (self.caixa_id,))
            rows_vendas = cur.fetchall()
            
            # --- NOVO: Busca Total Cancelado (apenas informativo) ---
            cur.execute("SELECT SUM(total_final) as total_canc FROM vendas WHERE caixa_id = ? AND status = 'CANCELADA'", (self.caixa_id,))
            total_cancelado = cur.fetchone()['total_canc'] or 0.0
            self.lbl_info_cancelado.setText(f"Vendas Canceladas neste caixa: R$ {total_cancelado:.2f}")
            if total_cancelado > 0:
                self.lbl_info_cancelado.setVisible(True)
            else:
                self.lbl_info_cancelado.setVisible(False)
            
            # 2. Busca Saldo Inicial
            cur.execute("SELECT valor_inicial FROM caixa_sessoes WHERE id = ?", (self.caixa_id,))
            abertura = cur.fetchone()
            suprimento_inicial = abertura['valor_inicial'] if abertura else 0.0

            # 3. Busca Sangrias e Suprimentos
            query_mov = """
                SELECT tipo, SUM(valor) as total_mov
                FROM caixa_movimentacoes
                WHERE caixa_id = ?
                GROUP BY tipo
            """
            cur.execute(query_mov, (self.caixa_id,))
            movimentacoes = cur.fetchall()

            suprimentos_mov = 0.0
            sangrias_mov = 0.0
            for mov in movimentacoes:
                if mov['tipo'] == 'SUPRIMENTO':
                    suprimentos_mov = mov['total_mov']
                elif mov['tipo'] == 'SANGRIA':
                    sangrias_mov = mov['total_mov']

            # Inicializa formas de pagamento padrão
            formas_pagamento = {"Dinheiro": 0.0, "Pix": 0.0, "Cartão": 0.0, "Doc. Crédito": 0.0, "Outros": 0.0}
            
            # Adiciona vendas
            for row in rows_vendas:
                forma = row['forma']
                if forma in formas_pagamento:
                    formas_pagamento[forma] += row['total_forma']
                else:
                    formas_pagamento[forma] = row['total_forma']
            
            # 4. Ajusta o Dinheiro com Abertura, Sangria e Suprimento
            formas_pagamento["Dinheiro"] += suprimento_inicial
            formas_pagamento["Dinheiro"] += suprimentos_mov
            formas_pagamento["Dinheiro"] -= sangrias_mov
            
            self.expected_totals = formas_pagamento
            self._populate_table()

        except Exception as e:
            QMessageBox.critical(self, "Erro de DB", f"Erro ao calcular totais do caixa: {e}")
        finally:
            conn.close()

    def _populate_table(self):
        self.table.setRowCount(0)
        self.table.verticalHeader().setDefaultSectionSize(36)

        for forma, valor_registrado in self.expected_totals.items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(forma))
            
            item_registrado = QTableWidgetItem(f"R$ {valor_registrado:.2f}")
            item_registrado.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 1, item_registrado)
            
            spin_box = QDoubleSpinBox()
            spin_box.setRange(0.00, 9999999.99)
            spin_box.setValue(0.00)
            spin_box.setButtonSymbols(QDoubleSpinBox.NoButtons)
            spin_box.setSingleStep(50)
            spin_box.setAlignment(Qt.AlignRight)

            spin_box.setStyleSheet("""
                QDoubleSpinBox {
                    border: 1px solid #c0c0d0;
                    border-radius: 6px;
                    background-color: #ffffff;
                    font-size: 14px;
                    font-weight: bold;
                    color: #333333;
                    selection-background-color: #0078d7;
                    selection-color: #ffffff;
                    padding: 2px 8px 2px 8px;
                    margin-top: 0px;
                    margin-bottom: 0px;
                }
                QDoubleSpinBox:disabled {
                    background-color: #f2f2f2;
                    color: #888888;
                }
            """)
            spin_box.setFixedHeight(26)

            spin_box.valueChanged.connect(
                lambda valor_informado, r=row, f=forma: self._on_value_changed(valor_informado, r, f)
            )

            self.table.setCellWidget(row, 2, spin_box)
            
            diferenca_inicial = valor_registrado - 0.0
            if abs(diferenca_inicial) < 0.01:
                texto_inicial = "R$ 0,00"
            else:
                texto_inicial = f"- R$ {abs(diferenca_inicial):.2f}"

            item_diferenca = QTableWidgetItem(texto_inicial)
            item_diferenca.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_diferenca.setForeground(QColor(Qt.black))
            self.table.setItem(row, 3, item_diferenca)
            
            self.informed_totals[forma] = 0.0
            self.differences[forma] = diferenca_inicial

        self._update_total_labels()

    def _on_value_changed(self, valor_informado, row, forma):
        valor_registrado = self.expected_totals.get(forma, 0.0)
        diferenca = valor_registrado - valor_informado

        self.informed_totals[forma] = valor_informado
        self.differences[forma] = diferenca

        item_dif = self.table.item(row, 3)
        
        if abs(diferenca) < 0.01:
            texto = "R$ 0,00"
        elif diferenca > 0: # Falta (Registrado > Informado)
            texto = f"- R$ {abs(diferenca):.2f}"
        else: # Sobra (Registrado < Informado)
            texto = f"R$ {abs(diferenca):.2f}"
            
        item_dif.setText(texto)
        item_dif.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        item_dif.setForeground(QColor(Qt.black))

        self._update_total_labels()


    def _update_total_labels(self):
        total_reg = sum(self.expected_totals.values())
        total_inf = sum(self.informed_totals.values())
        total_diff = total_reg - total_inf

        self.lbl_total_registrado.setText(f"R$ {total_reg:.2f}")
        self.lbl_total_informado.setText(f"R$ {total_inf:.2f}")

        if abs(total_diff) < 0.01:
            texto = "R$ 0,00"
            cor = "#2ECC71"
        elif total_diff > 0:
            texto = f"- R$ {abs(total_diff):.2f}  Falta"
            cor = "#E74C3C"
        else:
            texto = f"R$ {abs(total_diff):.2f}  Sobra"
            cor = "#0078D7" 

        self.lbl_total_diferenca.setText(texto)
        self.lbl_total_diferenca.setStyleSheet(f"color: {cor}; font-weight: bold;")

    def get_data(self):
        total_reg = sum(self.expected_totals.values())
        total_inf = sum(self.informed_totals.values())
        total_diff = total_reg - total_inf
        return {"calculado": total_reg, "informado": total_inf, "diferenca": total_diff}

    # Movimento da janela
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.title_bar.geometry().contains(event.pos()):
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.old_pos and event.buttons() == Qt.LeftButton:
            delta = QPoint(event.globalPos() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.old_pos = None