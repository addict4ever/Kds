import tkinter as tk
from tkinter import scrolledtext, ttk
import os
import glob
import re
import shutil
from datetime import datetime

# Importations depuis votre fichier serial_reader.py
try:
    from serial_reader import (
        SERIAL_PORT_PRINTER, 
        SERIAL_PORT_PRINTER_2, 
        SERIAL_PORT_PRINTER_3, 
        SerialReader
    )
except ImportError:
    SERIAL_PORT_PRINTER, SERIAL_PORT_PRINTER_2, SERIAL_PORT_PRINTER_3 = "COM5", "COM10", "TCP"

try:
    from keyboard import VirtualKeyboard
except ImportError:
    VirtualKeyboard = None

# --- CLASSE MESSAGEBOX PERSONNALISÉE (TACTILE & SÉCURISÉE) ---
class CustomMsgBox(tk.Toplevel):
    def __init__(self, parent, title, message, is_question=False):
        super().__init__(parent)
        self.result = False
        self.overrideredirect(True)  # Supprime la barre de titre (pas de X, pas de réduction)
        self.attributes("-topmost", True)
        self.config(bg="#1c1c1c", highlightbackground="#00d2ff", highlightthickness=4)
        
        # Taille adaptée au tactile
        w, h = 700, 400
        sw, sh = parent.winfo_screenwidth(), parent.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        tk.Label(self, text=title.upper(), font=("Arial", 22, "bold"), bg="#00d2ff", fg="black", pady=20).pack(fill=tk.X)
        
        msg_label = tk.Label(self, text=message, font=("Arial", 16), bg="#1c1c1c", fg="white", wraplength=600, pady=40)
        msg_label.pack(expand=True)

        btn_frame = tk.Frame(self, bg="#1c1c1c", pady=30)
        btn_frame.pack(fill=tk.X)

        if is_question:
            tk.Button(btn_frame, text="✅ OUI / CONFIRMER", font=("Arial", 18, "bold"), bg="#27ae60", fg="white", 
                      width=15, pady=15, command=self.set_yes).pack(side=tk.LEFT, padx=40)
            tk.Button(btn_frame, text="❌ NON / ANNULER", font=("Arial", 18, "bold"), bg="#c0392b", fg="white", 
                      width=15, pady=15, command=self.destroy).pack(side=tk.RIGHT, padx=40)
        else:
            tk.Button(btn_frame, text="OK / COMPRIS", font=("Arial", 18, "bold"), bg="#3498db", fg="white", 
                      width=20, pady=15, command=self.destroy).pack()

    def set_yes(self):
        self.result = True
        self.destroy()

