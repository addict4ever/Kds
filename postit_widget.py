# postit_widget.py (Début du fichier MODIFIÉ)

import tkinter as tk
import logging
from datetime import datetime
import json
import os
from serial_reader import SerialReader # Laissez commenté ou retirez si non utilisé dans ce module

# --- CORRECTION DU BLOC D'IMPORTATION DE TTK ---
from tkinter import ttk, messagebox
from keyboardModifier import VirtualKeyboard

import re


# -----------------------------------------------
# 🎯 Fichier de configuration global
CONFIG_FILE = 'config_gui.json'

MAX_ITEM_DISPLAY_HEIGHT = 300 # Hauteur maximale en pixels pour l'affichage des items avant troncature
CONFIRM_BG = '#34495e'
BUTTON_COLOR = '#2ecc71'
BUTTON_COLOR_YES = '#2ecc71'
BUTTON_COLOR_NO = '#e74c3c'
SUB_ITEM_POLICE = 13
MAIN_ITEM_POLICE = 12

def _load_config() -> dict:
    """
    Charge la configuration depuis config_gui.json. 
    Toutes les clés lues remplacent les valeurs par défaut définies ci-dessous.
    NOTE: Cette fonction est globale (pas de 'self').
    """
    
    # 1. Définition COMPLÈTE de la configuration par défaut
    config = {
        "STATUS_COLORS": {
            "En attente": "#3498db", 
            "En cours": "#f1c40f", 
            "Traitée": "#2ecc71", 
            "Annulée": "#e74c3c", 
            "Archivée": "#7f8c8d"
        },
        "CARD_WIDTH": 300,
        "CARD_PADDING": 5,
        "SUB_ITEM_POLICE": 14,
        "MAIN_ITEM_POLICE": 15,
        "BG_MAIN": "#2c3e50",
        "COLOR_TEXT": "#ecf0f1",
        "CARD_BG": "#34495e",
        "COLOR_NOTE": "#f1c40f",
        "MAX_CARDS_PER_ROW": 5, 
        "SCROLL_PAGE_SIZE": 1,
        
    }
    
    # 2. Vérification de l'existence du fichier
    if not os.path.exists(CONFIG_FILE): # Utilisation de la variable globale CONFIG_FILE
        print(f"Avertissement: Fichier de configuration '{CONFIG_FILE}' introuvable. Utilisation des valeurs par défaut complètes.")
        return config # Retourne les valeurs par défaut complètes

    # 3. Tentative de chargement et fusion
    try:
        with open(CONFIG_FILE, 'r') as f:
            config_data = json.load(f)
            
        # Écrase les valeurs par défaut avec celles lues dans le fichier JSON
        config.update(config_data) 
        
        print(f"Configuration chargée depuis {CONFIG_FILE}. Les constantes KDS ont été mises à jour.")
        return config
        
    except json.JSONDecodeError:
        messagebox.showerror("Erreur de Configuration", f"Fichier '{CONFIG_FILE}' mal formaté (JSON invalide). Utilisation des valeurs par défaut.")
        return config
    except Exception as e:
        messagebox.showerror("Erreur de Configuration", f"Échec de la lecture de '{CONFIG_FILE}'. Utilisation des valeurs par défaut. Détail: {e}")
        return config

# 🚀 APPEL CRITIQUE: Déclaration de la variable globale qui contient toute la configuration
KDS_CONFIG = _load_config() 

# ----------------------------------------------------------------------------------
# OPTIONNEL: Si vous souhaitez déclarer chaque constante individuellement pour l'ancien code:
# Cela n'est pas nécessaire si vous utilisez KDS_CONFIG['CLE'] partout.

STATUS_COLORS = KDS_CONFIG['STATUS_COLORS']
CARD_WIDTH = KDS_CONFIG['CARD_WIDTH']
CARD_PADDING = KDS_CONFIG['CARD_PADDING']
BG_MAIN = KDS_CONFIG['BG_MAIN']
COLOR_TEXT = KDS_CONFIG['COLOR_TEXT']
CARD_BG = KDS_CONFIG['CARD_BG']
COLOR_NOTE = KDS_CONFIG['COLOR_NOTE']
MAX_CARDS_PER_ROW = KDS_CONFIG['MAX_CARDS_PER_ROW']
SCROLL_PAGE_SIZE = KDS_CONFIG['SCROLL_PAGE_SIZE']
SUB_ITEM_POLICE = KDS_CONFIG['SUB_ITEM_POLICE']
MAIN_ITEM_POLICE = KDS_CONFIG['MAIN_ITEM_POLICE']

# ----------------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# --- Classe OrderPostIt (Contient le contenu formaté pour l'affichage) ---
# -------------------------------------------------------------------------

class ActionConfirmationDialog(tk.Toplevel):
    """
    Fenêtre personnalisée générique pour confirmer une action (Fusion, Échange, etc.).
    """
    def __init__(self, master, title: str, message: str, yes_text: str):
        super().__init__(master)
        
        self.result = False 
        
        self.title(title)
        self.geometry("500x200")
        self.config(bg=CONFIRM_BG)
        self.resizable(False, False)
        
        self.transient(master)
        self.grab_set() 
        
        # Titre
        tk.Label(self, text=title, 
                 font=('Segoe UI', 16, 'bold'), 
                 fg='white', bg=CONFIRM_BG).pack(pady=(15, 5))
        
        # Message de confirmation détaillé (utilise le message passé en argument)
        tk.Label(self, text=message, 
                 font=('Segoe UI', 10), 
                 fg='#ecf0f1', bg=CONFIRM_BG, justify=tk.CENTER).pack(pady=(5, 15))
                 
        # --- Zone des Boutons ---
        button_frame = tk.Frame(self, bg=CONFIRM_BG)
        button_frame.pack(pady=5)
        
        # Bouton OUI (Confirmer)
        tk.Button(button_frame, text=yes_text, command=self._on_yes, 
                  font=('Segoe UI', 12, 'bold'), bg=BUTTON_COLOR_YES, fg='white', 
                  activebackground=BUTTON_COLOR_YES, activeforeground='white',
                  width=15, relief=tk.FLAT).pack(side=tk.LEFT, padx=10)
                  
        # Bouton NON (Annuler)
        tk.Button(button_frame, text="Non, Annuler", command=self._on_no, 
                  font=('Segoe UI', 12), bg=BUTTON_COLOR_NO, fg='white', 
                  activebackground='#c0392b', activeforeground='white',
                  width=15, relief=tk.FLAT).pack(side=tk.LEFT, padx=10)
        
        self.protocol("WM_DELETE_WINDOW", self._on_no) 
        self.wait_window(self)

    def _on_yes(self):
        self.result = True
        self.destroy()

    def _on_no(self):
        self.result = False
        self.destroy()

class MergeConfirmationDialog(tk.Toplevel):
    """
    Fenêtre personnalisée pour confirmer la fusion de deux factures.
    """
    def __init__(self, master, p1, p2):
        super().__init__(master)
        
        # Le résultat sera stocké ici (True pour Oui, False pour Non)
        self.result = False 
        
        self.title("Confirmation de Fusion de Factures")
        self.geometry("500x200")
        self.config(bg=CONFIRM_BG)
        self.resizable(False, False)
        
        # Rendre cette fenêtre modale (bloque l'interaction avec le parent)
        self.transient(master)
        self.grab_set() 

        # --- Contenu de la fenêtre ---
        
        # Titre
        tk.Label(self, text="⚠️ Confirmer la Fusion ⚠️", 
                 font=('Segoe UI', 16, 'bold'), 
                 fg='white', bg=CONFIRM_BG).pack(pady=(15, 5))
        
        # Message de confirmation détaillé
       
                 
        # --- Zone des Boutons ---
        button_frame = tk.Frame(self, bg=CONFIRM_BG)
        button_frame.pack(pady=5)
        
        # Bouton OUI (Confirmer)
        tk.Button(button_frame, text="Oui, Fusionner", command=self._on_yes, 
                  font=('Segoe UI', 12, 'bold'), bg=BUTTON_COLOR, fg='white', 
                  activebackground=BUTTON_COLOR, activeforeground='white',
                  width=15, relief=tk.FLAT).pack(side=tk.LEFT, padx=10)
                  
        # Bouton NON (Annuler)
        tk.Button(button_frame, text="Non, Annuler", command=self._on_no, 
                  font=('Segoe UI', 12), bg='#e74c3c', fg='white', 
                  activebackground='#c0392b', activeforeground='white',
                  width=15, relief=tk.FLAT).pack(side=tk.LEFT, padx=10)
        
        # Attendre que la fenêtre soit fermée
        self.protocol("WM_DELETE_WINDOW", self._on_no) # Gère la fermeture par la croix
        self.wait_window(self)

    def _on_yes(self):
        """Action pour le bouton Oui."""
        self.result = True
        self.destroy()

    def _on_no(self):
        """Action pour le bouton Non (ou fermeture par la croix)."""
        self.result = False
        self.destroy()

