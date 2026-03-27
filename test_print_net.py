import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import os
import psutil
import platform
import subprocess
from datetime import datetime

# --- CONFIGURATION VISUELLE ---
BG_DARK = "#121212"
BG_PANEL = "#1E1E1E"
FG_TEXT = "#E0E0E0"
ACCENT_GREEN = "#00C853"
ACCENT_BLUE = "#2979FF"
ACCENT_RED = "#FF1744"
ACCENT_ORANGE = "#FF9100"

STATUS_CODES = {
    "READY": b'\x12',
    "PAPER_OUT": b'\x1E',
    "COVER_OPEN": b'\x16',
    "ERROR": b'\x14'
}

# --- BIBLIOTHÈQUE DE TICKETS ---
TICKETS_LIBRARY = {
    "Ticket Test Standard": b'\x1b@\x1b!2-- TEST TICKET --\n\n\x1dV\x00',
    "Livraison #302 (Addition 998628)": (
        b'\x1b@' b'\x1b!2\x1br\x00      1083\n'
        b'\x1b!\x12\x1b!2\x1br\x00 MOONEY OUEST\n'
        b'\x1b!\x12\x1b!2\x1br\x00  4183338092\n'
        b'\x1br\x00        2026-01-27 10:44:38\n'
        b'\x1b!2\x1br\x00\x1b!\x12     ADDITION #998628-1\n'
        b'\x1b!2\x1br\x00   TRANS #017J\n'
        b'\x1br\x00   1 MEDIUM GARNI         $25.99  FP\n'
        b'\x1br\x00   1 FAM. POUTINE         $17.99  FP\n'
        b'\x1br\x00   Frais de livrais       $2.50  FP\n'
        b'\x1br\x00\n      TOT:     $53.44\n'
        b'\x1b!2\x1br\x00 LIVRAISON #301\n' b'\x1bd\t\x1bi'
    ),
    "Cuisine #302 (Lasagne)": (
        b'\x1b@' b'\x1b!2\x1br\x00 PRINCIPALE\x1b!\x12\n'
        b'\x1b!2\x1br\x00    LIVRAISON\n'
        b'\x1br\x00 Heure: 10:52:11\n'
        b'\x1br\x00  27-01-2026\n'
        b'\x1b!2\x1br\x00   TABLE # 302\n'
        b'\x1b!\x12\x1br\x00 \x1b!2  1\x1b!\x12 DEMI LASAGNE\n'
        b'\x1br\x01   \x1b!2  1\x1b!\x12 VIANDE\x1br\x01\n'
        b'\n###############################\n' b'\x1bd\t\x1bi'
    ),
    "Table 32 (Soupe & Lasagne) - ASCII": (
        # --- SERVICE # 1 (Soupe Midi) ---
        b'\x1b@' b'\x1b!2\x1br\x00 PRINCIPALE\x1b!\x12\n'
        b'\x1b!2\x1br\x00    COMMANDE\n'
        b'\x1br\x00 Heure: 12:15:00\n'
        b'\x1br\x00  23-02-2026\n'
        b'\x1b!2\x1br\x00   TABLE # 32\n'
        b'\x1b!\x12\x1br\x00        ** SERVICE # 1 **\n'
        b'\x1b!2\x1br\x00  1\x1b!\x12 SOUPE MIDI\n'
        b'\x1br\x00    \x1b!\x12 -> *LEGUMES\n'
        b'\x1br\x00    \x1b!\x12 -> menage blanc\n'
        b'\n###############################\n' b'\x1bd\t\x1bi'
        
        # --- SERVICE # 2 (1/2 Lasagne) ---
        b'\x1b!2\x1br\x00 PRINCIPALE\x1b!\x12\n'
        b'\x1b!2\x1br\x00    COMMANDE\n'
        b'\x1br\x00 Heure: 12:15:05\n'
        b'\x1br\x00  23-02-2026\n'
        b'\x1b!2\x1br\x00   TABLE # 32\n'
        b'\x1b!\x12\x1br\x00        ** SERVICE # 2 **\n'
        b'\x1b!2\x1br\x00  1\x1b!\x12 1/2 LASAGNE\n'
        b'\x1br\x00    \x1b!\x12 -> *GRATINEE\n'
        b'\n###############################\n' b'\x1bd\t\x1bi'
    ),
    "Emporter #1 (Mini Special)": (
        b'\x1b@'
        b'\x1b!2\x1br\x00PRINCIPALE\n'
        b'\x1b!2\x1br\x00POUR EMPORTER\n\n'
        b'\x1b!\x12Heure: 16:18:12\n'
        b'\x1b!\x12 8-01-2026\n'
        b'\x1br\x00    POUR EMPORTE #1\n\n'
        b'\x1b!2 1 * MINI SPECIAL\n'
        b'\x1b!\x12 1 * pas trop croute\n'
        b'\n###############################\n'
        b'\x1bd\t\x1bi'
    ),
    "Livraison #302 (Addition 998629)": (
        b'\x1b@' b'\x1b!2\x1br\x00        37\n'
        b'\x1b!\x12\x1b!2\x1br\x00    ND OUEST\n'
        b'\x1b!\x12\x1b!2\x1br\x00   4183359141\n'
        b'\x1br\x00        2026-01-27 10:52:14\n'
        b'\x1b!2\x1br\x00\x1b!\x12     ADDITION #998629-1\n'
        b'\x1b!2\x1br\x00   TRANS #017K\n'
        b'\x1br\x00   1 DEMI LASAGNE           $0.00\n'
        b'\x1br\x00   1 * VIANDE                $13.99  FP\n'
        b'\x1br\x00\n      TOT:     $18.95\n'
        b'\x1b!2\x1br\x00 LIVRAISON #302\n' b'\x1bd\t\x1bi'
    ),
    "Cuisine #302 (Mini Garnie)": (
        b'\x1b@' b'\x1b!2\x1br\x00 PRINCIPALE\x1b!\x12\n'
        b'\x1b!2\x1br\x00    LIVRAISON\n'
        b'\x1br\x00 Heure: 11:05:42\n'
        b'\x1br\x00  27-01-2026\n'
        b'\x1b!2\x1br\x00   TABLE # 302\n'
        b'\x1b!\x12\x1br\x00 \x1b!2  1\x1b!\x12 MINI GARNIE\n'
        b'\n###############################\n' b'\x1bd\t\x1bi'
    ),
    "Addition Livraison #320 (8 Eime Ave)": (
        b'\x1b@' b'\n\x1b!2\x1br\x00      856\n'
        b'\x1b!2\x1br\x00 8 EIME AVENUE\n'
        b'\x1b!2\x1br\x00  4185702847\n'
        b'\x1b!\x12  2026-01-14 15:37:51\n'
        b'\x1b!2\x1br\x00  ADDITION #994940-1\n'
        b'\x1b!\x12  1 MEDIUM PEPE        $24.99\n'
        b'\x1br\x00  1 PEPSI              $2.99\n'
        b'\x1br\x00  1 PT. POUTINE        $10.59\n'
        b'\x1br\x00      1 * SAUCE BBQ      $0.00\n'
        b'\x1br\x00   Frais de livrais       $2.50\n'
        b'\n' b'\x1br\x00  TOT:      $47.22\n' b'\n'
        b'\x1br\x00      VOUS AVEZ SERVI\n'
        b'\x1br\x00        PAR : LIVRAISON\n'
        b'\x1b!2\x1br\x00LIVRAISON #320\n' b'\x1bd\t\x1bi'
    )
}

