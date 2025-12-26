# openapi.py
"""
OpenAPI / Swagger configuration for Bot42.

Rule: structure only — no behavior changes.
Keeps SAFE-KEY Swagger "Authorize" support in one place.
"""

from fastapi.openapi.utils import get_openapi
from security import SAFE_KEY_HEADER_NAME


def wire_openapi(app) -> None:
    """
    Installs a custom OpenAPI generator onto the FastAPI app.
    """

    def custom_openapi():
        # Cache
        if app.openapi_schema:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        # Ensure components/securitySchemes exists
        schema.setdefault("components", {}).setdefault("securitySchemes", {})

        # Swagger "Authorize" support: SAFE-KEY header
        schema["components"]["securitySchemes"]["SafeKeyAuth"] = {
            "type": "apiKey",
            "in": "header",
            "name": SAFE_KEY_HEADER_NAME,
        }

        # Apply globally so Swagger sends the header after Authorize
        schema["security"] = [{"SafeKeyAuth": []}]

        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi