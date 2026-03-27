# config_menu.py (Version Complète avec Style Amélioré, Corrections Tkinter, Clavier Virtuel et Onglet Raccourcis)

import tkinter as tk
from tkinter import messagebox, ttk, colorchooser, filedialog
import json
import os
import sys
import shutil 
from datetime import datetime 
from typing import Dict, Any, List

import serial.tools.list_ports

import uuid
import subprocess
import platform

# Import du clavier virtuel
try:
    from keyboard import VirtualKeyboard
except ImportError:
    # Fallback pour le test si le fichier n'est pas dans le même dossier
    print("ATTENTION: Le fichier 'keyboard.py' est introuvable. Le clavier virtuel ne fonctionnera pas.")
    VirtualKeyboard = None

# ==============================================================================
# 🚨 ATTENTION : MOCK DATA (À REMPLACER PAR VOS IMPORTS RÉELS)
# ==============================================================================
KDS_CONFIG: Dict[str, Any] = {
    "STATUS_COLORS": {
        "En attente": "#3498db", "En cours": "#f1c40f", "Traitée": "#2ecc71", 
        "Annulée": "#e74c3c", "Archivée": "#7f8c8d"
    },
    "BG_MAIN": "#2c3e50", "CARD_BG": "#34495e", "MAX_CARDS_PER_ROW": 5, "SCROLL_PAGE_SIZE": 1, 
    "COLOR_TEXT": "#ecf0f1", "COLOR_ACCENT": "#3498db", "COLOR_WARNING": "#f1c40f", 
    "COLOR_NOTE": "#f1c40f", "H_SCROLLBAR_HEIGHT": 15, "CARD_WIDTH": 300, 
    "CARD_BORDER_WIDTH": 5, "CARD_PADDING": 5, "H_MARGIN": 5, 
    "SERVICE_TYPES": ["COMMANDE"], "SERVICE_SPLIT_MARKER": "AUTRE", 
    "REFRESH_RATE_MS": 3000, "TRUNCATE_LEN": 40, "ORDER_STATUS_PENDING": "En attente", 
    "BAUD_RATE": 9600, "SERIAL_TIMEOUT": 0.5, 
    "SERIAL_PORT_WINDOWS": "COM3",
    "SERIAL_PORT_2_WINDOWS": "COM9", 
    "SERIAL_PORT_PRINTER_WINDOWS": "COM4",
    "SERIAL_PORT_PRINTER_2_WINDOWS": "COM10", 
    "SERIAL_PORT_COMPUTER_WINDOWS": "COM5", 
    "TICKET_STATUS_COMPLETED": "TERMINÉ"
}

# --- Config de Ports par Défaut ---
DEFAULT_PORTS_CONFIG = {
    "windows_ports": {
        "SERIAL_PORT": "COM8",
        "SERIAL_PORT_2": "COM9",
        "SERIAL_PORT_3": "COM12",
        "SERIAL_PORT_PRINTER": "COM5",
        "SERIAL_PORT_PRINTER_2": "COM10",
        "SERIAL_PORT_PRINTER_3": "COM13",
        "SERIAL_PORT_COMPUTER": "COM6"
    },
    "linux_ports": {
        "SERIAL_PORT": "/dev/ttyUSB0",
        "SERIAL_PORT_2": "/dev/ttyUSB3",
        "SERIAL_PORT_3": "/dev/ttyUSB5",
        "SERIAL_PORT_PRINTER": "/dev/ttyUSB1",
        "SERIAL_PORT_PRINTER_2": "/dev/ttyUSB4",
        "SERIAL_PORT_PRINTER_3": "/dev/ttyUSB6",
        "SERIAL_PORT_COMPUTER": "/dev/ttyUSB2"
    }
}

AUTO_CLOSE_FILE = "fermeture_auto.json"
CONFIG_FILE = 'config_gui.json'
PORTS_CONFIG_FILE = 'ports.json' 
SHORTCUT_FILE = 'shortcut_word.json' # Nouveau fichier de raccourcis

DEFAULT_KDS_CONFIG = KDS_CONFIG.copy() 
DEFAULT_KDS_CONFIG.update({
    "CARD_WIDTH": 300, "CARD_PADDING": 5, "BG_MAIN": "#2c3e50", 
    "COLOR_TEXT": "#ecf0f1", "MAX_CARDS_PER_ROW": 5, "REFRESH_RATE_MS": 3000
})
# ==============================================================================

# --- MAPPING POUR LA CRÉATION DYNAMIQUE DES WIDGETS (config_gui.json) ---
CONFIG_MAP: Dict[str, Dict[str, Any]] = {
    # --- COULEURS ---
    "BG_MAIN": {"label": "Couleur de Fond Principal", "section": "Couleurs", "type": "color"},
    "CARD_BG": {"label": "Couleur de Fond des Cartes", "section": "Couleurs", "type": "color"},
    "COLOR_TEXT": {"label": "Couleur de Texte Principal", "section": "Couleurs", "type": "color"},
    "COLOR_ACCENT": {"label": "Couleur d'Accentuation/Bouton", "section": "Couleurs", "type": "color"},
    "COLOR_WARNING": {"label": "Couleur d'Avertissement (Exemple: Urgent)", "section": "Couleurs", "type": "color"},
    "COLOR_NOTE": {"label": "Couleur Note/Message Spécial", "section": "Couleurs", "type": "color"},
    
    # --- DIMENSIONS ET AFFICHAGE ---
    "CARD_WIDTH": {"label": "Largeur de la carte (px)", "section": "Dimensions", "type": "int"},
    "CARD_PADDING": {"label": "Marge interne carte (px)", "section": "Dimensions", "type": "int"},
    "CARD_BORDER_WIDTH": {"label": "Épaisseur Bordure Carte (px)", "section": "Dimensions", "type": "int"},
    "H_MARGIN": {"label": "Marge Horizontale Générale (px)", "section": "Dimensions", "type": "int"},
    "MAX_CARDS_PER_ROW": {"label": "Max. Cartes par Rangée", "section": "Dimensions", "type": "int"},
    "SCROLL_PAGE_SIZE": {"label": "Taille de Défilement (rangées)", "section": "Dimensions", "type": "int"},
    "H_SCROLLBAR_HEIGHT": {"label": "Hauteur Barre Défilement H (px)", "section": "Dimensions", "type": "int"},
    "TRUNCATE_LEN": {"label": "Longueur Max. Texte Tronqué", "section": "Dimensions", "type": "int"},
    
    # --- STATUTS ET SERVICES ---
    "ORDER_STATUS_PENDING": {"label": "Statut Initial de Commande", "section": "Statuts & Services", "type": "string"},
    "TICKET_STATUS_COMPLETED": {"label": "Statut de Fin de Ticket", "section": "Statuts & Services", "type": "string"},
    "SERVICE_SPLIT_MARKER": {"label": "Marqueur de Séparation de Service", "section": "Statuts & Services", "type": "string"},
    "SERVICE_TYPES": {"label": "Types de Service (séparés par virgule)", "section": "Statuts & Services", "type": "list"},
    
    # --- PERFORMANCES ET SÉRIE ---
    "REFRESH_RATE_MS": {"label": "Taux de Rafraîchissement (ms)", "section": "Technique & Perf.", "type": "int"},
    "BAUD_RATE": {"label": "Vitesse de Transmission Série (Baud)", "section": "Technique & Perf.", "type": "int"},
    "SERIAL_TIMEOUT": {"label": "Délai d'Attente Série (sec)", "section": "Technique & Perf.", "type": "float"},
    "SERIAL_PORT_WINDOWS": {"label": "Port Série KDS (Win) [config_gui]", "section": "Technique & Perf.", "type": "string"},
    "SERIAL_PORT_2_WINDOWS": {"label": "Port Série KDS 2 (Win) [config_gui]", "section": "Technique & Perf.", "type": "string"},
    "SERIAL_PORT_PRINTER_WINDOWS": {"label": "Port Série Imprimante (Win) [config_gui]", "section": "Technique & Perf.", "type": "string"},
    "SERIAL_PORT_PRINTER_2_WINDOWS": {"label": "Port Série Imprimante 2 (Win) [config_gui]", "section": "Technique & Perf.", "type": "string"},
    "SERIAL_PORT_COMPUTER_WINDOWS": {"label": "Port Série Ordinateur (Win) [config_gui]", "section": "Technique & Perf.", "type": "string"},
}

