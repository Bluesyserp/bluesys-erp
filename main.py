# main.py
import sys
import os
import logging
import logging.handlers
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon 
from auth.login_window import LoginWindow
from database.db import create_tables

# --- Importa o verificador de atualizações ---
try:
    from updater.updater import check_for_update
except ImportError:
    check_for_update = None


def setup_logging():
    """Configura o sistema de logging para salvar em arquivos diários rotativos."""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_filename = os.path.join(log_dir, "main.log")
    log_format = '%(asctime)s - %(levelname)s - [%(name)s:%(filename)s:%(lineno)d] - %(message)s'
    formatter = logging.Formatter(log_format)

    handler = logging.handlers.TimedRotatingFileHandler(
        log_filename,
        when='midnight',
        backupCount=30,
        encoding='utf-8'
    )
    handler.setFormatter(formatter)
    handler.suffix = "%Y-%m-%d"

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.addHandler(console_handler)

    logging.info("=" * 50)
    logging.info("Sistema de Logging (Rotativo) Iniciado")
    logging.info(f"Salvando log principal em: {log_filename}")
    logging.info("=" * 50)


def main():
    """Função principal para iniciar o aplicativo."""
    setup_logging()

    try:
        logging.info("Iniciando BlueSys ERP...")

        # --- 1️⃣ Verifica atualizações antes de abrir o sistema ---
        if check_for_update:
            logging.info("Verificando atualizações disponíveis...")
            check_for_update()
        else:
            logging.warning("Módulo de atualização não encontrado. Continuando sem atualização automática.")

        # --- 2️⃣ Garante que as tabelas do banco de dados existam ---
        logging.debug("Verificando/Criando tabelas no banco de dados...")
        create_tables()
        logging.debug("Tabelas verificadas com sucesso.")

        # --- 3️⃣ Inicializa a aplicação PyQt ---
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        
        # --- CORREÇÃO 1: Define o Ícone Padrão ---
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(base_dir, "assets", "bandeja_1.ico")
            
            if os.path.exists(icon_path):
                app.setWindowIcon(QIcon(icon_path))
                logging.info(f"Ícone da aplicação carregado de: {icon_path}")
            else:
                logging.warning(f"Ícone da aplicação (bandeja_1.ico) não encontrado em: {icon_path}")
        except Exception as e:
            logging.error(f"Erro ao carregar o ícone da aplicação: {e}")
        
        # --- CORREÇÃO 2: Impede que o App feche ao ocultar a janela ---
        app.setQuitOnLastWindowClosed(False)
        # --- FIM DA CORREÇÃO ---


        login = LoginWindow()
        login.show()

        logging.info("Janela de login exibida. Aguardando autenticação.")
        
        # O aplicativo roda aqui.
        exit_code = app.exec_()
        return exit_code # Retorna o código de saída

    except Exception as e:
        logging.critical(f"Erro fatal não tratado ao iniciar a aplicação: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    # Chamada corrigida para usar o código de saída retornado por main()
    sys.exit(main())