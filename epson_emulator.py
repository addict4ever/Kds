# epson_emulator.py - Émulateur d'Imprimante EPSON RS232 pour KDS

import time
import threading
from datetime import datetime
import serial
import re
from typing import Dict, Any

try:
    # Simulez les constantes si elles ne sont pas disponibles
    # Vous devez vous assurer que ces ports correspondent à votre configuration virtuelle
    class KDSConstants:
        # Port où le KDS Reader.py écoute
        SERIAL_PORT = 'COM8' 
        BAUD_RATE = 9600
        SERIAL_TIMEOUT = 0.1
        TICKET_END_SEQUENCE = b'\x0C' # Code d'alimentation papier/coupe papier (Form Feed)

    kds_constants = KDSConstants()
    
    # Le port où l'émulateur doit écouter le POS. 
    # Doit être le port cible du POS dans votre configuration virtuelle.
    POS_LISTEN_PORT = 'COM6' 
    KDS_FORWARD_PORT = kds_constants.SERIAL_PORT # Le même port que le KDS lit (COM2 dans cet exemple)

except ImportError:
    print("ERREUR: Le script nécessite 'pyserial' (pip install pyserial).")
    exit()

# Récupération des constantes de base
BAUD_RATE = kds_constants.BAUD_RATE
SERIAL_TIMEOUT = kds_constants.SERIAL_TIMEOUT
TICKET_END_SEQUENCE = kds_constants.TICKET_END_SEQUENCE

# --- Constantes EPSON / Réponses de Statut ---
# DLE EOT Statut Réponse (réponse que l'imprimante donne au POS)
STATUS_MAPPING: Dict[bytes, bytes] = {
    # Requête de Statut Imprimante (DLE EOT 1) -> Réponse: Prête (0x12) ou autres statuts
    b'\x10\x04\x01': b'\x12',  # Prête, hors ligne (0x12)
    b'\x10\x04\x02': b'\x30',  # Statut hors ligne : Prête à imprimer (0x30)
    b'\x10\x04\x04': b'\x40',  # Statut du papier : Papier OK (0x40)
    # Le POS envoie parfois des requêtes ENQ pour vérifier la disponibilité
    b'\x05': b'\x06' # ENQ (Enquiry) -> ACK (Acknowledge)
}

# Commandes de contrôle de flux
CONTROL_COMMANDS: Dict[bytes, str] = {
    b'\x11': 'XON (Reprendre Envoi)',
    b'\x13': 'XOFF (Arrêter Envoi)',
    b'\x06': 'ACK (Accusé de Réception)',
    b'\x15': 'NAK (Négatif Acknowledge)'
}


