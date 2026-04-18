


####Config avec Groq et Llama 3.3-70B pour génération de rapport avec contexte local forcé####
import os
import json
from dotenv import load_dotenv
from groq import Groq
# ✅ FORCER le reload .env (pas de cache)
load_dotenv(override=True)

# 1. Récupérer la vraie clé depuis le fichier .env
API_KEY = os.getenv("GROQ_API_KEY")

# 2. Sécurité : Empêcher le script de tourner dans le vide si le .env est mal configuré
if not API_KEY:
    raise ValueError("🚨 ERREUR : La clé GROQ_API_KEY est introuvable. Vérifiez votre fichier .env")

# 3. Initialiser le client avec la variable
client = Groq(api_key=API_KEY)
class DonneesTerrain:
    """Représente les inputs exacts du formulaire HTML"""
    def __init__(self, data):
        self.delegation = data.get('delegation')
        self.surface_m2 = data.get('surface_m2')
        self.longueur_m = data.get('longueur_m')
        self.largeur_m = data.get('largeur_m')
        self.dimensions = f"{data.get('longueur_m')}m x {data.get('largeur_m')}m"
        self.sol = data.get('sol')
        self.eau = data.get('eau')
        self.arbres_existants = data.get('arbres_existants')
        self.objectif = data.get('objectif')
        self.budget = data.get('budget')
        self.preferences = data.get('preferences_arbres')
        self.probleme = data.get('probleme')

    def formatted_for_ai(self):
        """Formate les données pour le prompt IA"""
        return f"""
PROFIL DE L'AGRICULTEUR :
- Délégation : {self.delegation}
- Surface du terrain : {self.surface_m2} m² ({self.surface_m2/10000:.2f} ha)
- Dimensions : {self.dimensions}
- Type de sol : {self.sol}
- Source d'eau : {self.eau}
- État actuel : {self.arbres_existants}
- Objectif : {self.objectif}
- Budget disponible : {self.budget}
- Préférences d'arbres : {', '.join(self.preferences) if self.preferences else 'Aucune'}
- Problème connu : {self.probleme}
"""

def charger_contexte_local():
    """Lit les fichiers de référence depuis /data (racine du projet)"""
    base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    
    if not os.path.exists(base_path):
        raise FileNotFoundError(f"❌ Dossier /data introuvable à : {base_path}")
    
    contexte = {
        'stats_agricoles': None,
        'alertes_et_lois': None,
        'regles_techniques': None,
        'reglementation_agricole': None  # ✅ NOUVEAU
    }
    
    # Lecture agriculture.json
    try:
        with open(os.path.join(base_path, 'agriculture.json'), 'r', encoding='utf-8') as f:
            contexte['stats_agricoles'] = json.load(f)
            print(f"✅ agriculture.json chargé ({len(str(contexte['stats_agricoles']))} caractères)")
    except FileNotFoundError:
        print(f"⚠️ agriculture.json non trouvé dans {base_path}")
    except json.JSONDecodeError as e:
        print(f"❌ Erreur JSON dans agriculture.json : {e}")
    
    # Lecture diagnostic.json
    try:
        with open(os.path.join(base_path, 'diagnostic.json'), 'r', encoding='utf-8') as f:
            contexte['alertes_et_lois'] = json.load(f)
            print(f"✅ diagnostic.json chargé ({len(str(contexte['alertes_et_lois']))} caractères)")
    except FileNotFoundError:
        print(f"⚠️ diagnostic.json non trouvé dans {base_path}")
    except json.JSONDecodeError as e:
        print(f"❌ Erreur JSON dans diagnostic.json : {e}")
    
    # Lecture gabes_data.txt
    try:
        with open(os.path.join(base_path, 'gabes_data.txt'), 'r', encoding='utf-8') as f:
            contexte['regles_techniques'] = f.read()
            print(f"✅ gabes_data.txt chargé ({len(contexte['regles_techniques'])} caractères)")
    except FileNotFoundError:
        print(f"⚠️ gabes_data.txt non trouvé dans {base_path}")
    
    # ✅ NOUVEAU : Lecture reglementation_agricole.txt
    try:
        with open(os.path.join(base_path, 'reglementation_agricole.txt'), 'r', encoding='utf-8') as f:
            contexte['reglementation_agricole'] = f.read()
            print(f"✅ reglementation_agricole.txt chargé ({len(contexte['reglementation_agricole'])} caractères)")
    except FileNotFoundError:
        print(f"⚠️ reglementation_agricole.txt non trouvé dans {base_path}")
    
    return contexte

def formatter_contexte_pour_prompt(contexte):
    """Formate le contexte en texte structuré pour le prompt"""
    prompt_contexte = ""
    
    if contexte['stats_agricoles']:
        prompt_contexte += "\n=== DONNÉES STATISTIQUES GABÈS 2023-2024 ===\n"
        prompt_contexte += json.dumps(contexte['stats_agricoles'], indent=2, ensure_ascii=False)
    
    if contexte['alertes_et_lois']:
        prompt_contexte += "\n=== ALERTES LÉGALES ET ENVIRONNEMENTALES ===\n"
        prompt_contexte += json.dumps(contexte['alertes_et_lois'], indent=2, ensure_ascii=False)
    
    if contexte['regles_techniques']:
        prompt_contexte += "\n=== RÈGLES TECHNIQUES DE CULTURE ===\n"
        prompt_contexte += contexte['regles_techniques']
    
    # ✅ NOUVEAU : Ajouter la réglementation
    if contexte['reglementation_agricole']:
        prompt_contexte += "\n=== RÉGLEMENTATION AGRICOLE TUNISIENNE & GABÈS ===\n"
        prompt_contexte += contexte['reglementation_agricole']
    
    return prompt_contexte


