import secrets
import hashlib
import base64
import webbrowser
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from .config import CLIENT_ID, REDIRECT_URI, PORT

CODE_VERIFIER_MIN_LENGTH = 43
CODE_VERIFIER_MAX_LENGTH = 128
CODE_VERIFIER_CHARACTERS = (
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890-_.~"
)

SERVER_ADDRESS = ("", 8794)


def generate_code() -> (str, bytes):
    length = (
        secrets.randbelow(
            exclusive_upper_bound=CODE_VERIFIER_MAX_LENGTH
            - CODE_VERIFIER_MIN_LENGTH
            + 1
        )
        + CODE_VERIFIER_MIN_LENGTH
    )

    code_verifier = "".join(
        secrets.choice(CODE_VERIFIER_CHARACTERS) for i in range(length)
    )

    sha = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(sha)

    return (code_verifier, code_challenge)


STATE_CHARACTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"


def generate_state(remote) -> str:
    state = "".join(secrets.choice(STATE_CHARACTERS) for i in range(64))
    return ("remote-" if remote else "local-") + state


def generate_spotify_authorize_url(code_challenge):
    return "https://accounts.spotify.com/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&state={state}&code_challenge={code_challenge}&code_challenge_method=sha256".format(
        code_challenge=code_challenge, client_id=CLIENT_ID, redirect_uri=REDIRECT_URI
    )


class SpotifyRedirectRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        pass


def authenticate():
    code_verifier, code_challenge = generate_code()

    state = generate_state(remote=False)

    authorization_token = None

    httpd = HTTPServer(
        server_address=SERVER_ADDRESS, RequestHandlerClass=SpotifyRedirectRequestHandler
    )

    server_thread = threading.Thread(target=httpd.serve_forever)

    server_thread.start()

    webbrowser.open(url=generate_spotify_authorize_url(code_challenge=code_challenge))

    server_thread.join()


def authenticate_for_remote():
    pass