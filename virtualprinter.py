import socket
import serial
import threading
import time
import queue
import sys
import os
import subprocess

# ============================================================
# CONFIGURATION
# ============================================================

if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

COM_PORT = "COM7"

BAUDRATE = 9600
BYTESIZE = serial.EIGHTBITS
PARITY = serial.PARITY_NONE
STOPBITS = serial.STOPBITS_ONE

TCP_HOST = "192.168.5.201"
TCP_PORT = 9200

TCP_TIMEOUT = 5
DEBUG = True

# Séquence de fin de ticket ESC/POS standard
TICKET_END_BINARY_SEQUENCE = b'\x1bd\t\x1bi'

# Configuration du Watchdog (Délai d'inactivité max avant reboot forcé)
WATCHDOG_TIMEOUT = 10

# ============================================================
# ÉTAT IMPRIMANTE, QUEUE & WATCHDOG
# ============================================================

running = True
ser = None
print_queue = queue.Queue()
last_heartbeat = time.time()


def touch_watchdog():
    """Signale au Watchdog interne que le programme est actif."""
    global last_heartbeat
    last_heartbeat = time.time()


# ============================================================
# LOG
# ============================================================

def log(prefix, data):
    if not DEBUG:
        return
    if isinstance(data, bytes):
        try:
            text_repr = data.decode('latin-1', errors='replace')
        except Exception:
            text_repr = str(data)
            
        print(f"{prefix} [HEX] : {data.hex(' ').upper()}")
        print(f"{prefix} [TEXT]: {repr(text_repr)}")
    else:
        print(f"{prefix}: {data}")


# ============================================================
# FILTRAGE ET RÉPONSE ESC/POS ULTRA-ROBUSTE (TOUS STATUTS POS)
# ============================================================

def process_and_clean_escpos(data):
    """
    Intercepte et répond à l'ensemble des requêtes de statut, d'interrogation,
    de configuration automatique (ASB) et de synchronisation envoyées par le POS,
    tout en nettoyant le flux pour ne garder que le contenu textuel du ticket.
    """
    responses = bytearray()
    clean_bytes = bytearray()
    i = 0
    length = len(data)

    while i < length:
        byte = data[i]

        # 1. DLE EOT n (0x10 0x04 n) : Requête d'état temps réel (n=1 à 4)
        if i + 2 < length and byte == 0x10 and data[i+1] == 0x04:
            n = data[i+2]
            responses.extend(b"\x12") # Statut prêt standard
            print(f"[ESC/POS] DLE EOT détecté (n={n}) -> Réponse OK (0x12)")
            i += 3
            continue

        # 2. DLE ENQ n (0x10 0x05 n) : Demande de transmission en temps réel
        if i + 2 < length and byte == 0x10 and data[i+1] == 0x05:
            responses.extend(b"\x00")
            print(f"[ESC/POS] DLE ENQ détecté -> Réponse OK (0x00)")
            i += 3
            continue

        # 3. ENQ isolé (0x05) : Demande d'état globale de certains POS
        if byte == 0x05:
            responses.extend(b"\x00")
            print("[ESC/POS] ENQ (0x05) détecté -> Réponse OK (0x00)")
            i += 1
            continue

        # 4. DLE ou EOT isolés
        if byte == 0x10 or byte == 0x04:
            responses.extend(b"\x00")
            print(f"[ESC/POS] Octet de contrôle isolé détecté ({hex(byte)}) -> Réponse OK (0x00)")
            i += 1
            continue

        # 5. GS r n (0x1D 0x72 n) : Demande d'état des capteurs (papier / tiroir)
        if i + 2 < length and byte == 0x1D and data[i + 1] == 0x72:
            responses.extend(b"\x00") # 0x00 = Pas d'erreur / Capteurs OK
            print(f"[ESC/POS] GS r (Capteurs/Papier) détecté -> Réponse (0x00)")
            i += 3
            continue

        # 6. GS a n (0x1D 0x61 n) : Activation/Désactivation du statut automatique (ASB)
        if i + 2 < length and byte == 0x1D and data[i + 1] == 0x61:
            print("[ESC/POS] GS a (Configuration ASB) détecté -> Consommé/Ignoré")
            i += 3
            continue

        # 7. ESC v (0x1B 0x76) : Demande d'état du capteur de papier
        if i + 1 < length and byte == 0x1B and data[i + 1] == 0x76:
            responses.extend(b"\x00")
            print("[ESC/POS] ESC v (Papier) détecté -> Réponse (0x00)")
            i += 2
            continue

        # 8. ESC = n (0x1B 0x3D n) : Sélection de périphérique / Initialisation
        if i + 2 < length and byte == 0x1B and data[i + 1] == 0x3D:
            print("[ESC/POS] ESC = (Sélection périphérique) détecté -> Ignoré")
            i += 3
            continue

        # 9. ESC @ (0x1B 0x40) : Réinitialisation imprimante
        if i + 1 < length and byte == 0x1B and data[i + 1] == 0x40:
            print("[ESC/POS] ESC @ (Reset) -> Ignoré du flux texte")
            i += 2
            continue

        # Tout le reste est conservé pour former le texte réel du ticket
        clean_bytes.append(byte)
        i += 1

    return bytes(responses), bytes(clean_bytes)