# --- MAPPING POUR LA CRÉATION DYNAMIQUE DES WIDGETS (ports.json) ---
PORTS_CONFIG_MAP: Dict[str, Dict[str, Dict[str, Any]]] = {
    "windows_ports": {
        "SERIAL_PORT": {"label": "KDS (Win)", "type": "string"},
        "SERIAL_PORT_2": {"label": "KDS 2 (Win)", "type": "string"},
        "SERIAL_PORT_3": {"label": "KDS 3 (Win)", "type": "string"},
        "SERIAL_PORT_PRINTER": {"label": "Imprimante (Win)", "type": "string"},
        "SERIAL_PORT_PRINTER_2": {"label": "Imprimante 2 (Win)", "type": "string"},
        "SERIAL_PORT_PRINTER_3": {"label": "Imprimante 3 (Win)", "type": "string"},
        "SERIAL_PORT_COMPUTER": {"label": "Ordinateur (Win)", "type": "string"}
    },
    "linux_ports": {
        "SERIAL_PORT": {"label": "KDS (Linux)", "type": "string"},
        "SERIAL_PORT_2": {"label": "KDS 2 (Linux)", "type": "string"},
        "SERIAL_PORT_3": {"label": "KDS 3 (Linux)", "type": "string"},
        "SERIAL_PORT_PRINTER": {"label": "Imprimante (Linux)", "type": "string"},
        "SERIAL_PORT_PRINTER_2": {"label": "Imprimante 2 (Linux)", "type": "string"},
        "SERIAL_PORT_PRINTER_3": {"label": "Imprimante 3 (Linux)", "type": "string"},
        "SERIAL_PORT_COMPUTER": {"label": "Ordinateur (Linux)", "type": "string"}
    }
}


