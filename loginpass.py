import tkinter as tk
from tkinter import messagebox
import math
import hashlib
import os
import json
from functools import partial
from typing import Optional, Tuple

# --- Configuration du Système ---
CONFIG_FILE = "access_key_config.json" # Fichier pour stocker le sel et le hash
DIAL_SIZE = 520                      # Diamètre du cadran
BUTTON_RADIUS = 36                   # Rayon des boutons chiffres
FONT_NAME = "Helvetica"

# --- Paramètres de SÉCURITÉ ULTRA-SÉCURISÉE ---
MAX_PASSWORD_LENGTH = 40             # Limite maximale de 40 caractères/chiffres
HASH_ALGORITHM = 'sha256'
HASH_ITERATIONS = 600000             # Nombre d'itérations pour PBKDF2
SALT_SIZE = 16                       # 16 bytes = 32 caractères hexadécimaux


# --- Fonctions de Sécurité (Hashing et Stockage) ---

def load_security_config() -> Tuple[Optional[str], Optional[str]]:
    """Charge le sel et le hash à partir du fichier de configuration."""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('salt'), data.get('hash')
    except FileNotFoundError:
        # Initialisation si le fichier n'existe pas
        return None, None
    except json.JSONDecodeError:
        # Erreur si le fichier est corrompu
        return None, None
    except Exception as e:
        print(f"Erreur inattendue lors du chargement de la config de sécurité : {e}")
        return None, None

def save_security_config(salt_hex: str, hash_hex: str):
    """Sauvegarde le nouveau sel et le hash dans le fichier."""
    data = {
        'salt': salt_hex,
        'hash': hash_hex
    }
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde du fichier de configuration : {e}")
        raise

def hash_password(password: str, salt: bytes) -> str:
    """Hache le mot de passe en utilisant PBKDF2 avec le sel donné."""
    # Assure que seul l'input numérique est traité
    password_safe = "".join(c for c in password if c.isdigit())
    
    # Correction: PBKDF2 nécessite que le mot de passe soit encodé en bytes
    return hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        password_safe.encode('utf-8'),
        salt,
        HASH_ITERATIONS
    ).hex()

def verify_password(password: str, salt_hex: str, stored_hash_hex: str) -> bool:
    """
    Vérifie si le mot de passe correspond au hash stocké.
    """
    try:
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        print("Erreur: Le sel stocké n'est pas un hexadécimal valide.")
        return False
        
    computed_hash = hash_password(password, salt)
    
    # Comparaison directe des chaînes de hachage hexadécimales.
    return computed_hash == stored_hash_hex

# --- Chargement et Initialisation du Mot de Passe Maître ---

SAVED_SALT, SAVED_HASH = load_security_config()

if SAVED_SALT is None or SAVED_HASH is None:
    # Si c'est le premier lancement, initialiser avec un mot de passe par défaut (ex: 1234)
    print(f"FICHIER DE CONFIGURATION INTROUVABLE OU CORROMPU : Création d'un mot de passe par défaut (1234).")
    INITIAL_PASSWORD = "1234"
    # Génération d'un sel aléatoire et sécurisé
    NEW_SALT = os.urandom(SALT_SIZE) 
    NEW_HASH = hash_password(INITIAL_PASSWORD, NEW_SALT)
    
    try:
        save_security_config(NEW_SALT.hex(), NEW_HASH)
        SAVED_SALT, SAVED_HASH = NEW_SALT.hex(), NEW_HASH
        print(f"Mot de passe par défaut généré et sauvegardé dans {CONFIG_FILE}. Veuillez le changer immédiatement.")
    except Exception:
        # En cas d'échec de la sauvegarde, le programme doit s'arrêter ou fonctionner en mode non sécurisé.
        print("ÉCHEC CRITIQUE: Impossible de sauvegarder la configuration de sécurité initiale.")
        # Pour cet exemple, nous allons laisser les variables globales à None, ce qui empêchera la vérification.
        SAVED_SALT, SAVED_HASH = None, None