# ============================================================
# WORKER TCP SÉCURISÉ (AVEC RECONNEXION AUTOMATIQUE)
# ============================================================

def tcp_worker():
    global running
    while running:
        touch_watchdog()
        try:
            full_ticket_data = print_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        sock = None
        connected = False
        
        # Boucle de reconnexion TCP si le réseau décroche
        while running and not connected:
            touch_watchdog()
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(TCP_TIMEOUT)
                sock.connect((TCP_HOST, TCP_PORT))
                connected = True
            except Exception:
                if sock:
                    try:
                        sock.close()
                    except Exception:
                        pass
                time.sleep(3)

        if not running:
            break

        try:
            sock.sendall(full_ticket_data)
            log("[COM7 -> TCP (Bloc Complet Nettoyé)]", full_ticket_data)

            sock.settimeout(1.0)
            try:
                response_tcp = sock.recv(4096)
                if response_tcp:
                    log("[TCP -> COM7]", response_tcp)
                    if ser and ser.is_open:
                        ser.write(response_tcp)
                        ser.flush()
            except socket.timeout:
                pass

        except Exception as e:
            print(f"[TCP] Erreur durant l'envoi : {e}")
            # En cas d'échec réseau, on remet le ticket dans la file pour ne pas le perdre
            print_queue.put(full_ticket_data)

        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass
            time.sleep(0.2)
            print_queue.task_done()


# ============================================================
# LECTURE COM7 & GESTION DU BUFFER (ANTI-CRASH & RECO AUTO)
# ============================================================

def serial_receiver():
    global running, ser

    while running:
        touch_watchdog()
        # Vérification et ouverture/reconnexion sécurisée du port COM
        if ser is None or not ser.is_open:
            try:
                print(f"[COM] Tentative de connexion sur {COM_PORT}...")
                ser = serial.Serial(
                    port=COM_PORT,
                    baudrate=BAUDRATE,
                    bytesize=BYTESIZE,
                    parity=PARITY,
                    stopbits=STOPBITS,
                    timeout=0.1,
                    write_timeout=2
                )
                print(f"[COM] {COM_PORT} CONNECTÉ ET OPÉRATIONNEL")
            except Exception as e:
                print(f"[COM] Port {COM_PORT} indisponible ({e}). Nouvelle tentative dans 3 secondes...")
                time.sleep(3)
                continue

        input_b = b''

        while running:
            touch_watchdog()
            try:
                if not ser.is_open:
                    break

                waiting = ser.in_waiting
                if waiting:
                    data = ser.read(waiting)
                else:
                    data = ser.read(1)

                if not data:
                    continue

                log("[COM7 RX (Brut reçu)]", data)
                
                # 1. Analyse, réponse automatique obligatoire au POS et nettoyage
                response, clean_data = process_and_clean_escpos(data)
                
                if response:
                    ser.write(response)
                    ser.flush()

                if not clean_data:
                    continue

                # 2. Accumulation des données propres du ticket
                input_b += clean_data

                # 3. Découpage par séquence de fin de ticket
                if TICKET_END_BINARY_SEQUENCE in input_b:
                    parts = input_b.split(TICKET_END_BINARY_SEQUENCE)
                    residu = parts[-1]  
                    complete_tickets = parts[:-1]

                    input_b = residu  

                    for t_data in complete_tickets:
                        if len(t_data) < 2:
                            continue
                        full_ticket = t_data + TICKET_END_BINARY_SEQUENCE
                        print_queue.put(full_ticket)
                        print(f"[QUEUE] Ticket complet de {len(full_ticket)} octets mis en file d'attente.")
                
                elif len(input_b) > 16384:
                    # Sécurité anti-saturation si un flux arrive sans fin de ticket
                    print_queue.put(input_b)
                    input_b = b''

            except (serial.SerialException, OSError) as e:
                print(f"[COM] Alerte : Perte physique ou décrochage du port USB ({e}). Reconnexion en cours...")
                try:
                    if ser:
                        ser.close()
                except Exception:
                    pass
                ser = None
                time.sleep(2)
                break  # Sort de la boucle interne pour relancer la reconnexion propre
            except Exception as e:
                print(f"[COM] Erreur critique inattendue : {e}")
                time.sleep(1)


