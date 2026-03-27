# DBKonstantesManager.py (Version Complète avec Importation de keyboard.py)
import sqlite3
import json
import logging
import shutil
import datetime
import os # Ajouté pour les opérations de suppression de fichier
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from tkinter import colorchooser

# >>> IMPORTATION DU CLAVIER VIRTUEL <<<
try:
    from keyboard import VirtualKeyboard # Assurez-vous que keyboard.py est dans le même répertoire
except ImportError:
    messagebox.showerror("Erreur d'Importation", "Impossible d'importer la classe VirtualKeyboard. Assurez-vous que le fichier 'keyboard.py' est présent dans le même répertoire que 'DBKonstantesManager.py'.")
    class VirtualKeyboard: # Fallback pour éviter le plantage
        def __init__(self, master, target_entry_widget, ok_callback): pass
        def destroy(self): pass
# >>> FIN DE L'IMPORTATION <<<


# --- Configuration et Données Initiales (Inchangées) ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

INITIAL_CONSTANTS = {
    "COLOR_SAUCE": "#e74c3c",
    "COLOR_VINAIGRETTE": "#27ae60",
    "COLOR_SIDE": "#3498db",
    "COLOR_TOAST": "#f39c12",
    "COLOR_OEUF": "#e67e22",
    "COLOR_PATES": "#7f8c8d",
    "COLOR_BOISSON": "#9b59b6",
    "COLOR_PLATS": "#A6D40D",
    "COLOR_MAIN": "white",
    "COLOR_DEFAULT_FILTER_BG": "#546e7a",
    "COLOR_EGG_COOKING": "#ff7f50"
}

# Constantes en Listes (Mots-clés)
INITIAL_LIST_CONSTANTS = {
    "DOUBLING_MAIN_ITEM_KEYWORDS": [
        "NO 4 OEUF + VIANDE", "NO 2 OEUF", "LE BRUNCH", "LE QUEBECOIS", 
        "LA FRICASSE VEGE", "FRICASSE FORESTIERE"
    ],
    "TOAST_TOTAL_KEYWORDS": [
        "PAIN BLANC", "PAIN BRUN", "PAIN SEIGLE", "MENAGE BLANC", 
        "MENAGE BRUN", "BAGUEL BLANC", "BAGUEL BRUN", "FRUIT", "TOAST"
    ],
    "USER_PLATS_KEYWORDS_OVERRIDE": [
        'NACHOS GRAT.', 'CLUB', 'CUISSE', 'POITRINE POULET MIDI', 'POITRINE POULET', 
        'THAI', 'FISH N CHIP', 'MIGNON', 'POULET', 'SOLE MEUNIERE', 'SAL CESAR POULET', 
        'HAMBURGER', 'HOT', 'ST-JACQUES', 'SAUTE', 'COTES', 'SOUPE', 'BATONNETS', 
        'SMOKE', 'S-M', 'FETTUCINEE', 'STEAK', 'BURGER'
    ],
    "INCLUSION_OVERRIDES": [
        'DUO PIZZA SAL', 'DUO PIZZA SPAG', 'DUO PIZZA FRITE', 'DUO PATE ET PIZZ' 
    ],
    "EXCLUSION_KEYWORDS": [
        'PIZZA','SERVICE', 'PIZZAS','SMALL', 'PEPE', '1/2','BAMBINO', 'DUO PIZZA','GARNI', 
        'COMBO PIZZA','MINI', 'MEDIUM', 'LARGE', 'XLARGE', 'GARNIE', 'VEGE','COEUR PALMIER', 
        'ANNULATION', 'GRECQUE', 'HAWAÏENNE','VIANDE FUMÉE', 'SUPREME', 'FROMAGE', 
        'PETITE', 'MOYENNE', 'GRANDE', 'MINCE', 'FAMILLE','SPCIAL', 'CROUTE MINCE'
    ]
}