# --- FENÊTRE PRINCIPALE DES LOGS (FULLSCREEN TACTILE) ---
class LogViewWindow(tk.Toplevel):
    def __init__(self, master, serial_reader_instance=None):
        super().__init__(master)
        self.serial_reader = serial_reader_instance
        
        # Taille initiale de la fenêtre (pas de plein écran)
        self.geometry("1400x900")
        self.title("KDS EXPERT LOGS")
        self.config(bg="#000")

        # Variables d'état
        self.font_size = 18
        self.auto_scroll = tk.BooleanVar(value=True)
        self.current_opened_file = None
        
        self.port_mapping = {
            "Imprimante 1 (COM5)": SERIAL_PORT_PRINTER,
            "Imprimante 2 (COM10)": SERIAL_PORT_PRINTER_2,
            "Imprimante 3 (TCP)": SERIAL_PORT_PRINTER_3
        }

        # STYLE DES SCROLLBARS ULTRA-LARGES (50px)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Vertical.TScrollbar", width=50, background="#444", arrowsize=50)

        # --- HEADER ---
        header = tk.Frame(self, bg="#111", pady=10)
        header.pack(fill=tk.X)
        tk.Label(header, text="📑 SYSTEM LOGS", font=("Impact", 12), bg="#111", fg="#00d2ff").pack(side=tk.LEFT, padx=20)
        
        # Zoom Controls
        zoom_frame = tk.Frame(header, bg="#111")
        zoom_frame.pack(side=tk.RIGHT, padx=20)
        tk.Button(zoom_frame, text="A +", font=("Arial", 16, "bold"), bg="#333", fg="white", width=4, command=lambda: self.change_zoom(2)).pack(side=tk.LEFT, padx=5)
        tk.Button(zoom_frame, text="A -", font=("Arial", 16, "bold"), bg="#333", fg="white", width=4, command=lambda: self.change_zoom(-2)).pack(side=tk.LEFT, padx=5)

        # --- CORPS ---
        main_frame = tk.Frame(self, bg="#000")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Liste Gauche
        left_panel = tk.Frame(main_frame, bg="#111", width=350)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        self.log_listbox = tk.Listbox(left_panel, bg="#000", fg="white", font=("Arial", 14), 
                                      selectbackground="#00d2ff", borderwidth=0, highlightthickness=0)
        ls = ttk.Scrollbar(left_panel, orient="vertical", command=self.log_listbox.yview, style="Vertical.TScrollbar")
        self.log_listbox.configure(yscrollcommand=ls.set)
        self.log_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ls.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_listbox.bind("<<ListboxSelect>>", self.on_select_log)

        # Zone Droite
        right_panel = tk.Frame(main_frame, bg="#000")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Recherche
        s_bar = tk.Frame(right_panel, bg="#222", pady=5)
        s_bar.pack(fill=tk.X)
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(s_bar, textvariable=self.search_var, font=("Arial", 20), bg="#000", fg="yellow")
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.search_entry.bind("<Button-1>", self._open_virtual_keyboard)

        # Filtres & Auto-scroll
        filter_bar = tk.Frame(right_panel, bg="#000", pady=5)
        filter_bar.pack(fill=tk.X)
        for f in ["IP", "PRINTER", "OFFLINE", "ERROR"]:
            tk.Button(filter_bar, text=f, font=("Arial", 11, "bold"), bg="#2c3e50", fg="white", 
                      command=lambda v=f: self.apply_filter(v), padx=20, pady=10).pack(side=tk.LEFT, padx=3)
        
        tk.Checkbutton(filter_bar, text="AUTO-SCROLL", variable=self.auto_scroll, font=("Arial", 11), 
                       bg="#000", fg="#00d2ff", selectcolor="#000").pack(side=tk.RIGHT, padx=10)

        # Zone Texte (Scrollbar 50px)
        self.text_area = scrolledtext.ScrolledText(right_panel, bg="#050505", fg="#2ecc71", font=("Consolas", self.font_size))
        self.text_area.vbar.config(width=50) 
        self.text_area.pack(fill=tk.BOTH, expand=True)

        # Navigation & Export
        nav_bar = tk.Frame(right_panel, bg="#111", pady=10)
        nav_bar.pack(fill=tk.X)
        tk.Button(nav_bar, text="⏫ DÉBUT", font=("Arial", 12, "bold"), bg="#444", fg="white", width=10, pady=15, command=lambda: self.text_area.see("1.0")).pack(side=tk.LEFT, padx=5)
        tk.Button(nav_bar, text="⏬ FIN", font=("Arial", 12, "bold"), bg="#444", fg="white", width=10, pady=15, command=lambda: self.text_area.see(tk.END)).pack(side=tk.LEFT, padx=5)
        
        tk.Button(nav_bar, text="🧹 RESET", font=("Arial", 12), bg="#c0392b", fg="white", pady=15, padx=15, command=self.reset_filters).pack(side=tk.RIGHT, padx=5)
        tk.Button(nav_bar, text="💾 EXPORT USB (E:)", font=("Arial", 12, "bold"), bg="#f39c12", fg="black", pady=15, padx=15, command=self.export_usb).pack(side=tk.RIGHT, padx=5)

        # --- FOOTER ---
        footer = tk.Frame(self, bg="#111", pady=20)
        footer.pack(fill=tk.X, side=tk.BOTTOM)

        tk.Label(footer, text="SORTIE :", bg="#111", fg="white", font=("Arial", 14, "bold")).pack(side=tk.LEFT, padx=(30, 10))
        self.port_choice = tk.StringVar(value="Imprimante 3 (TCP)")
        cb = ttk.Combobox(footer, textvariable=self.port_choice, values=list(self.port_mapping.keys()), font=("Arial", 18), state="readonly", width=20)
        cb.pack(side=tk.LEFT, padx=10)

        tk.Button(footer, 
                  text="🖨️ RÉIMPRIMER", 
                  font=("Arial", 14, "bold"), 
                  bg="#27ae60", 
                  fg="white", 
                  pady=30,           # Hauteur doublée par rapport aux autres (15 -> 30)
                  padx=20, 
                  width=40,          # Largeur allongée horizontalement
                  command=self.handle_print_logic).pack(side=tk.LEFT, padx=30)

        # BOUTON QUITTER
        tk.Button(footer, 
                  text="QUITTER", 
                  font=("Arial", 14, "bold"), 
                  bg="#444", 
                  fg="white", 
                  command=self.destroy, 
                  padx=30, 
                  pady=15).pack(side=tk.RIGHT, padx=20)

        self.refresh_logs()

    # --- LOGIQUE NOUVEAUTÉS ---

    def change_zoom(self, delta):
        self.font_size += delta
        self.text_area.config(font=("Consolas", self.font_size))

    def export_usb(self):
        """Exporte le fichier log actuel vers E:\\LOG"""
        if not self.current_opened_file:
            CustomMsgBox(self, "Erreur", "Ouvrez un fichier log d'abord.")
            return

        target_dir = r"E:\LOG"
        filename = os.path.basename(self.current_opened_file)
        target_path = os.path.join(target_dir, filename)

        try:
            # 1. Vérifier si le lecteur E: existe
            if not os.path.exists("E:\\"):
                CustomMsgBox(self, "Erreur USB", "La clé USB (Lecteur E:) est introuvable.\nVeuillez l'insérer.")
                return

            # 2. Créer le dossier LOG s'il n'existe pas
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)

            # 3. Copier le fichier
            shutil.copy2(self.current_opened_file, target_path)
            
            CustomMsgBox(self, "Succès Export", f"Fichier copié avec succès dans :\n{target_path}")

        except Exception as e:
            CustomMsgBox(self, "Échec Export", f"Erreur lors de la copie :\n{str(e)}")

    def reset_filters(self):
        self.search_var.set("")
        self.text_area.tag_remove("match", "1.0", tk.END)
        self.refresh_logs()
        CustomMsgBox(self, "Info", "Filtres et recherche réinitialisés.")

    # --- LOGIQUE D'IMPRESSION ---

    def handle_print_logic(self):
        content = ""
        is_selection = False
        try:
            content = self.text_area.get(tk.SEL_FIRST, tk.SEL_LAST)
            is_selection = True
        except tk.TclError:
            content = self.text_area.get("1.0", tk.END)
            is_selection = False

        if not content.strip(): return

        msg = "Réimprimer la SÉLECTION ?" if is_selection else "AUCUNE SÉLECTION.\n\nVoulez-vous réimprimer la TOTALITÉ du log ?"
        dialog = CustomMsgBox(self, "Confirmation", msg, is_question=True)
        self.wait_window(dialog)

        if dialog.result:
            target = self.port_mapping.get(self.port_choice.get(), SERIAL_PORT_PRINTER_3)
            clean_text = self.clean_for_printer(content)
            success = SerialReader.reprint_ticket_to_printer(clean_text, target)
            
            if success:
                CustomMsgBox(self, "Succès", "Impression envoyée !")
            else:
                CustomMsgBox(self, "Échec", "Erreur de connexion imprimante.")

    def clean_for_printer(self, text):
        lines = text.split('\n')
        return "\n".join([re.sub(r'^\d{4}-\d{2}-\d{2}.*?-\s*\w+\s*-\s*', '', l) for l in lines])

    # --- MÉTHODES UI ---

    def on_select_log(self, event):
        selection = self.log_listbox.curselection()
        if not selection: return
        filename = self.log_listbox.get(selection[0])
        try:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
            self.current_opened_file = filename
            self.text_area.config(state=tk.NORMAL)
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert(tk.END, content)
            self.text_area.config(state=tk.DISABLED)
            if self.auto_scroll.get(): self.text_area.see(tk.END)
        except Exception as e:
            CustomMsgBox(self, "Erreur", str(e))

    def apply_filter(self, val):
        self.search_var.set(val)
        self.text_area.tag_remove("match", "1.0", tk.END)
        if not val: return
        start_pos = "1.0"
        while True:
            start_pos = self.text_area.search(val, start_pos, stopindex=tk.END, nocase=True)
            if not start_pos: break
            end_pos = f"{start_pos}+{len(val)}c"
            self.text_area.tag_add("match", start_pos, end_pos)
            self.text_area.tag_config("match", background="#d35400", foreground="white")
            start_pos = end_pos

    def refresh_logs(self):
        self.log_listbox.delete(0, tk.END)
        files = sorted(glob.glob("kds_serial_log_*.txt"), key=os.path.getmtime, reverse=True)
        for f in files: self.log_listbox.insert(tk.END, f)

    def _open_virtual_keyboard(self, event):
        if VirtualKeyboard:
            VirtualKeyboard(self, self.search_entry)

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    LogViewWindow(root).mainloop()