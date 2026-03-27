import tkinter as tk
from tkinter import ttk
import json
import os 
import logging 

logger = logging.getLogger(__name__)

# --- FONCTION DE CHARGEMENT DES RACCOURCIS ---
def _load_shortcuts_data(file_path):
    """Charge les mots de raccourci depuis un fichier JSON."""
    default_shortcuts = [
        "REMPLACER", "PAR", "PAS DE" ,"CHEF", "CÉSAR", "FRITES", "SALADE", 
        "PAT. ANCIENNES", "PAS DE LÉGUMES", "EXTRA SAUCE", "RIZ", 
        "SANS OIGNONS", "BIEN CUIT"
    ]
    
    if not os.path.exists(file_path): 
        return default_shortcuts

    try:
        with open(file_path, 'r', encoding='utf-8') as f: 
            data = json.load(f)
            shortcuts = data.get('shortcuts', [])
            if shortcuts and isinstance(shortcuts, list):
                return [word.upper() for word in shortcuts]
            return default_shortcuts
    except Exception:
        return default_shortcuts

# --- CLASSE CLAVIER VIRTUEL MODIFIÉE ---
class VirtualKeyboard(tk.Toplevel):
    SHORTCUT_FILE = 'shortcut_word.json' 
    SHORTCUT_WORDS = _load_shortcuts_data(SHORTCUT_FILE) 

    def __init__(self, master, initial_content, ok_callback, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.transient(master) 
        self.title("Clavier Virtuel")
        self.resizable(False, False)
        
        self.ok_callback = ok_callback 
        self.initial_content = initial_content

        # --- 1. CONFIGURATION DES 5 NIVEAUX DE ZOOM ---
        self.size_levels = [
            {'name': '1/5', 'w': 3, 'h': 1, 'f': 11, 'f_s': 10},
            {'name': '2/5', 'w': 3, 'h': 1, 'f': 13, 'f_s': 12},
            {'name': '3/5', 'w': 4, 'h': 1, 'f': 14, 'f_s': 13},
            {'name': '4/5', 'w': 4, 'h': 2, 'f': 16, 'f_s': 14},
            {'name': '5/5', 'w': 5, 'h': 2, 'f': 18, 'f_s': 14}
        ]
        self.current_size_idx = 4 # Niveau 2 par défaut

        # --- 2. CONTENEUR PRINCIPAL ---
        self.main_container = tk.Frame(self, bg="#ecf0f1")
        self.main_container.pack(fill='both', expand=True)

        # --- 3. RENDU INITIAL ---
        self.target_entry = None
        self._render_ui()

        # Positionnement
        self.geometry(f"+{master.winfo_rootx() + 50}+{master.winfo_rooty() + 50}")
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<FocusOut>", self.on_focus_out) 
        self.grab_set() 

    def _render_ui(self):
        """Dessine ou redessine l'interface selon la taille choisie."""
        # Sauvegarde du texte si l'entry existait déjà
        current_text = self.target_entry.get() if self.target_entry else self.initial_content

        # Nettoyage
        for widget in self.main_container.winfo_children():
            widget.destroy()

        sz = self.size_levels[self.current_size_idx]

        # --- SECTION CHAMP DE SAISIE ---
        input_frame = tk.Frame(self.main_container, padx=5, pady=5, bg='white')
        input_frame.pack(fill=tk.X)
        self.target_entry = tk.Entry(input_frame, bd=2, relief=tk.SUNKEN, font=('Segoe UI', 14))
        self.target_entry.insert(0, current_text)
        self.target_entry.pack(fill=tk.X, expand=True, ipady=8, padx=5, pady=5)

        # --- SECTION RACCOURCIS ---
        shortcut_container = tk.Frame(self.main_container, bg="#ecf0f1", padx=10, pady=5)
        shortcut_container.pack(fill='x')
        
        words_per_row = 6
        shortcuts = self.SHORTCUT_WORDS[:48]
        for i in range(0, len(shortcuts), words_per_row):
            row_frame = tk.Frame(shortcut_container, bg="#ecf0f1")
            row_frame.pack(fill='x', pady=1)
            for word in shortcuts[i:i + words_per_row]:
                btn = tk.Button(row_frame, text=word, bg='#f39c12', fg='white', 
                                font=('Arial', sz['f_s'], 'bold'), bd=1, relief=tk.RAISED,
                                command=lambda w=word: self._insert_text(w + ' '))
                btn.pack(side=tk.LEFT, padx=2, pady=1, expand=True, fill=tk.X)

        # --- SECTION CLAVIER PRINCIPAL ---
        kbd_frame = tk.Frame(self.main_container, bg="#ecf0f1", bd=1, relief=tk.RAISED)
        kbd_frame.pack(fill='x', padx=10, pady=5)
        
        keys = [
            ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
            ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
            ['Z', 'X', 'C', 'V', 'B', 'N', 'M'],
            ['-', '/', '*', '+', '(', ')', '.', "'"],
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
        ]
        
        for row in keys:
            row_f = tk.Frame(kbd_frame, bg="#ecf0f1")
            row_f.pack(pady=1)
            for key in row:
                btn = tk.Button(row_f, text=key, width=sz['w'], height=sz['h'],
                                bg='#bdc3c7', fg='#34495e', font=('Arial', sz['f'], 'bold'),
                                bd=1, relief=tk.RAISED, command=lambda k=key: self._key_press(k))
                btn.pack(side=tk.LEFT, padx=1, pady=1)

        # --- BARRE DE CONTRÔLE (BAS) ---
        # --- BARRE DE CONTRÔLE (BAS) ---
        tool_frame = tk.Frame(kbd_frame, bg="#ecf0f1")
        tool_frame.pack(pady=10)
        
        # Calcul de styles dynamiques pour les boutons de contrôle
        # On multiplie la largeur de base (sz['w']) pour les boutons de texte long
        ctrl_w = sz['w'] * 3 
        ctrl_h = sz['h']
        ctrl_f = sz['f_s'] # On utilise la taille de police des raccourcis

        # Bouton ZOOM
        tk.Button(tool_frame, text=f"ZOOM {sz['name']}", width=ctrl_w, height=ctrl_h, 
                  bg='#9b59b6', fg='white', font=('Arial', ctrl_f, 'bold'), 
                  command=self._cycle_size).pack(side=tk.LEFT, padx=5)

        # Bouton ESPACE
        tk.Button(tool_frame, text="ESPACE", width=ctrl_w, height=ctrl_h, 
                  bg='#bdc3c7', font=('Arial', ctrl_f, 'bold'),
                  command=lambda: self._key_press(' ')).pack(side=tk.LEFT, padx=5)

        # Bouton EFFACER
        tk.Button(tool_frame, text="EFFACER", width=ctrl_w, height=ctrl_h, 
                  bg='#e74c3c', fg='white', font=('Arial', ctrl_f, 'bold'),
                  command=lambda: self._key_press('DELETE')).pack(side=tk.LEFT, padx=5)
        
        # Bouton VIDER TOUT
        tk.Button(tool_frame, text="VIDER TOUT", width=ctrl_w, height=ctrl_h, 
                  bg='#c0392b', fg='white', font=('Arial', ctrl_f, 'bold'),
                  command=lambda: self._key_press('CLEAR_ALL')).pack(side=tk.LEFT, padx=5)

        # Bouton OK (Encore un peu plus large que les autres)
        tk.Button(tool_frame, text="OK (Enregistrer)", width=ctrl_w + 5, height=ctrl_h, 
                  bg='#2ecc71', fg='white', font=('Arial', ctrl_f, 'bold'),
                  command=lambda: self._key_press('OK')).pack(side=tk.LEFT, padx=5)
        self.target_entry.focus_set()

    def _cycle_size(self):
        """Bascule entre les 5 tailles."""
        self.current_size_idx = (self.current_size_idx + 1) % len(self.size_levels)
        self._render_ui()
        self.update_idletasks()

    def _insert_text(self, text):
        self.target_entry.insert(tk.INSERT, text)
        self.target_entry.focus_set()

    def _key_press(self, key):
        target = self.target_entry
        target.focus_set()

        if key == 'OK':
            if self.ok_callback: self.ok_callback(target) 
            self.destroy()
            return

        if key == 'CLEAR_ALL':
            target.delete(0, tk.END)
            return

        if key == 'DELETE':
            pos = target.index(tk.INSERT)
            if pos > 0: target.delete(pos - 1, pos)
        else:
            char = ' ' if key == ' ' else key.upper()
            target.insert(tk.INSERT, char)

    def on_focus_out(self, event):
        self.after(200, self._check_real_focus)

    def _check_real_focus(self):
        try:
            if self.focus_get() is None:
                self.destroy()
        except:
            pass