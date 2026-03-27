import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageChops

def get_content_ranges(data, threshold):
    """Trouve les segments de contenu (lignes ou colonnes)."""
    ranges = []
    start = None
    for i, has_content in enumerate(data):
        if has_content and start is None:
            start = i
        elif not has_content and start is not None:
            if i - start > 2:  # Sensibilité ajustée
                ranges.append((start, i))
            start = None
    if start is not None:
        ranges.append((start, len(data)))
    return ranges

def find_sprite_locations(img, threshold=20):
    """Détecte les sprites dans une image (grille irrégulière)."""
    width, height = img.size
    gray = img.convert("L")
    
    # 1. Détection des rangées
    row_content = []
    for y in range(height):
        has_content = any(gray.getpixel((x, y)) > threshold for x in range(width))
        row_content.append(has_content)
    
    row_ranges = get_content_ranges(row_content, threshold)
    all_sprites = []
    
    # 2. Détection des colonnes par rangée
    for r_start, r_end in row_ranges:
        col_content = []
        for x in range(width):
            has_content = any(gray.getpixel((x, y)) > threshold for y in range(r_start, r_end))
            col_content.append(has_content)
        
        col_ranges = get_content_ranges(col_content, threshold)
        for c_start, c_end in col_ranges:
            all_sprites.append((c_start, r_start, c_end, r_end))
            
    return all_sprites

def process_single_file(file_path, base_output_folder, target_w, target_h, make_transparent):
    """Traite une seule image de spritesheet."""
    try:
        img_name = os.path.splitext(os.path.basename(file_path))[0]
        # Création du sous-dossier spécifique à l'action (ex: RUN, IDLE)
        action_folder = os.path.join(base_output_folder, img_name)
        if not os.path.exists(action_folder):
            os.makedirs(action_folder)

        img_raw = Image.open(file_path).convert("RGBA")
        sprite_boxes = find_sprite_locations(img_raw)
        
        if not sprite_boxes:
            return False

        for i, box in enumerate(sprite_boxes):
            sprite = img_raw.crop(box)
            
            # Autocrop
            bg = Image.new("RGBA", sprite.size, (0, 0, 0, 0))
            diff = ImageChops.difference(sprite, bg)
            bbox = diff.getbbox()
            if bbox:
                sprite = sprite.crop(bbox)

            # Transparence du noir
            if make_transparent:
                datas = sprite.getdata()
                new_data = [(0,0,0,0) if (d[0]<25 and d[1]<25 and d[2]<25) else d for d in datas]
                sprite.putdata(new_data)

            # Redimensionnement centré
            sprite.thumbnail((target_w, target_h), Image.Resampling.NEAREST)
            canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
            offset = ((target_w - sprite.width) // 2, (target_h - sprite.height) // 2)
            canvas.paste(sprite, offset)

            # Sauvegarde format: NOM_ACTION_001.png
            save_name = f"{img_name}_{i+1:03d}.png"
            canvas.save(os.path.join(action_folder, save_name))
        return True
    except Exception as e:
        print(f"Erreur sur {file_path}: {e}")
        return False

def start_processing():
    path = entry_input.get()
    output_folder = entry_output.get()
    
    try:
        tw, th = int(entry_w.get()), int(entry_h.get())
    except:
        messagebox.showerror("Erreur", "Taille invalide.")
        return

    if not path or not output_folder:
        messagebox.showwarning("Attention", "Veuillez remplir les chemins.")
        return

    files_to_process = []
    if os.path.isfile(path):
        files_to_process.append(path)
    elif os.path.isdir(path):
        # Liste toutes les images du répertoire
        exts = ('.png', '.jpg', '.jpeg', '.bmp', '.webp')
        files_to_process = [os.path.join(path, f) for f in os.listdir(path) if f.lower().endswith(exts)]

    if not files_to_process:
        messagebox.showinfo("Info", "Aucune image trouvée.")
        return

    success_count = 0
    for f in files_to_process:
        if process_single_file(f, output_folder, tw, th, var_transparent.get()):
            success_count += 1

    messagebox.showinfo("Terminé", f"Traitement fini !\n{success_count} fichiers traités.")
    os.startfile(output_folder)

# --- GUI ---
root = tk.Tk()
root.title("Sprite Slicer Automatique par Dossier 🐱")
root.geometry("650x500")

tk.Label(root, text="Source (Fichier ou Dossier complet) :", font=("Arial", 9, "bold")).pack(pady=5)
frame_in = tk.Frame(root)
frame_in.pack()
entry_input = tk.Entry(frame_in, width=50)
entry_input.pack(side=tk.LEFT, padx=5)
tk.Button(frame_in, text="Fichier", command=lambda: (entry_input.delete(0, tk.END), entry_input.insert(0, filedialog.askopenfilename()))).pack(side=tk.LEFT)
tk.Button(frame_in, text="Dossier", command=lambda: (entry_input.delete(0, tk.END), entry_input.insert(0, filedialog.askdirectory()))).pack(side=tk.LEFT)

tk.Label(root, text="Dossier de destination (Export) :", font=("Arial", 9, "bold")).pack(pady=5)
frame_out = tk.Frame(root)
frame_out.pack()
entry_output = tk.Entry(frame_out, width=50)
entry_output.pack(side=tk.LEFT, padx=5)
tk.Button(frame_out, text="Choisir", command=lambda: (entry_output.delete(0, tk.END), entry_output.insert(0, filedialog.askdirectory()))).pack(side=tk.LEFT)

frame_size = tk.LabelFrame(root, text=" Paramètres d'exportation ", padx=10, pady=10)
frame_size.pack(pady=20)
tk.Label(frame_size, text="Largeur:").grid(row=0, column=0)
entry_w = tk.Entry(frame_size, width=8); entry_w.insert(0, "128"); entry_w.grid(row=0, column=1)
tk.Label(frame_size, text="Hauteur:").grid(row=0, column=2)
entry_h = tk.Entry(frame_size, width=8); entry_h.insert(0, "128"); entry_h.grid(row=0, column=3, padx=5)
var_transparent = tk.BooleanVar(value=True)
tk.Checkbutton(frame_size, text="Fond noir -> Transparent", variable=var_transparent).grid(row=1, column=0, columnspan=4)

tk.Button(root, text="LANCER L'EXTRACTION", command=start_processing, 
          bg="#27ae60", fg="white", font=("Arial", 12, "bold"), height=2, width=30).pack(pady=20)

root.mainloop()