# Constantes en Dictionnaires (Mappages complexes)
INITIAL_DICT_CONSTANTS = {
    "ITEM_CATEGORY": {
        'SAUCE': ['sauce','extra sce bbq','sauce a part', 'mayo', 'ketchup','relish', 'moutarde', 'bbq', 'tartare', 'brune', 'poivre', '2degree'],
        'VINAIGRETTE': ['vinaigrette', 'chef', 'césar', 'italienne', 'thaï', 'balsamique','salade chef'],
        'TOAST_SIDE': ['frites sauce','sauce a part','EXTRA POUTINE DEJ','extra gr creton','combo frite','cornichon','ailes','poutine','pt. poutine italien.','ff', 'Frite Famille','pain grille', 'frites', 'salade de chou', 'riz', 'legumes','patate au four', 'patate pille', 'patate ancienne', 'ancienne','bb. frite sauce','bb. poutine','extra poulet club','pois vert','extra poutine','frites sauce', 'spag', 'duo frite','pilées','oignon francais','extra bacon','extra oignon cuit'],
        'TOAST': ['pas beurre','toast', 'pain blanc', 'pain brun', 'pain menage', 'menage blanc','sand. aux poulet','menage brun', 'gaufre', 'muffin son et raisin', 'pain dore fruit','sand. aux tomates'],
        'OEUF_BASE': ['LE QUEBECOIS', 'NO 4 OEUF + VIANDE', 'fricasse', 'NO 3 OEUF + VIANDE', 'extra cottage','ordre viande', 'ordre crepe','saucisse', 'jambon','oeuf', 'omelette', 'benedictine', 'tourne', 'tourne leger', 'creve','omelette jambon/fromage', 'fricasse vege', 'demi fricasse vege','crepe choco-banane', 'omelette western', 'bene tradi', 'bene saumon','creve bien cuit', 'miroir','ENF. CHOCO BANANE', 'NO 1 OEUF', 'NO 2 OEUF'],
        'PATES': ['spag midi','FETT','viande', 'fett. alfredo','spag','spaghetti', 'lasagne', 'macaroni', 'penne', 'linguine','tagliatelle', 'fettuccine', 'carbonara', 'alfredo'],
        'BOISSON': ['café', 'thé', 'jus', 'lait', 'pepsi', '7up', 'eau', 'chocolat chaud', 'soda', 'latte', 'espresso'],
        'PLATS': ['POITRINE POULET MIDI','chessburger','ragout','CUISSE POULET MIDI', 'POITRINE POULET', 'CUISSE POULET MIDI', 'SAL. THAI CREV. BOUL', 'CROQUETTE POULET', 'DOIGT POULET ENF','DOIGTS POULET MIDI', 'FISH N CHIP MIDI', 'FISH N CHIP', 'BR. F.MIGNON', 'POULET', 'CLUB SANDWICH','bicfteck midi','FILET SOLE MEUNIERE','hambourgeois', 'SAL THAI POUL MIDI', 's-m. maison 12 po','SAL CESAR POULET', 'SAL. THAI POULET', 'hamburger', 'pizza'],
    },
    "KEYWORDS_PATES_SPECIALES": {
        'FETTUCCINE': ['fruits de mer', 'viande', 'alfredo', 'carbonara'],
        'SPAGHETTI': ['fruits de mer', 'viande', 'alfredo', 'carbonara'],
    },
    "ITEM_SAUCE_MAP": {
        "LE QUEBECOIS": {"Petit Patée": 1}, "LE BRUNCH": {"Petite Crêpe": 1},
        "SAL CESAR midi": {"Vinaigrette César": 1}, "BATONNETS MIDI": {"Sauce Spag": 1},
        "BAT. FROMAGE": {"Sauce Spag": 1}, "(6) AILES POULET": {"Sauce 2Degree": 1},
        "FONDU PARMESAN": {"Tartare Fondu": 1}, "ENT. SAL. CESAR": {"Vinaigrette César": 1},
        "ENT. SAL. DU CHEF": {"Vinaigrette Chef": 1}, "ENT. COQ. ST-JACQUES": {"Vinaigrette Chef": 1},
        "SALADE CESAR": {"Vinaigrette César": 1}, "SALADE CHEF": {"Vinaigrette Chef": 1},
        "SPC. FAMILLE": {"Frite Famille": 1}, "POITRINE POULET MIDI": {"Sauce BBq": 1},
        "CUISSE POULET MIDI": {"Sauce BBq": 1}, "DOIGTS POULET MIDI": {"Sauce BBq": 1},
        "DOIGTS POULET": {"Sauce BBq": 1}, "CROQUETTE POULET": {"Sauce BBq": 1},
        "STEAK HACHE MIDI": {"Sauce Brune": 1, "Vinaigrette Chef": 1},
        "STEAK HACHE": {"Sauce Brune": 1, "Vinaigrette Chef": 1},
        "BR. F.MIGNON": {"Vinaigrette Chef": 1, "Portion Ancienne": 1, "Sauce Poivre": 1},
        "BR. POULET": {"Vinaigrette Chef": 1, "Portion Ancienne": 1, "Sauce BBq": 1},
        "F.MIGNON": {"Vinaigrette Chef": 1, "Portion Ancienne": 1, "Sauce BBq": 1},
        "FILET SOLE MEUNIERE": {"Vinaigrette Chef": 1, "Tartare Sole": 1},
        "ASS. CREV. BOUL -BANG": {"Vinaigrette César": 1, "Portion Ancienne": 1},
        "ASS. CREV/LANGOUST.": {"Vinaigrette César": 1, "Portion Ancienne": 1},
        "ASS. CREV. AIL": {"Vinaigrette César": 1, "Portion Ancienne": 1},
        "SAL CHEF MIDI": {"Vinaigrette Chef": 1}, "SAL. CESAR POULET": {"Vinaigrette César": 1},
        "SAL CESAR POULET MIDI": {"Vinaigrette César": 1}, "SAL CHEF POULET MIDI": {"Vinaigrette César": 1},
        "SAL CESAR MIDI": {"Vinaigrette César": 1}, "SAL. THAI POULET": {"Vinaigrette Thai": 1},
        "SAL THAI POULET MIDI": {"Vinaigrette Thai": 1}, "SAL. THAI CREV. BOUL": {"Vinaigrette Thai": 1},
        "FISH N CHIP MIDI": {"Vinaigrette Chef": 1, "Tartare Fish": 1},
        "FISH N CHIPS": {"Vinaigrette Chef": 1, "Tartare Fish": 1},
        "NACHOS GRAT": {"Salsa": 2, "Crème Sure": 2},
        "DUO PIZZA SPAG MIDI": {"Combo Spag": 1}, "DUO PIZZA FRITE MIDI": {"Combo Frite": 1},
        "DUO PIZZA SAL CÉSARAR": {"Vinaigrette César": 1},
    },
    # Mappage pour l'exclusion des sous-items si l'item principal est présent
    "SAUCE_EXCLUSION_SUB_ITEM_MAP": {
        "Combo Spag": ["PATES"], 
        "Combo Frite": ["POUTINE", "FRITE FAMILLE", "FRITES"],
        "Vinaigrette César": ["CHEF", "VINEGRETTE CHEF", "VIN CHEF"],
        "Vinaigrette Chef": ["CESAR", "VINEGRETTE CESAR", "VIN CESAR"],
        "Portion Ancienne": ["SANS PATATE", "POUTINE"],
    }
}


# --- Classe de Gestion de la Base de Données (DBKonstantesManager) ---

