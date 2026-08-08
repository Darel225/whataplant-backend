# 🌿 WhatAPlant - Backend API

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![MySQL](https://img.shields.io/badge/mysql-4479A1.svg?style=for-the-badge&logo=mysql&logoColor=white)
![Render](https://img.shields.io/badge/Render-%46E3B7.svg?style=for-the-badge&logo=render&logoColor=white)

Ce dépôt contient le code source exclusif du **Backend** de l'application mobile WhatAPlant. Il expose une API RESTful conçue pour gérer l'identification botanique, le diagnostic phytosanitaire assisté par IA, et la persistance des données.

## 🚀 Fonctionnalités Principales

*   **Identification de Plantes :** Endpoints dédiés au traitement des images pour identifier les espèces (nom scientifique, nom local, famille).
*   **Diagnostic & Chatbot IA :** Intégration de l'API **Groq** pour analyser l'état de santé de la plante (feuilles jaunes, parasites) et fournir des conseils de soin ou des remèdes traditionnels.
*   **Gestion des Médias :** Upload, optimisation et stockage sécurisé des images des scans via **Cloudinary**.
*   **Persistance des Données :** Connexion robuste à une base de données **MySQL** hébergée sur **Clever Cloud** pour sauvegarder l'historique des scans et les statistiques utilisateurs.
*   **Healthcheck :** Route racine optimisée pour les pings **UptimeRobot**, empêchant la mise en veille du serveur sur les hébergements gratuits.

## 🛠️ Stack Technique

*   **Framework Web :** FastAPI (Python)
*   **Base de données :** MySQL (Clever Cloud)
*   **Stockage Images :** Cloudinary
*   **Intelligence Artificielle :** Groq API
*   **Hébergement & Déploiement :** Render
*   **Monitoring :** UptimeRobot

## ⚙️ Installation et Configuration Locale

### 1. Cloner le dépôt
```bash
git clone https://github.com/votre-nom-utilisateur/whataplant-backend.git
cd whataplant-backend
```

### 2. Créer un environnement virtuel
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Configuration des variables d'environnement
Créez un fichier `.env` à la racine du projet et ajoutez vos clés :
```env
# Configuration Base de Données (Clever Cloud)
DB_HOST=votre_host_clever_cloud
DB_USER=votre_user
DB_PASSWORD=votre_mot_de_passe
DB_NAME=votre_db_name

# Configuration Cloudinary
CLOUDINARY_CLOUD_NAME=votre_cloud_name
CLOUDINARY_API_KEY=votre_api_key
CLOUDINARY_API_SECRET=votre_api_secret

# Configuration IA
GROQ_API_KEY=votre_cle_groq
```

### 5. Lancer le serveur de développement
```bash
uvicorn main:app --reload
```
L'API sera accessible sur `http://localhost:8000`.

## 📚 Documentation API

FastAPI génère automatiquement la documentation interactive (Swagger UI).
Une fois le serveur lancé, naviguez vers :
👉 `http://localhost:8000/docs`

## 🌍 Déploiement Production

Le backend est configuré pour être déployé facilement sur **Render** en tant que Web Service. La commande de démarrage recommandée en production est :
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

## 👨‍💻 Auteur
Conçu et développé par **Darel Sylvestre** dans le cadre du projet d'ingénierie logicielle WhatAPlant.


