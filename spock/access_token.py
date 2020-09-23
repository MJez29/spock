from dataclasses import dataclass


@dataclass
class AccessToken:
    """Represents a specific token that can be used to access Spotify."""

    access_token: str
    token_type: str
    expires_in: str
    refresh_token: str
    scope: str
