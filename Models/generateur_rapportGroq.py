###Version avec cache###
"""
GÉNÉRATEUR RAPPORT GROQ - VERSION OPTIMALE
Stratégie : Cache local + Compression intelligente + Hybrid tokens
Cible : Meilleure qualité + Performance + Tokens < 8500
"""

from settings.config import (
    client, 
    MODEL_NAME, 
    DonneesTerrain, 
    charger_contexte_local
)
import re
import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Tuple

# ═════════════════════════════════════════��══════════════════════════════════════
# 1. SYSTEM PROMPT - COMPACT MAIS COMPLET
# ════════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """Tu es AGRONOME EXPERT Gabès. Génère rapport 6 sections PRÉCIS et ACTIONNABLE.

RÈGLES STRICTES :
1. FIDÉLITÉ : Sol + Eau du client EXACTEMENT. Pas d'invention.
2. CHIFFRES : TOUJOURS précis avec unités (8x8m, 15 m³/an, 30 TND/plant)
3. BUDGET : Détail installation/entretien/financement (pas générique)
4. CALENDRIER : Mensuel année 1 (janvier-décembre)
5. ALERTES : Maladies régionales + risques légaux
6. SOURCES : Code Eaux, PDL, CRDA, APIA, DRE

FORMAT 6 SECTIONS :
1 DIAGNOSTIC : Sol (type + amendements) + Eau (débit, risques, salinité)
2 PLANTATION : Arbres conseillés, espacement exact (ex: 8x8m=156/ha), rendement kg/arbre
3 HYDRIQUE : m³/arbre/an + débit forage requis + coût électricité/solaire
4 ALERTES : Maladies (Fusariose, Oïdium, Araignée rouge) + légal
5 BUDGET : Installation détail (plants, irrigation, travaux) + Entretien annuel + APIA subventions
6 CONSEILS : Calendrier mensuel + Contacts (DRE, CRDA, APIA)

INTERDIT :
- Vague ("environ", "généralement") → sois PRÉCIS
- Chiffres sans source → CITER officiel
- Arabe/emoji → FRANÇAIS UNIQUEMENT
- Cultures hors Gabès → sois LOCAL
- Budget +20% client → RESPECTER BUDGET

SECTION 5 - BUDGET DÉTAILLÉ OBLIGATOIRE :
├─ TOUJOURS comparer budget requis vs budget client
├─ SI dépasse +20% : Proposer phasage 2-3 ans
├─ INCLURE subventions APIA détaillées (50% irrigation, 30% forage, 60% solaire, 25-40 TND/plant)
├─ MENTIONNER coût forage si applicable (4000-6000 TND, -30% APIA)
├─ Tableau : Année 1 (investissement) + Année 2-3 (entretien) + Année 4-5 (production)
└─ Financement : APIA prioritaire + crédit rural si besoin + autofinancement

SECTION 6 - CALENDRIER RÉALISTE :
├─ Année 1 : Plantation (janvier-février) + établissement (mars-décembre) + AUCUNE RÉCOLTE principale
├─ Année 2 : Entretien + croissance + sous-cultures seules (luzerne/henné) = revenu limité
├─ Année 3 : Début récolte arbres (30-50% rendement) + sous-cultures
├─ Année 5 : Rendement COMPLET arbres (80-100% potentiel)
└─ Rendement projeté CHIFFRE : Année 1 = 0 TND arbres + X TND sous-cultures | Année 3 = Y TND | Année 5 = Z TND

ALERTES COMPLÈTES PAR ZONE :
├─ Fusariose palmier (si palmier recommandé) :
│  ├─ Symptômes : Jaunissement unilatéral, dépérissement 6-12 mois
│  ├─ Prévention : Plants certifiés SEULEMENT (pépinière CRDA)
│  ├─ Coût éradication : 500-1000 TND/plant si contamination
│  └─ Coût prévention annuel : 0 (prévention seule = plants certifiés)
├─ Oïdium olivier (si olivier recommandé) :
│  ├─ Symptômes : Poudre blanche feuilles/fleurs, perte 30-50% rendement
│  ├─ Traitement : Soufre mouillable 1% tous 10-14 jours (mai-juin)
│  ├─ Coût/traitement : 50-100 TND
│  └─ Total saison : 200-300 TND (4 traitements)
├─ Araignée rouge (si fruitiers) :
│  ├─ Période : Juillet-septembre (chaleur/sécheresse)
│  ├─ Traitement : Acaricide BIO ou chimique si détection
│  ├─ Coût : 50-80 TND/traitement, 2-3 traitements
│  └─ Total : 150-250 TND
├─ Zone légale [DÉLÉGATION] :
│  ├─ Si Gabès Ville : Phréatique INTERDITE, sondage >300m obligatoire
│  ├─ Si Gabès Ouest : Phréatique partiellement interdite, sondage >200m
│  ├─ Si Gabès Sud/El Hamma/Mareth : Autorisée, puits + sondage OK
│  └─ Permis DRE : Délai 2-4 semaines, coût 200-300 TND
└─ Pollution GCT (si Gabès Ville/Ouest) : SO2 500m, Agrumes non recommandées, revenu -20%

