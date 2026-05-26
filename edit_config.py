import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
import json
import os
from keyboard import VirtualKeyboard

class InputDialog(tk.Toplevel):
    def __init__(self, parent, title, prompt):
        super().__init__(parent)
        self.result = None
        self.attributes("-topmost", True)
        self.overrideredirect(True)
        self.configure(bg="#ffffff", highlightbackground="#3498db", highlightthickness=2)
        
        # Centrage
        w, h = 500, 280
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        # Header
        header = tk.Frame(self, bg="#3498db", height=40)
        header.pack(fill="x")
        tk.Label(header, text=title.upper(), fg="white", bg="#3498db", font=("Arial", 12, "bold")).pack(pady=10)

        # Corps
        body = tk.Frame(self, bg="white")
        body.pack(expand=True, fill="both", padx=20, pady=10)
        
        tk.Label(body, text=prompt, bg="white", font=("Arial", 11, "bold")).pack(anchor="w", pady=5)
        
        # Champ de saisie avec limite de 40 car.
        self.entry = tk.Entry(body, font=("Arial", 16), bd=2, relief=tk.GROOVE)
        self.entry.pack(fill="x", pady=10)
        self.entry.focus_set()

        # --- LIMITATION 40 CHAR ET CLAVIER VIRTUEL ---
        self.entry.bind("<Button-1>", lambda e: VirtualKeyboard(parent, self.entry, None))
        
        # Validation auto de la longueur
        vcmd = (self.register(self.validate_limit), '%P')
        self.entry.config(validate="key", validatecommand=vcmd)

        # Footer
        footer = tk.Frame(self, bg="#f9f9f9", height=70)
        footer.pack(fill="x")
        
        tk.Button(footer, text="VALIDER", bg="#2ecc71", fg="white", font=("Arial", 12, "bold"),
                  width=12, command=self.on_ok, relief=tk.FLAT).pack(side="right", padx=10, pady=10)
        tk.Button(footer, text="ANNULER", bg="#95a5a6", fg="white", font=("Arial", 12, "bold"),
                  width=12, command=self.destroy, relief=tk.FLAT).pack(side="right", padx=10, pady=10)

        self.grab_set()
        self.wait_window()

    def validate_limit(self, new_text):
        return len(new_text) <= 40

    def on_ok(self):
        val = self.entry.get().strip()
        if val:
            self.result = val
            self.destroy()
            
# --- NOUVEAU : DIALOGUE PERSONNALISÉ PROFESSIONNEL ---
class CustomDialog(tk.Toplevel):
    def __init__(self, parent, title, message, type="info"):
        super().__init__(parent)
        self.result = None
        self.attributes("-topmost", True)
        self.overrideredirect(True)  # Retire les bordures Windows
        self.configure(bg="#ffffff", highlightbackground="#2c3e50", highlightthickness=2)
        
        # Centrage sur l'écran
        w, h = 500, 250
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        # Barre de titre
        colors = {"info": "#2ecc71", "error": "#e74c3c", "confirm": "#3498db"}
        header_color = colors.get(type, "#2c3e50")
        
        header = tk.Frame(self, bg=header_color, height=40)
        header.pack(fill="x")
        tk.Label(header, text=title.upper(), fg="white", bg=header_color, font=("Arial", 12, "bold")).pack(pady=10)

        # Corps du message
        body = tk.Frame(self, bg="white")
        body.pack(expand=True, fill="both", padx=20, pady=20)
        tk.Label(body, text=message, bg="white", font=("Arial", 13), wraplength=450).pack(expand=True)

        # Zone des boutons
        footer = tk.Frame(self, bg="#f9f9f9", height=70)
        footer.pack(fill="x")
        footer.pack_propagate(False)

        if type == "confirm":
            tk.Button(footer, text="OUI", bg="#2ecc71", fg="white", font=("Arial", 12, "bold"),
                      width=12, command=self.on_yes, relief=tk.FLAT).pack(side="right", padx=10, pady=10)
            tk.Button(footer, text="NON", bg="#95a5a6", fg="white", font=("Arial", 12, "bold"),
                      width=12, command=self.on_no, relief=tk.FLAT).pack(side="right", padx=10, pady=10)
        else:
            tk.Button(footer, text="D'ACCORD", bg=header_color, fg="white", font=("Arial", 12, "bold"),
                      width=15, command=self.destroy, relief=tk.FLAT).pack(pady=10)

        self.grab_set()  # Rendre la fenêtre modale
        self.wait_window()

    def on_yes(self):
        self.result = True
        self.destroy()

    def on_no(self):
        self.result = False
        self.destroy()