class DBKonstantesManager:
    """Gestionnaire de DB pour le code complet et fonctionnel."""
    DB_NAME = 'kdstotal.db'
    
    def __init__(self): 
        self._initialize_db()
        
    def _get_conn(self): 
        return sqlite3.connect(self.DB_NAME)
    
    def _initialize_db(self):
        conn = self._get_conn(); cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS simple_constants (name TEXT PRIMARY KEY, value TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS list_constants (name TEXT PRIMARY KEY, data_json TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS dict_constants (name TEXT PRIMARY KEY, data_json TEXT)")
        self._populate_initial_data(conn); conn.close()
        logger.info("Base de données kdstotal.db initialisée.")

    def _populate_initial_data(self, conn):
        """Popule les données initiales dans la DB. Utilisé pour l'initialisation et le reset."""
        cursor = conn.cursor()
        for name, value in INITIAL_CONSTANTS.items(): cursor.execute("INSERT OR REPLACE INTO simple_constants (name, value) VALUES (?, ?)", (name, value))
        for name, data_list in INITIAL_LIST_CONSTANTS.items(): cursor.execute("INSERT OR REPLACE INTO list_constants (name, data_json) VALUES (?, ?)", (name, json.dumps(data_list)))
        for name, data_dict in INITIAL_DICT_CONSTANTS.items(): cursor.execute("INSERT OR REPLACE INTO dict_constants (name, data_json) VALUES (?, ?)", (name, json.dumps(data_dict)))
        conn.commit()

    # --- NOUVELLES MÉTHODES DE MAINTENANCE ---
    
    def delete_db_file(self):
        """Supprime physiquement le fichier de base de données."""
        if os.path.exists(self.DB_NAME):
            os.remove(self.DB_NAME)
            return True
        return False
    
    def reset_db_to_initial(self):
        """Supprime le fichier et recrée la DB avec les données initiales."""
        try:
            self.delete_db_file()
            self._initialize_db() # Recrée le fichier et le peuple
            return True
        except Exception as e:
            logger.error(f"Erreur lors du reset de la base de données: {e}")
            return False

    # --- ANCIENNES MÉTHODES DE GESTION (INCHANGÉES) ---

    def get_simple_constant(self, name: str) -> str | None:
        conn = self._get_conn(); cursor = conn.cursor(); cursor.execute("SELECT value FROM simple_constants WHERE name = ?", (name,))
        result = cursor.fetchone(); conn.close(); return result[0] if result else None
    
    def get_all_list_names(self) -> list[str]: return list(INITIAL_LIST_CONSTANTS.keys())
    def get_dict_constant_names(self, type_key: str) -> list[str]:
        if type_key == 'keyword': return ["ITEM_CATEGORY", "SAUCE_EXCLUSION_SUB_ITEM_MAP", "KEYWORDS_PATES_SPECIALES"]
        if type_key == 'map': return ["ITEM_SAUCE_MAP"]
        return []
    
    def get_list_constant(self, name: str) -> list:
        conn = self._get_conn(); cursor = conn.cursor(); cursor.execute("SELECT data_json FROM list_constants WHERE name = ?", (name,))
        result = cursor.fetchone(); conn.close(); return json.loads(result[0]) if result else []

    def get_dict_constant(self, name: str) -> dict:
        conn = self._get_conn(); cursor = conn.cursor(); cursor.execute("SELECT data_json FROM dict_constants WHERE name = ?", (name,))
        result = cursor.fetchone(); conn.close(); return json.loads(result[0]) if result else {}

    def update_simple_constant(self, name: str, new_value: str) -> int:
        conn = self._get_conn(); cursor = conn.cursor()
        cursor.execute("UPDATE simple_constants SET value = ? WHERE name = ?", (new_value, name))
        conn.commit(); conn.close(); return cursor.rowcount

    def update_list_constant(self, name: str, new_list: list) -> int:
        conn = self._get_conn(); cursor = conn.cursor()
        data_json = json.dumps(new_list)
        cursor.execute("UPDATE list_constants SET data_json = ? WHERE name = ?", (data_json, name))
        conn.commit(); conn.close(); return cursor.rowcount

    def update_dict_constant(self, name: str, new_dict: dict) -> int:
        conn = self._get_conn(); cursor = conn.cursor()
        data_json = json.dumps(new_dict)
        cursor.execute("INSERT OR REPLACE INTO dict_constants (name, data_json) VALUES (?, ?)", (name, data_json))
        conn.commit(); conn.close(); return cursor.rowcount
    
    # --- MÉTHODES DE SAUVEGARDE/RESTAURATION ---

    def export_db(self, backup_path: str) -> bool:
        """Copie la base de données kdstotal.db vers un chemin de sauvegarde."""
        try:
            shutil.copy2(self.DB_NAME, backup_path)
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'exportation de la base de données: {e}")
            return False

    def import_db(self, source_path: str) -> bool:
        """
        Remplace kdstotal.db par le fichier de sauvegarde et réinitialise les données.
        Ajoute une vérification de l'extension de fichier et de la structure de la DB.
        """
        # 1. Vérification de l'extension de sécurité (EXISTANT)
        if not source_path.lower().endswith('.db'):
            logger.error("Tentative d'importation d'un fichier sans extension .db.")
            messagebox.showerror("Erreur de Fichier", "Le fichier sélectionné n'est pas une base de données '.db' valide.")
            return False
        
        # 2. VÉRIFICATION DE LA STRUCTURE (NOUVEAU)
        if not self._check_db_structure(source_path):
            messagebox.showerror("Erreur de Structure", "Le fichier de base de données sélectionné ne contient pas la structure de tables requise (simple_constants, list_constants, dict_constants). L'importation a été annulée.")
            return False

        try:
            # 3. Tente de copier le fichier (Action risquée, maintenant validée)
            shutil.copy2(source_path, self.DB_NAME)
            
            # 4. Tente de l'initialiser 
            self._initialize_db()
            return True
            
        except shutil.Error as e:
            # Erreur de permission ou de disque
            logger.error(f"Erreur de copie lors de l'importation de la base de données: {e}")
            messagebox.showerror("Erreur de Fichier", "Impossible de copier le fichier. Assurez-vous que l'application KDS principale est fermée et que vous avez les permissions d'écriture.")
            return False
            
        except Exception as e:
            # Erreur générale
            logger.error(f"Erreur lors de l'importation de la base de données: {e}")
            messagebox.showerror("Erreur d'Importation", "Une erreur inconnue est survenue lors du traitement du fichier restauré.")
            return False
    def _check_db_structure(self, filepath: str) -> bool:
        """
        Vérifie si le fichier de base de données à 'filepath' contient les tables requises.
        """
        required_tables = {"simple_constants", "list_constants", "dict_constants"}
        found_tables = set()
        conn = None
        try:
            # Tente de se connecter au fichier d'importation
            conn = sqlite3.connect(filepath)
            cursor = conn.cursor()
            
            # Interroge la table master pour vérifier l'existence des tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            for row in cursor.fetchall():
                found_tables.add(row[0])
            
            # Vérifie si toutes les tables requises sont présentes
            if not required_tables.issubset(found_tables):
                logger.error(f"Tables manquantes dans la base de données importée. Requis: {required_tables}, Trouvé: {found_tables}")
                return False
            
            return True

        except sqlite3.Error as e:
            # Échec de la connexion ou de la requête, le fichier n'est pas une DB valide ou est corrompu
            logger.error(f"Échec de la connexion/lecture du fichier {filepath}. Probablement corrompu ou non-SQLite: {e}")
            return False
            
        finally:
            if conn:
                conn.close()

# --- Classes de Base et Utilitaire ---

class BaseEditor:
    """Classe de base pour les éditeurs."""
    def __init__(self, master, db_manager: DBKonstantesManager, constant_name: str, table_type: str):
        self.master = master
        self.db_manager = db_manager
        self.constant_name = constant_name
        self.table_type = table_type
        self.data = {}
        self.frame = ttk.Frame(master, padding="10")
        self.frame.pack(fill="both", expand=True)

    def load_data(self):
        if self.table_type == 'list':
            self.data = self.db_manager.get_list_constant(self.constant_name)
        elif self.table_type == 'dict':
            self.data = self.db_manager.get_dict_constant(self.constant_name)
    
    def save_data_to_db(self, new_data):
        try:
            if self.table_type == 'list':
                rows = self.db_manager.update_list_constant(self.constant_name, new_data)
            elif self.table_type == 'dict':
                rows = self.db_manager.update_dict_constant(self.constant_name, new_data)
            
            if rows >= 0:
                self.data = new_data
                return True
            else:
                messagebox.showerror("Erreur", "Échec de la mise à jour dans la base de données.")
                return False
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur de sauvegarde: {e}")
            logger.error(f"Erreur de sauvegarde: {e}")
            return False
            
    # --- MÉTHODE CLAVIER VIRTUEL ---
    def _bind_keyboard(self, entry_widget, action_callback=None):
        """Binde un clic à un champ d'entrée pour afficher le clavier virtuel."""
        def open_keyboard(event):
            # Détruire le clavier existant s'il y en a un pour éviter les doublons
            if hasattr(self.master.master, '_virtual_keyboard') and self.master.master._virtual_keyboard is not None:
                 self.master.master._virtual_keyboard.destroy()
            
            # La callback sera exécutée lorsque l'utilisateur appuie sur 'OK (Ajouter)' dans le clavier.
            final_callback = action_callback if action_callback else lambda: None
            
            # Instancie le clavier et stocke la référence dans la classe mère (KonstantesEditorApp)
            self.master.master._virtual_keyboard = VirtualKeyboard(self.master.master, entry_widget, final_callback)
            
        entry_widget.bind("<Button-1>", open_keyboard)

# ----------------------------------------------------------------------
# 1. Éditeur de Constantes Simples (Couleurs)
# ----------------------------------------------------------------------
class SimpleConstantsEditor(BaseEditor):
    def __init__(self, master, db_manager: DBKonstantesManager):
        super().__init__(master, db_manager, "SimpleConstants", 'simple')
        
        self.data = INITIAL_CONSTANTS
        self.vars = {}

        tk.Label(self.frame, text="Édition des Couleurs de Catégories", 
                 font=("Arial", 14, "bold"), fg="#1E90FF").pack(pady=10)
        tk.Label(self.frame, text="Redémarrez l'application KDS pour appliquer les changements de couleur.", 
                 font=("Arial", 10), fg="red").pack(pady=(0, 15))

        canvas = tk.Canvas(self.frame)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollable_frame = ttk.Frame(canvas, padding="5")
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        for name in sorted(self.data.keys()):
            self._create_color_row(scrollable_frame, name)
        
        ttk.Separator(self.frame, orient='horizontal').pack(fill='x', pady=10)
        ttk.Button(self.frame, text="Sauvegarder Toutes les Couleurs", 
                   command=self.save_data, style='Accent.TButton').pack(pady=15)
        
    def _create_color_row(self, master_frame, name):
        """Crée une ligne pour l'édition d'une couleur/constante simple."""
        frame = ttk.Frame(master_frame)
        frame.pack(fill="x", pady=4, padx=5)
        
        tk.Label(frame, text=f"{name}:", font=("Arial", 10, "bold"), width=30, anchor="w").pack(side=tk.LEFT, padx=(0, 10))
        
        initial_value = self.db_manager.get_simple_constant(name) or self.data[name]
        var = tk.StringVar(value=initial_value)
        self.vars[name] = var

        if "COLOR" in name.upper():
            color_canvas = tk.Canvas(frame, width=30, height=20, borderwidth=1, relief="solid")
            color_canvas.pack(side=tk.LEFT, padx=5)

            def update_color_preview(v, canvas):
                try:
                    color = v.get()
                    canvas.config(bg=color) 
                except tk.TclError:
                    canvas.config(bg="red")
            
            var.trace_add("write", lambda n, i, m, v=var, c=color_canvas: update_color_preview(v, c))
            update_color_preview(var, color_canvas)

            entry = tk.Entry(frame, textvariable=var, width=10, justify='center')
            entry.pack(side=tk.LEFT, padx=(0, 5))
            
            ttk.Button(frame, text="Palette", 
                       command=lambda v=var, c=color_canvas: self._choose_color(v, c)).pack(side=tk.LEFT)
        else:
            entry = tk.Entry(frame, textvariable=var, width=20)
            entry.pack(side=tk.LEFT, fill="x", expand=True)
            # Liaison du clavier pour les autres constantes simples
            self._bind_keyboard(entry)

    def _choose_color(self, var, canvas):
        """Ouvre le sélecteur de couleurs."""
        color_code = colorchooser.askcolor(var.get())
        if color_code and color_code[1]:
            var.set(color_code[1])

    def save_data(self):
        """Sauvegarde toutes les constantes simples."""
        updates = 0
        for name, var in self.vars.items():
            new_value = var.get().strip()
            if self.db_manager.update_simple_constant(name, new_value) > 0:
                updates += 1
        
        if updates > 0:
            messagebox.showinfo("Succès", f"{updates} constantes simples mises à jour.")
        else:
            messagebox.showwarning("Avertissement", "Aucune modification à sauvegarder.")

# ----------------------------------------------------------------------
# 2. Éditeur de Liste (ListEditor)
# ----------------------------------------------------------------------

class ListEditorBase(BaseEditor):
    """Classe de base pour les éditeurs de liste/dictionnaire affichant des listes."""
    def __init__(self, master, db_manager, constant_name, table_type='list', title="Éditeur de Liste"):
        super().__init__(master, db_manager, constant_name, table_type)
        self.load_data()
        
        tk.Label(self.frame, text=f"{title} : {self.constant_name}", 
                 font=("Arial", 14, "bold")).pack(pady=10)
        
        self.content_frame = ttk.Frame(self.frame)
        self.content_frame.pack(fill="both", expand=True, pady=5)
        
        self.listbox = None
        self._create_widgets()

    def _create_widgets(self):
        # Colonne de la liste principale
        list_col = ttk.Frame(self.content_frame, padding="10")
        list_col.pack(side=tk.LEFT, fill="both", expand=True)
        
        tk.Label(list_col, text="Éléments Actuels:", font=("Arial", 10, "underline")).pack(pady=(0, 5))

        list_frame = ttk.Frame(list_col)
        list_frame.pack(fill="both", expand=True)
        # CORRECTION DÉFINITIVE: Ajout de exportselection=False
        self.listbox = tk.Listbox(list_frame, height=15, width=50, selectbackground="#1E90FF", selectforeground="white", exportselection=False)
        self.listbox.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)
        
        self.refresh_listbox()

        # Commandes (Ajout/Suppression)
        cmd_frame = ttk.Frame(list_col)
        cmd_frame.pack(pady=10, fill="x")
        
        self.new_item_entry = tk.Entry(cmd_frame)
        self.new_item_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=(0, 5))
        
        # Liaison du clavier virtuel pour l'entrée et l'ajout
        self._bind_keyboard(self.new_item_entry, self.add_item)
        
        ttk.Button(cmd_frame, text="Ajouter", command=self.add_item).pack(side=tk.LEFT, padx=5)
        
        self.listbox.bind('<Double-Button-1>', self.delete_item)
        self.listbox.bind('<Delete>', self.delete_item)
        
        ttk.Button(cmd_frame, text="Supprimer Sélection", command=self.delete_item).pack(side=tk.LEFT)

    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        for item in self.data:
            self.listbox.insert(tk.END, item)

    def add_item(self):
        new_item = self.new_item_entry.get().strip().upper()
        if new_item and new_item not in [k.upper() for k in self.data]:
            self.data.append(new_item)
            self.new_item_entry.delete(0, tk.END)
            if self.save_data_to_db(self.data):
                self.refresh_listbox()
                # Sélectionne le nouvel élément
                new_idx = self.listbox.size() - 1
                self.listbox.selection_set(new_idx)
                self.listbox.activate(new_idx)
        elif new_item:
            messagebox.showwarning("Avertissement", f"'{new_item}' existe déjà ou est vide.")

    def delete_item(self, event=None):
        selection = self.listbox.curselection()
        if selection:
            idx_to_delete = selection[0]
            keyword_to_delete = self.listbox.get(idx_to_delete)
            if messagebox.askyesno("Confirmation", f"Voulez-vous supprimer '{keyword_to_delete}'?"):
                self.data.remove(keyword_to_delete)
                if self.save_data_to_db(self.data):
                    self.refresh_listbox()
                    
                    # Logique de pré-sélection
                    new_len = self.listbox.size()
                    if new_len > 0:
                        new_idx = min(idx_to_delete, new_len - 1)
                        self.listbox.selection_set(new_idx)
                        self.listbox.activate(new_idx)


