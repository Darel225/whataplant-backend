"""
services/llm_service.py — Analyse IA avec Grok Vision
"""

import requests
import json
import base64
from config import GROK_API_KEY, GROK_URL, GROK_MODELS


def analyser_plante(nom_scientifique: str, image_bytes: bytes) -> dict:
    """
    Envoie le nom scientifique + l'image à Grok Vision.
    Essaie plusieurs modèles jusqu'à trouver un qui fonctionne.
    """

    # Vérifie que la clé API est présente
    if not GROK_API_KEY or GROK_API_KEY == "":
        print("  ⚠️  GROK_API_KEY non configurée — utilisation base locale")
        return _reponse_defaut(nom_scientifique)

    # Convertit l'image en base64
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    # ============================================================
    # PROMPT OPTIMISÉ POUR GROK
    # ============================================================
    prompt = f"""Tu es un botaniste expert, spécialiste des plantes médicinales et alimentaires de Côte d'Ivoire et d'Afrique de l'Ouest.

Plante identifiée : **{nom_scientifique}**

**RÈGLE IMPORTANTE** : Même si l'identification n'est pas certaine, donne les informations sur cette plante comme si elle était correcte. Utilise tes connaissances botaniques.

Analyse l'image et réponds UNIQUEMENT en JSON valide avec cette structure exacte :

{{
  "is_healthy": true,
  "statut": "Plante en bonne santé",
  "alert_details": null,
  "noms_locaux": "Noms locaux en Côte d'Ivoire (Baoulé, Dioula, Français)",
  "statut_securite": "Plante Médicinale ou Plante Comestible ou Plante Toxique",
  "toxique": false,
  "info_toxicite": "Détails sur la toxicité",
  "usages": ["Usage 1", "Usage 2", "Usage 3", "Usage 4", "Usage 5"],
  "mode_utilisation": "Explication détaillée de la préparation et utilisation",
  "informations_complementaires": {{
    "parties_utilisees": "Feuilles, racines, fruits",
    "precautions": "Précautions d'usage",
    "contre_indications": "Contre-indications"
  }}
}}

Réponds UNIQUEMENT avec le JSON, sans texte avant ou après."""

    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }

    # Essaie chaque modèle
    for modele in GROK_MODELS:
        payload = {
            "model": modele,
            "max_tokens": 1000,
            "temperature": 0.3,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        }

        print(f"  Appel API Grok avec modèle: {modele}...")

        try:
            response = requests.post(
                GROK_URL,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            print(f"  Grok réponse status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"  ✅ Modèle fonctionnel: {modele}")
                contenu = response.json()["choices"][0]["message"]["content"]
                print(f"  Grok réponse reçue ({len(contenu)} caractères)")
                contenu = contenu.replace("```json", "").replace("```", "").strip()
                resultat = json.loads(contenu)
                return _valider_et_completer(resultat, nom_scientifique)
            else:
                print(f"  ❌ Modèle {modele} échoué: {response.text[:100]}")
                
        except requests.exceptions.Timeout:
            print(f"  ❌ Timeout pour {modele}")
        except Exception as e:
            print(f"  ❌ Exception pour {modele}: {e}")

    # Si aucun modèle ne fonctionne
    print("  ⚠️  Aucun modèle Grok fonctionnel, utilisation fallback")
    return _reponse_defaut(nom_scientifique)


def _valider_et_completer(resultat: dict, nom_scientifique: str) -> dict:
    """Valide et complète les champs manquants."""
    
    defaut = {
        "is_healthy": True,
        "statut": "Plante identifiée",
        "alert_details": None,
        "noms_locaux": f"Plante identifiée : {nom_scientifique}",
        "statut_securite": "Plante identifiée",
        "toxique": False,
        "info_toxicite": "Information non disponible",
        "usages": [f"Plante identifiée : {nom_scientifique}"],
        "mode_utilisation": "Consultez un expert local",
        "informations_complementaires": {
            "parties_utilisees": "Information non disponible",
            "precautions": "Information non disponible",
            "contre_indications": "Information non disponible"
        }
    }
    
    for key, value in defaut.items():
        if key not in resultat or resultat[key] is None:
            resultat[key] = value
    
    if "informations_complementaires" not in resultat:
        resultat["informations_complementaires"] = defaut["informations_complementaires"]
    else:
        for key, value in defaut["informations_complementaires"].items():
            if key not in resultat["informations_complementaires"]:
                resultat["informations_complementaires"][key] = value
    
    return resultat


def _reponse_defaut(nom_scientifique: str) -> dict:
    """Retourne une réponse par défaut."""
    return {
        "is_healthy": True,
        "statut": "Analyse IA temporairement indisponible",
        "alert_details": None,
        "noms_locaux": f"Plante identifiée : {nom_scientifique}",
        "statut_securite": "Plante identifiée",
        "toxique": False,
        "info_toxicite": "Information non disponible. Consultez un expert local.",
        "usages": [
            f"Plante identifiée : {nom_scientifique}",
            "Information détaillée non disponible actuellement"
        ],
        "mode_utilisation": "Consultez un botaniste local pour les usages traditionnels",
        "informations_complementaires": {
            "parties_utilisees": "Information non disponible",
            "precautions": "Information non disponible",
            "contre_indications": "Information non disponible"
        }
    }