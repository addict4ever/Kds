from PIL import Image
import os

def create_professional_ico(source_png_path, output_ico_path):
    try:
        # 1. Ouvrir l'image source
        img = Image.open(source_png_path)
        
        # 2. Vérifier si l'image est bien carrée
        if img.size[0] != img.size[1]:
            print("⚠️ Attention : Votre image n'est pas carrée. Elle risque d'être déformée.")
            # Optionnel : On peut forcer un redimensionnement carré ici
        
        # 3. Liste des tailles standard pour Windows (KDS / PyInstaller)
        # 16: Barre de titre, 32: Barre des tâches, 48: Explorateur, 256: Bureau/HD
        icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        
        # 4. Sauvegarder au format ICO avec toutes les tailles incluses
        img.save(output_ico_path, format='ICO', sizes=icon_sizes)
        
        print(f"✅ Succès ! L'icône '{output_ico_path}' a été générée avec {len(icon_sizes)} tailles.")
        print(f"Taille finale du fichier : {os.path.getsize(output_ico_path) // 1024} KB")

    except Exception as e:
        print(f"❌ Erreur : {e}")

# --- UTILISATION ---
# Remplacez 'logo_pizzeria.png' par le nom de votre image générée
create_professional_ico('votre_image_pizzeria.png', 'pizzeria_kds.ico')