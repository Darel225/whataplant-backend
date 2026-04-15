"""
routes/diagnostic.py — Endpoint principal du diagnostic
=========================================================
POST /diagnostic-complet

Pipeline :
  1. Prétraitement OpenCV
  2. Identification PlantNet
  3. ✅ Vérification du score → si < 30% : STOP, rien n'est sauvegardé
  4. Analyse IA Groq (seulement si score >= 30%)
  5. Sauvegarde image (seulement si score >= 30%)
  6. Persistance MySQL (seulement si score >= 30%)
  7. Retourne le JSON
"""

from fastapi           import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic          import BaseModel
from typing            import Optional
import traceback
import json
import os
import uuid
from datetime import datetime

from services.opencv_service   import pretraiter_depuis_bytes
from services.plantnet_service import identifier_plante
from services.groq_service     import analyser_plante
from database                  import sauvegarder_scan, get_stats_utilisateur, get_historique
from config                    import UPLOAD_DIR

router = APIRouter()

# ============================================================
# SEUILS DE CONFIANCE
# ============================================================
SEUIL_BLOQUE   = 0.30   # < 30%  → rien n'est sauvegardé, retourne erreur
SEUIL_PRUDENCE = 0.60   # 30-60% → sauvegarde + avertissement au frontend
                         # > 60%  → sauvegarde normale


# ============================================================
# FONCTION DE SAUVEGARDE D'IMAGE
# Appelée UNIQUEMENT si le score est suffisant
# ============================================================
def sauvegarder_image(image_bytes: bytes, user_id: int = None) -> str:
    """
    Sauvegarde l'image originale et retourne son chemin relatif.
    N'est appelée que si score >= SEUIL_BLOQUE.
    """
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    user_part = f"user_{user_id}" if user_id else "anonymous"
    filename  = f"scan_{user_part}_{timestamp}_{unique_id}.jpg"
    filepath  = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(image_bytes)

    url_path = filepath.replace("\\", "/")
    print(f"      Image sauvegardée : {url_path}")
    return url_path


# ============================================================
# MODELE POUR REQUETE BASE64
# ============================================================
class RequeteBase64(BaseModel):
    image   : str
    user_id : Optional[int] = None


# ============================================================
# ENDPOINT — UPLOAD FICHIER
# ============================================================
@router.post("/diagnostic-complet")
async def diagnostic_complet(
    image   : UploadFile = File(...),
    user_id : Optional[int] = Form(None)
):
    try:
        image_bytes = await image.read()
        return await _pipeline_diagnostic(image_bytes, user_id)
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur serveur : {str(e)}")


