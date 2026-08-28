import sqlite3
from datetime import datetime, timedelta
import json
import logging 
import re # ⭐ AJOUT NÉCESSAIRE pour le parsing des items (quantité)
import uuid
import threading  # <--- AJOUTEZ CECI EN HAUT DE VOTRE FICHIER
import textwrap # Outil standard pour couper le texte proprement


# Configuration de base du logger pour la classe
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- NOUVELLE CONSTANTE : Chemin de la BDD d'Archive ---
CONSULTATION_DB_PATH = 'consultation.db'
LIVREUR_DB_PATH = 'kds_livreur_orders.db'

class DBManager:
    """
    Gère toutes les interactions avec les bases de données SQLite pour le KDS.
    - kds_orders.db: BDD de travail (commandes 'En attente', 'En cours', 'Traitée', 'Annulée').
    - consultation.db: BDD d'archive (clonage instantané de tous les tickets pour consultation/analyse).
    """
    def __init__(self, db_path='kds_orders.db'):
        self.db_path = db_path
        logger.info(f"DBManager initialisé. Chemin BDD KDS: {self.db_path}. Chemin BDD Consultation: {CONSULTATION_DB_PATH}")
        self._create_tables()

    def _get_connection(self):
        """Retourne une connexion à la base de données KDS principale (kds_orders.db)."""
        try:
            # ⭐ INDISPENSABLE pour le multi-threading du SerialReader
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            return conn
        except sqlite3.Error as e:
            logger.error(f"Erreur de connexion à la base de données KDS : {e}")
            return None

    def _get_consultation_connection(self):
        """Retourne une connexion à la base de données de Consultation (Archive)."""
        try:
            # ⭐ AJOUTÉ ICI AUSSI pour la sécurité
            conn = sqlite3.connect(CONSULTATION_DB_PATH, check_same_thread=False)
            return conn
        except sqlite3.Error as e:
            logger.error(f"Erreur de connexion à la base de données de Consultation : {e}")
            raise

    def _create_tables(self):
        """Crée les tables KDS, la table 'orders_archive' (consultation) et le clone 'livreur'."""
        conn_kds = None
        conn_consultation = None
        conn_livreur = None
        
        try:
            # 1. Tables de la BDD KDS principale (kds_orders.db)
            conn_kds = self._get_connection()
            cursor_kds = conn_kds.cursor()
            
            cursor_kds.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bill_id TEXT NOT NULL,
                    table_number INTEGER NOT NULL,
                    serveuse_name TEXT NOT NULL, 
                    service_type TEXT NOT NULL, 
                    items TEXT NOT NULL,
                    creation_date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    raw_content BLOB
                )
            """)
            cursor_kds.execute("""
                CREATE TABLE IF NOT EXISTS bill_notes (
                    bill_id TEXT PRIMARY KEY,
                    note_content TEXT,
                    last_updated TEXT
                )
            """)
            conn_kds.commit()
            logger.info("Tables KDS ('orders', 'bill_notes') vérifiées/créées.")
            
            # 2. Table des commandes archivées (consultation.db)
            conn_consultation = self._get_consultation_connection()
            cursor_consultation = conn_consultation.cursor()
            
            cursor_consultation.execute("""
                CREATE TABLE IF NOT EXISTS orders_archive (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bill_id TEXT NOT NULL,
                    table_number INTEGER NOT NULL,
                    serveuse_name TEXT NOT NULL, 
                    service_type TEXT NOT NULL, 
                    items TEXT NOT NULL,
                    creation_date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    archived_date TEXT NOT NULL,
                    raw_content BLOB
                )
            """)
            conn_consultation.commit()
            logger.info("Table 'orders_archive' dans consultation.db vérifiée/créée.")

            # 3. Initialisation du clone 'kds_livreur_orders.db'
            conn_livreur = sqlite3.connect(LIVREUR_DB_PATH)
            cursor_livreur = conn_livreur.cursor()
            cursor_livreur.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bill_id TEXT NOT NULL,
                    table_number INTEGER NOT NULL,
                    serveuse_name TEXT NOT NULL, 
                    service_type TEXT NOT NULL, 
                    items TEXT NOT NULL,
                    creation_date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    raw_content BLOB
                )
            """)
            conn_livreur.commit()
            logger.info("Base clone 'kds_livreur_orders.db' vérifiée/créée.")
            
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de la création des tables : {e}")
        finally:
            if conn_kds: conn_kds.close()
            if conn_consultation: conn_consultation.close()
            if conn_livreur: conn_livreur.close()


    def _execute_on_main_and_clone(self, query, params):
        """
        Exécute une commande SQL sur la base principale (kds_orders.db) 
        et sur le clone (kds_livreur_orders.db).
        """
        # 1. Exécution sur la base principale
        conn = None
        try:
            conn = self._get_connection()
            conn.execute(query, params)
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de l'exécution sur la base principale : {e}")
            raise # On remonte l'erreur pour que l'app sache que l'insertion a échoué
        finally:
            if conn:
                conn.close()

        # 2. Exécution sur le clone 'Livreur'
        conn_clone = None
        try:
            conn_clone = sqlite3.connect(LIVREUR_DB_PATH)
            conn_clone.execute(query, params)
            conn_clone.commit()
        except sqlite3.Error as e:
            # On logue l'erreur mais on ne bloque pas tout le système si le clone échoue
            logger.error(f"Erreur lors de l'exécution sur le clone '{LIVREUR_DB_PATH}' : {e}")
        finally:
            if conn_clone:
                conn_clone.close()

    def get_main_dishes(self):
        """Récupère les noms et prix depuis kds_constants.db."""
        import sqlite3
        conn_const = sqlite3.connect('kds_constants.db')
        try:
            # On force le retour sous forme de dictionnaire pour éviter les erreurs d'index
            conn_const.row_factory = sqlite3.Row 
            cursor = conn_const.cursor()
            
            # On utilise dish_name (votre clé primaire dans kds_constants.db)
            cursor.execute("SELECT dish_name, price FROM main_dishes")
            rows = cursor.fetchall()
            
            # On transforme chaque ligne en un dictionnaire simple {'name': ..., 'price': ...}
            return [{"name": row["dish_name"], "price": row["price"]} for row in rows]
        except Exception as e:
            logging.error(f"Erreur SQL dans get_main_dishes: {e}")
            return []
        finally:
            conn_const.close()
    

    def get_main_dishes_with_prices(self):
        """Récupère les noms et prix depuis kds_constants.db."""
        import sqlite3
        conn_const = sqlite3.connect('kds_constants.db')
        try:
            # On force le retour sous forme de dictionnaire pour éviter les erreurs d'index
            conn_const.row_factory = sqlite3.Row 
            cursor = conn_const.cursor()
            
            # On utilise dish_name (votre clé primaire dans kds_constants.db)
            cursor.execute("SELECT dish_name, price FROM main_dishes")
            rows = cursor.fetchall()
            
            # On transforme chaque ligne en un dictionnaire simple {'name': ..., 'price': ...}
            return [{"name": row["dish_name"], "price": row["price"]} for row in rows]
        except Exception as e:
            logging.error(f"Erreur SQL dans get_main_dishes: {e}")
            return []
        finally:
            conn_const.close()

    def reactivate_order_by_table(self, table_number):
        """
        Réactive ou met à jour TOUTES les commandes correspondantes dans la base de données kds_orders 
        pour un même numéro de table (qu'elles soient 'Traitée' ou 'En attente').
        Ajoute l'item 'TABLE À SORTIR' uniquement s'il n'est pas déjà présent.
        """
        conn = self._get_connection()
        if not conn:
            print("Erreur de connexion à la BDD pour la réactivation.")
            return False
            
        try:
            cursor = conn.cursor()
            
            # 1. Récupérer TOUTES les commandes correspondantes (Traitée ou En attente)
            cursor.execute("""
                SELECT id, items FROM orders 
                WHERE table_number = ? AND status IN ('Traitée', 'En attente')
            """, (str(table_number),))
            
            rows = cursor.fetchall()
            if not rows:
                print(f"Aucune commande trouvée pour la table {table_number}.")
                return False
                
            success_count = 0
            sortir_text = "TABLE À SORTIR"

            # 2. Boucler sur chaque commande trouvée
            for row in rows:
                order_id, raw_items = row
                
                # Décoder les items existants
                current_items_objs = []
                if raw_items:
                    try:
                        loaded = json.loads(raw_items)
                        for item in (loaded if isinstance(loaded, list) else [loaded]):
                            current_items_objs.append(json.loads(item) if isinstance(item, str) else item)
                    except Exception:
                        current_items_objs = []
                
                # Vérifier si "TABLE À SORTIR" est déjà présent dans les items
                already_exists = any(
                    str(i.get('main_item', '')).strip().upper() == sortir_text 
                    for i in current_items_objs
                )
                
                # Si l'item n'existe pas encore, on l'ajoute au début
                if not already_exists:
                    new_main_item_obj = {"main_item": sortir_text, "sub_items": []}
                    current_items_objs.insert(0, new_main_item_obj)
                
                # Reconvertir la liste en JSON pour la BDD
                final_items_json = json.dumps([json.dumps(obj, ensure_ascii=False) for obj in current_items_objs], ensure_ascii=False)
                
                # Mettre à jour le statut à 'En attente' et actualiser les items pour cet ID spécifique
                query = """
                    UPDATE orders 
                    SET status = 'En attente', items = ? 
                    WHERE id = ?
                """
                cursor.execute(query, (final_items_json, order_id))
                if cursor.rowcount > 0:
                    success_count += 1

            conn.commit()
            
            if success_count > 0:
                print(f"✅ {success_count} commande(s) de la table {table_number} mises à jour avec succès.")
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Erreur SQL lors de la réactivation multiple par table : {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def create_new_order_from_split(self, original_data: dict, items: list, suffixe: str) -> str:
        original_bill_id = original_data['bill_id']
        new_bill_id = f"{original_bill_id}{suffixe}"
        
        # On récupère la date originale au lieu de générer une nouvelle date
        creation_date = original_data.get('creation_date') 
        
        items_json_list = [json.dumps(item, ensure_ascii=False) for item in items]
        items_json_str = json.dumps(items_json_list, ensure_ascii=False)

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # 1. ON FORCE LE STATUT À 'Traitée' POUR L'ANCIENNE
            cursor.execute("UPDATE orders SET status = 'Traitée' WHERE bill_id = ?", (original_bill_id,))
            
            # 2. ON INSÈRE LA NOUVELLE (avec la date d'origine)
            cursor.execute("""
                INSERT INTO orders (bill_id, table_number, serveuse_name, service_type, items, creation_date, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (new_bill_id, original_data['table_number'], original_data['serveuse_name'], 
                original_data['service_type'], items_json_str, creation_date, 'En attente'))
            
            conn.commit()
            return new_bill_id
        except Exception as e:
            if conn: conn.rollback()
            raise e
        finally:
            if conn: conn.close()

    def set_order_status_by_bill_id_livraison(self, bill_id: str, new_status: str) -> int:
        """
        Met à jour le statut d'une commande EXCLUSIVEMENT dans la base 'LIVREUR'.
        """
        row_count = 0
        conn = None
        
        try:
            # Connexion directe à la base du clone
            conn = sqlite3.connect(LIVREUR_DB_PATH)
            cursor = conn.cursor()
            clean_bid = str(bill_id).strip()
            
            # Mise à jour dans la base livreur
            cursor.execute("""
                UPDATE orders 
                SET status = ? 
                WHERE id = ? OR bill_id = ? OR bill_id LIKE ?
            """, (new_status, clean_bid, clean_bid, f"{clean_bid}-%"))
            
            conn.commit()
            row_count = cursor.rowcount
            
            if row_count > 0:
                logger.info(f"✅ Succès (Livreur) : {row_count} ligne(s) mise(s) à jour pour '{clean_bid}'")
            else:
                logger.warning(f"⚠️ Échec (Livreur) : Aucune facture trouvée pour '{clean_bid}'.")
                
        except sqlite3.Error as e:
            logger.error(f"❌ Erreur SQL (Livreur) : {e}")
            if conn: conn.rollback()
        finally:
            if conn: conn.close()
                
        return row_count

    # ⭐ MÉTHODE CRITIQUE : Changer le statut d'une commande (pour Fermer/Traiter/Post-it)
    def set_order_status_by_bill_id(self, bill_id: str, new_status: str) -> int:
        """
        Met à jour le statut d'une commande. 
        Recherche par l'ID numérique de la table (id) OU par correspondance textuelle (bill_id).
        """
        conn = self._get_connection()
        if not conn: return 0
        row_count = 0
        
        try:
            cursor = conn.cursor()
            clean_bid = str(bill_id).strip()
            
            # REQUÊTE MODIFIÉE : On ajoute la condition 'id = ?' pour attraper les numéros de ligne
            cursor.execute("""
                UPDATE orders 
                SET status = ? 
                WHERE id = ? OR bill_id = ? OR bill_id LIKE ?
            """, (new_status, clean_bid, clean_bid, f"{clean_bid}-%"))
            
            conn.commit()
            row_count = cursor.rowcount
            
            if row_count > 0:
                logger.info(f"✅ Succès : {row_count} ligne(s) mise(s) à jour pour l'ID/Bill_ID '{clean_bid}'")
            else:
                logger.warning(f"⚠️ Échec : Aucune facture trouvée avec id ou bill_id commençant par '{clean_bid}'.")
                
        except sqlite3.Error as e:
            logger.error(f"❌ Erreur SQL : {e}")
            if conn: conn.rollback()
        finally:
            if conn: conn.close()
                
        return row_count

    def merge_orders(self, source_bill_ids: list[str], destination_bill_id: str) -> tuple[str, list, str]:
        """
        Fusionne les items et la note des factures sources et destination
        dans une TOUTE NOUVELLE facture, en utilisant la date LA PLUS ANCIENNE,
        puis marque les originales comme 'Traitée'.
        """
        conn = self._get_connection()
        if not conn: 
            raise Exception("Connexion DB échouée.")

        # Liste de tous les IDs concernés
        all_original_bill_ids = [destination_bill_id] + source_bill_ids
        placeholders_all = ','.join('?' * len(all_original_bill_ids))
        
        try:
            cursor = conn.cursor()
            
            # --- 0. Récupération des infos de base et de la date la plus ancienne ---
            # On récupère table_number etc. de la destination, mais on SELECT creation_date de TOUS
            query_info = f"""
                SELECT table_number, serveuse_name, service_type, creation_date 
                FROM orders 
                WHERE bill_id IN ({placeholders_all})
            """
            cursor.execute(query_info, all_original_bill_ids)
            rows = cursor.fetchall()
            
            if not rows:
                raise ValueError("Aucune donnée trouvée pour les factures à fusionner.")

            # On extrait les données de la destination (pour la table/serveuse)
            # Et on collecte toutes les dates pour trouver la plus petite (la plus ancienne)
            all_dates = []
            target_info = None
            
            # On cherche les infos de la destination spécifiquement pour le contexte
            # Mais on stocke toutes les dates
            for row in rows:
                all_dates.append(row[3]) # creation_date est à l'index 3
            
            # Récupération des métadonnées de la destination pour la nouvelle facture
            cursor.execute("SELECT table_number, serveuse_name, service_type FROM orders WHERE bill_id = ?", (destination_bill_id,))
            dest_meta = cursor.fetchone()
            table_number, serveuse_name, service_type = dest_meta

            # La date la plus ancienne (min en string fonctionne bien sur le format YYYY-MM-DD HH:MM:S)
            oldest_creation_date = min(all_dates)

            # --- 1. Récupération et fusion des ITEMS ---
            new_items_list_json_strings = []
            
            separator_item_dict = {
                "is_separator": True,
                "bill_ids_merged": all_original_bill_ids 
            }
            separator_item_json_string = json.dumps(separator_item_dict)
            
            query_all_items = f"SELECT items FROM orders WHERE bill_id IN ({placeholders_all})"
            cursor.execute(query_all_items, all_original_bill_ids)
            source_and_dest_rows = cursor.fetchall()
            
            if source_and_dest_rows:
                new_items_list_json_strings.append(separator_item_json_string) 
                for row in source_and_dest_rows:
                    original_items_list_json_strings = json.loads(row[0])
                    new_items_list_json_strings.extend(original_items_list_json_strings)
            
            # --- 2. Récupération et fusion de la NOTE ---
            query_notes = f"SELECT note_content FROM bill_notes WHERE bill_id IN ({placeholders_all})"
            cursor.execute(query_notes, all_original_bill_ids)
            
            notes = [row[0] for row in cursor.fetchall() if row and row[0] and row[0].strip()]
            new_note_content = "\n---\n".join(notes).strip()
            
            # --- 3. Création de la NOUVELLE facture ---
            new_bill_id = datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]
            
            # On ferme pour laisser les méthodes suivantes gérer leurs transactions
            conn.close() 

            self.add_new_order(
                bill_id=new_bill_id, 
                table_number=table_number, 
                serveuse_name=serveuse_name, 
                service_type=service_type,
                items=new_items_list_json_strings, 
                status='En attente',
                creation_date=oldest_creation_date # <--- On applique la date la plus ancienne
            )
            self.set_bill_note(new_bill_id, new_note_content) 
            
            # ⭐ ÉTAPE 4: Marquer les originales comme 'Traitée'
            conn = self._get_connection()
            cursor = conn.cursor()

            query_update_status = f"UPDATE orders SET status = 'Traitée' WHERE bill_id IN ({placeholders_all})"
            cursor.execute(query_update_status, all_original_bill_ids)

            conn.commit()
            
            logger.info(f"Fusion réussie. Nouvelle facture {new_bill_id} créée avec la date ancienne {oldest_creation_date}.")
            return new_bill_id, new_items_list_json_strings, new_note_content 
            
        except Exception as e:
            logger.error(f"Erreur lors de la fusion : {e}")
            if conn and conn.in_transaction: 
                conn.rollback()
            raise Exception(f"Erreur lors de la fusion : {e}")
        finally:
            if conn:
                conn.close()

    def add_note(self, message):
        """
        Crée une entrée dans la table 'orders'. 
        Le message est découpé en lignes de 40 caractères max pour l'affichage KDS.
        """
        try:
            bill_id = f"NOTE-{uuid.uuid4().hex[:8].upper()}"
            
            # 1. Découpage du message en lignes de 40 caractères max
            # textwrap.wrap découpe proprement sans couper les mots au milieu si possible
            lines = textwrap.wrap(message, width=30)
            
            # 2. Création de l'objet (dictionnaire)
            note_dict = {
                "main_item": "MESSAGE",
                "sub_items": lines  # Utilise la liste de lignes découpées
            }
            
            # 3. Conversion en chaîne JSON (premier niveau)
            json_str = json.dumps(note_dict)
            
            # 4. Conversion finale pour la DB (double encodage avec les \ échappés)
            items_json = json.dumps([json_str])
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO orders (
                    bill_id, table_number, serveuse_name, service_type, 
                    items, creation_date, status
                ) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                bill_id, 
                888, 
                "MESSAGE", 
                "888", 
                items_json, 
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                "En attente"
            ))
            
            conn.commit()
            conn.close()
            return bill_id
            
        except Exception as e:
            logger.error(f"Erreur DB lors de l'insertion de la note : {e}")
            return None
                
    def get_active_orders(self) -> list:
        """
        Récupère toutes les commandes actives (En attente, En cours).
        Retourne une liste plate de dictionnaires de commandes. Utilisé par kds_gui.py.
        """
        conn = self._get_connection()
        if not conn: return []
        
        conn.row_factory = sqlite3.Row # Important pour obtenir un dictionnaire
        cursor = conn.cursor()
        
        # Filtre les statuts considérés comme "inactifs" ou "terminés"
        query = """
        SELECT * FROM orders 
        WHERE status NOT IN ('Traitée', 'Annulée', 'Archivée') 
        ORDER BY creation_date ASC
        """
        try:
            cursor.execute(query)
            # Convertit chaque ligne en dictionnaire.
            # Convertit aussi le champ 'items' (stocké comme liste de chaînes JSON) en liste Python
            orders_data = []
            for row in cursor.fetchall():
                order = dict(row)
                # S'assurer que le champ items est une liste pour kds_gui.py
                try:
                    order['items'] = json.loads(order['items'])
                except (json.JSONDecodeError, TypeError):
                    order['items'] = []
                orders_data.append(order)
                
            return orders_data
        except sqlite3.Error as e:
            logger.error(f"Erreur DB lors de la récupération des commandes actives: {e}")
            return []
        finally:
            if conn:
                conn.close()

    

    def get_all_bill_notes(self):
        """
        Récupère toutes les notes de facture et les retourne sous forme de dictionnaire 
        {bill_id: note_content}. Utilisé pour le rendu de toutes les cartes KDS.
        """
        conn = None
        notes = {}
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT bill_id, note_content FROM bill_notes")
            rows = cursor.fetchall()
            for row in rows:
                # Créer le dictionnaire {bill_id: note}
                notes[row[0]] = row[1]
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de la récupération de toutes les notes de facture : {e}")
        finally:
            if conn:
                conn.close()
        return notes
    # --- NOUVELLE MÉTHODE : Clonage Instantané ---
    def _archive_order_instant(self, bill_id, table_number, serveuse_name, service_type, items_json, creation_date, status):
        """
        Clône instantanément une nouvelle commande dans orders_archive de consultation.db.
        Cette méthode s'exécute à CHAQUE nouvelle commande (ticket) reçue via insert_order.
        """
        conn_consultation = None
        try:
            conn_consultation = self._get_consultation_connection()
            cursor_consultation = conn_consultation.cursor()
            # Note: archived_date est la date/heure à laquelle le ticket a été inséré dans l'archive (le temps actuel)
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S') 

            cursor_consultation.execute("""
                INSERT INTO orders_archive (bill_id, table_number, serveuse_name, service_type, items, creation_date, status, archived_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (bill_id, table_number, serveuse_name, service_type, items_json, creation_date, status, now))
            
            conn_consultation.commit()
            # logger.info(f"Commande Bill ID {bill_id} clonée instantanément dans consultation.db.")
        except sqlite3.Error as e:
            logger.error(f"Erreur lors du clonage instantané de la commande {bill_id} : {e}")
        finally:
            if conn_consultation:
                conn_consultation.close()

    # --- NOUVELLES MÉTHODES POUR consultation.db ---
    
    def get_all_archived_orders_from_consultation(self):
        """
        📊 Récupère TOUTES les commandes (tickets) archivées dans consultation.db.
        Retourne une liste plate de tickets de commande, triée par date d'archivage descendante.
        """
        conn = None
        rows = []
        try:
            conn = self._get_consultation_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT bill_id, table_number, serveuse_name, service_type, items, creation_date, status, archived_date
                FROM orders_archive 
                ORDER BY archived_date DESC
            """)
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de la récupération de toutes les commandes archivées : {e}")
        finally:
            if conn:
                conn.close()

        archived_orders_flat = []
        for row in rows:
            try:
                # 1. Décodage de la LISTE d'items (chaîne JSON -> Liste Python)
                items_list_json_strs = json.loads(row[4]) 
                
                # 2. Calculer le nombre total d'items (basé sur la quantité des 'main_item')
                total_items = 0
                for item_json_str in items_list_json_strs:
                    # 3. Décodage de l'item individuel (chaîne JSON -> Dict Python)
                    item_dict = json.loads(item_json_str)
                    main_item_str = item_dict.get('main_item', item_json_str) # Récupère la chaîne "N x ITEM"

                    # Tente de trouver la quantité au début (ex: "4 x ") dans le main_item
                    match = re.match(r'^(\d+)\s+x\s+(.*)', main_item_str, re.IGNORECASE)
                    
                    if match:
                        try:
                            quantity = int(match.group(1)) 
                            total_items += quantity
                        except ValueError:
                            total_items += 1 # Compte par défaut 1 si la quantité est mal parsée
                    else:
                        # Si pas de 'N x ' (ex: "SERVICE # 1"), compte comme 1
                        total_items += 1 

                archived_orders_flat.append({
                    'bill_id': row[0],
                    'table_number': row[1],
                    'serveuse_name': row[2],
                    'service_type': row[3],
                    'items': items_list_json_strs, # Reste la liste des chaînes JSON
                    'creation_date': row[5],
                    'status': row[6],
                    'archived_date': row[7], 
                    'total_items': total_items 
                })
            except (json.JSONDecodeError, IndexError, ValueError, AttributeError) as e:
                logger.warning(f"Erreur de décodage JSON ou de calcul d'items pour la facture {row[0]} dans orders_archive. Ligne ignorée. Erreur: {e}")
                continue
            
        return archived_orders_flat
    
    def search_archived_orders_in_consultation(self, bill_id=None, serveuse_name=None, table_number=None, start_date=None, end_date=None):
        """
        🔍 Recherche des commandes archivées dans consultation.db en utilisant des critères spécifiques.
        Les dates doivent être au format 'YYYY-MM-DD HH:MM:SS'.
        Retourne une liste plate de tickets de commande correspondants.
        """
        conn = None
        rows = []
        
        base_query = """
            SELECT bill_id, table_number, serveuse_name, service_type, items, creation_date, status, archived_date
            FROM orders_archive 
            WHERE 1=1
        """
        params = []
        
        if bill_id:
            base_query += " AND bill_id = ?"
            params.append(bill_id)
            
        if serveuse_name:
            # Utiliser LIKE pour une recherche partielle insensible à la casse
            base_query += " AND serveuse_name LIKE ?"
            params.append(f'%{serveuse_name}%')
            
        if table_number is not None and table_number != '': 
            base_query += " AND table_number = ?"
            params.append(table_number)
            
        if start_date:
            # Recherche par date d'archivage (quand le ticket a été traité/annulé/créé)
            base_query += " AND archived_date >= ?"
            params.append(start_date)

        if end_date:
            base_query += " AND archived_date <= ?"
            params.append(end_date)
            
        base_query += " ORDER BY archived_date DESC"

        try:
            conn = self._get_consultation_connection()
            cursor = conn.cursor()
            
            cursor.execute(base_query, params)
            rows = cursor.fetchall()
            logger.info(f"Recherche dans consultation.db exécutée. {len(rows)} résultats trouvés.")
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de la recherche dans orders_archive : {e}")
        finally:
            if conn:
                conn.close()

        archived_orders_flat = []
        for row in rows:
            try:
                # 1. Décodage de la LISTE d'items
                items_list_json_strs = json.loads(row[4])
                
                # 2. Calculer le nombre total d'items
                total_items = 0
                for item_json_str in items_list_json_strs:
                    # 3. Décodage de l'item individuel
                    item_dict = json.loads(item_json_str)
                    main_item_str = item_dict.get('main_item', item_json_str) 
                    
                    match = re.match(r'^(\d+)\s+x\s+(.*)', main_item_str, re.IGNORECASE)
                    
                    if match:
                        try:
                            quantity = int(match.group(1)) 
                            total_items += quantity
                        except ValueError:
                            total_items += 1
                    else:
                        total_items += 1

                archived_orders_flat.append({
                    'bill_id': row[0],
                    'table_number': row[1],
                    'serveuse_name': row[2],
                    'service_type': row[3],
                    'items': items_list_json_strs,
                    'creation_date': row[5],
                    'status': row[6],
                    'archived_date': row[7],
                    'total_items': total_items 
                })
            except (json.JSONDecodeError, IndexError, ValueError, AttributeError) as e:
                logger.warning(f"Erreur de décodage JSON ou de calcul d'items pour la facture {row[0]} dans orders_archive. Ligne ignorée. Erreur: {e}")
                continue
            
        return archived_orders_flat
    

    def update_order_service_and_table(self, bill_id: str, new_service_type: str, new_table_number: str):
        """
        1. Vérifie si le service est autorisé (LIVRAISON/LIVREUR).
        2. Vérifie si la table actuelle est autorisée (LIV/999).
        3. Ferme l'ancienne commande et en crée une nouvelle.
        """
        # 0. Vérification de sécurité du service et de la table cible
        authorized_services = ['LIVRAISON', 'LIVREUR']
        # On définit les tables autorisées selon le service choisi
        valid_tables = {'LIVRAISON': 'LIV', 'LIVREUR': '999'}
        
        if new_service_type not in authorized_services:
            return False, f"Service '{new_service_type}' non autorisé."
            
        # Vérification si la table demandée correspond bien au service
        if str(new_table_number) != str(valid_tables[new_service_type]):
            return False, f"Table {new_table_number} invalide pour le service {new_service_type}."

        conn = self._get_connection()
        if not conn: return False, "Erreur BDD."
        
        try:
            cursor = conn.cursor()
            
            # 1. Récupérer les données de l'ancienne commande
            cursor.execute("""
                SELECT items, serveuse_name, creation_date, table_number 
                FROM orders WHERE bill_id = ?
            """, (bill_id,))
            row = cursor.fetchone()
            
            if not row:
                return False, f"Commande {bill_id} introuvable."
            
            items_data, serveuse_name, creation_date, current_table = row
            
            # 2. Sécurité : Vérifier si la table actuelle est autorisée à être déplacée
            # Interdire si c'est 888 ou commence par PA
            curr_table_str = str(current_table).upper()
            if curr_table_str == '888' or curr_table_str.startswith('PA'):
                return False, f"La table {curr_table_str} est protégée (déplacement interdit)."

            # 3. Fermer l'ancienne
            cursor.execute("UPDATE orders SET status = 'Traitée' WHERE bill_id = ?", (bill_id,))
            
            # 4. Créer la nouvelle
            new_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO orders (bill_id, service_type, table_number, status, items, serveuse_name, creation_date)
                VALUES (?, ?, ?, 'En attente', ?, ?, ?)
            """, (new_id, new_service_type, str(new_table_number), items_data, serveuse_name, creation_date))
            
            conn.commit()
            msg = f"Commande transférée vers {new_service_type} ({new_table_number})."
            logger.info(msg)
            return True, msg
            
        except sqlite3.Error as e:
            return False, f"Erreur SQL : {e}"
        finally:
            if conn: conn.close()
            
    
    def add_items_to_existing_bill(self, table_number, serveuse_name, new_items_list):
        """
        Supprime l'ancienne commande et en crée une nouvelle dans la base principale et le clone livreur.
        """
        conn = self._get_connection()
        conn_livreur = None
        
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 1. Récupération de l'ancienne commande
            cursor.execute("""
                SELECT * FROM orders 
                WHERE table_number = ? AND serveuse_name = ? 
                ORDER BY id DESC LIMIT 1
            """, (str(table_number), str(serveuse_name)))
            
            row = cursor.fetchone()
            if not row:
                conn.close()
                return False

            # 2. Décodage et traitement des items
            current_items_objs = []
            raw_items_data = row['items']
            if raw_items_data:
                try:
                    loaded = json.loads(raw_items_data)
                    for item in (loaded if isinstance(loaded, list) else [loaded]):
                        current_items_objs.append(json.loads(item) if isinstance(item, str) else item)
                except:
                    current_items_objs = []

            prefixes_to_manage = {"HEURE:": "HEURE:", "NOTE:": "NOTE:", "UST:": "UST:"}

            for new_item_raw in new_items_list:
                new_obj = json.loads(new_item_raw) if isinstance(new_item_raw, str) else new_item_raw
                new_text = new_obj.get('main_item', "")
                
                found_prefix = next((p for p in prefixes_to_manage if new_text.startswith(p)), None)
                if found_prefix:
                    current_items_objs = [i for i in current_items_objs if not (isinstance(i, dict) and i.get('main_item', "").startswith(found_prefix))]
                current_items_objs.append(new_obj)

            # 3. Préparation des données
            final_items_json_strings = [json.dumps(obj) for obj in current_items_objs]
            order_data = dict(row)
            old_id = order_data.pop('id')
            order_data['status'] = 'En attente'
            order_data['items'] = json.dumps(final_items_json_strings)
            order_data['creation_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 4. EXÉCUTION SYNC (Base Principale + Clone Livreur)
            # Suppression dans les deux bases
            cursor.execute("DELETE FROM orders WHERE id = ?", (old_id,))
            
            conn_livreur = sqlite3.connect(LIVREUR_DB_PATH)
            conn_livreur.execute("DELETE FROM orders WHERE id = ?", (old_id,))

            # Insertion dans les deux bases
            columns = order_data.keys()
            placeholders = ":" + ", :".join(columns)
            sql = f"INSERT INTO orders ({', '.join(columns)}) VALUES ({placeholders})"
            
            cursor.execute(sql, order_data) # Base principale
            conn_livreur.execute(sql, order_data) # Clone livreur
            
            conn.commit()
            conn_livreur.commit()
            
            logger.info(f"DB: Commande #{old_id} mise à jour et synchronisée avec le clone.")
            return True

        except Exception as e:
            logger.error(f"Erreur lors de la synchro mise à jour : {e}")
            if conn: conn.rollback()
            if conn_livreur: conn_livreur.rollback()
            return False
        finally:
            if conn: conn.close()
            if conn_livreur: conn_livreur.close()
    import threading  # <--- AJOUTEZ CECI EN HAUT DE VOTRE FICHIER

# ... (votre classe DBManager)

    def update_pa_details(self, bid, note, desired_time, utensils, donner_au_pc=False, pa_number=None):
        import textwrap
        import json
        import threading
        import sqlite3

        conn = self._get_connection()
        conn_livreur = None
        str_bid = str(bid)
        
        try:
            # 1. Récupération
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM orders WHERE id = ?", (str_bid,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return False

            # 2. Traitement des items
            current_items_objs = []
            raw_items_data = row['items']
            if raw_items_data:
                try:
                    loaded = json.loads(raw_items_data)
                    for item in (loaded if isinstance(loaded, list) else [loaded]):
                        current_items_objs.append(json.loads(item) if isinstance(item, str) else item)
                except:
                    current_items_objs = []

            old_time = next((i['main_item'].replace("HEURE: ", "") for i in current_items_objs if str(i.get('main_item')).startswith("HEURE:")), None)
            old_ust = next((i['main_item'].replace("UST: ", "") for i in current_items_objs if str(i.get('main_item')).startswith("UST:")), None)
            old_note_obj = next((i for i in current_items_objs if str(i.get('main_item')) == "NOTE:"), None)

            final_time = desired_time if (desired_time and desired_time.upper() != 'HEURE') else old_time
            final_ust = utensils if (utensils and utensils.upper() != 'UST') else old_ust
            
            if note and note.upper() != 'NOTE':
                final_note = note
            else:
                final_note = " ".join(old_note_obj['sub_items']) if old_note_obj else None

            note_lines = textwrap.wrap(final_note, width=18) if final_note else []

            prefixes_to_clean = ["HEURE:", "UST:", "NOTE:", "*** DONNER AU PC", "*** ENLEVER", "PA #"]
            current_items_objs = [
                i for i in current_items_objs 
                if not any(str(i.get('main_item', '')).startswith(p) for p in prefixes_to_clean)
            ]

            if final_time: current_items_objs.append({"main_item": f"HEURE: {final_time}", "sub_items": []})
            if final_ust: current_items_objs.append({"main_item": f"UST: {final_ust}", "sub_items": []})
            if final_note: current_items_objs.append({"main_item": "NOTE:", "sub_items": note_lines})
            if donner_au_pc:
                display_pa = pa_number if pa_number else "???"
                current_items_objs.append({"main_item": f"*** DONNER AU PC (PA #{display_pa}) ***", "sub_items": []})
                current_items_objs.append({"main_item": "*** ENLEVER LE PAPIER JAUNE ***", "sub_items": []})

            final_json = json.dumps([json.dumps(obj) for obj in current_items_objs])
            
            # --- MISE À JOUR SYNCHRONISÉE ---
            query = "UPDATE orders SET items = ?, status = ? WHERE id = ?"
            cursor.execute(query, (final_json, 'Traitée', str_bid))
            
            conn_livreur = sqlite3.connect(LIVREUR_DB_PATH)
            conn_livreur.execute(query, (final_json, 'En attente', str_bid))
            
            conn.commit()
            conn_livreur.commit()
            
            # 3. RÉACTIVATION DIFFÉRÉE (KDS uniquement)
            # Définition propre de la fonction interne
            def reactivate_kds(order_id, db_path):
                try:
                    c = sqlite3.connect(db_path)
                    c.execute("UPDATE orders SET status = ? WHERE id = ?", ('En attente', order_id))
                    c.commit()
                    c.close()
                except Exception as e:
                    print(f"Erreur timer: {e}")

            # Déclenchement du délai de 3 secondes
            threading.Timer(3.0, reactivate_kds, args=[str_bid, self.db_path]).start()
            
            return True

        except Exception as e:
            logger.error(f"Erreur update_pa_details avec synchro: {e}")
            if conn: conn.rollback()
            if conn_livreur: conn_livreur.rollback()
            return False
        finally:
            if conn: conn.close()
            if conn_livreur: conn_livreur.close()

    def close_livraison_details(self, bid):
        """
        Récupère la commande, met à jour ses extras dans le JSON 'items',
        puis marque la commande comme 'Traitée'.
        """
        conn = self._get_connection()
        if not conn: return False
        
        try:
            cursor = conn.cursor()
            str_bid = str(bid).strip()

            # 1. On récupère d'abord les items actuels pour ne pas les écraser
            cursor.execute("SELECT items FROM orders WHERE id = ?", (str_bid,))
            row = cursor.fetchone()
            if not row:
                logger.error(f"Commande {str_bid} non trouvée pour fermeture.")
                return False

            # 2. On prépare les nouveaux extras
            # On suppose que vos extras sont stockés dans un champ spécifique ou dans le JSON items
            # Ici, on met à jour le statut et on pourrait mettre à jour le JSON si nécessaire
            
            # 3. Mise à jour finale : Statut 'Traitée'
            cursor.execute("""
                UPDATE orders 
                SET status = ? 
                WHERE id = ?
            """, ('Traitée', str_bid))
            
            conn.commit()
            logger.info(f"✅ Commande {str_bid} fermée et marquée comme 'Traitée'.")
            return True

        except Exception as e:
            logger.error(f"Erreur critique close_livraison_details pour {bid}: {e}")
            if conn: conn.rollback()
            return False
        finally:
            if conn: conn.close()


    def mark_specific_types_as_done_manual(self):
        """Marque les commandes par service_type comme 'Traitée'."""
        try:
            # Vérifie bien que ces noms correspondent exactement à ce qui est écrit sur tes tickets
            types_to_process = ('POUR EMPORTER', 'LIVRAISON')
            
            # Correction de la colonne : service_type au lieu de order_type
            query = """
                UPDATE orders 
                SET status = 'Traitée' 
                WHERE service_type IN (?, ?) 
                AND status != 'Traitée'
            """
            
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query, types_to_process)
            count = cursor.rowcount
            conn.commit()
            conn.close()
            
            if count > 0:
                logger.info(f"NETTOYAGE AUTO: {count} commandes ({types_to_process}) traitées.")
            return count
        except Exception as e:
            logger.error(f"Erreur lors du marquage automatique : {e}")
            return 0
    
    def mark_specific_types_as_done_all(self):
        """Marque les commandes par service_type comme 'Traitée' dans les deux bases."""
        try:
            types_to_process = ('POUR EMPORTER', 'LIVRAISON', 'COMMANDE', 'LIVREUR', '888')
            placeholders = ', '.join(['?'] * len(types_to_process))
            
            query = f"""
                UPDATE orders 
                SET status = 'Traitée' 
                WHERE service_type IN ({placeholders}) 
                AND status != 'Traitée'
            """
            
            total_count = 0
            
            # 1. Traitement Base Principale
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query, types_to_process)
            total_count += cursor.rowcount
            conn.commit()
            conn.close()
            
            # 2. Traitement Base Livreur
            conn_livreur = sqlite3.connect(LIVREUR_DB_PATH)
            cursor_livreur = conn_livreur.cursor()
            cursor_livreur.execute(query, types_to_process)
            total_count += cursor_livreur.rowcount
            conn_livreur.commit()
            conn_livreur.close()
            
            if total_count > 0:
                logger.info(f"NETTOYAGE AUTO (double base): {total_count} commandes ({types_to_process}) traitées.")
            
            return total_count
            
        except Exception as e:
            logger.error(f"Erreur lors du marquage automatique dans les deux bases : {e}")
            return 0

    def mark_all_as_done(self):
        """Marque TOUTES les commandes (quel que soit le service_type) comme 'Traitée' dans les deux bases."""
        total_count = 0
        
        # Requête pour mettre à jour tout ce qui n'est pas encore traité
        query = "UPDATE orders SET status = 'Traitée' WHERE status != 'Traitée'"
        
        try:
            # 1. Traitement BDD Principale
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query)
            count_main = cursor.rowcount
            conn.commit()
            conn.close()
            
            # 2. Traitement BDD Livreur
            conn_livreur = sqlite3.connect(LIVREUR_DB_PATH)
            cursor_livreur = conn_livreur.cursor()
            cursor_livreur.execute(query)
            count_livreur = cursor_livreur.rowcount
            conn_livreur.commit()
            conn_livreur.close()
            
            total_count = count_main + count_livreur
            
            if total_count > 0:
                logger.info(f"NETTOYAGE AUTO: {total_count} commandes marquées comme 'Traitée' dans les deux bases.")
                
            return total_count
            
        except Exception as e:
            logger.error(f"Erreur lors du marquage automatique de toutes les commandes : {e}")
            return 0

    # --- MÉTHODES DE COMMANDE (MODIFIÉE) ---
    def insert_order(self, bill_id, table_number, serveuse_name, service_type, items, status='En attente', creation_date=None, raw_content=None):
        """
        Insère une nouvelle commande.
        - Base principale: Toujours.
        - Clone livreur (kds_livreur_orders.db): Toujours (Vrai clone).
        - Consultation: Seulement si critères respectés.
        """
        conn = None
        conn_consul = None
        conn_livreur = None
        
        # 1. Création de l'ID unique
        unique_suffix = uuid.uuid4().hex[:8]
        safe_bill_id = f"{bill_id}-{unique_suffix}"
        
        if not creation_date:
            creation_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        items_json = json.dumps(items, ensure_ascii=False) 

        try:
            # --- 1. BASE PRINCIPALE (kds_orders.db) ---
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO orders (bill_id, table_number, serveuse_name, service_type, items, creation_date, status, raw_content)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (safe_bill_id, table_number, serveuse_name, service_type, items_json, creation_date, status, raw_content))
            
            cursor.execute("""
                REPLACE INTO bill_notes (bill_id, note_content, last_updated)
                VALUES (?, ?, ?)
            """, (safe_bill_id, "", creation_date))
            conn.commit()
            logger.info(f"Commande ajoutée (Base principale). ID: {safe_bill_id}")
            
            # --- 2. CLONE LIVREUR (kds_livreur_orders.db) ---
            # Ce bloc assure que le clone reçoit exactement les mêmes données que la base principale
            try:
                conn_livreur = sqlite3.connect(LIVREUR_DB_PATH)
                conn_livreur.execute("""
                    INSERT INTO orders (bill_id, table_number, serveuse_name, service_type, items, creation_date, status, raw_content)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (safe_bill_id, table_number, serveuse_name, service_type, items_json, creation_date, status, raw_content))
                conn_livreur.commit()
            except sqlite3.Error as e:
                logger.error(f"Erreur insertion dans clone livreur : {e}")

            # --- 3. BASE DE CONSULTATION ---
            est_livreur = (str(table_number) == "999")
            nom_serveuse_maj = str(serveuse_name).upper()
            est_inconnu_888 = (str(table_number) == "888" and "INCONNU" in nom_serveuse_maj)

            if not est_livreur and not est_inconnu_888:
                try:
                    conn_consul = self._get_consultation_connection()
                    conn_consul.execute("""
                        INSERT INTO orders_archive (
                            bill_id, table_number, serveuse_name, service_type, 
                            items, creation_date, status, archived_date, raw_content
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (safe_bill_id, table_number, serveuse_name, service_type, 
                          items_json, creation_date, status, creation_date, raw_content))
                    conn_consul.commit()
                    logger.info(f"Commande {safe_bill_id} dupliquée dans consultation.db")
                except sqlite3.Error as e_consul:
                    logger.error(f"Erreur archivage consultation.db : {e_consul}")

        except sqlite3.Error as e:
            logger.error(f"Erreur critique insertion ticket {bill_id} : {e}")
            if conn: conn.rollback()
        
        finally:
            if conn: conn.close()
            if conn_consul: conn_consul.close()
            if conn_livreur: conn_livreur.close()
        
    def add_new_order(self, bill_id, table_number, serveuse_name, service_type, items, status='En attente', creation_date=None, raw_content=None):
        """
        Ajoute une nouvelle commande. 
        Relaye les informations, y compris le ticket brut (raw_content), 
        à la méthode interne insert_order.
        """
        logger.info(f"Tentative d'ajout d'une nouvelle commande : Bill ID {bill_id}.")
        
        # On passe maintenant raw_content à insert_order
        return self.insert_order(
            bill_id=bill_id, 
            table_number=table_number, 
            serveuse_name=serveuse_name, 
            service_type=service_type, 
            items=items, 
            status=status, 
            creation_date=creation_date,
            raw_content=raw_content
        )

    def get_pending_orders_kds_alert(self):
        """
        Récupère toutes les commandes en cours depuis la base LIVREUR.
        Les regroupe par types incluant le contenu brut (BLOB).
        """
        conn = None
        rows = []
        
        # --- 1. LECTURE DE LA BASE LIVREUR ---
        try:
            # On se connecte spécifiquement au fichier du clone
            conn = sqlite3.connect(LIVREUR_DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, bill_id, table_number, serveuse_name, service_type, 
                       items, creation_date, status, raw_content 
                FROM orders 
                WHERE status NOT IN ('Traitée', 'Annulée','Pizza') 
                ORDER BY creation_date ASC
            """)
            rows = cursor.fetchall()
            
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de la récupération des commandes dans le clone '{LIVREUR_DB_PATH}' : {e}")
        finally:
            if conn: 
                conn.close()

        # --- 2. TRAITEMENT DES DONNÉES ---
        pending_orders_by_service = {
            'COMMANDE': [],
            'LIVRAISON': [],
            'LIVREUR': [],
            'POUR EMPORTER': []
        }
        
        for row in rows:
            try:
                raw_items = row[5]
                items_list = json.loads(raw_items) if raw_items else []
                
                order_data = {
                    'id': row[0],
                    'bill_id': row[1],
                    'table_number': str(row[2]).strip(),
                    'serveuse_name': str(row[3]).strip(),
                    'service_type': str(row[4]).upper(), 
                    'items': items_list,
                    'creation_date': row[6],
                    'status': row[7],
                    'raw_content': row[8]
                }
                
                stype = order_data['service_type']
                table = order_data['table_number']
                serveuse = order_data['serveuse_name']
                
                # --- LOGIQUE DE CLASSEMENT ---
                if table == "777" or serveuse == "777" or "LIVRAISON" in stype:
                    pending_orders_by_service['LIVRAISON'].append(order_data)
                
                elif table == "999" or serveuse == "999" or "LIVREUR" in stype:
                    pending_orders_by_service['LIVREUR'].append(order_data)
                
                elif table == "888" or "EMPORTER" in stype:
                    pending_orders_by_service['POUR EMPORTER'].append(order_data)
                
                else:
                    pending_orders_by_service['COMMANDE'].append(order_data)
                    
            except Exception as e:
                logger.warning(f"Erreur lors du traitement d'une ligne (Clone {LIVREUR_DB_PATH}, ID {row[0]}): {e}")
                continue
                
        return pending_orders_by_service
    
    def get_pending_orders_kds_alert_pizza(self):
        """
        Récupère toutes les commandes en cours depuis la base LIVREUR.
        Les regroupe par types incluant le contenu brut (BLOB).
        """
        conn = None
        rows = []
        
        # --- 1. LECTURE DE LA BASE LIVREUR ---
        try:
            # On se connecte spécifiquement au fichier du clone
            conn = sqlite3.connect(LIVREUR_DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, bill_id, table_number, serveuse_name, service_type, 
                       items, creation_date, status, raw_content 
                FROM orders 
                WHERE status NOT IN ('Traitée', 'Annulée' , 'En Attente') 
                ORDER BY creation_date ASC
            """)
            rows = cursor.fetchall()
            
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de la récupération des commandes dans le clone '{LIVREUR_DB_PATH}' : {e}")
        finally:
            if conn: 
                conn.close()

        # --- 2. TRAITEMENT DES DONNÉES ---
        pending_orders_by_service = {
            'COMMANDE': [],
            'LIVRAISON': [],
            'LIVREUR': [],
            'POUR EMPORTER': []
        }
        
        for row in rows:
            try:
                raw_items = row[5]
                items_list = json.loads(raw_items) if raw_items else []
                
                order_data = {
                    'id': row[0],
                    'bill_id': row[1],
                    'table_number': str(row[2]).strip(),
                    'serveuse_name': str(row[3]).strip(),
                    'service_type': str(row[4]).upper(), 
                    'items': items_list,
                    'creation_date': row[6],
                    'status': row[7],
                    'raw_content': row[8]
                }
                
                stype = order_data['service_type']
                table = order_data['table_number']
                serveuse = order_data['serveuse_name']
                
                # --- LOGIQUE DE CLASSEMENT ---
                if table == "777" or serveuse == "777" or "LIVRAISON" in stype:
                    pending_orders_by_service['LIVRAISON'].append(order_data)
                
                elif table == "999" or serveuse == "999" or "LIVREUR" in stype:
                    pending_orders_by_service['LIVREUR'].append(order_data)
                
                elif table == "888" or "EMPORTER" in stype:
                    pending_orders_by_service['POUR EMPORTER'].append(order_data)
                
                else:
                    pending_orders_by_service['COMMANDE'].append(order_data)
                    
            except Exception as e:
                logger.warning(f"Erreur lors du traitement d'une ligne (Clone {LIVREUR_DB_PATH}, ID {row[0]}): {e}")
                continue
                
        return pending_orders_by_service

    def get_pending_orders(self):
        """
        Récupère toutes les commandes en cours et les regroupe par types
        incluant le contenu brut (BLOB) pour la réimpression.
        """
        conn = None
        rows = []
        
        # --- 1. LECTURE DE LA BASE ---
        try:
            conn = self._get_connection()
            if conn:
                cursor = conn.cursor()
                # ⭐ AJOUT DE raw_content DANS LE SELECT (Index 8)
                cursor.execute("""
                    SELECT id, bill_id, table_number, serveuse_name, service_type, 
                           items, creation_date, status, raw_content 
                    FROM orders 
                    WHERE status NOT IN ('Traitée', 'Annulée') 
                    ORDER BY creation_date ASC
                """)
                rows = cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de la récupération des commandes : {e}")
        finally:
            if conn: 
                conn.close()

        # --- 2. TRAITEMENT DES DONNÉES ---
        pending_orders_by_service = {
            'COMMANDE': [],
            'LIVRAISON': [],
            'LIVREUR': [],
            'POUR EMPORTER': []
        }
        
        for row in rows:
            try:
                raw_items = row[5]
                items_list = json.loads(raw_items) if raw_items else []
                
                # Construction du dictionnaire avec le BLOB
                order_data = {
                    'id': row[0],
                    'bill_id': row[1],
                    'table_number': str(row[2]).strip(),
                    'serveuse_name': str(row[3]).strip(),
                    'service_type': str(row[4]).upper(), 
                    'items': items_list,
                    'creation_date': row[6],
                    'status': row[7],
                    'raw_content': row[8]  # ⭐ RÉCUPÉRATION DU BLOB BINAIRE
                }
                
                stype = order_data['service_type']
                table = order_data['table_number']
                serveuse = order_data['serveuse_name']
                
                # --- LOGIQUE DE CLASSEMENT ---
                # 1. LIVRAISON
                if table == "777" or serveuse == "777" or "LIVRAISON" in stype:
                    pending_orders_by_service['LIVRAISON'].append(order_data)
                
                # 2. LIVREUR
                elif table == "999" or serveuse == "999" or "LIVREUR" in stype:
                    pending_orders_by_service['LIVREUR'].append(order_data)
                
                # 3. POUR EMPORTER
                elif table == "888" or "EMPORTER" in stype:
                    pending_orders_by_service['POUR EMPORTER'].append(order_data)
                
                # 4. COMMANDE (Salle)
                else:
                    pending_orders_by_service['COMMANDE'].append(order_data)
                    
            except Exception as e:
                logger.warning(f"Erreur lors du traitement d'une ligne (ID {row[0]}): {e}")
                continue
                
        return pending_orders_by_service

    def get_pa_orders_with_history(self):
        """
        Récupère les PA (actifs + poubelle) limités aux 30 derniers
        et les formate en dictionnaire pour web_access.py.
        """
        conn = self._get_connection()
        rows = []
        try:
            cursor = conn.cursor()
            # On prend les PA actifs ET les 'Traitée' récents, limite à 30
            cursor.execute("""
                SELECT id, bill_id, table_number, serveuse_name, service_type, 
                       items, creation_date, status, raw_content 
                FROM orders 
                WHERE (table_number LIKE 'PA%' OR table_number = '888' OR service_type LIKE '%EMPORTER%')
                  AND status != 'Annulée'
                ORDER BY 
                    CASE WHEN status = 'En attente' THEN 1 ELSE 2 END ASC, 
                    creation_date DESC
                LIMIT 30
            """)
            rows = cursor.fetchall()
        finally:
            conn.close()

        # On prépare le format dictionnaire attendu par web_access.py
        data_filtered = {
            'POUR EMPORTER': []
        }

        for row in rows:
            try:
                raw_items = row[5]
                items_list = json.loads(raw_items) if raw_items else []
                data_filtered['POUR EMPORTER'].append({
                    'id': row[0],
                    'bill_id': row[1],
                    'table_number': str(row[2]).strip(),
                    'serveuse_name': str(row[3]).strip(),
                    'service_type': str(row[4]).upper(),
                    'items': items_list,
                    'creation_date': row[6],
                    'status': row[7],
                    'raw_content': row[8]
                })
            except Exception as e:
                logger.error(f"Erreur parsing item PA: {e}")
                continue
        
        return data_filtered
    
    def get_completed_orders(self):
        """
        Récupère toutes les commandes ayant le statut 'Traitée' ou 'Annulée'
        dans la BDD KDS principale (pour la Corbeille KDS).
        """
        conn = None
        rows = []
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, bill_id, table_number, serveuse_name, service_type, items, creation_date, status 
                FROM orders 
                WHERE status IN ('Traitée') 
                ORDER BY creation_date DESC
            """)
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de la récupération des commandes archivées : {e}")
        finally:
            if conn:
                conn.close()

        completed_orders = []
        
        for row in rows:
            try:
                # items est une LISTE de chaînes JSON. On la charge en Python.
                items_list = json.loads(row[5]) if row[5] else [] 
                order_data = {
                    'id': row[0],
                    'bill_id': row[1],
                    'table_number': row[2],
                    'serveuse_name': row[3],
                    'service_type': row[4],
                    'items': items_list, 
                    'creation_date': row[6],
                    'status': row[7]
                }
                completed_orders.append(order_data)
            except json.JSONDecodeError:
                logger.warning(f"Erreur de décodage JSON pour la commande ID {row[0]} dans l'archive. Ligne ignorée.")
                continue

        return completed_orders

    def get_archived_orders(self):
        """
        Récupère les commandes archivées avec l'aperçu de TOUS les VRAIS plats réels.
        """
        completed_orders_data = self.get_completed_orders()
        archived_orders = {} 
        
        # Liste des mots qui ne sont PAS des plats à ignorer dans l'aperçu court
        EXCLURE = ["LIVRAISON", "EMPORTER", "SUR PLACE", "TABLE", "COMMANDE", "SERVICE"]

        for data in completed_orders_data:
            try:
                apercu_lines = []
                main_items_only = [] 
                
                for item_json_str in data['items']:
                    item_dict = json.loads(item_json_str)
                    main_item_name = item_dict['main_item']
                    
                    # 1. On l'ajoute toujours à l'aperçu complet détaillé
                    apercu_lines.append(main_item_name)
                    
                    # 2. On vérifie si c'est un vrai plat pour l'aperçu court (short_preview)
                    is_service_info = any(mot in main_item_name.upper() for mot in EXCLURE)
                    
                    if not is_service_info:
                        main_items_only.append(main_item_name)
                    
                    for sub_item in item_dict.get('sub_items', []):
                        apercu_lines.append(f"   ↳ {sub_item}")
                
                # ⭐ On prend TOUS les VRAIS plats trouvés (sans limite de [:2])
                short_preview = ", ".join(main_items_only)
                        
                apercu = "\n".join(apercu_lines)
                
                order_dict = {
                    'commande_id': data['id'],
                    'table_number': data['table_number'],
                    'serveuse_name': data['serveuse_name'],
                    'apercu_contenu': apercu,
                    'short_preview': short_preview, # Contient maintenant TOUS les plats
                    'date_creation_str': data['creation_date'],
                    'completion_date': data['creation_date'], 
                    'status': data['status'],
                    'statut': data['status'],
                    'is_new': False 
                }
                
                archived_orders[data['bill_id']] = order_dict 
            except Exception as e:
                logger.error(f"Erreur de formatage Bill ID {data.get('bill_id')}: {e}")
            
        return archived_orders
        
    def delete_bill_note(self, bill_id):
        """
        Supprime la note associée à un bill_id donné dans la table bill_notes.
        Retourne le nombre de lignes affectées (normalement 1 si succès, 0 sinon).
        """
        conn = None
        rows_affected = 0
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Requête SQL pour supprimer l'enregistrement correspondant
            cursor.execute("""
                DELETE FROM bill_notes 
                WHERE bill_id = ?
            """, (bill_id,))
            
            conn.commit()
            rows_affected = cursor.rowcount 
            logger.info(f"Tentative de suppression de la note pour Facture {bill_id}. Lignes affectées: {rows_affected}")

        except sqlite3.Error as e:
            logger.error(f"Erreur SQLite lors de la suppression de la note pour Bill ID {bill_id} : {e}")
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la suppression de la note : {e}")
        finally:
            if conn:
                conn.close()
                
        return rows_affected

    def get_bill_note(self, bill_id):
        """Récupère la note pour un bill_id donné."""
        conn = None
        row = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT note_content FROM bill_notes WHERE bill_id = ?", (bill_id,))
            row = cursor.fetchone()
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de la récupération de la note pour Bill ID {bill_id} : {e}")
        finally:
            if conn:
                conn.close()

        result = row[0] if row and row[0] else ""
        return result

    # 💡 MODIFIÉ : Renommé en set_bill_note et ajout de la ligne de retour.
    def set_bill_note(self, bill_id, content):
        """
        Sauvegarde ou met à jour la note pour un bill_id. 
        Retourne le nombre de lignes affectées (1 si succès).
        """
        conn = None
        rows_affected = 0 # Initialisation du compteur
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute("""
                REPLACE INTO bill_notes (bill_id, note_content, last_updated)
                VALUES (?, ?, ?)
            """, (bill_id, content, now))
            
            conn.commit()
            rows_affected = cursor.rowcount # Récupère le nombre de lignes affectées
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de la sauvegarde de la note pour Bill ID {bill_id} : {e}")
        finally:
            if conn:
                conn.close()
                
        return rows_affected # 👈 Retourne le nombre de lignes pour la vérification dans postit_widget.py

    

    def save_bill_note(self, bill_id, content):
        """Sauvegarde ou met à jour la note pour un bill_id."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute("""
                REPLACE INTO bill_notes (bill_id, note_content, last_updated)
                VALUES (?, ?, ?)
            """, (bill_id, content, now))
            
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de la sauvegarde de la note pour Bill ID {bill_id} : {e}")
        finally:
            if conn:
                conn.close()
    
    
        

    def get_all_pending_orders_flat(self, bill_ids=None):
        """
        Récupère TOUS les ordres en attente (ou sélectionnés), 
        retournant une liste plate d'objets complets (bill_id, items, etc.). 
        """
        conn = None
        rows = []
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            base_query = """
                SELECT bill_id, items FROM orders 
                WHERE status NOT IN ('Traitée') 
            """
            params = []
            
            if bill_ids and len(bill_ids) > 0:
                placeholders = ','.join('?' * len(bill_ids))
                query = f"{base_query} AND bill_id IN ({placeholders})"
                params = bill_ids
            else:
                query = base_query
                
            cursor.execute(query, params)
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de la récupération plate des commandes en attente : {e}")
        finally:
            if conn:
                conn.close()
        
        pending_orders_flat = []
        
        for row in rows:
            try:
                # items est une LISTE de chaînes JSON. On la charge en Python.
                items_list = json.loads(row[1]) 
                pending_orders_flat.append({
                    'bill_id': row[0],
                    'items': items_list 
                })
            except json.JSONDecodeError:
                logger.warning(f"Erreur de décodage JSON des items pour la facture {row[0]}. Ligne ignorée.")
                continue 
            
        return pending_orders_flat

    def get_all_pending_items_for_kds_total(self, bill_ids=None):
        """
        Récupère tous les items des commandes en attente (ou sélectionnées) 
        pour calculer le total KDS.
        
        ⭐ MODIFIÉ pour décoder la structure JSON et inclure les sous-items dans le total.
        """
        conn = None
        rows = []
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if bill_ids and len(bill_ids) > 0:
                placeholders = ','.join('?' * len(bill_ids))
                query = f"""
                    SELECT items FROM orders 
                    WHERE status NOT IN ('Traitée') AND bill_id IN ({placeholders})
                """
                cursor.execute(query, bill_ids)
            else:
                query = """
                    SELECT items FROM orders 
                    WHERE status NOT IN ('Traitée')
                """
                cursor.execute(query)
                
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de la récupération des items pour le total KDS : {e}")
        finally:
            if conn:
                conn.close()
        
        all_items = {}
        
        for row in rows:
            try:
                # 1. Charger la liste des chaînes JSON d'items
                items_list = json.loads(row[0])
                
                for item_json_str in items_list:
                    # 2. Charger l'item principal/sous-item structuré
                    item_dict = json.loads(item_json_str)
                    
                    # --- Traitement de l'Item Principal (main_item) ---
                    main_item_str = item_dict.get('main_item', '').strip()
                    if main_item_str:
                        match = re.match(r'^(\d+)\s+x\s+(.*)', main_item_str, re.IGNORECASE)
                        
                        if match:
                            quantity = int(match.group(1))
                            name = match.group(2).strip()
                        else:
                            quantity = 1
                            name = main_item_str
                        
                        all_items[name] = all_items.get(name, 0) + quantity
                        
                    # --- Traitement des Sous-Items (sub_items) ---
                    for sub_item_str in item_dict.get('sub_items', []):
                        sub_item_str = sub_item_str.strip()
                        if not sub_item_str: continue
                            
                        sub_match = re.match(r'^(\d+)\s+x\s+(.*)', sub_item_str, re.IGNORECASE)
                        
                        if sub_match:
                            sub_quantity = int(sub_match.group(1))
                            sub_name = sub_match.group(2).strip()
                        else:
                            sub_quantity = 1
                            sub_name = sub_item_str
                            
                        # Les sous-items sont comptés comme des items à part
                        all_items[sub_name] = all_items.get(sub_name, 0) + sub_quantity
                        
            except (json.JSONDecodeError, IndexError, ValueError, AttributeError) as e:
                logger.error(f"Erreur de traitement/format JSON pour un item : {row[0]}. Erreur: {e}")
                continue 
        
        return all_items
    
    def get_new_order_count_since(self, last_check_time):
        """
        Compte le nombre de commandes 'En attente' créées APRES l'heure fournie.
        """
        conn = None
        count = 0
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(id) FROM orders
                WHERE status = 'En attente' AND creation_date > ?
            """, (last_check_time,))
            
            count = cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"Erreur lors du comptage de nouvelles commandes : {e}")
        finally:
            if conn:
                conn.close()
        return count
    
    
    
    def reset_bill_status_to_pending(self, bill_id):
        """
        Rétablit le statut de TOUTES les commandes liées à un bill_id 
        (généralement depuis 'Traitée'/'Annulée') à 'En attente'.
        """
        logger.warning(f"Réinitialisation du statut à 'En attente' pour Bill ID {bill_id}.")
        return self.set_order_status_by_bill_id(bill_id, 'En attente')

    # --- MÉTHODES DE SUPPRESSION (Vérifiées pour être KDS-only) ---
    def clear_all_data(self):
        """
        Supprime TOUTES les données dans la BDD KDS et le clone Livreur.
        """
        conn = None
        conn_livreur = None
        orders_deleted = 0
        notes_deleted = 0
        
        logger.critical("ATTENTION: Suppression totale des données (KDS + Clone Livreur).")
        
        try:
            # Nettoyage base principale
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM orders")
            orders_deleted = cursor.rowcount
            cursor.execute("DELETE FROM bill_notes")
            notes_deleted = cursor.rowcount
            conn.commit()
            
            # Nettoyage clone livreur
            conn_livreur = sqlite3.connect(LIVREUR_DB_PATH)
            conn_livreur.execute("DELETE FROM orders")
            conn_livreur.commit()
            
            logger.critical(f"Nettoyage complet : {orders_deleted} commandes supprimées des deux bases.")
        except sqlite3.Error as e:
            logger.error(f"Erreur lors du nettoyage complet : {e}")
        finally:
            if conn: conn.close()
            if conn_livreur: conn_livreur.close()
        
        return orders_deleted, notes_deleted

    def mark_all_as_treated_livreur(self):
        """
        Marque TOUTES les commandes de la base LIVREUR comme 'Traitée'.
        """
        conn = None
        row_count = 0
        try:
            # Connexion directe à la base du clone livreur
            conn = sqlite3.connect(LIVREUR_DB_PATH)
            cursor = conn.cursor()
            
            # Mise à jour de toutes les commandes non traitées/annulées
            cursor.execute("""
                UPDATE orders 
                SET status = 'Traitée' 
                WHERE status NOT IN ('Traitée', 'Annulée')
            """)
            
            conn.commit()
            row_count = cursor.rowcount
            logger.info(f"✅ Succès (Livreur) : {row_count} commandes marquées comme 'Traitée'.")
            
        except sqlite3.Error as e:
            logger.error(f"❌ Erreur SQL lors du marquage en 'Traitée' (Livreur) : {e}")
            if conn: conn.rollback()
        finally:
            if conn: conn.close()
                
        return row_count
            
    def delete_completed_and_cancelled_orders(self):
        """
        Supprime les commandes 'Traitée'/'Annulée' dans la BDD KDS et le clone Livreur.
        """
        conn = None
        conn_livreur = None
        row_count = 0
        
        try:
            # Nettoyage base principale
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM orders WHERE status IN ('Traitée', 'Annulée')")
            row_count = cursor.rowcount
            conn.commit()
            
            # Nettoyage clone livreur
            conn_livreur = sqlite3.connect(LIVREUR_DB_PATH)
            conn_livreur.execute("DELETE FROM orders WHERE status IN ('Traitée', 'Annulée')")
            conn_livreur.commit()
            
            logger.warning(f"Corbeille vidée : {row_count} commandes supprimées des deux bases.")
        except sqlite3.Error as e:
            logger.error(f"Erreur lors du vidage de la corbeille : {e}")
        finally:
            if conn: conn.close()
            if conn_livreur: conn_livreur.close()
            
        return row_count

# --------------------------------------------------------------------------------
# SIMULATION DE DONNÉES 
# --------------------------------------------------------------------------------

def initialize_data(db_manager):
    """Insère des données de test si la base est vide."""
    
    all_pending = db_manager.get_pending_orders()
    # Vérifie si au moins une liste de commandes en attente a des éléments
    has_pending = any(len(orders) > 0 for orders in all_pending.values())
    
    if has_pending:
        #logger.info("La base de données contient déjà des commandes en attente. Ignoré l'initialisation des données de test.")
        return

    # Si vous voulez ajouter des données de simulation, le format de 'items' est maintenant:
    # [ json.dumps({"main_item": "1 x POUTINE", "sub_items": ["GARNIE", "EXTRA SAUCE"]}), 
    #   json.dumps({"main_item": "2 x SALADE CESAR", "sub_items": ["PEU DE POULET"]}) ]
    
    # ... (le reste de la fonction d'initialisation n'est pas modifié dans son appel à db_manager.add_new_order)