# -*- coding: utf-8 -*-
# modules/category_form.py
import sqlite3
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QGridLayout, QFrame, QTreeWidget, QTreeWidgetItem, 
    QAbstractItemView, QStackedWidget, QComboBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from database.db import get_connection

class CategoryForm(QWidget):
    """
    Formulário para CRUD de Classes de Produtos (hierárquico).
    (Anteriormente 'Categorias')
    """
    def __init__(self, user_id, **kwargs):
        super().__init__()
        self.user_id = user_id
        self.current_category_id = None
        self.current_parent_id = None # Para criar subclasses
        self.setWindowTitle("Cadastro de Classes de Produtos")
        
        self.company_map = {} # {id_empresa: razao_social}
        self.category_nodes = {} # {id_categoria: QTreeWidgetItem}
        
        self._setup_styles()
        self._build_ui()
        self._connect_signals()
        
        self._load_empresas_combobox()
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
        
        filter_layout = QGridLayout()
        filter_layout.addWidget(QLabel("Empresa:"), 0, 0)
        self.empresa_combo = QComboBox()
        filter_layout.addWidget(self.empresa_combo, 0, 1)
        left_layout.addLayout(filter_layout)
        
        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderHidden(True) # Esconde cabeçalho
        left_layout.addWidget(self.category_tree, 1)
        
        tree_btn_layout = QHBoxLayout()
        self.btn_add_root = QPushButton("Adicionar Raiz")
        self.btn_add_sub = QPushButton("Adicionar Subclasse")
        tree_btn_layout.addWidget(self.btn_add_root)
        tree_btn_layout.addWidget(self.btn_add_sub)
        left_layout.addLayout(tree_btn_layout)
        
        # --- 2. COLUNA DIREITA (Formulário) ---
        self.form_panel = QFrame()
        self.form_panel.setObjectName("main_panel")
        form_layout = QVBoxLayout(self.form_panel)
        form_layout.setContentsMargins(15, 10, 15, 15)
        
        self.form_title = QLabel("Selecione ou crie uma classe", objectName="form_title")
        form_layout.addWidget(self.form_title)
        
        form_grid = QGridLayout()
        form_grid.setSpacing(10)
        
        self.nome_input = QLineEdit()
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Ex: ELE, CEL, ACESS (Opcional)")
        self.status_combo = QComboBox()
        self.status_combo.addItems(["1 - Ativo", "2 - Inativo"])
        self.parent_input = QLineEdit()
        self.parent_input.setReadOnly(True)
        
        form_grid.addWidget(QLabel("Nome da Classe: *", objectName="required"), 0, 0)
        form_grid.addWidget(self.nome_input, 0, 1)
        form_grid.addWidget(QLabel("Código Curto (p/ SKU):"), 1, 0)
        form_grid.addWidget(self.code_input, 1, 1)
        form_grid.addWidget(QLabel("Status:"), 2, 0)
        form_grid.addWidget(self.status_combo, 2, 1)
        form_grid.addWidget(QLabel("Classe Pai:"), 3, 0)
        form_grid.addWidget(self.parent_input, 3, 1)
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
        self.empresa_combo.currentIndexChanged.connect(self.load_categories)
        self.category_tree.itemSelectionChanged.connect(self._on_category_selected)
        
        self.btn_add_root.clicked.connect(self._show_new_form_root)
        self.btn_add_sub.clicked.connect(self._show_new_form_sub)
        
        self.btn_salvar.clicked.connect(self.save_category)
        self.btn_excluir.clicked.connect(self.delete_category)
        self.btn_cancelar.clicked.connect(self.cancel_edit)

    def _load_empresas_combobox(self):
        """Carrega a lista de empresas (matriz) no combobox."""
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
            
            # Auto-seleciona a empresa ID 1 (padrão)
            if self.empresa_combo.findData(1) >= 0:
                self.empresa_combo.setCurrentIndex(self.empresa_combo.findData(1))
                
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar empresas: {e}")
        finally:
            conn.close()
            
    def load_categories(self):
        """Carrega as classes da empresa selecionada e constrói a árvore."""
        self.category_tree.clear()
        self.category_nodes.clear()
        self.cancel_edit()
        
        empresa_id = self.empresa_combo.currentData()
        if empresa_id is None:
            self.btn_add_root.setEnabled(False)
            return
            
        self.btn_add_root.setEnabled(True)
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            query = "SELECT id, name, parent_id, code, active FROM categorias WHERE empresa_id = ? ORDER BY name"
            cur.execute(query, (empresa_id,))
            
            all_categories = cur.fetchall()
            
            # Mapeia ID da categoria para o objeto de dados
            category_data_map = {cat['id']: dict(cat) for cat in all_categories}
            # Mapeia ID da categoria para o item da árvore
            tree_item_map = {}
            # Mapeia ID PAI para lista de IDs filhos
            children_map = {}
            
            for cat_id, cat_data in category_data_map.items():
                parent_id = cat_data['parent_id']
                if parent_id not in children_map:
                    children_map[parent_id] = []
                children_map[parent_id].append(cat_id)

            # Função recursiva para construir a árvore
            def build_tree(parent_id, parent_item):
                if parent_id not in children_map:
                    return # Não tem filhos
                    
                for cat_id in children_map[parent_id]:
                    cat_data = category_data_map[cat_id]
                    
                    item = QTreeWidgetItem(parent_item)
                    item.setText(0, cat_data['name'])
                    item.setData(0, Qt.UserRole, cat_data['id'])
                    
                    if not cat_data['active']:
                        item.setForeground(0, QColor(Qt.gray))
                        item.setText(0, f"{cat_data['name']} (Inativa)")
                        
                    tree_item_map[cat_id] = item
                    build_tree(cat_id, item) # Chama recursivamente

            # Inicia a construção a partir da raiz (None)
            build_tree(None, self.category_tree.invisibleRootItem())
            self.category_tree.expandAll()

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar classes: {e}")
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
            cur.execute("SELECT * FROM categorias WHERE id = ?", (category_id,))
            data = cur.fetchone()
            if not data:
                QMessageBox.warning(self, "Erro", "Classe não encontrada.")
                self.cancel_edit()
                return
                
            self.form_panel.setEnabled(True)
            self.current_category_id = data['id']
            self.current_parent_id = data['parent_id']
            
            self.form_title.setText(f"Editando: {data['name']}")
            self.nome_input.setText(data['name'])
            self.code_input.setText(data['code'])
            self.status_combo.setCurrentIndex(0 if data['active'] else 1)
            
            if data['parent_id']:
                cur.execute("SELECT name FROM categorias WHERE id = ?", (data['parent_id'],))
                parent_data = cur.fetchone()
                self.parent_input.setText(parent_data['name'] if parent_data else "N/A")
            else:
                self.parent_input.setText("(Classe Raiz)")
                
            self.btn_excluir.setEnabled(True)
            self.btn_add_sub.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar classe: {e}")
        finally:
            conn.close()

    def _show_new_form_root(self):
        """Prepara o formulário para uma nova classe RAIZ."""
        self._show_new_form(parent_id=None, parent_name="(Classe Raiz)")

    def _show_new_form_sub(self):
        """Prepara o formulário para uma nova SUBCLASSE."""
        selected_items = self.category_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Seleção", "Selecione uma classe pai na árvore primeiro.")
            return
            
        parent_item = selected_items[0]
        parent_id = parent_item.data(0, Qt.UserRole)
        parent_name = parent_item.text(0)
        
        self._show_new_form(parent_id=parent_id, parent_name=parent_name)

    def _show_new_form(self, parent_id, parent_name):
        self.form_panel.setEnabled(True)
        self.category_tree.clearSelection()
        
        self.current_category_id = None # Modo INSERT
        self.current_parent_id = parent_id
        
        self.form_title.setText(f"Nova Classe (filha de: {parent_name})")
        self.nome_input.clear()
        self.code_input.clear()
        self.status_combo.setCurrentIndex(0)
        self.parent_input.setText(parent_name)
        
        self.btn_excluir.setEnabled(False)
        self.nome_input.setFocus()

    def cancel_edit(self):
        """Limpa e desabilita o formulário de edição."""
        self.form_panel.setEnabled(False)
        self.category_tree.clearSelection()
        
        self.current_category_id = None
        self.current_parent_id = None
        
        self.form_title.setText("Selecione ou crie uma classe")
        self.nome_input.clear()
        self.code_input.clear()
        self.status_combo.setCurrentIndex(0)
        self.parent_input.clear()
        
        self.btn_excluir.setEnabled(False)
        self.btn_add_sub.setEnabled(False) # Só habilita quando seleciona

    def _get_parent_level(self, conn, parent_id):
        """Busca o nível do pai para calcular o nível do filho."""
        if parent_id is None:
            return -1 # Raiz será 0
        try:
            cur = conn.cursor()
            cur.execute("SELECT level FROM categorias WHERE id = ?", (parent_id,))
            result = cur.fetchone()
            return result['level'] if result else -1
        except Exception:
            return -1

    def save_category(self):
        empresa_id = self.empresa_combo.currentData()
        if empresa_id is None:
            QMessageBox.warning(self, "Erro", "Nenhuma empresa selecionada.")
            return
            
        nome = self.nome_input.text().strip()
        if not nome:
            QMessageBox.warning(self, "Campo Obrigatório", "O campo 'Nome da Classe' é obrigatório.")
            return
            
        data = {
            "empresa_id": empresa_id,
            "name": nome,
            "code": self.code_input.text().strip() or None,
            "active": 1 if self.status_combo.currentIndex() == 0 else 0,
            "parent_id": self.current_parent_id
        }
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            
            if self.current_category_id:
                # --- UPDATE ---
                data["id"] = self.current_category_id
                query = """
                    UPDATE categorias 
                    SET name = :name, code = :code, active = :active, parent_id = :parent_id
                    WHERE id = :id AND empresa_id = :empresa_id
                """
                msg = "Classe atualizada com sucesso!"
            else:
                # --- INSERT ---
                level = self._get_parent_level(conn, self.current_parent_id) + 1
                data["level"] = level
                
                fields = ", ".join(data.keys())
                placeholders = ", ".join([f":{k}" for k in data.keys()])
                query = f"INSERT INTO categorias ({fields}) VALUES ({placeholders})"
                msg = "Classe salva com sucesso!"

            cur.execute(query, data)
            conn.commit()
            
            QMessageBox.information(self, "Sucesso", msg)
            self.load_categories() # Recarrega a árvore
            self.cancel_edit()

        except sqlite3.IntegrityError:
            QMessageBox.critical(self, "Erro", "Erro de integridade (possível código duplicado).")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar classe: {e}")
        finally:
            conn.close()
            
    def delete_category(self):
        if not self.current_category_id:
            QMessageBox.warning(self, "Erro", "Nenhuma classe selecionada.")
            return

        # 1. Verifica se tem filhos
        item = self.category_tree.selectedItems()[0]
        if item.childCount() > 0:
            QMessageBox.critical(self, "Erro", "Não é possível excluir. Esta classe contém subclasses.")
            return
            
        conn = get_connection()
        try:
            cur = conn.cursor()
            
            # 2. Verifica se está em uso por um produto
            cur.execute("SELECT id FROM produtos WHERE categoria_id = ?", (self.current_category_id,))
            produto_usando = cur.fetchone()
            if produto_usando:
                QMessageBox.critical(self, "Erro", "Não é possível excluir. Esta classe está em uso por um ou mais produtos.")
                return

            # 3. Confirmação
            reply = QMessageBox.question(self, "Confirmação",
                f"Tem certeza que deseja excluir a classe '{self.nome_input.text()}'?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                
            if reply == QMessageBox.No:
                return
            
            # 4. Exclusão
            cur.execute("DELETE FROM categorias WHERE id = ?", (self.current_category_id,))
            conn.commit()
            
            QMessageBox.information(self, "Sucesso", "Classe excluída com sucesso.")
            self.load_categories()
            self.cancel_edit()
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao excluir classe: {e}")
        finally:
            conn.close()