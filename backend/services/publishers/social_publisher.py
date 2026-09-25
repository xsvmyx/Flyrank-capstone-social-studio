# from abc import ABC, abstractmethod
# from typing import Dict, Any, Optional


# class SocialPublisher(ABC):
#     """
#     Interface abstraite unique pour tous les adaptateurs de publication (réels et mocks).
#     """

#     @abstractmethod
#     async def publish(
#         self, content: str, metadata: Optional[Dict[str, Any]] = None
#     ) -> Dict[str, Any]:
#         """
#         Publie le contenu du variant sur la plateforme cible.

#         :param content: Le texte du variant à publier.
#         :param metadata: Données supplémentaires facultatives (ex: image_url, title).
#         :return: Un dictionnaire contenant les détails du résultat (status, external_id, url, etc.).
#         """
#         pass