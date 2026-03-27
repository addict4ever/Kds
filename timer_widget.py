import tkinter as tk
from tkinter import messagebox, ttk
import time
from threading import Thread, Event
import uuid
import random 
import platform 
import os 
import subprocess 
from typing import Optional

os.environ['SDL_AUDIODRIVER'] = 'dummy'

# --- IMPORTS POUR LE SON MP3 ---
# Nécessite : pip install pygame
try:
    import pygame.mixer as mixer
    # L'initialisation doit être faite AVANT de charger ou jouer un son
    mixer.init() 
    SUPPORTS_MP3 = True
except ImportError:
    SUPPORTS_MP3 = False
    print("ATTENTION: Pygame n'est pas installé. La lecture des MP3 ne fonctionnera pas.")

# --- Imports pour les sons (Windows uniquement) ---
try:
    if platform.system() == "Windows":
        import winsound
except ImportError:
    winsound = None 
    
# --- Configuration des sons du minuteur (MP3 et Bips) ---
# Chemin du dossier musique
MUSIC_FOLDER = "musique"

# Les 3 choix de sonnerie MP3
TIMER_SOUNDS = {
    1: {"name": "Pop Fire", "file": os.path.join(MUSIC_FOLDER, "pop-fireworks-274597.mp3"), "windows_beep": (1000, 500)}, 
    2: {"name": "Rock Power", "file": os.path.join(MUSIC_FOLDER, "rock-power-ringtone-245179.mp3"), "windows_beep": (800, 200)}, 
    3: {"name": "Pop Energy", "file": os.path.join(MUSIC_FOLDER, "pop-energy-beat-250249.mp3"), "windows_beep": (1500, 300)}, 
}
# -----------------------------------------------------

# --- Fonction ALARME MINUTEUR (Réelle) ---
def play_timer_alarm(sound_id: int):
    """
    Jouer l'alarme du minuteur. 
    """
    
    sound_data = TIMER_SOUNDS.get(sound_id, TIMER_SOUNDS[1]) 
    sound_file = sound_data.get("file")
    
    # 1. TENTE DE JOUER LE MP3 EN BOUCLE VIA PYGAME
    if SUPPORTS_MP3 and sound_file and os.path.exists(sound_file):
        try:
            mixer.music.stop()
            mixer.music.load(sound_file)
            # Joue en boucle infinie (le paramètre -1)
            mixer.music.play(-1) 
            return # Succès, on sort
            
        except Exception as e:
            print(f"Erreur Pygame lors de la lecture de {sound_file}: {e}. Tentative de BEEP de secours.")
            
    # 2. MÉTHODE DE REPLI (Bips ou Son Système - Joue une seule fois)
    
    if platform.system() == "Windows" and winsound:
        frequency, duration = sound_data.get("windows_beep", (1000, 500))
        winsound.Beep(frequency, duration)
        
    elif platform.system() == "Darwin": # macOS
        os.system(f'afplay /System/Library/Sounds/Tink.aiff &')
        
    elif platform.system() == "Linux": # Linux
        os.system('echo -e "\a" &') 
        
    else:
        print(f"ALARME: Son de secours activé pour {sound_data['name']}. Pas de boucle automatique.")
        
# Constantes de couleur
COLOR_BACKGROUND = "#34495e" 
COLOR_TEXT = "#ecf0f1"
COLOR_WARNING = "#f1c40f"
COLOR_FINISHED = "#e74c3c"
COLOR_ALARM_FLASH = "#c0392b" 

