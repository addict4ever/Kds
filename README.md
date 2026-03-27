<img width="3840" height="1080" alt="image" src="https://github.com/user-attachments/assets/ea6317ee-4122-4047-b41d-d0d7b4a3fd8e" />


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

--- LE PRINCIPE DE FONCTIONNEMENT : UN PONT INTELLIGENT ---

Le logiciel agit comme un RÉCEPTEUR D'IMPRESSION VIRTUEL UNIVERSEL. Il se place 
stratégiquement entre votre logiciel de caisse (POS) et la production, 
éliminant le besoin de papier thermique tout en structurant l'information.

1. CAPTURE MULTI-FLUX (Dual-Listening) :
   Le système surveille simultanément plusieurs vecteurs d'entrée sans conflit :
   - RÉSEAU TCP (Port 9100) : Émule une imprimante réseau standard (Standard JetDirect).
   - PORTS SÉRIE (RS232/USB) : Écoute les ports COM (Windows) ou /dev/tty (Linux) 
     pour intercepter les données des caisses physiques traditionnelles.
   - MODE "SILENT SNIFFER" : Capture les données brutes sans interrompre le 
     flux de communication original.

2. PARSING & INTELLIGENCE ARTIFICIELLE LOCALE :
   Le "moteur de parsing" ne se contente pas de lire du texte, il analyse la 
   structure ESC/POS (langage universel des imprimantes thermiques) :
   - NETTOYAGE OCR : Corrige les erreurs de frappe récurrentes du personnel 
     (ex: "C-SAR" devient "CÉSAR") via un dictionnaire de correspondance.
   - EXTRACTION DE STRUCTURE : Isole intelligemment le numéro de facture, 
     le nom du serveur, le type de service (Livraison, Salle, Emporter) 
     et la destination (Table #).
   - DÉCOUPE D'ITEMS : Sépare le plat principal de ses options/modificateurs 
     (ex: "1 x PIZZA" lié à "EXTRA FROMAGE") pour un affichage hiérarchisé.

3. AFFICHAGE DYNAMIQUE & GESTION DES PRIORITÉS :
   Les commandes sont converties en "Post-it" numériques intelligents :
   - COLONNAGE AUTOMATIQUE : Répartition automatique dans les zones dédiées 
     (ex: Les livraisons à gauche, les tables en salle au centre).
   - TRI CHRONOLOGIQUE : Gestion stricte de l'ordre d'arrivée pour respecter 
     le "Premier Entré, Premier Sorti" (FIFO).
   - ADAPTABILITÉ VISUELLE : Les polices et tailles de cartes s'ajustent 
     selon le volume de commandes pour rester lisibles même en plein "rush".

4. CYCLE DE VIE DE LA COMMANDE (Interaction Tactile) :
   Le cuisinier fait progresser la production d'une simple pression sur l'écran :
   - EN ATTENTE (Bleu) : Commande reçue, prête à être lancée.
   - EN COURS (Jaune) : Indique au reste de l'équipe qu'un cuisinier s'en occupe.
   - PRÊT / TRAITÉ (Vert) : La commande disparaît de l'écran de production, 
     est archivée en base de données, et l'information est envoyée en temps 
     réel vers l'interface des serveurs/livreurs.
   - ARCHIVAGE & RÉCUPÉRATION : Chaque action est loggée. Une facture 
     effacée par erreur peut être restaurée instantanément via la corbeille.
     
--- L'ÉCOSYSTÈME WEB (ACCÈS À DISTANCE) ---

Le programme intègre un serveur Web local (Flask) permettant de consulter les 
données de cuisine sur n'importe quel appareil (Tablette, Mobile, PC) :

* VUE CUISINE GLOBALE (/kds) : 
  Une réplique de l'écran principal pour la supervision.
  
* VUE LIVREURS (/kds_livreur) : 
  Interface simplifiée affichant uniquement les commandes prêtes pour la 
  livraison. Permet aux livreurs de visualiser leur charge de travail sans 
  entrer en cuisine.

* VUE SERVEURS / PA (/kds_pa) : 
  Permet au personnel de salle de voir instantanément quelle table est prête 
  et de recevoir les appels (PA) envoyés par les cuisiniers.

* ANALYSE & HISTORIQUE : 
  Accès à la base de données de consultation pour revoir les performances 
  passées sans interrompre le "rush" en cuisine.

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
