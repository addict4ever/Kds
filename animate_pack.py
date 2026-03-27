import tkinter as tk
from PIL import Image, ImageTk
from datetime import datetime  # <--- NOUVEAU : Pour gérer l'heure
import random
import json  # <--- NOUVEAU
import os    # <--- NOUVEAU

class CharacterSelector(tk.Toplevel):
    def __init__(self, parent, characters, callback, hide_callback, x, y):
        super().__init__(parent)
        self.callback = callback
        self.hide_callback = hide_callback

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.geometry(f"+{x}+{y}")
        self.configure(bg="#2c3e50", padx=5, pady=5)

        # Bloque les clics ailleurs tant que le menu est ouvert
        self.grab_set() 

        # BOUTON ANNULER
        btn_close = tk.Button(self, text="ANNULER", command=self.destroy,
                             bg="#c0392b", fg="white", relief="flat", 
                             font=("Arial", 9))
        btn_close.pack(fill="x", pady=(10,0))

        # --- TITRE PERSONNAGES ---
        tk.Label(self, text="PERSONNAGES", bg="#2c3e50", fg="#bdc3c7", 
                 font=("Arial", 8, "bold")).pack(fill="x", pady=(0, 2))

        # Boutons des personnages
        for name in characters:
            btn = tk.Button(self, text=name.capitalize(), 
                            command=lambda n=name: self.select(n),
                            bg="#34495e", fg="white", activebackground="#3498db",
                            relief="flat", padx=10, pady=5, font=("Arial", 10, "bold"))
            btn.pack(fill="x", pady=1)

        # --- SECTION CACHER ---
        tk.Label(self, text="💤 CACHER POUR...", bg="#2c3e50", fg="#f39c12", 
                 font=("Arial", 8, "bold")).pack(fill="x", pady=(10, 2))

        # Configuration des durées : (Texte du bouton, Heures)
        durations = [
            ("2H", 2),
            ("4H", 4),
            ("8H", 8),
            ("12H", 12),
            ("24H", 24)
        ]

        # Création d'un cadre pour les boutons d'heures (pour les mettre côte à côte ou en grille)
        grid_frame = tk.Frame(self, bg="#2c3e50")
        grid_frame.pack(fill="x")

        # On les affiche sur deux colonnes pour que ce soit joli
        for i, (label, hours) in enumerate(durations):
            btn_h = tk.Button(grid_frame, text=label, 
                             command=lambda h=hours: self.hide_action(h),
                             bg="#e67e22", fg="white", activebackground="#d35400",
                             relief="flat", font=("Arial", 9, "bold"), width=4)
            row = i // 3
            col = i % 3
            btn_h.grid(row=row, column=col, padx=1, pady=1, sticky="nsew")
        

    def select(self, name):
        self.callback(name)
        self.destroy()

    def hide_action(self, hours):
        # On envoie le nombre d'heures à la fonction de rappel
        self.hide_callback(hours)
        self.destroy()

