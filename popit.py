import pygame
import random
import math
import array
import json
import os

# --- Configuration ---
WIDTH, HEIGHT = 1920, 1080
BUBBLE_RADIUS = 28
FPS = 60
GRAVITY = 0.28
COLORS = [
    (255, 80, 80), (80, 255, 80), (80, 80, 255), 
    (255, 255, 80), (255, 80, 255), (80, 255, 255), (255, 150, 50)
]
FUN_TEXTS = [
    # --- Action & BD ---
    "POW!", "ZAP!", "SLAM!", "YEAH!", "WIZZ!", 
    "BOOM!", "POP!", "SUPER!", "WOW!", "MEGA!",
    "KABOOM!", "BAM!", "ULTRA!", "CHAMPION!", "KING!",
    
    # --- Menu Restaurant & Salsa ---
    "PIZZA!", "BURGER!", "TACO!", "SUSHI!", "FRITES!",
    "SALSA!", "SPICY!", "PIMENT!", "BURRITO!", "NACHOS!",
    "GUACAMOLE!", "CHORIZO!", "JALAPEÑO!", "TABASCO!", "CALIENTE!",
    
    # --- Humour & Chef ---
    "MAMMA MIA!", "CHEF!", "YUMMY!", "CRUNCH!", "DELUXE!",
    "C'EST CUIT!", "SAIGNANT!", "MAMMOUTH!", "GROS LOT!", "JACKPOT!"

    # --- Spécial Salsa & Mexique ---
    "QUESADILLA!", "ENCHILADA!", "CHILI!", "MUY BUENO!", "FIESTA!",
    "CARAMBA!", "SOMBRERO!", "CORIANDRE!", "LIME!", "PICANTE!",
    
    # --- Fast-Food & Junk Food ---
    "NUGGETS!", "HOT-DOG!", "KEBAB!", "DONUT!", "PANCAKE!",
    "MILKSHAKE!", "FRY-DAY!", "BACON!", "CHEDDAR!", "KETCHUP!",
    
    # --- Humour de Cuisine ---
    "AU FOUR!", "CRAMÉ!", "TROP BON!", "L'ADDITION!", "SANS OIGNON!",
    "TRIPLE STEAK!", "MENU MAXI!", "FRITOOO!", "C'EST CHAUD!", "PAS TOUCHE!",
    
    # --- Onomatopées Drôles & Bruitages ---
    "SHLOOOUP!", "CRUNCHY!", "SPLAT!", "GLOU-GLOU!", "MMMHHH!",
    "Miam-Miam!", "SLURP!", "BURP!", "CRAAAAC!", "GIGA-GOUT!"

]

SCORE_FILE = "bubble_history.json"


# --- INITIALISATION AUDIO GLOBALE COMPATIBLE PYQT ---
audio_works = False

# Force un pilote audio compatible avec les applications GUI externes
import platform
if platform.system() == "Windows":
    # 'waveout' ou 'directsound' permettent à Pygame de partager la carte son avec PyQt
    os.environ['SDL_AUDIODRIVER'] = 'waveout' 

try:
    pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
    pygame.mixer.init()
    audio_works = True
    print("Pygame Mixer initialisé avec succès.")
except pygame.error as e:
    try:
        # Repli si waveout n'est pas supporté par la vieille carte son
        if 'SDL_AUDIODRIVER' in os.environ: del os.environ['SDL_AUDIODRIVER']
        pygame.mixer.init()
        audio_works = True
    except pygame.error:
        # Sécurité ultime pour éviter le crash complet
        os.environ['SDL_AUDIODRIVER'] = 'dummy'
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2)
            print("Mode audio virtuel activé (cohabitation GUI).")
        except:
            print("Impossible d'initialiser le mixer audio.")

pygame.init()

# --- Gestion des Scores ---
def save_score(score):
    if score <= 0: return
    history = load_history()
    history.append(score)
    history.sort(reverse=True)
    history = history[:5]
    with open(SCORE_FILE, "w") as f:
        json.dump(history, f)

def load_history():
    if not os.path.exists(SCORE_FILE): return [0]
    try:
        with open(SCORE_FILE, "r") as f: return json.load(f)
    except: return [0]

# --- Générateur de Sons ---
def gen_snd(f_start, f_end, dur, wave_type="sine", vol=15000):
    s_rate = 22050
    n = int(s_rate * (dur / 1000.0))
    buf = array.array('h', [0] * n)
    for i in range(n):
        t = i / s_rate
        f = f_start + (f_end - f_start) * (i / n)
        v = math.sin(2 * math.pi * f * t) if wave_type == "sine" else (1.0 if math.sin(2 * math.pi * f * t) > 0 else -1.0)
        buf[i] = int(v * vol * (1 - i / n))
    
    try:
        # Tente de générer le son si le mixer a répondu
        return pygame.mixer.Sound(buf)
    except:
        # Retourne un conteneur de données vides pour éviter que le jeu plante si l'audio est muet
        return pygame.mixer.Sound(buffer=bytes(n * 2))

SOUNDS_POP = [gen_snd(random.randint(600, 1200), random.randint(300, 500), 100) for _ in range(8)]
SOUNDS_GOLD = [gen_snd(800, 1600, 200, "sine", 18000) for _ in range(3)]
EXPLOSION_SND = gen_snd(120, 30, 600, "square", 20000)
LEVEL_UP_SND = gen_snd(400, 900, 800, "sine")

# --- Classes d'Effets Visuels ---
class Effect:
    def __init__(self, x, y, color):
        self.x, self.y = float(x), float(y)
        self.color = color
        self.life = 1.0
        self.dead = False
    def update(self):
        self.life -= 0.02
        if self.life <= 0: self.dead = True

class Debris(Effect):
    def __init__(self, x, y, color):
        super().__init__(x, y, color)
        self.vx, self.vy = random.uniform(-7, 7), random.uniform(-12, 2)
    def update(self):
        super().update()
        self.vy += GRAVITY
        self.x += self.vx
        self.y += self.vy
    def draw(self, surf):
        s = int(self.life * 10)
        if s > 0: pygame.draw.rect(surf, self.color, (int(self.x), int(self.y), s, s))

