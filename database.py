"""
database.py — Connexion et opérations MySQL
=============================================
Gère la connexion à la base de données et
la création automatique des tables.
"""

import pymysql
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME


# ============================================================
# CONNEXION
# ============================================================
def get_connection():
    """Retourne une connexion à la base MySQL."""
    return pymysql.connect(
        host     = DB_HOST,
        port     = DB_PORT,
        user     = DB_USER,
        password = DB_PASSWORD,
        database = DB_NAME,
        charset  = 'utf8mb4',
        cursorclass = pymysql.cursors.DictCursor
    )


# ============================================================
# CREATION DES TABLES
# ============================================================
def creer_tables():
    """
    Crée les tables si elles n'existent pas.
    Appelé au démarrage de l'application.
    """
    
    # Table users
    sql_users = """
    CREATE TABLE IF NOT EXISTS users (
        id         INT AUTO_INCREMENT PRIMARY KEY,
        nom        VARCHAR(200) NOT NULL,
        email      VARCHAR(200) NOT NULL UNIQUE,
        password   VARCHAR(300) NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    
    # Table scans avec toutes les colonnes
    sql_scans = """
    CREATE TABLE IF NOT EXISTS scans (
        id                   INT AUTO_INCREMENT PRIMARY KEY,
        user_id              INT          NULL,
        nom_scientifique     VARCHAR(200) NOT NULL,
        nom_local            VARCHAR(200) NULL,
        famille              VARCHAR(200) NULL,
        statut               VARCHAR(100) NULL,
        is_healthy           BOOLEAN      DEFAULT TRUE,
        alert_details        TEXT         NULL,
        usages               TEXT         NULL,
        mode_utilisation     TEXT         NULL,
        parties_utilisees    VARCHAR(200) NULL,
        precautions          TEXT         NULL,
        contre_indications   TEXT         NULL,
        image_url            VARCHAR(500) NULL,
        score_confiance      FLOAT        NULL,
        created_at           DATETIME     DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql_users)
            cursor.execute(sql_scans)
        conn.commit()
        conn.close()
        print("  Tables créées/mises à jour avec succès")
    except Exception as e:
        print(f"  Erreur création tables : {e}")


# ============================================================
# AJOUT DES NOUVELLES COLONNES (SI ELLES N'EXISTENT PAS)
# ============================================================
def migrer_base_donnees():
    """
    Ajoute les nouvelles colonnes à la table scans si elles n'existent pas.
    À exécuter après la création des tables.
    """
    nouvelles_colonnes = [
        ("mode_utilisation", "TEXT NULL"),
        ("parties_utilisees", "VARCHAR(200) NULL"),
        ("precautions", "TEXT NULL"),
        ("contre_indications", "TEXT NULL"),
    ]
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Vérifie les colonnes existantes
            cursor.execute("SHOW COLUMNS FROM scans")
            colonnes_existantes = [col["Field"] for col in cursor.fetchall()]
            
            # Ajoute chaque nouvelle colonne si elle n'existe pas
            for colonne, type_sql in nouvelles_colonnes:
                if colonne not in colonnes_existantes:
                    try:
                        cursor.execute(f"ALTER TABLE scans ADD COLUMN {colonne} {type_sql}")
                        print(f"  Colonne '{colonne}' ajoutée avec succès")
                    except Exception as e:
                        print(f"  Erreur ajout colonne '{colonne}': {e}")
            
            conn.commit()
            print("  Migration de la base de données terminée")
    except Exception as e:
        print(f"  Erreur migration : {e}")
    finally:
        conn.close()


# ============================================================
# SAUVEGARDER UN SCAN (AVEC LES NOUVELLES COLONNES)
# ============================================================
def sauvegarder_scan(donnees: dict) -> int:
    """
    Insère un nouveau scan dans la base de données.
    Retourne l'ID du scan créé.
    """
    print(f"  📝 Sauvegarde des données: {donnees}")
    
    sql = """
    INSERT INTO scans
        (user_id, nom_scientifique, nom_local, famille,
         statut, is_healthy, alert_details, usages,
         mode_utilisation, parties_utilisees, precautions,
         contre_indications, image_url, score_confiance)
    VALUES
        (%(user_id)s, %(nom_scientifique)s, %(nom_local)s, %(famille)s,
         %(statut)s, %(is_healthy)s, %(alert_details)s, %(usages)s,
         %(mode_utilisation)s, %(parties_utilisees)s, %(precautions)s,
         %(contre_indications)s, %(image_url)s, %(score_confiance)s)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, donnees)
        conn.commit()
        
        # Utilise cursor.lastrowid au lieu de conn.insert_id()
        new_id = cursor.lastrowid
        print(f"  ✅ Scan sauvegardé avec ID: {new_id}")
        return new_id
    except Exception as e:
        print(f"  ❌ Erreur sauvegarde: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


# ============================================================
# STATISTIQUES UTILISATEUR
# ============================================================
def get_stats_utilisateur(user_id: int = None) -> dict:
    """
    Retourne les statistiques pour le dashboard :
    - Nombre total de scans
    - Nombre d'alertes (plantes malades)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:

            # Total scans
            if user_id:
                cursor.execute(
                    "SELECT COUNT(*) as total FROM scans WHERE user_id = %s",
                    (user_id,)
                )
            else:
                cursor.execute("SELECT COUNT(*) as total FROM scans")
            total_scans = cursor.fetchone()["total"]

            # Total alertes (plantes malades)
            if user_id:
                cursor.execute(
                    "SELECT COUNT(*) as alertes FROM scans WHERE user_id = %s AND is_healthy = 0",
                    (user_id,)
                )
            else:
                cursor.execute(
                    "SELECT COUNT(*) as alertes FROM scans WHERE is_healthy = 0"
                )
            total_alertes = cursor.fetchone()["alertes"]

        return {
            "total_scans"  : total_scans,
            "total_alertes": total_alertes,
        }
    finally:
        conn.close()


# ============================================================
# HISTORIQUE SCANS
# ============================================================
def get_historique(user_id: int = None, limite: int = 10) -> list:
    """Retourne les derniers scans pour l'historique."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            if user_id:
                cursor.execute(
                    """SELECT * FROM scans WHERE user_id = %s
                       ORDER BY created_at DESC LIMIT %s""",
                    (user_id, limite)
                )
            else:
                cursor.execute(
                    "SELECT * FROM scans ORDER BY created_at DESC LIMIT %s",
                    (limite,)
                )
            return cursor.fetchall()
    finally:
        conn.close()


# ============================================================
# RÉCUPÉRER UN SCAN PAR ID
# ============================================================
def get_scan_par_id(scan_id: int) -> dict:
    """Retourne un scan spécifique par son ID."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM scans WHERE id = %s",
                (scan_id,)
            )
            return cursor.fetchone()
    finally:
        conn.close()