class EpsonEmulator(threading.Thread):
    """
    Simule l'imprimante EPSON, répond aux requêtes de statut du POS, 
    et transmet le flux de données au KDS Reader.
    """
    def __init__(self):
        super().__init__()
        self._stop_event = threading.Event()
        self.daemon = True
        
        self.pos_ser = None  # Port pour la communication avec le POS (Lecture & Réponse)
        self.kds_ser = None  # Port pour l'envoi des commandes au KDS (Écriture seule)
        
        # Tampon pour accumuler les données du POS
        self.current_buffer = b'' 
        
        # Tente d'ouvrir les deux ports
        if not self._open_ports():
            self._stop_event.set()

    def _open_ports(self) -> bool:
        """Tente d'ouvrir les ports POS et KDS."""
        try:
            # 1. Port d'écoute du POS (COM1 dans l'exemple)
            self.pos_ser = serial.Serial(
                port=POS_LISTEN_PORT,
                baudrate=BAUD_RATE,
                timeout=SERIAL_TIMEOUT
            )
            print(f"[OK] Émulateur écoute sur le port POS: {POS_LISTEN_PORT} @ {BAUD_RATE} bps")
            
            # 2. Port de transmission au KDS (COM2 dans l'exemple)
            self.kds_ser = serial.Serial(
                port=KDS_FORWARD_PORT,
                baudrate=BAUD_RATE,
                timeout=SERIAL_TIMEOUT
            )
            print(f"[OK] Émulateur transmet au port KDS: {KDS_FORWARD_PORT} @ {BAUD_RATE} bps")
            
            return True
            
        except serial.SerialException as e:
            print(f"[ERREUR FATALE] Impossible d'ouvrir un ou les deux ports. Vérifiez les connexions virtuelles.")
            print(f"Port(s) en cause ou déjà utilisé(s): {e}")
            return False

    def run(self):
        """Méthode de thread pour la lecture en continu du port POS."""
        if self._stop_event.is_set():
            return

        print("\n=============================================")
        print(f"Émulateur EPSON Démarré, simulant l'imprimante...")
        print("=============================================\n")
        
        while not self._stop_event.is_set():
            try:
                # Lit les données disponibles envoyées par le POS
                data = self.pos_ser.read(self.pos_ser.in_waiting or 1)
                
                if data:
                    self.process_incoming_data(data)
                
                time.sleep(SERIAL_TIMEOUT / 2)
                
            except Exception as e:
                # Gestion des erreurs de lecture/connexion
                print(f"[ERREUR LECTURE POS] {e}")
                time.sleep(1)

    def process_incoming_data(self, data: bytes):
        """
        Analyse les données entrantes, répond au POS si nécessaire (simulation de l'imprimante),
        et transfère le flux de données au KDS.
        """
        
        # 1. Vérification des commandes de Statut et de Contrôle
        
        # Cherche et répond aux requêtes de statut (DLE EOT, ENQ)
        for req_bytes, resp_bytes in STATUS_MAPPING.items():
            if req_bytes in data:
                # Répond immédiatement au POS pour maintenir le flux
                self.pos_ser.write(resp_bytes)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [RÉPONSE] Statut {req_bytes.hex()} -> Envoyé: {resp_bytes.hex()} (Printer Ready)")
                
                # Retire le signal du buffer pour ne pas l'envoyer au KDS comme texte
                data = data.replace(req_bytes, b'')
                
        # Log les commandes de contrôle (XON/XOFF/ACK/NAK)
        for cmd_bytes, cmd_name in CONTROL_COMMANDS.items():
            if cmd_bytes in data:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [LOG POS] Commande de contrôle reçue: {cmd_name} ({cmd_bytes.hex()})")
                # Retire le signal du buffer pour ne pas l'envoyer au KDS comme texte
                data = data.replace(cmd_bytes, b'')

        # 2. Accumulation et Transfert des données brutes
        
        if data:
            # Envoie la donnée brute (texte + commandes d'impression) au KDS Reader
            # Le KDS Reader se chargera de décoder et nettoyer le texte.
            try:
                self.kds_ser.write(data)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [TRANSFERT KDS] {len(data)} octets transférés.")
                
            except serial.SerialException as e:
                print(f"[ERREUR TRANSFERT] Impossible d'écrire sur le port KDS: {e}")

    def stop_emulator(self):
        """Arrête le thread de l'émulateur et ferme les ports."""
        print("Émulateur EPSON arrêté.")
        self._stop_event.set()
        if self.pos_ser and self.pos_ser.is_open:
            self.pos_ser.close()
        if self.kds_ser and self.kds_ser.is_open:
            self.kds_ser.close()

# --- Bloc d'Execution Principal ---
if __name__ == "__main__":
    
    print(f"Configuration: POS écoute sur {POS_LISTEN_PORT} / KDS écoute sur {KDS_FORWARD_PORT}")
    
    # 1. Initialisation de l'émulateur
    emulator = EpsonEmulator()
    
    # 2. Démarrage de l'émulateur dans un thread séparé
    if not emulator._stop_event.is_set():
        emulator.start()
    
    # 3. Le thread principal attend.
    try:
        while not emulator._stop_event.is_set():
            time.sleep(1)
            
    except KeyboardInterrupt:
        # Arrêt propre lorsque l'utilisateur appuie sur CTRL+C
        print("\nSignal d'interruption reçu. Arrêt du système...")
        emulator.stop_emulator()
        emulator.join() 
        print("Système d'émulation EPSON arrêté proprement.")