import serial
import time
from datetime import datetime

# Configuration
PORT = 'COM17'
BAUD_RATE = 9600

def start_sniffer():
    try:
        # Ouverture du port
        ser = serial.Serial(
            port=PORT,
            baudrate=BAUD_RATE,
            timeout=1,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS
        )
        
        print(f"--- Écoute active sur {PORT} ({BAUD_RATE} bps) ---")
        print("--- Appuyez sur CTRL+C pour arrêter ---\n")

        while True:
            if ser.in_waiting > 0:
                # Lecture des données en attente
                data = ser.read(ser.in_waiting)
                timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                
                print(f"[{timestamp}] Reçu ({len(data)} octets):")
                
                # Affichage en Hexadécimal (Utile pour les commandes ESC/POS)
                hex_view = " ".join(f"{b:02X}" for b in data)
                print(f"  HEX: {hex_view}")
                
                # Affichage en Texte (en remplaçant les caractères non-imprimables)
                text_view = "".join(chr(b) if 32 <= b <= 126 or b in [10, 13] else "." for b in data)
                print(f"  TXT: {text_view}")
                print("-" * 50)
                
            time.sleep(0.1)

    except serial.SerialException as e:
        print(f"Erreur : Impossible d'ouvrir le port {PORT}. Vérifiez s'il est déjà utilisé.")
        print(f"Détails : {e}")
    except KeyboardInterrupt:
        print("\nArrêt de l'écoute.")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    start_sniffer()