class ListEditor(ListEditorBase):
    """Éditeur pour les constantes de type LISTE."""
    def __init__(self, master, db_manager, constant_name):
        super().__init__(master, db_manager, constant_name, table_type='list', title="Liste de Mots-clés")


# ----------------------------------------------------------------------
# 3. Éditeur de Dictionnaire Clé -> Liste de Mots-clés
# ----------------------------------------------------------------------

class DictKeywordListEditor(ListEditorBase):
    """Éditeur pour les constantes de type DICT (Clé -> Liste)."""
    def __init__(self, master, db_manager, constant_name):
        # BaseEditor.__init__ sans _create_widgets pour le surcharge
        BaseEditor.__init__(self, master, db_manager, constant_name, 'dict')
        self.load_data()
        
        tk.Label(self.frame, text=f"Dictionnaire (Clé: [Mots-clés]) : {self.constant_name}", 
                 font=("Arial", 14, "bold")).pack(pady=10)
        
        self.content_frame = ttk.Frame(self.frame)
        self.content_frame.pack(fill="both", expand=True, pady=5)
        
        self._setup_key_column()
        self._setup_value_column()

        self.key_listbox.bind("<<ListboxSelect>>", self._load_keywords)
        self.refresh_key_listbox()
        
    def _create_widgets(self):
        pass

    def _setup_key_column(self):
        """Colonne de Gauche: Clés/Catégories."""
        key_frame = ttk.Frame(self.content_frame, padding="10", style='TFrame')
        key_frame.pack(side=tk.LEFT, fill="y")
        tk.Label(key_frame, text="1. Catégories/Clés:", font=("Arial", 10, "underline")).pack(pady=(0, 5))
        
        # Liste des clés
        self.key_listbox = tk.Listbox(key_frame, height=15, width=25, selectbackground="#1E90FF", selectforeground="white", exportselection=False)
        self.key_listbox.pack(fill="y", expand=True)
        
        # Commandes de clé
        entry_frame = ttk.Frame(key_frame)
        entry_frame.pack(pady=10, fill="x")
        self.new_key_entry = tk.Entry(entry_frame)
        self.new_key_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=(0, 5))
        
        # Liaison du clavier virtuel pour l'entrée et l'ajout de clé
        self._bind_keyboard(self.new_key_entry, self._add_key)
        
        ttk.Button(entry_frame, text="Ajouter Clé", command=self._add_key).pack(side=tk.LEFT)
        
        self.key_listbox.bind('<Double-Button-1>', self._delete_key)
        self.key_listbox.bind('<Delete>', self._delete_key)
        
        ttk.Button(key_frame, text="Supprimer Clé Sélectionnée", command=self._delete_key, 
                   style='Danger.TButton').pack(fill="x", pady=5)

    def _setup_value_column(self):
        """Colonne de Droite: Mots-clés (Valeurs)."""
        value_frame = ttk.Frame(self.content_frame, padding="10", style='TFrame')
        value_frame.pack(side=tk.LEFT, fill="both", expand=True, padx=(10, 0))
        tk.Label(value_frame, text="2. Mots-clés de la Clé Sélectionnée:", font=("Arial", 10, "underline")).pack(pady=(0, 5))
        
        # Liste des valeurs (mots-clés)
        self.value_listbox = tk.Listbox(value_frame, height=15, width=40, selectbackground="#1E90FF", selectforeground="white", exportselection=False)
        self.value_listbox.pack(fill="both", expand=True)
        
        # Commandes de valeur
        entry_frame = ttk.Frame(value_frame)
        entry_frame.pack(pady=10, fill="x")
        self.new_value_entry = tk.Entry(entry_frame)
        self.new_value_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=(0, 5))
        
        # Liaison du clavier virtuel pour l'entrée et l'ajout de mot-clé
        self._bind_keyboard(self.new_value_entry, self._add_keyword)
        
        ttk.Button(entry_frame, text="Ajouter Mot-clé", command=self._add_keyword).pack(side=tk.LEFT)
        
        self.value_listbox.bind('<Double-Button-1>', self._delete_keyword)
        self.value_listbox.bind('<Delete>', self._delete_keyword)
        
        ttk.Button(value_frame, text="Supprimer Mot-clé Sélectionné", command=self._delete_keyword).pack(fill="x", pady=5)

    # --- Logique de gestion des Clés ---

    def refresh_key_listbox(self):
        self.key_listbox.delete(0, tk.END)
        for key in sorted(self.data.keys()):
            self.key_listbox.insert(tk.END, key)

    def _add_key(self):
        new_key = self.new_key_entry.get().strip().upper()
        if new_key and new_key not in self.data:
            if self.constant_name == "ITEM_SAUCE_MAP":
                self.data[new_key] = {}
            else:
                self.data[new_key] = []
                
            if self.save_data_to_db(self.data):
                self.new_key_entry.delete(0, tk.END)
                self.refresh_key_listbox()
                # Sélectionne le nouvel élément (la clé)
                new_idx = self.key_listbox.size() - 1
                self.key_listbox.selection_set(new_idx)
                self.key_listbox.activate(new_idx)
                self._load_keywords() # Charge les mots-clés (liste vide)
                
    def _delete_key(self, event=None):
        selection = self.key_listbox.curselection()
        if selection:
            idx_to_delete = selection[0]
            key_to_delete = self.key_listbox.get(idx_to_delete)
            if messagebox.askyesno("Confirmation", f"Voulez-vous supprimer la clé '{key_to_delete}' et ses mots-clés?"):
                del self.data[key_to_delete]
                if self.save_data_to_db(self.data):
                    self.value_listbox.delete(0, tk.END)
                    self.refresh_key_listbox()
                    
                    # Logique de pré-sélection pour la clé
                    new_len = self.key_listbox.size()
                    if new_len > 0:
                        new_idx = min(idx_to_delete, new_len - 1)
                        self.key_listbox.selection_set(new_idx)
                        self.key_listbox.activate(new_idx)
                        self._load_keywords() # Recharger les mots-clés de la nouvelle sélection
                    else:
                        self.value_listbox.delete(0, tk.END) # S'assurer que la liste de droite est vide si la liste de gauche est vide
    
    # --- Logique de gestion des Mots-clés (Valeurs) ---

    def _get_current_key(self):
        selection = self.key_listbox.curselection()
        return self.key_listbox.get(selection[0]) if selection else None

    def _load_keywords(self, event=None):
        """Affiche les mots-clés pour les dictionnaires de type Clé -> Liste (comme ITEM_CATEGORY)."""
        current_key = self._get_current_key()
        self.value_listbox.delete(0, tk.END)
        
        if current_key and current_key in self.data:
            keywords = self.data[current_key]
            
            if isinstance(keywords, list):
                for keyword in keywords:
                    self.value_listbox.insert(tk.END, keyword)
            

    def _add_keyword(self):
        current_key = self._get_current_key()
        keyword = self.new_value_entry.get().strip().upper()
        
        if current_key and keyword:
            if not isinstance(self.data.get(current_key), list):
                self.data[current_key] = []
            
            if keyword not in self.data[current_key]:
                self.data[current_key].append(keyword)
                if self.save_data_to_db(self.data):
                    self.new_value_entry.delete(0, tk.END)
                    self._load_keywords()
                    # Sélectionne le nouvel élément
                    new_idx = self.value_listbox.size() - 1
                    self.value_listbox.selection_set(new_idx)
                    self.value_listbox.activate(new_idx)
            else:
                messagebox.showwarning("Avertissement", f"'{keyword}' existe déjà pour cette clé.")

    def _delete_keyword(self, event=None):
        current_key = self._get_current_key()
        selection = self.value_listbox.curselection()
        
        if current_key and selection:
            idx_to_delete = selection[0]
            keyword_to_delete = self.value_listbox.get(idx_to_delete)
            if messagebox.askyesno("Confirmation", f"Voulez-vous supprimer '{keyword_to_delete}'?"):
                if isinstance(self.data.get(current_key), list) and keyword_to_delete in self.data[current_key]:
                    self.data[current_key].remove(keyword_to_delete)
                    if self.save_data_to_db(self.data):
                        self._load_keywords()
                        
                        # Logique de pré-sélection pour le mot-clé
                        new_len = self.value_listbox.size()
                        if new_len > 0:
                            new_idx = min(idx_to_delete, new_len - 1)
                            self.value_listbox.selection_set(new_idx)
                            self.value_listbox.activate(new_idx)
                else:
                    messagebox.showerror("Erreur", "Type de données incorrect ou mot-clé non trouvé.")


