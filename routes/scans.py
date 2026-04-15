"""
routes/scans.py — Endpoints Bibliothèque
==========================================
GET /api/scans/{user_id}        → Liste des scans d'un utilisateur
GET /api/scans/detail/{scan_id} → Détail d'un scan
"""

from fastapi           import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from typing            import Optional
import json
from database          import get_connection

router = APIRouter()


# ============================================================
# LISTE DES SCANS D'UN UTILISATEUR (pour la Bibliothèque)
# ============================================================
@router.get("/scans/{user_id}")
async def liste_scans(user_id: int, limite: int = 50):
    """
    Retourne tous les scans d'un utilisateur
    pour afficher la bibliothèque.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    id,
                    nom_scientifique,
                    nom_local,
                    famille,
                    statut,
                    is_healthy,
                    alert_details,
                    image_url,
                    score_confiance,
                    created_at
                FROM scans
                WHERE user_id = %s OR user_id IS NULL
                ORDER BY created_at DESC
                LIMIT %s
            """, (user_id, limite))
            scans = cursor.fetchall()

        # Formate les dates
        for s in scans:
            if s.get("created_at"):
                s["created_at"] = s["created_at"].strftime("%d/%m/%Y %H:%M")

        return JSONResponse(content={
            "scans": scans,
            "total": len(scans)
        })
    finally:
        conn.close()


# ============================================================
# DETAIL D'UN SCAN (pour DiagnosticScreen)
# ============================================================
@router.get("/scans/detail/{scan_id}")
async def detail_scan(scan_id: int):
    """
    Retourne le détail complet d'un scan.
    Utilisé quand on clique sur une plante dans la bibliothèque.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM scans WHERE id = %s", (scan_id,))
            scan = cursor.fetchone()

        if not scan:
            raise HTTPException(status_code=404, detail="Scan introuvable")

        # Formate la date
        if scan.get("created_at"):
            scan["created_at"] = scan["created_at"].strftime("%d/%m/%Y %H:%M")

        # Parse les usages (stockés en JSON)
        if scan.get("usages") and isinstance(scan["usages"], str):
            try:
                scan["usages"] = json.loads(scan["usages"])
            except:
                scan["usages"] = []

        return JSONResponse(content={"scan": scan})
    finally:
        conn.close()