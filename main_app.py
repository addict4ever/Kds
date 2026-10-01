import tkinter as tk
import threading
import sys
import os
import time
import socket
import subprocess
from db_manager import DBManager, initialize_data
from kds_gui import KDSGUI
from serial_reader import SerialReader, TCPReader, load_network_config_from_json
from web_access import ServerManager
import requests

def main():
    # 0. Chargement de la configuration réseau depuis le JSON
    net_config = load_network_config_from_json('printer_ip.json')

    # 1. Initialisation de la Base de Données
    db_manager = DBManager("kds_orders.db")
    initialize_data(db_manager)

    # --- 2. Démarrage des Lecteurs dans des Threads séparés ---
    reader = SerialReader(db_manager)
    serial_thread = threading.Thread(target=reader.start, daemon=True)
    serial_thread.start()

    # ⭐ Démarrage des 3 serveurs TCP (Ports 9100, 9200 et 9300)
    tcp_reader_1 = TCPReader(reader, net_config, server_id=1)
    tcp_reader_1.daemon = True
    tcp_reader_1.start()

    tcp_reader_2 = TCPReader(reader, net_config, server_id=2)
    tcp_reader_2.daemon = True
    tcp_reader_2.start()

    tcp_reader_3 = TCPReader(reader, net_config, server_id=3)
    tcp_reader_3.daemon = True
    tcp_reader_3.start()

    # --- 3. DÉMARRAGE AUTOMATIQUE DU SERVEUR WEB (Flask) ---
    flask_manager = ServerManager()
    flask_manager.start_server(host='0.0.0.0', port=5000)

    # ------------------------------------------------

    # Fonction de redémarrage pointant directement vers C:\resto_controller\main_app.exe
    def restart_application():
        print("Redémarrage de l'application depuis C:\\resto_controller\\main_app.exe...")
        
        # Arrêt propre des services
        try:
            flask_manager.stop_server()
        except Exception:
            pass
            
        try:
            reader.stop_reader()
        except Exception:
            pass
            
        try:
            tcp_reader_1.stop_server()
        except Exception:
            pass

        try:
            tcp_reader_2.stop_server()
        except Exception:
            pass

        try:
            tcp_reader_3.stop_server()
        except Exception:
            pass

        # Forcer la fermeture des ports locaux s'ils restent en suspens (Ajout des ports 9200 et 9300)
        for port in [5000, 9100, 9200, 9300]:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('127.0.0.1', port))
                s.close()
            except Exception:
                pass
            
        # Destruction de la fenêtre Tkinter
        try:
            root.destroy()
        except Exception:
            pass
        
        # Chemin direct et fixe de l'exécutable
        target_exe = r"C:\resto_controller\main_app.exe"
        
        # 🚀 REDÉMARRAGE VIA SCRIPT BATCH AVEC TASKKILL
        if getattr(sys, 'frozen', False):
            bat_path = os.path.join(os.environ['TEMP'], 'restart_kds.bat')
            
            # Le script .bat tue le processus, attend 1 seconde, puis relance
            bat_content = f"""
            @echo off
            taskkill /f /im main_app.exe >nul 2>&1
            timeout /t 1 /nobreak > nul
            start "" "{target_exe}"
            del "%~f0"
            """
            
            with open(bat_path, 'w') as f:
                f.write(bat_content)
                
            subprocess.Popen(bat_path, shell=True)
        else:
            # Mode script Python normal (.py)
            time.sleep(0.5)
            subprocess.Popen([sys.executable] + sys.argv)
        
        # Fermeture brutale et instantanée de l'ancien processus
        os._exit(0)

    # 3. Initialisation de l'Interface Graphique (Main Thread)
    root = tk.Tk()
    root.title("KDS - Kitchen Display System (Multi-TCP & Série)")

    app = KDSGUI(root, db_manager, reader, restart_callback=restart_application)

    # 4. Fonction de fermeture propre (Croix de la fenêtre)
    def on_closing():
        print("Fermeture des services...")
        
        if 'flask_manager' in locals():
            flask_manager.stop_server()

        if 'reader' in locals():
            reader.stop_reader()
        
        if 'tcp_reader_1' in locals():
            tcp_reader_1.stop_server()

        if 'tcp_reader_2' in locals():
            tcp_reader_2.stop_server()

        if 'tcp_reader_3' in locals():
            tcp_reader_3.stop_server()
            
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()