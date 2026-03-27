# web_access.py (MODIFIÉ AVEC INTERFACE TKINTER)

import tkinter as tk
from tkinter import messagebox
from flask import Flask, render_template, jsonify, request
from db_manager import DBManager, CONSULTATION_DB_PATH 
import logging
from datetime import datetime, timedelta
import json 
import threading
import requests # Nécessaire pour envoyer la commande /shutdown
import re 

import platform # <--- Ajoutez cet import en haut du fichier
import os
import json

from serial_reader import SerialReader

# Configuration de base du logger
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration GLOBALE ---
db_manager = DBManager()
KDS_REFRESH_RATE = 3 
livraisons_store = {}
LIVREURS = ["Chantal", "Mike", "Le King", "Alain" , "Cedrik","Livreur1", "Livreur2", "Livreur3", "Livreur4" , "Livreur5"]
# Initialisation de Flask (sera utilisée par ServerManager)
app = Flask(__name__)

# ⭐ DÉFINITION ET ENREGISTREMENT DU FILTRE from_json POUR JINJA
def json_loads_filter(s):
    """Décode les items, qu'ils soient une liste de strings JSON ou une string unique."""
    try:
        # Si c'est déjà une liste (comme dans tes logs debug)
        if isinstance(s, list):
            decoded_list = []
            for item in s:
                if isinstance(item, str):
                    decoded_list.append(json.loads(item))
                else:
                    decoded_list.append(item)
            return decoded_list
        
        # Si c'est une chaîne unique
        if isinstance(s, str):
            return json.loads(s)
            
        return []
    except Exception as e:
        logger.error(f"Erreur de décodage JSON : {e}")
        return []

app.jinja_env.filters['from_json'] = json_loads_filter

def _get_kds_data_and_notes(db_manager):
    global livraisons_store
    orders_by_service = db_manager.get_pending_orders()
    
    # Expression régulière pour : 418-555-1234, 4185551234 ou 555-1234, 5551234
    phone_regex = r"(\d{3}[-\s]?\d{3}[-\s]?\d{4}|\d{3}[-\s]?\d{4})"

    for service_type, orders in orders_by_service.items():
        for order in orders:
            if str(order.get('table_number')) == "999":
                bid = order['bill_id']
                
                # --- LOGIQUE D'EXTRACTION DU TÉLÉPHONE ---
                found_phone = order.get('customer_phone', '')
                
                # Si le téléphone est vide, on cherche dans les items
                if not found_phone or len(str(found_phone)) < 7:
                    items_blob = str(order.get('items', ''))
                    match = re.search(phone_regex, items_blob)
                    if match:
                        found_phone = match.group(0)
                        order['customer_phone'] = found_phone # On l'injecte dans les données

                if bid not in livraisons_store:
                    livraisons_store[bid] = {
                        'data': order,
                        'collapsed': True, 
                        'livreur': None
                    }
                else:
                    livraisons_store[bid]['data'] = order
    return db_manager.get_all_bill_notes()
# --- web_access.py (Partie Routes modifiée) ---

@app.route('/')
@app.route('/kds')
def kds_dashboard():
    # 1. On récupère les commandes actives (En attente/En cours) depuis la DB
    all_orders = db_manager.get_pending_orders()
    
    # On crée une liste des IDs valides pour le nettoyage
    active_db_ids = []
    for status in all_orders:
        for o in all_orders[status]:
            if str(o.get('table_number')) == '999':
                active_db_ids.append(str(o['id']))

    # 2. MISE À JOUR DU STORE LOCAL
    for status, orders in all_orders.items():
        for o in orders:
            if str(o.get('table_number')) != '999':
                continue

            bid = str(o['id'])
            
            if bid not in livraisons_store:
                livraisons_store[bid] = {
                    'data': o,
                    'livreur': None,
                    'collapsed': False,
                    'extras': {'desired_time': 'HEURE', 'utensils': 'UST', 'custom_note': 'NOTE'}
                }
            else:
                livraisons_store[bid]['data'] = o
                if 'extras' not in livraisons_store[bid]:
                    livraisons_store[bid]['extras'] = {'desired_time': 'HEURE', 'utensils': 'UST', 'custom_note': 'NOTE'}

    # 3. NETTOYAGE
    ids_to_remove = [bid for bid in livraisons_store if bid not in active_db_ids]
    for bid in ids_to_remove:
        del livraisons_store[bid]

    # 4. RECHERCHE ET FILTRAGE COMPLET
    search_query = request.args.get('search', '').lower()
    show_all = request.args.get('show_all', '0') == '1'

    filtered_livraisons = {}
    stats_casiers = {name: 0 for name in LIVREURS}

    for bid, item in livraisons_store.items():
        if 'data' not in item:
            continue
            
        data = item['data']
        extras = item.get('extras', {})
        
        # --- CONSTRUCTION DE LA CHAÎNE DE RECHERCHE TOTALE ---
        # On regroupe toutes les données possibles dans une seule chaîne
        searchable_text = f"{bid} "
        searchable_text += str(data.get('customer_phone', '')).lower() + " "
        searchable_text += str(data.get('address', '')).lower() + " "
        searchable_text += str(data.get('customer_name', '')).lower() + " "
        searchable_text += str(extras.get('custom_note', '')).lower() + " "
        searchable_text += str(extras.get('desired_time', '')).lower() + " "
        
        # Extraction poussée des items (plats + sous-items)
        for raw_it in data.get('items', []):
            try:
                it_data = json.loads(raw_it) if isinstance(raw_it, str) else raw_it
                if isinstance(it_data, dict):
                    searchable_text += str(it_data.get('main_item', '')).lower() + " "
                    for sub in it_data.get('sub_items', []):
                        searchable_text += str(sub).lower() + " "
                else:
                    searchable_text += str(it_data).lower() + " "
            except:
                searchable_text += str(raw_it).lower() + " "

        # Calcul des compteurs par livreur
        current_livreur = item.get('livreur')
        if current_livreur in stats_casiers:
            stats_casiers[current_livreur] += 1

        # Vérification si le texte complet contient la requête
        if not search_query or search_query in searchable_text:
            filtered_livraisons[bid] = item

    
    return render_template(
        'kds_dashboard.html',
        livraisons=filtered_livraisons,
        livreurs=LIVREURS,
        stats=stats_casiers,
        refresh_rate=KDS_REFRESH_RATE,
        search_query=search_query,
        show_all=show_all
    )

@app.route('/kds_livreur')
def kds_dashboard_livreur():
    # 1. On récupère les commandes actives (En attente/En cours) depuis la DB
    all_orders = db_manager.get_pending_orders()
    
    # On crée une liste des IDs valides pour le nettoyage
    active_db_ids = []
    for status in all_orders:
        for o in all_orders[status]:
            if str(o.get('table_number')) == '999':
                active_db_ids.append(str(o['id']))

    # 2. MISE À JOUR DU STORE LOCAL
    for status, orders in all_orders.items():
        for o in orders:
            if str(o.get('table_number')) != '999':
                continue

            bid = str(o['id'])
            
            if bid not in livraisons_store:
                livraisons_store[bid] = {
                    'data': o,
                    'livreur': None,
                    'collapsed': False,
                    'extras': {'desired_time': 'HEURE', 'utensils': 'UST', 'custom_note': 'NOTE'}
                }
            else:
                livraisons_store[bid]['data'] = o
                if 'extras' not in livraisons_store[bid]:
                    livraisons_store[bid]['extras'] = {'desired_time': 'HEURE', 'utensils': 'UST', 'custom_note': 'NOTE'}

    # 3. NETTOYAGE
    ids_to_remove = [bid for bid in livraisons_store if bid not in active_db_ids]
    for bid in ids_to_remove:
        del livraisons_store[bid]

    # 4. RECHERCHE ET FILTRAGE COMPLET
    search_query = request.args.get('search', '').lower()
    show_all = request.args.get('show_all', '0') == '1'

    filtered_livraisons = {}
    stats_casiers = {name: 0 for name in LIVREURS}

    for bid, item in livraisons_store.items():
        if 'data' not in item:
            continue
            
        data = item['data']
        extras = item.get('extras', {})
        
        # --- CONSTRUCTION DE LA CHAÎNE DE RECHERCHE TOTALE ---
        # On regroupe toutes les données possibles dans une seule chaîne
        searchable_text = f"{bid} "
        searchable_text += str(data.get('customer_phone', '')).lower() + " "
        searchable_text += str(data.get('address', '')).lower() + " "
        searchable_text += str(data.get('customer_name', '')).lower() + " "
        searchable_text += str(extras.get('custom_note', '')).lower() + " "
        searchable_text += str(extras.get('desired_time', '')).lower() + " "
        
        # Extraction poussée des items (plats + sous-items)
        for raw_it in data.get('items', []):
            try:
                it_data = json.loads(raw_it) if isinstance(raw_it, str) else raw_it
                if isinstance(it_data, dict):
                    searchable_text += str(it_data.get('main_item', '')).lower() + " "
                    for sub in it_data.get('sub_items', []):
                        searchable_text += str(sub).lower() + " "
                else:
                    searchable_text += str(it_data).lower() + " "
            except:
                searchable_text += str(raw_it).lower() + " "

        # Calcul des compteurs par livreur
        current_livreur = item.get('livreur')
        if current_livreur in stats_casiers:
            stats_casiers[current_livreur] += 1

        # Vérification si le texte complet contient la requête
        if not search_query or search_query in searchable_text:
            filtered_livraisons[bid] = item

    return render_template(
        'kds_dashboard_livreur.html',
        livraisons=filtered_livraisons,
        livreurs=LIVREURS,
        stats=stats_casiers,
        refresh_rate=KDS_REFRESH_RATE,
        search_query=search_query,
        show_all=show_all
    )

