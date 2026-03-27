import tkinter as tk
from tkinter import messagebox, ttk
# Importation pour la conversion de chaînes de date en objets pour un tri correct
from datetime import datetime 

# NOTE IMPORTANTE: Assurez-vous que 'db_manager' et l'instance de 'KDSGUI' 
# existent et sont correctement définis ou importés dans votre application principale.
from db_manager import DBManager 
# Nous utilisons le type Hinting 'KDSGUI' pour la lisibilité
# mais l'importation de la classe réelle KDSGUI doit être gérée dans votre fichier principal.

class KDSConfirmDialog(tk.Toplevel):
    """Confirmation personnalisée sans barre de titre et toujours au premier plan."""
    def __init__(self, parent, title, message, callback):
        super().__init__(parent)
        self.callback = callback
        self.overrideredirect(True)
        self.attributes('-topmost', True) # Premier plan
        self.config(bg='#2c3e50', highlightbackground="#3498db", highlightthickness=4)
        
        # Centrage
        w, h = 450, 220
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        tk.Label(self, text=title, font=("Arial", 16, "bold"), bg='#2c3e50', fg='#3498db').pack(pady=15)
        tk.Label(self, text=message, font=("Arial", 13), bg='#2c3e50', fg='white', justify="center").pack(pady=10)

        btn_frame = tk.Frame(self, bg='#2c3e50')
        btn_frame.pack(side='bottom', fill='x', pady=20)

        tk.Button(btn_frame, text="ANNULER", font=("Arial", 12, "bold"), bg='#e74c3c', fg='white', 
                  width=12, height=2, command=self.destroy).pack(side='left', padx=30)

        tk.Button(btn_frame, text="CONFIRMER", font=("Arial", 12, "bold"), bg='#27ae60', fg='white', 
                  width=12, height=2, command=self.execute).pack(side='right', padx=30)

        self.grab_set()
        self.focus_force()

    def execute(self):
        self.callback()
        self.destroy()
        
class KDSAlertDialog(tk.Toplevel):
    def __init__(self, parent, title, message):
        super().__init__(parent)
        
        self.overrideredirect(True)
        self.attributes('-topmost', True) # ⭐ Force le premier plan
        self.config(bg='#2c3e50', highlightbackground="#e67e22", highlightthickness=4)
        
        # Centrage
        w, h = 400, 180
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        tk.Label(self, text=f"⚠️ {title}", font=("Arial", 14, "bold"), 
                 bg='#2c3e50', fg='#e67e22').pack(pady=15)
        
        tk.Label(self, text=message, font=("Arial", 12), 
                 bg='#2c3e50', fg='white').pack(pady=10)

        tk.Button(self, text="OK", font=("Arial", 12, "bold"), bg='#34495e', fg='white', 
                  width=15, height=2, command=self.destroy).pack(side='bottom', pady=15)

        self.grab_set() 
        self.focus_force() # ⭐ Force le focus


