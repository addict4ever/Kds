# utils.py

from datetime import datetime
import platform

# --- Fonction BEEP ---
def play_beep():
    """Joue un son d'alerte pour les nouvelles commandes."""
    try:
        # Pour les systèmes Linux/macOS (nécessite 'say' ou 'aplay')
        if platform.system() == "Darwin": # macOS
            import os
            os.system('afplay /System/Library/Sounds/Tink.aiff &')
        elif platform.system() == "Linux":
            import os
            os.system('aplay /usr/share/sounds/gnome/default/alerts/glass.ogg &')
        elif platform.system() == "Windows":
            # Pour Windows, on peut utiliser la librairie winsound
            import winsound
            winsound.Beep(1000, 200) # Fréquence, Durée
        else:
             print("BEEP! (Son d'alerte non supporté sur ce système)")

    except Exception as e:
        print(f"Erreur lors de la tentative de jouer un son : {e}")

# Fin utils.py