# modules/customer_quick_dialog.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout
from PyQt5.QtCore import pyqtSlot
from .customer_form import CustomerForm

class CustomerQuickDialog(QDialog):
    """
    Este é um 'wrapper' de QDialog para o CustomerForm (que é um QWidget).
    Isso permite que o CustomerForm seja chamado como um diálogo modal
    a partir do SalesForm (PDV).
    """
    def __init__(self, user_id, start_cpf=None, start_cnpj=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cadastro Rápido de Cliente")
        self.setModal(True)
        self.setFixedSize(800, 600) # Tamanho razoável para o formulário

        self.new_customer_id = None
        self.new_customer_name = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 1. Instancia o CustomerForm original
        self.form = CustomerForm(
            user_id=user_id,
            start_cpf=start_cpf,
            start_cnpj=start_cnpj,
            parent=self # Importante: 'self' (o QDialog) é o pai
        )
        
        # 2. Conecta o sinal 'customer_saved' do formulário a um slot local
        # Isso captura os dados do novo cliente ANTES do diálogo fechar
        self.form.customer_saved.connect(self.on_customer_saved)
        
        # 3. Adiciona o formulário ao layout do diálogo
        layout.addWidget(self.form)
        
        # NOTA: O CustomerForm (linha 278) já chama self.parent().accept()
        # e (linha 219) self.parent().reject(), então os botões Salvar/Cancelar
        # do formulário já irão fechar este diálogo corretamente.

    @pyqtSlot(int, str)
    def on_customer_saved(self, customer_id, customer_name):
        """
        Slot que captura os dados emitidos pelo CustomerForm
        quando o cliente é salvo com sucesso.
        """
        self.new_customer_id = customer_id
        self.new_customer_name = customer_name

    def get_new_customer_data(self):
        """
        Método chamado pelo SalesForm (PDV) após o diálogo ser
        aceito (exec_ == QDialog.Accepted) para recuperar os dados.
        """
        return self.new_customer_id, self.new_customer_name