class DesktopPet:
    def __init__(self, root, char_name="chat_blanc_01"):
        self.root = root
        
        # --- CONFIG WINDOW ---
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "white")
        self.root.config(bg="white")

        self.current_character = char_name #
        # --- ÉTATS ET EXPRESSIONS ---
        self.is_hidden = False
        self.hidden_until = None
        self.state = "IDLE"
        self.active_menu = None
        self.brain_rules = []  # <--- AJOUTE CETTE LIGNE ICI (Initialisation par défaut)
        self.anims = {}
        self.facing_right = True
        self.offset_x = 0
        self.offset_y = 0
        self.inertia_x = 0
        self.inertia_y = 0
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.current_frame = 0
        self.is_waiting = False
        self.press_start_time = datetime.now().timestamp() # <--- Timer pour le menu
        self.grab_start_time = 0
        self.menu_opened = False
        self.last_message_time = 0 # <--- Pour suivre le délai de 5 min
        self.click_times = []        # Liste pour stocker l'heure des derniers clics
        self.is_punished = False     # Est-ce que le pet boude ?
        self.punishment_end = 0      # Heure de fin de la punition
        self.expressions = [
            "Lâche pas la patate ! 🥔", "C'est l'heure du coup de feu ! 🔥", "On n'est pas ici pour enfiler des perles !",
            "T'as mis trop de sel dans ton attitude. 🧂", "C'est du velours ! ✨", "Envoyez la sauce ! 🥫",
            "C'est pas de la tarte, hein ?", "Mets de l'huile ! 🍳", "Y'a un cheveu dans la soupe...",
            "Chef, oui Chef ! 👨‍🍳", "Reste calme et fais la plonge. 🧼", "Ça burn en cuisine ! 🥖",
            "As je te dis, ça va être écoeurant ! 👨‍🍳", "C'est CRU ! Un bon vétérinaire pourrait encore le sauver ! 🥩",
            "Où est la SAUCE LAMB ?! 🐑", "Espèce de sandwich à l'idiot ! 🍞🥪", "C'est un désastre total.",
            "Dégage de ma cuisine ! 🚪", "Tu appelles ça un risotto ? On dirait du plâtre !",
            "Montez en température, on traîne là !", "Service ! Envoyez la 12 !", "C'est du caoutchouc, pas du calamar !",
            "Réveille-toi ! On dirait que tu dors debout !", "C'est tellement gras que j'ai l'impression de boire du pétrole.",
            "Éteins tes fourneaux et va-t'en.", "Goûte-moi ça... c'est dégueulasse !", "Fais chauffer la poêle, pas tes oreilles !",
            "On envoie du lourd aujourd'hui !", "C'est le rush, perdez pas le fil !", "Un peu de finesse dans ce monde de brutes.",
            "C'est brillant ! 🌟", "Ta mise en place est une honte.", "Même mon chat cuisinerait mieux que ça.",
            "C'est sec ! On dirait que je mange le Sahara !", "Trop de beurre ? Y'a jamais trop de beurre !",
            "C'est la crème de la crème. 🥛", "On n'est pas au buffet de la gare ici !", "Précision, rapidité, efficacité.",
            "T'as pas de couilles en cuisine ou quoi ?", "Le client attend, bouge tes fesses !", "C'est de l'art dans l'assiette. 🎨",
            "T'as confondu le sucre et le sel ?", "Arrête de pleurer sur tes oignons.", "On lâche rien, les gars !",
            "C'est une explosion de saveurs ! 💥", "Ton plan de travail est un dépotoir.", "Respecte le produit, bordel !",
            "C'est une insulte à la gastronomie.", "On est dans le jus ! 🌊", "Un chef qui ne goûte pas est un chef mort.",
            "Remue-moi ça, ça attache !", "C'est cuit à la perfection. 👌", "File-moi ton tablier, t'es viré.",
            "On dirait de la nourriture pour chien.", "C'est de la bouillie !", "T'as appris à cuisiner dans un livre de coloriage ?",
            "Concentration ! Le diable est dans les détails.", "C'est une tuerie ! 🔫🍴", "Fais-moi rêver avec ton plat.",
            "C'est fade, on dirait de l'eau chaude.", "Envoie la purée ! 🥔", "C'est chaud devant ! ⚠️",
            "On n'attend pas le dégel !", "C'est de la haute voltige.", "Tu sors ça à un client, il fait une syncope.",
            "C'est de la dynamite ! 🧨", "On a du pain sur la planche. 🥖", "Ne mélange pas les torchons et les serviettes.",
            "C'est la cerise sur le gâteau. 🍒", "T'as le feu au cul ou quoi ?", "Faut que ça chante dans la poêle ! 🎵",
            "C'est digne d'une étoile ! ⭐", "Ramasse tes dents, on accélère !", "C'est un carnage.",
            "On fait pas d'omelette sans casser des œufs. 🥚", "T'es une vraie passoire !", "C'est du béton ton soufflé !",
            "On est au taquet ! ⚡", "Vise le sommet, pas la poubelle.", "C'est carré, j'aime ça.",
            "Un petit zeste de folie. 🍋", "C'est la foire aux canards ici !", "T'es pas en vacances !",
            "C'est du caviar. 🐟", "On va se régaler ! 😋", "C'est un régal pour les yeux.",
            "Fais gaffe à tes doigts !", "C'est pas Versailles ici, éteins le four !", "Ça manque de pep's ! ✨",
            "C'est de la bombe ! 💣", "On est les rois de la popote.", "T'as mis le paquet !",
            "C'est un sans-faute. 💯", "On cuisine avec le cœur ou on cuisine pas.", "C'est l'extase culinaire.",
            "Mets-y du sien, sac à papier !", "C'est la débandade !", "Reste focus, le service finit bientôt.",
            "C'est le top du top.", "On va leur montrer de quoi on est capables !",
            "C'est de la bouillie pour chats ! 🐱", "On n'est pas à la kermesse du village !",
            "T'as trouvé ta recette dans un biscuit chinois ? 🥠", "C'est plus salé que la Mer Morte !",
            "Appelle les pompiers, ton plat est en train de mourir ! 🚒", "C'est une insulte aux papilles !",
            "Tu cuisines avec tes pieds ou quoi ? 👣", "On dirait une scène de crime dans l'assiette ! 🚨",
            "C'est tellement acide que ça décaperait un tank ! 🛡️", "Va jouer aux billes, la cuisine c'est pour les grands !",
            "Ta sauce est plus claire que tes idées ! 🧠", "C'est pas un restaurant ici, c'est un asile !",
            "Même un micro-ondes ferait mieux que toi ! 📟", "Ton poisson est si peu cuit qu'il cherche encore Nemo ! 🐠",
            "C'est de la semelle de botte ! 👢", "T'as confondu la cuisine et le bricolage ?",
            "On dirait du vomi de licorne... 🦄", "C'est plus mou qu'une éponge mouillée !",
            "Range ta pelle et ton seau, on n'est pas à la plage ! 🏖️", "C'est une catastrophe industrielle !",
            "T'as oublié d'allumer le cerveau avant les fourneaux ? 💡", "C'est sec comme un coup de trique ! 🥖",
            "On dirait de la nourriture pour astronaute... sans l'espace ! 👨‍🚀", "C'est une blague ? Où sont les caméras cachées ? 🎥",
            "Ta mise en place ressemble à un champ de bataille ! 💣", "C'est du caoutchouc de pneu ! 🏎️",
            "T'as mis tout le stock de poivre dans une seule assiette ?", "C'est fade comme un lundi matin... ☁️",
            "Même l'inspecteur d'hygiène n'en voudrait pas ! 📋", "On est en plein cauchemar en cuisine !",
            "Ton plat manque de dignité ! 😤", "C'est une insulte au produit ! 🍅",
            "T'as cru que c'était une soupe populaire ?!", "C'est plus lourd qu'un parpaing ! 🧱",
            "On dirait que ça a déjà été mangé une fois... 🤢", "C'est pas de la cuisine, c'est de la magie noire ! 🧙‍♂️",
            "T'as noyé le poisson... littéralement ! 🌊", "C'est un attentat culinaire !",
            "Ton gâteau ressemble à un chapeau écrasé ! 🎩", "C'est plus amer que ton ex ! 💔",
            "T'as fait chauffer l'eau au moins ? 💧", "C'est d'une tristesse absolue... ✨",
            "On dirait une expérience de chimie qui a foiré ! 🧪", "C'est pas un dressage, c'est un dépotoir !",
            "Tu nous fais quoi là ? Un remake de Titanic ? 🚢", "C'est trop cuit, c'est du charbon de bois ! 🪵",
            "T'as plus de chance de gagner au loto que de réussir ce plat !", "C'est d'un ennui mortel... 💀",
            "On dirait de la pâte à modeler ! 🎨", "T'as mis de la colle au lieu de la farine ?",
            "C'est tellement gras que l'assiette glisse toute seule ! ⛸️", "C'est un crime contre l'humanité !",
            "Ta viande est plus dure que ma grand-mère ! 👵", "C'est une parodie de cuisine française !",
            "T'as oublié le sel... et le talent ! 🧂", "On dirait un repas de cantine de prison ! ⛓️",
            "C'est plus liquide que de l'eau !", "T'as cru que c'était un atelier poterie ? 🏺",
            "C'est un désastre monumental ! 🏛️", "Ton assiette fait pitié à voir !",
            "C'est tellement moche que ça fait pleurer les oignons ! 🧅", "On n'est pas au cirque, range tes jongleries !",
            "T'as balancé les ingrédients par la fenêtre ? 🪟", "C'est une purée ou du ciment ? 🏗️",
            "On dirait un plat de la dinette de ma nièce ! 🧸", "C'est d'une médiocrité effrayante ! 👻",
            "T'as confondu la cannelle et le cumin ?!", "C'est plus piquant qu'un cactus ! 🌵",
            "On dirait de la nourriture pour poisson rouge ! 🐟", "C'est une insulte au métier de cuisinier !",
            "T'as fait tomber ton cendrier dans la marmite ? 🚬", "C'est plus froid que le cœur de mon proprio ! 🧊",
            "On dirait une bouillie de l'espace ! 🪐", "C'est un naufrage total !",
            "T'as cru que c'était Halloween avec ce dressage ? 🎃", "C'est plus mou que du chewing-gum !",
            "On dirait un échantillon de laboratoire ! 🔬", "C'est une blague de mauvais goût !",
            "T'as mis le feu à la cuisine ou quoi ? 🔥", "C'est plus visqueux qu'une limace ! 🐌",
            "On dirait que ça a été coupé avec une tondeuse à gazon ! 🚜", "C'est une parodie de grand chef !",
            "T'as confondu le frigo et le four ? ❄️", "C'est plus aigre qu'un citron pourri ! 🍋",
            "On dirait de la pâtée pour chien de luxe ! 🐩", "C'est un massacre à la tronçonneuse ! 🪚",
            "T'as cru que c'était un buffet à volonté ici ?", "C'est plus noir que mon café ! ☕",
            "On dirait une éponge à vaisselle ! 🧽", "C'est une honte pour la profession !",
            "T'as mis de la laque sur ton plat ? 🧴", "C'est plus élastique qu'un élastique !",
            "On dirait un tas de sable ! 🏖️", "C'est une insulte à l'Italie ! 🇮🇹",
            "T'as cru que c'était une soupe de sorcière ? 🧙‍♀️", "C'est plus plat qu'une crêpe !",
            "On dirait un reste de la semaine dernière ! 📅", "C'est une catastrophe nucléaire ! ☢️",
            "T'as mis de la peinture dedans ? 🖌️", "C'est la fin du monde dans ton assiette ! ☄️",
            "Regarde-moi dans les yeux... c'est quoi ça ? 👀", "Y'a pas de rigueur ! Zéro !",
            "C'est un manque de respect pour le métier. 😤", "On n'est pas là pour faire de la figuration !",
            "Goûte ! Est-ce que tu servirais ça à ta mère ? 👵", "T'as pas de niac ! Elle est où l'envie ?",
            "C'est plat, c'est vide, c'est comme toi aujourd'hui ! 😶", "Un peu de tenue, t'es pas dans ton salon !",
            "Le dressage, c'est de la chirurgie ! 🏥", "C'est brouillon, je veux de la netteté !",
            "Ramasse ton plan de travail, c'est une porcherie ! 🐷", "T'es en train de couler le service là !",
            "C'est mou ! Donne du relief à ton plat ! ⛰️", "On ne triche pas avec le produit !",
            "Fais-moi de la cuisine, de la vraie ! 🥘", "Ta technique est à revoir de A à Z.",
            "C'est de l'amateurisme ! ⛔", "Concentration ! Ne te laisse pas polluer par le stress !",
            "On dirait de la bouillie pour bébé ! 🍼", "C'est l'anarchie dans ton assiette ! 🏴‍☠️",
            "Ton assaisonnement est aux abonnés absents. 📵", "Tire sur tes manches et va au charbon ! ⚒️",
            "C'est quoi ce taillage ? C'est fait à la hache ? 🪓", "Respecte la saisonnalité, bordel ! 🍂",
            "C'est une hérésie culinaire ! ⛪", "T'es trop lent, on va se faire enterrer !",
            "Ouvre tes oreilles, le client attend ! 👂", "C'est sec comme une vieille écorce ! 🪵",
            "Ta sauce a tranché, comme ta carrière si tu continues ! 🔪", "C'est de la poudre aux yeux ton truc. ✨",
            "Fais-moi rêver, ne me fais pas pleurer ! 😢", "On n'est pas à la cantine scolaire !",
            "C'est bâclé ! Je veux de l'excellence ! 🌟", "T'as le cerveau en vacances ?",
            "Ta mise en place est un cauchemar... 👻", "C'est de la cuisine de supermarché ! 🛒",
            "On dirait que ça a été jeté au lance-pierre ! 🏹", "Sois précis ! Un gramme c'est un gramme !",
            "C'est une faute professionnelle grave ! 🚫", "Tu nous sors un sketch là ? 🤡",
            "Redresse la barre avant qu'on sombre ! ⚓", "Y'a pas d'âme dans ton plat. C'est vide. 🧊",
            "C'est trop gras, j'ai l'artère qui se bouche ! 💔", "On dirait du plâtre ton écrasé de pomme de terre ! 🏗️",
            "Réveille-toi, t'es pas sur TikTok là ! 📱", "C'est une insulte au terroir ! 🇫🇷",
            "Ta cuisson est erratique ! C'est aléatoire !", "Fais preuve de bon sens ! 🔥",
            "C'est d'une fadeur sans nom... 😶", "On n'est pas chez les scouts, on envoie !",
            "C'est quoi ce dressage de kermesse ? 🎡", "T'as pas de caractère, ça se sent dans l'assiette !",
            "C'est médiocre. Je n'aime pas la médiocrité. 👎", "Sois fier de ce que tu sors ou ne sors rien !",
            "C'est de la petite cuisine ça... je veux de la GRANDE ! 🏰", "T'as pas de technique, t'as juste de la chance.",
            "C'est malhonnête de servir ça ! 🤨", "On dirait une déco de Noël périmée. 🎄",
            "C'est trop complexe, va à l'essentiel !", "La simplicité est la sophistication suprême. ✨",
            "T'as noyé la saveur sous le beurre... 🧈", "C'est une erreur de débutant, t'as quel âge ?",
            "On n'attend pas demain, le service c'est MAINTENANT !", "C'est d'une pauvreté gustative affligeante. 📉",
            "T'as confondu raffinement et superflu ! 🎀", "Range ton orgueil et écoute les ordres ! 📢",
            "C'est décevant. Très décevant. 😞", "On dirait de la cuisine industrielle. 🏭",
            "Ta garniture fait de la peine à voir... 🥀", "C'est de l'esbroufe ton dressage !",
            "Sois rigoureux ! La cuisine c'est du travail ! 👷", "C'est un manque d'élégance flagrant. 🎩",
            "T'as brûlé l'ingrédient, t'as tué le goût ! 💀", "C'est de la bouillie de luxe ! 💎",
            "On dirait que ça a été fait dans le noir ! 🌑", "T'as pas le niveau pour cette brigade.",
            "C'est d'une lourdeur... j'ai besoin d'air ! 💨", "T'as pas respecté le temps de repos !",
            "C'est déséquilibré, ça penche d'un côté ! ⚖️", "On dirait de la déco de mariage bas de gamme. 💒",
            "T'as fait quoi pendant 2 heures ? De la peinture ? 🎨", "C'est fade comme un discours politique ! 🎤",
            "On dirait de la nourriture en plastique ! 🧸", "C'est une parodie de gastronomie.",
            "T'as mis trop de fioritures, on s'y perd ! 🕸️", "C'est un gâchis de marchandises ! 🗑️",
            "Ta vinaigrette est plus agressive qu'un pitbull ! 🐕", "C'est d'une tristesse... mets-y de la vie !",
            "On dirait un plat de la semaine passée réchauffé ! 🗓️", "C'est quoi ces proportions ? C'est pour un géant ? 👹",
            "T'as pas d'imagination, tu recopies mal !", "C'est d'une banalité déconcertante. 🥱",
            "On dirait que tu as peur de la nourriture ! 😨", "C'est de la cuisine de camping ! ⛺",
            "T'as confondu délicatesse et faiblesse. 🥀", "C'est une catastrophe visuelle !",
            "On dirait une expérience de biologie ! 🧪", "T'as raté le coche, le train est passé. 🚂",
            "C'est pas un plat, c'est une punition ! 👊", "On termine en beauté ou on ne termine pas !",
            "Attention, c'est chaud ! ⚠️🔥", "Attention, je suis en arrière ! 🏃‍♂️💨", "Attention, j'arrive avec un couteau ! 🔪😱", 
            "Sache-le ! ☝️✨", "Ta yeule ! 🤫🚫", "Charogne immonde ! 🧟‍♂️🤢", "Heille, merci ! 🙌✨", 
            "On est fermés ! 🚪🔒", "Tony, la sauce ! 🥫🇮🇹", "Ça burn, tbk ! 🥵🔥", "Ah, j'te dis... 🙄💨", 
            "Ben si ça reste de même... 🤷‍♂️📉", "La drogue c'est mal, vous voyezzzz... ☝️🥴", "Lâche pas la patate ! 🥔💪", 
            "24 dans un deux et demi ! 🏢🏘️", "La douleur, c'est dans la tête ! 🧠💥", "Lâche pas, ça achève ! 🏁💪", 
            "On lâche pas la gang ! 👨‍🍳🔥", "Ayoye, tu me fais mal avec ta graine de cheval ! 🐎💥", "Leave your fucking phone! 📱🚫", 
            "Criss de stagiaire ! 🧑‍🍳🤦‍♂️", "La shop à biscuits ! 🍪🏬", "La plus belle journée de ma vie ! 🌟🤩", 
            "Ça a jamais ben été de même... 📉🤔", "Elle achève-tu c't'hiver ? ❄️🧤", "Y'a pas de 's' à 'point-s' ! ✍️🚫", 
            "Lâche pas, ça va passer ! 🌊🩹", "Eille, c'est quoi la soupe ? 🥣🤔", "Baise-moi dans le cul ! 🍑💥", 
            "Use your fucking brain! 🧠🔥", "Sweet fuck all! 🚫🤷‍♂️", "Souper après souper ! 🍽️🔁", 
            "Y'en reste moins long qu'il en restait ! ⏳🏁", "Move your feet! 👟💨", "Ah seigneur... Non, moi c'est Éric Lessard. 🧔‍♂️🙏", 
            "Des fois je me tou... 😳🤚","Ma femme est partie, pas ma chance ! 🍀", "J'adore le noir, comme mon avenir. 🌑", "Dieu est mort, je l'ai remplacé. 👑",
            "Le cimetière est plein de gens irremplaçables. ⚰️", "Je ne suis pas fou, j'ai raison. 🧠", "L'espoir fait vivre, l'acide fait mourir. 🧪",
            "Ton avis ? Je m'en sers de litière. 🐈", "C'est cuit, comme ton cerveau. 🔥", "Un suicide ? Non, une retraite anticipée. 📉",
            "La mort te va si bien, chéri. 💀", "J'ai mangé ton clown ce matin. 🤡", "Vis chaque jour comme le dernier. ⏳",
            "L'enfer est pavé de tes bonnes intentions. 👹", "Tu es moche, même de dos. 🎭", "La patience a des limites, moi aussi. 🧨",
            "J'aime ton parfum, c'est du chloroforme ? 😴", "Éteins la lumière, tu me fais peur. 🔦", "Ton sang est rouge, c'est original. 🩸",
            "Je soigne ma dépression à la hache. 🪓", "Tais-toi, tu pollues l'air ambiant. 😷", "L'alcool tue, mais l'eau aussi. 🍷",
            "Je ne dors pas, je simule. 💤", "Ton chat me regarde bizarrement. 🐱", "C'est l'heure de la piqûre, souris ! 💉",
            "J'ai enterré mes problèmes au jardin. 🌻", "Le silence est d'or, le scotch aussi. 🙊", "Tu ressembles à un accident industriel. 🏗️",
            "Je t'aime, mais de très loin. 🔭", "Un cadavre de plus dans le placard. 🚪", "La vie est une maladie mortelle. 🤒",
            "J'ai perdu mon ombre ce matin. 👣", "Le bonheur est une erreur de calcul. 🧮", "Fais un vœu, puis crève. 🌟",
            "Ton cerveau est en option, visiblement. 🕹️", "C'est gratuit ? Alors j'en veux deux. 🎁", "J'entends des voix et elles t'insultent. 🗣️",
            "La solitude, c'est mon seul ami. 👤", "T'as une tête à faire peur aux oignons. 🧅", "Mange tes morts, c'est riche en fer. 🦴",
            "La faucheuse arrive, cache ton portefeuille. 🧺", "Je suis allergique à ta bêtise. 🤧", "C'est moche, mais c'est toi. 🖼️",
            "Dors bien, le monstre surveille. 👹", "J'ai vendu mon âme sur eBay. 💻", "Rien ne va, merci de demander. 👋",
            "Ta vie est un mauvais film. 🎬", "J'aime le bruit des os cassés. 🦴", "C'est fini, pose ce couteau. 🔪",
            "L'intelligence te poursuit, cours plus vite ! 🏃", "J'ai oublié de t'aimer aujourd'hui. 🥀", "Un dernier verre avant le gouffre ? 🥃",
            "Ton ombre a peur de toi. 👥", "C'est pas sale, c'est du vécu. 🗑️", "La fin est proche, apporte l'apéro. 🥂",
            "Je ne suis pas méchant, juste honnête. 😇", "Ton sourire fait peur aux enfants. 👶", "L'amour rend aveugle, le mariage assomme. 🔨",
            "Je collectionne les regrets des autres. 🎒", "T'es pas brillant, t'es juste gras. ✨", "La réalité est une hallucination collective. 🌀",
            "J'ai un plan, apporte la pelle. 🚜", "C'est dégueulasse, j'adore ça ! 🤮", "Ta mère ne t'a pas fini ? 🛠️",
            "Je ris seul, c'est plus sûr. 😂", "L'apocalypse ? J'ai déjà mes billets. 🎫", "Tu es le maillon très faible. 🔗",
            "J'ai mangé le messager, désolé. 💌", "Le vide me regarde avec envie. 🕳️", "T'as la jugeote d'une huître périmée. 🦪",
            "La nuit porte conseil et des masques. 👺", "Je déteste tout le monde équitablement. ⚖️", "Ton avenir tient dans une cuillère. 🥄",
            "C'est un désastre, bravo l'artiste ! 👏", "J'ai perdu mon humanité au pressing. 👔", "T'as le charisme d'une endive cuite. 🥬",
            "La vie est dure, comme mon cœur. 💎", "J'ai peur de moi-même parfois. 🙀", "Ton âme est en solde à -90%. 🏷️",
            "C'est l'heure du grand saut, vole ! 🦅", "Je n'ai pas de sentiments, merci. ❄️", "T'es plus utile mort que vif. 💵",
            "Le cauchemar ne fait que commencer. 👻", "J'ai troqué mon cœur contre du café. ☕", "Ton existence est une erreur 404. 🚫",
            "Je m'ennuie, tu veux mourir ? 🗡️", "L'enfer, c'est tes stories Instagram. 🤳", "T'as une tête de lendemain de veille. 🍺",
            "Je ne juge pas, je condamne. 👨‍⚖️", "La haine est un moteur puissant. 🏎️", "C'est trop tard pour demander pardon. 🕰️",
            "Ton chat complote contre toi, fuis ! 🐈‍⬛", "J'ai un secret, mais t'es mort. 🤐", "La chance tourne, la corde aussi. 🪢",
            "Tu es l'erreur que j'assume pas. ✖️", "J'aime l'odeur du chaos matinal. 🌋", "C'est pas de l'humour, c'est triste. 🎭",
            "Ton cerveau fait 'bip' dans le vide. 📟", "La fête est finie, rentre chez toi. 🏠", "Je t'observe depuis le grenier. 👀",
            "C'est beau la mort vue d'ici. 🌤️", "Fais un pas, le vide t'attend. 🕳️", "L'espoir est une maladie mentale. 🧠",
            "Je préfère les chiens, ils se taisent. 🐕", "Ton cercueil sera en carton recyclé. 📦", "J'ai mangé ton ange gardien. 🍗",
            "La politesse est une perte de temps. ⏱️", "T'as le QI d'une poignée de porte. 🚪", "Je recycle tes larmes en glaçons. 🧊",
            "L'avenir est une blague de mauvais goût. 🃏", "T'es une erreur de la nature. 🍄", "La vérité blesse, je vais t'achever. 🗡️",
            "J'ai vendu ton héritage au casino. 🎰", "Ton visage est une insulte au monde. 🌍", "Je ris jaune, comme tes dents. 🦷",
            "L'amour ? Une réaction chimique foireuse. 🧪", "T'es aussi utile qu'un parapluie troué. ☂️", "J'ai oublié d'avoir de la pitié. 😶",
            "Ton testament tient sur un Post-it. 📝", "La faucheuse me doit de l'argent. 💰", "T'as la personnalité d'un parpaing. 🧱",
            "Je t'offrirais bien mon cœur, mais... 🍖", "Le soleil brille, quel enfer. ☀️", "T'es le brouillon de quelqu'un d'autre. ✒️",
            "J'ai nettoyé mon fusil en pensant à toi. 🔫", "La vie passe, la douleur reste. 🩹", "T'as le regard d'un poisson mort. 🐟",
            "Je ne dors plus, je guette. 👁️", "Ton destin est déjà à la poubelle. 🗑️", "J'aime ton désespoir, il brille. ✨",
            "T'as confondu courage et stupidité. 🤡", "La fin du monde ? Enfin ! ☄️", "J'ai repeint ma chambre avec mes regrets. 🎨",
            "Ton cœur bat pour rien, arrête-le. 💓", "Je suis le monstre sous ton lit. 👹", "T'as l'élégance d'une méduse échouée. 🪼",
            "Le bonheur est une légende urbaine. 🏙️", "J'ai cassé ton rêve hier soir. 🔨", "Tu sers à rien, même comme engrais. 🌱",
            "La mort rit, je l'accompagne. 😂", "Ton âme pue la défaite. 👃", "J'ai jeté tes clés au fond du puits. 🗝️",
            "T'as le cerveau qui fait écho. 📣", "La vie est une farce sans chute. 🎭", "J'ai épousé mes cauchemars. 💍",
            "Ton existence est un bug système. 💻", "Le futur est déjà périmé. 🥛", "J'ai tué le temps, il saigne. ⌚",
            "T'es beau comme un accident de voiture. 🏎️", "La solitude est mon armure. 🛡️", "J'ai troqué mes amis contre du silence. 🤐",
            "Ton chemin mène direct au mur. 🧱", "J'aime le vide, il me comprend. 🕳️", "T'as la grâce d'un hippopotame bourré. 🦛",
            "La joie est une insulte personnelle. 😤", "J'ai enterré le passé, il bouge encore. ⚰️", "Ton ombre est plus sympa que toi. 👋",
            "Le monde est une fosse commune. 🌍", "J'ai oublié comment on sourit. 😶", "T'as le charme d'un pneu crevé. 🛞",
            "La mort est mon unique certitude. ✔️", "J'ai noyé mes soucis, ils nagent. 🏊", "Ton talent est une rumeur infondée. 🤫",
            "Le néant est mon jardin préféré. 🌳", "J'ai mis du poison dans tes céréales. 🥣", "T'as la tête d'un jour sans pain. 🥖",
            "La raison est partie en vacances. 🏖️", "J'ai griffonné ton nom sur ma hache. 🪓", "Ton cri est ma musique préférée. 🎶",
            "Le malheur est mon ombre portée. 👤", "J'ai vendu tes souvenirs aux puces. 🐜", "T'as la profondeur d'une flaque d'eau. 💧",
            "La haine me tient chaud l'hiver. ❄️", "J'ai tué le Père Noël, désolé. 🎅", "Ton espoir est un aveugle égaré. 👨‍🦯",
            "Le sang lave tout, même l'honneur. 🩸", "J'ai perdu la tête, tu l'as vue ? 🧠", "T'as l'intelligence d'un bulot cuit. 🐚",
            "La fin justifie les moyens sales. 🧤", "J'ai bu tes larmes, c'est salé. 🧂", "Ton avenir est écrit en noir. ✒️",
            "Le chaos est mon seul maître. 🌀", "J'ai fermé la porte à double tour. 🔒", "T'as la finesse d'un bulldozer. 🚜",
            "La vie m'épuise, la mort m'attend. 🛋️", "J'ai brûlé les ponts et le fleuve. 🔥", "Ton génie est une erreur de frappe. ⌨️",
            "Le vide est plein de promesses. ✨", "J'ai enterré la hache... dans ton dos. 🪓", "T'as le charisme d'un yaourt nature. 🍦",
            "La fin est là, range ta chambre. 🧹", "J'ai souri une fois, c'était horrible. 🤮", "Ton destin est un cul-de-sac. 🚧",
            "Le silence hurle plus fort que toi. 📢", "J'ai mangé la dernière part d'espoir. 🍰", "T'as le cerveau en grève illimitée. 🪧",
            "T'as le regard d'une vache qui regarde passer un train. 🐄", "Ton âme est un parking vide à minuit. 🏢", "J'ai remplacé mes rêves par des pilules. 💊",
            "La mort n'est qu'un changement de propriétaire. 🏠", "Ton cerveau est en mode économie d'énergie permanent. 🔋", "J'ai enterré ma dignité avec mon premier ex. ⚰️",
            "L'espoir est le café des pauvres d'esprit. ☕", "T'as la réactivité d'un paresseux sous Valium. 🦥", "Je ne vieillis pas, je me corrode. ⚙️",
            "Ta vie ressemble à une erreur de copier-coller. 📄", "J'ai mis du sel dans ton café, juste par haine. 🧂", "Le bonheur est une légende pour enfants sages. 📖",
            "T'as le charisme d'un meuble en kit manquant. 🛋️", "La solitude pue, mais elle ne ment jamais. 👃", "J'ai vendu tes secrets pour un ticket de métro. 🎫",
            "Ton destin est aussi brillant qu'un trou noir. 🌑", "Le monde est une blague, je suis le rire. 😂", "T'as l'audace d'un moustique dans une chambre fermée. 🦟",
            "La vérité est un poison lent mais efficace. 🧪", "J'ai dessiné une cible sur ton futur. 🎯", "Ton sourire est une menace pour l'humanité. 👄",
            "Le vide me murmure ton nom sans arrêt. 🗣️", "T'as la profondeur d'une assiette à dessert. 🍰", "J'ai oublié d'être poli avec les déchets. 🗑️",
            "La fin du voyage est une impasse bétonnée. 🚧", "Ton cœur bat au rythme d'une erreur système. 💻", "J'aime l'ombre, elle ne juge pas mes cernes. 👁️",
            "T'as la grâce d'un piano qui tombe du ciel. 🎹", "Le chaos est la seule langue que je parle. 🌀", "J'ai noyé ma conscience dans un verre d'eau. 💧",
            "Ton avis est un bruit parasite dans ma tête. 📻", "La mort est une porte qui ne s'ouvre qu'une fois. 🚪", "T'as le cerveau qui flotte dans du vide. 🎈",
            "J'ai gravé 'échec' sur ton paillasson. 👞", "Le temps est un bourreau qui ne dort jamais. ⏱️", "T'as la personnalité d'une facture d'électricité. ⚡",
            "J'ai troqué mon empathie contre du cynisme pur. 💎", "Ta réussite est un mirage dans le désert. 🌵", "Le néant t'attend, fais-lui un beau sourire. 👋",
            "T'as l'utilité d'un parapluie dans un sous-marin. ⚓", "J'ai caché la vérité sous un tapis de mensonges. 🧹", "Ton nom est déjà effacé de ma mémoire. 🧠",
            "La haine est une flamme qui ne s'éteint jamais. 🔥", "T'as le dynamisme d'une huître en fin de vie. 🦪", "J'ai parié sur ta chute, j'ai gagné gros. 💰",
            "Le futur est un monstre qui nous dévore. 🐲", "T'as le génie d'un caillou dans une chaussure. 👟", "La vie est un film dont j'ai détesté la fin. 🎬",
            "J'ai rempli ton oreiller de doutes amers. 🛌", "Ton existence est une note de bas de page. 📝", "Le silence est le cri de mon âme. 📢",
            "T'as la logique d'un poulet sans tête. 🐔", "J'ai vendu tes larmes à un collectionneur d'art. 🎨", "La réalité blesse, le mensonge achève proprement. 🔪",
            "Ton espoir est un ballon percé par mon mépris. 🎈", "J'ai mis ton bonheur au congélateur. ❄️", "T'as l'aura d'un néon qui clignote trop. 💡",
            "La mort est la seule chose équitable ici. ⚖️", "J'ai oublié de t'inviter à ma survie. 🚫", "T'as le flair d'un chien de porcelaine. 🐕",
            "Le monde brûle, je regarde les étincelles. 🎇", "J'ai écrit 'fuis' sur ton miroir de salle de bain. 🧼", "Ton passé est un boulet que j'adore polir. ⛓️",
            "T'as l'éclat d'une cuillère rouillée. 🥄", "La joie est une distraction pour les simples d'esprit. 🧠", "J'ai donné tes rêves aux rats de la cave. 🐀",
            "Ton destin est un ticket de loto perdant. 🎫", "Le néant est une maison où je suis né. 🏚️", "T'as la tête d'un accident de jardinage. 🚜",
            "La souffrance est le seul professeur honnête. 👨‍🏫", "J'ai mis ton ego dans une déchiqueteuse. 📄", "Ton âme a l'odeur du vieux renfermé. 👃",
            "Le temps coule, mon sang aussi. 🩸", "T'as la prestance d'un sac poubelle éventré. 🗑️", "J'ai échangé ton futur contre un sandwich. 🥪",
            "La vie est un naufrage sans gilet de sauvetage. 🚢", "T'as la subtilité d'un coup de masse. 🔨", "J'ai éteint la lumière au bout du tunnel. 🌑",
            "Ton courage est une illusion pour les faibles. 🎭", "Le malheur est mon seul compagnon fidèle. 👤", "T'as l'intelligence d'un bouton de culotte. 🔘",
            "J'ai mangé tes envies pour calmer ma faim. 😋", "La fin est un plat qui se mange froid. 🍽️", "T'as le regard d'un poisson dans un mixeur. 🐟",
            "J'ai effacé ton visage de toutes les photos. 📷", "Le vide m'appelle, je vais raccrocher. ☎️", "T'as l'originalité d'un code-barres. 🏷️",
            "La vie est une farce, je suis le clown triste. 🤡", "J'ai vendu mon cœur pour une poignée de clous. 🔩", "Ton bonheur est une erreur de programmation. ⌨️",
            "T'as la souplesse d'un poteau électrique. ⚡", "Le destin est une corde qui se resserre. 🪢", "J'ai peint ton avenir en gris béton. 🎨",
            "La solitude est un festin où je suis seul. 🍷", "T'as le flair d'une taupe en plein jour. 🕶️", "J'ai mis ton nom sur une liste noire. 📓",
            "La réalité est une cage dont j'ai perdu la clé. 🔐", "T'as la mémoire d'un poisson rouge amnésique. 🐠", "J'ai jeté tes promesses par la fenêtre. 🪟",
            "Le monde est une fosse, je creuse encore. 🕳️", "T'as le style d'un épouvantail en hiver. 🧥", "J'ai oublié comment on fait semblant. 😶",
            "La mort est une amie qui ne déçoit jamais. 🤝", "T'as l'énergie d'une pile plate. 🔋", "J'ai enterré mes remords sous le goudron. 🛣️",
            "La vie est un test que j'ai raté exprès. 📝", "T'as la tête d'un lendemain de défaite. 📉", "J'ai mis du piment dans tes larmes. 🌶️",
            "Le néant est mon paysage de vacances. 🏜️", "T'as la profondeur d'un trottoir mouillé. ☔", "J'ai brisé ton miroir pour voir ton vrai moi. 🪞",
            "La haine est mon moteur, la vengeance mon carburant. 🏎️", "T'as l'audace d'un moucheron sur un pare-brise. 🚘", "J'ai coupé les fils de ton cerf-volant. 🪁",
            "La mort est le point final de ton insignifiance. ✍️", "T'as le génie d'une ampoule grillée. 💡", "J'ai caché ta boussole dans le brouillard. 🌫️",
            "Le futur est une porte qui claque au nez. 🚪", "T'as l'aura d'une poubelle un jour d'été. ☀️", "J'ai mis tes espoirs dans un broyeur. 🏗️",
            "La réalité est une insulte quotidienne. 😤", "T'as la finesse d'un éléphant dans un magasin de vitres. 🐘", "J'ai oublié ton nom avant même de le savoir. 📛",
            "La vie est une maladie qu'on attrape à la naissance. 🍼", "T'as le dynamisme d'un meuble en formica. 🗄️", "J'ai parié sur ton échec, je suis millionnaire. 💎",
            "Le vide est mon meilleur ami, il ne parle pas. 🤐", "T'as la tête d'une erreur de la nature. 🍄", "J'ai repeint ton enfer avec tes rêves. 🎨",
            "La fin est proche, apporte ton doudou. 🧸", "T'as le charisme d'un caillou sans mousse. 🪨", "J'ai vendu ton âme à un marchand de sable. ⏳",
            "La solitude est une mer où je me noie. 🌊", "T'as le flair d'une statue en marbre. 🗿", "J'ai mis ton bonheur dans une décharge. 🗑️",
            "La réalité est une prison sans barreaux. ⛓️", "T'as la mémoire d'une brique. 🧱", "J'ai jeté ton cœur aux chiens galeux. 🐕‍🦺",
            "Le monde est un trou, je suis au fond. 🕳️", "T'as le style d'un naufragé du dimanche. 🏝️", "J'ai oublié de t'aimer, j'avais piscine. 🏊",
            "La mort est une danse, je n'ai pas de partenaire. 💃", "T'as l'énergie d'un vieux tapis poussiéreux. 🧹", "J'ai enterré le futur dans le jardin. 🌻",
            "La vie est un mauvais rêve dont on ne se réveille pas. 😴", "T'as la tête d'un bug informatique. 🐛", "J'ai mis tes remords dans un mixeur. 🥤",
            "Le néant est une mélodie que j'adore siffler. 🎶", "T'as la profondeur d'un post-it. 📝", "J'ai brisé tes illusions à coups de marteau. 🔨",
            "La haine est mon jardin, la douleur ma récolte. 👨‍🌾", "T'as l'audace d'un grain de sable. 🏖️", "J'ai brûlé ton testament pour rire. 🔥",
            "La mort est la chute de ta mauvaise blague. 🎭", "T'as le génie d'un tournevis émoussé. 🪛", "J'ai caché ton destin derrière un mur. 🧱",
            "Le futur est un train qui nous écrase. 🚂", "T'as l'aura d'un vieux pneu brûlé. 🛞", "J'ai mis tes rêves dans une centrifugeuse. 🌀",
            "La réalité est une gifle permanente. 👋", "T'as la finesse d'un tronc d'arbre. 🪵", "J'ai oublié de te dire que je m'en fous. 🤷",
            "La vie est un contrat que je n'ai pas lu. 📜", "T'as le dynamisme d'une pierre tombale. 🪦", "J'ai parié sur ton silence, j'ai gagné. 🤐",
            "Le vide est mon luxe, l'ennui mon domaine. 🏰", "T'as la tête d'un mauvais présage. 🦅", "J'ai repeint ton futur en noir corbeau. 🐦",
            "La fin est une porte dérobée. 🚪", "T'as le charisme d'un cure-dent usagé. 🦷", "J'ai vendu ton espoir aux enchères. 🔨",
            "La solitude est un cri sans écho. 📣", "T'as le flair d'un bouchon de liège. 🍾", "J'ai mis ta joie au rebut. 🚮",
            "La réalité est un cauchemar éveillé. 👁️", "T'as la mémoire d'un vieux disque rayé. 💿", "J'ai jeté tes souvenirs dans l'acide. 🧪",
            "Le monde est une farce, je n'ai pas ri. 😐", "T'as le style d'un gant de toilette perdu. 🧼", "J'ai oublié d'être humain aujourd'hui. 🤖",
            "La mort est une promesse que je tiens. 💀", "T'as l'énergie d'une limace fatiguée. 🐌", "J'ai enterré tes excuses sous la neige. ❄️",
            "La vie est un cirque sans animaux. 🎪", "T'as la tête d'une mauvaise idée. 💡", "J'ai mis tes désirs dans une broyeuse. 🚜",
            "Le néant est mon seul héritage. 📂", "T'as la profondeur d'une cuillère à café. ☕", "J'ai brisé ton élan avec une enclume. 🔨",
            "La haine est une racine, la mort est le fruit. 🍎", "T'as l'audace d'une poussière. 🌬️", "J'ai brûlé ta chance pour me chauffer. 🔥",
            "La mort est la seule sortie de secours. 🚪", "T'as le génie d'un bocal vide. 🫙", "J'ai caché la lumière pour ne plus te voir. 🌑",
            "Le futur est un abîme sans fond. 🕳️", "T'as l'aura d'une chaussette orpheline. 🧦", "J'ai mis tes ambitions au compost. 🍂",
            "La réalité est un mirage qui pique. 🌵", "T'as la finesse d'une masse d'arme. ⚔️", "J'ai oublié ton existence, c'était génial. 🌈"
        ]

        self.asset_path = r"C:\resto_controller\anim_perso"
        self.json_path = r"C:\resto_controller\anim_perso.json"

        # --- CONFIG DES ANIMATIONS ---
        # (Fichier, Largeur, Hauteur, Nb_Frames)
        self.anims = {}
        self.brain_rules = [] # Très important pour éviter l'erreur de tout à l'heure
        self.load_character_config(char_name) # char_name est passé à l'init (ex: "vampire")
        
        # Widget Image de sécurité
        self.img_label = tk.Label(root, bg="white", bd=0)
        self.img_label.pack()

        # --- POSITION ET DÉPLACEMENT ---
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.x, self.y = random.randint(100, 500), random.randint(100, 500)
        self.dx, self.dy = 0, 0 
        self.speed = 4
        self.is_grabbed = False
        
        self.root.geometry(f"+{self.x}+{self.y}")
        
        # BINDINGS
       # Remplace tes anciens binds par ceux-ci :
        self.img_label.bind("<Button-1>", self.on_press)
        self.img_label.bind("<B1-Motion>", self.on_drag)
        self.img_label.bind("<ButtonRelease-1>", self.on_release)

        self.brain_loop()      
        self.animation_loop()
        self.check_time_loop() # <--- Lancement de la surveillance horaire
        self.check_visibility()


    def hide_for_time(self, hours):
        """Cache le personnage pour une durée spécifique (reçue en argument)."""
        self.is_hidden = True
        
        # On multiplie le nombre d'heures reçu par 3600 (secondes dans une heure)
        self.hidden_until = datetime.now().timestamp() + (hours * 3600) 
        
        self.root.withdraw() # Cache la fenêtre complètement
        print(f"Le personnage est caché pour {hours} heure(s).")

    def reveal_pet(self):
        """Fait réapparaître le personnage proprement."""
        self.is_hidden = False
        self.hidden_until = 0 # On remet à zéro
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.state = "IDLE"

    def check_visibility(self):
        """Vérifie si le temps est écoulé pour réapparaître."""
        if self.is_hidden and self.hidden_until > 0:
            now = datetime.now().timestamp()
            if now >= self.hidden_until:
                self.reveal_pet() # Utilise la fonction de réapparition
                print("Le personnage est de retour après 4 heures !")
        
        # Relance la vérification chaque seconde
        self.root.after(1000, self.check_visibility)

    def load_character_config(self, char_name):
        try:
            if not os.path.exists(self.json_path):
                raise FileNotFoundError("Le fichier anim_perso.json est introuvable !")

            with open(self.json_path, 'r') as f:
                config = json.load(f)
            
            if char_name in config:
                data = config[char_name]
                
                # --- OPTIMISATION : Vider la mémoire avant de recharger ---
                self.anims.clear() 
                
                # Chargement de TOUTES les animations définies dans le JSON en mémoire
                for action, params in data.get("animations", {}).items():
                    full_path = os.path.join(self.asset_path, params[0])
                    if os.path.exists(full_path):
                        # Cette fonction crée les objets PhotoImage qui restent en RAM
                        self.anims[action] = self.load_flexible_frames(full_path, params[1], params[2], params[3])
                    else:
                        print(f"🚫 Fichier image manquant: {params[0]}")
                
                self.brain_rules = data.get("brain", [])
                print(f"✅ {char_name} chargé intégralement en mémoire ({len(self.anims)} animations).")
            else:
                print(f"❓ Perso '{char_name}' inconnu dans le JSON.")
                
        except Exception as e:
            print(f"💥 ERREUR CHARGEMENT CONFIG: {e}")
            self.brain_rules = [{"state": "IDLE", "chance": 1.0, "movement": "stop"}]

    def check_time_loop(self):
        """Déclenche un message toutes les 10 minutes, peu importe l'heure."""
        # 1. On affiche le message (sauf si on est en train de traîner le pet)
        if not self.is_grabbed:
            self.show_message()

        # 2. On programme le prochain message dans 30 minutes exactement
        # 30 minutes * 60 secondes * 1000 millisecondes = 1 800 000 ms
        intervalle_ms = 10 * 60 * 1000 
        
        self.root.after(intervalle_ms, self.check_time_loop)
        
    def load_flexible_frames(self, filename, fw, fh, num_frames):
        """Charge et découpe les frames avec gestion d'erreur."""
        frames_r, frames_l = [], []
        try:
            sheet = Image.open(filename).convert("RGBA")
            for i in range(num_frames):
                box = (i * fw, 0, (i + 1) * fw, fh)
                frame = sheet.crop(box)
                frames_r.append(ImageTk.PhotoImage(frame))
                frames_l.append(ImageTk.PhotoImage(frame.transpose(Image.FLIP_LEFT_RIGHT)))
        except Exception as e:
            print(f"Erreur sur {filename}: {e}")
            # Création d'un carré vide si le fichier manque
            err = Image.new('RGBA', (fw, fh), (0, 0, 0, 0))
            frames_r = [ImageTk.PhotoImage(err)]
            frames_l = [ImageTk.PhotoImage(err)]
        return {"R": frames_r, "L": frames_l}

    def on_click(self, event):
        """Affiche une bulle de texte temporaire."""
        msg = random.choice(self.expressions)
        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.geometry(f"+{int(self.x) + 20}+{int(self.y) - 40}")
        
        tk.Label(popup, text=msg, bg="#FFF9C4", fg="black", 
                 relief="solid", bd=1, padx=5, font=("Arial", 9, "bold")).pack()
        self.root.after(2500, popup.destroy)

    

    
    
    def brain_loop(self):
        """Choisit le prochain état parmi toutes les variations disponibles avec gestion d'actions spécifiques."""
        if self.is_grabbed:
            self.root.after(1000, self.brain_loop)
            return
            
        # --- GESTION DE LA PUNITION ANIMÉE ---
        if self.is_punished:
            # On récupère toutes les variantes de repos (IDLE_01, IDLE_02, etc.)
            idle_variants = [s for s in self.anims.keys() if "IDLE" in s.upper()]
            
            if idle_variants:
                self.state = random.choice(idle_variants)
            else:
                self.state = "IDLE" # Repli si aucune variante n'est trouvée
                
            self.speed = 0
            self.dx, self.dy = 0, 0
            self.current_frame = 0 # On reset la frame pour lancer la nouvelle animation
            
            # Change de direction de regard aléatoirement pour simuler l'ennui
            self.facing_right = random.choice([True, False])

            # On relance le cerveau entre 3 et 6 secondes pour changer de posture d'IDLE
            self.root.after(random.randint(3000, 6000), self.brain_loop) 
            return

        # --- COMPORTEMENT NORMAL ---
        self.is_waiting = False 
        
        try:
            states_available = list(self.anims.keys())
            if not states_available:
                self.state = "IDLE"
                return

            # Sélection d'un nouvel état aléatoire
            self.state = random.choice(states_available)
            self.current_frame = 0
            
            upper_state = self.state.upper()

            # --- LOGIQUE DE VITESSE ET DIRECTION SELON L'ACTION ---
            
            # 1. État de Course (Rapide)
            if "RUN" in upper_state:
                self.speed = 8
                self.dx = random.choice([-1, 1])
                self.dy = 0
                
            # 2. État de Marche (Normal)
            elif "WALK" in upper_state:
                self.speed = 3
                self.dx = random.choice([-1, 1])
                self.dy = 0
                
            # 3. État de Vol (Mouvement vertical autorisé)
            elif "FLY" in upper_state:
                self.speed = 5
                self.dx = random.choice([-1, 1])
                self.dy = random.choice([-1, 0, 1]) # Peut monter, descendre ou stagner
                
            # 4. État de Saut (Impulsion initiale vers le haut)
            elif "JUMP" in upper_state:
                self.speed = 5
                self.dx = random.choice([-1, 1])
                self.dy = -4 # Cette valeur sera gérée par la gravité dans move_logic
                
            # 5. États Statiques ou Spéciaux (EAU, FEU, COUCOU, IDLE)
            else:
                self.speed = 0
                self.dx, self.dy = 0, 0

        except Exception as e:
            print(f"❌ Erreur critique dans brain_loop: {e}")
            # En cas de crash, on tente de trouver n'importe quel IDLE pour rester stable
            self.state = next((s for s in states_available if "IDLE" in s.upper()), "IDLE")

        # Mise à jour de l'orientation visuelle selon le mouvement horizontal
        if self.dx > 0: 
            self.facing_right = True
        elif self.dx < 0: 
            self.facing_right = False


    def move_logic(self):
        """Déplace la fenêtre avec rebonds physiques, lancer, et maintien sur l'écran 1."""
        # On ne calcule pas la physique si on est en train de le traîner
        if self.is_grabbed or self.is_waiting:
            return

        # --- 1. LOGIQUE DE PUNITION (Téléportation ou arrêt au coin) ---
        if self.is_punished:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            self.x = sw - 250
            self.y = sh - 150
            self.speed = 0
            self.root.geometry(f"+{int(self.x)}+{int(self.y)}")
            return

        # --- 2. GESTION DE LA VÉLOCITÉ (LANCER) ---
        # Si on l'a lancé, il ralentit progressivement (friction)
        if self.speed > 2.5:
            self.speed *= 0.97  
        else:
            self.speed = 2 # Vitesse de croisière minimale

        # --- 3. LOGIQUE DE SAUT / VOL ---
        if "JUMP" in self.state:
            jump_progress = self.current_frame / (len(self.anims[self.state]["R"]) or 1)
            self.dy = -4 + (jump_progress * 8) 
        elif "FLY" in self.state:
            import math
            self.dy += math.sin(self.current_frame * 0.5) * 0.2

        # --- 4. APPLICATION DU MOUVEMENT ---
        self.x += self.dx * self.speed
        self.y += self.dy * self.speed

        # --- 5. COLLISIONS ET REBONDS RÉELS (ÉCRAN 1) ---
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        padding = 128 

        # REBOND HORIZONTAL (Gauche / Droite)
        if self.x <= 0:
            self.x = 0
            self.dx = abs(self.dx)  # Force à aller vers la droite (positif)
            self.facing_right = True
        elif self.x >= sw - padding:
            self.x = sw - padding
            self.dx = -abs(self.dx) # Force à aller vers la gauche (négatif)
            self.facing_right = False

        # REBOND VERTICAL (Haut / Bas)
        if self.y <= 0:
            self.y = 0
            self.dy = abs(self.dy) # Rebondit vers le bas
        elif self.y >= sh - padding:
            self.y = sh - padding
            
            # Si le perso arrive avec de la vitesse (lancer)
            if self.speed > 4:
                self.dy = -abs(self.dy) * 0.7 # Rebondit vers le haut avec perte d'énergie
            else:
                # Comportement normal au sol
                if any(s in self.state.upper() for s in ["JUMP", "WALK", "RUN"]):
                    self.dy = 0
                else:
                    self.dy = -0.5 # Petit flottement

        # --- 6. MISE À JOUR FINALE ---
        self.root.geometry(f"+{int(self.x)}+{int(self.y)}")

    def animation_loop(self):
        """Gère les images avec détection d'erreurs, vitesse adaptative et mode caché."""
        try:
            # --- 1. VÉRIFICATION DU MODE CACHÉ ---
            if self.is_hidden:
                # On ne fait rien, on relance juste la boucle plus tard 
                # pour vérifier quand self.is_hidden repassera à False
                self.root.after(500, self.animation_loop)
                return

            now = datetime.now().timestamp()
            if self.is_punished and now > self.punishment_end:
                self.is_punished = False
                self.state = "IDLE"

            # Délai par défaut (en millisecondes)
            animation_delay = 100 

            if not self.is_grabbed:
                self.move_logic()
                
                side = "R" if self.facing_right else "L"
                
                if self.state in self.anims and side in self.anims[self.state]:
                    frames = self.anims[self.state][side]
                    num_frames = len(frames)
                    
                    if not frames:
                        raise ValueError(f"Liste d'images vide pour {self.state}")

                    # --- LOGIQUE DE VITESSE ---
                    if num_frames <= 8:
                        animation_delay = 200
                    elif num_frames >= 12:
                        animation_delay = 150
                    else:
                        animation_delay = 150 

                    if self.current_frame >= num_frames:
                        self.current_frame = 0
                    
                    self.img_label.config(image=frames[self.current_frame])
                    self.current_frame += 1
                    
                    if self.current_frame >= num_frames:
                        if not self.is_waiting and not self.is_punished:
                            self.is_waiting = True
                            self.dx, self.dy = 0, 0
                            self.root.after(1000, self.brain_loop) 
                else:
                    self.state = "IDLE"

            # On relance la boucle avec le délai calculé
            self.root.after(animation_delay, self.animation_loop)

        except Exception as e:
            print(f"Erreur animation: {e}")
            self.state = "IDLE"
            self.root.after(100, self.animation_loop)

    def on_press(self, event):
        """Fusion de on_click et du chrono menu : Gère messages, punition et 10s."""
        now = datetime.now().timestamp()

        # 1. GESTION SI DÉJÀ EN PUNITION (Tes 100 messages)
        if self.is_punished:
            if now < self.punishment_end:
                messages_boude = [
                    "GRR ! Laisse-moi tranquille ! 💢", "NON ! 😤", "ARRÊTE ! Je bouillonne là ! 🔥",
                    "Touche-moi encore et je mords ! 🦷", "GRRR... Je suis un tigre féroce ! 🐯",
                    "Méchant humain ! 😠", "C'est fini entre nous pour 5 minutes ! 💔",
                    "Ne me regarde même pas ! 🙈", "Je suis en pétard ! 🧨", "Hé ! Mes poils se hérissent ! 🐈",
                    "Je ne suis pas d'humeur ! 👺", "Vade Retro Satana ! ✝️", "C'est la guerre ! ⚔️",
                    "Tu vas tâter de mes griffes ! 🐾", "Même pas en rêve ! 💭", "Je fulmine ! 💨",
                    "Alerte ! Zone de danger ! ⚠️", "Je suis une petite boule de rage ! 💣",
                    "PFF... Je ne te parle plus. 🙄", "M'en fiche, je boude. 😒", "Même pas mal. 💅",
                    "Cause toujours, tu m'intéresses... 🥱", "Je t'ignore royalement. 👑",
                    "Tu parles à mon dos là. 🎒", "Bof. 😑", "Quel ennui... 🌫️", "Inintéressant. ☁️",
                    "Je fais la grève du clic ! 🪧", "Désolé, je suis en mode avion. ✈️",
                    "Cherche pas, je suis ailleurs. 🌌", "Bla bla bla... 🗣️", "Zéro attention pour toi. 📉",
                    "Je suis invisible, tu ne me vois pas. 👻", "Silence radio. 📻",
                    "ZZZ... (Fait semblant de dormir) 😴", "Je dors, reviens jamais ! 💤",
                    "Ron-pschiiit... 🌙", "Dodo thérapeutique. 🛌", "Ne pas déranger l'artiste. 🎨",
                    "Mon cerveau est en maintenance. 🛠️", "Mode hibernation activé. ❄️",
                    "Je recharge mes batteries loin de toi. 🔋", "Trop fatigué pour tes bêtises. 🦇",
                    "Je suis en grève, contacte mon syndicat. ✊", "Error 404: Patience not found. 🚫",
                    "Je suis un fantôme maintenant. Houuu ! 👻", "Appelle mon avocat ! ⚖️",
                    "Je suis parti vivre sur Mars. 🚀", "Je médite pour ne pas t'exploser. 🧘",
                    "Je compte les pixels au plafond. 🔢", "Je prépare ma vengeance... 😈",
                    "C'est mon quart d'heure de drama. 🎭", "Je suis une statue de sel. 🧂",
                    "Alerte : Trop de clics, système surchauffé ! 🌡️",
                    "Je transforme tes clics en poussière d'étoile. ✨",
                    "Na ! 😝", "Tu l'as bien cherché ! 🤷", "C'est ton problème, pas le mien. 🧩",
                    "Bouderie niveau 100 activée. 📈", "Je fais la tête et j'aime ça. 🗿",
                    "Regarde ailleurs, je suis moche quand je boude. 👺",
                    "Même mes oreilles boudent. 👂", "Je me retire de la vie publique. 🚪",
                    "Privé de chat pour aujourd'hui ! 🚫", "Je vais dire à tout le monde que t'es méchant. 📢",
                    "Je suis tout petit mais ma colère est géante ! 🌋", "Pas de câlin ! 🙅",
                    "Je suis une noisette en colère. 🌰", "Pousse pas mémé dans les orties ! 🌿",
                    "Je boude, mais je suis toujours beau. ✨", "Mon petit cœur est en pierre. 💎",
                    "Je fais la moue. 😗", "Je me cache dans ma boîte imaginaire. 📦",
                    "NON. 🛑", "STOP. ✋", "OUBLIE. 🧠", "CHUT ! 🤫", "MERCI, NON. 🙅‍♂️",
                    "BYE. 👋", "FINI. 🏁", "NOPE. 👎", "NADA. ⭕", "LATER. ⏳",
                    "On fera les comptes plus tard. 🧮", "Tu ne perds rien pour attendre... 🕰️",
                    "Ma vengeance sera terrible (et mignonne). 🎀",
                    "Attend que je sorte de ce panier ! 🧺", "Tu joues avec le feu là... 🔥",
                    "Un jour, je viderai ta batterie pour me venger. 🔌",
                    "Je note ton nom sur ma liste noire. 📝",
                    "T'as de la chance que je sois coincé dans l'écran ! 🖥️",
                    "Ma patience a des limites, et tu les as sautées ! 🚩",
                    "Je vais hanter ton curseur ! 🖱️"
                ]
                self.show_message(random.choice(messages_boude))
                return 
            else:
                self.is_punished = False 

        # 2. ENREGISTRER LE CLIC ET MESSAGE NORMAL
        self.click_times.append(now)
        self.click_times = [t for t in self.click_times if now - t < 5]
        
        if len(self.click_times) < 5:
            self.show_message() # Ton message normal de clic

        # 3. DÉCLENCHEMENT DE LA PUNITION (5 clics rapides)
        if len(self.click_times) >= 5:
            self.is_punished = True
            self.punishment_end = now + (5 * 60)
            self.is_grabbed = False
            self.press_start_time = 0
            
            sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            self.x, self.y = sw - 250, sh - 150
            
            idle_anims = [s for s in self.anims.keys() if "IDLE" in s.upper()]
            self.state = random.choice(idle_anims) if idle_anims else "IDLE"
            self.speed = 0
            self.root.geometry(f"+{int(self.x)}+{int(self.y)}")
            self.show_message("C'EST TROP ! 💢\nJe m'en vais bouder dans mon coin !")
            self.click_times = []
            return

        # 4. INITIALISATION DU GRAB ET CHRONO MENU (10s)
        self.is_grabbed = True
        self.press_start_time = now
        self.offset_x, self.offset_y = event.x, event.y
        self.last_mouse_x, self.last_mouse_y = event.x_root, event.y_root
        self.inertia_x, self.inertia_y = 0, 0

        # Lancement de la surveillance auto pour le menu
        self.check_long_press()
        
    def check_long_press(self):
        """Vérifie le temps en boucle, même sans bouger la souris."""
        if self.is_grabbed and self.press_start_time > 0:
            duration = datetime.now().timestamp() - self.press_start_time
            
            # J'ai mis 10.0 secondes comme demandé
            if duration >= 7.0:
                self.is_grabbed = False
                self.press_start_time = 0 # Reset immédiat
                self.show_character_menu()
                return # Arrêt de la boucle
            
            # Revérifier dans 100ms
            self.root.after(100, self.check_long_press)
    
    

    def update_message_position(self):
        """Repositionne le message au-dessus du personnage s'il existe."""
        if hasattr(self, 'msg_popup') and self.msg_popup.winfo_exists():
            # Calcul de la nouvelle position (centré au-dessus du pet)
            w = self.msg_popup.winfo_width()
            # On utilise int() pour s'assurer que les coordonnées sont des nombres entiers
            pos_x = int(self.x + 64 - (w / 2))
            pos_y = int(self.y - 60) 
            self.msg_popup.geometry(f"+{pos_x}+{pos_y}")

    def on_drag(self, event):
        """Déplacement uniquement si on est toujours en mode grabbed."""
        if self.is_grabbed:
            self.inertia_x = event.x_root - self.last_mouse_x
            self.inertia_y = event.y_root - self.last_mouse_y
            self.last_mouse_x = event.x_root
            self.last_mouse_y = event.y_root

            self.x = event.x_root - self.offset_x
            self.y = event.y_root - self.offset_y
            self.root.geometry(f"+{int(self.x)}+{int(self.y)}")
            
            # --- LA LIGNE À AJOUTER ICI ---
            self.update_message_position()

    def on_release(self, event):
        """Nettoyage total pour permettre une réutilisation immédiate."""
        self.is_grabbed = False
        self.press_start_time = 0 # Arrête check_long_press
        
        force = (abs(self.inertia_x) + abs(self.inertia_y))
        if force > 3:
            self.dx = 1 if self.inertia_x > 0 else -1
            self.dy = 1 if self.inertia_y > 0 else -1
            self.speed = min(force, 35)
            if "FLY" in self.anims: self.state = "FLY"
        else:
            self.speed = 2

    def show_character_menu(self):
        """Affiche le menu même si puni et permet de cacher le pet."""
        # if self.is_punished: return  <-- SUPPRIMÉ pour que ça marche tout le temps

        if self.active_menu is not None and self.active_menu.winfo_exists():
            self.active_menu.lift()
            return

        try:
            with open(self.json_path, 'r') as f:
                config = json.load(f)
                character_names = list(config.keys())
                
            self.active_menu = CharacterSelector(
                self.root, 
                character_names, 
                self.change_character, 
                self.hide_for_time,
                self.last_mouse_x, 
                self.last_mouse_y
            )
            
            self.active_menu.bind("<Destroy>", lambda e: setattr(self, 'active_menu', None))

        except Exception as e:
            print(f"Erreur menu: {e}")

    def change_character(self, name):
        """Change le personnage, charge les images et force le premier plan."""
        try:
            # 1. Sécurité : Initialisation de la variable si absente
            if not hasattr(self, 'current_character'):
                self.current_character = name
            elif name == self.current_character:
                return

            print(f"🔄 Tentative de chargement : {name}...")
            
            # 2. On réinitialise les compteurs AVANT de charger pour éviter les crashs d'index
            self.current_frame = 0
            self.state = "IDLE_01"
            self.current_character = name

            # 3. ON APPELLE TA FONCTION DE CHARGEMENT
            # Vérifie bien que ce nom correspond exactement à ta fonction (ligne 7xx)
            self.load_character_config(name)
            
            # 4. FORCER LA MISE À JOUR VISUELLE IMMÉDIATE
            # On prend la première image du nouvel état pour éviter un label vide
            side = "R" if self.facing_right else "L"
            if self.state in self.anims and side in self.anims[self.state]:
                first_frame = self.anims[self.state][side][0]
                self.img_label.config(image=first_frame)

            # 5. FORCER LE RETOUR AU PREMIER PLAN
            self.root.deiconify()           # Sort de la barre des tâches
            self.root.attributes("-topmost", True) # Force devant
            self.root.lift()                # Remonte la pile
            self.root.focus_force()         # Prend l'attention
            
            print(f"✅ {name} est maintenant actif et au premier plan.")

        except Exception as e:
            print(f"💥 ERREUR CRITIQUE lors du changement de perso: {e}")
            # En cas d'erreur, on essaie de revenir à un état stable
            self.state = "IDLE"
            self.current_frame = 0

    def on_toss(self, event):
        """Relance le comportement du personnage quand on le lâche."""
        self.is_grabbed = False
        self.menu_opened = False 
        
        # On remet l'état par défaut
        self.state = "IDLE"
        self.current_frame = 0 # Recommence l'anim au début
        
        # --- ESSENTIEL : On relance le cerveau immédiatement ---
        # On attend un tout petit peu (100ms) pour laisser Tkinter 
        # stabiliser la position de la fenêtre après le lâcher.
        self.root.after(200, self.brain_loop)
    
    def show_message(self, msg=None):
        """Affiche une bulle de texte avec dégradé rouge si punie."""
        # 1. On détruit l'ancien message s'il existe déjà pour éviter les superpositions
        if hasattr(self, 'msg_popup') and self.msg_popup.winfo_exists():
            self.msg_popup.destroy()

        if msg is None:
            msg = random.choice(self.expressions)
            
        # 2. ON UTILISE self.msg_popup au lieu de popup
        self.msg_popup = tk.Toplevel(self.root)
        self.msg_popup.overrideredirect(True)
        self.msg_popup.attributes("-topmost", True)
        
        bg_color = "#FFFFFE" 
        self.msg_popup.config(bg=bg_color)
        self.msg_popup.attributes("-transparentcolor", bg_color)
        
        # --- CONFIGURATION DES COULEURS ---
        if self.is_punished:
            color_top = (255, 50, 50)    
            color_bottom = (150, 0, 0)
            text_color = "white"
        else:
            color_top = (255, 255, 255)
            color_bottom = (240, 240, 240)
            text_color = "black"

        # --- CRÉATION DU DÉGRADÉ ---
        w, h = 160, 80 
        gradient_img = Image.new('RGB', (w, h), color_top)
        pixels = gradient_img.load()
        for y in range(h):
            r = int(color_top[0] + (color_bottom[0] - color_top[0]) * (y / h))
            g = int(color_top[1] + (color_bottom[1] - color_top[1]) * (y / h))
            b = int(color_top[2] + (color_bottom[2] - color_top[2]) * (y / h))
            for x in range(w):
                pixels[x, y] = (r, g, b)
        
        self.msg_bg_image = ImageTk.PhotoImage(gradient_img)

        # On utilise un Canvas
        canvas = tk.Canvas(self.msg_popup, width=w, height=h, bg=bg_color, highlightthickness=3, highlightbackground="black")
        canvas.pack()
        
        canvas.create_image(w/2, h/2, image=self.msg_bg_image)
        
        canvas.create_text(
            w/2, h/2, 
            text=msg, 
            fill=text_color, 
            font=("Comic Sans MS", 10, "bold"),
            width=w-20, 
            justify="center"
        )

        # --- POSITIONNEMENT INITIAL ---
        # On appelle directement notre nouvelle fonction de positionnement
        self.update_message_position()
        
        # On ferme après 2.5 secondes
        self.root.after(2500, self.msg_popup.destroy)
    
        
if __name__ == "__main__":
    main_root = tk.Tk()
    main_root.withdraw() 
    # Utilisation d'un Toplevel pour éviter les problèmes de focus de la fenêtre root
    pet_window = tk.Toplevel(main_root)
    app = DesktopPet(pet_window)
    main_root.mainloop()