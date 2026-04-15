"""
services/plantnet_service.py — Identification via PlantNet API
===============================================================
Version utilisant exactement le même code qui fonctionnait avant.
"""

import requests
from config import PLANTNET_API_KEY, PLANTNET_URL


def identifier_plante(image_bytes: bytes) -> dict:
    """
    Envoie l'image à l'API PlantNet.
    Utilise le même format que le code qui fonctionnait.
    """
    
    url = (
        f"{PLANTNET_URL}?api-key={PLANTNET_API_KEY}"
        f"&lang=fr&include-related-images=false"
    )
    
    try:
        response = requests.post(
            url,
            files=[('images', ('plante.jpg', image_bytes, 'image/jpeg'))],
            data={'organs': 'leaf'},
            timeout=15
        )
        
        if response.status_code != 200:
            print(f"      PlantNet erreur {response.status_code}: {response.text[:200]}")
            raise Exception(f"Erreur PlantNet: code {response.status_code}")
        
        data = response.json()
        
        if "results" not in data or not data["results"]:
            raise Exception("Aucun résultat trouvé")
        
        meilleur = data["results"][0]
        noms_communs = meilleur["species"].get("commonNames", [])
        
        return {
            "nom_scientifique": meilleur["species"]["scientificNameWithoutAuthor"],
            "famille": meilleur["species"].get("family", {}).get("scientificNameWithoutAuthor", "—"),
            "nom_commun": noms_communs[0] if noms_communs else "—",
            "score": round(meilleur["score"], 4),
        }
        
    except requests.exceptions.ConnectionError:
        raise Exception("PlantNet API injoignable — vérifiez votre connexion")
    except requests.exceptions.Timeout:
        raise Exception("PlantNet API timeout — réessayez")
    except Exception as e:
        raise Exception(f"Erreur identification: {str(e)}")