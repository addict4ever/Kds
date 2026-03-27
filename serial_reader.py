# serial_reader.py - Lecteur de port série KDS (FINAL: CONNEXION DB SQLite AVEC LOGGING COMPLET)

import time
import threading
import socket  # <--- AJOUTER CECI
from datetime import datetime
import logging
import re
from typing import Dict, Any, List # Import de List
import sys 
import json 
import random 
import os
from db_manager import DBManager # ⭐ IMPORTATION DE LA CLASSE DBManager
from db_maindish import MainDishDBManager

try:
    import serial
except ImportError:
    print("ERREUR: Le script nécessite 'pyserial' (pip install pyserial).")
    class serial:
        SerialException = Exception
        @staticmethod
        def Serial(port, baudrate, timeout, rtscts=False, dsrdtr=False):
            return type('MockSerial', (object,), {
                'write': lambda self, data: print(f"SIMULATION: Écriture de {len(data)} octets sur {port}"), 
                'is_open': True, 
                'close': lambda self: None, 
                'read': lambda self, size: b'', 
                'in_waiting': 0, 
                'open': lambda self: None, 
                'name': port,
                '__enter__': lambda self: self, 
                '__exit__': lambda self, *args: None
            })

CORRECTIONS_OCR = {
    "C-SARAR": "CÉSAR",
    "CSAR": "CÉSAR",
    "BURG": "BURGER"
}

SERIAL_PORT_TCP_1 = '0.0.0.0'  # Écoute sur toutes les interfaces réseau
SERIAL_PORT_TCP_1_PORT = 9100      # Port standard pour les imprimantes réseau

SERIAL_TCP_PRINTER_1 = '192.168.5.210'  # IP de l'imprimante cible
SERIAL_TCP_PRINTER_1_PORT = 9100        # Port de l'imprimante cible

SERIAL_TCP_COMPUTER_1 = '127.0.0.1'  # IP de l'imprimante cible
SERIAL_TCP_COMPUTER_PORT_1 = 9200        # Port de l'imprimante cible

MAX_TICKET_SIZE = 1048576

ESC_POS_STATUS_QUERIES = [b'\x10\x04\x01', b'\x10\x04\x02', b'\x10\x04\x03', b'\x10\x04\x04']
# Réponse standard "Prêt / Papier OK / Capot fermé"
ESC_POS_STATUS_READY = b'\x12'
TICKET_END_BINARY_SEQUENCE = b'\x1bd\t\x1bi' 

BUFFER_SIZE_TCP = 4096

# --- FONCTION DE LOGGING GLOBALE (GARDÉE EN HAUT POUR L'UTILISATION IMMÉDIATE) ---
def _log_activity(message: str, category: str = "INFO"):
    date_str = datetime.now().strftime('%Y%m%d')
    log_filename = f"kds_serial_log_{date_str}.txt"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] 
    log_message = f"[{timestamp}] [{category.upper()}] {message}\n"
    
    try:
        with open(log_filename, 'a', encoding='utf-8') as f:
            f.write(log_message)
    except Exception as e:
        print(f"[LOG_ERROR] Échec de l'écriture du log: {e} - Message original: {log_message.strip()}")


# --------------------------------------------------------------------------------
# ⭐ NOUVEAU: LOGIQUE DE CHARGEMENT DES PORTS SÉRIE DEPUIS JSON
# --------------------------------------------------------------------------------
def load_serial_ports_from_json(json_file='ports.json') -> Dict[str, str]:
    """Charge les ports série appropriés pour l'OS actuel depuis le fichier JSON."""
    
    IS_WINDOWS = os.name == 'nt'
    OS_KEY = 'windows_ports' if IS_WINDOWS else 'linux_ports'
    
    # Valeurs par défaut codées en dur (fallback) avec les nouveaux ports
    default_ports = {
        'SERIAL_PORT': 'COM8' if IS_WINDOWS else '/dev/ttyUSB0',
        'SERIAL_PORT_2': 'COM9' if IS_WINDOWS else '/dev/ttyUSB3',
        'SERIAL_PORT_3': 'COM11' if IS_WINDOWS else '/dev/ttyUSB5',
        'SERIAL_PORT_PRINTER': 'COM5' if IS_WINDOWS else '/dev/ttyUSB1',
        'SERIAL_PORT_PRINTER_2': 'COM10' if IS_WINDOWS else '/dev/ttyUSB4',
        'SERIAL_PORT_PRINTER_3': 'COM12' if IS_WINDOWS else '/dev/ttyUSB6',
        'SERIAL_PORT_COMPUTER': 'COM6' if IS_WINDOWS else '/dev/ttyUSB2'
    }

    try:
        if not os.path.exists(json_file):
             _log_activity(f"Fichier {json_file} absent. Utilisation des fallbacks.", "CONFIG_JSON_WARN")
             return default_ports

        with open(json_file, 'r', encoding='utf-8') as f:
            port_config = json.load(f)
        
        if OS_KEY in port_config:
            os_ports = port_config[OS_KEY]
            # On construit le dictionnaire en vérifiant chaque clé individuellement
            ports = {
                'SERIAL_PORT': os_ports.get('SERIAL_PORT', default_ports['SERIAL_PORT']),
                'SERIAL_PORT_2': os_ports.get('SERIAL_PORT_2', default_ports['SERIAL_PORT_2']),
                'SERIAL_PORT_3': os_ports.get('SERIAL_PORT_3', default_ports['SERIAL_PORT_3']),
                'SERIAL_PORT_PRINTER': os_ports.get('SERIAL_PORT_PRINTER', default_ports['SERIAL_PORT_PRINTER']),
                'SERIAL_PORT_PRINTER_2': os_ports.get('SERIAL_PORT_PRINTER_2', default_ports['SERIAL_PORT_PRINTER_2']),
                'SERIAL_PORT_PRINTER_3': os_ports.get('SERIAL_PORT_PRINTER_3', default_ports['SERIAL_PORT_PRINTER_3']),
                'SERIAL_PORT_COMPUTER': os_ports.get('SERIAL_PORT_COMPUTER', default_ports['SERIAL_PORT_COMPUTER'])
            }
            _log_activity(f"Ports chargés depuis {json_file} pour {OS_KEY}.", "CONFIG_JSON_OK")
            return ports

        _log_activity(f"Clé '{OS_KEY}' introuvable dans {json_file}. Valeurs par défaut utilisées.", "CONFIG_JSON_WARN")

    except (FileNotFoundError, json.JSONDecodeError) as e:
        _log_activity(f"Erreur de lecture/décodage de {json_file}: {e}. Valeurs par défaut utilisées.", "CONFIG_JSON_ERROR")
        
    return default_ports

