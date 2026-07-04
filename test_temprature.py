import json
import os
import random
from datetime import datetime, timedelta

# Configuration
LOG_DIR = r"C:\resto_controller\temperature"
SENSOR_NAME = "Frigo_1"
DAYS_TO_GENERATE = 10

def generate_mock_data():
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Date de départ : il y a 10 jours
    start_date = datetime.now() - timedelta(days=DAYS_TO_GENERATE)
    
    for day_offset in range(DAYS_TO_GENERATE):
        current_date = start_date + timedelta(days=day_offset)
        date_str = current_date.strftime("%Y-%m-%d")
        file_path = os.path.join(LOG_DIR, f"logs_{date_str}.json")
        
        daily_data = []
        
        # Générer 24 mesures (une par heure)
        for hour in range(24):
            # Simulation d'une température entre 2.0 et 5.0 degrés
            temp = round(random.uniform(2.0, 5.0), 1)
            
            entry = {
                "heure": f"{hour:02d}:00:00",
                "sensor": SENSOR_NAME,
                "val": temp
            }
            daily_data.append(entry)
        
        # Sauvegarde du fichier
        with open(file_path, "w") as f:
            json.dump(daily_data, f, indent=4)
        
        print(f"Fichier créé : {file_path}")

if __name__ == "__main__":
    generate_mock_data()
    print("\nGénération terminée avec succès.")