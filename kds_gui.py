# kds_gui.py (Adapté avec Authentification, Corbeille et Consultation)
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
import logging
import sys
import signal # 🚨 NOUVEAU : Pour intercepter Ctrl+C (sur Linux/macOS)
import os     # 🚨 NOUVEAU : Pour vérifier le système d'exploitation
import subprocess # ⭐ NOUVEAU : Pour exécuter des commandes externes
import uuid
import random
import json 
import threading
import math
import textwrap  # Pour le retour à la ligne automatique




from serial_reader import SerialReader # ⬅️ Assurez-vous d'avoir cet import !

os.environ['SDL_AUDIODRIVER'] = 'dummy'

import platform 
try:
    if platform.system() == 'Windows':
        import winsound
    else:
        # Tente d'utiliser une bibliothèque multiplateforme simple si disponible
        # Nous allons simuler ici pour ne pas ajouter de dépendance externe stricte au KDS
        logger.warning("Winsound non disponible. Le son peut ne pas fonctionner sur Linux/macOS sans pygame/simpleaudio.")
        winsound = None 
except ImportError:
    winsound = None

try:
    from log_view import LogViewWindow
except ImportError:
    LogViewWindow = None

try:
    from animate_pack import DesktopPet
except ImportError:
    DesktopPet = None
    print("⚠️ animate_pack.py non trouvé, le compagnon ne sera pas chargé.")



# ⭐ NOUVEAU: Importation du widget de minuteur
try:
    from timer_widget import TimerManagerWindow, TimerWidget
except ImportError:
    class TimerManagerWindow(tk.Toplevel):
        def __init__(self, master, kds_gui_instance): super().__init__(master); self.destroy()
        def on_close(self): pass
    class TimerWidget(tk.Toplevel):
        def __init__(self, master, *args): super().__init__(master); self.destroy()
        def on_close(self): pass

# NÉCESSITE DBManager (non fourni mais requis)
try:
    from db_manager import DBManager 
except ImportError:
    class DBManager:
        def __init__(self): logging.warning("DBManager simulé.")
        def get_pending_orders(self):return {'Sur Place': [], 'À Emporter': [], 'Livraison': [], 'Livreur': []}
        def update_order_status(self, bill_id, status): return 1
        def permanent_delete_order_by_bill_id(self, bill_id): return 1
        # Simuler les méthodes requises par les autres modules pour éviter les crashs
        def set_order_status_by_bill_id(self, bill_id, status): return 1
        def delete_completed_and_cancelled_orders(self): return 1
        def get_archived_orders(self): return []

# ⭐ Importation des modules pour la configuration des plats principaux
try:
    from db_maindish_gui import MainDishApp 
    from db_maindish import MainDishDBManager
except ImportError:
    def MainDishApp(*args): logging.error("MainDishApp non disponible. Vérifiez db_maindish_gui.py.")
    class MainDishDBManager:
        def __init__(self): logging.warning("MainDishDBManager simulé.")
        pass

# ⭐ Importation du module de consultation des ventes
try:
    from consultation import ConsultationWindow 
except ImportError:
    def ConsultationWindow(*args, **kwargs): logging.error("ConsultationWindow non disponible. Vérifiez consultation.py.")

# ⭐ NOUVEAU: Importation du module de la Corbeille
try:
    from kds_trash_window import TrashWindow
except ImportError:
    def TrashWindow(*args, **kwargs): logging.error("TrashWindow non disponible. Vérifiez kds_trash_window.py.")

# ⭐ NOUVEAU: Importation du module d'authentification
try:
    from loginpass import check_access_password
except ImportError:
    def check_access_password(action_name: str) -> bool: 
        logging.error(f"Module 'loginpass.py' non disponible. Authentification pour '{action_name}' désactivée.")
        return True # Permet l'accès par défaut si le module est manquant

# NÉCESSITE OrderPostIt, PostitSelector, TotalWidget et constantes 
from postit_widget import OrderPostIt, PostitSelector 
from kds_total_widget import TotalWidget # <<< MODIFIÉ: Importation de TotalWidget
from kds_constants import REFRESH_RATE_MS, SERVICE_TYPES, BG_MAIN, COLOR_TEXT, CARD_BG


try:
    # Assurez-vous que DBKonstantesManager.py est dans le même dossier.
    from DBKonstantesManager import KonstantesEditorApp, DBKonstantesManager 
except ImportError:
    # Gestion d'erreur au cas où le fichier n'est pas trouvé
    logger.error("DBKonstantesManager.py non trouvé ou structure de classe incorrecte pour l'import.")
    # On définit des classes simulées pour éviter un crash complet de l'application principale
    class KonstantesEditorApp:
        def __init__(self, master, db_manager): logging.warning("KonstantesEditorApp simulée.")
    class DBKonstantesManager:
        def __init__(self): logging.warning("DBKonstantesManager simulée.")

try:
    from config_menu import ConfigMenu
except ImportError:
    class ConfigMenu(tk.Toplevel):
        def __init__(self, master): 
            super().__init__(master)
            messagebox.showerror("Erreur", "Le module 'config_menu.py' est introuvable.")
            self.destroy()



# Configuration du logger pour kds_gui
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BG_MAIN = "#2c3e50"
CARD_BG = "#34495e"
COLOR_TEXT = "#ecf0f1"
SCREEN_2_GEOMETRY_FULLSCREEN = "1920x1080+1920+0"

import tkinter as tk
from tkinter import ttk
import logging
from datetime import datetime


class ServeurWindow(tk.Toplevel):
    """
    Fenêtre de suivi des tables (Écran 2)
    Optimisée pour Windows 10 (Gestion du réveil de veille et multi-moniteurs)
    """

    NB_COLONNES = 4 

    def __init__(self, master, kds_gui_instance):
        super().__init__(master)
        print("DEBUG: [ServeurWindow] Initialisation de la fenêtre Écran 2")
        
        self.kds_gui_instance = kds_gui_instance
        self.title("KDS - Suivi des Tables")
        
        self.serveuses_colors = self._load_serveuses_config()
        from kds_constants import BG_MAIN, SCREEN_2_GEOMETRY_FULLSCREEN

        # Configuration initiale de la fenêtre
        self.overrideredirect(False) 
        self.configure(bg=BG_MAIN)
        self.protocol("WM_DELETE_WINDOW", self._prevent_close)
        
        # S'assurer que la fenêtre est toujours au-dessus
        self.attributes('-topmost', True)
        
        try:
            self.geometry(SCREEN_2_GEOMETRY_FULLSCREEN)
        except Exception as e:
            print(f"DEBUG: [ServeurWindow] Erreur géométrie écran 2: {e}")
            self.geometry("1200x800+1920+0")

        self.active_tables_frames = {}

        self.main_frame = tk.Frame(self, bg=BG_MAIN)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.columns_container = tk.Frame(self.main_frame, bg=BG_MAIN)
        self.columns_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.column_frames = []
        for i in range(self.NB_COLONNES):
            col = tk.Frame(self.columns_container, bg=BG_MAIN)
            col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
            self.column_frames.append(col)

        # Lancement des boucles de maintenance
        self._update_elapsed_time()
        self._maintain_window_position()

    def _maintain_window_position(self):
        """Force la fenêtre à rester sur l'écran 2."""
        try:
            if self.winfo_exists():
                from kds_constants import SCREEN_2_GEOMETRY_FULLSCREEN
                if self.state() == 'withdrawn' or self.state() == 'iconic':
                    self.deiconify()
                
                if self.winfo_x() < 1000:
                    self.geometry(SCREEN_2_GEOMETRY_FULLSCREEN)
                
                self.lift()
                self.attributes('-topmost', True)
                self.after(5000, self._maintain_window_position)
        except Exception as e:
            print(f"DEBUG: [ServeurWindow] Erreur maintain_position: {e}")

    def update_table(self, bill_id, table_number, items_data, server_name=""):
        """
        Logique demandée :
        - Si AUCUN item n'est raturé -> On n'affiche RIEN (Lève la table).
        - Dès qu'un item est raturé -> On AFFICHE la table.
        - Si TOUT est raturé -> On LAISSE la table affichée.
        """
        from kds_constants import CARD_BG, COLOR_TEXT

        # 1. ANALYSE : Est-ce qu'il y a au moins une rature ?
        has_any_raye = False
        if items_data:
            for item in items_data:
                is_raye = item.get('is_raye', False) if isinstance(item, dict) else False
                if is_raye:
                    has_any_raye = True
                    break # On en a trouvé une, c'est suffisant pour afficher

        # 2. CONDITION DE VISIBILITÉ
        # Si rien n'est raturé (has_any_raye est False), on enlève la table
        if not has_any_raye:
            if bill_id in self.active_tables_frames:
                print(f"DEBUG: [ServeurWindow] Table {table_number} levée (Aucun item raturé).")
                self.remove_table(bill_id)
            return

        # 3. AFFICHAGE (Si on arrive ici, c'est qu'il y a au moins un item raturé)
        clean_name = server_name.strip().upper() if server_name else ""
        s_color = self.serveuses_colors.get(clean_name, self.serveuses_colors.get("DEFAULT_COLOR", "#FFFFFF"))

        # Si la table n'est pas encore sur l'écran, on la crée
        if bill_id not in self.active_tables_frames:
            target_col = min(self.column_frames, key=lambda c: len(c.winfo_children()))
            
            frame = tk.Frame(target_col, bg=CARD_BG, bd=3, relief=tk.RIDGE, highlightbackground=s_color)
            frame.pack(fill=tk.X, pady=4)

            header = tk.Frame(frame, bg=s_color)
            header.pack(fill=tk.X)

            tk.Label(header, text=f"T-{table_number}", font=("Arial", 16, "bold"), bg=s_color, fg="black").pack(side=tk.LEFT, padx=5)
            tk.Label(header, text=server_name if server_name else "SERVEUSE", font=("Arial", 14, "bold"), bg=s_color, fg="black").pack(side=tk.LEFT, expand=True)
            
            time_lbl = tk.Label(header, text="0m", font=("Arial", 14, "bold"), bg=s_color, fg="black")
            time_lbl.pack(side=tk.RIGHT, padx=5)

            i_frame = tk.Frame(frame, bg=CARD_BG)
            i_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)

            self.active_tables_frames[bill_id] = {
                "frame": frame, "i_frame": i_frame, "item_labels": [],
                "start_time": datetime.now(), "time_label": time_lbl, "table_num": table_number
            }

        # 4. DESSIN/MISE À JOUR DES ITEMS
        info = self.active_tables_frames[bill_id]
        for lbl in info["item_labels"]:
            try: lbl.destroy()
            except: pass
        info["item_labels"].clear()

        for item in items_data:
            text_to_show = item.get('text', "") if isinstance(item, dict) else str(item)
            is_raye = item.get('is_raye', False) if isinstance(item, dict) else False

            if is_raye:
                # Texte raturé (GRIS)
                current_font = ("Arial", 14, "bold overstrike")
                current_fg = "#7f8c8d" 
            else:
                # Texte normal (NOIR/COULEUR TEXTE)
                current_font = ("Arial", 14, "bold")
                current_fg = COLOR_TEXT

            padding_left = 20 if text_to_show.strip().startswith("↳") else 5
            l = tk.Label(info["i_frame"], text=text_to_show, font=current_font, bg=CARD_BG, fg=current_fg, anchor="w", justify=tk.LEFT, wraplength=280)
            l.pack(fill=tk.X, padx=(padding_left, 5))
            info["item_labels"].append(l)

    def remove_table(self, bill_id):
        if bill_id in self.active_tables_frames:
            try:
                self.active_tables_frames[bill_id]["frame"].destroy()
            except: pass
            del self.active_tables_frames[bill_id]

    def _update_elapsed_time(self):
        try:
            if self.winfo_exists():
                now = datetime.now()
                for info in self.active_tables_frames.values():
                    elapsed = now - info["start_time"]
                    m, s = divmod(elapsed.seconds, 60)
                    info["time_label"].config(text=f"{m}m {s}s")
                self.after(1000, self._update_elapsed_time)
        except: pass

    def _load_serveuses_config(self):
        file_path = 'serveuses_config.json'
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return {"DEFAULT_COLOR": "#FFFFFF"}
    
    def flash_screen(self):
        """Lance 2 shots de 3 secondes avec un dégradé Jaune -> Vert -> Bleu -> Mauve."""
        import math
        import random
        from datetime import datetime

        def interpolate_color(c1, c2, factor):
            """Mélange deux couleurs RGB et retourne le format hex #RRGGBB"""
            f = max(0, min(1, factor))
            r = int(c1[0] + (c2[0] - c1[0]) * f)
            g = int(c1[1] + (c2[1] - c1[1]) * f)
            b = int(c1[2] + (c2[2] - c1[2]) * f)
            return f'#{r:02x}{g:02x}{b:02x}'

        def get_multi_step_color(progress):
            """Calcule la couleur hexadécimale sur la séquence."""
            # Définition des points de passage (RGB Tuples)
            steps = [
                (241, 196, 15),  # Jaune
                (46, 204, 113),  # Vert
                (52, 152, 219),  # Bleu
                (155, 89, 182)   # Mauve
            ]
            
            if progress <= 0: 
                return f'#{steps[0][0]:02x}{steps[0][1]:02x}{steps[0][2]:02x}'
            if progress >= 1: 
                return f'#{steps[-1][0]:02x}{steps[-1][1]:02x}{steps[-1][2]:02x}'

            num_segments = len(steps) - 1
            segment_idx = int(progress * num_segments)
            segment_progress = (progress * num_segments) - segment_idx
            
            # On interpole entre le segment actuel et le suivant
            return interpolate_color(steps[segment_idx], steps[segment_idx + 1], segment_progress)

        def start_shot(shot_number):
            duration_sec = 3.0
            start_time = datetime.now().timestamp()

            def run_animation():
                now = datetime.now().timestamp()
                elapsed = now - start_time
                
                if elapsed < duration_sec:
                    progress = elapsed / duration_sec
                    main_bg = get_multi_step_color(progress)
                    
                    # Application sécurisée des couleurs
                    try:
                        self.configure(bg=main_bg)
                        if hasattr(self, 'main_frame') and self.main_frame:
                            self.main_frame.configure(bg=main_bg)
                        if hasattr(self, 'columns_container') and self.columns_container:
                            self.columns_container.configure(bg=main_bg)
                        
                        # Propagation sur les colonnes
                        for i, col in enumerate(getattr(self, 'column_frames', [])):
                            col_elapsed = elapsed - (i * 0.1)
                            col_p = max(0, min(1, col_elapsed / (duration_sec - 0.5)))
                            col.configure(bg=get_multi_step_color(col_p))
                    except Exception as e:
                        print(f"Erreur config couleur: {e}")

                    self.after(30, run_animation)
                else:
                    if shot_number < 2:
                        self.after(100, lambda: start_shot(shot_number + 1))
                    else:
                        if hasattr(self, '_reset_background'):
                            self._reset_background()

            run_animation()

        start_shot(1)

    def _reset_background(self):
        from kds_constants import BG_MAIN
        self.configure(bg=BG_MAIN)
        self.main_frame.configure(bg=BG_MAIN)
        self.columns_container.configure(bg=BG_MAIN)
        for col in self.column_frames:
            col.configure(bg=BG_MAIN)


    def _prevent_close(self):
        pass

    def on_close(self):
        print("DEBUG: Fermeture contrôlée de ServeurWindow")
        self.kds_gui_instance.serveur_window = None
        self.destroy()
        