def load_network_config_from_json(json_file='printer_ip.json') -> Dict[str, Any]:
    """Charge les configurations IP et Ports TCP depuis le fichier JSON."""
    
    # Valeurs par défaut (Fallback)
    default_config = {
        'SERIAL_PORT_TCP_1': '0.0.0.0',
        'SERIAL_PORT_TCP_1_PORT': 9100,
        'SERIAL_TCP_PRINTER_1': '192.168.5.210',
        'SERIAL_TCP_PRINTER_1_PORT': 9100,
        "SERIAL_TCP_COMPUTER_1": "127.0.0.1",
        "SERIAL_TCP_COMPUTER_PORT_1": 9200 
    }

    try:
        if not os.path.exists(json_file):
            return default_config

        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        tcp_section = data.get('tcp_config', {})
        
        # On extrait TOUTES les clés, incluant celles de l'ordinateur
        config = {
            'SERIAL_PORT_TCP_1': tcp_section.get('SERIAL_PORT_TCP_1', default_config['SERIAL_PORT_TCP_1']),
            'SERIAL_PORT_TCP_1_PORT': int(tcp_section.get('SERIAL_PORT_TCP_1_PORT', default_config['SERIAL_PORT_TCP_1_PORT'])),
            'SERIAL_TCP_PRINTER_1': tcp_section.get('SERIAL_TCP_PRINTER_1', default_config['SERIAL_TCP_PRINTER_1']),
            'SERIAL_TCP_PRINTER_1_PORT': int(tcp_section.get('SERIAL_TCP_PRINTER_1_PORT', default_config['SERIAL_TCP_PRINTER_1_PORT'])),
            # ⭐ AJOUT DES LIGNES CI-DESSOUS :
            'SERIAL_TCP_COMPUTER_1': tcp_section.get('SERIAL_TCP_COMPUTER_1', default_config['SERIAL_TCP_COMPUTER_1']),
            'SERIAL_TCP_COMPUTER_PORT_1': int(tcp_section.get('SERIAL_TCP_COMPUTER_PORT_1', default_config['SERIAL_TCP_COMPUTER_PORT_1']))
        }
        
        print(f"[OK] Configuration réseau complète chargée.")
        return config

    except Exception as e:
        print(f"[ERROR] Erreur config réseau: {e}")
        return default_config


# --- CONSTANTES MINIMALISTES (SANS LOGIQUE DE PORT) ---
class KDSConstants:
    """Contient les constantes KDS indépendantes de la configuration du port série."""

    # Détection du système d'exploitation
    IS_WINDOWS = os.name == 'nt'
    
    # Constantes indépendantes de l'OS
    BAUD_RATE = 9600
    SERIAL_TIMEOUT = 0.1
    TICKET_END_SEQUENCE = "\n--FIN--\n"
    
    ESC_POS_STATUS_PREFIX = b'\x10\x04\x01' 
    ESC_POS_STATUS_RESPONSE = b'\x12' 
    TICKET_END_BINARY_SEQUENCE = b'\x1bd\t\x1bi' 




SERIAL_PORT_TCP_1 = '0.0.0.0'      # Écoute sur toutes les interfaces réseau
SERIAL_PORT_TCP_1_PORT = 9100      # Port standard pour les imprimantes réseau
BUFFER_SIZE_TCP = 4096

# --------------------------------------------------------------------------------
# ⭐ DEFINITION DES VARIABLES GLOBALES (APPEL DIRECT AU JSON)
# --------------------------------------------------------------------------------
kds_constants = KDSConstants()


ports_config = load_serial_ports_from_json()
net_config = load_network_config_from_json('printer_ip.json')

# Définition des variables globales à partir du JSON et des constantes
SERIAL_PORT = ports_config['SERIAL_PORT']
SERIAL_PORT_2 = ports_config['SERIAL_PORT_2'] # <--- Nouveau
SERIAL_PORT_3 = ports_config['SERIAL_PORT_3'] # <--- Nouveau

SERIAL_PORT_PRINTER = ports_config['SERIAL_PORT_PRINTER']
SERIAL_PORT_PRINTER_2 = ports_config['SERIAL_PORT_PRINTER_2'] # <--- Nouveau
SERIAL_PORT_PRINTER_3 = ports_config['SERIAL_PORT_PRINTER_3'] # <--- Nouveau

SERIAL_TCP_COMPUTER_1 = net_config['SERIAL_TCP_COMPUTER_1']
SERIAL_TCP_COMPUTER_PORT_1 = net_config['SERIAL_TCP_COMPUTER_PORT_1']

SERIAL_PORT_COMPUTER = ports_config['SERIAL_PORT_COMPUTER']
BAUD_RATE = kds_constants.BAUD_RATE
SERIAL_TIMEOUT = kds_constants.SERIAL_TIMEOUT
TICKET_END_SEQUENCE = kds_constants.TICKET_END_SEQUENCE
ESC_POS_STATUS_PREFIX = kds_constants.ESC_POS_STATUS_PREFIX 
ESC_POS_STATUS_RESPONSE = kds_constants.ESC_POS_STATUS_RESPONSE 
TICKET_END_BINARY_SEQUENCE = kds_constants.TICKET_END_BINARY_SEQUENCE 


# --------------------------------------------------------------------------------
# ⭐ CONSTANTES POUR L'EXTRACTION (MODIFIÉES POUR UNE LOGIQUE STRICTE)
# Ces noms ne sont plus utilisés pour l'extraction stricte, mais sont conservés si besoin ailleurs.
MODIFIERS_NAMES = [
    'EXTRA POUTINE', 'GARNIE', 'PATE MINCE', 'PEPE', 
    'FROMAGE', 'PT. FRITES', 'PEU DE', 'SERVICE # '
]
# --------------------------------------------------------------------------------