# ----------------------------------------------------------------------
# 4. Éditeur Dict Item/Sauce Mapping (DictItemSauceMapEditor)
# ----------------------------------------------------------------------

class DictItemSauceMapEditor(DictKeywordListEditor):
    """Éditeur spécialisé pour ITEM_SAUCE_MAP (Article Principal -> {Sauce: Qte})."""
    def __init__(self, master, db_manager, constant_name):
        super().__init__(master, db_manager, constant_name)
        tk.Label(self.frame, text="Attention: Le format de valeur est {Sauce: Quantité} pour ce dictionnaire.", 
                 font=("Arial", 10), fg="blue").pack(pady=5)

    def _setup_value_column(self):
        """Colonne de Droite: Mapping Sauce/Quantité."""
        value_frame = ttk.Frame(self.content_frame, padding="10", style='TFrame')
        value_frame.pack(side=tk.LEFT, fill="both", expand=True, padx=(10, 0))
        tk.Label(value_frame, text="2. Sauces Mappées pour l'Article Sélectionné:", font=("Arial", 10, "underline")).pack(pady=(0, 5))
        
        # Liste des valeurs (Sauce: Qte)
        self.value_listbox = tk.Listbox(value_frame, height=15, width=40, selectbackground="#1E90FF", selectforeground="white", exportselection=False)
        self.value_listbox.pack(fill="both", expand=True)
        
        # Commandes de valeur
        cmd_frame = ttk.Frame(value_frame)
        cmd_frame.pack(pady=10, fill="x")

        tk.Label(cmd_frame, text="Sauce:", width=5).pack(side=tk.LEFT)
        self.sauce_entry = tk.Entry(cmd_frame, width=15)
        self.sauce_entry.pack(side=tk.LEFT, padx=5)
        # Liaison du clavier pour la sauce
        self._bind_keyboard(self.sauce_entry)
        
        tk.Label(cmd_frame, text="Qte:", width=3).pack(side=tk.LEFT)
        self.qty_entry = tk.Entry(cmd_frame, width=5)
        self.qty_entry.pack(side=tk.LEFT, padx=5)
        # Liaison du clavier pour la quantité, et exécution de l'action sur 'OK'
        self._bind_keyboard(self.qty_entry, self._add_or_update_map)
        
        ttk.Button(cmd_frame, text="Ajouter/Modifier", command=self._add_or_update_map).pack(side=tk.LEFT)
        
        self.value_listbox.bind('<Double-Button-1>', self._delete_map)
        self.value_listbox.bind('<Delete>', self._delete_map)
        
        ttk.Button(value_frame, text="Supprimer Sauce Sélectionnée", command=self._delete_map).pack(fill="x", pady=5)
        
    def _load_keywords(self, event=None):
        """Affiche les mappings sous forme 'Sauce: Quantité'. (Correction pour s'assurer que c'est un dict)."""
        current_item = self._get_current_key()
        self.value_listbox.delete(0, tk.END)
        if current_item and current_item in self.data:
            mapped_sauces = self.data[current_item]
            
            if not isinstance(mapped_sauces, dict):
                self.data[current_item] = {}
                mapped_sauces = self.data[current_item]

            for sauce, qty in mapped_sauces.items():
                self.value_listbox.insert(tk.END, f"{sauce}: {qty}")

    def _add_or_update_map(self):
        """Ajoute ou modifie un mapping Sauce/Quantité."""
        current_item = self._get_current_key()
        sauce = self.sauce_entry.get().strip().upper()
        qty_str = self.qty_entry.get().strip()
        
        if not current_item: 
            messagebox.showwarning("Avertissement", "Veuillez sélectionner un Article Principal.")
            return
            
        if not sauce or not qty_str: 
            messagebox.showwarning("Avertissement", "Veuillez entrer la Sauce et la Quantité.")
            return

        try:
            qty = int(qty_str)
            if qty < 1: raise ValueError
        except ValueError:
            messagebox.showerror("Erreur", "La quantité doit être un nombre entier positif.")
            return

        if current_item not in self.data or not isinstance(self.data[current_item], dict):
            self.data[current_item] = {}
            
        self.data[current_item][sauce] = qty
        
        if self.save_data_to_db(self.data):
            self.sauce_entry.delete(0, tk.END)
            self.qty_entry.delete(0, tk.END)
            self._load_keywords()
            
            # Tente de trouver l'index de la sauce ajoutée/modifiée pour la présélection
            new_idx = -1
            for i in range(self.value_listbox.size()):
                if self.value_listbox.get(i).startswith(f"{sauce}:"):
                    new_idx = i
                    break
            
            if new_idx != -1:
                self.value_listbox.selection_set(new_idx)
                self.value_listbox.activate(new_idx)

    def _delete_map(self, event=None):
        """Supprime un mapping Sauce/Quantité."""
        current_item = self._get_current_key()
        selection = self.value_listbox.curselection()
        
        if not current_item or not selection:
            return

        idx_to_delete = selection[0]
        map_to_delete = self.value_listbox.get(selection[0])
        sauce_name = map_to_delete.split(':')[0].strip()
        
        if messagebox.askyesno("Confirmation", f"Voulez-vous supprimer le mapping pour la sauce '{sauce_name}'?"):
            if isinstance(self.data.get(current_item), dict) and sauce_name in self.data[current_item]:
                del self.data[current_item][sauce_name]
                if self.save_data_to_db(self.data):
                    self._load_keywords()

                    # Logique de pré-sélection pour le map
                    new_len = self.value_listbox.size()
                    if new_len > 0:
                        new_idx = min(idx_to_delete, new_len - 1)
                        self.value_listbox.selection_set(new_idx)
                        self.value_listbox.activate(new_idx)
            else:
                messagebox.showerror("Erreur", "Erreur lors de la suppression du mapping.")

