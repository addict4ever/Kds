import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image

class SpriteSheetGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("⛩️ Ninja Sprite Tool - AUTO MODE")
        self.root.geometry("650x700")
        self.root.configure(bg="#F5F5F5")

        self.source_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.tile_size = tk.IntVar(value=128)
        self.open_after = tk.BooleanVar(value=True)

        self.setup_ui()

    def setup_ui(self):
        ttk.Label(self.root, text="⛩️ AUTO SPRITE CONVERTER", font=("Segoe UI", 16, "bold")).pack(pady=15)

        # SOURCE : Dossier Parent (Ex: Skeleton_Crusader_1)
        frame_input = tk.LabelFrame(self.root, text=" 📂 Dossier du Personnage (Contient les sous-dossiers) ", padx=10, pady=10)
        frame_input.pack(fill="x", padx=20, pady=5)
        tk.Entry(frame_input, textvariable=self.source_path, width=50).pack(side="left", padx=5)
        ttk.Button(frame_input, text="Parcourir", command=self.browse_source).pack(side="left")

        # SORTIE
        frame_output = tk.LabelFrame(self.root, text=" 💾 Destination des Sheets ", padx=10, pady=10)
        frame_output.pack(fill="x", padx=20, pady=5)
        tk.Entry(frame_output, textvariable=self.output_dir, width=50).pack(side="left", padx=5)
        ttk.Button(frame_output, text="Parcourir", command=self.browse_output).pack(side="left")

        # OPTIONS
        frame_opts = tk.Frame(self.root, bg="#F5F5F5")
        frame_opts.pack(fill="x", padx=20, pady=10)
        tk.Label(frame_opts, text="Taille Frame:").pack(side="left")
        tk.Spinbox(frame_opts, from_=32, to=512, textvariable=self.tile_size, width=10).pack(side="left", padx=10)
        tk.Checkbutton(frame_opts, text="Ouvrir dossier final", variable=self.open_after, bg="#F5F5F5").pack(side="left")

        # JSON OUTPUT
        tk.Label(self.root, text="Code JSON complet généré :", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=20)
        self.log_box = tk.Text(self.root, height=18, width=75, font=("Consolas", 9), bg="#1E1E1E", fg="#D4D4D4")
        self.log_box.pack(pady=5, padx=20)

        # BOUTONS
        btn_frame = tk.Frame(self.root, bg="#F5F5F5")
        btn_frame.pack(fill="x", padx=20, pady=10)
        tk.Button(btn_frame, text="🚀 TOUT GÉNÉRER", bg="#4CAF50", fg="white", font=("Segoe UI", 12, "bold"), 
                  command=self.generate_all, height=2, relief="flat").pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(btn_frame, text="📋 COPIER JSON", bg="#2196F3", fg="white", font=("Segoe UI", 12, "bold"), 
                  command=self.copy_json, height=2, relief="flat").pack(side="left", fill="x", expand=True, padx=5)

    def browse_source(self):
        path = filedialog.askdirectory()
        if path:
            self.source_path.set(path)
            if not self.output_dir.get(): self.output_dir.set(path)

    def browse_output(self):
        path = filedialog.askdirectory()
        if path: self.output_dir.set(path)

    def copy_json(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.log_box.get("1.0", "end-1c"))
        messagebox.showinfo("Copie", "JSON copié !")

    def generate_all(self):
        root_src = self.source_path.get()
        dest_dir = self.output_dir.get()
        size = self.tile_size.get()

        if not root_src or not os.path.exists(root_src): return

        char_name = os.path.basename(root_src)
        char_key = char_name.lower().replace(" ", "_")
        
        animations_json = []
        brain_json = []

        # Parcourir chaque sous-dossier
        subfolders = [f for f in os.listdir(root_src) if os.path.isdir(os.path.join(root_src, f))]
        
        if not subfolders:
            messagebox.showwarning("Info", "Aucun sous-dossier trouvé dans le répertoire sélectionné.")
            return

        for folder in subfolders:
            folder_path = os.path.join(root_src, folder)
            images = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg'))]
            images.sort()

            if not images: continue

            num_frames = len(images)
            sheet_name = f"{folder}_Sheet.png"
            output_path = os.path.join(dest_dir, sheet_name)

            # Création de la planche
            sheet = Image.new("RGBA", (size * num_frames, size), (0, 0, 0, 0))
            for i, img_name in enumerate(images):
                with Image.open(os.path.join(folder_path, img_name)) as img:
                    img = img.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
                    sheet.paste(img, (i * size, 0))
            sheet.save(output_path)

            # Préparation des données JSON
            action_key = folder.upper().replace(" ", "_")
            animations_json.append(f'        "{action_key}": ["{char_name}/{sheet_name}", {size}, {size}, {num_frames}]')
            
            mvt = "random" if any(k in action_key for k in ["WALK", "RUN", "MOVE"]) else "stop"
            brain_json.append(f'        {{ "state": "{action_key}", "chance": 0.1, "movement": "{mvt}" }}')

        # Construction du texte final
        final_json = f'"{char_key}": {{\n    "animations": {{\n'
        final_json += ",\n".join(animations_json)
        final_json += '\n    },\n    "brain": [\n'
        final_json += ",\n".join(brain_json)
        final_json += '\n    ]\n}'

        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.insert("1.0", final_json)
        self.log_box.config(state="disabled")

        if self.open_after.get(): os.startfile(dest_dir)
        messagebox.showinfo("Terminé", f"Planches générées pour {len(animations_json)} animations !")

if __name__ == "__main__":
    root = tk.Tk()
    app = SpriteSheetGUI(root)
    root.mainloop()