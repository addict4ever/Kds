import sys
import socket
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QPushButton, QLabel, QTabWidget, QSizePolicy)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings

# --- CONFIGURATION ---
PRINTER_IP = "192.168.5.201"
PRINTER_PORT = 9100
KDS_URL_GLOBAL = "http://192.168.5.201:5000/kds"
KDS_URL_LIVREUR = "http://192.168.5.201:5000/kds_livreur"
KDS_URL_PA = "http://192.168.5.201:5000/kds_pa"

class PizzeriaApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KDS Control - Pizzeria Du Boulevard")
        
        # Mode Plein Écran pour Touchscreen
        self.showFullScreen()
        
        self.current_code = ""
        
        # Stylesheet Globale (Optimisée pour le toucher)
        self.setStyleSheet("""
            QMainWindow { background-color: #121212; }
            QTabWidget::pane { border: none; top: -1px; }
            QTabBar::tab { 
                background: #2d2d2d; color: #aaaaaa; 
                padding: 30px; font-size: 22px; font-weight: bold; 
                min-width: 250px; border-right: 2px solid #1a1a1a;
            }
            QTabBar::tab:selected { 
                background: #e61919; color: white; 
                border-bottom: 5px solid white;
            }
            QPushButton:pressed { background-color: #ff5555; }
        """)

        # Widget Central
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Initialisation des modules
        self.setup_keypad_ui()
        self.tabs.addTab(self.create_web_tab(KDS_URL_GLOBAL, "SERVEUSE"), " 📋 SERVEUSE ")
        self.tabs.addTab(self.create_web_tab(KDS_URL_LIVREUR, "LIVREURS"), " 🚚 LIVREURS ")
        self.tabs.addTab(self.create_web_tab(KDS_URL_PA, "P.A."), " 🍕 P.A. ")

    def closeEvent(self, event):
        """Empêche la fermeture de la fenêtre (Alt+F4 via système)."""
        event.ignore()

    def keyPressEvent(self, event):
        # 1. On autorise explicitement Alt+Tab
        if event.key() == Qt.Key.Key_Tab and (event.modifiers() & Qt.KeyboardModifier.AltModifier):
            super().keyPressEvent(event) # Laisse Windows gérer le switch
        
        # 2. On bloque Alt+F4
        elif event.key() == Qt.Key.Key_F4 and (event.modifiers() & Qt.KeyboardModifier.AltModifier):
            event.ignore()
            
        # 3. On bloque la touche Échap
        elif event.key() == Qt.Key.Key_Escape:
            event.ignore()
            
        # 4. Pour tout le reste, comportement normal
        else:
            super().keyPressEvent(event)

    def setup_keypad_ui(self):
        """Interface Clavier Numérique Géant."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Afficheur
        self.display_label = QLabel("---")
        self.display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display_label.setStyleSheet("""
            background-color: #1e1e1e; color: #00ff00; border-radius: 20px;
            font-family: 'Courier'; font-size: 140px; font-weight: bold; 
            margin-bottom: 20px; border: 3px solid #333;
        """)
        layout.addWidget(self.display_label, 1)

        # Grille
        grid = QGridLayout()
        grid.setSpacing(15)
        
        buttons = [
            ('1', 0, 0), ('2', 0, 1), ('3', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('7', 2, 0), ('8', 2, 1), ('9', 2, 2),
            ('CLEAR', 3, 0), ('0', 3, 1), ('SEND', 3, 2)
        ]

        for text, r, c in buttons:
            btn = QPushButton(text)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            
            base_style = "font-size: 50px; font-weight: bold; border-radius: 25px; "
            if text == 'SEND':
                style = base_style + "background-color: #e61919; color: white; border: 4px solid #b31212;"
            elif text == 'CLEAR':
                style = base_style + "background-color: #444; color: white;"
            else:
                style = base_style + "background-color: #f5f5f5; color: #121212; border: 2px solid #ccc;"
            
            btn.setStyleSheet(style)
            btn.pressed.connect(lambda t=text: self.handle_press(t))
            grid.addWidget(btn, r, c)

        layout.addLayout(grid, 4)
        self.tabs.addTab(tab, " ⌨️ CLAVIER D'ENVOI ")

    def create_web_tab(self, url, title):
        """Navigateur Web plein écran avec contrôles tactiles."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        nav_bar = QHBoxLayout()
        nav_bar.setContentsMargins(10, 10, 10, 10)
        
        btn_refresh = QPushButton(f" 🔄 {title} ")
        btn_refresh.setMinimumHeight(20) # Hauteur réduite
        btn_refresh.setMinimumWidth(200) # Largeur fixe pour éviter qu'il prenne tout l'écran
        btn_refresh.setStyleSheet("""
            background-color: #333; color: white; font-weight: bold; 
            font-size: 16px; border-radius: 10px; border: 1px solid #555;
            padding: 5px 15px;
        """)
        
        nav_bar.addWidget(btn_refresh)
        nav_bar.addStretch()
        layout.addLayout(nav_bar)

        browser = QWebEngineView()
        browser.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        
        settings = browser.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        
        browser.setUrl(QUrl(url))
        btn_refresh.pressed.connect(browser.reload)
        
        layout.addWidget(browser)
        return container

    def handle_press(self, key):
        if key == 'CLEAR':
            self.current_code = ""
        elif key == 'SEND':
            if 1 <= len(self.current_code) <= 4:
                self.send_to_printer(self.current_code)
            else:
                self.display_label.setText("ERR")
                return
        else:
            if len(self.current_code) < 4:
                self.current_code += key
        
        self.display_label.setText(self.current_code if self.current_code else "---")

    def send_to_printer(self, code):
        """Envoi compatible avec la détection de ticket de serial_reader.py"""
        try:
            heure = datetime.now().strftime('%H:%M:%S')
            payload = (
                f"\x1b@\x1b!2PIZZERIA DU BOULEVARD\n\n"
                f"Heure: {heure}\n"
                f"TABLE # 888\n"
                f"ENLEVER LE PAPIER JAUNE\n\n"
                f"\x1b!3 DONNER PA {code} SVP\x1b!0\n\n"
                f"-------------------------------\n"
                f"\x1bd\t\x1bi"  # Séquence de fin attendue par serial_reader.py
            )
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                s.connect((PRINTER_IP, PRINTER_PORT))
                s.sendall(payload.encode('latin-1'))
            
            self.current_code = ""
            self.display_label.setText("ENVOYÉ")
            
        except Exception as e:
            self.display_label.setText("ERREUR")
            print(f"Erreur imprimante: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # L'attribut problématique a été supprimé ici
    window = PizzeriaApp()
    window.show()
    sys.exit(app.exec())