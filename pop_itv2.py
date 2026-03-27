import pygame
import random
import math
import array
import json
import os

# --- Configuration ---
WIDTH, HEIGHT = 900, 950
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

# --- Initialisation ---
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2)

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
    return pygame.mixer.Sound(buf)

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

# --- Système de Bubble ---
class Bubble:
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        self.base_color = color
        self.popped = False
        self.scale = 0.0
        self.target_scale = 1.0
        self.is_bomb = random.random() < 0.08
        self.is_gold = random.random() < 0.04
        self.pulse = random.uniform(0, 10)

    def update(self):
        self.scale += (self.target_scale - self.scale) * 0.15
        self.pulse += 0.1

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
            pygame.draw.circle(surf, col, (self.x, self.y), r + glow, 2)

        pygame.draw.circle(surf, (10, 10, 20), (self.x+4, self.y+4), r) 
        pygame.draw.circle(surf, col, (self.x, self.y), r)
        
        if not self.popped:
            pygame.draw.circle(surf, (255,255,255), (self.x-r//3, self.y-r//3), r//4)

# --- Générateur de Formes ---
def get_shape(name):
    bubbles = []
    # --- FORMES CLASSIQUES ---
    if name == "CARRE":
        for r in range(8):
            for c in range(8):
                bubbles.append(Bubble(230+c*65, 220+r*65, COLORS[r%len(COLORS)]))
    elif name == "TRIANGLE":
        for r in range(10):
            for c in range(r + 1):
                bubbles.append(Bubble(450-(r*32)+c*64, 200+r*60, COLORS[r%len(COLORS)]))
    elif name == "COEUR":
        for r in range(-3, 11):
            for c in range(-7, 8):
                x, y = c/6.0, -r/6.0
                if (x**2 + y**2 - 1)**3 - x**2 * y**3 <= 0:
                    bubbles.append(Bubble(450+c*48, 420+r*48, COLORS[abs(r)%len(COLORS)]))
    elif name == "ETOILE":
        for i in range(160):
            a = random.uniform(0, 2*math.pi)
            r_dist = 320 * (math.sin(5 * a)**2 + 0.4) * random.uniform(0.1, 1.0)
            bx, by = 450 + math.cos(a)*r_dist, 450 + math.sin(a)*r_dist
            if all(math.hypot(bx-b.x, by-b.y) > 42 for b in bubbles):
                bubbles.append(Bubble(bx, by, random.choice(COLORS)))
    elif name == "DIAMANT":
        for r in range(12):
            w = 6 - abs(6 - r)
            for c in range(-w, w + 1):
                bubbles.append(Bubble(450+c*65, 120+r*65, COLORS[r%len(COLORS)]))
    elif name == "HEXAGONE":
        for r in range(-5, 6):
            for c in range(-5, 6):
                if abs(r + c) <= 5:
                    bubbles.append(Bubble(450+c*58+r*29, 450+r*50, COLORS[(r+5)%len(COLORS)]))
    
    # --- NOUVELLES FORMES RIGOLOTES ---
    elif name == "SMILEY":
        # Visage
        for a in range(0, 360, 15):
            bx = 450 + math.cos(math.radians(a)) * 250
            by = 450 + math.sin(math.radians(a)) * 250
            bubbles.append(Bubble(bx, by, (255, 255, 0)))
        # Yeux
        bubbles.append(Bubble(370, 380, (255, 255, 255)))
        bubbles.append(Bubble(530, 380, (255, 255, 255)))
        # Sourire
        for a in range(30, 151, 20):
            bx = 450 + math.cos(math.radians(a)) * 150
            by = 450 + math.sin(math.radians(a)) * 150
            bubbles.append(Bubble(bx, by, (255, 80, 80)))

    elif name == "PACMAN":
        for r in range(-6, 7):
            for c in range(-6, 7):
                dist = math.hypot(c, r)
                angle = math.degrees(math.atan2(r, c))
                if dist < 6 and not (-30 < angle < 30):
                    bubbles.append(Bubble(450+c*60, 450+r*60, (255, 255, 0)))

    elif name == "DONUT":
        for r in range(-7, 8):
            for c in range(-7, 8):
                dist = math.hypot(c, r)
                if 3 < dist < 7:
                    bubbles.append(Bubble(450+c*55, 450+r*55, random.choice(COLORS)))

    elif name == "INFINI":
        for t in range(0, 100):
            angle = (t / 100) * 2 * math.pi
            bx = 450 + (350 * math.cos(angle)) / (1 + math.sin(angle)**2)
            by = 450 + (350 * math.sin(angle) * math.cos(angle)) / (1 + math.sin(angle)**2)
            if all(math.hypot(bx-b.x, by-b.y) > 40 for b in bubbles):
                bubbles.append(Bubble(bx, by, COLORS[t%len(COLORS)]))

    elif name == "SPIRALE":
        for i in range(80):
            angle = 0.4 * i
            dist = 5 * i
            bx = 450 + math.cos(angle) * dist
            by = 450 + math.sin(angle) * dist
            bubbles.append(Bubble(bx, by, COLORS[i%len(COLORS)]))

    elif name == "CROIX":
        for i in range(-5, 6):
            bubbles.append(Bubble(450+i*65, 450, (255, 50, 50)))
            bubbles.append(Bubble(450, 450+i*65, (255, 50, 50)))

    elif name == "LUNETTES":
        for a in range(0, 360, 30):
            bubbles.append(Bubble(300 + math.cos(math.radians(a))*100, 450 + math.sin(math.radians(a))*100, (80, 255, 255)))
            bubbles.append(Bubble(600 + math.cos(math.radians(a))*100, 450 + math.sin(math.radians(a))*100, (80, 255, 255)))
        for i in range(1, 5): bubbles.append(Bubble(400+i*20, 450, (255, 255, 255)))

    elif name == "PYRAMIDE":
        for r in range(8):
            for c in range(r + 1):
                bubbles.append(Bubble(450 - (r*35) + c*70, 200 + r*70, (180, 140, 40)))

    elif name == "CHAMPIGNON": # Façon Mario
        for r in range(-4, 5):
            for c in range(-5, 6):
                if math.hypot(c, r) < 5 and r < 2: # Chapeau
                    bubbles.append(Bubble(450+c*60, 400+r*60, (255, 50, 50)))
                if abs(c) < 2 and 1 < r < 5: # Pied
                    bubbles.append(Bubble(450+c*60, 400+r*60, (255, 255, 255)))

    elif name == "SABLIER":
        for r in range(-5, 6):
            w = abs(r)
            for c in range(-w, w + 1):
                bubbles.append(Bubble(450+c*65, 450+r*65, COLORS[abs(r)%len(COLORS)]))

    elif name == "FLEUR":
        for a in range(0, 360, 45): # Pétales
            for r in range(1, 4):
                bx = 450 + math.cos(math.radians(a)) * r * 70
                by = 450 + math.sin(math.radians(a)) * r * 70
                bubbles.append(Bubble(bx, by, (255, 100, 200)))
        bubbles.append(Bubble(450, 450, (255, 255, 0))) # Cœur

    elif name == "ECLAIR":
        pts = [(450, 150), (350, 450), (500, 450), (400, 800)]
        for i in range(len(pts)-1):
            p1, p2 = pts[i], pts[i+1]
            for j in range(6):
                bx = p1[0] + (p2[0]-p1[0]) * (j/6)
                by = p1[1] + (p2[1]-p1[1]) * (j/6)
                bubbles.append(Bubble(bx, by, (255, 255, 50)))

    elif name == "SERPENT":
        for i in range(15):
            bx = 200 + i * 45
            by = 450 + math.sin(i*0.8) * 100
            bubbles.append(Bubble(bx, by, (50, 255, 50)))

    elif name == "VAGUE":
        for r in range(3):
            for c in range(12):
                bubbles.append(Bubble(100+c*65, 400+r*65 + math.sin(c)*50, (80, 80, 255)))

    elif name == "CIBLE":
        for rad in [100, 200, 300]:
            for a in range(0, 360, 20):
                bx = 450 + math.cos(math.radians(a)) * rad
                by = 450 + math.sin(math.radians(a)) * rad
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

    btn_pause_ui = Button(20, 20, 120, 50, "MENU", (80, 80, 220))
    menu_btns = [
        Button(325, 400, 250, 60, "CONTINUER", (50, 180, 50)),
        Button(325, 480, 250, 60, "RECOMMENCER", (220, 140, 0)),
        Button(325, 560, 250, 60, "QUITTER", (200, 50, 50))
    ]

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
                if menu_btns[0].rect.collidepoint(px, py): paused = False
                if menu_btns[1].rect.collidepoint(px, py):
                    save_score(score)
                    score, level, combo, paused = 0, 1, 0, False
                    bubbles = get_shape(shapes_list[cur_idx])
                if menu_btns[2].rect.collidepoint(px, py):
                    save_score(score)
                    return
            else:
                for b in bubbles:
                    if not b.popped and math.hypot(px-b.x, py-b.y) < BUBBLE_RADIUS + 10:
                        b.popped = True
                        b.target_scale = 0.5
                        
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
                                    effects.append(PixelPop(o.x, o.y, o.base_color))
                                    score += 10
                        elif b.is_gold:
                            random.choice(SOUNDS_GOLD).play()
                            effects.append(MoneySign(b.x, b.y, (255, 215, 0)))
                            effects.append(StarParticle(b.x, b.y, (255, 255, 255)))
                        else:
                            random.choice(SOUNDS_POP).play()

                        # --- Déclenchement des 10 Nouveaux Effets Aléatoires ---
                        # On mélange les anciens et les nouveaux pour un max de fun
                        txt = f"+{val}" if combo > 5 else random.choice(FUN_TEXTS)
                        effects.append(FloatingText(b.x, b.y, b.base_color, txt))
                        
                        # Effet de base (Onde de choc)
                        effects.append(Shockwave(b.x, b.y, b.base_color))
                        
                        # Ajout d'un effet visuel aléatoire parmi les nouveaux
                        chance = random.random()
                        if chance < 0.2:
                            effects.append(Firework(b.x, b.y, b.base_color))
                        elif chance < 0.4:
                            effects.append(RingExpand(b.x, b.y, b.base_color))
                        elif chance < 0.5:
                            effects.append(GhostBubble(b.x, b.y, b.base_color))
                        elif chance < 0.6:
                            effects.append(SparkleLine(b.x, b.y, (255, 255, 255)))
                        elif chance < 0.7:
                            effects.append(GlitchCircle(b.x, b.y, b.base_color))
                        elif chance < 0.8:
                            effects.append(PolygonSpin(b.x, b.y, b.base_color))
                        
                        # Si on est dans la forme COEUR, on force l'effet HeartBurst
                        if shapes_list[cur_idx] == "COEUR":
                            effects.append(HeartBurst(b.x, b.y, (255, 50, 50)))

                        # Particules de débris classiques
                        for _ in range(8): 
                            effects.append(Debris(b.x, b.y, b.base_color))
                        
                        # Effet spécial "Fever" si le combo est haut
                        if is_fever:
                            effects.append(SparkleLine(b.x, b.y, (255, 255, 0)))
                            shake = max(shake, 5)

        if not paused:
            for b in bubbles: b.update()
            for e in effects: e.update()
            effects = [e for e in effects if not e.dead]
            
            if all(b.popped for b in bubbles):
                level += 1
                LEVEL_UP_SND.play()
                for _ in range(60): effects.append(Confetti(random.randint(50, WIDTH-50), HEIGHT+20))
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
            p_title = pygame.font.SysFont("Impact", 80).render("PAUSE", True, (255,255,255))
            temp.blit(p_title, (WIDTH//2 - p_title.get_width()//2, 80))
            
            # Affichage Historique
            h_title = pygame.font.SysFont("Impact", 30).render("TOP 5 SCORES", True, (255, 215, 0))
            temp.blit(h_title, (WIDTH//2 - h_title.get_width()//2, 180))
            for i, s in enumerate(load_history()):
                txt = pygame.font.SysFont("Arial", 25).render(f"#{i+1} : {s} pts", True, (200, 200, 200))
                temp.blit(txt, (WIDTH//2 - txt.get_width()//2, 220 + i*30))

            for b in menu_btns: b.draw(temp)

        screen.blit(temp, (off_x, off_y))
        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()