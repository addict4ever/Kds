# web_access.py (MODIFIÉ AVEC INTERFACE TKINTER)

import tkinter as tk
import socket
from tkinter import messagebox
from flask import Flask, render_template, jsonify, request
from db_manager import DBManager, CONSULTATION_DB_PATH 
import logging
from datetime import datetime, timedelta
import json 
import threading
import requests # Nécessaire pour envoyer la commande /shutdown
import re 
import uuid
import platform # <--- Ajoutez cet import en haut du fichier
import os
import json
from flask import send_from_directory,send_file# Ajoutez cet import en haut du fichier

from serial_reader import SerialReader

# Configuration de base du logger
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration GLOBALE ---

APP_AUTH_KEY = "MonApplicationUnique123!" # Changez ceci par une clé secrète
ALLOWED_IPS = ['192.168.5.205', '192.168.5.203', '127.0.0.1']
ALLOWED_USER_AGENT = "MaSuperAppKDS/2.0" # Le nom de votre application

# --- LISTE DES ROUTES AUTORISÉES (WHITELIST) ---
# Seules ces routes seront accessibles. Tout le reste sera bloqué.
WHITELIST_ROUTES = [
    '/',
    '/kds',
    '/kds_livreur',
    '/update_status_livraisons',
    '/kds_pa',
    '/kds_placeur',
    '/mark_all_treated_livreur',
    '/api/livreurs',
    '/api/livreurs/add',
    '/api/livreurs/rename',
    '/api/livreurs/reorder',
    '/nouvelle_livraison',
    '/api/livreurs/delete',
    '/api/livreurs/check_status',
    '/static/css/bootstrap.min.css',
    '/kds_pa_alert',              # Ajouté : Page des alertes PA
    '/marquer_pa_traitee',        # Ajouté : Action sur alerte PA
    '/api/livreurs/toggle_status', # Ajouté : Activation/Désactivation livreur
    '/mark_pa_donner',
    '/close_order',
    '/update_pa_details',
    '/print_bill',
    '/update_livraison_details',
    '/update_order_extra',
    '/reset_all_commandes',
    '/reset_livraison',
    '/toggle_view',
    '/assign_livreur',
    '/fermer_livraison',
    '/kds_cards_html',
    '/kds_content',
    '/consultation',
    '/update_status_livraison',
    '/update_status',
    '/delete_bill',
    '/static/css/dashboard.css',
    '/static/js/Sortable.min.js',
    '/static/sound/beep_short.ogg',
    '/favicon.ico',
    '/temperatures',
    '/suivi',
    '/livraisons',
    '/static/css/tabulator.min.css',
    '/static/css/flatpickr.min.css',
    '/static/js/chart.min.js',
    '/static/js/flatpickr.js',
    '/static/js/tabulator.min.js',
    '/static/js/jspdf.umd.min.js',
    '/static/js/jspdf.plugin.autotable.min.js',
    '/static/js/chartjs-plugin-zoom.min.js',
    '/static/js/html2pdf.bundle.min.js',
    '/kds_pa_pizza',
    '/envoyer_tcp_commande'
    
    
]

INACTIFS_FILE = "livreurs_inactifs.json"



# --- Initialisation au démarrage ---
db_manager = DBManager()
KDS_REFRESH_RATE = 3 
livraisons_store = {}
# Initialisation de Flask (sera utilisée par ServerManager)
app = Flask(__name__)

