import os
import sys
import shutil
import cv2 # --- NOUVEAU : OpenCV ---
import numpy as np # --- NOUVEAU : NumPy ---

# --- Imports PyQt6 regroupés ---
from PyQt6.QtWidgets import (
    QApplication, QSpinBox, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QFileDialog, QListWidget, 
    QListWidgetItem, QCheckBox, QProgressBar, QSplitter, 
    QFrame, QMessageBox, QAbstractItemView, QTreeView, 
    QMenu, QInputDialog, QScrollArea, QColorDialog
)

from PyQt6.QtGui import (
    QPixmap, QIcon, QAction, QCursor, QFileSystemModel,
    QPainter, QColor, QPen, QImage, QShortcut, QKeySequence,
    QTransform  # <--- AJOUTÉ pour la rotation 90°
)

from PyQt6.QtCore import (
    Qt, QSize, QThread, pyqtSignal, QPoint, 
    QRect       # <--- AJOUTÉ pour la gestion des zones de dessin
)

# --- Traitement d'image ---
from PIL import Image, ImageOps, ImageFilter, ImageDraw
# --- TES FONCTIONS DE TRAITEMENT (ORIGINALES) ---

def get_content_ranges(data, min_size=5):
    ranges = []
    start = None
    for i, has_content in enumerate(data):
        if has_content and start is None: start = i
        elif not has_content and start is not None:
            if i - start >= min_size: ranges.append((start, i))
            start = None
    if start is not None: ranges.append((start, len(data)))
    return ranges

