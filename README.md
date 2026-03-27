*******************************************************************************
* LICENCE / LICENSE                           *
*******************************************************************************

MIT License

Copyright (c) 2026 François

L'autorisation est accordée, gracieusement, à toute personne acquérant une copie 
de ce logiciel et des fichiers de documentation associés (le « Logiciel »), 
d'utiliser le Logiciel sans restriction, y compris, sans limitation, les droits 
d'utiliser, de copier, de modifier, de fusionner, de publier, de distribuer, 
de sous-licencier et/ou de vendre des copies du Logiciel, et de permettre aux 
personnes auxquelles le Logiciel est fourni de le faire, sous réserve des 
conditions suivantes :

La notice de copyright ci-dessus et la présente autorisation doivent être 
incluses dans toutes les copies ou parties substantielles du Logiciel.

LE LOGICIEL EST FOURNI « TEL QUEL », SANS GARANTIE D'AUCUNE SORTE, EXPRESSE OU 
IMPLICITE, Y COMPRIS MAIS SANS S'Y LIMITER, LES GARANTIES DE QUALITÉ MARCHANDE, 
D'ADÉQUATION À UN USAGE PARTICULIER ET DE NON-CONTREFAÇON. EN AUCUN CAS LES 
AUTEURS OU TITULAIRES DES DROITS D'AUTEUR NE SERONT RESPONSABLES D'UNE 
RÉCLAMATION, DE DOMMAGES OU D'AUTRE RESPONSABILITÉ, QUE CE SOIT DANS LE CADRE 
D'UN CONTRAT, D'UN DÉLIT OU AUTRE, DÉCOULANT DE, OU EN RELATION AVEC LE 
LOGICIEL OU L'UTILISATION OU AUTRES RAPPORTS DANS LE LOGICIEL.

-------------------------------------------------------------------------------

MIT License

Copyright (c) 2026 François

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

*******************************************************************************
* KDS - KITCHEN DISPLAY SYSTEM (Python & Tkinter)             *
*******************************************************************************

Un système d'affichage de cuisine (KDS) moderne, tactile et entièrement 
HORS-LIGNE, développé en Python. Il remplace les imprimantes de bons 
traditionnelles par des écrans fluides et intuitifs pour optimiser le flux 
de travail des restaurants et pizzerias.

--- LE PRINCIPE DE FONCTIONNEMENT ---

Le logiciel agit comme un RÉCEPTEUR D'IMPRESSION VIRTUEL UNIVERSEL. Il s'intercepte 
entre votre logiciel de caisse (POS) et la cuisine :

1. CAPTURE : Le système écoute en continu les flux entrants via Réseau TCP 
   (Port 9100) ou Ports Série RS232/USB.
2. INTERPRÉTATION (Parsing) : Il décode les données brutes (langage standard 
   ESC/POS) pour extraire : Numéro de facture, Table, Serveur et Items.
3. AFFICHAGE DYNAMIQUE : Les commandes apparaissent sous forme de "Post-it" 
   numériques colorés selon leur statut.
4. INTERACTION : Les cuisiniers gèrent la production tactilement 
   (En attente 🟦 -> En cours 🟨 -> Prêt/Traité 🟩).

--- FONCTIONNALITÉS CLÉS ---

* INTERFACE TACTILE OPTIMISÉE :
  - Post-it graphiques adaptatifs avec défilement fluide.
  - Claviers virtuels intégrés à taille variable (5 niveaux de zoom).
  - Raccourcis de modification rapides (ex: "SANS OIGNONS", "EXTRA SAUCE").

* INTELLIGENCE OPÉRATIONNELLE :
  - TOTALISATEUR AUTOMATIQUE : Affiche les besoins de production globaux 
    (ex: "15 frites au total") toutes factures confondues.
  - GESTIONNAIRE DE CUISSON : Minuteurs visuels avec alertes audio MP3 
    (via Pygame) ou bips système.
  - BASE DE DONNÉES PLATS : Gestion des prix, menus et couleurs par groupe.

* SÉCURITÉ ET ADMINISTRATION :
  - ZÉRO CLOUD : 100% Hors-ligne, données stockées en SQLite local.
  - AUTHENTIFICATION SÉCURISÉE : Accès admin protégé par cadran rotatif tactile 
    et hachage cryptographique lourd (PBKDF2-SHA256).
  - CORBEILLE INTELLIGENTE : Pour restaurer les factures archivées par erreur.

--- ARCHITECTURE ET CONFIGURATION ---

L'écosystème utilise des fichiers JSON pour une flexibilité totale :

* CONFIGURATION :
  - ports.json : Mappage matériel (Windows COM / Linux /dev/ttyUSB).
  - config_gui.json : Couleurs, colonnes et polices d'écriture.
  - shortcut_word.json : Personnalisation des boutons d'annotations rapides.
  - printer_ip.json : Configuration des adresses IP pour l'écoute TCP.

* BASES DE DONNÉES (SQLite) :
  - kds_orders.db : Commandes actives en temps réel.
  - consultation.db : Archive historique pour analyse sans ralentir le service.
  - kds_constants.db : Liste maître des prix et menus.

--- OUTILS DE TESTS INCLUS ---

* send_pa_print.py : Utilitaire PyQt6 pour envoyer des messages "PA" rapides.
* serial_reader.py : Cœur du système gérant l'interception Série et TCP.
* log_view.py : Visualiseur de logs intégré pour diagnostic instantané.

--- INSTALLATION ET LANCEMENT ---

1. PRÉREQUIS :
   - Python 3.10+
   - pip install pyserial pygame flask requests PyQt6

2. LANCEMENT :
   Exécutez le fichier principal : 
   > python main_app.py

3. POUR LES LIVREURS/SERVEURS :
   Accédez à l'interface web (si activée) via l'IP locale sur le port 5000.

--- CRÉDITS ---
Développé par François (2026).
Conçu par un cuisinier, pour des cuisiniers.
*******************************************************************************