class ProfessionalPOSDebugger:
    def __init__(self, master=None):
        if master is None:
            self.root = tk.Tk()
            self.root.geometry("1100x850")
        else:
            self.root = master

        self.root.title("POS ENGINE PRO - V4.0")
        self.root.configure(bg=BG_DARK)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.is_running = False
        self.server_socket = None
        self.status_var = tk.StringVar(value="READY")
        
        self._setup_styles()
        self._setup_ui()
        self.refresh_interfaces()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TNotebook", background=BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG_PANEL, foreground=FG_TEXT, padding=[15, 5])
        style.map("TNotebook.Tab", background=[("selected", ACCENT_BLUE)], foreground=[("selected", "white")])
        style.configure("TCombobox", fieldbackground=BG_PANEL, background=BG_PANEL, foreground="white")

    def show_custom_alert(self, title, message, color=ACCENT_RED):
        """Crée une fenêtre d'alerte personnalisée, TopLevel et non fermable."""
        alert = tk.Toplevel(self.root)
        alert.title(title)
        # On définit une taille fixe et on centre grossièrement
        alert.geometry("450x220")
        alert.configure(bg=BG_PANEL)
        alert.resizable(False, False)
        
        # Rendre la fenêtre toujours au-dessus et bloquer l'interaction avec le reste
        alert.attributes("-topmost", True)
        alert.grab_set()

        # EMPÊCHER LA FERMETURE (Le X en haut à droite ne fera rien)
        alert.protocol("WM_DELETE_WINDOW", lambda: None)

        # Barre de titre custom
        tk.Label(alert, text=f" ⚠ {title.upper()} ", bg=color, fg="white", 
                 font=("Segoe UI", 11, "bold"), pady=5).pack(fill="x")
        
        # Message
        tk.Label(alert, text=message, bg=BG_PANEL, fg=FG_TEXT, 
                 wraplength=400, font=("Segoe UI", 10), pady=30).pack(expand=True)

        # Bouton de fermeture manuel
        btn_close = tk.Button(alert, text="J'AI COMPRIS", 
                              command=alert.destroy, # Seule façon de fermer
                              bg=BG_DARK, fg=color, 
                              activebackground=color, activeforeground="white",
                              font=("Segoe UI", 9, "bold"),
                              relief="flat", width=20, cursor="hand2")
        btn_close.pack(pady=15)
        
    def _setup_ui(self):
        header = tk.Frame(self.root, bg=ACCENT_BLUE, height=40)
        header.pack(fill="x")
        tk.Label(header, text="POS ENGINE & NETWORK DIAGNOSTIC", bg=ACCENT_BLUE, fg="white", 
                 font=("Segoe UI", 11, "bold")).pack(pady=5)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # --- TAB 1: SERVEUR ---
        self.tab_srv = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_srv, text=" 🖨️ SERVEUR ")
        
        ctrl_bar = tk.Frame(self.tab_srv, bg=BG_PANEL, pady=10)
        ctrl_bar.pack(fill="x")
        
        tk.Label(ctrl_bar, text="Port:", bg=BG_PANEL, fg=FG_TEXT).pack(side="left", padx=5)
        self.srv_port = tk.Entry(ctrl_bar, width=8, bg=BG_DARK, fg="white", insertbackground="white")
        self.srv_port.insert(0, "9100")
        self.srv_port.pack(side="left")

        self.start_btn = tk.Button(ctrl_bar, text="DÉMARRER SERVEUR", command=self.toggle_server, 
                                   bg=ACCENT_GREEN, fg="white", font=("Segoe UI", 9, "bold"), width=18, relief="flat")
        self.start_btn.pack(side="left", padx=15)

        for key in STATUS_CODES.keys():
            tk.Radiobutton(ctrl_bar, text=key, variable=self.status_var, value=key, 
                           bg=BG_PANEL, fg=ACCENT_ORANGE, selectcolor=BG_DARK).pack(side="left")

        self.log_area = scrolledtext.ScrolledText(self.tab_srv, bg="#000000", fg="#d4d4d4", font=("Consolas", 10))
        self.log_area.pack(fill="both", expand=True, padx=5, pady=5)
        self._setup_tags()

        # --- TAB 2: OUTILS & ENVOI ---
        self.tab_tools = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_tools, text=" 🛠️ OUTILS ")
        
        # Section Envoi Manuel
        f1 = tk.LabelFrame(self.tab_tools, text=" Envoi Manuel de Tickets ", bg=BG_DARK, fg=ACCENT_BLUE, pady=10, padx=10)
        f1.pack(fill="x", padx=10, pady=5)

        row1 = tk.Frame(f1, bg=BG_DARK)
        row1.pack(fill="x", pady=5)
        tk.Label(row1, text="IP Cible:", bg=BG_DARK, fg=FG_TEXT).pack(side="left")
        self.cli_ip = tk.Entry(row1, width=15, bg=BG_PANEL, fg="white"); self.cli_ip.insert(0, "127.0.0.1"); self.cli_ip.pack(side="left", padx=5)
        tk.Label(row1, text="Port:", bg=BG_DARK, fg=FG_TEXT).pack(side="left", padx=5)
        self.cli_port = tk.Entry(row1, width=6, bg=BG_PANEL, fg="white"); self.cli_port.insert(0, "9100"); self.cli_port.pack(side="left", padx=5)

        row2 = tk.Frame(f1, bg=BG_DARK)
        row2.pack(fill="x", pady=5)
        tk.Label(row2, text="Choisir Ticket:", bg=BG_DARK, fg=FG_TEXT).pack(side="left")
        self.ticket_selector = ttk.Combobox(row2, values=list(TICKETS_LIBRARY.keys()), width=40, state="readonly")
        self.ticket_selector.current(0)
        self.ticket_selector.pack(side="left", padx=10)

        tk.Button(row2, text="🚀 ENVOYER TICKET", command=self.send_test_ticket, bg=ACCENT_BLUE, fg="white", font=("Arial", 9, "bold")).pack(side="left", padx=5)

        # Section Diagnostic
        f2 = tk.LabelFrame(self.tab_tools, text=" Diagnostic Réseau ", bg=BG_DARK, fg=ACCENT_BLUE, pady=10, padx=10)
        f2.pack(fill="x", padx=10, pady=5)
        self.ping_entry = tk.Entry(f2, width=15); self.ping_entry.insert(0, "192.168.1.100"); self.ping_entry.pack(side="left", padx=5)
        tk.Button(f2, text="PING IP", command=self.ping_ip, bg="#546E7A", fg="white").pack(side="left", padx=5)

        # --- TAB 3: INTERFACES RÉSEAU ---
        self.tab_net = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_net, text=" 🌐 INTERFACES ")
        self.net_area = scrolledtext.ScrolledText(self.tab_net, bg=BG_PANEL, fg=ACCENT_GREEN, font=("Consolas", 10))
        self.net_area.pack(fill="both", expand=True, padx=10, pady=10)

    def _setup_tags(self):
        self.log_area.tag_config("CONNECT", foreground=ACCENT_GREEN, font=("Consolas", 10, "bold"))
        self.log_area.tag_config("DISCONNECT", foreground=ACCENT_ORANGE, font=("Consolas", 10, "bold"))
        self.log_area.tag_config("HEX", foreground="#569cd6")
        self.log_area.tag_config("TXT", foreground="#ce9178")
        self.log_area.tag_config("ERR", foreground=ACCENT_RED)
        self.log_area.tag_config("REPLY", foreground="#f1c40f", font=("Consolas", 10, "italic"))

    def log(self, msg, tag="SYS"):
        ts = datetime.now().strftime("%H:%M:%S")
        try:
            self.log_area.configure(state='normal')
            self.log_area.insert(tk.END, f"[{ts}] {msg}\n", tag)
            self.log_area.configure(state='disabled')
            self.log_area.see(tk.END)
        except: pass

    def on_close(self):
        self.is_running = False
        if self.server_socket:
            try: self.server_socket.close()
            except: pass
        self.root.destroy()

    def toggle_server(self):
        if not self.is_running:
            try:
                # Récupération du port
                port_val = self.srv_port.get()
                if not port_val.isdigit():
                    raise ValueError("Le numéro de port doit être un nombre.")
                
                port = int(port_val)
                
                # Initialisation socket
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_socket.bind(("0.0.0.0", port))
                self.server_socket.listen(5)
                
                self.is_running = True
                self.start_btn.config(text="ARRÊTER LE SERVEUR", bg=ACCENT_RED)
                
                threading.Thread(target=self.run_server, daemon=True).start()
                self.log(f"SERVEUR DÉMARRÉ SUR LE PORT {port}", "CONNECT")
                
            except Exception as e:
                # --- APPEL DE LA FENÊTRE CUSTOM AU LIEU DE MESSAGEBOX ---
                error_msg = f"Impossible de démarrer le serveur sur le port {self.srv_port.get()}.\n\nErreur : {str(e)}"
                self.show_custom_alert("Erreur Critique Port", error_msg)
                
        else:
            self.is_running = False
            self.start_btn.config(text="DÉMARRER SERVEUR", bg=ACCENT_GREEN)
            if self.server_socket: 
                try:
                    self.server_socket.close()
                except:
                    pass
            self.log("Serveur arrêté.", "DISCONNECT")

    def run_server(self):
        while self.is_running:
            try:
                self.server_socket.settimeout(1.0)
                client, addr = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client, addr), daemon=True).start()
            except (socket.timeout, OSError): continue

    def handle_client(self, sock, addr):
        self.log(f"CONNECTÉ: {addr[0]}", "CONNECT")
        with sock:
            while self.is_running:
                try:
                    data = sock.recv(16384)
                    if not data: break
                    self.log(f"HEX: {data.hex(' ').upper()}", "HEX")
                    self.log(f"TXT: {''.join([chr(b) if 32 <= b <= 255 else '.' for b in data])}", "TXT")
                    if b'\x10\x04' in data:
                        resp = STATUS_CODES.get(self.status_var.get(), b'\x12')
                        sock.sendall(resp)
                        self.log(f">> RÉPONSE STATUT: {resp.hex().upper()}", "REPLY")
                except: break
        self.log(f"DÉCONNECTÉ: {addr[0]}", "DISCONNECT")

    def send_test_ticket(self):
        ip = self.cli_ip.get()
        try: 
            port = int(self.cli_port.get())
        except: 
            self.show_custom_alert("Erreur Format", "Le port cible doit être un nombre valide.")
            return
        
        ticket_key = self.ticket_selector.get()
        data = TICKETS_LIBRARY.get(ticket_key)

        def _task():
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(4)
                    s.connect((ip, port))
                    s.sendall(data)
                    self.log(f"SUCCÈS: '{ticket_key}' envoyé à {ip}")
            except Exception as e:
                self.log(f"ERREUR ENVOI: {e}", "ERR")
                # On utilise .after(0, ...) pour forcer l'affichage sur le thread principal
                error_msg = f"Impossible de joindre l'imprimante à l'adresse {ip}:{port}.\n\nDétail : {e}"
                self.root.after(0, lambda: self.show_custom_alert("Échec de Connexion", error_msg))

        threading.Thread(target=_task, daemon=True).start()
    def ping_ip(self):
        target = self.ping_entry.get()
        def _task():
            param = "-n" if platform.system().lower() == "windows" else "-c"
            res = subprocess.run(["ping", param, "1", target], capture_output=True)
            self.log(f"PING {target}: {'OK' if res.returncode==0 else 'ÉCHEC'}")
        threading.Thread(target=_task, daemon=True).start()

    def refresh_interfaces(self):
        self.net_area.configure(state='normal')
        self.net_area.delete('1.0', tk.END)
        for iface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    self.net_area.insert(tk.END, f"{iface}: {addr.address}\n")
        self.net_area.configure(state='disabled')

if __name__ == "__main__":
    app = ProfessionalPOSDebugger()
    app.root.mainloop()