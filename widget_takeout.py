# widget_takeout.py
import tkinter as tk
import time
from threading import Event

# Constantes de couleur (Assorties à ton KDS)
COLOR_BACKGROUND = "#2c3e50" # Bleu nuit
COLOR_TEXT_HEADER = "#ecf0f1" # Blanc cassé
COLOR_BILL_NUM = "#f1c40f"    # Jaune pour le numéro (très visible)
COLOR_CLOSE = "#e74c3c"       # Rouge pour le bouton X

class TakeoutWidget(tk.Toplevel):
    """
    Widget flottant avec moteur physique pour signaler les commandes à ramasser.
    Affiche "ENLEVER : #ID"
    """
    def __init__(self, master, bill_id, remove_callback):
        super().__init__(master)
        self.bill_id = bill_id
        self.remove_callback = remove_callback

        # --- CONFIGURATION FENÊTRE ---
        self.overrideredirect(True) 
        self.attributes("-topmost", True) 
        self.geometry("300x120") # Un peu moins haut que le minuteur
        self.config(bg=COLOR_BACKGROUND, borderwidth=3, relief="raised") 

        # --- MOTEUR PHYSIQUE (Même que Timer) ---
        self.vx = 0
        self.vy = 0
        self.friction = 0.98
        self.bounce = -0.75
        self.is_tossed = False
        self._offset_x = 0
        self._offset_y = 0
        self.move_history = []

        # --- INTERFACE ---
        self.canvas = tk.Canvas(self, bg=COLOR_BACKGROUND, highlightthickness=0, bd=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)

        # Texte principal
        self.header_label = tk.Label(self, text="ENLEVER :", bg=COLOR_BACKGROUND, 
                                    fg=COLOR_TEXT_HEADER, font=("Arial", 20, "bold"))
        self.header_label.pack(pady=(15, 0))
        
        # Numéro de facture (Gros et Jaune)
        self.id_label = tk.Label(self, text=f"#{self.bill_id}", bg=COLOR_BACKGROUND, 
                                fg=COLOR_BILL_NUM, font=("Arial", 28, "bold"))
        self.id_label.pack(pady=5)
        
        # Bouton X pour fermer (en haut à droite)
        self.close_btn = tk.Button(self, text="X", command=self._on_close, 
                                  bg=COLOR_CLOSE, fg="white", font=("Arial", 12, "bold"),
                                  relief="flat", bd=0, width=3)
        self.close_btn.place(x=265, y=5)

        # Bindings tactiles pour le déplacement physique
        for w in [self, self.header_label, self.id_label, self.canvas]:
            w.bind('<Button-1>', self._start_drag)
            w.bind('<B1-Motion>', self._drag)
            w.bind('<ButtonRelease-1>', self._stop_drag)
            w.bind('<Double-Button-1>', lambda e: self._on_close())

    # --- LOGIQUE PHYSIQUE ---
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

        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        ww, wh = self.winfo_width(), self.winfo_height()
        
        nx = self.winfo_x() + self.vx
        ny = self.winfo_y() + self.vy

        if nx <= 0 or nx + ww >= sw:
            self.vx *= self.bounce
            nx = max(0, min(nx, sw - ww))

        if ny <= 0 or ny + wh >= sh:
            self.vy *= self.bounce
            ny = max(0, min(ny, sh - wh))

        self.vx *= self.friction
        self.vy *= self.friction

        try:
            self.geometry(f"+{int(nx)}+{int(ny)}")
            if abs(self.vx) > 0.3 or abs(self.vy) > 0.3:
                self.after(10, self._apply_physics)
            else:
                self.is_tossed = False
        except: pass

    def _on_close(self):
        # Appelle le callback pour nettoyer la liste dans kds_gui si nécessaire
        if self.remove_callback:
            self.remove_callback(self.bill_id)
        self.destroy()