# ============================================================
# MONITEUR INTERNE WATCHDOG (BATTEMENT DE CŒUR)
# ============================================================

def watchdog_monitor():
    """
    Surveille si le programme s'est figé. Si aucune tâche ne rafraîchit
    le heartbeat dans le délai imparti, on force l'arrêt complet du sous-processus.
    """
    global running, last_heartbeat
    while running:
        time.sleep(2)
        elapsed = time.time() - last_heartbeat
        if elapsed > WATCHDOG_TIMEOUT:
            print(f"\n[WATCHDOG ALERTE] Aucun signe de vie depuis {elapsed:.1f}s ! Forçage du redémarrage...")
            os._exit(1)  # Arrêt brutal immédiat pour déclencher le reboot par le superviseur


# ============================================================
# EXÉCUTION DU WORKER ET DU SUPERVISEUR PERMANENT
# ============================================================

def run_worker():
    global running

    print("[SYSTEM] Démarrage des threads de travail...")

    thread_watchdog = threading.Thread(target=watchdog_monitor, daemon=True)
    thread_watchdog.start()

    thread_com = threading.Thread(target=serial_receiver, daemon=True)
    thread_com.start()

    thread_tcp_worker = threading.Thread(target=tcp_worker, daemon=True)
    thread_tcp_worker.start()

    try:
        while running:
            # Si un thread s'est éteint anormalement, on tue l'application pour redémarrer propre
            if not thread_com.is_alive() or not thread_tcp_worker.is_alive():
                print("[SYSTEM] Un thread critique est mort ! Relance automatique...")
                os._exit(1)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SYSTEM] Arrêt du worker demandé.")
        running = False

    if ser:
        try:
            ser.close()
        except Exception:
            pass


def run_supervisor():
    print("============================================================")
    print("   SUPERVISEUR PERMANENT ACTIF (INCESSANT & AUTO-RESTART)    ")
    print("============================================================")
    
    args = [a for a in sys.argv if a != "--worker"]
    cmd = [sys.executable] + args + ["--worker"]

    while True:
        try:
            print("[SUPERVISEUR] Lancement du sous-processus...")
            process = subprocess.Popen(cmd)
            exit_code = process.wait()
            
            # Peu importe la cause d'arrêt (crash, fin normale, kill), on redémarre systématiquement
            print(f"\n[SUPERVISEUR] Le programme s'est arrêté (Code de sortie: {exit_code}). Redémarrage dans 2s...")
            time.sleep(2)
            
        except KeyboardInterrupt:
            print("\n[SUPERVISEUR] Interruption détectée. Redémarrage forcé dans 2s...")
            time.sleep(2)
        except Exception as e:
            print(f"[SUPERVISEUR] Erreur du superviseur : {e}. Redémarrage dans 2s...")
            time.sleep(2)


if __name__ == "__main__":
    if "--worker" in sys.argv:
        run_worker()
    else:
        run_supervisor()