class DialUnlockDialog(tk.Toplevel):
    """Fenêtre modale avec cadran tactile et gestion de la clé maître."""

    def __init__(self, parent, stored_hash: str, stored_salt: str, key_update_callback, action_name: str = "Authentification"):
        super().__init__(parent)
        
        # S'assurer que les données de sécurité sont valides avant de continuer
        if not stored_salt or not stored_hash:
            messagebox.showerror("Erreur de Sécurité", "Configuration de sécurité manquante ou corrompue. Impossible de continuer.")
            self.destroy()
            return

        self.parent = parent
        self.action_name = action_name
        self.title(action_name)
        self.configure(bg="#222")
        
        # Fonctions et données de sécurité
        self.stored_hash = stored_hash
        self.stored_salt = stored_salt
        self.key_update_callback = key_update_callback 

        # Configuration de la fenêtre
        self.attributes('-topmost', True)
        self.after(10, self.lift) 
        self.transient(parent)
        self.grab_set()

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        # Ajuster la taille en fonction de la résolution de l'écran
        size = min(DIAL_SIZE, int(min(sw, sh) * 0.85))
        self.diameter = size
        
        win_w = size + 120
        win_h = size + 280 
        x = (sw - win_w) // 2
        y = (sh - win_h) // 2
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.resizable(False, False)

        # Internal state
        self.input_code = ""
        self.new_key_temp = ""
        self.masked = True
        self.result = False
        
        # État de la procédure de changement de clé :
        # 0: Mode Login (par défaut)
        # 1: Saisie de l'Ancienne Clé
        # 2: Saisie de la Nouvelle Clé (première fois)
        # 3: Confirmation de la Nouvelle Clé (deuxième fois)
        self.change_key_state = 0 
        
        # Amélioration Tactile/Souris
        self.digit_positions = {}
        self.digit_items = {}
        self._pending_tap_digit = None 
        self._is_drag_active = False
        self._long_press_job = None
        self._current_pressed_item_id = None 


        # Layout
        self._create_widgets()
        self._draw_dial()
        self._refresh_key_mode_ui() 

        self.bind("<Escape>", lambda e: self._on_cancel())

    def _create_widgets(self):
        self.header_var = tk.StringVar(value=self.action_name)
        self.header = tk.Label(self, textvariable=self.header_var, font=(FONT_NAME, 18, "bold"), fg="#fff", bg="#222")
        self.header.pack(pady=(12, 6))

        # Canvas for dial
        self.canvas = tk.Canvas(self, width=self.diameter, height=self.diameter, bg="#111", highlightthickness=0)
        self.canvas.pack(pady=(4, 10))

        # Display input (masked)
        self.display_var = tk.StringVar(value="")
        display_frame = tk.Frame(self, bg="#222")
        display_frame.pack()
        self.display_label = tk.Label(display_frame, textvariable=self.display_var, font=(FONT_NAME, 24), fg="#0ff", bg="#222")
        self.display_label.pack()

        # Action buttons (Enter and Clear)
        btn_frame = tk.Frame(self, bg="#222")
        btn_frame.pack(pady=(10, 6))

        self.enter_btn = tk.Button(btn_frame, text="✅ ENTRER", command=self._on_enter, font=(FONT_NAME, 16, "bold"), width=12, height=2, bg="#3fbf7f", fg="#fff")
        self.enter_btn.grid(row=0, column=0, padx=8)
        self.clear_btn = tk.Button(btn_frame, text="❌ EFFACER", command=self._on_clear, font=(FONT_NAME, 16), width=12, height=2, bg="#c0392b", fg="#fff")
        self.clear_btn.grid(row=0, column=1, padx=8)
        
        # Bouton pour changer la clé (roue dentée)
        self.change_key_btn = tk.Button(self, text="⚙️", command=self._on_change_key_mode, font=(FONT_NAME, 20), width=4, bg="#3498db", fg="#fff", relief=tk.FLAT)
        self.change_key_btn.pack(pady=(10, 4))

        # Tip
        self.tip_var = tk.StringVar(value="Touchez un chiffre pour l'ajouter. Maintenez le fond pour effacer le dernier.")
        tip = tk.Label(self, textvariable=self.tip_var, font=(FONT_NAME, 10), fg="#aaa", bg="#222")
        tip.pack(pady=(6, 10))
        
        # Bindings
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self._long_press_job = None

    def _draw_dial(self):
        self.canvas.delete("all")
        cx = cy = self.diameter // 2
        r = int(self.diameter * 0.42)

        # Outer bevel to simulate pseudo-3D
        for i in range(12):
            shade = 60 + int(80 * (i / 11.0))
            color = f"#{shade:02x}{shade:02x}{shade:02x}"
            self.canvas.create_oval(cx - r - i, cy - r - i, cx + r + i, cy + r + i, outline=color)

        # Core disk with gradient-ish rings
        for ring in range(6):
            t = ring / 5.0
            col_val = 40 + int(120 * (1 - t))
            color = f"#{col_val:02x}{col_val:02x}{col_val + 30:02x}"
            self.canvas.create_oval(cx - r + ring*6, cy - r + ring*6, cx + r - ring*6, cy + r - ring*6, fill=color, outline="")

        # Center cap (like a safe's hub)
        hub_r = int(r * 0.22)
        self.canvas.create_oval(cx - hub_r, cy - hub_r, cx + hub_r, cy + hub_r, fill="#222", outline="#000")
        self.canvas.create_oval(cx - hub_r + 6, cy - hub_r + 6, cx + hub_r - 6, cy + hub_r - 6, fill="#333", outline="")

        # Draw digits 0-9 around circle
        digits = [str(i) for i in range(10)]

        # Arrange digits
        start_angle = 270 # top
        step = -360 / len(digits) # clockwise rotation
        angle_offset = 0

        for idx, d in enumerate(digits):
            angle_deg = start_angle + (idx * step) + angle_offset
            angle_rad = math.radians(angle_deg)
            dx = int(cx + (r - 70) * math.cos(angle_rad))
            dy = int(cy + (r - 70) * math.sin(angle_rad))
            self.digit_positions[d] = (dx, dy)

            # shadow
            self.canvas.create_oval(dx - BUTTON_RADIUS - 4, dy - BUTTON_RADIUS - 4,
                                             dx + BUTTON_RADIUS - 4, dy + BUTTON_RADIUS - 4,
                                             fill="#000", outline="", tags=(f"btn_{d}_shadow",))
            # button circle
            btn_item = self.canvas.create_oval(dx - BUTTON_RADIUS, dy - BUTTON_RADIUS,
                                                 dx + BUTTON_RADIUS, dy + BUTTON_RADIUS,
                                                 fill="#1a6", outline="#0c4", width=3, tags=(f"btn_{d}",))
            self.digit_items[d] = btn_item 

            # digit text
            self.canvas.create_text(dx, dy, text=d, font=(FONT_NAME, 20, "bold"), fill="#fff", tags=(f"txt_{d}",))

        # Add invisible center disc to look nicer
        self.canvas.create_oval(cx - int(r*0.12), cy - int(r*0.12), cx + int(r*0.12), cy + int(r*0.12), fill="", outline="")
    
    # --- LOGIQUE DE CHANGEMENT DE CLÉ ---
    
    def _refresh_key_mode_ui(self):
        """Met à jour les textes des boutons et le titre selon le mode (Login/Old/New Key)."""
        self.input_code = ""
        self._refresh_display()
        
        if self.change_key_state == 1: # Saisie de l'Ancienne Clé
            self.header_var.set("VÉRIFICATION : ANCIENNE CLÉ")
            self.enter_btn.config(text="VÉRIFIER", bg="#f39c12", state=tk.NORMAL)
            self.clear_btn.config(text="❌ ANNULER", command=self._on_cancel_change)
            self.tip_var.set("Saisissez votre clé d'accès ACTUELLE.")
            if self.change_key_btn.winfo_ismapped():
                 self.change_key_btn.pack_forget() 
        elif self.change_key_state == 2: # Saisie de la Nouvelle Clé (1ère fois)
            self.header_var.set("NOUVELLE CLÉ (1/2)")
            self.enter_btn.config(text="SUIVANT >>", bg="#3498db", state=tk.NORMAL)
            self.clear_btn.config(text="❌ ANNULER", command=self._on_cancel_change)
            self.tip_var.set(f"Entrez le NOUVEAU code secret (4-{MAX_PASSWORD_LENGTH} chiffres).")
            if self.change_key_btn.winfo_ismapped():
                 self.change_key_btn.pack_forget() 
        elif self.change_key_state == 3: # Confirmation de la Nouvelle Clé (2ème fois)
            self.header_var.set("CONFIRMER NOUVELLE CLÉ (2/2)")
            self.enter_btn.config(text="💾 ENREGISTRER", bg="#3fbf7f", state=tk.NORMAL)
            self.clear_btn.config(text="❌ ANNULER", command=self._on_cancel_change)
            self.tip_var.set("Confirmez le nouveau code.")
            if self.change_key_btn.winfo_ismapped():
                 self.change_key_btn.pack_forget() 
        else: # Mode Login (change_key_state == 0)
            self.header_var.set(self.action_name)
            self.enter_btn.config(text="✅ ENTRER", bg="#3fbf7f", state=tk.NORMAL)
            self.clear_btn.config(text="❌ EFFACER", command=self._on_clear)
            self.tip_var.set("Touchez un chiffre pour l'ajouter. Maintenez le fond pour effacer le dernier.")
            self.change_key_btn.pack(pady=(10, 4)) 

    def _on_change_key_mode(self):
        """Passe à l'étape 1 : Saisie de l'ancienne clé pour vérification."""
        self.new_key_temp = "" # Réinitialiser la clé temporaire
        self.change_key_state = 1
        self._refresh_key_mode_ui()

    def _on_cancel_change(self):
        """Annule le mode de changement et revient au mode login."""
        self.new_key_temp = ""
        self.change_key_state = 0
        self._refresh_key_mode_ui()

    def _on_enter(self):
        """Gère l'action du bouton ENTRER/CONFIRMER/VÉRIFIER selon l'état."""
        if self.change_key_state == 1:
            self._verify_old_key()
        elif self.change_key_state == 2:
            self._store_new_key_first_time()
        elif self.change_key_state == 3:
            self._confirm_new_key_second_time()
        else: # change_key_state == 0 (Mode Login)
            self._verify_access()

    def _verify_access(self):
        """Vérifie le code en mode normal (login) avec le HASH stocké."""
        if verify_password(self.input_code, self.stored_salt, self.stored_hash):
            self.result = True
            self.destroy()
        else:
            self._shake()
            self.input_code = ""
            self._refresh_display()
            
    def _verify_old_key(self):
        """Vérifie l'ancienne clé d'accès et passe à l'étape 2 si correcte."""
        if verify_password(self.input_code, self.stored_salt, self.stored_hash):
            # Ancienne clé correcte, passer à l'étape de saisie de la nouvelle clé
            self.change_key_state = 2
            self._refresh_key_mode_ui()
        else:
            # Requis par l'utilisateur: Secouer, réinitialiser l'input et annuler
            messagebox.showerror("Erreur de Vérification", "Ancienne clé incorrecte. Réessayez.")
            self._shake()
            self.input_code = "" # Réinitialiser le champ de saisie
            self.after(50, self._on_cancel_change) # Revenir au mode login après un petit délai
            
    def _store_new_key_first_time(self):
        """Sauvegarde le premier essai de la nouvelle clé et passe à l'étape de confirmation."""
        new_key = self.input_code
        if len(new_key) < 4:
            messagebox.showerror("Erreur", "La clé doit contenir au moins 4 chiffres.")
            self._shake()
            self.input_code = ""
            self._refresh_display()
            return

        self.new_key_temp = new_key # Stocke la première saisie
        self.change_key_state = 3 # Passe à l'étape de confirmation
        self._refresh_key_mode_ui()
        
    def _confirm_new_key_second_time(self):
        """Vérifie la confirmation et procède à l'enregistrement ou à l'annulation."""
        confirmed_key = self.input_code
        
        if confirmed_key != self.new_key_temp:
            # Clés différentes : Annulation du processus
            messagebox.showerror("Erreur de Confirmation", "Les deux clés saisies ne correspondent pas. Processus annulé.")
            self._shake()
            self.after(50, self._on_cancel_change) 
            return

        # Les clés correspondent, procéder à l'enregistrement
        new_key = self.new_key_temp
            
        # 1. Générer un nouveau sel et hacher la nouvelle clé
        new_salt = os.urandom(SALT_SIZE)
        new_hash = hash_password(new_key, new_salt)
        
        # 2. Appeler la fonction de rappel pour la sauvegarde
        success = self.key_update_callback(new_salt.hex(), new_hash)

        if success:
            # Mettre à jour les variables de classe pour la session en cours
            self.stored_salt = new_salt.hex()
            self.stored_hash = new_hash
            
            # Réinitialiser au mode Login et forcer la reconnexion avec la nouvelle clé
            messagebox.showinfo("Succès", "Clé d'accès mise à jour et sécurisée. Veuillez maintenant vous authentifier avec votre nouvelle clé.")
            
            self.new_key_temp = ""
            self.change_key_state = 0 
            self._refresh_key_mode_ui()
            
        else:
            messagebox.showerror("Erreur", "La clé n'a pas pu être mise à jour.")
            self._on_cancel_change() 

    # --- LOGIQUE D'INTERACTION CORRIGÉE ---
    
    def _get_clicked_digit(self, x, y):
        """Détermine quel chiffre, le cas échéant, a été cliqué."""
        for d, (dx, dy) in self.digit_positions.items():
            dist = math.hypot(dx - x, dy - y)
            # On donne une tolérance un peu plus large pour le tactile
            if dist <= BUTTON_RADIUS + 10: 
                return d
        return None

    def _on_canvas_click(self, event):
        """Gère l'appui initial (Button-1)."""
        # Réinitialisation des états
        self._is_drag_active = False 
        self._cancel_long_press()
        
        clicked_digit = self._get_clicked_digit(event.x, event.y)
        
        if clicked_digit is not None:
            # Si un chiffre est cliqué, on le note pour l'enregistrement au relâchement
            self._pending_tap_digit = clicked_digit
            self._flash_digit_press(clicked_digit) # Anime la pression
            
            # Mémoriser l'élément en cours d'appui pour gérer le drag/hover
            self._current_pressed_item_id = self.digit_items.get(clicked_digit)
        else:
            # Si le fond est cliqué, on démarre l'effacement par appui long
            self._pending_tap_digit = None
            self._start_long_press()

    def _on_canvas_drag(self, event):
        """Gère le mouvement (B1-Motion). NE DOIT PAS ENREGISTRER LE CHIFFRE."""
        # Si un mouvement est détecté après un appui initial sur un chiffre,
        # on considère que c'est un drag, même si on reste sur le bouton.
        if self._pending_tap_digit is not None:
            self._is_drag_active = True
            
        # Si l'appui long était actif, le drag l'annule
        self._cancel_long_press()

        # Logique de survol/flash (optionnelle pour améliorer le ressenti)
        x, y = event.x, event.y
        current_digit_over = self._get_clicked_digit(x, y)
        
        # Remet l'ancien bouton à son état normal
        if self._current_pressed_item_id is not None:
            self.canvas.itemconfig(self._current_pressed_item_id, fill="#1a6")
        
        # Met en surbrillance le nouveau bouton survolé
        if current_digit_over is not None:
            self._current_pressed_item_id = self.digit_items.get(current_digit_over)
            self.canvas.itemconfig(self._current_pressed_item_id, fill="#3fbf7f") # Couleur pressée
        else:
            self._current_pressed_item_id = None


    def _on_canvas_release(self, event):
        """Gère le relâchement du bouton de la souris/doigt (ButtonRelease-1)."""
        self._cancel_long_press()

        final_digit = self._get_clicked_digit(event.x, event.y)
        
        # 1. Logique d'enregistrement du chiffre (Simple Tap)
        # Si un chiffre était initialement appuyé (pending_tap_digit) ET
        # s'il n'y a pas eu de glissement (is_drag_active) OU si on a relâché sur le même chiffre
        is_tap = (self._pending_tap_digit is not None and 
                  final_digit == self._pending_tap_digit and 
                  not self._is_drag_active)

        if is_tap:
            # Ceci est un tap réussi, ajouter le chiffre
            self._press_digit_logic(self._pending_tap_digit)

        # 2. Rétablir l'état visuel du bouton pressé (s'il existe)
        if self._current_pressed_item_id is not None:
            self.canvas.itemconfig(self._current_pressed_item_id, fill="#1a6")

        # 3. Réinitialiser les états
        self._pending_tap_digit = None
        self._is_drag_active = False
        self._current_pressed_item_id = None 
        

    def _flash_digit_press(self, digit):
        """Anime l'état pressé du bouton."""
        item = self.digit_items.get(digit)
        if item:
            self.canvas.itemconfig(item, fill="#3fbf7f")
            # L'état normal sera rétabli dans _on_canvas_release


    def _press_digit_logic(self, digit):
        """Ajoute le chiffre à la saisie, avec une limite de 40 caractères."""
        if len(self.input_code) >= MAX_PASSWORD_LENGTH:
            return
        self.input_code += digit
        self._refresh_display()

    def _start_long_press(self):
        """Démarre le mode d'appui long pour l'effacement."""
        # Seul l'appui sur le fond active l'effacement.
        if self.change_key_state == 0:
            self.tip_var.set("Relâchez pour annuler l'effacement. Maintenez pour effacer.")
        else:
            self.tip_var.set("Appuyez sur 'Effacer' pour recommencer la saisie.")

        self._long_press_job = self.after(700, self._on_long_press)

    def _cancel_long_press(self):
        """Annule l'effacement par appui long et rétablit le message d'aide."""
        if self._long_press_job is not None:
            self.after_cancel(self._long_press_job)
            self._long_press_job = None
            
            # Rétablit le message d'aide si on était en mode appui long
            if self.change_key_state == 0:
                self.tip_var.set("Touchez un chiffre pour l'ajouter. Maintenez le fond pour effacer le dernier.")
            elif self.change_key_state == 1:
                self.tip_var.set("Saisissez votre clé d'accès ACTUELLE.")
            elif self.change_key_state == 2:
                self.tip_var.set(f"Entrez le NOUVEAU code secret (4-{MAX_PASSWORD_LENGTH} chiffres).")
            elif self.change_key_state == 3:
                self.tip_var.set("Confirmez le nouveau code.")

    def _on_long_press(self):
        """Action déclenchée par l'appui long (effacement continu)."""
        if self.input_code:
             self._on_backspace()
             self._long_press_job = self.after(150, self._on_long_press)
        else:
            self._cancel_long_press() # Arrêter si le champ est vide

    def _on_backspace(self):
        if self.input_code:
            self.input_code = self.input_code[:-1]
            self._refresh_display()

    def _on_clear(self):
        self.input_code = ""
        self._refresh_display()

    def _on_cancel(self):
        self.result = False
        self.destroy()

    def _refresh_display(self):
        if self.masked:
            # Affiche la longueur actuelle par rapport au maximum autorisé
            mask_text = "*" * len(self.input_code)
            self.display_var.set(mask_text)
            
        else:
            self.display_var.set(self.input_code)

    def _shake(self):
        def shake_once(offsets, idx=0):
            if idx >= len(offsets):
                return
            off = offsets[idx]
            self.geometry(f"+{self.winfo_x() + off}+{self.winfo_y()}")
            self.after(40, lambda: shake_once(offsets, idx+1))

        offsets = [8, -8, 6, -6, 3, -3, 0]
        shake_once(offsets)


