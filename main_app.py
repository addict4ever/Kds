import tkinter as tk
import threading
from db_manager import DBManager, initialize_data
from kds_gui import KDSGUI
# On importe la fonction de chargement JSON ici ⭐
from serial_reader import SerialReader, TCPReader, load_network_config_from_json
from web_access import ServerManager
import requests

if __name__ == "__main__":
    # 0. Chargement de la configuration réseau depuis le JSON
    # Assure-toi que le fichier printer_ip.json existe dans le dossier
    net_config = load_network_config_from_json('printer_ip.json')

    # 1. Initialisation de la Base de Données
    db_manager = DBManager("kds_orders.db")
    initialize_data(db_manager)

    # --- 2. Démarrage des Lecteurs dans des Threads séparés ---
    
    # Lecteur Série
    reader = SerialReader(db_manager)
    serial_thread = threading.Thread(target=reader.start, daemon=True)
    serial_thread.start()

    # Lecteur TCP (On passe maintenant net_config en 2ème argument ⭐)
    tcp_reader = TCPReader(reader, net_config)
    # On utilise directement tcp_reader.start() car TCPReader hérite de threading.Thread
    tcp_reader.daemon = True
    tcp_reader.start()

    # --- 3. DÉMARRAGE AUTOMATIQUE DU SERVEUR WEB (Flask) ---
    flask_manager = ServerManager()
    # On le lance sur 0.0.0.0:5000 par défaut
    flask_manager.start_server(host='0.0.0.0', port=5000)

    # ------------------------------------------------

    # 3. Initialisation de l'Interface Graphique (Main Thread)
    root = tk.Tk()
    root.title("KDS - Kitchen Display System (Port Série + TCP 9100)")

    app = KDSGUI(root, db_manager, reader)
    # 4. Fonction de fermeture propre
    def on_closing():
        print("Fermeture des services...")
        
        if 'flask_manager' in locals():
            # Note: On utilise l'IP locale pour la commande de shutdown interne
            flask_manager.stop_server()

        # Arrêt sécurisé du lecteur série
        if 'reader' in locals():
            reader.stop_reader()
        
        # Arrêt sécurisé du serveur TCP
        if 'tcp_reader' in locals():
            tcp_reader.stop_server()
            
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()