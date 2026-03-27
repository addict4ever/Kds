# Ce fichier centralise les constantes et configurations partagées entre les différents modules KDS.

import os
# kds_constants.py

# --- Couleurs (Inspirées de l'interface Web) ---
STATUS_COLORS = {
    'En attente': '#3498db', # Bleu
    'En cours': '#f1c40f',    # Jaune
    'Traitée': '#2ecc71',     # Vert
    'Annulée': '#e74c3c',     # Rouge Vif (pour la suppression rapide)
    'Archivée': '#7f8c8d',
}

SERIAL_PORT_TCP_1 = '0.0.0.0'  # Écoute sur toutes les interfaces réseau
SERIAL_PORT_TCP_1_PORT = 9100      # Port standard pour les imprimantes réseau

SERIAL_TCP_PRINTER_1 = '192.168.5.210'  # IP de l'imprimante cible
SERIAL_TCP_PRINTER_1_PORT = 9100        # Port de l'imprimante cible

SCREEN_2_GEOMETRY_FULLSCREEN = "1920x1080+1920+0"

# Couleurs de fond de l'interface (Inspirées de base.html)
BG_MAIN = '#2c3e50'     # Gris foncé / Background
# Correction: Renommage de BG_CARD en CARD_BG pour correspondre aux imports
CARD_BG = '#34495e'     # Bleu foncé / Card background 

MAX_CARDS_PER_ROW = 5   # Maximum de cartes par rangée horizontale
SCROLL_PAGE_SIZE = 1    # Nombre de rangées à faire défiler lors d'un clic sur la flèche
# Autres couleurs
COLOR_TEXT = '#ecf0f1'  # Blanc cassé
COLOR_ACCENT = '#3498db'
COLOR_WARNING = '#f1c40f'
COLOR_NOTE = '#f1c40f'

# --- Dimensions ---

H_SCROLLBAR_HEIGHT = 15

CARD_WIDTH = 300
CARD_BORDER_WIDTH = 5
CARD_PADDING = 5
H_MARGIN = 5 # Marge horizontale entre les colonnes

# --- Logique KDS ---
# Définir l'ordre et les colonnes de service
SERVICE_TYPES = ["COMMANDE"]
SERVICE_SPLIT_MARKER = 'AUTRE' 

# Autres
REFRESH_RATE_MS = 3000
TRUNCATE_LEN = 40

ORDER_STATUS_PENDING = 'En attente'  # ⭐ AJOUT CRITIQUE

# --- PARAMÈTRES DE LECTURE DU PORT SÉRIE ---
BAUD_RATE = 9600
SERIAL_TIMEOUT = 0.5

# --- Détection du système d’exploitation ---
if os.name == 'nt':  # Windows
    SERIAL_PORT = 'COM3'
    SERIAL_PORT_PRINTER = 'COM4'
    SERIAL_PORT_COMPUTER = 'COM5'
else:  # Linux / Mac
    SERIAL_PORT = '/dev/ttyUSB0'
    SERIAL_PORT_PRINTER = '/dev/ttyUSB1'
    SERIAL_PORT_COMPUTER = '/dev/ttyUSB2'

# --- PARAMÈTRES DE DÉCODAGE DU FLUX POS ---
ESC = b'\x1b'
TICKET_END_SEQUENCE = b'#############################'
SERVICE_SPLIT_MARKER = " | SERVICE_SPLIT | "

TICKET_STATUS_COMPLETED = 'TERMINÉ'

