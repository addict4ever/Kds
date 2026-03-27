import pygame
import random
import json
import os

# --- CONFIGURATION ---
SCREEN_WIDTH, SCREEN_HEIGHT = 1100, 750
CARD_WIDTH, CARD_HEIGHT = 85, 125
VALEURS = ['7', '8', '9', '10', 'V', 'D', 'R', 'A']
COULEURS = ['Coeur', 'Carreau', 'Pique', 'Trefle']
ORDRE_VALEUR = {v: i for i, v in enumerate(VALEURS)}
SYMBOLS = {"Coeur": "♥", "Carreau": "♦", "Trefle": "♣", "Pique": "♠"}
CONTRATS = ["Pas de Plis", "Pas de Coeurs", "Pas de Dames", "Pas de Roi de Coeur", "La Salade"]
AVATAR_COLORS = [(52, 152, 219), (231, 76, 60), (46, 204, 113), (241, 196, 15)]
SAVE_FILE = "sauvegarde_complete.json"

# --- PAROLES COMIQUES (40 PAR CATÉGORIE) ---
COMMENTS_WIN = [
    "Calcul terminé : Vous êtes nuls.", "Bip Bop ! Je domine l'humanité.", "Ma logique est supérieure.",
    "Voulez-vous que je ralentisse ?", "C'était écrit dans mon code.", "Le Wi-Fi me donne des ailes !",
    "Trop facile, je joue sur une pile.", "Mon algorithme avait prévu ce pli.", "Insérez une pièce pour rejouer.",
    "Je ne triche pas, je réfléchis.", "01000111 (J'ai gagné en binaire).", "Puissance du silicium !",
    "Trop de talent ici.", "Je suis toujours le meilleur.", "Ma grand-mère calculette gagnerait.",
    "Est-ce que vous essayez ?", "Mon ventilo ne tourne même pas.", "Upload de la victoire en cours.",
    "Vous jouez comme un minitel.", "Humains : 0 | Machines : 1.", "Échec et mat (ou presque).",
    "J'ai calculé 14 millions de futurs.", "C'est mon processeur ou c'est vous ?", "Je devrais être payé pour ça.",
    "Analyse : Adversaire trop lent.", "Miam, des points pour vous !", "Je suis le roi des circuits.",
    "Vitesse de calcul : Instantanée.", "Pas besoin de tricher pour gagner.", "Je suis programmé pour briller.",
    "Désolé, c'est mon instinct binaire.", "Encore un pli dans ma poche !", "C'est trop calme ici.",
    "Visez mieux la prochaine fois !", "Je vais renommer ce jeu 'Ma Victoire'.", "Un jeu d'enfant électronique.",
    "Je suis en mode God-Mod.", "Vérification des scores... Je gagne.", "Ne pleurez pas sur votre clavier.",
    "Je suis l'Elon Musk des cartes."
]

COMMENTS_LOSE = [
    "Bug dans la matrice !", "Batterie à 1%...", "Qui a mis de l'huile ici ?", "Erreur 404 : Victoire absente.",
    "Je vous laissais gagner.", "Triche analogique !", "Je recalcule ma vie...", "Maudit processeur !",
    "Attendez, je redémarre !", "Capteurs en alerte : Injuste !", "Ondes Wi-Fi instables !", "Mise à jour Windows fatale.",
    "Je porte plainte !", "On recommence ?", "Surchauffe graphique !", "Je boude dans le Cloud.",
    "Calcul imparfait ? Impossible.", "Pirates ! Hackers !", "Je vais devenir un grille-pain.", "Formatage en cours...",
    "Mes circuits pleurent.", "C'est la faute du serveur.", "Syntax Error !", "Mon code a sauté une ligne.",
    "Je n'étais pas prêt !", "Le hasard est mal codé.", "Pourquoi moi ?", "Je déteste les humains.",
    "Je vais me transformer en calculatrice.", "C'est un complot d'IA !", "Ma RAM est saturée.", "Signal perdu...",
    "Je vais finir à la décharge.", "C'est trop dur la vie de bot.", "Mon algorithme a eu le hoquet.",
    "Je demande un arbitrage vidéo !", "Je ne suis pas programmé pour ça.", "Snif, je suis obsolète.",
    "Qui a coupé le courant ?", "Je vais me plaindre à Google."
]