class StarParticle(Effect):
    def __init__(self, x, y, color):
        super().__init__(x, y, color)
        self.angle = random.uniform(0, math.pi*2)
        self.speed = random.uniform(3, 8)
    def update(self):
        super().update()
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
    def draw(self, surf):
        r = 8 * self.life
        pygame.draw.circle(surf, (255, 255, 255), (int(self.x), int(self.y)), int(r))

class Shockwave(Effect):
    def draw(self, surf):
        r = int((1 - self.life) * 160)
        alpha = int(self.life * 255)
        s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r, r), r, 5)
        surf.blit(s, (self.x-r, self.y-r))

class FloatingText(Effect):
    def __init__(self, x, y, color, text, size=45):
        super().__init__(x, y, color)
        self.text = text
        self.font = pygame.font.SysFont("Impact", size)
        self.vx = random.uniform(-2, 2)
        self.angle = random.randint(-15, 15)
    def draw(self, surf):
        t_surf = self.font.render(self.text, True, self.color)
        t_surf = pygame.transform.rotate(t_surf, self.angle)
        t_surf.set_alpha(int(self.life * 255))
        y_off = (1 - self.life) * 120
        surf.blit(t_surf, (int(self.x - t_surf.get_width()//2), int(self.y - y_off)))

class Confetti(Effect):
    def __init__(self, x, y):
        super().__init__(x, y, random.choice(COLORS))
        self.vx, self.vy = random.uniform(-4, 4), random.uniform(-10, -20)
        self.rot = 0
    def update(self):
        super().update()
        self.vy += 0.4
        self.x += self.vx
        self.y += self.vy
        self.rot += 15
    def draw(self, surf):
        s = pygame.Surface((12, 12), pygame.SRCALPHA)
        s.fill(self.color)
        rs = pygame.transform.rotate(s, self.rot)
        surf.blit(rs, (self.x, self.y))
# --- 10 Nouveaux Effets Visuels ---

class Firework(Effect):
    """Explosion de petites étincelles qui ralentissent"""
    def __init__(self, x, y, color):
        super().__init__(x, y, color)
        self.vels = [(random.uniform(-5, 5), random.uniform(-5, 5)) for _ in range(8)]
    def update(self):
        super().update()
        self.x += random.uniform(-1, 1) # Tremblement
    def draw(self, surf):
        for vx, vy in self.vels:
            px = self.x + vx * (1 - self.life) * 50
            py = self.y + vy * (1 - self.life) * 50
            size = int(self.life * 5)
            if size > 0:
                pygame.draw.circle(surf, self.color, (int(px), int(py)), size)

class RingExpand(Effect):
    """Un disque plein qui s'évapore en s'agrandissant"""
    def draw(self, surf):
        radius = int((1 - self.life) * 100)
        alpha = int(self.life * 150)
        s = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (radius, radius), radius)
        surf.blit(s, (self.x - radius, self.y - radius))

class GhostBubble(Effect):
    """Une silhouette de bulle qui monte vers le ciel"""
    def __init__(self, x, y, color):
        super().__init__(x, y, color)
        self.vy = -2
    def update(self):
        super().update()
        self.y += self.vy
    def draw(self, surf):
        alpha = int(self.life * 255)
        r = BUBBLE_RADIUS
        s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r, r), r, 2)
        surf.blit(s, (self.x - r, self.y - r))

class SparkleLine(Effect):
    """Des traits laser qui partent du centre"""
    def __init__(self, x, y, color):
        super().__init__(x, y, color)
        self.angles = [random.uniform(0, math.pi*2) for _ in range(6)]
    def draw(self, surf):
        length = (1 - self.life) * 80
        for a in self.angles:
            x2 = self.x + math.cos(a) * length
            y2 = self.y + math.sin(a) * length
            pygame.draw.line(surf, self.color, (self.x, self.y), (x2, y2), 3)

class PixelPop(Effect):
    """Des pixels qui s'éparpillent en grille"""
    def __init__(self, x, y, color):
        super().__init__(x, y, color)
        self.offsets = [(random.randint(-20, 20), random.randint(-20, 20)) for _ in range(5)]
    def draw(self, surf):
        for ox, oy in self.offsets:
            dist = (1 - self.life) * 40
            pygame.draw.rect(surf, self.color, (self.x + ox*dist*0.1, self.y + oy*dist*0.1, 6, 6))

class GlitchCircle(Effect):
    """Un cercle qui se décale bizarrement (effet électronique)"""
    def draw(self, surf):
        r = int(self.life * BUBBLE_RADIUS)
        if r > 0:
            off = random.randint(-10, 10)
            pygame.draw.circle(surf, (255, 255, 255), (self.x + off, self.y), r, 1)
            pygame.draw.circle(surf, self.color, (self.x - off, self.y), r, 1)

class SmokeCloud(Effect):
    """Un petit nuage de fumée qui disparaît"""
    def __init__(self, x, y, color):
        super().__init__(x, y, (200, 200, 200))
        self.vx = random.uniform(-1, 1)
    def update(self):
        super().update()
        self.y -= 1
        self.x += self.vx
    def draw(self, surf):
        alpha = int(self.life * 100)
        size = int((1 - self.life) * 40) + 10
        s = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (200, 200, 200, alpha), (size, size), size)
        surf.blit(s, (self.x - size, self.y - size))

class MoneySign(Effect):
    """Pour les bulles dorées : un symbole '$' qui monte"""
    def __init__(self, x, y, color):
        super().__init__(x, y, (255, 215, 0))
        self.font = pygame.font.SysFont("Arial", 30, bold=True)
    def update(self):
        super().update()
        self.y -= 3
    def draw(self, surf):
        t = self.font.render("$", True, self.color)
        t.set_alpha(int(self.life * 255))
        surf.blit(t, (self.x, self.y))

