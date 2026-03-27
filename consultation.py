import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import logging
from collections import Counter
import numpy as np
import random 
import json # Ajouté pour le décodage d'items structurés
import re # Ajouté pour le nettoyage de chaînes

# --- NOUVEL IMPORT ---
from keyboard import VirtualKeyboard 
# ---------------------

# --- GRAPHIQUES ---
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# ------------------

# Assurez-vous que db_manager.py est dans le même répertoire
from db_manager import DBManager 
from db_maindish import MainDishDBManager

try:
    from tkcalendar import DateEntry
except ImportError:
    # Si non installé, on affichera une erreur ou on utilisera l'ancien système
    DateEntry = None

logger = logging.getLogger(__name__)

# Valeur simulée pour le montant de la facture (puisque non présent dans db_manager fourni)
def simulate_bill_amount(item_count):
    """Simule un montant de facture basé sur le nombre d'items."""
    base = item_count * 15 # 15$ par item en moyenne
    variance = random.uniform(-10, 10)
    return round(max(5, base + variance), 2) # Minimum 5$

# ====================================================================================
# CLASSE UNIQUE ET AVANCÉE : ConsultationWindow (Tableau de Bord Visuel)
# ====================================================================================

class ConsultationWindow(tk.Toplevel):
    """
    Tableau de Bord d'Analyse des Ventes sophistiqué avec visualisation graphique.
    """
    def __init__(self, master, db_manager: DBManager):
        super().__init__(master)
        self.db_manager = db_manager
        self.main_dish_db = MainDishDBManager()

        
        
        self.geometry("1500x950")
        self.title("✨ Tableau de Bord d'Analyse des Ventes PREMIUM")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        
        self.all_orders_cache = [] 
        self.keyboard_window = None # Gère l'instance du clavier flottant

        self.setup_styles()
        self.create_widgets()
        self.load_data_and_analyze()
        self.attributes('-topmost', True)
        
        # --- AJOUTER CETTE LIGNE ---
        # Solution pour Linux : s'assurer que l'attribut est appliqué après le rendu initial
        self.after(10, self.lift) # Tente de 'soulever' la fenêtre après 10ms

        self.transient(master) 
        self.grab_set()
        
        # Gérer la fermeture de la fenêtre pour détruire le clavier aussi
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # --- 3. Configuration des styles (Adapté pour Tactile) ---
        style = ttk.Style()
        
        # TRÈS IMPORTANT : 'clam' permet de forcer l'affichage des couleurs sur les onglets
        style.theme_use('clam') 
        
        # ✅ STYLE DES ONGLETS (En-têtes)
        style.configure("Treeview.Heading", 
                        font=('Arial', 12, 'bold'), 
                        background="#2c3e50",    # Couleur de fond des onglets (Bleu Nuit)
                        foreground="white",       # Couleur du texte
                        relief="flat",
                        padding=10)               # Espace autour du texte
        
        # ✅ EFFET AU CLIC SUR LES ONGLETS (Feedback visuel)
        style.map("Treeview.Heading",
                  background=[('active', '#34495e')], # Couleur quand on appuie
                  foreground=[('active', '#f1c40f')]) # Texte devient jaune au clic
        
        # ✅ STYLE DU CORPS DU TABLEAU
        style.configure("Treeview", 
                        font=('Arial', 11), 
                        rowheight=40,            # Augmenté à 40 pour un confort tactile optimal
                        fieldbackground="white",
                        borderwidth=0)
        
        # Couleur de la ligne sélectionnée
        style.map("Treeview", 
                  background=[('selected', '#3498db')],
                  foreground=[('selected', 'white')])

        # ✅ STYLE DÉDIÉ POUR LE GRAND BOUTON FERMER TACTILE
        style.configure("CloseTactile.TButton", 
                        font=("Arial", 16, "bold"),
                        background="#c0392b", 
                        foreground="white",
                        padding=[30, 20])
        style.map('CloseTactile.TButton', 
                  background=[('active', '#e74c3c')]) 
        
        # ✅ SCROLLBAR PLUS GROSSE POUR LE TACTILE
        style.layout('Touch.Vertical.TScrollbar', 
                     [('Vertical.Scrollbar.trough', 
                       {'children': [('Vertical.Scrollbar.thumb', {'expand': '1', 'sticky': 'nswe'})], 
                        'sticky': 'ns'})])
        
        style.configure('Touch.Vertical.TScrollbar',
                        gripcount=0,
                        troughcolor='#bdc3c7', 
                        background='#34495e',
                        bordercolor='#2c3e50',
                        arrowsize=35,
                        width=35,
                        troughrelief='flat')
        
        # master.wait_window(self)
        
    # --- GESTION DU CLAVIER VIRTUEL ---


    def get_real_bill_total(self, order_items_raw):
        """Calcule le total réel d'une commande en interrogeant la DB des prix."""
        total = 0.0
        # On récupère tous les prix une seule fois pour être plus rapide
        prices_dict = {name.upper(): price for name, price in self.main_dish_db.get_all_dishes()}
        
        for raw_item in order_items_raw:
            # On utilise votre méthode existante pour extraire le nom propre du plat
            item_name, _ = self._extract_main_item_and_quantity(raw_item)
            
            if item_name:
                # Cherche le prix dans le dictionnaire (0.0 si non trouvé)
                price = prices_dict.get(item_name.upper().strip(), 0.0)
                total += price
                
        return round(total, 2)

    def on_close(self):
        """Ferme la fenêtre du clavier avant de détruire la fenêtre principale de consultation."""
        if self.keyboard_window and self.keyboard_window.winfo_exists():
            self.keyboard_window.destroy()
        self.destroy()
        
    def show_keyboard(self, entry_widget, callback_function):
        """
        Affiche le clavier virtuel UNIQUEMENT au focus (clic).
        Détruit l'ancien clavier s'il cible un champ différent.
        """
        # Si un clavier existe
        if self.keyboard_window and self.keyboard_window.winfo_exists():
            # Si on clique sur le même champ, on le relève (pas de destruction/recréation)
            if self.keyboard_window.target_entry == entry_widget:
                self.keyboard_window.lift()
                return
            else:
                # Si on clique sur un autre champ, on détruit l'ancien
                self.keyboard_window.destroy()
                self.keyboard_window = None 

        # Crée un nouveau clavier UNIQUEMENT si aucun clavier n'est actif ou si on clique sur un nouveau champ après fermeture
        self.keyboard_window = VirtualKeyboard(self, entry_widget, callback_function)
    
    # -----------------------------------

    def setup_styles(self):
        """Configure les styles Tkinter pour un look moderne, coloré et TACTILE."""
        s = ttk.Style()
        s.theme_use('clam') 
        
        # --- Agrandissement TACTILE (Partie inchangée, mais ici pour contexte) ---
        # ... (Styles pour les TFrame, TLabel, TNotebook.Tab) ...
        # Styles de Boutons (Plus grands et rembourrage accru)
        s.configure('TButton', font=('Helvetica', 14, 'bold'), padding=15, background='#3498db', foreground='white') 
        s.map('TButton', background=[('active', '#2980b9')])
        
        # Styles d'Onglets (Très grands pour le toucher)
        s.configure('TNotebook.Tab', padding=[20, 15], font=('Helvetica', 16, 'bold'), foreground='#2c3e50') 
        
        # ✅ CORRECTION DU STYLE DE BOUTON FERMER : Renommé en Close.TButton
        s.configure("Close.TButton", 
                    font=('Helvetica', 20, 'bold'), 
                    background='#c0392b', # Rouge d'urgence
                    foreground='white',
                    padding=[30, 25]) # Très grand rembourrage
        
        # Assurer que le bouton a un état actif
        s.map('Close.TButton', background=[('active', '#e74c3c')]) 

        # ✅ CONFIGURATION DES SCROLLBARS TACTILES (Barres de défilement très larges)
        s.layout("Vertical.TScrollbar",
             [('Vertical.Scrollbar.trough',
               {'children': [('Vertical.Scrollbar.thumb',
                              {'expand': '1', 'sticky': 'nswe'})],
                'sticky': 'ns'})])
        s.configure("Vertical.TScrollbar", arrowsize=30, troughcolor="#ecf0f1", background="#95a5a6", width=30)
        s.configure("Horizontal.TScrollbar", arrowsize=30, troughcolor="#ecf0f1", background="#95a5a6", width=30)
    def create_widgets(self):
        # Assurez-vous d'importer ces éléments si ce n'est pas déjà fait en haut du fichier
        from datetime import datetime, timedelta 
        
        # --- 1. Cadre de Contrôle Global (Filtre de Période) ---
        control_frame = ttk.Frame(self, style='Control.TFrame', padding="15 15")
        control_frame.grid(row=0, column=0, sticky='ew')
        
        # Variables de filtre de période (Dernier mois par défaut)
        last_month = datetime.now() - timedelta(days=30)
        self.start_date_var = tk.StringVar(value=last_month.strftime('%Y-%m-%d 00:00:00'))
        self.end_date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d 23:59:59'))

       # --- Champ Période Début avec Calendrier ---
        ttk.Label(control_frame, text="Période Début:", background='#ffffff').pack(side=tk.LEFT, padx=(0, 10))
        
        # On remplace ttk.Entry par DateEntry
        self.start_date_entry = DateEntry(control_frame, 
                                          width=28, 
                                          font=('Helvetica', 14),
                                          background='darkblue', 
                                          foreground='white', 
                                          borderwidth=2,
                                          date_pattern='y-mm-dd') # Format SQL standard
        self.start_date_entry.pack(side=tk.LEFT, padx=(0, 25))
        
        # --- Champ Période Fin avec Calendrier ---
        ttk.Label(control_frame, text="Période Fin:", background='#ffffff').pack(side=tk.LEFT, padx=(0, 10))
        
        self.end_date_entry = DateEntry(control_frame, 
                                        width=28, 
                                        font=('Helvetica', 14),
                                        background='darkblue', 
                                        foreground='white', 
                                        borderwidth=2,
                                        date_pattern='y-mm-dd')
        self.end_date_entry.pack(side=tk.LEFT, padx=(0, 30))

        # Bouton Appliquer Filtres (plus grand)
        ttk.Button(control_frame, text="Appliquer 🚀", command=self.load_data_and_analyze, style='TButton').pack(side=tk.LEFT, padx=(20, 15))
        
        # ✅ Bouton FERMER (Très grand style 'Close.TButton')
        # ✅ Bouton FERMER déplacé à gauche (tk.LEFT) et espacement réduit pour être adjacent
        ttk.Button(control_frame, 
                   text="(X)", 
                   command=self.on_close, 
                   style='Close.TButton').pack(side=tk.LEFT, padx=(5, 0)) 
        
        # --- 2. Cadre Principal avec Onglets (Notebook) ---
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=1, column=0, sticky='nsew', padx=10, pady=(0, 10))
        
        # --- Création des Onglets ---
        self.tab_dashboard = ttk.Frame(self.notebook, style='Main.TFrame')
        self.tab_item_analysis = ttk.Frame(self.notebook, style='Main.TFrame')
        self.tab_history = ttk.Frame(self.notebook, style='Main.TFrame')
        self.tab_server_perf = ttk.Frame(self.notebook, style='Main.TFrame')

        self.notebook.add(self.tab_dashboard, text="1. 📈 Tableau de Bord Global")
        self.notebook.add(self.tab_item_analysis, text="2. 🍽️ Décompte des Items")
        self.notebook.add(self.tab_server_perf, text="3. 👤 Performance Serveuse")
        self.notebook.add(self.tab_history, text="4. 📜 Historique Détaillé")
        
        # Initialisation du contenu de chaque onglet
        self.create_dashboard_tab(self.tab_dashboard)
        self.create_item_analysis_tab(self.tab_item_analysis)
        self.create_server_perf_tab(self.tab_server_perf)
        self.create_history_tab(self.tab_history)

        # Mettre à jour l'analyse quand on change d'onglet
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)        
        
        # Analyse d'Items (Onglet 2) -> display_item_analysis
        # NOTE: Les liaisons suivantes nécessitent que les widgets aient été créés dans leur onglet respectif
        if hasattr(self, 'item_count_search_entry'):
            self.item_count_search_entry.bind("<Button-1>", lambda e: self.show_keyboard(self.item_count_search_entry, self.display_item_analysis))

        # Historique (Onglet 4) -> display_order_history
        callback_history = self.display_order_history
        if hasattr(self, 'bill_id_entry'):
            self.bill_id_entry.bind("<Button-1>", lambda e: self.show_keyboard(self.bill_id_entry, callback_history))
        if hasattr(self, 'serveuse_entry'):
            self.serveuse_entry.bind("<Button-1>", lambda e: self.show_keyboard(self.serveuse_entry, callback_history))
        if hasattr(self, 'table_entry'):
            self.table_entry.bind("<Button-1>", lambda e: self.show_keyboard(self.table_entry, callback_history))
        if hasattr(self, 'item_search_entry'):
            self.item_search_entry.bind("<Button-1>", lambda e: self.show_keyboard(self.item_search_entry, callback_history))
        
        # -----------------------------------------------------------------

    # ==================================================================
    # 2. Création des Onglets Détaillés
    # ==================================================================
    
    def create_dashboard_tab(self, tab):
        """Crée l'onglet de l'analyse globale avec les graphiques."""
        tab.columnconfigure(0, weight=1, minsize=450)
        tab.columnconfigure(1, weight=1, minsize=450)
        tab.columnconfigure(2, weight=1, minsize=450)
        tab.rowconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        # Cadres pour les 6 graphiques/métriques
        self.charts_frames = []
        for i in range(6):
            r, c = divmod(i, 3)
            frame = ttk.Frame(tab, style='Analysis.TFrame', relief='ridge', borderwidth=1)
            frame.grid(row=r, column=c, sticky='nsew', padx=5, pady=5)
            self.charts_frames.append(frame)
        
        # Zone pour les Métriques Clés (Temps de Service Moyen & Montant Moyen)
        self.metric_frame = ttk.Frame(tab, style='Analysis.TFrame', relief='ridge', borderwidth=1)
        self.metric_frame.grid(row=2, column=0, columnspan=3, sticky='ew', padx=5, pady=5)
        self.metric_frame.columnconfigure(0, weight=1)
        self.metric_frame.columnconfigure(1, weight=1)

        self.service_time_label = ttk.Label(self.metric_frame, style='Metric.TLabel', text="⏱️ Temps de Service Moyen: En attente...", background='#ecf0f1', anchor='center')
        self.service_time_label.grid(row=0, column=0, sticky='ew', padx=10, pady=10)
        
        self.avg_bill_label = ttk.Label(self.metric_frame, style='Metric.TLabel', text="💰 Montant Moyen de la Facture: En attente...", background='#ecf0f1', anchor='center')
        self.avg_bill_label.grid(row=0, column=1, sticky='ew', padx=10, pady=10)
        

    def create_item_analysis_tab(self, tab):
        """Crée l'onglet de l'analyse des items (décompte agrégé et triable)."""
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        
        # Cadre de contrôle pour le filtre local des items
        item_control_frame = ttk.Frame(tab, padding="5 5", style='Control.TFrame')
        item_control_frame.grid(row=0, column=0, sticky='ew')
        
        self.item_count_search_var = tk.StringVar()
        
        ttk.Label(item_control_frame, text="Filtrer Item (dans la période):", background='#ffffff').pack(side=tk.LEFT, padx=(0, 5))
        
        # ✅ Modification de la largeur à 30 et ajout de la police agrandie
        self.item_count_search_entry = ttk.Entry(item_control_frame, 
                                                 textvariable=self.item_count_search_var, 
                                                 width=30, # Réduit de 50 à 30
                                                 font=('Helvetica', 14)) # Augmenté pour le tactile
        self.item_count_search_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(item_control_frame, text="Rechercher Item", command=self.display_item_analysis).pack(side=tk.LEFT, padx=5)

        # Treeview pour l'analyse des items
        tree_frame = ttk.Frame(tab, style='Main.TFrame')
        tree_frame.grid(row=1, column=0, sticky='nsew', pady=(5, 0))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        columns = ('item_name', 'count')
        self.item_count_tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        # Les en-têtes et colonnes du Treeview restent compacts
        self.item_count_tree.heading('item_name', text='Plat Principal', anchor='w', command=lambda: self.sort_treeview(self.item_count_tree, 'item_name'))
        self.item_count_tree.heading('count', text='Décompte Total', anchor='center', command=lambda: self.sort_treeview(self.item_count_tree, 'count'))
        
        self.item_count_tree.column('item_name', width=40, anchor='w') 
        self.item_count_tree.column('count', width=80, anchor='center', stretch=tk.NO) 

        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.item_count_tree.yview)
        self.item_count_tree.configure(yscrollcommand=v_scrollbar.set)
        
        self.item_count_tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        
        
    def create_server_perf_tab(self, tab):
        """Crée l'onglet du rapport de performance par serveuse."""
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        
        ttk.Label(tab, text="Performance des Serveuses (dans la période sélectionnée) :", style='Title.TLabel', background='#e8f0fe').grid(row=0, column=0, sticky='w', pady=(0, 5))

        # Treeview pour la performance
        tree_frame = ttk.Frame(tab, style='Main.TFrame')
        tree_frame.grid(row=1, column=0, sticky='nsew', pady=(5, 0))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        columns = ('serveuse_name', 'order_count', 'item_count', 'avg_items', 'total_amount', 'avg_bill')
        self.server_perf_tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        self.server_perf_tree.heading('serveuse_name', text='Serveuse', command=lambda: self.sort_treeview(self.server_perf_tree, 'serveuse_name'))
        self.server_perf_tree.heading('order_count', text='Commandes Traitées', command=lambda: self.sort_treeview(self.server_perf_tree, 'order_count'))
        self.server_perf_tree.heading('item_count', text='Items Totaux', command=lambda: self.sort_treeview(self.server_perf_tree, 'item_count'))
        self.server_perf_tree.heading('avg_items', text='Moy. Items/Cde', command=lambda: self.sort_treeview(self.server_perf_tree, 'avg_items'))
        self.server_perf_tree.heading('total_amount', text='Revenus Totaux ($)', command=lambda: self.sort_treeview(self.server_perf_tree, 'total_amount'))
        self.server_perf_tree.heading('avg_bill', text='Facture Moyenne ($)', command=lambda: self.sort_treeview(self.server_perf_tree, 'avg_bill'))

        self.server_perf_tree.column('serveuse_name', width=150, anchor='w') 
        self.server_perf_tree.column('total_amount', width=150, anchor='center') 
        self.server_perf_tree.column('avg_bill', width=150, anchor='center') 

        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.server_perf_tree.yview)
        self.server_perf_tree.configure(yscrollcommand=v_scrollbar.set)
        self.server_perf_tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        
    def create_history_tab(self, tab):
        """Crée l'onglet de l'historique détaillé des commandes."""
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        
        # --- Cadre de Recherche/Filtre Spécifique à l'Historique ---
        hist_filter_frame = ttk.Frame(tab, padding="5 5", style='Control.TFrame')
        hist_filter_frame.grid(row=0, column=0, sticky='ew')
        
        self.bill_id_var = tk.StringVar()
        self.serveuse_var = tk.StringVar()
        self.table_var = tk.StringVar()
        self.item_search_var = tk.StringVar() 
        
        ttk.Label(hist_filter_frame, text="Filtre local: Bill ID / Serveuse / Table / Item", background='#ffffff').pack(side=tk.LEFT, padx=(0, 20))
        
        self.bill_id_entry = ttk.Entry(hist_filter_frame, textvariable=self.bill_id_var, width=10)
        self.bill_id_entry.pack(side=tk.LEFT)
        
        self.serveuse_entry = ttk.Entry(hist_filter_frame, textvariable=self.serveuse_var, width=12)
        self.serveuse_entry.pack(side=tk.LEFT, padx=5)
        
        self.table_entry = ttk.Entry(hist_filter_frame, textvariable=self.table_var, width=5)
        self.table_entry.pack(side=tk.LEFT)
        
        self.item_search_entry = ttk.Entry(hist_filter_frame, textvariable=self.item_search_var, width=20)
        self.item_search_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(hist_filter_frame, text="Appliquer Filtre", command=self.display_order_history).pack(side=tk.LEFT, padx=(10, 5))

        # --- Treeview pour l'Historique des Commandes ---
        tree_frame = ttk.Frame(tab, style='Main.TFrame')
        tree_frame.grid(row=1, column=0, sticky='nsew', pady=(5, 0))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        columns = ('bill_id', 'table_number', 'serveuse_name', 'status', 'total_items', 'creation_date', 'archived_date', 'items_preview')
        self.history_tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        # En-têtes cliquables pour le tri
        for col in columns:
            self.history_tree.heading(col, text=col.replace('_', ' ').title(), command=lambda c=col: self.sort_treeview(self.history_tree, c))

        self.history_tree.column('bill_id', width=80, anchor='center', stretch=tk.NO)
        self.history_tree.column('table_number', width=60, anchor='center', stretch=tk.NO)
        self.history_tree.column('items_preview', width=400, anchor='w')

        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=v_scrollbar.set)
        
        self.history_tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        
        self.history_tree.bind('<Double-1>', self.on_order_double_click)


    # ==================================================================
    # 3. Logique de Chargement et d'Analyse des Données
    # ==================================================================

    def load_data_and_analyze(self):
        """Charge les données réelles, calcule le montant total via la DB et lance les analyses."""
        try:
            start_date = self.start_date_var.get().strip()
            end_date = self.end_date_var.get().strip()
            
            raw_orders = self.db_manager.search_archived_orders_in_consultation(
                start_date=start_date,
                end_date=end_date,
            )
            
            # 1. Préparation des prix réels depuis la base de données Main Dish
            # On crée un dictionnaire { 'NOM DU PLAT': prix_float } pour une recherche rapide
            try:
                all_dishes = self.main_dish_db.get_all_dishes()
                prices_dict = {name.upper().strip(): price for name, price in all_dishes}
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des prix: {e}")
                prices_dict = {}

            # 2. Calcul du Montant Réel de la Facture
            self.all_orders_cache = []
            for order in raw_orders:
                total_bill = 0.0
                # On récupère la liste des items de la commande (généralement dans order['items'])
                items_list = order.get('items', [])
                
                for raw_item in items_list:
                    # On utilise votre méthode interne pour nettoyer le nom (ex: "2x BURGER" -> "BURGER")
                    clean_name, _ = self._extract_main_item_and_quantity(raw_item)
                    
                    if clean_name:
                        # On récupère le prix réel. Si le plat n'existe pas, on met 0.0
                        price = prices_dict.get(clean_name.upper().strip(), 0.0)
                        total_bill += price
                
                # On remplace la simulation par le total calculé
                order['total_bill_amount'] = round(total_bill, 2)
                self.all_orders_cache.append(order)
            
            # --- Fin du calcul réel ---
            
            if not self.all_orders_cache:
                messagebox.showinfo("Données", "Aucune commande trouvée pour la période sélectionnée.")
                # Nettoyage de toutes les vues
                for tree in [self.history_tree, self.item_count_tree, self.server_perf_tree]:
                    self._clear_treeview(tree)
                self.service_time_label.config(text="⏱️ Temps de Service Moyen: 0h 0m 0s")
                self.avg_bill_label.config(text="💰 Montant Moyen de la Facture: 0.00 $")
                for frame in self.charts_frames:
                    for widget in frame.winfo_children(): widget.destroy()
                    ttk.Label(frame, text="Aucune donnée à afficher.", background='#ffffff').pack(expand=True, fill='both')
                return

            # Mise à jour de toutes les vues avec les vrais chiffres
            self.display_order_history()
            self.display_item_analysis()
            self.display_server_performance()
            self.display_dashboard_analysis()
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données: {e}")
            messagebox.showerror("Erreur", f"Impossible de charger les données: {e}")

    # --- MÉTHODE D'AGRÉGATION ET D'EXTRACTION DU PLAT PRINCIPAL ---
    def _extract_main_item_and_quantity(self, raw_item_data: str) -> tuple[str, int]:
        """
        Tente de décoder la donnée brute pour extraire le plat principal ('main_item') 
        et sa quantité agrégée. Ignore les sous-items ('sub_items').
        """
        main_item_full_name = None
        
        # 1. Tenter de décoder si c'est une chaîne JSON structurée
        try:
            if isinstance(raw_item_data, str):
                item_dict = json.loads(raw_item_data)
                if isinstance(item_dict, dict) and 'main_item' in item_dict:
                    main_item_full_name = item_dict["main_item"]
        except (json.JSONDecodeError, TypeError):
             # 2. Si non structuré ou échec du décodage, traiter comme un item simple (le plat principal)
             if isinstance(raw_item_data, str):
                 main_item_full_name = raw_item_data
             
        if not main_item_full_name:
            return None, 0

        # Fonction de nettoyage et d'extraction de quantité (réutilisée/simplifiée)
        if not isinstance(main_item_full_name, str):
             main_item_full_name = str(main_item_full_name)

        cleaned_name = main_item_full_name.strip()
        quantity = 1
        item_key = cleaned_name

        parts = cleaned_name.split(" ", 2)
        
        if len(parts) >= 2 and parts[0].isdigit():
            if parts[1].lower() == "x":
                try:
                    quantity = int(parts[0])
                    item_key = parts[2].strip() if len(parts) == 3 else ""
                except ValueError:
                    item_key = cleaned_name
                    quantity = 1
            else:
                 try:
                    quantity = int(parts[0])
                    item_key = cleaned_name[len(parts[0]):].strip()
                 except ValueError:
                    item_key = cleaned_name
                    quantity = 1
                    
        item_key = item_key.split(" (")[0].strip()
        
        # Le nom de l'item ne doit pas être vide après le nettoyage
        if not item_key:
            return None, 0

        # Filtre contre la pollution de données
        if item_key.lower() in ('item', 'items', 'order', 'n/a'):
            return None, 0
            
        return item_key, quantity

    # --- DÉCOMPTE DES ITEMS (TAB 2) ---
    def display_item_analysis(self):
        """
        Calcule et affiche uniquement le décompte total des Plats Principaux 
        pour la période (avec filtre local).
        """
        self._clear_treeview(self.item_count_tree)
        
        item_counter = Counter()
        
        for order in self.all_orders_cache:
            if 'items' in order and isinstance(order['items'], list):
                for raw_item_data in order['items']:
                    # Utiliser la nouvelle méthode pour extraire UNIQUEMENT le plat principal
                    item_key, quantity = self._extract_main_item_and_quantity(raw_item_data)
                    
                    if item_key:
                        # Agrégation par la quantité extraite
                        item_counter[item_key] += quantity # Compte le nombre *vendu* agrégé
        
        sorted_items = sorted(item_counter.items(), key=lambda item: item[1], reverse=True)
        
        filter_text = self.item_count_search_var.get().strip().lower()
        
        for item_name, count in sorted_items:
            if filter_text and filter_text not in item_name.lower():
                continue
            # Affichage du nom du Main Item et de son total agrégé
            self.item_count_tree.insert('', tk.END, values=(item_name, count))

    # --- PERFORMANCE SERVEUSE (TAB 3) ---
    def display_server_performance(self):
        """Calcule et affiche le rapport de performance par serveuse, incluant les montants."""
        self._clear_treeview(self.server_perf_tree)
        
        server_data = {}
        for order in self.all_orders_cache:
            serveuse = order.get('serveuse_name', 'INCONNU')
            item_count = order.get('total_items', 0)
            bill_amount = order.get('total_bill_amount', 0.0) # Utilisation du montant simulé
            
            if serveuse not in server_data:
                server_data[serveuse] = {'orders': 0, 'items': 0, 'amount': 0.0}
            
            server_data[serveuse]['orders'] += 1
            server_data[serveuse]['items'] += item_count
            server_data[serveuse]['amount'] += bill_amount
            
        perf_list = []
        for serveuse, data in server_data.items():
            avg_items = round(data['items'] / data['orders'], 1) if data['orders'] > 0 else 0
            avg_bill = round(data['amount'] / data['orders'], 2) if data['orders'] > 0 else 0.0
            
            perf_list.append((
                serveuse, 
                data['orders'], 
                data['items'], 
                avg_items, 
                round(data['amount'], 2), # Total de Revenus
                avg_bill # Montant Moyen de Facture
            ))
        
        perf_list.sort(key=lambda x: x[4], reverse=True) # Tri initial par Revenus Totaux

        for serveuse, order_count, item_count, avg_items, total_amount, avg_bill in perf_list:
            self.server_perf_tree.insert('', tk.END, values=(
                serveuse, order_count, item_count, avg_items, 
                f"{total_amount:.2f} $", f"{avg_bill:.2f} $"
            ))


    # --- TABLEAU DE BORD GLOBAL (TAB 4) ---
    def display_dashboard_analysis(self):
        """Calcule et met à jour les graphiques et les métriques clés."""
        
        # Initialisation des calculs
        total_revenue = sum(order.get('total_bill_amount', 0) for order in self.all_orders_cache)
        total_orders = len(self.all_orders_cache)
        
        # --- MÉTRIQUES CLÉS ---
        
        # 1. Montant Moyen de la Facture
        avg_bill = total_revenue / total_orders if total_orders > 0 else 0.0
        self.avg_bill_label.config(text=f"💰 Montant Moyen de la Facture: {avg_bill:.2f} $")
        
        # 2. Temps de Service Moyen (Fonctionnalité initiale)
        total_time_seconds = 0
        valid_orders = 0
        for order in self.all_orders_cache:
            try:
                creation = datetime.strptime(order['creation_date'], '%Y-%m-%d %H:%M:%S')
                archived = datetime.strptime(order['archived_date'], '%Y-%m-%d %H:%M:%S')
                if order['status'] == 'Traitée' and archived > creation:
                    total_time_seconds += (archived - creation).total_seconds()
                    valid_orders += 1
            except (KeyError, ValueError, TypeError):
                continue
        
        avg_seconds = total_time_seconds / valid_orders if valid_orders > 0 else 0
        avg_time = str(timedelta(seconds=int(avg_seconds)))
        self.service_time_label.config(text=f"⏱️ Temps de Service Moyen: {avg_time} (sur {valid_orders} commandes)")
        
        
        # --- GRAPHIQUES ET ANALYSES NOUVELLES ---
        
        # 3. Distribution des Types de Service (Tarte)
        service_counts = Counter(order.get('service_type', 'Autre') for order in self.all_orders_cache)
        self.create_chart(self.charts_frames[0], service_counts, "Distribution des Types de Service", 'pie', "Répartition par Service")
        
        # 4. Tendance des Ventes Horaires (Barres)
        hourly_counts = Counter()
        for order in self.all_orders_cache:
             try:
                creation_hour = datetime.strptime(order['creation_date'], '%Y-%m-%d %H:%M:%S').hour
                hourly_counts[creation_hour] += 1
             except (KeyError, ValueError, TypeError):
                 continue
        hourly_data = sorted(hourly_counts.items())
        self.create_chart(self.charts_frames[1], hourly_data, "Tendance des Commandes par Heure", 'bar', "Pics d'Activité")
        
        # 5. Répartition des Revenus par Serveuse (Barres Empilées)
        server_revenue_data = {}
        for order in self.all_orders_cache:
            serveuse = order.get('serveuse_name', 'INCONNU')
            amount = order.get('total_bill_amount', 0)
            status = order.get('status', 'Annulée') # Pour simuler l'empilement
            
            if serveuse not in server_revenue_data:
                server_revenue_data[serveuse] = {'Traitée': 0, 'Annulée': 0}
            
            # Pour l'empilement, on ajoute seulement le montant total aux commandes traitées
            if status == 'Traitée':
                 server_revenue_data[serveuse]['Traitée'] += amount
            else:
                 server_revenue_data[serveuse]['Annulée'] += amount # Montants 'perdus' par annulation (simulé)

        # On prend le Top 5 des serveuses par revenu total
        top_servers = sorted(server_revenue_data.items(), key=lambda item: item[1]['Traitée'], reverse=True)[:5]

        data_stacked = {
            'Serveuses': [s[0] for s in top_servers],
            'Traitée': [s[1]['Traitée'] for s in top_servers],
            'Annulée': [s[1]['Annulée'] for s in top_servers],
        }

        self.create_chart(self.charts_frames[2], data_stacked, "Revenus (Top 5 Serveuses)", 'stacked_bar', "Revenus par Serveuse ($)")
        
        # 6. Relation Temps/Nombre d'Items (Nuage de Points)
        scatter_data = []
        for order in self.all_orders_cache:
            try:
                creation = datetime.strptime(order['creation_date'], '%Y-%m-%d %H:%M:%S')
                archived = datetime.strptime(order['archived_date'], '%Y-%m-%d %H:%M:%S')
                duration = (archived - creation).total_seconds() / 60 # Durée en minutes
                item_count = order.get('total_items', 0)
                if item_count > 0 and duration > 0:
                    scatter_data.append((item_count, duration))
            except Exception:
                continue

        self.create_chart(self.charts_frames[3], scatter_data, "Relation Temps Traitement/Items", 'scatter', "Items vs. Temps (Min)")
        
        # 7. Distribution des Montants de Facture (Histogramme)
        bill_amounts = [order.get('total_bill_amount', 0) for order in self.all_orders_cache]
        self.create_chart(self.charts_frames[4], bill_amounts, "Distribution des Montants de Facture", 'hist', "Fréquence des Montants ($)")
        
        # 8. Service le plus lent vs. le plus rapide (Barres)
        service_durations = {} # service_type: [durations en secondes]
        for order in self.all_orders_cache:
            try:
                creation = datetime.strptime(order['creation_date'], '%Y-%m-%d %H:%M:%S')
                archived = datetime.strptime(order['archived_date'], '%Y-%m-%d %H:%M:%S')
                duration = (archived - creation).total_seconds()
                service_type = order.get('service_type', 'Autre')
                
                if service_type not in service_durations:
                    service_durations[service_type] = []
                
                service_durations[service_type].append(duration)
            except Exception:
                continue
                
        avg_service_times = {
            s: round(np.mean(times) / 60, 1) # Moyenne en minutes
            for s, times in service_durations.items() if times
        }
        
        avg_service_times_data = sorted(avg_service_times.items(), key=lambda item: item[1], reverse=True)
        self.create_chart(self.charts_frames[5], avg_service_times_data, "Temps Moyen par Type de Service", 'bar', "Durée Moyenne (Min)")


    # ==================================================================
    # 4. Fonctions Utilitaires (Graphiques et Tri)
    # ==================================================================
    
    def create_chart(self, frame, data, title, chart_type, y_label):
        """Crée et affiche un graphique Matplotlib dans un cadre Tkinter."""
        for widget in frame.winfo_children():
            widget.destroy()

        if not data:
            ttk.Label(frame, text=f"Aucune donnée pour {title}.", background='#ffffff').pack(expand=True, fill='both')
            return

        fig, ax = plt.subplots(figsize=(4, 3))
        
        plt.style.use('ggplot')
        
        if chart_type == 'pie':
            labels = data.keys()
            sizes = data.values()
            def autopct_format(pct):
                return ('%.1f%%' % pct) if pct > 5 else ''
            ax.pie(sizes, labels=labels, autopct=autopct_format, startangle=90)
            ax.axis('equal') 
            
        elif chart_type == 'bar':
            categories = [item[0] for item in data]
            counts = [item[1] for item in data]
            if title == "Tendance des Commandes par Heure":
                categories = [f"{h}h" for h in categories]
            
            y_pos = np.arange(len(categories))
            ax.bar(y_pos, counts, align='center', color='#2ecc71')
            ax.set_xticks(y_pos)
            ax.set_xticklabels(categories, rotation=45, ha='right')
            ax.set_ylabel(y_label)
            
        elif chart_type == 'stacked_bar':
            serveuses = data['Serveuses']
            traitees = data['Traitée']
            annulees = data['Annulée']
            
            ind = np.arange(len(serveuses))
            width = 0.5
            
            ax.bar(ind, traitees, width, label='Revenu Traité ($)', color='#3498db')
            ax.bar(ind, annulees, width, bottom=traitees, label='Revenu Annulé ($)', color='#e74c3c')
            
            ax.set_xticks(ind)
            ax.set_xticklabels(serveuses, rotation=45, ha='right')
            ax.legend(loc='upper right')
            ax.set_ylabel(y_label)
            
        elif chart_type == 'scatter':
            x_data = [d[0] for d in data]
            y_data = [d[1] for d in data]
            
            # Regression linéaire simple pour montrer une tendance
            if len(x_data) > 1:
                m, b = np.polyfit(x_data, y_data, 1)
                ax.plot(x_data, m*np.array(x_data) + b, color='#e67e22', linestyle='--')
            
            ax.scatter(x_data, y_data, color='#3498db', alpha=0.6)
            ax.set_xlabel("Nombre d'Items")
            ax.set_ylabel("Temps Traitement (Min)")
            
        elif chart_type == 'hist':
            ax.hist(data, bins=10, color='#9b59b6', edgecolor='black')
            ax.set_xlabel("Montant Facture ($)")
            ax.set_ylabel("Fréquence")
            
        elif chart_type == 'bar_avg':
            categories = [item[0] for item in data]
            counts = [item[1] for item in data]
            
            y_pos = np.arange(len(categories))
            ax.bar(y_pos, counts, align='center', color='#8e44ad')
            ax.set_xticks(y_pos)
            ax.set_xticklabels(categories, rotation=45, ha='right')
            ax.set_ylabel(y_label)
            
        ax.set_title(title, fontsize=10)
        ax.tick_params(axis='both', which='major', labelsize=8)

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(fill=tk.BOTH, expand=True)
        canvas.draw()
        plt.close(fig)

    # --- Tri et Utilitaires ---

    def sort_treeview(self, tree, col):
        """Fonction générique pour trier les données dans n'importe quel Treeview."""
        data = [(tree.set(item, col), item) for item in tree.get_children('')]
        
        def get_key(item):
            value = item[0].replace('$', '').strip() # Retirer le symbole $ pour le tri
            try:
                # Tente de convertir en float pour un tri numérique
                return float(value)
            except ValueError:
                return value.lower() # Tri alphabétique par défaut

        reverse = not getattr(tree, '_sort_reverse', True) 
        data.sort(key=get_key, reverse=reverse)
        
        for index, (val, item_id) in enumerate(data):
            tree.move(item_id, '', index)
            
        setattr(tree, '_sort_reverse', reverse)
        setattr(tree, '_sort_column', col)

        up_arrow = '▲' if not reverse else '▼'
        for c in tree['columns']:
            text = tree.heading(c, option="text").split()[0]
            tree.heading(c, text=text)
        tree.heading(col, text=f"{tree.heading(col, option='text').split()[0]} {up_arrow}")
        
    def _clear_treeview(self, tree):
        """Vide un Treeview donné."""
        for i in tree.get_children():
            tree.delete(i)
            
    def on_tab_change(self, event):
        """Met à jour l'onglet actif si nécessaire lors du changement."""
        pass
        
    def display_order_history(self):
        self._clear_treeview(self.history_tree)
        
        bill_id = self.bill_id_var.get().strip() or None
        serveuse_name = self.serveuse_var.get().strip().lower() or None
        table_number = self.table_var.get().strip() or None
        item_filter = self.item_search_var.get().strip().lower() or None

        try:
            table_number = int(table_number) if table_number else None
        except ValueError:
             messagebox.showerror("Erreur de Saisie", "Le numéro de table doit être un nombre entier.")
             return
             
        filtered_orders = []
        for order in self.all_orders_cache:
            if bill_id and str(order.get('bill_id', '')).strip() != bill_id:
                continue
            if serveuse_name and serveuse_name not in order.get('serveuse_name', '').lower():
                continue
            if table_number is not None and order.get('table_number') != table_number:
                continue
            if item_filter and not any(item_filter in item.lower() for item in order.get('items', [])):
                continue
                
            filtered_orders.append(order)
            
        if not filtered_orders:
            self.history_tree.insert('', tk.END, values=("", "", "", "Aucune commande trouvée", "", "", "", ""), tags=('empty',))
            return

        for order in filtered_orders:
            items_preview = ", ".join(order['items'][:3])
            if len(order['items']) > 3:
                items_preview += f", ... (+{len(order['items']) - 3} items)"
            
            values = (
                order['bill_id'], order.get('table_number', 'N/A'), order.get('serveuse_name', 'Inconnu'), 
                order['status'], order['total_items'], order['creation_date'], 
                order['archived_date'], items_preview
            )
            self.history_tree.insert('', tk.END, values=values, tags=('treated' if order['status'] == 'Traitée' else 'cancelled',))
            
        self.history_tree.tag_configure('treated', foreground='#27ae60') 
        self.history_tree.tag_configure('cancelled', foreground='#e74c3c', font=('TkDefaultFont', 10, 'bold'))

    def on_order_double_click(self, event):
        """Affiche les détails complets d'une commande au double-clic."""
        item_id = self.history_tree.focus()
        if not item_id:
            return

        selected_bill_id = self.history_tree.item(item_id, 'values')[0]
        order = next((o for o in self.all_orders_cache if str(o.get('bill_id')) == str(selected_bill_id)), None)
        
        if order:
            items_text = "\n".join(f"• {item}" for item in order['items'])
            
            detail_message = (
                f"Facture ID: {order['bill_id']}\n"
                f"Table: {order.get('table_number', 'N/A')} / Service: {order.get('service_type', 'N/A')}\n"
                f"Serveuse: {order.get('serveuse_name', 'Inconnu')}\n"
                f"Montant Total: {order.get('total_bill_amount', 0.00):.2f} $\n"
                f"Statut: {order['status']} ({order['total_items']} items)\n"
                f"\n--- Détails de la Commande ---\n"
                f"{items_text}"
            )
            
            messagebox.showinfo(f"Détails Commande {order['bill_id']}", detail_message)