class OrderPostIt(tk.Frame): # Assurez-vous d'avoir (tk.Frame) ici!
    """Représente une carte de commande individuelle (Post-it)."""
    
    def __init__(self, master_selector, order_data: dict, db_manager, 
                 service_types: list, kds_gui_instance, **kwargs):

        # 1. Initialisation du cadre (Frame) parent
        super().__init__(master_selector, bg=BG_MAIN, **kwargs) 

        self.kds_params = _load_config()
        self.master_selector = master_selector
        self.order_data = order_data
        self.db_manager = db_manager
        self.service_types = service_types
        self.kds_gui_instance = kds_gui_instance
        
        # Statut de vue et de clignotement
        self.is_viewed = (self.order_data['status'] != 'En attente') 
        self.flash_state = True 
        self.flash_after_id = None
        self.auto_close_timer = None

        # Callbacks pour les actions
        self.status_callback = self._handle_status_change
        self.delete_callback = self._handle_delete_order
        
        self.bill_id = order_data['bill_id']
        self.display_ticket_content = "" 
        self.status = order_data['status']
        self.service_type = order_data.get('service_type', 'Standard')

        # Gestion des annulations regroupées
        if self.service_type == 'ANNULATION':
            self.service_type = 'COMMANDE' 
        if self.service_type == 'LIVRAISON':
            self.service_type = 'COMMANDE' 
        if self.service_type == 'LIVREUR':
            self.service_type = 'COMMANDE' 
        if self.service_type == 'POUR EMPORTER':
            self.service_type = 'COMMANDE' 
        
        self.column_frame = self.master_selector.get_column_frame(self.service_type)

        # Conversion de la date
        try:
            self.creation_date = datetime.fromisoformat(order_data['creation_date'])
        except (ValueError, KeyError):
            self.creation_date = datetime.now()
        
        # Gestion des items et ratures
        self.item_widgets_map = {}
        self.is_overstrike_map = {} 
        self.main_item_names = {}
        
        # Sélection et appui long
        self.is_selected = False
        self.long_press_id = None
        
        # --- CRÉATION VISUELLE ---
        self._create_widgets()
        self.master_selector.add_postit(self, self.service_type)
        
        # Démarrer le clignotement si nouveau
        #if not self.is_viewed and self.status == 'En attente':
        #    self._start_flashing()

        # ==========================================================
        # ⭐ LOGIQUE D'AUTO-FERMETURE DYNAMIQUE (Depuis JSON)
        # ==========================================================
        
        # 1. Charger les tailles depuis fermeture_auto.json
        pizza_sizes_upper = []
        config_file = "fermeture_auto.json"
        
        try:
            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                    pizza_sizes_upper = [str(s).upper() for s in config_data.get("pizza_sizes", [])]
            else:
                pizza_sizes_upper = ['BAMBINO', 'MINI', 'SMALL', 'MEDIUM', 'LARGE', 'XLARGE', 'DESSERT JOUR MIDI']
        except Exception as e:
            pizza_sizes_upper = ['BAMBINO', 'MINI', 'SMALL', 'MEDIUM', 'LARGE', 'XLARGE']

        items = order_data.get('items', [])
        table_number = str(order_data.get('table_number', '')).strip()
        
        should_auto_close = False
        close_reason = ""

        # --- NOUVELLE CONDITION : Table 999 (LIVREUR) ---
        #if table_number == "999":
        #    should_auto_close = True
        #    close_reason = "LIVREUR (Table 999)"

        # --- CONDITION EXISTANTE : 1 seul item avec mot-clé ---
        if len(items) == 1:
            try:
                item_data = items[0]
                if isinstance(item_data, str):
                    item_data = json.loads(item_data)
                
                nom_item_upper = str(item_data.get('main_item', '')).upper()
                match = next((t for t in pizza_sizes_upper if t in nom_item_upper), None)

                if match:
                    should_auto_close = True
                    close_reason = f"Item unique avec mot-clé '{match}'"
            except Exception as e:
                logger.error(f"[DEBUG] Erreur lors de l'analyse de l'item unique : {e}")

        # --- DÉCLENCHEMENT DU MINUTEUR SI UNE CONDITION EST REMPLIE ---
        if should_auto_close:
            
            def safe_auto_close():
                if self.winfo_exists():
                    self._handle_status_change(self.bill_id, 'Traitée')
                else:
                    logger.info(f"[DEBUG] Pas d'auto-fermeture pour #{self.bill_id} (Table: {table_number}, Items: {len(items)})")
            self.after(60000, safe_auto_close)
        else:
            logger.info(f"[DEBUG] Pas d'auto-fermeture pour #{self.bill_id} (Table: {table_number}, Items: {len(items)})")
            
    def _strike_all_items(self, event=None):
        """Raye absolument tous les items et sous-items du ticket."""
        for item_idx, widgets in self.item_widgets_map.items():
            # Raye l'item principal
            main_label = widgets.get('main_item_label')
            if main_label and main_label.winfo_exists():
                size = MAIN_ITEM_POLICE if '15' in str(main_label.cget("font")) else SUB_ITEM_POLICE
                main_label.config(font=('Segoe UI', size, 'overstrike'))
            
            # Raye les sous-items
            for sub_label in widgets.get('sub_item_labels', []):
                if sub_label and sub_label.winfo_exists():
                    sub_label.config(font=('Segoe UI', SUB_ITEM_POLICE, 'overstrike'))
        
        # Notifier la fenêtre serveur et vérifier l'auto-fermeture
        self._notify_serveur_window()

    def _unstrike_all_items(self, event=None):
        """Retire la rature de tous les items et sous-items du ticket."""
        for item_idx, widgets in self.item_widgets_map.items():
            main_label = widgets.get('main_item_label')
            if main_label and main_label.winfo_exists():
                size = MAIN_ITEM_POLICE if '15' in str(main_label.cget("font")) else SUB_ITEM_POLICE
                main_label.config(font=('Segoe UI', size, 'bold'))
            
            for sub_label in widgets.get('sub_item_labels', []):
                if sub_label and sub_label.winfo_exists():
                    sub_label.config(font=('Segoe UI', SUB_ITEM_POLICE, 'bold'))
        
        self._notify_serveur_window()

    def _toggle_strike_all_items(self, event=None):
        """
        Bascule l'état de rature pour TOUS les items.
        Si tout est déjà rayé -> on retire tout.
        Sinon -> on raye tout.
        """
        # 1. Vérifier l'état actuel : est-ce que TOUT est déjà rayé ?
        all_already_struck = True
        for widgets in self.item_widgets_map.values():
            main_label = widgets.get('main_item_label')
            if main_label and main_label.winfo_exists():
                if "overstrike" not in str(main_label.cget("font")).lower():
                    all_already_struck = False
                    break
        
        # 2. Déterminer le nouvel état
        # Si tout est rayé, on veut remettre en 'bold'. Sinon, on met en 'overstrike'.
        new_state = "bold" if all_already_struck else "overstrike"
        
        # 3. Appliquer le changement à tous les labels
        for widgets in self.item_widgets_map.values():
            # Item principal
            ml = widgets.get('main_item_label')
            if ml and ml.winfo_exists():
                size = MAIN_ITEM_POLICE if '15' in str(ml.cget("font")) else SUB_ITEM_POLICE
                ml.config(font=('Segoe UI', size, new_state))
            
            # Sous-items
            for sl in widgets.get('sub_item_labels', []):
                if sl and sl.winfo_exists():
                    sl.config(font=('Segoe UI', SUB_ITEM_POLICE, new_state))
        
        # 4. Notifier le système (pour la fenêtre serveur et le timer de fermeture)
        self._notify_serveur_window()

    def _handle_status_change(self, bill_id, new_status: str):
        """Met à jour le statut dans la DB et retire ou met à jour le post-it."""
        # 1. On arrête le clignotement dès qu'on touche à la carte
        self._stop_flashing() 
        
        # 2. Désélection si nécessaire
        if getattr(self, 'is_selected', False):
            self._toggle_selection() 

        
        # 3. Mise à jour dans la BDD
        rows_affected = self.db_manager.set_order_status_by_bill_id(bill_id, new_status)
        
        if rows_affected > 0:
            # 4. ROUTAGE LOGIQUE
            if new_status in ('Traitée', 'Annulée', 'Archivée'):
                # Si le statut est final, on supprime direct (pas besoin d'update visuel)
                self.master_selector.remove_postit(self) 
            else:
                # On ne met à jour le visuel que pour les statuts intermédiaires (ex: "En cours")
                self.order_data['status'] = new_status
        else:
            messagebox.showerror("Erreur de Statut", f"Impossible de mettre à jour la facture {bill_id}.")

    def _handle_delete_order(self, bill_id):
        """Supprime définitivement une commande de l'interface (simulé pour l'instant)."""
        
        if self.status not in ('Traitée', 'Annulée'):
            messagebox.showwarning("Suppression Impossible", "La suppression définitive ne peut se faire que sur les commandes 'Traitée' ou 'Annulée' (Corbeille).")
            return

        if messagebox.askyesno("Confirmation de Suppression", 
                               f"Êtes-vous sûr de vouloir supprimer DÉFINITIVEMENT la facture {bill_id} ?"):
            # Ici, il faudrait idéalement appeler une fonction unitaire de suppression 
            # et d'archivage dans DBManager, mais nous simulerons la suppression visuelle.
            self.master_selector.remove_postit(self)

    def _handle_print(self):
        """Affiche un menu pour choisir l'imprimante avant d'imprimer."""
        content_to_print = self.display_ticket_content 
        
        if not content_to_print or not isinstance(content_to_print, str):
            messagebox.showwarning("Impression", "Contenu introuvable.")
            return

        # Création d'une petite fenêtre de dialogue pour le choix
        print_win = tk.Toplevel(self)
        
        # SUPPRESSION DU X ET DE LA BARRE DE TITRE
        print_win.overrideredirect(True) 
        print_win.resizable(False, False)
        
        # Dimensions et Centrage
        width, height = 300, 320
        screen_width = print_win.winfo_screenwidth()
        screen_height = print_win.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        print_win.geometry(f"{width}x{height}+{x}+{y}")
        
        # Style de la fenêtre
        print_win.config(bg="#34495e", highlightbackground="white", highlightthickness=2)
        print_win.grab_set() 

        tk.Label(print_win, text="CHOIX DE L'IMPRIMANTE", 
                 font=('Arial', 12, 'bold'), bg="#34495e", fg="white", pady=15).pack()

        # Fonction interne pour lancer l'impression
        def send_to(p_index):
            # Import local pour éviter les problèmes de dépendances circulaires
            from serial_reader import SerialReader, SERIAL_PORT_PRINTER, SERIAL_PORT_PRINTER_2, SERIAL_PORT_PRINTER_3
            
            ports = [SERIAL_PORT_PRINTER, SERIAL_PORT_PRINTER_2, SERIAL_PORT_PRINTER_3]
            selected_port = ports[p_index-1]
            
            # APPEL STATIQUE DIRECT (Pas besoin de self.serial_reader)
            # La logique TCP pour le port 3 est maintenant à l'intérieur de cette fonction
            success = SerialReader.reprint_ticket_to_printer(content_to_print, selected_port)
            
            if success:
                print_win.destroy()
            else:
                messagebox.showerror("Erreur", f"Échec de l'impression sur Imprimante {p_index}")

        # --- Boutons de sélection ---
        tk.Button(print_win, text="Imprimante 1 (Cuisine)", font=('Arial', 10, 'bold'),
                  height=2, width=22, bg="#2ecc71", fg="white", activebackground="#27ae60",
                  command=lambda: send_to(1)).pack(pady=5)
                  
        tk.Button(print_win, text="Imprimante 2 (Livraison Caisse)", font=('Arial', 10, 'bold'),
                  height=2, width=22, bg="#3498db", fg="white", activebackground="#2980b9",
                  command=lambda: send_to(2)).pack(pady=5)
                  
        tk.Button(print_win, text="Imprimante 3 (Livraison Pa TCP)", font=('Arial', 10, 'bold'),
                  height=2, width=22, bg="#9b59b6", fg="white", activebackground="#8e44ad",
                  command=lambda: send_to(3)).pack(pady=5)
        
        # Bouton Annuler
        tk.Button(print_win, text="ANNULER", font=('Arial', 10),
                  height=1, width=15, bg="#95a5a6", fg="white",
                  command=print_win.destroy).pack(pady=20)
    
    # ⭐ MODIFIÉ: SÉPARATION (SPLIT) - Utilisation de la logique de distribution des items
    def _handle_split_order(self):
        self._stop_flashing()
        if self.is_selected:
            self._toggle_selection() 
            
        if not messagebox.askyesno("Confirmer Séparation", 
                                f"Voulez-vous séparer la facture {self.bill_id} ?"):
            return

        original_data = self.order_data
        items_json_strings = original_data['items']
        
        # 1. Décodage des items
        decoded_items = []
        for item_json_string in items_json_strings:
            try:
                item = item_json_string if isinstance(item_json_string, dict) else json.loads(item_json_string)
                decoded_items.append(item)
            except (json.JSONDecodeError, TypeError):
                continue

        if len(decoded_items) < 2:
            messagebox.showwarning("Séparation Impossible", "Pas assez d'items.")
            return

        split_point = len(decoded_items) // 2
        items_1 = decoded_items[:split_point]
        items_2 = decoded_items[split_point:]
        
        try:
            # 2. Création des nouvelles factures (Ceci marque aussi l'originale comme 'Traitée')
            new_bill_id_1 = self.db_manager.create_new_order_from_split(original_data, items_1, suffixe='-A') 
            new_bill_id_2 = self.db_manager.create_new_order_from_split(original_data, items_2, suffixe='-B') 
            
            # 3. MISE À JOUR IMMÉDIATE DE L'INTERFACE
            # Au lieu d'attendre le cycle auto, on force le rafraîchissement via le parent
            if hasattr(self.master_selector, 'refresh_display'):
                self.master_selector.refresh_display()
            else:
                # Si refresh_display n'est pas accessible, on retire au moins la carte actuelle
                self.master_selector.remove_postit(self) 
                

        except Exception as e:
            messagebox.critical("Erreur DB", f"La séparation a échoué : {e}")

    def _toggle_single_strike(self, label_widget):
        """Bascule la rature uniquement sur le widget cliqué."""
        if self.is_selected:
            self._toggle_selection()

        current_font = label_widget.cget("font")
        size = '15' if '15' in str(current_font) else SUB_ITEM_POLICE
        
        if "overstrike" in str(current_font):
            label_widget.config(font=('Segoe UI', size, 'bold'))
        else:
            label_widget.config(font=('Segoe UI', size, 'overstrike'))
        
        # Correction ici aussi
        self._notify_serveur_window()

    def _toggle_single_widget_strike(self, label_widget):
        """
        Bascule l'état de rature sur un widget spécifique (Label).
        """
        current_font = label_widget.cget("font")
        # On vérifie si 'overstrike' est déjà présent dans la police
        if "overstrike" in current_font:
            # On retire la rature (on remet en gras par défaut ici)
            new_font = ('Segoe UI', '15' if '15' in current_font else SUB_ITEM_POLICE, 'bold')
        else:
            # On ajoute la rature
            new_font = ('Segoe UI', '15' if '15' in current_font else SUB_ITEM_POLICE, 'overstrike')
        
        label_widget.config(font=new_font)
        self._notify_serveur_window()


    # ⭐ AJOUTER CELLE-CI IMMÉDIATEMENT APRÈS DANS LA CLASSE OrderPostIt
    def _notify_serveur_window(self):
        """Prépare les données raturées avec gestion du timer d'annulation."""
        if hasattr(self, 'kds_gui_instance') and self.kds_gui_instance.serveur_window:
            items_with_status = []
            total_elements = 0
            struck_elements = 0
            
            # ... (votre boucle for existante pour compter les items reste la même) ...
            for item_idx, widgets in self.item_widgets_map.items():
                # (Vérification plat principal)
                main_label = widgets.get('main_item_label')
                if main_label:
                    font_info = str(main_label.cget("font")).lower()
                    is_raye = "overstrike" in font_info
                    items_with_status.append({"text": main_label.cget("text"), "is_raye": is_raye})
                    total_elements += 1
                    if is_raye: struck_elements += 1
                
                # (Vérification sous-items)
                for sub_label in widgets.get('sub_item_labels', []):
                    sub_font_info = str(sub_label.cget("font")).lower()
                    is_raye_sub = "overstrike" in sub_font_info
                    items_with_status.append({"text": sub_label.cget("text"), "is_raye": is_raye_sub})
                    total_elements += 1
                    if is_raye_sub: struck_elements += 1

            # Mise à jour de la fenêtre serveur
            self.kds_gui_instance.serveur_window.update_table(
                self.bill_id, self.order_data.get('table_number', '??'), 
                items_with_status, self.order_data.get('serveuse_name', '')
            )

            # --- GESTION DU TIMER ---
            
            # 1. On annule TOUJOURS le timer existant s'il y en a un
            if self.auto_close_timer:
                self.after_cancel(self.auto_close_timer)
                self.auto_close_timer = None

            # 2. Si tout est rayé, on lance (ou relance) le chrono de 4 minutes
            if total_elements > 0 and struck_elements == total_elements:
                # On stocke l'ID du timer pour pouvoir l'annuler plus tard
                self.auto_close_timer = self.after(600000, self._check_and_close_if_still_struck)
                
    def _check_and_close_if_still_struck(self):
        """Vérifie une dernière fois si tout est raturé avant de fermer."""
        try:
            # 1. Vérification de sécurité de base
            if not self.winfo_exists():
                return

            still_fully_struck = True
            
            # 2. On vérifie si tout est encore raturé
            for widgets in self.item_widgets_map.values():
                ml = widgets.get('main_item_label')
                # On ajoute un try interne pour chaque label au cas où
                try:
                    if ml and ml.winfo_exists():
                        font_info = str(ml.cget("font")).lower()
                        if "overstrike" not in font_info:
                            still_fully_struck = False
                            break
                    
                    for sl in widgets.get('sub_item_labels', []):
                        if sl and sl.winfo_exists():
                            sub_font_info = str(sl.cget("font")).lower()
                            if "overstrike" not in sub_font_info:
                                still_fully_struck = False
                                break
                except Exception:
                    # Si un label pose problème, on considère que la vérification échoue par sécurité
                    still_fully_struck = False
                    break
            
            # 3. Fermeture effective
            if still_fully_struck:
                print(f"DEBUG: Fermeture automatique EFFECTIVE de #{self.bill_id}")
                
                # IMPORTANT: On s'assure que la commande n'est pas déjà fermée
                if hasattr(self, '_handle_status_change'):
                    self._handle_status_change(self.bill_id, 'Traitée')
            else:
                print(f"DEBUG: Fermeture ANNULEE pour #{self.bill_id} (modifié ou introuvable)")
                
        except Exception as e:
            # Évite que le crash ne bloque l'interface
            print(f"DEBUG: Erreur lors de l'auto-fermeture (ignorée) : {e}")


    # ⭐ NOUVEAU: GESTION DE LA SÉLECTION (Longue pression)
    def _start_long_press(self, event):
        """Démarre le timer de 300ms pour la longue pression."""
        # Annuler la pression s'il y en a déjà une en cours (par sécurité)
        self._cancel_long_press(None)
        
        # Arrête le clignotement dès le premier appui
        self._stop_flashing() 
        
        # Démarre le timer de 300ms (1 demi seconde)
        self.long_press_id = self.postit_frame.after(300, self._perform_selection)

    def _cancel_long_press(self, event):
        """Annule le timer de longue pression si le bouton est relâché trop tôt."""
        if self.long_press_id:
            self.postit_frame.after_cancel(self.long_press_id)
            self.long_press_id = None
            
    def _perform_selection(self):
        """Exécuté si la pression a duré 1 seconde (timer écoulé)."""
        self.long_press_id = None # Réinitialiser l'ID après exécution
        self._toggle_selection()

    def _toggle_selection(self):
        """Change l'état de sélection et met à jour le style visuel (bordure bleue)."""
        self.is_selected = not self.is_selected
        
        if self.is_selected:
            # Cadre bleu (highlightthickness=4) pour la sélection
            self.postit_frame.config(highlightthickness=4, highlightbackground='#3498db') # Bleu vif
        else:
            # Retirer le cadre de sélection
            self.postit_frame.config(highlightthickness=0)

        # Notifier le PostitSelector de la nécessité de mettre à jour la liste totale (pour TotalWidget)
        self.master_selector.notify_selection_change()
    # --- FIN NOUVELLES MÉTHODES ---


    def _start_flashing(self):
        """Démarre le clignotement du cadre du Post-it."""
        # On initialise l'état si nécessaire
        if not hasattr(self, 'flash_state'):
            self.flash_state = False
        
        # On lance le premier cycle
        self.flash_after_id = self.after(500, self._flash_border)

    def _flash_border(self):
        """Change la couleur alternativement, mais S'ARRÊTE si le statut change."""
        
        # 🛑 SÉCURITÉ : Si on a cliqué sur "En cours", on arrête tout de suite !
        if self.status != "En attente":
            self._stop_flashing() # On s'assure que c'est jaune fixe
            return

        # Vérification si le widget existe encore pour éviter l'erreur "invalid command name"
        if not hasattr(self, 'border_frame') or not self.border_frame.winfo_exists():
            return

        try:
            # Couleurs de base
            current_color = self.kds_params.get("STATUS_COLORS", {}).get(self.status, "#3498db")
            flash_color = '#e74c3c' # Rouge vif
            
            # Logique de sélection vs clignotement
            if self.is_selected:
                new_color = current_color # Bleu de sélection prioritaire
            else:
                new_color = flash_color if self.flash_state else current_color
            
            # Application de la couleur au cadre
            self.border_frame.config(bg=new_color)
            
            # Inversion de l'état pour le prochain coup
            self.flash_state = not self.flash_state 
            
            # On replanifie le prochain flash (On garde l'ID dans flash_after_id)
            self.flash_after_id = self.after(500, self._flash_border)
            
        except (tk.TclError, AttributeError):
            pass

    def _stop_flashing(self):
        """Arrête proprement le cycle de flash et fige la couleur jaune."""
        # 1. Annulation du timer (On coupe le moteur du flash)
        if hasattr(self, 'flash_after_id') and self.flash_after_id:
            try:
                self.after_cancel(self.flash_after_id)
            except:
                pass
            self.flash_after_id = None
        
        # 2. On vérifie si les widgets existent toujours avant de configurer
        if not hasattr(self, 'border_frame') or not self.border_frame.winfo_exists():
            return 

        try:
            # On récupère la couleur associée au statut actuel (ex: Jaune pour 'En cours')
            colors = self.kds_params.get("STATUS_COLORS", {})
            target_color = colors.get(self.status, "#f1c40f")

            # Application au cadre extérieur
            self.border_frame.config(bg=target_color)

            # Application au fond du Canvas
            if hasattr(self, 'config_canvas') and self.config_canvas.winfo_exists():
                self.config_canvas.itemconfig(self.bg_rect, fill=target_color)
                
            # Mise à jour du label de statut (Texte noir sur jaune pour lisibilité)
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                self.status_label.config(text=self.status, bg=target_color)
                if self.status == "En cours":
                    self.status_label.config(fg="black")
                    
        except (tk.TclError, AttributeError):
            pass

    def _create_widgets(self):
        """Crée tous les widgets de la carte et construit le contenu du ticket formaté pour l'affichage."""
        
        ticket_display_str = ""
        
        
        # Détermination de la couleur du texte selon le numéro de table
        table_num = str(self.order_data['table_number']).upper()
        if table_num == "LIV":
            header_color = "yellow"
        elif table_num == "PA":
            header_color = "green"
        elif table_num == "999":
            header_color = "orange"
        elif table_num == "888":
            header_color = "red"
        else:
            header_color = COLOR_TEXT  # Couleur par défaut
        
        # ⭐ MODIFIÉ: Utilisation de highlightthickness pour la bordure de sélection.
        self.postit_frame = tk.Frame(self.column_frame, bg=CARD_BG, padx=CARD_PADDING, pady=CARD_PADDING, bd=0, 
                                        width=CARD_WIDTH, highlightthickness=0, highlightbackground=CARD_BG)
        
        self.border_frame = tk.Frame(self.postit_frame, bg=STATUS_COLORS.get(self.status, BG_MAIN), bd=0)
        self.border_frame.pack(fill=tk.BOTH, expand=True)
        self.content_frame = tk.Frame(self.border_frame, bg=CARD_BG, padx=10, pady=5)
        self.content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        header_text = f"T: {self.order_data['table_number']} | {self.order_data['serveuse_name']}"
        time_text = self.creation_date.strftime("%H:%M:%S")

        header_frame = tk.Frame(self.content_frame, bg=CARD_BG)
        header_frame.pack(fill=tk.X)

        ticket_display_str += header_text + "\n"
        ticket_display_str += f"Heure: {time_text}\n"

        # On utilise ici header_color au lieu de COLOR_TEXT
        self.header_label = tk.Label(header_frame, text=header_text,
                                        font=('Segoe UI', 18, 'bold'), fg=header_color, bg=CARD_BG)
        self.header_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # LIAISON DE LA LONGUE PRESSION (inchangé)
        widgets_to_bind = [
            self.postit_frame, 
            self.border_frame, 
            self.content_frame,
            self.header_label,
            header_frame
        ]
        
        for widget in widgets_to_bind:
            widget.bind("<ButtonPress-1>", self._start_long_press)
            widget.bind("<ButtonRelease-1>", self._cancel_long_press) 
        
        # Récupération de la note (inchangé)
        note_content = self.db_manager.get_bill_note(self.bill_id)
        
        if note_content:
            self.note_label = tk.Label(self.content_frame, 
                                        text=f"Note: {note_content}",
                                        font=('Segoe UI', 15, 'italic'), fg='black', bg=COLOR_NOTE, wraplength=CARD_WIDTH - 20, justify=tk.LEFT, anchor='w')
            self.note_label.pack(fill=tk.X, pady=5)
            ticket_display_str += f"Note: {note_content}\n"
        
        ttk.Separator(self.content_frame, orient='horizontal').pack(fill='x', pady=5)
        ticket_display_str += "-------------------------------\n"
        
        # --- Items Détaillés (Liste) ---
        items_frame = tk.Frame(self.content_frame, bg=CARD_BG)
        items_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame temporaire pour simuler et mesurer la hauteur totale des items
        temp_item_frame = tk.Frame(items_frame, bg=CARD_BG) 
        
        full_ticket_items_content = "" # Pour l'impression complète
        
        # Vider le map de widgets avant de recréer
        self.item_widgets_map = {}
        self.main_item_names = {}
        
        # 1. Création et mesure de TOUS les items dans la frame temporaire
        # 1. Création et mesure de TOUS les items dans la frame temporaire
        for item_index, item_json_str in enumerate(self.order_data['items']):
            try:
                item_data = json.loads(item_json_str)
            except json.JSONDecodeError:
                item_data = {'main_item': 'ERREUR: JSON Invalide', 'sub_items': []}

            item_name = item_data.get('main_item', 'Item Inconnu')

            self.main_item_names[item_index] = item_name

            # ⭐ CORRECTION ICI : GESTION DU SÉPARATEUR
            if item_data.get('is_separator', False):
                sep_text = item_data.get('main_item', "-- FUSION --")
                
                # Création du label du séparateur dans la frame temporaire pour le calcul de hauteur
                tk.Label(temp_item_frame, 
                        text=sep_text,
                        font=('Segoe UI', 9, 'bold'),
                        bg='#7f8c8d', # Gris foncé
                        fg='white', 
                        anchor='center',
                        pady=4,
                        relief=tk.FLAT).pack(fill='x', pady=(5, 5))
                
                full_ticket_items_content += f"\n--- {sep_text} ---\n"
                continue # Passer à l'élément suivant (pas un item raturable)
                
            # --- Item régulier (raturable) ---
            
            # Préparer la structure pour le main item
            self.item_widgets_map[item_index] = {
                'main_item_label': None,
                'sub_item_labels': []
            }
            
            # ⭐ TAILLE DE POLICE PRINCIPALE: 15
            # Déterminer la couleur : Bleu si '*' est présent, sinon COLOR_TEXT
            # On définit d'abord le texte en majuscules pour une détection fiable
            main_text = item_data['main_item'].upper()

            # --- LOGIQUE DE COULEUR MODIFIÉE ---
            # On vérifie si c'est une ligne de modification manuelle pour mettre en ROUGE
            if any(key in main_text for key in ["HEURE:", "EXTRAS:", "NOTE:", "ENLEVER LE PAPIER JAUNE"]):
                item_fg = "#e74c3c"  # Code couleur Rouge (Flat UI)
            elif "*" in main_text:
                item_fg = "#3498db"  # Bleu pour les items modifiés standards
            else:
                item_fg = COLOR_TEXT # Couleur par défaut (souvent blanc ou gris très clair)

            main_item_label = tk.Label(temp_item_frame, 
                                        text=item_data['main_item'], 
                                        font=('Segoe UI', MAIN_ITEM_POLICE, 'bold'), 
                                        fg=item_fg, 
                                        bg=CARD_BG, 
                                        anchor='w', 
                                        justify=tk.LEFT)
            main_item_label.pack(fill=tk.X, padx=5)

            # 🌟 LIER LE CLIC AU TOGGLE RATURE
            main_item_label.bind("<Button-1>", lambda e, w=main_item_label: self._toggle_single_strike(w))

            # Stocker le widget
            self.item_widgets_map[item_index]['main_item_label'] = main_item_label

            full_ticket_items_content += f"{item_data['main_item']}\n"

            for sub_item in item_data.get('sub_items', []):
                # 1. Nettoyage et mise en majuscules pour la comparaison
                sub_upper = sub_item.upper()

                # Rose : Cuissons
                mots_rose = ["BROUILLE", "TOURNE BC", "TOURNE", "MIRROIR", "MIROIR", "*", "DONNER"]
                
                # Brun Pâle : Pains
                mots_brun = ["MENAGE BLANC", "MENAGE BRUN", "BRUN", "BLANC", "BAGUEL BLANC", "BAGUEL BRUN", "BAGEUL" , "PAIN"]

                # --- LOGIQUE DE COULEUR ---
                if any(mot in sub_upper for mot in mots_rose):
                    sub_fg = "#FF1493"  # Rose
                elif any(mot in sub_upper for mot in mots_brun):
                    sub_fg = "#D2B48C"  # Brun pâle (Tan)
                else:
                    sub_fg = COLOR_TEXT  # Couleur par défaut

                # 3. Création du Label
                sub_item_label = tk.Label(
                    temp_item_frame, 
                    text=f"→ {sub_item}", 
                    font=('Segoe UI', SUB_ITEM_POLICE, 'bold'), 
                    fg=sub_fg, 
                    bg=CARD_BG, 
                    anchor='w', 
                    justify=tk.LEFT
                )
                sub_item_label.pack(fill=tk.X, padx=15)
                
                # Sauvegarde la couleur pour ne pas la perdre quand on raye l'item
                sub_item_label.original_fg = sub_fg
                
                # Lier le clic pour rayer
                sub_item_label.bind("<Button-1>", lambda e, w=sub_item_label: self._toggle_single_strike(w))
                
                self.item_widgets_map[item_index]['sub_item_labels'].append(sub_item_label)
                full_ticket_items_content += f"  → {sub_item}\n"
        
        # 2. Forcer le calcul de la géométrie pour obtenir la hauteur réelle
        temp_item_frame.update_idletasks()
        
        # 3. Vérification de la hauteur (Hauteur maximale arbitraire, ici 300px)
        
        if temp_item_frame.winfo_height() > MAX_ITEM_DISPLAY_HEIGHT:
            # Logique de troncature
            temp_item_frame.destroy() 
            self.item_widgets_map = {} 
            
            visible_item_count = 0 
            
            for i, item_json_str in enumerate(self.order_data['items']):
                
                try:
                    item_data = json.loads(item_json_str)
                except json.JSONDecodeError:
                    item_data = {'main_item': 'ERREUR: JSON Invalide', 'sub_items': []}

                # ⭐ CORRECTION ICI : GESTION DU SÉPARATEUR (s'affiche toujours)
                if item_data.get('is_separator', False):
                    sep_text = item_data.get('main_item', "--- SÉPARATION COMMANDE ---")
                    tk.Label(items_frame, 
                            text=sep_text,
                            font=('Segoe UI', 9, 'bold'),
                            bg='#7f8c8d', 
                            fg='white', 
                            anchor='center',
                            pady=4,
                            relief=tk.FLAT).pack(fill='x', pady=(5, 5))
                    continue # Ne pas incrémenter visible_item_count

                # --- Gestion de la Troncature des Items Réguliers ---
                if visible_item_count >= 3:
                    tk.Label(items_frame, text="... et plus", font=('Segoe UI', 9), fg='#7f8c8d', bg=CARD_BG, anchor='w').pack(fill=tk.X, padx=5)
                    break
                    
                self.is_overstrike_map[i] = False
                self.item_widgets_map[i] = {'main_item_label': None, 'sub_item_labels': []}

                # Version avec un beau bleu pâle moderne
                item_fg = "#3498db" if "*" in item_data['main_item'] else COLOR_TEXT

                main_item_label = tk.Label(items_frame, text=item_data['main_item'], 
                                            font=('Segoe UI', MAIN_ITEM_POLICE, 'bold'), 
                                            fg=item_fg, bg=CARD_BG, anchor='w', justify=tk.LEFT)
                main_item_label.pack(fill=tk.X, padx=5)
                # 🌟 LIER LE CLIC AU TOGGLE RATURE
                sub_item_label.bind("<Button-1>", lambda e, w=sub_item_label: self._toggle_single_widget_strike(w))
                self.item_widgets_map[i]['main_item_label'] = main_item_label
                
                for sub_item in item_data.get('sub_items', []):
                    # ⭐ DÉTERMINATION DE LA COULEUR DU SOUS-ITEM
                    # Jaune pâle (#FFFACD) si '*' est présent, sinon couleur normale
                    sub_fg = "#FFB6C1" if "*" in sub_item else COLOR_TEXT

                    # Recréation des labels (Sub Item)
                    sub_item_label = tk.Label(items_frame, 
                                            text=f"→ {sub_item}", 
                                            font=('Segoe UI', SUB_ITEM_POLICE, 'bold'), 
                                            fg=sub_fg,  # <--- Utilisation de la couleur calculée
                                            bg=CARD_BG, 
                                            anchor='w', 
                                            justify=tk.LEFT)
                    sub_item_label.pack(fill=tk.X, padx=15)

                    # 🌟 LIER LE CLIC AU TOGGLE RATURE
                    sub_item_label.bind("<Button-1>", lambda e, idx=i: self._toggle_overstrike(idx))
                    self.item_widgets_map[i]['sub_item_labels'].append(sub_item_label)
                    
                visible_item_count += 1 # Incrémenter seulement si un item régulier a été affiché

        else:
            # Si le contenu est court, on garde la frame temporaire (avec tous les items) 
            temp_item_frame.pack(fill=tk.BOTH, expand=True) 
            
            # 💡 Mise à jour de l'état de rature
            for item_index in range(len(self.order_data['items'])):
                # S'assurer que les séparateurs (qui n'ont pas de mapping d'items) sont ignorés ici.
                if item_index in self.item_widgets_map:
                    self.is_overstrike_map[item_index] = False
                    
        # 💡 S'assurer que les items non visibles (tronqués) sont également dans l'état non-rayé par défaut
        for i in range(len(self.order_data['items'])):
            if i not in self.is_overstrike_map:
                    self.is_overstrike_map[i] = False
            
        
        # La chaîne de contenu pour la réimpression doit TOUJOURS être la version COMPLÈTE.
        self.display_ticket_content = ticket_display_str + full_ticket_items_content
        
        # --- Boutons d'Action (inchangé) ---
        self._create_buttons()
        
        # --- Temps de Préparation (inchangé) ---
        self.timer_label = tk.Label(self.content_frame, 
                                        text="Durée: 0m 0s", 
                                        font=('Segoe UI', 10), fg=COLOR_TEXT, bg=CARD_BG)
        self.timer_label.pack(fill=tk.X, pady=(5,0))

        self.timer_label.bind("<Button-1>", self._toggle_strike_all_items)
        
        # Clic droit (ou appui long sur tactile) sur le temps = Tout retirer
        # <Button-3> est le clic droit standard


        self.update_timer()


    def _delete_note_in_db(self):
        """
        Supprime la note du bill_id courant dans la base de données.
        """
        try:
            # 💡 Appel de la nouvelle méthode que vous devez créer dans DBManager
            rows_affected = self.db_manager.delete_bill_note(self.bill_id)
            
            if rows_affected > 0:
                self._refresh_note_display("") # Efface l'affichage en passant une chaîne vide
            else:
                logger.warning(f"Note non trouvée/non supprimée pour Bill ID: {self.bill_id}")
        except AttributeError:
            logger.error("La méthode 'delete_bill_note' est manquante dans DBManager.")
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de la note : {e}")

    def _update_note_in_db(self, new_note_content: str):
        """
        Callback pour le clavier virtuel: met à jour la note dans la DB 
        et rafraîchit l'affichage du post-it.
        """
        # Récupère le contenu final
        note_text = new_note_content.strip()

        
        # 1. Mise à jour dans la BDD
        rows_affected = self.db_manager.set_bill_note(self.bill_id, note_text)
        
        if rows_affected > 0:
            # 2. Mise à jour de l'affichage
            self._refresh_note_display(note_text)
        else:
            messagebox.showerror("Erreur de Note", f"Impossible de mettre à jour la note pour la facture {self.bill_id}.")

    def _refresh_note_display(self, note_content: str):
        """Met à jour l'affichage du label de la note, en le créant s'il n'existe pas et en le positionnant correctement.
        Utilisé après la sauvegarde ou la suppression via le clavier virtuel.
        """
        
        # NOTE: Assurez-vous que COLOR_NOTE et CARD_WIDTH sont bien définis dans votre fichier de configuration global.
        
        note_content = note_content.strip()
        
        # 1. CAS: Contenu présent (Création/Mise à jour)
        if note_content:
            # Création du label s'il n'existe pas
            if not hasattr(self, 'note_label') or not self.note_label.winfo_exists():
                # Crée le Label dans self.content_frame
                self.note_label = tk.Label(self.content_frame, 
                                            text="", 
                                            font=('Segoe UI', 15, 'italic'), fg='black', 
                                            bg=COLOR_NOTE, wraplength=CARD_WIDTH - 20, 
                                            justify=tk.LEFT, anchor='w')
                
                # 🚨 LOGIQUE D'INSERTION DYNAMIQUE
                # Tente d'insérer le label juste avant l'élément "séparateur" (hypothèse: 3e dernier enfant)
                separator = None
                try:
                    # On tente de trouver le séparateur. Cette ligne dépend de la structure de vos widgets.
                    # On suppose que le séparateur est l'enfant après le header et la note
                    children = self.content_frame.winfo_children()
                    for child in children:
                        if isinstance(child, ttk.Separator):
                            separator = child
                            break
                    if separator is None:
                        # Si le séparateur n'est pas trouvé, on prend le premier enfant après le header (header_frame)
                        separator = children[1] if len(children) > 1 else None 
                except IndexError:
                    pass
                
                # Configuration et insertion
                self.note_label.config(text=f"Note: {note_content}", bg=COLOR_NOTE)
                
                # Utilisation de pady=(5, 0) pour ajouter de l'espace au-dessus du label.
                if separator and separator.winfo_exists():
                    # Insère avant le séparateur/élément trouvé
                    self.note_label.pack(fill=tk.X, pady=(5, 0), padx=5, before=separator) 
                else:
                    # Si le séparateur n'est pas trouvé, on packe simplement (ce qui le mettra à la fin)
                    self.note_label.pack(fill=tk.X, pady=(5, 0), padx=5)

            else:
                # Si le label existe, simplement mettre à jour son contenu et le rendre visible
                self.note_label.config(text=f"Note: {note_content}", bg=COLOR_NOTE)
                # Assure qu'il est bien packé et visible avec la configuration désirée
                self.note_label.pack(fill=tk.X, pady=(5, 0), padx=5) 
                
            
        # 2. CAS: Contenu vide (Suppression/Masquage)
        elif hasattr(self, 'note_label') and self.note_label.winfo_exists():
            # Masque l'étiquette de la note si le contenu est vide
            self.note_label.pack_forget()


    def _handle_note_input(self):
        """
        Ouvre le clavier virtuel pour permettre la saisie d'une note.
        Maintenant, met à jour la note avec une chaîne vide si l'utilisateur efface tout.
        """
        # Arrêter le clignotement lors de l'interaction
        self._stop_flashing()
        
        # 1. Récupérer la note existante pour la passer au clavier
        current_note = self.db_manager.get_bill_note(self.bill_id)
        
        # 2. Définir la fonction de rappel pour l'action 'OK' du clavier
        def ok_action(entry_widget): 
            # 💡 On récupère le contenu, qu'il soit vide ou non.
            final_note = entry_widget.get().strip() 
            
            # 💡 CHANGEMENT ICI : On appelle toujours _update_note_in_db
            # Si final_note est vide (''), la base de données est mise à jour avec une chaîne vide.
            self._update_note_in_db(final_note)
            
            # Le clavier se détruit lui-même

        # 3. Ouvrir le clavier virtuel
        VirtualKeyboard(
            master=self.master_selector.master, 
            initial_content=current_note,      
            ok_callback=ok_action
        )

    def _create_buttons(self):
        """
        Crée les boutons d'action avec les couleurs et émojis demandés.
        Ajout du bouton SPLIT (Séparation).
        """
        
        btn_frame_1 = tk.Frame(self.content_frame, bg=CARD_BG)
        btn_frame_1.pack(fill=tk.X, pady=(10, 5))
        
        # --- Ligne 1 : Actions de statut ---
        
        # Bouton 'En cours'
        #tk.Button(btn_frame_1, 
        #          text="👉", 
        #          command=lambda: self.status_callback(self.bill_id, 'En cours'),
        #          font=('Segoe UI', 14, 'bold') , 
        #          bg='#f1c40f', fg='black', relief=tk.FLAT).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        # Bouton 'Régler/Terminer'
        # --- PREMIÈRE LIGNE DE BOUTONS ---
        # Bouton '✅' (REGLER - Reste VERT)
        tk.Button(btn_frame_1, 
                  text="🤝", 
                  command=self.master_selector.merge_selected_orders, 
                  font=('Segoe UI', 14, 'bold') ,
                  bg='#f39c12', # Orange/Jaune original
                  fg='white', 
                  relief=tk.FLAT).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        tk.Button(btn_frame_1, 
                  text="✅", 
                  command=lambda: self.status_callback(self.bill_id, 'Traitée'),
                  font=('Segoe UI', 14, 'bold') ,
                  bg='#2ecc71', fg='white', relief=tk.FLAT).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
                  
        # Bouton '📄' (IMPRIMER - Changé en TURQUOISE)
        tk.Button(btn_frame_1, 
                  text="📄", 
                  command=lambda: self._handle_print(), 
                  font=('Segoe UI', 14),
                  bg='#1abc9c', # Code pour le turquoise
                  fg='white', 
                  relief=tk.FLAT).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        # Bouton '🤝' (FUSIONNER - Jaune/Orange pour le distinguer)
        

        # --- DEUXIÈME LIGNE DE BOUTONS ---
        btn_frame_2 = tk.Frame(self.content_frame, bg=CARD_BG)
        btn_frame_2.pack(fill=tk.X, pady=(5, 10))

        # Bouton '🔵' (NOTE - Changé en ROSE)
        tk.Button(btn_frame_2, 
                  text="🔵", 
                  command=self._handle_note_input, 
                  font=('Segoe UI', 14, 'bold'), 
                  bg='#e91e63', # Code pour le rose
                  fg='white', 
                  relief=tk.FLAT).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        # Bouton '↔️' (ÉCHANGER - Gris foncé ou Turquoise selon ton goût)
        tk.Button(btn_frame_2, 
                  text="↔️", 
                  command=self.master_selector.swap_selected_orders, 
                  font=('Segoe UI', 14, 'bold') ,
                  bg='#3498db', # Turquoise original
                  fg='white', 
                  relief=tk.FLAT).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        # Bouton '🪚' (SÉPARER - Reste ROUGE)
        tk.Button(btn_frame_2, 
                  text="🪚", 
                  command=self._handle_split_order, 
                  font=('Segoe UI', 14, 'bold') ,
                  bg='#e74c3c', fg='white', relief=tk.FLAT).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

    


    def update_timer(self):
        time_diff = datetime.now() - self.creation_date
        total_seconds = int(time_diff.total_seconds())
        
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        
        # ⭐ AMÉLIORATION : Progression de couleur pour le minuteur
        if total_seconds > 900: # 15 minutes
            color = 'red' 
        elif total_seconds > 480: # 8 minutes
            color = '#e67e22' # Orange
        elif total_seconds > 300: # 5 minutes
            color = '#f1c40f' # Jaune
        else:
            color = COLOR_TEXT
        
        font_style = ('Segoe UI', 10, 'bold') if minutes >= 8 else ('Segoe UI', 10)

        self.timer_label.config(text=f"Durée: {minutes}m {seconds}s", fg=color, font=font_style)
        
        try:
            self.timer_id = self.postit_frame.after(1000, self.update_timer)
        except tk.TclError:
            pass

    def destroy(self):
        """Détruit la carte et nettoie les serveuses proprement."""
        # 1. ARRÊT IMMÉDIAT DES TIMERS
        self._stop_flashing() 
        self._cancel_long_press(None) 
        try:
            if hasattr(self, 'timer_id'):
                self.postit_frame.after_cancel(self.timer_id)
        except:
            pass

        # 2. ⭐ NETTOYAGE RADICAL (SANS PASSER PAR LES LABELS)
        try:
            app = getattr(self, 'master_app', self.master)
            if app and hasattr(app, 'serveur_window') and app.serveur_window.winfo_exists():
                
                # Au lieu de cliquer sur les boutons (qui cause l'erreur), 
                # on dit directement à la mémoire du serveur : "Efface ces items"
                if hasattr(app.serveur_window, 'active_items'):
                    # On garde seulement les items qui NE SONT PAS à cette facture
                    app.serveur_window.active_items = [
                        it for it in app.serveur_window.active_items 
                        if str(it.get('bill_id')) != str(self.bill_id)
                    ]
                
                # On retire visuellement la table
                app.serveur_window.remove_table(self.bill_id)
                
                # On rafraîchit l'affichage serveur
                if hasattr(app.serveur_window, 'update_view'):
                    app.serveur_window.update_view()
        except:
            pass

        # 3. APPEL À TON UNSTRIKE (Pour la logique interne si nécessaire)
        try:
            # On l'appelle après le nettoyage mémoire pour éviter les conflits
            self._unstrike_all_items()
        except:
            # Si ça génère l'erreur "invalid command name", on l'étouffe ici
            pass

        # 4. DESTRUCTION FINALE
        if self.postit_frame.winfo_exists():
            try:
                self.postit_frame.destroy()
            except:
                pass