class TimerWidget(tk.Toplevel):
    """
    VERSION FINALE : Physique Tactile avec rebonds sur les 4 bords
    et système de Buzzer (sans musique).
    """
    def __init__(self, master, timer_id, name, duration_seconds, sound_id, remove_callback):
        super().__init__(master) 
        self.timer_id = timer_id
        self.name = name
        self.duration_seconds = duration_seconds
        self.sound_id = sound_id
        self.remove_callback = remove_callback
        
        # --- CONFIGURATION FENÊTRE ---
        self.overrideredirect(True) 
        self.attributes("-topmost", True) 
        self.geometry("300x150") 
        self.config(bg=COLOR_BACKGROUND, borderwidth=2, relief="raised") 
        
        # --- MOTEUR PHYSIQUE ---
        self.vx = 0
        self.vy = 0
        self.friction = 0.98     # Glisse
        self.bounce = -0.75      # Force du rebond
        self.is_tossed = False
        self._offset_x = 0
        self._offset_y = 0
        self.move_history = []

        # --- LOGIQUE ---
        self.is_finished = False 
        self.is_running = False
        self.stop_event = Event()
        self.thread = None
        self.start_time = None
        self.remaining_seconds = duration_seconds
        self.alarm_loop_id = None 

        # --- INTERFACE ---
        self.canvas = tk.Canvas(self, bg=COLOR_BACKGROUND, highlightthickness=0, bd=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)

        self.name_label = tk.Label(self, text=name, bg=COLOR_BACKGROUND, fg="white", font=("Arial", 18, "bold"))
        self.name_label.pack(pady=(5, 0))
        
        self.time_label = tk.Label(self, text=self._format_time(duration_seconds), bg=COLOR_BACKGROUND, fg=COLOR_TEXT, font=("Arial", 22, "bold"))
        self.time_label.pack(pady=2)
        
        button_frame = tk.Frame(self, bg=COLOR_BACKGROUND)
        button_frame.pack(pady=5)
        
        btn_font = ("Arial", 18, "bold")
        self.start_button = tk.Button(button_frame, text="▶️", command=self.start_timer, bg="#2ecc71", fg="white", font=btn_font, width=2)
        self.start_button.pack(side=tk.LEFT, padx=1)
        
        self.reset_button = tk.Button(button_frame, text="↩️", command=self.reset_timer, bg="#f39c12", fg="white", font=btn_font, width=2)
        self.reset_button.pack(side=tk.LEFT, padx=1)
        
        self.remove_button = tk.Button(button_frame, text="❌", command=self._on_close, bg=COLOR_FINISHED, fg="white", font=btn_font, width=2)
        self.remove_button.pack(side=tk.LEFT, padx=1)

        # Bindings tactiles sur tous les éléments
        for w in [self, self.name_label, self.time_label, self.canvas]:
            w.bind('<Button-1>', self._start_drag)
            w.bind('<B1-Motion>', self._drag)
            w.bind('<ButtonRelease-1>', self._stop_drag)
            w.bind('<Double-Button-1>', lambda e: self._on_close())

    def _3play_buzzer(self):
        """Joue un son de buzzer haute fréquence (très audible)"""

        def run_sound():
            try:
                import winsound
                import random
                import time

                # Fréquences réglées entre 2500 et 4000 Hz pour un volume perçu maximum
                sounds = [
                    # 1️⃣ Beep simple strident
                    [(3000, 250)],

                    # 2️⃣ Double choc aigu
                    [(3500, 100), (0, 50), (3500, 100)],

                    # 3️⃣ Alerte rapide perçante
                    [(4000, 80), (0, 40), (4000, 80)],

                    # 4️⃣ Montée aiguë
                    [(2500, 100), (3200, 100), (3900, 150)],

                    # 5️⃣ Erreur critique (Alternance rapide)
                    [(2000, 200), (0, 50), (2000, 200)],

                    # 6️⃣ Triple scan
                    [(3000, 80), (3500, 80), (4000, 80)],

                    # 7️⃣ Bip laser
                    [(3800, 50), (3600, 50), (3400, 50)],

                    # 8️⃣ Alarme longue
                    [(3200, 600)],

                    # 9️⃣ SOS ultra-rapide
                    [(3500, 50), (0, 30), (3500, 50), (0, 30), (3500, 50)],

                    # 🔟 Radar strident
                    [(2800, 100), (0, 150), (3800, 100)],

                    # 1️⃣1️⃣ Double ton discordant (très désagréable/audible)
                    [(3000, 150), (2800, 150)],

                    # 1️⃣2️⃣ Pic aigu
                    [(4200, 100)],

                    # 1️⃣3️⃣ Réveil d'urgence
                    [(3000, 200), (0, 100), (3500, 250)],

                    # 1️⃣4️⃣ Confirmation haute
                    [(3200, 100), (3800, 200)],

                    # 1️⃣5️⃣ Sirène accélérée
                    [(2500, 80), (3000, 80), (3500, 80), (4000, 150)]
                ]

                notes = random.choice(sounds)

                for freq, dur in notes:
                    # Vérification de l'état (assure-toi que self.is_finished est logique ici)
                    if not self.is_finished: 
                        break
                    if freq == 0:
                        time.sleep(dur / 1000)
                    else:
                        # winsound.Beep(fréquence, durée)
                        winsound.Beep(freq, dur)

            except Exception as e:
                print("Erreur buzzer:", e)

        import threading
        threading.Thread(target=run_sound, daemon=True).start()

    # --- SECTION SON (BUZZER) ---
    def _play_buzzer(self):
        def run_sound():
            try:
                import winsound
                import time
                # La fréquence 3500Hz est perçue comme la plus "agressive" et forte
                # On crée une rafale de 3 bips ultra-rapides pour percer le silence
                for _ in range(3):
                    winsound.Beep(2500, 150) # Fréquence stridente
                    time.sleep(0.05)         # Pause minuscule pour l'effet de répétition
            except: 
                pass

        from threading import Thread
        Thread(target=run_sound, daemon=True).start()

    # --- SECTION PHYSIQUE (REBONDS 4 CÔTÉS) ---
    def _start_drag(self, event):
        self.is_tossed = False
        self._offset_x = event.x
        self._offset_y = event.y
        self.move_history = [(time.time(), event.x_root, event.y_root)]

    def _drag(self, event):
        self.move_history.append((time.time(), event.x_root, event.y_root))
        if len(self.move_history) > 5: self.move_history.pop(0)
        nx = self.winfo_x() + event.x - self._offset_x
        ny = self.winfo_y() + event.y - self._offset_y
        self.geometry(f"+{nx}+{ny}")

    def _stop_drag(self, event):
        if len(self.move_history) >= 2:
            t1, x1, y1 = self.move_history[0]
            t2, x2, y2 = self.move_history[-1]
            dt = t2 - t1
            if dt > 0:
                self.vx = (x2 - x1) / (dt * 45)
                self.vy = (y2 - y1) / (dt * 45)
                self.is_tossed = True
                self._apply_physics()

    def _apply_physics(self):
        if not self.is_tossed or not self.winfo_exists(): return

        # Taille de l'écran et du widget
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        ww = self.winfo_width()
        wh = self.winfo_height()
        
        # Position actuelle + vitesse
        nx = self.winfo_x() + self.vx
        ny = self.winfo_y() + self.vy

        # --- REBOND GAUCHE / DROITE ---
        if nx <= 0:
            nx = 0
            self.vx *= self.bounce
        elif nx + ww >= sw:
            nx = sw - ww
            self.vx *= self.bounce

        # --- REBOND HAUT / BAS ---
        if ny <= 0:
            ny = 0
            self.vy *= self.bounce
        elif ny + wh >= sh:
            ny = sh - wh
            self.vy *= self.bounce

        # Amortissement constant
        self.vx *= self.friction
        self.vy *= self.friction

        try:
            self.geometry(f"+{int(nx)}+{int(ny)}")
            # On continue tant qu'il y a de la vitesse
            if abs(self.vx) > 0.3 or abs(self.vy) > 0.3:
                self.after(10, self._apply_physics)
            else:
                self.is_tossed = False
        except: pass

    # --- LOGIQUE MINUTEUR ---
    def _format_time(self, seconds):
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        return f"{h:01d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

    def start_timer(self):
        if not self.is_running and not self.is_finished:
            self.start_time = time.time() - (self.duration_seconds - self.remaining_seconds)
            self.is_running = True
            self.stop_event.clear()
            self.start_button.config(text="⏸️", bg="#9b59b6", command=self.pause_timer)
            if not self.thread or not self.thread.is_alive():
                self.thread = Thread(target=self._run_timer, daemon=True)
                self.thread.start()

    def pause_timer(self):
        self.is_running = False
        self.stop_event.set()
        self.start_button.config(text="▶️", bg="#2ecc71", command=self.start_timer)

    def reset_timer(self):
        self._stop_alarm_loop()
        self.pause_timer()
        self.is_finished = False
        self.remaining_seconds = self.duration_seconds
        self.start_button.config(text="▶️", state=tk.NORMAL)
        self._update_colors(COLOR_BACKGROUND, COLOR_TEXT, self.duration_seconds)

    def _run_timer(self):
        while self.is_running and not self.stop_event.is_set():
            rem = self.duration_seconds - (time.time() - self.start_time)
            if rem <= 0:
                self.after(0, self._trigger_finished)
                break
            bg = COLOR_FINISHED if rem <= 10 and int(rem) % 2 == 0 else COLOR_BACKGROUND
            fg = COLOR_WARNING if rem <= 60 else COLOR_TEXT
            self.after(0, lambda b=bg, f=fg, r=rem: self._update_colors(b, f, r))
            time.sleep(0.1)

    def _update_colors(self, bg, fg, t):
        if not self.winfo_exists(): return
        try:
            self.config(bg=bg)
            self.name_label.config(bg=bg)
            self.time_label.config(bg=bg, fg=fg, text=self._format_time(t))
            self.canvas.config(bg=bg)
        except: pass

    def _trigger_finished(self):
        self.is_finished = True
        self.time_label.config(text="FINI !", fg="white")
        self.start_button.config(text="🔇 OK", command=self._stop_alarm_and_confirm, bg="#1abc9c")
        self._loop_alarm()

    def _loop_alarm(self):
        """Boucle de clignotement et de BIP (Buzzer)."""
        if self.is_finished and self.winfo_exists():
            self._play_buzzer() # Bip à chaque cycle
            
            # Clignotement visuel
            new_bg = COLOR_ALARM_FLASH if self.cget('bg') == COLOR_FINISHED else COLOR_FINISHED
            self._update_colors(new_bg, "white", 0)
            
            self.alarm_loop_id = self.after(1000, self._loop_alarm)

    def _stop_alarm_loop(self):
        if self.alarm_loop_id: 
            self.after_cancel(self.alarm_loop_id)
            self.alarm_loop_id = None

    def _stop_alarm_and_confirm(self):
        self._stop_alarm_loop()
        self.reset_timer()

    def _on_close(self):
        self.is_running = False
        self.stop_event.set()
        self._stop_alarm_loop()
        self.remove_callback(self.timer_id)
        if self.winfo_exists(): self.destroy()

    def on_close(self): self._on_close()