# --- FONCTION DÉCODAGE ESC/POS ---
def _decode_escpos(data: str) -> str:
    """Tente de corriger les caractères mal encodés et les répétitions d'OCR."""
    fixes = {
        # Encodages standards
        '├ë': 'É', '├©': 'é', '├á': 'à', '├è': 'è', '├ê': 'ê',
        '├ô': 'ô', '├û': 'û', 'Ã©': 'é', 'Ã¨': 'è', 'Ã§': 'ç',
        'Ã': 'à', 
        
        # --- Zone CÉSAR ---
        'C-SARAR': 'CÉSAR',    # Le cas spécifique que vous avez vu
        'CÉSARAR': 'CÉSAR',    # Si l'accent est là mais que le AR est doublé
        'C\x90S': 'CÉSAR', 
        'C\x82S': 'CÉSAR',
        'SAL CÉS': 'SAL CÉSAR',
        
        # --- Autres corrections ---
        'PILEES': 'PILÉES', 
    }
    
    for bad, good in fixes.items():
        data = data.replace(bad, good)
    
    # Correction de sécurité pour les "AR" en trop en fin de mot
    # Remplace "CÉSARAR" par "CÉSAR" si jamais une autre variante apparaît
    data = data.replace('SARAR', 'SAR')
        
    return data


class TCPReader(threading.Thread):
    def __init__(self, serial_reader_instance, net_config):
        super().__init__()
        self.reader = serial_reader_instance
        self.net_config = net_config
        self._stop_event = threading.Event()
        # Initialisation du socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.settimeout(1.0)

    def _forward_to_tcp_printer(self, raw_bytes):
        """Redirige les octets vers l'imprimante IP réelle sauf si le filtre est activé."""
        
        # --- LOGIQUE DE FILTRE ---
        ticket_content = raw_bytes.decode('latin-1', errors='ignore').upper()
        
        if "ENLEVER LE PAPIER JAUNE" in ticket_content:
            _log_activity("FILTRE: 'ENLEVER LE PAPIER JAUNE' détecté. Impression physique bloquée, mais redirection PC maintenue.", "TCP_FILTER")
            return # Ici, le return arrête SEULEMENT l'envoi à l'imprimante IP
        
        # --- ENVOI PHYSIQUE (uniquement si le filtre n'a pas déclenché le return ci-dessus) ---
        printer_ip = self.net_config.get('SERIAL_TCP_PRINTER_1')
        printer_port = self.net_config.get('SERIAL_TCP_PRINTER_1_PORT')
        
        if not printer_ip:
            return

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as printer_sock:
                printer_sock.settimeout(2.0)
                printer_sock.connect((printer_ip, printer_port))
                printer_sock.sendall(raw_bytes)
                _log_activity(f"Redirection réussie vers {printer_ip}", "TCP_OUT")
        except Exception as e:
            _log_activity(f"Imprimante IP {printer_ip} hors ligne ou erreur: {e}", "TCP_OFFLINE")

    def run(self):
        host = self.net_config.get('SERIAL_PORT_TCP_1', '0.0.0.0')
        port = self.net_config.get('SERIAL_PORT_TCP_1_PORT', 9100)

        try:
            self.server_socket.bind((host, port))
            self.server_socket.listen(5)
            _log_activity(f"Serveur TCP prêt sur {host}:{port}", "TCP_START")
        except Exception as e:
            _log_activity(f"Erreur bind TCP: {e}", "TCP_ERROR")
            return

        while not self._stop_event.is_set():
            conn = None
            try:
                conn, addr = self.server_socket.accept()
                conn.settimeout(3.0)
                full_data = b""
                
                try:
                    while True:
                        data = conn.recv(4096)
                        if not data:
                            break
                        
                        if any(data.startswith(q) for q in ESC_POS_STATUS_QUERIES) or data == b'\x10\x04':
                            conn.sendall(ESC_POS_STATUS_READY)
                            continue

                        full_data += data
                        
                        if TICKET_END_BINARY_SEQUENCE in full_data:
                            break 
                            
                except socket.timeout:
                    pass 
                
                if full_data:
                    # 1. Redirection Imprimante IP (Physique)
                    self._forward_to_tcp_printer(full_data)

                    # 2. Décodage
                    ticket_text = full_data.decode('latin-1', errors='ignore')
                    
                    # 3. TRAITEMENT KDS (Base de données)
                    # On retire le log ici pour ne pas saturer l'écran
                    self.reader._process_ticket_line(ticket_text)
                    
                    # 4. Redirection vers l'ordinateur avec FILTRE
                    # Si on voit ADDITION ou SOUS-TOTAL, on n'envoie PAS à l'ordinateur
                    mots_bloques = ["ADDITION"]
                    if not any(mot in ticket_text.upper() for mot in mots_bloques):
                        try:
                            # Utilisation du port série de sortie
                            self.reader._write_to_output_port(ticket_text, SERIAL_PORT_COMPUTER, "Ordinateur")
                        except Exception:
                            # Silencieux en cas d'erreur de port pour ne pas bloquer
                            pass

            except Exception:
                pass
            finally:
                if conn:
                    conn.close()

    def stop_server(self):
        self._stop_event.set()
        try:
            self.server_socket.close()
        except:
            pass
            
