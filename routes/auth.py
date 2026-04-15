"""
routes/auth.py — Authentification JWT
=======================================
POST /auth/register       → Inscription
POST /auth/login          → Connexion + token JWT
POST /auth/forgot-password → Demande code OTP
POST /auth/verify-otp     → Vérifie le code OTP
POST /auth/reset-password → Nouveau mot de passe
"""

from fastapi           import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic          import BaseModel
from typing            import Optional
from datetime          import datetime, timedelta
import bcrypt
import jwt
import random
import string

from database import get_connection

router = APIRouter()

# ============================================================
# CONFIGURATION JWT
# ============================================================
SECRET_KEY  = "whataplant_secret_key_change_en_production"
ALGORITHM   = "HS256"
EXPIRE_DAYS = 30


# ============================================================
# MODELES PYDANTIC
# ============================================================
class InscriptionData(BaseModel):
    nom      : str
    email    : str
    password : str

class ConnexionData(BaseModel):
    email    : str
    password : str

class OublieData(BaseModel):
    email    : str

class VerifOTPData(BaseModel):
    email    : str
    code     : str

class ResetData(BaseModel):
    email       : str
    code        : str
    nouveau_mdp : str


# ============================================================
# HELPERS — Utilisation directe de bcrypt
# ============================================================
def hasher_mdp(mdp: str) -> str:
    """Hash un mot de passe avec bcrypt."""
    # bcrypt limite à 72 caractères, on tronque si nécessaire
    mdp_bytes = mdp.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(mdp_bytes, salt).decode('utf-8')

def verifier_mdp(mdp: str, hash_mdp: str) -> bool:
    """Vérifie un mot de passe avec bcrypt."""
    mdp_bytes = mdp.encode('utf-8')[:72]
    hash_bytes = hash_mdp.encode('utf-8')
    return bcrypt.checkpw(mdp_bytes, hash_bytes)

def creer_token(user_id: int, email: str, nom: str) -> str:
    """Crée un token JWT."""
    payload = {
        "user_id": user_id,
        "email": email,
        "nom": nom,
        "exp": datetime.utcnow() + timedelta(days=EXPIRE_DAYS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def generer_otp() -> str:
    """Génère un code OTP à 6 chiffres."""
    return ''.join(random.choices(string.digits, k=6))


# ============================================================
# CREATION DES TABLES AUTH
# ============================================================
def creer_tables_auth():
    sql_users = """
    CREATE TABLE IF NOT EXISTS users (
        id         INT AUTO_INCREMENT PRIMARY KEY,
        nom        VARCHAR(200) NOT NULL,
        email      VARCHAR(200) NOT NULL UNIQUE,
        password   VARCHAR(300) NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    sql_otp = """
    CREATE TABLE IF NOT EXISTS password_resets (
        id         INT AUTO_INCREMENT PRIMARY KEY,
        email      VARCHAR(200) NOT NULL,
        code       VARCHAR(10)  NOT NULL,
        expire_at  DATETIME     NOT NULL,
        utilise    BOOLEAN      DEFAULT FALSE,
        created_at DATETIME     DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql_users)
            cursor.execute(sql_otp)
        conn.commit()
        print("  Tables auth créées")
    finally:
        conn.close()


# ============================================================
# INSCRIPTION
# ============================================================
@router.post("/auth/register")
async def inscription(data: InscriptionData):
    conn = get_connection()
    try:
        # Vérifie si l'email existe déjà
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM users WHERE email = %s",
                (data.email,)
            )
            if cursor.fetchone():
                raise HTTPException(
                    status_code=409,
                    detail="Un compte existe déjà avec cet email"
                )

        # Crée l'utilisateur
        mdp_hashe = hasher_mdp(data.password)
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (nom, email, password) VALUES (%s, %s, %s)",
                (data.nom, data.email, mdp_hashe)
            )
            user_id = conn.insert_id()
        conn.commit()

        # Génère le token directement
        token = creer_token(user_id, data.email, data.nom)

        return JSONResponse(content={
            "succes": True,
            "token": token,
            "user": {
                "id": user_id,
                "nom": data.nom,
                "email": data.email,
            },
            "message": "Compte créé avec succès"
        })
    finally:
        conn.close()