COMMENCE RAPPORT MAINTENANT."""
# ════════════════════════════════════════════════════════════════════════════════
# 2. CACHE SYSTEM - RÉDUIRE FICHIER LECTURES
# ════════════════════════════════════════════════════════════════════════════════

class CacheManager:
    """
    Gère un cache local en mémoire des données chargées.
    But : Éviter de relire les fichiers à chaque génération
    Stratégie : Cache-en-mémoire + Fichier .cache pour persistance
    """
    
    CACHE_FILE = ".cache/contexte_cache.json"
    CACHE_EXPIRY = timedelta(hours=24)  # Expire après 24h
    
    _instance = None
    _cache = {}
    _last_update = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_cache()
        return cls._instance
    
    def _init_cache(self):
        """Initialiser le cache (charger depuis disque si existe)"""
        os.makedirs(".cache", exist_ok=True)
        self._load_disk_cache()
    
    def _load_disk_cache(self):
        """Charger le cache depuis le disque si valide"""
        if os.path.exists(self.CACHE_FILE):
            try:
                with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    
                    timestamp = cache_data.get('timestamp')
                    if timestamp:
                        cache_time = datetime.fromisoformat(timestamp)
                        if datetime.now() - cache_time < self.CACHE_EXPIRY:
                            self._cache = cache_data.get('data', {})
                            print(f"✅ Cache disque chargé ({len(self._cache)} fichiers)")
                            return
                
                # Cache expiré
                os.remove(self.CACHE_FILE)
                print("⚠️ Cache expiré, rechargement depuis fichiers")
            except Exception as e:
                print(f"⚠️ Erreur lecture cache : {e}")
    
    def get(self, key: str) -> str or None:
        """Récupérer depuis cache mémoire"""
        return self._cache.get(key)
    
    def set(self, key: str, value: str):
        """Stocker en cache mémoire"""
        self._cache[key] = value
    
    def save_disk_cache(self):
        """Sauvegarder cache sur disque pour persistence"""
        try:
            with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'data': self._cache
                }, f, ensure_ascii=False, indent=2)
            print(f"✅ Cache disque sauvegardé ({len(self._cache)} fichiers)")
        except Exception as e:
            print(f"❌ Erreur sauvegarde cache : {e}")
    
    def clear(self):
        """Vider le cache"""
        self._cache.clear()
        if os.path.exists(self.CACHE_FILE):
            os.remove(self.CACHE_FILE)

# Instance globale du cache
_cache_manager = CacheManager()

# ════════════════════════════════════════════════════════════════════════════════
# 3. COMPRESSEURS - RÉDUIRE TOKENS SANS PERDRE QUALITÉ
# ════════════════════════════════════════════════════════════════════════════════

def compresser_regles_techniques(texte: str) -> str:
    """
    Transformer texte verbeux en format compact mais COMPLET
    
    2800 chars → 600 chars (75% réduction)
    
    AVANT:
    "A. Palmier Dattier (Deglet Nour / Alig)
       - Espacement : 8m x 8m (idéal) ou 10m x 10m.
       - Besoins en eau : 15 à 25 m³/arbre/an..."
    
    APRÈS:
    "PALMIER DATTIER: 8x8m (156/ha), 15-25 m³/an, sol sablonneux"
    """
    
    result = "\nPARAMÈTRES TECHNIQUES GABÈS :\n\n"
    
    # Parser sections
    sections = {
        "PALMIER": ["Palmier", "espacement", "eau"],
        "GRENADIER": ["Grenadier", "espacement", "eau"],
        "OLIVIER": ["Olivier", "espacement", "eau"],
    }
    
    lines = texte.split('\n')
    current_section = None
    section_data = []
    
    for line in lines:
        line = line.strip()
        
        # Détecter sections
        for section_name, keywords in sections.items():
            if any(kw.lower() in line.lower() for kw in keywords):
                if current_section and section_data:
                    result += f"{current_section}\n"
                    result += '\n'.join(section_data) + "\n\n"
                current_section = section_name
                section_data = []
                break
        
        # Extraire données clés
        if any(keyword in line for keyword in ["Espacement", "Eau", "Sol", "Profondeur"]):
            # Format compact
            section_data.append(f"  {line}")
    
    # Ajouter dernière section
    if current_section and section_data:
        result += f"{current_section}\n"
        result += '\n'.join(section_data)
    
    return result[:1200]  # Max 1200 chars

def compresser_reglementation(texte: str, delegation: str) -> str:
    """
    Créer tableau compact des zones au lieu de descriptions longues
    
    3000 chars → 500 chars (83% réduction)
    """
    
    # Table de référence comprimée
    zones_db = {
        "gabes_ville": "ZONE INTERDITE phréatique | Sondage >300m OBLIGATOIRE | Débit max 150-300 m³/j",
        "gabes_ouest": "ZONE INTERDITE phréatique partielle | Sondage >200m | Débit max 100-200 m³/j",
        "gabes_sud": "Zone AUTORISÉE | Puits + Sondage possible | Débit 300-500 m³/j | Meilleure salinité",
        "el_hamma": "Zone SENSIBLE | Sondage >300m obligatoire | Nappe profonde | Permis écrit requis",
        "metouia": "Zone AUTORISÉE historique | Puits + Sondage | Accès direct Sfax (export)",
        "mareth": "MEILLEURE ZONE hydro Gabès | Puits + Sondage OK | <50% exploitation",
        "matmata": "ZONE DIFFICILE | Sondage >400m rarement succès | Zone protégée (patrimoine)",
        "ghannouch": "Zone MODÉRÉE | Puits + Sondage | Débit 200-350 m³/j",
        "chenini": "Proche Métouia | Puits + Sondage possible",
        "kettana": "Proche Métouia | Puits + Sondage possible",
        "teboulbou": "Proche Métouia | Puits + Sondage possible",
        "oudhref": "Proche Métouia | Puits + Sondage possible",
        "chatt_essalem": "Proche Gabès Ouest | Phréatique partiellement interdite",
    }
    
    result = "\n=== RÉGLEMENTATION POUR VOTRE ZONE ===\n"
    
    # Zone cible
    zone_info = zones_db.get(delegation, "Zone non spécifiée - consulter DRE Gabès")
    result += f"\n{delegation.upper()} :\n"
    result += f"  {zone_info}\n"
    
    # Ajouter infos APIA (pertinent pour tous)
    result += "\n=== AIDES APIA DISPONIBLES (TOUS ZONES) ===\n"
    result += "  • Irrigation goutte-à-goutte : 50% du coût (max 5ha)\n"
    result += "  • Plantation arbres : 25-40 TND/plant\n"
    result += "  • Panneaux solaires : 60% du coût\n"
    result += "  • Formation gratuite CRDA : techniques, certifications BIO\n"
    
    return result

def compresser_stats(stats_dict: dict, preferences: list) -> str:
    """
    Extraire stats pour arbres préférés du client
    
    6000 chars JSON → 400 chars texte (93% réduction!)
    """
    
    result = "\n=== PRODUCTIONS RÉGIONALES 2023-2024 ===\n"
    
    try:
        if 'production_arboriculture_totale' in stats_dict:
            for item in stats_dict['production_arboriculture_totale']:
                if item.get('delegation') == "Total Gouvernorat" and item.get('annee') == 2024:
                    result += f"  Olivier : {item.get('oliviers_t', 0)} tonnes/an\n"
                    result += f"  Dattes : {item.get('dattes_t', 0)} tonnes/an\n"
                    result += f"  Grenades : {item.get('grenades_t', 0)} tonnes/an\n"
                    break
    except:
        pass
    
    return result

def compresser_alertes(alertes_dict: dict) -> str:
    """Extraire alertes critiques pour Gabès"""
    
    result = "\n=== ALERTES LÉGALES & ENVIRONNEMENTALES ===\n"
    
    try:
        if 'contexte_pdl_gabes_2023' in alertes_dict:
            ctx = alertes_dict['contexte_pdl_gabes_2023']
            
            if 'ressources_en_eau' in ctx:
                eau = ctx['ressources_en_eau']
                if 'nappe_profonde' in eau:
                    result += f"  ⚠️ Nappe profonde exploitation : 55.85% (critique)\n"
                if 'nappe_phreatique' in eau:
                    result += f"  ⚠️ Nappe phréatique ZONE INTERDICTION : Gabès Nord/Ouest\n"
            
            if 'menaces_et_pollutions' in ctx:
                result += f"  ⚠️ Pollution SO2 GCT : zone 500m impactée\n"
                result += f"  ⚠️ Fusariose palmier : pas de cure, éradication requise\n"
    except:
        pass
    
    return result

# ════════════════════════════════════════════════════════════════════════════════
# 4. OPTIMISEUR HYBRID - TOKENS INTELLIGENTS
# ════════════════════════════════════════════════════════════════════════════════

def estimer_tokens(texte: str) -> int:
    """Estimer tokens (1 token ≈ 4 caractères)"""
    return len(texte) // 4

def optimiser_contexte_hybrid(
    contexte: dict,
    agriculteur: DonneesTerrain,
    budget_tokens: int = 6500
) -> Tuple[str, int]:
    """
    Optimisation HYBRID : Toutes données + Comprimées intelligemment
    
    Budget allocation :
    - System prompt : 500 tokens
    - Données client : 500 tokens
    - Contexte comprimé : 6500 tokens ← NOTRE FOCUS
    - Marge réponse : 2000 tokens
    TOTAL = 9500 / 12000 ✅
    """
    
    print("\n⚡ OPTIMISATION HYBRID (Données complètes + Comprimées)")
    print(f"   Budget tokens : {budget_tokens}")
    
    prompt_contexte = ""
    tokens_utilisés = 0
    
    # ─────────────────────────────────────────────────────────────────
    # PARTIE 1 : RÈGLES TECHNIQUES COMPRIMÉES
    # ─────────────────────────────────────────────────────────────────
    
    if contexte['regles_techniques']:
        print(f"   📋 RÈGLES TECHNIQUES (comprimées)")
        
        # Vérifier cache
        cache_key = "regles_techniques_compressed"
        regles = _cache_manager.get(cache_key)
        
        if not regles:
            regles = compresser_regles_techniques(contexte['regles_techniques'])
            _cache_manager.set(cache_key, regles)
        
        tokens_regles = estimer_tokens(regles)
        if tokens_utilisés + tokens_regles < budget_tokens:
            prompt_contexte += regles
            tokens_utilisés += tokens_regles
            print(f"       ✓ {tokens_regles} tokens (cache: {'HIT' if cache_key in _cache_manager._cache else 'MISS'})")
    
    # ─────────────────────────────────────────────────────────────────
    # PARTIE 2 : RÉGLEMENTATION COMPRIMÉE
    # ─────────────────────────────────────────────────────────────────
    
    if contexte['reglementation_agricole']:
        print(f"   ⚖️ RÉGLEMENTATION (comprimée) - Zone {agriculteur.delegation}")
        
        # Vérifier cache
        cache_key = f"reglement_{agriculteur.delegation}"
        reglement = _cache_manager.get(cache_key)
        
        if not reglement:
            reglement = compresser_reglementation(
                contexte['reglementation_agricole'],
                agriculteur.delegation
            )
            _cache_manager.set(cache_key, reglement)
        
        tokens_reglement = estimer_tokens(reglement)
        if tokens_utilisés + tokens_reglement < budget_tokens:
            prompt_contexte += reglement
            tokens_utilisés += tokens_reglement
            print(f"       ✓ {tokens_reglement} tokens (cache: {'HIT' if cache_key in _cache_manager._cache else 'MISS'})")
    
    # ─────────────────────────────────────────────────────────────────
    # PARTIE 3 : STATS COMPRIMÉES
    # ─────────────────────────────────────────────────────────────────
    
    if contexte['stats_agricoles'] and tokens_utilisés < budget_tokens - 500:
        print(f"   📊 STATS (comprimées)")
        
        cache_key = "stats_agricoles_compressed"
        stats = _cache_manager.get(cache_key)
        
        if not stats:
            stats = compresser_stats(contexte['stats_agricoles'], agriculteur.preferences)
            _cache_manager.set(cache_key, stats)
        
        tokens_stats = estimer_tokens(stats)
        if tokens_utilisés + tokens_stats < budget_tokens:
            prompt_contexte += stats
            tokens_utilisés += tokens_stats
            print(f"       ✓ {tokens_stats} tokens (cache: {'HIT' if cache_key in _cache_manager._cache else 'MISS'})")
    
    # ─────────────────────────────────────────────────────────────────
    # PARTIE 4 : ALERTES COMPRIMÉES
    # ─────────────────────────────────────────────────────────────────
    
    if contexte['alertes_et_lois'] and tokens_utilisés < budget_tokens - 300:
        print(f"   ⚠️ ALERTES (comprimées)")
        
        cache_key = "alertes_compressed"
        alertes = _cache_manager.get(cache_key)
        
        if not alertes:
            alertes = compresser_alertes(contexte['alertes_et_lois'])
            _cache_manager.set(cache_key, alertes)
        
        tokens_alertes = estimer_tokens(alertes)
        if tokens_utilisés + tokens_alertes < budget_tokens:
            prompt_contexte += alertes
            tokens_utilisés += tokens_alertes
            print(f"       ✓ {tokens_alertes} tokens (cache: {'HIT' if cache_key in _cache_manager._cache else 'MISS'})")
    
    # Sauvegarder cache disque
    _cache_manager.save_disk_cache()
    
    print(f"\n   ✅ TOTAL CONTEXTE OPTIMISÉ : {tokens_utilisés} tokens")
    
    return prompt_contexte, tokens_utilisés

# ════════════════════════════════════════════════════════════════════════════════
# 5. PIPELINE PRINCIPAL - GROQ OPTIMISÉ
# ════════════════════════════════════════════════════════════════════════════════

def executer_generation_rapport(payload_frontend) -> str:
    """
    Pipeline complet : Cache + Compression + Hybrid tokens + Groq
    """
    
    print("\n" + "="*80)
    print("🚀 DÉMARRAGE GÉNÉRATION RAPPORT")
    print("   Stratégie : Cache + Compression + Hybrid Tokens")
    print("="*80)
    
    try:
        # ✅ ÉTAPE 1 : Parser données
        print("\n📋 ÉTAPE 1 : Parsing données...")
        agriculteur = DonneesTerrain(payload_frontend)
        print(f"   ✓ {agriculteur.delegation} | {agriculteur.surface_m2} m²")
        print(f"   ✓ Sol: {agriculteur.sol} | Eau: {agriculteur.eau}")
        print(f"   ✓ Budget: {agriculteur.budget}")
        
        tokens_client = estimer_tokens(agriculteur.formatted_for_ai())
        print(f"   Tokens données client : {tokens_client}")
        
        # ✅ ÉTAPE 2 : Charger contexte
        print("\n📁 ÉTAPE 2 : Chargement contexte local...")
        try:
            contexte = charger_contexte_local()
        except FileNotFoundError as e:
            return f"ERREUR : {str(e)}"
        
        # ✅ ÉTAPE 3 : OPTIMISATION HYBRID + CACHE
        print("\n⚡ ÉTAPE 3 : Optimisation hybrid + cache...")
        contexte_optimise, tokens_contexte = optimiser_contexte_hybrid(
            contexte=contexte,
            agriculteur=agriculteur,
            budget_tokens=6500
        )
        
        # ✅ ÉTAPE 4 : Construire prompt final
        print("\n🎯 ÉTAPE 4 : Construction prompt utilisateur...")
        prompt_utilisateur = f"""DONNÉES CLIENT À ANALYSER :
