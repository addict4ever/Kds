import socket
import random
import time

def envoyer_test_takeout(ip_adresse="16.16.16.100", port=9100):
    """
    Envoie un message de test au format TAKEOUT sur un port TCP.
    """
    # Générer un numéro au hasard entre 300 et 400
    numero_table = random.randint(300, 400)
    
    # Préparer le message selon votre format
    message = f"??MSG-TAKEOUT??{numero_table}??\n"
    
    print(f"Connexion à {ip_adresse}:{port}...")
    
    try:
        # Création du socket TCP
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5) # Timeout de 5 secondes
            s.connect((ip_adresse, port))
            
            # Envoi du message encodé en UTF-8
            s.sendall(message.encode('utf-8'))
            
            print(f"✅ Message envoyé avec succès : {message.strip()}")
            
    except ConnectionRefusedError:
        print(f"❌ Erreur : Connexion refusée sur le port {port}. Vérifiez que votre KDS/SerialReader est bien lancé.")
    except Exception as e:
        print(f"❌ Une erreur est survenue : {e}")

if __name__ == "__main__":
    # Si vous testez sur le même ordinateur, laissez 127.0.0.1
    # Sinon, mettez l'adresse IP de l'ordinateur où tourne le KDS
    envoyer_test_takeout(ip_adresse="127.0.0.1", port=9100)