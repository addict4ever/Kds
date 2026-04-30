import tkinter as tk
from PIL import Image, ImageTk
from datetime import datetime  # <--- NOUVEAU : Pour gérer l'heure
import random
import json  # <--- NOUVEAU
import os    # <--- NOUVEAU

class CharacterSelector(tk.Toplevel):
    def __init__(self, parent, characters, callback, hide_callback, x, y):
        super().__init__(parent)
        self.callback = callback
        self.hide_callback = hide_callback

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.geometry(f"+{x}+{y}")
        self.configure(bg="#2c3e50", padx=5, pady=5)

        self.grab_set() 

        # BOUTON ANNULER
        btn_close = tk.Button(self, text="ANNULER", command=self.destroy,
                             bg="#c0392b", fg="white", relief="flat", 
                             font=("Arial", 9))
        btn_close.pack(fill="x", pady=(5, 5))

        # --- NOUVEAU : BOUTON ALÉATOIRE ---
        btn_random = tk.Button(self, text="🎲 ALÉATOIRE", 
                              command=lambda: self.select("RANDOM"),
                              bg="#8e44ad", fg="white", activebackground="#9b59b6",
                              relief="flat", font=("Arial", 10, "bold"))
        btn_random.pack(fill="x", pady=(0, 10))

        # --- TITRE PERSONNAGES ---
        tk.Label(self, text="PERSONNAGES", bg="#2c3e50", fg="#bdc3c7", 
                 font=("Arial", 8, "bold")).pack(fill="x", pady=(0, 2))

        # --- CADRE POUR LA GRILLE DES PERSONNAGES ---
        char_grid_frame = tk.Frame(self, bg="#2c3e50")
        char_grid_frame.pack(fill="both", expand=True)

        # Limite de 6 noms verticalement
        max_rows = 6

        # Boutons des personnages avec logique de colonnes
        for i, name in enumerate(characters):
            btn = tk.Button(char_grid_frame, text=name.capitalize(), 
                            command=lambda n=name: self.select(n),
                            bg="#34495e", fg="white", activebackground="#3498db",
                            relief="flat", padx=10, pady=5, font=("Arial", 10, "bold"),
                            width=12) # Largeur fixe pour garder les colonnes égales
            
            # Calcul de la position : change de colonne après 6 éléments
            row_pos = i % max_rows
            col_pos = i // max_rows
            
            btn.grid(row=row_pos, column=col_pos, padx=1, pady=1, sticky="nsew")

        # --- SECTION CACHER ---
        tk.Label(self, text="💤 CACHER POUR...", bg="#2c3e50", fg="#f39c12", 
                 font=("Arial", 8, "bold")).pack(fill="x", pady=(10, 2))

        durations = [
            ("2H", 2), ("4H", 4), ("8H", 8),
            ("12H", 12), ("24H", 24)
        ]

        grid_frame = tk.Frame(self, bg="#2c3e50")
        grid_frame.pack(fill="x")

        for i, (label, hours) in enumerate(durations):
            btn_h = tk.Button(grid_frame, text=label, 
                             command=lambda h=hours: self.hide_action(h),
                             bg="#e67e22", fg="white", activebackground="#d35400",
                             relief="flat", font=("Arial", 9, "bold"), width=4)
            row = i // 3
            col = i % 3
            btn_h.grid(row=row, column=col, padx=1, pady=1, sticky="nsew")

    def select(self, name):
        self.callback(name)
        self.destroy()

    def hide_action(self, hours):
        self.hide_callback(hours)
        self.destroy()

