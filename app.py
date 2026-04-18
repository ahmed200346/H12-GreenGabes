####Version download rapport dans pc directement####
from flask import Flask, request, jsonify, render_template, send_file
from Models.generateur_rapportGroq import executer_generation_rapport
from utils.export_pdf import generer_pdf_rapport
import os
from datetime import datetime
app = Flask(__name__, template_folder='templates')

@app.route('/')
def index():
    """Page d'accueil avec formulaire"""
    return render_template('formulaire_terrainVfinale.html')



@app.route('/api/generate-report', methods=['POST'])
def handle_form():
    """
    Route principale : Reçoit les données du formulaire, génère le rapport
    """
    
    print("\n" + "="*80)
    print("📩 REQUÊTE REÇUE - /api/generate-report")
    print("="*80)
    
    try:
        # 1. Récupérer les données JSON du frontend
        data = request.json
        
        if not data:
            return jsonify({
                "status": "error",
                "message": "Aucune donnée reçue"
            }), 400
        
        delegation = data.get('delegation', 'Gabes')
        print(f"✅ Données reçues : {delegation} | {data.get('surface_m2')} m²")
        
        # 2. Générer le rapport avec l'IA (+ données locales)
        print("\n🤖 Appel du générateur de rapport...")
        rapport_texte = executer_generation_rapport(data)
        
        if not rapport_texte or rapport_texte.startswith("ERREUR"):
            return jsonify({
                "status": "error",
                "message": rapport_texte
            }), 500
        
        # 3. Générer le PDF
        print("\n📄 Génération du PDF...")
        
        # Nom du fichier propre et lisible pour l'utilisateur
        date_rapport = datetime.now().strftime('%Y%m%d')
        nom_fichier_propre = f"Rapport_{delegation}_{date_rapport}.pdf"
        
        pdf_path = generer_pdf_rapport(rapport_texte, delegation)
        
        if not pdf_path:
            return jsonify({
                "status": "error",
                "message": "Erreur lors de la génération du PDF"
            }), 500
        
        # 4. Obtenir le nom du fichier généré
        nom_fichier_genere = os.path.basename(pdf_path)
        
        # 5. Retourner la réponse au frontend
        print("\n✅ SUCCÈS - Réponse envoyée au frontend")
        print("="*80 + "\n")
        
        return jsonify({
            "status": "success",
            "report_text": rapport_texte,
            "pdf_url": f"/download-rapport/{nom_fichier_genere}",
            "pdf_filename": nom_fichier_genere,
            "delegation": delegation,
            "timestamp": datetime.now().isoformat()
        }), 200
    
    except Exception as e:
        print(f"\n❌ ERREUR NON ATTENDUE : {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"Erreur serveur : {str(e)}"
        }), 500

@app.route('/download-rapport/<filename>', methods=['GET'])
def download_rapport(filename):
    """
    Route pour télécharger le PDF généré
    Les en-têtes HTTP forcent le navigateur à télécharger au lieu d'afficher
    """
    try:
        chemin_fichier = os.path.join('rapports', filename)
        
        # Vérifier que le fichier existe
        if not os.path.exists(chemin_fichier):
            return jsonify({"error": "Fichier non trouvé"}), 404
        
        # Générer un nom de fichier propre pour le téléchargement
        nom_fichier_telechargement = filename
        
        # 🔑 CLÉS : Ces en-têtes forcent le téléchargement
        return send_file(
            chemin_fichier,
            as_attachment=True,  # ✅ Force le téléchargement
            download_name=nom_fichier_telechargement,  # ✅ Nom affiché
            mimetype='application/pdf'  # ✅ Type MIME correct
        )
    except Exception as e:
        print(f"❌ Erreur téléchargement : {e}")
        return jsonify({"error": str(e)}), 500