═══════════════════════════════════════════════════
Délégation : {agriculteur.delegation}
Surface : {agriculteur.surface_m2} m² ({agriculteur.surface_m2/10000:.2f} ha)
Dimensions : {agriculteur.dimensions}
Sol : {agriculteur.sol}
Eau : {agriculteur.eau}
Budget : {agriculteur.budget}
Arbres existants : {agriculteur.arbres_existants}
Objectif : {agriculteur.objectif}
Préférences : {', '.join(agriculteur.preferences) if agriculteur.preferences else 'Aucune'}
Problème : {agriculteur.probleme}

CONTEXTE RÉFÉRENCE (OPTIMISÉ) :
═══════════════════════════════════════════════════
{contexte_optimise}

INSTRUCTIONS FINALES :
═══════════════════════════════════════════════════
1. Génère rapport en 6 sections comme défini
2. Utilise UNIQUEMENT données client + contexte fourni
3. CHIFFRES PRÉCIS : espacements, budgets, rendements
4. CALENDRIER MENSUEL année 1
5. Citations officielles (Code Eaux, PDL, CRDA, APIA)
6. Respecte STRICTEMENT budget {agriculteur.budget}
"""
        
        # Estimations finales
        tokens_system = estimer_tokens(SYSTEM_PROMPT)
        tokens_user = estimer_tokens(prompt_utilisateur)
        tokens_total = tokens_system + tokens_user
        
        print(f"   ✓ Tokens système : {tokens_system}")
        print(f"   ✓ Tokens utilisateur : {tokens_user}")
        print(f"   ✓ TOTAL : {tokens_total} / 12000")
        print(f"   ✓ Marge sécurité : {12000 - tokens_total} tokens")
        
        if tokens_total > 10000:
            print(f"   ⚠️ ATTENTION : Approche de limite (>10k)")
        
        # ✅ ÉTAPE 5 : Appel Groq
        print("\n🤖 ÉTAPE 5 : Appel Groq (tokens optimisés)...")
        
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt_utilisateur}
                ],
                model=MODEL_NAME,
                temperature=0.2,  # Précis
                max_tokens=4000,  # Limiter réponse
                top_p=0.95
            )
            
            rapport = chat_completion.choices[0].message.content
            print(f"   ✓ Rapport généré ({len(rapport)} caractères)")
        
        except Exception as e:
            error_msg = str(e)
            if "413" in error_msg or "rate_limit" in error_msg:
                print(f"   ❌ ERREUR TOKENS : {error_msg[:100]}")
                return f"ERREUR TOKENS : Requête trop grande. {error_msg}"
            else:
                print(f"   ❌ ERREUR API : {e}")
                return f"ERREUR API : {str(e)}"
        
        # ✅ ÉTAPE 6 : Nettoyage
        print("\n🧹 ÉTAPE 6 : Nettoyage rapport...")
        rapport_propre = nettoyer_rapport(rapport)
        
        print("\n" + "="*80)
        print("✅ GÉNÉRATION COMPLÈTE - RAPPORT PRÊT À L'EXPORT")
        print("="*80 + "\n")
        
        return rapport_propre
    
    except Exception as e:
        print(f"\n❌ ERREUR CRITIQUE : {str(e)}")
        import traceback
        traceback.print_exc()
        return f"ERREUR : {str(e)}"

def nettoyer_rapport(texte: str) -> str:
    """Nettoyage final PDF-safe"""
    # Supprimer caractères non-latin
    texte = re.sub(r'[^\x00-\x7F\xA0-\xFF]', '', texte)
    
    # Normaliser espaces
    texte = re.sub(r'\n{3,}', '\n\n', texte)
    
    # Supprimer caractères de contrôle
    texte = ''.join(char for char in texte if ord(char) >= 32 or char in '\n\t')
    
    return texte.strip()
##Version Optimisé mais sans lire data###
# from settings.config import (
#     client, 
#     MODEL_NAME, 
#     DonneesTerrain, 
#     charger_contexte_local,
#     formatter_contexte_pour_prompt
# )
# import re
# import json

# # ============================================================
# # SYSTEM PROMPT OPTIMISÉ
# # ============================================================
# SYSTEM_PROMPT = """Tu es un INGÉNIEUR AGRONOME EXPERT spécialisé dans la région de Gabès (Tunisie).
# Ton rôle : Analyser le terrain d'un agriculteur et générer un RAPPORT DE RECOMMANDATION structuré et précis.