def load_config_inactifs():
    """Charge la liste des livreurs inactifs depuis le fichier JSON."""
    if os.path.exists(INACTIFS_FILE):
        try:
            with open(INACTIFS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erreur lecture inactifs: {e}")
    return []

def save_config_inactifs(liste_inactifs):
    """Sauvegarde la liste des livreurs inactifs dans le fichier JSON."""
    try:
        with open(INACTIFS_FILE, 'w', encoding='utf-8') as f:
            json.dump(liste_inactifs, f)
    except Exception as e:
        logger.error(f"Erreur sauvegarde inactifs: {e}")

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

LIVREURS_FILE = 'livreurs.json'


def load_livreurs():
    """Charge les livreurs depuis le JSON ou utilise la liste par défaut."""
    # Liste par défaut basée sur ton équipe actuelle
    default_livreurs = [
        "Chantal", "Mike", "Le King", "Alain", "Cedrik", 
        "Dylan", "Joey", "Mathis", "Xavier", "Anthony", 
        "DINER", "SOIR"
    ]
    
    if os.path.exists(LIVREURS_FILE):
        try:
            with open(LIVREURS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # On vérifie que c'est bien une liste et qu'elle n'est pas vide
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception as e:
            logger.error(f"Erreur lors de la lecture de {LIVREURS_FILE}: {e}")
    
    # Si le fichier n'existe pas ou est corrompu, on crée le fichier par défaut
    save_livreurs(default_livreurs)
    return default_livreurs

def save_livreurs(liste):
    """Sauvegarde la liste dans le fichier JSON."""
    try:
        with open(LIVREURS_FILE, 'w', encoding='utf-8') as f:
            json.dump(liste, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Impossible de sauvegarder les livreurs: {e}")

# Initialisation au démarrage
LIVREURS = load_livreurs()
LIVREURS_INACTIFS = load_config_inactifs()


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


def is_ip_allowed():
    """Retourne True si l'IP est dans la liste autorisée."""
    return request.remote_addr in ALLOWED_IPS

def is_header_valid():
    """Retourne True si le header secret est correct."""
    return request.headers.get("X-App-Access") == APP_AUTH_KEY

def is_user_agent_allowed():
    """Vérifie si le User-Agent correspond à votre application."""
    user_agent = request.headers.get('User-Agent', '')
    # On vérifie si notre nom d'app est contenu dans le User-Agent
    return ALLOWED_USER_AGENT in user_agent

@app.before_request
def filtrer_acces_global():
    """Vérification stricte de l'IP, du Header et de la Route demandée."""
    
    # 1. Extraction de la route demandée (ex: /kds)
    path = request.path
    
    # Pour les routes avec paramètres (ex: /reset_livraison/123), 
    # on ne garde que le début pour comparer avec la whitelist.
    base_path = "/" + path.split('/')[1] if len(path.split('/')) > 1 else "/"
    
    # 2. VÉRIFICATION DE LA ROUTE (Le nouveau blocage que tu as demandé)
    # On vérifie si le chemin exact OU le chemin de base est dans la liste
    route_autorisee = False
    for route in WHITELIST_ROUTES:
        if path == route or path.startswith(route + "/"):
            route_autorisee = True
            break
            
    if not route_autorisee:
        logger.warning(f"🚫 ROUTE NON AUTORISÉE: {path} par {request.remote_addr}")
        return jsonify({"status": "error", "message": "ACCÈS REFUSÉ : ROUTE INCONNUE"}), 403

    #3. EXCEPTION : Le shutdown doit être accessible sans header secret (depuis 127.0.0.1)

    
    if path == '/kds_pa_alert':
        return
    if path == '/suivi':
        return
    if path == '/temperatures':
        return
    if path == '/static/css/bootstrap.min.css':
        return
    if path == '/static/css/tabulator.min.css':
        return
    if path == '/static/js/tabulator.min.js':
        return
    if path == '/static/js/flatpickr.js':
        return
    if path == '/static/js/jspdf.plugin.autotable.min.js':
        return
    if path == '/static/js/jspdf.umd.min.js':
        return
    if path == '/static/css/flatpickr.min.css':
        return
    if path == '/static/js/html2pdf.bundle.min.js':
        return
    if path == '/static/js/chart.min.js':
        return
    if path == '/static/js/chartjs-plugin-zoom.min.js':
        return
    if path == '/nouvelle_livraison':
        return
    if path == '/mark_all_treated_livreur':
        return
    if path.startswith('/update_status'):
        return
    if path == '/static/sound/beep_short.ogg':
        return
    if path == '/favicon.ico':
        return
    if path == '/kds_pa_pizza':
        return
    if path == '/envoyer_tcp_commande':
        return

    # 4. VÉRIFICATION DE L'IP (Couche 1)
    #if not is_ip_allowed():
    #    logger.warning(f"🚫 IP bloquée: {request.remote_addr}")
    #    return "Accès refusé: IP non autorisée.", 403

    # 5. VÉRIFICATION DU USER-AGENT (Couche 2)
    if not is_user_agent_allowed():
        logger.warning(f"📱 User-Agent non autorisé de: {request.remote_addr}")
        return "Accès interdit: Navigateur non autorisé.", 403

    # 6. VÉRIFICATION DU HEADER SECRET (Couche 3)
    # Obligatoire pour toutes les routes API et KDS
    #if not is_header_valid():
    #    logger.warning(f"🔑 Header invalide de: {request.remote_addr}")
    #    return "Accès interdit: Application non identifiée.", 403


@app.route('/kds_pa_alert')
def kds_pa_alert():
    # 1. Récupération des commandes
    all_orders = db_manager.get_pending_orders_kds_alert()
    
    # 2. On transforme le dictionnaire en une liste pour le tri
    # On crée une liste plate avec toutes les commandes
    order_list = []
    for category in all_orders:
        for order in all_orders.get(category, []):
            order_list.append(order)

    # 3. Tri personnalisé : 
    # Critère 1 : Si service_type est '888', il vient en premier (False < True en Python)
    # Critère 2 : Si service_type n'est pas 888, on trie par bill_id décroissant (nouveau -> ancien)
    # On supprime le int() et on utilise une comparaison de chaînes de caractères
    order_list.sort(key=lambda x: (x.get('service_type') != '888', str(x.get('bill_id', ''))), reverse=False)

    # 4. Reconstruction du dictionnaire pour le template
    # On garde la structure attendue par kds_order_list.html
    pa_alerts = {order['bill_id']: {'data': order} for order in order_list}

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('partials/kds_order_list.html', pa_list=pa_alerts)
    
    return render_template('kds_alert_pa.html', pa_list=pa_alerts, refresh_rate=5)

@app.route('/kds_pa_pizza')
def kds_pa_alert_pizza():
    # 1. Récupération des commandes
    all_orders = db_manager.get_pending_orders_kds_alert_pizza()
    
    # 2. On transforme le dictionnaire en une liste pour le tri, 
    # EN NE GARDANT QUE CEUX QUI ONT LE STATUT 'PIZZA'
    order_list = []
    for category in all_orders:
        for order in all_orders.get(category, []):
            # Filtrage sur le statut PIZZA (insensible à la casse si besoin avec .upper() ou .lower())
            if str(order.get('status', '')).strip().upper() == 'PIZZA':
                order_list.append(order)

    # 3. Tri personnalisé : 
    # Critère 1 : Si service_type est '888', il vient en premier (False < True en Python)
    # Critère 2 : Si service_type n'est pas 888, on trie par bill_id décroissant (nouveau -> ancien)
    order_list.sort(key=lambda x: (x.get('service_type') != '888', str(x.get('bill_id', ''))), reverse=False)

    # 4. Reconstruction du dictionnaire pour le template
    pa_alerts = {order['bill_id']: {'data': order} for order in order_list}

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('partials/kds_order_list.html', pa_list=pa_alerts)
    
    return render_template('kds_alert_pizza.html', pa_list=pa_alerts, refresh_rate=5)

@app.route('/marquer_pa_traitee/<bill_id>', methods=['POST'])
def marquer_pa_traitee(bill_id):
    # On utilise la méthode existante du DBManager
    # Elle gère déjà les bill_id avec suffixes UUID grâce au LIKE
    row_count = db_manager.set_order_status_by_bill_id(bill_id, 'Traitée')
    
    if row_count > 0:
        return jsonify({"status": "success", "message": "Commande marquée comme traitée"}), 200
    else:
        return jsonify({"status": "error", "message": "Facture non trouvée"}), 404

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
    global LIVREURS, LIVREURS_INACTIFS, livraisons_store
    all_orders = db_manager.get_pending_orders()
    
    # 1. LISTE DES IDS VALIDES POUR LE NETTOYAGE
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

    # 3. NETTOYAGE DES COMMANDES TERMINÉES
    ids_to_remove = [bid for bid in livraisons_store if bid not in active_db_ids]
    for bid in ids_to_remove:
        del livraisons_store[bid]

    # 4. PRÉPARATION DU FILTRAGE ET DES STATS
    search_query = request.args.get('search', '').lower()
    show_all = request.args.get('show_all', '0') == '1'

    filtered_livraisons = {}
    stats_casiers = {name: 0 for name in LIVREURS}
    
    # On définit les livreurs qui apparaissent dans les boutons d'assignation
    livreurs_disponibles = [l for l in LIVREURS if l not in LIVREURS_INACTIFS]

    for bid, item in livraisons_store.items():
        if 'data' not in item:
            continue
            
        data = item['data']
        extras = item.get('extras', {})
        
        # --- CONSTRUCTION DE LA CHAÎNE DE RECHERCHE TOTALE ---
        searchable_text = f"{bid} "
        searchable_text += str(data.get('customer_phone', '')).lower() + " "
        searchable_text += str(data.get('address', '')).lower() + " "
        searchable_text += str(data.get('customer_name', '')).lower() + " "
        searchable_text += str(extras.get('custom_note', '')).lower() + " "
        searchable_text += str(extras.get('desired_time', '')).lower() + " "
        
        # Extraction des items pour la recherche
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

        # Calcul des compteurs (on compte même les livreurs inactifs s'ils ont une commande en cours)
        current_livreur = item.get('livreur')
        if current_livreur in stats_casiers:
            stats_casiers[current_livreur] += 1

        # Application du filtre de recherche
        if not search_query or search_query in searchable_text:
            filtered_livraisons[bid] = item

    return render_template(
        'kds_dashboard_livreur.html',
        livraisons=filtered_livraisons,
        livreurs=LIVREURS,              # Liste complète pour l'admin/stats
        livreurs_actifs=livreurs_disponibles, # Liste filtrée pour les boutons d'assignation
        stats=stats_casiers,
        refresh_rate=KDS_REFRESH_RATE,
        search_query=search_query,
        show_all=show_all
    )

@app.route('/kds_pa')
def kds_dashboard_pa():
    # 1. On récupère les commandes actives (En attente, En cours) via la fonction existante
    all_orders = db_manager.get_pa_orders_with_history()
    
    # 2. On récupère les commandes traitées (Archives)
    # Note: On utilise le nom exact de la fonction dans votre db_manager.py
    try:
        data_traitee = db_manager.get_orders_by_status_list(['Traitée'])
        orders_traitees = data_traitee.get('Traitée', [])[-10:] # On prend les 10 dernières
    except AttributeError:
        # Sécurité au cas où le nom de la fonction varierait
        orders_traitees = []

    pa_orders = {}
    
    # Fonction interne pour filtrer et ajouter les commandes de type PA
    def filtrer_et_ajouter(liste_commandes):
        for o in liste_commandes:
            t_num = str(o.get('table_number', '')).strip().upper()
            # On accepte 'PA' seul ou avec un numéro (ex: PA501)
            if t_num == 'PA' or t_num.startswith('PA'):
                bid = str(o.get('id'))
                pa_orders[bid] = {
                    'data': o,
                    'extras': {'custom_note': o.get('note', '')} 
                }

    # On traite les commandes actives
    for status, orders in all_orders.items():
        filtrer_et_ajouter(orders)
    
    # On ajoute les commandes déjà traitées
    filtrer_et_ajouter(orders_traitees)

    # 3. LOGIQUE DE RECHERCHE (Recherche par ID, Table ou Serveur)
    search_query = request.args.get('search', '').lower()
    filtered_pa = {}

    for bid, item in pa_orders.items():
        data = item['data']
        searchable_text = f"{bid} {str(data.get('table_number', '')).lower()} {str(data.get('serveur_name', '')).lower()} "
        
        items_list = data.get('items', [])
        if isinstance(items_list, list):
            for raw_it in items_list:
                searchable_text += str(raw_it).lower() + " "

        if not search_query or search_query in searchable_text:
            filtered_pa[bid] = item

    # 4. Rendu avec le rafraîchissement automatique
    return render_template(
        'kds_dashboard_pa.html',
        pa_list=filtered_pa,
        refresh_rate=KDS_REFRESH_RATE,
        search_query=search_query
    )

@app.route('/kds_placeur')
def kds_dashboard_placeur():
    # 1. Récupération des commandes actives (En attente/En cours)
    all_orders = db_manager.get_pending_orders()
    
    active_db_ids = []
    for status in all_orders:
        for o in all_orders[status]:
            # On considère généralement les livraisons (999) pour le placement
            if str(o.get('table_number')) == '999':
                active_db_ids.append(str(o['id']))

    # 2. Mise à jour du store local (Synchronisation avec la mémoire vive)
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

    # 3. Nettoyage des commandes qui ne sont plus en attente
    ids_to_remove = [bid for bid in livraisons_store if bid not in active_db_ids]
    for bid in ids_to_remove:
        del livraisons_store[bid]

    # 4. Gestion de la recherche
    search_query = request.args.get('search', '').lower()
    filtered_placeur = {}

    for bid, item in livraisons_store.items():
        data = item.get('data', {})
        searchable_text = f"{bid} {str(data.get('address', '')).lower()} {str(data.get('customer_name', '')).lower()}"
        
        if not search_query or search_query in searchable_text:
            filtered_placeur[bid] = item

    # 5. Rendu du template spécifique au placeur
    return render_template(
        'kds_dashboard_placeur.html',
        livraisons=filtered_placeur,
        livreurs=LIVREURS,
        refresh_rate=KDS_REFRESH_RATE,
        search_query=search_query
    )

@app.route('/mark_all_treated_livreur', methods=['POST'])
def mark_all_treated_livreur():
    if request.headers.get('X-App-Access') != APP_AUTH_KEY:
        return jsonify({"success": False, "message": "Accès interdit"}), 403

    try:
        count = db_manager.mark_all_as_treated_livreur()
        return jsonify({"success": True, "count": count, "message": f"{count} commandes marquées comme traitées."}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    
@app.route('/api/livreurs', methods=['GET'])
def get_livreurs():
    return jsonify(load_livreurs())

@app.route('/api/livreurs/add', methods=['POST'])
def add_livreur():
    nom = request.json.get('nom')
    current = load_livreurs()
    if nom and nom not in current:
        current.append(nom)
        save_livreurs(current)
        global LIVREURS
        LIVREURS = current
        return jsonify(success=True)
    return jsonify(success=False, error="Nom invalide ou déjà présent")


@app.route('/envoyer_tcp_commande', methods=['POST'])
def envoyer_tcp_commande():
    # 1. Vérification de la sécurité (Headers)
    if request.headers.get("X-App-Access") != APP_AUTH_KEY:
        return jsonify({"success": False, "message": "🚫 ACCÈS REFUSÉ : SÉCURITÉ"}), 403

    # 2. Récupération des données JSON pour extraire les paramètres
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Aucune donnée reçue"}), 400

    table_number = data.get('table_number')
    order_id = data.get('order_id')

    if not table_number or not order_id:
        return jsonify({"success": False, "message": "Numéro de table ou ID de commande manquant"}), 400

    # 3. Formatage de la trame brute
    trame_tcp = f"ENVOIE #{table_number}"

    # Paramètres du serveur TCP cible (ajustez selon vos besoins ou chargez depuis le JSON)
    IP_DESTINATION = "127.0.0.1"  # Remplacez par l'IP de votre serveur cible
    PORT_DESTINATION = 9100       # Le port TCP d'écoute

    try:
        # 4. Envoi direct via socket TCP (Protocole brut, non JSON)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.settimeout(3.0)  # Timeout de 3 secondes
            client_socket.connect((IP_DESTINATION, PORT_DESTINATION))
            client_socket.sendall(trame_tcp.encode('utf-8'))

        logger.info(f"📤 Trame TCP brute envoyée : '{trame_tcp}' vers {IP_DESTINATION}:{PORT_DESTINATION} pour la commande ID #{order_id}")

        return jsonify({
            "success": True, 
            "trame_envoyee": trame_tcp,
            "message": f"Ordre '{trame_tcp}' envoyé avec succès en TCP brut."
        }), 200

    except Exception as e:
        logger.error(f"💥 Erreur lors de l'envoi TCP de la trame '{trame_tcp}': {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/nouvelle_livraison', methods=['GET', 'POST'])
def nouvelle_livraison():
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify(success=False, error="Aucune donnée reçue"), 400
        
        # Récupération et TRONCATURE des données (Validation)
        # On utilise [:limite] pour couper le texte s'il est trop long
        adresse = str(data.get('adresse', ''))[:200].strip()
        telephone = str(data.get('telephone', 'N/A'))[:15].strip()
        note = str(data.get('note', ''))[:200].strip()
        heure = str(data.get('heure', 'ASAP'))[:20] # 20 suffit largement pour une heure
        
        # Vérification minimale obligatoire
        if not adresse:
            return jsonify(success=False, error="L'adresse est obligatoire"), 400
        
        bid = str(uuid.uuid4())[:8].upper()
        
        # Structure enrichie
        items_list = [
            json.dumps({
                "main_item": f"ADRESSE: {adresse}", 
                "sub_items": [
                    f"TEL: {telephone}", 
                    f"NOTE: {note}", 
                    f"HEURE: {heure}"
                ]
            })
        ]
        
        try:
            db_manager.add_new_order(
                bill_id=bid,
                table_number="999",
                serveuse_name="SYSTÈME",
                service_type="LIVREUR",
                items=items_list,
                status='En attente',
                creation_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                raw_content=f"LIVRAISON MANUELLE\nADR: {adresse}\nTEL: {telephone}\nNOTE: {note}\nHEURE: {heure}"
            )
            return jsonify(success=True, bid=bid)
        except Exception as e:
            logger.error(f"Erreur DB : {e}")
            return jsonify(success=False, error=str(e)), 500
            
    return render_template('formulaire_adresse.html')

@app.route('/api/livreurs/toggle_status', methods=['POST'])
def api_toggle_livreur():
    if request.headers.get("X-App-Access") != APP_AUTH_KEY:
        return jsonify({"status": "error", "message": "🚫 ACCÈS REFUSÉ"}), 403

    data = request.get_json()
    nom = data.get('nom', '').strip()
    
    global LIVREURS_INACTIFS
    if nom in LIVREURS_INACTIFS:
        LIVREURS_INACTIFS.remove(nom)
        msg = f"✅ {nom.upper()} EST RÉACTIVÉ"
    else:
        LIVREURS_INACTIFS.append(nom)
        msg = f"💤 {nom.upper()} EST DÉSACTIVÉ"
    
    # Optionnel: Sauvegarde dans un petit JSON pour garder l'état après redémarrage
    save_config_inactifs(LIVREURS_INACTIFS) 
    
    return jsonify({"status": "success", "message": msg})

@app.route('/api/livreurs/rename', methods=['POST'])
def api_rename_livreur():
    # 1. Sécurité
    if request.headers.get("X-App-Access") != APP_AUTH_KEY:
        return jsonify({"status": "error", "message": "🚫 SÉCURITÉ : ACCÈS NON AUTORISÉ"}), 403

    data = request.get_json()
    ancien = data.get('ancien', '').strip()
    nouveau = data.get('nouveau', '').strip().upper()

    if not nouveau:
        return jsonify({"status": "error", "message": "⚠️ LE NOM NE PEUT PAS ÊTRE VIDE"}), 400

    try:
        # 2. VÉRIFICATION : On regarde dans livraisons_store comme pour le delete
        # On cherche si des commandes sont encore liées à l'ancien nom
        commandes_actives = [
            bid for bid, item in livraisons_store.items() 
            if item.get('livreur') and item.get('livreur').upper() == ancien.upper()
        ]
        
        nb = len(commandes_actives)
        if nb > 0:
            # On bloque car si on renomme le livreur, les commandes en cours 
            # dans livraisons_store deviendraient orphelines.
            return jsonify({
                "status": "error",
                "message": f"🚫 RENOMMAGE IMPOSSIBLE\n\nIl reste {nb} commande(s) dans le casier de {ancien.upper()}.\n\nLivrez-les avant de changer le nom."
            }), 400

        # 3. SI LE CASIER EST VIDE : On procède au changement dans la liste globale
        global LIVREURS
        # On cherche l'index de l'ancien nom pour le remplacer au même endroit
        if ancien in LIVREURS:
            idx = LIVREURS.index(ancien)
            LIVREURS[idx] = nouveau
            save_livreurs(LIVREURS)
            return jsonify({
                "status": "success", 
                "message": f"✅ NOM MODIFIÉ\n\n{ancien.upper()} est maintenant {nouveau}."
            }), 200
        
        return jsonify({"status": "error", "message": f"⚠️ Le livreur '{ancien}' n'existe pas."}), 404

    except Exception as e:
        logger.error(f"Erreur lors du renommage : {e}")
        return jsonify({"status": "error", "message": f"💥 ERREUR SYSTÈME : {str(e)}"}), 500

@app.route('/favicon.ico')
def favicon():
    # Code SVG simple et épuré (Écran noir, bordure orange néon, texte KDS blanc)
    svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
        <rect width="32" height="32" rx="6" fill="#1a1a1a" stroke="#e67e22" stroke-width="2"/>
        <text x="50%" y="60%" font-family="Arial, sans-serif" font-weight="bold" font-size="11" fill="#ffffff" text-anchor="middle" dominant-baseline="middle">KDS</text>
    </svg>"""
    
    response = app.make_response(svg_content)
    response.headers['Content-Type'] = 'image/svg+xml'
    # Optionnel: Cache de 1 jour pour éviter de surcharger le serveur à chaque clic
    response.headers['Cache-Control'] = 'public, max-age=86400'
    return response

@app.route('/api/livreurs/reorder', methods=['POST'])
def api_reorder_livreur():
    data = request.json
    idx = data.get('index')
    direction = data.get('direction')
    
    global LIVREURS
    if direction == 'up' and idx > 0:
        LIVREURS[idx], LIVREURS[idx-1] = LIVREURS[idx-1], LIVREURS[idx]
    elif direction == 'down' and idx < len(LIVREURS) - 1:
        LIVREURS[idx], LIVREURS[idx+1] = LIVREURS[idx+1], LIVREURS[idx]
    
    save_livreurs(LIVREURS)
    return jsonify(success=True)
    
@app.route('/mark_pa_donner/<int:order_id>', methods=['POST'])
def mark_pa_donner(order_id):
    data = request.get_json()
    pa_number = data.get('pa_number', '???')
    
    # On récupère les extras envoyés par le JS (s'ils existent)
    # Si le JS n'envoie rien, on met None pour dire "ne pas toucher à la BD"
    new_note = data.get('custom_note')
    new_time = data.get('desired_time')

    # Logique : Si c'est 'NOTE' ou 'HEURE' (les textes par défaut), 
    # on considère que c'est vide et on ne veut pas écraser la BD.
    if new_note == 'NOTE': new_note = None
    if new_time == 'HEURE': new_time = None

    # On passe ces valeurs à ta fonction. 
    # IL FAUDRA QUE db_manager.update_pa_details SOIT PRÊT À RECEVOIR None
    success = db_manager.update_pa_details(
        order_id, 
        new_note,   # Sera None si inchangé
        new_time,   # Sera None si inchangé
        'UST',      # À adapter si tu gères les ustensiles aussi
        donner_au_pc=True, 
        pa_number=pa_number
    )
    
    if success:
        return jsonify({'status': 'success', 'pa_number': pa_number})
    return jsonify({'status': 'error'}), 500


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
                port_reel = ports_config.get(key_suffix, {}).get("SERIAL_PORT_PRINTER")
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


@app.route('/update_status_livraisons/<string:bill_id>/<string:new_status>', methods=['POST'])
def update_status_livraisons(bill_id, new_status):
    # Sécurité globale
    if request.headers.get('X-App-Access') != APP_AUTH_KEY:
        return jsonify({"success": False, "message": "Accès interdit"}), 403

    # Correction des accents (si nécessaire)
    if new_status == 'Traitee':
        new_status = 'Traitée'

    valid_statuses = ['En cours', 'Traitée', 'Annulée', 'En attente', 'Pizza']
    if new_status not in valid_statuses:
        return jsonify({"success": False, "message": f"Statut non valide: {new_status}"}), 400
        
    try:
        # Appel à la fonction spécifique qui cible uniquement le clone Livreur
        row_count = db_manager.set_order_status_by_bill_id_livraison(bill_id, new_status)
        
        if row_count > 0:
            logger.info(f"Statut (Livreur) Bill ID {bill_id} mis à jour à '{new_status}'.")
            return jsonify({"success": True, "message": f"Statut mis à jour pour {bill_id} dans la base Livreur."}), 200
        else:
            return jsonify({"success": False, "message": f"Bill ID {bill_id} non trouvé dans la base Livreur ou aucun changement."}), 404
    except Exception as e:
        logger.error(f"Erreur DB Livreur: {str(e)}")
        return jsonify({"success": False, "message": f"Erreur DB: {str(e)}"}), 500

@app.route('/update_status/<string:bill_id>/<string:new_status>', methods=['POST'])
def update_status(bill_id, new_status):
    # Sécurité globale
    if request.headers.get('X-App-Access') != 'MonApplicationUnique123!':
        return jsonify({"success": False, "message": "Accès interdit"}), 403

    # CORRECTION DES ACCENTS : Si le JS envoie 'Traitee', on le remet en 'Traitée' pour la DB
    if new_status == 'Traitee':
        new_status = 'Traitée'

    valid_statuses = ['En cours', 'Traitée', 'Annulée', 'En attente' , 'Pizza']
    if new_status not in valid_statuses:
        return jsonify({"success": False, "message": f"Statut non valide: {new_status}"}), 400
        
    try:
        row_count = db_manager.set_order_status_by_bill_id(bill_id, new_status)
        
        if row_count > 0:
            logger.info(f"Statut Bill ID {bill_id} mis à jour à '{new_status}'.")
            return jsonify({"success": True, "message": f"Statut mis à jour pour {bill_id}."}), 200
        else:
            return jsonify({"success": False, "message": f"Bill ID {bill_id} non trouvé ou aucun changement."}), 404
    except Exception as e:
        return jsonify({"success": False, "message": f"Erreur DB: {str(e)}"}), 500

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

@app.route('/api/livreurs/delete', methods=['POST'])
def api_delete_livreur():
    if request.headers.get("X-App-Access") != APP_AUTH_KEY:
        return jsonify({"status": "error", "message": "🚫 SÉCURITÉ : ACCÈS NON AUTORISÉ"}), 403

    data = request.get_json()
    nom_livreur = data.get('nom', '').strip()

    try:
        # On vérifie dans livraisons_store
        commandes_actives = [
            bid for bid, item in livraisons_store.items() 
            if item.get('livreur') and item.get('livreur').upper() == nom_livreur.upper()
        ]
        
        nb = len(commandes_actives)
        if nb > 0:
            # MESSAGE EXPLICITE : On dit pourquoi ET quoi faire.
            return jsonify({
                "status": "error",
                "message": f"🚫 SUPPRESSION IMPOSSIBLE\n\nLe casier de {nom_livreur.upper()} contient encore {nb} commande(s).\n\nVeuillez livrer ou transférer ces commandes avant de retirer ce livreur."
            }), 400

        global LIVREURS
        # On cherche le nom exact (sensible à la casse ou non selon ton stockage)
        if nom_livreur in LIVREURS:
            LIVREURS.remove(nom_livreur)
            save_livreurs(LIVREURS)
            return jsonify({
                "status": "success", 
                "message": f"✅ CONFIGURATION MISE À JOUR\n\nLe casier de {nom_livreur.upper()} a été définitivement supprimé."
            }), 200
        
        return jsonify({"status": "error", "message": f"⚠️ Erreur : Le livreur '{nom_livreur}' n'existe pas dans la liste."}), 404

    except Exception as e:
        logger.error(f"Erreur suppression livreur: {e}")
        return jsonify({"status": "error", "message": f"💥 ERREUR SYSTÈME : {str(e)}"}), 500

@app.route('/suivi', methods=['GET'])
def afficher_suivi():
    # render_template cherche automatiquement dans le dossier 'templates'
    return render_template('temperature_view.html')

@app.route('/temperatures', methods=['GET'])
def get_temperatures():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        return jsonify({"data": [], "error": "Dates manquantes"})

    results = []
    log_directory = r"C:\resto_controller\temperature"
    
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        for day_offset in range((end - start).days + 1):
            current_date = start + timedelta(days=day_offset)
            date_str = current_date.strftime('%Y-%m-%d')
            file_name = f"logs_{date_str}.json"
            file_path = os.path.join(log_directory, file_name)
            
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                    
                    # --- ICI : On ajoute la date à chaque entrée ---
                    for entry in file_data:
                        # Si 'entry' est un dictionnaire, on ajoute la clé 'date'
                        if isinstance(entry, dict):
                            entry['date'] = date_str
                            
                    results.extend(file_data)
                    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
    return jsonify({"data": results})

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
            requests.post(f'http://127.0.0.1:5000/shutdown') # On utilise localhost et le port par défaut pour le shutdown (sauf si on change la route)
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
            requests.post(f'http://127.0.0.1:5000/shutdown')
            
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