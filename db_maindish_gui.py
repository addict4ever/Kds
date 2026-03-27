# db_maindish_gui.py

import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from tkinter.scrolledtext import ScrolledText
import datetime
from typing import List, Literal, Tuple, Union

# Assurez-vous d'avoir le fichier db_maindish.py mis à jour pour la gestion du prix et la fonction 'update_dish'
from db_maindish import MainDishDBManager

# 🌟 NÉCESSAIRE: Importation du clavier virtuel (doit être disponible dans keyboard.py)
try:
    from keyboard import VirtualKeyboard
except ImportError:
    # Définition d'un mock si le fichier n'est pas trouvé (pour ne pas crasher)
    class VirtualKeyboard:
        def __init__(self, master, target_entry_widget, ok_callback=None):
            messagebox.showerror("Erreur", "Le module 'keyboard.py' est introuvable.\nLe clavier virtuel ne fonctionnera pas.")
            
class MainDishApp:
    """
    Interface graphique (Tkinter) pour gérer la liste des plats principaux.
    V3.0: Ajout de la fonction MODIFIER, gestion des PRIX, et structure améliorée.
    """
    def __init__(self, master):
        self.master = master
        master.title("Gestion des Plats Principaux KDS (v3.0 - MODIFICATION & PRIX)")
        master.geometry("800x950")
        master.resizable(False, False)

        self.db_manager = MainDishDBManager() 
        # Cache local des plats: liste de tuples (nom, prix)
        self.dishes: List[Tuple[str, float]] = [] 
        # Variable pour stocker le nom original du plat sélectionné lors d'une modification
        self.selected_original_dish_name: Union[str, None] = None 

        # --- Configuration du Style (Tactile/Visuel) ---
        self.style = ttk.Style()
        self.style.configure("Vertical.TScrollbar", width=35) # Scrollbar large pour le tactile
        self.style.configure("TNotebook.Tab", font=('Arial', 14, 'bold'), padding=[15, 10], background='#e0e0e0', foreground='#333333')
        self.style.map("TNotebook.Tab", background=[("selected", '#3498db')], foreground=[("selected", 'white')])
        self.master.config(bg='#f7f7f7')

        # --- Cadre de l'en-tête (pour le bouton Quitter) ---
        header_frame = tk.Frame(master, bg='#f7f7f7', padx=15, pady=10)
        header_frame.pack(fill='x')
        
        tk.Label(header_frame, text="KDS Plat Principal", font=('Arial', 18, 'bold'), fg='#333333', bg='#f7f7f7').pack(side='left')
        
        self.quit_button_top = tk.Button(header_frame, text="❌ FERMER L'APPLICATION", command=self.master.destroy, 
                                        bg='#e74c3c', fg='white', font=('Arial', 12, 'bold'), padx=10, pady=5)
        self.quit_button_top.pack(side='right')

        # --- Onglets (Notebook) ---
        self.notebook = ttk.Notebook(master)
        self.notebook.pack(pady=10, padx=15, fill='both', expand=True)

        # Onglet 1: Gestion
        self.manage_frame = tk.Frame(self.notebook, bg='white')
        self.manage_frame.pack(fill='both', expand=True)
        self.notebook.add(self.manage_frame, text="🍴 Gérer les Plats")

        # Onglet 2: Sauvegarde
        self.backup_frame = tk.Frame(self.notebook, bg='#eaf2f8')
        self.backup_frame.pack(fill='both', expand=True)
        self.notebook.add(self.backup_frame, text="💾 Sauvegarde / Importation")

        self.explorer_frame = tk.Frame(self.notebook, bg='#f4f6f7')
        self.notebook.add(self.explorer_frame, text="🔍 Explorateur Archive")
        self._setup_explorer_tab()

        # --- Variables d'état ---
        self.dish_name_var = tk.StringVar()
        self.dish_price_var = tk.StringVar(value="0.00")
        self.filter_var = tk.StringVar()
        self.sort_order: Literal["asc", "desc"] = "asc" 
        self.replace_existing_var = tk.BooleanVar(value=False) 

        # Déclenchement automatique du filtre lors de la saisie
        self.filter_var.trace_add("write", lambda name, index, mode: self.filter_list())
        
        self._setup_manage_tab()
        self._setup_backup_tab()
        
        # Chargement initial des données
        self.load_and_refresh() 

    # ----------------------------------------------------------------------
    # --- CONFIGURATION DES ONGLETS ---
    # ----------------------------------------------------------------------

    # Dans db_maindish_gui.py, modifiez les méthodes de l'explorateur

    def _setup_explorer_tab(self):
        """Interface pour transformer des Sub-Items en Main Dishes sans quantités."""
        self.filter_new_var = tk.BooleanVar(value=False) # Variable pour le bouton filtre

        container = tk.Frame(self.explorer_frame, bg='#f4f6f7')
        container.pack(fill='both', expand=True, padx=10, pady=10)

        # --- COLONNE GAUCHE : SUB-ITEMS ---
        left_f = tk.LabelFrame(container, text="🌿 Sous-Items (Archive)", font=('Arial', 10, 'bold'))
        left_f.pack(side='left', fill='both', expand=True, padx=5)
        
        # Barre de contrôle en haut de la liste
        ctrl_bar = tk.Frame(left_f)
        ctrl_bar.pack(fill='x', padx=5, pady=5)
        
        # BOUTON FILTRE : Nouveaux seulement
        tk.Checkbutton(ctrl_bar, text="Afficher seulement les nouveaux", 
                    variable=self.filter_new_var, command=self.refresh_explorer,
                    font=('Arial', 9, 'italic')).pack(side='left')

        self.sub_archive_listbox = tk.Listbox(left_f, font=('Arial', 11), selectmode=tk.MULTIPLE)
        self.sub_archive_listbox.pack(side='left', fill='both', expand=True)
        
        scroll = ttk.Scrollbar(left_f, command=self.sub_archive_listbox.yview)
        scroll.pack(side='right', fill='y')
        self.sub_archive_listbox.config(yscrollcommand=scroll.set)

        # --- CENTRE : ACTIONS ---
        mid_f = tk.Frame(container, bg='#f4f6f7')
        mid_f.pack(side='left', padx=15)
        
        tk.Button(mid_f, text="AJOUTER\nAU MENU ➡", bg='#27ae60', fg='white', 
                font=('Arial', 10, 'bold'), command=self.transfer_subs_to_main, width=12).pack(pady=20)
        
        tk.Button(mid_f, text="🔄 Actualiser", command=self.refresh_explorer, bg='#d5dbdb').pack()

        # --- COLONNE DROITE : MENU ACTUEL ---
        right_f = tk.LabelFrame(container, text="✅ Menu Principal Actuel", font=('Arial', 10, 'bold'))
        right_f.pack(side='left', fill='both', expand=True, padx=5)
        
        self.current_menu_display = tk.Listbox(right_f, font=('Arial', 10), bg='#ecf0f1')
        self.current_menu_display.pack(fill='both', expand=True, padx=5, pady=5)

        self.refresh_explorer()

    def refresh_explorer(self):
        """Rafraîchit la liste sans les chiffres et avec filtre."""
        self.sub_archive_listbox.delete(0, tk.END)
        self.current_menu_display.delete(0, tk.END)
        
        # Charger les sous-items (le nettoyage se fait dans le manager via re.sub)
        subs = self.db_manager.get_unique_subitems_from_archive(only_new=self.filter_new_var.get())
        for s in subs:
            self.sub_archive_listbox.insert(tk.END, s)
            
        # Charger le menu actuel
        current = self.db_manager.get_all_dishes()
        for dish in current:
            self.current_menu_display.insert(tk.END, f" {dish[0]}")

    def transfer_subs_to_main(self):
        """Transfert avec boîte de dialogue toujours au premier plan."""
        selected_indices = self.sub_archive_listbox.curselection()
        
        if not selected_indices:
            # parent=self.master force la boîte au-dessus de VOTRE app
            messagebox.showwarning("Sélection vide", 
                                 "Veuillez sélectionner des items à transférer.", 
                                 parent=self.master)
            return

        added = 0
        ignored = 0
        for idx in selected_indices:
            sub_name = self.sub_archive_listbox.get(idx)
            if self.db_manager.add_dish_if_not_exists(sub_name):
                added += 1
            else:
                ignored += 1
                
        self.refresh_explorer()
        if hasattr(self, 'refresh_dish_list'): 
            self.refresh_dish_list()
        
        # Message final "Topmost"
        messagebox.showinfo("Importation Réussie", 
                          f"Traitement terminé :\n\n"
                          f"✅ {added} nouveaux plats ajoutés\n"
                          f"❌ {ignored} déjà présents",
                          parent=self.master)
        
        # Redonne le focus à la fenêtre principale
        self.master.focus_force()

    def _setup_manage_tab(self):
        
        # Cadre de Contrôle (Ajout/Modification/Suppression/Filtre)
        self.control_frame = tk.Frame(self.manage_frame, padx=15, pady=15, bg='white', relief=tk.RAISED, bd=1)
        self.control_frame.pack(fill='x', padx=10, pady=10)
        
        # Sous-cadre pour les entrées de Nom et Prix
        input_frame = tk.Frame(self.control_frame, bg='white')
        input_frame.grid(row=0, column=0, columnspan=4, sticky='ew', pady=5)
        input_frame.grid_columnconfigure(1, weight=1) 
        
        # Nom du Plat
        tk.Label(input_frame, text="Nom du Plat:", bg='white', font=('Arial', 12, 'bold')).grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.dish_entry = tk.Entry(input_frame, textvariable=self.dish_name_var, justify='left', font=('Arial', 14), bd=2, relief=tk.GROOVE)
        self.dish_entry.grid(row=0, column=1, sticky='ew')
        self.dish_name_var.trace_add("write", lambda name, index, mode: self.dish_name_var.set(self.dish_name_var.get().upper())) 
        
        self.keyboard_button = tk.Button(input_frame, text="⌨️ NOM", command=self.open_dish_keyboard, font=('Arial', 10, 'bold'), width=8, bg='#3498db', fg='white', relief=tk.RAISED)
        self.keyboard_button.grid(row=0, column=2, padx=(5, 0), sticky='e')

        # Prix du Plat 
        tk.Label(input_frame, text="Prix ($):", bg='white', font=('Arial', 12, 'bold')).grid(row=1, column=0, sticky='w', padx=(0, 10), pady=(5,0))
        self.price_entry = tk.Entry(input_frame, textvariable=self.dish_price_var, justify='right', font=('Arial', 14), bd=2, relief=tk.GROOVE)
        self.price_entry.grid(row=1, column=1, sticky='ew', pady=(5, 0))
        
        self.keyboard_price_button = tk.Button(input_frame, text="⌨️ PRIX", command=self.open_price_keyboard, font=('Arial', 10, 'bold'), width=8, bg='#2980b9', fg='white', relief=tk.RAISED)
        self.keyboard_price_button.grid(row=1, column=2, padx=(5, 0), sticky='e', pady=(5, 0))

        # Raccourcis clavier
        self.dish_entry.bind('<Return>', lambda event: self.add_dish()) 
        self.price_entry.bind('<Return>', lambda event: self.add_dish()) 
        
        # --- Boutons d'Action (4 colonnes) ---
        self.add_button = tk.Button(self.control_frame, text="➕ AJOUTER", command=self.add_dish, bg='#2ecc71', fg='white', font=('Arial', 12, 'bold'), height=2)
        self.add_button.grid(row=2, column=0, padx=5, pady=10, sticky='ew')
        
        self.modify_button = tk.Button(self.control_frame, text="✏️ MODIFIER", command=self.modify_dish, bg='#f39c12', fg='white', font=('Arial', 12, 'bold'), height=2)
        self.modify_button.grid(row=2, column=1, padx=5, pady=10, sticky='ew')

        self.remove_button = tk.Button(self.control_frame, text="➖ SUPPRIMER", command=self.remove_dish, bg='#e67e22', fg='white', font=('Arial', 12, 'bold'), height=2)
        self.remove_button.grid(row=2, column=2, padx=5, pady=10, sticky='ew')
        
        self.refresh_button = tk.Button(self.control_frame, text="🔄 ACTUALISER", command=self.load_and_refresh, bg='#3498db', fg='white', font=('Arial', 12, 'bold'), height=2)
        self.refresh_button.grid(row=2, column=3, padx=5, pady=10, sticky='ew')

        # --- Filtre et Tri ---
        filter_frame = tk.Frame(self.control_frame, bg='white', pady=5)
        filter_frame.grid(row=3, column=0, columnspan=4, sticky='ew')
        filter_frame.grid_columnconfigure(1, weight=1) 

        tk.Label(filter_frame, text="Rechercher:", bg='white', font=('Arial', 12, 'bold')).grid(row=0, column=0, sticky='w', padx=(0, 10))
        
        self.filter_entry = tk.Entry(filter_frame, textvariable=self.filter_var, justify='left', font=('Arial', 14), bd=2, relief=tk.GROOVE)
        self.filter_entry.grid(row=0, column=1, sticky='ew')
        self.filter_var.trace_add("write", lambda name, index, mode: self.filter_var.set(self.filter_var.get().upper()))
        
        self.keyboard_filter_button = tk.Button(filter_frame, text="⌨️", command=self.open_filter_keyboard, font=('Arial', 12, 'bold'), width=3, bg='#3498db', fg='white', relief=tk.RAISED)
        self.keyboard_filter_button.grid(row=0, column=2, padx=(5, 0), sticky='e')
        
        self.sort_button = tk.Button(filter_frame, text="🔠 Tri", command=self.toggle_sort, bg='#9b59b6', fg='white', font=('Arial', 12, 'bold'), width=5)
        self.sort_button.grid(row=0, column=3, padx=5, sticky='e')
        
        # --- Journal des Opérations (Statut) ---
        tk.Label(self.control_frame, text="Journal des Opérations:", font=('Arial', 10)).grid(row=4, column=0, columnspan=4, sticky='w', pady=(5,0))
        self.status_text = ScrolledText(self.control_frame, height=3, font=('Arial', 10), bd=1, relief=tk.SUNKEN) 
        self.status_text.grid(row=5, column=0, columnspan=4, sticky='ew', pady=(0, 5))
        self.update_status("Prêt à gérer les plats...") 

        self.control_frame.grid_columnconfigure(0, weight=1)
        self.control_frame.grid_columnconfigure(1, weight=1)
        self.control_frame.grid_columnconfigure(2, weight=1)
        self.control_frame.grid_columnconfigure(3, weight=1)
        
        # --- Listbox d'Affichage des Plats ---
        self.list_frame = tk.Frame(self.manage_frame, padx=15, pady=10, bg='white')
        self.list_frame.pack(fill='both', expand=True)

        tk.Label(self.list_frame, text="Plats Principaux Actuels (Nom | Prix):", font=('Arial', 12, 'bold'), bg='white').pack(fill='x', pady=5)
        
        self.listbox = tk.Listbox(self.list_frame, height=20, selectmode=tk.SINGLE, font=('Courier', 14), bd=2, relief=tk.GROOVE) 
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind('<<ListboxSelect>>', self.on_listbox_select) # Action lors de la sélection

        scrollbar = ttk.Scrollbar(self.list_frame, orient="vertical", style="Vertical.TScrollbar") 
        scrollbar.config(command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        
        self.listbox.config(yscrollcommand=scrollbar.set)
        
        
    def _setup_backup_tab(self):
        
        # --- Section 1: Sauvegarde/Restauration DB Complète ---
        db_group = ttk.LabelFrame(self.backup_frame, text="Sauvegarde / Restauration COMPLÈTE (Fichier DB)", padding="10")
        db_group.pack(fill='x', padx=20, pady=15)
        
        tk.Label(db_group, text="Crée une copie du fichier kds_constants.db. Restauration rapide mais nécessite le redémarrage.", font=('Arial', 10, 'bold'), bg='#eaf2f8').pack(pady=5)

        db_buttons_frame = tk.Frame(db_group, bg='#eaf2f8')
        db_buttons_frame.pack(fill='x')
        
        export_db_button = tk.Button(db_buttons_frame, text="⬇️ EXPORTER DB", command=self.export_db_file, bg='#3499db', fg='white', font=('Arial', 12, 'bold'), height=2)
        export_db_button.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        import_db_button = tk.Button(db_buttons_frame, text="⬆️ IMPORTER DB", command=self.import_db_file, bg='#e74c3c', fg='white', font=('Arial', 12, 'bold'), height=2)
        import_db_button.pack(side='right', fill='x', expand=True, padx=(5, 0))


        # --- Section 2: Exportation/Importation de Données (Fichier JSON) ---
        json_group = ttk.LabelFrame(self.backup_frame, text="Échange de Données (Fichier JSON)", padding="10")
        json_group.pack(fill='x', padx=20, pady=15)
        
        tk.Label(json_group, text="Export/Import des noms de plats ET de leurs PRIX. Idéal pour l'édition ou le partage.", font=('Arial', 10), bg='#eaf2f8').pack(pady=5)

        json_buttons_frame = tk.Frame(json_group, bg='#eaf2f8')
        json_buttons_frame.pack(fill='x')
        
        replace_check = tk.Checkbutton(json_group, text="⚠️ EFFACER la DB actuelle avant l'importation JSON", 
                                       variable=self.replace_existing_var, onvalue=True, offvalue=False, 
                                       font=('Arial', 10, 'bold'), fg='#c0392b', bg='#eaf2f8')
        replace_check.pack(pady=5, anchor='w')

        export_json_button = tk.Button(json_buttons_frame, text="⬇️ EXPORTER JSON", command=self.export_dishes, bg='#2980b9', fg='white', font=('Arial', 12, 'bold'), height=2)
        export_json_button.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        import_json_button = tk.Button(json_buttons_frame, text="⬆️ IMPORTER JSON", command=self.import_dishes, bg='#27ae60', fg='white', font=('Arial', 12, 'bold'), height=2)
        import_json_button.pack(side='right', fill='x', expand=True, padx=(5, 0))


        # Statut de l'opération (pour l'onglet Sauvegarde)
        tk.Label(self.backup_frame, text="Journal des Opérations :", font=('Arial', 10, 'bold'), bg='#eaf2f8').pack(fill='x', padx=20, pady=(5,0))
        self.backup_status_text = ScrolledText(self.backup_frame, height=12, font=('Arial', 10), bd=1, relief=tk.SUNKEN)
        self.backup_status_text.pack(fill='both', padx=20, pady=5, expand=True)
        self.backup_status_text.insert(tk.END, "Prêt pour la sauvegarde/restauration.")
        self.backup_status_text.config(state=tk.DISABLED) 

    # ----------------------------------------------------------------------
    # --- MÉTHODES D'ASSISTANCE (Statut, Tri, Filtre, Sélection) ---
    # ----------------------------------------------------------------------

    def open_dish_keyboard(self):
        VirtualKeyboard(self.master, self.dish_entry, self.add_dish)
        
    def open_price_keyboard(self):
        VirtualKeyboard(self.master, self.price_entry, self.add_dish) 
        
    def open_filter_keyboard(self):
        VirtualKeyboard(self.master, self.filter_entry, self.filter_list)

    def on_listbox_select(self, event):
        """Met à jour les champs d'entrée avec le plat sélectionné et prépare l'état 'Modifier'."""
        try:
            selected_index = self.listbox.curselection()[0]
            
            # Recrée la liste filtrée/triée pour trouver l'élément sélectionné
            search_term = self.filter_var.get().strip().upper()
            filtered_dishes: List[Tuple[str, float]]
            
            if search_term:
                filtered_dishes = [dish for dish in self.dishes if search_term in dish[0]]
            else:
                filtered_dishes = self.dishes[:] 
            
            filtered_dishes.sort(key=lambda x: x[0], reverse=(self.sort_order == "desc"))
            
            selected_dish_name, selected_dish_price = filtered_dishes[selected_index]
            
            # Stocker le nom original pour la fonction de modification
            self.selected_original_dish_name = selected_dish_name
            self.modify_button.config(bg='#2ecc71', text="✅ PRÊT À MODIFIER") # Visuel pour indiquer l'état
            
            # Mettre à jour les champs Nom ET Prix
            self.dish_name_var.set(selected_dish_name) 
            self.dish_price_var.set(f"{selected_dish_price:.2f}") 
            
            self.filter_var.set("") 
            self.filter_list() 
            
            self.update_status(f"Plat '{selected_dish_name}' sélectionné pour modification. Entrez les nouvelles valeurs.")
            
        except IndexError:
            # Réinitialiser si rien n'est sélectionné
            self.selected_original_dish_name = None
            self.modify_button.config(bg='#f39c12', text="✏️ MODIFIER")
            pass
        except Exception as e:
            self.update_status(f"Erreur de sélection: {e}")

    def update_status(self, message: str, is_backup: bool = False):
        """Met à jour le widget de statut approprié (Journal des Opérations)."""
        timestamp = datetime.datetime.now().strftime("[%H:%M:%S]")
        if is_backup:
            self.backup_status_text.config(state=tk.NORMAL)
            self.backup_status_text.insert(tk.END, f"{timestamp} {message}\n---\n")
            self.backup_status_text.config(state=tk.DISABLED)
            self.backup_status_text.see(tk.END) 
        else:
            self.status_text.config(state=tk.NORMAL)
            self.status_text.delete('1.0', tk.END) 
            self.status_text.insert(tk.END, f"{timestamp} {message}")
            self.status_text.config(state=tk.DISABLED)
            
    def load_and_refresh(self):
        """Charge les données de la DB, met à jour le cache et affiche la liste."""
        self.dishes = self.db_manager.load_all_dishes() 
        self.filter_list() 
        self.update_status(f"Base de données chargée. {len(self.dishes)} plats au total.")
        # Réinitialiser l'état de modification après l'actualisation
        self.selected_original_dish_name = None
        self.modify_button.config(bg='#f39c12', text="✏️ MODIFIER")
        
    def filter_list(self):
        """Filtre, trie et affiche les plats dans la Listbox."""
        search_term = self.filter_var.get().strip().upper()
        
        filtered_dishes: List[Tuple[str, float]]
        
        # 1. Filtration
        if search_term:
            filtered_dishes = [dish for dish in self.dishes if search_term in dish[0]]
        else:
            filtered_dishes = self.dishes[:] 
            
        # 2. Tri
        if self.sort_order == "asc":
            filtered_dishes.sort(key=lambda x: x[0])
            self.sort_button.config(text="🔠 Tri (A-Z)")
        else:
            filtered_dishes.sort(key=lambda x: x[0], reverse=True)
            self.sort_button.config(text="🔠 Tri (Z-A)")
            
        # 3. Mise à jour de la Listbox
        self.listbox.delete(0, tk.END)
        for name, price in filtered_dishes:
            # Formatage aligné pour l'affichage (Nom | $X.XX)
            self.listbox.insert(tk.END, f"{name.ljust(40)} ${price:.2f}")

        if search_term:
             self.update_status(f"Liste filtrée/triée. Total affiché: {len(filtered_dishes)}.")
        
    def toggle_sort(self):
        """Bascule l'ordre de tri et rafraîchit la liste."""
        self.sort_order = "desc" if self.sort_order == "asc" else "asc"
        self.filter_list()

    # ----------------------------------------------------------------------
    # --- MÉTHODES D'OPÉRATIONS (CRUD) ---
    # ----------------------------------------------------------------------

    def add_dish(self):
        """Ajoute un nouveau plat et son prix à la DB."""
        dish_name = self.dish_name_var.get().strip()
        dish_price_str = self.dish_price_var.get().strip().replace(',', '.') 

        if not dish_name or not dish_price_str:
            messagebox.showwarning("Attention", "Veuillez entrer un nom et un prix.", parent=self.master)
            return

        try:
            dish_price = float(dish_price_str)
        except ValueError:
            messagebox.showerror("Erreur de format", "Le prix doit être un nombre valide.", parent=self.master)
            return

        result_message = self.db_manager.add_dish(dish_name, dish_price) 
        self.update_status(result_message)
        
        self.load_and_refresh() 
        if result_message.startswith("SUCCÈS"):
            self.dish_name_var.set("")
            self.dish_price_var.set("0.00") 
            self.selected_original_dish_name = None 
            self.modify_button.config(bg='#f39c12', text="✏️ MODIFIER")
            
        # Force le retour du focus sur l'application
        self.master.focus_force()
            
    def modify_dish(self):
        """Met à jour le nom et/ou le prix d'un plat sélectionné."""
        original_name = self.selected_original_dish_name
        new_dish_name = self.dish_name_var.get().strip()
        new_dish_price_str = self.dish_price_var.get().strip().replace(',', '.')

        if not original_name:
            messagebox.showwarning("Attention", "Veuillez sélectionner un plat dans la liste.", parent=self.master)
            return

        if not new_dish_name or not new_dish_price_str:
            messagebox.showwarning("Attention", "Le nom et le prix ne peuvent pas être vides.", parent=self.master)
            return
            
        try:
            new_dish_price = float(new_dish_price_str)
        except ValueError:
            messagebox.showerror("Erreur de format", "Le nouveau prix doit être valide.", parent=self.master)
            return
            
        # parent=self.master lie cette question à votre fenêtre
        confirm = messagebox.askyesno(
            "Confirmer la Modification",
            f"Modifier '{original_name}' ?\n\nNouveau Nom: '{new_dish_name}'\nPrix: {new_dish_price:.2f}$",
            parent=self.master
        )
        
        if confirm:
            result_message = self.db_manager.update_dish(original_name, new_dish_name, new_dish_price)
            self.update_status(result_message)
            
            if "SUCCÈS" in result_message:
                self.load_and_refresh()
                self.dish_name_var.set("")
                self.dish_price_var.set("0.00")
                self.selected_original_dish_name = None
                self.modify_button.config(bg='#f39c12', text="✏️ MODIFIER")
        
        self.master.focus_force()

    def remove_dish(self):
        """Supprime le plat sélectionné."""
        dish_name = self.dish_name_var.get().strip().upper() 
        
        if not dish_name:
            messagebox.showwarning("Attention", "Sélectionnez un plat à supprimer.", parent=self.master)
            return

        confirm = messagebox.askyesno(
            "Confirmer la Suppression",
            f"Êtes-vous sûr de vouloir supprimer :\n\n'{dish_name}' ?",
            parent=self.master
        )
        
        if confirm:
            result_message = self.db_manager.remove_dish(dish_name)
            self.update_status(result_message)
            self.load_and_refresh()
            if result_message.startswith("SUCCÈS"):
                self.dish_name_var.set("")
                self.dish_price_var.set("0.00") 
                self.selected_original_dish_name = None 
                self.modify_button.config(bg='#f39c12', text="✏️ MODIFIER")
        
        self.master.focus_force()

    # ----------------------------------------------------------------------
    # --- MÉTHODES DE SAUVEGARDE/IMPORTATION ---
    # ----------------------------------------------------------------------
    
    def export_dishes(self):
        """Exporte les plats (Nom et Prix) vers JSON."""
        file_path = filedialog.asksaveasfilename(
            parent=self.master, # Garde le focus
            defaultextension=".json",
            filetypes=[("Fichiers JSON", "*.json")],
            initialfile=f"kds_maindishes_backup_{datetime.date.today()}.json",
            title="Enregistrer la Sauvegarde JSON"
        )
        if file_path:
            result_message = self.db_manager.export_dishes_to_json(file_path)
            self.update_status(result_message, is_backup=True)
        
        self.master.focus_force()

    def import_dishes(self):
        """Importe les plats (Nom et Prix) depuis JSON."""
        file_path = filedialog.askopenfilename(
            parent=self.master,
            defaultextension=".json",
            filetypes=[("Fichiers JSON", "*.json")],
            title="Sélectionner le Fichier JSON à Importer"
        )
        if file_path:
            replace = self.replace_existing_var.get()
            if replace:
                # parent=self.master pour que la confirmation soit au-dessus
                confirm = messagebox.askyesno(
                    "⚠️ CONFIRMATION D'EFFACEMENT",
                    "Vous avez choisi d'EFFACER TOUTES les données actuelles avant d'importer. Continuer ?",
                    parent=self.master
                )
                if not confirm:
                    self.update_status("Importation JSON annulée par l'utilisateur.", is_backup=True)
                    self.master.focus_force()
                    return
                    
            result_message = self.db_manager.import_dishes_from_json(file_path, replace_existing=replace)
            self.update_status(result_message, is_backup=True)
            self.load_and_refresh() 
            self.notebook.select(self.manage_frame) # Revenir à l'onglet de gestion
        
        self.master.focus_force()

    def export_db_file(self):
        """Exporte le fichier DB complet."""
        file_path = filedialog.asksaveasfilename(
            parent=self.master,
            defaultextension=".db",
            filetypes=[("Fichiers SQLite Database", "*.db")],
            initialfile=f"kds_constants_backup_{datetime.date.today()}.db",
            title="Enregistrer la Sauvegarde DB Complète"
        )
        if file_path:
            result_message = self.db_manager.export_database_file(file_path)
            self.update_status(result_message, is_backup=True)
        
        self.master.focus_force()

    def import_db_file(self):
        """Importe (remplace) le fichier DB complet."""
        confirm = messagebox.askyesno(
            "⚠️ RESTAURATION DB COMPLÈTE",
            "Ceci va remplacer le fichier de base de données kds_constants.db par le fichier sélectionné.\n\n"
            "TOUTES LES DONNÉES ACTUELLES SERONT PERDUES et l'application DEVRA ÊTRE REDÉMARRÉE pour charger la nouvelle DB. Continuer ?",
            parent=self.master
        )
        
        if not confirm:
            self.update_status("Restauration DB annulée par l'utilisateur.", is_backup=True)
            self.master.focus_force()
            return

        file_path = filedialog.askopenfilename(
            parent=self.master,
            defaultextension=".db",
            filetypes=[("Fichiers SQLite Database", "*.db")],
            title="Sélectionner le Fichier DB à Restaurer"
        )
        
        if file_path:
            result_message = self.db_manager.import_database_file(file_path)
            self.update_status(result_message, is_backup=True)
            
            if "SUCCÈS" in result_message:
                messagebox.showinfo(
                    "Restauration Réussie",
                    "Base de données restaurée. Veuillez redémarrer l'application.",
                    parent=self.master
                )
            elif "ERREUR DE SÉCURITÉ/STRUCTURE" in result_message:
                 messagebox.showerror(
                    "Erreur de Sécurité",
                    "Le fichier sélectionné n'est pas une base de données KDS valide.",
                    parent=self.master
                )
            elif "Échec de la restauration" in result_message:
                messagebox.showerror(
                    "Erreur d'Importation",
                    "Échec. Assurez-vous d'avoir fermé et rouvert l'application avant d'importer.",
                    parent=self.master
                )
        
        self.master.focus_force()

if __name__ == '__main__':
    root = tk.Tk()
    app = MainDishApp(root)
    root.mainloop()