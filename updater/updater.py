# modules/updater/updater.py
import requests
import os
import sys
import logging
import subprocess
import zipfile
import shutil
from PyQt5.QtWidgets import QMessageBox
from config.version import APP_VERSION

# --- CONFIGURAÇÕES ---
CURRENT_VERSION = APP_VERSION
REPO_OWNER = "Bluesyserp" 
REPO_NAME = "bluesys-erp"
# ---------------------

GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"

def check_for_update():
    logger = logging.getLogger(__name__)
    
    try:
        if not getattr(sys, 'frozen', False):
            logger.info("Modo desenvolvimento. Update pulado.")
            return

        logger.info(f"Buscando updates em {GITHUB_API_URL}...")
        response = requests.get(GITHUB_API_URL, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            tag = data["tag_name"].replace("v", "")
            
            if tag > CURRENT_VERSION:
                reply = QMessageBox.question(
                    None, "Atualização", 
                    f"Versão {tag} disponível!\nO sistema será atualizado e reiniciado.",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    # Procura o asset que termina em .zip
                    asset = next((a for a in data["assets"] if a["name"].endswith(".zip")), None)
                    if asset:
                        perform_update_zip(asset["browser_download_url"])
                    else:
                        logger.error("Arquivo .zip não encontrado na release.")
    except Exception as e:
        logger.error(f"Erro no update: {e}")

def perform_update_zip(url):
    """Baixa ZIP, extrai e substitui arquivos usando script BAT."""
    logger = logging.getLogger(__name__)
    try:
        base_dir = os.path.dirname(sys.executable)
        zip_path = os.path.join(base_dir, "update.zip")
        extract_folder = os.path.join(base_dir, "update_temp")
        bat_path = os.path.join(base_dir, "update.bat")

        # 1. Baixar
        logger.info("Baixando...")
        r = requests.get(url, stream=True)
        with open(zip_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): f.write(chunk)

        # 2. Extrair
        logger.info("Extraindo...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_folder)
        
        # O zip contém uma pasta "BlueSys". Precisamos do conteúdo dela.
        # Caminho da nova pasta interna: update_temp/BlueSys/_internal
        new_internal = os.path.join(extract_folder, "BlueSys", "_internal")
        new_exe = os.path.join(extract_folder, "BlueSys", "BlueSys.exe")
        
        # 3. Criar Script de Troca
        # Este script vai: 
        # a) Esperar o programa fechar
        # b) Apagar a pasta _internal antiga
        # c) Mover a nova _internal para cá
        # d) Substituir o .exe
        # e) Limpar lixo e reabrir
        
        bat_content = f"""
@echo off
timeout /t 3 /nobreak > NUL

:: 1. Remove a pasta interna antiga
rmdir /S /Q "_internal"

:: 2. Move a nova pasta interna para cá
move "{new_internal}" "_internal"

:: 3. Substitui o executável
del "BlueSys.exe"
move "{new_exe}" "BlueSys.exe"

:: 4. Limpa arquivos temporários
rmdir /S /Q "{extract_folder}"
del "update.zip"

:: 5. Reabre o sistema
start "" "BlueSys.exe"
del "%~f0"
"""
        with open(bat_path, 'w') as f:
            f.write(bat_content)

        # 4. Executar
        logger.info("Reiniciando para aplicar...")
        subprocess.Popen([bat_path], shell=True)
        sys.exit(0)

    except Exception as e:
        logger.error(f"Falha crítica no update: {e}")
        QMessageBox.critical(None, "Erro", f"Falha ao atualizar:\n{e}")