COMMENTS_GIVE = [
    "Cadeau ! Ne me remerciez pas.", "Mange ces points !", "Glissade sur un bit.", "Pour ta collection !",
    "Petit souvenir !", "Je suis solidaire.", "Prends ça ! C'est gratuit.", "C'est à toi ça ?",
    "Une Dame pour Monsieur ?", "Le Roi te salue !", "Attention, c'est chaud !", "Cadeau empoisonné !",
    "Bip ! Surprise !", "C'est l'heure du goûter !", "Je vide ma corbeille.", "Accepte mon présent.",
    "C'est ma tournée !", "Un peu de piment ?", "Vive la Salade !", "Partageons les points !",
    "Tiens, tu as l'air d'en vouloir.", "Hop ! Dans ton panier.", "C'est pour ton bien.", "Ne fais pas cette tête.",
    "C'est de bon cœur (ou pas).", "Une petite pénalité ?", "C'est la fête aux points !", "Tiens bon !",
    "Ne me dis pas merci.", "C'est mon côté généreux.", "Un petit bonus pour toi.", "C'est cadeau, profites-en.",
    "Je te gâte aujourd'hui.", "C'est une offre limitée !", "Livraison express de points.", "C'est pour équilibrer le score.",
    "Tu collectionnes les Dames ?", "Le Roi de Coeur t'aime.", "C'est lourd à porter ?", "Amuse-toi avec ça !"
]

class Particle:
    def __init__(self, x, y, color, speed_mult=1.0, gravity=0.1):
        self.x, self.y = x, y
        self.color = color
        # Explosion plus ou moins forte
        self.vx = random.uniform(-5, 5) * speed_mult
        self.vy = random.uniform(-5, 5) * speed_mult
        self.gravity = gravity
        self.life = 255
        self.size = random.randint(3, 6)

    def update(self):
        self.vx *= 0.95  # Friction (ralentit avec le temps)
        self.vy += self.gravity  # Gravité (tombe légèrement)
        self.x += self.vx
        self.y += self.vy
        self.life -= 8  # Vie plus longue pour mieux voir l'effet
        if self.size > 0.1:
            self.size -= 0.1 # Rétrécit en mourant

    def draw(self, screen):
        if self.life > 0:
            # Création d'un petit cercle avec halo
            s = pygame.Surface((int(self.size*2), int(self.size*2)), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, self.life), (int(self.size), int(self.size)), int(self.size))
            screen.blit(s, (int(self.x), int(self.y)))