# ----------------------------------------------------------------------
# Fenêtre de gestion des minuteurs (TimerManagerWindow)
# ----------------------------------------------------------------------
QUICK_PRESETS = [
    ("🥔 Patates Four", 60 * 60), 
    ("🍕 Pain Pizza", 24 * 60),
    ("🍖 Côtes Levées", 12 * 60),
    ("🍤 Crevettes", 12 * 60),
    ("🧅 Soupe Oignon", 2 * 60),
    ("🐚 Entree Coquille", 2 * 60), # Changé 🧅 pour 🐚
    ("🥪 Smoke Meat", 2 * 60),      # Changé 🧅 pour 🥪
    ("🍄 Champignons Gratinés", 2 * 60),
    ("🍕 Pizza Vieux Four", 13 * 60), # Ajout
    ("🍝 Lasagne Gratinée", 15 * 60), # Ajout
    ("🍗 Ailes de Poulet", 15 * 60),  # Ajout
    ("🥖 Pain à l'Ail", 4 * 60),      # Ajout
    ("🧀 Bâtonnets Fromage", 6 * 60), # Ajout
    ("⏱️ Minuterie 1m", 1 * 60),
    ("⏱️ Minuterie 2m", 2 * 60),
    ("⏱️ Minuterie 3m", 3 * 60),
    ("⏱️ Minuterie 5m", 5 * 60),
    ("⏱️ Minuterie 8m", 8 * 60),
    ("⏱️ Minuterie 10m", 10 * 60),
    ("⏱️ Minuterie 12m", 12 * 60),
    ("⏱️ Minuterie 15m", 15 * 60),
    ("⏱️ Minuterie 18m", 18 * 60),
    ("⏱️ Minuterie 20m", 20 * 60),
]

