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
        """Crée les tables KDS et la table 'orders_archive' dans la BDD de consultation."""
        conn_kds = None
        conn_consultation = None
        try:
            # 1. Tables de la BDD KDS principale
            conn_kds = self._get_connection()
            cursor_kds = conn_kds.cursor()
            
            # Table des commandes (orders)
            cursor_kds.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bill_id TEXT NOT NULL,
                    table_number INTEGER NOT NULL,
                    serveuse_name TEXT NOT NULL, 
                    service_type TEXT NOT NULL, 
                    items TEXT NOT NULL,
                    creation_date TEXT NOT NULL,
                    status TEXT NOT NULL
                )
            """)
            
            # Table des notes de facture (bill_notes)
            cursor_kds.execute("""
                CREATE TABLE IF NOT EXISTS bill_notes (
                    bill_id TEXT PRIMARY KEY,
                    note_content TEXT,
                    last_updated TEXT
                )
            """)
            conn_kds.commit()
            logger.info("Tables KDS ('orders', 'bill_notes') vérifiées/créées.")
            
            # 2. Table des commandes archivées (orders_archive) - Base de consultation
            conn_consultation = self._get_consultation_connection()
            cursor_consultation = conn_consultation.cursor()
            
            # Table orders_archive (même structure + archived_date)
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
                    archived_date TEXT NOT NULL
                )
            """)
            conn_consultation.commit()
            logger.info("Table 'orders_archive' dans consultation.db vérifiée/créée.")
            
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de la création des tables : {e}")
        finally:
            if conn_kds:
                conn_kds.close()
            if conn_consultation:
                conn_consultation.close()
    # ⭐ MÉTHODE À AJOUTER POUR CORRIGER L'AttributeError

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

    # ⭐ MÉTHODE CRITIQUE : Changer le statut d'une commande (pour Fermer/Traiter/Post-it)
    def set_order_status_by_bill_id(self, bill_id: str, new_status: str) -> int:
        """
        Met à jour le statut d'une commande. 
        Recherche par correspondance partielle car bill_id contient un suffixe UUID.
        """
        conn = self._get_connection()
        if not conn: return 0
        row_count = 0
        
        try:
            cursor = conn.cursor()
            clean_bid = str(bill_id).strip()
            
            # On utilise LIKE car vos IDs en DB ressemblent à "106-a1b2c3d4"
            # On cherche tout ce qui commence par l'ID fourni suivi du tiret
            cursor.execute("""
                UPDATE orders 
                SET status = ? 
                WHERE bill_id = ? OR bill_id LIKE ?
            """, (new_status, clean_bid, f"{clean_bid}-%"))
            
            conn.commit()
            row_count = cursor.rowcount
            
            if row_count > 0:
                logger.info(f"✅ Succès : {row_count} ligne(s) mise(s) à jour pour l'ID {clean_bid}")
            else:
                logger.warning(f"⚠️ Échec : Aucune facture commençant par {clean_bid} n'a été trouvée.")
                
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
    
    
    def add_items_to_existing_bill(self, table_number, serveuse_name, new_items_list):
        """
        Supprime l'ancienne commande et en crée une nouvelle.
        Si une HEURE, une NOTE ou des UST sont déjà présents, ils sont MIS À JOUR
        au lieu d'être additionnés. La commande repasse en 'En attente'.
        """
        conn = self._get_connection()
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 1. On récupère la dernière commande (peu importe le statut)
            cursor.execute("""
                SELECT * FROM orders 
                WHERE table_number = ? AND serveuse_name = ? 
                ORDER BY id DESC LIMIT 1
            """, (str(table_number), str(serveuse_name)))
            
            row = cursor.fetchone()
            
            if row:
                # 2. Décodage des items actuels
                current_items_objs = []
                raw_items_data = row['items']
                if raw_items_data:
                    try:
                        loaded = json.loads(raw_items_data)
                        for item in (loaded if isinstance(loaded, list) else [loaded]):
                            current_items_objs.append(json.loads(item) if isinstance(item, str) else item)
                    except:
                        current_items_objs = []

                # --- 3. LOGIQUE DE MISE À JOUR (REMPLACEMENT) ---
                prefixes_to_manage = {
                    "HEURE:": "HEURE:",
                    "NOTE:": "NOTE:",
                    "UST:": "UST:"
                }

                for new_item_raw in new_items_list:
                    new_obj = json.loads(new_item_raw) if isinstance(new_item_raw, str) else new_item_raw
                    new_text = new_obj.get('main_item', "")
                    
                    # On cherche si le nouvel item commence par un de nos préfixes
                    found_prefix = None
                    for prefix in prefixes_to_manage:
                        if new_text.startswith(prefix):
                            found_prefix = prefix
                            break
                    
                    if found_prefix:
                        # On SUPPRIME l'ancien item qui avait ce préfixe avant d'ajouter le nouveau
                        current_items_objs = [
                            item for item in current_items_objs 
                            if not (isinstance(item, dict) and item.get('main_item', "").startswith(found_prefix))
                        ]
                    
                    # On ajoute le nouvel item (qui remplace donc l'ancien s'il existait)
                    current_items_objs.append(new_obj)

                # 4. Préparation des données pour la nouvelle commande
                final_items_json_strings = [json.dumps(obj) for obj in current_items_objs]
                order_data = dict(row)
                old_id = order_data.pop('id') # On enlève l'ID pour en générer un nouveau
                
                # Mise à jour forcée
                order_data['status'] = 'En attente'
                order_data['items'] = json.dumps(final_items_json_strings)
                
                # Update de la date pour le tri KDS
                for date_col in ['date', 'timestamp', 'created_at']:
                    if date_col in order_data:
                        order_data[date_col] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # 5. Cycle Suppression / Insertion (Nouvel ID)
                cursor.execute("DELETE FROM orders WHERE id = ?", (old_id,))

                columns = order_data.keys()
                placeholders = ":" + ", :".join(columns)
                sql = f"INSERT INTO orders ({', '.join(columns)}) VALUES ({placeholders})"
                
                cursor.execute(sql, order_data)
                
                conn.commit()
                logger.info(f"DB: Commande #{old_id} mise à jour (Remplacement Heure/Note) et réactivée.")
                return True
            
            return False

        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour/réactivation : {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    import threading  # <--- AJOUTEZ CECI EN HAUT DE VOTRE FICHIER

# ... (votre classe DBManager)

    def update_pa_details(self, bid, note, desired_time, utensils):
        """
        Met à jour les détails (HEURE, NOTE, UST). 
        Découpe la NOTE en plusieurs lignes de 20 caractères max dans les sub_items.
        """
        
        conn = self._get_connection()
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            str_bid = str(bid)
            
            cursor.execute("SELECT * FROM orders WHERE id = ?", (str_bid,))
            row = cursor.fetchone()
            if not row:
                return False

            # 1. Décodage sécurisé
            current_items_objs = []
            raw_items_data = row['items']
            if raw_items_data:
                try:
                    loaded = json.loads(raw_items_data)
                    for item in (loaded if isinstance(loaded, list) else [loaded]):
                        current_items_objs.append(json.loads(item) if isinstance(item, str) else item)
                except:
                    current_items_objs = []

            # --- LOGIQUE DE DÉCOUPAGE DE LA NOTE ---
            note_valide = note if (note and note.upper() != 'NOTE') else None
            note_lines = []
            if note_valide:
                # textwrap.wrap coupe à 20 carac en respectant les espaces entre les mots
                note_lines = textwrap.wrap(note_valide, width=18)

            # 2. Logique de Mise à jour des extras existants
            extras_map = {
                "HEURE:": desired_time if (desired_time and desired_time.upper() != 'HEURE') else None,
                "UST:": utensils if (utensils and utensils.upper() != 'UST') else None,
                "NOTE:": note_valide # Utilisé pour flagger la présence
            }

            found_keys = set()
            for item in current_items_objs:
                if isinstance(item, dict):
                    main_item = str(item.get('main_item', ""))
                    
                    # Gestion Spécifique de la NOTE (avec sub_items)
                    if main_item.startswith("NOTE:"):
                        if note_valide:
                            item['main_item'] = "NOTE:"
                            item['sub_items'] = note_lines # On met les morceaux ici
                            found_keys.add("NOTE:")
                        else:
                            item['to_delete'] = True
                        continue

                    # Gestion HEURE et UST
                    for prefix in ["HEURE:", "UST:"]:
                        if main_item.startswith(prefix):
                            new_val = extras_map[prefix]
                            if new_val:
                                item['main_item'] = f"{prefix} {new_val}"
                                item['sub_items'] = [] # Nettoyage au cas où
                                found_keys.add(prefix)
                            else:
                                item['to_delete'] = True
                            break
            
            # Suppression des items marqués
            current_items_objs = [i for i in current_items_objs if not i.get('to_delete')]

            # 3. Ajout des nouveaux si non trouvés
            if extras_map["HEURE:"] and "HEURE:" not in found_keys:
                current_items_objs.append({"main_item": f"HEURE: {extras_map['HEURE:']}", "sub_items": []})
            
            if extras_map["UST:"] and "UST:" not in found_keys:
                current_items_objs.append({"main_item": f"UST: {extras_map['UST:']}", "sub_items": []})

            if extras_map["NOTE:"] and "NOTE:" not in found_keys:
                current_items_objs.append({"main_item": "NOTE:", "sub_items": note_lines})

            # 4. Mise à jour en base
            final_items_json_strings = [json.dumps(obj) for obj in current_items_objs]
            
            cursor.execute("""
                UPDATE orders 
                SET items = ?, status = ? 
                WHERE id = ?
            """, (json.dumps(final_items_json_strings), 'Traitée', str_bid))
            
            conn.commit()
            
            # 5. Timer pour retour à 'En attente'
            def reset_to_pending():
                try:
                    conn_timer = self._get_connection()
                    cur = conn_timer.cursor()
                    cur.execute("UPDATE orders SET status = ? WHERE id = ?", ('En attente', str_bid))
                    conn_timer.commit()
                    conn_timer.close()
                except Exception as e:
                    logger.error(f"Erreur reset {str_bid}: {e}")

            threading.Timer(1.0, reset_to_pending).start()
            return True

        except Exception as e:
            logger.error(f"Erreur critique update_pa_details pour {bid}: {e}")
            if conn: conn.rollback()
            return False
        finally:
            if conn: conn.close()

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

    def mark_specific_types_as_done(self):
        """Marque les commandes par service_type comme 'Traitée'."""
        try:
            # Vérifie bien que ces noms correspondent exactement à ce qui est écrit sur tes tickets
            types_to_process = ('POUR EMPORTER', 'LIVRAISON', 'LIVREUR')
            
            # Correction de la colonne : service_type au lieu de order_type
            query = """
                UPDATE orders 
                SET status = 'Traitée' 
                WHERE service_type IN (?, ?, ?) 
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

    # --- MÉTHODES DE COMMANDE (MODIFIÉE) ---
    def insert_order(self, bill_id, table_number, serveuse_name, service_type, items, status='En attente', creation_date=None):
        """
        Insère une nouvelle ligne de commande en garantissant l'unicité par un suffixe de 8 caractères.
        Gère l'insertion dans la base principale et l'archive de consultation de manière sécurisée.
        """
        conn = None
        conn_consul = None # Pour la base d'archive
        
        # 1. Création de l'ID unique (ID original + 8 caractères aléatoires)
        unique_suffix = uuid.uuid4().hex[:8]
        safe_bill_id = f"{bill_id}-{unique_suffix}"
        
        # 2. Gestion de la date
        if not creation_date:
            creation_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Encodage des items
        items_json = json.dumps(items, ensure_ascii=False) 

        try:
            # --- BASE PRINCIPALE ---
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 3. Insertion avec le safe_bill_id
            cursor.execute("""
                INSERT INTO orders (bill_id, table_number, serveuse_name, service_type, items, creation_date, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (safe_bill_id, table_number, serveuse_name, service_type, items_json, creation_date, status))
            
            # 4. Note de facture (obligatoire pour le fonctionnement du KDS)
            cursor.execute("""
                REPLACE INTO bill_notes (bill_id, note_content, last_updated)
                VALUES (?, ?, ?)
            """, (safe_bill_id, "", creation_date))
            
            conn.commit()
            logger.info(f"Commande ajoutée avec succès. ID unique: {safe_bill_id}")
            
           
            est_livreur = (str(table_number) == "999")
            
            # 2. Est-ce la table 888 ET le nom contient "INCONNU" ?
            # On met tout en MAJUSCULES pour que ça marche avec "Inconnu", "INCONNU", etc.
            nom_serveuse_maj = str(serveuse_name).upper()
            est_inconnu_888 = (str(table_number) == "888" and "INCONNU" in nom_serveuse_maj)

            # On n'enregistre dans CONSULTATION que si ce n'est NI l'un NI l'autre
            if not est_livreur and not est_inconnu_888:
                try:
                    conn_consul = self._get_consultation_connection()
                    cursor_consul = conn_consul.cursor()
                    
                    # Insertion avec archived_date pour respecter la contrainte NOT NULL
                    cursor_consul.execute("""
                        INSERT INTO orders_archive (
                            bill_id, table_number, serveuse_name, service_type, 
                            items, creation_date, status, archived_date
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        safe_bill_id, table_number, serveuse_name, service_type, 
                        items_json, creation_date, status, creation_date
                    ))
                    
                    conn_consul.commit()
                    logger.info(f"Commande {safe_bill_id} dupliquée dans l'archive consultation.")
                except sqlite3.Error as e_consul:
                    logger.error(f"Erreur lors de l'archivage (consultation.db) : {e_consul}")
                    if conn_consul: conn_consul.rollback()
            else:
                # Log précis pour tes vérifications
                raison = "LIVREUR (999)" if est_livreur else "TEST/ERREUR (888 + Nom contient INCONNU)"
                logger.info(f"Commande {safe_bill_id} ignorée pour l'archive (Raison: {raison})")

        except sqlite3.Error as e:
            logger.error(f"Erreur lors de l'insertion du ticket {bill_id} dans la base principale : {e}")
            if conn: conn.rollback()
        
        finally:
            # ⭐ SÉCURITÉ : Fermeture impérative de toutes les connexions
            if conn:
                conn.close()
            if conn_consul:
                conn_consul.close()
        
    def add_new_order(self, bill_id, table_number, serveuse_name, service_type, items, status='En attente', creation_date=None):
        """
        Ajoute une nouvelle commande. 
        Appelle la méthode interne insert_order avec la date optionnelle.
        """
        logger.info(f"Tentative d'ajout d'une nouvelle commande : Bill ID {bill_id}.")
        return self.insert_order(bill_id, table_number, serveuse_name, service_type, items, status, creation_date)
        # --- MÉTHODES DE LECTURE ---

    def get_pending_orders(self):
        """
        Récupère toutes les commandes en cours et les regroupe par types
        (COMMANDE, LIVRAISON, LIVREUR, POUR EMPORTER).
        777 -> LIVRAISON, 999 -> LIVREUR, 888 -> EMPORTER.
        """
        conn = None
        rows = []
        
        # --- 1. LECTURE DE LA BASE (Le plus court possible) ---
        try:
            conn = self._get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, bill_id, table_number, serveuse_name, service_type, items, creation_date, status 
                    FROM orders 
                    WHERE status NOT IN ('Traitée', 'Annulée') 
                    ORDER BY creation_date ASC
                """)
                rows = cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de la récupération des commandes : {e}")
        finally:
            # ⭐ CRUCIAL : On ferme la connexion immédiatement après la lecture 
            # pour laisser la place aux threads d'écriture (SerialReader).
            if conn: 
                conn.close()

        # --- 2. TRAITEMENT DES DONNÉES (Hors connexion SQL) ---
        pending_orders_by_service = {
            'COMMANDE': [],
            'LIVRAISON': [],
            'LIVREUR': [],
            'POUR EMPORTER': []
        }
        
        for row in rows:
            try:
                # Sécurité sur la désérialisation JSON
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
                    'status': row[7]
                }
                
                stype = order_data['service_type']
                table = order_data['table_number']
                serveuse = order_data['serveuse_name']
                
                # --- LOGIQUE DE CLASSEMENT ---
                
                # 1. LIVRAISON (Table 777 ou Serveuse 777 ou mot clé)
                if table == "777" or serveuse == "777" or "LIVRAISON" in stype:
                    pending_orders_by_service['LIVRAISON'].append(order_data)
                
                # 2. LIVREUR (Table 999 ou Serveuse 999 ou mot clé)
                elif table == "999" or serveuse == "999" or "LIVREUR" in stype:
                    pending_orders_by_service['LIVREUR'].append(order_data)
                
                # 3. POUR EMPORTER (Table 888 ou mot clé)
                elif table == "888" or "EMPORTER" in stype:
                    pending_orders_by_service['POUR EMPORTER'].append(order_data)
                
                # 4. COMMANDE (Par défaut : Salle)
                else:
                    pending_orders_by_service['COMMANDE'].append(order_data)
                    
            except Exception as e:
                # Si un ticket est corrompu, on log l'erreur et on passe au suivant sans crasher
                logger.warning(f"Erreur lors du traitement d'une ligne (ID {row[0]}): {e}")
                continue
                
        return pending_orders_by_service
    
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
        Récupère les commandes archivées avec un aperçu des 2 premiers PLATS réels.
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
                    # On vérifie que le texte n'est pas dans notre liste d'exclusion
                    is_service_info = any(mot in main_item_name.upper() for mot in EXCLURE)
                    
                    if not is_service_info:
                        main_items_only.append(main_item_name)
                    
                    for sub_item in item_dict.get('sub_items', []):
                        apercu_lines.append(f"  ↳ {sub_item}")
                
                # ⭐ On prend les 2 premiers VRAIS plats trouvés
                short_preview = ", ".join(main_items_only[:2])
                if len(main_items_only) > 2:
                    short_preview += "..."
                        
                apercu = "\n".join(apercu_lines)
                
                order_dict = {
                    'commande_id': data['id'],
                    'table_number': data['table_number'],
                    'serveuse_name': data['serveuse_name'],
                    'apercu_contenu': apercu,
                    'short_preview': short_preview, # Contient maintenant juste les plats
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
        🗑️ Supprime TOUTES les commandes de la table 'orders' et 
        TOUTES les notes de la table 'bill_notes' DANS LA BDD KDS SEULEMENT.
        L'archive (consultation.db) N'EST PAS AFFECTÉE.
        """
        conn = None
        orders_deleted = 0
        notes_deleted = 0
        logger.critical("ATTENTION: Suppression de TOUTES les données de la BDD KDS principale.")
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Supprimer toutes les lignes de la table orders (KDS)
            cursor.execute("DELETE FROM orders")
            orders_deleted = cursor.rowcount
            
            # Supprimer toutes les lignes de la table bill_notes (KDS)
            cursor.execute("DELETE FROM bill_notes")
            notes_deleted = cursor.rowcount
            
            conn.commit()
            logger.critical(f"Nettoyage complet effectué : {orders_deleted} commandes et {notes_deleted} notes supprimées de kds_orders.db.")
        except sqlite3.Error as e:
            logger.error(f"Erreur critique lors du nettoyage complet de la BDD KDS : {e}")
        finally:
            if conn:
                conn.close()
        
        return orders_deleted, notes_deleted 
        
    def delete_completed_and_cancelled_orders(self):
        """
        ✅ Fonction Corbeille : Supprime définitivement de la BDD KDS 
        toutes les commandes ayant le statut 'Traitée' ou 'Annulée'.
        L'archive (consultation.db) N'EST PAS AFFECTÉE (Clonage effectué à l'insertion).
        """
        conn = None
        row_count = 0
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM orders
                WHERE status IN ('Traitée', 'Annulée')
            """)
            
            row_count = cursor.rowcount
            conn.commit()
            logger.warning(f"Corbeille vidée : {row_count} commandes 'Traitée'/'Annulée' supprimées définitivement de kds_orders.db.")
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de la suppression des commandes archivées : {e}")
        finally:
            if conn:
                conn.close()
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