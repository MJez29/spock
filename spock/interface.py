import click
import tekore as tk
from tekore.model import Device, RepeatState
from spock.state import State
from spock.authenticate import authenticate
from functools import wraps
from fuzzywuzzy import fuzz
import itertools
from spock.config import CLIENT_ID

class Spock:

    def __init__(self, default_client_id=CLIENT_ID):
        self.state = State(default_client_id)
        self.user = None

    def check_auth(func):
        """
        Wrap spock command function invoking actions on spotify user with error checking
        :param func: Function using self.user
        :return: Wrapped function
        """
        @wraps(func)
        def invoke(self, *args, **kwargs):
            try:
                self.user = self.state.get_user()
                if self.user is None:
                    print("Authentication is needed, run spock auth")
                    return
                return func(self, *args, **kwargs)
            except (tk.Forbidden, tk.NotFound) as e:
                # TODO better error messages
                print(e)

        return invoke

    @check_auth
    def resume(self):
        self.user.playback_resume()
        return self.user.playback()

    @check_auth
    def pause(self):
        context = self.user.playback()
        if context is not None and context.is_playing:
            self.user.playback_pause()
            return True, self.user.playback()
        else:
            self.user.playback_resume()
            return False, self.user.playback()

    @check_auth
    def next(self):
        self.user.playback_next()
        return self.user.playback()

    @check_auth
    def prev(self):
        self.user.playback_prev()
        return self.user.playback()

    @check_auth
    def volume(self, level):
        if level < 0 or level > 100:
            raise ValueError('Level must be between 0 and 100 inclusive')
        self.user.playback_volume(level)
        return self.user.playback()

    @check_auth
    def shuffle(self, shuffle_state=None):
        if shuffle_state is None:
            context = user.playback()
            if context is not None:
                shuffle_state = not context.shuffle_state
        self.user.playback_shuffle(shuffle_state)
        return self.user.playback()

    @check_auth
    def repeat(self, repeat_state):
        if repeat_state is None:
            repeat_state = RepeatState.off
            context = self.user.playback()
            if context is not None:
                if context.repeat_state == RepeatState.off:
                    repeat_state = RepeatState.track

        self.user.playback_repeat(repeat_state)
        return self.user.playback()

    @check_auth
    def get_devices(self):
        return self.user.playback_devices()

    @check_auth
    def use_device(self, device):
        if isinstance(device, Device):
            self.user.playback_transfer(device.id, force_play=True)
            return device

        device_list = self.user.playback_devices()
        # find closest named device looking at name and type
        # e.g. name='Web Player (Chrome)', type='Computer'
        scorer = lambda dev: fuzz.partial_ratio(device, f"{dev.name} {dev.type}")
        best_device = max(device_list, key=scorer)
        score = scorer(best_device)
        if best_device and score > 50:
            self.user.playback_transfer(best_device.id, force_play=True)
            return best_device

    @check_auth
    def use_device_by_id(self, dev_id):
        self.user.playback_transfer(dev_id, force_play=True)

    @check_auth
    def play(self, query, use_library=False,
            artist=False, album=False,
            track=False, playlist=False):
        if not query:
            return
        if isinstance(query, list):
            query = " ".join(query)

        types = []
        if artist:
            types.append("artist")
        if album:
            types.append("album")
        if track:
            types.append("track")
        if playlist:
            types.append("playlist")

        if not types:
            types = ["playlist", "artist", "album", "track"]

        # source from user library
        if use_library:
            results = []
            if "playlist" in types:
                results.extend(self.user.all_items(self.user.playlists(self.user.current_user().id)))
            if "album" in types:
                results.extend([x.album for x in self.user.all_items(self.user.saved_albums())])
            if "track" in types:
                results.extend([x.track for x in self.user.all_items(self.user.saved_tracks())])
        # source from global search
        else:
            # flatten results across different categories into list
            results = list(
                itertools.chain(
                    *[list(x.items) for x in self.user.search(query, types, limit=5)]
                )
            )

        # find best match irrespective of category by name
        scorer = (
            lambda x: 0
            if x is None
            else fuzz.ratio(query.lower(), ascii(x.name).lower())
            + (x.popularity if x.type in ["track", "artist"] else 0)
        )
        best_result = max(results, key=scorer, default=None)
        score = scorer(best_result)
        if score < 50:
            return

        if best_result.type == "track":
            self.user.playback_start_tracks([best_result.id])
        else:
            self.user.playback_start_context(best_result.uri)

        return best_result

    def auth(self):
        token = authenticate()
        self.state.set_refresh_token(token.refresh_token)
