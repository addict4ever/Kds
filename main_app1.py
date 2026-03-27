# main_app.py

import tkinter as tk
# Nous importons 'initialize_data' qui est la fonction de simulation de données
from db_manager import DBManager, initialize_data 

# AJUSTEMENT : Importer KDSGUI depuis le nouveau fichier kds_main_window
from kds_main_window import KDSGUI 
# --- LIGNE CLÉ AJOUTÉE : Importation du SerialReader ---
from serial_reader import SerialReader 

if __name__ == "__main__":
    
    # 1. Initialisation de la Base de Données
    db_manager = DBManager("kds_orders.db")
    
    # Initialisation des données (simulation)
    initialize_data(db_manager) 
    
    # --- 2. Démarrage du Lecteur Série (Remplacement de l'Émulateur) ---
    reader = SerialReader(db_manager)
    reader.start() # Lance le lecteur série dans un thread séparé
    # ------------------------------------------------------------------

    # 3. Initialisation de l'Interface Graphique
    root = tk.Tk()
    root.title("KDS - Kitchen Display System (Séparation Services 1 & 2)")

    # Utilisation de la classe KDSGUI (maintenant importée de kds_main_window)
    app = KDSGUI(root, db_manager)
    
    # 4. Fonction à exécuter lors de la fermeture de l'application
    def on_closing():
        # --- LIGNE CLÉ AJOUTÉE : Arrêt propre du thread SerialReader ---
        if 'reader' in locals() and reader:
             reader.stop_reader() # Appelle la méthode d'arrêt du SerialReader
        # -------------------------------------------------------------
            
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)

    # 5. Lancement de la boucle principale de Tkinter
    root.mainloop()