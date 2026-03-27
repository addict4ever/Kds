# 🍳 KDS - Kitchen Display System (Python & Tkinter)

Un système d'affichage de cuisine (KDS) moderne, tactile et entièrement **hors-ligne**, développé en Python avec Tkinter. Il remplace les imprimantes de bons traditionnelles par des écrans fluides et intuitifs pour optimiser le flux de travail des restaurants et pizzerias.

---

## 📖 Le Principe de Fonctionnement

Le logiciel agit comme un **récepteur d'impression virtuel universel**. Il s'intercepte entre votre logiciel de caisse (POS) et la cuisine.

1. **Capture** : Le système écoute en continu les flux entrants via **Réseau TCP (Port 9100)** ou **Ports Série RS232/USB**.
2. **Interprétation (Parsing)** : Il décode les données brutes (langage standard d'imprimante ESC/POS) pour en extraire l'essentiel : Numéro de facture, Table, Serveur, Items de commande.
3. **Affichage Dynamique** : Les commandes apparaissent instantanément à l'écran sous forme de **"Post-it" numériques** colorés selon leur statut.
4. **Interaction & Suivi** : Les cuisiniers gèrent la production tactilement (En attente 🟦 ➔ En cours 🟨 ➔ Prêt/Traité 🟩).

---

## ✨ Fonctionnalités Clés

### 🖥️ Interface Utilisateur Tactile
* **Post-it Graphiques** : Tickets visuels adaptatifs avec défilement fluide.
* **Claviers Virtuels Intégrés** : Conception ergonomique (AZERTY/QWERTY) à taille variable (5 niveaux de zoom) pour une utilisation sans clavier physique.
* **Raccourcis de modification rapides** : Insertion en un clic de mentions fréquentes (ex: *"SANS OIGNONS"*, *"EXTRA SAUCE"*).

### ⚙️ Intelligence Opérationnelle
* **Totalisateur Automatique (Widget Total)** : Agrège les besoins de production totaux en temps réel (ex: *"Afficher 15 frites au total toutes factures confondues"*).
* **Gestionnaire de Cuisson (Timers)** : Minuteurs visuels intégrés avec alertes audio (MP3 via Pygame ou bips système).
* **Base de données des plats (Menu & Prix)** : Typage des items et association de couleurs intelligentes selon les groupes d'aliments.

### 🔐 Sécurité & Administration Locale
* **Zéro Cloud / 100% Hors-ligne** : Vos données restent chez vous (Bases de données SQLite locales).
* **Authentification par Cadran Rotatif Tactile** : Verrouillage d'accès administratif sécurisé par hachage cryptographique lourd (`PBKDF2-SHA256` à 600 000 itérations).
* **Corbeille intelligente** : Restauration rapide des factures accidentellement archivées.

---

## 🗂️ Architecture & Configuration

L'écosystème utilise des fichiers JSON pour offrir une flexibilité totale sans altérer le code source :

### 📂 Fichiers de Configuration
* `ports.json` : Mappe l'environnement matériel (Comptabilité Windows `COM` et Linux `/dev/ttyUSB`).
* `config_gui.json` : Personnalise l'affichage visuel (Couleurs des statuts, colonnes, polices d'écritures).
* `shortcut_word.json` : Personnalise les boutons d'annotations textuelles rapides.

### 🗃️ Architecture de Données (SQLite)
* `kds_orders.db` : Opérations actives en cuisine en temps réel.
* `consultation.db` : Archive historique permettant d'analyser les statistiques de vente sans ralentir l'écran de production.
* `kds_constants.db` : Fichier maître contenant la liste des prix, menus et mots-clés d'ingrédients.

---

## 🛠️ Outils de Tests Inclus

Le dépôt contient des utilitaires indispensables pour tester la connectivité réseau sans gaspiller de papier thermique :
* `test_print_net.py` : Simule l'envoi de trames d'impressions (Livraisons, additions) vers le KDS.
* `epson_emulator.py` : Émulateur de ponts série pour simuler un raccordement physique de caisse enregistreuse.

---

## 🚀 Installation & Lancement

### Prérequis
* Python 3.10+
* Bibliothèques externes recommandées : `pyserial`, `pygame` (pour la lecture audio des alarmes), `pillow` (pour l'affichage des images).

### Déploiement
```bash
# 1. Cloner le projet
git clone [https://github.com/votre-nom-utilisateur/votre-projet-kds.git](https://github.com/votre-nom-utilisateur/votre-projet-kds.git)
cd votre-projet-kds

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Démarrer l'application principale
python main_app.py