class ConfigMenu(tk.Toplevel):
    
    def __init__(self, master):
        super().__init__(master)
        self.title("Configuration KDS (Optimisé Tactile)")
        self.geometry("800x850") 
        self.transient(master) 
        
        self.working_config: Dict[str, Any] = KDS_CONFIG.copy() 
        self.temp_config: Dict[str, Any] = {} 
        self.color_vars: Dict[str, tk.StringVar] = {} 
        self.status_color_vars: Dict[str, tk.StringVar] = {} 

        self.working_ports_config: Dict[str, Any] = self._load_ports_config() 
        self.temp_ports_config: Dict[str, Any] = {} 

        # --- NOUVEAU: Configuration des raccourcis ---
        self.working_shortcuts: List[str] = self._load_shortcuts_config()
        self.shortcut_list_var = tk.StringVar(value="\n".join(self.working_shortcuts))
        self.shortcut_listbox: Any = None # Pour stocker la référence au Listbox

        # --- Définition des constantes de couleur pour les styles ---
        BG_MAIN = KDS_CONFIG["BG_MAIN"]       # #2c3e50 (Fond Principal)
        CARD_BG = KDS_CONFIG["CARD_BG"]       # #34495e (Fond Carte/Widget)
        COLOR_TEXT = KDS_CONFIG["COLOR_TEXT"] # #ecf0f1 (Texte Clair)
        COLOR_ACCENT = KDS_CONFIG["COLOR_ACCENT"] # #3498db (Bleu Vif)
        COLOR_SAVE = KDS_CONFIG["STATUS_COLORS"].get("Traitée", "#2ecc71") # Vert pour Sauvegarder
        COLOR_QUIT = KDS_CONFIG["STATUS_COLORS"].get("Annulée", "#e74c3c") # Rouge pour Annuler/Quitter/Reset
        COLOR_RESTORE = KDS_CONFIG["COLOR_WARNING"] # #f1c40f (Jaune/Orange pour Restaurer)

        # --- Styles Optimisés Tactile (Amélioration du look) ---
        font_size = 14
        style = ttk.Style()
        style.theme_use('clam')

        # 1. Styles généraux (Dark Theme)
        self.config(bg=BG_MAIN) # Arrière-plan de la fenêtre Toplevel
        style.configure(".", background=BG_MAIN, foreground=COLOR_TEXT)
        style.configure("TFrame", background=BG_MAIN)
        style.configure("TLabel", font=("Helvetica", font_size), background=BG_MAIN, foreground=COLOR_TEXT)
        style.configure("TNotebook", background=BG_MAIN, borderwidth=0)
        style.configure("TNotebook.Tab", background=CARD_BG, foreground=COLOR_TEXT, padding=[15, 10]) # Onglets sombres
        style.map("TNotebook.Tab", 
                  background=[("selected", COLOR_ACCENT), ('active', CARD_BG)], 
                  foreground=[("selected", 'white'), ('active', COLOR_TEXT)])
        
        # Entrées (Entries)
        # 🚨 Modification pour Entry - pour une meilleure intégration tactile (ajout du curseur)
        style.configure("TEntry", fieldbackground=CARD_BG, foreground=COLOR_TEXT, borderwidth=1, relief="flat", padding=5)
        
        # En-têtes et descriptions
        style.configure("Header.TLabel", font=("Helvetica", font_size + 2, "bold"), foreground=COLOR_ACCENT, background=BG_MAIN)
        style.configure("AdminDesc.TLabel", wraplength=700, font=("Helvetica", font_size - 4, "italic"), foreground='#95a5a6', background=BG_MAIN)

        # 2. Styles des Boutons de Contrôle et d'Administration
        
        # Style général des boutons (pour les boutons "Choisir couleur")
        style.configure("TButton", font=("Helvetica", font_size, "bold"), padding=10, background=CARD_BG, foreground=COLOR_TEXT) 
        style.map("TButton", background=[('active', BG_MAIN)])

        # ⭐ Gros bouton Sauvegarder (Vert)
        style.configure("Save.TButton", 
                        foreground='white', 
                        background=COLOR_SAVE, 
                        borderwidth=0, 
                        font=("Helvetica", font_size + 4, "bold"))
        style.map("Save.TButton", background=[('active', '#27ae60')]) # Vert foncé à l'activation

        # Styles pour les boutons d'administration (taille tactile)
        for style_name in ["Backup.TButton", "Restore.TButton", "Reset.TButton", "AddRemove.TButton"]:
             style.configure(style_name, font=("Helvetica", font_size, "bold"), padding=10, foreground='white')

        # 🚀 Alignement des couleurs d'administration
        style.configure("Backup.TButton", background=COLOR_ACCENT) # Bleu d'accentuation
        style.map("Backup.TButton", background=[('active', '#2980b9')])

        style.configure("Restore.TButton", background=COLOR_RESTORE, foreground=BG_MAIN) # Jaune Avertissement
        style.map("Restore.TButton", background=[('active', '#d35400')]) 
        
        style.configure("AddRemove.TButton", background='#16a085', foreground='white') # Turquoise pour Ajouter/Retirer
        style.map("AddRemove.TButton", background=[('active', '#1abc9c')]) 

        # ❌ Bouton Quitter/Réinitialiser (Rouge)
        style.configure("Reset.TButton", background=COLOR_QUIT) 
        style.map("Reset.TButton", background=[('active', '#c0392b')]) # Rouge foncé à l'activation
        
        # 3. Style pour la Scrollbar Verticale 
        style.layout('Vertical.TScrollbar', 
            [('Vertical.Scrollbar.trough',
              {'children': [('Vertical.Scrollbar.thumb', {'expand': '1', 'sticky': 'ns'})],
               'sticky': 'ns'})])
        style.configure('Vertical.TScrollbar', troughcolor=BG_MAIN, background=COLOR_ACCENT, width=30) 
        style.map('Vertical.TScrollbar', background=[('active', COLOR_ACCENT)])
        
        
        # --- Frame principale pour les onglets (Notebook) ---
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=(15, 0)) 

        # --- Onglet 1: Configuration Générale (config_gui.json) ---
        self.config_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.config_tab, text="⚙️ Configuration Générale")
        self._create_config_tab_content(self.config_tab)

        # --- Onglet 2: Ports Série (ports.json) ---
        self.ports_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.ports_tab, text="🔌 Ports Série")
        self._create_ports_tab_content(self.ports_tab)

        # --- NOUVEAU Onglet 3: Raccourcis de Mots (shortcut_word.json) ---
        self.shortcut_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.shortcut_tab, text="📝 Raccourcis")
        self._create_shortcut_tab_content(self.shortcut_tab)

        # --- Onglet 4: Sauvegarde & Administration ---
        self.admin_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.admin_tab, text="💾 Sauvegarde & Admin")
        self._create_admin_tab_content(self.admin_tab)

        # --- Onglet 5: Licence & Matériel (Nouveau) ---
        self.license_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.license_tab, text="🔑 Licence")
        self._create_license_tab_content(self.license_tab)

        # ⭐ NOUVEAU - Onglet 6: Auto-Fermeture
        self.auto_close_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.auto_close_tab, text="🍕 Auto-Fermeture")
        self._create_auto_close_tab_content(self.auto_close_tab)

        # À la fin de la méthode _create_widgets(self):
        self.tab_serveuses = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_serveuses, text="Serveuses")
        self._setup_serveuses_tab()
        
        # Boutons de contrôle en bas
        control_frame = ttk.Frame(self)
        control_frame.pack(fill='x', padx=15, pady=15) 
        
        # ⭐ Gros bouton Quitter à gauche (Utilise Reset.TButton pour le rouge)
        ttk.Button(control_frame, text="❌ Quitter (Annuler)", command=self.destroy,
                   style="Reset.TButton").pack(side='left', padx=10, ipady=10)

        # Bouton Sauvegarder à droite (Utilise Save.TButton pour le vert)
        ttk.Button(control_frame, text="✅ Sauvegarder et Appliquer", style="Save.TButton", 
                   command=self._save_all_configs).pack(side='right', padx=10, ipady=10)

    # --------------------------------------------------------------------------
    # --- MÉTHODES DE CHARGEMENT DE CONFIGURATION ---
    # --------------------------------------------------------------------------

    def _get_hardware_info(self):
        """Récupère l'adresse MAC et le numéro de série du disque pour PyArmor."""
        # 1. Récupération de l'adresse MAC
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff)
                         for ele in range(0, 8*6, 8)][::-1]).upper()
        
        # 2. Récupération du numéro de série du disque (Windows)
        disk_serial = "Non disponible"
        try:
            if platform.system() == "Windows":
                # Utilise WMIC pour obtenir le numéro de série du disque physique
                cmd = "wmic diskdrive get serialnumber"
                output = subprocess.check_output(cmd, shell=True).decode().split()
                if len(output) >= 2:
                    disk_serial = output[1].strip()
            else:
                # Commande simplifiée pour Linux (nécessite souvent les droits root)
                disk_serial = "Utiliser 'lsblk -d -no serial' sur Linux"
        except Exception:
            disk_serial = "Erreur de lecture"

        return mac, disk_serial

    

    def _create_auto_close_tab_content(self, parent):
        """ Crée l'interface pour gérer les mots-clés de fermeture automatique """
        # Récupération des couleurs depuis la config globale pour match avec votre style
        BG_MAIN = KDS_CONFIG.get("BG_MAIN", "#2c3e50")
        COLOR_ACCENT = KDS_CONFIG.get("COLOR_ACCENT", "#3498db")
        COLOR_TEXT = KDS_CONFIG.get("COLOR_TEXT", "#ecf0f1")
        CARD_BG = KDS_CONFIG.get("CARD_BG", "#34495e")

        container = tk.Frame(parent, bg=BG_MAIN, padx=20, pady=20)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(container, text="Gestion de l'Auto-Fermeture (60 secondes)", 
                 font=("Helvetica", 16, "bold"), fg=COLOR_ACCENT, bg=BG_MAIN).pack(pady=(0, 5))
        
        tk.Label(container, text="Tickets avec 1 seul item correspondant à ces mots = Fermeture auto après 1 min.", 
                 font=("Helvetica", 10, "italic"), fg="#95a5a6", bg=BG_MAIN).pack(pady=(0, 15))

        # --- Zone Listbox (Optimisée Tactile) ---
        list_frame = tk.Frame(container, bg=BG_MAIN)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.auto_close_listbox = tk.Listbox(
            list_frame, font=("Helvetica", 14), bg=CARD_BG, fg=COLOR_TEXT, 
            selectbackground=COLOR_ACCENT, bd=0, highlightthickness=1,
            activestyle='none'
        )
        self.auto_close_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar large pour le tactile
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.auto_close_listbox.yview, style="Vertical.TScrollbar")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.auto_close_listbox.config(yscrollcommand=scrollbar.set)

        # --- Zone d'Ajout ---
        add_frame = tk.Frame(container, bg=BG_MAIN, pady=20)
        add_frame.pack(fill=tk.X)

        self.new_item_entry = tk.Entry(add_frame, font=("Helvetica", 16), bg="white", fg="black", bd=2)
        self.new_item_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 15), ipady=8)
        
        # ⭐ CORRECTIF CLAVIER : On utilise <Button-1> (le clic) au lieu de <FocusIn>
        # Cela évite que le clavier ne boucle à chaque lettre tapée.
        if VirtualKeyboard:
            self.new_item_entry.bind("<Button-1>", lambda e: VirtualKeyboard(self, self.new_item_entry, "Nouveau mot-clé"))

        btn_add = tk.Button(add_frame, text="➕ AJOUTER", command=self._add_auto_close_item,
                             bg='#2ecc71', fg='white', font=("Helvetica", 12, "bold"), 
                             width=12, relief=tk.FLAT, padx=10)
        btn_add.pack(side=tk.RIGHT, fill=tk.Y)

        # --- Bouton Supprimer ---
        btn_del = tk.Button(container, text="🗑️ SUPPRIMER L'ÉLÉMENT SÉLECTIONNÉ", 
                             command=self._delete_auto_close_item,
                             bg='#e74c3c', fg='white', font=("Helvetica", 12, "bold"), 
                             height=2, relief=tk.FLAT)
        btn_del.pack(fill=tk.X, pady=(10, 0))

        # Chargement initial
        self._refresh_auto_close_list()

    def _refresh_auto_close_list(self):
        """ Lit le fichier JSON et remplit la Listbox """
        self.auto_close_listbox.delete(0, tk.END)
        if os.path.exists(AUTO_CLOSE_FILE):
            try:
                with open(AUTO_CLOSE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    items = data.get("pizza_sizes", [])
                    for item in sorted(items):
                        self.auto_close_listbox.insert(tk.END, item)
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur de lecture JSON: {e}")

    def _add_auto_close_item(self):
        """ Ajoute un item à la liste et sauvegarde """
        val = self.new_item_entry.get().strip().upper()
        if not val: return
        
        current_items = self.auto_close_listbox.get(0, tk.END)
        if val in current_items:
            messagebox.showwarning("Doublon", "Ce mot-clé existe déjà.")
            return

        self.auto_close_listbox.insert(tk.END, val)
        self.new_item_entry.delete(0, tk.END)
        self._save_auto_close_to_json()

    def _delete_auto_close_item(self):
        """ Supprime l'item sélectionné et sauvegarde """
        selection = self.auto_close_listbox.curselection()
        if not selection:
            messagebox.showwarning("Sélection", "Veuillez sélectionner un élément à supprimer.")
            return
        
        if messagebox.askyesno("Confirmation", "Voulez-vous supprimer ce mot-clé ?"):
            self.auto_close_listbox.delete(selection)
            self._save_auto_close_to_json()

    def _save_auto_close_to_json(self):
        """ Sauvegarde le contenu de la listbox dans le fichier fermeture_auto.json """
        items = list(self.auto_close_listbox.get(0, tk.END))
        try:
            with open(AUTO_CLOSE_FILE, 'w', encoding='utf-8') as f:
                json.dump({"pizza_sizes": items}, f, indent=4, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Erreur Sauvegarde", f"Échec de l'écriture: {e}")


    def _create_license_tab_content(self, tab: ttk.Frame):
        """Crée l'onglet pour afficher les infos de licence PyArmor avec texte voyant."""
        accent = KDS_CONFIG.get("COLOR_ACCENT", "#3498db")
        
        frame = ttk.Frame(tab, padding=25)
        frame.pack(fill='both', expand=True)

        ttk.Label(frame, text="🔑 IDENTIFIANTS MATÉRIEL (PYARMOR)", 
                  font=("Helvetica", 16, "bold"), foreground=accent).pack(pady=(0, 20))

        mac, disk = self._get_hardware_info()

        # --- Style pour les informations voyantes ---
        # On utilise une couleur vive (Orange : #e67e22) et une police plus grande
        STYLE_VOYANT = ("Courier", 16, "bold")
        COULEUR_ALERTE = "#e67e22" 

        # Affichage de l'adresse MAC
        ttk.Label(frame, text="ADRESSE MAC :", font=("Helvetica", 12, "bold")).pack(anchor="w")
        mac_label = tk.Label(frame, text=mac, font=STYLE_VOYANT, 
                             fg=COULEUR_ALERTE, bg=KDS_CONFIG.get("BG_MAIN", "#2c3e50"),
                             pady=10, padx=10, relief="sunken")
        mac_label.pack(fill='x', pady=(5, 20))

        # Affichage du Numéro de série du disque
        ttk.Label(frame, text="SÉRIE DU DISQUE (HDD SERIAL) :", font=("Helvetica", 12, "bold")).pack(anchor="w")
        disk_label = tk.Label(frame, text=disk, font=STYLE_VOYANT, 
                              fg=COULEUR_ALERTE, bg=KDS_CONFIG.get("BG_MAIN", "#2c3e50"),
                              pady=10, padx=10, relief="sunken")
        disk_label.pack(fill='x', pady=(5, 20))

        ttk.Label(frame, text="⚠️ Note: Notez exactement ces codes pour générer votre licence.", 
                  foreground="#f1c40f", font=("Helvetica", 10, "italic")).pack(pady=20)

    def _refresh_license_tab(self, m_entry, d_entry):
        mac, disk = self._get_hardware_info()
        m_entry.config(state='normal')
        d_entry.config(state='normal')
        m_entry.delete(0, tk.END)
        d_entry.delete(0, tk.END)
        m_entry.insert(0, mac)
        d_entry.insert(0, disk)
        m_entry.config(state='readonly')
        d_entry.config(state='readonly')

    def _load_ports_config(self) -> Dict[str, Any]:
        """ Charge le contenu de ports.json ou retourne la config par défaut. """
        try:
            if os.path.exists(PORTS_CONFIG_FILE):
                with open(PORTS_CONFIG_FILE, 'r') as f:
                    return json.load(f)
            else:
                return DEFAULT_PORTS_CONFIG.copy()
        except Exception:
            # Si le fichier est corrompu, on utilise la version par défaut
            return DEFAULT_PORTS_CONFIG.copy()
            
    def _load_shortcuts_config(self) -> List[str]:
        """ Charge le contenu de shortcut_word.json ou retourne une liste par défaut. """
        try:
            if os.path.exists(SHORTCUT_FILE):
                with open(SHORTCUT_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get("shortcuts", [])
            else:
                # Configuration par défaut si le fichier n'existe pas
                return [
                    "REMPLACER", "PAR", "PAS DE", "CHEF", "CÉSAR", 
                    "FRITES", "SALADE", "PAT. ANCIENNES", "PAS DE LÉGUMES", 
                    "EXTRA SAUCE", "RIZ", "SANS OIGNONS", "BIEN CUIT"
                ]
        except Exception:
            # Si le fichier est corrompu, on utilise la version par défaut
            messagebox.showwarning("Erreur de Fichier", f"Le fichier '{SHORTCUT_FILE}' est corrompu ou illisible. Chargement des raccourcis par défaut.")
            return []


    # --------------------------------------------------------------------------
    # --- CRÉATION DE L'ONGLET CONFIGURATION GÉNÉRALE (config_gui.json) ---
    # --------------------------------------------------------------------------

    def _create_config_tab_content(self, tab: ttk.Frame):
        """ Crée le contenu de l'onglet de configuration générale (avec scrollbar). """
        
        main_frame = ttk.Frame(tab)
        main_frame.pack(fill="both", expand=True)
        
        # L'arrière-plan du canvas doit être configuré pour le thème sombre
        canvas = tk.Canvas(main_frame, borderwidth=0, highlightthickness=0, bg=KDS_CONFIG["BG_MAIN"])
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview, style='Vertical.TScrollbar') 
        
        self.scrollable_frame_config = ttk.Frame(canvas) 
        
        canvas_window = canvas.create_window((0, 0), window=self.scrollable_frame_config, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(canvas_window, width=canvas.winfo_width())

        self.scrollable_frame_config.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_frame_configure) 

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.scrollable_frame_config.columnconfigure(0, weight=1)
        
        self._create_widgets_dynamically() 

    def _setup_serveuses_tab(self):
        """Configure l'onglet Serveuses avec Ajout, Export et Import (Sans modification de nom)."""
        bg_main = KDS_CONFIG.get("BG_MAIN", "#2c3e50")
        txt_col = KDS_CONFIG.get("COLOR_TEXT", "#ecf0f1")
        
        main_frame = tk.Frame(self.tab_serveuses, bg=bg_main)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.active_keyboard = None

        # --- Barre d'outils (Export/Import) ---
        tools_frame = tk.Frame(main_frame, bg=bg_main)
        tools_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(tools_frame, text="💾 Exporter Liste (Sauvegarde)", command=self._export_serveuses,
                  bg="#34495e", fg="white", font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        tk.Button(tools_frame, text="📂 Importer Liste (Restauration)", command=self._import_serveuses,
                  bg="#34495e", fg="white", font=("Arial", 9)).pack(side=tk.LEFT, padx=5)

        # --- Section Ajout ---
        add_frame = tk.LabelFrame(main_frame, text="Ajouter une Serveuse", bg=bg_main, fg=txt_col, padx=10, pady=10)
        add_frame.pack(fill=tk.X, pady=5)

        tk.Label(add_frame, text="Nom:", bg=bg_main, fg=txt_col).pack(side=tk.LEFT)
        self.new_serveuse_name = tk.Entry(add_frame, width=20, font=("Arial", 12))
        self.new_serveuse_name.pack(side=tk.LEFT, padx=5)

        # Le clavier s'ouvre seulement si on clique dans la case
        self.new_serveuse_name.bind("<Button-1>", lambda e: self._open_keyboard(self.new_serveuse_name))

        tk.Button(add_frame, text="➕ Ajouter", command=self._add_serveuse_action, 
                  bg="#2ecc71", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=5)

        # --- Liste des serveuses ---
        list_frame = tk.LabelFrame(main_frame, text="Liste des Serveuses (Cliquez sur la couleur pour modifier)", 
                                   bg=bg_main, fg=txt_col, padx=10, pady=10)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.serv_canvas = tk.Canvas(list_frame, bg=bg_main, highlightthickness=0)
        self.serv_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.serv_canvas.yview)
        self.serv_scrollable_frame = tk.Frame(self.serv_canvas, bg=bg_main)

        self.serv_scrollable_frame.bind("<Configure>", lambda e: self.serv_canvas.configure(scrollregion=self.serv_canvas.bbox("all")))
        self.serv_canvas.create_window((0, 0), window=self.serv_scrollable_frame, anchor="nw", width=450)
        self.serv_canvas.configure(yscrollcommand=self.serv_scrollbar.set)
        self.serv_canvas.pack(side="left", fill="both", expand=True)
        self.serv_scrollbar.pack(side="right", fill="y")

        self.tab_serveuses.focus_set()
        self._refresh_serveuses_list()

    def _refresh_serveuses_list(self):
        """Affiche la liste simplifiée (Couleur + Nom + Supprimer)."""
        for widget in self.serv_scrollable_frame.winfo_children():
            widget.destroy()

        bg_main = KDS_CONFIG.get("BG_MAIN", "#2c3e50")
        txt_col = KDS_CONFIG.get("COLOR_TEXT", "#ecf0f1")
        data = self._load_serv_json('serveuses_config.json')

        for name, color in data.items():
            if name == "DEFAULT_COLOR": continue
            row = tk.Frame(self.serv_scrollable_frame, bg=bg_main, pady=5)
            row.pack(fill=tk.X)

            # Bouton de couleur (Palette)
            btn_col = tk.Button(row, bg=color, width=4, relief=tk.RAISED,
                                command=lambda n=name, c=color: self._change_serveuse_color(n, c))
            btn_col.pack(side=tk.LEFT, padx=10)

            # Nom de la serveuse
            tk.Label(row, text=name, bg=bg_main, fg=txt_col, font=("Arial", 11, "bold"), 
                     width=25, anchor="w").pack(side=tk.LEFT)

            # Bouton Supprimer uniquement
            tk.Button(row, text=" 🗑️ ", command=lambda n=name: self._delete_serveuse(n),
                      bg="#e74c3c", fg="white", relief=tk.FLAT).pack(side=tk.RIGHT, padx=10)

    # --- FONCTIONS DE SAUVEGARDE EXTERNE ---

    def _export_serveuses(self):
        """Sauvegarde une copie de la config ailleurs (clé USB, bureau, etc)."""
        path = filedialog.asksaveasfilename(defaultextension=".json", initialfile="backup_serveuses.json",
                                            title="Exporter la liste des serveuses")
        if path:
            data = self._load_serv_json('serveuses_config.json')
            self._save_serv_json(path, data)
            messagebox.showinfo("Succès", "Sauvegarde terminée !")

    def _import_serveuses(self):
        """Restaure une liste à partir d'un fichier JSON."""
        path = filedialog.askopenfilename(filetypes=[("Fichiers JSON", "*.json")],
                                          title="Importer une liste de serveuses")
        if path:
            if messagebox.askyesno("Attention", "Cela écrasera votre liste actuelle. Continuer ?"):
                data = self._load_serv_json(path)
                self._save_serv_json('serveuses_config.json', data)
                self._refresh_serveuses_list()

    # --- UTILS ---

    def _open_keyboard(self, target):
        """Ouvre le clavier pour le champ spécifié."""
        if VirtualKeyboard and (self.active_keyboard is None or not self.active_keyboard.winfo_exists()):
            self.active_keyboard = VirtualKeyboard(self, target, lambda: None)

    def _load_serv_json(self, path):
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f: return json.load(f)
            except: pass
        return {"DEFAULT_COLOR": "#FFFFFF"}

    def _save_serv_json(self, path, data):
        try:
            with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)
        except Exception as e: messagebox.showerror("Erreur", str(e))

    def _add_serveuse_action(self):
        """Ajoute la serveuse et ferme le clavier."""
        name = self.new_serveuse_name.get().strip().upper()
        if not name: return
        data = self._load_serv_json('serveuses_config.json')
        if name not in data:
            data[name] = "#FFFFFF"
            self._save_serv_json('serveuses_config.json', data)
            self.new_serveuse_name.delete(0, tk.END)
            # Fermer le clavier si ouvert
            if self.active_keyboard and self.active_keyboard.winfo_exists():
                self.active_keyboard.destroy()
            self._refresh_serveuses_list()
            self.tab_serveuses.focus_set()

    def _delete_serveuse(self, name):
        if messagebox.askyesno("Supprimer", f"Voulez-vous supprimer {name} ?"):
            data = self._load_serv_json('serveuses_config.json')
            if name in data:
                del data[name]
                self._save_serv_json('serveuses_config.json', data)
                self._refresh_serveuses_list()

    def _change_serveuse_color(self, name, current_color):
        color_code = colorchooser.askcolor(initialcolor=current_color, title=f"Couleur pour {name}")
        if color_code[1]:
            data = self._load_serv_json('serveuses_config.json')
            data[name] = color_code[1]
            self._save_serv_json('serveuses_config.json', data)
            self._refresh_serveuses_list()
            
    def _create_widgets_dynamically(self):
        """ Crée les widgets en se basant sur la CONFIG_MAP (sans titres de section visibles). """
        
        grouped_keys: Dict[str, list] = {}
        for key, details in CONFIG_MAP.items():
            section = details["section"]
            if section not in grouped_keys:
                grouped_keys[section] = []
            grouped_keys[section].append(key)
            
        row_counter = 0
        
        for section_title, keys in grouped_keys.items():
            frame = self._create_section_frame_flat(self.scrollable_frame_config, row_counter)
            row_counter += 1
            
            internal_row = 0
            for key in keys:
                details = CONFIG_MAP[key]
                widget_type = details["type"]
                label = details["label"]
                
                if widget_type in ('int', 'float', 'string'):
                    self._create_input_field(frame, key, label, widget_type, internal_row)
                elif widget_type == 'list':
                    self._create_list_input(frame, key, label, internal_row)
                elif widget_type == 'color':
                    self._create_color_picker(frame, key, label, internal_row)
                
                internal_row += 1

        # Ajout de l'éditeur de couleurs des Statuts (Séparé)
        self._create_status_color_section(self.scrollable_frame_config, row_counter)

    
    def _create_section_frame_flat(self, master: ttk.Frame, row: int):
        """ Crée un cadre simple (sans titre ni groove) pour le regroupement interne. """
        frame = ttk.Frame(master, padding="10")
        frame.grid(row=row, column=0, sticky='ew', padx=10, pady=(0, 10))
        frame.columnconfigure(1, weight=1)
        return frame

    # 🚨 Modification: Ajout de l'événement de clic pour le clavier virtuel
    def _create_input_field(self, master: ttk.Frame, key: str, label: str, widget_type: str, row: int):
        """ Crée des champs d'entrée simples (int, float, string) adaptés au tactile avec support clavier virtuel. """
        ttk.Label(master, text=label + ":").grid(row=row, column=0, sticky='w', padx=5, pady=5)
        
        var = tk.StringVar(value=str(self.working_config[key]))
        self.temp_config[key] = var 
        
        entry = ttk.Entry(master, textvariable=var, width=30, font=("Helvetica", 14)) 
        entry.grid(row=row, column=1, sticky='ew', padx=5, pady=5, ipady=5) 
        
        var.widget_type = widget_type 

        # 🚀 CLAVIER VIRTUEL
        if VirtualKeyboard:
            # Lier un clic sur le champ à l'ouverture du clavier
            entry.bind("<Button-1>", lambda e, entry=entry: self._show_keyboard(entry))
            # S'assurer que le focus n'est pas pris par l'Entry pour éviter le clavier OS
            entry.bind("<FocusIn>", lambda e: self.focus_set())
            
    # 🚨 Modification: Ajout de l'événement de clic pour le clavier virtuel
    def _create_list_input(self, master: ttk.Frame, key: str, label: str, row: int):
        """ Crée un champ d'entrée pour les listes (séparées par des virgules) avec support clavier virtuel. """
        ttk.Label(master, text=label + ":").grid(row=row, column=0, sticky='w', padx=5, pady=5)
        
        initial_value = ", ".join(self.working_config[key]) if isinstance(self.working_config[key], list) else str(self.working_config[key])
        var = tk.StringVar(value=initial_value)
        
        self.temp_config[key] = var 
        
        entry = ttk.Entry(master, textvariable=var, width=30, font=("Helvetica", 14)) 
        entry.grid(row=row, column=1, sticky='ew', padx=5, pady=5, ipady=5) 
        
        var.widget_type = 'list'

        # 🚀 CLAVIER VIRTUEL
        if VirtualKeyboard:
            entry.bind("<Button-1>", lambda e, entry=entry: self._show_keyboard(entry))
            entry.bind("<FocusIn>", lambda e: self.focus_set())


    def _create_color_picker(self, master: ttk.Frame, key: str, label: str, row: int):
        """ Crée un sélecteur de couleur pour une clé de configuration simple. """
        ttk.Label(master, text=label + ":").grid(row=row, column=0, sticky='w', padx=5, pady=5)
        
        current_color = self.working_config.get(key, "#FFFFFF")
        var = tk.StringVar(value=current_color)
        self.color_vars[key] = var 
        
        color_frame = ttk.Frame(master)
        color_frame.grid(row=row, column=1, sticky='ew', padx=5, pady=5)
        
        color_box = tk.Label(color_frame, bg=current_color, width=5, relief=tk.RAISED, borderwidth=1)
        color_box.pack(side='left', padx=5)
        
        ttk.Button(color_frame, text="Choisir la Couleur", 
                   command=lambda k=key, box=color_box: self._pick_color(k, box),
                   style="TButton").pack(side='left', fill='x', expand=True)


    def _pick_color(self, key: str, color_box: tk.Label):
        """ Ouvre le dialogue de choix de couleur et met à jour la config et le widget. """
        # Empêcher le clavier virtuel d'apparaître sur la fenêtre du colorchooser
        self.unbind_all("<Button-1>") 

        color_code = colorchooser.askcolor(title=f"Choisir la couleur pour {key}")
        
        if color_code and color_code[1]: 
            hex_color = color_code[1].upper()
            
            if key in self.color_vars:
                self.color_vars[key].set(hex_color)
            
            self.working_config[key] = hex_color
            
            color_box.config(bg=hex_color)

        # Réactiver la liaison après le choix de couleur
        self.bind_all("<Button-1>", lambda e: self.focus_set())
            

    def _create_status_color_section(self, master: ttk.Frame, row: int):
        """ Crée la section pour l'édition des couleurs de statut. """
        
        ttk.Separator(master, orient='horizontal').grid(row=row, column=0, sticky='ew', padx=10, pady=(20, 10))
        
        status_frame = ttk.Frame(master, padding="10")
        status_frame.grid(row=row + 1, column=0, sticky='ew', padx=10, pady=(0, 10))
        status_frame.columnconfigure(0, weight=1)
        
        ttk.Label(status_frame, text="Couleurs des Statuts de Commande :", font=("Helvetica", 14, "bold")).pack(pady=(0, 10))
        
        inner_grid = ttk.Frame(status_frame)
        inner_grid.pack(fill='x', padx=50)
        inner_grid.columnconfigure(1, weight=1)
        
        statuses = sorted(self.working_config["STATUS_COLORS"].keys())
        
        for i, status in enumerate(statuses):
            current_color = self.working_config["STATUS_COLORS"].get(status, "#FFFFFF")
            
            ttk.Label(inner_grid, text=f"Statut '{status}':").grid(row=i, column=0, sticky='w', padx=5, pady=5)
            
            color_frame = ttk.Frame(inner_grid)
            color_frame.grid(row=i, column=1, sticky='ew', padx=5, pady=5)

            color_box = tk.Label(color_frame, bg=current_color, width=5, relief=tk.RAISED, borderwidth=1)
            color_box.pack(side='left', padx=5)
            
            ttk.Button(color_frame, text="Choisir", 
                       command=lambda s=status, box=color_box: self._pick_status_color(s, box),
                       style="TButton").pack(side='left', fill='x', expand=True)

    
    def _pick_status_color(self, status: str, color_box: tk.Label):
        """ Ouvre le dialogue de choix de couleur pour un statut. """
        # Empêcher le clavier virtuel d'apparaître sur la fenêtre du colorchooser
        self.unbind_all("<Button-1>") 
        
        color_code = colorchooser.askcolor(title=f"Choisir la couleur pour le statut: {status}")
        
        if color_code and color_code[1]: 
            hex_color = color_code[1].upper()
            
            self.working_config["STATUS_COLORS"][status] = hex_color
            
            color_box.config(bg=hex_color)

        # Réactiver la liaison après le choix de couleur
        self.bind_all("<Button-1>", lambda e: self.focus_set())


    # --------------------------------------------------------------------------
    # --- CRÉATION DE L'ONGLET PORTS SÉRIE (ports.json) ---
    # --------------------------------------------------------------------------

    def _create_ports_tab_content(self, tab: ttk.Frame):
        """ Crée le contenu de l'onglet de configuration des ports avec détection automatique. """
        
        # Panneau principal
        main_frame = ttk.Frame(tab, padding=20)
        main_frame.pack(fill='both', expand=True)
        
        # --- COLONNE DE GAUCHE : CONFIGURATION (Scrollable si nécessaire) ---
        left_side = ttk.Frame(main_frame)
        left_side.pack(side='left', fill='both', expand=True, padx=(0, 20))

        ttk.Label(left_side, text="⚠️ Les ports sont sauvegardés dans ports.json.", 
                  style="AdminDesc.TLabel", wraplength=500, foreground='#f1c40f').pack(anchor='w', pady=(0, 15))

        # Conteneur pour les champs de saisie (Utilise grid à l'intérieur pour l'alignement)
        config_container = ttk.Frame(left_side)
        config_container.pack(fill='both', expand=True)
        config_container.columnconfigure(1, weight=1)

        self._create_ports_section(config_container, "Windows", "windows_ports", 0)
        self._create_ports_section(config_container, "Linux", "linux_ports", 10)

        # --- COLONNE DE DROITE : PORTS DISPONIBLES (Diagnostic) ---
        # Note : On retire -minwidth ici pour corriger l'erreur
        right_side = ttk.LabelFrame(main_frame, text=" 🔍 Diagnostic : Ports Systèmes ", padding=10)
        right_side.pack(side='right', fill='y') 

        # Liste des ports (on définit la largeur ici avec 'width' en caractères)
        self.available_ports_listbox = tk.Listbox(right_side, font=("Consolas", 10), 
                                                bg="#2c3e50", fg="#ecf0f1", width=40)
        self.available_ports_listbox.pack(fill='both', expand=True)

        btn_refresh = ttk.Button(right_side, text="Actualiser la liste", command=self._refresh_available_ports)
        btn_refresh.pack(fill='x', pady=(10, 0))

        # Lancer la détection initiale
        self._refresh_available_ports()

    def _refresh_available_ports(self):
        """ Détecte et liste les ports série réellement branchés sur la machine. """
        import serial.tools.list_ports
        self.available_ports_listbox.delete(0, tk.END)
        
        ports = serial.tools.list_ports.comports()
        
        if not ports:
            self.available_ports_listbox.insert(tk.END, "Aucun port détecté")
            return

        for p in sorted(ports):
            # Format: COM8 - USB Serial Port (Manufacturer)
            display_text = f" {p.device}: {p.description}"
            self.available_ports_listbox.insert(tk.END, display_text)


    def _create_ports_section(self, master: ttk.Frame, title: str, section_key: str, start_row: int):
        """ Crée un groupe de champs d'entrée pour les ports. """
        
        ttk.Label(master, text=f"🔹 {title} :", font=("Helvetica", 14, "bold"), foreground='#3498db').grid(row=start_row, column=0, sticky='w', pady=(10, 5), columnspan=2)
        
        ports_map = PORTS_CONFIG_MAP.get(section_key, {})
        current_ports = self.working_ports_config.get(section_key, {})
        
        row_counter = start_row + 1
        
        for port_key, details in ports_map.items():
            label = details["label"]
            current_value = current_ports.get(port_key, "")
            
            ttk.Label(master, text=f"{label}:").grid(row=row_counter, column=0, sticky='w', padx=5, pady=2)
            
            var = tk.StringVar(value=str(current_value))
            if section_key not in self.temp_ports_config:
                self.temp_ports_config[section_key] = {}
            self.temp_ports_config[section_key][port_key] = var
            
            entry = ttk.Entry(master, textvariable=var, width=20, font=("Helvetica", 12))
            entry.grid(row=row_counter, column=1, sticky='ew', padx=5, pady=2)
            
            if hasattr(self, '_show_keyboard'): # Protection si VirtualKeyboard est actif
                entry.bind("<Button-1>", lambda e, entry=entry: self._show_keyboard(entry))
            
            row_counter += 1


    # --------------------------------------------------------------------------
    # --- NOUVEAU: CRÉATION DE L'ONGLET RACCOURCIS (shortcut_word.json) ---
    # --------------------------------------------------------------------------
    
    def _create_shortcut_tab_content(self, tab: ttk.Frame):
        """ Crée le contenu de l'onglet de gestion des raccourcis. """
        
        frame = ttk.Frame(tab, padding=25)
        frame.pack(fill='both', expand=True)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        
        ttk.Label(frame, text="📝 Gérer les Raccourcis de Mots (sauvegardé dans shortcut_word.json)", 
                  font=("Helvetica", 16, "bold"), anchor="w", foreground='#16a085').grid(row=0, column=0, sticky='w', pady=(0, 10), columnspan=2)
        ttk.Separator(frame, orient='horizontal').grid(row=1, column=0, sticky='ew', padx=5, pady=(0, 15), columnspan=2)

        # --- Section de la liste des raccourcis ---
        list_frame = ttk.Frame(frame)
        list_frame.grid(row=2, column=0, columnspan=2, sticky='nsew', pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        scrollbar.grid(row=0, column=1, sticky='ns')

        # Listbox
        self.shortcut_listbox = tk.Listbox(list_frame, 
                                            listvariable=self.shortcut_list_var, 
                                            yscrollcommand=scrollbar.set,
                                            selectmode=tk.SINGLE,
                                            height=10, 
                                            font=("Helvetica", 16),
                                            bg=KDS_CONFIG["CARD_BG"], 
                                            fg=KDS_CONFIG["COLOR_TEXT"],
                                            selectbackground=KDS_CONFIG["COLOR_ACCENT"],
                                            selectforeground='white',
                                            borderwidth=0, 
                                            highlightthickness=0)
        self.shortcut_listbox.grid(row=0, column=0, sticky='nsew')
        scrollbar.config(command=self.shortcut_listbox.yview)
        
        self._refresh_shortcut_listbox()

        # --- Section Ajout/Suppression ---
        control_frame = ttk.Frame(frame, padding=10)
        control_frame.grid(row=3, column=0, columnspan=2, sticky='ew', pady=(10, 0))
        control_frame.columnconfigure(1, weight=1)
        
        # Champ d'entrée pour le nouveau raccourci
        self.new_shortcut_var = tk.StringVar()
        ttk.Label(control_frame, text="Nouveau Raccourci:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.new_shortcut_entry = ttk.Entry(control_frame, textvariable=self.new_shortcut_var, font=("Helvetica", 14))
        self.new_shortcut_entry.grid(row=0, column=1, sticky='ew', padx=5, pady=5, ipady=5)

        # 🚀 CLAVIER VIRTUEL pour le champ de nouveau raccourci
        if VirtualKeyboard:
            self.new_shortcut_entry.bind("<Button-1>", lambda e: self._show_keyboard(self.new_shortcut_entry, self._add_shortcut_to_list))
            self.new_shortcut_entry.bind("<FocusIn>", lambda e: self.focus_set())
            
        # Boutons d'action
        add_btn = ttk.Button(control_frame, text="➕ Ajouter", 
                             command=self._add_shortcut_to_list, style="AddRemove.TButton")
        add_btn.grid(row=1, column=0, sticky='ew', padx=5, pady=5, ipady=5)

        remove_btn = ttk.Button(control_frame, text="➖ Retirer la Sélection", 
                                command=self._remove_shortcut_from_list, style="Reset.TButton")
        remove_btn.grid(row=1, column=1, sticky='ew', padx=5, pady=5, ipady=5)
        
        ttk.Label(frame, text="NB: La liste ci-dessus ne sera mise à jour dans le fichier qu'après avoir cliqué sur 'Sauvegarder et Appliquer' en bas de la fenêtre.", 
                  style="AdminDesc.TLabel", wraplength=750, foreground='#f1c40f').grid(row=4, column=0, sticky='w', pady=(10, 0), columnspan=2)

    def _refresh_shortcut_listbox(self):
        """ Met à jour le Listbox à partir de self.working_shortcuts. """
        self.shortcut_listbox.delete(0, tk.END)
        for item in self.working_shortcuts:
            self.shortcut_listbox.insert(tk.END, item)

    def _add_shortcut_to_list(self):
        """ Ajoute le texte du champ d'entrée à la liste des raccourcis. """
        new_shortcut = self.new_shortcut_var.get().strip().upper()
        
        if new_shortcut and new_shortcut not in self.working_shortcuts:
            self.working_shortcuts.append(new_shortcut)
            self._refresh_shortcut_listbox()
            self.new_shortcut_var.set("") # Nettoyer le champ
        elif new_shortcut in self.working_shortcuts:
            messagebox.showwarning("Doublon", f"Le raccourci '{new_shortcut}' existe déjà.")
        else:
            messagebox.showwarning("Erreur de Saisie", "Veuillez entrer un mot ou une phrase valide.")

    def _remove_shortcut_from_list(self):
        """ Retire le raccourci sélectionné de la liste. """
        selected_indices = self.shortcut_listbox.curselection()
        
        if not selected_indices:
            messagebox.showwarning("Sélection", "Veuillez sélectionner un raccourci à retirer.")
            return

        # Les indices de Listbox sont basés sur la vue, il faut retirer de la fin
        # pour que les indices ne changent pas lors de la suppression.
        for index in sorted(selected_indices, reverse=True):
            shortcut_to_remove = self.shortcut_listbox.get(index)
            if shortcut_to_remove in self.working_shortcuts:
                self.working_shortcuts.remove(shortcut_to_remove)
        
        self._refresh_shortcut_listbox()

    # --------------------------------------------------------------------------
    # --- CLAVIER VIRTUEL ---
    # --------------------------------------------------------------------------

    def _show_keyboard(self, target_entry: ttk.Entry, ok_callback=None):
        """ 
        Ouvre le clavier virtuel pour le champ d'entrée spécifié.
        Utilise un callback par défaut si non spécifié (ici, on ne fait rien de spécial,
        le clavier se ferme juste après OK).
        """
        # Fermer toute instance de clavier existante pour éviter les doublons
        for child in self.winfo_children():
            if isinstance(child, tk.Toplevel) and child.winfo_toplevel().title() == "Clavier Virtuel":
                 child.destroy()
        
        # Le callback 'OK' du clavier est généralement une fonction de recherche/action,
        # mais ici, nous l'utilisons pour valider la saisie et fermer le clavier.
        def default_ok_action():
            target_entry.focus_set() # Redonne le focus à l'Entry après fermeture
        
        # Le clavier prend le focus pendant son utilisation
        VirtualKeyboard(self.master, target_entry, ok_callback if ok_callback else default_ok_action)


    # --------------------------------------------------------------------------
    # --- MÉTHODES DE SAUVEGARDE GLOBALE ---
    # --------------------------------------------------------------------------

    def _save_all_configs(self):
        """ Tente de sauvegarder les trois fichiers de configuration. """
        
        # 1. Sauvegarde config_gui.json
        success_gui, gui_config = self._process_and_validate_gui_config()
        if not success_gui:
            return

        # 2. Sauvegarde ports.json
        success_ports, ports_config = self._process_and_validate_ports_config()
        if not success_ports:
            return
            
        # 3. Sauvegarde shortcut_word.json (pas de validation complexe requise)
        success_shortcut = self._write_shortcuts_config()
        if not success_shortcut:
            return
            
        # 4. Écriture finale des deux premiers fichiers (shortcut_word est déjà écrit)
        gui_saved = self._write_gui_config(gui_config)
        ports_saved = self._write_ports_config(ports_config)

        if gui_saved and ports_saved and success_shortcut:
             messagebox.showinfo("Succès", "Configurations config_gui.json, ports.json ET shortcut_word.json sauvegardées ! Veuillez redémarrer l'application pour appliquer les changements.")
             self.destroy()
        else:
             pass

    
    def _process_and_validate_gui_config(self):
        """ Collecte et valide la configuration de config_gui.json. """
        final_config = self.working_config.copy() 
        errors = []

        for key, details in CONFIG_MAP.items():
            if key in self.temp_config and isinstance(self.temp_config[key], tk.StringVar):
                var = self.temp_config[key]
                value_str = var.get().strip()
                widget_type = details["type"]

                # Validation
                if widget_type == 'int':
                    try:
                        value = int(value_str)
                        if value < 0:
                             errors.append(f"'{key}' doit être un entier positif ou zéro.")
                        final_config[key] = value
                    except ValueError:
                        errors.append(f"'{key}' ('{value_str}') doit être un nombre entier valide.")
                        
                elif widget_type == 'float':
                    try:
                        value = float(value_str)
                        if value < 0:
                             errors.append(f"'{key}' doit être un nombre positif ou zéro.")
                        final_config[key] = value
                    except ValueError:
                        errors.append(f"'{key}' ('{value_str}') doit être un nombre décimal valide.")
                        
                elif widget_type == 'list':
                    # Conserve la casse pour les types de service, mais enlève les espaces.
                    final_config[key] = [item.strip() for item in value_str.split(',') if item.strip()]

                elif widget_type == 'string':
                    final_config[key] = value_str
        
        if errors:
            messagebox.showerror("Erreur de Validation (config_gui.json)", "Veuillez corriger les erreurs suivantes :\n\n" + "\n".join(errors))
            return False, None
        
        return True, final_config


    def _write_gui_config(self, final_config: Dict[str, Any]) -> bool:
        """ Écrit la configuration de config_gui.json. """
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(final_config, f, indent=4)
            
            # Mise à jour de la configuration globale
            KDS_CONFIG.clear()
            KDS_CONFIG.update(final_config)
            return True
        except Exception as e:
            messagebox.showerror("Erreur de Sauvegarde (config_gui.json)", f"Impossible d'écrire dans '{CONFIG_FILE}'. Détail: {e}")
            return False


    def _process_and_validate_ports_config(self):
        """ Collecte et valide la configuration de ports.json. """
        final_ports_config = self.working_ports_config.copy()
        errors = []

        for section_key, ports_map in PORTS_CONFIG_MAP.items():
            section_vars = self.temp_ports_config.get(section_key, {})
            
            if section_key not in final_ports_config:
                final_ports_config[section_key] = {}
                
            for port_key, details in ports_map.items():
                if port_key in section_vars and isinstance(section_vars[port_key], tk.StringVar):
                    var = section_vars[port_key]
                    value_str = var.get().strip()
                    
                    if not value_str:
                         errors.append(f"Le port '{port_key}' dans '{section_key}' ne peut pas être vide.")
                    
                    final_ports_config[section_key][port_key] = value_str
        
        if errors:
            messagebox.showerror("Erreur de Validation (ports.json)", "Veuillez corriger les erreurs suivantes :\n\n" + "\n".join(errors))
            return False, None

        return True, final_ports_config


    def _write_ports_config(self, final_ports_config: Dict[str, Any]) -> bool:
        """ Écrit la configuration de ports.json. """
        try:
            with open(PORTS_CONFIG_FILE, 'w') as f:
                json.dump(final_ports_config, f, indent=4)
            return True
        except Exception as e:
            messagebox.showerror("Erreur de Sauvegarde (ports.json)", f"Impossible d'écrire dans '{PORTS_CONFIG_FILE}'. Détail: {e}")
            return False
            
    def _write_shortcuts_config(self) -> bool:
        """ Écrit la liste des raccourcis dans shortcut_word.json. """
        try:
            final_data = {"shortcuts": self.working_shortcuts}
            with open(SHORTCUT_FILE, 'w') as f:
                json.dump(final_data, f, indent=4)
            return True
        except Exception as e:
            messagebox.showerror("Erreur de Sauvegarde (shortcut_word.json)", f"Impossible d'écrire dans '{SHORTCUT_FILE}'. Détail: {e}")
            return False


    # --------------------------------------------------------------------------
    # --- MÉTHODES D'ADMINISTRATION (BACKUP, RESTORE, RESET) ---
    # --------------------------------------------------------------------------

    def _create_admin_tab_content(self, tab: ttk.Frame):
        """ Crée le contenu de l'onglet Sauvegarde, Restauration et Réinitialisation. """
        
        frame = ttk.Frame(tab, padding=25)
        frame.pack(fill='both', expand=True)
        frame.columnconfigure(0, weight=1) 
        
        # Ligne 0 : Note d'information
        ttk.Label(frame, text="Note : Ces fonctions affectent uniquement le fichier 'config_gui.json'. Le fichier 'ports.json' et 'shortcut_word.json' doivent être gérés manuellement (ou via leurs onglets).", 
                  style="AdminDesc.TLabel", wraplength=750, foreground='#e74c3c').grid(row=0, column=0, sticky='w', padx=5, pady=(0, 20), columnspan=2)
        
        # Section Sauvegarde (Backup)
        self._create_admin_section(frame, "1. Sauvegarde du Fichier Actuel (Backup)", 1) 
        # Ligne 3 : Description Sauvegarde
        ttk.Label(frame, text="Crée une copie horodatée du fichier de configuration actuel (config_gui.json).", style="AdminDesc.TLabel").grid(row=3, column=0, sticky='w', padx=5, pady=(0, 10), columnspan=2)
        # Ligne 4 : Bouton Sauvegarde
        ttk.Button(frame, text="💾 Créer une Sauvegarde", command=self._backup_config, 
                   style="Backup.TButton").grid(row=4, column=0, sticky='ew', padx=5, pady=(0, 30), ipady=10, columnspan=2)

        # Section Restauration (Restore)
        self._create_admin_section(frame, "2. Restauration (Restore)", 5) 
        # Ligne 7 : Description Restauration
        ttk.Label(frame, text="Charge une configuration précédente à partir d'un fichier .json sélectionné et remplace config_gui.json. REQUIERT REDÉMARRAGE.", style="AdminDesc.TLabel").grid(row=7, column=0, sticky='w', padx=5, pady=(0, 10), columnspan=2)
        # Ligne 8 : Bouton Restauration
        ttk.Button(frame, text="📥 Restaurer depuis un fichier JSON...", command=self._restore_config, 
                   style="Restore.TButton").grid(row=8, column=0, sticky='ew', padx=5, pady=(0, 30), ipady=10, columnspan=2)

        # Section Réinitialisation (Reset)
        self._create_admin_section(frame, "3. Réinitialisation aux Valeurs d'Usine (Reset)", 9) 
        # Ligne 11 : Description Réinitialisation
        ttk.Label(frame, text="Rétablit la configuration aux valeurs initiales par défaut. ATTENTION: Toutes les modifications non sauvegardées seront perdues.", style="AdminDesc.TLabel").grid(row=11, column=0, sticky='w', padx=5, pady=(0, 10), columnspan=2)
        # Ligne 12 : Bouton Réinitialisation
        ttk.Button(frame, text="🗑️ Réinitialiser la Configuration", command=self._reset_config, 
                   style="Reset.TButton").grid(row=12, column=0, sticky='ew', padx=5, pady=(0, 30), ipady=10, columnspan=2)


    def _create_admin_section(self, master: ttk.Frame, title: str, start_row: int):
        """ Crée le titre de section pour l'onglet Admin. """
        header = ttk.Label(master, text=title, font=("Helvetica", 16, "bold"), anchor="w", foreground='#3498db')
        header.grid(row=start_row, column=0, sticky='w', padx=5, pady=(20, 5), columnspan=2)
        ttk.Separator(master, orient='horizontal').grid(row=start_row+1, column=0, sticky='ew', padx=5, columnspan=2)


    def _backup_config(self):
        """ Crée une copie de config_gui.json avec un timestamp. """
        if not os.path.exists(CONFIG_FILE):
            messagebox.showerror("Erreur", f"Le fichier de configuration '{CONFIG_FILE}' est introuvable.")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        backup_filename = f"config_gui_backup_{timestamp}.json"
        
        try:
            target_dir = os.path.dirname(os.path.abspath(CONFIG_FILE)) or '.'
            destination_path = os.path.join(target_dir, backup_filename)
            
            shutil.copy2(CONFIG_FILE, destination_path) 
            messagebox.showinfo("Sauvegarde Réussie", 
                                f"Configuration sauvegardée dans :\n{destination_path}")
            
        except Exception as e:
            messagebox.showerror("Erreur de Sauvegarde", 
                                 f"Échec de la sauvegarde du fichier:\n{e}")

    
    def _restore_config(self):
        """ Restaure la configuration depuis un fichier JSON sélectionné. """
        
        file_path = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("Fichiers JSON de Configuration", "*.json")],
            title="Sélectionner le Fichier de Configuration à Restaurer"
        )
        
        if not file_path:
            return

        confirm = messagebox.askyesno(
            "Confirmer la Restauration",
            f"Êtes-vous sûr de vouloir remplacer la configuration actuelle par le contenu de :\n\n{os.path.basename(file_path)}\n\nCeci n'est PAS annulable."
        )
        
        if not confirm:
            return

        try:
            with open(file_path, 'r') as f:
                restored_config = json.load(f)
            
            if not isinstance(restored_config, dict) or "STATUS_COLORS" not in restored_config or "CARD_WIDTH" not in restored_config:
                messagebox.showerror("Erreur de Fichier", "Le fichier sélectionné ne semble pas être un fichier de configuration KDS valide.")
                return

            with open(CONFIG_FILE, 'w') as f:
                json.dump(restored_config, f, indent=4)
            
            KDS_CONFIG.clear()
            KDS_CONFIG.update(restored_config)
            
            messagebox.showinfo("Restauration Réussie", 
                                "Configuration restaurée ! Veuillez redémarrer l'application KDS pour appliquer complètement les changements.")
            self.destroy()

        except json.JSONDecodeError:
            messagebox.showerror("Erreur de Fichier", "Le fichier sélectionné n'est pas un fichier JSON valide.")
        except Exception as e:
            messagebox.showerror("Erreur de Restauration", f"Échec de la restauration:\n{e}")

    
    def _reset_config(self):
        """ Réinitialise la configuration au DEFAULT_KDS_CONFIG. """
        
        confirm = messagebox.askyesno(
            "Confirmer la Réinitialisation",
            "Êtes-vous sûr de vouloir réinitialiser la configuration aux valeurs PAR DÉFAUT ?\n\nTOUTES les modifications non sauvegardées seront perdues."
        )
        
        if not confirm:
            return

        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(DEFAULT_KDS_CONFIG, f, indent=4)
            
            KDS_CONFIG.clear()
            KDS_CONFIG.update(DEFAULT_KDS_CONFIG)
            
            messagebox.showinfo("Réinitialisation Réussie", 
                                "Configuration réinitialisée aux valeurs par défaut. Veuillez redémarrer l'application KDS.")
            self.destroy()

        except Exception as e:
            messagebox.showerror("Erreur de Réinitialisation", f"Échec de la réinitialisation:\n{e}")

