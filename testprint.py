import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import time
import json
import os
import sys
from datetime import datetime
from serial_reader import SerialReader

# --- BIBLIOTHÈQUE DE TESTS ESC/POS ÉTENDUE ---
TEST_MODELS = {
    # ==========================================
    # --- COMMANDES SYSTÈME ---
    # ==========================================
    "--- COMMANDES SYSTÈME ---": None,
    "Requête Statut (10 04 01)": b'\x10\x04\x01',
    "Initialisation (ESC @)": b'\x1b@',
    "Bip Sonore / Tiroir (ESC p)": b'\x1b\x70\x00\x19\xfa',
    "Coupe Papier Totale": b'\x1d\x56\x00',
    "Coupe Papier Partielle": b'\x1d\x56\x01',
    
    # ==========================================
    # --- TESTS DE TAILLES & LISIBILITÉ ---
    # ==========================================
    "--- TESTS D'IMPRESSION ---": None,
    "Test Polices (A/B/Gras)": (
        b'\x1b@' b'Police Normale\n'
        b'\x1b!1Police B (Petite)\n'
        b'\x1b!8Police Grasse\n'
        b'\x1b!20Double Hauteur\n'
        b'\x1b!30Double Largeur\n'
        b'--------------------------------\n'
    ),
    "Test Alignement (G/C/D)": (
        b'\x1b@'
        b'\x1ba\x00Gauche\n'
        b'\x1ba\x01Centre\n'
        b'\x1ba\x02Droite\n'
        b'\x1ba\x00'
    ),
    "Test Tailles Standards (Mode !)": (
        b'\x1b@'
        b'\x1b!\x00Police Normale (Default)\n'
        b'\x1b!\x01Police B (Petite)\n'
        b'\x1b!\x08Police Normale + Gras\n'
        b'\x1b!\x10Double Hauteur\n'
        b'\x1b!\x20Double Largeur\n'
        b'\x1b!\x30Double Hauteur + Largeur\n'
        b'\x1b!\x38Dbl H. + Dbl L. + Gras\n'
        b'--------------------------------\n'
        b'\x1d\x56\x01'
    ),
    "Test Tailles Multiples (Mode GS !)": (
        b'\x1b@'
        b'Taille standard (1x1)\n'
        b'\x1d!\x01Largeur 2x (Hauteur 1x)\n'
        b'\x1d!\x10Hauteur 2x (Largeur 1x)\n'
        b'\x1d!\x11Taille 2x2 (Largeur 2, Haut 2)\n'
        b'\x1d!\x22Taille 3x3 (Largeur 3, Haut 3)\n'
        b'\x1d!\x33Taille 4x4 (Largeur 4, Haut 4)\n'
        b'\x1b!\x00\nRETOUR NORMAL\n'
        b'--------------------------------\n'
        b'\x1d\x56\x01'
    ),
    "Test Combo Lisibilité Cuisine": (
        b'\x1b@'
        b'\x1ba\x01' # Centré
        b'\x1d!\x11*** TEST CUISINE ***\n\n'
        b'\x1ba\x00' # Gauche
        b'\x1b!\x38LARGE PEPPERONI\n'
        b'\x1b!\x08  + EXTRA FROMAGE\n'
        b'\x1b!\x08  + BIEN CUIT\n'
        b'\x1b!\x00--------------------------------\n'
        b'\x1d!\x11TABLE # 12 (2x2)\n'
        b'\x1d\x56\x01'
    ),

    # ==========================================
    # --- TICKETS RÉELS (JANVIER 2026) ---
    # ==========================================
    "--- NOUVEAUX TICKETS (JANV 2026) ---": None,
    "Livraison #301 (Addition 998628)": (
        b'\x1b@'
        b'\x1b!2\x1br\x00      1083\n'
        b'\x1b!\x12\x1b!2\x1br\x00 MOONEY OUEST\n'
        b'\x1b!\x12\x1b!2\x1br\x00  4183338092\n'
        b'\x1br\x00        2026-01-27 10:44:38\n'
        b'\x1b!2\x1br\x00\x1b!\x12     ADDITION #998628-1\n'
        b'\x1b!2\x1br\x00   TRANS #017J\n'
        b'\x1br\x00   1 MEDIUM GARNI         $25.99  FP\n'
        b'\x1br\x00   1 FAM. POUTINE         $17.99  FP\n'
        b'\x1br\x00   Frais de livrais       $2.50  FP\n'
        b'\x1br\x00\n      TOT:     $53.44\n'
        b'\x1b!2\x1br\x00 LIVRAISON #301\n'
        b'\x1bd\t\x1bi'
    ),
    "Cuisine #302 (Lasagne)": (
        b'\x1b@'
        b'\x1b!2\x1br\x00 PRINCIPALE\x1b!\x12\n'
        b'\x1b!2\x1br\x00    LIVRAISON\n'
        b'\x1br\x00 Heure: 10:52:11\n'
        b'\x1br\x00  27-01-2026\n'
        b'\x1b!2\x1br\x00   TABLE # 302\n'
        b'\x1b!\x12\x1br\x00 \x1b!2  1\x1b!\x12 DEMI LASAGNE\n'
        b'\x1br\x01   \x1b!2  1\x1b!\x12 VIANDE\x1br\x01\n'
        b'\n###############################\n'
        b'\x1bd\t\x1bi'
    ),
    "Livraison #302 (Addition 998629)": (
        b'\x1b@'
        b'\x1b!2\x1br\x00        37\n'
        b'\x1b!\x12\x1b!2\x1br\x00    ND OUEST\n'
        b'\x1b!\x12\x1b!2\x1br\x00   4183359141\n'
        b'\x1br\x00        2026-01-27 10:52:14\n'
        b'\x1b!2\x1br\x00\x1b!\x12     ADDITION #998629-1\n'
        b'\x1b!2\x1br\x00   TRANS #017K\n'
        b'\x1br\x00   1 DEMI LASAGNE           $0.00\n'
        b'\x1br\x00   1 VIANDE                $13.99  FP\n'
        b'\x1br\x00\n      TOT:     $18.95\n'
        b'\x1b!2\x1br\x00 LIVRAISON #302\n'
        b'\x1bd\t\x1bi'
    ),
    "Livraison #303 (Addition 998632)": (
        b'\x1b@'
        b'\x1b!2\x1br\x00        66\n'
        b'\x1b!\x12\x1b!2\x1br\x00 st alph NORD\n'
        b'\x1b!\x12\x1b!2\x1br\x00      #109\n'
        b'\x1b!\x12\x1b!2\x1br\x00   4187553106\n'
        b'\x1br\x00        2026-01-27 11:03:43\n'
        b'\x1b!2\x1br\x00\x1b!\x12     ADDITION #998632-1\n'
        b'\x1b!2\x1br\x00   TRANS #017M\n'
        b'\x1br\x00   1 DESSERT JOUR MIDI     $3.00  FP\n'
        b'\x1br\x00   1 soupe midi            $2.00  FP\n'
        b'\x1br\x00   1 FISH N CHIP MIDI     $16.95  FP\n'
        b'\x1br\x00   Frais de livrais       $2.50  FP\n'
        b'\x1br\x00\n      TOT:     $28.11\n'
        b'\x1b!2\x1br\x00 LIVRAISON #303\n'
        b'\x1bd\t\x1bi'
    ),
    "Cuisine #304 (Mini Garnie)": (
        b'\x1b@'
        b'\x1b!2\x1br\x00 PRINCIPALE\x1b!\x12\n'
        b'\x1b!2\x1br\x00    LIVRAISON\n'
        b'\x1br\x00 Heure: 11:05:42\n'
        b'\x1br\x00  27-01-2026\n'
        b'\x1b!2\x1br\x00   TABLE # 304\n'
        b'\x1b!\x12\x1br\x00 \x1b!2  1\x1b!\x12 MINI GARNIE\n'
        b'\x1br\x00\n###############################\n'
        b'\x1bd\t\x1bi'
    ),

    # ==========================================
    # --- TESTS COMPLÉMENTAIRES ---
    # ==========================================
    "--- TESTS COMPLÉMENTAIRES ---": None,
    "Emporter #1 (Mini Special)": (
        b'\x1b@'
        b'\x1b!2\x1br\x00PRINCIPALE\n'
        b'\x1b!2\x1br\x00POUR EMPORTER\n\n'
        b'\x1b!\x12Heure: 16:18:12\n'
        b'\x1b!\x12 8-01-2026\n'
        b'\x1br\x00    POUR EMPORTE #1\n\n'
        b'\x1b!2 1 MINI SPECIAL\n'
        b'\x1b!\x12 pas trop croute\n'
        b'\n###############################\n'
        b'\x1bd\t\x1bi'
    ),
    "Livraison #342 (Frites/Pizza)": (
        b'\x1b@'
        b'\x1b!2\x1br\x00PRINCIPALE\n'
        b'\x1b!2\x1br\x00LIVRAISON\n\n'
        b'\x1b!\x12Heure: 16:17:15\n'
        b'\x1b!\x12 8-01-2026  1 CLIENT\n'
        b'\x1br\x00    LIVRAISON\n'
        b'\x1b!2\x1br\x00 TABLE # 342\n\n'
        b'\x1b!\x12 1 PT. FRITES\n'
        b'\x1b!\x12 1 LARGE PEP FROM BAC\n'
        b'\n###############################\n'
        b'\x1bd\t\x1bi'
    ),
    "Table 32 (Soupe & Lasagne) - ASCII": (
        # --- SERVICE # 1 (Soupe Midi) ---
        b'\x1b@' b'\x1b!2\x1br\x00 PRINCIPALE\x1b!\x12\n'
        b'\x1b!2\x1br\x00    COMMANDE\n'
        b'\x1br\x00 Heure: 12:15:00\n'
        b'\x1br\x00  23-02-2026\n'
        b'\x1b!2\x1br\x00   TABLE # 32\n'
        b'\x1b!\x12\x1br\x00        ** SERVICE # 1 **\n'
        b'\x1b!2\x1br\x00  1\x1b!\x12 SOUPE MIDI\n'
        b'\x1br\x00    \x1b!\x12 -> *LEGUMES\n'
        b'\n###############################\n' b'\x1bd\t\x1bi'
        
        # --- SERVICE # 2 (1/2 Lasagne) ---
        b'\x1b!2\x1br\x00 PRINCIPALE\x1b!\x12\n'
        b'\x1b!2\x1br\x00    COMMANDE\n'
        b'\x1br\x00 Heure: 12:15:05\n'
        b'\x1br\x00  23-02-2026\n'
        b'\x1b!2\x1br\x00   TABLE # 32\n'
        b'\x1b!\x12\x1br\x00        ** SERVICE # 2 **\n'
        b'\x1b!2\x1br\x00  1\x1b!\x12 1/2 LASAGNE\n'
        b'\x1br\x00    \x1b!\x12 -> *GRATINEE\n'
        b'\n###############################\n' b'\x1bd\t\x1bi'
    ),
    "Addition Livraison #320 (8 Eime Ave)": (
        b'\x1b@'
        b'\n\x1b!2\x1br\x00      856\n'
        b'\x1b!2\x1br\x00 8 EIME AVENUE\n'
        b'\x1b!2\x1br\x00  4185702847\n'
        b'\x1b!\x12  2026-01-14 15:37:51\n'
        b'\x1b!2\x1br\x00  ADDITION #994940-1\n'
        b'\x1b!\x12  1 MEDIUM PEPE        $24.99\n'
        b'\x1br\x00  1 PEPSI              $2.99\n'
        b'\x1br\x00  1 PT. POUTINE        $10.59\n'
        b'\x1br\x00      1 SAUCE BBQ      $0.00\n'
        b'\x1br\x00   Frais de livrais       $2.50\n'
        b'\n'
        b'\x1br\x00  TOT:      $47.22\n'
        b'\n'
        b'\x1br\x00      VOUS AVEZ SERVI\n'
        b'\x1br\x00        PAR : LIVRAISON\n'
        b'\x1b!2\x1br\x00LIVRAISON #320\n'
        b'\x1bd\t\x1bi'
    )
}

