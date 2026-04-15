"""
routes/chat.py — Endpoints du Chat IA contextuel
==================================================
POST /chat/new-session  → Crée une session avec contexte plante
POST /chat/send         → Envoie un message et reçoit la réponse IA
GET  /chat/sessions/:id → Historique des sessions utilisateur
GET  /chat/messages/:id → Messages d'une session
"""

from fastapi           import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic          import BaseModel
from typing            import Optional
import requests
import traceback
from datetime          import datetime, date

from config import GROQ_API_KEY, GROQ_URL
from database import get_connection

router = APIRouter()


# ============================================================
# MODELES PYDANTIC
# ============================================================
class NouvelleSession(BaseModel):
    user_id    : Optional[int] = None
    nom_plante : Optional[str] = None
    diagnostic : Optional[str] = None


class EnvoiMessage(BaseModel):
    session_id : int
    contenu    : str
    user_id    : Optional[int] = None


# ============================================================
# CREATION DES TABLES CHAT
# ============================================================
def creer_tables_chat():
    sql_sessions = """
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        user_id     INT          NULL,
        titre       VARCHAR(200) NOT NULL DEFAULT 'Nouvelle conversation',
        nom_plante  VARCHAR(200) NULL,
        diagnostic  VARCHAR(200) NULL,
        system_prompt TEXT       NULL,
        created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
        updated_at  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    sql_messages = """
    CREATE TABLE IF NOT EXISTS chat_messages (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        session_id  INT          NOT NULL,
        auteur      ENUM('user','ia') NOT NULL,
        contenu     TEXT         NOT NULL,
        image_url   VARCHAR(500) NULL,
        created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql_sessions)
            cursor.execute(sql_messages)
        conn.commit()
        print("  Tables chat créées")
    finally:
        conn.close()


# ============================================================
# HELPER — Formatage de date relative
# ============================================================
def formater_date_relative(dt):
    """Retourne 'Aujourd'hui', 'Hier' ou 'JJ/MM'"""
    if not dt:
        return None
    
    # Si dt est une string, la convertir en datetime
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
        except:
            return dt
    
    today = date.today()
    if dt.date() == today:
        return "Aujourd'hui"
    elif dt.date() == today.replace(day=today.day-1):
        return "Hier"
    else:
        return dt.strftime("%d/%m")