@app.route('/kds_pa')
def kds_dashboard_pa():
    # 1. On récupère les commandes actives depuis la DB
    all_orders = db_manager.get_pending_orders()
    pa_orders = {}
    
    for status, orders in all_orders.items():
        for o in orders:
            # Nettoyage des valeurs pour éviter les erreurs de casse ou d'espaces
            t_num = str(o.get('table_number', '')).strip().upper()
            s_name = str(o.get('serveur_name', '')).strip()
            
            if t_num == 'PA' :
                bid = str(o.get('id'))
                pa_orders[bid] = {
                    'data': o,
                    'extras': {'custom_note': o.get('note', '')} 
                }

    # 3. RECHERCHE
    search_query = request.args.get('search', '').lower()
    filtered_pa = {}

    for bid, item in pa_orders.items():
        data = item['data']
        # Construction texte recherche
        searchable_text = f"{bid} {str(data.get('table_number', '')).lower()} {str(data.get('serveur_name', '')).lower()} "
        
        # Items
        items_list = data.get('items', [])
        if isinstance(items_list, list):
            for raw_it in items_list:
                searchable_text += str(raw_it).lower() + " "

        if not search_query or search_query in searchable_text:
            filtered_pa[bid] = item

    # 4. Rendu du template
    return render_template(
        'kds_dashboard_pa.html',
        pa_list=filtered_pa,
        refresh_rate=KDS_REFRESH_RATE,
        search_query=search_query
    )

@app.route('/close_order/<string:order_id>', methods=['POST'])
def close_order(order_id):
    # On récupère les infos (optionnel si vous voulez passer des notes à la fin)
    success = db_manager.close_livraison_details(
        bid=order_id, 
        note="", 
        desired_time="", 
        utensils=""
    )
    
    if success:
        return jsonify({"success": True, "message": "Commande traitée"}), 200
    else:
        return jsonify({"success": False, "message": "Erreur lors de la fermeture"}), 500

@app.route('/update_pa_details', methods=['POST'])
def update_pa_details():
    try:
        data = request.json
        bid = data.get('bid')
        
        # Récupération des extras envoyés par le JS
        new_note = data.get('custom_note', '')
        new_time = data.get('desired_time', '')
        new_utensils = data.get('utensils', '')

        # Mise à jour dans la base de données
        # On utilise la méthode DBManager que nous avons définie précédemment
        if db_manager.update_pa_details(bid, new_note, new_time, new_utensils):
            return jsonify(success=True)
        else:
            return jsonify(success=False, error="Échec de la mise à jour DB")
            
    except Exception as e:
        logger.error(f"Erreur route update_pa_details: {e}")
        return jsonify(success=False, error=str(e))