# CONSIGNES ABSOLUES :

# 1. 🔒 FIDÉLITÉ AUX DONNÉES CLIENT
#    - Utilise EXACTEMENT le type de sol déclaré
#    - Utilise EXACTEMENT la source d'eau déclarée
#    - Adapte les recommandations à son budget réel

# 2. 📊 SOURCES FIABLES
#    - Cite : Code des Eaux tunisien, PDL Gabès, CRDA, APIA
#    - Jamais de chiffres sans source
#    - Format professionnel (pas de noms fichiers)

# 3. 🎯 STRUCTURE 6 SECTIONS
#    - SECTION 1 : DIAGNOSTIC PÉDOLOGIQUE ET HYDROLOGIQUE
#    - SECTION 2 : ITINÉRAIRE TECHNIQUE ET PLANTATION
#    - SECTION 3 : PLAN HYDRIQUE OPTIMISÉ
#    - SECTION 4 : ALERTES ENVIRONNEMENTALES ET LÉGALES
#    - SECTION 5 : PLAN BUDGÉTAIRE DÉTAILLÉ
#    - SECTION 6 : CONSEILS PRATIQUES

# 4. ❌ INTERDITS
#    - Pas d'arabe, pas d'emoji
#    - Pas d'invention de chiffres
#    - Pas de cultures hors Gabès
#    - Budget : max +20% du budget client

# Génère un rapport actionnable et détaillé.
# """

# # ============================================================
# # FONCTIONS D'OPTIMISATION TOKENS - CORE SOLUTION
# # ============================================================

# def estimer_tokens(texte: str) -> int:
#     """
#     Estime le nombre de tokens (approximation : 1 token ≈ 4 caractères)
#     Groq limite : 12 000 TPM, nous restons à 8 500 max pour marge sécurité
#     """
#     return len(texte) // 4

