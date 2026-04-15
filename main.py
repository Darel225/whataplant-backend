"""
main.py — Point d'entrée de l'application FastAPI
===================================================
Lance le serveur avec : uvicorn main:app --reload
Documentation auto  : http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from database          import creer_tables
from routes.diagnostic import router as diagnostic_router
from routes.chat       import router as chat_router, creer_tables_chat
from routes.auth       import router as auth_router, creer_tables_auth
from routes.scans      import router as scans_router
from routes.home       import router as home_router
from config import UPLOAD_DIR

# ============================================================
# INITIALISATION
# ============================================================
app = FastAPI(
    title       = "WhatAPlant API",
    description = "Backend de diagnostic de plantes pour la Côte d'Ivoire",
    version     = "1.0.0"
)

# ============================================================
# CORS — permet à React Native d'appeler l'API
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],   # en production, mettre l'URL exacte
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ============================================================
# FICHIERS STATIQUES — pour servir les images uploadées
# ============================================================
# Crée le dossier uploads s'il n'existe pas
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# ============================================================
# ROUTES
# ============================================================
app.include_router(diagnostic_router, prefix="/api", tags=["Diagnostic"])
app.include_router(chat_router,        prefix="/api", tags=["Chat IA"])
app.include_router(auth_router,        prefix="/api", tags=["Authentification"])
app.include_router(scans_router,       prefix="/api", tags=["Bibliothèque"])
app.include_router(home_router,        prefix="/api", tags=["Dashboard"])

# ============================================================
# EVENEMENT DEMARRAGE
# ============================================================
@app.on_event("startup")
async def startup():
    print("\n  WhatAPlant API démarrée")
    print("  Création des tables MySQL...")
    creer_tables()
    creer_tables_chat()
    creer_tables_auth()
    print(f"  Dossier uploads: {UPLOAD_DIR}")
    print("  Prête à recevoir des requêtes !\n")

# ============================================================
# ROUTE SANTE
# ============================================================
@app.get("/")
async def racine():
    return {
        "app"    : "WhatAPlant API",
        "version": "1.0.0",
        "statut" : "en ligne",
        "docs"   : "/docs"
    }

@app.get("/health")
async def health():
    return {"statut": "ok"}