# --- LOGIQUE DE CLASSIFICATION DES ITEMS ---
ITEM_CATEGORY = {
    # Sauces
    'SAUCE': [
        'sauce','extra sce bbq','sauce a part', 'mayo', 'ketchup','relish', 'moutarde', 'bbq', 'tartare', 'brune', 'poivre', '2degree'
    ],

    # Vinaigrettes
    'VINAIGRETTE': [
        'vinaigrette', 'chef', 'césar', 'italienne', 'thaï', 'balsamique','salade chef'
    ],

    # Côtés / accompagnements
    'TOAST_SIDE': [
        'frites sauce','sauce a part','EXTRA POUTINE DEJ','extra gr creton','combo frite','cornichon','ailes','poutine','pt. poutine italien.','ff', 'Frite Famille','pain grille', 'frites', 'salade de chou', 'riz', 'legumes',
        'patate au four', 'patate pille', 'patate ancienne', 'ancienne','bb. frite sauce','bb. poutine',
        'extra poulet club','pois vert','extra poutine','frites sauce', 'spag', 'duo frite','pilées','oignon francais','extra bacon','extra oignon cuit'
    ],

    # Toasts / pains
    'TOAST': [
        'pas beurre','toast', 'pain blanc', 'pain brun', 'pain menage', 'menage blanc','sand. aux poulet'
        'menage brun', 'gaufre', 'muffin son et raisin', 'pain dore fruit','sand. aux tomates'
    ],

    # Bases à œufs
    'OEUF_BASE': [
        'LE QUEBECOIS', 'NO 4 OEUF + VIANDE', 'fricasse', 'NO 3 OEUF + VIANDE', 'extra cottage',
        'ordre viande', 'ordre crepe','saucisse', 'jambon','oeuf', 'omelette', 'benedictine', 'tourne', 'tourne leger', 'creve',
        'omelette jambon/fromage', 'fricasse vege', 'demi fricasse vege',
        'crepe choco-banane', 'omelette western', 'bene tradi', 'bene saumon',
        'creve bien cuit', 'miroir','ENF. CHOCO BANANE', 'NO 1 OEUF', 'NO 2 OEUF'
    ],

    # Pâtes
    'PATES': [
        'spag midi','FETT','viande', 'fett. alfredo','spag','spaghetti', 'lasagne', 'macaroni', 'penne', 'linguine',
        'tagliatelle', 'fettuccine', 'carbonara', 'alfredo'
    ],

    # Boissons
    'BOISSON': [
        'café', 'thé', 'jus', 'lait', 'pepsi', '7up', 'eau', 'chocolat chaud', 'soda', 'latte', 'espresso'
    ],

    # ⭐ PLATS (PIZZA RETIRÉE)
    'PLATS': [
        'POITRINE POULET MIDI','chessburger','ragout','CUISSE POULET MIDI', 'POITRINE POULET', 'CUISSE POULET MIDI', 'SAL. THAI CREV. BOUL', 'CROQUETTE POULET', 'DOIGT POULET ENF',
        'DOIGTS POULET MIDI', 'FISH N CHIP MIDI', 'FISH N CHIP', 'BR. F.MIGNON', 'POULET', 'CLUB SANDWICH',
        'bicfteck midi','FILET SOLE MEUNIERE','hambourgeois' 'SAL THAI POUL MIDI',  's-m. maison 12 po','SAL CESAR POULET', 'SAL. THAI POULET', 'hamburger', 'pizza'
    ],
}

USER_PLATS_KEYWORDS_OVERRIDE = [
    'nachos grat.','club', 'cuisse', 'POITRINE POULET MIDI', 'POITRINE POULET', 'THAI', 
    'FISH N CHIP', 'mignon', 'poulet', 'CLUB', 'SOLE MEUNIERE', 
    'SAL CESAR POULET', 'THAI', 'hamburger', 'hot', 'ST-JACQUES',
    'saute', 'cotes','hamburger','soupe', 'batonnets', 'smoke', 's-m', 'fettucinee','steak','burger'
]

# --- LOGIQUE PÂTES SPÉCIALES ---
KEYWORDS_PATES_SPECIALES = {
    'FETTUCCINE': ['fruits de mer', 'viande', 'alfredo', 'carbonara'], # Logique maintenue
    'SPAGHETTI': ['fruits de mer', 'viande', 'alfredo', 'carbonara'],
}