class TrashWindow(tk.Toplevel):
    """
    Fenêtre pour visualiser et réactiver les commandes qui sont 'Traitée' ou 'Annulée'.
    Design adapté au tactile et à la souris, avec tri clicable par colonne.
    """

    def __init__(self, master, db_manager: 'DBManager', kds_gui_instance: 'KDSGUI'):
        import tkinter as tk
        from tkinter import ttk
        
        super().__init__(master)
        self.db_manager = db_manager
        self.kds_gui = kds_gui_instance 
        
        # --- 1. Configuration de base ---
        self.sort_column = 'date_hidden' 
        self.sort_reverse = True
        self.current_filter = "COMMANDE"  # Filtre actif par défaut
        self.title("🗑️ Commandes Terminées (Corbeille)")
        
        # Taille augmentée pour accommoder les gros boutons tactiles
        self.geometry("900x700") 
        self.config(bg="#ecf0f1")
        self.wm_attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self._safe_destroy)
        
        # --- 2. Configuration des styles TTK ---
        style = ttk.Style()
        style.theme_use('clam') 
        
        style.configure("Treeview.Heading", 
                        font=('Arial', 12, 'bold'), 
                        background="#2c3e50", foreground="white", 
                        relief="flat", padding=10)
        
        style.map("Treeview.Heading",
                  background=[('active', '#34495e')],
                  foreground=[('active', '#f1c40f')])
        
        style.configure("Treeview", 
                        font=('Arial', 12), 
                        rowheight=45, 
                        fieldbackground="white", borderwidth=0)
        
        style.map("Treeview", 
                  background=[('selected', '#3498db')],
                  foreground=[('selected', 'white')])

        style.configure("CloseTactile.TButton", 
                        font=("Arial", 14, "bold"),
                        background="#c0392b", foreground="white",
                        padding=15)
        
        style.layout('Touch.Vertical.TScrollbar', 
                     [('Vertical.Scrollbar.trough', 
                        {'children': [('Vertical.Scrollbar.thumb', {'expand': '1', 'sticky': 'nswe'})], 
                        'sticky': 'ns'})])
        style.configure('Touch.Vertical.TScrollbar', width=40, arrowsize=40)

        # --- 3. ZONE DU HAUT (Titre & Fermer) ---
        top_frame = tk.Frame(self, bg="#ecf0f1")
        top_frame.pack(side=tk.TOP, fill="x", padx=10, pady=10)

        tk.Label(top_frame, text="🗑️ CORBEILLE", 
                 font=("Arial", 18, "bold"), bg="#ecf0f1", fg="#2c3e50").pack(side=tk.LEFT)
        
        ttk.Button(top_frame, text="FERMER (X)", 
                   command=self._safe_destroy, 
                   style='CloseTactile.TButton').pack(side=tk.RIGHT)

        # --- 4. NOUVEAU : BARRE DE FILTRES (Tactile) ---
        filter_frame = tk.Frame(self, bg="#ecf0f1")
        filter_frame.pack(side=tk.TOP, fill="x", padx=10, pady=5)

        # Définition des filtres : (Texte du bouton, Valeur du filtre)
        filter_options = [
            ("TOUT", "TOUT"),
            ("COMMANDE (SALLE)", "COMMANDE"),
            ("P.A.", "PA"),
            ("LIVRAISON", "LIV"),
            ("LIVREURS (999)", "LIVREUR")
        ]

        self.filter_buttons = {}
        for text, val in filter_options:
            btn = tk.Button(
                filter_frame, text=text,
                command=lambda v=val: self.set_filter(v),
                bg="#bdc3c7", fg="black", 
                font=("Arial", 11, "bold"),
                relief="raised", bd=3,
                padx=15, pady=8
            )
            btn.pack(side=tk.LEFT, padx=5)
            self.filter_buttons[val] = btn

        # Activer visuellement le bouton "TOUT" au démarrage
        self.filter_buttons["COMMANDE"].config(bg="#3498db", fg="white")

        # --- 5. ZONE DU BAS (Boutons d'action) ---
        button_frame = tk.Frame(self, bg="#ecf0f1", height=100)
        button_frame.pack(side=tk.BOTTOM, fill="x", padx=10, pady=15)
        button_frame.pack_propagate(False)

        self.btn_reactivate = tk.Button(
            button_frame, text="↩️ RÉACTIVER", 
            command=self.reactivate_selected_order,
            bg="#2ecc71", fg="white", font=("Arial", 12, "bold"),
            relief="raised", bd=4, activebackground="#27ae60"
        )
        self.btn_reactivate.pack(side=tk.LEFT, fill="both", expand=True, padx=5)

        self.btn_clear = tk.Button(
            button_frame, text="🗑️ TOUT SUPPRIMER", 
            command=self.clear_all_archived,
            bg="#e74c3c", fg="white", font=("Arial", 12, "bold"),
            relief="raised", bd=4, activebackground="#c0392b"
        )
        self.btn_clear.pack(side=tk.RIGHT, fill="both", expand=True, padx=5)

        # --- 6. ZONE DU MILIEU (Treeview) ---
        tree_container = tk.Frame(self, bg="#ecf0f1")
        tree_container.pack(side=tk.TOP, fill="both", expand=True, padx=10)
        
        tree_scroll = ttk.Scrollbar(tree_container, style='Touch.Vertical.TScrollbar')
        tree_scroll.pack(side="right", fill="y")

        self.tree = ttk.Treeview(
            tree_container, 
            yscrollcommand=tree_scroll.set, 
            selectmode="browse",
            columns=("bill_id_hidden", "table_number", "serveuse_name", "preview", "completion_time", "status_hidden", "date_hidden"), 
            show="headings"
        )
        self.tree.pack(fill="both", expand=True) 
        tree_scroll.config(command=self.tree.yview)

        columns_config = {
            "bill_id_hidden": ("ID", 0), 
            "table_number": ("Table", 100),       # Un peu plus petit
            "serveuse_name": ("Serveur(se)", 150), # Un peu plus petit
            "preview": ("Contenu (Aperçu)", 350), # ⭐ LARGEUR GÉNÉREUSE
            "completion_time": ("Heure", 100),    # Un peu plus petit
            "status_hidden": ("Statut", 0),
            "date_hidden": ("Date", 0)
        }
        
        for col, (text, width) in columns_config.items():
            is_clickable = not col.endswith('_hidden')
            self.tree.heading(col, text=text, anchor=tk.W,
                             command=lambda c=col: self.sort_treeview(c) if is_clickable else None)
            
            if is_clickable:
                self.tree.column(col, width=width, stretch=(tk.YES if col=="serveuse_name" else tk.NO))
            else:
                self.tree.column(col, width=0, stretch=tk.NO)
                
        # --- 7. Chargement des données ---
        self.all_archived_orders = {} 
        self.load_all_archived_orders()
        self.display_orders()
        self.update_sort_indicator()

    def set_filter(self, filter_value):
        """Change le filtre actif et rafraîchit l'affichage."""
        self.current_filter = filter_value
        
        # Mise à jour visuelle des boutons
        for val, btn in self.filter_buttons.items():
            if val == filter_value:
                btn.config(bg="#3498db", fg="white")
            else:
                btn.config(bg="#bdc3c7", fg="black")
                
        self.display_orders()

    def _check_filter(self, table_val):
        """Vérifie si la valeur de la table correspond au filtre sélectionné."""
        table_str = str(table_val).upper().strip()
        f = self.current_filter

        if f == "TOUT":
            return table_str != "888"
        
        if f == "COMMANDE":
            # On garde si c'est un chiffre (sauf 999)
            return table_str.isdigit() and table_str != "999" and table_str != "888"
        
        if f == "LIVREUR":
            # On garde si c'est 'LIVREUR' ou '999'
            return "LIVREUR" in table_str or table_str == "999"
        if f == "LIV":
            # On garde si c'est 'LIVREUR' 
            return "LIV" in table_str 
        
        # Pour PA et LIVRAISON (recherche partielle)
        return f in table_str
        # --- Logique de Tri ---
    
    def _safe_destroy(self):
        """
        Détruit la fenêtre Corbeille et réinitialise la référence 
        dans l'instance KDSGUI parente pour permettre une réouverture propre.
        """
        # 1. Détruire la fenêtre Toplevel
        self.destroy()
        
        # 2. Réinitialiser la référence dans l'instance KDSGUI
        if hasattr(self.kds_gui, 'trash_window'): 
            self.kds_gui.trash_window = None
            
    def sort_treeview(self, col):
        """Gère le tri croissant/décroissant lors du clic sur l'en-tête."""
        
        # Si la colonne 'Heure de Fin' est cliquée, on trie par la date complète cachée
        col_to_sort = col
        if col == 'completion_time':
            col_to_sort = 'date_hidden'
            
        if col_to_sort == self.sort_column:
            # Inverse l'ordre si on clique sur la même colonne
            self.sort_reverse = not self.sort_reverse
        else:
            # Nouvelle colonne: commence par l'ordre croissant (False)
            self.sort_column = col_to_sort
            self.sort_reverse = False
            
        self.update_sort_indicator()
        self.display_orders()
        
    def update_sort_indicator(self):
        """Met à jour l'indicateur (flèche) sur l'en-tête de la colonne triée."""
        visible_cols = ["table_number", "serveuse_name", "completion_time"]
        
        # 1. Nettoyer les flèches des colonnes
        for c in self.tree['columns']:
            if c in visible_cols:
                # Conserve uniquement le texte (enlève les flèches existantes)
                current_text = self.tree.heading(c)['text'].split(' ')[0]
                self.tree.heading(c, text=current_text)

        # 2. Déterminer la colonne visible pour l'indicateur
        col_to_show_indicator = self.sort_column
        if self.sort_column == 'date_hidden':
            col_to_show_indicator = 'completion_time'
            
        # 3. Ajouter la flèche (⬇️ pour décroissant, ⬆️ pour croissant)
        indicator = " ⬇️" if self.sort_reverse else " ⬆️"
        current_text = self.tree.heading(col_to_show_indicator)['text']
        self.tree.heading(col_to_show_indicator, text=current_text + indicator)

    def load_all_archived_orders(self):
        """Charge toutes les commandes archivées."""
        # Ceci est un appel simulé à votre base de données
        self.all_archived_orders = self.db_manager.get_archived_orders()

    def display_orders(self, event=None):
        """Affiche les commandes archivées en utilisant le filtre ET le tri actuel."""
        
        # 1. Nettoyer le tableau actuel
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 2. Appliquer le FILTRAGE avant le tri
        filtered_orders = []
        for bill_id, data in self.all_archived_orders.items():
            if self._check_filter(data.get('table_number', '')):
                filtered_orders.append((bill_id, data))
        
        # 3. Logique de TRI (sur la liste filtrée)
        def sort_key(item):
            col_name = self.sort_column
            
            if col_name == 'table_number':
                val = str(item[1]['table_number'])
                try:
                    # Tri numérique pour les tables (ex: 1, 2, 10)
                    return int(val)
                except ValueError:
                    # Tri alphabétique si contient des lettres (ex: "PA-1")
                    return val 
            
            elif col_name == 'serveuse_name':
                return str(item[1]['serveuse_name']).lower()

            # ⭐ AJOUT : Tri pour la nouvelle colonne d'aperçu
            elif col_name == 'preview':
                return str(item[1].get('short_preview', '')).lower()
            
            elif col_name == 'date_hidden':
                date_str = item[1].get('completion_date', '1970-01-01 00:00:00')
                try:
                    return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    return datetime.min

            else: 
                # Tri par Bill ID (pour les autres cas)
                try:
                    return int(item[0])
                except:
                    return str(item[0])

        # Application du tri
        filtered_orders.sort(key=sort_key, reverse=self.sort_reverse)
        
        # 4. AFFICHAGE final dans le Treeview
        for bill_id, data in filtered_orders:
            completion_date_str = data.get('completion_date', 'N/A')
            # Extraire l'heure pour l'affichage visible
            completion_time_display = completion_date_str.split(' ')[1] if ' ' in completion_date_str else 'N/A'
            
            self.tree.insert(
                "", 
                tk.END, 
                iid=bill_id,
                values=(
                    bill_id,                             # Col 0 (Caché: ID)
                    data['table_number'],                # Col 1 (Table)
                    data['serveuse_name'],               # Col 2 (Serveur)
                    data.get('short_preview', ''),       # ⭐ Col 3 (APERÇU DES 2 PLATS)
                    completion_time_display,             # Col 4 (Heure)
                    data.get('status', 'N/A'),           # Col 5 (Caché: Statut)
                    completion_date_str                  # Col 6 (Caché: Date complète)
                ),
                tags=('treated' if data.get('status') == 'Traitée' else 'cancelled')
            )
        
        # Couleurs des lignes
        self.tree.tag_configure('treated', background='#d4e6f1', foreground='#2c3e50')
        self.tree.tag_configure('cancelled', background='#f7dc6f', foreground='#c0392b')

    def reactivate_selected_order(self):
        """Réactive la commande sélectionnée sans rafraîchir tout l'écran KDS."""
        selected_item_id = self.tree.focus()
        
        if not selected_item_id:
            KDSAlertDialog(
                self, 
                "Sélection requise", 
                "Veuillez sélectionner une facture\ndans la liste pour la réactiver."
            )
            return

        bill_id = selected_item_id 
        
        # 1. Mise à jour dans la base de données
        self.db_manager.set_order_status_by_bill_id(bill_id, 'En attente')
        
        # 2. Rafraîchissement de la fenêtre Corbeille (on enlève la ligne de la liste)
        self.load_all_archived_orders()
        self.display_orders()           
        
        

        # Confirmation visuelle
        if hasattr(self.kds_gui, 'update_status'):
            self.kds_gui.update_status(f"Facture {bill_id} réactivée.", "green")
        

    def clear_all_archived(self):
        """Supprime définitivement toutes les commandes terminées après confirmation KDS."""
        
        def action_suppression_totale():
            # Exécution de la suppression dans la base de données
            deleted_count = self.db_manager.delete_completed_and_cancelled_orders()
            
            # Rafraîchissement de l'interface
            self.load_all_archived_orders()
            self.update_sort_indicator()
            self.display_orders()           
            
            # Message de succès dans la barre de statut
            self.kds_gui.update_status(f"🗑️ {deleted_count} commandes supprimées définitivement.", 'red')
            self.kds_gui.refresh_orders(force_sound_off=True)

        # Utilisation du dialogue de confirmation personnalisé en avant-plan
        KDSConfirmDialog(
            self, 
            "⚠️ SUPPRESSION TOTALE", 
            "Êtes-vous SÛR de vouloir VIDER la corbeille ?\nCette action est irréversible.", 
            action_suppression_totale
        )