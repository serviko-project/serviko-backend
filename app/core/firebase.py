import json
import logging
import os

import firebase_admin
from firebase_admin import auth, credentials

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedException

logger = logging.getLogger(__name__)

_firebase_app = None


def init_firebase() -> None:
    global _firebase_app
    if _firebase_app is not None:
        return

    settings = get_settings()
    
    firebase_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
    if firebase_json:
        try:
            cred_dict = json.loads(firebase_json)
            cred = credentials.Certificate(cred_dict)
        except Exception as e:
            logger.error("Failed to parse FIREBASE_CREDENTIALS_JSON: %s", str(e))
            raise
    else:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        
    _firebase_app = firebase_admin.initialize_app(cred)
    logger.info("Firebase Admin SDK initialized")


def verify_firebase_token(token: str) -> dict:
    try:
        decoded = auth.verify_id_token(token)
        return {
            "uid": decoded["uid"],
            "email": decoded.get("email"),
            "name": decoded.get("name"),
        }
    except auth.ExpiredIdTokenError:
        raise UnauthorizedException("Token has expired")
    except auth.RevokedIdTokenError:
        raise UnauthorizedException("Token has been revoked")
    except auth.InvalidIdTokenError:
        raise UnauthorizedException("Invalid authentication token")
    except Exception as e:
        logger.error("Firebase token verification failed: %s", str(e))
        raise UnauthorizedException("Authentication failed")