# --- PARTIE 2 : La Classe SerialReader ---
class SerialReader(threading.Thread):
    
    
    

    def __init__(self, db_manager, print_forwarding_state=None):
        super().__init__()
        self.db_manager = db_manager 
        self._stop_event = threading.Event()
        
        # --- 1. INITIALISATION DES LOCKS ---
        # Lock pour l'accès aux ports de sortie (Ordinateur/Imprimante)
        if not hasattr(SerialReader, '_print_lock'):
            SerialReader._print_lock = threading.Lock()
        self.output_lock = threading.Lock() 

        # --- 2. CONFIGURATION DES PORTS KDS ---
        self.ports_config = {
            1: {"port": SERIAL_PORT,   "attr": "serial_port",   "buffer": "input_buffer"},
            2: {"port": SERIAL_PORT_2, "attr": "serial_port_2", "buffer": "input_buffer_2"},
            3: {"port": SERIAL_PORT_3, "attr": "serial_port_3", "buffer": "input_buffer_3"}
        }

        # Initialisation par défaut des attributs et buffers
        for cfg in self.ports_config.values():
            setattr(self, cfg["attr"], None)
            setattr(self, cfg["buffer"], b'')

        # --- 3. BASE DE DONNÉES & ÉTAT ---
        self.main_dish_db_manager = MainDishDBManager()
        self.MAIN_DISHES_FOR_NEW_GROUP = self.main_dish_db_manager.load_all_dishes()
        
        # ⭐ CORRECTION DU BUG : Ajout de 'self' dans le lambda
        if print_forwarding_state is None:
            # On utilise une petite classe pour être 100% sûr de la compatibilité
            class MockBooleanVar:
                def get(self): return True
            self.print_forwarding_enabled_var = MockBooleanVar()
        else:
            self.print_forwarding_enabled_var = print_forwarding_state

        # --- 4. OUVERTURE AUTOMATISÉE DES PORTS ---
        for i, cfg in self.ports_config.items():
            if not cfg["port"]: continue
            try:
                conn = serial.Serial(
                    port=cfg["port"], 
                    baudrate=BAUD_RATE, 
                    timeout=SERIAL_TIMEOUT, 
                    rtscts=True, 
                    dsrdtr=True
                )
                setattr(self, cfg["attr"], conn)
                _log_activity(f"Port KDS {i} ({cfg['port']}) OUVERT.", "PORT_KDS_OK")
            except Exception as e:
                _log_activity(f"Erreur Port KDS {i} ({cfg['port']}): {e}", "PORT_KDS_ERROR")
    

    def _async_process_ticket(self, ticket_bytes, source_name, is_print_enabled):
        """Traitement asynchrone sécurisé pour l'impression du Service 1 et 2."""
        try:
            raw_ticket_data = ticket_bytes.decode('latin-1', errors='ignore') 
            
            # A. Enregistrement en base de données
            self._process_ticket_line(raw_ticket_data) 
            
            # B. Redirection vers l'imprimante (utilise la valeur passée à l'ouverture du thread)
            if is_print_enabled:
                # Ajout d'un petit log pour confirmer l'envoi
                _log_activity(f"Impression automatique : {source_name}", "PRINT_OK")
                self._forward_ticket_data(raw_ticket_data, source_name)
                
        except Exception as e:
            _log_activity(f"Erreur thread (Source: {source_name}): {e}", "THREAD_ERROR")
    
    @staticmethod
    def _write_to_output_port_print(data_to_print: str, port: str, port_name: str) -> bool:
        """Écrit les données sur un port de sortie avec nettoyage du texte uniquement."""

        import string

        def clean_print_text(text: str) -> str:
            # On ne nettoie QUE le texte brut ici
            lines = text.splitlines()
            seen_table = False
            seen_time = False
            clean_lines = []
            
            # On garde les caractères imprimables + les retours à la ligne
            printable = set(string.printable)

            for raw_line in lines:
                stripped = raw_line.strip()

                # Suppression des doublons
                if "Table:" in stripped:
                    if seen_table: continue
                    seen_table = True
                if "Heure:" in stripped:
                    if seen_time: continue
                    seen_time = True

                # Nettoyage des caractères bizarres du texte (remplace par espace au lieu de tiret)
                cleaned_line = ''.join(c if c in printable else ' ' for c in raw_line)
                clean_lines.append(cleaned_line)

            return "\n".join(clean_lines)

        # 1. On nettoie le texte
        data_to_print = clean_print_text(data_to_print)
        
        _log_activity(f"Tentative d'ouverture du port {port_name} {port}.", f"PORT_{port_name.upper()}_OUT")
        
        try:
            with serial.Serial(port, BAUD_RATE, timeout=1) as output_port:
                # 2. On prépare les commandes BINAIRES (ne JAMAIS nettoyer ces octets)
                ESC = b'\x1b' 
                GS = b'\x1d'
                
                # Réinitialisation + Police A + Gras
                COMMAND_INIT = ESC + b'@' 
                COMMAND_BIG_FONT = ESC + b'!' + b'\x19' # Double hauteur + Double largeur + Gras
                
                # Encodage du texte nettoyé
                encoded_body = data_to_print.encode('latin-1', errors='replace')

                # 3. Assemblage final
                # On met les commandes binaires AUTOUR du texte nettoyé
                final_data = (
                    COMMAND_INIT +
                    COMMAND_BIG_FONT +
                    b'\n' + 
                    encoded_body +
                    b'\n\n\n\n' +
                    GS + b'V' + b'\x00'  # Coupe papier (Commande GS V 0)
                )

                output_port.write(final_data)
                time.sleep(0.5)

                _log_activity(f"Ticket envoyé à {port_name} ({port}).", "DATA_SENT")
                return True

        except Exception as e:
            _log_activity(f"Erreur impression sur {port}: {e}", "PRINT_ERROR")
            return False


    @staticmethod
    def _write_to_output_port(data_to_print: str, port, port_name: str, is_printing_enabled=True) -> bool:
        """
        Écrit le texte brut sur le port série avec protection par Lock et gestion de Retry.
        Version optimisée pour éviter les collisions et les erreurs d'accès refusé.
        """
        # 1. Extraction de la valeur (gestion si c'est une BooleanVar ou un bool)
        actual_enabled = is_printing_enabled.get() if hasattr(is_printing_enabled, 'get') else is_printing_enabled

        if not actual_enabled:
            _log_activity(f"ACTION ANNULÉE : Envoi vers {port_name} désactivé.", f"SKIP_{port_name.upper()}")
            return True

        if "ENLEVER LE PAPIER JAUNE" in data_to_print.upper():
            return True

        # 2. Préparation des données pour le log
        content_for_log = data_to_print.replace('\n', ' [LINE_BREAK] ')
        _log_activity(f"PRÉPARATION ENVOI À {port_name.upper()}: {content_for_log}", "PRINT_PREPARE")

        # 3. Paramètres de Retry
        max_retries = 3
        retry_delay = 0.5  # Attendre 500ms entre chaque essai

        # ⭐ Utilisation du LOCK : un seul thread à la fois accède à la partie série
        with SerialReader._print_lock:
            for attempt in range(max_retries):
                output_port = None
                try:
                    # Gestion de la connexion
                    is_new_connection = isinstance(port, str)
                    if is_new_connection:
                        # On tente d'ouvrir le port
                        output_port = serial.Serial(port, 9600, timeout=1)
                    else:
                        output_port = port

                    # Construction des données : Juste Initialisation (ESC @) + Texte
                    ESC = b'\x1b'
                    encoded_data = data_to_print.encode('latin-1', errors='replace')
                    final_data = ESC + b'@' + encoded_data
                    
                    # Écriture et purge du buffer
                    output_port.write(final_data)
                    output_port.flush()
                    
                    # Si c'était une nouvelle connexion, on attend un peu et on ferme
                    if is_new_connection:
                        time.sleep(0.3) 
                        output_port.close()

                    _log_activity(f"Transmission réussie vers {port_name} à l'essai {attempt + 1}.", "DATA_SENT")
                    return True # Succès !

                except Exception as e:
                    _log_activity(f"Échec essai {attempt + 1}/{max_retries} sur {port_name}: {e}", "RETRY_WARNING")
                    
                    # Fermeture sécurisée en cas d'erreur
                    if output_port and hasattr(output_port, 'close'):
                        try: output_port.close()
                        except: pass
                    
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay) # Pause avant le prochain essai
                    else:
                        _log_activity(f"ERREUR DÉFINITIVE sur {port_name} après {max_retries} essais.", "SERIAL_ERROR")
                        return False

        return False

    @staticmethod
    def reprint_ticket_to_printer(ticket_content: str, port_target: str) -> bool:
        """
        Réimpression avec récupération TCP depuis le JSON et gestion d'encodage sécurisée.
        """
        _log_activity(f"RÉIMPRESSION sur : {port_target}", "REPRINT_REQUEST")
        
        # --- 1. PRÉPARATION DU CONTENU ---
        ESC = '\x1b'
        GS = '\x1d'
        CMD_BOLD_ON = f'{ESC}{chr(69)}{chr(1)}' 
        CMD_RESET_ALL = f'{ESC}@' 
        header_text = f"REIMPRESSION ({datetime.now().strftime('%H:%M:%S')})\n"
        
        full_content = CMD_RESET_ALL + CMD_BOLD_ON + header_text + CMD_RESET_ALL + "\n"
        full_content += ticket_content + '\n\n' 

        # --- 2. ROUTAGE ---
        if port_target == SERIAL_PORT_PRINTER_3:
            try:
                # Valeurs par défaut
                target_ip = "16.16.16.100" 
                target_port = 9200
                
                config_file = "printer_ip.json"
                if os.path.exists(config_file):
                    with open(config_file, "r") as f:
                        data = json.load(f)
                        tcp_cfg = data.get("tcp_config", {})
                        target_ip = tcp_cfg.get("SERIAL_TCP_PRINTER_1", target_ip)
                        target_port = int(tcp_cfg.get("SERIAL_TCP_PRINTER_1_PORT", target_port))

                _log_activity(f"Réimpression TCP -> Connexion à {target_ip}:{target_port}", "REPRINT_TCP")

                # --- SÉCURISATION DE L'ENCODAGE ---
                # On encode en 'latin-1' mais on remplace les caractères impossibles (comme →) par '?'
                # ou on peut essayer 'cp850' qui est souvent le standard des imprimantes ESC/POS
                try:
                    raw_data = full_content.encode('latin-1', errors='replace')
                except:
                    raw_data = full_content.encode('ascii', errors='replace')

                # Envoi direct par Socket
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(5)
                    s.connect((target_ip, target_port))
                    s.sendall(raw_data) # On envoie les données déjà encodées
                
                _log_activity("Réimpression TCP réussie.", "REPRINT_SUCCESS")
                return True

            except Exception as e:
                _log_activity(f"ÉCHEC Réimpression TCP sur Port 3: {e}", "REPRINT_ERROR")
                return False
        
        else:
            # Pour le port série, on utilise la même logique de sécurité d'encodage si nécessaire
            return SerialReader._write_to_output_port_print(full_content, port_target, "Imprimante (Reprint)")

    def _send_to_computer_tcp(self, raw_ticket_data: str):
        """
        Envoie une copie du ticket via TCP à l'ordinateur cible.
        Utilise strictement SERIAL_TCP_COMPUTER_1 et SERIAL_TCP_COMPUTER_PORT_1.
        """
        try:
            # Encodage pour l'envoi réseau
            encoded_data = raw_ticket_data.encode('latin-1', errors='replace')
            
            # Connexion directe à l'IP définie
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.5)  # Timeout pour ne pas bloquer si l'IP est injoignable
                s.connect((SERIAL_TCP_COMPUTER_1, SERIAL_TCP_COMPUTER_PORT_1))
                s.sendall(encoded_data)
                
                # Ajout de la séquence de fin si absente
                if TICKET_END_BINARY_SEQUENCE not in encoded_data:
                    s.sendall(TICKET_END_BINARY_SEQUENCE)
                    
            _log_activity(f"Copie TCP envoyée à {SERIAL_TCP_COMPUTER_1}:{SERIAL_TCP_COMPUTER_PORT_1}", "TCP_SYNC_OK")
        except Exception as e:
            # Erreur silencieuse pour le flux principal : on logue et on continue
            _log_activity(f"TCP non disponible ({SERIAL_TCP_COMPUTER_1}) : {e}", "TCP_SYNC_SKIP")
            pass

    def _forward_ticket_data(self, raw_ticket_data: str, source_port: str):
        # On vérifie si c'est une addition pour le blocage PC
        est_une_addition = "ADDITION" in raw_ticket_data.upper()

        # ⭐ ÉTAPE 1 : ENVOI À L'ORDINATEUR (Sans lock)
        if not est_une_addition:
            try:
                # A. Envoi via le Port Série (COM)
                SerialReader._write_to_output_port(
                    raw_ticket_data,
                    SERIAL_PORT_COMPUTER,
                    "Ordinateur"
                )

                # B. Envoi via le Réseau (TCP 9200)
                self._send_to_computer_tcp(raw_ticket_data)
                
                # Petit délai de 100ms pour laisser le matériel respirer
                time.sleep(0.1)
            except Exception as e:
                _log_activity(f"Erreur sur port ordinateur : {e}", "SERIAL_ERROR")
        else:
            # On ignore l'envoi PC pour les additions, mais on continue vers l'imprimante
            pass

        # ⭐ ÉTAPE 2 : LOGIQUE DE VÉRIFICATION DU FICHIER JSON POUR L'IMPRESSION
        file_path = 'imprimante_var.json'
        should_print = True

        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    should_print = data.get("print_enabled", True)
        except Exception as e:
            _log_activity(f"Erreur lecture JSON imprimante_var : {e}", "CONFIG_ERROR")
            should_print = True

        # ⭐ ÉTAPE 3 : ROUTAGE VERS LES IMPRIMANTES PHYSIQUES (Conditionnel)
        if should_print:
            # Cas A : Le ticket vient du premier KDS
            if source_port == SERIAL_PORT:
                SerialReader._write_to_output_port(
                    raw_ticket_data,
                    SERIAL_PORT_PRINTER,
                    "Imprimante 1"
                )
            
            # Cas B : Le ticket vient du deuxième KDS
            elif source_port == SERIAL_PORT_2:
                SerialReader._write_to_output_port(
                    raw_ticket_data,
                    SERIAL_PORT_PRINTER_2,
                    "Imprimante 2"
                )
                
            # Cas C : Le ticket vient du troisième KDS (Réseau)
            elif source_port == SERIAL_PORT_3:
                _log_activity(f"Routage KDS 3 ({source_port}) vers Imprimante TCP", "ROUTE_TCP")
                self._send_to_network_printer(raw_ticket_data)
    
    
    def _handle_input_buffer_generic(self, port_number: int):
        # 1. MAPPING DYNAMIQUE (Évite les répétitions IF/ELIF)
        mapping = {
            1: (self.serial_port, "input_buffer", SERIAL_PORT),
            2: (self.serial_port_2, "input_buffer_2", SERIAL_PORT_2),
            3: (self.serial_port_3, "input_buffer_3", SERIAL_PORT_3)
        }
        
        if port_number not in mapping: return
        
        serial_conn, buffer_attr, source_name = mapping[port_number]
        if not serial_conn: return
        
        # On récupère le contenu actuel du buffer
        current_buffer = getattr(self, buffer_attr)

        # 2. TRAITEMENT DU STATUT ESC/POS (Réponse immédiate)
        if current_buffer.startswith(ESC_POS_STATUS_PREFIX) and len(current_buffer) >= 3:
            try:
                serial_conn.write(ESC_POS_STATUS_RESPONSE)
                # Mise à jour dynamique du buffer (on enlève les 3 octets de statut)
                setattr(self, buffer_attr, current_buffer[3:])
                _log_activity(f"Réponse Statut ESC/POS envoyée sur Port {port_number}", "SERIAL_STATUS")
            except Exception as e:
                _log_activity(f"Erreur réponse statut Port {port_number}: {e}", "SERIAL_ERR")
            return 

        # 3. TRAITEMENT DES TICKETS
        if TICKET_END_BINARY_SEQUENCE in current_buffer:
            # On découpe le buffer
            transactions_bytes = current_buffer.split(TICKET_END_BINARY_SEQUENCE)
            
            # Le résidu (ce qui n'est pas encore un ticket complet)
            residu = transactions_bytes[-1]
            tickets_to_process = transactions_bytes[:-1]

            # NETTOYAGE IMMÉDIAT DU BUFFER (Attribution dynamique)
            setattr(self, buffer_attr, residu)

            # RÉCUPÉRATION DE L'ÉTAT DU BOUTON (Thread-Safe)
            is_print_enabled = self.print_forwarding_enabled_var.get() if hasattr(self, 'print_forwarding_enabled_var') else False

            for raw_ticket_bytes in tickets_to_process:
                if len(raw_ticket_bytes) < 5: continue
                
                # Reconstruction du ticket avec sa séquence de fin
                full_bytes = raw_ticket_bytes + TICKET_END_BINARY_SEQUENCE
                
                # Lancement du traitement asynchrone
                t = threading.Thread(
                    target=self._async_process_ticket, 
                    args=(full_bytes, str(source_name), is_print_enabled)
                )
                t.daemon = True
                t.start()
                
            _log_activity(f"{len(tickets_to_process)} ticket(s) extraits du Port {port_number}", "BUFFER_PARSE")

    
    def run(self):
        """Boucle principale de lecture pour les 3 ports KDS (Version Sécurisée)."""
        _log_activity("Démarrage de la lecture sur les ports KDS...", "THREAD_START")

        # 1. Préparation de la structure des ports à surveiller
        kds_ports = [
            {"id": 1, "obj_attr": "serial_port",   "buf_attr": "input_buffer",   "name": SERIAL_PORT},
            {"id": 2, "obj_attr": "serial_port_2", "buf_attr": "input_buffer_2", "name": SERIAL_PORT_2},
            {"id": 3, "obj_attr": "serial_port_3", "buf_attr": "input_buffer_3", "name": SERIAL_PORT_3},
        ]

        # 2. On filtre pour ne garder que ceux qui ont été initialisés au départ
        active_ports = [p for p in kds_ports if getattr(self, p["obj_attr"]) is not None]
        
        if not active_ports:
            _log_activity("Aucun port série KDS disponible. Arrêt du thread.", "FATAL")
            return

        # 3. Boucle principale
        while not self._stop_event.is_set():
            for p in active_ports:
                
                # ⭐ SÉCURITÉ : Si on demande l'arrêt pendant qu'on boucle sur les 3 ports, on sort direct
                if self._stop_event.is_set():
                    break

                # On récupère l'objet port actuel
                port_obj = getattr(self, p["obj_attr"])
                
                # ⭐ SÉCURITÉ : On vérifie si stop_reader n'a pas mis le port à None
                if port_obj is None or not port_obj.is_open:
                    continue

                try:
                    # On vérifie s'il y a des données en attente
                    if port_obj.in_waiting > 0:
                        # Lecture de toutes les données disponibles
                        data = port_obj.read(port_obj.in_waiting)
                        
                        if data:
                            # Récupération et mise à jour du buffer spécifique
                            current_buf = getattr(self, p["buf_attr"])
                            setattr(self, p["buf_attr"], current_buf + data)
                            
                            _log_activity(f"Données reçues sur KDS {p['id']} ({p['name']}): {len(data)} octets", "DATA_RECV")
                            
                            # Appel du traitement du buffer (découpage par ticket)
                            self._handle_input_buffer_generic(p["id"])
                            
                except Exception as e:
                    # Si une erreur survient (ex: adaptateur débranché), on logge mais on continue pour les autres ports
                    _log_activity(f"Erreur de lecture sur Port {p['id']}: {e}", "SERIAL_ERR")
            
            # Temps de pause court (0.05s à 0.1s)
            # Permet de regrouper les paquets de données tout en restant réactif à la fermeture
            time.sleep(0.05)

        _log_activity("Boucle de lecture KDS arrêtée proprement.", "THREAD_STOP")

    # --------------------------------------------------------------------------------
    # ⭐ CORRECTION FINALE: Extraction structurée des items (Logique basée sur le texte nettoyé)
    # --------------------------------------------------------------------------------
    def _extract_items(self, ticket_data: str) -> List[str]:
        """
        Extrait et groupe les items principaux avec leurs sous-items/modificateurs
        à partir du texte nettoyé.
        """
        
        # 1. Isole la zone des items
        try:
            # On cherche après 'TABLE # [Nombre]'
            table_zone_match = re.search(r'(TABLE # \d+)(.*)', ticket_data, re.DOTALL)
            if table_zone_match:
                # La zone des items commence juste après la ligne de la table et se termine avant '###'
                items_zone = table_zone_match.group(2).split('###############################')[0].strip()
            else:
                # Fallback si 'TABLE #' n'est pas trouvé
                items_zone = ticket_data.split('###############################')[0].strip()
        except IndexError:
                items_zone = ticket_data.strip()

        # Nettoyage initial : retire les lignes vides
        raw_lines = [line.strip() for line in items_zone.split('\n') if line.strip()]
        
        # ⭐ Étape 1.5 : Suppression des métadonnées résiduelles
        raw_lines = [
            line for line in raw_lines 
            if not (
                'PRINCIPALE' in line.upper() or 
                'CLIENT' in line.upper() or 
                'TABLE #' in line.upper() or
                line.upper().startswith('HEURE:') or
                re.match(r'^\d{2}-\d{2}-\d{4}', line) # Date
            )
        ]
        
        # 2. Groupement des items
        grouped_items: List[Dict[str, Any]] = []
        current_main_item_dict: Dict[str, Any] | None = None
        
        # Récupération de la liste des plats principaux
        main_dishes_list = self.MAIN_DISHES_FOR_NEW_GROUP 
        
        for raw_item in raw_lines:
            # Tente d'extraire la quantité et le nom
            match = re.match(r'^\s*(\d+)\s+(.*)', raw_item)
            if not match:
                # Si la ligne n'a pas de quantité, c'est probablement un modificateur sans quantité affichée
                item_name = raw_item.strip().upper()
                is_main_item_candidate = False
            else:
                item_name = match.group(2).strip().upper()
                
                # Vérification si le nom de l'item contient un mot-clé de plat principal
                # ✅ CORRECTION APPLIQUÉE : keyword[0] extrait le nom du plat (chaîne) du tuple.
                is_main_item_candidate = any(keyword[0] in item_name for keyword in main_dishes_list)
                
            
            # Logique de Groupement
            
            # 1. C'est un Main Item SI: 
            #    a) C'est le tout premier item détecté, OU
            #    b) C'est un plat identifié comme "Main Dish" et il y a déjà un groupe actif.
            
            if current_main_item_dict is None or is_main_item_candidate:
                # Fermer le groupe précédent (si existant) si on commence un NOUVEAU plat principal
                if current_main_item_dict is not None and is_main_item_candidate:
                    pass 

                # Commencer un nouveau groupe
                item_dict = {'main_item': raw_item, 'sub_items': []}
                grouped_items.append(item_dict)
                current_main_item_dict = item_dict 

            # 2. C'est un Sous-Item SI: 
            #    Ce n'est PAS un nouveau Main Item CANDIDAT et un groupe parent est actif.
            elif current_main_item_dict is not None and not is_main_item_candidate:
                current_main_item_dict['sub_items'].append(raw_item)
                
                
        # 3. Transformation en liste de chaînes JSON
        final_list = [json.dumps(item, ensure_ascii=False) for item in grouped_items]
        return final_list

    # --------------------------------------------------------------------------------

    def _process_ticket_line(self, raw_ticket_data: str):
        """
        Décode le ticket. 
        Salle : Extrait le nom de la serveuse.
        Livraison : Table = No Livraison, Serveuse = Téléphone + Adresse.
        """
        try:
            _log_activity("Début du traitement du ticket.", "PROCESS_START")

            # --- 1️⃣ NETTOYAGE DU CONTENU ---
            # --- NETTOYAGE RENFORCÉ ET CIBLÉ ---
            # --- 1️⃣ NETTOYAGE DU CONTENU ---
            cleaned_text = raw_ticket_data
            cleaned_text = re.sub(r'\x1b[@!rda-zA-Z0-9]{1,3}', ' ', cleaned_text)
            cleaned_text = re.sub(r'[\x00-\x09\x0b-\x1f\x7f]', ' ', cleaned_text) 
            cleaned_text = re.sub(r'[ \t\r\f\v]+', ' ', cleaned_text)
            cleaned_text = _decode_escpos(cleaned_text).strip() 
            cleaned_text = cleaned_text.replace('\xa0', ' ')
            cleaned_text = re.sub(r' *\n *', '\n', cleaned_text).strip()
            
            upper_text = cleaned_text.upper()
            lines = cleaned_text.split('\n')

            # --- 2️⃣ DÉTECTION DU TYPE ---
            is_livraison = "LIVRAISON" in upper_text

            # --- 3️⃣ FILTRAGE : IGNORER LES ADDITIONS (SAUF SI LIVRAISON) ---
            if ("ADDITION" in upper_text or "COPIE DU COMMERCANT" in upper_text) and not is_livraison:
                _log_activity("Addition standard ignorée.", "SKIP")
                return 

            # --- 4️⃣ EXTRACTION DES DONNÉES ---
            server_name = "INCONNU"
            table_number = 999
            service_type = "COMMANDE"

            if is_livraison:
                tel_livr = ""
                found_table_id = "777" # Valeur par défaut si rien n'est trouvé

                # A. Extraire le numéro de table (ex: 304) pour le format petit
                table_match = re.search(r'TABLE\s*#?\s*(\d+)', upper_text)
                if table_match:
                    found_table_id = table_match.group(1)

                # B. Extraire le téléphone pour déterminer le format
                for l in lines[:15]:
                    l_strip = l.strip()
                    # Cherche un format 4183338092 ou 418 333 8092
                    tel_match = re.search(r'(\d{3}\s*\d{3}\s*\d{4})', l_strip)
                    if tel_match:
                        tel_livr = tel_match.group(1).replace(" ", "")
                        break 
                
                # C. DÉCISION DES NUMÉROS ET DU TYPE DE SERVICE
                if tel_livr:
                    # FORMAT LONG (Avec téléphone) -> Livraison standard
                    service_type = "LIVREUR"
                    table_number = found_table_id if table_match else "999"
                    server_name = tel_livr  
                else:
                    # FORMAT PETIT (Sans téléphone) -> Utilise le numéro de table extrait
                    service_type = "LIVRAISON"
                    table_number = "LIV"
                    server_name = found_table_id # Remplace le 777 par le numéro de table (ex: 304)

                

            else:
                # --- LOGIQUE ORIGINALE POUR COMMANDE EN SALLE ---
                # Extraction du nom de la serveuse
                for i, line in enumerate(lines):
                    if any(x in line.upper() for x in ["CLIENTS", "CLIENT", "PAR :", "SERVI PAR"]):
                        for j in range(1, 3):
                            if i + j < len(lines):
                                potential = lines[i + j].strip().upper()
                                if potential and "TABLE #" not in potential and len(potential) > 1:
                                    server_name = potential
                                    break
                        if server_name != "INCONNU": break
                
                # Extraction du numéro de table
                table_match = re.search(r'TABLE\s*#?\s*(\d+)', upper_text)
                table_number = int(table_match.group(1)) if table_match else 999

                # Gestion Emporter
                if "POUR EMPORTER" in upper_text or "EMPORTER" in upper_text:
                    service_type = "POUR EMPORTER"
                    table_number = "PA"  # On force le numéro 888 pour les PA
                    server_name = "888"

            # --- 5️⃣ IDS ET ITEMS ---
            # On cherche le numéro de facture ou d'addition
            bill_match = re.search(r'(?:FACTURE|ADDITION)\s*#?\s*([\d-]+)', upper_text)
            bill_id = bill_match.group(1) if bill_match else datetime.now().strftime('%H%M%S')

            items_list_json_str = self._extract_items(cleaned_text)
            if not items_list_json_str:
                items_list_json_str = [json.dumps({"main_item": "VOIR TICKET PHYSIQUE", "sub_items": []})]

            # --- 6️⃣ INSERTION DB ---
            try:
                self.db_manager.add_new_order(
                    bill_id=bill_id,
                    table_number=table_number,   # No Livraison ou No Table
                    serveuse_name=server_name,   # Tel + Adresse ou Nom Serveuse
                    service_type=service_type,
                    items=items_list_json_str,
                    status='En attente'
                )
                _log_activity(f"Succès: {service_type} ajouté. Table/Livr: {table_number}, Info: {server_name}")
            except Exception as db_e:
                _log_activity(f"Erreur DB: {db_e}", "DB_ERROR")

        except Exception as e:
            _log_activity(f"Erreur fatale: {e}", "PROCESS_FATAL")

    def stop_reader(self):
        """Arrête les lecteurs série KDS en mode FORCÉ pour éviter tout gel."""
        _log_activity("DÉBUT DE LA FERMETURE DES SERVICES KDS...", "SHUTDOWN_URGENT")
        
        # 1. Signaler l'arrêt au thread 'run' immédiatement
        self._stop_event.set()

        # 2. Laisser une micro-chance au thread de finir proprement (0.1s)
        if self.is_alive():
            self.join(timeout=0.1)

        # 3. Liste des ports à traiter (Mise en correspondance attribut <-> Label)
        ports_to_kill = [
            ('serial_port', "1"),
            ('serial_port_2', "2"),
            ('serial_port_3', "3")
        ]

        for attr_name, label in ports_to_kill:
            # On récupère l'objet port actuel
            port_obj = getattr(self, attr_name, None)
            
            if port_obj:
                try:
                    _log_activity(f"Libération forcée du Port {label}...", "SHUTDOWN_FORCE")
                    
                    # ⭐ ÉTAPE 1 : On coupe le lien avec la classe immédiatement.
                    # Ton thread 'run' verra 'None' et sortira de sa boucle pour ce port.
                    setattr(self, attr_name, None)
                    
                    # ⭐ ÉTAPE 2 : On force le déblocage au niveau du driver
                    if port_obj.is_open:
                        try:
                            # Débloque les appels .read() en attente
                            port_obj.cancel_read()
                            port_obj.cancel_write()
                        except: 
                            pass # Le driver peut ne pas supporter cancel_read si déjà crashé
                        
                        # Vide les buffers pour éviter les données fantômes
                        port_obj.reset_input_buffer()
                        
                        # Fermeture physique
                        port_obj.close()
                    
                    _log_activity(f"Port {label} fermé et ressources libérées.", "PORT_KDS")
                
                except Exception as e:
                    _log_activity(f"Erreur lors du forçage Port {label}: {e}", "SHUTDOWN_ERROR")

        # 4. Nettoyage final du thread principal
        if self.is_alive():
            # Si le thread est encore là, on ne l'attend plus
            _log_activity("Thread de lecture forcé à l'abandon.", "SHUTDOWN_WARN")

        _log_activity("Services série KDS totalement arrêtés.", "SHUTDOWN_DONE")
        