@app.errorhandler(404)
def page_not_found(e):
    return jsonify({"error": "Page non trouvée"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Erreur interne du serveur"}), 500

if __name__ == '__main__':
    # Créer le dossier 'rapports' s'il n'existe pas
    if not os.path.exists('rapports'):
        os.makedirs('rapports')
    
    print("\n🚀 Démarrage du serveur Flask...")
    print("📍 Adresse : http://localhost:5000")
    print("📁 Dossier /data requis à la racine du projet")
    print("🔐 Variables d'environnement : GROQ_API_KEY dans .env\n")
    
    app.run(debug=True, host='localhost', port=5000)


 ####--Version telechargement rapport dans dossier rapports--####   

# from flask import Flask, request, jsonify, render_template, send_file
# from Models.generateur_rapport import executer_generation_rapport
# from utils.export_pdf import generer_pdf_rapport
# import os

# app = Flask(__name__, template_folder='templates')

# @app.route('/')
# def index():
#     """Page d'accueil avec formulaire"""
#     return render_template('formulaire_terrainVfinale.html')

# @app.route('/api/generate-report', methods=['POST'])
# def handle_form():
#     """
#     Route principale : Reçoit les données du formulaire, génère le rapport
#     """
    
#     print("\n" + "="*80)
#     print("📩 REQUÊTE REÇUE - /api/generate-report")
#     print("="*80)
    
#     try:
#         # 1. Récupérer les données JSON du frontend
#         data = request.json
        
#         if not data:
#             return jsonify({
#                 "status": "error",
#                 "message": "Aucune donnée reçue"
#             }), 400
        
#         print(f"✅ Données reçues : {data.get('delegation')} | {data.get('surface_m2')} m²")
        
#         # 2. Générer le rapport avec l'IA (+ données locales)
#         print("\n🤖 Appel du générateur de rapport...")
#         rapport_texte = executer_generation_rapport(data)
        
#         if not rapport_texte or rapport_texte.startswith("ERREUR"):
#             return jsonify({
#                 "status": "error",
#                 "message": rapport_texte
#             }), 500
        
#         # 3. Générer le PDF
#         print("\n📄 Génération du PDF...")
#         delegation = data.get('delegation', 'Gabes')
#         pdf_path = generer_pdf_rapport(rapport_texte, f"{delegation}")
        
#         if not pdf_path:
#             return jsonify({
#                 "status": "error",
#                 "message": "Erreur lors de la génération du PDF"
#             }), 500
        
#         # 4. Retourner la réponse au frontend
#         print("\n✅ SUCCÈS - Réponse envoyée au frontend")
#         print("="*80 + "\n")
        
#         return jsonify({
#             "status": "success",
#             "report_text": rapport_texte,
#             "pdf_url": f"/download-rapport/{os.path.basename(pdf_path)}",
#             "pdf_filename": os.path.basename(pdf_path)
#         }), 200
    
#     except Exception as e:
#         print(f"\n❌ ERREUR NON ATTENDUE : {str(e)}")
#         return jsonify({
#             "status": "error",
#             "message": f"Erreur serveur : {str(e)}"
#         }), 500

# @app.route('/download-rapport/<filename>', methods=['GET'])
# def download_rapport(filename):
#     """Route pour télécharger le PDF généré"""
#     try:
#         chemin_fichier = os.path.join('rapports', filename)
        
#         if not os.path.exists(chemin_fichier):
#             return jsonify({"error": "Fichier non trouvé"}), 404
        
#         return send_file(
#             chemin_fichier,
#             as_attachment=True,
#             download_name=filename,
#             mimetype='application/pdf'
#         )
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# @app.errorhandler(404)
# def page_not_found(e):
#     return jsonify({"error": "Page non trouvée"}), 404

# @app.errorhandler(500)
# def internal_error(e):
#     return jsonify({"error": "Erreur interne du serveur"}), 500

# if __name__ == '__main__':
#     # Créer le dossier 'rapports' s'il n'existe pas
#     if not os.path.exists('rapports'):
#         os.makedirs('rapports')
    
#     print("\n🚀 Démarrage du serveur Flask...")
#     print("📍 Adresse : http://localhost:5000")
#     print("📁 Dossier /data requis à la racine du projet")
#     print("🔐 Variables d'environnement : GROQ_API_KEY dans .env\n")
    
#     app.run(debug=True, host='localhost', port=5000)