# Fichier: kds_gui.py
class KonstantesManagerWindow(tk.Toplevel):
    """
    Fenêtre modale qui héberge l'application KonstantesEditorApp.
    """
    def __init__(self, master):
        super().__init__(master)
        self.title("KDS Constantes Editor Avancé")
        self.geometry("1000x700")
        
        # Rend la fenêtre modale par rapport au parent et capture les événements
        self.transient(master) 
        self.grab_set()       
        
        # 1. Instancier le DBManager spécifique aux constantes
        # DBKonstantesManager gère sa propre connexion à 'kdstotal.db'
        self.db_konstantes_manager = DBKonstantesManager()

        # 2. Intégrer l'application KonstantesEditorApp dans cette fenêtre Toplevel
        # KonstantesEditorApp prend la fenêtre Toplevel (self) comme maître.
        self.editor_app = KonstantesEditorApp(self, self.db_konstantes_manager)
        
        # Gère la fermeture : relâche le focus et détruit la fenêtre
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.center_window()

    def center_window(self):
        """Centre la fenêtre sur l'écran."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.master.winfo_screenwidth() // 2) - (width // 2)
        y = (self.master.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'+{x}+{y}')

    def on_close(self):
        """Relâche le focus et détruit la fenêtre."""
        self.grab_release()
        self.destroy()

class ExitOptionsDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)

        # Supprime entièrement la barre de titre
        self.overrideredirect(True)

        # Taille fixe
        w, h = 350, 200

        # Centrage
        self.update_idletasks()
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws - w) // 2
        y = (hs - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        # Pour garantir la modale
        self.grab_set()

        # Valeur par défaut
        self.result = "cancel"

        # ======= STYLE DE LA FENÊTRE ==========
        frame = tk.Frame(self, bg="#2c3e50", bd=2, relief="ridge")
        frame.pack(fill="both", expand=True)

        tk.Label(frame, 
                 text="Que souhaitez-vous faire ?", 
                 font=("Arial", 13, "bold"),
                 bg="#2c3e50", fg="white").pack(pady=15)

        btn_style = {"width": 20, "height": 1, "font": ("Arial", 11)}

        tk.Button(frame, text="🔁 Redémarrer", command=self.choose_reboot, **btn_style).pack(pady=5)
        tk.Button(frame, text="⏻ Éteindre", command=self.choose_shutdown, **btn_style).pack(pady=5)
        tk.Button(frame, text="❌ Annuler", command=self.choose_cancel, **btn_style).pack(pady=5)

        # Interdire toute fermeture externe (Alt+F4, etc.)
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        self.wait_window(self)

    def choose_reboot(self):
        self.result = "reboot"
        self.destroy()

    def choose_shutdown(self):
        self.result = "shutdown"
        self.destroy()

    def choose_cancel(self):
        self.result = "cancel"
        self.destroy()


# Note: Vous devez toujours importer 'subprocess' en haut du fichier kds_gui.py
# import subprocess

class KDSGUI:
    """
    Interface graphique KDS principale basée sur Tkinter.
    """
    def __init__(self, root: tk.Tk, db_manager: DBManager, reader=None):
        # 'root' est le premier argument de type tk.Tk
        self.root = root
        # ⭐ CORRECTION CRITIQUE : Utilisez l'argument 'root' pour initialiser 'self.master'
        self.master = root 
        self.db_manager = db_manager
        self.reader = reader  # <-- AJOUTEZ CETTE LIGNE : elle stocke le lecteur pour le menu technique

        self.print_enabled_var = tk.BooleanVar(value=True)
        self.lock = threading.Lock() # Ajout du verrou
        self.last_cleanup_date = None
        self.active_postits = {} # {bill_id: OrderPostIt}
        self.last_check_time = datetime.now() 

        self._configure_root()
        self._setup_signal_handler() 
        self.pa_spam_lock = False


        self.current_type_filter = "TOUS"  # Par défaut, on affiche tout

        self.active_filters = {
            "COMMANDE": True,
            "LIVRAISON": True,
            "LIVREUR": True,
            "POUR EMPORTER": True
        }
        self.all_selected = True

        if DesktopPet:
            # On crée une nouvelle fenêtre par-dessus pour le compagnon
            pet_window = tk.Toplevel(self.root)
            self.desktop_pet = DesktopPet(pet_window)
        
        # Initialisation du gestionnaire des plats principaux
        try:
            self.main_dish_db_manager = MainDishDBManager()
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de MainDishDBManager: {e}")
            self.main_dish_db_manager = None
            
        self.total_widget = None 
        self.trash_window = None 
        self.consultation_window = None
        self.timer_manager_window = None
        self.serveur_window = None
        self.active_timers = {}
        self.print_enabled_var = tk.BooleanVar(value=True)
        self.print_forwarding_enabled_var = tk.BooleanVar(value=True) # Activé par défaut 

        self.sound_enabled = tk.BooleanVar(value=True) # Par défaut, le son est activé
        self.serial_reader = SerialReader(
        self.db_manager, 
        print_forwarding_state=self.print_enabled_var
        )
        
        # 3. Démarrer le thread
        self.serial_reader.daemon = True
        self.serial_reader.start()
        self._create_main_frames()
        self._create_widgets()
        
        self.check_for_new_orders()
        self.root.after(1000, self._open_serveur_window) # On attend 1s pour que le reste soit prêt
        self.check_auto_cleanup()
        self._schedule_auto_cleanup()
        
    
    def _schedule_auto_cleanup(self):
        # Récupération de l'heure actuelle
        now = datetime.now()
        
        # 1. Vérification fenêtre matinale : 7h40 (déclenchement à 7h40)
        if now.hour == 7 and 30 <= now.minute <= 40:
            # Vérification du verrou pour le matin
            if getattr(self, 'last_cleanup_morning', None) != now.date():
                print(f"🕒 {now.strftime('%H:%M')} - Début du nettoyage automatique matinal...")
                try:
                    count = self.db_manager.mark_specific_types_as_done()
                    if count > 0:
                        self.update_status(f"Nettoyage Auto Matin : {count} commandes traitées.", "#2ecc71")
                        self.refresh_display()
                    
                    self.last_cleanup_morning = now.date()
                    print(f"✅ Nettoyage matinal terminé le {now.date()}.")
                except Exception as e:
                    logging.error(f"Erreur lors du nettoyage automatique matinal: {e}")

        # 2. Vérification fenêtre après-midi : 14h00 - 14h05
        elif now.hour == 14 and 0 <= now.minute <= 5:
            # Vérification du verrou pour l'après-midi
            if getattr(self, 'last_cleanup_afternoon', None) != now.date():
                print(f"🕒 {now.strftime('%H:%M')} - Début du nettoyage automatique après-midi...")
                try:
                    count = self.db_manager.mark_specific_types_as_done()
                    if count > 0:
                        self.update_status(f"Nettoyage Auto Après-midi : {count} commandes traitées.", "#2ecc71")
                        self.refresh_display()
                    
                    self.last_cleanup_afternoon = now.date()
                    print(f"✅ Nettoyage après-midi terminé le {now.date()}.")
                except Exception as e:
                    logging.error(f"Erreur lors du nettoyage automatique après-midi: {e}")

        # Rappelle la fonction dans 60 secondes (1 minute)
        self.root.after(60000, self._schedule_auto_cleanup)
            
    def check_auto_cleanup(self):
        # Récupération de l'heure actuelle
        now = datetime.now()
        
        # 1. Vérification de la fenêtre horaire : 
        # Le matin (hour == 7) ET entre 45 et 50 minutes.
        # Si le soir (ex: 19h), now.hour est 19, donc le 'if' est ignoré.
        if now.hour == 7 and 45 <= now.minute <= 50:
            
            # 2. Vérification si on a déjà fait le nettoyage aujourd'hui
            # Cela empêche de supprimer plusieurs fois entre 7:45 et 7:50
            if getattr(self, 'last_cleanup_date', None) != now.date():
                
                print(f"🕒 {now.strftime('%H:%M')} - Début du nettoyage automatique matinal...")
                
                try:
                    # Appel à la fonction de nettoyage
                    deleted_count = self.db_manager.delete_completed_and_cancelled_orders()
                    self.update_status(f"🗑️ Nettoyage auto matinal : {deleted_count} commandes supprimées.", 'red')
                    
                    # Mise à jour du verrou pour la date du jour
                    self.last_cleanup_date = now.date()
                    print(f"✅ Nettoyage terminé pour ce matin le {now.date()}.")
                    
                except Exception as e:
                    print(f"❌ Erreur lors du nettoyage auto : {e}")

        # Rappelle la fonction dans 60 secondes (1 minute)
        self.root.after(60000, self.check_auto_cleanup)
    

    def _configure_root(self):
        """Configuration : Boutons à gauche, Heure/Compteur à DROITE en JAUNE."""
        self.root.title("KDS - Kitchen Display System")
        self.root.configure(bg=BG_MAIN)
        self.root.overrideredirect(True)
        self.root.state('zoomed') 
        
        
        # --- 🔵 1. LE HEADER (Bandeau noir) ---
        self.header_frame = tk.Frame(self.root, bg='#2c3e50', height=60)
        self.header_frame.pack(side=tk.TOP, fill=tk.X)

        # --- 📑 A. ZONE GAUCHE : LES BOUTONS (Onglets) ---
        self.left_tabs_frame = tk.Frame(self.header_frame, bg='#2c3e50')
        self.left_tabs_frame.pack(side=tk.LEFT, padx=10)

        # Bouton TOUT (Bleu standard)
        self.btn_tout = tk.Button(self.left_tabs_frame, text="TOUT", 
            font=('Arial', 11, 'bold'), bg='#34495e', fg='white', relief='flat', padx=15,
            command=lambda: self._switch_tab("TOUT"))
        self.btn_tout.pack(side=tk.LEFT, padx=5)

        # Bouton INTÉRIEUR (Orange)
        self.btn_interieur = tk.Button(self.left_tabs_frame, text="COMMANDE", 
            font=('Arial', 11, 'bold'), bg='#e67e22', fg='white', relief='flat', padx=15,
            command=lambda: self._switch_tab("COMMANDE"))
        self.btn_interieur.pack(side=tk.LEFT, padx=5)

        # Bouton LIVRAISON (Vert)
        self.btn_livraison = tk.Button(self.left_tabs_frame, text="LIVRAISON", 
            font=('Arial', 11, 'bold'), bg='#27ae60', fg='white', relief='flat', padx=15,
            command=lambda: self._switch_tab("LIVRAISON"))
        self.btn_livraison.pack(side=tk.LEFT, padx=5)

        # Bouton LIVRAISON (Vert)
        self.btn_livreur = tk.Button(self.left_tabs_frame, text="LIVREUR", 
            font=('Arial', 11, 'bold'), bg='#27ae60', fg='white', relief='flat', padx=15,
            command=lambda: self._switch_tab("LIVREUR"))
        self.btn_livreur.pack(side=tk.LEFT, padx=5)

        # Bouton PA (Violet)
        self.btn_pa = tk.Button(self.left_tabs_frame, text="POUR EMPORTER", 
            font=('Arial', 11, 'bold'), bg='#8e44ad', fg='white', relief='flat', padx=15,
            command=lambda: self._switch_tab("POUR EMPORTER"))
        self.btn_pa.pack(side=tk.LEFT, padx=5)

        # --- 🕒 B. ZONE DROITE : HEURE ET COMPTEUR (EN JAUNE) ---
        self.top_title_label = tk.Label(
            self.header_frame, 
            text="CHARGEMENT...", 
            font=('Arial', 18, 'bold'), 
            bg='#2c3e50', 
            fg='#f1c40f',  # 🟡 JAUNE
            padx=20
        )
        self.top_title_label.pack(side=tk.RIGHT) # ⬅️ Déplacé à droite

        # --- 📦 3. ZONE D'AFFICHAGE PRINCIPALE ---
        self.main_display_frame = tk.Frame(self.root, bg=BG_MAIN)

        self.update_button_counts()
        # Lancement de l'horloge
        self._update_top_clock()
    
    def _trigger_pa_flash(self):
        """Action du bouton PA : fait flasher avec anti-spam de 25s."""
        # Si le verrou est actif, on ne fait rien
        if getattr(self, 'pa_spam_lock', False):
            self.update_status("Veuillez patienter (Anti-spam 25s)", "orange")
            return

        if self.serveur_window and self.serveur_window.winfo_exists():
            # 1. Activer le verrou
            self.pa_spam_lock = True
            
            # 2. Désactiver visuellement le bouton
            if hasattr(self, 'btn_flash_pa'):
                self.btn_flash_pa.config(state=tk.DISABLED, bg='#7f8c8d')

            # 3. Lancer le flash sur la fenêtre serveur
            self.serveur_window.flash_screen()
            
            # 4. Correction de l'erreur : on utilise self.root.after
            # Si votre variable de fenêtre principale s'appelle autrement (ex: self.master), adaptez-le.
            self.root.after(15000, self._reset_pa_lock)
        else:
            self.update_status("Fenêtre Serveur non ouverte", "red")

    def custom_confirm(self, title, message, color="#f39c12"):
        """Affiche une boîte de confirmation adaptée au TOUCHSCREEN."""
        res = {"value": False}
        
        confirm = tk.Toplevel(self.root)
        confirm.overrideredirect(True)
        confirm.config(bg="#2c3e50", bd=4, relief="ridge") # Bordure plus épaisse
        confirm.attributes("-topmost", True)
        
        # --- TAILLE AJUSTÉE POUR LE TOUCHER ---
        # Plus large et plus haut pour laisser de la place aux gros boutons
        w, h = 450, 280 
        x = self.root.winfo_x() + (self.root.winfo_width()//2) - (w//2)
        y = self.root.winfo_y() + (self.root.winfo_height()//2) - (h//2)
        confirm.geometry(f"{w}x{h}+{x}+{y}")

        # Titre plus gros
        tk.Label(confirm, text=title, font=("Arial", 16, "bold"), 
                 bg="#2c3e50", fg=color).pack(pady=15)
        
        # Message plus lisible
        tk.Label(confirm, text=message, font=("Arial", 12), 
                 bg="#2c3e50", fg="white", wraplength=400).pack(pady=10)

        # Cadre pour les boutons
        btn_frame = tk.Frame(confirm, bg="#2c3e50")
        btn_frame.pack(pady=20, fill="x")

        def on_yes():
            res["value"] = True
            confirm.destroy()

        def on_no():
            res["value"] = False
            confirm.destroy()

        # --- BOUTON OUI (Plus gros, hauteur augmentée avec pady) ---
        tk.Button(btn_frame, text="OUI, RESET", 
                  font=("Arial", 12, "bold"), 
                  bg="#e74c3c", fg="white", 
                  bd=0, cursor="hand2",
                  activebackground="#c0392b", # Couleur quand on appuie avec le doigt
                  padx=20, pady=15, # Zone de clic agrandie
                  command=on_yes).pack(side=tk.LEFT, expand=True, padx=20)
        
        # --- BOUTON NON (Plus gros) ---
        tk.Button(btn_frame, text="ANNULER", 
                  font=("Arial", 12, "bold"), 
                  bg="#95a5a6", fg="white", 
                  bd=0, cursor="hand2",
                  activebackground="#7f8c8d",
                  padx=20, pady=15, # Zone de clic agrandie
                  command=on_no).pack(side=tk.LEFT, expand=True, padx=20)

        confirm.grab_set()
        self.root.wait_window(confirm)
        return res["value"]

    def _reset_serial_adapters(self):
        """Réinitialise les adaptateurs après confirmation."""
        # On demande confirmation avec la box custom
        if not self.custom_confirm("CONFIRMATION", "Voulez-vous vraiment relancer les adaptateurs série ?"):
            return

        self.update_status("Réinitialisation en cours...", "#f39c12")
        
        try:
            # 1. On tue l'ancien proprement (ta nouvelle fonction magique)
            if hasattr(self, 'reader') and self.reader:
                self.reader.stop_reader()
            
            # 2. On attend 0.5s et on relance
            self.root.after(500, self._start_new_reader)
            
        except Exception as e:
            self.update_status(f"Erreur Reset: {e}", "#e74c3c")

    def _start_new_reader(self):
        """Lance physiquement le nouveau lecteur."""
        try:
            from serial_reader import SerialReader
            import threading
            
            # Recréation
            self.reader = SerialReader(self.db_manager)
            
            # Démarrage
            self.reader.start()
            
            self.update_status("Adaptateurs KDS en ligne.", "#2ecc71")
        except Exception as e:
            self.update_status(f"Échec redémarrage: {e}", "#e74c3c")

    def _reset_pa_lock(self):
        """Réactive le bouton PA après le délai."""
        self.pa_spam_lock = False
        if hasattr(self, 'btn_flash_pa'):
            self.btn_flash_pa.config(state=tk.NORMAL, bg='#e74c3c')
        self.update_status("Bouton PA prêt", "green")

    def update_button_counts(self):
        """Calcule les totaux depuis la DB et met à jour le texte des boutons."""
        # On récupère TOUTES les listes classées par le DBManager
        all_pending = self.db_manager.get_pending_orders()
        
        c_liv = len(all_pending.get('LIVRAISON', []))
        c_livreur = len(all_pending.get('LIVREUR', []))
        c_pa = len(all_pending.get('POUR EMPORTER', []))
        c_salle = len(all_pending.get('COMMANDE', []))
        
        # Correction : On ajoute bien c_livreur ici !
        total = c_liv + c_livreur + c_pa + c_salle

        # Mise à jour des textes sur les boutons
        if hasattr(self, 'btn_tout'): 
            self.btn_tout.config(text=f"TOUT ({total})")
            
        if hasattr(self, 'btn_interieur'): 
            self.btn_interieur.config(text=f"SALLE ({c_salle})")
            
        if hasattr(self, 'btn_livraison'): 
            self.btn_livraison.config(text=f"LIVRAISON ({c_liv})")
            
        if hasattr(self, 'btn_livreur'): 
            self.btn_livreur.config(text=f"LIVREUR ({c_livreur})")
            
        if hasattr(self, 'btn_pa'): 
            self.btn_pa.config(text=f"EMPORTER ({c_pa})")
    def _update_top_clock(self):
        """Met à jour le compteur et l'heure à droite en jaune."""
        try:
            now = datetime.now().strftime("%H:%M:%S")
            total_orders = len(self.active_postits)
            
            # Texte formaté
            title_text = f"📦 COMMANDES : {total_orders}   |   🕒 {now}"
            
            if hasattr(self, 'top_title_label') and self.top_title_label.winfo_exists():
                self.top_title_label.config(text=title_text)
            
            self.root.after(1000, self._update_top_clock)
        except Exception as e:
            logging.error(f"Erreur horloge: {e}")

    
    def _switch_tab(self, tab_name):
        """Gère la sélection et maintient les compteurs globaux à jour en tout temps."""
        
        # Couleurs pour le feedback visuel
        COLORS = {
            "TOUT": {"on": "#3498db", "off": "#34495e"},
            "COMMANDE": {"on": "#e67e22", "off": "#5d4037"}, 
            "LIVRAISON": {"on": "#27ae60", "off": "#1b5e20"},
            "LIVREUR": {"on": "#1abc9c", "off": "#16a085"}, # Couleur distincte pour livreur
            "POUR EMPORTER": {"on": "#8e44ad", "off": "#4a235a"}
        }

        # --- 1. LOGIQUE DE SÉLECTION (TOGGLE) ---
        if tab_name == "TOUT":
            self.all_selected = True
            for key in self.active_filters:
                self.active_filters[key] = True
        else:
            self.active_filters[tab_name] = not self.active_filters.get(tab_name, True)
            self.all_selected = all(self.active_filters.values())

        # --- 2. CALCUL DES COMPTEURS RÉELS (DEPUIS LA DB) ---
        all_pending = self.db_manager.get_pending_orders()
        
        c_liv = len(all_pending.get('LIVRAISON', []))
        c_livreur = len(all_pending.get('LIVREUR', []))
        c_pa = len(all_pending.get('POUR EMPORTER', []))
        c_salle = len(all_pending.get('COMMANDE', []))
        
        # Le total inclut maintenant les 4 catégories
        total = c_liv + c_livreur + c_pa + c_salle

        # --- 3. MISE À JOUR VISUELLE DES BOUTONS ---
        
        # Bouton TOUT
        tout_color = COLORS["TOUT"]["on"] if self.all_selected else COLORS["TOUT"]["off"]
        self.btn_tout.config(
            text=f"TOUT ({total})",
            bg=tout_color, 
            relief='sunken' if self.all_selected else 'flat'
        )

        # Bouton COMMANDE (Salle)
        is_cmd = self.active_filters["COMMANDE"]
        self.btn_interieur.config(
            text=f"SALLE ({c_salle})",
            bg=COLORS["COMMANDE"]["on"] if is_cmd else COLORS["COMMANDE"]["off"],
            relief='sunken' if is_cmd else 'flat'
        )

        # Bouton LIVRAISON (Format Long 999)
        is_liv = self.active_filters["LIVRAISON"]
        self.btn_livraison.config(
            text=f"LIVRAISON ({c_liv})",
            bg=COLORS["LIVRAISON"]["on"] if is_liv else COLORS["LIVRAISON"]["off"],
            relief='sunken' if is_liv else 'flat'
        )

        # Bouton LIVREUR (Format Petit 777)
        is_livreur = self.active_filters["LIVREUR"]
        self.btn_livreur.config( # Correction ici: self.btn_livreur au lieu de btn_livraison
            text=f"LIVREUR ({c_livreur})",
            bg=COLORS["LIVREUR"]["on"] if is_livreur else COLORS["LIVREUR"]["off"],
            relief='sunken' if is_livreur else 'flat'
        )

        # Bouton POUR EMPORTER (888)
        is_pa = self.active_filters["POUR EMPORTER"]
        self.btn_pa.config(
            text=f"EMPORTER ({c_pa})",
            bg=COLORS["POUR EMPORTER"]["on"] if is_pa else COLORS["POUR EMPORTER"]["off"],
            relief='sunken' if is_pa else 'flat'
        )

        # --- 4. APPLICATION DU FILTRE SUR L'ÉCRAN ---
        self.refresh_orders(force_sound_off=True)
    def _open_serveur_window(self):
        """Ouvre la fenêtre de suivi des commandes pour les serveuses."""
        if self.serveur_window and self.serveur_window.winfo_exists():
            self.serveur_window.lift()
            self.update_status("Fenêtre Serveuses déjà ouverte.", '#2980b9')
            return

        try:
            # 🌟 CORRECTION 1: Passer l'instance KDSGUI (self) à ServeurWindow
            self.serveur_window = ServeurWindow(self.root, self)
            
            # 🌟 CORRECTION 2: Utiliser la méthode on_close de ServeurWindow
            # Cette méthode gère déjà la mise à jour de self.serveur_window = None via l'instance KDSGUI
            self.serveur_window.protocol("WM_DELETE_WINDOW", self.serveur_window.on_close)
            
            self.update_status("Fenêtre de suivi des Serveuses ouverte.", '#3498db')
            
        except Exception as e:
            logger.error(f"Erreur lors du lancement de ServeurWindow: {e}")
            messagebox.showerror("Erreur", f"Échec du lancement de ServeurWindow: {e}")
            self.serveur_window = None

    def _close_serveur_window(self):
        """Gère la fermeture de la fenêtre ServeurWindow."""
        if self.serveur_window:
            self.serveur_window.on_close()
            self.serveur_window = None
            self.update_status("Fenêtre de suivi des Serveuses fermée.", '#3498db')
            
    def update_serveur_window(self,
        bill_id: str,
        table_number: str,
        items_overstruck: list,
        server_name: str = ""  # <- valeur par défaut si on ne connaît pas la serveuse
    ):
        """
        Appelée par OrderPostIt lors d'une rature.
        Transmet l'information à la ServeurWindow si elle est ouverte.
        """
        if self.serveur_window and self.serveur_window.winfo_exists():
            self.serveur_window.update_table(
                bill_id,
                table_number,
                items_overstruck,
                server_name=server_name  # <- passe la serveuse
            )

            
    def close_serveur_table(self, bill_id: str):
        """
        Appelée par OrderPostIt lors du statut 'Traitée' ou 'Annulée'.
        """
        if self.serveur_window and self.serveur_window.winfo_exists():
            self.serveur_window.remove_table(bill_id)
            

        
    def _toggle_fullscreen(self, event=None):
        """Active/désactive le mode plein écran."""
        self.fullscreen_state = not self.fullscreen_state
        self.root.attributes("-fullscreen", self.fullscreen_state)
        
    def _exit_fullscreen(self, event=None):
        """Quitte le mode plein écran (ancienne fonction, maintenant gérée par _authenticate_and_exit pour la sécurité)."""
        if self.fullscreen_state:
            self.root.attributes("-fullscreen", False)
            self.fullscreen_state = False
            
    # 🚨 NOUVELLE MÉTHODE : Gestionnaire de signaux (Ctrl+C)
    def _setup_signal_handler(self):
        """Configure le gestionnaire de signal pour intercepter Ctrl+C (SIGINT) sur UNIX/Linux."""
        if os.name != 'nt': # N'est pas nécessaire sur Windows
            try:
                # Intercepte le signal SIGINT (généré par Ctrl+C)
                signal.signal(signal.SIGINT, self._handle_sigint)
            except ValueError:
                # Peut échouer si non exécuté dans le thread principal
                logger.warning("Impossible de configurer le signal handler (pas le thread principal).")

    def _handle_sigint(self, signum, frame):
        """Appelle la méthode d'authentification lorsque Ctrl+C est détecté."""
        logger.info(f"Signal {signum} (SIGINT/Ctrl+C) intercepté. Tentative de sortie sécurisée.")
        self._authenticate_and_exit()

    
    def _toggle_sound(self):
        """
        Active ou désactive le son.
        Cette méthode est appelée lorsque l'utilisateur clique sur le bouton.
        """
        # Inverse la valeur de la variable d'état
        current_state = self.sound_enabled.get()
        self.sound_enabled.set(not current_state)
        
        # Met à jour l'affichage du bouton immédiatement
        self._update_sound_button_text()

        status = "activé" if self.sound_enabled.get() else "désactivé"
        self.update_status(f"Notification sonore {status}.", '#27ae60')
        
    def _update_sound_button_text(self):
        """
        Met à jour le texte (icône) et la couleur du bouton
        en fonction de l'état ON/OFF du son.
        """
        if self.sound_enabled.get():
            text = "🔔 Son ON"
            bg_color = '#27ae60' # Vert
        else:
            text = "🔇 Son OFF"
            bg_color = '#7f8c8d' # Gris
            
        self.sound_button.config(text=text, bg=bg_color)
        
    def _play_new_order_sound(self, order_data=None):
        """Joue un des 4 sons spécifiques selon le numéro de table."""
        if not self.sound_enabled.get() or not winsound:
            return
            
        table_num = str(order_data.get('table_number', '')).upper() if order_data else ""

        # --- 0. EXCLUSION ---
        if table_num == "999":
            return # Pas de son pour les 999

        try:
            # --- 1. LES 888 (Son Grave et Saccadé) ---
            if "888" in table_num:
                # 3 bips graves lents
                for _ in range(3):
                    winsound.Beep(600, 250)
                    self.root.after(100)

            # --- 2. LES LIVRAISONS (Son d'Alerte) ---
            elif "LIV" in table_num:
                # Bip long montant
                winsound.Beep(800, 400)
                winsound.Beep(1000, 200)

            # --- 3. LES PA / POUR EMPORTER (Son Rapide) ---
            elif "PA" in table_num:
                # Triple bip très aigu et sec
                winsound.Beep(1800, 80)
                winsound.Beep(1800, 80)

            # --- 4. LE RESTE (Tables Normales / Salle) ---
            else:
                # Double bip standard original
                winsound.Beep(1200, 200)
                self.root.after(150, lambda: winsound.Beep(1200, 200))

        except Exception as e:
            logging.error(f"Erreur sonore: {e}")

    def add_new_timer(self, name: str, duration_seconds: int, sound_id: int):
        """
        Crée et lance un nouveau widget minuteur flottant (appelé par TimerManagerWindow).
        """
        timer_id = str(uuid.uuid4()) # Génère un ID unique
        
        try:
            # Crée le widget individuel, lui donnant la méthode de nettoyage
            widget = TimerWidget(
                self.root, 
                timer_id, 
                name, 
                duration_seconds, 
                sound_id, 
                self.remove_timer # Callback pour l'auto-nettoyage
            )
            
            # Positionnement du widget (décalage aléatoire par rapport au KDS)
            x_offset = random.randint(100, 400)
            y_offset = random.randint(100, 400)
            widget.geometry(f"+{self.root.winfo_x() + x_offset}+{self.root.winfo_y() + y_offset}")
            
            # Démarre immédiatement le minuteur
            widget.start_timer()
            
            self.active_timers[timer_id] = widget
            self.update_status(f"Nouveau minuteur '{name}' démarré (ID: {timer_id[:8]}).", '#3498db')

        except Exception as e:
            logging.error(f"Erreur lors du lancement d'un TimerWidget individuel: {e}")
            messagebox.showerror("Erreur Minuteur", f"Échec du lancement d'un minuteur: {e}")
            
    def remove_timer(self, timer_id: str):
        """
        Retire la référence du minuteur de la liste active (appelé par TimerWidget).
        """
        if timer_id in self.active_timers:
            # Le widget lui-même a déjà géré l'arrêt des threads et la destruction
            del self.active_timers[timer_id] 
            self.update_status(f"Minuteur {timer_id[:8]} retiré.", '#3498db')


    def _open_timer_manager(self):
        """
        Ouvre la fenêtre de gestion des minuteurs (TimerManagerWindow).
        """
        if self.timer_manager_window and self.timer_manager_window.winfo_exists():
            self.timer_manager_window.lift()
            self.update_status("Fenêtre de gestion des Minuteurs déjà ouverte.", '#3498db')
            return

        try:
            # Ouvre le gestionnaire (en lui passant l'instance de KDSGUI pour le callback)
            self.timer_manager_window = TimerManagerWindow(self.root, self)
            
            # Protocole de nettoyage à la fermeture
            self.timer_manager_window.protocol(
                "WM_DELETE_WINDOW", 
                lambda: self._close_timer_manager(self.timer_manager_window)
            )

            self.update_status("Fenêtre de gestion des Minuteurs ouverte.", '#3498db')

        except Exception as e:
            logging.error(f"Erreur lors du lancement de TimerManagerWindow: {e}")
            messagebox.showerror("Erreur", f"Échec du lancement du gestionnaire de minuteur: {e}")
            if self.timer_manager_window:
                self.timer_manager_window.destroy()
                self.timer_manager_window = None

    def _close_timer_manager(self, window):
        """
        Méthode de nettoyage appelée lorsque la fenêtre de gestion est fermée.
        """
        if window and window.winfo_exists():
            window.on_close() 
            
        self.timer_manager_window = None # Nettoie la référence
        
        self.root.lift() 
        self.update_status("Fenêtre de gestion des Minuteurs fermée.", '#3498db')
    # -------------------------------------------------------------

    # --- NOUVELLES MÉTHODES D'AUTHENTIFICATION ---
    def _authenticate_and_exit(self, event=None):
        """Authentifie avant de fermer l'application."""
        
        # 1. Vérification d'accès par TOTP
        if check_access_password("Quitter l'Application"):
            
            # 2. Afficher la boîte de dialogue personnalisée
            dialog = ExitOptionsDialog(self.root)
            action = dialog.result
            
            if action == "reboot":
                self.update_status("Initialisation du Redémarrage du PC...", '#e67e22')
                self.root.destroy()
                
                # Exécution de la commande de Redémarrage
                if os.name == 'nt':  # Windows
                    subprocess.Popen(['shutdown', '/r', '/t', '1'])
                else:  # Linux/macOS (nécessite des permissions sudo si ce n'est pas le bureau)
                    subprocess.Popen(['sudo', 'shutdown', '-r', 'now'])
                
            elif action == "shutdown":
                self.update_status("Initialisation de l'Arrêt du PC...", '#e74c3c')
                self.root.destroy()
                
                # Exécution de la commande d'Extinction
                if os.name == 'nt':  # Windows
                    subprocess.Popen(['shutdown', '/s', '/t', '1'])
                else:  # Linux/macOS (nécessite des permissions sudo si ce n'est pas le bureau)
                    subprocess.Popen(['sudo', 'shutdown', '-h', 'now'])
                
            else: # action == "cancel" ou fermeture par la croix
                self.update_status("Sortie annulée ou non requise. L'application reste ouverte.", '#f1c40f')
        
        else:
            self.update_status("Tentative de sortie de l'application refusée (Authentification échouée).", 'red')

    def _authenticate_and_open_maindish_config(self):
        """Authentifie avant d'ouvrir la fenêtre de configuration des plats."""
        if check_access_password("Configuration Plats Principaux"):
            self._open_maindish_config() # Appel de la méthode sans authentification
        else:
            self.update_status("Accès à la configuration des plats refusé (Authentification échouée).", 'red')
    # ---------------------------------------------

    def _create_main_frames(self):
        """Crée les cadres principaux : Header/Status et PostitSelector."""
        
        # 1. Cadre de statut (en bas)
        self.status_frame = tk.Frame(self.root, bg=CARD_BG, height=30)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        # Label de statut (à gauche)
        self.status_label = tk.Label(self.status_frame, text="Système KDS démarré.", fg=COLOR_TEXT, bg=CARD_BG, anchor='w')
        self.status_label.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        self.print_var_file = 'imprimante_var.json'
        initial_status = True # Par défaut True si le fichier n'existe pas

        if os.path.exists(self.print_var_file):
            try:
                with open(self.print_var_file, 'r') as f:
                    data = json.load(f)
                    initial_status = data.get("print_enabled", True)
            except Exception:
                initial_status = True

        # Sauvegarde de l'état dans l'objet self
        self.print_enabled = initial_status

        

        # ⭐ NOUVEAU: Bouton pour Quitter l'application (Authentifié)
        tk.Button(self.status_frame, 
                  text="❌ Quitter",
                  command=self._authenticate_and_exit,
                  font=('Segoe UI', 12, 'bold'),
                  bg='#c0392b', fg='white', relief=tk.FLAT, bd=0 # ROUGE
        ).pack(side=tk.RIGHT, padx=5)

        # ⭐ Bouton de la Corbeille (en ROUGE)
        tk.Button(self.status_frame, 
                  text="🗑️ Corbeille",
                  command=self._open_trash_window,
                  font=('Segoe UI', 12, 'bold'),
                  bg='#c0392b', fg='white', relief=tk.FLAT, bd=0 # ROUGE demandé
        ).pack(side=tk.RIGHT, padx=5)

        # Bouton de Consultation des Ventes (à droite)
        #tk.Button(self.status_frame, 
        #          text="📈 Ventes",
        #          command=self._open_consultation_window, # Appelle la nouvelle méthode sécurisée
        #          font=('Segoe UI', 12, 'bold'),
        #          bg='#2980b9', fg='white', relief=tk.FLAT, bd=0
        #).pack(side=tk.RIGHT, padx=5)

        # ⭐ Bouton de Configuration des Plats Principaux (Authentifié)
        tk.Button(self.status_frame, 
                  text="⚙️-P",
                  command=self._authenticate_and_open_maindish_config, # Authentification OBLIGATOIRE
                  font=('Segoe UI', 12, 'bold'),
                  bg='#9b59b6', fg='white', relief=tk.FLAT, bd=0
        ).pack(side=tk.RIGHT, padx=5)

        tk.Button(self.status_frame, 
                  text="⚙️-K",
                  command=self._authenticate_and_open_konstant_manager, # Commande ajoutée en étape 1
                  font=('Segoe UI', 12, 'bold'),
                  bg='#8e44ad', fg='white', relief=tk.FLAT, bd=0 # Nouvelle couleur
        ).pack(side=tk.RIGHT, padx=5)

        tk.Button(self.status_frame,
            text="⚙️-G", # Changé pour être plus pertinent au menu
            command=self._open_config_menu, 
            font=('Segoe UI', 12, 'bold'),
            bg='#8e44ad', fg='white', relief=tk.FLAT, bd=0 # Orange/Ambre
        ).pack(side=tk.RIGHT, padx=5)

        # Bouton d'accès aux réglages et logs
        self.print_toggle_button = tk.Button(
            self.status_frame,
            text="⚙️-L", 
            command=self._open_log_viewer,
            font=('Segoe UI', 12, 'bold'),
            bg='#8e44ad',
            fg='white',
            bd=0,
            relief=tk.FLAT
        )
        self.print_toggle_button.pack(side=tk.RIGHT, padx=5)

        tk.Button(self.status_frame, 
                  text="⏱ Minuteur",
                  command=self._open_timer_manager, 
                  font=('Segoe UI', 12, 'bold'),
                  # ⭐ CORRECTION : Couleur de fond changée en vert (#2ecc71)
                  bg='#2ecc71', 
                  fg='white', 
                  relief=tk.FLAT, 
                  bd=0
        ).pack(side=tk.RIGHT, padx=5)

        tk.Button(self.status_frame, text="👩‍🍳 Suivi", 
                command=self._open_serveur_window,
                font=('Segoe UI', 12, 'bold'), 
                bg='#3498db', # Bleu
                fg='white', 
                relief=tk.FLAT, bd=0
        ).pack(side=tk.RIGHT, padx=5)

        # Bouton Impression (Turquoise)
        # Détermination du texte et de la couleur selon l'état lu
        btn_text = "🖨️ : ON" if self.print_enabled else "🖨️ : OFF"
        btn_bg = '#1abc9c' if self.print_enabled else '#95a5a6'

        # Création du bouton avec les bonnes valeurs de départ
        self.btn_print_toggle = tk.Button(self.status_frame, 
                text=btn_text, 
                command=self.toggle_print_status,
                font=('Segoe UI', 12, 'bold'), 
                bg=btn_bg, 
                fg='white', 
                relief=tk.FLAT, bd=0
        )
        self.btn_print_toggle.pack(side=tk.RIGHT, padx=5)
        
        # Positionnement (ajustez side/padx/pady selon l'agencement souhaité)
        self.print_toggle_button.pack(side=tk.RIGHT, padx=5, pady=5)

        self.sound_button = tk.Button(self.status_frame,
                  text="", # Laissez le texte initial vide, il sera défini par la méthode ci-dessous
                  command=self._toggle_sound, 
                  font=('Segoe UI', 12, 'bold'),
                  # La couleur sera gérée par la méthode _update_sound_button_text
                  bg='#27ae60', fg='white', relief=tk.FLAT, bd=0 
        )
        self.sound_button.pack(side=tk.RIGHT, padx=5)

        # Bouton Nettoyage Manuel (Livraison/Emporter)
        self.clean_button = tk.Button(self.status_frame,
                  text="🧹 NETTOYER", 
                  command=self._manual_clean_types, 
                  font=('Segoe UI', 12, 'bold'),
                  bg='#2980b9', # Bleu
                  fg='white', 
                  relief=tk.FLAT, 
                  bd=0 
        )
        self.clean_button.pack(side=tk.RIGHT, padx=5)

        #tk.Button(self.status_frame,
        #          text="🔄 RESET",
        #          command=self._reset_serial_adapters,
        #          font=('Segoe UI', 12, 'bold'),
        #          bg='#e74c3c',  # Rouge pour indiquer une action technique
        #          fg='white', 
        #          relief=tk.FLAT, 
        #          bd=0,
        #          padx=10
        #).pack(side=tk.RIGHT, padx=5)

        # Nouveau bouton INGRÉDIENTS à la place du RESET
        tk.Button(self.status_frame,
                text="🍔 INGRÉDIENTS",
                command=self._show_burger_recipes, # Nouvelle méthode
                font=('Segoe UI', 12, 'bold'),
                bg='#2ecc71',  # Vert pour un aspect menu/nourriture
                fg='white', 
                relief=tk.FLAT, 
                bd=0,
                padx=10
        ).pack(side=tk.RIGHT, padx=5)

        tk.Button(self.status_frame,
                  text="📊 KDS",
                  command=self._open_total_widget, # Nouvelle fonction
                  font=('Segoe UI', 12, 'bold'),
                  bg='#f39c12', fg='white', relief=tk.FLAT, bd=0 # Orange/Ambre
        ).pack(side=tk.RIGHT, padx=5)

        

        self.btn_flash_pa = tk.Button(self.status_frame,
                text="🚨 PA",
                command=self._trigger_pa_flash,
                font=('Segoe UI', 12, 'bold'),
                bg='#e74c3c', fg='white', relief=tk.FLAT, bd=0
        )
        self.btn_flash_pa.pack(side=tk.RIGHT, padx=5)

        
        # 🔑 CRUCIAL: Appelez cette méthode immédiatement pour définir le texte initial ("🔔 Son ON") et la couleur.
        self._update_sound_button_text()

        
        self.postit_selector = PostitSelector(
            self.root, 
            self.db_manager, 
            SERVICE_TYPES,
            kds_gui_instance=self  # <--- Ceci doit être passé
        )
        self.postit_selector.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self._update_top_clock()


    def _show_burger_recipes(self):
        """Affiche le guide des recettes en chargeant TOUT depuis menu_config.json."""
        import textwrap
        import json
        import os

        # --- CHARGEMENT DU JSON ---
        config_file = "menu_ingredient.json"
        if not os.path.exists(config_file):
            messagebox.showerror("Erreur", f"Le fichier {config_file} est introuvable !")
            return

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                tags_config = data.get("couleurs_tags", {})
                categories = data.get("categories", {})
        except Exception as e:
            messagebox.showerror("Erreur JSON", f"Impossible de lire le fichier : {e}")
            return

        recipe_win = tk.Toplevel(self.root)
        recipe_win.configure(bg="#2c3e50")
        recipe_win.attributes("-topmost", True)
        
        # Fenêtre extra-large (1800px) décalée de 70px à gauche
        w, h = 1800, 850 
        x = 70 
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        recipe_win.geometry(f"{w}x{h}+{x}+{y}")
        recipe_win.overrideredirect(True) 

        main_frame = tk.Frame(recipe_win, bg="#2c3e50", bd=4, relief="ridge")
        main_frame.pack(fill="both", expand=True)

        tk.Label(main_frame, text="📖 GUIDE DES RECETTES (Chargé depuis JSON)", font=("Arial", 28, "bold"), 
                bg="#2c3e50", foreground="#f1c40f").pack(pady=20)

        # Style des Onglets
        style = ttk.Style()
        style.theme_use('default')
        style.configure("TNotebook", background="#2c3e50", borderwidth=0)
        style.configure("TNotebook.Tab", font=("Arial", 18, "bold"), padding=[35, 12], background="#95a5a6")
        style.map("TNotebook.Tab", background=[("selected", "#2ecc71")], foreground=[("selected", "white")])

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True, padx=20, pady=10)

        for cat_name, items in categories.items():
            tab = tk.Frame(notebook, bg="#2c3e50")
            notebook.add(tab, text=cat_name)
            
            canvas = tk.Canvas(tab, bg="#2c3e50", highlightthickness=0)
            scroll_y = tk.Scrollbar(tab, orient="vertical", command=canvas.yview, width=45)
            scroll_frame = tk.Frame(canvas, bg="#2c3e50")
            
            canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
            canvas.bind('<Configure>', lambda e, c=canvas: c.itemconfig(canvas_window, width=e.width))
            canvas.configure(yscrollcommand=scroll_y.set)

            for name, ingredients in items.items():
                f = tk.Frame(scroll_frame, bg="#34495e", pady=15, highlightbackground="#2ecc71", highlightthickness=2)
                f.pack(fill="x", pady=8, padx=40)
                
                tk.Label(f, text=name, font=("Arial", 20, "bold"), bg="#34495e", 
                        foreground="#2ecc71", width=24, anchor="w").pack(side="left", padx=30)
                
                wrapped_text = textwrap.fill(ingredients, width=95)
                line_count = wrapped_text.count('\n') + 1

                txt = tk.Text(f, font=("Arial", 18, "bold"), bg="#34495e", 
                            height=line_count, bd=0, highlightthickness=0)
                txt.pack(side="left", fill="x", expand=True)

                # Application des tags de couleur dynamiques
                for tag_name, info in tags_config.items():
                    txt.tag_config(tag_name, foreground=info["color"])
                txt.tag_config("base", foreground="#ffffff")

                # Logique de coloration par mot-clé
                words = wrapped_text.replace('\n', ' \n ').split(' ')
                for word in words:
                    upper_word = word.upper().strip(",. \n")
                    applied_tag = "base"
                    
                    for tag_name, info in tags_config.items():
                        if any(k in upper_word for k in info["keywords"]):
                            applied_tag = tag_name
                            break
                    
                    txt.insert(tk.END, word + " ", applied_tag)
                
                txt.config(state=tk.DISABLED)

            scroll_frame.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.pack(side="left", fill="both", expand=True)
            scroll_y.pack(side="right", fill="y")

        tk.Button(main_frame, text="RETOUR", font=("Arial", 22, "bold"), bg="#e74c3c", 
                foreground="white", command=recipe_win.destroy).pack(side="bottom", pady=20)

    def _manual_clean_types(self):
        """Déclenche manuellement le marquage des commandes spécifiques comme traitées."""
        try:
            # 1. Effectuer l'opération en base de données
            count = self.db_manager.mark_specific_types_as_done_manual()
            
            if count > 0:
                self.update_status(f"Succès: {count} commandes traitées.", "#2ecc71")
                
                # 2. SÉCURITÉ : Utiliser 'after' pour forcer la mise à jour 
                # dans le thread principal de Tkinter (évite les conflits graphiques)
                self.root.after(0, self._refresh_ui_safely)
                
            else:
                self.update_status("Aucune commande Livraison/Emporter à traiter.", "#f1c40f")
                self.update_button_counts()
                
        except Exception as e:
            logging.error(f"Erreur lors du nettoyage manuel : {e}")
            self.update_status("Erreur lors du nettoyage.", "#e74c3c")

    def _refresh_ui_safely(self):
        """Méthode dédiée pour nettoyer l'interface visuelle sans risque de bug."""
        # On supprime physiquement les éléments qui ne sont plus en base
        # ou qui sont marqués 'Traitée'
        to_remove = [bid for bid, postit in self.active_postits.items() 
                     if postit.status == 'Traitée']
        
        for bid in to_remove:
            self._remove_postit(bid) # Appel de votre méthode existante
            
        # Mise à jour finale des compteurs
        self.update_button_counts()

    def toggle_print_status(self):
        """
        Authentifie et bascule l'état de l'impression automatique.
        """
        # 1. Demande le mot de passe (exactement comme pour la config)
        if check_access_password("Bouton Print"):
            try:
                import json
                import os

                file_path = 'imprimante_var.json'
                
                # Lecture de l'état actuel
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        current_status = data.get("print_enabled", True)
                else:
                    current_status = True

                # Inversion
                new_status = not current_status

                # Sauvegarde
                with open(file_path, 'w') as f:
                    json.dump({"print_enabled": new_status}, f)

                # Mise à jour graphique
                if new_status:
                    self.btn_print_toggle.config(
                        text="🖨️ Impression : ON", 
                        bg='#1abc9c' 
                    )
                    self.update_status("Impression automatique activée", "#1abc9c")
                else:
                    self.btn_print_toggle.config(
                        text="🖨️ Impression : OFF", 
                        bg='#95a5a6' 
                    )
                    self.update_status("Impression automatique désactivée", "#e74c3c")

            except Exception as e:
                logger.error(f"Erreur lors du basculement de l'impression: {e}")
                messagebox.showerror("Erreur", f"Impossible de modifier l'état d'impression: {e}")
        
        else:
            # Si l'authentification échoue
            self.update_status("Accès au Bouton Print refusé (Authentification échouée).", 'red')

    def _create_widgets(self):
        """Crée d'autres widgets (comme le TotalWidget)."""
        # Note: Le TotalWidget est créé uniquement lors du premier appel à _open_total_widget
        pass 
    
    def _open_config_menu(self):
        """Ouvre la fenêtre de configuration (ConfigMenu)."""
        
        # Empêche l'ouverture de plusieurs fenêtres
        if hasattr(self, 'config_window') and self.config_window.winfo_exists():
            self.config_window.lift()
            return
        
        # 🎯 CORRECTION DE L'ERREUR :
        # On passe self.master (l'instance tk.Tk ou le master widget) 
        # qui possède l'attribut .tk, au lieu de l'instance KDSGUI (self).
        self.config_window = ConfigMenu(self.master)
    # --- NOUVELLE MÉTHODE : Gère l'ouverture du TotalWidget ---
    def _open_total_widget(self):
        """
        Crée ou affiche le TotalWidget.
        Le TotalWidget est une fenêtre Toplevel flottante.
        """
        # Vérifier si l'instance existe et si la fenêtre est toujours active
        if self.total_widget is None or not self.total_widget.winfo_exists():
            try:
                # La callback est la fonction qui permet au TotalWidget de connaître les bill_ids sélectionnés
                # pour filtrer son affichage, si nécessaire.
                selected_bill_ids_callback = self.postit_selector.get_selected_bill_ids 
                # ⭐ MODIFIÉ: Passe l'instance KDSGUI (self) à TotalWidget
                self.total_widget = TotalWidget(self, self.db_manager, selected_bill_ids_callback)
                # ⭐ NOUVEAU: Définir la taille maximale en vertical (90% de la hauteur)
                screen_height = self.root.winfo_screenheight()
                screen_width = self.root.winfo_screenwidth()

                # Largeur fixe pour le widget (ajustable)
                widget_width = 350
                # 90% de la hauteur de l'écran
                widget_height = int(screen_height * 0.9) 

                # Positionner le widget près du coin supérieur droit (avec une petite marge)
                x_pos = screen_width - widget_width - 10 
                y_pos = 10 

                # Appliquer la géométrie au Toplevel qui est self.total_widget
                self.total_widget.geometry(f"{widget_width}x{widget_height}+{x_pos}+{y_pos}")

                self.total_widget.update_content() # Mise à jour immédiate
                self.update_status("TotalWidget affiché.", '#f39c12')
            except Exception as e:
                logger.error(f"Erreur lors du lancement du TotalWidget: {e}")
                messagebox.showerror("Erreur", f"Échec du lancement du TotalWidget: {e}")
                self.total_widget = None # S'assurer que l'instance est réinitialisée en cas d'échec
        else:
            # Si la fenêtre existe, la mettre en premier plan
            self.total_widget.lift()
            self.total_widget.update_content() # Mise à jour du contenu
            self.update_status("TotalWidget mis à jour et affiché en premier plan.", '#f39c12')
    # ----------------------------------------------------------
    
    
                    
    def _open_log_viewer(self):
        """
        Demande le mot de passe puis propose d'ouvrir les Logs, Simulateurs ou gérer les Ports COM.
        Version complète avec monitoring d'état.
        """
        # 1. Authentification
        if check_access_password("Zone de Maintenance"):
            
            # --- CONFIGURATION POUR L'EXE (PYINSTALLER) ---
            if getattr(sys, 'frozen', False):
                bundle_dir = sys._MEIPASS
                if bundle_dir not in sys.path:
                    sys.path.insert(0, bundle_dir)

            # 2. Fenêtre de sélection
            choice_win = tk.Toplevel(self.root)
            choice_win.title("MENU TECHNIQUE & MAINTENANCE")
            choice_win.geometry("450x600") # Taille ajustée pour tout contenir
            choice_win.config(bg="#2c3e50")
            choice_win.grab_set() 
            choice_win.attributes("-topmost", True)

            # --- TITRE ---
            tk.Label(choice_win, text=" MENU TECHNIQUE ", 
                     font=("Arial", 14, "bold"), bg="#2c3e50", fg="white").pack(pady=15)

            # --- CADRE D'ÉTAT (VOIR SI C'EST ACTIF OU PAS) ---
            status_frame = tk.Frame(choice_win, bg="#34495e", bd=2, relief="groove")
            status_frame.pack(pady=10, fill="x", padx=40)
            
            lbl_status_com = tk.Label(status_frame, text="PORT COM : ANALYSE...", 
                                      font=("Arial", 10, "bold"), bg="#34495e", fg="white")
            lbl_status_com.pack(pady=10)

            # --- LOGIQUE DE VÉRIFICATION AUTOMATIQUE ---
            def update_com_display():
                """Vérifie l'état réel du reader et met à jour l'étiquette chaque seconde."""
                if not choice_win.winfo_exists(): return 
                
                if hasattr(self, 'reader') and self.reader:
                    # Vérification de l'event de stop du SerialReader
                    is_running = not self.reader._stop_event.is_set()
                    if is_running:
                        lbl_status_com.config(text="● PORT COM : ACTIF (ÉCOUTE)", fg="#2ecc71")
                    else:
                        lbl_status_com.config(text="○ PORT COM : ARRÊTÉ / FERMÉ", fg="#e74c3c")
                else:
                    lbl_status_com.config(text="PORT COM : NON INITIALISÉ", fg="orange")
                
                # Relance la vérification dans 1 seconde
                choice_win.after(1000, update_com_display)

            # --- FONCTION GESTION PORTS COM ---
            # --- FONCTION POUR LES MESSAGES PERSONNALISÉS (SANS BARRE DE TITRE) ---
            def custom_alert(title, message, color="#3498db"):
                alert = tk.Toplevel(choice_win)
                alert.overrideredirect(True)  # Supprime la barre de titre, le X et la réduction
                alert.config(bg="#2c3e50", bd=3, relief="ridge")
                alert.attributes("-topmost", True)
                
                # Taille et centrage par rapport au menu technique
                w, h = 350, 180
                x = choice_win.winfo_x() + (choice_win.winfo_width()//2) - (w//2)
                y = choice_win.winfo_y() + (choice_win.winfo_height()//2) - (h//2)
                alert.geometry(f"{w}x{h}+{x}+{y}")

                tk.Label(alert, text=title, font=("Arial", 12, "bold"), 
                         bg="#2c3e50", fg=color).pack(pady=12)
                
                tk.Label(alert, text=message, font=("Arial", 10), 
                         bg="#2c3e50", fg="white", wraplength=300).pack(pady=10)
                
                # Bouton OK unique pour fermer
                tk.Button(alert, text="OK", font=("Arial", 10, "bold"), width=12,
                          bg=color, fg="white", bd=0, cursor="hand2",
                          command=alert.destroy).pack(pady=15)
                
                alert.grab_set() # Bloque l'interaction avec le reste tant que pas cliqué

            # --- LA FONCTION MANAGE_SERIAL MODIFIÉE ---
            def manage_serial(action):
                """Arrête ou recrée une instance du lecteur avec alertes personnalisées."""
                try:
                    # 1. ARRÊT
                    if action == "stop":
                        if hasattr(self, 'reader') and self.reader:
                            self.reader.stop_reader()
                            self.update_status("Port COM : ARRÊTÉ", "orange")
                            custom_alert("SÉRIE", "Lecture du port série arrêtée.", "#e67e22")
                    
                    # 2. REDÉMARRAGE
                    elif action == "start":
                        if hasattr(self, 'reader') and self.reader:
                            if not self.reader._stop_event.is_set():
                                custom_alert("INFO", "Le lecteur est déjà en cours d'exécution.", "#3498db")
                                return
                        
                        from serial_reader import SerialReader
                        import threading
                        
                        # Recréation de l'objet pour éviter le RuntimeError de Thread
                        self.reader = SerialReader(self.db_manager)
                        
                        new_thread = threading.Thread(target=self.reader.start, daemon=True)
                        new_thread.start()
                        
                        self.update_status("Port COM : REDÉMARRÉ", "green")
                        custom_alert("SÉRIE", "Le lecteur a été recréé et relancé avec succès.", "#27ae60")

                except Exception as e:
                    custom_alert("ERREUR COM", f"Échec de l'action : {e}", "#e74c3c")

            # --- FONCTIONS DE LANCEMENT ---
            def launch_logs():
                choice_win.destroy()
                try:
                    import log_view
                    import importlib
                    importlib.reload(log_view)
                    self.log_window = log_view.LogViewWindow(self.root)
                    self.update_status("Logs ouverts.", "green")
                except Exception as e:
                    messagebox.showerror("Erreur Logs", f"Erreur: {e}")

            def launch_simulator():
                choice_win.destroy()
                try:
                    import testprint
                    import importlib
                    importlib.reload(testprint)
                    sim_win = tk.Toplevel(self.root)
                    testprint.POSSimulatorGUI(master=sim_win)
                except Exception as e:
                    messagebox.showerror("Erreur Simulateur", f"Échec : {e}")

            def launch_tcp_print():
                try:
                    import test_print_net
                    import importlib
                    importlib.reload(test_print_net)
                    sim_win = tk.Toplevel(self.root)
                    sim_win.title("Diagnostic Réseau & TCP Print")
                    test_print_net.ProfessionalPOSDebugger(master=sim_win)
                except Exception as e:
                    messagebox.showerror("Erreur TCP", f"Échec : {e}")

            # --- BOUTONS PRINCIPAUX ---
            tk.Button(choice_win, text="📋 VOIR LES LOGS", font=("Arial", 11, "bold"), 
                      bg="#3498db", fg="white", width=30, pady=10, command=launch_logs).pack(pady=5)

            tk.Button(choice_win, text="🌐 SIMULATEUR TCP & RÉSEAU", font=("Arial", 11, "bold"), 
                      bg="#A2D149", fg="white", width=30, pady=10, command=launch_tcp_print).pack(pady=5)

            tk.Button(choice_win, text="🖨️ SIMULATEUR D'IMPRESSION", font=("Arial", 11, "bold"), 
                      bg="#9b59b6", fg="white", width=30, pady=10, command=launch_simulator).pack(pady=5)

            # --- SECTION GESTION COM (CORRIGÉE) ---
            tk.Label(choice_win, text="--- ACTIONS MATÉRIEL (PORTS COM) ---", 
                     font=("Arial", 10, "italic"), bg="#2c3e50", fg="#bdc3c7").pack(pady=15)

            # On crée d'abord le cadre (frame_com)
            frame_com = tk.Frame(choice_win, bg="#2c3e50")
            frame_com.pack(pady=5)

            # Puis on met les boutons dedans
            tk.Button(frame_com, text="⛔ ARRÊTER COM", font=("Arial", 10, "bold"), 
                      bg="#e74c3c", fg="white", width=14, pady=12, 
                      command=lambda: manage_serial("stop")).pack(side=tk.LEFT, padx=5)

            tk.Button(frame_com, text="🔄 RELANCER COM", font=("Arial", 10, "bold"), 
                      bg="#27ae60", fg="white", width=14, pady=12, 
                      command=lambda: manage_serial("start")).pack(side=tk.LEFT, padx=5)

            # Lancement initial de la vérification d'état
            update_com_display()

            # Liaison touche Entrée -> Logs par défaut
            choice_win.bind('<Return>', lambda e: launch_logs())
            
        else:
            self.update_status("Accès refusé.", "red")

    def _open_config_menu(self):
        """
        Authentifie et lance le DBKonstantesManager dans une fenêtre modale Toplevel.
        """
        # L'utilisation de 'check_access_password' est supposée être définie ailleurs.
        if check_access_password("Configuration Gui et Autre"):
            try:
                # ⭐ CORRECTION: Lance la nouvelle fenêtre modale au lieu de subprocess
                self.config_window = ConfigMenu(self.master)
                self.update_status("Configuration Gui et Autre a été lancé.", 'green')
                
            except Exception as e:
                # Cette erreur inclura l'ImportError si le fichier n'est pas trouvé
                logger.error(f"Erreur lors du lancement de Configuration Gui et Autre: {e}")
                messagebox.showerror("Erreur de Lancement", 
                                    f"Impossible de lancer Configuration Gui et Autre. Erreur: {e}")
                self.update_status("Échec du lancement Configuration Gui et Autre", 'red')
        else:
            self.update_status("Accès à Configuration Gui et Autre refusé (Authentification échouée).", 'red')

    def _authenticate_and_open_konstant_manager(self):
        """
        Authentifie et lance le DBKonstantesManager dans une fenêtre modale Toplevel.
        """
        # L'utilisation de 'check_access_password' est supposée être définie ailleurs.
        if check_access_password("Éditeur de Constantes KDS"):
            try:
                # ⭐ CORRECTION: Lance la nouvelle fenêtre modale au lieu de subprocess
                KonstantesManagerWindow(self.master)
                self.update_status("L'éditeur de constantes a été lancé.", 'green')
                
            except Exception as e:
                # Cette erreur inclura l'ImportError si le fichier n'est pas trouvé
                logger.error(f"Erreur lors du lancement de l'éditeur de constantes: {e}")
                messagebox.showerror("Erreur de Lancement", 
                                    f"Impossible de lancer l'éditeur de constantes. Erreur: {e}")
                self.update_status("Échec du lancement de KonstantManager.", 'red')
        else:
            self.update_status("Accès à l'éditeur de constantes refusé (Authentification échouée).", 'red')
    # ⭐ MÉTHODE: Ouvre la fenêtre de la Corbeille (Rouge)
    def _open_trash_window(self):
        """Ouvre la Corbeille (commandes Traitées/Annulées) dans une fenêtre Toplevel."""
        if not isinstance(self.db_manager, DBManager):
            self.update_status("ERREUR: Le gestionnaire de base de données n'est pas prêt.", 'red')
            messagebox.showerror("Erreur", "Le gestionnaire de base de données n'est pas prêt. Vérifiez l'initialisation.")
            return

        # ⭐ NOUVEAU: Vérifier si la fenêtre est déjà ouverte
        if self.trash_window and self.trash_window.winfo_exists():
            self.trash_window.lift()
            self.update_status("Fenêtre de la Corbeille affichée en premier plan.", '#c0392b')
            return

        # Lancer l'application de la corbeille (TrashWindow hérite de Toplevel)
        try:
            # On passe self.root comme master (la fenêtre principale) et on stocke l'instance
            self.trash_window = TrashWindow(self.root, self.db_manager, self) # ⭐ MODIFIÉ
            self.update_status("Fenêtre de la Corbeille ouverte.", '#c0392b') # Afficher la couleur rouge dans le statut
        except Exception as e:
            logger.error(f"Erreur lors du lancement de TrashWindow: {e}")
            messagebox.showerror("Erreur", f"Échec du lancement de la Corbeille: {e}")
            self.trash_window = None # Réinitialisation en cas d'erreur critique
            return

    def _open_consultation_window(self):
        """
        Ouvre la fenêtre de consultation des ventes.
        Gère l'authentification, l'instance unique et le nettoyage de la référence.
        """
        if not check_access_password("Consultation des Ventes"):
            self.update_status("Accès à la consultation des ventes refusé (Authentification échouée).", 'red')
            return

        if not isinstance(self.db_manager, DBManager):
            self.update_status("ERREUR: Le gestionnaire de base de données n'est pas prêt.", 'red')
            messagebox.showerror("Erreur", "Le gestionnaire de base de données n'est pas prêt.")
            return

        # 1. Vérifier si la fenêtre existe déjà
        if self.consultation_window is not None:
            try:
                if self.consultation_window.winfo_exists():
                    self.consultation_window.lift()
                    self.update_status("Fenêtre de Consultation affichée en premier plan.", '#2980b9')
                    return
            except tk.TclError:
                # La fenêtre a été détruite mais la référence n'a pas été nettoyée
                self.consultation_window = None

        try:
            # 2. Lancer l'application de consultation
            # On importe ici pour éviter les imports circulaires si nécessaire
            from consultation import ConsultationWindow
            
            # Création de l'instance
            new_win = ConsultationWindow(self.root, self.db_manager)
            
            # --- CORRECTION CRUCIALE ---
            # On vérifie que 'new_win' n'est pas None avant de continuer
            if new_win is not None:
                self.consultation_window = new_win
                
                # 3. Ajouter le protocole de fermeture
                self.consultation_window.protocol(
                    "WM_DELETE_WINDOW", 
                    lambda: self._close_consultation_window(self.consultation_window)
                )
                self.update_status("Fenêtre de Consultation des Ventes ouverte.", '#2980b9')
            else:
                raise ValueError("La fenêtre de consultation n'a pas pu être initialisée (retourne None).")

        except Exception as e:
            logger.error(f"Erreur lors du lancement de ConsultationWindow: {e}")
            messagebox.showerror("Erreur", f"Échec du lancement de la fenêtre de consultation: {e}")
            self.consultation_window = None

    def _close_consultation_window(self, window_ref):
        """Nettoie la référence et détruit la fenêtre."""
        if window_ref:
            window_ref.destroy()
        self.consultation_window = None
        self.update_status("Fenêtre de consultation fermée.", "gray")

    def _open_maindish_config(self):
        """Ouvre le gestionnaire des plats principaux dans une fenêtre Toplevel (appelé après authentification)."""
        if not self.main_dish_db_manager:
            self.update_status("ERREUR: Le gestionnaire de plats principaux n'est pas initialisé.", 'red')
            messagebox.showerror("Erreur", "Le gestionnaire de plats principaux n'est pas prêt. Vérifiez les imports/initialisation.")
            return

        # 1. Créer une fenêtre Toplevel (non bloquante)
        config_window = tk.Toplevel(self.root)
        config_window.title("Gestion des Plats Principaux")
        
        # 2. Configuration de la fenêtre 
        config_window.geometry("650x800") 
        
        # 3. Lancer l'application de gestion des plats
        try:
            MainDishApp(config_window)
        except Exception as e:
            logger.error(f"Erreur lors du lancement de MainDishApp: {e}")
            messagebox.showerror("Erreur", f"Échec du lancement de la configuration des plats principaux: {e}")
            config_window.destroy()
            return
            
        self.update_status("Fenêtre de configuration des plats principaux ouverte.")
    
    # ⭐ NOUVELLE MÉTHODE PUBLIQUE: Appelée par TrashWindow
    def refresh_orders(self, force_sound_off=False):
        """
        Met à jour les filtres et déclenche la vérification intelligente.
        """
        # 1. Déterminer le texte du statut selon les filtres cochés
        if self.all_selected:
            types_to_fetch = ["COMMANDE", "LIVRAISON", "LIVREUR", "POUR EMPORTER"]
            status_text = "Affichage : TOUT"
        else:
            types_to_fetch = [k for k, v in self.active_filters.items() if v]
            status_text = "Aucun filtre" if not types_to_fetch else f"Filtres : {', '.join(types_to_fetch)}"

        # 2. Mettre à jour la barre de statut en haut
        self.update_status(status_text, "#3498db")

        # 3. LANCER LA VÉRIFICATION (C'est elle qui ajoutera/supprimera proprement)
        # On ne fait SURTOUT PAS de .clear() ou de .destroy() ici.
        self.check_for_new_orders(is_refresh=True)

    def _change_type_filter(self, type_selection):
        """
        Déclenche la logique de bascule (Toggle) pour l'onglet sélectionné.
        """
        # Appelle la fonction qui gère les couleurs et les états True/False
        self._switch_tab(type_selection)

    def update_status(self, message: str, color: str = COLOR_TEXT):
        """Met à jour le message de statut en bas de l'écran."""
        self.status_label.config(text=f"[{datetime.now().strftime('%H:%M:%S')}] {message}", fg=color)
        logger.info(message)

    def check_for_new_orders(self, is_refresh=False):
        """Vérifie les commandes sans détruire l'état visuel (ratures)."""
        current_orders_raw = self.db_manager.get_pending_orders()

        # Signature globale pour éviter de travailler pour rien
        # Par une signature qui regarde les IDs et les items (ce qui change vraiment) :
        items_signature = {order['id']: order.get('items') for service in current_orders_raw.values() for order in service}
        state_signature = str(items_signature)
        if not is_refresh and hasattr(self, '_last_db_signature') and self._last_db_signature == state_signature:
            self.root.after(getattr(self, 'REFRESH_RATE_MS', 1500), self.check_for_new_orders)
            return
        self._last_db_signature = state_signature

        flat_active_orders = {}
        for service, orders in current_orders_raw.items():
            for order in orders:
                s_type = order.get('service_type', 'COMMANDE')
                if not self.active_filters.get(s_type, False): continue 
                flat_active_orders[order['id']] = order

        new_ids = set(flat_active_orders.keys())
        old_ids = set(self.active_postits.keys())

        changed_detected = False
        new_orders_found = False 

        # --- SUPPRESSION ---
        ids_to_remove = old_ids - new_ids
        if ids_to_remove:
            changed_detected = True
            for uid in ids_to_remove:
                self._remove_postit(uid)

        # --- AJOUT ---
        ids_to_add = new_ids - old_ids
        if ids_to_add:
            changed_detected = True
            new_orders_found = True
            for uid in ids_to_add:
                self._create_new_postit(flat_active_orders[uid])

        # --- MISE À JOUR DES EXISTANTS (SÉCURISÉE) ---
        ids_to_check = new_ids & old_ids
        for uid in ids_to_check:
            order_data = flat_active_orders[uid]
            postit = self.active_postits[uid]
            
            # Signature du contenu (les plats)
            current_items_str = str(order_data.get('items', []))
            last_items_str = getattr(postit, '_last_items_content', "")

            # A) Si les PLATS ont changé (ex: extra ajouté) : On reconstruit
            if current_items_str != last_items_str:
                changed_detected = True # Force le re-pack car la taille change
                postit.order_data = order_data
                postit._last_items_content = current_items_str
                for widget in postit.winfo_children(): widget.destroy()
            
            # B) Si SEUL le statut a changé : On ne touche PAS au UI des plats
            elif postit.status != order_data['status']:
                # On ne met PAS changed_detected à True ici ! 
                # C'est la clé pour garder les ratures.
                postit.status = order_data['status']
                if hasattr(postit, 'update_status_ui'):
                    postit.update_status_ui(order_data['status'])
                elif hasattr(postit, 'refresh_status_color'):
                    postit.refresh_status_color()

        # --- FINALISATION ---
        # On ne rafraîchit les colonnes que si c'est strictement nécessaire 
        # (nouvel ajout, suppression ou changement de texte)
        if changed_detected:
            if hasattr(self, 'postit_selector'):
                self.postit_selector.update_column_titles()
            self.update_button_counts()

        if new_orders_found and not is_refresh:
            self._play_new_order_sound(None)

        self.root.after(getattr(self, 'REFRESH_RATE_MS', 1500), self.check_for_new_orders)

    def _create_new_postit(self, order_data: dict):
        """Crée une nouvelle carte de commande et l'ajoute au sélecteur."""
        # ⭐ On utilise l'ID technique (unique) pour la gestion interne
        unique_id = order_data['id']
        bill_id = order_data['bill_id']
        
        # Création de l'objet OrderPostIt
        new_postit = OrderPostIt(
            master_selector=self.postit_selector, 
            order_data=order_data, 
            db_manager=self.db_manager,
            service_types=self.postit_selector.service_types, 
            kds_gui_instance=self
        )
        
        # ⭐ On stocke avec unique_id pour correspondre à check_for_new_orders
        self.active_postits[unique_id] = new_postit
        
        # ⭐ MÉMOIRE ANTI-EFFACEMENT : On fixe le contenu dès la création
        # Cela empêche check_for_new_orders de croire que c'est nouveau à 1.5s
        new_postit._last_items_content = str(order_data.get('items', []))
        new_postit.status = order_data.get('status')
        
        # Mise à jour de la barre de statut
        self.update_status(f"Nouvelle commande ajoutée: Facture #{bill_id}.", '#3498db')


    def _remove_postit(self, bill_id: str):
        """Retire une carte de commande de l'interface et des listes de suivi en toute sécurité."""
        
        # 1. Vérifier si la carte existe bien dans notre dictionnaire de suivi
        if bill_id in self.active_postits:
            try:
                # 2. Extraire l'objet postit avant de le supprimer du dictionnaire
                postit = self.active_postits.pop(bill_id)
                
                # 3. 🎯 Retirer la table de la fenêtre Serveuse si elle est ouverte et valide
                if hasattr(self, 'serveur_window') and self.serveur_window:
                    try:
                        # On vérifie si la fenêtre existe vraiment dans le système Tkinter
                        if self.serveur_window.winfo_exists():
                            self.serveur_window.remove_table(bill_id)
                    except Exception as e:
                        logging.debug(f"Erreur lors du retrait de la table serveur : {e}")

                # 4. Suppression physique du widget
                # Vérifier si le widget existe encore avant de détruire
                if postit and postit.winfo_exists():
                    postit.destroy()
                
                # 5. Mise à jour des compteurs et de l'affichage global
                self.update_button_counts()
                
                logging.info(f"Post-it {bill_id} supprimé avec succès.")
                
            except Exception as e:
                # On capture l'erreur ici pour éviter de bloquer le thread principal
                logging.error(f"Erreur critique lors de la suppression du post-it {bill_id} : {e}")
        else:
            logging.debug(f"Tentative de suppression d'un post-it inexistant : {bill_id}")

            
    def _handle_status_update(self, bill_id: str, new_status: str):
        """
        Met à jour le statut d'une commande dans la base de données et dans l'interface.
        """
        if bill_id not in self.active_postits:
            self.update_status(f"Erreur: Facture #{bill_id} non trouvée pour la mise à jour du statut.", '#e74c3c')
            return
            
        rows_updated = self.db_manager.update_order_status(bill_id, new_status)
        
        if rows_updated > 0:
            self.update_status(f"Statut de la Facture #{bill_id} mis à jour à '{new_status}'.")
            postit = self.active_postits[bill_id]
            postit.update_status(new_status)
            
            # 🌟 NOUVEAU: Retirer la table du suivi des serveuses si le statut est final
            if new_status in ('Traitée', 'Annulée'):
                if self.serveur_window:
                    self.serveur_window.remove_table(bill_id)
                    
        else:
            self.update_status(f"Erreur DB: Impossible de mettre à jour le statut de la Facture #{bill_id}.", '#e74c3c')

    def _handle_delete_bill(self, bill_id: str):
        """Gère la suppression définitive d'une commande (bouton 'Supprimer (Def.)')."""
        if bill_id not in self.active_postits:
            self.update_status(f"Erreur: Facture #{bill_id} non trouvée pour la suppression.", '#e74c3c')
            return
            
        if messagebox.askyesno("Confirmation de Suppression Définitive", 
                               f"Êtes-vous SÛR de vouloir SUPPRIMER DÉFINITIVEMENT la facture #{bill_id} ?"):
            
            rows_deleted = self.db_manager.permanent_delete_order_by_bill_id(bill_id)
            
            if rows_deleted > 0:
                self._remove_postit(bill_id)
                self.update_status(f"Facture #{bill_id} supprimée définitivement.", '#e74c3c')
            else:
                self.update_status(f"Erreur DB: Impossible de supprimer la Facture #{bill_id}.", '#e74c3c')