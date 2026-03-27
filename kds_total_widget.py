import tkinter as tk
from tkinter import ttk
from db_manager import DBManager
import json 
import re 
from datetime import datetime

# --- SIMULATION/IMPORTATION DU GESTIONNAIRE DE CONSTANTES BASÉ SUR LA DB ---
try:
    from DBKonstantesManager import DBKonstantesManager
except ImportError:
    # Fallback/Logique d'erreur si le gestionnaire n'est pas trouvé
    class DBKonstantesManager:
        def __init__(self): 
            print("DBKonstantesManager introuvable. Les constantes seront manquantes.")
        def get_dict_constant(self, name): return {}
        def get_list_constant(self, name): return []
        # Fallback pour les couleurs
        def get_simple_constant(self, name): 
            if "COLOR" in name: return "#FFFFFF" 
            return None


# --- Constantes Statiques/Logiques (Non gérées par la DB, pour l'instant) ---
# Si ces mots-clés sont gérés par la DB, ils devraient être déplacés dans _load_constants_from_db.
KEYWORDS_VINEGRETTE_CHEF = "salade chef"
KEYWORDS_VINEGRETTE_CESAR = "salade césar"
KEYWORDS_SANS_SALADE = "sans salade"
# --------------------------------------------------------------------------------------


class TotalWidget(tk.Toplevel):
    """
    Fenêtre flottante KDS - Affiche le total global des items avec filtres et couleurs.
    Toutes les constantes sont chargées de kdstotal.db.
    """

    def __init__(self, master_kds_instance, db_manager: DBManager, update_callback):
        super().__init__(master_kds_instance.root)
        self.kds_root_instance = master_kds_instance # ⭐ Sauvegarde de l'instance KDSGUI
        self.db_manager = db_manager
        self.update_callback = update_callback
        self.overrideredirect(True)
        self.geometry("350x480+10+10")
        self.configure(bg="#34495e", relief="raised", borderwidth=2)
        self.attributes("-topmost", True)

        self.all_aggregated_items = {}
        self.aggregated_structured_items = {} 
        self.current_filter = "ALL"
        
        # --- Totaux spécifiques ---
        self.egg_cooking_totals = {} 
        self.toast_cooking_totals = {} 
        
        # ⭐ NOUVEAU: Initialisation du gestionnaire de constantes DB
        self.konstantes_db = DBKonstantesManager()
        
        # Initialisation par défaut de tous les attributs (sera écrasé par la DB)
        self.COLOR_SAUCE = "red"
        self.COLOR_VINAIGRETTE = "green"
        self.COLOR_SIDE = "blue"
        self.COLOR_TOAST = "orange"
        self.COLOR_OEUF = "brown"
        self.COLOR_PATES = "gray"
        self.COLOR_BOISSON = "purple"
        self.COLOR_PLATS = "lightgreen"
        self.COLOR_MAIN = "white"
        self.COLOR_EGG_COOKING = "coral"
        self.COLOR_DEFAULT_FILTER_BG = "darkslategray"
        
        self.ITEM_CATEGORY = {}
        self.USER_PLATS_KEYWORDS_OVERRIDE = []
        self.DOUBLING_MAIN_ITEM_KEYWORDS = []
        self.TOAST_TOTAL_KEYWORDS = []
        self.EXCLUSION_KEYWORDS = []
        self.INCLUSION_OVERRIDES = []
        self.ITEM_SAUCE_MAP = {}
        self.KEYWORDS_PATES_SPECIALES = {}
        self.SAUCE_EXCLUSION_SUB_ITEM_MAP = {}

        self._load_constants_from_db() # Chargement initial des constantes
        
        # --- HEADER ---
        # --- HEADER ---
        self.header = tk.Frame(self, bg="#2c3e50")
        self.header.pack(fill="x")
        tk.Label(
            self.header,
            text="📊 TOTAL KDS 📊",
            font=("Arial", 14, "bold"),
            fg="white",
            bg="#2c3e50",
        ).pack(side=tk.LEFT, padx=5, pady=5)
        
        # ⭐ BOUTON DE FERMETURE 'X' MODIFIÉ POUR LE TACTILE ⭐
        tk.Button(
            self.header,
            text="X",
            command=self._safe_destroy, # ⭐ Nouvelle méthode de fermeture
            bg="#e74c3c",
            fg="white",
            bd=0,
            relief="flat",
            font=("Arial", 18, "bold"),  # Augmente le 'X'
            width=3,                     # Augmente la zone de clic horizontale
            height=1                     # Augmente la zone de clic verticale
        ).pack(side=tk.RIGHT, padx=5, pady=5) # Ajoute du padding autour
        # ⭐ FIN DE LA MODIFICATION TACTILE ⭐

        self._setup_filter_bar()

        # --- ZONE DE SCROLL ---
        self.canvas_frame = tk.Frame(self, bg="#34495e")
        self.canvas_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.canvas = tk.Canvas(self.canvas_frame, bg="#34495e", highlightthickness=0)
        self.vscrollbar = ttk.Scrollbar(
            self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview
        )
        self.scrollable_frame = tk.Frame(self.canvas, bg="#34495e")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.vscrollbar.set)

        self.vscrollbar.pack(side=tk.RIGHT, fill="y")
        self.canvas.pack(side=tk.LEFT, fill="both", expand=True)

        self._setup_drag()
        self.update_content()
        self.after(5000, self._periodic_update)

    def _safe_destroy(self):
        """
        Détruit la fenêtre TotalWidget et réinitialise la référence
        dans l'instance KDSGUI parente.
        """
        # 1. Détruire la fenêtre Toplevel
        self.destroy()
        
        # 2. Réinitialiser la référence dans l'instance KDSGUI
        if hasattr(self.kds_root_instance, 'total_widget'):
            self.kds_root_instance.total_widget = None
            
    def _load_constants_from_db(self):
        """
        Charge toutes les constantes nécessaires depuis la base de données 
        et met à jour les attributs d'instance (self.XXX).
        """
        db = self.konstantes_db

        # --- Chargement des Dictionnaires ---
        self.ITEM_CATEGORY = db.get_dict_constant("ITEM_CATEGORY") or {}
        self.ITEM_SAUCE_MAP = db.get_dict_constant("ITEM_SAUCE_MAP") or {}
        self.KEYWORDS_PATES_SPECIALES = db.get_dict_constant("KEYWORDS_PATES_SPECIALES") or {}
        self.SAUCE_EXCLUSION_SUB_ITEM_MAP = db.get_dict_constant("SAUCE_EXCLUSION_SUB_ITEM_MAP") or {}

        # --- Chargement des Listes ---
        self.USER_PLATS_KEYWORDS_OVERRIDE = db.get_list_constant("USER_PLATS_KEYWORDS_OVERRIDE") or []
        self.DOUBLING_MAIN_ITEM_KEYWORDS = db.get_list_constant("DOUBLING_MAIN_ITEM_KEYWORDS") or []
        self.TOAST_TOTAL_KEYWORDS = db.get_list_constant("TOAST_TOTAL_KEYWORDS") or []
        self.EXCLUSION_KEYWORDS = db.get_list_constant("EXCLUSION_KEYWORDS") or []
        self.INCLUSION_OVERRIDES = db.get_list_constant("INCLUSION_OVERRIDES") or []
        
        # --- Chargement des Couleurs (Simple) ---
        # Utilise l'opérateur 'or' pour conserver la valeur par défaut si la DB ne trouve rien
        self.COLOR_SAUCE = db.get_simple_constant("COLOR_SAUCE") or self.COLOR_SAUCE
        self.COLOR_VINAIGRETTE = db.get_simple_constant("COLOR_VINAIGRETTE") or self.COLOR_VINAIGRETTE
        self.COLOR_SIDE = db.get_simple_constant("COLOR_SIDE") or self.COLOR_SIDE
        self.COLOR_TOAST = db.get_simple_constant("COLOR_TOAST") or self.COLOR_TOAST
        self.COLOR_OEUF = db.get_simple_constant("COLOR_OEUF") or self.COLOR_OEUF
        self.COLOR_PATES = db.get_simple_constant("COLOR_PATES") or self.COLOR_PATES
        self.COLOR_BOISSON = db.get_simple_constant("COLOR_BOISSON") or self.COLOR_BOISSON
        self.COLOR_PLATS = db.get_simple_constant("COLOR_PLATS") or self.COLOR_PLATS
        self.COLOR_MAIN = db.get_simple_constant("COLOR_MAIN") or self.COLOR_MAIN
        self.COLOR_EGG_COOKING = db.get_simple_constant("COLOR_EGG_COOKING") or self.COLOR_EGG_COOKING
        self.COLOR_DEFAULT_FILTER_BG = db.get_simple_constant("COLOR_DEFAULT_FILTER_BG") or self.COLOR_DEFAULT_FILTER_BG
        

    # --- AUTO-MAJ ---
    def _periodic_update(self):
        if self.winfo_exists():
            selected_bill_ids = self.update_callback()
            # Recharge les constantes à chaque update pour refléter les changements sans redémarrer
            self._load_constants_from_db() 
            self.update_content(selected_bill_ids)
            self.after(5000, self._periodic_update)

    # --- BARRE DE FILTRES ---
    def _setup_filter_bar(self):
        filter_bar_container = tk.Frame(self, bg="#2c3e50")
        filter_bar_container.pack(fill="x")

        # Utilisation des couleurs chargées dans self.
        filters = {
            "ALL": {"text": "⭐", "color": self.COLOR_DEFAULT_FILTER_BG, "filter_key": "ALL"},
            "SAUCE": {"text": "🍲", "color": self.COLOR_SAUCE, "filter_key": "SAUCE"},
            "VINAIGRETTE": {"text": " 🥗", "color": self.COLOR_VINAIGRETTE, "filter_key": "VINAIGRETTE"},
            "SIDE": {"text": "🍟", "color": self.COLOR_SIDE, "filter_key": "SIDE"},
            "OEUF_BASE": {"text": "🍳", "color": self.COLOR_OEUF, "filter_key": "OEUF_BASE"},
            "TOAST": {"text": "🍞", "color": self.COLOR_TOAST, "filter_key": "TOAST"},
            "PATES": {"text": "🍝", "color": self.COLOR_PATES, "filter_key": "PATES"},           
            "PLATS": {"text": "🥣", "color": self.COLOR_PLATS, "filter_key": "PLATS"},
        }

        # Répartition sur deux rangées
        filter_values = list(filters.values())
        row1_filters = filter_values[:4]
        row2_filters = filter_values[4:]

        filter_bar_top = tk.Frame(filter_bar_container, bg="#2c3e50")
        filter_bar_top.pack(fill="x", padx=1)
        filter_bar_bottom = tk.Frame(filter_bar_container, bg="#2c3e50")
        filter_bar_bottom.pack(fill="x", padx=1)

        def create_filter_button(parent_frame, filter_data):
            key, icon, color = (
                filter_data["filter_key"],
                filter_data["text"],
                filter_data["color"],
            )
            btn_frame = tk.Frame(parent_frame, bg=color, bd=1, relief="raised")
            btn_frame.pack(side=tk.LEFT, padx=1, pady=2, fill="x", expand=True)
            btn_label = tk.Label(
                btn_frame,
                text=icon,
                font=("Arial", 22),
                fg="white",
                bg=color,
                cursor="hand2",
            )
            btn_label.pack(fill="both", expand=True, padx=2, pady=2)
            btn_label.bind("<Button-1>", lambda event, k=key: self._set_filter(k))

        for f_data in row1_filters:
            create_filter_button(filter_bar_top, f_data)
        for f_data in row2_filters:
            create_filter_button(filter_bar_bottom, f_data)

    def _set_filter(self, filter_key: str):
        self.current_filter = filter_key
        self.update_display_only()

    # --- CLASSIFICATION ---
    def _get_item_category(self, item_name: str) -> tuple[str, str]:
        item_lower = item_name.lower()

        # Utilisation de self.ITEM_CATEGORY et self.COLOR_XXX
        if any(k in item_lower for k in self.ITEM_CATEGORY.get("SAUCE", [])):
            return "SAUCE", self.COLOR_SAUCE
        if any(k in item_lower for k in self.ITEM_CATEGORY.get("VINAIGRETTE", [])):
            return "VINAIGRETTE", self.COLOR_VINAIGRETTE
        if any(k in item_lower for k in self.ITEM_CATEGORY.get("TOAST", [])):
            return "TOAST", self.COLOR_TOAST
        if any(k in item_lower for k in self.ITEM_CATEGORY.get("OEUF_BASE", [])):
            return "OEUF_BASE", self.COLOR_OEUF
        if any(k in item_lower for k in self.ITEM_CATEGORY.get("TOAST_SIDE", [])):
            return "SIDE", self.COLOR_SIDE

        # ⭐ DÉTECTION SPÉCIALE PÂTES COMBINÉES
        for base_pate, modifiers in self.KEYWORDS_PATES_SPECIALES.items():
            base_lower = base_pate.lower()
            if base_lower in item_lower:
                for modifier in modifiers:
                    if modifier.lower() in item_lower:
                        return "PATES", self.COLOR_PATES

        if any(k in item_lower for k in self.ITEM_CATEGORY.get("PATES", [])):
            return "PATES", self.COLOR_PATES
        if any(k in item_lower for k in self.ITEM_CATEGORY.get("BOISSON", [])):
            return "BOISSON", self.COLOR_BOISSON
            
        # ⭐ VÉRIFICATION ROBUSTE POUR PLATS (inclut la liste utilisateur et les constantes)
        all_plats_keywords = set(
            [k.lower() for k in self.ITEM_CATEGORY.get("PLATS", [])]
            + [k.lower() for k in self.USER_PLATS_KEYWORDS_OVERRIDE]
        )
        
        if any(k in item_lower for k in all_plats_keywords):
            return "PLATS", self.COLOR_PLATS
            
        return "MAIN", self.COLOR_MAIN

    # --- NETTOYAGE NOM ---
    def _clean_item_name_for_match(self, item_full_name: str) -> tuple[str, int]:
        # Assurez-vous que 'import re' est présent en haut de votre fichier
        
        # S'assurer que l'entrée est une chaîne
        if not isinstance(item_full_name, str):
             item_full_name = str(item_full_name)

        # ÉTAPE 1: Nettoyer les caractères de contrôle/mise en forme POS et l'espace insécable.
        control_chars_regex = r'[\x00-\x1f\x7f\x90]'
        cleaned_name = re.sub(control_chars_regex, '', item_full_name)
        cleaned_name = cleaned_name.replace('\xa0', ' ').strip()
        
        # NOUVEAU: Conversion de (N) en N (N'IMPORTE OÙ DANS LA CHAÎNE)
        cleaned_name = re.sub(r'\(\s*(\d+)\s*\)', r'\1', cleaned_name)
        
        # Assurer qu'il y a un espace entre le nombre et la lettre si la suppression a collé les deux
        cleaned_name = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', cleaned_name, 1).strip()
        
        if not cleaned_name:
            return "", 0

        quantity = 1
        item_key = cleaned_name
        
        # --- LOGIQUE DE DÉTECTION DE QUANTITÉ (le reste du code) ---

        # Utiliser la version sans le suffixe '(...' pour le reste du nettoyage
        name_without_suffix = cleaned_name.split("(")[0].strip()
        
        parts = name_without_suffix.split(" ", 2)
        
        if len(parts) >= 2 and parts[0].isdigit():
            
            # Cas N x ITEM
            if parts[1].lower() == "x":
                try:
                    quantity = int(parts[0])
                    item_key = parts[2].strip() if len(parts) == 3 else ""
                except ValueError:
                    pass
                
            # Cas N ITEM...
            else:
                try:
                    quantity = int(parts[0])
                    # Le reste de la chaîne est le nom de l'article (e.g., "BR. POULET")
                    item_key = name_without_suffix[len(parts[0]):].strip()
                except ValueError:
                    item_key = name_without_suffix
                    quantity = 1
        else:
            item_key = name_without_suffix
        
        # ÉTAPE FINALE : Nettoyer les espaces résiduels et les suffixes
        item_key = item_key.split(" (")[0].strip()
        
        # Gérer le cas où le retrait de la quantité laisserait une chaîne vide
        if not item_key:
            return cleaned_name.split(" (")[0].strip(), 1

        return item_key, quantity


    # --- EXTRACTION SAUCES ---
    def _extract_and_aggregate_sauces(self, aggregated_items, items_for_sauce_logic):
        # Utilisation de self.ITEM_SAUCE_MAP et self.SAUCE_EXCLUSION_SUB_ITEM_MAP
        lower_case_map = {key.lower(): key for key in self.ITEM_SAUCE_MAP.keys()}
        
        for order in items_for_sauce_logic:
            
            items_for_sauce_check = []
            sub_items_lower_list = [] 
            
            # Déterminer les items à vérifier
            if isinstance(order, dict):
                if 'main_item' in order:
                    items_for_sauce_check.append(order['main_item'])
                
                # Extraire et nettoyer les sous-items pour la vérification
                raw_sub_items = order.get('sub_items', [])
                for raw_sub in raw_sub_items:
                    sub_key, _ = self._clean_item_name_for_match(raw_sub)
                    sub_items_lower_list.append(sub_key.lower()) 
                    
                items_for_sauce_check.extend(raw_sub_items) 
            
            elif isinstance(order, str):
                 items_for_sauce_check.append(order)


            # --- ÉTAPE 1: Déterminer les sauces AUTOMATIQUES pour l'item principal ---
            current_item_sauces = {}
            main_item_full_name = items_for_sauce_check[0] if items_for_sauce_check else ""
            if main_item_full_name:
                item_key, quantity = self._clean_item_name_for_match(main_item_full_name)
                item_name_lower = item_key.lower()

                main_item_match_key = next(
                    (orig for low, orig in lower_case_map.items() if item_name_lower.startswith(low)),
                    None,
                )
                
                if main_item_match_key:
                    current_item_sauces = self.ITEM_SAUCE_MAP[main_item_match_key].copy()
                    
                    # Logique de substitution/exclusion simple (utilise les constantes globales statiques)
                    if "Vinaigrette Chef" in current_item_sauces and KEYWORDS_VINEGRETTE_CESAR.lower() in item_name_lower:
                        current_item_sauces["Vinaigrette César"] = current_item_sauces.pop("Vinaigrette Chef")
                    elif "Vinaigrette César" in current_item_sauces and KEYWORDS_VINEGRETTE_CHEF.lower() in item_name_lower:
                        current_item_sauces["Vinaigrette Chef"] = current_item_sauces.pop("Vinaigrette César")

                    if KEYWORDS_SANS_SALADE.lower() in item_name_lower:
                        current_item_sauces.pop("Vinaigrette Chef", None)
                        current_item_sauces.pop("Vinaigrette César", None)

                    if "sans patate ancienne" in item_name_lower:
                        current_item_sauces.pop("Portion Ancienne", None)
                        
            
            # --- ÉTAPE 2: Gérer l'exclusion par SOUS-ITEM ---
            sauces_to_remove = set()
            # Utilisation de self.SAUCE_EXCLUSION_SUB_ITEM_MAP
            for sauce_name in current_item_sauces.keys():
                
                exclusion_keywords = self.SAUCE_EXCLUSION_SUB_ITEM_MAP.get(sauce_name, [])
                
                for keyword in exclusion_keywords:
                    # Vérifier si un mot-clé d'exclusion est présent dans les sous-items
                    if any(keyword.lower() in sub for sub in sub_items_lower_list):
                        sauces_to_remove.add(sauce_name)
                        print(f"    [EXCLUSION SAUCE] '{sauce_name}' exclu car '{keyword}' trouvé dans les sous-items: {sub_items_lower_list}")
                        break
                        
            for sauce_name in sauces_to_remove:
                current_item_sauces.pop(sauce_name, None)
            

            # --- ÉTAPE 3: Agrégation (seulement des sauces restantes) ---
            for sauce_name, qty in current_item_sauces.items():
                # On utilise la quantité du main_item pour le calcul de l'agrégation
                aggregated_items[sauce_name] = aggregated_items.get(sauce_name, 0) + (qty * quantity) 
                    
        return aggregated_items

    # --- MISE À JOUR DU CONTENU (LOGIQUE UNIFIÉE D'AGRÉGATION) ---
    def update_content(self, selected_bill_ids=None):
        ids_to_fetch = selected_bill_ids if selected_bill_ids else None
        all_pending_orders_raw = self.db_manager.get_all_pending_orders_flat(ids_to_fetch)

        # Assurez-vous que les constantes sont à jour avant de commencer l'analyse
        # (Déjà fait dans _periodic_update, mais bonne pratique en début de fonction principale)
        # self._load_constants_from_db() 

        # --- ÉTAPE D'APLATISSEMENT SUPPLÉMENTAIRE ---
        flattened_orders_raw = []
        for raw_data in all_pending_orders_raw:
            if isinstance(raw_data, dict) and 'items' in raw_data and 'bill_id' in raw_data:
                 flattened_orders_raw.extend(raw_data.get('items', []))
            else:
                flattened_orders_raw.append(raw_data)
                
        all_pending_orders_raw = flattened_orders_raw 
        # --- FIN DE L'ÉTAPE D'APLATISSEMENT ---

        # --- PRINT 1: Raw Orders Info ---
        print("\n==============================================")
        print(f"TotalWidget: Début de l'agrégation pour {len(all_pending_orders_raw)} commandes brutes.")
        
        items_total = {}
        structured_items_for_display = {} 
        orders_for_sauce_extraction = [] 
        self.egg_cooking_totals = {} 
        self.toast_cooking_totals = {} 

        for raw_item_data in all_pending_orders_raw:
            
            main_item_key = None
            quantity = 1
            sub_items = []
            item_dict = None 

            # --- DÉCODAGE/NORMALISATION ---
            if isinstance(raw_item_data, str):
                try:
                    # Tenter de décoder si c'est une chaîne JSON
                    item_dict = json.loads(raw_item_data)
                except (json.JSONDecodeError, TypeError):
                    # Si la chaîne n'est pas du JSON, c'est un article simple
                    item_dict = raw_item_data 
            elif isinstance(raw_item_data, dict):
                item_dict = raw_item_data
            else:
                print(f"[DEBUG DISCARDED] Type inattendu ({type(raw_item_data)}) pour {raw_item_data}")
                continue


            # --- EXTRACTION DES ITEMS PRINCIPAUX ET SECONDAIRES ---
            if isinstance(item_dict, dict) and 'main_item' in item_dict:
                # Cas 1: Item structuré (Main/Sub)
                main_item_full_name = item_dict["main_item"]
                main_item_key, quantity = self._clean_item_name_for_match(main_item_full_name)
                sub_items = item_dict.get("sub_items", [])
                
                orders_for_sauce_extraction.append(item_dict)
                print(f"\n[AGGRÉGATION] Item STRUCTURÉ détecté: {main_item_key} (Qty: {quantity})")
                
            elif isinstance(item_dict, str):
                # Cas 2: Item simple (Chaîne de nom)
                main_item_key, quantity = self._clean_item_name_for_match(item_dict)
                orders_for_sauce_extraction.append(item_dict)
                print(f"\n[AGGRÉGATION] Item SIMPLE détecté: {main_item_key} (Qty: {quantity})")
            
            else:
                print(f"[DEBUG DISCARDED] item_dict est un dictionnaire mais sans 'main_item': {item_dict}")
                continue
                
            if not main_item_key:
                print(f"[DEBUG DISCARDED] item_dict a produit une clé vide et est DISCARDED: {item_dict}")
                continue
                
            # --- VÉRIFICATION DES EXCLUSIONS / INCLUSIONS SUR L'ITEM PRINCIPAL ---
            main_item_lower = main_item_key.lower()
            
            # ÉTAPE 1: VÉRIFICATION DE L'INCLUSION (Utilisation de self.INCLUSION_OVERRIDES)
            is_inclusion_override = any(k.lower() in main_item_lower for k in self.INCLUSION_OVERRIDES)
            
            if is_inclusion_override:
                 print(f"[DEBUG INCLUDED] Item principal inclus (via INCLUSION_OVERRIDES): {main_item_key}")
                 pass
            
            # ÉTAPE 2: VÉRIFICATION DE L'EXCLUSION (Utilisation de self.EXCLUSION_KEYWORDS)
            elif any(k.lower() in main_item_lower for k in self.EXCLUSION_KEYWORDS):
                 print(f"[DEBUG DISCARDED] Item principal exclu (via EXCLUSION_KEYWORDS): {main_item_key}")
                 continue 

            # --- 1. Agrégation du Main Item ---
            items_total[main_item_key] = items_total.get(main_item_key, 0) + quantity
            
            if main_item_key not in structured_items_for_display:
                category, color = self._get_item_category(main_item_key)
                structured_items_for_display[main_item_key] = {
                    'qty': 0, 
                    'color': color, 
                    'category': category, 
                    'subs': {}
                }
            structured_items_for_display[main_item_key]['qty'] += quantity
            
            # --- 2. Agrégation des Sub Items (Uniquement si Cas 1) ---
            
            # --- DÉCLENCHEUR DE DOUBLEMENT (Utilisation de self.DOUBLING_MAIN_ITEM_KEYWORDS) ---
            main_item_for_doubling_check = main_item_key.upper() if main_item_key else ""
            should_apply_doubling = any(k.upper() in main_item_for_doubling_check for k in self.DOUBLING_MAIN_ITEM_KEYWORDS)
            # ---------------------------------
            
            for sub_item_full_name in sub_items:
                sub_item_key, sub_quantity = self._clean_item_name_for_match(sub_item_full_name)
                is_asterisk_sub_item = sub_item_full_name.strip().startswith('*')

                # --- LOGIQUE DE DOUBLEMENT APPLIQUÉE EN PREMIER ICI ---
                if should_apply_doubling and is_asterisk_sub_item:
                    # Multiplie par 2 la quantité du sous-article AVANT l'agrégation
                    sub_quantity *= 2
                    print(f"    [DOUBLÉ] Sous-item {sub_item_key} doublé pour {main_item_key} car commence par '*'. Nouvelle Qty: {sub_quantity}")
                # ----------------------------------------------------------------------

                # *** Application de la quantité de l'item principal ***
                final_sub_quantity_for_aggregation = sub_quantity * quantity 
                print(f"    [AGGRÉGATION QTY] Qty finale pour {sub_item_key} : {final_sub_quantity_for_aggregation}")
                # --------------------------------------------------------------------


                # --- AGRÉGATION SPÉCIFIQUE DES CUISSONS D'ŒUFS (*) ---
                if is_asterisk_sub_item:
                     self.egg_cooking_totals[sub_item_key] = self.egg_cooking_totals.get(sub_item_key, 0) + final_sub_quantity_for_aggregation
                     print(f"    [TOTAL CUISSON] {sub_item_key} ajouté au total des cuissons (Qty finale: {final_sub_quantity_for_aggregation})")
                # -----------------------------------------------------------------------------------------------------------------

                # --- AGRÉGATION SPÉCIFIQUE DES TOASTS/BAGUELS (Utilisation de self.TOAST_TOTAL_KEYWORDS) ---
                toast_name_upper = sub_item_key.upper()
                is_toast_item = any(k in toast_name_upper for k in self.TOAST_TOTAL_KEYWORDS)

                if is_toast_item and sub_quantity > 0:
                     self.toast_cooking_totals[sub_item_key] = self.toast_cooking_totals.get(sub_item_key, 0) + final_sub_quantity_for_aggregation
                     print(f"    [TOTAL TOAST] {sub_item_key} ajouté au total des toasts (Qty: {final_sub_quantity_for_aggregation})")
                # --------------------------------------------------------
                
                # Agrégation pour les totaux (items_total)
                if sub_item_key:
                    items_total[sub_item_key] = items_total.get(sub_item_key, 0) + final_sub_quantity_for_aggregation 
                    
                    # Ajout au sous-item de l'article principal (pour la vue structurée)
                    current_subs = structured_items_for_display[main_item_key]['subs']
                    current_subs[sub_item_key] = current_subs.get(sub_item_key, 0) + final_sub_quantity_for_aggregation 


        # Extraction et agrégation des sauces basées sur orders_for_sauce_extraction
        final_total = self._extract_and_aggregate_sauces(items_total, orders_for_sauce_extraction)
        self.all_aggregated_items = final_total # Agrégation finale pour les filtres
        
        # Mise à jour de la structure d'affichage (quantité finale après sauce)
        for main_name, data in structured_items_for_display.items():
             data['qty'] = final_total.get(main_name, data['qty'])
        self.aggregated_structured_items = structured_items_for_display
        
        # ... (le reste du logging console est inchangé) ...
        
        self.update_display_only(selected_bill_ids, len(self.all_aggregated_items) > 0)

    # --- AFFICHAGE (LIGNES SÉPARÉES ET INDENTÉES) ---
    # --- AFFICHAGE (LIGNES SÉPARÉES ET INDENTÉES) ---
    def update_display_only(self, selected_bill_ids=None, has_content=True):
        
        # ⭐ ÉTAPE 1: SAUVEGARDER LA POSITION ACTUELLE DU SCROLLBAR
        # On peut laisser cette logique, même si la liste sera plus courte.
        self._scroll_position = 0.0
        if self.canvas.yview():
             self._scroll_position = self.canvas.yview()[0] 
        
        # Destruction de l'ancien contenu
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if selected_bill_ids is None:
            selected_bill_ids = self.update_callback()

        if selected_bill_ids:
            title_text = f"Total des {len(selected_bill_ids)} Facture(s) Sélect. (Filtre: {self.current_filter})"
        elif has_content:
            title_text = f"Total de TOUTES les commandes en attente (Filtre: {self.current_filter})"
        else:
            title_text = "Aucune commande en attente."

        tk.Label(
            self.scrollable_frame,
            text=title_text,
            font=("Arial", 12, "italic"),
            fg="#ecf0f1",
            bg="#34495e",
        ).pack(fill="x", pady=5)

        if not self.all_aggregated_items:
            tk.Label(
                self.scrollable_frame,
                text="Rien à faire !",
                font=("Arial", 16),
                fg="#e74c3c",
                bg="#34495e",
            ).pack(fill="x", pady=10)
            return

        # =================================================================
        # 1. AFFICHAGE PRIORITAIRE DES CUISSONS D'ŒUFS
        # =================================================================
        if self.egg_cooking_totals:
            tk.Label(
                self.scrollable_frame,
                text="🍳 TOTAL CUISSONS D'ŒUFS 🍳",
                font=("Arial", 14, "bold"),
                fg=self.COLOR_EGG_COOKING, 
                bg="#2c3e50",
            ).pack(fill="x", pady=(5, 0))

            sorted_egg_totals = sorted(self.egg_cooking_totals.items(), key=lambda item: item[1], reverse=True)
            
            egg_frame = tk.Frame(self.scrollable_frame, bg="#34495e")
            egg_frame.pack(fill="x", pady=(0, 5), padx=5)

            for item_name, total_qty in sorted_egg_totals:
                 
                line_frame = tk.Frame(egg_frame, bg="#34495e")
                line_frame.pack(fill="x", pady=1)

                tk.Label(line_frame, text=f"x{total_qty}", font=("Courier", 16, "bold"),
                         fg=self.COLOR_EGG_COOKING, bg="#34495e", width=4, anchor="w").pack(side=tk.LEFT)
                tk.Label(line_frame, text=item_name, font=("Arial", 15, "bold"),
                         fg=self.COLOR_EGG_COOKING, bg="#34495e", anchor="w").pack(side=tk.LEFT, fill="x", expand=True)

            tk.Frame(self.scrollable_frame, height=2, bg="#546e7a").pack(fill="x", pady=5)

        # =================================================================
        # 2. AFFICHAGE PRIORITAIRE DES TOTAUX DE TOAST (CONDITIONNEL)
        # =================================================================
        if self.toast_cooking_totals: # Changé 'and self.egg_cooking_totals' en simple vérification
            
            color_toast_total = self.COLOR_TOAST 
            
            tk.Label(
                self.scrollable_frame,
                text="🍞 TOTAL TOASTS/BAGUELS 🍞",
                font=("Arial", 14, "bold"),
                fg=color_toast_total,
                bg="#2c3e50",
            ).pack(fill="x", pady=(5, 0))

            sorted_toast_totals = sorted(self.toast_cooking_totals.items(), key=lambda item: item[1], reverse=True)
            
            toast_frame = tk.Frame(self.scrollable_frame, bg="#34495e")
            toast_frame.pack(fill="x", pady=(0, 5), padx=5)

            for item_name, total_qty in sorted_toast_totals:
                 
                line_frame = tk.Frame(toast_frame, bg="#34495e")
                line_frame.pack(fill="x", pady=1)

                tk.Label(line_frame, text=f"x{total_qty}", font=("Courier", 16, "bold"),
                         fg=color_toast_total, bg="#34495e", width=4, anchor="w").pack(side=tk.LEFT)
                tk.Label(line_frame, text=item_name, font=("Arial", 15, "bold"),
                         fg=color_toast_total, bg="#34495e", anchor="w").pack(side=tk.LEFT, fill="x", expand=True)

            tk.Frame(self.scrollable_frame, height=2, bg="#546e7a").pack(fill="x", pady=5)


        # =================================================================
        # 3. AFFICHAGE DE TOUS LES AUTRES ITEMS AGRÉGÉS
        #    (Remplacement de la logique de Groupement Main/Sub Items)
        # =================================================================
            
        processed_keys = set(self.egg_cooking_totals.keys()) 
        processed_keys.update(self.toast_cooking_totals.keys()) 
        
        all_items_to_display = []
        
        # Parcourir TOUS les items agrégés (main items, sub items, sauces, simples)
        for item_name, total_qty in self.all_aggregated_items.items():
            item_lower = item_name.lower()
            
            # Exclusions de base (items de service ou JSON non résolus)
            if "service" in item_lower or item_name.strip().startswith('{'):
                continue
            
            # N'inclure que les items qui ne sont PAS déjà affichés dans les totaux Oeuf/Toast
            if item_name not in processed_keys:
                category, color = self._get_item_category(item_name)
                
                # Appliquer le filtre (ou afficher TOUT)
                if self.current_filter == "ALL" or self.current_filter == category:
                    sort_order = {
                         "SAUCE": 1, "VINAIGRETTE": 2, "SIDE": 3, "TOAST": 4, "OEUF_BASE": 5, "PLATS": 6, "PATES": 7, "BOISSON": 8, "MAIN": 9,
                    }.get(category, 10)
                    all_items_to_display.append((item_name, total_qty, color, sort_order))

        
        # Tri : par catégorie (ordre fixe) puis par quantité (décroissant) puis par nom (croissant)
        sorted_all_items = sorted(all_items_to_display, key=lambda item: (item[3], -item[1], item[0]))

        # Titre pour la section des items agrégés (si nécessaire)
        if sorted_all_items:
             tk.Label(
                self.scrollable_frame,
                text="--- Tous les Items Agrégés (par Catégorie) ---",
                font=("Arial", 10, "italic"),
                fg="#7f8c8d",
                bg="#34495e",
            ).pack(fill="x", pady=5)


        # AFFICHER TOUS LES ITEMS AGRÉGÉS ET FILTRÉS
        for item_name, total_qty, color, _ in sorted_all_items:
            item_frame = tk.Frame(self.scrollable_frame, bg="#34495e")
            item_frame.pack(fill="x", pady=1, padx=5)
            tk.Label(item_frame, text=f"x{total_qty}", font=("Courier", 15, "bold"),
                     fg=color, bg="#34495e", width=4, anchor="w").pack(side=tk.LEFT)
            tk.Label(item_frame, text=item_name, font=("Arial", 13, "bold" if color != self.COLOR_MAIN else ""),
                     fg=color, bg="#34495e", anchor="w").pack(side=tk.LEFT, fill="x", expand=True) 

        self.update_idletasks()
        
        # ⭐ ÉTAPE 2: RESTAURER LA POSITION
        # On restaure la position sauvegardée si elle est > 0.0 
        if self._scroll_position > 0.0:
            self.canvas.yview_moveto(self._scroll_position)

    # --- GLISSEMENT ---
    def _setup_drag(self):
        self.header.bind("<Button-1>", self.start_move)
        self.header.bind("<B1-Motion>", self.do_move)
        self._x = 0
        self._y = 0

    def start_move(self, event):
        self._x = event.x_root - self.winfo_rootx()
        self._y = event.y_root - self.winfo_rooty()

    def do_move(self, event):
        x = event.x_root - self._x
        y = event.y_root - self._y # Correction: utiliser self._y ici
        self.geometry(f"+{x}+{y}")