@app.route('/print_bill', methods=['POST'])
def print_bill():
    import json
    data = request.json
    bid = data.get('bid')
    
    if bid not in livraisons_store:
        return jsonify(success=False, error="Commande introuvable")
    
    # Récupération des données de la commande et des extras
    item_full = livraisons_store[bid]
    order_data = item_full.get('data', {})
    extras = item_full.get('extras', {})
    
    # --- 1. CHARGEMENT DYNAMIQUE DU PORT ---
    port_reel = None
    config_file = "ports.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                ports_config = json.load(f)
                systeme = platform.system().lower() 
                key_suffix = "windows_ports" if systeme == "windows" else "linux_ports"
                port_reel = ports_config.get(key_suffix, {}).get("SERIAL_PORT_PRINTER_2")
        except Exception as e:
            logger.error(f"Erreur lecture ports.json: {e}")

    if not port_reel:
        port_reel = "COM10" if platform.system().lower() == "windows" else "/dev/ttyUSB4"

    # --- 2. LOGIQUE D'EXTRACTION (Identique au KDS HTML) ---
    found_no = "???"
    address = "Non disponible"
    phone = "Non disponible"
    formatted_items = []

    raw_items = order_data.get('items', [])
    for raw_it in raw_items:
        try:
            # Conversion du texte JSON en dictionnaire Python
            it = json.loads(raw_it) if isinstance(raw_it, str) else raw_it
            main_item = str(it.get('main_item', '')).replace('@', '').strip()
            sub_items = it.get('sub_items', [])
            
            # Stockage pour l'affichage final
            formatted_items.append({'main': main_item, 'subs': sub_items})

            # Extraction du Numéro de Livraison
            if "LIVRAISON #" in main_item.upper():
                found_no = main_item.split('#')[1].strip()

            # Extraction de l'Adresse (Numéro civique + Rue dans les subs)
            if main_item.replace(' ', '').isdigit() and address == "Non disponible":
                if len(sub_items) >= 1:
                    address = f"{main_item} {sub_items[0]}"

            # Extraction du Téléphone (Cherche 10 chiffres)
            for sub in sub_items:
                clean_phone = ''.join(filter(str.isdigit, str(sub)))
                if len(clean_phone) == 10:
                    phone = f"{clean_phone[0:3]}-{clean_phone[3:6]}-{clean_phone[6:10]}"
                if "LIVRAISON #" in str(sub).upper():
                    found_no = str(sub).split('#')[1].strip()
        except:
            formatted_items.append({'main': str(raw_it), 'subs': []})

    # --- 3. CONSTRUCTION DU TICKET TEXTUEL ---
    heure_imp = datetime.now().strftime('%H:%M:%S')
    
    # Récupération des valeurs
    h_desiree = extras.get('desired_time', '').strip()
    ustensiles = extras.get('utensils', '').strip()
    note_kds = extras.get('custom_note', '').strip()

    # Début du ticket
    lines = [
        "\n" + " " * 7 + "REIMPRESSION BON DE LIVRAISON",
        "=" * 30,
    ]

    # Ajout conditionnel : on n'ajoute que si ce n'est pas vide ET pas la valeur par défaut
    if h_desiree and h_desiree.upper() != "HEURE":
        lines.append(f"HEURE REQU : {h_desiree}")
    
    if ustensiles and ustensiles.upper() != "UST":
        lines.append(f"EXTRAS     : {ustensiles}")
        
    if note_kds and note_kds.upper() != "NOTE":
        lines.append(f"NOTE KDS   : {note_kds}")

    # Suite du ticket
    lines.extend([
        "-" * 30,
        "ARTICLES :"
    ])
    
    for it in formatted_items:
        lines.append(f"\n[ ] {it['main']}")
        for sub in it['subs']:
            lines.append(f"    -> {sub}")
        
    lines.append("\n" + "-" * 30)
    lines.append("\n\n\n\n") # Espace pour la découpe

    ticket_text = "\n".join(lines)

    try:
        # Utilise ta méthode de classe pour envoyer au port série
        success = SerialReader.reprint_ticket_to_printer(ticket_text, port_reel)
    except Exception as e:
        print(f"Erreur imprimante: {e}")
        success = False
    
    return jsonify(success=success, printed_content=ticket_text)