# ============================================================
# ENDPOINT — BASE64 (React Native caméra)
# ============================================================
@router.post("/diagnostic-complet/base64")
async def diagnostic_complet_base64(requete: RequeteBase64):
    try:
        return await _pipeline_base64(requete.image, requete.user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur serveur : {str(e)}")


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================
async def _pipeline_diagnostic(image_bytes_bruts: bytes, user_id: int = None):

    # ---- ETAPE 1 : Prétraitement OpenCV ----
    print("  [1/4] Prétraitement OpenCV...")
    try:
        image_traitee = pretraiter_depuis_bytes(image_bytes_bruts)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # ---- ETAPE 2 : Identification PlantNet ----
    print("  [2/4] Identification PlantNet...")
    try:
        infos_plantnet  = identifier_plante(image_traitee)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    nom_scientifique = infos_plantnet["nom_scientifique"]
    score_confiance  = infos_plantnet["score"]
    score_pct        = round(score_confiance * 100, 1)
    print(f"      → {nom_scientifique} ({score_pct}%)")

    # ---- ETAPE 3 : VÉRIFICATION DU SEUIL ----
    # Si score < 30% → on arrête ICI.
    # Ni l'image ni la DB ne sont touchées.
    if score_confiance < SEUIL_BLOQUE:
        print(f"  ⛔ Score {score_pct}% < {SEUIL_BLOQUE*100:.0f}% → REJETÉ, rien sauvegardé")
        return JSONResponse(
            status_code=200,
            content={
                "succes"           : False,
                "score_insuffisant": True,
                "plante": {
                    "score_confiance": score_pct,
                    "seuil_minimum"  : SEUIL_BLOQUE * 100,
                },
                "message": (
                    f"Score de confiance trop bas ({score_pct}%). "
                    f"Minimum requis : {SEUIL_BLOQUE*100:.0f}%. "
                    f"Veuillez reprendre une meilleure photo."
                )
            }
        )

    # Score suffisant (>= 30%) — on continue
    niveau = "prudence" if score_confiance < SEUIL_PRUDENCE else "fiable"
    print(f"  ✅ Score {score_pct}% accepté — niveau : {niveau}")

    # ---- ETAPE 4a : Analyse IA Groq ----
    print("  [3/4] Analyse IA Groq...")
    infos_ia              = analyser_plante(nom_scientifique, image_traitee)
    infos_complementaires = infos_ia.get("informations_complementaires", {})

    # ---- ETAPE 4b : Sauvegarde image + MySQL ----
    print("  [4/4] Sauvegarde image + MySQL...")
    image_url = sauvegarder_image(image_bytes_bruts, user_id)

    scan_id = sauvegarder_scan({
        "user_id"           : user_id,
        "nom_scientifique"  : nom_scientifique,
        "nom_local"         : infos_ia.get("noms_locaux"),
        "famille"           : infos_plantnet.get("famille"),
        "statut"            : infos_ia.get("statut_securite"),
        "is_healthy"        : infos_ia.get("is_healthy", True),
        "alert_details"     : infos_ia.get("alert_details"),
        "usages"            : json.dumps(
                                  infos_ia.get("usages", []),
                                  ensure_ascii=False
                              ),
        "mode_utilisation"  : infos_ia.get("mode_utilisation"),
        "parties_utilisees" : infos_complementaires.get("parties_utilisees"),
        "precautions"       : infos_complementaires.get("precautions"),
        "contre_indications": infos_complementaires.get("contre_indications"),
        "image_url"         : image_url,
        "score_confiance"   : score_confiance,
    })

    stats = get_stats_utilisateur(user_id)

    return JSONResponse(content={
        "succes"           : True,
        "scan_id"          : scan_id,
        "niveau_confiance" : niveau,

        "plante": {
            "nom_scientifique": nom_scientifique,
            "nom_commun"      : infos_plantnet.get("nom_commun"),
            "noms_locaux"     : infos_ia.get("noms_locaux"),
            "famille"         : infos_plantnet.get("famille"),
            "score_confiance" : score_pct,
        },
        "sante": {
            "is_healthy"   : infos_ia.get("is_healthy", True),
            "statut"       : infos_ia.get("statut"),
            "alert_details": infos_ia.get("alert_details"),
        },
        "securite": {
            "statut_securite": infos_ia.get("statut_securite"),
            "toxique"        : infos_ia.get("toxique", False),
            "info_toxicite"  : infos_ia.get("info_toxicite"),
        },
        "usages": {
            "liste"             : infos_ia.get("usages", []),
            "mode_utilisation"  : infos_ia.get("mode_utilisation"),
            "parties_utilisees" : infos_complementaires.get("parties_utilisees"),
            "precautions"       : infos_complementaires.get("precautions"),
            "contre_indications": infos_complementaires.get("contre_indications"),
        },
        "image_url": image_url,
        "dashboard": {
            "total_scans"  : stats["total_scans"],
            "total_alertes": stats["total_alertes"],
        }
    })


async def _pipeline_base64(image_base64: str, user_id: int = None):
    import base64 as b64
    if "," in image_base64:
        image_base64 = image_base64.split(",")[1]
    image_bytes = b64.b64decode(image_base64)
    return await _pipeline_diagnostic(image_bytes, user_id)


# ============================================================
# ENDPOINT HISTORIQUE
# ============================================================
@router.get("/historique")
async def historique(user_id: Optional[int] = None, limite: int = 10):
    scans = get_historique(user_id, limite)
    return JSONResponse(content={"scans": scans, "total": len(scans)})


# ============================================================
# ENDPOINT STATS
# ============================================================
@router.get("/stats")
async def stats_dashboard(user_id: Optional[int] = None):
    stats = get_stats_utilisateur(user_id)
    return JSONResponse(content=stats)