class PolygonSpin(Effect):
    """Un triangle ou carré qui tourne sur lui-même"""
    def __init__(self, x, y, color):
        super().__init__(x, y, color)
        self.angle = 0
    def update(self):
        super().update()
        self.angle += 20
    def draw(self, surf):
        size = int(self.life * 25)
        if size > 0:
            s = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
            pygame.draw.rect(s, self.color, (0, 0, size, size))
            rs = pygame.transform.rotate(s, self.angle)
            surf.blit(rs, (self.x, self.y))

class HeartBurst(Effect):
    """Des petits coeurs qui s'envolent (parfait pour la forme COEUR)"""
    def draw(self, surf):
        alpha = int(self.life * 255)
        size = int(self.life * 15)
        if size > 5:
            # Dessine un petit diamant/coeur simplifié
            pts = [(self.x, self.y-size), (self.x+size, self.y), (self.x, self.y+size), (self.x-size, self.y)]
            pygame.draw.polygon(surf, (*self.color, alpha), pts)

# --- 20 Nouveaux Effets Visuels ---

class SpeedLine(Effect):
    """Des lignes de vitesse verticales (effet Manga/Action)"""
    def __init__(self, x, y, color):
        super().__init__(x, y, color)
        self.h = random.randint(40, 100)
    def draw(self, surf):
        alpha = int(self.life * 255)
        s = pygame.Surface((4, self.h), pygame.SRCALPHA)
        s.fill((*self.color, alpha))
        surf.blit(s, (self.x, self.y - (1 - self.life) * 200))

class PizzaSlice(Effect):
    """Une petite pointe de pizza qui tourne (spécial Pizzeria)"""
    def __init__(self, x, y, color):
        super().__init__(x, y, (255, 200, 50))
        self.angle = 0
        self.vx = random.uniform(-5, 5)
        self.vy = random.uniform(-8, -2)
    def update(self):
        super().update()
        self.vy += 0.3
        self.x += self.vx
        self.y += self.vy
        self.angle += 10
    def draw(self, surf):
        size = int(self.life * 20)
        if size > 2:
            s = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
            pygame.draw.polygon(s, (255, 200, 50), [(size, 0), (size*2, size*2), (0, size*2)])
            rs = pygame.transform.rotate(s, self.angle)
            surf.blit(rs, (self.x, self.y))

class BubbleFragment(Effect):
    """La bulle éclate en deux demi-cercles qui s'écartent"""
    def __init__(self, x, y, color):
        super().__init__(x, y, color)
        self.offset = 0
    def update(self):
        super().update()
        self.offset += 4
    def draw(self, surf):
        alpha = int(self.life * 255)
        r = BUBBLE_RADIUS
        # Gauche
        pygame.draw.arc(surf, (*self.color, alpha), (self.x-r-self.offset, self.y-r, r*2, r*2), math.pi/2, 3*math.pi/2, 3)
        # Droite
        pygame.draw.arc(surf, (*self.color, alpha), (self.x-r+self.offset, self.y-r, r*2, r*2), -math.pi/2, math.pi/2, 3)

class LightningBolt(Effect):
    """Un petit éclair électrique instantané"""
    def __init__(self, x, y, color):
        super().__init__(x, y, (200, 255, 255))
        self.pts = [(x + random.randint(-20, 20), y + i*20) for i in range(-3, 4)]
    def draw(self, surf):
        if self.life > 0.5:
            pygame.draw.lines(surf, self.color, False, self.pts, 3)

class DNAHelix(Effect):
    """Deux points qui tournent l'un autour de l'autre"""
    def draw(self, surf):
        t = (1 - self.life) * 10
        off_x = math.sin(t) * 40
        pygame.draw.circle(surf, self.color, (int(self.x + off_x), int(self.y)), 5)
        pygame.draw.circle(surf, (255, 255, 255), (int(self.x - off_x), int(self.y)), 5)

class DigitalRain(Effect):
    """Des petits chiffres qui tombent (Style Matrix)"""
    def __init__(self, x, y, color):
        super().__init__(x, y, (0, 255, 70))
        self.char = str(random.randint(0, 9))
        self.font = pygame.font.SysFont("Courier", 20)
    def draw(self, surf):
        t = self.font.render(self.char, True, self.color)
        t.set_alpha(int(self.life * 255))
        surf.blit(t, (self.x, self.y + (1-self.life)*100))

class ExplodingStar(Effect):
    """Une étoile qui grandit et tourne"""
    def __init__(self, x, y, color):
        super().__init__(x, y, color)
        self.rot = 0
    def draw(self, surf):
        self.rot += 15
        s = int(self.life * 40)
        if s > 0:
            pts = []
            for i in range(10):
                r = s if i % 2 == 0 else s//2
                a = math.radians(i * 36 + self.rot)
                pts.append((self.x + math.cos(a)*r, self.y + math.sin(a)*r))
            pygame.draw.polygon(surf, self.color, pts, 2)

class SolarFlare(Effect):
    """Une onde de chaleur ondulante"""
    def draw(self, surf):
        r = int((1 - self.life) * 120)
        for i in range(3):
            off = math.sin(pygame.time.get_ticks()*0.01 + i) * 10
            pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), r + int(off), 1)

class SparkleDust(Effect):
    """Poussière scintillante qui flotte"""
    def __init__(self, x, y, color):
        super().__init__(x, y, (255, 255, 255))
        self.vx = random.uniform(-2, 2)
        self.vy = random.uniform(-2, 2)
    def update(self):
        super().update()
        self.x += self.vx
        self.y += self.vy
    def draw(self, surf):
        if random.random() > 0.3:
            pygame.draw.rect(surf, (255, 255, 255), (self.x, self.y, 2, 2))

class TargetLock(Effect):
    """Un viseur qui se referme"""
    def draw(self, surf):
        gap = self.life * 50
        size = 20
        # 4 coins de viseur
        pygame.draw.line(surf, self.color, (self.x-gap, self.y-gap), (self.x-gap+size, self.y-gap), 2)
        pygame.draw.line(surf, self.color, (self.x-gap, self.y-gap), (self.x-gap, self.y-gap+size), 2)
        pygame.draw.line(surf, self.color, (self.x+gap, self.y+gap), (self.x+gap-size, self.y+gap), 2)
        pygame.draw.line(surf, self.color, (self.x+gap, self.y+gap), (self.x+gap, self.y+gap-size), 2)

