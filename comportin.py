import os
import subprocess
import shutil

def protect_all_files():
    # 1. Configuration des dossiers
    current_dir = os.getcwd()
    output_dir = os.path.join(current_dir, "distprotected")
    
    # Créer le dossier de sortie s'il n'existe pas
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Création du dossier : {output_dir}")

    # 2. Lister tous les fichiers .py
    # On ignore ce script lui-même (nommé par exemple 'protect_script.py')
    files_to_protect = [f for f in os.listdir(current_dir) 
                        if f.endswith('.py') and f != os.path.basename(__file__)]

    if not files_to_protect:
        print("Aucun fichier .py trouvé à protéger.")
        return

    print(f"Fichiers trouvés ({len(files_to_protect)}) : {files_to_protect}")
    print("-" * 50)

    # 3. Lancer PyArmor pour chaque fichier
    for file in files_to_protect:
        print(f"🔒 Protection de : {file} ...")
        
        # Commande : pyarmor gen -O distprotected/ nom_du_fichier.py
        # -O permet de spécifier le dossier de sortie
        try:
            command = ["pyarmor", "gen", "-O", output_dir, file]
            
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            print(f"✅ Terminé : {file}")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Erreur lors de la protection de {file}:")
            print(e.stderr)
        except FileNotFoundError:
            print("❌ Erreur : 'pyarmor' n'est pas installé ou n'est pas dans le PATH.")
            break

    print("-" * 50)
    print(f"Opération terminée. Les fichiers protégés sont dans : {output_dir}")

if __name__ == "__main__":
    protect_all_files()