# ----------------------------------------------------------------------
# 5. Éditeur de Sauvegarde/Restauration (Maintenance Ajoutée)
# ----------------------------------------------------------------------

class BackupRestoreEditor(BaseEditor):
    def __init__(self, master, db_manager: DBKonstantesManager):
        super().__init__(master, db_manager, "Backup/Restore", 'simple')
        
        tk.Label(self.frame, text="⚙️ Gestion des Sauvegardes et Restauration", 
                 font=("Arial", 14, "bold"), fg="#1E90FF").pack(pady=20)
        
        tk.Label(self.frame, text=f"Fichier de Base de Données Principal: {db_manager.DB_NAME}").pack(pady=5)
        
        self._setup_export_import_section()
        self._setup_maintenance_section()

    def _setup_export_import_section(self):
        """Section standard d'exportation et d'importation."""
        ttk.Separator(self.frame, orient='horizontal').pack(fill='x', pady=10, padx=50)

        # Section Exportation
        export_frame = ttk.Frame(self.frame, padding="15", relief=tk.RIDGE)
        export_frame.pack(pady=15, padx=50, fill='x')
        tk.Label(export_frame, text="Exporter la Base de Données (Sauvegarde)", 
                 font=("Arial", 12, "underline")).pack(pady=5)
        
        tk.Label(export_frame, text=f"Crée une copie du fichier '{self.db_manager.DB_NAME}' à l'emplacement choisi.").pack()
        ttk.Button(export_frame, text="💾 Exporter / Sauvegarder", command=self._export_db_dialog, 
                   style='Accent.TButton').pack(pady=10, ipadx=20)

        # Section Importation
        import_frame = ttk.Frame(self.frame, padding="15", relief=tk.RIDGE)
        import_frame.pack(pady=15, padx=50, fill='x')
        tk.Label(import_frame, text="Importer / Restaurer la Base de Données", 
                 font=("Arial", 12, "underline")).pack(pady=5)
        
        tk.Label(import_frame, text=f"ATTENTION: Ceci Remplacera le fichier '{self.db_manager.DB_NAME}' actuel. \nAssurez-vous que l'application KDS principale est fermée.", 
                 fg='red', font=("Arial", 10, "bold")).pack()
        ttk.Button(import_frame, text="📤 Importer / Restaurer", command=self._import_db_dialog, 
                   style='Danger.TButton').pack(pady=10, ipadx=20)
                   
    def _export_db_dialog(self):
        """Ouvre la boîte de dialogue pour l'exportation."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"kdstotal_backup_{timestamp}.db"
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".db",
            initialfile=default_filename,
            filetypes=[("SQLite Database files", "*.db"), ("Tous les fichiers", "*.*")],
            title="Sélectionnez l'emplacement de sauvegarde"
        )
        
        if filepath:
            if self.db_manager.export_db(filepath):
                messagebox.showinfo("Succès de l'Exportation", f"Base de données sauvegardée avec succès à:\n{filepath}")
            else:
                messagebox.showerror("Erreur de Sauvegarde", "Échec de l'exportation. Vérifiez les permissions.")

    

    def _import_db_dialog(self):
        """Ouvre la boîte de dialogue pour l'importation."""
        filepath = filedialog.askopenfilename(
            defaultextension=".db",
            # Ajout du filtre pour ne montrer que les fichiers .db
            filetypes=[("Base de données SQLite", "*.db"), ("Tous les fichiers", "*.*")], 
            title="Sélectionnez le fichier de base de données à restaurer"
        )
        
        if filepath:
            if messagebox.askyesno("Confirmation de Restauration", 
                                   "Êtes-vous SÛR de vouloir remplacer la base de données actuelle par ce fichier?\nCETTE ACTION EST IRRÉVERSIBLE. \n\nContinuer?"):
                # Aucune modification nécessaire ici, car la vérification est faite dans db_manager.import_db(filepath)
                if self.db_manager.import_db(filepath):
                    messagebox.showinfo("Succès de la Restauration", "Base de données restaurée avec succès.\nLes changements seront effectifs au prochain redémarrage.")
    # --- NOUVELLE SECTION DE MAINTENANCE ---
    
    def _setup_maintenance_section(self):
        """Ajoute la section des opérations de maintenance (DANGER)."""
        ttk.Separator(self.frame, orient='horizontal').pack(fill='x', pady=10, padx=50)
        
        danger_frame = ttk.Frame(self.frame, padding="15", relief=tk.RIDGE)
        danger_frame.pack(pady=15, padx=50, fill='x')
        tk.Label(danger_frame, text="⚠️ Opérations de Maintenance (DANGER)", 
                 font=("Arial", 12, "bold"), fg='red').pack(pady=5)
        
        tk.Label(danger_frame, text="Ces actions sont extrêmes et nécessitent un redémarrage de l'application KDS pour être complètement effectives.", 
                 font=("Arial", 9, "italic"), fg='red').pack(pady=5)
                 
        # Bouton Réinitialiser
        ttk.Button(danger_frame, text="🔄 Réinitialiser la DB (Valeurs Initiales)", 
                   command=self._reset_db_dialog, style='Danger.TButton').pack(pady=5, ipadx=10, fill='x')
        
        # Bouton Supprimer
        ttk.Button(danger_frame, text="💣 Supprimer le Fichier DB (Perte de TOUTES les données)", 
                   command=self._delete_db_dialog, style='Danger.TButton').pack(pady=5, ipadx=10, fill='x')

    def _reset_db_dialog(self):
        """Réinitialise la base de données aux valeurs initiales."""
        if messagebox.askyesno("Confirmation de Réinitialisation", 
                               "Êtes-vous SÛR de vouloir réinitialiser la base de données aux valeurs par défaut?\nCETTE ACTION EST IRRÉVERSIBLE. Continuer?"):
            if self.db_manager.reset_db_to_initial():
                messagebox.showinfo("Succès de la Réinitialisation", 
                                    "Base de données réinitialisée aux constantes initiales.\nVeuillez redémarrer l'application pour recharger les données.")
            else:
                messagebox.showerror("Erreur", "Échec de la réinitialisation de la base de données.")

    def _delete_db_dialog(self):
        """Supprime physiquement le fichier de base de données."""
        if messagebox.askyesno("Confirmation de Suppression", 
                               "⚠️ ATTENTION: Voulez-vous VRAIMENT supprimer le fichier de base de données?\nCette opération supprimera TOUTES les données personnalisées. CONTINUER?"):
            if self.db_manager.delete_db_file():
                messagebox.showinfo("Succès de la Suppression", 
                                    "Fichier de base de données supprimé avec succès.\nL'application va se fermer. Veuillez la redémarrer pour la recréer vide.")
                self.master.master.destroy() # Fermer l'application principale
            else:
                messagebox.showerror("Erreur", "Échec de la suppression du fichier de base de données.")