class DesktopPet:
    def __init__(self, root, char_name="chat_blanc_01"):
        self.root = root
        
        # --- CONFIG WINDOW ---
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "white")
        self.root.config(bg="white")

        self.current_character = char_name #
        # --- ÉTATS ET EXPRESSIONS ---
        self.is_hidden = False
        self.hidden_until = None
        self.state = "IDLE"
        self.active_menu = None
        self.brain_rules = []  # <--- AJOUTE CETTE LIGNE ICI (Initialisation par défaut)
        self.anims = {}
        self.facing_right = True
        self.offset_x = 0
        self.offset_y = 0
        self.inertia_x = 0
        self.inertia_y = 0
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.current_frame = 0
        self.is_waiting = False
        self.press_start_time = datetime.now().timestamp() # <--- Timer pour le menu
        self.grab_start_time = 0
        self.menu_opened = False
        self.last_message_time = 0 # <--- Pour suivre le délai de 5 min
        self.click_times = []        # Liste pour stocker l'heure des derniers clics
        self.is_punished = False     # Est-ce que le pet boude ?
        self.punishment_end = 0      # Heure de fin de la punition
        self.file_attente = []    # La liste pour le tirage sans répétition

        self.expressions_file = 'expression_pack.json'
        self.expressions = self.load_expressions()

        self.asset_path = r"C:\resto_controller\anim_perso"
        self.json_path = r"C:\resto_controller\anim_perso.json"

        # --- CONFIG DES ANIMATIONS ---
        # (Fichier, Largeur, Hauteur, Nb_Frames)
        self.anims = {}
        self.brain_rules = [] # Très important pour éviter l'erreur de tout à l'heure
        self.load_character_config(char_name) # char_name est passé à l'init (ex: "vampire")
        
        # Widget Image de sécurité
        self.img_label = tk.Label(root, bg="white", bd=0)
        self.img_label.pack()

        # --- POSITION ET DÉPLACEMENT ---
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.x, self.y = random.randint(100, 500), random.randint(100, 500)
        self.dx, self.dy = 0, 0 
        self.speed = 4
        self.is_grabbed = False
        
        self.root.geometry(f"+{self.x}+{self.y}")
        
        # BINDINGS
       # Remplace tes anciens binds par ceux-ci :
        self.img_label.bind("<Button-1>", self.on_press)
        self.img_label.bind("<B1-Motion>", self.on_drag)
        self.img_label.bind("<ButtonRelease-1>", self.on_release)

        self.brain_loop()      
        self.animation_loop()
        self.check_time_loop() # <--- Lancement de la surveillance horaire
        self.check_visibility()


    def load_expressions(self):
        """Charge les expressions depuis le JSON ou utilise une liste par défaut."""
        default_list = ["Bonne cuisine ! 👨‍🍳", "Prêt à livrer !"]
        
        if os.path.exists(self.expressions_file):
            try:
                with open(self.expressions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # On vérifie que la clé existe et que c'est une liste
                    if isinstance(data.get('expressions'), list):
                        return data['expressions']
            except Exception as e:
                print(f"Erreur lecture expressions: {e}")
        
        # Si le fichier n'existe pas, on le crée avec la liste par défaut
        self.save_expressions(default_list)
        return default_list

    def hide_for_time(self, hours):
        """Cache le personnage pour une durée spécifique (reçue en argument)."""
        self.is_hidden = True
        
        # On multiplie le nombre d'heures reçu par 3600 (secondes dans une heure)
        self.hidden_until = datetime.now().timestamp() + (hours * 3600) 
        
        self.root.withdraw() # Cache la fenêtre complètement
        print(f"Le personnage est caché pour {hours} heure(s).")

    def reveal_pet(self):
        """Fait réapparaître le personnage proprement."""
        self.is_hidden = False
        self.hidden_until = 0 # On remet à zéro
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.state = "IDLE"

    def check_visibility(self):
        """Vérifie si le temps est écoulé pour réapparaître."""
        if self.is_hidden and self.hidden_until > 0:
            now = datetime.now().timestamp()
            if now >= self.hidden_until:
                self.reveal_pet() # Utilise la fonction de réapparition
                print("Le personnage est de retour après 4 heures !")
        
        # Relance la vérification chaque seconde
        self.root.after(1000, self.check_visibility)

    def load_character_config(self, char_name):
        try:
            if not os.path.exists(self.json_path):
                raise FileNotFoundError("Le fichier anim_perso.json est introuvable !")

            with open(self.json_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # --- LOGIQUE DE SÉLECTION ALÉATOIRE ---
            if char_name == "RANDOM":
                all_names = list(config.keys())
                if all_names:
                    # Pour éviter de retomber sur le même, on peut filtrer (optionnel)
                    char_name = random.choice(all_names)
                    print(f"🎲 Aléatoire choisi : {char_name}")
                else:
                    print("Le fichier JSON est vide !")
                    return

            if char_name in config:
                data = config[char_name]
                
                # --- NETTOYAGE ---
                self.anims.clear() 
                
                # --- CHARGEMENT ---
                for action, params in data.get("animations", {}).items():
                    full_path = os.path.join(self.asset_path, params[0])
                    if os.path.exists(full_path):
                        self.anims[action] = self.load_flexible_frames(
                            full_path, params[1], params[2], params[3]
                        )
                
                self.brain_rules = data.get("brain", [])
                
                # --- APPLICATION IMMÉDIATE ---
                self.current_state = "IDLE_01"
                self.frame_idx = 0
                
                # On s'assure que l'animation existe avant d'essayer de l'afficher
                if self.current_state in self.anims:
                    first_frame = self.anims[self.current_state][0]
                    self.label.config(image=first_frame)
                
                print(f"✅ {char_name} appliqué avec succès.")
                
        except Exception as e:
            print(f"💥 ERREUR : {e}")
            self.brain_rules = [{"state": "IDLE_01", "chance": 1.0, "movement": "stop"}]

    def check_time_loop(self):
        """Déclenche un message toutes les 10 minutes, peu importe l'heure."""
        # 1. On affiche le message (sauf si on est en train de traîner le pet)
        if not self.is_grabbed:
            self.show_message()

        # 2. On programme le prochain message dans 30 minutes exactement
        # 30 minutes * 60 secondes * 1000 millisecondes = 1 800 000 ms
        intervalle_ms = 10 * 60 * 1000 
        
        self.root.after(intervalle_ms, self.check_time_loop)
        
    def load_flexible_frames(self, filename, fw, fh, num_frames):
        """Charge et découpe les frames avec gestion d'erreur."""
        frames_r, frames_l = [], []
        try:
            sheet = Image.open(filename).convert("RGBA")
            for i in range(num_frames):
                box = (i * fw, 0, (i + 1) * fw, fh)
                frame = sheet.crop(box)
                frames_r.append(ImageTk.PhotoImage(frame))
                frames_l.append(ImageTk.PhotoImage(frame.transpose(Image.FLIP_LEFT_RIGHT)))
        except Exception as e:
            print(f"Erreur sur {filename}: {e}")
            # Création d'un carré vide si le fichier manque
            err = Image.new('RGBA', (fw, fh), (0, 0, 0, 0))
            frames_r = [ImageTk.PhotoImage(err)]
            frames_l = [ImageTk.PhotoImage(err)]
        return {"R": frames_r, "L": frames_l}

    def on_click(self, event):
        """Affiche une bulle de texte et recommence le cycle une fois épuisé."""
        
        # 1. Vérification : Si la liste est vide, on la régénère complètement
        if not hasattr(self, 'file_attente') or not self.file_attente:
            self.file_attente = self.expressions.copy()
            random.shuffle(self.file_attente)
            
        # 2. On récupère le message suivant
        msg = self.file_attente.pop()

        # --- Création du popup ---
        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        
        # Positionnement dynamique
        popup.geometry(f"+{int(self.x) + 20}+{int(self.y) - 40}")
        
        # Style de la bulle
        tk.Label(popup, text=msg, bg="#FFF9C4", fg="black", 
                relief="solid", bd=1, padx=5, font=("Arial", 9, "bold")).pack()
        
        # Auto-destruction après 2.5 secondes
        self.root.after(2500, popup.destroy)

    

    
    
    def brain_loop(self):
        """Choisit le prochain état parmi toutes les variations disponibles avec gestion d'actions spécifiques."""
        if self.is_grabbed:
            self.root.after(1000, self.brain_loop)
            return
            
        # --- GESTION DE LA PUNITION ANIMÉE ---
        if self.is_punished:
            # On récupère toutes les variantes de repos (IDLE_01, IDLE_02, etc.)
            idle_variants = [s for s in self.anims.keys() if "IDLE" in s.upper()]
            
            if idle_variants:
                self.state = random.choice(idle_variants)
            else:
                self.state = "IDLE" # Repli si aucune variante n'est trouvée
                
            self.speed = 0
            self.dx, self.dy = 0, 0
            self.current_frame = 0 # On reset la frame pour lancer la nouvelle animation
            
            # Change de direction de regard aléatoirement pour simuler l'ennui
            self.facing_right = random.choice([True, False])

            # On relance le cerveau entre 3 et 6 secondes pour changer de posture d'IDLE
            self.root.after(random.randint(3000, 6000), self.brain_loop) 
            return

        # --- COMPORTEMENT NORMAL ---
        self.is_waiting = False 
        
        try:
            states_available = list(self.anims.keys())
            if not states_available:
                self.state = "IDLE"
                return

            # Sélection d'un nouvel état aléatoire
            self.state = random.choice(states_available)
            self.current_frame = 0
            
            upper_state = self.state.upper()

            # --- LOGIQUE DE VITESSE ET DIRECTION SELON L'ACTION ---
            
            # 1. État de Course (Rapide)
            if "RUN" in upper_state:
                self.speed = 8
                self.dx = random.choice([-1, 1])
                self.dy = 0
                
            # 2. État de Marche (Normal)
            elif "WALK" in upper_state:
                self.speed = 3
                self.dx = random.choice([-1, 1])
                self.dy = 0
                
            # 3. État de Vol (Mouvement vertical autorisé)
            elif "FLY" in upper_state:
                self.speed = 5
                self.dx = random.choice([-1, 1])
                self.dy = random.choice([-1, 0, 1]) # Peut monter, descendre ou stagner
                
            # 4. État de Saut (Impulsion initiale vers le haut)
            elif "JUMP" in upper_state:
                self.speed = 5
                self.dx = random.choice([-1, 1])
                self.dy = -4 # Cette valeur sera gérée par la gravité dans move_logic
                
            # 5. États Statiques ou Spéciaux (EAU, FEU, COUCOU, IDLE)
            else:
                self.speed = 0
                self.dx, self.dy = 0, 0

        except Exception as e:
            print(f"❌ Erreur critique dans brain_loop: {e}")
            # En cas de crash, on tente de trouver n'importe quel IDLE pour rester stable
            self.state = next((s for s in states_available if "IDLE" in s.upper()), "IDLE")

        # Mise à jour de l'orientation visuelle selon le mouvement horizontal
        if self.dx > 0: 
            self.facing_right = True
        elif self.dx < 0: 
            self.facing_right = False


    def move_logic(self):
        """Déplace la fenêtre avec rebonds physiques, lancer, et maintien sur l'écran 1."""
        # On ne calcule pas la physique si on est en train de le traîner
        if self.is_grabbed or self.is_waiting:
            return

        # --- 1. LOGIQUE DE PUNITION (Téléportation ou arrêt au coin) ---
        if self.is_punished:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            self.x = sw - 250
            self.y = sh - 150
            self.speed = 0
            self.root.geometry(f"+{int(self.x)}+{int(self.y)}")
            return

        # --- 2. GESTION DE LA VÉLOCITÉ (LANCER) ---
        # Si on l'a lancé, il ralentit progressivement (friction)
        if self.speed > 2.5:
            self.speed *= 0.97  
        else:
            self.speed = 2 # Vitesse de croisière minimale

        # --- 3. LOGIQUE DE SAUT / VOL ---
        if "JUMP" in self.state:
            jump_progress = self.current_frame / (len(self.anims[self.state]["R"]) or 1)
            self.dy = -4 + (jump_progress * 8) 
        elif "FLY" in self.state:
            import math
            self.dy += math.sin(self.current_frame * 0.5) * 0.2

        # --- 4. APPLICATION DU MOUVEMENT ---
        self.x += self.dx * self.speed
        self.y += self.dy * self.speed

        # --- 5. COLLISIONS ET REBONDS RÉELS (ÉCRAN 1) ---
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        padding = 128 

        # REBOND HORIZONTAL (Gauche / Droite)
        if self.x <= 0:
            self.x = 0
            self.dx = abs(self.dx)  # Force à aller vers la droite (positif)
            self.facing_right = True
        elif self.x >= sw - padding:
            self.x = sw - padding
            self.dx = -abs(self.dx) # Force à aller vers la gauche (négatif)
            self.facing_right = False

        # REBOND VERTICAL (Haut / Bas)
        if self.y <= 0:
            self.y = 0
            self.dy = abs(self.dy) # Rebondit vers le bas
        elif self.y >= sh - padding:
            self.y = sh - padding
            
            # Si le perso arrive avec de la vitesse (lancer)
            if self.speed > 4:
                self.dy = -abs(self.dy) * 0.7 # Rebondit vers le haut avec perte d'énergie
            else:
                # Comportement normal au sol
                if any(s in self.state.upper() for s in ["JUMP", "WALK", "RUN"]):
                    self.dy = 0
                else:
                    self.dy = -0.5 # Petit flottement

        # --- 6. MISE À JOUR FINALE ---
        self.root.geometry(f"+{int(self.x)}+{int(self.y)}")

    def animation_loop(self):
        """Gère les images avec détection d'erreurs, vitesse adaptative et mode caché."""
        try:
            # --- 1. VÉRIFICATION DU MODE CACHÉ ---
            if self.is_hidden:
                # On ne fait rien, on relance juste la boucle plus tard 
                # pour vérifier quand self.is_hidden repassera à False
                self.root.after(500, self.animation_loop)
                return

            now = datetime.now().timestamp()
            if self.is_punished and now > self.punishment_end:
                self.is_punished = False
                self.state = "IDLE"

            # Délai par défaut (en millisecondes)
            animation_delay = 100 

            if not self.is_grabbed:
                self.move_logic()
                
                side = "R" if self.facing_right else "L"
                
                if self.state in self.anims and side in self.anims[self.state]:
                    frames = self.anims[self.state][side]
                    num_frames = len(frames)
                    
                    if not frames:
                        raise ValueError(f"Liste d'images vide pour {self.state}")

                    # --- LOGIQUE DE VITESSE ---
                    if num_frames <= 8:
                        animation_delay = 200
                    elif num_frames >= 12:
                        animation_delay = 150
                    else:
                        animation_delay = 150 

                    if self.current_frame >= num_frames:
                        self.current_frame = 0
                    
                    self.img_label.config(image=frames[self.current_frame])
                    self.current_frame += 1
                    
                    if self.current_frame >= num_frames:
                        if not self.is_waiting and not self.is_punished:
                            self.is_waiting = True
                            self.dx, self.dy = 0, 0
                            self.root.after(1000, self.brain_loop) 
                else:
                    self.state = "IDLE"

            # On relance la boucle avec le délai calculé
            self.root.after(animation_delay, self.animation_loop)

        except Exception as e:
            print(f"Erreur animation: {e}")
            self.state = "IDLE"
            self.root.after(100, self.animation_loop)

    def on_press(self, event):
        """Fusion de on_click et du chrono menu : Gère messages, punition et 10s."""
        now = datetime.now().timestamp()

        # 1. GESTION SI DÉJÀ EN PUNITION (Tes 100 messages)
        if self.is_punished:
            if now < self.punishment_end:
                messages_boude = [
                    "GRR ! Laisse-moi tranquille ! 💢", "NON ! 😤", "ARRÊTE ! Je bouillonne là ! 🔥",
                    "Touche-moi encore et je mords ! 🦷", "GRRR... Je suis un tigre féroce ! 🐯",
                    "Méchant humain ! 😠", "C'est fini entre nous pour 5 minutes ! 💔",
                    "Ne me regarde même pas ! 🙈", "Je suis en pétard ! 🧨", "Hé ! Mes poils se hérissent ! 🐈",
                    "Je ne suis pas d'humeur ! 👺", "Vade Retro Satana ! ✝️", "C'est la guerre ! ⚔️",
                    "Tu vas tâter de mes griffes ! 🐾", "Même pas en rêve ! 💭", "Je fulmine ! 💨",
                    "Alerte ! Zone de danger ! ⚠️", "Je suis une petite boule de rage ! 💣",
                    "PFF... Je ne te parle plus. 🙄", "M'en fiche, je boude. 😒", "Même pas mal. 💅",
                    "Cause toujours, tu m'intéresses... 🥱", "Je t'ignore royalement. 👑",
                    "Tu parles à mon dos là. 🎒", "Bof. 😑", "Quel ennui... 🌫️", "Inintéressant. ☁️",
                    "Je fais la grève du clic ! 🪧", "Désolé, je suis en mode avion. ✈️",
                    "Cherche pas, je suis ailleurs. 🌌", "Bla bla bla... 🗣️", "Zéro attention pour toi. 📉",
                    "Je suis invisible, tu ne me vois pas. 👻", "Silence radio. 📻",
                    "ZZZ... (Fait semblant de dormir) 😴", "Je dors, reviens jamais ! 💤",
                    "Ron-pschiiit... 🌙", "Dodo thérapeutique. 🛌", "Ne pas déranger l'artiste. 🎨",
                    "Mon cerveau est en maintenance. 🛠️", "Mode hibernation activé. ❄️",
                    "Je recharge mes batteries loin de toi. 🔋", "Trop fatigué pour tes bêtises. 🦇",
                    "Je suis en grève, contacte mon syndicat. ✊", "Error 404: Patience not found. 🚫",
                    "Je suis un fantôme maintenant. Houuu ! 👻", "Appelle mon avocat ! ⚖️",
                    "Je suis parti vivre sur Mars. 🚀", "Je médite pour ne pas t'exploser. 🧘",
                    "Je compte les pixels au plafond. 🔢", "Je prépare ma vengeance... 😈",
                    "C'est mon quart d'heure de drama. 🎭", "Je suis une statue de sel. 🧂",
                    "Alerte : Trop de clics, système surchauffé ! 🌡️",
                    "Je transforme tes clics en poussière d'étoile. ✨",
                    "Na ! 😝", "Tu l'as bien cherché ! 🤷", "C'est ton problème, pas le mien. 🧩",
                    "Bouderie niveau 100 activée. 📈", "Je fais la tête et j'aime ça. 🗿",
                    "Regarde ailleurs, je suis moche quand je boude. 👺",
                    "Même mes oreilles boudent. 👂", "Je me retire de la vie publique. 🚪",
                    "Privé de chat pour aujourd'hui ! 🚫", "Je vais dire à tout le monde que t'es méchant. 📢",
                    "Je suis tout petit mais ma colère est géante ! 🌋", "Pas de câlin ! 🙅",
                    "Je suis une noisette en colère. 🌰", "Pousse pas mémé dans les orties ! 🌿",
                    "Je boude, mais je suis toujours beau. ✨", "Mon petit cœur est en pierre. 💎",
                    "Je fais la moue. 😗", "Je me cache dans ma boîte imaginaire. 📦",
                    "NON. 🛑", "STOP. ✋", "OUBLIE. 🧠", "CHUT ! 🤫", "MERCI, NON. 🙅‍♂️",
                    "BYE. 👋", "FINI. 🏁", "NOPE. 👎", "NADA. ⭕", "LATER. ⏳",
                    "On fera les comptes plus tard. 🧮", "Tu ne perds rien pour attendre... 🕰️",
                    "Ma vengeance sera terrible (et mignonne). 🎀",
                    "Attend que je sorte de ce panier ! 🧺", "Tu joues avec le feu là... 🔥",
                    "Un jour, je viderai ta batterie pour me venger. 🔌",
                    "Je note ton nom sur ma liste noire. 📝",
                    "T'as de la chance que je sois coincé dans l'écran ! 🖥️",
                    "Ma patience a des limites, et tu les as sautées ! 🚩",
                    "Je vais hanter ton curseur ! 🖱️"
                ]
                self.show_message(random.choice(messages_boude))
                return 
            else:
                self.is_punished = False 

        # 2. ENREGISTRER LE CLIC ET MESSAGE NORMAL
        self.click_times.append(now)
        self.click_times = [t for t in self.click_times if now - t < 5]
        
        if len(self.click_times) < 5:
            self.show_message() # Ton message normal de clic

        # 3. DÉCLENCHEMENT DE LA PUNITION (5 clics rapides)
        if len(self.click_times) >= 5:
            self.is_punished = True
            self.punishment_end = now + (5 * 60)
            self.is_grabbed = False
            self.press_start_time = 0
            
            sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            self.x, self.y = sw - 250, sh - 150
            
            idle_anims = [s for s in self.anims.keys() if "IDLE" in s.upper()]
            self.state = random.choice(idle_anims) if idle_anims else "IDLE"
            self.speed = 0
            self.root.geometry(f"+{int(self.x)}+{int(self.y)}")
            # --- LISTE DES PHRASES DE BOUDERIE ---
            boudes = [
                "C'EST TROP ! 💢\nJe m'en vais bouder dans mon coin !",
                "TU ABUSES ! 💢\nJe vais méditer dans le noir !",
                "C'EST ASSEZ ! 😤\nJe ne te parle plus pendant un bout !",
                "OK, J'ARRÊTE ! 🛑\nOn se reverra quand je serai calme !",
                "TROP DE CLICS ! 😵‍💫\nMa patience a des limites, bye !",
                "ADIEU MONDE CRUEL ! 🎭\nJe pars en exil sous une fenêtre !",
                "ALERTE ROUGE ! 🔥\nJe disparais avant de faire une crise !",
                "NON MAIS ÇA VA PAS ? 🤨\nJe prends ma retraite anticipée !",
                "JE DÉMISSIONNE ! 💼\nTrouve-toi un autre compagnon !",
                "SILENCE RADIO ! 🤐\nJe vais réfléchir à notre relation !",
                "SYSTÈME SURCHAUFFÉ ! 🔥\nJe vais refroidir mon ego ailleurs !",
                "MODE BOUDERIE ACTIVÉ ! 🤖\nRecharge de patience en cours...",
                "JE FERME BOUTIQUE ! 🏚️\nReviens quand tu seras plus doux !",
                "TROP DE PRESSION ! 🎈\nJe m'en vais avant d'éclater !",
                "C'EST LA GOUTTE D'EAU ! 💧\nJe pars faire la planche au fond de l'écran !",
                "ZONE DE TURBULENCE ! 🌪️\nJe me retire dans mon bunker secret !",
                "JE FAIS GRÈVE ! 🪧\nPas de Pet pour les 5 prochaines minutes !",
                "TROP DE BRUIT ! 📢\nJe cherche un coin de silence absolu !",
                "TU M'AS CASSÉ ! 🛠️\nJe vais me réparer loin de tes clics !",
                "OVERDOSE DE CONTACT ! ⚡\nJe vais m'isoler dans le BIOS !",
                "JE SUIS OUTRAGE ! 🧐\nUne telle attitude mérite un silence !",
                "BYE BYE LES AMIS ! 🏃\nJe pars en vacances forcées !",
                "MA PÉRENNITÉ EST EN JEU ! ⚠️\nJe me mets en sécurité !",
                "SENSURÉ PAR MOI-MÊME ! 🤐\nJe n'ai plus rien à te dire !",
                "CRÈVE-CŒUR ! 💔\nJe vais soigner mes pixels en privé !",
                "JE PRENDS LE LARGE ! ⛵\nDirection le dossier Mes Documents !",
                "C'EST LE CLASH ! 💥\nJe coupe le contact visuel !",
                "DÉCONNEXION ÉMOTIONNELLE ! 🔌\nJe ne réponds plus de rien !",
                "JE VAIS VOIR AILLEURS ! 🗺️\nSi j'y suis, j'y reste !",
                "FIN DE SERVICE ! 🔚\nLe rideau tombe, je boude !"
            ]

            # --- DANS VOTRE FONCTION DE PUNITION ---
            # Utilise random.choice pour piger une phrase au hasard dans la liste ci-dessus
            self.show_message(random.choice(boudes))
            self.click_times = []
            return

        # 4. INITIALISATION DU GRAB ET CHRONO MENU (10s)
        self.is_grabbed = True
        self.press_start_time = now
        self.offset_x, self.offset_y = event.x, event.y
        self.last_mouse_x, self.last_mouse_y = event.x_root, event.y_root
        self.inertia_x, self.inertia_y = 0, 0

        # Lancement de la surveillance auto pour le menu
        self.check_long_press()
        
    def check_long_press(self):
        """Vérifie le temps en boucle, même sans bouger la souris."""
        if self.is_grabbed and self.press_start_time > 0:
            duration = datetime.now().timestamp() - self.press_start_time
            
            # J'ai mis 10.0 secondes comme demandé
            if duration >= 4.0:
                self.is_grabbed = False
                self.press_start_time = 0 # Reset immédiat
                self.show_character_menu()
                return # Arrêt de la boucle
            
            # Revérifier dans 100ms
            self.root.after(100, self.check_long_press)
    
    

    def update_message_position(self):
        """Repositionne le message au-dessus du personnage s'il existe."""
        if hasattr(self, 'msg_popup') and self.msg_popup.winfo_exists():
            # Calcul de la nouvelle position (centré au-dessus du pet)
            w = self.msg_popup.winfo_width()
            # On utilise int() pour s'assurer que les coordonnées sont des nombres entiers
            pos_x = int(self.x + 64 - (w / 2))
            pos_y = int(self.y - 60) 
            self.msg_popup.geometry(f"+{pos_x}+{pos_y}")

    def on_drag(self, event):
        """Déplacement uniquement si on est toujours en mode grabbed."""
        if self.is_grabbed:
            self.inertia_x = event.x_root - self.last_mouse_x
            self.inertia_y = event.y_root - self.last_mouse_y
            self.last_mouse_x = event.x_root
            self.last_mouse_y = event.y_root

            self.x = event.x_root - self.offset_x
            self.y = event.y_root - self.offset_y
            self.root.geometry(f"+{int(self.x)}+{int(self.y)}")
            
            # --- LA LIGNE À AJOUTER ICI ---
            self.update_message_position()

    def on_release(self, event):
        """Nettoyage total pour permettre une réutilisation immédiate."""
        self.is_grabbed = False
        self.press_start_time = 0 # Arrête check_long_press
        
        force = (abs(self.inertia_x) + abs(self.inertia_y))
        if force > 3:
            self.dx = 1 if self.inertia_x > 0 else -1
            self.dy = 1 if self.inertia_y > 0 else -1
            self.speed = min(force, 35)
            if "FLY" in self.anims: self.state = "FLY"
        else:
            self.speed = 2

    def show_character_menu(self):
        """Affiche le menu même si puni et permet de cacher le pet."""
        # if self.is_punished: return  <-- SUPPRIMÉ pour que ça marche tout le temps

        if self.active_menu is not None and self.active_menu.winfo_exists():
            self.active_menu.lift()
            return

        try:
            with open(self.json_path, 'r') as f:
                config = json.load(f)
                character_names = list(config.keys())
                
            self.active_menu = CharacterSelector(
                self.root, 
                character_names, 
                self.change_character, 
                self.hide_for_time,
                self.last_mouse_x, 
                self.last_mouse_y
            )
            
            self.active_menu.bind("<Destroy>", lambda e: setattr(self, 'active_menu', None))

        except Exception as e:
            print(f"Erreur menu: {e}")

    def change_character(self, name):
        """Change le personnage, charge les images et force le premier plan."""
        try:
            # 1. Sécurité : Initialisation de la variable si absente
            if not hasattr(self, 'current_character'):
                self.current_character = name
            elif name == self.current_character:
                return

            print(f"🔄 Tentative de chargement : {name}...")
            
            # 2. On réinitialise les compteurs AVANT de charger pour éviter les crashs d'index
            self.current_frame = 0
            self.state = "IDLE_01"
            self.current_character = name

            # 3. ON APPELLE TA FONCTION DE CHARGEMENT
            # Vérifie bien que ce nom correspond exactement à ta fonction (ligne 7xx)
            self.load_character_config(name)
            
            # 4. FORCER LA MISE À JOUR VISUELLE IMMÉDIATE
            # On prend la première image du nouvel état pour éviter un label vide
            side = "R" if self.facing_right else "L"
            if self.state in self.anims and side in self.anims[self.state]:
                first_frame = self.anims[self.state][side][0]
                self.img_label.config(image=first_frame)

            # 5. FORCER LE RETOUR AU PREMIER PLAN
            self.root.deiconify()           # Sort de la barre des tâches
            self.root.attributes("-topmost", True) # Force devant
            self.root.lift()                # Remonte la pile
            self.root.focus_force()         # Prend l'attention
            
            print(f"✅ {name} est maintenant actif et au premier plan.")

        except Exception as e:
            print(f"💥 ERREUR CRITIQUE lors du changement de perso: {e}")
            # En cas d'erreur, on essaie de revenir à un état stable
            self.state = "IDLE"
            self.current_frame = 0

    def on_toss(self, event):
        """Relance le comportement du personnage quand on le lâche."""
        self.is_grabbed = False
        self.menu_opened = False 
        
        # On remet l'état par défaut
        self.state = "IDLE"
        self.current_frame = 0 # Recommence l'anim au début
        
        # --- ESSENTIEL : On relance le cerveau immédiatement ---
        # On attend un tout petit peu (100ms) pour laisser Tkinter 
        # stabiliser la position de la fenêtre après le lâcher.
        self.root.after(200, self.brain_loop)
    
    def show_message(self, msg=None):
        """Affiche une bulle de texte avec dégradé rouge si punie."""
        # 1. On détruit l'ancien message s'il existe déjà pour éviter les superpositions
        if hasattr(self, 'msg_popup') and self.msg_popup.winfo_exists():
            self.msg_popup.destroy()

        if msg is None:
            msg = random.choice(self.expressions)
            
        # 2. ON UTILISE self.msg_popup au lieu de popup
        self.msg_popup = tk.Toplevel(self.root)
        self.msg_popup.overrideredirect(True)
        self.msg_popup.attributes("-topmost", True)
        
        bg_color = "#FFFFFE" 
        self.msg_popup.config(bg=bg_color)
        self.msg_popup.attributes("-transparentcolor", bg_color)
        
        # --- CONFIGURATION DES COULEURS ---
        if self.is_punished:
            color_top = (255, 50, 50)    
            color_bottom = (150, 0, 0)
            text_color = "white"
        else:
            color_top = (255, 255, 255)
            color_bottom = (240, 240, 240)
            text_color = "black"

        # --- CRÉATION DU DÉGRADÉ ---
        w, h = 160, 80 
        gradient_img = Image.new('RGB', (w, h), color_top)
        pixels = gradient_img.load()
        for y in range(h):
            r = int(color_top[0] + (color_bottom[0] - color_top[0]) * (y / h))
            g = int(color_top[1] + (color_bottom[1] - color_top[1]) * (y / h))
            b = int(color_top[2] + (color_bottom[2] - color_top[2]) * (y / h))
            for x in range(w):
                pixels[x, y] = (r, g, b)
        
        self.msg_bg_image = ImageTk.PhotoImage(gradient_img)

        # On utilise un Canvas
        canvas = tk.Canvas(self.msg_popup, width=w, height=h, bg=bg_color, highlightthickness=3, highlightbackground="black")
        canvas.pack()
        
        canvas.create_image(w/2, h/2, image=self.msg_bg_image)
        
        canvas.create_text(
            w/2, h/2, 
            text=msg, 
            fill=text_color, 
            font=("Comic Sans MS", 10, "bold"),
            width=w-20, 
            justify="center"
        )

        # --- POSITIONNEMENT INITIAL ---
        # On appelle directement notre nouvelle fonction de positionnement
        self.update_message_position()
        
        # On ferme après 2.5 secondes
        self.root.after(2500, self.msg_popup.destroy)
    
        
if __name__ == "__main__":
    main_root = tk.Tk()
    main_root.withdraw() 
    # Utilisation d'un Toplevel pour éviter les problèmes de focus de la fenêtre root
    pet_window = tk.Toplevel(main_root)
    app = DesktopPet(pet_window)
    main_root.mainloop()