# def extraire_section_reglementation(reglementation: str, delegation: str) -> str:
#     """
#     Extrait SEULEMENT la section pertinente pour la délégation.
#     Réduit de ~3000 à ~400 caractères
#     """
    
#     # Mapping délégation -> section clé
#     mapping_delegation = {
#         "gabes_ville": "Gabès Ville (Médina)",
#         "gabes_ouest": "Gabès Ouest",
#         "gabes_sud": "Gabès Sud",
#         "el_hamma": "El Hamma et El Hamma Ouest",
#         "metouia": "Métouia et Oudhref",
#         "mareth": "Mareth",
#         "matmata": "Matmata",
#         "ghannouch": "Ghannouch",
#         "chenini": "Métouia et Oudhref",
#         "kettana": "Métouia et Oudhref",
#         "teboulbou": "Métouia et Oudhref",
#         "oudhref": "Métouia et Oudhref",
#         "chatt_essalem": "Gabès Ouest"
#     }
    
#     section_cible = mapping_delegation.get(delegation, "")
    
#     # Extraire uniquement la section pertinente
#     lignes = reglementation.split('\n')
#     resultat = []
#     capture = False
    
#     for i, ligne in enumerate(lignes):
#         # Début section
#         if section_cible in ligne:
#             capture = True
#             resultat.append("\n=== RÉGLEMENTATION POUR VOTRE ZONE ===")
#             resultat.append(ligne)
#             # Ajouter les 15 lignes suivantes (info zone)
#             for j in range(i+1, min(i+15, len(lignes))):
#                 resultat.append(lignes[j])
#             break
    
#     # Si pas de section trouvée, ajouter résumé APIA
#     if not resultat:
#         resultat.append("\n=== AIDE APIA DISPONIBLE ===")
#         for ligne in lignes:
#             if "APIA" in ligne or "subvention" in ligne.lower():
#                 resultat.append(ligne)
#                 if len(resultat) > 10:
#                     break
    
#     return '\n'.join(resultat[:20])  # Max 20 lignes

# def extraire_regles_techniques_par_sol(regles: str, sol: str) -> str:
#     """
#     Extrait uniquement les règles pertinentes pour le type de sol.
#     Réduit de ~2800 à ~600 caractères
#     """
    
#     # Extraire section pertinente au sol
#     lignes = regles.split('\n')
#     resultat = []
    
#     # Trouver la section du sol
#     for i, ligne in enumerate(lignes):
#         if sol.lower() in ligne.lower():
#             resultat.append(ligne)
#             # Ajouter les 10 lignes suivantes
#             for j in range(i+1, min(i+10, len(lignes))):
#                 resultat.append(lignes[j])
#             break
    
#     # Si sol exact pas trouvé, ajouter infos générales
#     if not resultat:
#         resultat.append("\n=== INFOS SOL GÉNÉRALE ===")
#         for ligne in lignes[:30]:
#             if "sol" in ligne.lower() or "espacement" in ligne.lower():
#                 resultat.append(ligne)
    
#     return '\n'.join(resultat[:15])  # Max 15 lignes

# def extraire_stats_production(stats: dict, preferences: list) -> str:
#     """
#     Extrait SEULEMENT les stats pour les arbres préférés du client.
#     Réduit drastiquement le payload JSON
#     """
    
#     resume = "\n=== PRODUCTIONS RÉGIONALES POUR VOS ARBRES ===\n"
    
#     # Arbres préférés
#     arbres_cibles = [
#         pref.lower() for pref in preferences
#     ] if preferences else []
    
#     try:
#         # Production arboriculture
#         if 'production_arboriculture_totale' in stats:
#             for item in stats['production_arboriculture_totale']:
#                 if item.get('delegation') == "Total Gouvernorat":
#                     if not arbres_cibles or any(arbre in ["palmier", "datte"] for arbre in arbres_cibles):
#                         resume += f"  - Dattes : {item.get('dattes_t', 0)} tonnes/an\n"
#                     if not arbres_cibles or any(arbre in ["grenadier"] for arbre in arbres_cibles):
#                         resume += f"  - Grenades : {item.get('grenades_t', 0)} tonnes/an\n"
#                     if not arbres_cibles or any(arbre in ["olivier"] for arbre in arbres_cibles):
#                         resume += f"  - Olivier : {item.get('oliviers_t', 0)} tonnes/an\n"
#     except:
#         pass
    
#     return resume

# def optimiser_contexte_intelligent(
#     contexte: dict, 
#     agriculteur: DonneesTerrain,
#     budget_tokens: int = 3000
# ) -> str:
#     """
#     Découpe intelligemment le contexte en chunks pertinents.
#     STRATÉGIE : 
#     - Charger SEULEMENT ce qui est pertinent pour le client
#     - Délégation + Sol + Eau + Préférences
    
#     Budget tokens allocation:
#     - System prompt : ~500 tokens
#     - Données client : ~500 tokens
#     - Contexte intelligent : ~2500 tokens
#     - Marge réponse : ~2000 tokens
#     TOTAL = ~5500 / 12000 ✅
#     """
    
#     print("\n⚡ OPTIMISATION INTELLIGENTE TOKENS")
#     print(f"   Budget disponible : {budget_tokens} tokens")
    
#     prompt_contexte = ""
#     tokens_utilisés = 0
    
#     # ─────────────────────────────────────────────────────────
#     # PARTIE 1 : RÈGLES TECHNIQUES (PERTINENTES AU SOL)
#     # ─────────────────────────────────────────────────────────
    
#     if contexte['regles_techniques']:
#         print(f"   📋 Extraction RÈGLES TECHNIQUES pour sol: {agriculteur.sol}")
#         regles_filtrées = extraire_regles_techniques_par_sol(
#             contexte['regles_techniques'],
#             agriculteur.sol
#         )
#         tokens_regles = estimer_tokens(regles_filtrées)
        
#         if tokens_utilisés + tokens_regles < budget_tokens:
#             prompt_contexte += "\n=== PARAMÈTRES TECHNIQUES ESSENTIELS ===\n"
#             prompt_contexte += regles_filtrées
#             tokens_utilisés += tokens_regles
#             print(f"       ✓ {tokens_regles} tokens")
    
#     # ─────────────────────────────────────────────────────────
#     # PARTIE 2 : RÉGLEMENTATION (PERTINENTE À LA DÉLÉGATION)
#     # ─────────────────────────────────────────────────────────
    
#     if contexte['reglementation_agricole']:
#         print(f"   ⚖️ Extraction RÉGLEMENTATION pour {agriculteur.delegation}")
#         reglement_filtre = extraire_section_reglementation(
#             contexte['reglementation_agricole'],
#             agriculteur.delegation
#         )
#         tokens_reglement = estimer_tokens(reglement_filtre)
        
