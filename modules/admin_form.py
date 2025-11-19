# -*- coding: utf-8 -*-
# modules/admin_form.py
import sqlite3
import json
import logging # <-- NOVO
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QMessageBox, QGridLayout,
    QTabWidget, QCheckBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView,
    QTreeWidget, QTreeWidgetItem, QComboBox,
    QScrollArea, QRadioButton, QButtonGroup,
    QDoubleSpinBox, QFrame, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPixmap, QIcon
from database.db import get_connection
from config.permissions import PERMISSION_SCHEMA, FIELD_PERMISSIONS, MODULE_PERMISSIONS

THEME_MAP = {
    "Amarelo": "#F1C40F", "Azul": "#0078d7", "Azul claro": "#3498DB",
    "Cinza": "#95A5A6", "Cinza escuro": "#34495E", "Laranja claro": "#E67E22",
    "Rosa": "#E91E63", "Roxo": "#8E44AD", "Verde": "#2ECC71", "Verde escuro": "#16A085"
}

class AdminForm(QWidget):
    def __init__(self, current_user_id):
        super().__init__()
        
        self.setWindowTitle("Administração do Sistema")
        self.current_edit_user_id = None
        self.admin_user_id = current_user_id
        
        # --- NOVO: Logger ---
        self.logger = logging.getLogger(__name__)
        
        self.perm_modulos = {} 
        self.perm_formularios = {} 
        self.perm_campos = {} 
        
        self._setup_styles()
        self._build_ui()
        self._load_users_table()
        self._check_admin_self_permissions()
        self._load_current_theme()

    def _setup_styles(self):
        # (CSS Inalterado)
        self.setStyleSheet("""
            QWidget { background-color: #f8f8fb; font-family: 'Segoe UI', sans-serif; }
            
            QTabWidget::pane { 
                border-top: 1px solid #c0c0d0; 
                background: #f8f8fb; 
            }
            QTabBar::tab { 
                background: #e0e0e0; 
                padding: 10px 25px; 
                font-weight: bold; 
                font-size: 14px;
            }
            QTabBar::tab:selected { 
                background: #f8f8fb; 
                border: 1px solid #c0c0d0; 
                border-bottom: none; 
            }
            
            QLabel { font-weight: bold; color: #444; font-size: 13px; }
            QLabel#panel_title {
                font-size: 16px; font-weight: bold; color: #005fa3;
                padding-bottom: 5px; border-bottom: 1px solid #eee;
                margin-bottom: 10px;
            }
            
            QFrame#panel {
                background-color: #fdfdfd;
                border: 1px solid #c0c0d0;
                border-radius: 8px;
            }
            
            QLineEdit, QSpinBox, QComboBox, QDoubleSpinBox {
                border: 1px solid #c0c0d0; border-radius: 5px; padding: 6px; 
                background-color: white; color: #333; font-size: 13px;
            }
            
            QTreeWidget { 
                border: 1px solid #c0c0d0; background-color: white; 
            }
            QTreeWidget::item { 
                color: #333; 
                padding: 4px 0px; 
            }
            QTreeWidget QComboBox { 
                padding: 4px; 
                margin-right: 5px; 
            }
            QTreeWidget::item:hover { background-color: #e0e8f0; color: #333; }
            QTreeWidget::item:selected { background-color: #0078d7; color: white; }
            QTreeWidget::item:!child { font-weight: bold; }

            QPushButton {
                background-color: #0078d7; color: white; border-radius: 6px;
                padding: 8px 15px; font-weight: bold; text-align: center;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #005fa3; }
            QPushButton#deleteButton { background-color: #e74c3c; }
            QPushButton#deleteButton:hover { background-color: #c0392b; }
            QPushButton#cancelButton { background-color: #95A5A6; }
            QPushButton#cancelButton:hover { background-color: #7F8C8D; }
            
            QHeaderView::section { 
                background-color: #e8e8e8; padding: 8px; 
                border: 1px solid #c0c0d0; font-weight: bold; 
                font-size: 14px;
            }
            QScrollArea { border: 1px solid #c0c0d0; background-color: white; }
            QRadioButton::indicator::unchecked {
                border: 1px solid #999; background-color: white;
                border-radius: 7px; width: 14px; height: 14px;
            }
            QRadioButton::indicator::checked {
                border: 1px solid #555; background-color: #0078d7;
                border-radius: 7px; width: 14px; height: 14px;
            }
        """)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # --- Aba 1: Lista de Usuários ---
        self.tab_users_list = QWidget()
        self.tabs.addTab(self.tab_users_list, "Usuários")
        users_list_layout = QVBoxLayout(self.tab_users_list)
        users_list_layout.setContentsMargins(10, 15, 10, 10)
        
        list_btn_layout = QHBoxLayout()
        self.new_btn = QPushButton("Novo Usuário")
        self.delete_btn = QPushButton("Excluir Usuário Selecionado")
        self.delete_btn.setObjectName("deleteButton")
        list_btn_layout.addWidget(self.new_btn)
        list_btn_layout.addWidget(self.delete_btn)
        list_btn_layout.addStretch()
        users_list_layout.addLayout(list_btn_layout)
        
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(3)
        self.users_table.setHorizontalHeaderLabels(["ID", "Usuário", "Ativo?"])
        self.users_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.users_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.users_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.users_table.setColumnHidden(0, True)
        users_list_layout.addWidget(self.users_table)
        
        # --- Aba 2: Editor de Usuário ---
        self.tab_user_editor = QWidget()
        self.tabs.addTab(self.tab_user_editor, "Editor de Usuário")
        editor_layout = QVBoxLayout(self.tab_user_editor)
        editor_layout.setContentsMargins(10, 15, 10, 10)

        top_panel = QFrame()
        top_panel.setObjectName("panel")
        top_layout = QGridLayout(top_panel)
        top_layout.setSpacing(10)
        top_layout.setContentsMargins(10, 10, 10, 10)

        top_layout.addWidget(QLabel("Dados do Usuário:", objectName="panel_title"), 0, 0, 1, 4)

        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.is_active_check = QCheckBox("Usuário Ativo")
        self.is_active_check.setChecked(True)
        
        self.limite_desconto_label = QLabel("Limite Desconto (%):")
        self.limite_desconto_input = QDoubleSpinBox()
        self.limite_desconto_input.setRange(0.0, 100.0)
        self.limite_desconto_input.setSuffix(" %")

        top_layout.addWidget(QLabel("Usuário:"), 1, 0)
        top_layout.addWidget(self.username_input, 1, 1)
        top_layout.addWidget(QLabel("Senha:"), 2, 0)
        top_layout.addWidget(self.password_input, 2, 1)
        
        top_layout.addWidget(self.limite_desconto_label, 1, 2)
        top_layout.addWidget(self.limite_desconto_input, 1, 3)
        top_layout.addWidget(self.is_active_check, 2, 3)
        
        top_layout.setColumnStretch(1, 2)
        top_layout.setColumnStretch(3, 1)

        editor_layout.addWidget(top_panel)

        bottom_panel = QFrame()
        bottom_panel.setObjectName("panel")
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(10, 10, 10, 10)

        self.perm_label = QLabel("Permissões do Usuário:", objectName="panel_title")
        bottom_layout.addWidget(self.perm_label)
        
        self.perm_tree = QTreeWidget()
        self.perm_tree.setHeaderLabels(["Módulo / Formulário / Campo", "Permissão"])
        self.perm_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        bottom_layout.addWidget(self.perm_tree)
        self._populate_permission_tree() 
        
        editor_layout.addWidget(bottom_panel, 1)

        editor_btn_layout = QHBoxLayout()
        editor_btn_layout.addStretch()
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setObjectName("cancelButton")
        self.btn_salvar = QPushButton("Salvar Usuário e Permissões")
        editor_btn_layout.addWidget(self.btn_cancelar)
        editor_btn_layout.addWidget(self.btn_salvar)
        editor_layout.addLayout(editor_btn_layout)
        
        # --- ABA 3: Temas ---
        self.tab_themes = QWidget()
        self.tabs.addTab(self.tab_themes, "Meu Tema")
        self._build_tab_themes()
        
        # --- Estado Inicial ---
        self.tabs.setCurrentIndex(0)
        self.tabs.widget(1).setEnabled(False)

        # Conectar Sinais
        self.new_btn.clicked.connect(self.show_new_form)
        self.btn_salvar.clicked.connect(self.save_user_and_permissions)
        self.delete_btn.clicked.connect(self.delete_user) 
        self.btn_cancelar.clicked.connect(self.cancel_action)
        self.users_table.itemDoubleClicked.connect(self._load_user_for_edit)
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index):
        if index == 0:
            self.cancel_action()
        
    def _build_tab_themes(self):
        layout = QVBoxLayout(self.tab_themes)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.addWidget(QLabel("Selecione o seu tema de preferência:"))
        layout.addWidget(QLabel("A cor será aplicada na próxima vez que você fizer login."))
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("ThemeScrollArea")
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: white;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(20, 20, 20, 20)
        scroll_layout.setSpacing(15)
        self.theme_button_group = QButtonGroup(self)
        for name, color_hex in THEME_MAP.items():
            rb = QRadioButton(name)
            pixmap = QPixmap(20, 20); pixmap.fill(QColor(color_hex))
            rb.setIcon(QIcon(pixmap))
            rb.setStyleSheet("font-size: 14px;")
            self.theme_button_group.addButton(rb)
            scroll_layout.addWidget(rb)
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.save_theme_btn = QPushButton("Salvar Meu Tema")
        self.save_theme_btn.clicked.connect(self._save_theme)
        btn_layout.addWidget(self.save_theme_btn)
        layout.addLayout(btn_layout)

    def _load_current_theme(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT theme_name FROM usuarios WHERE id = ?", (self.admin_user_id,))
            result = cur.fetchone()
            conn.close()
            if result:
                theme_name = result['theme_name']
                for rb in self.theme_button_group.buttons():
                    if rb.text() == theme_name:
                        rb.setChecked(True)
                        break
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível carregar o tema salvo: {e}")

    def _save_theme(self):
        checked_btn = self.theme_button_group.checkedButton()
        if not checked_btn:
            QMessageBox.warning(self, "Erro", "Nenhum tema foi selecionado.")
            return
        theme_name = checked_btn.text()
        theme_color = THEME_MAP[theme_name]
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("UPDATE usuarios SET theme_name = ?, theme_color = ? WHERE id = ?", 
                       (theme_name, theme_color, self.admin_user_id))
            conn.commit()
            conn.close()
            
            # --- LOG ADICIONADO ---
            self.logger.info(f"Usuário ID {self.admin_user_id} alterou seu tema para '{theme_name}'.")
            
            QMessageBox.information(self, "Sucesso", 
                f"Tema '{theme_name}' salvo.\n\nSaia e entre novamente no sistema para ver a mudança.")
        except Exception as e:
            self.logger.error(f"Erro ao salvar tema: {e}")
            QMessageBox.critical(self, "Erro", f"Não foi possível salvar o tema: {e}")

    def _populate_permission_tree(self):
        self.perm_tree.clear()
        
        for mod_display, mod_data in PERMISSION_SCHEMA.items():
            mod_key = mod_data['db_key_modulo']
            
            mod_item = QTreeWidgetItem(self.perm_tree)
            mod_item.setText(0, mod_display)
            mod_item.setData(0, Qt.UserRole, ("mod", mod_key))
            
            mod_combo = QComboBox()
            mod_combo.addItems(MODULE_PERMISSIONS)
            self.perm_tree.setItemWidget(mod_item, 1, mod_combo)
            
            for form_key, form_data in mod_data["formularios"].items():
                form_db_key = form_data['db_key_form']
                
                form_item = QTreeWidgetItem(mod_item)
                form_item.setText(0, f"  {form_data['display_name']}")
                form_item.setData(0, Qt.UserRole, ("form", form_key, form_db_key))
                
                form_combo = QComboBox()
                form_combo.addItems(MODULE_PERMISSIONS)
                self.perm_tree.setItemWidget(form_item, 1, form_combo)
                
                for campo_display, campo_db_key in form_data["campos"].items():
                    campo_item = QTreeWidgetItem(form_item)
                    campo_item.setText(0, f"    - {campo_display}")
                    
                    campo_data = ("field", form_key, campo_db_key)
                    campo_item.setData(0, Qt.UserRole, campo_data)
                    
                    campo_combo = QComboBox()
                    campo_combo.addItems(FIELD_PERMISSIONS)
                    self.perm_tree.setItemWidget(campo_item, 1, campo_combo)
        
        self.perm_tree.setEnabled(False)

    def _load_users_table(self):
        self.users_table.setRowCount(0)
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, username, is_active FROM usuarios ORDER BY username")
            users = cur.fetchall()
            
            for user in users:
                row = self.users_table.rowCount()
                self.users_table.insertRow(row)
                self.users_table.setItem(row, 0, QTableWidgetItem(str(user['id'])))
                self.users_table.setItem(row, 1, QTableWidgetItem(user['username']))
                self.users_table.setItem(row, 2, QTableWidgetItem("Sim" if user['is_active'] else "Não"))
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar usuários: {e}")
        finally:
            conn.close()

    def _load_user_for_edit(self, item):
        """Carrega os dados do usuário E preenche a árvore de permissões."""
        row = item.row()
        self.current_edit_user_id = int(self.users_table.item(row, 0).text())
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM usuarios WHERE id = ?", (self.current_edit_user_id,))
            user_data = cur.fetchone()
            if not user_data:
                self.cancel_action(); return

            self.username_input.setText(user_data['username'])
            self.is_active_check.setChecked(bool(user_data['is_active']))
            self.password_input.clear()
            self.password_input.setPlaceholderText("Deixe em branco para não alterar")
            
            self.perm_label.setText(f"Editando permissões para: {user_data['username']}")
            self.perm_tree.setEnabled(True)
        
            cur.execute("SELECT modulos, formularios, campos, limites FROM permissoes WHERE user_id = ?", (self.current_edit_user_id,))
            perms = cur.fetchone()
            
            try:
                self.perm_modulos = json.loads(perms['modulos']) if perms and perms['modulos'] else {}
                self.perm_formularios = json.loads(perms['formularios']) if perms and perms['formularios'] else {}
                self.perm_campos = json.loads(perms['campos']) if perms and perms['campos'] else {}
                limites_perms = json.loads(perms['limites']) if perms and perms['limites'] else {}
            except Exception as json_e:
                QMessageBox.critical(self, "Erro de Dados", f"Erro ao carregar JSON de permissões. Dados corrompidos. {json_e}")
                self.cancel_action()
                return

            self.limite_desconto_input.setValue(limites_perms.get("desconto_max_perc", 0.0))
            
            root = self.perm_tree.invisibleRootItem()
            for i in range(root.childCount()):
                mod_item = root.child(i)
                tipo, mod_db_key = mod_item.data(0, Qt.UserRole)
                perm_mod = self.perm_modulos.get(mod_db_key, False)
                self.perm_tree.itemWidget(mod_item, 1).setCurrentText("Permitido" if perm_mod else "Negado")
                
                for j in range(mod_item.childCount()):
                    form_item = mod_item.child(j)
                    tipo, form_key, form_db_key = form_item.data(0, Qt.UserRole)
                    perm_form = self.perm_formularios.get(form_db_key, False)
                    self.perm_tree.itemWidget(form_item, 1).setCurrentText("Permitido" if perm_form else "Negado")
                    
                    for k in range(form_item.childCount()):
                        campo_item = form_item.child(k)
                        tipo, form_key, field_key = campo_item.data(0, Qt.UserRole)
                        perm_value = self.perm_campos.get(form_key, {}).get(field_key, "Total")
                        self.perm_tree.itemWidget(campo_item, 1).setCurrentText(perm_value)
                        
            self.tabs.widget(1).setEnabled(True) 
            self.tabs.setCurrentIndex(1) 
            self.username_input.setFocus()
                        
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar permissões: {e}")
        finally:
            conn.close()

    def show_new_form(self):
        """Limpa o formulário de edição e muda para a aba de edição."""
        self.current_edit_user_id = None
        self.username_input.clear()
        self.password_input.clear()
        self.password_input.setPlaceholderText("")
        self.is_active_check.setChecked(True)
        self.limite_desconto_input.setValue(0.0)
        
        self.perm_label.setText("Editando permissões para: NOVO USUÁRIO")
        self.perm_tree.setEnabled(True)
        
        root = self.perm_tree.invisibleRootItem()
        for i in range(root.childCount()):
            mod_item = root.child(i)
            self.perm_tree.itemWidget(mod_item, 1).setCurrentText("Negado")
            for j in range(mod_item.childCount()):
                form_item = mod_item.child(j)
                self.perm_tree.itemWidget(form_item, 1).setCurrentText("Negado")
                for k in range(form_item.childCount()):
                    campo_item = form_item.child(k)
                    self.perm_tree.itemWidget(campo_item, 1).setCurrentText("Total")
            
        self.users_table.clearSelection()
        self.tabs.widget(1).setEnabled(True)
        self.tabs.setCurrentIndex(1)
        self.username_input.setFocus()

    def cancel_action(self):
        """Limpa o formulário de edição e volta para a aba de lista."""
        self.current_edit_user_id = None
        self.username_input.clear()
        self.password_input.clear()
        self.password_input.setPlaceholderText("")
        self.is_active_check.setChecked(True)
        self.limite_desconto_input.setValue(0.0)
        
        self.perm_label.setText("Selecione um usuário na tabela para editar suas permissões.")
        self.perm_tree.setEnabled(False)
        self.users_table.clearSelection()
        
        self.tabs.setCurrentIndex(0) 
        self.tabs.widget(1).setEnabled(False)

    def save_user_and_permissions(self):
        """Salva o usuário E as permissões da árvore (Módulos, Formulários, Campos, Limites)."""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        is_active = 1 if self.is_active_check.isChecked() else 0
        
        if not username:
            QMessageBox.warning(self, "Erro", "O nome de usuário é obrigatório.")
            return
            
        limites_perms = {
            "desconto_max_perc": self.limite_desconto_input.value()
        }
        
        self.perm_modulos = {}
        self.perm_formularios = {}
        self.perm_campos = {}
        
        root = self.perm_tree.invisibleRootItem()
        for i in range(root.childCount()):
            mod_item = root.child(i)
            tipo, mod_db_key = mod_item.data(0, Qt.UserRole)
            self.perm_modulos[mod_db_key] = (self.perm_tree.itemWidget(mod_item, 1).currentText() == "Permitido")
            
            for j in range(mod_item.childCount()):
                form_item = mod_item.child(j)
                tipo, form_key, form_db_key = form_item.data(0, Qt.UserRole)
                self.perm_formularios[form_db_key] = (self.perm_tree.itemWidget(form_item, 1).currentText() == "Permitido")
                
                for k in range(form_item.childCount()):
                    campo_item = form_item.child(k)
                    tipo, form_key, field_key = campo_item.data(0, Qt.UserRole)
                    if form_key not in self.perm_campos:
                        self.perm_campos[form_key] = {}
                    perm_value = self.perm_tree.itemWidget(campo_item, 1).currentText()
                    self.perm_campos[form_key][field_key] = perm_value

        modulos_json = json.dumps(self.perm_modulos)
        formularios_json = json.dumps(self.perm_formularios) 
        campos_json = json.dumps(self.perm_campos)
        limites_json = json.dumps(limites_perms)

        conn = get_connection()
        cur = conn.cursor()
        
        try:
            if self.current_edit_user_id is None:
                if not password:
                    QMessageBox.warning(self, "Erro", "A senha é obrigatória para novos usuários.")
                    return
                cur.execute("INSERT INTO usuarios (username, password_text, is_active) VALUES (?, ?, ?)",
                            (username, password, is_active))
                new_user_id = cur.lastrowid
                cur.execute("INSERT INTO permissoes (user_id, modulos, formularios, campos, limites) VALUES (?, ?, ?, ?, ?)",
                            (new_user_id, modulos_json, formularios_json, campos_json, limites_json))
                
                # --- LOG ADICIONADO ---
                self.logger.info(f"ADMIN (ID {self.admin_user_id}) criou novo usuário: '{username}' (ID {new_user_id}).")
                
                QMessageBox.information(self, "Sucesso", "Usuário e permissões criados.")

            else:
                if password:
                    cur.execute("UPDATE usuarios SET username = ?, password_text = ?, is_active = ? WHERE id = ?",
                                (username, password, is_active, self.current_edit_user_id))
                else:
                    cur.execute("UPDATE usuarios SET username = ?, is_active = ? WHERE id = ?",
                                (username, is_active, self.current_edit_user_id))
                
                cur.execute("UPDATE permissoes SET modulos = ?, formularios = ?, campos = ?, limites = ? WHERE user_id = ?",
                            (modulos_json, formularios_json, campos_json, limites_json, self.current_edit_user_id))
                
                # --- LOG ADICIONADO ---
                self.logger.info(f"ADMIN (ID {self.admin_user_id}) atualizou o usuário: '{username}' (ID {self.current_edit_user_id}).")
                
                QMessageBox.information(self, "Sucesso", "Usuário e permissões atualizados.")
                
            conn.commit()
            
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Erro", "Este nome de usuário já existe.")
        except Exception as e:
            self.logger.error(f"Erro ao salvar usuário: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro: {e}")
        finally:
            conn.close()
            
        self._load_users_table()
        self.cancel_action()

    def delete_user(self):
        selected_items = self.users_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Erro", "Nenhum usuário selecionado na tabela.")
            return
            
        row = selected_items[0].row()
        user_id_to_delete = int(self.users_table.item(row, 0).text())
        username_to_delete = self.users_table.item(row, 1).text()

        if username_to_delete == "admin":
            QMessageBox.critical(self, "Erro", "O usuário 'admin' não pode ser excluído.")
            return
            
        reply = QMessageBox.question(self, "Confirmação",
                                     f"Tem certeza que deseja excluir o usuário '{username_to_delete}'?\nIsso é irreversível.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            conn = get_connection()
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM usuarios WHERE id = ?", (user_id_to_delete,))
                conn.commit()
                
                # --- LOG ADICIONADO ---
                self.logger.info(f"ADMIN (ID {self.admin_user_id}) excluiu o usuário: '{username_to_delete}' (ID {user_id_to_delete}).")
                
                QMessageBox.information(self, "Sucesso", "Usuário excluído.")
            except Exception as e:
                self.logger.error(f"Erro ao excluir usuário: {e}", exc_info=True)
                QMessageBox.critical(self, "Erro", f"Erro ao excluir: {e}")
            finally:
                conn.close()
            self._load_users_table()
            self.cancel_action()

    def _check_admin_self_permissions(self):
        # (Lógica inalterada)
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT campos FROM permissoes WHERE user_id = ?", (self.admin_user_id,))
            perms_row = cur.fetchone()
            
            if not perms_row or not perms_row['campos']:
                raise Exception("Permissões de campos não encontradas para o admin.")

            try:
                perms_json = perms_row['campos']
                perms = json.loads(perms_json)
            except Exception as json_e:
                QMessageBox.critical(self, "Erro de JSON", f"Falha ao carregar permissões: {json_e}")
                self.setEnabled(False)
                return

            admin_form_perms = perms.get('admin_form', {})
            
            delete_perm = admin_form_perms.get('delete_btn', 'Total')
            if delete_perm == 'Oculto':
                self.delete_btn.setVisible(False)
            elif delete_perm == 'Leitura':
                self.delete_btn.setEnabled(False)
                
            limite_perm = admin_form_perms.get('campo_limite_desconto', 'Total')
            if limite_perm == 'Oculto':
                self.limite_desconto_input.setVisible(False)
                self.limite_desconto_label.setVisible(False)
            elif limite_perm == 'Leitura':
                self.limite_desconto_input.setReadOnly(True)
                self.limite_desconto_input.setStyleSheet("background-color: #e0e0e0;")

        except Exception as e:
            print(f"Erro ao verificar permissões do admin: {e}")
            QMessageBox.critical(self, "Erro de Permissão", f"Não foi possível verificar as permissões do usuário admin: {e}")
            self.setEnabled(False)
        finally:
            conn.close()