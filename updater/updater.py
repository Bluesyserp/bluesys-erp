# modules/updater/updater.py
import requests
import os
import sys
import logging
import subprocess
import time
from PyQt5.QtWidgets import QMessageBox

# --- CONFIGURAÇÕES ---
CURRENT_VERSION = "1.0.0" # <--- ATUALIZE ISSO A CADA VERSÃO NOVA NO CÓDIGO
REPO_OWNER = "Bluesyserp"  # <--- COLOQUE SEU USUÁRIO AQUI
REPO_NAME = "bluesys-erp"          # <--- COLOQUE O NOME DO REPO AQUI
# ---------------------

GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"

def check_for_update():
    """
    Verifica se há uma nova versão no GitHub, baixa e instala.
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Se estiver rodando em modo desenvolvimento (.py), geralmente não queremos atualizar
        if not getattr(sys, 'frozen', False):
            logger.info("Modo desenvolvimento detectado. Pulo verificação de update.")
            return

        logger.info(f"Verificando atualizações em {GITHUB_API_URL}...")
        response = requests.get(GITHUB_API_URL, timeout=5)
        
        if response.status_code == 200:
            release_data = response.json()
            latest_tag = release_data["tag_name"] # Ex: v1.0.1
            latest_version = latest_tag.replace("v", "") 
            
            if is_newer(latest_version, CURRENT_VERSION):
                logger.info(f"Nova versão encontrada: {latest_version} (Atual: {CURRENT_VERSION})")
                
                reply = QMessageBox.question(
                    None, 
                    "Atualização Disponível",
                    f"Uma nova versão ({latest_version}) está disponível.\n"
                    "O sistema precisa reiniciar para atualizar.\n\nDeseja fazer isso agora?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    # Pega o link do primeiro asset (o .exe)
                    if "assets" in release_data and len(release_data["assets"]) > 0:
                        download_url = release_data["assets"][0]["browser_download_url"]
                        perform_update(download_url, "BlueSys.exe")
                    else:
                        logger.error("Release encontrada, mas sem arquivo .exe anexado.")
            else:
                logger.info("Sistema já está na versão mais recente.")
        else:
            logger.warning(f"Não foi possível checar atualizações. Status: {response.status_code}")
            
    except Exception as e:
        logger.error(f"Erro ao verificar atualizações: {e}")

def is_newer(v_remote, v_local):
    # Compara versões simples (ex: "1.0.1" > "1.0.0")
    # Pode ser melhorado com 'packaging.version' se necessário
    return v_remote > v_local

def perform_update(url, filename):
    """Baixa o novo executável e cria o script de troca."""
    logger = logging.getLogger(__name__)
    try:
        # 1. Define caminhos
        current_exe = sys.executable
        app_dir = os.path.dirname(current_exe)
        new_exe_path = os.path.join(app_dir, f"new_{filename}")
        bat_path = os.path.join(app_dir, "update.bat")

        # 2. Baixa o arquivo
        logger.info(f"Baixando atualização de {url}...")
        r = requests.get(url, stream=True)
        with open(new_exe_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info("Download concluído. Criando script de atualização...")

        # 3. Cria o script BAT para fazer a troca
        # O script espera 3 segundos, deleta o exe antigo, renomeia o novo e abre.
        bat_content = f"""
@echo off
timeout /t 3 /nobreak > NUL
del "{current_exe}"
move "{new_exe_path}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
"""
        with open(bat_path, 'w') as f:
            f.write(bat_content)

        # 4. Executa o script e fecha o programa atual
        logger.info("Iniciando script de troca e encerrando aplicação.")
        subprocess.Popen([bat_path], shell=True)
        sys.exit(0)

    except Exception as e:
        logger.error(f"Falha crítica ao atualizar: {e}")
        QMessageBox.critical(None, "Erro", f"Falha ao baixar atualização:\n{e}")