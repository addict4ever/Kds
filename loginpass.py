import tkinter as tk
from tkinter import messagebox
import math
import hashlib
import os
import json
import pyotp  # <-- AJOUT ICI
from functools import partial
from typing import Optional, Tuple
from PIL import ImageTk
import qrcode

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


class CustomMessageBox(tk.Toplevel):
    """Boîte de message personnalisée de style sombre, tactile, sans barre de titre et toujours au premier plan."""
    def __init__(self, parent, title: str, message: str, is_error: bool = True):
        super().__init__(parent)
        self.configure(bg="#222")
        
        # --- ENLEVER LE X ET LA BARRE DE TITRE COMPLET ---
        
        # S'assurer qu'elle s'affiche par-dessus le cadran topmost
        self.attributes('-topmost', True)
        self.transient(parent)
        self.grab_set()

        # Dimensions et centrage
        win_w, win_h = 450, 220
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - win_w) // 2
        y = (sh - win_h) // 2
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")

        # On ajoute une petite bordure colorée tout autour pour compenser la perte de la fenêtre Windows
        border_color = "#e74c3c" if is_error else "#3498db"
        self.configure(highlightbackground=border_color, highlightthickness=3)

        # Conteneur principal
        main_frame = tk.Frame(self, bg="#222", padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Icône et Titre réintégrés à l'intérieur de la boîte
        icon_color = "#e74c3c" if is_error else "#3498db"
        icon_text = "🚨" if is_error else "ℹ️"
        
        header_frame = tk.Frame(main_frame, bg="#222")
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(header_frame, text=icon_text, font=("Helvetica", 24), fg=icon_color, bg="#222").pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(header_frame, text=title.upper(), font=("Helvetica", 14, "bold"), fg="#fff", bg="#222").pack(side=tk.LEFT)

        # Message textuel
        self.msg_label = tk.Label(
            main_frame, 
            text=message, 
            font=("Helvetica", 11), 
            fg="#eee", 
            bg="#222", 
            justify=tk.LEFT, 
            wraplength=400
        )
        self.msg_label.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Gros bouton de fermeture (idéal pour le tactile)
        btn_color = "#c0392b" if is_error else "#2980b9"
        self.ok_btn = tk.Button(
            main_frame, 
            text="COMPRIS", 
            command=self.destroy, 
            font=("Helvetica", 12, "bold"), 
            bg=btn_color, 
            fg="#fff", 
            activebackground="#e74c3c", 
            activeforeground="#fff",
            relief=tk.FLAT,
            height=1,
            width=12
        )
        self.ok_btn.pack(side=tk.BOTTOM)
        
        # Permet de valider aussi en appuyant sur Entrée ou Espace
        # Permet de valider aussi en appuyant sur Entrée ou Espace
        self.bind("<Return>", lambda e: self.destroy())
        self.bind("<space>", lambda e: self.destroy())  # <-- REMPLACE <Space> PAR <space> EN MINUSCULE

    @classmethod
    def show_error(cls, parent, title: str, message: str):
        """Méthode pratique pour afficher une erreur."""
        dialog = cls(parent, title, message, is_error=True)
        parent.wait_window(dialog)

    @classmethod
    def show_info(cls, parent, title: str, message: str):
        """Méthode pratique pour afficher une information standard."""
        dialog = cls(parent, title, message, is_error=False)
        parent.wait_window(dialog)

# --- Fonctions de Sécurité (Hashing et Stockage) ---

def load_security_config() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Charge le sel, le hash et le secret OTP à partir du fichier."""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('salt'), data.get('hash'), data.get('otp_secret')
    except (FileNotFoundError, json.JSONDecodeError):
        return None, None, None
    except Exception as e:
        print(f"Erreur inattendue lors du chargement : {e}")
        return None, None, None

def save_security_config(salt_hex: str, hash_hex: str, otp_secret: str):
    """Sauvegarde le sel, le hash et le secret OTP dans le fichier."""
    data = {
        'salt': salt_hex,
        'hash': hash_hex,
        'otp_secret': otp_secret  # <-- AJOUT ICI
    }
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde : {e}")
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

# --- Chargement et Initialisation ---
SAVED_SALT, SAVED_HASH, SAVED_OTP_SECRET = load_security_config()

if SAVED_SALT is None or SAVED_HASH is None or SAVED_OTP_SECRET is None:
    print(f"INITIALISATION DE LA SÉCURITÉ...")
    INITIAL_PASSWORD = "567418978"
    NEW_SALT = os.urandom(SALT_SIZE) 
    NEW_HASH = hash_password(INITIAL_PASSWORD, NEW_SALT)
    
    # Génération d'une clé secrète OTP standard (Base32)
    NEW_OTP_SECRET = pyotp.random_base32()
    
    try:
        save_security_config(NEW_SALT.hex(), NEW_HASH, NEW_OTP_SECRET)
        SAVED_SALT, SAVED_HASH, SAVED_OTP_SECRET = NEW_SALT.hex(), NEW_HASH, NEW_OTP_SECRET
        
        # Génération de l'URL pour l'application mobile (Google Authenticator)
        totp = pyotp.TOTP(NEW_OTP_SECRET)
        provisioning_url = totp.provisioning_uri(name="Pizzeria", issuer_name="KDS-Secure")
        
        print("\n" + "="*60)
        print("🚨 PREMIER LANCEMENT : CONFIGURATION OTP REQUISE 🚨")
        print(f"1. Code par défaut : {INITIAL_PASSWORD} (À changer immédiatement)")
        print(f"2. Clé secrète OTP à copier dans Authenticator : {NEW_OTP_SECRET}")
        print(f"3. Lien pour générer un QR Code : https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={provisioning_url}")
        print("="*60 + "\n")
    except Exception:
        print("ÉCHEC CRITIQUE: Impossible de sauvegarder la configuration initiale.")
        SAVED_SALT, SAVED_HASH, SAVED_OTP_SECRET = None, None, None


class DialUnlockDialog(tk.Toplevel):
    """Fenêtre modale avec cadran tactile et gestion de la clé maître."""

    def __init__(self, parent, stored_hash: str, stored_salt: str, stored_otp_secret: str, key_update_callback, action_name: str = "Authentification"):
        super().__init__(parent)
        
        # S'assurer que les données de sécurité sont valides avant de continuer
        if not stored_salt or not stored_hash:
            messagebox.showerror("Erreur de Sécurité", "Configuration de sécurité manquante ou corrompue. Impossible de continuer.")
            self.destroy()
            return
        self.master.protocol("WM_DELETE_WINDOW", self.disable_event)

        
        
        # Empêche Alt+F4, Alt+Tab, etc.
        self.master.bind("<Alt-F4>", self.disable_event)
        self.master.bind("<Alt-Tab>", self.disable_event)
        self.master.bind("<Alt-Escape>", self.disable_event)

        self.parent = parent
        self.action_name = action_name
        self.title(action_name)
        self.configure(bg="#222")

        self.request_otp_reset = False
        
        self.stored_hash = stored_hash
        self.stored_salt = stored_salt
        self.stored_otp_secret = stored_otp_secret # <-- AJOUT
        self.key_update_callback = key_update_callback 
        
        self.otp_mode = True # <-- AJOUT : Indique si on est en train de demander le code OTP à 6 chiffres

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
    
    def disable_event(self, event=None):
        """Fonction qui ne fait rien pour bloquer les tentatives de fermeture."""
        return "break"
        

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
        """Met à jour l'interface pour l'authentification OTP."""
        self.input_code = ""
        self._refresh_display()
        
        # --- MODE OTP ---
        self.header_var.set("🔑 AUTHENTIFICATION OTP")
        self.enter_btn.config(text="✅ VALIDER OTP", bg="#9b59b6", state=tk.NORMAL)
        self.clear_btn.config(text="❌ EFFACER", command=self._on_clear)
        self.tip_var.set("Saisissez le code à 6 chiffres.")
        
        # --- MODIFICATION : Réafficher le bouton pour permettre le changement volontaire d'OTP ---
        self.change_key_btn.config(text="⚙️ MODIFIER OTP", font=(FONT_NAME, 12), width=16)
        self.change_key_btn.pack(pady=(10, 4))

    def _on_change_key_mode(self):
        """Vérifie le code OTP actuel, et si valide, autorise la réinitialisation."""
        otp_to_check = self.input_code.strip()
        totp = pyotp.TOTP(self.stored_otp_secret)

        # 1. Vérification de validité
        if totp.verify(otp_to_check, valid_window=10):
            # Code valide : on autorise la demande de reset
            self.request_otp_reset = True
            self.result = True  # On marque le succès
            self.destroy()      # On ferme pour laisser check_access_password gérer le QR Code
        else:
            # Code invalide : on refuse l'accès à la modification
            CustomMessageBox.show_error(self, "Accès Refusé", "Code OTP invalide. Modification impossible.")
            self._shake()
            self.input_code = ""
            self._refresh_display()

    def _on_cancel_change(self):
        """Annule le mode de changement ou le mode OTP et revient au mode login."""
        self.new_key_temp = ""
        self.otp_mode = False # <-- AJOUT
        self.change_key_state = 0
        self._refresh_key_mode_ui()

    def _on_enter(self):
        """Gère l'action du bouton ENTRER/CONFIRMER/VÉRIFIER selon l'état."""
        if self.otp_mode:
            self._verify_otp() # <-- AJOUT
        elif self.change_key_state == 1:
            self._verify_old_key()
        elif self.change_key_state == 2:
            self._store_new_key_first_time()
        elif self.change_key_state == 3:
            self._confirm_new_key_second_time()
        else: # change_key_state == 0 (Mode Login)
            self._verify_access()

    def _verify_access(self):
        """Vérifie le code en mode normal. Si OK, bascule sur la validation OTP."""
        if verify_password(self.input_code, self.stored_salt, self.stored_hash):
            # Étape 1 validée ! On passe à l'étape 2 (OTP)
            self.otp_mode = True
            self._refresh_key_mode_ui()
        else:
            CustomMessageBox.show_error(
                self, 
                "Erreur d'Accès", 
                "Code d'accès incorrect. Veuillez réessayer."
            )
            self._shake()
            self.input_code = ""
            self._refresh_display()

    def _verify_otp(self):
        """Vérifie le code OTP à 6 chiffres avec une tolérance de 5 minutes."""
        # Nettoyage des espaces si jamais il y en a
        otp_to_check = self.input_code.strip()
        
        totp = pyotp.TOTP(self.stored_otp_secret)
        
        # valid_window=10 permet de valider un code qui a jusqu'à 5 minutes 
        # d'avance ou de retard (10 * 30 secondes = 300 secondes / 5 minutes)
        if totp.verify(otp_to_check, valid_window=10):
            self.result = True
            self.destroy() # Authentification totalement réussie !
        else:
            CustomMessageBox.show_error(
                self,
                "Erreur OTP", 
                "Code OTP invalide.\n\n"
                "Vérifiez que l'heure de votre téléphone est bien synchronisée et réessayez."
            )
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
            CustomMessageBox.show_error(
                self, 
                "Erreur de Vérification", 
                "Ancienne clé incorrecte. Réessayez."
            )
            self._shake()
            self.input_code = "" # Réinitialiser le champ de saisie
            self.after(50, self._on_cancel_change) # Revenir au mode login après un petit délai
            
    def _store_new_key_first_time(self):
        """Sauvegarde le premier essai de la nouvelle clé et passe à l'étape de confirmation."""
        new_key = self.input_code
        if len(new_key) < 4:
            CustomMessageBox.show_error(
                self,
                "Erreur", 
                f"La clé doit contenir au moins 4 chiffres."
            )
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
            CustomMessageBox.show_error(
                self,
                "Erreur de Confirmation", 
                "Les deux clés saisies ne correspondent pas. Processus annulé."
            )
            self._shake()
            self.after(50, self._on_cancel_change) 
            return

        # Les clés correspondent, procéder à l'enregistrement
        new_key = self.new_key_temp
            
        # 1. Générer un nouveau sel, hacher la nouvelle clé ET générer un NOUVEAU secret OTP
        new_salt = os.urandom(SALT_SIZE)
        new_hash = hash_password(new_key, new_salt)
        new_otp_secret = pyotp.random_base32() # <-- Génération du nouveau secret OTP pour Authenticator
        
        # 2. Appeler la fonction de rappel pour la sauvegarde (avec le paramètre OTP en plus)
        success = self.key_update_callback(new_salt.hex(), new_hash, new_otp_secret)

        if success:
            # Mettre à jour les variables de classe pour la session en cours
            self.stored_salt = new_salt.hex()
            self.stored_hash = new_hash
            self.stored_otp_secret = new_otp_secret # <-- Mise à jour de la variable locale
            
            # 3. Générer l'URL pour que tu puisses scanner ton nouveau QR code dans la console
            totp = pyotp.TOTP(new_otp_secret)
            provisioning_url = totp.provisioning_uri(name="Pizzeria", issuer_name="KDS-Secure")
            
            print("\n" + "="*60)
            print("🚨 NOUVELLE CONFIGURATION OTP GÉNÉRÉE SUITE AU CHANGEMENT DE CLÉ 🚨")
            print(f"Nouveau secret OTP (manuel) : {new_otp_secret}")
            print(f"Lien pour le nouveau QR Code : https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={provisioning_url}")
            print("="*60 + "\n")
            
            # Alerte visuelle personnalisée (Style Info Bleu) pour l'utilisateur
            CustomMessageBox.show_info(
                self,
                "Succès", 
                "Clé d'accès et OTP mis à jour avec succès.\n\n"
                "IMPORTANT : Scannez le nouveau QR code affiché dans la console avant de tenter de vous reconnecter !"
            )
            
            # Réinitialiser au mode Login et forcer la reconnexion avec la nouvelle clé
            self.new_key_temp = ""
            self.change_key_state = 0 
            self._refresh_key_mode_ui()
            
        else:
            CustomMessageBox.show_error(
                self,
                "Erreur", 
                "La clé n'a pas pu être mise à jour."
            )
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
    """Authentification OTP et modification volontaire via le bouton ⚙️."""
    
    global SAVED_SALT, SAVED_HASH, SAVED_OTP_SECRET
    
    # 1. Préparation du root Tkinter
    root = tk._default_root
    created_root = False
    if root is None:
        root = tk.Tk()
        root.withdraw()
        created_root = True

    if SAVED_OTP_SECRET is None:
        CustomMessageBox.show_error(root, "Erreur Critique", "Configuration OTP manquante.")
        if created_root: root.destroy()
        return False
    
    def handle_key_update(new_salt_hex: str, new_hash_hex: str, new_otp_secret: str) -> bool:
        global SAVED_SALT, SAVED_HASH, SAVED_OTP_SECRET
        try:
            save_security_config(new_salt_hex, new_hash_hex, new_otp_secret)
            SAVED_SALT, SAVED_HASH, SAVED_OTP_SECRET = new_salt_hex, new_hash_hex, new_otp_secret
            return True
        except Exception as e:
            CustomMessageBox.show_error(dialog, "Erreur", f"Échec de sauvegarde : {e}")
            return False

    # 2. Lancement du cadran tactile
    dialog = DialUnlockDialog(
        root, 
        stored_hash=SAVED_HASH, 
        stored_salt=SAVED_SALT, 
        stored_otp_secret=SAVED_OTP_SECRET,
        key_update_callback=handle_key_update,
        action_name=action_name
    )
    dialog.otp_mode = True
    dialog._refresh_key_mode_ui()
    
    root.wait_window(dialog)

    # 3. Logique post-authentification
    success = dialog.result
    
    # Si le bouton de modification a été pressé, on invalide immédiatement l'accès
    if success and getattr(dialog, 'request_otp_reset', False):
        success = False 
        
        # Demande de confirmation personnalisée
        confirm_win = tk.Toplevel(root)
        confirm_win.title("Configuration")
        confirm_win.attributes('-topmost', True)
        confirm_win.configure(bg="#222")
        
        tk.Label(confirm_win, text="Vous avez demandé à modifier l'OTP.\nConfirmer la génération d'un nouveau code ?", 
                 bg="#222", fg="white", font=("Helvetica", 12), pady=20).pack()
        
        should_reset = [False]
        def do_reset():
            should_reset[0] = True
            confirm_win.destroy()

        btn_f = tk.Frame(confirm_win, bg="#222")
        btn_f.pack(pady=10)
        tk.Button(btn_f, text="OUI", command=do_reset, bg="#e74c3c", fg="white").pack(side=tk.LEFT, padx=10)
        tk.Button(btn_f, text="NON", command=confirm_win.destroy, bg="#3498db", fg="white").pack(side=tk.LEFT, padx=10)
        
        root.wait_window(confirm_win)

        # Gestion du résultat de la confirmation
        if should_reset[0]:
            # GÉNÉRATION DU NOUVEAU SECRET
            new_secret = pyotp.random_base32()
            save_security_config(SAVED_SALT, SAVED_HASH, new_secret)
            SAVED_OTP_SECRET = new_secret
            
            # Affichage du QR Code
            qr_win = tk.Toplevel(root)
            qr_win.title("Nouveau QR Code")
            qr_win.attributes('-topmost', True)
            qr_win.configure(bg="#222")
            
            uri = pyotp.TOTP(new_secret).provisioning_uri(name="Pizzeria", issuer_name="KDS-Secure")
            qr_img = ImageTk.PhotoImage(qrcode.make(uri))
            
            tk.Label(qr_win, text="Scannez ce nouveau code :", bg="#222", fg="white").pack(pady=10)
            lbl = tk.Label(qr_win, image=qr_img)
            lbl.image = qr_img
            lbl.pack(pady=10)
            tk.Button(qr_win, text="FERMER", command=qr_win.destroy).pack(pady=10)
            
            root.wait_window(qr_win)
            # success reste False, l'accès est donc invalidé
        else:
            # Si l'utilisateur clique sur "NON", il n'a pas accès
            success = False

    # 4. Nettoyage
    if created_root:
        try: root.destroy()
        except: pass

    return success

# --- EXEMPLE D'UTILISATION ---
if __name__ == "__main__":
    if check_access_password("Lancement du Gestionnaire de Mots de Passe"):
        print("\n✅ ACCÈS ACCORDÉ. Vous pouvez maintenant ouvrir votre base de données chiffrée.")
    else:
        print("\n❌ AUTHENTIFICATION ÉCHOUÉE OU ANNULÉE. Fermeture de l'application.")