# db_maindish.py

import sqlite3
import json
import os 
import shutil 
import re

from typing import List, Tuple, Union

class MainDishDBManager:
    """
    Couche de gestion des opérations CRUD pour la table 'main_dishes' 
    dans 'kds_constants.db', incluant l'exportation/importation JSON et DB avec des mesures de sécurité.
    """
    DB_FILE = 'kds_constants.db'

    def __init__(self):
        """Initialise la connexion à la base de données et crée la table si elle n'existe pas."""
        # Utilise la fonction d'initialisation pour la structure par Nom du Plat (plus simple pour le CRUD)
        self._initialize_db() 
        
        # ⭐ Votre liste originale de l'utilisateur avec les prix ajustés du PDF
        # Format: (Nom_du_Plat, Prix_du_Plat)
        self.initial_dishes_list: List[Tuple[str, float]] = [
            # Plats de déjeuner/petits plats (prix génériques ou conservés)
            ('2 GAUFFRES FR', 12.99), ('ENF. CHOCO BANANE', 8.50), ('FRICASSE FOREST', 15.99), 
            ('FRICASSE VEGE', 14.99), ('LE BRUNCH', 16.99), ('LE QUEBECOIS', 17.99), 
            ('MENAGE', 16.99), ('NO 1 OEUF', 10.99), ('NO 2 OEUF', 12.99), 
            ('NO 3 OEUF + VIANDE', 14.50), ('NO 4 OEUF + VIANDE', 15.99), 

            # Pizzas (prix génériques ou ajustés)
            ('BAMBINO', 11.99), ('BAMBINO ANANAS', 11.99), ('BAMBINO CHAMPIGNON', 11.99), 
            ('BAMBINO COTES LEVEE', 14.99), ('BAMBINO FAJITAS', 13.99), ('BAMBINO FROM', 11.99), 
            ('BAMBINO GARNIE', 12.99), ('BAMBINO GREC', 12.99), ('BAMBINO GUETTI', 11.99), 
            ('BAMBINO MEXICAINE', 12.99), ('BAMBINO PEPE', 11.99), ('BAMBINO SPECIAL', 13.99), 
            ('BAMBINO VEGE', 11.99), ('BAMBINO FRUITS MER', 15.99), ('BAMBINO 4 FROM ANCIENNE', 12.99), 
            ('BAMBINO 4 FROM PLAIN', 12.99), 
            ('SMALL', 14.99), ('SMALL ANANAS', 14.99), ('SMALL CHAMPIGNON', 14.99), 
            ('SMALL COTES LEVEE', 17.99), ('SMALL FAJITAS', 16.99), ('SMALL FROM', 14.99), 
            ('SMALL GARNIE', 15.99), ('SMALL GRECQUE', 15.99), ('SMALL GUETTI', 14.99), 
            ('SMALL MEXICAINE', 15.99), ('SMALL PEPE', 14.99), ('SMALL SPECIAL', 16.99), 
            ('SMALL VEGE', 14.99), ('SMALL FRUITS MER', 18.99), ('SMALL 4 FROM ANCIENNE', 15.99), 
            ('SMALL 4 FROM PLAIN', 15.99), 
            ('MEDIUM', 18.99), ('MEDIUM ANANAS', 18.99), ('MEDIUM CHAMPIGNON', 18.99), 
            ('MEDIUM COTES LEVEE', 21.99), ('MEDIUM FAJITAS', 20.99), ('MEDIUM FROM', 18.99), 
            ('MEDIUM GARNI', 19.99), ('MEDIUM GRECQUE', 19.99), ('MEDIUM GUETTI', 18.99), 
            ('MEDIUM MEXICAINE', 19.99), ('MEDIUM PEPE', 18.99), ('MEDIUM SPECIAL', 20.99), 
            ('MEDIUM VEGE', 18.99), ('MEDIUM FRUITS MER', 22.99), ('MEDIUM 4 FROM ANCIENNE', 19.99), 
            ('MEDIUM 4 FROM PLAIN', 19.99), 
            ('LARGE', 22.99), ('LARGE ANANAS', 22.99), ('LARGE CHAMPIGNON', 22.99), 
            ('LARGE COTES LEVEE', 25.99), ('LARGE FAJITAS', 24.99), ('LARGE FROM', 22.99), 
            ('LARGE GARNIE', 23.99), ('LARGE GRECQUE', 23.99), ('LARGE GUETTI', 22.99), 
            ('LARGE MEXICAINE', 23.99), ('LARGE PEPE', 22.99), ('LARGE SPECIAL', 24.99), 
            ('LARGE VEGE', 22.99), ('LARGE FRUITS MER', 26.99), ('LARGE 4 FROM ANCIENNE', 23.99), 
            ('LARGE 4 FROM PLAIN', 23.99), 
            ('XLARGE', 26.99), ('XLARGE ANANAS', 26.99), ('XLARGE CHAMPIGNON', 26.99), 
            ('XLARGE COTES LEVEE', 29.99), ('XLARGE FAJITAS', 28.99), ('XLARGE FROM', 26.99), 
            ('XLARGE GARNIE', 27.99), ('XLARGE GRECQUE', 27.99), ('XLARGE GUETTI', 26.99), 
            ('XLARGE MEXICAINE', 27.99), ('XLARGE PEPE', 26.99), ('XLARGE SPECIAL', 28.99), 
            ('XLARGE VEGE', 26.99), ('XLARGE FRUITS MER', 30.99), ('XLARGE 4 FROM ANCIENNE', 27.99), 
            ('XLARGE 4 FROM PLAIN', 27.99), 
            
            # Combos et Plats Enfants 
            ('COMBO PIZZA', 29.99), ('DUO PATE ET PIZZ', 24.99), ('DUO PIZZA', 24.99), 
            ('PIZZA ENF', 7.99), 
            
            # Frites et Poutines
            ('BB. FRITES', 3.99), ('BB. POUTINE', 6.29), ('FAM .FRITE', 10.99), 
            ('FRITES SAUCE', 5.99), ('GR. DALTONE', 15.99), ('GR. GALVAUDE', 15.50), 
            ('GR. POUTINE', 13.99), ('GR. POUTINE ITAL', 15.99), ('PT. DALTONE', 12.99), 
            ('PT. FRITES', 5.99), ('PT. GALVAUDE', 13.50), ('PT. PAT ANC', 10.99), 
            ('PT. POUTINE', 10.59), ('PT. POUTINE ITAL', 11.99), ('PM. POUTINE', 8.50), 
            
            # Sandwichs et Plats 
            ('CHEESEBURGER', 16.29), ('ASS. COQ. ST-JACQUES', 21.99), ('FETT.', 15.88), 
            ('FETTUCCINE', 15.88), ('FONDU PARMESAN', 8.99), ('LASAGNE', 16.99), 
            ('MEDIUM GUETTI', 16.99), ('SPAG VIANDE', 16.99), ('SPAGHETTI', 16.99), 
            ('SPAGHETTI ENF', 7.99), ('(12) CREV. BOUL-BANG', 15.99), ('(6) CREV. BOUL-BANG', 9.99), 
            ('AILES POULET', 15.99), ('ASS. CREV. BOUL-BANG', 20.99), ('ASS. CREVETTE AIL', 20.99), 
            ('BATONNETS MIDI', 14.99), ('BAT. FROMAGE', 8.99), ('BICFTECK MIDI', 18.99), 
            ('BR. POULET', 17.99), ('BURGER', 13.99), ('CHAMP. GRATINER', 8.99), 
            ('CLUB', 17.99), ('COTES LEVEES 15OZ', 24.99), ('CUISSE POULET', 17.29), 
            ('CUISSE POULET MIDI', 12.99), ('DOIGTS POULET', 17.99), ('DOIGT/ COTE LEVE', 28.99), 
            ('F.MIGNON', 26.99), ('F.SOLE MEUNIERE', 20.99), ('FILET SOLE MEUNIERE', 20.99), 
            ('FISH AND CHIPS', 21.99), ('FISH N CHIP MIDI', 12.99), ('HAMB', 12.99), 
            ('HOT CHICKEN', 16.90), ('POITRINE', 18.49), ('POITRINE/ COTE LEVEE', 29.99), 
            ('POIT/ COTE LEVE', 29.99), ('SMOKE MEAT', 18.40), ('STEAK HACHE', 18.99), 
            
            # Salades 
            ('ENT. SAL. CESAR', 9.99), ('ENT. SAL. DU CHEF', 8.99), ('SAL CESAR MIDI', 12.99), 
            ('SAL CHEF POULET MIDI', 14.99), ('SAL THAI', 18.99), ('SAL. CESAR', 16.99), 
            ('SAL. CESAR POULET', 18.09), ('SAL. THAI CREV. BOUL', 19.09), ('SAL. THAI POUL. BOUL', 18.99), 
            ('SAL. VARIEE', 17.48), 
            
            # Extras/Divers 
            ('CROQUETTE ENF', 7.99), ('CREME DE POULET', 4.99), ('DIVERS NOURRITURE', 0.00), 
            ('EXTRÊME', 2.00), ('JALAPENO POPPERS', 8.99), ('MINI', 1.00), 
            ('OIGNON FRANCAIS', 7.99), ('POGO ENF', 6.99), ('PROMO CORNICHONS', 5.99), 
            ('RAGOUT', 12.99), ('SAND. AUX', 11.99), ('S-M.', 1.00), 
            ('SOUPE', 4.99), ('SOUPE AUX LEGUMES', 4.99)
        ]
        
        # Tente l'insertion initiale si la base de données est vide
        self.populate_initial_dishes(self.initial_dishes_list)

    def _safe_float_conversion(self, value: Union[str, float, int]) -> float:
        """Convertit une chaîne ou un entier en float pour la DB, sinon retourne 0.00."""
        if isinstance(value, (float, int)):
            return float(value)
        try:
            return float(str(value).replace(',', '.').strip())
        except (ValueError, TypeError):
            return 0.00

    def _get_connection(self) -> sqlite3.Connection:
        """Établit la connexion à la base de données."""
        return sqlite3.connect(self.DB_FILE)

    def _initialize_db(self):
        """Crée la table 'main_dishes' avec dish_name comme clé primaire et inclut le prix."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Structure de table la plus simple et robuste pour cette application (Nom en clé primaire)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS main_dishes (
                dish_name TEXT PRIMARY KEY,
                price REAL DEFAULT 0.00
            )
        """)
        
        # Tente d'ajouter la colonne 'price' si elle n'existe pas (pour les anciennes DB)
        try:
            cursor.execute("PRAGMA table_info(main_dishes)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'price' not in columns:
                cursor.execute("ALTER TABLE main_dishes ADD COLUMN price REAL DEFAULT 0.00")
        except sqlite3.OperationalError:
            pass # La colonne existe déjà ou autre erreur mineure
            
        conn.commit()
        conn.close()


    def populate_initial_dishes(self, dishes: List[Tuple[str, float]]):
        """Insère la liste initiale des plats si la table est vide."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM main_dishes")
        count = cursor.fetchone()[0]
        
        if count == 0:
            data_to_insert = []
            for dish_name, dish_price in dishes:
                clean_name = dish_name.strip().upper()
                clean_price = self._safe_float_conversion(dish_price)
                if clean_name:
                    data_to_insert.append((clean_name, clean_price))

            try:
                # Utilisation de INSERT OR IGNORE pour gérer les doublons potentiels dans la liste initiale
                cursor.executemany("INSERT OR IGNORE INTO main_dishes (dish_name, price) VALUES (?, ?)", data_to_insert)
                conn.commit()
            except Exception as e:
                print(f"Erreur lors de l'insertion initiale: {e}")
        
        conn.close()

    

    def get_all_dishes(self):
        """Récupère les plats avec la colonne dish_name corrigée."""
        conn = sqlite3.connect(self.DB_FILE)
        cursor = conn.cursor()
        # Utilisation de dish_name pour correspondre à votre DB
        cursor.execute("SELECT dish_name, price FROM main_dishes ORDER BY dish_name")
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_unique_subitems_from_archive(self, only_new=False):
        """Extrait les sous-items et nettoie les symboles (*, x) et les chiffres au début."""
        consult_db = 'consultation.db'
        if not os.path.exists(consult_db):
            return []
        
        existing_dishes = [d[0].upper().strip() for d in self.get_all_dishes()] if only_new else []
        sub_items_set = set()

        try:
            conn = sqlite3.connect(consult_db)
            cursor = conn.cursor()
            cursor.execute("SELECT items FROM orders_archive")
            
            for row in cursor.fetchall():
                items_list = json.loads(row[0])
                for item_json in items_list:
                    item_data = json.loads(item_json)
                    subs = item_data.get('sub_items', [])
                    for s in subs:
                        # REGEX EXPLIQUÉE :
                        # ^[\s*xX\d]+  -> Cherche au début (^) n'importe quelle combinaison 
                        #                 d'espaces, d'étoiles (*), de x, ou de chiffres (\d)
                        # \s+          -> Suivi d'un ou plusieurs espaces
                        clean_s = re.sub(r'^[\s*xX\d]+\s*', '', s).upper().strip()
                        
                        if clean_s:
                            if only_new:
                                if clean_s not in existing_dishes:
                                    sub_items_set.add(clean_s)
                            else:
                                sub_items_set.add(clean_s)
            conn.close()
        except Exception as e:
            print(f"Erreur extraction: {e}")
        
        return sorted(list(sub_items_set))

    def add_dish_if_not_exists(self, name, price=0.0):
        """Ajoute l'item dans la table main_dishes (colonne dish_name)."""
        conn = sqlite3.connect(self.DB_FILE)
        cursor = conn.cursor()
        name = name.upper().strip()
        cursor.execute("SELECT dish_name FROM main_dishes WHERE UPPER(dish_name) = ?", (name,))
        if cursor.fetchone():
            conn.close()
            return False
        
        cursor.execute("INSERT INTO main_dishes (dish_name, price) VALUES (?, ?)", (name, price))
        conn.commit()
        conn.close()
        return True

    def get_items_from_consultation(self):
        """Extrait les plats et accompagnements de consultation.db."""
        if not os.path.exists(self.CONSULT_DB):
            return []
        
        extracted_data = []
        seen = set()
        try:
            conn = sqlite3.connect(self.CONSULT_DB)
            cursor = conn.cursor()
            # Lecture des archives JSON
            cursor.execute("SELECT items FROM orders_archive")
            for row in cursor.fetchall():
                items_list = json.loads(row[0])
                for item_str in items_list:
                    data = json.loads(item_str)
                    
                    # Nettoyage du nom (enlève le "1 x ")
                    raw_main = data.get('main_item', '').upper()
                    clean_main = re.sub(r'^\d+\s*x\s*', '', raw_main).strip()
                    subs = [s.upper().strip() for s in data.get('sub_items', [])]
                    
                    if clean_main and (clean_main, tuple(subs)) not in seen:
                        seen.add((clean_main, tuple(subs)))
                        extracted_data.append({'main': clean_main, 'subs': subs})
            conn.close()
        except Exception as e:
            print(f"Erreur archive: {e}")
        return sorted(extracted_data, key=lambda x: x['main'])

    def load_all_dishes(self) -> List[Tuple[str, float]]:
        """
        Charge et retourne la liste de tous les plats principaux triés.
        Retourne une liste de tuples (dish_name, price).
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT dish_name, price FROM main_dishes ORDER BY dish_name ASC")
        dishes = cursor.fetchall() 
        conn.close()
        return dishes

    def add_dish(self, dish_name: str, price: Union[str, float]) -> str:
        """Ajoute un plat principal avec son prix, ou met à jour le prix si le plat existe (UPSERT)."""
        dish_name = dish_name.strip().upper() 
        clean_price = self._safe_float_conversion(price)

        if not dish_name:
            return "ERREUR: Le nom du plat ne peut pas être vide."
            
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # Tente de mettre à jour le prix si le plat existe
            cursor.execute("UPDATE main_dishes SET price = ? WHERE dish_name = ?", (clean_price, dish_name))
            if cursor.rowcount > 0:
                conn.commit()
                return f"SUCCÈS: Prix du plat existant '{dish_name}' mis à jour à ${clean_price:.2f}."

            # Sinon, insère le nouveau plat
            cursor.execute("INSERT INTO main_dishes (dish_name, price) VALUES (?, ?)", (dish_name, clean_price))
            conn.commit()
            return f"SUCCÈS: Plat '{dish_name}' (Prix: ${clean_price:.2f}) ajouté."

        except sqlite3.IntegrityError:
            return f"Avertissement: Le plat '{dish_name}' existe déjà."
        except Exception as e:
            return f"ERREUR: Échec de l'ajout - {e}"
        finally:
            conn.close()

    # ⭐ MÉTHODE CLÉ POUR LA MODIFICATION (RENOMMER ET/OU CHANGER LE PRIX)
    def update_dish(self, old_dish_name: str, new_dish_name: str, new_dish_price: float) -> str:
        """Met à jour le nom et/ou le prix d'un plat existant. Tous les noms sont en MAJUSCULES."""
        old_dish_name = old_dish_name.strip().upper()
        new_dish_name = new_dish_name.strip().upper()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Cas simple: Seul le prix change (le nom reste le même)
            if old_dish_name == new_dish_name:
                cursor.execute("""
                    UPDATE main_dishes 
                    SET price = ? 
                    WHERE dish_name = ?
                """, (new_dish_price, old_dish_name))
                conn.commit()
                if cursor.rowcount > 0:
                    return f"SUCCÈS: Prix du plat '{new_dish_name}' mis à jour à ${new_dish_price:.2f}."
                else:
                    return f"Avertissement: Plat '{old_dish_name}' introuvable pour la modification du prix."

            # 2. Cas complexe: Le nom change (nécessite de supprimer l'ancienne PK et d'insérer la nouvelle)
            else:
                # A. Vérification si le nouveau nom est déjà pris
                cursor.execute("SELECT 1 FROM main_dishes WHERE dish_name = ?", (new_dish_name,))
                if cursor.fetchone():
                    return f"Avertissement: Le nouveau nom '{new_dish_name}' existe déjà pour un autre plat. Veuillez choisir un autre nom."
            
                # B. Suppression de l'ancienne entrée et insertion de la nouvelle (simulation de renommage)
                cursor.execute("DELETE FROM main_dishes WHERE dish_name = ?", (old_dish_name,))
                if cursor.rowcount == 0:
                    conn.close()
                    return f"Avertissement: Plat original '{old_dish_name}' introuvable pour le renommage."
                    
                cursor.execute("INSERT INTO main_dishes (dish_name, price) VALUES (?, ?)", (new_dish_name, new_dish_price))
                
                conn.commit()
                return f"SUCCÈS: Plat renommé de '{old_dish_name}' à '{new_dish_name}' et prix mis à jour à ${new_dish_price:.2f}."

        except Exception as e:
            conn.rollback()
            return f"ERREUR: Échec de la modification/renommage - {e}"
        finally:
            conn.close()

    def remove_dish(self, dish_name: str) -> str:
        """Supprime un plat principal existant."""
        dish_name = dish_name.strip().upper()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM main_dishes WHERE dish_name = ?", (dish_name,))
            rows_affected = cursor.rowcount
            conn.commit()
            
            if rows_affected > 0:
                return f"SUCCÈS: Plat '{dish_name}' supprimé."
            else:
                return f"Avertissement: Plat '{dish_name}' introuvable."
        except Exception as e:
            return f"ERREUR: Échec de la suppression - {e}"
        finally:
            conn.close()

    # --- MÉTHODES POUR BACKUP/IMPORTATION JSON ---

    def export_dishes_to_json(self, file_path: str) -> str:
        """Exporte tous les plats (Nom et Prix) vers un fichier JSON."""
        dishes_data = [{"dish_name": name, "price": price} for name, price in self.load_all_dishes()]
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(dishes_data, f, indent=4, ensure_ascii=False)
            return f"SUCCÈS: {len(dishes_data)} plats (Nom et Prix) exportés vers {os.path.basename(file_path)}."
        except Exception as e:
            return f"ERREUR: Échec de l'exportation - {e}"

    def import_dishes_from_json(self, file_path: str, replace_existing: bool = False) -> str:
        """
        Importe les plats depuis un fichier JSON. 
        Utilise le comportement UPSERT (met à jour le prix si le plat existe, sinon insère).
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            return f"ERREUR: Fichier introuvable à l'emplacement: {file_path}"
        except json.JSONDecodeError:
            return "ERREUR: Format de fichier JSON invalide."
        except Exception as e:
            return f"ERREUR: Échec de la lecture du fichier - {e}"

        if not isinstance(data, list):
            return "ERREUR DE STRUCTURE: Le fichier JSON doit contenir une liste d'objets (plats)."
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if replace_existing:
            cursor.execute("DELETE FROM main_dishes")
            conn.commit()
            
        success_count = 0
        update_count = 0
        invalid_count = 0

        for item in data:
            if not isinstance(item, dict) or 'dish_name' not in item:
                invalid_count += 1
                continue
                
            dish_name = item.get('dish_name')
            dish_price = item.get('price', 0.00) 
            
            if not isinstance(dish_name, str) or not dish_name.strip():
                invalid_count += 1
                continue

            clean_name = dish_name.strip().upper()
            clean_price = self._safe_float_conversion(dish_price)

            try:
                # Tente de mettre à jour le prix (UPSERT)
                cursor.execute("UPDATE main_dishes SET price = ? WHERE dish_name = ?", (clean_price, clean_name))
                if cursor.rowcount > 0:
                    update_count += 1
                else:
                    # Insertion si le plat n'existe pas
                    cursor.execute("INSERT INTO main_dishes (dish_name, price) VALUES (?, ?)", (clean_name, clean_price))
                    success_count += 1
            except Exception as e:
                print(f"Erreur d'insertion/mise à jour pour {clean_name}: {e}")
                
        conn.commit()
        conn.close()

        summary = [f"SUCCÈS: Importation terminée.",
                   f"Nouveaux plats insérés: {success_count}.",
                   f"Plats existants mis à jour: {update_count}.",
                   f"Plats invalides (structure incorrecte) ignorés: {invalid_count}."
                   ]
        if replace_existing:
            summary.insert(1, "ATTENTION: La base de données existante a été EFFACÉE avant l'insertion.")
            
        return '\n'.join(summary)
        
    # --- MÉTHODES POUR BACKUP/IMPORTATION DB ---
    
    def _verify_db_structure(self, db_path: str) -> bool:
        """
        Vérifie si le fichier DB importé contient la table 'main_dishes' 
        avec les colonnes 'dish_name' et 'price'.
        """
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='main_dishes'")
            if cursor.fetchone() is None:
                conn.close()
                return False

            cursor.execute("PRAGMA table_info(main_dishes)")
            columns = [col[1] for col in cursor.fetchall()]
            conn.close()
            
            return 'dish_name' in columns and 'price' in columns
        except sqlite3.DatabaseError:
            return False
        except Exception:
            return False

    def export_database_file(self, dest_path: str) -> str:
        """Copie le fichier kds_constants.db vers un chemin spécifié."""
        if not os.path.exists(self.DB_FILE):
             return f"ERREUR: Le fichier DB source '{self.DB_FILE}' est introuvable."

        try:
            # Utilise une transaction pour copier la DB de manière sécuritaire
            conn = self._get_connection()
            bck = sqlite3.connect(dest_path)
            with conn:
                conn.backup(bck)
            bck.close()
            conn.close()
            return f"SUCCÈS: Fichier DB copié vers {os.path.basename(dest_path)}.\n(Sauvegarde complète de la DB)"
        except Exception as e:
            return f"ERREUR: Échec de l'exportation du fichier DB. Le fichier est peut-être en cours d'utilisation par une autre application. - {e}"


    def import_database_file(self, source_path: str) -> str:
        """Remplace le fichier kds_constants.db actuel par le fichier de sauvegarde, après vérification."""
        if not os.path.exists(source_path):
             return f"ERREUR: Le fichier source '{os.path.basename(source_path)}' est introuvable."

        if not self._verify_db_structure(source_path):
            return f"ERREUR DE SÉCURITÉ/STRUCTURE: Le fichier '{os.path.basename(source_path)}' n'est pas une DB KDS valide (colonne 'price' manquante ou table incorrecte)."
            
        try:
            shutil.copyfile(source_path, self.DB_FILE)
            return f"SUCCÈS: Base de données restaurée à partir de {os.path.basename(source_path)}.\n(L'application doit être redémarrée pour charger les nouvelles données)"
        except Exception as e:
            return f"ERREUR: Échec de la restauration du fichier DB. Veuillez fermer et rouvrir l'application avant l'importation. - {e}"


if __name__ == '__main__':
    print("Test d'initialisation de MainDishDBManager...")
    manager = MainDishDBManager()
    print("Initialisation OK.")