def find_sprite_locations_opencv(pil_img, min_area=500):
    """
    Utilise OpenCV pour trouver les composantes connexes (îlots de pixels).
    C'est la méthode la plus fiable pour séparer des objets.
    """
    # 1. Convertir l'image PIL (RGBA) en format OpenCV (BGRA)
    opencv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGBA2BGRA)
    
    # 2. Extraire le canal Alpha (le masque de transparence)
    alpha_channel = opencv_img[:, :, 3]
    
    # 3. Binariser le masque (s'assurer que c'est bien noir et blanc pur)
    _, thresh = cv2.threshold(alpha_channel, 10, 255, cv2.THRESH_BINARY)
    
    # 4. Trouver les composantes connexes (les îlots de pixels)
    # n_labels: nombre d'objets trouvés
    # labels: une carte de l'image où chaque pixel a l'ID de son objet
    # stats: statistiques incluant la boîte englobante (x, y, w, h, area)
    n_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(thresh, connectivity=8)
    
    all_sprites = []
    
    # 5. Parcourir les objets trouvés (on commence à 1 car 0 est le fond)
    for i in range(1, n_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        
        # Filtrer les petits parasites (poussières de pixels)
        if area < min_area:
            continue
            
        # Récupérer la boîte englobante (bbox)
        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        w = stats[i, cv2.CC_STAT_WIDTH]
        h = stats[i, cv2.CC_STAT_HEIGHT]
        
        # Convertir au format PIL (left, top, right, bottom)
        all_sprites.append((x, y, x + w, y + h))
        
    # Optionnel : Trier les sprites de haut en bas, puis de gauche à droite
    all_sprites.sort(key=lambda b: (b[1], b[0]))
    
    return all_sprites

# --- WORKER THREAD POUR LE TRAITEMENT ---

from PyQt6.QtWidgets import QScrollArea, QColorDialog
from PyQt6.QtGui import QPainter, QColor, QPen, QImage, QPixmap
from PyQt6.QtCore import Qt, QPoint
import os

class ClickableLabel(QLabel):
    def __init__(self, parent_editor):
        super().__init__()
        self.editor = parent_editor
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.editor.save_to_history()
            self.editor.draw_at_pixel(event.pos())
        elif event.button() == Qt.MouseButton.RightButton:
            self.editor.pick_color(event.pos())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.editor.draw_at_pixel(event.pos())

class SpriteEditor(QMainWindow):
    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path
        self.image = QImage(image_path).convertToFormat(QImage.Format.Format_ARGB32)
        self.setWindowTitle(f"Éditeur Pixel Pro - {os.path.basename(image_path)}")
        
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(int(screen.width() * 0.8), int(screen.height() * 0.8))

        # --- PARAMÈTRES ---
        self.zoom = 20
        self.brush_size = 4
        self.brush_color = QColor(255, 255, 255)
        self.is_erasing = True
        self.show_grid = True
        self.history = []
        self.save_to_history()

        self.init_editor_ui()
        self.setup_shortcuts()

    def init_editor_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # --- BARRE D'OUTILS ---
        toolbar = QHBoxLayout()
        
        # Outils de base
        btn_pencil = QPushButton("✏️")
        btn_pencil.setToolTip("Crayon")
        btn_pencil.clicked.connect(self.set_pencil)
        
        btn_eraser = QPushButton("🧽")
        btn_eraser.setToolTip("Gomme")
        btn_eraser.clicked.connect(self.set_eraser)

        # Taille
        toolbar.addWidget(QLabel(" Taille:"))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 20)
        self.size_spin.setValue(self.brush_size)
        self.size_spin.valueChanged.connect(self.set_brush_size)
        toolbar.addWidget(self.size_spin)

        # Couleur
        self.color_preview = QPushButton()
        self.update_color_preview()
        self.color_preview.clicked.connect(self.choose_color)
        toolbar.addWidget(self.color_preview)

        toolbar.addSpacing(10)

        # --- ZOOM ET UNDO (RÉINTÉGRÉS) ---
        btn_undo = QPushButton("↩️")
        btn_undo.setToolTip("Annuler (Ctrl+Z)")
        btn_undo.clicked.connect(self.undo)

        btn_z_in = QPushButton("➕")
        btn_z_in.setToolTip("Zoom Avant")
        btn_z_in.clicked.connect(lambda: self.adjust_zoom(5))

        btn_z_out = QPushButton("➖")
        btn_z_out.setToolTip("Zoom Arrière")
        btn_z_out.clicked.connect(lambda: self.adjust_zoom(-5))

        # --- OUTILS DE TRANSFORMATION ---
        btn_flip_v = QPushButton("↕️")
        btn_flip_v.clicked.connect(self.flip_vertical)

        btn_rotate = QPushButton("🔄")
        btn_rotate.clicked.connect(self.rotate_90)

        btn_invert = QPushButton("🌈")
        btn_invert.clicked.connect(self.invert_colors)

        btn_clear = QPushButton("🗑️")
        btn_clear.clicked.connect(self.clear_all)

        btn_center = QPushButton("🎯")
        btn_center.clicked.connect(lambda: self.set_zoom(20))

        self.grid_check = QCheckBox("🏁")
        self.grid_check.setChecked(True)
        self.grid_check.stateChanged.connect(self.toggle_grid)

        btn_save = QPushButton("💾 SAUVEGARDER")
        btn_save.setStyleSheet("background-color: #2E7D32; color: white; font-weight: bold; padding: 5px 15px;")
        btn_save.clicked.connect(self.save_image)
        
        # Ajout à la barre
        for w in [btn_pencil, btn_eraser, btn_undo, btn_z_in, btn_z_out, btn_flip_v, 
                   btn_rotate, btn_invert, btn_clear, btn_center, self.grid_check]:
            toolbar.addWidget(w)
        
        toolbar.addStretch()
        toolbar.addWidget(btn_save)
        self.main_layout.addLayout(toolbar)

        # Zone de dessin
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setStyleSheet("background-color: #050505;")

        self.canvas = ClickableLabel(self)
        self.canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setWidget(self.canvas)
        self.main_layout.addWidget(self.scroll_area)

        self.refresh_canvas()

    def draw_at_pixel(self, pos):
        # Calcul précis du pixel central sous la souris
        center_x = pos.x() // self.zoom
        center_y = pos.y() // self.zoom
        
        target_color = QColor(0, 0, 0, 0) if self.is_erasing else self.brush_color
        
        # Précision de l'effacement/dessin selon la taille
        half = self.brush_size // 2
        changed = False

        for dx in range(-half, self.brush_size - half):
            for dy in range(-half, self.brush_size - half):
                x, y = center_x + dx, center_y + dy
                if 0 <= x < self.image.width() and 0 <= y < self.image.height():
                    if self.image.pixelColor(x, y) != target_color:
                        self.image.setPixelColor(x, y, target_color)
                        changed = True
        if changed:
            self.refresh_canvas()

    def pick_color(self, pos):
        x, y = pos.x() // self.zoom, pos.y() // self.zoom
        if 0 <= x < self.image.width() and 0 <= y < self.image.height():
            picked = self.image.pixelColor(x, y)
            if picked.alpha() > 0:
                self.brush_color = picked
                self.is_erasing = False
                self.update_color_preview()

    def rotate_90(self):
        self.save_to_history()
        self.image = self.image.transformed(QTransform().rotate(90))
        self.refresh_canvas()

    def flip_vertical(self):
        self.save_to_history()
        self.image = self.image.mirrored(False, True)
        self.refresh_canvas()

    def invert_colors(self):
        self.save_to_history()
        self.image.invertPixels(QImage.InvertMode.InvertRgb)
        self.refresh_canvas()

    def clear_all(self):
        if QMessageBox.question(self, "Confirmer", "Vider tout le sprite ?") == QMessageBox.StandardButton.Yes:
            self.save_to_history()
            self.image.fill(QColor(0, 0, 0, 0))
            self.refresh_canvas()

    def adjust_zoom(self, delta):
        new_zoom = self.zoom + delta
        if 2 <= new_zoom <= 100:
            self.zoom = new_zoom
            self.refresh_canvas()

    def set_zoom(self, val):
        self.zoom = val
        self.refresh_canvas()

    def set_brush_size(self, val): self.brush_size = val
    def set_pencil(self): self.is_erasing = False
    def set_eraser(self): self.is_erasing = True
    def toggle_grid(self): self.show_grid = self.grid_check.isChecked(); self.refresh_canvas()

    def update_color_preview(self):
        self.color_preview.setStyleSheet(f"background-color: {self.brush_color.name()}; border: 2px solid white; min-width: 30px;")

    def refresh_canvas(self):
        w, h = self.image.width() * self.zoom, self.image.height() * self.zoom
        pixmap = QPixmap(w, h)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        # Damier de transparence
        d_size = self.zoom
        for i in range(0, w, d_size*2):
            for j in range(0, h, d_size*2):
                painter.fillRect(i, j, d_size, d_size, QColor(25, 25, 25))
                painter.fillRect(i+d_size, j+d_size, d_size, d_size, QColor(25, 25, 25))
        
        painter.drawImage(pixmap.rect(), self.image)

        if self.show_grid and self.zoom > 4:
            painter.setPen(QPen(QColor(100, 100, 100, 50), 1))
            for x in range(0, w + 1, self.zoom): painter.drawLine(x, 0, x, h)
            for y in range(0, h + 1, self.zoom): painter.drawLine(0, y, w, y)
        painter.end()
        self.canvas.setPixmap(pixmap)

    def save_to_history(self):
        if len(self.history) > 30: self.history.pop(0)
        self.history.append(QImage(self.image))

    def undo(self):
        if len(self.history) > 1:
            self.history.pop()
            self.image = QImage(self.history[-1])
            self.refresh_canvas()

    def choose_color(self):
        color = QColorDialog.getColor(self.brush_color, self, "Couleur")
        if color.isValid():
            self.brush_color = color
            self.is_erasing = False
            self.update_color_preview()

    def save_image(self):
        # Sauvegarde le sprite en PNG
        if self.image.save(self.image_path, "PNG"):
            # Produit un petit son système pour confirmer la réussite
            QApplication.beep()

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self.undo)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.save_image)
        QShortcut(QKeySequence("Ctrl++"), self).activated.connect(lambda: self.adjust_zoom(5))
        QShortcut(QKeySequence("Ctrl+-"), self).activated.connect(lambda: self.adjust_zoom(-5))

class ProcessorThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(int)

    def __init__(self, files, output_dir, tw, th, settings):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.tw, self.th = tw, th
        self.settings = settings

    def run(self):
        count = 0
        for i, file_path in enumerate(self.files):
            if self.process_file(file_path):
                count += 1
            self.progress.emit(int((i + 1) / len(self.files) * 100))
        self.finished.emit(count)

    def fix_white_edges(self, pil_img):
        """Étend les couleurs des pixels pour éliminer les bordures blanches de découpe."""
        # On s'assure d'être en RGBA
        img = pil_img.convert("RGBA")
        r, g, b, a = img.split()
        
        # On crée une version "dilatée" des couleurs (étalement des pixels voisins)
        rgb = Image.merge("RGB", (r, g, b))
        # MaxFilter(3) est idéal pour le pixel art et les sprites
        rgb_dilated = rgb.filter(ImageFilter.MaxFilter(3))
        
        # On recompose avec le masque alpha original pour garder la forme exacte
        return Image.merge("RGBA", (r, g, b, a))

    def process_file(self, file_path):
        try:
            img_name = os.path.splitext(os.path.basename(file_path))[0]
            out_folder = os.path.join(self.output_dir, img_name)
            os.makedirs(out_folder, exist_ok=True)
            
            # 1. Charger l'image
            img = Image.open(file_path).convert("RGBA")
            width, height = img.size

            # 2. Nettoyer le fond (Flood Fill depuis les coins)
            target_color = (0, 0, 0, 0)
            for seed_point in [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]:
                if img.getpixel(seed_point)[3] != 0:
                    ImageDraw.floodfill(img, seed_point, target_color, thresh=30)

            # 3. DÉTECTION INTELLIGENTE (OpenCV)
            boxes = find_sprite_locations_opencv(img, min_area=1000) 
            
            for j, box in enumerate(boxes):
                sprite = img.crop(box)
                
                # Recrop serré pour un centrage parfait
                tight_bbox = sprite.getbbox()
                if tight_bbox:
                    sprite = sprite.crop(tight_bbox)

                # --- CORRECTION DES BORDURES ---
                # On applique l'extension de couleur ici, avant le redimensionnement
                sprite = self.fix_white_edges(sprite)
                # -------------------------------

                # Thumbnail de haute qualité (LANCZOS pour garder la netteté)
                sprite.thumbnail((self.tw-10, self.th-10), Image.Resampling.LANCZOS)
                
                # Canvas transparent de destination (128x128 par défaut)
                canvas = Image.new("RGBA", (self.tw, self.th), (0, 0, 0, 0))
                
                # Calcul des offsets de centrage
                offset_x = (self.tw - sprite.width) // 2
                
                # Ancrage bas ou centré selon tes réglages
                if self.settings.get('anchor_bottom'):
                    offset_y = (self.th - sprite.height)
                else:
                    offset_y = (self.th - sprite.height) // 2
                
                # Collage final en utilisant le sprite comme son propre masque alpha
                canvas.paste(sprite, (offset_x, offset_y), sprite) 
                canvas.save(os.path.join(out_folder, f"{img_name}_{j:03d}.png"), "PNG")
                
            return True
        except Exception as e: 
            print(f"Erreur lors du traitement de {file_path}: {e}")
            return False

