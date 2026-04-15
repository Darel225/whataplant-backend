"""
routes/home.py — Statistiques Dashboard
=========================================
GET /api/home/stats/{user_id}
"""

from fastapi           import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from datetime          import datetime
from database          import get_connection

router = APIRouter()


@router.get("/home/stats/{user_id}")
async def stats_home(user_id: int):
    """
    Retourne toutes les données pour le HomeScreen :
    - Nom de l'utilisateur
    - Total scans
    - Alertes santé (is_healthy = 0)
    - Jours sans alerte
    - Dernier scan complet
    - Historique récent (3 derniers)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:

            # Nom utilisateur
            cursor.execute(
                "SELECT nom FROM users WHERE id = %s", (user_id,)
            )
            user = cursor.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="Utilisateur introuvable")

            # Total scans
            cursor.execute(
                "SELECT COUNT(*) as total FROM scans WHERE user_id = %s",
                (user_id,)
            )
            total_scans = cursor.fetchone()["total"]

            # Alertes santé
            cursor.execute(
                "SELECT COUNT(*) as alertes FROM scans WHERE user_id = %s AND is_healthy = 0",
                (user_id,)
            )
            alertes = cursor.fetchone()["alertes"]

            # Jours sans alerte
            cursor.execute("""
                SELECT created_at FROM scans
                WHERE user_id = %s AND is_healthy = 0
                ORDER BY created_at DESC LIMIT 1
            """, (user_id,))
            derniere_alerte = cursor.fetchone()

            if derniere_alerte:
                delta = datetime.now() - derniere_alerte["created_at"]
                jours_sans_alerte = delta.days
            else:
                jours_sans_alerte = 0

            # Dernier scan
            cursor.execute("""
                SELECT id, nom_scientifique, nom_local, statut,
                       is_healthy, alert_details, image_url,
                       score_confiance, created_at
                FROM scans WHERE user_id = %s
                ORDER BY created_at DESC LIMIT 1
            """, (user_id,))
            dernier_scan = cursor.fetchone()

            # Historique récent (3 derniers)
            cursor.execute("""
                SELECT id, nom_scientifique, nom_local, statut,
                       is_healthy, image_url, created_at
                FROM scans WHERE user_id = %s
                ORDER BY created_at DESC LIMIT 3
            """, (user_id,))
            historique = cursor.fetchall()

        # Formate les dates
        def fmt(dt):
            if not dt: return None
            if isinstance(dt, str): return dt
            now   = datetime.now()
            delta = now - dt
            if delta.days == 0:
                return f"Aujourd'hui, {dt.strftime('%H:%M')}"
            elif delta.days == 1:
                return f"Hier, {dt.strftime('%H:%M')}"
            else:
                return dt.strftime("%d/%m/%Y %H:%M")

        if dernier_scan:
            dernier_scan["created_at"] = fmt(dernier_scan["created_at"])
        for h in historique:
            h["created_at"] = fmt(h["created_at"])

        return JSONResponse(content={
            "user_name"        : user["nom"],
            "total_scans"      : total_scans,
            "alertes_sante"    : alertes,
            "jours_sans_alerte": jours_sans_alerte,
            "dernier_scan"     : dernier_scan,
            "historique"       : historique,
        })
    finally:
        conn.close()