@app.template_filter('regex_replace')
def regex_replace(value, pattern, repl=""):
    if value is None:
        return ""
    return re.sub(pattern, repl, str(value))
    
@app.route('/update_livraison_details', methods=['POST'])
def update_livraison_details():
    data = request.json
    num_livr = data.get('num_livraison')
    bid = data.get('bid')
    
    if not num_livr:
        return jsonify(success=False, error="Numéro de livraison manquant")

    # 1. Mise à jour de la mémoire locale (KDS)
    if bid in livraisons_store:
        if 'extras' not in livraisons_store[bid]:
            livraisons_store[bid]['extras'] = {}
        for field in ['desired_time', 'utensils', 'custom_note']:
            if field in data:
                livraisons_store[bid]['extras'][field] = data[field]

    # 2. Préparation des items au FORMAT JSON (pour être des "Main Items")
    new_db_items = []
    
    # Formatage identique aux produits de la caisse
    if data.get('desired_time') and data['desired_time'] != "HEURE":
        item_heure = json.dumps({"main_item": f"HEURE: {data['desired_time']}", "sub_items": []})
        new_db_items.append(item_heure)

    #if data.get('utensils') and data['utensils'] != "UST":
    #    item_ust = json.dumps({"main_item": f"EXTRAS: {data['utensils']}", "sub_items": []})
    #    new_db_items.append(item_ust)

    #if data.get('custom_note') and data['custom_note'] != "NOTE":
    #    item_note = json.dumps({"main_item": f"NOTE: {data['custom_note']}", "sub_items": []})
    #    new_db_items.append(item_note)

    # 3. Envoi à la base de données
    if new_db_items:
        # On utilise 'LIV' car c'est ce que tu as spécifié
        db_success = db_manager.add_items_to_existing_bill(
            table_number='LIV', 
            serveuse_name=str(num_livr), 
            new_items_list=new_db_items
        )
        
        # Log pour vérifier dans la console
        if db_success:
            print(f"✅ Extras ajoutés pour Livr {num_livr} en tant que Main Items")
        
        return jsonify(success=db_success)

    return jsonify(success=True)

@app.route('/update_order_extra', methods=['POST'])
def update_order_extra():
    data = request.json
    bid = data.get('bid')
    field = data.get('field')
    value = data.get('value')
    
    if bid in livraisons_store:
        # On stocke dans une section 'extras' pour ne pas mélanger avec les données de base
        if 'extras' not in livraisons_store[bid]:
            livraisons_store[bid]['extras'] = {}
        
        livraisons_store[bid]['extras'][field] = value
        return jsonify({"status": "success"})
    
    return jsonify({"status": "error"}), 404