# --- INTERFACE PRINCIPALE ---

class SpriteManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sprite Slicer Pro - Gestionnaire d'Assets")
        self.resize(1200, 800)
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e2e; }
            QWidget { color: #cdd6f4; font-family: 'Segoe UI'; }
            
            /* Style de l'explorateur */
            QTreeView { 
                background-color: #313244; 
                border: none; 
                outline: none;
            }

            /* --- GRANDEUR DES FLÈCHES (BRANCHES) --- */
            QTreeView::branch {
                width: 30px; /* Augmente la zone de clic et l'espace de la flèche */
            }

            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {
                image: url(none); /* On peut mettre une image ici, mais on va styliser le symbole */
                border-image: none;
            }

            /* Personnalisation visuelle des flèches via les indicateurs */
            QTreeView::indicator {
                width: 20px;
                height: 20px;
            }
            
            /* Si tu veux des flèches vraiment visibles et personnalisées sans images externes, 
               la méthode la plus simple est d'augmenter l'indentation globale : */
        """)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Splitter principal : Explorateur | Galerie
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # 1. Explorateur de fichiers (Gauche)
        # On récupère le chemin "Home" de l'utilisateur (ex: C:/Users/Nom)
        home_path = os.path.expanduser("~") 
        
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath(home_path) # Définit le périmètre du modèle
        
        self.tree = QTreeView()
        self.tree.setModel(self.file_model)
        
        # --- MODIFICATION ICI : On force l'arborescence à s'ouvrir sur le Home ---
        self.tree.setRootIndex(self.file_model.index(home_path)) 
        
        self.tree.setColumnWidth(0, 250)
        for i in range(1, 4): self.tree.hideColumn(i) # Garde seulement le nom
        self.tree.clicked.connect(self.on_directory_selected)
        
        # 2. Zone Galerie et Contrôles (Droite)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)

        # Barre d'outils supérieure
        top_bar = QHBoxLayout()
        self.path_display = QLineEdit()
        self.path_display.setReadOnly(True)
        self.btn_refresh = QPushButton("🔄 Rafraîchir")
        self.btn_refresh.clicked.connect(lambda: self.load_images_from_path(self.path_display.text()))
        top_bar.addWidget(QLabel("Dossier actuel:"))
        top_bar.addWidget(self.path_display)
        top_bar.addWidget(self.btn_refresh)

        # La grille d'images
        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.ViewMode.IconMode)
        self.list_widget.setIconSize(QSize(120, 120))
        self.list_widget.setSpacing(10)
        self.list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        # Connecter le double-clic à l'ouverture de l'éditeur
        self.list_widget.itemDoubleClicked.connect(self.open_in_editor)

        # Panneau de réglages de découpe
        slice_panel = QFrame()
        slice_panel.setStyleSheet("background-color: #313244; border-radius: 8px;")
        slice_layout = QHBoxLayout(slice_panel)
        
        self.check_clean = QCheckBox("Nettoyer destination")
        self.check_anchor = QCheckBox("Ancrage bas")
        self.btn_slice = QPushButton("✂ LANCER LE DÉCOUPAGE")
        self.btn_slice.setStyleSheet("background-color: #fab387; color: #11111b; font-weight: bold;")
        self.btn_slice.clicked.connect(self.start_processing)
        
        slice_layout.addWidget(self.check_clean)
        slice_layout.addWidget(self.check_anchor)
        slice_layout.addStretch()
        slice_layout.addWidget(self.btn_slice)

        self.prog_bar = QProgressBar()

        right_layout.addLayout(top_bar)
        right_layout.addWidget(self.list_widget)
        right_layout.addWidget(slice_panel)
        right_layout.addWidget(self.prog_bar)

        self.splitter.addWidget(self.tree)
        self.splitter.addWidget(right_container)
        self.splitter.setStretchFactor(1, 3)
        main_layout.addWidget(self.splitter)
    # --- GESTION DE LA NAVIGATION ---

    def on_directory_selected(self, index):
        path = self.file_model.filePath(index)
        if os.path.isdir(path):
            self.load_images_from_path(path)

    def load_images_from_path(self, path):
        if not path or not os.path.exists(path): return
        self.path_display.setText(path)
        self.list_widget.clear()
        
        files = [f for f in os.listdir(path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        for f in files:
            full_path = os.path.join(path, f)
            item = QListWidgetItem(f)
            item.setIcon(QIcon(full_path))
            item.setData(Qt.ItemDataRole.UserRole, full_path)
            self.list_widget.addItem(item)

    # --- MENU CLIC-DROIT (FONCTIONS DE GESTION) ---

    def open_in_editor(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        
        # 1. Vérification de l'existence du fichier
        if not path or not os.path.exists(path):
            return

        # 2. Vérification de l'extension (pour ignorer .json, .py, etc.)
        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.webp')
        if not path.lower().endswith(valid_extensions):
            QMessageBox.warning(self, "Format non supporté", 
                                "Ce fichier n'est pas une image éditable.")
            return

        # 3. Tentative d'ouverture sécurisée
        try:
            # On vérifie si l'image est lisible par QImage avant d'ouvrir la fenêtre
            test_img = QImage(path)
            if test_img.isNull():
                raise ValueError("L'image semble corrompue ou illisible.")

            # Si tout est OK, on lance l'éditeur
            self.editor = SpriteEditor(path)
            self.editor.show()
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur d'ouverture", f"Impossible d'ouvrir l'éditeur : {str(e)}")

    def show_context_menu(self, pos):
        items = self.list_widget.selectedItems()
        if not items: return

        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background-color: #2b2b3b; color: white; border: 1px solid #45475a; padding: 5px; }
            QMenu::item:selected { background-color: #fab387; color: #11111b; border-radius: 3px; }
            QMenu::separator { height: 1px; background: #45475a; margin: 5px; }
        """)

        # --- NAVIGATION & VUE ---
        open_act = menu.addAction("👁 Voir en grand")
        folder_act = menu.addAction("📂 Ouvrir l'emplacement")
        copy_path_act = menu.addAction("🔗 Copier le chemin complet")
        menu.addSeparator()

        # --- ÉDITION EXTERNE ---
        edit_menu = menu.addMenu("🎨 Modifier avec...")
        paint_act = edit_menu.addAction("🖌 Microsoft Paint")
        external_act = edit_menu.addAction("🦊 Choisir un logiciel (GIMP, etc.)")
        menu.addSeparator()

        # --- TRANSFORMATIONS (PIL) ---
        transform_menu = menu.addMenu("🔄 Transformations rapides")
        flip_h_act = transform_menu.addAction("↔ Miroir Horizontal")
        flip_v_act = transform_menu.addAction("↕ Miroir Vertical")
        rot_r_act = transform_menu.addAction("↷ Rotation 90° Droite")
        gray_act = transform_menu.addAction("🌑 Convertir en Noir & Blanc")
        
        # Action de sauvegarde explicite (si on veut valider les changements)
        save_act = menu.addAction("💾 Enregistrer les modifications")
        menu.addSeparator()

        # --- ACTIONS DE FICHIERS ---
        rename_act = menu.addAction("✏ Renommer")
        dup_act = menu.addAction("👯 Dupliquer")
        copy_to_act = menu.addAction("📁 Copier vers...")
        menu.addSeparator()
        delete_act = menu.addAction("🗑 Supprimer")

        action = menu.exec(self.list_widget.mapToGlobal(pos))
        if not action: return

        paths = [item.data(Qt.ItemDataRole.UserRole) for item in items]

        try:
            # 1. OUVERTURE & EXPLORATEUR
            if action == open_act:
                for p in paths: os.startfile(p) if sys.platform == 'win32' else os.system(f'open "{p}"')
            
            elif action == folder_act:
                os.system(f'explorer /select,"{os.path.normpath(paths[0])}"')

            elif action == copy_path_act:
                QApplication.clipboard().setText("\n".join(paths))

            # 2. LOGICIELS EXTERNES
            elif action == paint_act:
                for p in paths: os.system(f'mspaint "{p}"')

            elif action == external_act:
                exe_path, _ = QFileDialog.getOpenFileName(self, "Sélectionner le logiciel (GIMP, Aseprite, Photoshop)", "C:/Program Files", "Executable (*.exe)")
                if exe_path:
                    for p in paths: os.startfile(exe_path, arguments=f'"{p}"')

            # 3. TRANSFORMATIONS (Sauvegarde auto incluse pour rafraîchir l'icône)
            elif action in [flip_h_act, flip_v_act, rot_r_act, gray_act]:
                for p in paths:
                    with Image.open(p) as img:
                        img = img.convert("RGBA")
                        if action == flip_h_act: img = img.transpose(Image.FLIP_LEFT_RIGHT)
                        elif action == flip_v_act: img = img.transpose(Image.FLIP_TOP_BOTTOM)
                        elif action == rot_r_act: img = img.rotate(-90, expand=True)
                        elif action == gray_act: img = img.convert("L").convert("RGBA")
                        img.save(p)
                self.load_images_from_path(self.path_display.text())

            elif action == save_act:
                # Rafraîchit simplement pour confirmer que tout est sur disque
                self.load_images_from_path(self.path_display.text())
                QMessageBox.information(self, "Sauvegarde", "Changements appliqués et images rafraîchies.")

            # 4. GESTION DE FICHIERS
            elif action == rename_act and len(items) == 1:
                self.rename_file(items[0])

            elif action == dup_act:
                for p in paths:
                    base, ext = os.path.splitext(p)
                    shutil.copy(p, f"{base}_copy{ext}")
                self.load_images_from_path(self.path_display.text())

            elif action == copy_to_act:
                self.copy_files(items)

            elif action == delete_act:
                self.delete_files(items)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Une erreur est survenue : {str(e)}")
    # --- MÉTHODES DE SUPPORT ---

    # --- MÉTHODES DE GESTION AMÉLIORÉES ---

    def delete_files(self, items):
        msg = f"Voulez-vous vraiment supprimer {len(items)} fichier(s) définitivement ?"
        confirm = QMessageBox.question(self, "Confirmation", msg, 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if confirm == QMessageBox.StandardButton.Yes:
            for item in items:
                path = item.data(Qt.ItemDataRole.UserRole)
                try:
                    if os.path.exists(path):
                        os.remove(path)
                    self.list_widget.takeItem(self.list_widget.row(item))
                except Exception as e:
                    print(f"Erreur suppression {path}: {e}")

    def rename_file(self, item):
        old_path = item.data(Qt.ItemDataRole.UserRole)
        old_name = os.path.basename(old_path)
        new_name, ok = QInputDialog.getText(self, "Renommer", "Nouveau nom (avec extension):", text=old_name)
        
        if ok and new_name and new_name != old_name:
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            try:
                if os.path.exists(new_path):
                    raise FileExistsError("Un fichier porte déjà ce nom.")
                os.rename(old_path, new_path)
                item.setText(new_name)
                item.setData(Qt.ItemDataRole.UserRole, new_path)
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def copy_files(self, items):
        if not items: return
        dest_dir = QFileDialog.getExistingDirectory(self, "Dossier de destination", os.path.expanduser("~"))
        if dest_dir:
            errors = []
            for item in items:
                src = item.data(Qt.ItemDataRole.UserRole)
                try:
                    shutil.copy(src, dest_dir)
                except Exception as e:
                    errors.append(f"{os.path.basename(src)}: {str(e)}")
            
            if errors:
                QMessageBox.warning(self, "Erreur de copie", "\n".join(errors))
            else:
                QMessageBox.information(self, "Succès", "Tous les fichiers ont été copiés.")

    # --- TRAITEMENT DU DÉCOUPAGE ---

    def start_processing(self):
        # 1. On récupère le dossier actuellement affiché à droite
        src = self.path_display.text()
        if not src or not os.path.exists(src):
            QMessageBox.warning(self, "Erreur", "Veuillez d'abord sélectionner un dossier valide.")
            return

        # 2. On ouvre la boîte de dialogue DIRECTEMENT dans le dossier source
        # Le second argument de getExistingDirectory est le dossier de départ
        dst = QFileDialog.getExistingDirectory(
            self, 
            "Choisir le dossier de destination", 
            src  # <--- C'est ici que la magie opère : on démarre dans le dossier actuel
        )

        if not dst:
            return

        # 3. Sécurité : éviter de supprimer le dossier source par erreur
        if self.check_clean.isChecked() and os.path.abspath(dst) == os.path.abspath(src):
            QMessageBox.critical(self, "Action Interdite", 
                                "Le dossier de destination est le même que la source. "
                                "Désactivez 'Nettoyer destination' pour extraire ici.")
            return

        if self.check_clean.isChecked() and os.path.exists(dst):
            shutil.rmtree(dst)
            os.makedirs(dst)

        # 4. Liste des fichiers à traiter
        files = [os.path.join(src, f) for f in os.listdir(src) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        if not files:
            QMessageBox.information(self, "Info", "Aucune image trouvée dans ce dossier.")
            return

        settings = {'anchor_bottom': self.check_anchor.isChecked()}
        
        # Lancement du thread (inchangé)
        self.thread = ProcessorThread(files, dst, 128, 128, settings)
        self.thread.progress.connect(self.prog_bar.setValue)
        self.thread.finished.connect(lambda c: QMessageBox.information(self, "Succès", f"{c} images traitées avec succès !"))
        self.thread.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SpriteManagerApp()
    window.show()
    sys.exit(app.exec())