import tkinter as tk
from tkinter import messagebox
from keyboardModifier import VirtualKeyboard
import logging

logger = logging.getLogger(__name__)

class FloatingNote(tk.Toplevel):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        
        # --- SÉCURITÉ ---
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.grab_set()
        
        self.geometry("400x380")
        self.configure(bg="#ecf0f1", highlightthickness=2, highlightbackground="#34495e")

        self.protocol("WM_DELETE_WINDOW", self._ignore_close)

        tk.Label(self, text="Note Tactile (Max 100 char)", font=("Segoe UI", 12, "bold"), bg="#ecf0f1").pack(pady=10)
        
        # --- TEXT WIDGET SUR 3 LIGNES ---
        # height=3 définit visuellement 3 lignes de texte
        self.msg_text = tk.Text(self, width=40, height=3, font=("Segoe UI", 12), wrap=tk.WORD)
        self.msg_text.pack(pady=5, padx=10)
        self.msg_text.bind("<KeyRelease>", self._update_counter)
        self.msg_text.bind("<Button-1>", lambda e: self._open_keyboard())
        self.msg_text.focus_set()
        
        # Compteur
        self.lbl_counter = tk.Label(self, text="0/100", font=("Segoe UI", 9), bg="#ecf0f1", fg="gray")
        self.lbl_counter.pack()
        
        # Boutons
        btn_frame = tk.Frame(self, bg="#ecf0f1")
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="⌨️ Clavier", command=self._open_keyboard, bg="#3498db", fg="white", width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="🗑️ Effacer", command=self._clear_text, bg="#e67e22", fg="white", width=12).pack(side=tk.LEFT, padx=5)
        
        tk.Button(self, text="ENREGISTRER", command=self._save_note, 
                  bg="#27ae60", fg="white", font=("Segoe UI", 12, "bold"), relief=tk.FLAT, bd=0, width=25, height=2).pack(pady=10)
        
        tk.Button(self, text="QUITTER (ANNULER)", command=self._safe_close, 
                  bg="#c0392b", fg="white", font=("Segoe UI", 10), relief=tk.FLAT, bd=0).pack(pady=5)

    def _ignore_close(self):
        pass

    def _update_counter(self, event=None):
        # On récupère le texte du widget Text (1.0 = début, end-1c = fin sans saut de ligne final)
        content = self.msg_text.get("1.0", "end-1c")
        length = len(content)
        if length > 100:
            # Tronquer à 100
            self.msg_text.delete("1.100", "end")
            length = 100
        self.lbl_counter.config(text=f"{length}/100", fg="red" if length >= 100 else "gray")

    def _clear_text(self):
        self.msg_text.delete("1.0", tk.END)
        self._update_counter()

    def _open_keyboard(self):
        try:
            # 1. Définir le callback qui sera exécuté quand on clique sur "OK"
            def on_ok(target_widget):
                # On met à jour le compteur après la fermeture du clavier
                self._update_counter()
                logger.info("Clavier fermé, contenu récupéré.")

            # 2. Récupérer le contenu actuel
            initial_val = self.msg_text.get("1.0", "end-1c")
            
            # 3. Instancier le clavier en passant OBLIGATOIREMENT le ok_callback
            keyboard = VirtualKeyboard(
                self, 
                initial_content=initial_val, 
                ok_callback=on_ok  # <--- C'est ici que l'argument manquant est ajouté
            )
            
            # 4. Assigner la cible
            keyboard.target_entry = self.msg_text
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ouverture du clavier: {e}")
            messagebox.showerror("Erreur", "Impossible d'ouvrir le clavier.")

    def _safe_close(self):
        self.grab_release()
        self.destroy()

    def _save_note(self):
        try:
            message = self.msg_text.get("1.0", "end-1c").strip()
            if not message:
                messagebox.showwarning("Attention", "Message vide")
                return
            self.db_manager.add_note(message)
            self.grab_release()
            self.destroy()
        except Exception as e:
            logger.error(f"Erreur DB: {e}")
            messagebox.showerror("Erreur", "Sauvegarde impossible")