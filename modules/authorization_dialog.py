# modules/authorization_dialog.py
import json
from PyQt5.QtWidgets import QLineEdit, QMessageBox, QLabel
from database.db import get_connection
from .custom_dialogs import FramelessDialog, CustomInputDialog

class AuthorizationDialog(CustomInputDialog):
    """
    Diálogo que pede usuário/senha e verifica uma permissão específica.
    Retorna o ID do usuário autorizado se for bem-sucedido.
    """
    def __init__(self, parent, permission_key_to_check):
        # Usamos CustomInputDialog como base, mas vamos adicionar um campo de senha
        super().__init__(parent, "Autorização Necessária", "Usuário Supervisor:")
        
        self.permission_key = permission_key_to_check
        self.authorized_user_id = None
        
        self.password_label = QLabel("Senha Supervisor:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet("font-size: 13px;")
        
        # Adiciona o campo de senha ao layout
        self.content_layout.addWidget(self.password_label)
        self.content_layout.addWidget(self.password_input)
        
        self.setFixedSize(380, 220) # Aumenta a altura
        
        # Conecta o Enter da senha ao 'accept'
        self.password_input.returnPressed.connect(self.check_authorization)
        # Re-conecta o botão OK para chamar a verificação
        self.button_box.accepted.disconnect()
        self.button_box.accepted.connect(self.check_authorization)

    def check_authorization(self):
        username = self.get_text() # Pega o usuário do campo 'line_edit'
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "Erro", "Usuário e senha são obrigatórios.")
            return

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, password_text FROM usuarios WHERE username = ? AND is_active = 1", (username,))
            user_data = cur.fetchone()

            if not user_data or user_data["password_text"] != password:
                QMessageBox.critical(self, "Acesso Negado", "Usuário ou senha inválidos!")
                return

            user_id = user_data["id"]
            
            # Agora, verifica a permissão específica
            cur.execute("SELECT campos FROM permissoes WHERE user_id = ?", (user_id,))
            perms_row = cur.fetchone()
            
            if not perms_row or not perms_row['campos']:
                QMessageBox.critical(self, "Acesso Negado", "O usuário não possui permissões configuradas.")
                return

            perms = json.loads(perms_row['campos'])
            sales_perms = perms.get('sales_form', {})
            
            # Verifica a permissão (ex: "pode_fechar_com_divergencia")
            if sales_perms.get(self.permission_key, False):
                self.authorized_user_id = user_id
                self.accept() # Fecha o diálogo com sucesso
            else:
                QMessageBox.critical(self, "Acesso Negado", f"O usuário '{username}' não tem permissão para esta ação.")

        except Exception as e:
            QMessageBox.critical(self, "Erro de DB", f"Erro ao verificar permissões: {e}")
        finally:
            conn.close()

    def get_authorized_id(self):
        return self.authorized_user_id