"""
Obtain a PKCE refresh token for debugging purposes

1. Run script with SPOTIFY_CLIENT_ID envvar set
2. Accept the Spotify interstitial that pops up in your favorite web browser
3. Wait for connection to timeout after redirecting to localhost
4. Copy everything in your URL bar and paste it into this program
5. Profit
"""

import tekore as tk
import os

client_id = os.environ.get("SPOTIFY_CLIENT_ID")
print(
    tk.prompt_for_pkce_token(
        client_id, "http://localhost", tk.scope.every
    ).refresh_token
)
