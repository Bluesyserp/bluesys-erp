# -*- coding: utf-8 -*-
# modules/categorias_financeiras_form.py
import sqlite3
import logging # <-- NOVO
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QGridLayout, QFrame, QTreeWidget, QTreeWidgetItem, 
    QAbstractItemView, QStackedWidget, QComboBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from database.db import get_connection

class CategoriasFinanceirasForm(QWidget):
    """
    Formulário para CRUD de Categorias Financeiras (Plano de Contas).
    Req. #3 e #8 do Módulo Financeiro.
    """
    def __init__(self, user_id, **kwargs):
        super().__init__()
        self.user_id = user_id
        self.current_category_id = None
        self.current_parent_id = None # Para criar subcategorias
        self.setWindowTitle("Cadastro de Categorias Financeiras (Plano de Contas)")
        
        # --- NOVO: Logger ---
        self.logger = logging.getLogger(__name__)
        
        self.category_nodes = {} # {id_categoria: QTreeWidgetItem}
        
        self._setup_styles()
        self._build_ui()
        self._connect_signals()
        
        self.load_categories()
        self.cancel_edit() # Esconde o formulário da direita

    def _setup_styles(self):
        self.setStyleSheet("""
            QWidget { background-color: #f8f8fb; font-family: 'Segoe UI'; }
            QLabel { font-weight: bold; color: #444; font-size: 13px; }
            QLabel.required::after { content: " *"; color: #e74c3c; }
            QFrame#main_panel {
                background-color: #fdfdfd;
                border: 1px solid #c0c0d0;
                border-radius: 8px;
            }
            QLabel#form_title {
                font-size: 16px; font-weight: bold; color: #005fa3;
                padding-bottom: 5px; border-bottom: 1px solid #eee;
            }
            QTreeWidget {
                border: 1px solid #c0c0d0;
                font-size: 14px;
            }
            QTreeWidget::item { padding: 6px; }
            QTreeWidget::item:selected { background-color: #0078d7; color: white; }
            QTreeWidget::item:!selected:hover { background-color: #e0e8f0; }
            
            QLineEdit, QComboBox {
                border: 1px solid #c0c0d0; border-radius: 5px; 
                padding: 6px; background-color: white; font-size: 13px;
            }
            QLineEdit[readOnly=true] { background-color: #f0f0f0; }
            QPushButton {
                background-color: #0078d7; color: white; border-radius: 6px;
                padding: 8px 15px; font-weight: bold; font-size: 13px;
            }
            QPushButton:hover { background-color: #005fa3; }
            QPushButton#deleteButton { background-color: #e74c3c; }
            QPushButton#deleteButton:hover { background-color: #c0392b; }
            QPushButton#cancelButton { background-color: #95A5A6; }
            QPushButton#cancelButton:hover { background-color: #7F8C8D; }
        """)

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        
        # --- 1. COLUNA ESQUERDA (Árvore) ---
        left_panel = QFrame()
        left_panel.setObjectName("main_panel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        left_layout.addWidget(QLabel("Plano de Contas (Receitas e Despesas):"))
        
        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderHidden(True) # Esconde cabeçalho
        left_layout.addWidget(self.category_tree, 1)
        
        tree_btn_layout = QHBoxLayout()
        self.btn_add_root = QPushButton("Adicionar Raiz (Receita/Despesa)")
        self.btn_add_sub = QPushButton("Adicionar Subcategoria")
        tree_btn_layout.addWidget(self.btn_add_root)
        tree_btn_layout.addWidget(self.btn_add_sub)
        left_layout.addLayout(tree_btn_layout)
        
        # --- 2. COLUNA DIREITA (Formulário) ---
        self.form_panel = QFrame()
        self.form_panel.setObjectName("main_panel")
        form_layout = QVBoxLayout(self.form_panel)
        form_layout.setContentsMargins(15, 10, 15, 15)
        
        self.form_title = QLabel("Selecione ou crie uma categoria", objectName="form_title")
        form_layout.addWidget(self.form_title)
        
        form_grid = QGridLayout()
        form_grid.setSpacing(10)
        
        self.nome_input = QLineEdit()
        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems(["RECEITA", "DESPESA"])
        self.parent_input = QLineEdit()
        self.parent_input.setReadOnly(True)
        
        form_grid.addWidget(QLabel("Nome da Categoria: *", objectName="required"), 0, 0)
        form_grid.addWidget(self.nome_input, 0, 1)
        form_grid.addWidget(QLabel("Tipo: *", objectName="required"), 1, 0)
        form_grid.addWidget(self.tipo_combo, 1, 1)
        form_grid.addWidget(QLabel("Categoria Pai:"), 2, 0)
        form_grid.addWidget(self.parent_input, 2, 1)
        form_grid.setColumnStretch(1, 1)
        
        form_layout.addLayout(form_grid)
        form_layout.addStretch()
        
        form_btn_layout = QHBoxLayout()
        form_btn_layout.addStretch()
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setObjectName("cancelButton")
        self.btn_excluir = QPushButton("Excluir")
        self.btn_excluir.setObjectName("deleteButton")
        self.btn_salvar = QPushButton("Salvar")
        form_btn_layout.addWidget(self.btn_cancelar)
        form_btn_layout.addWidget(self.btn_excluir)
        form_btn_layout.addWidget(self.btn_salvar)
        form_layout.addLayout(form_btn_layout)

        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(self.form_panel, 1)

    def _connect_signals(self):
        self.category_tree.itemSelectionChanged.connect(self._on_category_selected)
        self.btn_add_root.clicked.connect(self._show_new_form_root)
        self.btn_add_sub.clicked.connect(self._show_new_form_sub)
        self.btn_salvar.clicked.connect(self.save_category)
        self.btn_excluir.clicked.connect(self.delete_category)
        self.btn_cancelar.clicked.connect(self.cancel_edit)
            
    def load_categories(self):
        """Carrega as categorias financeiras e constrói a árvore."""
        self.category_tree.clear()
        self.category_nodes.clear()
        self.cancel_edit()
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            # Busca todas, ordenadas por nome
            query = "SELECT id, nome, tipo, parent_id FROM categorias_financeiras ORDER BY nome"
            cur.execute(query)
            
            all_categories = cur.fetchall()
            
            category_data_map = {cat['id']: dict(cat) for cat in all_categories}
            children_map = {}
            
            for cat_id, cat_data in category_data_map.items():
                parent_id = cat_data['parent_id']
                if parent_id not in children_map:
                    children_map[parent_id] = []
                children_map[parent_id].append(cat_id)

            def build_tree(parent_id, parent_item):
                if parent_id not in children_map:
                    return 
                    
                for cat_id in children_map[parent_id]:
                    cat_data = category_data_map[cat_id]
                    
                    item = QTreeWidgetItem(parent_item)
                    item.setText(0, cat_data['nome'])
                    item.setData(0, Qt.UserRole, cat_data['id'])
                    
                    # Define a cor (Receita = Verde, Despesa = Vermelho)
                    if cat_data['tipo'] == 'RECEITA':
                        item.setForeground(0, QColor("#008800")) # Verde escuro
                    else:
                        item.setForeground(0, QColor("#c0392b")) # Vermelho
                        
                    self.category_nodes[cat_id] = item
                    build_tree(cat_id, item) # Chama recursivamente

            # Inicia a construção a partir da raiz (None)
            build_tree(None, self.category_tree.invisibleRootItem())
            self.category_tree.expandAll()

        except Exception as e:
            self.logger.error(f"Erro ao carregar categorias: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao carregar categorias financeiras: {e}")
        finally:
            conn.close()

    def _on_category_selected(self):
        """Chamado quando um item da árvore é clicado."""
        selected_items = self.category_tree.selectedItems()
        if not selected_items:
            self.cancel_edit()
            return
            
        item = selected_items[0]
        category_id = item.data(0, Qt.UserRole)
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM categorias_financeiras WHERE id = ?", (category_id,))
            data = cur.fetchone()
            if not data:
                QMessageBox.warning(self, "Erro", "Categoria não encontrada.")
                self.cancel_edit()
                return
                
            self.form_panel.setEnabled(True)
            self.current_category_id = data['id']
            self.current_parent_id = data['parent_id']
            
            self.form_title.setText(f"Editando: {data['nome']}")
            self.nome_input.setText(data['nome'])
            self.tipo_combo.setCurrentText(data['tipo'])
            
            # Se for uma subcategoria, o tipo (RECEITA/DESPESA) é travado
            if data['parent_id']:
                cur.execute("SELECT nome FROM categorias_financeiras WHERE id = ?", (data['parent_id'],))
                parent_data = cur.fetchone()
                self.parent_input.setText(parent_data['name'] if parent_data else "N/A")
                self.tipo_combo.setEnabled(False) # Trava o tipo
            else:
                self.parent_input.setText("(Categoria Raiz)")
                self.tipo_combo.setEnabled(True) # Destrava o tipo
                
            self.btn_excluir.setEnabled(True)
            self.btn_add_sub.setEnabled(True)

        except Exception as e:
            self.logger.error(f"Erro ao carregar detalhes da categoria ID {category_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao carregar categoria: {e}")
        finally:
            conn.close()

    def _show_new_form_root(self):
        """Prepara o formulário para uma nova categoria RAIZ."""
        self._show_new_form(parent_id=None, parent_name="(Categoria Raiz)", parent_tipo=None)

    def _show_new_form_sub(self):
        """Prepara o formulário para uma nova SUB-CATEGORIA."""
        selected_items = self.category_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Seleção", "Selecione uma categoria pai na árvore primeiro.")
            return
            
        parent_item = selected_items[0]
        parent_id = parent_item.data(0, Qt.UserRole)
        parent_name = parent_item.text(0)
        
        # Busca o tipo do pai para travar o combo
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT tipo FROM categorias_financeiras WHERE id = ?", (parent_id,))
            parent_data = cur.fetchone()
            parent_tipo = parent_data['tipo'] if parent_data else None
        except Exception:
            parent_tipo = None
        finally:
            conn.close()
            
        self._show_new_form(parent_id=parent_id, parent_name=parent_name, parent_tipo=parent_tipo)

    def _show_new_form(self, parent_id, parent_name, parent_tipo):
        self.form_panel.setEnabled(True)
        self.category_tree.clearSelection()
        
        self.current_category_id = None # Modo INSERT
        self.current_parent_id = parent_id
        
        self.form_title.setText(f"Nova Subcategoria (filha de: {parent_name})")
        self.nome_input.clear()
        self.parent_input.setText(parent_name)
        
        if parent_tipo:
            # Se é filha, trava o tipo (uma despesa só pode ter filhas despesas)
            self.tipo_combo.setCurrentText(parent_tipo)
            self.tipo_combo.setEnabled(False)
        else:
            # Se é raiz, destrava o tipo
            self.tipo_combo.setCurrentIndex(0)
            self.tipo_combo.setEnabled(True)
            
        self.btn_excluir.setEnabled(False)
        self.nome_input.setFocus()

    def cancel_edit(self):
        """Limpa e desabilita o formulário de edição."""
        self.form_panel.setEnabled(False)
        self.category_tree.clearSelection()
        
        self.current_category_id = None
        self.current_parent_id = None
        
        self.form_title.setText("Selecione ou crie uma categoria")
        self.nome_input.clear()
        self.tipo_combo.setCurrentIndex(0)
        self.tipo_combo.setEnabled(True)
        self.parent_input.clear()
        
        self.btn_excluir.setEnabled(False)
        self.btn_add_sub.setEnabled(False) # Só habilita quando seleciona

    def save_category(self):
        nome = self.nome_input.text().strip()
        tipo = self.tipo_combo.currentText()
        
        if not nome:
            QMessageBox.warning(self, "Campo Obrigatório", "O campo 'Nome da Categoria' é obrigatório.")
            return
            
        data = {
            "nome": nome,
            "tipo": tipo,
            "parent_id": self.current_parent_id
        }
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            
            if self.current_category_id:
                # --- UPDATE ---
                data["id"] = self.current_category_id
                query = """
                    UPDATE categorias_financeiras 
                    SET nome = :nome, tipo = :tipo, parent_id = :parent_id
                    WHERE id = :id
                """
                msg = "Categoria atualizada com sucesso!"
                action_verb = "ATUALIZOU"
            else:
                # --- INSERT ---
                fields = ", ".join(data.keys())
                placeholders = ", ".join([f":{k}" for k in data.keys()])
                query = f"INSERT INTO categorias_financeiras ({fields}) VALUES ({placeholders})"
                msg = "Categoria salva com sucesso!"
                action_verb = "CRIOU"

            cur.execute(query, data)
            conn.commit()
            
            # --- LOG ADICIONADO ---
            self.logger.info(f"Usuário {self.user_id} {action_verb} categoria financeira: '{data['nome']}' (Tipo: {data['tipo']}).")
            
            QMessageBox.information(self, "Sucesso", msg)
            self.load_categories() # Recarrega a árvore
            self.cancel_edit()

        except Exception as e:
            self.logger.error(f"Erro ao salvar categoria financeira: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao salvar categoria: {e}")
        finally:
            conn.close()
            
    def delete_category(self):
        if not self.current_category_id:
            QMessageBox.warning(self, "Erro", "Nenhuma categoria selecionada.")
            return

        # 1. Verifica se tem filhos
        item = self.category_tree.selectedItems()[0]
        if item.childCount() > 0:
            QMessageBox.critical(self, "Erro", "Não é possível excluir. Esta categoria contém subcategorias.")
            return
            
        conn = get_connection()
        try:
            cur = conn.cursor()
            
            # 2. Verifica se está em uso por um título ou lançamento
            cur.execute("SELECT id FROM titulos_financeiros WHERE categoria_id = ?", (self.current_category_id,))
            titulo_usando = cur.fetchone()
            cur.execute("SELECT id FROM lancamentos_financeiros WHERE categoria_id = ?", (self.current_category_id,))
            lanc_usando = cur.fetchone()
            
            if titulo_usando or lanc_usando:
                QMessageBox.critical(self, "Erro", "Não é possível excluir. Esta categoria está em uso por Títulos ou Lançamentos financeiros.")
                return

            # 3. Confirmação
            reply = QMessageBox.question(self, "Confirmação",
                f"Tem certeza que deseja excluir a categoria '{self.nome_input.text()}'?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                
            if reply == QMessageBox.No:
                return
            
            # 4. Exclusão
            cur.execute("DELETE FROM categorias_financeiras WHERE id = ?", (self.current_category_id,))
            conn.commit()
            
            # --- LOG ADICIONADO ---
            self.logger.info(f"Usuário {self.user_id} EXCLUIU categoria financeira ID {self.current_category_id} ('{self.nome_input.text()}').")
            
            QMessageBox.information(self, "Sucesso", "Categoria excluída com sucesso.")
            self.load_categories()
            self.cancel_edit()
            
        except Exception as e:
            self.logger.error(f"Erro ao excluir categoria financeira: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao excluir categoria: {e}")
        finally:
            conn.close()