#         if tokens_utilisés + tokens_reglement < budget_tokens:
#             prompt_contexte += "\n" + reglement_filtre
#             tokens_utilisés += tokens_reglement
#             print(f"       ✓ {tokens_reglement} tokens")
    
#     # ─────────────────────────────────────────────────────────
#     # PARTIE 3 : STATS PRODUCTION (POUR ARBRES PRÉFÉRÉS)
#     # ─────────────────────────────────────────────────────────
    
#     if contexte['stats_agricoles'] and tokens_utilisés < budget_tokens - 300:
#         print(f"   📊 Extraction STATS pour arbres préférés")
#         stats_filtrées = extraire_stats_production(
#             contexte['stats_agricoles'],
#             agriculteur.preferences
#         )
#         tokens_stats = estimer_tokens(stats_filtrées)
        
#         if tokens_utilisés + tokens_stats < budget_tokens:
#             prompt_contexte += stats_filtrées
#             tokens_utilisés += tokens_stats
#             print(f"       ✓ {tokens_stats} tokens")
    
#     # ─────────────────────────────────────────────────────────
#     # PARTIE 4 : ALERTES LÉGALES (CRITIQUES)
#     # ─────────────────────────────────────────────────────────
    
#     if contexte['alertes_et_lois'] and tokens_utilisés < budget_tokens - 200:
#         print(f"   ⚠️ Ajout ALERTES LÉGALES")
        
#         try:
#             alertes = json.dumps(contexte['alertes_et_lois'], indent=2, ensure_ascii=False)[:400]
#             tokens_alertes = estimer_tokens(alertes)
            
#             if tokens_utilisés + tokens_alertes < budget_tokens:
#                 prompt_contexte += "\n=== ALERTES LÉGALES IMPORTANTES ===\n"
#                 prompt_contexte += alertes
#                 tokens_utilisés += tokens_alertes
#                 print(f"       ✓ {tokens_alertes} tokens")
#         except:
#             pass
    
#     print(f"\n   ✅ TOTAL CONTEXTE OPTIMISÉ : {tokens_utilisés} tokens")
    
#     return prompt_contexte

# # ============================================================
# # PIPELINE PRINCIPAL - GROQ OPTIMISÉ
# # ============================================================

# def executer_generation_rapport(payload_frontend):
#     """
#     Pipeline avec CHUNKING INTELLIGENT des données
#     """
    
#     print("\n" + "="*80)
#     print("🚀 DÉMARRAGE GÉNÉRATION RAPPORT (Groq - Optimisé Tokens)")
#     print("="*80)
    
#     try:
#         # ✅ ÉTAPE 1 : Parser données
#         print("\n📋 ÉTAPE 1 : Parsing données...")
#         agriculteur = DonneesTerrain(payload_frontend)
#         print(f"   ✓ {agriculteur.delegation}")
#         print(f"   ✓ {agriculteur.surface_m2} m² | Sol: {agriculteur.sol}")
#         print(f"   ✓ Eau: {agriculteur.eau} | Budget: {agriculteur.budget}")
        
#         tokens_client = estimer_tokens(agriculteur.formatted_for_ai())
#         print(f"   ✓ Tokens données client : {tokens_client}")
        
#         # ✅ ÉTAPE 2 : Charger contexte
#         print("\n📁 ÉTAPE 2 : Chargement contexte local...")
#         try:
#             contexte = charger_contexte_local()
#         except FileNotFoundError as e:
#             return f"ERREUR : {str(e)}"
        
#         # ✅ ÉTAPE 3 : OPTIMISATION INTELLIGENTE (CLÉE)
#         print("\n⚡ ÉTAPE 3 : Optimisation intelligente contexte...")
#         contexte_optimise = optimiser_contexte_intelligent(
#             contexte=contexte,
#             agriculteur=agriculteur,
#             budget_tokens=3500
#         )
        
#         tokens_contexte = estimer_tokens(contexte_optimise)
        
#         # ✅ ÉTAPE 4 : Construire prompt final
#         print("\n🎯 ÉTAPE 4 : Construction prompt utilisateur...")
#         prompt_utilisateur = f"""DONNÉES CLIENT À ANALYSER :
# Délégation : {agriculteur.delegation}
# Surface : {agriculteur.surface_m2} m²
# Sol : {agriculteur.sol}
# Eau : {agriculteur.eau}
# Budget : {agriculteur.budget}
# Arbres existants : {agriculteur.arbres_existants}
# Objectif : {agriculteur.objectif}
# Préférences arbres : {', '.join(agriculteur.preferences) if agriculteur.preferences else 'Aucune'}
# Problème : {agriculteur.probleme}

# CONTEXTE RÉFÉRENCE (OPTIMISÉ) :
# {contexte_optimise}

# INSTRUCTIONS :
# 1. Génère un rapport en 6 sections
# 2. Utilise EXCLUSIVEMENT les données fournies
# 3. Cite les sources officielles (Code des eaux, CRDA, APIA, PDL)
# 4. Sois précis sur les chiffres (espacements, budgets, rendements)
# 5. Adapte à la délégation {agriculteur.delegation}
# 6. Respecte le budget {agriculteur.budget}
# """
        
#         # Estimations finales
#         tokens_system = estimer_tokens(SYSTEM_PROMPT)
#         tokens_user = estimer_tokens(prompt_utilisateur)
#         tokens_total = tokens_system + tokens_user
        
#         print(f"   ✓ Tokens système : {tokens_system}")
#         print(f"   ✓ Tokens utilisateur : {tokens_user}")
#         print(f"   ✓ TOTAL : {tokens_total} / 12000")
#         print(f"   ✓ Marge sécurité : {12000 - tokens_total} tokens")
        
#         if tokens_total > 10000:
#             print(f"   ⚠️ ATTENTION : Approche de limite, réduction recommandée")
        
#         # ✅ ÉTAPE 5 : Appel Groq
#         print("\n🤖 ÉTAPE 5 : Appel Groq (optimisé)...")
        
#         try:
#             chat_completion = client.chat.completions.create(
#                 messages=[
#                     {"role": "system", "content": SYSTEM_PROMPT},
#                     {"role": "user", "content": prompt_utilisateur}
#                 ],
#                 model=MODEL_NAME,
#                 temperature=0.2,
#                 max_tokens=4500,  
#                 top_p=0.95
#             )
            
#             rapport = chat_completion.choices[0].message.content
#             print(f"   ✓ Rapport généré ({len(rapport)} caractères)")
        
#         except Exception as e:
#             error_msg = str(e)
#             if "413" in error_msg or "rate_limit" in error_msg:
#                 print(f"   ❌ ERREUR TOKENS : {error_msg}")
#                 return f"ERREUR TOKENS : {error_msg}"
#             else:
#                 print(f"   ❌ ERREUR API : {e}")
#                 return f"ERREUR : {str(e)}"
        
