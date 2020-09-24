import os
import tekore as tk
import keyring

KEYRING_SERVICE_NAME = "spock"


class State:
    def __init__(self, default_client_id):
        self.client_id = os.environ.get("SPOTIFY_CLIENT_ID", default_client_id)

    def get_user(self):
        """
        Get a tekore.Spotify object representing a user using the refresh token.
        :return: None if the refresh token is invalid.
        """
        refresh_token = self.get_refresh_token()
        if refresh_token:
            creds = tk.Credentials(client_id=self.client_id)
            try:
                new_token = creds.refresh_pkce_token(refresh_token)
                self.set_refresh_token(new_token.refresh_token)
                return tk.Spotify(new_token)
            except tk.BadRequest:
                self.remove_refresh_token()
        return None

    def get_refresh_token(self):
        """
        :return: The refresh token stored in the keyring or from envvar
        """
        # Get refresh token from keyring or environment variable (for testing)
        kr_refresh_token = keyring.get_password(KEYRING_SERVICE_NAME, "refresh_token")
        return os.environ.get("SPOTIFY_REFRESH_TOKEN", kr_refresh_token)

    def set_refresh_token(self, refresh_token):
        keyring.set_password(KEYRING_SERVICE_NAME, "refresh_token", refresh_token)

    def remove_refresh_token(self):
        keyring.delete_password(KEYRING_SERVICE_NAME, "refresh_token")