# ----------------------------------------------------------------------
# 6. Application Principale (KonstantesEditorApp)
# ----------------------------------------------------------------------

class KonstantesEditorApp:
    """Application principale utilisant ttk.Notebook pour les éditeurs spécialisés."""
    def __init__(self, master, db_manager: DBKonstantesManager):
        self.master = master
        self.db_manager = db_manager
        self.master.title("KDS Constantes Editor Avancé (Tactile)")
        self.master.geometry("1000x900")

        # Initialise un attribut pour stocker la référence au clavier virtuel (pour le fermer au besoin)
        self._virtual_keyboard = None 

        # --- Style ---
        style = ttk.Style(master)
        style.configure('Danger.TButton', foreground='white', background='#e74c3c', font=('Arial', 10, 'bold'))
        style.map('Danger.TButton', background=[('active', '#c0392b')]) # Amélioration visuelle du bouton danger
        style.configure('Accent.TButton', foreground='white', background='#1E90FF', font=('Arial', 10, 'bold'))
        style.map('Accent.TButton', background=[('active', '#3498db')])

        # Initialisation du Notebook (Système d'onglets)
        self.notebook = ttk.Notebook(master)
        self.notebook.pack(pady=10, padx=10, fill="both", expand=True)

        self._setup_simple_constants_editor()
        self._setup_list_editor()
        self._setup_dict_keyword_list_editor()
        self._setup_item_sauce_map_editor()
        self._setup_backup_restore_editor()

    def _setup_simple_constants_editor(self):
        simple_frame = ttk.Frame(self.notebook, padding="10", style='TFrame')
        self.notebook.add(simple_frame, text="🎨 Couleurs")
        SimpleConstantsEditor(simple_frame, self.db_manager)

    def _setup_list_editor(self):
        list_frame = ttk.Frame(self.notebook, padding="10", style='TFrame')
        self.notebook.add(list_frame, text="📝 Listes (Mots-clés)")
        
        list_names = self.db_manager.get_all_list_names()
        self.list_name_var = tk.StringVar(list_frame, value=list_names[0] if list_names else "")
        
        select_frame = ttk.Frame(list_frame)
        select_frame.pack(fill='x', pady=5)
        ttk.Label(select_frame, text="Liste à ÉDITER:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.list_combobox = ttk.Combobox(select_frame, textvariable=self.list_name_var, values=list_names, state="readonly", width=50)
        self.list_combobox.pack(side=tk.LEFT, fill='x', expand=True, padx=5)
        self.list_combobox.bind("<<ComboboxSelected>>", self._load_selected_list_editor)

        self.current_list_editor_frame = ttk.Frame(list_frame)
        self.current_list_editor_frame.pack(fill="both", expand=True)
        self._load_selected_list_editor()

    def _load_selected_list_editor(self, event=None):
        for widget in self.current_list_editor_frame.winfo_children():
            widget.destroy()
        selected_name = self.list_name_var.get()
        if selected_name:
            ListEditor(self.current_list_editor_frame, self.db_manager, selected_name)

    def _setup_dict_keyword_list_editor(self):
        dict_frame = ttk.Frame(self.notebook, padding="10", style='TFrame')
        self.notebook.add(dict_frame, text="🔑 Catégories (Clé: [Liste])")

        dict_names = self.db_manager.get_dict_constant_names('keyword')
        self.dict_name_var = tk.StringVar(dict_frame, value=dict_names[0] if dict_names else "")
        
        select_frame = ttk.Frame(dict_frame)
        select_frame.pack(fill='x', pady=5)
        ttk.Label(select_frame, text="Dictionnaire à ÉDITER:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.dict_combobox = ttk.Combobox(select_frame, textvariable=self.dict_name_var, values=dict_names, state="readonly", width=50)
        self.dict_combobox.pack(side=tk.LEFT, fill='x', expand=True, padx=5)
        self.dict_combobox.bind("<<ComboboxSelected>>", self._load_selected_dict_editor)

        self.current_dict_editor_frame = ttk.Frame(dict_frame)
        self.current_dict_editor_frame.pack(fill="both", expand=True)
        self._load_selected_dict_editor()

    def _load_selected_dict_editor(self, event=None):
        for widget in self.current_dict_editor_frame.winfo_children():
            widget.destroy()
        selected_name = self.dict_name_var.get()
        if selected_name:
            DictKeywordListEditor(self.current_dict_editor_frame, self.db_manager, selected_name)

    def _setup_item_sauce_map_editor(self):
        map_frame = ttk.Frame(self.notebook, padding="10", style='TFrame')
        self.notebook.add(map_frame, text="🗺️ ITEM_SAUCE_MAP")
        
        DictItemSauceMapEditor(map_frame, self.db_manager, "ITEM_SAUCE_MAP")

    def _setup_backup_restore_editor(self):
        backup_frame = ttk.Frame(self.notebook, padding="10", style='TFrame')
        self.notebook.add(backup_frame, text="💾 Sauvegarde / Restauration")
        BackupRestoreEditor(backup_frame, self.db_manager)


if __name__ == '__main__':
    db_manager = DBKonstantesManager()
    root = tk.Tk()
    app = KonstantesEditorApp(root, db_manager)
    root.mainloop()