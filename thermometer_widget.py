import tkinter as tk
import json, os, threading, time, logging
from datetime import datetime
from pymodbus.client.sync import ModbusSerialClient

# Configuration des logs système
LOG_SYS_PATH = r"C:\resto_controller\logs\system_errors_thermometres.log"
os.makedirs(os.path.dirname(LOG_SYS_PATH), exist_ok=True)
logging.basicConfig(
    filename=LOG_SYS_PATH,
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

CONFIG_FILE = r"C:\resto_controller\thermometre.json"
LOG_DIR = r"C:\resto_controller\temperature"

class SensorWidget:
    def __init__(self, root, sensor_config):
        self.config = sensor_config
        self.root = root
        self.frame = tk.Frame(root, bg="black", relief="raised", bd=2)
        self.frame.pack(side="left", padx=5)
        self.label = tk.Label(self.frame, text=f"{self.config['name']}\n--°C", bg="black", fg="white", font=("Arial", 10), width=10, height=3)
        self.label.pack()

    def update(self, val):
        if val is None:
            # Affichage de NA au lieu de Err
            self.label.config(text=f"{self.config['name']}\nNA", fg="yellow")
            return
        t_min = self.config.get('min', 0)
        t_max = self.config.get('max', 100)
        color = self.config.get('color', 'white') if t_min <= val <= t_max else "red"
        self.label.config(text=f"{self.config['name']}\n{val:.1f}°C", fg=color)

class FloatingApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="black")
        
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"+0+{screen_height - 60}")
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        
        try:
            self.sensors = self.load_sensors()
        except Exception as e:
            self.sensors = []
            
        # Gestion si aucun capteur n'est configuré
        if not self.sensors:
            self.widgets = [SensorWidget(self.root, {'name': 'Aucun', 'min': 0, 'max': 0})]
            self.root.after(100, lambda: self.widgets[0].update(None))
        else:
            self.widgets = [SensorWidget(self.root, s) for s in self.sensors]
            
        threading.Thread(target=self.loop, daemon=True).start()
        self.root.mainloop()

    def load_sensors(self):
        default_config = {
            "sensors": [
                {
                    "name": "Frigo_1", 
                    "port": "COM20", 
                    "slave_id": 1, 
                    "addr": 1, 
                    "color": "white", 
                    "visible": True,
                    "min": 0.0,
                    "max": 5.0
                }
            ]
        }

        # 1. Si le fichier n'existe pas, on le crée
        if not os.path.exists(CONFIG_FILE):
            try:
                os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
                with open(CONFIG_FILE, "w") as f:
                    json.dump(default_config, f, indent=4)
                return default_config['sensors']
            except IOError:
                return []

        # 2. Si le fichier existe, on tente de le lire
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f).get('sensors', [])
        except (json.JSONDecodeError, IOError):
            # 3. GESTION D'ERREUR : Fichier corrompu ou illisible
            # On renomme le fichier corrompu pour le sauvegarder au cas où
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{CONFIG_FILE}.corrupted_{timestamp}"
            try:
                os.rename(CONFIG_FILE, backup_path)
                # On recrée un fichier sain par-dessus
                with open(CONFIG_FILE, "w") as f:
                    json.dump(default_config, f, indent=4)
                return default_config['sensors']
            except Exception:
                # Si même la création échoue, on retourne vide
                return []

    def save_log(self, name, val):
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            date_str = datetime.now().strftime("%Y-%m-%d")
            file_name = f"logs_{date_str}.json"
            file_path = os.path.join(LOG_DIR, file_name)
            temp_path = file_path + ".tmp"
            
            data = []
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r") as f:
                        data = json.load(f)
                except (json.JSONDecodeError, IOError):
                    data = []
            
            data.append({
                "heure": datetime.now().strftime("%H:%M:%S"), 
                "sensor": name, 
                "val": val
            })
            
            with open(temp_path, "w") as f:
                json.dump(data, f, indent=4)
            os.replace(temp_path, file_path)
        except Exception as e:
            logging.error(f"Erreur lors de la sauvegarde du log : {e}")
            if 'temp_path' in locals() and os.path.exists(temp_path): 
                try: os.remove(temp_path)
                except: pass
                
    def read_modbus(self, s):
        client = None
        try:
            client = ModbusSerialClient(method='rtu', port=s['port'], baudrate=9600, timeout=1)
            if client.connect():
                res = client.read_holding_registers(address=s['addr'], count=1, unit=s['slave_id'])
                client.close()
                if not res.isError():
                    return res.registers[0] / 10.0
            return None
        except Exception:
            if client: client.close()
            return None

    def loop(self):
        while True:
            # Ne boucle que si nous avons de vrais capteurs
            if self.sensors:
                for i, s in enumerate(self.sensors):
                    val = self.read_modbus(s)
                    self.root.after(0, lambda w=self.widgets[i], v=val: w.update(v))
                    
                    if val is not None and datetime.now().minute == 0:
                        self.save_log(s['name'], val)
            else:
                # Si aucun capteur, on attend juste pour ne pas surcharger le CPU
                time.sleep(60)
                continue
            
            time.sleep(60)

if __name__ == "__main__":
    FloatingApp()