# --- PARTIE 3 : Bloc d'Execution Principal (VERSION PRODUCTION) ---
if __name__ == "__main__":
    
    # 1. Initialisation du gestionnaire de base de données
    try:
        manager = DBManager()
        _log_activity("Base de données connectée.", "DB_READY")
    except Exception as e:
        print(f"ERREUR CRITIQUE DB: {e}")
        sys.exit(1)

    # 2. Initialisation du SerialReader
    # Le constructeur tente d'ouvrir les 3 ports définis (SERIAL_PORT, _2, _3)
    reader = SerialReader(manager)
    
    # 3. Vérification de la disponibilité multi-ports
    # On crée la liste des ports pour vérifier si au moins un est ouvert
    active_ports_list = []
    if reader.serial_port: active_ports_list.append(SERIAL_PORT)
    if reader.serial_port_2: active_ports_list.append(SERIAL_PORT_2)
    if reader.serial_port_3: active_ports_list.append(SERIAL_PORT_3)

    if not any([reader.serial_port, reader.serial_port_2, reader.serial_port_3]):
        _log_activity("ERREUR FATALE: Aucun port KDS n'est disponible. Vérifiez les branchements.", "FATAL_EXIT")
        reader.stop_reader()
        sys.exit(1) 
    
    # 4. Démarrage du système
    try:
        _log_activity(f"Démarrage sur ports: {', '.join(active_ports_list)}", "SYSTEM_START")
        reader.start()
        
        _log_activity("Système KDS en ligne. Surveillance active (CTRL+C pour quitter).", "SYSTEM_READY")

        # Boucle de surveillance principale
        while not reader._stop_event.is_set():
            # Une pause de 0.5s est idéale pour ne pas consommer de CPU
            time.sleep(0.5)
                
    except KeyboardInterrupt:
        _log_activity("Signal d'arrêt manuel reçu (KeyboardInterrupt).", "SHUTDOWN_SIGNAL")
        
    except Exception as e:
        _log_activity(f"ERREUR SYSTÈME INATTENDUE: {e}", "SYSTEM_CRASH")
        
    finally:
        # ⭐ SÉCURITÉ ABSOLUE :
        # On exécute stop_reader() qui utilise cancel_read() pour éviter tout gel
        print("\n[INFO] Fermeture des ports série et arrêt des services...")
        reader.stop_reader()
        
    print("Le système KDS est maintenant éteint proprement.")
    sys.exit(0)