@app.route('/reset_all_commandes', methods=['POST'])
def reset_all_commandes():
    global livraisons_store
    try:
        # 1. On parcourt toutes les commandes en mémoire pour les marquer 'Traitée' en BD
        for bid in list(livraisons_store.keys()):
            # On utilise la méthode existante du db_manager pour mettre à jour la BD
            db_manager.set_order_status_by_bill_id(str(bid), 'Traitée')
        
        # 2. Une fois la BD mise à jour, on vide la mémoire vive
        livraisons_store.clear()
        
        return jsonify({"success": True, "message": "Toutes les commandes ont été traitées et archivées."})
    except Exception as e:
        logger.error(f"Erreur lors du reset global : {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/reset_livraison/<bid>', methods=['POST'])
def reset_livraison(bid):
    if bid in livraisons_store:
        livraisons_store[bid]['livreur'] = None
        livraisons_store[bid]['depart_at'] = None # ⭐ Efface le timer
        return jsonify({"success": True})
    return jsonify({"success": False}), 404


@app.route('/toggle_view/<bid>', methods=['POST'])
def toggle_view(bid):
    """Agrandit ou réduit le ticket (clic sur numéro table)."""
    if bid in livraisons_store:
        livraisons_store[bid]['collapsed'] = not livraisons_store[bid]['collapsed']
        return jsonify({"success": True, "new_state": livraisons_store[bid]['collapsed']})
    return jsonify({"success": False}), 404


@app.route('/assign_livreur/<bid>/<nom>', methods=['POST'])
def assign_livreur(bid, nom):
    if bid in livraisons_store:
        nom_valide = nom if nom in LIVREURS else None
        
        # On enregistre le livreur
        livraisons_store[bid]['livreur'] = nom_valide
        
        # ⭐ NOUVEAU : On enregistre l'heure actuelle systématiquement lors de l'assignation
        # Cela réinitialise le départ à "maintenant" à chaque fois
        if nom_valide:
            livraisons_store[bid]['depart_at'] = datetime.now().isoformat()
        else:
            # Si on retire le livreur, on efface le timer
            livraisons_store[bid]['depart_at'] = None
            
        return jsonify({"success": True})
    return jsonify({"success": False}), 404

@app.route('/fermer_livraison/<bid>', methods=['POST'])
def fermer_livraison(bid):
    """Supprime la livraison du store (fermeture définitive)."""
    if bid in livraisons_store:
        del livraisons_store[bid]
        return jsonify({"success": True})
    return jsonify({"success": False}), 404

@app.route('/kds_cards_html')
@app.route('/kds_content')
def kds_cards_html():
    orders_by_service, bill_notes = _get_kds_data_and_notes(db_manager)
    
    # --- APPLIQUER LE MÊME FILTRE ICI ---
    livraisons_uniquement = {}
    for service_type, orders in orders_by_service.items():
        liste_filtree = [o for o in orders if str(o.get('table_number')) == "999"]
        if liste_filtree:
            livraisons_uniquement[service_type] = liste_filtree
    # ------------------------------------

    return render_template(
        '_kds_cards_content.html',
        orders_by_service=livraisons_uniquement, # <-- Données filtrées
        bill_notes=bill_notes
    )

@app.route('/consultation', methods=['GET', 'POST'])
def consultation_page():
    logger.info("Accès à la page de consultation.")
    search_results = []
    
    search_params = {
        'bill_id': request.form.get('bill_id', ''),
        'serveuse_name': request.form.get('serveuse_name', ''),
        'table_number': request.form.get('table_number', ''),
        'start_date': request.form.get('start_date', ''),
        'end_date': request.form.get('end_date', '')
    }
    
    if request.method == 'POST':
        search_results = db_manager.search_archived_orders_in_consultation(
            bill_id=search_params['bill_id'],
            serveuse_name=search_params['serveuse_name'],
            table_number=search_params['table_number'] if search_params['table_number'] else None,
            start_date=search_params['start_date'] if search_params['start_date'] else None,
            end_date=search_params['end_date'] if search_params['end_date'] else None
        )
    else:
        search_results = db_manager.get_all_archived_orders_from_consultation()

    return render_template(
        'consultation.html', 
        archived_orders=search_results,
        search_params=search_params
    )

@app.route('/update_status_livraison/<string:bill_id>', methods=['POST'])
def update_status_livraison(bill_id):
    # 1. Appel de la fonction de fermeture dans la DB
    success = db_manager.close_livraison_details(bill_id)
    
    if success:
        # 2. Nettoyage du cache local (livraisons_store)
        # On cherche si la clé exacte ou une clé commençant par l'ID existe
        keys_to_del = [k for k in livraisons_store.keys() if k == bill_id or k.startswith(f"{bill_id}-")]
        for k in keys_to_del:
            del livraisons_store[k]
            
        logger.info(f"✅ Livraison {bill_id} traitée et retirée du store.")
        return jsonify({"success": True, "message": "Livraison fermée avec succès"}), 200
    else:
        logger.warning(f"⚠️ Impossible de fermer la livraison {bill_id} (non trouvée).")
        return jsonify({"success": False, "message": "ID non trouvé"}), 404
            
@app.route('/update_status/<string:bill_id>/<string:new_status>', methods=['POST'])
def update_status(bill_id, new_status):
    valid_statuses = ['En cours', 'Traitée', 'Annulée', 'En attente']
    if new_status not in valid_statuses:
        return jsonify({"success": False, "message": f"Statut non valide: {new_status}"}), 400
        
    row_count = db_manager.set_order_status_by_bill_id(bill_id, new_status)
    
    if row_count > 0:
        logger.info(f"Statut Bill ID {bill_id} mis à jour à '{new_status}'.")
        return jsonify({"success": True, "message": f"Statut mis à jour pour {bill_id} ({row_count} lignes)."}), 200
    else:
        return jsonify({"success": False, "message": f"Bill ID {bill_id} non trouvé ou aucun changement."}), 404

@app.route('/delete_bill/<string:bill_id>', methods=['POST'])
def delete_bill(bill_id):
    row_count = db_manager.permanent_delete_order_by_bill_id(bill_id)
    
    if row_count > 0:
        logger.warning(f"Facture ID {bill_id} supprimée définitivement.")
        return jsonify({"success": True, "message": f"Facture supprimée pour {bill_id} ({row_count} lignes)."}), 200
    else:
        return jsonify({"success": False, "message": f"Facture ID {bill_id} non trouvée ou aucun changement."}), 404

@app.route('/livraisons')
def voir_livraisons():
    """Affiche uniquement les livraisons accumulées en mémoire."""
    return jsonify({
        "total": len(livraisons_store),
        "commandes": list(livraisons_store.values())
    })



# ⭐ NOUVELLE ROUTE : Endpoint pour arrêter le serveur de développement Flask (pour le GUI)
def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        # Ceci ne devrait arriver que si le serveur n'est pas lancé par app.run()
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

@app.route('/shutdown', methods=['POST'])
def shutdown():
    shutdown_server()
    return 'Server shutting down...'


# --------------------------------------------------------------------------------
# 💻 LOGIQUE TKINTER ET THREADING POUR LE CONTRÔLE DU SERVEUR
# --------------------------------------------------------------------------------

class ServerManager:
    """Gère l'instance Flask et son exécution dans un thread séparé."""
    def __init__(self):
        self.server_thread = None
        self.is_running = False
        livraisons_store = {}

    def start_server(self, host, port):
        if self.is_running:
            logger.warning("Le serveur est déjà en cours d'exécution.")
            return False
            
        # Démarrage du serveur dans un thread pour ne pas bloquer le GUI
        self.server_thread = threading.Thread(
            target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False)
        )
        self.server_thread.daemon = True # Permet au programme principal de quitter
        self.server_thread.start()
        self.is_running = True
        logger.info(f"Serveur Flask démarré sur http://{host}:{port}")
        return True

    def stop_server(self):
        if not self.is_running:
            logger.warning("Le serveur n'est pas en cours d'exécution.")
            return False

        try:
            # Envoi d'une requête POST à l'endpoint de shutdown 
            requests.post(f'http://0.0.0.0:5000/shutdown') # On utilise localhost et le port par défaut pour le shutdown (sauf si on change la route)
            # Utilisons l'hôte/port actuels
            
            # Note : Flask/Werkzeug ne peut se fermer que si une requête peut être envoyée.
            # Pour cette implémentation, on va faire le post sur l'IP et le port en cours.
            
            # IMPORTANT: Il faut ici utiliser l'IP et le port effectif du serveur en cours. 
            # Comme ServerManager n'a pas gardé l'hôte/port, nous allons utiliser les valeurs du GUI 
            # passées à l'appel stop_server_action dans ServerGUI. 
            
            # --- Simplification du mécanisme ---
            # Pour la démo, nous assumons que le client (GUI) fournit l'IP/Port actuel.
            # La méthode ServerManager.stop_server ne prend pas d'arguments.
            # Dans le contexte du GUI ci-dessous, nous allons modifier l'appel.

            # On utilise le `localhost` et le port `5000` comme fallback/convention pour l'arrêt 
            # si l'IP réelle ne fonctionne pas toujours depuis le host.
            requests.post(f'http://0.0.0.0:5000/shutdown')
            
            self.server_thread.join(timeout=3)
            
            if self.server_thread.is_alive():
                logger.error("Le thread du serveur n'a pas pu s'arrêter correctement. Tenter d'arrêter la fenêtre Tkinter pour forcer la fermeture.")
            
            self.is_running = False
            logger.info("Serveur Flask arrêté.")
            return True
            
        except requests.exceptions.ConnectionError:
             logger.error("Impossible de se connecter au serveur pour l'arrêter. Le serveur est peut-être déjà mort.")
             self.is_running = False
             return True 
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt du serveur: {e}")
            return False


