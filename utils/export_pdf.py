from fpdf import FPDF
from datetime import datetime
import os
import re

class RapportPDFGreenGabes:
    """
    Classe pour générer des rapports PDF professionnels pour Green Gabes
    Design : Vert (couleur principale), blanc (fond), gris (texte)
    Logo : 🌴 Green Gabes
    """
    
    def __init__(self):
        self.pdf = FPDF()
        self.pdf.set_auto_page_break(auto=True, margin=15)
        
        # Palette de couleurs Green Gabes
        self.couleur_primaire = (75, 199, 20)      # Vert éclatant #4BC714
        self.couleur_secondaire = (48, 136, 13)    # Vert foncé #308809
        self.couleur_accent = (99, 206, 51)        # Vert clair #63CE33
        self.couleur_border = (26, 90, 15)         # Vert très foncé #1A5A0F
        self.couleur_texte = (50, 50, 50)          # Gris foncé
        self.couleur_muted = (120, 120, 120)       # Gris clair
        self.couleur_fond = (245, 250, 245)        # Blanc crème très léger
        
        self.largeur_page = self.pdf.w
        self.hauteur_page = self.pdf.h
        self.margin = 15
        self.largeur_util = self.largeur_page - (2 * self.margin)
        
        # Ajouter la première page
        self.pdf.add_page()
        self.pdf.set_auto_page_break(auto=True, margin=self.margin)
    
    def ajouter_logo_entete(self):
        """Ajoute le logo et en-tête Green Gabes avec design professionnel"""
        
        # Fond rectangle vert dégradé (simulation avec rectangle)
        self.pdf.set_fill_color(*self.couleur_primaire)
        self.pdf.rect(0, 0, self.largeur_page, 45, 'F')
        
        # Bordure accent haut
        self.pdf.set_draw_color(*self.couleur_secondaire)
        self.pdf.set_line_width(3)
        self.pdf.line(0, 45, self.largeur_page, 45)
        
        # Logo avec emoji et titre
        self.pdf.set_y(8)
        self.pdf.set_x(self.margin)
        self.pdf.set_font("Helvetica", 'B', 24)
        self.pdf.set_text_color(255, 255, 255)  # Blanc sur fond vert
        
        # Logo (emoji datte + texte)
        logo_text = "Green Gabes"
        self.pdf.cell(0, 12, logo_text, ln=True, align='C')
        
        # Sous-titre
        self.pdf.set_font("Helvetica", '', 11)
        self.pdf.set_text_color(220, 255, 220)  # Vert très clair
        self.pdf.cell(0, 6, "Rapport de Recommandation Agricole", ln=True, align='C')
        
        # Espace après en-tête
        self.pdf.set_y(50)
    
    def ajouter_info_rapport(self, delegation, date_rapport):
        """Ajoute les infos du rapport (métadonnées)"""
        
        # Cadre info léger
        self.pdf.set_draw_color(*self.couleur_border)
        self.pdf.set_line_width(0.5)
        self.pdf.rect(self.margin, self.pdf.get_y(), self.largeur_util, 20)
        
        # Infos texte
        self.pdf.set_font("Helvetica", '', 9)
        self.pdf.set_text_color(*self.couleur_muted)
        
        y_info = self.pdf.get_y() + 3
        self.pdf.set_xy(self.margin + 3, y_info)
        self.pdf.cell(50, 4, f"Delegation : {delegation}", ln=False)
        
        self.pdf.set_xy(self.largeur_page / 2, y_info)
        self.pdf.cell(0, 4, f"Date : {date_rapport}", ln=True)
        
        self.pdf.set_xy(self.margin + 3, y_info + 6)
        self.pdf.cell(0, 4, "Gouvernorat : Gabes, Tunisie", ln=True)
        
        self.pdf.set_y(self.pdf.get_y() + 5)
    
    def ajouter_section(self, titre_section):
        """Ajoute un titre de section avec style professionnel"""
        
        # Espace avant section
        self.pdf.ln(3)
        
        # Ligne verte au-dessus du titre
        self.pdf.set_draw_color(*self.couleur_primaire)
        self.pdf.set_line_width(2)
        y_ligne = self.pdf.get_y()
        self.pdf.line(self.margin, y_ligne, self.largeur_page - self.margin, y_ligne)
        
        # Titre section avec fond légèrement teinté
        self.pdf.set_fill_color(245, 252, 245)  # Fond très clair
        self.pdf.set_font("Helvetica", 'B', 12)
        self.pdf.set_text_color(*self.couleur_secondaire)
        self.pdf.set_y(y_ligne + 2)
        self.pdf.set_x(self.margin)
        
        # Nettoyer titre (enlever "SECTION X :")
        titre_propre = re.sub(r'^SECTION\s+\d+\s*:\s*', '', titre_section, flags=re.IGNORECASE).strip()
        
        # Ajouter titre dans une cellule avec padding
        self.pdf.multi_cell(
            self.largeur_util, 
            6, 
            titre_propre, 
            border=0,
            align='L',
            fill=False
        )
        
        # Ligne vert clair sous titre
        self.pdf.set_draw_color(*self.couleur_accent)
        self.pdf.set_line_width(1)
        y_apres = self.pdf.get_y()
        self.pdf.line(self.margin, y_apres - 1, self.largeur_page - self.margin, y_apres - 1)
        
        self.pdf.set_y(y_apres + 2)
    
    def ajouter_contenu(self, texte_rapport):
        """Ajoute le contenu structuré du rapport"""
        
        # Nettoyer le texte
        texte_propre = self._nettoyer_texte_complet(texte_rapport)
        
        # Extraire les sections
        sections = self._extraire_sections(texte_propre)
        
        for titre_section, contenu_section in sections:
            # Ajouter titre section (avec style)
            self.ajouter_section(titre_section)
            
            # Traiter le contenu (listes, paragraphes)
            contenu_formate = self._formater_contenu(contenu_section)
            
            # Ajouter texte contenu
            self.pdf.set_font("Helvetica", '', 10)
            self.pdf.set_text_color(*self.couleur_texte)
            
            self.pdf.multi_cell(self.largeur_util, 5, txt=contenu_formate, align='L')
            
            # Espace entre sections
            self.pdf.ln(2)
            
            # Vérifier si on a besoin d'une nouvelle page
            if self.pdf.get_y() > self.hauteur_page - 30:
                self.pdf.add_page()
                self._ajouter_header_page_suivante()
    
    def _ajouter_header_page_suivante(self):
        """Ajoute un petit header aux pages suivantes"""
        self.pdf.set_font("Helvetica", 'I', 9)
        self.pdf.set_text_color(*self.couleur_muted)
        self.pdf.cell(0, 5, "Green Gabes - Rapport de Recommandation", ln=True, align='C')
        self.pdf.ln(2)
    
    def ajouter_pied_de_page(self):
        """Ajoute un pied de page professionnel"""
        
        # Espace avant
        self.pdf.ln(5)
        
        # Ligne vert foncé
        self.pdf.set_draw_color(*self.couleur_border)
        self.pdf.set_line_width(1)
        y_ligne = self.pdf.get_y()
        self.pdf.line(self.margin, y_ligne, self.largeur_page - self.margin, y_ligne)
        
        self.pdf.ln(3)
        
        # Texte pied de page
        self.pdf.set_font("Helvetica", 'I', 8)
        self.pdf.set_text_color(*self.couleur_muted)
        
        texte_pied = (
            "Green Gabes - Systeme Intelligent de Recommandation Agricole\n"
            "Gouvernorat de Gabes, Tunisie | "
            f"Genere le {datetime.now().strftime('%d/%m/%Y a %H:%M')}\n"
            "Tous droits reserves - Donnees confidentielles agriculteur"
        )
        
        self.pdf.multi_cell(self.largeur_util, 3, txt=texte_pied, align='C')
    
    def _nettoyer_texte_complet(self, texte):
        """Nettoyage COMPLET du texte pour FPDF2"""
        
        # Remplacer les puces
        texte = texte.replace('•', '-')
        texte = texte.replace('◦', '-')
        texte = texte.replace('○', '-')
        texte = texte.replace('●', '*')
        
        # Remplacer accents problématiques
        accents = {
            'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
            'à': 'a', 'â': 'a', 'ä': 'a',
            'ù': 'u', 'û': 'u', 'ü': 'u',
            'ô': 'o', 'ö': 'o',
            'ç': 'c',
            'î': 'i', 'ï': 'i',
            'œ': 'oe', 'æ': 'ae'
        }
        
        for accent, replacement in accents.items():
            texte = texte.replace(accent, replacement)
        
        # Garder seulement caractères Latin-1
        texte_propre = ''
        for char in texte:
            code = ord(char)
            if code <= 255 or char in '\n\t ':
                texte_propre += char
            else:
                if not char.isspace():
                    texte_propre += ' '
        
        texte = texte_propre
        
        # Supprimer balises Markdown
        texte = re.sub(r'^#+\s+', '', texte, flags=re.MULTILINE)
        texte = re.sub(r'\*\*(.+?)\*\*', r'\1', texte)
        texte = re.sub(r'__(.+?)__', r'\1', texte)
        texte = re.sub(r'\*(.+?)\*', r'\1', texte)
        texte = re.sub(r'_(.+?)_', r'\1', texte)
        texte = re.sub(r'`(.+?)`', r'\1', texte)
        texte = re.sub(r'\[(.+?)\]\(.*?\)', r'\1', texte)
        
        # Normaliser espaces
        texte = re.sub(r' +', ' ', texte)
        texte = re.sub(r'\n{3,}', '\n\n', texte)
        texte = '\n'.join(line.strip() for line in texte.split('\n'))
        
        # Encodage final
        try:
            texte.encode('latin-1')
        except UnicodeEncodeError:
            texte = texte.encode('latin-1', 'ignore').decode('latin-1')
        
        return texte.strip()
    
    def _formater_contenu(self, texte):
        """Formate le contenu avec meilleure présentation"""
        
        lignes = texte.split('\n')
        contenu_formate = []
        
        for ligne in lignes:
            ligne = ligne.strip()
            if not ligne:
                contenu_formate.append('')  # Garder les lignes vides
            elif ligne.startswith('-') or ligne.startswith('•'):
                # Reformater les puces avec indentation
                contenu_formate.append('  ' + ligne)
            elif ligne.startswith('*'):
                contenu_formate.append('  * ' + ligne[1:].strip())
            else:
                contenu_formate.append(ligne)
        
        return '\n'.join(contenu_formate)
    
    def _extraire_sections(self, texte):
        """Extrait les sections du rapport"""
        sections = []
        
        # Pattern pour détecter les titres de section (§1, §2, etc.)
        # Accepte aussi les formats "SECTION 1 :" ou "1. TITRE"
        pattern = r'(?:§|SECTION\s+|^|\n)(?:\d+[\.:]\s+)?(.+?)(?=(?:§|SECTION\s+\d+|^|\n)\d+[\.:]\s+|$)'
        
        # Alternative : chercher SECTION X : format
        pattern_section = r'(SECTION\s+\d+\s*:.*?)(?=SECTION\s+\d+|$)'
        matches = re.finditer(pattern_section, texte, re.IGNORECASE | re.DOTALL)
        
        for match in matches:
            contenu_complet = match.group(1)
            lignes = contenu_complet.split('\n')
            titre = lignes[0].strip()
            contenu = '\n'.join(lignes[1:]).strip()
            
            if titre and contenu:  # Vérifier que titre et contenu ne sont pas vides
                sections.append((titre, contenu))
        
        # Si pas de sections trouvées, utiliser tout le texte
        if not sections:
            # Essayer de trouver les titres avec § ou numérotation
            lignes = texte.split('\n')
            titre_courant = ""
            contenu_courant = ""
            
            for ligne in lignes:
                if ligne.strip().startswith('§') or re.match(r'^\d+[\.:]\s+', ligne.strip()):
                    # C'est un nouveau titre
                    if titre_courant and contenu_courant:
                        sections.append((titre_courant, contenu_courant))
                    titre_courant = ligne.strip()
                    contenu_courant = ""
                else:
                    # C'est du contenu
                    if titre_courant:
                        contenu_courant += ligne + '\n'
            
            # Ajouter la dernière section
            if titre_courant and contenu_courant:
                sections.append((titre_courant, contenu_courant.strip()))
        
        # Si toujours rien, créer une section par défaut
        if not sections:
            sections.append(("Rapport Detaille", texte))
        
        return sections
    
    def generer_fichier(self, nom_fichier=None):
        """Génère le fichier PDF final"""
        
        if nom_fichier is None:
            nom_fichier = f"rapport_green_gabes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Créer dossier 'rapports'
        dossier = 'rapports'
        if not os.path.exists(dossier):
            os.makedirs(dossier)
        
        chemin_complet = os.path.join(dossier, nom_fichier)
        
        try:
            self.pdf.output(chemin_complet)
            print(f"✅ PDF Green Gabes genere : {chemin_complet}")
            return chemin_complet
        except Exception as e:
            print(f"❌ Erreur generation PDF : {e}")
            return None