# ============================================================
# ENDPOINT — NOUVELLE SESSION
# ============================================================
@router.post("/chat/new-session")
async def nouvelle_session(data: NouvelleSession):
    """Crée une nouvelle session de chat avec contexte plante."""

    if data.nom_plante:
        titre = f"{data.nom_plante}"
        if data.diagnostic:
            titre += f" — {data.diagnostic}"
            system_prompt = f"""Tu es un expert botaniste certifié avec plus de 20 ans d'expérience en Afrique de l'Ouest, spécialisé dans la flore de Côte d'Ivoire.
L'utilisateur a scanné une plante identifiée comme : {data.nom_plante}.
Diagnostic automatique : {data.diagnostic}.
Réponds exclusivement en français, de manière claire, précise et pédagogique.
Fournis des informations basées sur des connaissances botaniques scientifiques établies.
Évite toute spéculation ou information non vérifiée.
Si tu n'es pas certain d'une information, indique-le explicitement.
N'offre pas de conseils médicaux ou de traitement ; concentre-toi sur l'identification et les caractéristiques botaniques.
Réponds uniquement aux questions relatives à cette plante et ce diagnostic."""
        else:
            system_prompt = f"""Tu es un expert botaniste certifié avec plus de 20 ans d'expérience en Afrique de l'Ouest, spécialisé dans la flore de Côte d'Ivoire.
L'utilisateur a scanné une plante identifiée comme : {data.nom_plante}.
Réponds exclusivement en français, de manière claire, précise et pédagogique.
Fournis des informations basées sur des connaissances botaniques scientifiques établies.
Évite toute spéculation ou information non vérifiée.
Si tu n'es pas certain d'une information, indique-le explicitement.
N'offre pas de conseils médicaux ou de traitement ; concentre-toi sur l'identification et les caractéristiques botaniques.
Réponds uniquement aux questions relatives à cette plante."""
    else:
        titre         = "Nouvelle conversation"
        system_prompt = """Tu es un expert botaniste certifié avec plus de 20 ans d'expérience en Afrique de l'Ouest, spécialisé dans la flore de Côte d'Ivoire.
Réponds exclusivement en français, de manière claire, précise et pédagogique.
Fournis des informations basées sur des connaissances botaniques scientifiques établies.
Évite toute spéculation ou information non vérifiée.
Si tu n'es pas certain d'une information, indique-le explicitement.
N'offre pas de conseils médicaux ou de traitement ; concentre-toi sur l'identification et les caractéristiques botaniques.
Limite tes réponses aux plantes d'Afrique de l'Ouest."""

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO chat_sessions
                    (user_id, titre, nom_plante, diagnostic, system_prompt)
                VALUES (%s, %s, %s, %s, %s)
            """, (data.user_id, titre, data.nom_plante,
                  data.diagnostic, system_prompt))
            session_id = conn.insert_id()

            # Message de bienvenue contextuel
            if data.nom_plante:
                if data.diagnostic:
                    bienvenue = (f"Bonjour ! Je vois que vous avez scanné **{data.nom_plante}** "
                                 f"avec un diagnostic de **{data.diagnostic}**. "
                                 f"Je suis là pour répondre à toutes vos questions sur cette plante. "
                                 f"Comment puis-je vous aider ?")
                else:
                    bienvenue = (f"Bonjour ! Je vois que vous avez scanné **{data.nom_plante}**. "
                                 f"Je suis votre assistant expert pour tout savoir sur cette plante. "
                                 f"Comment puis-je vous aider ?")
            else:
                bienvenue = ("Bonjour ! Je suis votre assistant IA pour tout savoir "
                             "sur les plantes de Côte d'Ivoire. Comment puis-je vous aider ?")

            cursor.execute("""
                INSERT INTO chat_messages (session_id, auteur, contenu)
                VALUES (%s, 'ia', %s)
            """, (session_id, bienvenue))

        conn.commit()

        return JSONResponse(content={
            "session_id"  : session_id,
            "titre"       : titre,
            "nom_plante"  : data.nom_plante,
            "diagnostic"  : data.diagnostic,
            "bienvenue"   : bienvenue,
        })
    finally:
        conn.close()


# ============================================================
# ENDPOINT — ENVOYER UN MESSAGE
# ============================================================
@router.post("/chat/send")
async def envoyer_message(data: EnvoiMessage):
    """Reçoit le message de l'utilisateur, appelle Groq, sauvegarde et retourne la réponse."""
    conn = get_connection()
    try:
        # Récupère la session et son system prompt
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM chat_sessions WHERE id = %s",
                (data.session_id,)
            )
            session = cursor.fetchone()
            if not session:
                raise HTTPException(status_code=404, detail="Session introuvable")

            # Récupère les 10 derniers messages pour le contexte
            cursor.execute("""
                SELECT auteur, contenu FROM chat_messages
                WHERE session_id = %s
                ORDER BY created_at DESC LIMIT 10
            """, (data.session_id,))
            historique = cursor.fetchall()
            historique.reverse()

        # Sauvegarde le message utilisateur
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO chat_messages (session_id, auteur, contenu)
                VALUES (%s, 'user', %s)
            """, (data.session_id, data.contenu))
        conn.commit()

        # Construit les messages pour Groq
        messages_grok = [
            {"role": "system", "content": session["system_prompt"] or "Tu es un expert botaniste."}
        ]

        for msg in historique:
            role = "user" if msg["auteur"] == "user" else "assistant"
            messages_grok.append({"role": role, "content": msg["contenu"]})

        messages_grok.append({"role": "user", "content": data.contenu})

        # Appel Groq
        reponse_ia = _appeler_grok(messages_grok)

        # Sauvegarde la réponse IA
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO chat_messages
                    (session_id, auteur, contenu)
                VALUES (%s, 'ia', %s)
            """, (data.session_id, reponse_ia))
            message_id = conn.insert_id()
        conn.commit()

        return JSONResponse(content={
            "message_id": message_id,
            "contenu"   : reponse_ia,
            "image_url" : None,
            "auteur"    : "ia",
            "heure"     : datetime.now().strftime("%H:%M"),
        })

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# ============================================================
# ENDPOINT — SESSIONS D'UN UTILISATEUR
# ============================================================
@router.get("/chat/sessions/{user_id}")
async def sessions_utilisateur(user_id: int):
    """Retourne les sessions de chat pour le panneau historique."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    s.id, s.titre, s.nom_plante, s.diagnostic,
                    s.created_at, s.updated_at,
                    COUNT(m.id) as nb_messages,
                    MAX(CASE WHEN m.auteur = 'user' THEN m.contenu END) as dernier_message,
                    MAX(m.created_at) as dernier_message_date
                FROM chat_sessions s
                LEFT JOIN chat_messages m ON m.session_id = s.id
                WHERE s.user_id = %s
                GROUP BY s.id
                ORDER BY s.updated_at DESC
                LIMIT 20
            """, (user_id,))
            sessions = cursor.fetchall()

        # Formate les dates pour JSON
        for s in sessions:
            if s.get("created_at"):
                s["created_at"] = s["created_at"].strftime("%Y-%m-%d %H:%M")
            if s.get("updated_at"):
                s["updated_at"] = s["updated_at"].strftime("%Y-%m-%d %H:%M")
            if s.get("dernier_message_date"):
                # Convertir datetime en string si nécessaire
                if hasattr(s["dernier_message_date"], 'strftime'):
                    s["dernier_message_date"] = s["dernier_message_date"].strftime("%Y-%m-%d %H:%M:%S")
                s["date_relative"] = formater_date_relative(s["dernier_message_date"])
            else:
                s["date_relative"] = formater_date_relative(s.get("created_at"))

        return JSONResponse(content={"sessions": sessions})
    finally:
        conn.close()


# ============================================================
# ENDPOINT — MESSAGES D'UNE SESSION
# ============================================================
@router.get("/chat/messages/{session_id}")
async def messages_session(session_id: int):
    """Retourne tous les messages d'une session."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, auteur, contenu, image_url,
                       TIME_FORMAT(created_at, '%%H:%%i') as heure
                FROM chat_messages
                WHERE session_id = %s
                ORDER BY created_at ASC
            """, (session_id,))
            messages = cursor.fetchall()
        return JSONResponse(content={"messages": messages})
    finally:
        conn.close()



# ============================================================
# APPEL GROQ
# ============================================================
def _appeler_grok(messages: list) -> str:
    """
    Appelle l'API Groq et retourne la réponse texte.
    """
    print(f"  Appel Groq avec {len(messages)} messages...")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "max_tokens": 600,
        "messages": messages
    }

    try:
        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=60)
        print(f"  Groq réponse status: {response.status_code}")

        if response.status_code == 200:
            texte = response.json()["choices"][0]["message"]["content"]
            print(f"  Groq réponse reçue: {len(texte)} caractères")
            return texte
        else:
            print(f"  Erreur Groq: {response.text[:200]}")
            return "Je rencontre une difficulté technique. Réessayez dans un instant."
    except Exception as e:
        print(f"  Exception Groq: {e}")
        return "Service IA temporairement indisponible. Réessayez dans un instant."