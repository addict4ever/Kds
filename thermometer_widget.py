import tkinter as tk
from tkinter import ttk, messagebox
import json, os, threading, time, logging, sys
from datetime import datetime
from pymodbus.client.sync import ModbusSerialClient

# Import de la vue professionnelle avancée
from temperature_view_gui import AdvancedThermometerDashboard

LOG_SYS_PATH = r"C:\resto_controller\logs\system_errors_thermometres.log"
os.makedirs(os.path.dirname(LOG_SYS_PATH), exist_ok=True)
logging.basicConfig(filename=LOG_SYS_PATH, level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG_FILE = r"C:\resto_controller\thermometre.json"
LOG_DIR = r"C:\resto_controller\temperature"


class SensorWidget:
    """Widget de capteur optimisé tactile avec appui long de 5 secondes."""
    def __init__(self, root, sensor_config, callback_long_press):
        self.config = sensor_config
        self.root = root
        self.callback_long_press = callback_long_press
        self.timer_id = None
        self.is_pressing = False

        self.frame = tk.Frame(root, bg="black", relief="raised", bd=2)
        self.frame.pack(side="left", padx=5)
        
        self.label = tk.Label(
            self.frame, 
            text=f"{self.config['name']}\n--°C", 
            bg="black", 
            fg="white", 
            font=("Segoe UI", 10, "bold"), 
            width=10, 
            height=3,
            cursor="hand2"
        )
        self.label.pack()

        self.label.bind("<ButtonPress-1>", self._on_press)
        self.label.bind("<ButtonRelease-1>", self._on_release)
        self.label.bind("<Leave>", self._on_release)

    def _on_press(self, event):
        self.is_pressing = True
        self.frame.config(bg="#2980b9")
        self.label.config(bg="#2980b9", fg="#f1c40f")

        def trigger_long_press():
            if self.is_pressing:
                self._reset_style()
                self.callback_long_press(self.config['name'])

        self.timer_id = self.root.after(5000, trigger_long_press)

    def _on_release(self, event):
        if self.is_pressing:
            self.is_pressing = False
            self._reset_style()
            if hasattr(self, 'timer_id') and self.timer_id:
                try: self.root.after_cancel(self.timer_id)
                except Exception: pass

    def _reset_style(self):
        try:
            self.frame.config(bg="black")
            self.label.config(bg="black")
        except Exception: pass

    def update(self, val):
        if val is None:
            if not self.is_pressing:
                self.label.config(text=f"{self.config['name']}\nNA", fg="yellow")
            return
            
        t_min = self.config.get('min', 0.0)
        t_max = self.config.get('max', 100.0)
        color = self.config.get('color', 'white') if t_min <= val <= t_max else "red"
        
        if not self.is_pressing:
            self.label.config(text=f"{self.config['name']}\n{val:.1f}°C", fg=color)


class FloatingApp:
    """Application flottante principale."""
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="black")
        
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"+0+{screen_height - 60}")
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        
        self.sensors = self.load_sensors()
        self.widgets = []
        self.init_widgets()
            
        self.running = True
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()
        
        try:
            self.root.mainloop()
        except Exception as e:
            logging.error(f"Erreur boucle Tkinter : {e}")
        finally:
            self.running = False

    def init_widgets(self):
        if not self.sensors:
            dummy_config = {'name': 'Aucun', 'min': 0, 'max': 0}
            widget = SensorWidget(self.root, dummy_config, self.open_advanced_dashboard)
            widget.update(None)
            self.widgets.append(widget)
        else:
            for s in self.sensors:
                widget = SensorWidget(self.root, s, self.open_advanced_dashboard)
                self.widgets.append(widget)

    def open_advanced_dashboard(self, sensor_name):
        AdvancedThermometerDashboard(self.root, target_sensor=sensor_name)

    def load_sensors(self):
        default_config = {
            "sensors": [{"name": "Frigo_1", "port": "COM20", "slave_id": 1, "addr": 1, "color": "white", "visible": True, "min": 0.0, "max": 5.0}]
        }
        if not os.path.exists(CONFIG_FILE):
            try:
                os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(default_config, f, indent=4)
                return default_config['sensors']
            except Exception:
                return default_config['sensors']
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get('sensors', default_config['sensors'])
        except Exception:
            return default_config['sensors']

    def save_log(self, name, val):
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            date_str = datetime.now().strftime("%Y-%m-%d")
            file_path = os.path.join(LOG_DIR, f"logs_{date_str}.json")
            temp_path = file_path + ".tmp"
            
            data = []
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if not isinstance(data, list): data = []
                except Exception: data = []
            
            data.append({"heure": datetime.now().strftime("%H:%M:%S"), "sensor": name, "val": val})
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            os.replace(temp_path, file_path)
        except Exception as e:
            logging.error(f"Erreur log : {e}")

    def read_modbus(self, s):
        client = None
        try:
            client = ModbusSerialClient(method='rtu', port=s.get('port', 'COM20'), baudrate=9600, timeout=1.5, stopbits=1, bytesize=8, parity='N')
            if client.connect():
                res = client.read_holding_registers(address=s.get('addr', 1), count=1, unit=s.get('slave_id', 1))
                client.close()
                if res and not res.isError() and hasattr(res, 'registers'):
                    return res.registers[0] / 10.0
            return None
        except Exception:
            if client:
                try: client.close()
                except Exception: pass
            return None

    def loop(self):
        while self.running:
            try:
                if self.sensors:
                    for i, s in enumerate(self.sensors):
                        if not self.running: break
                        val = self.read_modbus(s)
                        if i < len(self.widgets):
                            self.root.after(0, lambda w=self.widgets[i], v=val: w.update(v))
                        if val is not None:
                            self.save_log(s['name'], val)
                for _ in range(60):
                    if not self.running: break
                    time.sleep(1)
            except Exception as e:
                logging.error(f"Erreur boucle : {e}")
                time.sleep(10)


if __name__ == "__main__":
    FloatingApp()