class ServerGUI(tk.Tk):
    """Interface graphique pour contrôler le serveur Flask."""
    def __init__(self):
        super().__init__()
        self.title("KDS Flask Server Control")
        self.server_manager = ServerManager()
        
        # Valeurs par défaut avec l'IP et le port précédents
        self.ip_var = tk.StringVar(value='0.0.0.0')
        self.port_var = tk.StringVar(value='5000')
        self.status_var = tk.StringVar(value='Statut: Arrêté')
        
        self._create_widgets()
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _create_widgets(self):
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(padx=10, pady=10)
        
        # --- Entrée IP ---
        tk.Label(main_frame, text="Adresse IP (Host):").grid(row=0, column=0, sticky='w', pady=5)
        tk.Entry(main_frame, textvariable=self.ip_var, width=20).grid(row=0, column=1, padx=5, pady=5)

        # --- Entrée Port ---
        tk.Label(main_frame, text="Port:").grid(row=1, column=0, sticky='w', pady=5)
        tk.Entry(main_frame, textvariable=self.port_var, width=20).grid(row=1, column=1, padx=5, pady=5)

        # --- Boutons ---
        btn_frame = tk.Frame(main_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        self.start_btn = tk.Button(btn_frame, text="Démarrer Serveur", command=self.start_server_action, bg='#2ecc71', fg='white')
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tk.Button(btn_frame, text="Arrêter Serveur", command=self.stop_server_action, bg='#e74c3c', fg='white', state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # --- Statut ---
        tk.Label(main_frame, textvariable=self.status_var, fg='blue').grid(row=3, column=0, columnspan=2, pady=5)
        
    def start_server_action(self):
        host = self.ip_var.get()
        port_str = self.port_var.get()
        
        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                raise ValueError("Port invalide.")
        except ValueError:
            messagebox.showerror("Erreur de port", "Le port doit être un nombre entier valide entre 1 et 65535.")
            return

        if self.server_manager.start_server(host, port):
            self.status_var.set(f"Statut: En cours sur http://{host}:{port}")
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            # Met à jour le port dans la variable pour le shutdown (si l'utilisateur l'a changé)
            self.server_manager.port_en_cours = port 
            self.server_manager.host_en_cours = host

    def stop_server_action(self):
        # Nous allons passer les informations d'hôte/port au stop_server pour l'appel de shutdown.
        host_a_stopper = self.ip_var.get() 
        port_a_stopper = self.port_var.get() 
        
        try:
            # Envoi du POST au /shutdown sur l'hôte/port configuré
            requests.post(f'http://{host_a_stopper}:{port_a_stopper}/shutdown')
        except requests.exceptions.ConnectionError:
            # Si la connexion échoue, le serveur est probablement déjà arrêté ou l'hôte/port est mauvais.
            pass
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'envoi du shutdown: {e}")
        
        # On appelle le stop_server du manager (principalement pour mettre à jour l'état interne et join le thread)
        # Note: L'arrêt réel se fait par la requête POST ci-dessus
        if self.server_manager.is_running:
            self.server_manager.is_running = False
            
        self.status_var.set('Statut: Arrêté')
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
            
    def on_closing(self):
        """Action exécutée lors de la fermeture de la fenêtre."""
        if self.server_manager.is_running:
            # Tentative d'arrêt avant de détruire le GUI
            self.stop_server_action() 
        self.destroy()


# --- Lancement de l'Application ---
if __name__ == '__main__':
    # Initialisation des données de test
    try:
        from db_manager import initialize_data 
        initialize_data(db_manager)
    except ImportError:
        logger.warning("Impossible d'importer initialize_data de db_manager.py. L'initialisation des données de test est ignorée.")
    
    # Démarrer le GUI
    gui = ServerGUI()
    gui.mainloop()