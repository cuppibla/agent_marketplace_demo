"""Shared Google auth helper for Agent Registry + MCP calls."""

import google.auth
import google.auth.transport.requests


def get_dynamic_headers(context=None) -> dict:
    """Fetch fresh OIDC headers each call to avoid token expiry."""
    credentials, _ = google.auth.default()
    auth_request = google.auth.transport.requests.Request()
    credentials.refresh(auth_request)

    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json",
    }
    quota_project_id = getattr(credentials, "quota_project_id", None)
    if quota_project_id:
        headers["x-goog-user-project"] = quota_project_id
    return headers