# --- APPLICATION PRINCIPALE MODIFIÉE ---
class ProConfigManager:
    def __init__(self, root):
        self.root = root
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg="#f0f0f0")

        # --- SÉCURITÉ MAXIMUM ---
        # Empêche Alt+F4
        self.root.protocol("WM_DELETE_WINDOW", self.disable_event)
        # Empêche Alt+Tab, Alt+Esc, etc. (Windows seulement)
        self.root.bind("<Alt-F4>", self.disable_event)
        self.root.bind("<Alt-Tab>", self.disable_event)
        self.root.bind("<Alt-Escape>", self.disable_event)
        
        # Ajout de Livreurs Inactifs[cite: 15]
        self.files = {
            "KDS Config": "mini_kds.json",
            "Couleurs Mots": "color_keywords.json",
            "Livreurs": "livreurs.json",
            "Livreurs Inactifs": "livreurs_inactifs.json", 
            "Mots Bloqués": "block_word_print.json",
            "Raccourcis": "shortcut_word.json",
            "Tags & Menu": "menu_ingredient.json" 
        }
        self.data = {}
        self.load_all_data()
        self.setup_ui()

    def disable_event(self, event=None):
        """Fonction qui ne fait rien pour bloquer les tentatives de fermeture."""
        return "break"
        

    def load_all_data(self):
        for label, path in self.files.items():
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        self.data[label] = json.load(f)
                except Exception as e:
                    print(f"Erreur de lecture sur {path}: {e}")
                    self.data[label] = {} # Sécurité : dictionnaire par défaut
            else:
                # Force l'objet selon le type de fichier
                if label == "Tags & Menu":
                    self.data[label] = {"couleurs_tags": {}, "categories": {}} #
                elif label == "KDS Config":
                    self.data[label] = {"modes_comptage": []}
                elif label in ["Couleurs Mots", "Mots Bloqués"]:
                    self.data[label] = {}
                else:
                    self.data[label] = []

    def setup_ui(self):
        """Initialise l'interface avec le bouton de fermeture sécurisé et stylisé."""
        title_bar = tk.Frame(self.root, bg="#2c3e50", height=60)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)

        tk.Label(title_bar, text="GESTIONNAIRE TOUCHSCREEN - PIZZERIA DU BOULEVARD", 
                 fg="white", bg="#2c3e50", font=("Arial", 18, "bold")).pack(side="left", padx=20)
        
        # Le bouton utilise maintenant safe_exit avec le CustomDialog
        tk.Button(title_bar, text=" QUITTER L'APP X ", bg="#c0392b", fg="white", font=("Arial", 14, "bold"),
                  command=self.safe_exit, relief=tk.FLAT, padx=20).pack(side="right", fill="y")

        self.nb = ttk.Notebook(self.root)
        self.nb.pack(expand=True, fill="both", padx=5, pady=5)

        for label in self.files.keys():
            tab = ttk.Frame(self.nb)
            self.nb.add(tab, text=label)
            self.render_tab(tab, label)

    def safe_exit(self):
        """Sortie sécurisée utilisant le CustomDialog professionnel."""
        # Création de l'instance du dialogue de confirmation
        dialog = CustomDialog(
            self.root, 
            "Quitter l'application", 
            "Voulez-vous vraiment fermer le gestionnaire ?\nToutes les modifications non enregistrées seront perdues.", 
            type="confirm"
        )
        
        # Si l'utilisateur clique sur 'OUI', dialog.result sera True
        if dialog.result:
            self.root.destroy()



    def render_tab(self, container, label):
        for w in container.winfo_children(): w.destroy()
        
        toolbar = tk.Frame(container, bg="#bdc3c7", height=65)
        toolbar.pack(fill="x")

        # Bouton Sauvegarder
        tk.Button(toolbar, text=f"💾 SAUVEGARDER", bg="#27ae60", fg="white", font=("Arial", 12, "bold"),
                  width=20, command=lambda l=label: self.save_data(l)).pack(side="right", padx=10, pady=10)
        
        # Bouton Annuler (Nouvel ajout)
        tk.Button(toolbar, text=f"✖ ANNULER MODIFS", bg="#e67e22", fg="white", font=("Arial", 12, "bold"),
                  width=20, command=lambda l=label, c=container: self.cancel_changes(l, c)).pack(side="right", padx=10, pady=10)

        canvas = tk.Canvas(container, bg="#ecf0f1")
        vsb = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg="#ecf0f1")
        
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=self.root.winfo_screenwidth()-50)
        canvas.configure(yscrollcommand=vsb.set)

        if label == "KDS Config": self.ui_kds_config(scroll_frame)
        elif label == "Mots Bloqués": self.ui_blocked_words(scroll_frame)
        elif label == "Tags & Menu": self.ui_menu_tags(scroll_frame) # <--- AJOUTER CECI[cite: 20]
        elif label == "Couleurs Mots": self.ui_color_words(scroll_frame)
        else: self.ui_generic_list(scroll_frame, label)

        canvas.pack(side="left", expand=True, fill="both")
        vsb.pack(side="right", fill="y")

    def cancel_changes(self, label, container):
        """Recharge le fichier pour annuler les modifs en cours avec un dialogue pro."""
        # On demande d'abord confirmation au lieu d'annuler directement
        dialog = CustomDialog(
            self.root, 
            "Annuler les modifications", 
            f"Voulez-vous vraiment ignorer les changements pour '{label}' et recharger le fichier ?", 
            type="confirm"
        )
        
        # Si l'utilisateur clique sur "OUI"
        if dialog.result:
            path = self.files[label]
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        self.data[label] = json.load(f)
                    
                    # On rafraîchit l'interface du panneau actuel
                    self.render_tab(container, label)
                    
                    # Message de succès stylisé
                    CustomDialog(
                        self.root, 
                        "Annulé", 
                        "Les modifications non enregistrées ont été effacées avec succès.", 
                        type="info"
                    )
                except Exception as e:
                    CustomDialog(
                        self.root, 
                        "Erreur", 
                        f"Impossible de recharger le fichier :\n{e}", 
                        type="error"
                    )

    def ui_menu_tags(self, frame):
        """Interface de gestion avec support complet du clavier virtuel."""
        data = self.data.get("Tags & Menu", {})
        if not isinstance(data, dict): 
            data = {"couleurs_tags": {}, "categories": {}}

        # --- SECTION 1 : TAGS DE COULEURS ---
        header_tags = tk.Frame(frame, bg="#ecf0f1")
        header_tags.pack(fill="x", pady=10)
        tk.Label(header_tags, text="🎨 TAGS DE COULEURS", font=("Arial", 16, "bold"), bg="#ecf0f1").pack(side="left", padx=10)
        tk.Button(header_tags, text="+ Ajouter Tag", bg="#2ecc71", fg="white", font=("Arial", 10, "bold"),
                  command=self.add_tag).pack(side="right", padx=10)

        tags = data.get("couleurs_tags", {})
        for tag_id, info in list(tags.items()):
            row = tk.LabelFrame(frame, text=f"Tag: {tag_id.upper()}", font=("Arial", 11, "bold"), bg="white")
            row.pack(fill="x", padx=10, pady=5)
            
            # Bouton de couleur
            tk.Button(row, text="🎨", bg=info.get('color', '#ffffff'), width=4, 
                      command=lambda t=tag_id: self.pick_tag_color(t)).pack(side="left", padx=10, pady=5)
            
            # --- CHAMP MOTS-CLÉS AVEC CLAVIER ---
            ent_words = tk.Entry(row, font=("Arial", 12))
            ent_words.insert(0, ", ".join(info.get('keywords', [])))
            ent_words.pack(side="left", expand=True, fill="x", padx=10)
            
            # CORRECTION : Ajout de None pour le ok_callback
            ent_words.bind("<Button-1>", lambda e, w=ent_words: VirtualKeyboard(self.root, w, None))
            ent_words.bind("<FocusOut>", lambda e, t=tag_id, w=ent_words: self.sync_tag_words(t, w.get()))
            
            tk.Button(row, text="🗑️", bg="#ff7675", fg="white", 
                      command=lambda t=tag_id: self.delete_item("tags", t)).pack(side="right", padx=10)

        # --- SECTION 2 : CATÉGORIES ET PLATS ---
        header_menu = tk.Frame(frame, bg="#ecf0f1")
        header_menu.pack(fill="x", pady=20)
        tk.Label(header_menu, text="🍴 MENU ET COMPOSITIONS", font=("Arial", 16, "bold"), bg="#ecf0f1").pack(side="left", padx=10)
        tk.Button(header_menu, text="+ Nouvelle Catégorie", bg="#3498db", fg="white", font=("Arial", 10, "bold"),
                  command=self.add_category).pack(side="right", padx=10)

        cats = data.get("categories", {})
        for cat_name, dishes in list(cats.items()):
            cat_frame = tk.LabelFrame(frame, text=cat_name, font=("Arial", 13, "bold"), bg="#dfe6e9", pady=5)
            cat_frame.pack(fill="x", padx=10, pady=10)
            
            cat_ctrl = tk.Frame(cat_frame, bg="#dfe6e9")
            cat_ctrl.pack(fill="x", padx=5, pady=5)
            tk.Button(cat_ctrl, text="+ Ajouter un Plat", bg="#2ecc71", fg="white", font=("Arial", 9, "bold"), 
                      command=lambda c=cat_name: self.add_dish(c)).pack(side="left")
            tk.Button(cat_ctrl, text="Supprimer Catégorie", bg="#ff7675", fg="white", font=("Arial", 9), 
                      command=lambda c=cat_name: self.delete_item("cat", c)).pack(side="right")

            for dish_name, ingredients in list(dishes.items()):
                dish_row = tk.Frame(cat_frame, bg="#dfe6e9")
                dish_row.pack(fill="x", padx=5, pady=2)
                
                tk.Label(dish_row, text=dish_name, font=("Arial", 10, "bold"), width=25, anchor="w", bg="#dfe6e9").pack(side="left")
                
                # --- CHAMP INGRÉDIENTS AVEC CLAVIER ---
                ent_ing = tk.Entry(dish_row, font=("Arial", 11))
                ent_ing.insert(0, ingredients)
                ent_ing.pack(side="left", expand=True, fill="x", padx=5)
                
                # CORRECTION : Ajout de None pour le ok_callback
                ent_ing.bind("<Button-1>", lambda e, w=ent_ing: VirtualKeyboard(self.root, w, None))
                ent_ing.bind("<FocusOut>", lambda e, c=cat_name, d=dish_name, w=ent_ing: self.sync_dish(c, d, w.get()))
                
                tk.Button(dish_row, text=" × ", bg="#fab1a0", font=("Arial", 10, "bold"),
                          command=lambda c=cat_name, d=dish_name: self.delete_item("dish", c, d)).pack(side="right", padx=2)

    # --- MÉTHODES D'AJOUT MISES À JOUR ---
    def add_tag(self):
        dialog = InputDialog(self.root, "Nouveau Tag", "Nom du tag (ex: extra) :")
        if dialog.result:
            name = dialog.result
            self.data["Tags & Menu"]["couleurs_tags"][name.lower()] = {"color": "#ffffff", "keywords": []}
            self.render_tab(self.nb.winfo_children()[self.nb.index("current")], "Tags & Menu")

    def add_category(self):
        dialog = InputDialog(self.root, "Nouvelle Catégorie", "Nom de la catégorie (ex: GRILLADES) :")
        if dialog.result:
            name = dialog.result
            self.data["Tags & Menu"]["categories"][name.upper()] = {}
            self.render_tab(self.nb.winfo_children()[self.nb.index("current")], "Tags & Menu")

    def add_dish(self, cat_name):
        dialog = InputDialog(self.root, "Nouveau Plat", f"Nom du plat dans {cat_name} :")
        if dialog.result:
            name = dialog.result
            self.data["Tags & Menu"]["categories"][cat_name][name.upper()] = ""
            self.render_tab(self.nb.winfo_children()[self.nb.index("current")], "Tags & Menu")

    # --- MÉTHODE DE SUPPRESSION UNIQUE ---
    def delete_item(self, type_item, key1, key2=None):
        dialog = CustomDialog(self.root, "Confirmation", f"Supprimer {key2 if key2 else key1} ?", type="confirm")
        if dialog.result:
            if type_item == "tags":
                del self.data["Tags & Menu"]["couleurs_tags"][key1]
            elif type_item == "cat":
                del self.data["Tags & Menu"]["categories"][key1]
            elif type_item == "dish":
                del self.data["Tags & Menu"]["categories"][key1][key2]
            
            # Rafraîchir l'affichage
            self.render_tab(self.nb.winfo_children()[self.nb.index("current")], "Tags & Menu")

    # --- MÉTHODES DE SYNCHRONISATION ---
    def sync_tag_words(self, tag_id, val):
        self.data["Tags & Menu"]["couleurs_tags"][tag_id]["keywords"] = [s.strip() for s in val.split(",") if s.strip()]

    def sync_dish(self, cat, dish, val):
        self.data["Tags & Menu"]["categories"][cat][dish] = val
        
    def pick_tag_color(self, tag_id):
        c = colorchooser.askcolor(initialcolor=self.data["Tags & Menu"]["couleurs_tags"][tag_id]["color"])[1]
        if c:
            self.data["Tags & Menu"]["couleurs_tags"][tag_id]["color"] = c.upper()
            self.render_tab(self.nb.winfo_children()[self.nb.index("current")], "Tags & Menu")

    def ui_kds_config(self, frame):
        data = self.data["KDS Config"]
        for i, mode in enumerate(data.get("modes_comptage", [])):
            row = tk.LabelFrame(frame, text=f"Mode #{i+1}", font=("Arial", 12, "bold"), bg="white", pady=10)
            row.pack(fill="x", padx=10, pady=10)
            self.create_full_field(row, "Préfixe :", mode, "prefix")
            self.create_full_field(row, "Cibles (séparer par virgule) :", mode, "targets", is_list=True)
            self.create_full_field(row, "Labels (séparer par virgule) :", mode, "labels", is_list=True)
            tk.Button(row, text="SUPPRIMER CE MODE", bg="#ff7675", command=lambda idx=i: self.remove_item("KDS Config", "modes_comptage", idx)).pack(anchor="e", padx=10)
        tk.Button(frame, text="➕ AJOUTER UN NOUVEAU MODE", font=("Arial", 14, "bold"), bg="#0984e3", fg="white", pady=10, command=self.add_kds_mode).pack(pady=20)

    def create_full_field(self, parent, label, obj, key, is_list=False):
        """Crée un champ texte qui prend toute la largeur avec support clavier."""
        tk.Label(parent, text=label, bg="white", font=("Arial", 11)).pack(anchor="w", padx=10)
        
        ent = tk.Entry(parent, font=("Arial", 14), bd=2, relief=tk.GROOVE)
        val = ", ".join(obj[key]) if is_list else obj[key]
        ent.insert(0, str(val))
        ent.pack(fill="x", padx=10, pady=5)
        
        # --- CORRECTION ICI : Ajout de None pour le ok_callback ---
        ent.bind("<Button-1>", lambda e, w=ent: VirtualKeyboard(self.root, w, None))
        # ----------------------------------------------------------
        
        ent.bind("<FocusOut>", lambda e, o=obj, k=key, w=ent, il=is_list: self.sync_field(o, k, w.get(), il))

    def sync_field(self, obj, key, val, is_list):
        if is_list: obj[key] = [s.strip() for s in val.split(",") if s.strip()]
        else: obj[key] = val

    def ui_blocked_words(self, frame):
        """Interface des mots bloqués avec support tactile complet."""
        data = self.data["Mots Bloqués"]
        
        # --- HEADER TOGGLE ---
        toggle_frame = tk.Frame(frame, bg="white", pady=20, bd=1, relief=tk.RIDGE)
        toggle_frame.pack(fill="x", padx=20, pady=10)
        
        status = data.get("filter_enabled", True)
        self.toggle_btn = tk.Button(toggle_frame, 
                                    text="FILTRE ACTIVÉ" if status else "FILTRE DÉSACTIVÉ", 
                                    font=("Arial", 14, "bold"),
                                    bg="#2ecc71" if status else "#95a5a6",
                                    fg="white", width=25, height=2,
                                    command=self.toggle_filter)
        self.toggle_btn.pack(side="left", padx=20)
        
        # --- CHAMPS DE SAISIE ---
        # Note : On utilise directement la création de champ pour s'assurer du bind
        self.render_blocked_field(frame, "MOTS CLÉS PRINCIPAUX (Keywords) :", "keywords")
        self.render_blocked_field(frame, "GARNITURES À BLOQUER :", "garnitures")

    def render_blocked_field(self, container, label_text, data_key):
        """Fonction locale pour créer un champ avec bind clavier automatique."""
        data = self.data["Mots Bloqués"]
        
        lbl_frame = tk.LabelFrame(container, text=label_text, font=("Arial", 12, "bold"), bg="#ecf0f1", pady=10)
        lbl_frame.pack(fill="x", padx=20, pady=10)
        
        # On récupère la liste et on la transforme en texte pour l'Entry
        current_val = ", ".join(data.get(data_key, []))
        
        ent = tk.Entry(lbl_frame, font=("Arial", 14))
        ent.insert(0, current_val)
        ent.pack(fill="x", padx=10, pady=5)
        
        # --- LES BINDS POUR LE CLAVIER TACTILE ---
        # 1. Ouverture du clavier au clic (Correction : ajout de None)
        ent.bind("<Button-1>", lambda e, w=ent: VirtualKeyboard(self.root, w, None))
        
        # 2. Sauvegarde auto quand on quitte le champ (FocusOut)
        ent.bind("<FocusOut>", lambda e, k=data_key, w=ent: self.sync_blocked_list(k, w.get()))
    
    def sync_blocked_list(self, key, value):
        """Transforme la chaîne de caractères en liste pour le JSON."""
        # On sépare par les virgules et on nettoie les espaces
        word_list = [w.strip() for w in value.split(",") if w.strip()]
        self.data["Mots Bloqués"][key] = word_list
        

    def toggle_filter(self):
        """Bascule entre True et False pour le filtre"""
        current = self.data["Mots Bloqués"].get("filter_enabled", True)
        new_val = not current
        self.data["Mots Bloqués"]["filter_enabled"] = new_val
        self.toggle_btn.config(text="FILTRE ACTIVÉ" if new_val else "FILTRE DÉSACTIVÉ", 
                               bg="#2ecc71" if new_val else "#95a5a6")
        # --- FOCUS ---
        self.root.lift()
        self.root.focus_force()

    def ui_color_words(self, frame):
        """Interface des couleurs par mots avec support clavier tactile."""
        data = self.data["Couleurs Mots"]
        
        for hex_color, words in list(data.items()):
            row = tk.Frame(frame, bg="white", pady=10, bd=1, relief=tk.SUNKEN)
            row.pack(fill="x", padx=10, pady=5)
            
            # Bouton pour changer la couleur
            btn_col = tk.Button(row, bg=hex_color, width=8, height=2, 
                                command=lambda c=hex_color: self.change_color_key(c))
            btn_col.pack(side="left", padx=10)
            
            # Champ de saisie des mots
            ent = tk.Entry(row, font=("Arial", 16))
            ent.insert(0, ", ".join(words))
            ent.pack(side="left", expand=True, fill="x", padx=10)
            
            # --- MODIFICATION ICI : AJOUT DE None POUR LE CALLBACK ---
            ent.bind("<Button-1>", lambda e, w=ent: VirtualKeyboard(self.root, w, None))
            # ---------------------------------------------------------
            
            ent.bind("<FocusOut>", lambda e, c=hex_color, w=ent: self.update_color_words(c, w.get()))
            
            # Bouton supprimer
            tk.Button(row, text="🗑️", bg="#fab1a0", font=("Arial", 12), 
                      command=lambda c=hex_color: self.delete_color_key(c)).pack(side="right", padx=10)
        
        # Bouton pour ajouter une nouvelle ligne de couleur
        tk.Button(frame, text="🎨 AJOUTER COULEUR", font=("Arial", 14), 
                  bg="#0984e3", fg="white", command=self.add_new_color_entry).pack(pady=20)

    def ui_generic_list(self, frame, label):
        items = self.data[label]
        if isinstance(items, dict):
            for k, v in items.items():
                if isinstance(v, list):
                    f = tk.LabelFrame(frame, text=k, bg="white")
                    f.pack(fill="x", padx=10, pady=5)
                    
                    ent = tk.Entry(f, font=("Arial", 14))
                    ent.insert(0, ", ".join(v))
                    ent.pack(fill="x", padx=10, pady=10)
                    
                    # CORRECTION : Utilisation de 'ent' et ajout de 'None' pour le callback
                    ent.bind("<Button-1>", lambda e, w=ent: VirtualKeyboard(self.root, w, None))
                    ent.bind("<FocusOut>", lambda e, l=label, key=k, w=ent: self.sync_dict(l, key, w.get()))
        else:
            for i, val in enumerate(items):
                row = tk.Frame(frame, bg="white", pady=5)
                row.pack(fill="x", padx=10)
                
                ent = tk.Entry(row, font=("Arial", 14))
                ent.insert(0, str(val))
                ent.pack(side="left", expand=True, fill="x", padx=10)
                
                # CORRECTION : Ajout de 'None' pour éviter le manque d'argument ok_callback
                ent.bind("<Button-1>", lambda e, w=ent: VirtualKeyboard(self.root, w, None))
                ent.bind("<FocusOut>", lambda e, l=label, idx=i, w=ent: self.sync_list(l, idx, w.get()))
                
                tk.Button(row, text="🗑️", bg="#fab1a0", 
                          command=lambda idx=i: self.remove_simple(label, idx)).pack(side="right", padx=10)
            
            tk.Button(frame, text="➕ AJOUTER ENTRÉE", bg="#2ecc71", fg="white", 
                      command=lambda: self.add_simple(label)).pack(pady=20)

    def sync_list(self, label, idx, val): 
        self.data[label][idx] = val
        self.root.lift()
        self.root.focus_force()

    def sync_dict(self, label, key, val): 
        self.data[label][key] = [s.strip() for s in val.split(",") if s.strip()]
        self.root.lift()
        self.root.focus_force()

    def add_simple(self, label):
        self.data[label].append("NOUVEAU")
        self.render_tab(self.nb.winfo_children()[self.nb.index("current")], label)
        # --- FOCUS ---
        self.root.lift()
        self.root.focus_force()

    def remove_simple(self, label, idx):
        self.data[label].pop(idx)
        self.render_tab(self.nb.winfo_children()[self.nb.index("current")], label)
        # --- FOCUS ---
        self.root.lift()
        self.root.focus_force()

    def add_kds_mode(self):
        self.data["KDS Config"]["modes_comptage"].append({
            "id": len(self.data["KDS Config"]["modes_comptage"]), 
            "prefix": "", "targets": [], "labels": []
        })
        self.render_tab(self.nb.winfo_children()[0], "KDS Config")
        # --- FOCUS ---
        self.root.lift()
        self.root.focus_force()

    def remove_item(self, label, key, idx):
        """Supprime un élément après confirmation pour éviter les erreurs de manipulation."""
        try:
            item_value = self.data[label][key][idx]
            if isinstance(item_value, dict):
                display_name = item_value.get('prefix') or f"Élément #{idx + 1}"
            else:
                display_name = str(item_value)
        except:
            display_name = "cet élément"

        # Demande de confirmation stylisée
        dialog = CustomDialog(
            self.root, 
            "Confirmation de suppression", 
            f"Êtes-vous certain de vouloir supprimer :\n\n'{display_name}' ?", 
            type="confirm"
        )

        # --- NOUVEAU : On force le retour au premier plan dès que le dialogue se ferme ---
        self.root.lift()
        self.root.focus_force()

        if dialog.result:
            # Suppression effective
            self.data[label][key].pop(idx)
            
            # Rafraîchissement de l'onglet actuel
            current_tab = self.nb.winfo_children()[self.nb.index("current")]
            self.render_tab(current_tab, label)
            
            # On remet une couche de focus après le rendu au cas où
            self.root.lift()
            self.root.focus_force()

    def save_data(self, label):
        """Sauvegarde les données avec le dialogue professionnel CustomDialog."""
        try:
            # Chemin du fichier à partir du dictionnaire des fichiers
            file_path = self.files[label]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data[label], f, indent=4, ensure_ascii=False)
            
            # Message de succès professionnel
            CustomDialog(
                self.root, 
                "Sauvegarde réussie", 
                f"Le fichier '{label}' a été enregistré avec succès.\n\nEmplacement : {file_path}", 
                type="info"
            )
            
        except Exception as e:
            # Message d'erreur professionnel en cas d'échec[cite: 8, 16]
            CustomDialog(
                self.root, 
                "Erreur de sauvegarde", 
                f"Une erreur est survenue lors de l'écriture du fichier :\n\n{str(e)}", 
                type="error"
            )

    def update_color_words(self, hex_key, val): 
        self.data["Couleurs Mots"][hex_key] = [s.strip() for s in val.split(",") if s.strip()]
        # Force le focus après la mise à jour du texte
        self.root.lift()
        self.root.focus_force()

    def delete_color_key(self, hex_key): 
        del self.data["Couleurs Mots"][hex_key]
        self.render_tab(self.nb.winfo_children()[1], "Couleurs Mots")
        # Remet l'application devant après la suppression
        self.root.lift()
        self.root.focus_force()

    def add_new_color_entry(self):
        c = colorchooser.askcolor()[1]
        # On force le retour immédiat, même si l'utilisateur fait "Annuler"
        self.root.lift()
        self.root.focus_force()
        
        if c: 
            self.data["Couleurs Mots"][c.upper()] = []
            self.render_tab(self.nb.winfo_children()[1], "Couleurs Mots")

    def change_color_key(self, old):
        c = colorchooser.askcolor(initialcolor=old)[1]
        # On force le retour immédiat
        self.root.lift()
        self.root.focus_force()
        
        if c:
            # On récupère la valeur, on crée la nouvelle clé et on supprime l'ancienne
            self.data["Couleurs Mots"][c.upper()] = self.data["Couleurs Mots"].pop(old)
            self.render_tab(self.nb.winfo_children()[1], "Couleurs Mots")

if __name__ == "__main__":
    root = tk.Tk()
    app = ProConfigManager(root)
    root.mainloop()