import secrets
import hashlib
import base64
import webbrowser
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import requests

from spock.config import CLIENT_ID, REDIRECT_URI, PORT
from spock.templates.template import get_authorized_page, get_error_page
from spock.access_token import AccessToken

CODE_VERIFIER_MIN_LENGTH = 43
CODE_VERIFIER_MAX_LENGTH = 128
CODE_VERIFIER_CHARACTERS = (
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890-_.~"
)


def generate_code() -> (str, str):
    """
    Generates a (code_verifier, code_challenge) pair where code_verifier is a cryptographically random
    string and code_challenge is the base64urlencoded string (with right '=' removed) of the sha256 hash of the code_verifier.
    """
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

    return (code_verifier, code_challenge.decode().rstrip("="))


STATE_CHARACTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"


def generate_state(remote) -> str:
    """
    Generates a cryptographically secure random string for CSRF protection.
    """
    state = "".join(secrets.choice(STATE_CHARACTERS) for i in range(64))
    return ("remote-" if remote else "local-") + state


def generate_spotify_authorize_url(code_challenge, state):
    """
    Returns the Spotify URL to begin the authorization process for a user.
    """
    return "https://accounts.spotify.com/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&state={state}&code_challenge={code_challenge}&code_challenge_method=S256".format(
        code_challenge=code_challenge,
        client_id=CLIENT_ID,
        redirect_uri=REDIRECT_URI,
        scope="user-read-playback-state user-modify-playback-state user-read-currently-playing streaming playlist-read-collaborative playlist-read-private user-library-read",
        state=state,
    )


def merge_kwargs(kwargs1, kwargs2):
    kwargs1.update(kwargs2)
    return kwargs1


class AuthorizationServer:
    """
    Runs a server to capture a Spotify authorization code. Once wait_for_stop()
    has returned the code is accessible from authorization_code.
    """

    def __init__(self, state):
        self.server_started_event = threading.Event()
        self.state = state

        self.authorization_code = None
        self.authorization_attempted_event = threading.Event()

        self.server_thread = threading.Thread(target=self.listen)
        self.server_thread.start()

    def wait_for_start(self):
        """
        A blocking function that will only return once the server has started.
        """
        self.server_started_event.wait()

    def wait_for_stop(self):
        """
        A blocking function that will only return once the server has stopped.
        """
        self.server_thread.join()

    def listen(self):
        with HTTPServer(
            ("", PORT),
            SpotifyRedirectRequestHandler.partial_init(
                state=self.state,
                set_authorization_code=self.set_authorization_code,
                authorization_attempted_event=self.authorization_attempted_event,
            ),
        ) as server:
            self.server_started_event.set()
            while not self.authorization_attempted_event.is_set():
                server.handle_request()

    def set_authorization_code(self, code):
        self.authorization_code = code


class SpotifyRedirectRequestHandler(BaseHTTPRequestHandler):
    STATE_MISMATCH = "state_mismatch"
    MISSING_ARGS = "missing_arguments"
    INVALID_PATH = "invalid_path"

    @staticmethod
    def partial_init(**kwargs):
        return lambda *largs, **lkwargs: SpotifyRedirectRequestHandler(
            *largs, **merge_kwargs(kwargs, lkwargs)
        )

    def __init__(self, *args, **kwargs):
        self.state = kwargs.pop("state")
        self.authorization_attempted_event = kwargs.pop("authorization_attempted_event")
        self.set_authorization_code = kwargs.pop("set_authorization_code")

        super().__init__(*args, **kwargs)

    def _handle_success(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        self.wfile.write(get_authorized_page())

    def _handle_error(self, error):
        self.send_response(400)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        self.wfile.write(get_error_page(error_code=error))

    def do_GET(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)

        if url.path == "/authorize":
            self.authorization_attempted_event.set()
            if "code" in query and "state" in query:
                if query["state"][0] == self.state:
                    self._handle_success()
                    self.set_authorization_code(query["code"][0])
                else:
                    self._handle_error(self.STATE_MISMATCH)
            elif "error" in query and "state" in query:
                if query["state"][0] == self.state:
                    self._handle_error(query["error"][0])
                else:
                    self._handle_error(self.MISSING_ARGS)
            else:
                self._handle_error(self.MISSING_ARGS)
        else:
            self._handle_error(self.INVALID_PATH)

    def log_message(self, format, *args):
        """
        Overriden from BaseHTTPRequestHandler to silence logging.
        """
        pass


def get_access_token(authorization_code: str, code_verifier: str):
    """
    Exchanges an authorization code for an access token with the Spotify API
    """
    response = requests.post(
        "https://accounts.spotify.com/api/token",
        data={
            "client_id": CLIENT_ID,
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": code_verifier,
        },
    )

    return AccessToken(**response.json())


def authenticate() -> AccessToken:
    code_verifier, code_challenge = generate_code()

    state = generate_state(remote=False)

    auth_server = AuthorizationServer(state=state)

    auth_server.wait_for_start()

    url = generate_spotify_authorize_url(code_challenge=code_challenge, state=state)

    print(f"Please visit {url} in a browser where you are logged in to Spotify.")

    webbrowser.open(url=url)

    auth_server.wait_for_stop()

    authorization_code = auth_server.authorization_code

    if not authorization_code:
        print("Authorization failed. Please try again.")
        return

    access_token = get_access_token(
        authorization_code=authorization_code, code_verifier=code_verifier
    )

    return access_token


def authenticate_for_remote():
    pass