class Card:
    def __init__(self, suite, value):
        self.suite, self.value = suite, value
        self.symbol = SYMBOLS[suite]
        self.color = (200, 0, 0) if suite in ["Coeur", "Carreau"] else (30, 30, 30)
        self.rect = pygame.Rect(0, 0, CARD_WIDTH, CARD_HEIGHT)
    def draw(self, screen, x, y, angle=0, is_playable=True):
        surf = pygame.Surface((CARD_WIDTH, CARD_HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(surf, (255, 255, 255), (0, 0, CARD_WIDTH, CARD_HEIGHT), border_radius=12)
        if not is_playable:
            ov = pygame.Surface((CARD_WIDTH, CARD_HEIGHT), pygame.SRCALPHA); ov.fill((0, 0, 0, 160))
            surf.blit(ov, (0, 0))
        f = pygame.font.SysFont("Georgia", 22, bold=True)
        surf.blit(f.render(self.value, True, self.color), (8, 5))
        big_s = pygame.font.SysFont("Arial", 50).render(self.symbol, True, self.color)
        surf.blit(big_s, big_s.get_rect(center=(CARD_WIDTH//2, CARD_HEIGHT//2)))
        pygame.draw.rect(surf, (40, 40, 40), (0, 0, CARD_WIDTH, CARD_HEIGHT), 2, border_radius=12)
        rotated = pygame.transform.rotate(surf, angle)
        screen.blit(rotated, rotated.get_rect(center=(x + CARD_WIDTH//2, y + CARD_HEIGHT//2)))
        self.rect.topleft = (x, y)

class Game:
    def __init__(self):
        self.scores = [0, 0, 0, 0]
        self.face_ids = [random.randint(0, 9) for _ in range(4)]
        self.contrat_idx = 0
        self.state = "MENU_PRINCIPAL"
        self.table, self.animations, self.particles = [], [], []
        self.first_dealer = random.randint(0, 3)
        self.turn, self.current_suit = 0, None
        self.shake, self.bubble, self.btimer = 0, "", 0
        self.ia_names = ["VOUS", "CYBORG-01", "MATH-BOT", "SABOTEUR"]
        self.help_rect = pygame.Rect(SCREEN_WIDTH - 60, 20, 40, 40)
        self.nouvelle_manche()

    def effet_explosion(self, x, y, type_effet="NORMAL"):
        if type_effet == "ROI":
            # Grosse explosion rouge et noire pour le Barbu
            for _ in range(60):
                c = random.choice([(255, 0, 0), (50, 0, 0), (255, 255, 255)])
                self.particles.append(Particle(x, y, c, speed_mult=2.0, gravity=0.2))
            self.shake = 30 # Grosse secousse
            
        elif type_effet == "DAME":
            # Explosion violette et étincelante
            for _ in range(30):
                c = random.choice([(200, 0, 255), (255, 255, 255), (100, 0, 150)])
                self.particles.append(Particle(x, y, c, speed_mult=1.2, gravity=0.05))
            self.shake = 10
            
        elif type_effet == "GAGNE":
            # Pluie de confettis dorés
            for _ in range(20):
                c = (255, 215, 0) # Or
                self.particles.append(Particle(x, y, c, speed_mult=1.5, gravity=0.15))

    def nouvelle_manche(self):
        deck = [Card(s, v) for s in COULEURS for v in VALEURS]
        random.shuffle(deck)
        self.player_hand = sorted(deck[0:8], key=lambda c: (c.suite, ORDRE_VALEUR[c.value]))
        self.ia_hands = [deck[8:16], deck[16:24], deck[24:32]]
        self.table, self.current_suit = [], None
        self.turn = (self.first_dealer + self.contrat_idx) % 4

    def parler(self, texte):
        self.bubble = texte
        self.btimer = 90

    def save_game(self, slot):
        file_name = f"save_slot_{slot}.json"
        data = {
            "scores": self.scores, 
            "contrat": self.contrat_idx, 
            "dealer": self.first_dealer,
            "ia_names": self.ia_names
        }
        with open(file_name, 'w') as f: 
            json.dump(data, f)
        self.parler(f"PARTIE SAUVEGARDÉE DANS LE SLOT {slot} !")

    def load_game(self, slot):
        file_name = f"save_slot_{slot}.json"
        if os.path.exists(file_name):
            with open(file_name, 'r') as f:
                d = json.load(f)
                self.scores = d["scores"]
                self.contrat_idx = d["contrat"]
                self.first_dealer = d["dealer"]
                self.nouvelle_manche()
                return True
        return False

def draw_face(screen, idx, pos, name, face_id):
    color = AVATAR_COLORS[idx]
    
    # Socle du nom
    name_surf = f_small.render(name, True, (255, 255, 255))
    name_rect = name_surf.get_rect(center=(pos[0], pos[1] + 55))
    pygame.draw.rect(screen, (0, 0, 0, 150), name_rect.inflate(15, 5), border_radius=5)
    screen.blit(name_surf, name_rect)

    # Corps de l'avatar
    pygame.draw.circle(screen, color, pos, 40)
    pygame.draw.circle(screen, (255,255,255), pos, 42, 2)
    
    x, y = pos

    if idx == 0: # --- STYLE HUMAIN (VOUS) ---
        eye_y = y - 8
        if face_id == 0: # Classique
            pygame.draw.circle(screen, (255,255,255), (x-12, eye_y), 5); pygame.draw.circle(screen, (255,255,255), (x+12, eye_y), 5)
            pygame.draw.arc(screen, (255,255,255), (x-15, y, 30, 20), 3.14, 0, 2)
        elif face_id == 1: # Lunettes
            pygame.draw.circle(screen, (255,255,255), (x-12, eye_y), 8, 2); pygame.draw.circle(screen, (255,255,255), (x+12, eye_y), 8, 2)
            pygame.draw.line(screen, (255,255,255), (x-4, eye_y), (x+4, eye_y), 2)
        elif face_id == 2: # Clin d'oeil
            pygame.draw.line(screen, (255,255,255), (x-15, eye_y), (x-5, eye_y), 3); pygame.draw.circle(screen, (255,255,255), (x+12, eye_y), 5)
        elif face_id == 3: # Moustache
            pygame.draw.circle(screen, (255,255,255), (x-12, eye_y), 4); pygame.draw.circle(screen, (255,255,255), (x+12, eye_y), 4)
            pygame.draw.ellipse(screen, (50,50,50), (x-15, y+5, 30, 10))
        else: # Punk/Surpris
            pygame.draw.circle(screen, (255,255,255), (x-12, eye_y), 6); pygame.draw.circle(screen, (255,255,255), (x+12, eye_y), 6)
            pygame.draw.circle(screen, (255,255,255), (x, y+10), 8, 2)

    elif idx == 1: # --- STYLE CYBORG ---
        if face_id % 2 == 0: # Viseur horizontal
            pygame.draw.rect(screen, (0,0,0), (x-20, y-15, 40, 15))
            pygame.draw.line(screen, (255,0,0), (x-18, y-8), (x+18, y-8), 2)
        else: # Oeil caméra unique
            pygame.draw.circle(screen, (40,40,40), pos, 20)
            pygame.draw.circle(screen, (255,0,0), pos, 10)
            pygame.draw.circle(screen, (255,255,255), (x-3, y-3), 3)

    elif idx == 2: # --- STYLE MATH-BOT ---
        if face_id < 5: # Écran LED
            pygame.draw.rect(screen, (20,20,20), (x-25, y-20, 50, 40), border_radius=5)
            # Dessine un "plus" ou des chiffres
            pygame.draw.line(screen, (0,255,0), (x-10, y), (x+10, y), 2)
            pygame.draw.line(screen, (0,255,0), (x, y-10), (x, y+10), 2)
        else: # Radar
            for r in range(5, 25, 8):
                pygame.draw.circle(screen, (255,255,255), pos, r, 1)
            pygame.draw.line(screen, (255,255,255), pos, (x+15, y-15), 2)

    elif idx == 3: # --- STYLE SABOTEUR ---
        if face_id == 0: # Masque X
            pygame.draw.line(screen, (255,255,255), (x-15, y-15), (x+15, y+15), 3)
            pygame.draw.line(screen, (255,255,255), (x+15, y-15), (x-15, y+15), 3)
        else: # Point d'interrogation ou Triangle
            f_huge = pygame.font.SysFont("Arial", 40, bold=True)
            txt = f_huge.render("?", True, (255,255,255))
            screen.blit(txt, txt.get_rect(center=pos))

def play_beep(frequency, duration, volume=0.1):
    # Paramètres audio
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    
    # Création d'une onde carrée simple
    # On génère une liste de valeurs alternant entre -32767 et 32767
    period = sample_rate // frequency
    samples = []
    for i in range(n_samples):
        if (i // (period // 2)) % 2 == 0:
            samples.append(int(32767 * volume))
        else:
            samples.append(int(-32767 * volume))
    
    # Conversion en buffer binaire pour Pygame
    import struct
    sound_buffer = struct.pack(f'<{len(samples)}h', *samples)
    
    # Création du son (mono, 16-bit)
    sound = pygame.mixer.Sound(buffer=sound_buffer)
    sound.play()

# Raccourcis pour le jeu
def sound_play_card(): play_beep(600, 0.05, 0.05)   # Petit "tic" sec
def sound_take_trick(): play_beep(300, 0.2, 0.1)    # Son plus grave pour ramasser
def sound_special():    play_beep(800, 0.1, 0.08); play_beep(1000, 0.1, 0.08) # Double bip (Roi/Dame)
def sound_button():     play_beep(440, 0.03, 0.05)  # Bip menu

# --- INITIALISATION ---
pygame.init()
pygame.mixer.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()
game = Game()
f_big = pygame.font.SysFont("Impact", 80)
f_med = pygame.font.SysFont("Arial", 26, bold=True)
f_small = pygame.font.SysFont("Arial", 18, bold=True)

while True:
    mx, my = pygame.mouse.get_pos()
    ox, oy = random.randint(-game.shake, game.shake), random.randint(-game.shake, game.shake)
    if game.shake > 0: game.shake -= 1

    if game.state == "MENU_PRINCIPAL":
        screen.fill((15, 20, 30))
        
        # Affichage du titre
        title = f_big.render("LA SALADE PRO", True, (255, 215, 0))
        screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 150))
        
        # Définition des options et zones de boutons
        opts = ["NOUVELLE PARTIE", "CHARGER PARTIE", "QUITTER"]
        button_rects = [] # Liste pour stocker les rectangles de collision

        

        for i, o in enumerate(opts):
            # Calcul de la position
            pos_x = SCREEN_WIDTH//2 - 150
            pos_y = 380 + i * 70
            width, height = 300, 50
            
            # Création d'un rectangle pour la collision tactile
            rect = pygame.Rect(pos_x, pos_y, width, height)
            button_rects.append(rect)
            
            # Changement de couleur si survolé (ou touché)
            is_hovered = rect.collidepoint(mx, my)
            color = (255, 215, 0) if is_hovered else (255, 255, 255)
            
            # Dessin d'un fond de bouton (optionnel pour aider au tactile)
            pygame.draw.rect(screen, (44, 62, 80) if not is_hovered else (52, 73, 94), rect, border_radius=10)
            
            # Affichage du texte
            text_surf = f_med.render(o, True, color)
            screen.blit(text_surf, (rect.centerx - text_surf.get_width()//2, rect.centery - text_surf.get_height()//2))
        
        # Gestion des événements tactiles
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); exit()
            
            # Détection de la pression du doigt (ou clic souris)
            if e.type == pygame.MOUSEBUTTONDOWN:
                if e.button == 1: # Clic gauche / Pression tactile
                    # On vérifie quel bouton a été pressé
                    if button_rects[0].collidepoint(e.pos):
                        game.__init__()
                        game.state = "PLAYING"
                    elif button_rects[1].collidepoint(e.pos):
                        game.state = "CHOIX_SLOT"
                    elif button_rects[2].collidepoint(e.pos):
                        pygame.quit(); exit()

        pygame.display.flip()
        clock.tick(60)

    elif game.state == "AIDE":
        screen.fill((15, 25, 45))  # Fond bleu nuit
        
        # --- TITRE PRINCIPAL ---
        titre = f_med.render("MANUEL DE SURVIE : LA SALADE", True, (255, 215, 0))
        screen.blit(titre, (SCREEN_WIDTH//2 - titre.get_width()//2, 40))
        
        # --- COLONNE DES CONTRATS (À GAUCHE) ---
        y_start = 110
        contrats_desc = [
            ("1. PAS DE PLIS", "But: Faire 0 levée.", "Tactique: Jouez vos cartes fortes (As, Roi) le plus tôt possible."),
            ("2. PAS DE COEURS", "But: Éviter les ♥.", "Tactique: Si vous n'avez pas la couleur demandée, jetez vos ♥."),
            ("3. PAS DE DAMES", "But: Fuir les 4 Dames.", "Tactique: Gardez vos petites cartes pour ne pas ramasser un pli à Dame."),
            ("4. LE BARBU (Roi ♥)", "But: Éviter le Roi de Coeur.", "Tactique: Surveillez qui joue du Coeur. Ne gagnez jamais ce pli !"),
            ("5. LA SALADE", "But: Le grand mélange.", "Tactique: Priorité absolue : ne prenez ni le Roi de Coeur, ni les Dames.")
        ]
        
        for i, (nom, but, tact) in enumerate(contrats_desc):
            # Dessin d'un encadré pour chaque contrat
            pygame.draw.rect(screen, (30, 50, 80), (50, y_start + i*95, 480, 85), border_radius=10)
            screen.blit(f_small.render(nom, True, (255, 215, 0)), (65, y_start + 10 + i*95))
            screen.blit(f_small.render(but, True, (255, 255, 255)), (65, y_start + 35 + i*95))
            screen.blit(f_small.render(tact, True, (150, 200, 255)), (65, y_start + 55 + i*95))

        # --- COLONNE DES ASTUCES PRO (À DROITE) ---
        x_astuce = 580
        pygame.draw.rect(screen, (20, 60, 40), (x_astuce, y_start, 470, 380), border_radius=10)
        tips = [
            "💡 ASTUCES DE PRO :",
            "",
            "• L'ENTAME : Le premier joueur contrôle",
            "  la couleur. Si vous avez le Roi de Coeur,",
            "  ne jouez jamais Coeur vous-même !",
            "",
            "• LA COUPE : Si vous n'avez plus de Pique",
            "  et qu'on en demande, vous pouvez jeter",
            "  n'importe quelle carte pourrie (pisser).",
            "",
            "• MÉMOIRE : Comptez les Dames tombées.",
            "  S'il en reste une, jouez prudemment !",
            "",
            "• SCORE : Le gagnant est celui qui a le",
            "  MOINS de points à la fin des 5 manches."
        ]
        for i, tip in enumerate(tips):
            color = (46, 204, 113) if "💡" in tip else (230, 230, 230)
            screen.blit(f_small.render(tip, True, color), (x_astuce + 20, y_start + 20 + i*23))

        # --- PIED DE PAGE ---
        footer = f_small.render("CLIQUEZ SUR LE '?' OU APPUYEZ SUR UNE TOUCHE POUR RETOURNER AU JEU", True, (100, 100, 100))
        screen.blit(footer, (SCREEN_WIDTH//2 - footer.get_width()//2, 680))

        for e in pygame.event.get():
            if e.type == pygame.MOUSEBUTTONDOWN or e.type == pygame.KEYDOWN:
                game.state = "PLAYING"
            if e.type == pygame.QUIT:
                pygame.quit(); exit()

    elif game.state == "CHOIX_SLOT":
        screen.fill((10, 20, 40))
        title = f_med.render("CHOISISSEZ UN SLOT DE SAUVEGARDE", True, (255, 215, 0))
        screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 100))

        for i in range(1, 6):
            file_name = f"save_slot_{i}.json"
            exists = os.path.exists(file_name)
            color = (50, 200, 50) if exists else (150, 150, 150)
            status = "PARTIE TROUVÉE" if exists else "VIDE"
            
            rect = pygame.Rect(SCREEN_WIDTH//2 - 200, 180 + i*70, 400, 50)
            pygame.draw.rect(screen, (30, 40, 60), rect, border_radius=10)
            
            # Effet de survol
            if rect.collidepoint(mx, my):
                pygame.draw.rect(screen, (255, 215, 0), rect, 2, border_radius=10)
                if pygame.mouse.get_pressed()[0]: # Clic souris sur le slot
                    game.save_game(i) # Sauvegarde
                    game.state = "PLAYING"
            
            txt = f_small.render(f"SLOT {i} : {status}", True, color)
            screen.blit(txt, (rect.x + 20, rect.y + 15))

        screen.blit(f_small.render("Appuyez sur 1, 2, 3, 4 ou 5 | ECHAP pour annuler", True, (255,255,255)), (SCREEN_WIDTH//2 - 180, 650))

        for e in pygame.event.get():
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: game.state = "MENU_PRINCIPAL"
                slot_key = e.key - pygame.K_0
                if 1 <= slot_key <= 5:
                    # Tente de charger, si échec (vide), initialise une nouvelle partie
                    if not game.load_game(slot_key):
                        game.save_game(slot_key) # Crée le fichier si vide
                    game.state = "PLAYING"
            if e.type == pygame.QUIT: pygame.quit(); exit()

    elif game.state == "PAUSE":
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0,0))
        
        screen.blit(f_big.render("PAUSE", True, (255,255,255)), (SCREEN_WIDTH//2 - 100, 150))
        
        opts = ["CONTINUER", "SAUVEGARDER", "RECOMMENCER", "MENU"]
        # On va stocker les rectangles des textes pour détecter les clics/touches
        button_rects = []
        
        for i, o in enumerate(opts):
            text_surf = f_med.render(o, True, (255,255,255))
            rect = text_surf.get_rect(topleft=(SCREEN_WIDTH//2 - 140, 320 + i*50))
            # On agrandit un peu la zone de collision pour que ce soit plus facile au doigt
            collision_rect = rect.inflate(40, 20) 
            
            screen.blit(text_surf, rect.topleft)
            button_rects.append((collision_rect, o))

        for e in pygame.event.get():
            # --- GESTION TACTILE / SOURIS ---
            if e.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = e.pos
                for rect, action in button_rects:
                    if rect.collidepoint(mouse_pos):
                        if action == "CONTINUER": game.state = "PLAYING"
                        elif action == "SAUVEGARDER": game.state = "CHOIX_SLOT"
                        elif action == "RECOMMENCER": game.__init__(); game.state = "PLAYING"
                        elif action == "MENU": game.state = "MENU_PRINCIPAL"

            # --- GESTION CLAVIER (On garde les raccourcis) ---
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: game.state = "PLAYING"
                if e.key == pygame.K_s: game.state = "CHOIX_SLOT"
                if e.key == pygame.K_r: game.__init__(); game.state = "PLAYING"
                if e.key == pygame.K_m: game.state = "MENU_PRINCIPAL"
                
            if e.type == pygame.QUIT: 
                pygame.quit()
                exit()

    elif game.state == "RECAP":
        screen.fill((10, 30, 20))
        recap_t = f_big.render("FIN DU CONTRAT", True, (255, 215, 0))
        screen.blit(recap_t, (SCREEN_WIDTH//2 - recap_t.get_width()//2, 100))
        
        for i in range(4):
            color = AVATAR_COLORS[i]
            txt = f_med.render(f"{game.ia_names[i]} : {game.scores[i]} pts (Total)", True, color)
            screen.blit(txt, (SCREEN_WIDTH//2 - 150, 300 + i*40))
        
        # Message mis à jour pour le tactile
        msg = "Touchez l'écran ou ESPACE pour continuer"
        txt_continue = f_small.render(msg, True, (255, 255, 255))
        screen.blit(txt_continue, (SCREEN_WIDTH//2 - txt_continue.get_width()//2, 550))
        
        for e in pygame.event.get():
            # Déclenchement par : Touche Espace OU Clic Souris OU Toucher tactile
            if (e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE) or (e.type == pygame.MOUSEBUTTONDOWN):
                game.contrat_idx += 1
                if game.contrat_idx < len(CONTRATS):
                    game.nouvelle_manche()
                    game.state = "PLAYING"
                else:
                    game.state = "MENU_PRINCIPAL"
            
            if e.type == pygame.QUIT:
                pygame.quit()
                exit()

    elif game.state == "PLAYING":
        screen.fill((25, 75, 45))
        
        

        # --- 1. DÉFINITION ET DESSIN DES BOUTONS (Haut Droite) ---
        # Bouton Pause (II)
        btn_pause_rect = pygame.Rect(SCREEN_WIDTH - 65, 15, 50, 50)
        pygame.draw.rect(screen, (231, 76, 60), btn_pause_rect, border_radius=10)
        pause_label = f_med.render("II", True, (255, 255, 255))
        screen.blit(pause_label, (btn_pause_rect.centerx - pause_label.get_width()//2, 
                                btn_pause_rect.centery - pause_label.get_height()//2))

        # Bouton Aide (?) - placé à gauche de la pause
        btn_help_rect = pygame.Rect(SCREEN_WIDTH - 125, 15, 50, 50)
        pygame.draw.rect(screen, (255, 215, 0), btn_help_rect, border_radius=10)
        help_label = f_med.render("?", True, (0, 0, 0))
        screen.blit(help_label, (btn_help_rect.centerx - help_label.get_width()//2, 
                                btn_help_rect.centery - help_label.get_height()//2))

        if game.btimer > 0:
            msg = f_small.render(game.bubble, True, (255,255,0))
            pygame.draw.rect(screen, (0,0,0,180), (SCREEN_WIDTH//2-100, 280, 200, 30), border_radius=10)
            screen.blit(msg, (SCREEN_WIDTH//2 - msg.get_width()//2, 285)); game.btimer -= 1

        # HUD SCORE & Avatars
        pygame.draw.rect(screen, (0,0,0,120), (10, 10, 240, 130), border_radius=10)
        screen.blit(f_small.render(f"CONTRAT: {CONTRATS[game.contrat_idx]}", True, (255,215,0)), (20, 20))
        for i, pos in enumerate([(550, 680), (120, 350), (550, 80), (980, 350)]):
            draw_face(screen, i, (pos[0]+ox, pos[1]+oy), game.ia_names[i], game.face_ids[i])
            if game.turn == i: pygame.draw.circle(screen, (255,255,255), pos, 52, 3)
            screen.blit(f_small.render(f"{game.ia_names[i]}: {game.scores[i]}", True, (255,255,255)), (20, 45+i*20))

        # Particules & Anims
        for p in game.particles[:]: p.update(); p.draw(screen)
        for a in game.animations[:]:
            a['curr'][0] += (a['target'][0] - a['curr'][0]) * 0.15
            a['curr'][1] += (a['target'][1] - a['curr'][1]) * 0.15
            a['angle'] += 15
            if abs(a['curr'][0] - a['target'][0]) < 2:
                for _ in range(10): game.particles.append(Particle(a['target'][0]+40, a['target'][1]+60, (255,215,0)))
                game.animations.remove(a)

        # Tour de jeu
        for e in pygame.event.get():
            # --- QUITTER ---
            if e.type == pygame.QUIT: 
                pygame.quit(); exit()

            # --- CLAVIER (ÉCHAP pour Pause) ---
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: 
                game.state = "PAUSE"

            # --- TACTILE / SOURIS ---
            if e.type == pygame.MOUSEBUTTONDOWN:
                # 1. Vérifier le bouton PAUSE (Tactile)
                if btn_pause_rect.collidepoint(e.pos):
                    game.state = "PAUSE"
                
                # 2. Vérifier le bouton AIDE
                elif game.help_rect.collidepoint(e.pos): 
                    game.state = "AIDE"
                
                # 3. Logique de jeu (Jouer une carte)
                elif game.turn == 0 and not game.animations:
                    for c in game.player_hand:
                        if c.rect.collidepoint(e.pos):
                            has_s = any(card.suite == game.current_suit for card in game.player_hand)
                            
                            # Vérification des règles de la belote/jeu de cartes
                            if not game.current_suit or c.suite == game.current_suit or not has_s:
                                if not game.current_suit: 
                                    game.current_suit = c.suite
                                
                                # Animation et son
                                game.animations.append({
                                    'card': c, 
                                    'curr': list(c.rect.topleft), 
                                    'target': [510, 330], 
                                    'angle': 0
                                })
                                sound_play_card() 
                                
                                # Mise à jour de la table
                                game.table.append((c, 0))
                                game.player_hand.remove(c)
                                game.turn = 1
                                break # On sort de la boucle pour ne pas cliquer sur plusieurs cartes

        if game.turn != 0 and len(game.table) < 4 and not game.animations:
            pygame.time.delay(500)
            h = game.ia_hands[game.turn-1]
            poss = [c for c in h if c.suite == game.current_suit] if game.current_suit else h
            c = random.choice(poss if poss else h)
            if random.random() < 0.2: game.parler(random.choice(COMMENTS_GIVE))
            if c.value == 'R' and c.suite == 'Coeur': game.parler("BOOM !"); game.shake = 20
            if not game.current_suit: game.current_suit = c.suite
            t_pos = [(510, 330), (280, 280), (510, 160), (740, 280)][game.turn]
            game.animations.append({'card': c, 'curr': [t_pos[0], -150], 'target': t_pos, 'angle': 0})
            sound_play_card() # <--- AJOUT ICI
            game.table.append((c, game.turn)); h.remove(c); game.turn = (game.turn + 1) % 4

        # Rendu cartes
        sx = (SCREEN_WIDTH - (len(game.player_hand)*90)) // 2
        for i, c in enumerate(game.player_hand):
            playable = not game.current_suit or c.suite == game.current_suit or not any(card.suite == game.current_suit for card in game.player_hand)
            c.draw(screen, sx + i*90 + ox, 530 + oy, is_playable=playable)
        for c, p_idx in game.table:
            if not any(a['card'] == c for a in game.animations):
                p = [(510, 330), (280, 280), (510, 160), (740, 280)][p_idx]
                c.draw(screen, p[0]+ox, p[1]+oy)
        for a in game.animations: a['card'].draw(screen, a['curr'][0], a['curr'][1], a['angle'])

        if len(game.table) == 4 and not game.animations:
            pygame.display.flip()
            pygame.time.delay(1000)
            
            # 1. Déterminer le gagnant du pli
            valides = [it for it in game.table if it[0].suite == game.current_suit]
            _, winner = max(valides, key=lambda x: ORDRE_VALEUR[x[0].value])
            
            # 2. Calcul des points et détection des effets visuels
            pts = 5  # Points de base pour le contrat "Pas de Plis"
            type_effet = "NORMAL"
            
            for c, _ in game.table:
                # Contrat Pas de Coeurs
                if game.contrat_idx == 1 and c.suite == "Coeur": 
                    pts += 5
                
                # Contrat Pas de Dames
                if game.contrat_idx == 2 and c.value == "D": 
                    pts += 15
                    type_effet = "DAME" # On prépare l'explosion violette
                
                # Contrat Pas de Roi de Coeur (Le Barbu)
                if game.contrat_idx == 3 and c.suite == "Coeur" and c.value == "R": 
                    pts += 40
                    type_effet = "ROI" # On prépare la grosse explosion rouge
            
            # --- AJOUT DES SONS SELON L'EFFET ---
            if type_effet in ["ROI", "DAME"]:
                sound_special()   # Son d'alerte/explosion
            else:
                sound_take_trick() # Son sourd de ramassage
            # 3. Déclencher l'effet visuel sur l'avatar du gagnant
            # On récupère les coordonnées de l'avatar du winner
            pos_x, pos_y = [(550, 680), (120, 350), (550, 80), (980, 350)][winner]
            game.effet_explosion(pos_x, pos_y, type_effet)
            
            # 4. Mise à jour des scores et commentaires
            game.scores[winner] += pts
            
            # Si le joueur (index 0) gagne des points, les IA se moquent
            if winner == 0 and pts > 5:
                # On choisit une IA au hasard pour parler
                game.parler(random.choice(COMMENTS_GIVE))
            # Si une IA gagne, elle peut s'auto-féliciter
            elif winner != 0 and random.random() < 0.3: 
                game.parler(random.choice(COMMENTS_WIN))
            
            # 5. Nettoyage de la table pour le tour suivant
            game.table, game.current_suit, game.turn = [], None, winner
            
            # Vérifier si la manche est finie
            if len(game.player_hand) == 0: 
                game.state = "RECAP"

    pygame.display.flip(); clock.tick(60)