class GravityWell(Effect):
    """Un cercle qui aspire les particules (visuel)"""
    def draw(self, surf):
        r = int(self.life * 60)
        if r > 0:
            pygame.draw.circle(surf, (0, 0, 0), (self.x, self.y), r)
            pygame.draw.circle(surf, self.color, (self.x, self.y), r, 2)

class RainbowTrace(Effect):
    """Un trait qui change de couleur"""
    def draw(self, surf):
        c = random.choice(COLORS)
        pygame.draw.line(surf, c, (self.x-50, self.y), (self.x+50, self.y), 4)

class PulseGrid(Effect):
    """Une grille de pixels locale"""
    def draw(self, surf):
        step = 15
        for i in range(-2, 3):
            for j in range(-2, 3):
                alpha = int(self.life * 150)
                pygame.draw.rect(surf, (*self.color, alpha), (self.x + i*step, self.y + j*step, 4, 4))

class FireBall(Effect):
    """Boule de feu qui monte"""
    def update(self):
        super().update()
        self.y -= 4
        self.x += math.sin(self.life * 10) * 5
    def draw(self, surf):
        r = int(self.life * 20)
        pygame.draw.circle(surf, (255, 100, 0), (self.x, self.y), r)

class WaterDrop(Effect):
    """Onde de choc bleue très fine"""
    def draw(self, surf):
        r = int((1 - self.life) * 200)
        pygame.draw.circle(surf, (100, 150, 255), (self.x, self.y), r, 1)

class GeometryPop(Effect):
    """Un triangle, carré et rond s'envolent"""
    def draw(self, surf):
        d = (1-self.life) * 60
        pygame.draw.circle(surf, self.color, (self.x, self.y-d), 5)
        pygame.draw.rect(surf, self.color, (self.x-d, self.y+d, 8, 8))
        pygame.draw.polygon(surf, self.color, [(self.x+d, self.y), (self.x+d+10, self.y+10), (self.x+d-10, self.y+10)])

class GhostTrail(Effect):
    """Laisse une traînée de texte flou"""
    def draw(self, surf):
        f = pygame.font.SysFont("Arial", 20)
        t = f.render("POP!", True, self.color)
        t.set_alpha(int(self.life * 100))
        surf.blit(t, (self.x, self.y))

class MirrorBlast(Effect):
    """Quatre points qui partent en diagonale"""
    def draw(self, surf):
        d = (1-self.life) * 150
        for sx, sy in [(-1,-1), (1,-1), (-1,1), (1,1)]:
            pygame.draw.circle(surf, self.color, (self.x + sx*d, self.y + sy*d), 4)

class EnergyShield(Effect):
    """Un hexagone protecteur qui disparaît"""
    def draw(self, surf):
        r = 50 * self.life
        pts = []
        for i in range(6):
            a = math.radians(i * 60)
            pts.append((self.x + math.cos(a)*r, self.y + math.sin(a)*r))
        pygame.draw.polygon(surf, self.color, pts, 2)