# --- FONCTION D'UTILISATION PRINCIPALE ---
def check_access_password(action_name: str = "Action protégée") -> bool:
    """Ouvre le dialogue de cadran et gère la mise à jour de la clé."""
    
    global SAVED_SALT, SAVED_HASH
    
    # 1. Gestion des erreurs de configuration critiques au démarrage
    if SAVED_SALT is None or SAVED_HASH is None:
        messagebox.showerror("Erreur Critique", "Le système de sécurité n'a pas pu s'initialiser correctement. Le mot de passe maître est manquant.")
        return False
    
    # 2. Fonction de rappel pour la sauvegarde du hash
    def handle_key_update(new_salt_hex: str, new_hash_hex: str) -> bool:
        """Met à jour les variables globales et le fichier de configuration."""
        # 🚨 CORRECTION : Utiliser 'global' car SAVED_SALT/HASH sont définis au niveau du module.
        global SAVED_SALT, SAVED_HASH
        try:
            save_security_config(new_salt_hex, new_hash_hex)
            SAVED_SALT = new_salt_hex
            SAVED_HASH = new_hash_hex
            return True
        except Exception as e:
            messagebox.showerror("Erreur de Sauvegarde", f"Impossible de sauvegarder la nouvelle clé: {e}")
            return False

    # 3. Préparation du root Tkinter
    root = tk._default_root
    created_root = False
    if root is None:
        root = tk.Tk()
        root.withdraw()
        created_root = True

    # 4. Lancement de la boîte de dialogue
    dialog = DialUnlockDialog(
        root, 
        stored_hash=SAVED_HASH, 
        stored_salt=SAVED_SALT, 
        key_update_callback=handle_key_update,
        action_name=action_name
    )
    root.wait_window(dialog)

    # 5. Destruction du root si créé pour cette session
    if created_root:
        try:
            root.destroy()
        except Exception:
            pass

    return dialog.result

# --- EXEMPLE D'UTILISATION ---
if __name__ == "__main__":
    if check_access_password("Lancement du Gestionnaire de Mots de Passe"):
        print("\n✅ ACCÈS ACCORDÉ. Vous pouvez maintenant ouvrir votre base de données chiffrée.")
    else:
        print("\n❌ AUTHENTIFICATION ÉCHOUÉE OU ANNULÉE. Fermeture de l'application.")