def generer_pdf_rapport(contenu_ia, delegation="Gabes"):
    """
    Fonction principale pour générer un rapport PDF Green Gabes
    
    Args:
        contenu_ia (str) : Contenu du rapport généré par Groq
        delegation (str) : Nom de la délégation (pour le fichier)
        
    Returns:
        str : Chemin du fichier PDF généré
    """
    
    print("\n" + "="*80)
    print("📄 GÉNÉRATION DU PDF - GREEN GABES")
    print("="*80)
    
    try:
        # Créer instance rapport
        rapport = RapportPDFGreenGabes()
        
        # Construire le rapport
        rapport.ajouter_logo_entete()
        rapport.ajouter_info_rapport(
            delegation=delegation,
            date_rapport=datetime.now().strftime('%d/%m/%Y')
        )
        rapport.ajouter_contenu(contenu_ia)
        rapport.ajouter_pied_de_page()
        
        # Générer le fichier
        nom_fichier = f"Rapport_{delegation}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        chemin_pdf = rapport.generer_fichier(nom_fichier)
        
        if chemin_pdf:
            print("✅ PDF genere avec succes!")
            print(f"📁 Chemin : {chemin_pdf}")
        
        return chemin_pdf
        
    except Exception as e:
        print(f"❌ ERREUR GENERATION PDF : {e}")
        import traceback
        traceback.print_exc()
        return None