# --- MAPPAGE DES SAUCES AUTOMATIQUES (aucun changement) ---
ITEM_SAUCE_MAP = {
    "LE QUEBECOIS": {"Petit Patée": 1},
    "LE BRUNCH": {"Petite Crêpe": 1},
    "SAL CESAR midi": {"Vinaigrette César": 1},
    "BATONNETS MIDI": {"Sauce Spag": 1},
    "BAT. FROMAGE": {"Sauce Spag": 1},
    "(6) AILES POULET": {"Sauce 2Degree": 1},
    "FONDU PARMESAN": {"Tartare Fondu": 1},
    "ENT. SAL. CESAR": {"Vinaigrette César": 1},
    "ENT. SAL. DU CHEF": {"Vinaigrette Chef": 1},
    "ENT. COQ. ST-JACQUES": {"Vinaigrette Chef": 1},
    "SALADE CESAR": {"Vinaigrette César": 1},
    "SALADE CHEF": {"Vinaigrette Chef": 1},

    "SPC. FAMILLE": {"Frite Famille": 1},
    "POITRINE POULET MIDI": {"Sauce BBq": 1},
    "CUISSE POULET MIDI": {"Sauce BBq": 1},
    "DOIGTS POULET MIDI": {"Sauce BBq": 1},
    "DOIGTS POULET": {"Sauce BBq": 1},
    "CROQUETTE POULET": {"Sauce BBq": 1},

    "STEAK HACHE MIDI": {"Sauce Brune": 1, "Vinaigrette Chef": 1},
    "STEAK HACHE": {"Sauce Brune": 1, "Vinaigrette Chef": 1},

    "BR. F.MIGNON": {"Vinaigrette Chef": 1, "Portion Ancienne": 1, "Sauce Poivre": 1},
    "BR. POULET": {"Vinaigrette Chef": 1, "Portion Ancienne": 1, "Sauce BBq": 1},
    "F.MIGNON": {"Vinaigrette Chef": 1, "Portion Ancienne": 1, "Sauce BBq": 1},

    "FILET SOLE MEUNIERE": {"Vinaigrette Chef": 1, "Tartare Sole": 1},
    "ASS. CREV. BOUL -BANG": {"Vinaigrette César": 1, "Portion Ancienne": 1},
    "ASS. CREV/LANGOUST.": {"Vinaigrette César": 1, "Portion Ancienne": 1},
    "ASS. CREV. AIL": {"Vinaigrette César": 1, "Portion Ancienne": 1},

    "SAL CHEF MIDI": {"Vinaigrette Chef": 1},
    "SAL. CESAR POULET": {"Vinaigrette César": 1},
    "SAL CESAR POULET MIDI": {"Vinaigrette César": 1},
    "SAL CHEF POULET MIDI": {"Vinaigrette César": 1},
    "SAL CESAR MIDI": {"Vinaigrette César": 1},
    "SAL. THAI POULET": {"Vinaigrette Thai": 1},
    "SAL THAI POULET MIDI": {"Vinaigrette Thai": 1},
    "SAL. THAI CREV. BOUL": {"Vinaigrette Thai": 1},

    "FISH N CHIP MIDI": {"Vinaigrette Chef": 1, "Tartare Fish": 1},
    "FISH N CHIPS": {"Vinaigrette Chef": 1, "Tartare Fish": 1},

    "NACHOS GRAT": {"Salsa": 2, "Crème Sure": 2},
    "DUO PIZZA SPAG MIDI": {"Combo Spag": 1},
    "DUO PIZZA FRITE MIDI": {"Combo Frite": 1},
    "DUO PIZZA SAL CÉSARAR": {"Vinaigrette César": 1},
}

# --- DÉTECTION DE VINAIGRETTES (aucun changement) ---
KEYWORDS_VINEGRETTE_CHEF = "salade chef"
KEYWORDS_VINEGRETTE_CESAR = "salade césar"
KEYWORDS_SANS_SALADE = "sans salade"

# --- AGRÉGATION DE FRUITS DE MER (aucun changement) ---
SEAFOOD_COUNT_MAP = {
    "F.MIGNON CREVETTE": {"Crevettes Total": 6, "Langoustines Total": 0},
    "F.MIGNON LANGOUSTINE": {"Crevettes Total": 0, "Langoustines Total": 4},
    "F.MIGNON CREV LANG": {"Crevettes Total": 3, "Langoustines Total": 3},
    "ass. crevette ail": {"Crevettes Total": 12, "Langoustines Total": 0},
    "ass. lang ail": {"Crevettes Total": 0, "Langoustines Total": 8},
    "ass. crev. lang": {"Crevettes Total": 6, "Langoustines Total": 4},
}

KEYWORDS_SEAFOOD_MODIFIERS = {
    "CREVETTE": ["crevette", "creves", "crev"],
    "LANGOUSTINE": ["langoustine", "langoustines", "lang"],
    "CREV LANG": ["crev lang", "lang crev", "crevette langoustine", "langoustine crevette"],
}

TOTAL_KEY_SHRIMP = "CREVETTES TOTAL 🍤"
TOTAL_KEY_SCAMPI = "LANGOUSTINES TOTAL 🦐"

# --- LOGIQUE D'INCLUSION/EXCLUSION SPÉCIALE (NOUVELLE) ---
# Ces mots-clés dans l'article principal annulent toute EXCLUSION de pizza.
INCLUSION_OVERRIDES = [
    'DUO PIZZA SAL',     # Ex: DUO PIZZA SAL CÉSARAR
    'DUO PIZZA SPAG',    # Ex: DUO PIZZA SPAG MIDI
    'DUO PIZZA FRITE',   # Ex: DUO PIZZA FRITE MIDI
    'DUO PATE ET PIZZ'   # Ex: DUO PATE ET PIZZ
]

# --- EXCLUSIONS ---
# AJOUT DE TOUS LES MOTS-CLÉS DE PIZZA POUR FILTRER LES COMMANDES COMPLÈTES
EXCLUSION_KEYWORDS = [
    'pizza','service', 'pizzas','small', 'pepe', '1/2','bambino', 'duo pizza','pizza','garni', 'combo pizza','mini', 'small', 'medium', 'large', 'xlarge', 'bambino',
    'garnie', 'vege','coeur palmier', 'annulation', 'vege', 'grecque', 'hawaïenne',
    'viande fumée', 'supreme', 'fromage', # Types de pizza
    'petite', 'moyenne', 'grande', 'mince', 'famille','spcial', 'croute mince' # Tailles/Croûtes
]
