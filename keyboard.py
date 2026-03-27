import tkinter as tk
from tkinter import ttk

class VirtualKeyboard(tk.Toplevel):
    def __init__(self, master, target_entry_widget, ok_callback, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.transient(master)
        self.title("Clavier Virtuel")
        self.resizable(False, False)
        
        self.target_entry = target_entry_widget
        self.ok_callback = ok_callback 
        
        # --- 5 Niveaux de taille (de Small à Medium) ---
        # w: largeur, h: hauteur, f: font size
        self.sizes = [
            {'name': 'Taille 1', 'w': 3, 'h': 1, 'f': 12}, # Small
            {'name': 'Taille 2', 'w': 3, 'h': 1, 'f': 14},
            {'name': 'Taille 3', 'w': 4, 'h': 1, 'f': 15},
            {'name': 'Taille 4', 'w': 4, 'h': 2, 'f': 16},
            {'name': 'Taille 5', 'w': 5, 'h': 2, 'f': 18}  # Medium max
        ]
        self.current_size_idx = 4
        
        # Positionnement initial
        self.geometry(f"+{master.winfo_rootx() + 50}+{master.winfo_rooty() + 100}")

        self._create_virtual_keyboard()
        
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<FocusOut>", self.on_focus_out) 
        self.grab_set() 
        self.target_entry.focus_set() 

    def _create_virtual_keyboard(self):
        """Reconstruit le clavier avec la taille sélectionnée et les outils adaptés."""
        # Nettoyage de l'interface précédente
        for widget in self.winfo_children():
            widget.destroy()

        container = tk.Frame(self, bg="#ecf0f1", bd=2, relief=tk.RAISED)
        container.pack(fill='both', expand=True, padx=5, pady=5)
        
        keys = [
            ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
            ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
            ['Z', 'X', 'C', 'V', 'B', 'N', 'M'],
            ['-', '/', '*', '+', '(', ')', '.', "'", ":"],
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
        ]
        
        sz = self.sizes[self.current_size_idx]
        
        # --- Touches de caractères ---
        for row in keys:
            row_frame = tk.Frame(container, bg="#ecf0f1")
            row_frame.pack(pady=1)
            for key in row:
                btn = tk.Button(row_frame, text=key, width=sz['w'], height=sz['h'],
                                bg='#bdc3c7', fg='#2c3e50', font=('Arial', sz['f'], 'bold'),
                                activebackground='#95a5a6',
                                command=lambda k=key: self._key_press(k))
                btn.pack(side=tk.LEFT, padx=1, pady=1)

        # --- Barre d'outils adaptée ---
        tool_row = tk.Frame(container, bg="#ecf0f1")
        tool_row.pack(pady=10)
        
        # Calcul des dimensions pour les boutons d'outils
        # On multiplie la largeur de base par 2.5 pour les textes longs (ESPACE, EFFACER)
        btn_w = int(sz['w'] * 2.5) 
        btn_h = sz['h']
        # On utilise une police légèrement plus petite que les touches pour que les mots rentrent
        btn_f = max(9, sz['f'] - 2) 

        # Bouton Cycle de Taille (couleur violette)
        size_label = f"LOUPE ({self.current_size_idx + 1}/5)"
        tk.Button(tool_row, text=size_label, 
                  width=btn_w, height=btn_h,
                  bg='#9b59b6', fg='white', 
                  font=('Arial', btn_f, 'bold'),
                  command=self._cycle_size).pack(side=tk.LEFT, padx=2)

        # Bouton ESPACE
        tk.Button(tool_row, text="ESPACE", 
                  width=btn_w, height=btn_h, 
                  bg='#bdc3c7', 
                  font=('Arial', btn_f, 'bold'),
                  command=lambda: self._key_press(' ')).pack(side=tk.LEFT, padx=2)

        # Bouton EFFACER
        tk.Button(tool_row, text="EFFACER", 
                  width=btn_w, height=btn_h, 
                  bg='#e74c3c', fg='white', 
                  font=('Arial', btn_f, 'bold'),
                  command=lambda: self._key_press('DELETE')).pack(side=tk.LEFT, padx=2)
        
        # Bouton OK
        tk.Button(tool_row, text="OK", 
                  width=btn_w, height=btn_h, 
                  bg='#2ecc71', fg='white', 
                  font=('Arial', btn_f, 'bold'),
                  command=lambda: self._key_press('OK')).pack(side=tk.LEFT, padx=2)

    def _cycle_size(self):
        """Passe au niveau de zoom suivant (1 à 5)."""
        self.current_size_idx = (self.current_size_idx + 1) % len(self.sizes)
        self._create_virtual_keyboard()
        # Forcer la fenêtre à se réajuster à son contenu
        self.update_idletasks()

    def _key_press(self, key):
        target = self.target_entry
        if key == 'OK':
            if self.ok_callback: self.ok_callback()
            self.destroy()
            return

        if isinstance(target, (tk.Entry, ttk.Entry)):
            target.focus_set()
            if key == 'DELETE':
                current_pos = target.index(tk.INSERT)
                if current_pos > 0:
                    target.delete(current_pos - 1, current_pos)
            else:
                char = ' ' if key == ' ' else key.upper()
                target.insert(tk.INSERT, char)

    def on_focus_out(self, event):
        # On vérifie si le nouveau focus appartient au clavier
        self.after(100, self._check_focus)

    def _check_focus(self):
        focused_widget = self.focus_get()
        if focused_widget is None:
            self.destroy()