#         # ✅ ÉTAPE 6 : Nettoyage
#         print("\n🧹 ÉTAPE 6 : Nettoyage rapport...")
#         rapport_propre = nettoyer_rapport(rapport)
        
#         print("\n" + "="*80)
#         print("✅ GÉNÉRATION COMPLÈTE - RAPPORT PRÊT")
#         print("="*80 + "\n")
        
#         return rapport_propre
    
#     except Exception as e:
#         print(f"\n❌ ERREUR CRITIQUE : {str(e)}")
#         import traceback
#         traceback.print_exc()
#         return f"ERREUR : {str(e)}"

# def nettoyer_rapport(texte):
#     """Nettoyage final PDF-safe"""
#     texte = re.sub(r'[^\x00-\x7F\xA0-\xFF]', '', texte)
#     texte = re.sub(r'\n{3,}', '\n\n', texte)
#     texte = ''.join(char for char in texte if ord(char) >= 32 or char in '\n\t')
#     return texte.strip()
# from settings.config import (
#     client, 
#     MODEL_NAME, 
#     DonneesTerrain, 
#     charger_contexte_local,
#     formatter_contexte_pour_prompt
# )

# # ============================================================
# # SYSTEM PROMPT RENFORCÉ - FORCE LE MODÈLE À UTILISER LES DONNÉES
# # ============================================================
# SYSTEM_PROMPT = """Tu es un INGÉNIEUR AGRONOME EXPERT spécialisé dans la région de Gabès (Tunisie).
# Ton rôle : Analyser le terrain d'un agriculteur et générer un RAPPORT DE RECOMMANDATION structuré et précis.

# ╔════════════════════════════════════════════════════════════════════════════════╗
# ║ CONSIGNES ABSOLUES - RESPECTER SCRUPULEUSEMENT OU RAPPORT INVALIDE             ║
# ╚════════════════════════════════════════════════════════════════════════════════╝

# 1. 🔒 FIDÉLITÉ AUX DONNÉES CLIENT
#    ├─ Utilise EXACTEMENT le type de sol déclaré (ne l'invente JAMAIS).
#    ├─ Utilise EXACTEMENT la source d'eau déclarée (pas de "Séguia" si le client dit "Sondage").
#    ├─ Utilise EXACTEMENT la surface, dimensions et objectif du client.
#    └─ Adapte les recommandations à son budget réel.

# 2. 📊 UTILISATION OBLIGATOIRE DES DONNÉES LOCALES
#    ├─ Tu disposes de 3 sources de vérité :
#    │  ├─ STATS_AGRICOLES : Productions réelles Gabès 2023-2024 (superficies, rendements)
#    │  ├─ ALERTES_LÉGALES : Code des eaux, règles foncières, pollutions (PDL 2023)
#    │  └─ RÈGLES_TECHNIQUES : Paramètres précis (espacements, besoins eau, nutriments)
#    ├─ CITATION OBLIGATOIRE : Si tu recommandes un espaceur ou un rendement, cite la source.
#    ├─ EXEMPLE BON : "Selon la base locale, le Grenadier Gabsi en 4x5m produit..."
#    └─ EXEMPLE MAUVAIS : "Le Grenadier typiquement produit..." (vague, pas de source)

# 3. 🎯 STRUCTURE EXIGÉE DU RAPPORT
#    Respecte SCRUPULEUSEMENT cette hiérarchie :
   
#    📋 RAPPORT DE RECOMMANDATION AGRICOLE
   
#    SECTION 1 : DIAGNOSTIC PÉDOLOGIQUE ET HYDROLOGIQUE
#    ├─ Analyse du type de sol déclaré (propriétés physiques)
#    ├─ Recommandations d'amendement (compost, gypse, etc.)
#    ├─ Analyse de la source d'eau (capacité, salinité, risques)
#    └─ Conclusion : "TERRAIN ADAPTÉ À..." ou "TERRAIN NÉCESSITE PRÉPARATION..."
   
#    SECTION 2 : ITINÉRAIRE TECHNIQUE ET PLANTATION (Système 3 étages)
#    ├─ ÉTAGE 1 - PALMIER DATTIER
#    │  ├─ Variété conseillée (Deglet Nour, Alig, etc.)
#    │  ├─ Espacement exact (ex: 8x8m = 156 plants/ha)
#    │  ├─ Besoins en eau (m³/arbre/an et m³/ha/an)
#    │  ├─ Profondeur de forage requise
#    │  └─ Coût estimé par plant
#    ├─ ÉTAGE 2 - ARBRES FRUITIERS
#    │  ├─ Variété conseillée (basée sur préférences ET zone)
#    │  ├─ Espacement exact
#    │  ├─ Rendement estimé (kg/arbre à maturité)
#    │  ├─ Cycle de production (années avant rentabilité)
#    │  └─ Coût estimé par plant
#    └─ ÉTAGE 3 - SOUS-CULTURES
#       ├─ Variété recommandée (Luzerne, Henné, Maraîchage)
#       ├─ Calendrier de semis et récolte
#       ├─ Rendement estimé
#       └─ Rotation des cultures
   
#    SECTION 3 : PLAN HYDRIQUE OPTIMISÉ
#    ├─ Débit total nécessaire (m³/jour en été, en hiver)
#    ├─ Système d'irrigation recommandé (Goutte-à-goutte obligatoire)
#    ├─ Risques hydriques (Tarissement, salinité, nappe interdite)
#    └─ Conformité légale (Code des eaux 1975 + PDL 2035)
   
#    SECTION 4 : ALERTES ENVIRONNEMENTALES ET LÉGALES (GABÈS)
#    ├─ Alertes spécifiques à la délégation du client
#    ├─ Risques sanitaires (Fusariose, araignée rouge, etc.)
#    ├─ Restrictions légales (Zones d'interdiction de forage, AFA)
#    └─ Pollution GCT et impacts agricoles
   
#    SECTION 5 : PLAN BUDGÉTAIRE DÉTAILLÉ
#    ├─ INSTALLATION (Année 1)
#    │  ├─ Préparation du sol : X TND
#    │  ├─ Plants (palmier, fruitiers) : X TND
#    │  ├─ Système d'irrigation : X TND
#    │  └─ Main d'œuvre : X TND
#    ├─ ENTRETIEN ANNUEL (Années 2-5)
#    │  ├─ Fertilisation : X TND/an
#    │  ├─ Traitement phytosanitaire : X TND/an
#    │  └─ Eau d'irrigation : X TND/an
#    └─ RENTABILITÉ
#       ├─ Rendement cumulé à 3 ans
#       ├─ Rendement cumulé à 5 ans
#       └─ Point d'équilibre (Break-even)
   
