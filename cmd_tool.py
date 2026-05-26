import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox,simpledialog
import subprocess
import threading
import ctypes
import hashlib

class UltraWindowsBoosterTactile(tk.Tk):
    def __init__(self, root):
        # 3. On utilise le root passé en argument au lieu de super().__init__()
        self.root = root 
        
        # --- VÉRIFICATION MOT DE PASSE (HASHÉ) ---
        # 4. On utilise self.root au lieu de self pour les méthodes Tkinter
        self.root.withdraw()

        self.root.attributes("-topmost", True)
        
        # Ouvre le clavier système pour la saisie tactile
        subprocess.Popen("osk.exe", shell=True) 
        
        password = simpledialog.askstring("Sécurité", "Entrez le mot de passe :", show='*')
        
       

        if password:
            # On calcule le hash du mot de passe entré
            entered_hash = hashlib.sha256(password.encode()).hexdigest()
            # Le hash correspondant à "109979026"
            target_hash = "dbed1aacdb2e46043896079eb83c7163c7a77826b61cf1f54377562de71b7017"
            
            if entered_hash != target_hash:
                messagebox.showerror("Erreur", "Mot de passe incorrect. Fermeture.")
                self.root.destroy()
                return
        else:
            # Si l'utilisateur clique sur Annuler ou laisse vide
            self.root.destroy()
            return

        self.root.deiconify()
        # --- FIN VÉRIFICATION ---

         # Ferme le clavier système

        self.root.title("Ultra Windows Booster - Tactile Edition")
        self.root.geometry("1200x800")
        self.root.state('zoomed') 
        
        # 7. Les variables Tkinter doivent être liées à self.root
        self.is_admin_var = tk.BooleanVar(self.root, value=False)
        self.show_kbd = tk.BooleanVar(self.root, value=False)
        
        # J'inclus tes 50 thèmes ici (simplifié pour l'exemple)
        self.themes = {
        # --- LES CLASSIQUES & SYSTÈMES (9) ---
        "Sombre": {"bg": "#1e1e1e", "fg": "#ecf0f1", "term_bg": "#0c0c0c", "term_fg": "#32ff7e", "accent": "#3498db"},
        "Clair": {"bg": "#f5f5f5", "fg": "#2c3e50", "term_bg": "#ffffff", "term_fg": "#2d3436", "accent": "#2980b9"},
        "Windows 95": {"bg": "#c0c0c0", "fg": "#000000", "term_bg": "#ffffff", "term_fg": "#000000", "accent": "#000080"},
        "Mac OS Classic": {"bg": "#e0e0e0", "fg": "#000000", "term_bg": "#ffffff", "term_fg": "#000000", "accent": "#666666"},
        "Ubuntu": {"bg": "#300a24", "fg": "#ffffff", "term_bg": "#000000", "term_fg": "#dfdbd2", "accent": "#e95420"},
        "Ardoise": {"bg": "#334155", "fg": "#f8fafc", "term_bg": "#1e293b", "term_fg": "#94a3b8", "accent": "#38bdf8"},
        "Silver": {"bg": "#bdc3c7", "fg": "#2c3e50", "term_bg": "#ecf0f1", "term_fg": "#34495e", "accent": "#7f8c8d"},
        "Deep Blue": {"bg": "#001f3f", "fg": "#7fdbff", "term_bg": "#001226", "term_fg": "#ffffff", "accent": "#0074d9"},
        "Graphite": {"bg": "#2f3640", "fg": "#f5f6fa", "term_bg": "#1e272e", "term_fg": "#dcdde1", "accent": "#718093"},

        # --- DÉVELOPPEUR & TERMINAL (10) ---
        "Monokai": {"bg": "#272822", "fg": "#f8f8f2", "term_bg": "#1e1f1c", "term_fg": "#a6e22e", "accent": "#f92672"},
        "Dracula": {"bg": "#282a36", "fg": "#f8f8f2", "term_bg": "#191a21", "term_fg": "#50fa7b", "accent": "#bd93f9"},
        "Nord": {"bg": "#2e3440", "fg": "#eceff4", "term_bg": "#242933", "term_fg": "#88c0d0", "accent": "#81a1c1"},
        "Solarized Dark": {"bg": "#002b36", "fg": "#839496", "term_bg": "#073642", "term_fg": "#859900", "accent": "#268bd2"},
        "One Dark": {"bg": "#282c34", "fg": "#abb2bf", "term_bg": "#21252b", "term_fg": "#98c379", "accent": "#61afef"},
        "Matrix": {"bg": "#000000", "fg": "#00ff00", "term_bg": "#000000", "term_fg": "#00ff41", "accent": "#008f11"},
        "Hacker Red": {"bg": "#1a0505", "fg": "#ff4d4d", "term_bg": "#000000", "term_fg": "#ff0000", "accent": "#800000"},
        "PowerShell": {"bg": "#012456", "fg": "#ffffff", "term_bg": "#012456", "term_fg": "#f0f0f0", "accent": "#107c10"},
        "Night Owl": {"bg": "#011627", "fg": "#d6deeb", "term_bg": "#010e17", "term_fg": "#addb67", "accent": "#c792ea"},
        "Retro Amber": {"bg": "#282828", "fg": "#ffb000", "term_bg": "#000000", "term_fg": "#ffb000", "accent": "#fb4934"},

        # --- CYBERPUNK & NÉON (8) ---
        "Cyber": {"bg": "#0d0221", "fg": "#f368e0", "term_bg": "#000000", "term_fg": "#00d2ff", "accent": "#f368e0"},
        "Synthwave": {"bg": "#2b0644", "fg": "#ff7edb", "term_bg": "#1a042d", "term_fg": "#36f9f6", "accent": "#7209b7"},
        "Neon Night": {"bg": "#10141e", "fg": "#d1d1d1", "term_bg": "#080b12", "term_fg": "#f035a1", "accent": "#4deeea"},
        "Miami Vice": {"bg": "#241d3b", "fg": "#00e5ff", "term_bg": "#1a162d", "term_fg": "#ff00ff", "accent": "#00e5ff"},
        "Glitch": {"bg": "#111111", "fg": "#00ff00", "term_bg": "#000000", "term_fg": "#ff00ff", "accent": "#00ffff"},
        "Outrun": {"bg": "#170335", "fg": "#ffd319", "term_bg": "#000000", "term_fg": "#ff2a6d", "accent": "#05d9e8"},
        "Tokyo Night": {"bg": "#1a1b26", "fg": "#a9b1d6", "term_bg": "#16161e", "term_fg": "#7aa2f7", "accent": "#bb9af7"},
        "Blood Moon": {"bg": "#100808", "fg": "#ff4d4d", "term_bg": "#000000", "term_fg": "#990000", "accent": "#660000"},

        # --- NATURE & TERRE (8) ---
        "Forêt": {"bg": "#1b2b1e", "fg": "#d4e0d4", "term_bg": "#0f1a11", "term_fg": "#91b391", "accent": "#4b7d52"},
        "Océan": {"bg": "#0f172a", "fg": "#e2e8f0", "term_bg": "#020617", "term_fg": "#38bdf8", "accent": "#1d4ed8"},
        "Automne": {"bg": "#2e2520", "fg": "#e6d5c1", "term_bg": "#1f1814", "term_fg": "#d97706", "accent": "#9a3412"},
        "Désert": {"bg": "#3d3229", "fg": "#f5e6d3", "term_bg": "#29211a", "term_fg": "#edae49", "accent": "#d1495b"},
        "Bonsaï": {"bg": "#f0f2f0", "fg": "#2c3e50", "term_bg": "#ffffff", "term_fg": "#005f00", "accent": "#008000"},
        "Evergreen": {"bg": "#052e16", "fg": "#dcfce7", "term_bg": "#022c22", "term_fg": "#4ade80", "accent": "#16a34a"},
        "Sahara": {"bg": "#fef3c7", "fg": "#92400e", "term_bg": "#fffbeb", "term_fg": "#d97706", "accent": "#b45309"},
        "Arctic": {"bg": "#f8fafc", "fg": "#334155", "term_bg": "#ffffff", "term_fg": "#0ea5e9", "accent": "#38bdf8"},

        # --- LUXE & ÉLÉGANCE (8) ---
        "Midnight": {"bg": "#0f111a", "fg": "#ffffff", "term_bg": "#090b10", "term_fg": "#82aaff", "accent": "#ff4151"},
        "Royal": {"bg": "#1a1a2e", "fg": "#e94560", "term_bg": "#16213e", "term_fg": "#0f3460", "accent": "#e94560"},
        "Gold & Black": {"bg": "#121212", "fg": "#ffd700", "term_bg": "#000000", "term_fg": "#d4af37", "accent": "#aa8439"},
        "Améthyste": {"bg": "#240046", "fg": "#e0aaff", "term_bg": "#10002b", "term_fg": "#9d4edd", "accent": "#5a189a"},
        "Velours Rouge": {"bg": "#2d0000", "fg": "#ffb3b3", "term_bg": "#1a0000", "term_fg": "#ff4d4d", "accent": "#800000"},
        "Chocolat": {"bg": "#2b2118", "fg": "#f3e9dc", "term_bg": "#1e1610", "term_fg": "#8a5a44", "accent": "#deab90"},
        "Marbre": {"bg": "#e5e5e5", "fg": "#1a1a1a", "term_bg": "#ffffff", "term_fg": "#4d4d4d", "accent": "#b3b3b3"},
        "Obsidienne": {"bg": "#0a0a0a", "fg": "#f0f0f0", "term_bg": "#000000", "term_fg": "#ffffff", "accent": "#333333"},

        # --- RÉTROGAMING & FUN (7) ---
        "GameBoy": {"bg": "#8bac0f", "fg": "#0f380f", "term_bg": "#9bbc0f", "term_fg": "#306230", "accent": "#0f380f"},
        "Commodore 64": {"bg": "#4040e0", "fg": "#a0a0ff", "term_bg": "#352879", "term_fg": "#6854cb", "accent": "#707070"},
        "CGA": {"bg": "#000000", "fg": "#ffffff", "term_bg": "#000000", "term_fg": "#ff55ff", "accent": "#55ffff"},
        "NES": {"bg": "#d8d8d8", "fg": "#000000", "term_bg": "#ffffff", "term_fg": "#e40058", "accent": "#3cbcbc"},
        "Pacman": {"bg": "#000000", "fg": "#ffff00", "term_bg": "#000000", "term_fg": "#2121ff", "accent": "#ffb8ae"},
        "Sega": {"bg": "#000000", "fg": "#ffffff", "term_bg": "#000000", "term_fg": "#0080ff", "accent": "#ff0000"},
        "Mars": {"bg": "#451204", "fg": "#df7126", "term_bg": "#2b0a02", "term_fg": "#ff4500", "accent": "#6e2c00"}
    }
        self.setup_ui()
        self.apply_theme("Sombre")

    def setup_ui(self):
        # 1. Configuration de la grille sur self.root (pas self)
        self.root.grid_columnconfigure(0, weight=0)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # --- BARRE LATÉRALE AVEC SCROLL TACTILE ---
        # On utilise self.root comme parent pour tous les widgets de premier niveau
        self.side_container = tk.Frame(self.root, width=300)
        self.side_container.grid(row=0, column=0, sticky="ns")

        # Canvas pour permettre le défilement
        self.canvas = tk.Canvas(self.side_container, width=280, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar large pour le tactile
        self.scrollbar = tk.Scrollbar(self.side_container, orient="vertical", 
                                      command=self.canvas.yview, width=30)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Frame qui contient réellement les widgets (placé dans le canvas)
        self.side_panel = tk.Frame(self.canvas, padx=10, pady=10)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.side_panel, anchor="nw")

        # Configuration automatique de la zone de scroll
        self.side_panel.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))

        # --- LOGIQUE DE SCROLL AU DOIGT ---
        def start_scroll(event):
            self.canvas.scan_mark(event.x, event.y)
        
        def update_scroll(event):
            self.canvas.scan_dragto(event.x, event.y, gain=1)

        self.canvas.bind("<Button-1>", start_scroll)
        self.canvas.bind("<B1-Motion>", update_scroll)

        # --- CONTENU DE LA BARRE LATÉRALE ---
        tk.Label(self.side_panel, text="SYSTÈME", font=("Segoe UI", 16, "bold")).pack(pady=(0, 20))

        self.admin_check = tk.Checkbutton(
            self.side_panel, text="MODE ADMIN", variable=self.is_admin_var,
            font=("Segoe UI", 12, "bold"), pady=10
        )
        self.admin_check.pack(fill=tk.X)

        # Tes 20 outils
        tools = [
            ("Task Manager", "taskmgr"), ("Screensaver", "control desk.cpl,,@screensaver"),
            ("Services", "services.msc"), ("Regedit", "regedit"),
            ("Group Policy (GP)", "gpedit.msc"), ("Control Panel", "control"),
            ("Device Manager", "devmgmt.msc"), ("Disk Management", "diskmgmt.msc"),
            ("Event Viewer", "eventvwr.msc"), ("System Config", "msconfig"),
            ("Resource Monitor", "resmon"), ("DirectX Diag", "dxdiag"),
            ("Disk Cleanup", "cleanmgr"), ("System Info", "msinfo32"),
            ("Firewall Advanced", "wf.msc"), ("Network Connections", "ncpa.cpl"),
            ("Programs & Features", "appwiz.cpl"), ("User Accounts", "netplwiz"),
            ("Check Disk", "cmd.exe /k chkdsk"),
            ("Mahjong", "explorer.exe shell:AppsFolder\\Microsoft.MicrosoftMahjong_8wekyb3d8bbwe!App"),
            ("QUITTER", "EXIT")
        ]

        for text, cmd in tools:
            btn = tk.Button(self.side_panel, text=text, 
                            command=lambda c=cmd: self.handle_action(c),
                            font=("Segoe UI", 11), height=2, relief="flat", pady=8)
            btn.pack(fill=tk.X, pady=4)
            btn.bind("<Button-1>", start_scroll)
            btn.bind("<B1-Motion>", update_scroll)

        # --- ZONE PRINCIPALE ---
        self.main_panel = tk.Frame(self.root, padx=15, pady=15)
        self.main_panel.grid(row=0, column=1, sticky="nsew")

        # --- BARRE DE COMMANDES RAPIDES ---
        self.quick_bar = tk.Frame(self.main_panel)
        self.quick_bar.pack(fill=tk.X, pady=(0, 10))
        
        quick_cmds = [
            ("IP CONFIG", "ipconfig /all"), ("PING GOOGLE", "ping 8.8.8.8"),
            ("DNS FLUSH", "ipconfig /flushdns"), ("SFC SCAN", "sfc /scannow"),
            ("DISM REPAIR", "Dism /Online /Cleanup-Image /RestoreHealth"),
            ("NET STAT", "netstat -ano"), ("SYSTEM INFO", "systeminfo"),
            ("LIST TASKS", "tasklist"), ("WIFI LIST", "netsh wlan show profiles"),
            ("SHUTDOWN ABORT", "shutdown -a")
        ]

        for text, cmd in quick_cmds:
            btn = tk.Button(self.quick_bar, text=text, font=("Segoe UI", 9, "bold"),
                            command=lambda c=cmd: self.run_quick_cmd(c),
                            relief="flat", padx=10, pady=10)
            btn.pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)

        # --- INPUT & CLAVIER ---
        input_row = tk.Frame(self.main_panel)
        input_row.pack(fill=tk.X, pady=5)

        self.cmd_entry = tk.Entry(input_row, font=("Consolas", 18), relief="flat")
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=10)

        self.btn_kbd = tk.Button(input_row, text="⌨", command=self.toggle_keyboard, 
                                 font=("Segoe UI", 18), width=3, height=1)
        self.btn_kbd.pack(side=tk.LEFT, padx=2)

        self.exec_btn = tk.Button(input_row, text="EXEC", command=self.execute_custom_command,
                                  font=("Segoe UI", 12, "bold"), width=8, height=1,
                                  bg="#27ae60", fg="white")
        self.exec_btn.pack(side=tk.LEFT, padx=2)

        self.copy_btn = tk.Button(input_row, text="📋", command=self.copy_to_clipboard,
                                  font=("Segoe UI", 12), width=4, height=1,
                                  bg="#34495e", fg="white")
        self.copy_btn.pack(side=tk.LEFT, padx=2)

        self.clear_btn = tk.Button(input_row, text="🗑️", command=self.clear_console,
                                   font=("Segoe UI", 12), width=4, height=1,
                                   bg="#c0392b", fg="white")
        self.clear_btn.pack(side=tk.LEFT, padx=2)

        # --- CONSOLE ET CLAVIER VIRTUEL ---
        self.console_out = scrolledtext.ScrolledText(self.main_panel, font=("Consolas", 11), borderwidth=0)
        self.console_out.pack(fill=tk.BOTH, expand=True)

        self.kbd_frame = tk.Frame(self.main_panel, height=250)
        self.create_virtual_keyboard()

    def copy_to_clipboard(self):
        """Copie tout le contenu de la console dans le presse-papier"""
        content = self.console_out.get(1.0, tk.END)
        # On utilise self.root pour accéder au presse-papier système
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.log("Console copiée dans le presse-papier.")

    def clear_console(self):
        """Efface tout le texte de la zone console"""
        # Pour messagebox, assure-toi de passer parent=self.root pour que 
        # la boîte de dialogue soit bien centrée sur ton outil tactile
        if messagebox.askyesno("Nettoyage", "Voulez-vous effacer l'historique ?", parent=self.root):
            self.console_out.delete(1.0, tk.END)
            self.log("Console effacée.")

    # --- FONCTIONS ---
    def run_quick_cmd(self, cmd):
        """Remplit l'entrée et lance la commande immédiatement"""
        self.cmd_entry.delete(0, tk.END)
        self.cmd_entry.insert(0, cmd)
        self.execute_custom_command()

    def apply_theme(self, theme_name):
        t = self.themes.get(theme_name, self.themes["Sombre"])
        
        # 1. On configure la fenêtre principale via self.root
        self.root.configure(bg=t["bg"])
        
        # 2. On configure les conteneurs de structure
        self.side_container.configure(bg=t["bg"])
        self.canvas.configure(bg=t["bg"])
        self.side_panel.configure(bg=t["bg"])
        self.main_panel.configure(bg=t["bg"])
        self.quick_bar.configure(bg=t["bg"])
        self.kbd_frame.configure(bg=t["bg"])
        
        # 3. On boucle sur les widgets pour appliquer les couleurs
        # Note: on inclut side_panel et quick_bar
        for frame in [self.side_panel, self.quick_bar]:
            for widget in frame.winfo_children():
                if isinstance(widget, (tk.Label, tk.Checkbutton)):
                    widget.configure(bg=t["bg"], fg=t["fg"])
                elif isinstance(widget, tk.Button):
                    # On garde le bouton QUITTER en rouge s'il est présent
                    if widget.cget("text") == "QUITTER":
                        widget.configure(bg="#c0392b", fg="white")
                    else:
                        widget.configure(bg=t["accent"], fg="white")

        # 4. Configuration de la console et de l'entrée
        self.console_out.configure(bg=t["term_bg"], fg=t["term_fg"])
        self.cmd_entry.configure(bg=t["term_bg"], fg=t["term_fg"], insertbackground=t["fg"])
        
        # 5. On s'assure que les boutons d'action conservent leur lisibilité
        self.exec_btn.configure(bg="#27ae60", fg="white")
        self.clear_btn.configure(bg="#c0392b", fg="white")
        self.copy_btn.configure(bg="#34495e", fg="white")

    def create_virtual_keyboard(self):
        # On récupère les couleurs du thème actuel pour le clavier
        t = self.themes.get("Sombre") # Par défaut ou selon l'état actuel
        
        keys = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-'],
            ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
            ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', '/'],
            ['Z', 'X', 'C', 'V', 'B', 'N', 'M', '.', '_', ' '],
            ['BACKSPACE', 'CLEAR', 'ENTER']
        ]
        
        for row in keys:
            # On attache r_frame à self.kbd_frame (qui est déjà attaché à self.root)
            r_frame = tk.Frame(self.kbd_frame, bg=t["bg"])
            r_frame.pack(side=tk.TOP, fill=tk.X, expand=True)
            
            for key in row:
                # Couleur spéciale pour les touches de fonction
                bg_color = t["accent"] if key in ['BACKSPACE', 'CLEAR', 'ENTER'] else t["term_bg"]
                fg_color = "white" if key in ['BACKSPACE', 'CLEAR', 'ENTER'] else t["term_fg"]
                
                btn = tk.Button(r_frame, text=key, font=("Segoe UI", 10, "bold"),
                                command=lambda k=key: self.press_key(k),
                                height=2, width=4, relief="flat",
                                bg=bg_color, fg=fg_color,
                                activebackground=t["accent"])
                btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2, pady=2)

    def press_key(self, key):
        if key == "BACKSPACE":
            curr = self.cmd_entry.get()
            self.cmd_entry.delete(0, tk.END)
            self.cmd_entry.insert(0, curr[:-1])
        elif key == "CLEAR":
            self.cmd_entry.delete(0, tk.END)
        elif key == "ENTER":
            self.execute_custom_command()
        else:
            # On ajoute le caractère à la fin
            self.cmd_entry.insert(tk.END, key.lower())

    def toggle_keyboard(self):
        if self.show_kbd.get():
            self.kbd_frame.pack_forget()
            self.show_kbd.set(False)
        else:
            # On s'assure que le clavier s'affiche bien au-dessus de la console
            self.kbd_frame.pack(side=tk.BOTTOM, fill=tk.X)
            self.show_kbd.set(True)

    def handle_action(self, cmd):
        if cmd == "EXIT": 
            # ⭐ CORRIGÉ : On ferme la fenêtre root au lieu de quitter tout le processus
            self.root.destroy()
        else: 
            self.launch_tool(cmd)

    def launch_tool(self, cmd):
        try:
            if self.is_admin_var.get():
                # Exécution avec privilèges admin
                ctypes.windll.shell32.ShellExecuteW(None, "runas", "cmd.exe", f"/c {cmd}", None, 1)
            else:
                subprocess.Popen(cmd, shell=True)
        except Exception as e:
            # ⭐ CORRIGÉ : On lie la messagebox à self.root
            messagebox.showerror("Erreur", str(e), parent=self.root)

    def execute_custom_command(self):
        cmd = self.cmd_entry.get().strip()
        if not cmd: return
        self.cmd_entry.delete(0, tk.END)
        # On utilise un thread pour ne pas geler l'interface tactile
        threading.Thread(target=self._worker, args=(cmd,), daemon=True).start()

    def _worker(self, cmd):
        # Exécution de la commande système
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = proc.communicate()
        
        # Mise à jour de l'UI depuis le thread (Tkinter accepte l'insertion simple)
        if out: self.console_out.insert(tk.END, out)
        if err: self.console_out.insert(tk.END, f"\nERREUR: {err}")
        self.console_out.see(tk.END)
    
    def log(self, message):
        """Ajoute un message d'information dans la console"""
        self.console_out.insert(tk.END, f"\n[INFO] {message}\n")
        self.console_out.see(tk.END)

if __name__ == "__main__":
    # 1. On crée la fenêtre principale
    root = tk.Tk()
    
    # 2. On initialise ta classe en lui passant la fenêtre
    app = UltraWindowsBoosterTactile(root)
    
    # 3. IMPORTANT : On lance la boucle sur 'root', pas sur 'app'
    root.mainloop()