class POSSimulatorGUI:
    def __init__(self, master=None):
        self.master = master if master else tk.Tk()
        if not master:
            self.master.title("Simulateur & Diagnostic Série")
            self.master.geometry("750x780")
            self.master.configure(bg="#1c1c1c")

        self.ports_config = self._load_ports_json()
        self._setup_ui()
        self.refresh_ports()

    def _load_ports_json(self):
        path = 'ports.json'
        is_win = os.name == 'nt'
        key = 'windows_ports' if is_win else 'linux_ports'
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f).get(key, {})
            except: pass
        return {}

    def _setup_ui(self):
        # --- CONFIGURATION DU STYLE ---
        style = ttk.Style()
        style.theme_use('clam') # 'clam' est le meilleur thème pour accepter les changements de taille
        
        # 1. GROSSE BARRE DE DÉFILEMENT (Scrollbar)
        style.configure("Vertical.TScrollbar", 
                        width=40,      # Largeur de la barre
                        arrowsize=35)  # Flèches de la barre

        # 2. GROS MENU DÉROULANT (Combobox)
        # On change la taille de la flèche du menu déroulant ici
        style.configure("TCombobox", 
                        arrowsize=35,      # TAILLE DE LA FLÈCHE DU MENU
                        arrowcolor="white", # Couleur de la flèche
                        padding=10)        # Espace interne pour que ce soit épais

        # Modifier la taille de la liste qui descend (le menu ouvert)
        self.master.option_add('*TCombobox*Listbox.font', ("Arial", 16))
        self.master.option_add('*TCombobox*Listbox.itemHeight', 40) # Hauteur de chaque ligne dans la liste

        main_container = tk.Frame(self.master, bg="#1c1c1c", padx=20, pady=20)
        main_container.pack(fill='both', expand=True)

        # Titre
        tk.Label(main_container, text="🖨️ OUTIL DE DIAGNOSTIC POS & KDS", 
                 font=("Segoe UI", 22, "bold"), bg="#1c1c1c", fg="#3498db").pack(pady=(0,20))

        # --- SECTION SELECTION PORT ---
        port_group = tk.LabelFrame(main_container, text=" 📡 Port Série ", 
                                    bg="#1c1c1c", fg="white", font=("Arial", 12, "bold"), padx=15, pady=15)
        port_group.pack(fill='x', pady=10)

        self.port_var = tk.StringVar()
        # On applique le style à ce combo
        self.port_combo = ttk.Combobox(port_group, textvariable=self.port_var, font=("Consolas", 18), height=10)
        self.port_combo.pack(side='left', fill='x', expand=True, padx=(0, 15))

        tk.Button(port_group, text="🔄 ACTUALISER", command=self.refresh_ports, 
                  bg="#2980b9", fg="white", font=("Arial", 12, "bold"), padx=20, pady=10).pack(side='right')

        # --- SECTION SELECTION DU TEST ---
        test_group = tk.LabelFrame(main_container, text=" 📝 Contenu à envoyer ", 
                                    bg="#1c1c1c", fg="white", font=("Arial", 12, "bold"), padx=15, pady=15)
        test_group.pack(fill='x', pady=10)

        self.template_var = tk.StringVar()
        self.template_combo = ttk.Combobox(test_group, textvariable=self.template_var, 
                                           values=list(TEST_MODELS.keys()), state="readonly", font=("Arial", 18))
        self.template_combo.pack(fill='x', ipady=10) # ipady=10 pour que le champ soit haut
        self.template_combo.current(1)

        # --- CONSOLE DE LOGS ---
        tk.Label(main_container, text="📋 Activité du Port :", bg="#1c1c1c", fg="#95a5a6", font=("Arial", 12)).pack(anchor='w', pady=(15,0))
        
        log_frame = tk.Frame(main_container, bg="#0d0d0d")
        log_frame.pack(fill='both', expand=True, pady=5)

        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", style="Vertical.TScrollbar")
        scrollbar.pack(side='right', fill='y')

        self.log_text = tk.Text(log_frame, height=10, bg="#0d0d0d", fg="#00ff00", 
                                font=("Consolas", 14), yscrollcommand=scrollbar.set)
        self.log_text.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.log_text.yview)

        # --- BOUTONS D'ACTION GÉANTS ---
        # --- BOUTONS D'ACTION GÉANTS ---
        btn_frame = tk.Frame(main_container, bg="#1c1c1c")
        btn_frame.pack(fill='x', pady=20)

        # Bouton existant (Vert)
        self.btn_send = tk.Button(btn_frame, text="⚡ ENVOYER TEST UNIQUE", 
                                  bg="#27ae60", fg="white", font=("Arial", 14, "bold"), 
                                  height=2, command=self.send_data)
        self.btn_send.pack(side='left', fill='x', expand=True, padx=(0, 10))

        # NOUVEAU BOUTON (Orange / Corail)
        self.btn_bulk = tk.Button(btn_frame, text="🚀 TEST MASSIF (20)", 
                                  bg="#e67e22", fg="white", font=("Arial", 14, "bold"), 
                                  height=2, command=self.generate_kds_test_data)
        self.btn_bulk.pack(side='left', fill='x', expand=True, padx=(0, 10))

        # Bouton Clear (Rouge)
        tk.Button(btn_frame, text="🗑️ Clear", bg="#e74c3c", fg="white", font=("Arial", 12, "bold"),
                  width=10, command=lambda: self.log_text.delete('1.0', tk.END)).pack(side='right', fill='y')
    
    def show_custom_alert(self, title, message, is_error=True):
        """Alerte format Géant pour Touch Screen, centrée à l'écran."""
        alert = tk.Toplevel(self.master)
        
        # 1. Configuration de base (Bordure plus épaisse pour le style)
        alert.configure(bg="#1c1c1c", highlightbackground="#3498db", highlightthickness=3)
        alert.overrideredirect(True) 
        
        # 2. Dimensions augmentées pour le tactile (plus large et plus haut)
        width = 600
        height = 350
        
        # 3. Calcul du centrage précis
        screen_width = alert.winfo_screenwidth()
        screen_height = alert.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        
        alert.geometry(f"{width}x{height}+{x}+{y}")

        # 4. Comportement
        alert.attributes("-topmost", True)
        alert.grab_set()

        # 5. Entête massive
        header_color = "#e74c3c" if is_error else "#27ae60"
        tk.Label(alert, text=title.upper(), bg=header_color, fg="white", 
                 font=("Segoe UI", 16, "bold"), pady=15).pack(fill="x")

        # 6. Message plus lisible
        tk.Label(alert, text=message, bg="#1c1c1c", fg="white", 
                 font=("Segoe UI", 14), wraplength=550, pady=20).pack(expand=True)

        # 7. BOUTON GÉANT (Optimisé pour les gros doigts/écrans tactiles)
        # width=30 et pady=20 créent une zone de clic impossible à rater
        btn = tk.Button(alert, 
                        text="D'ACCORD", 
                        command=alert.destroy, 
                        bg="#34495e", 
                        fg="white", 
                        font=("Segoe UI", 18, "bold"),
                        relief="raised",      # Effet 3D pour simuler un vrai bouton
                        activebackground=header_color,
                        activeforeground="white",
                        width=25,             # Largeur fixe pour être massif
                        pady=15,              # Hauteur interne pour le tactile
                        cursor="hand2")
        btn.pack(pady=(0, 30)) # Espace en bas
        
        # Accessibilité clavier
        btn.focus_set()
        alert.bind("<Return>", lambda e: alert.destroy())
        alert.bind("<Escape>", lambda e: alert.destroy())
        
    def generate_kds_test_data(self):
        """Génère 20 tickets LIVRAISON avec numéros incrémentaux et IDs uniques."""
        import random
        from serial_reader import DBManager, SerialReader
        
        self.log("🚀 Injection de 20 livraisons uniques (Tables 300 à 319)...")

        try:
            # 1. Initialisation des outils
            manager = DBManager()
            reader = SerialReader(manager, print_forwarding_state=None)
            
            plats = ["PIZZA GARNIE", "POUTINE LARGE", "BURGER DOUBLE", "LASAGNE MAISON", "FISH N CHIPS", "DUO PIZZA-CÉSAR"]
            
            # On boucle 20 fois
            for i in range(20):
                # Numéro de table incrémental (300, 301, 302...)
                table_num = 300 + i
                
                # Génération d'un Bill ID unique
                timestamp_id = datetime.now().strftime("%H%M%S")
                unique_bill = f"{timestamp_id}-{i}"
                
                plat = random.choice(plats)
                heure = datetime.now().strftime("%H:%M:%S")
                
                # Format TEXTE pur
                ticket_template = (
                    f"PRINCIPALE\n"
                    f"LIVRAISON\n"
                    f"ADDITION #{unique_bill}\n"
                    f"Heure: {heure}\n"
                    f"TABLE # LIV\n"
                    f"SERVI PAR: {table_num}\n"
                    f"-------------------------------\n"
                    f"1 {plat}\n"
                    f"  * BIEN CUIT\n"
                    f"###############################\n"
                )
                
                # Injection dans le parser
                reader._process_ticket_line(ticket_template)
                self.log(f"Ticket {i+1}/20 injecté : Bill {unique_bill} | Table {table_num}")
            
            self.log("✅ Terminé. Les 20 commandes distinctes sont en base de données.")
            
            # --- REMPLACEMENT MESSAGEBOX SUCCÈS ---
            self.show_custom_alert(
                "Injection Réussie", 
                "Les 20 tickets de test (Tables 300-319) ont été injectés avec succès dans la base de données.",
                is_error=False
            )

        except Exception as e:
            self.log(f"❌ ERREUR : {str(e)}")
            
            # --- REMPLACEMENT MESSAGEBOX ERREUR ---
            self.show_custom_alert(
                "Erreur d'injection", 
                f"Une erreur est survenue lors de la génération massive :\n\n{e}",
                is_error=True
            )

    def refresh_ports(self):
        """ Scanne le système et croise avec ports.json """
        self.log("Scan des ports en cours...")
        
        # 1. Détection physique
        system_ports = serial.tools.list_ports.comports()
        detected = [f"{p.device} ({p.description})" for p in system_ports]
        
        # 2. Ajout des ports du JSON s'ils ne sont pas déjà dans la liste
        json_list = []
        for key, val in self.ports_config.items():
            json_list.append(f"{val} (Config: {key})")
        
        # Fusion et tri
        final_list = sorted(list(set(detected + json_list)))
        self.port_combo['values'] = final_list
        
        if final_list:
            self.port_combo.current(0)
            self.log(f"✅ {len(final_list)} port(s) identifié(s).")
        else:
            self.log("⚠️ Aucun port série détecté sur cette machine.")

    def log(self, msg):
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{stamp}] {msg}\n")
        self.log_text.see(tk.END)
        self.master.update()

    def send_data(self):
        target_raw = self.port_var.get()
        tpl_key = self.template_var.get()
        
        data = TEST_MODELS.get(tpl_key)
        if data is None:
            return # Séparateur ou titre de catégorie

        # On extrait uniquement le nom du port (ex: COM8 ou /dev/ttyUSB0)
        port_name = target_raw.split(' ')[0]

        if not port_name:
            self.show_custom_alert("Erreur Port", "Veuillez sélectionner un port série valide.", is_error=True)
            return

        try:
            # Désactive le bouton pendant l'envoi
            self.btn_send.config(state="disabled", bg="#7f8c8d")
            self.log(f"Tentative de connexion sur {port_name}...")
            
            with serial.Serial(port_name, 9600, timeout=1) as ser:
                self.log(f"Succès ! Envoi de {len(data)} octets...")
                
                # Envoi par paquets pour ne pas saturer le buffer de l'imprimante
                chunk = 16
                for i in range(0, len(data), chunk):
                    ser.write(data[i:i+chunk])
                    ser.flush()
                    time.sleep(0.05)
                
                self.log("✅ Données transmises.")

        except Exception as e:
            self.log(f"❌ ERREUR : {e}")
            # --- REMPLACEMENT DU MESSAGEBOX PAR L'ALERTE CUSTOM ---
            error_msg = f"Impossible de communiquer avec {port_name}.\n\nAssurez-vous que l'imprimante est allumée et n'est pas utilisée par un autre programme."
            self.show_custom_alert("Erreur Port Série", error_msg, is_error=True)
            
        finally:
            # Réactivation du bouton
            self.btn_send.config(state="normal", bg="#27ae60")

if __name__ == "__main__":
    app = POSSimulatorGUI()
    app.master.mainloop()