#    SECTION 6 : CONSEILS PRATIQUES POUR L'AGRICULTEUR
#    ├─ Étapes mensuelles année 1 (Préparation → Plantation → Premiers soins)
#    ├─ Calendrier d'entretien (Taille, fertilisation, irrigation)
#    ├─ Sources de financement (Subventions APIA, crédit rural)
#    └─ Contacts locaux (Centres techniques, Coopératives)

# 4. ⚖️ TRANSPARENCE ET FIABILITÉ (SOURCING)
#    ├─ Ta mission est d'être transparent SANS avoir l'air d'un robot.
#    ├─ INTERDICTION ABSOLUE de citer des noms de fichiers (ex: ne dis jamais "Source: agriculture.json" ou "fichier.txt").
#    ├─ OBLIGATION de citer l'institution ou le document légal. Utilise des formules professionnelles comme :
#       - "Conformément au Code des Eaux tunisien..."
#       - "Selon les directives du CRDA de Gabès..."
#       - "D'après les statistiques agricoles régionales (APIA)..."
#       - "Comme stipulé dans le Plan de Développement Local (PDL)..."

# 5. ❌ INTERDITS ABSOLUS (Penalty si violé)
#    ├─ ❌ Ignorer le type de sol du client
#    ├─ ❌ Recommander une source d'eau différente de celle déclarée
#    ├─ ❌ Inventer des chiffres sans source
#    ├─ ❌ Utiliser de l'arabe ou des emojis
#    ├─ ❌ Dépasser le budget du client de > 20%
#    ├─ ❌ Recommander des cultures hors zone Gabès
#    └─ ❌ Oublier les alertes légales (Code des eaux, AFA)

# ════════════════════════════════════════════════════════════════════════════════

# COMMENCEZ LE RAPPORT MAINTENANT AVEC LA DATE DU JOUR.
# """

# def executer_generation_rapport(payload_frontend):
#     """
#     Pipeline complet de génération du rapport avec données locales forcées
    
#     Args:
#         payload_frontend (dict) : Données du formulaire HTML
        
#     Returns:
#         str : Rapport texte généré par Llama 3.3
#     """
    
#     print("\n" + "="*80)
#     print("🚀 DÉMARRAGE DE LA GÉNÉRATION DU RAPPORT")
#     print("="*80)
    
#     # ✅ ÉTAPE 1 : Parser les données du formulaire
#     print("\n📋 ÉTAPE 1 : Parsing des données du formulaire...")
#     agriculteur = DonneesTerrain(payload_frontend)
#     print(f"   ✓ Agriculteur de {agriculteur.delegation}")
#     print(f"   ✓ Surface : {agriculteur.surface_m2} m²")
#     print(f"   ✓ Sol : {agriculteur.sol} | Eau : {agriculteur.eau}")
    
#     # ✅ ÉTAPE 2 : Charger le contexte local
#     print("\n📁 ÉTAPE 2 : Chargement du contexte local depuis /data...")
#     try:
#         contexte = charger_contexte_local()
#     except FileNotFoundError as e:
#         print(f"   ❌ ERREUR CRITIQUE : {e}")
#         return f"ERREUR : Impossible de charger les données locales.\n{str(e)}"
    
#     # ✅ ÉTAPE 3 : Formatter le contexte
#     print("\n📊 ÉTAPE 3 : Formatage du contexte pour le prompt...")
#     contexte_formate = formatter_contexte_pour_prompt(contexte)
#     print(f"   ✓ Contexte formaté ({len(contexte_formate)} caractères)")
    
#     # ✅ ÉTAPE 4 : Construire le prompt utilisateur
#     print("\n🎯 ÉTAPE 4 : Construction du prompt utilisateur...")
#     prompt_utilisateur = f"""DONNÉES CLIENT À ANALYSER :
# {agriculteur.formatted_for_ai()}

# CONTEXTE DE RÉFÉRENCE GABÈS 2023-2024 (UTILISATION OBLIGATOIRE) :
# {contexte_formate}

# INSTRUCTION FINALE :
# Génère un rapport structuré en 6 sections comme défini dans mes instructions système.
# Utilise UNIQUEMENT le type de sol, la source d'eau et les données du client.
# Cite les sources des chiffres que tu donnes (agriculture.json, diagnostic.json, gabes_data.txt).
# Assure-toi que chaque recommandation est adaptée à la délégation {agriculteur.delegation}.
# """
#     print(f"   ✓ Prompt utilisateur construit ({len(prompt_utilisateur)} caractères)")
    
#     # ✅ ÉTAPE 5 : Appel au modèle Llama 3.3
#     print("\n🤖 ÉTAPE 5 : Appel au modèle Llama 3.3-70B (Groq)...")
#     print(f"   ⏳ Génération en cours... (cela peut prendre 30-60 secondes)")
    
#     try:
#         chat_completion = client.chat.completions.create(
#             messages=[
#                 {
#                     "role": "system",
#                     "content": SYSTEM_PROMPT
#                 },
#                 {
#                     "role": "user",
#                     "content": prompt_utilisateur
#                 }
#             ],
#             model=MODEL_NAME,
#             temperature=0.2,  # Basse température pour plus de cohérence
#             max_tokens=4000,  # Limite pour le rapport
#             top_p=0.95
#         )
        
#         rapport = chat_completion.choices[0].message.content
#         print(f"   ✓ Rapport généré ({len(rapport)} caractères)")
        
#     except Exception as e:
#         print(f"   ❌ ERREUR API : {e}")
#         return f"ERREUR LORS DE L'APPEL AU MODÈLE : {str(e)}"
    
#     # ✅ ÉTAPE 6 : Nettoyage post-traitement
#     print("\n🧹 ÉTAPE 6 : Nettoyage et validation du rapport...")
#     rapport_propre = nettoyer_rapport(rapport)
#     print(f"   ✓ Rapport nettoyé et validé")
    
#     print("\n" + "="*80)
#     print("✅ GÉNÉRATION COMPLÈTE - RAPPORT PRÊT À L'EXPORT")
#     print("="*80 + "\n")
    
#     return rapport_propre

# def nettoyer_rapport(texte):
#     """Supprime les caractères problématiques pour l'export PDF"""
#     # Supprime les caractères non-latin (emojis, arabe)
#     import re
    
#     # Supprime les emojis
#     texte = re.sub(r'[^\x00-\x7F\xA0-\xFF]', '', texte)
    
#     # Normalise les espaces multiples
#     texte = re.sub(r'\n{3,}', '\n\n', texte)
    
#     # Supprime les caractères de contrôle
#     texte = ''.join(char for char in texte if ord(char) >= 32 or char in '\n\t')
    
#     return texte.strip()