# -------------------------------------------------------------------------
# --- Classe PostitSelector (Avec synchronisation et correction TclError) ---
# -------------------------------------------------------------------------

class PostitSelector(tk.Frame):
    """
    Cadre conteneur pour les colonnes de cartes.
    Gère la disposition en grille et utilise une Scrollbar Tkinter standard.
    Ajout des méthodes pour la fusion et l'échange de position.
    """
    def __init__(self, master, db_manager, service_types: list, kds_gui_instance, **kwargs):
        super().__init__(master, bg=BG_MAIN, **kwargs)

        self.header_frame = tk.Frame(self, bg="#34495e") 
        self.header_frame.pack(side=tk.TOP, fill=tk.X)

        self.db_manager = db_manager
        self.service_types = service_types
        self.column_data = {} 
        self.postit_containers = {} 
        self.master_widget = master # Référence au widget parent (App principale)
        self.selected_postits = {} # { service_type: [postit1, postit2, ...] }      
        self.kds_gui_instance = kds_gui_instance
        
        self._create_columns()
        
    # ⭐ NOUVELLE MÉTHODE : LIMITATION DE LA SÉLECTION
    def limit_selection_by_service(self, current_service_type: str, new_bill_id: str):
        """
        Désélectionne toutes les cartes du service donné, sauf celle qui est sur le point d'être sélectionnée.
        Ceci est pour limiter les actions (Fusion/Swap) à deux cartes à la fois, dans la même colonne.
        """
        for postit in self.postit_containers.get(current_service_type, []):
            if postit.bill_id != new_bill_id and postit.is_selected:
                postit._toggle_selection() 


    def filter_columns(self, selected_services):
        """Affiche ou cache les colonnes selon les boutons cliqués."""
        # On boucle sur les types de service définis dans le selector (INTERIEUR, LIVRAISON, PA)
        for service in self.service_types:
            # On vérifie si la colonne existe dans column_data
            if service in self.column_data:
                # Dans votre code, le cadre de la colonne est souvent stocké dans 'container' ou 'column_frame'
                # On va essayer de trouver le bon widget à cacher
                col_frame = self.column_data[service].get('frame') or self.column_data[service].get('container')
                
                if col_frame:
                    if service in selected_services:
                        # On réaffiche la colonne
                        col_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
                    else:
                        # On cache la colonne
                        col_frame.pack_forget()

    # ⭐ MODIFIÉ: FUSION - Utilisation de db_manager.merge_orders et rafraîchissement complet
    def merge_selected_orders(self):
        """
        Tente de fusionner les factures sélectionnées (2) dans une TOUTE NOUVELLE FACTURE via DBManager.
        """
        # 1. Récupération des post-its avec filtrage des widgets détruits
        selected_postits = self.get_selected_postits()
        
        # ⭐ SÉCURITÉ : Vérifier le nombre AVANT d'accéder aux index [0] ou [1]
        # Cela évite l'erreur "IndexError: list index out of range"
        num_selected = len(selected_postits)
        

        # p1 = Destination (métadonnées), p2 = Source
        p1, p2 = selected_postits[0], selected_postits[1] 
        
        # 3. Fenêtre de confirmation personnalisée
        dialog = MergeConfirmationDialog(self.master, p1, p2)
        
        if dialog.result: 
            try:
                # Appel du DBManager pour la fusion
                new_bill_id, _, _ = self.db_manager.merge_orders(
                    source_bill_ids=[p2.bill_id], 
                    destination_bill_id=p1.bill_id
                )
                
                # 4. Désélectionner (retirer bordures bleues)
                p1._toggle_selection() 
                p2._toggle_selection() 
                
                # 5. Supprimer les deux cartes d'ORIGINE de l'interface
                self.remove_postit(p2) 
                self.remove_postit(p1)
                
                # Optionnel: forcer le refresh ici si nécessaire
                # self.kds_app.check_for_new_orders()

            except Exception as e:
                messagebox.showerror("Erreur de Fusion DB", f"Échec de la fusion : {e}")

    # ⭐ NOUVELLE MÉTHODE : ÉCHANGE DE POSITION (SWAP)
    def swap_selected_orders(self):
        return
    
    def notify_selection_change(self):
        """Appelée par OrderPostIt pour indiquer qu'un état de sélection a changé.
        Permet au TotalWidget ou aux contrôles externes de mettre à jour leur état."""
        self.selected_postits = self.get_selected_postits()


    def _create_columns(self):
        """Crée une colonne unique pour tous les types de services."""
        # On s'assure qu'on ne traite qu'un seul type
        service = 'COMMANDE'
        
        # Frame principal qui prend tout l'écran
        col_frame = tk.Frame(self, bg=CARD_BG, bd=0, relief=tk.FLAT) 
        col_frame.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.BOTH, expand=True) 

        # --- Conteneur du Canvas et Scrollbar ---
        scroll_container = tk.Frame(col_frame, bg=CARD_BG)
        scroll_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        scroll_container.grid_rowconfigure(0, weight=1)
        scroll_container.grid_columnconfigure(0, weight=1)

        # 1. Scrollbar Verticale
        scrollbar = ttk.Scrollbar(scroll_container, orient=tk.VERTICAL)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # 2. Canvas pour le contenu (C'est ici que les post-its "vivent")
        canvas = tk.Canvas(scroll_container, bg=CARD_BG, highlightthickness=0, 
                           yscrollcommand=scrollbar.set) 
        canvas.grid(row=0, column=0, sticky="nwes") 
        
        # Lier la Scrollbar au Canvas
        scrollbar.config(command=canvas.yview)
        
        # 3. Frame interne (inner_frame) où on va mettre la GRILLE de post-its
        inner_frame = tk.Frame(canvas, bg=CARD_BG) 
        
        # Positionnement de l'inner_frame dans le canvas
        window_item_id = canvas.create_window((0, 0), window=inner_frame, anchor="nw")

        # Mise à jour auto de la zone de défilement
        inner_frame.bind("<Configure>", 
                          lambda e, c=canvas: c.config(scrollregion=c.bbox("all"))) 

        # Ajustement auto de la largeur pour que la grille suive la taille de l'écran
        canvas.bind('<Configure>', 
                     lambda e, c=canvas, i=window_item_id: c.itemconfigure(i, width=c.winfo_width()))

        # --- Configuration de la Grille interne ---
        # On configure les colonnes de la grille pour que les post-its soient côte à côte
        for j in range(MAX_CARDS_PER_ROW):
            inner_frame.grid_columnconfigure(j, weight=1) 

        # Stockage unique
        self.column_data[service] = {
            'inner_frame': inner_frame, 
            'canvas': canvas,
            'scrollbar': scrollbar
        }
        self.postit_containers[service] = []
        
        # On initialise aussi les autres services dans le dictionnaire 
        # pour éviter les erreurs "KeyError" si le serial_reader envoie "LIVRAISON"
        self.postit_containers['LIVRAISON'] = self.postit_containers[service]
        self.postit_containers['POUR EMPORTER'] = self.postit_containers[service]


    def get_selected_postits(self) -> list['OrderPostIt']:
        """Retourne les objets OrderPostIt réellement affichés et sélectionnés."""
        selected = []
        # On parcourt tous les conteneurs de colonnes
        for service_type in self.postit_containers:
            for postit in self.postit_containers[service_type]:
                try:
                    # 1. Vérifie si le widget existe encore physiquement
                    # 2. Vérifie si la variable is_selected est True
                    if postit.winfo_exists() and getattr(postit, 'is_selected', False):
                        selected.append(postit)
                except Exception:
                    # Si le postit est détruit, on l'ignore
                    continue
        return selected

    # 🌟 MODIFIÉ: Logique de sélection pour le KDS Total
    def get_selected_bill_ids(self) -> list[str]:
        """
        Retourne les IDs des factures sélectionnées. 
        Si aucune facture n'est sélectionnée, retourne les IDs de TOUTES les factures actives.
        """
        selected_postits = self.get_selected_postits()
        if selected_postits:
            return [p.bill_id for p in selected_postits]
        else:
            # Sinon, on retourne toutes les factures actives (comportement par défaut)
            all_active_ids = []
            for postit_list in self.postit_containers.values():
                for postit in postit_list:
                    if postit.postit_frame and postit.postit_frame.winfo_exists():
                        all_active_ids.append(postit.bill_id)
            return all_active_ids
        
    def get_column_frame(self, service_type):
        """Retourne le cadre interne du Canvas pour le placement en grille."""
        if service_type in self.column_data:
            return self.column_data[service_type]['inner_frame']
        else:
            return self.column_data[self.service_types[-1]]['inner_frame']

    def _get_display_service_type(self, service_type):
        """Force l'affichage de tous les types dans la colonne 'COMMANDE'."""
        return 'COMMANDE'

    
    def _repack_column(self, service_type: str):
        """Réorganise les cartes en plaçant la table 888 en priorité à gauche."""
        target = 'COMMANDE'
        parent_frame = self.get_column_frame(target)
        if not parent_frame:
            return

        postit_list = self.postit_containers.get(target, [])
        live_postit_list = [p for p in postit_list if p.postit_frame and p.postit_frame.winfo_exists()]

        # --- AJOUT DU TRI PRIORITAIRE ICI ---
        # On trie : priorité 0 si table 888, sinon priorité 1. 
        # Ensuite on trie par date de création pour garder l'ordre chronologique pour le reste.
        live_postit_list.sort(key=lambda p: (
            0 if str(p.order_data.get('table_number', '')).strip() == "888" else 1,
            p.creation_date
        ))
        # ------------------------------------

        max_cols = MAX_CARDS_PER_ROW if MAX_CARDS_PER_ROW > 0 else 3
        
        for index, postit in enumerate(live_postit_list):
            r = index // max_cols
            c = index % max_cols
            
            # On force la mise à jour de la position sur la grille
            postit.postit_frame.grid(
                row=r, 
                column=c, 
                padx=10, 
                pady=10, 
                sticky="nwes"
            )


    def add_postit(self, postit, service_type: str):
        """Ajoute un nouveau PostIt en forçant le regroupement."""
        # On ignore le service_type reçu (LIVRAISON) et on utilise 'COMMANDE'
        target = 'COMMANDE'
        
        # On met à jour l'étiquette interne du postit pour le repack
        postit.service_type = target
        
        if target in self.postit_containers:
            self.postit_containers[target].append(postit)
            self.update_column_title(target, len(self.postit_containers[target]))
        else:
            logger.error(f"ERREUR: La colonne {target} est absente de l'interface.")
                    
    def remove_postit(self, postit: OrderPostIt):
        """Retire un post-it et le détruit."""
        
        # ⭐ ÉTAPE CLÉ : Redirection du service_type pour la manipulation de colonne
        # On utilise l'attribut actuel de la carte qui a été mis à jour par add_postit (COMMANDE)
        display_service_type = self._get_display_service_type(postit.service_type)
        
        # Désélectionner avant de retirer si la carte était sélectionnée
        if postit.is_selected:
            postit._toggle_selection()
            
        if postit in self.postit_containers.get(display_service_type, []):
            self.postit_containers[display_service_type].remove(postit)
            postit.destroy() 
            self._repack_column(display_service_type)
            self.update_column_title(display_service_type, len(self.postit_containers[display_service_type]))

    
    def update_column_title(self, service_type, count):
        """Met à jour le compteur dans le titre de chaque colonne."""
        #if service_type in self.column_data:
         #   self.column_data[service_type]['count_label'].config(text=f"({count} commandes)")

    def update_column_titles(self):
        """Met à jour les compteurs et la scrollregion de manière optimisée."""
        for service in self.service_types:
            count = len(self.postit_containers.get(service, []))
            self.update_column_title(service, count)
            # On réorganise la colonne sans rafraîchir le scroll ici
            self._repack_column(service)

        # On rafraîchit la zone de défilement UNE SEULE FOIS à la fin
        try:
            # IMPORTANT: Vérifie si c'est self.canvas ou self.master_canvas
            if hasattr(self, 'canvas') and self.canvas.winfo_exists():
                self.update_idletasks()
                self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except Exception as e:
            print(f"Erreur rafraîchissement scroll: {e}")
            
# postit_widget.py (Fin du fichier MODIFIÉ)