class CoinSpin(Effect):
    """Une pièce qui tourne (score bonus)"""
    def __init__(self, x, y, color):
        super().__init__(x, y, (255, 215, 0))
    def draw(self, surf):
        w = abs(math.sin(pygame.time.get_ticks()*0.01)) * 20
        if w > 1:
            pygame.draw.ellipse(surf, self.color, (self.x - w//2, self.y - 10, w, 20))

class Bubble:
    def __init__(self, x, y, color):
        self.start_x, self.start_y = x, y # Position initiale
        self.x, self.y = x, y
        self.base_color = color
        self.popped = False
        self.scale = 0.0
        self.target_scale = 1.0
        self.is_bomb = random.random() < 0.08
        self.is_gold = random.random() < 0.04
        self.pulse = random.uniform(0, 10)
        # Déphasage unique pour que chaque bulle bouge différemment
        self.offset = random.uniform(0, math.pi * 2)

    def update(self, level=1):
        self.scale += (self.target_scale - self.scale) * 0.15
        self.pulse += 0.1
        
        # --- Logique de mouvement progressif ---
        if not self.popped:
            # Plus le level est haut, plus ça bouge (max 20 pixels de rayon à haut niveau)
            amplitude = min(level * 2, 20) 
            vitesse = 0.002 + (level * 0.0005)
            
            t = pygame.time.get_ticks()
            self.x = self.start_x + math.sin(t * vitesse + self.offset) * amplitude
            self.y = self.start_y + math.cos(t * vitesse + self.offset) * amplitude

    def draw(self, surf):
        r = int(BUBBLE_RADIUS * self.scale)
        if r < 1: return
        
        col = self.base_color
        if self.is_bomb: col = (30, 30, 30)
        elif self.is_gold: col = (255, 220, 50)
        
        if self.popped:
            col = (50, 50, 70)
        else:
            glow = int(math.sin(self.pulse)*6) + 6
            pygame.draw.circle(surf, col, (int(self.x), int(self.y)), r + glow, 2)

        # On convertit en int() pour éviter les erreurs de dessin avec les floats
        pygame.draw.circle(surf, (10, 10, 20), (int(self.x+4), int(self.y+4)), r) 
        pygame.draw.circle(surf, col, (int(self.x), int(self.y)), r)
        
        if not self.popped:
            pygame.draw.circle(surf, (255,255,255), (int(self.x-r//3), int(self.y-r//3)), r//4)

# --- Générateur de Formes ---
def get_shape(name):
    bubbles = []
    # Points de centrage pour 1920x1080
    CX, CY = 960, 540

    # --- FORMES CLASSIQUES (Ajustées pour 1080p) ---
    if name == "CARRE":
        # Grille augmentée à 12x10 pour remplir l'espace
        for r in range(10):
            for c in range(12):
                bubbles.append(Bubble(CX - 420 + c*75, CY - 350 + r*75, COLORS[r%len(COLORS)]))

    elif name == "TRIANGLE":
        for r in range(12):
            for c in range(r + 1):
                bubbles.append(Bubble(CX - (r*35) + c*70, CY - 350 + r*65, COLORS[r%len(COLORS)]))

    elif name == "COEUR":
        for r in range(-3, 11):
            for c in range(-7, 8):
                x, y = c/6.0, -r/6.0
                if (x**2 + y**2 - 1)**3 - x**2 * y**3 <= 0:
                    # Taille augmentée (multiplicateur 85)
                    bubbles.append(Bubble(CX + c*85, CY + r*85 - 50, COLORS[abs(r)%len(COLORS)]))

    elif name == "ETOILE":
        for i in range(250): # Plus de bulles pour une étoile plus dense
            a = random.uniform(0, 2*math.pi)
            r_dist = 450 * (math.sin(5 * a)**2 + 0.4) * random.uniform(0.1, 1.0)
            bx, by = CX + math.cos(a)*r_dist, CY + math.sin(a)*r_dist
            if all(math.hypot(bx-b.x, by-b.y) > 42 for b in bubbles):
                bubbles.append(Bubble(bx, by, random.choice(COLORS)))

    elif name == "DIAMANT":
        for r in range(16):
            w = 8 - abs(8 - r)
            for c in range(-w, w + 1):
                bubbles.append(Bubble(CX + c*70, CY - 400 + r*65, COLORS[r%len(COLORS)]))

    elif name == "HEXAGONE":
        for r in range(-7, 8):
            for c in range(-7, 8):
                if abs(r + c) <= 7:
                    bubbles.append(Bubble(CX + c*65 + r*32, CY + r*55, COLORS[(r+7)%len(COLORS)]))
    
    # --- NOUVELLES FORMES RIGOLOTES (Ajustées pour 1080p) ---
    elif name == "SMILEY":
        # Visage plus grand
        for a in range(0, 360, 10):
            bx = CX + math.cos(math.radians(a)) * 400
            by = CY + math.sin(math.radians(a)) * 400
            bubbles.append(Bubble(bx, by, (255, 255, 0)))
        # Yeux
        bubbles.append(Bubble(CX - 150, CY - 100, (255, 255, 255)))
        bubbles.append(Bubble(CX + 150, CY - 100, (255, 255, 255)))
        # Sourire
        for a in range(30, 151, 15):
            bx = CX + math.cos(math.radians(a)) * 250
            by = CY + math.sin(math.radians(a)) * 250
            bubbles.append(Bubble(bx, by, (255, 80, 80)))

    elif name == "PACMAN":
        for r in range(-9, 10):
            for c in range(-9, 10):
                dist = math.hypot(c, r)
                angle = math.degrees(math.atan2(r, c))
                if dist < 9 and not (-35 < angle < 35):
                    bubbles.append(Bubble(CX + c*65, CY + r*65, (255, 255, 0)))

    elif name == "DONUT":
        for r in range(-10, 11):
            for c in range(-10, 11):
                dist = math.hypot(c, r)
                if 5 < dist < 10:
                    bubbles.append(Bubble(CX + c*60, CY + r*60, random.choice(COLORS)))

    elif name == "INFINI":
        for t in range(0, 150):
            angle = (t / 150) * 2 * math.pi
            bx = CX + (600 * math.cos(angle)) / (1 + math.sin(angle)**2)
            by = CY + (600 * math.sin(angle) * math.cos(angle)) / (1 + math.sin(angle)**2)
            if all(math.hypot(bx-b.x, by-b.y) > 42 for b in bubbles):
                bubbles.append(Bubble(bx, by, COLORS[t%len(COLORS)]))

    elif name == "SPIRALE":
        for i in range(120):
            angle = 0.4 * i
            dist = 6 * i
            bx = CX + math.cos(angle) * dist
            by = CY + math.sin(angle) * dist
            bubbles.append(Bubble(bx, by, COLORS[i%len(COLORS)]))

    elif name == "CROIX":
        for i in range(-8, 9):
            bubbles.append(Bubble(CX + i*70, CY, (255, 50, 50)))
            bubbles.append(Bubble(CX, CY + i*70, (255, 50, 50)))

    elif name == "LUNETTES":
        for a in range(0, 360, 20):
            bubbles.append(Bubble(CX - 250 + math.cos(math.radians(a))*180, CY, (80, 255, 255)))
            bubbles.append(Bubble(CX + 250 + math.cos(math.radians(a))*180, CY, (80, 255, 255)))
        for i in range(1, 6): bubbles.append(Bubble(CX - 60 + i*20, CY, (255, 255, 255)))

    elif name == "PYRAMIDE":
        for r in range(10):
            for c in range(r + 1):
                bubbles.append(Bubble(CX - (r*40) + c*80, CY - 300 + r*75, (180, 140, 40)))

    elif name == "CHAMPIGNON":
        for r in range(-6, 7):
            for c in range(-7, 8):
                if math.hypot(c, r) < 7 and r < 2: # Chapeau
                    bubbles.append(Bubble(CX + c*70, CY - 50 + r*70, (255, 50, 50)))
                if abs(c) < 3 and 2 <= r < 6: # Pied
                    bubbles.append(Bubble(CX + c*70, CY - 50 + r*70, (255, 255, 255)))

    elif name == "SABLIER":
        for r in range(-7, 8):
            w = abs(r)
            for c in range(-w, w + 1):
                bubbles.append(Bubble(CX + c*70, CY + r*70, COLORS[abs(r)%len(COLORS)]))

    elif name == "FLEUR":
        for a in range(0, 360, 45): # Pétales
            for r_dist in range(1, 5):
                bx = CX + math.cos(math.radians(a)) * r_dist * 85
                by = CY + math.sin(math.radians(a)) * r_dist * 85
                bubbles.append(Bubble(bx, by, (255, 100, 200)))
        bubbles.append(Bubble(CX, CY, (255, 255, 0))) # Cœur

    elif name == "ECLAIR":
        pts = [(CX, CY - 400), (CX - 150, CY), (CX + 100, CY), (CX - 50, CY + 450)]
        for i in range(len(pts)-1):
            p1, p2 = pts[i], pts[i+1]
            for j in range(8):
                bx = p1[0] + (p2[0]-p1[0]) * (j/8)
                by = p1[1] + (p2[1]-p1[1]) * (j/8)
                bubbles.append(Bubble(bx, by, (255, 255, 50)))

    elif name == "SERPENT":
        for i in range(25):
            bx = CX - 600 + i * 55
            by = CY + math.sin(i*0.6) * 150
            bubbles.append(Bubble(bx, by, (50, 255, 50)))

    elif name == "VAGUE":
        for r in range(4):
            for c in range(20):
                bubbles.append(Bubble(CX - 700 + c*75, CY + r*75 + math.sin(c*0.5)*80, (80, 80, 255)))

    elif name == "CIBLE":
        for rad in [150, 300, 450]:
            for a in range(0, 360, 15):
                bx = CX + math.cos(math.radians(a)) * rad
                by = CY + math.sin(math.radians(a)) * rad
                bubbles.append(Bubble(bx, by, random.choice(COLORS)))

    return bubbles

class Button:
    def __init__(self, x, y, w, h, text, col):
        self.rect = pygame.Rect(x, y, w, h)
        self.text, self.col = text, col
    def draw(self, surf):
        pygame.draw.rect(surf, self.col, self.rect, border_radius=15)
        pygame.draw.rect(surf, (255,255,255), self.rect, 3, border_radius=15)
        f = pygame.font.SysFont("Impact", 28)
        t = f.render(self.text, True, (255,255,255))
        surf.blit(t, (self.rect.centerx - t.get_width()//2, self.rect.centery - t.get_height()//2))

def show_game_over(screen, score, high_score):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    font_big = pygame.font.SysFont("Impact", 120)
    font_small = pygame.font.SysFont("Impact", 50)
    font_btn = pygame.font.SysFont("Impact", 40)
    
    # --- 1. Animation de fondu ---
    for alpha in range(0, 200, 10):
        overlay.fill((0, 0, 0, alpha))
        screen.blit(overlay, (0, 0))
        pygame.display.flip()
        pygame.time.delay(5)

    # --- 2. Préparation des Textes ---
    text_gameover = font_big.render("GAME OVER", True, (255, 50, 50))
    text_score = font_small.render(f"SCORE FINAL : {score}", True, (255, 255, 255))
    text_best = font_small.render(f"MEILLEUR : {high_score}", True, (255, 215, 0))

    # --- 3. Définition des Boutons Tactiles ---
    # Bouton Rejouer (Vert)
    btn_retry_rect = pygame.Rect(WIDTH//2 - 260, HEIGHT - 200, 240, 80)
    # Bouton Menu (Rouge/Gris)
    btn_menu_rect = pygame.Rect(WIDTH//2 + 20, HEIGHT - 200, 240, 80)

    # --- 4. Boucle d'attente interactive ---
    waiting = True
    action = "restart" # Action par défaut

    while waiting:
        # Dessin du texte statique
        screen.blit(text_gameover, (WIDTH//2 - text_gameover.get_width()//2, HEIGHT//3))
        screen.blit(text_score, (WIDTH//2 - text_score.get_width()//2, HEIGHT//2))
        screen.blit(text_best, (WIDTH//2 - text_best.get_width()//2, HEIGHT//2 + 70))

        # Dessin du bouton REJOUER
        pygame.draw.rect(screen, (50, 180, 50), btn_retry_rect, border_radius=15)
        txt_rejouer = font_btn.render("REJOUER", True, (255, 255, 255))
        screen.blit(txt_rejouer, (btn_retry_rect.centerx - txt_rejouer.get_width()//2, btn_retry_rect.centery - txt_rejouer.get_height()//2))

        # Dessin du bouton QUITTER
        pygame.draw.rect(screen, (200, 50, 50), btn_menu_rect, border_radius=15)
        txt_quit = font_btn.render("QUITTER", True, (255, 255, 255))
        screen.blit(txt_quit, (btn_menu_rect.centerx - txt_quit.get_width()//2, btn_menu_rect.centery - txt_quit.get_height()//2))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"

            # Gestion Souris et Tactile
            pos = None
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = event.pos
            elif event.type == pygame.FINGERDOWN:
                pos = (int(event.x * WIDTH), int(event.y * HEIGHT))

            if pos:
                if btn_retry_rect.collidepoint(pos):
                    return "restart"
                elif btn_menu_rect.collidepoint(pos):
                    return "quit"
    return action

# --- Boucle Principale ---
def main():
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("POP IT ULTRA 2026 - MULTI-TOUCH")
    clock = pygame.time.Clock()
    
    shapes_list = ["CARRE", "TRIANGLE", "COEUR", "ETOILE", "DIAMANT", "HEXAGONE"]
    cur_idx = 0
    bubbles = get_shape(shapes_list[cur_idx])
    effects = []
    
    score, combo, level = 0, 0, 1
    last_pop_time = 0
    paused = False
    shake = 0
    history = load_history()
    high_score = history[0]

    # Paramètres de jeu (Toggles)
    use_timer = True       # Active/Désactive la barre de survie
    use_movement = True    # Active/Désactive le mouvement des bulles

    max_timer = 100.0  # Capacité maximale de la barre
    timer = max_timer  # Temps restant actuel
    timer_speed = 0.005 # Vitesse de descente de base
    
    btn_pause_ui = Button(20, 20, 120, 50, "MENU", (80, 80, 220))
    menu_btns = [
        Button(WIDTH//2 - 150, 300, 300, 60, "CONTINUER", (50, 180, 50)),
        Button(WIDTH//2 - 150, 380, 300, 60, "SURVIE: ON", (100, 100, 100)),
        Button(WIDTH//2 - 150, 460, 300, 60, "MOUVEMENT: ON", (100, 100, 100)),
        Button(WIDTH//2 - 150, 540, 300, 60, "RECOMMENCER", (220, 140, 0)),
        Button(WIDTH//2 - 150, 620, 300, 60, "QUITTER", (200, 50, 50))
    ]

    random_effects_pool = [
        Firework, RingExpand, GhostBubble, SparkleLine, PixelPop, 
        GlitchCircle, SmokeCloud, MoneySign, PolygonSpin, SpeedLine, 
        PizzaSlice, BubbleFragment, LightningBolt, DNAHelix, DigitalRain, 
        ExplodingStar, SolarFlare, SparkleDust, TargetLock, GravityWell, 
        RainbowTrace, PulseGrid, FireBall, WaterDrop, GeometryPop, 
        GhostTrail, MirrorBlast, EnergyShield, CoinSpin
    ]
    try:


        while True:
            now = pygame.time.get_ticks()
            pts_to_process = []
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    save_score(score)
                    return
                
                # SUPPORT SOURIS
                if event.type == pygame.MOUSEBUTTONDOWN:
                    pts_to_process.append(event.pos)
                
                # SUPPORT TACTILE (Jusqu'à 10 points simultanés)
                if event.type == pygame.FINGERDOWN:
                    pts_to_process.append((event.x * WIDTH, event.y * HEIGHT))

            for px, py in pts_to_process:
                if btn_pause_ui.rect.collidepoint(px, py):
                    paused = not paused
                    continue

                if paused:
                    # On vérifie chaque bouton de la liste menu_btns
                    if menu_btns[0].rect.collidepoint(px, py): # CONTINUER
                        paused = False
                    
                    elif menu_btns[1].rect.collidepoint(px, py): # SURVIE
                        use_timer = not use_timer
                        timer = max_timer 
                    
                    elif menu_btns[2].rect.collidepoint(px, py): # MOUVEMENT
                        use_movement = not use_movement
                    
                    elif menu_btns[3].rect.collidepoint(px, py): # RECOMMENCER
                        save_score(score)
                        score, level, combo, paused, timer = 0, 1, 0, False, max_timer
                        bubbles = get_shape(shapes_list[cur_idx])
                        effects = []
                    
                    elif menu_btns[4].rect.collidepoint(px, py): # QUITTER
                        save_score(score)
                        return
                else:
                    for b in bubbles:
                        # Utilise b.x et b.y (qui sont maintenant dynamiques) pour la collision
                        if not b.popped and math.hypot(px-b.x, py-b.y) < BUBBLE_RADIUS + 10:
                            b.popped = True
                            b.target_scale = 0.5
                            
                            # --- AJOUT : BONUS DE TEMPS (BARRE DE SURVIE) ---
                            # Donne 5 pts pour une dorée, 1.5 pts pour une normale
                            bonus = 5.0 if b.is_gold else 1.5
                            timer = min(max_timer, timer + bonus)
                            
                            # --- Gestion Combo et Score ---
                            if now - last_pop_time < 800: combo += 1
                            else: combo = 1
                            last_pop_time = now
                            
                            is_fever = combo > 15
                            val = (15 * combo * (5 if b.is_gold else 1)) * (2 if is_fever else 1)
                            score += val
                            if score > high_score: high_score = score
                            
                            # --- Logique des Sons ---
                            if b.is_bomb:
                                EXPLOSION_SND.play()
                                shake = 25
                                # Effets d'explosion massive
                                effects.append(Firework(b.x, b.y, (255, 100, 0)))
                                effects.append(RingExpand(b.x, b.y, (255, 255, 255)))
                                for o in bubbles:
                                    if not o.popped and math.hypot(b.x-o.x, b.y-o.y) < 180:
                                        o.popped = True
                                        # Les explosions en chaîne redonnent aussi un tout petit peu de temps
                                        timer = min(max_timer, timer + 0.5) 
                                        effects.append(PixelPop(o.x, o.y, o.base_color))
                                        score += 10
                            elif b.is_gold:
                                random.choice(SOUNDS_GOLD).play()
                                effects.append(MoneySign(b.x, b.y, (255, 215, 0)))
                                effects.append(StarParticle(b.x, b.y, (255, 255, 255)))
                            else:
                                random.choice(SOUNDS_POP).play()

                            # --- Déclenchement des Effets Visuels ---
                            txt = f"+{val}" if combo > 5 else random.choice(FUN_TEXTS)
                            effects.append(FloatingText(b.x, b.y, b.base_color, txt))
                            
                            # Effet aléatoire pioché dans la grande liste
                            EffectClass = random.choice(random_effects_pool)
                            effects.append(EffectClass(b.x, b.y, b.base_color))
                            
                            # Effets forcés selon contexte
                            if shapes_list[cur_idx] == "COEUR":
                                effects.append(HeartBurst(b.x, b.y, (255, 50, 80)))
                            
                            if is_fever:
                                effects.append(Shockwave(b.x, b.y, (255, 255, 0)))
                                shake = max(shake, 7)

                            # Toujours quelques débris pour la physique
                            for _ in range(6): 
                                effects.append(Debris(b.x, b.y, b.base_color))
                                
            if not paused:
                # --- GESTION DU TIMER (Seulement si activé) ---
                if use_timer:
                    # Le temps descend. La vitesse augmente avec le niveau.
                    timer -= timer_speed + (level * 0.05)
                    
                    # CONDITION DE DÉFAITE
                    if timer <= 0:
                        EXPLOSION_SND.play()
                        save_score(score)
                        
                        # On récupère le choix de l'utilisateur (Rejouer ou Quitter)
                        choice = show_game_over(screen, score, high_score)
                        
                        if choice == "quit":
                            return  # Quitte la fonction main() et ferme le jeu
                        
                        # Sinon, on réinitialise tout pour recommencer (RESTART)
                        score, level, combo = 0, 1, 0
                        timer = max_timer
                        effects = [] 
                        cur_idx = 0
                        bubbles = get_shape(shapes_list[cur_idx])
                        
                        # On s'assure que high_score est à jour pour la nouvelle partie
                        high_score = max(high_score, score)
                        
                        continue

                # --- MISE À JOUR DES BULLES ---
                # Si use_movement est False, on envoie '0' comme niveau pour figer les positions
                current_move_level = level if use_movement else 0
                for b in bubbles: 
                    b.update(current_move_level) 
                
                # --- MISE À JOUR DES EFFETS ---
                for e in effects: 
                    e.update()
                    
                effects = [e for e in effects if not e.dead]
                
                # --- CHANGEMENT DE NIVEAU ---
                if all(b.popped for b in bubbles):
                    level += 1
                    LEVEL_UP_SND.play()
                    
                    # Bonus de temps seulement si le mode survie est ON
                    if use_timer:
                        timer = min(max_timer, timer + 20)
                    
                    # Explosion de confettis
                    nb_confetti = min(150, 60 + (level * 5))
                    for _ in range(nb_confetti): 
                        effects.append(Confetti(random.randint(50, WIDTH-50), HEIGHT+20))
                    
                    cur_idx = (cur_idx + 1) % len(shapes_list)
                    bubbles = get_shape(shapes_list[cur_idx])

            # --- DESSIN ---
            off_x = random.randint(-shake, shake) if shake > 0 else 0
            off_y = random.randint(-shake, shake) if shake > 0 else 0
            if shake > 0: shake -= 1

            temp = pygame.Surface((WIDTH, HEIGHT))
            temp.fill((10, 10, 25))
            
            # Fond quadrillé
            for x in range(0, WIDTH, 80): pygame.draw.line(temp, (20, 20, 45), (x, 0), (x, HEIGHT))
            for y in range(0, HEIGHT, 80): pygame.draw.line(temp, (20, 20, 45), (0, y), (WIDTH, y))

            for b in bubbles: b.draw(temp)
            for e in effects: e.draw(temp)
            
            # Barre de Progression
            popped_count = sum(1 for b in bubbles if b.popped)
            prog = popped_count / len(bubbles)
            pygame.draw.rect(temp, (40, 40, 60), (WIDTH//2-150, 25, 300, 20), border_radius=10)
            pygame.draw.rect(temp, (100, 255, 100), (WIDTH//2-150, 25, 300 * prog, 20), border_radius=10)

            # --- DESSIN DE LA BARRE DE SURVIE ---
            if use_timer:
                # Fond de la barre (Rouge sombre)
                pygame.draw.rect(temp, (60, 20, 20), (WIDTH//2 - 250, 60, 500, 15), border_radius=5)
                
                # Couleur changeante : Vert si haut, Rouge si critique
                # On peut aussi ajouter le clignotement ici si tu veux
                bar_color = (100, 255, 100) if timer > 30 else (255, 50, 50)
                
                # Remplissage selon le temps restant
                timer_width = (timer / max_timer) * 500
                pygame.draw.rect(temp, bar_color, (WIDTH//2 - 250, 60, timer_width, 15), border_radius=5)
                
                # Petit texte "SURVIE"
                f_timer = pygame.font.SysFont("Impact", 18)
                temp.blit(f_timer.render("SURVIE", True, (255, 255, 255)), (WIDTH//2 - 250, 42))

            # Interface
            btn_pause_ui.draw(temp)
            f_main = pygame.font.SysFont("Impact", 38)
            temp.blit(f_main.render(f"SCORE: {score}", True, (255,255,255)), (WIDTH - 260, 20))
            temp.blit(pygame.font.SysFont("Impact", 20).render(f"BEST: {high_score}", True, (255,215,0)), (WIDTH - 260, 65))
            
            if combo > 1:
                col = (255, 100, 100) if combo > 15 else (255, 255, 255)
                temp.blit(f_main.render(f"COMBO X{combo}", True, col), (160, 20))

            if paused:
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 220))
                temp.blit(overlay, (0, 0))
                
                # Titre Pause
                p_title = pygame.font.SysFont("Impact", 100).render("PAUSE", True, (255, 255, 255))
                temp.blit(p_title, (WIDTH//2 - p_title.get_width()//2, 60))
                
                # --- MISE À JOUR VISUELLE DES BOUTONS TOGGLE ---
                # On met à jour les propriétés AVANT de dessiner
                # Note: On utilise .col car c'est le nom dans ton __init__ de la classe Button
                
                # Bouton Survie (Index 1)
                menu_btns[1].text = f"SURVIE: {'ON' if use_timer else 'OFF'}"
                menu_btns[1].col = (50, 180, 50) if use_timer else (180, 50, 50)
                
                # Bouton Mouvement (Index 2)
                menu_btns[2].text = f"MOUVEMENT: {'ON' if use_movement else 'OFF'}"
                menu_btns[2].col = (50, 150, 200) if use_movement else (100, 100, 100)

                # --- DESSIN DES BOUTONS ---
                for b in menu_btns: 
                    b.draw(temp)

                # --- AFFICHAGE HISTORIQUE ---
                # On le place à gauche pour ne pas gêner les boutons au centre
                h_title = pygame.font.SysFont("Impact", 35).render("TOP 5 SCORES", True, (255, 215, 0))
                temp.blit(h_title, (150, 350)) 
                for i, s in enumerate(load_history()):
                    score_txt = pygame.font.SysFont("Arial", 28).render(f"#{i+1} : {s} pts", True, (220, 220, 220))
                    temp.blit(score_txt, (150, 400 + i * 40))

            # Application du tremblement (Shake) et affichage final
            screen.blit(temp, (off_x, off_y))
            pygame.display.flip()
            clock.tick(FPS)
    finally:
        # --- NETTOYAGE ABSOLU ---
        # S'exécute TOUJOURS, que ce soit un return normal, un Ctrl+C ou un crash !
        pygame.display.quit()
        try:
            pygame.mixer.quit()
        except:
            pass
            
if __name__ == "__main__":
    main()