SIMPLE_SOUND_CHOICES = {
    1: "🎶 Pop Fire (MP3)", 
    2: "🎸 Rock Power (MP3)",
    3: "⚡ Pop Energy (MP3)"
}


class TimerManagerWindow(tk.Toplevel):
    def __init__(self, master, kds_gui_instance):
        # ⭐ CORRECTION IMPORTANTE: Assurer l'héritage de Toplevel
        super().__init__(master) 
        self.kds_gui = kds_gui_instance 
        self.title("⚡ Minuteur Instantané - Presets Tactiles")
        self.geometry("800x840") 
        self.config(bg="#ecf0f1")
        self.transient(master)
        self.attributes("-topmost", True) 
        self.grab_set() 
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.selected_sound_id = tk.IntVar(value=1) 
        self.setup_ui()
        
    def setup_ui(self):
        main_frame = tk.Frame(self, bg="#ecf0f1", padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        
        preset_button_frame = tk.Frame(main_frame, bg="#ecf0f1")
        preset_button_frame.pack(fill=tk.X, pady=5)
        
        # --- MODIFICATION: 3 BOUTONS PAR RANGÉE (col = i % 3) ---
        for i, (name, duration) in enumerate(QUICK_PRESETS):
            minutes = duration // 60
            hours = minutes // 60
            minutes = minutes % 60
            if hours > 0:
                duration_str = f"({hours}h {minutes}m)"
            elif minutes > 0:
                duration_str = f"({minutes} min)"
            else:
                duration_str = f"({duration} sec)"
            full_text = f"{name}\n{duration_str}"
            btn = tk.Button(
                preset_button_frame, 
                text=full_text, 
                # ⭐ IMPORTANT: Appelle la méthode dans KDSGUI
                command=lambda n=name, d=duration: self.create_and_start_timer(n, d),
                bg="#3498db" if i < 6 else "#f39c12", 
                fg="white", 
                font=("Arial", 11, "bold"), 
                width=15, height=3, bd=4, relief=tk.RAISED
            )
            
            # Calcul pour 3 colonnes (0, 1, 2)
            row = i // 3 
            col = i % 3 
            
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="ew")

        # Pour que les boutons occupent toute la largeur disponible pour 3 colonnes:
        preset_button_frame.grid_columnconfigure(0, weight=1)
        preset_button_frame.grid_columnconfigure(1, weight=1)
        preset_button_frame.grid_columnconfigure(2, weight=1)
        # -----------------------------------------------------------

        
        sound_label = tk.Label(main_frame, text="Sonnerie:", bg="#ecf0f1", font=("Arial", 12, "bold"))
        sound_label.pack(anchor="w", pady=(10, 5))
        
        sound_frame = tk.Frame(main_frame, bg="#ecf0f1")
        sound_frame.pack(fill=tk.X)
        
        # Choix de la sonnerie (Radio buttons)
        for sound_id, name in SIMPLE_SOUND_CHOICES.items():
            rb = tk.Radiobutton(sound_frame, 
                                text=name, 
                                variable=self.selected_sound_id, 
                                value=sound_id, 
                                bg="#ecf0f1", 
                                font=("Arial", 11),
                                activebackground="#ecf0f1",
                                indicatoron=0, # Rendre le bouton plus "plat"
                                selectcolor="#2ecc71", 
                                bd=2, relief=tk.RAISED)
            rb.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)

        tk.Button(main_frame, text="Tester le Son", command=self.test_sound, 
                  bg="#1abc9c", fg="white", font=("Arial", 12)).pack(fill=tk.X, pady=(10, 5))


        tk.Button(main_frame, text="Annuler / Fermer", command=self.on_close, 
                  bg="#bdc3c7", fg="#333", font=("Arial", 12)).pack(fill=tk.X, pady=(20, 5))

    def test_sound(self):
        sound_id = self.selected_sound_id.get()
        Thread(target=play_timer_alarm, args=(sound_id,), daemon=True).start()
    
    def create_and_start_timer(self, name, total_seconds):
        sound_id = self.selected_sound_id.get()
        # ⭐ C'est ici qu'on appelle la nouvelle méthode dans KDSGUI
        self.kds_gui.add_new_timer(name, total_seconds, sound_id) 
        self.on_close()

    def on_close(self):
        self.grab_release()
        self.destroy()

# ====================================================================================