# ============================================================
# CONNEXION
# ============================================================
@router.post("/auth/login")
async def connexion(data: ConnexionData):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, nom, email, password FROM users WHERE email = %s",
                (data.email,)
            )
            user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Email ou mot de passe incorrect"
            )

        if not verifier_mdp(data.password, user["password"]):
            raise HTTPException(
                status_code=401,
                detail="Email ou mot de passe incorrect"
            )

        token = creer_token(user["id"], user["email"], user["nom"])

        return JSONResponse(content={
            "succes": True,
            "token": token,
            "user": {
                "id": user["id"],
                "nom": user["nom"],
                "email": user["email"],
            }
        })
    finally:
        conn.close()


# ============================================================
# MOT DE PASSE OUBLIE — envoie OTP
# ============================================================
@router.post("/auth/forgot-password")
async def mot_de_passe_oublie(data: OublieData):
    conn = get_connection()
    try:
        # Vérifie que l'email existe
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM users WHERE email = %s",
                (data.email,)
            )
            if not cursor.fetchone():
                return JSONResponse(content={
                    "succes": True,
                    "message": "Si cet email existe, un code a été envoyé"
                })

        # Génère et sauvegarde le code OTP
        code = generer_otp()
        expire_at = datetime.utcnow() + timedelta(minutes=15)

        with conn.cursor() as cursor:
            # Invalide les anciens codes
            cursor.execute(
                "UPDATE password_resets SET utilise=TRUE WHERE email=%s",
                (data.email,)
            )
            # Crée le nouveau code
            cursor.execute(
                "INSERT INTO password_resets (email, code, expire_at) VALUES (%s, %s, %s)",
                (data.email, code, expire_at)
            )
        conn.commit()

        # Pour le développement, on retourne le code
        print(f"\n  *** CODE OTP pour {data.email} : {code} ***\n")

        return JSONResponse(content={
            "succes": True,
            "message": "Code envoyé sur votre email",
            "code_dev": code
        })
    finally:
        conn.close()


# ============================================================
# VERIFICATION OTP
# ============================================================
@router.post("/auth/verify-otp")
async def verifier_otp(data: VerifOTPData):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id FROM password_resets
                WHERE email = %s
                  AND code = %s
                  AND utilise = FALSE
                  AND expire_at > NOW()
                ORDER BY created_at DESC
                LIMIT 1
            """, (data.email, data.code))
            reset = cursor.fetchone()

        if not reset:
            raise HTTPException(
                status_code=400,
                detail="Code invalide ou expiré"
            )

        return JSONResponse(content={
            "succes": True,
            "message": "Code vérifié avec succès"
        })
    finally:
        conn.close()


# ============================================================
# RESET MOT DE PASSE
# ============================================================
@router.post("/auth/reset-password")
async def reset_mot_de_passe(data: ResetData):
    conn = get_connection()
    try:
        # Vérifie le code OTP une dernière fois
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id FROM password_resets
                WHERE email = %s
                  AND code = %s
                  AND utilise = FALSE
                  AND expire_at > NOW()
                ORDER BY created_at DESC
                LIMIT 1
            """, (data.email, data.code))
            reset = cursor.fetchone()

        if not reset:
            raise HTTPException(
                status_code=400,
                detail="Code invalide ou expiré"
            )

        # Met à jour le mot de passe
        nouveau_hash = hasher_mdp(data.nouveau_mdp)
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET password = %s WHERE email = %s",
                (nouveau_hash, data.email)
            )
            # Invalide le code OTP
            cursor.execute(
                "UPDATE password_resets SET utilise=TRUE WHERE email=%s AND code=%s",
                (data.email, data.code)
            )
        conn.commit()

        return JSONResponse(content={
            "succes": True,
            "message": "Mot de passe modifié avec succès"
        })
    finally:
        conn.close()