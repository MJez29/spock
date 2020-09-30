import click
import tekore as tk
from tekore.model import Device, RepeatState, \
        FullArtistOffsetPaging, SimpleAlbumPaging, SimplePlaylistPaging, FullTrackPaging
from spock.state import State
from spock.authenticate import authenticate
from functools import wraps
from fuzzywuzzy import fuzz
import itertools
from spock.config import CLIENT_ID

def get_track_info_string(result):
    if result.type == "track":
        return f"{result.type} '{result.name}' from '{result.album.name}' by '{', '.join(map(lambda x: x.name, result.artists))}'"
    if result.type == "album":
        return f"{result.type} '{result.name}' by '{', '.join(map(lambda x: x.name, result.artists))}'"
    elif result.type == "playlist":
        ret = f"{result.type} '{result.name}' by {result.owner.display_name}"
        if result.description:
            ret += f': "{result.description}"'
        return ret
    elif result.type == "artist":
        return f"{result.type} '{result.name}'"

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
        self.user.playback_previous()
        return self.user.playback()

    @check_auth
    def volume_up(self):
        context = self.user.playback()
        new_level = min(100, context.device.volume_percent + 10)
        self.user.playback_volume(new_level)
        return new_level

    @check_auth
    def volume_down(self):
        context = self.user.playback()
        new_level = max(0, context.device.volume_percent - 10)
        self.user.playback_volume(new_level)
        return new_level

    @check_auth
    def volume(self, level):
        if level < 0 or level > 100:
            raise ValueError("Level must be between 0 and 100 inclusive")
        self.user.playback_volume(level)
        return level

    @check_auth
    def shuffle(self, shuffle_state=None):
        if shuffle_state is None:
            context = self.user.playback()
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
    def get_search_results(
        self,
        query,
        use_library=False,
        artist=False,
        album=False,
        track=False,
        playlist=False,
        limit=5
    ):
        if not query and not use_library:
            return {}
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
        results = {}
        # source from user library
        if use_library:
            if "playlist" in types:
                results['playlist'] = self.user.all_items(self.user.playlists(self.user.current_user().id))

            if "album" in types:
                results['album'] = [x.album for x in self.user.all_items(self.user.saved_albums())]

            if "track" in types:
                results['track'] = [x.track for x in self.user.all_items(self.user.saved_tracks())]

        # source from global search
        else:
            search = self.user.search(query, tuple(types), limit=limit)
            for collection in search:
                if isinstance(collection, FullArtistOffsetPaging):
                    results['artist'] = collection.items
                elif isinstance(collection, SimpleAlbumPaging):
                    results['album'] = collection.items
                elif isinstance(collection, SimplePlaylistPaging):
                    results['playlist'] = collection.items
                elif isinstance(collection, FullTrackPaging):
                    results['track'] = collection.items
        
        return results

    @check_auth
    def play(
        self,
        query,
        use_library=False,
        artist=False,
        album=False,
        track=False,
        playlist=False,
    ):
        search_res = self.get_search_results(
                query,
                use_library=use_library,
                artist=artist,
                album=album,
                track=track,
                playlist=playlist)

        results = []
        for t, items in search_res.items():
            results.extend(items)

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

    @check_auth
    def play_object(self, obj):
        if obj.type == "track":
            self.user.playback_start_tracks([obj.id])
        else:
            self.user.playback_start_context(obj.uri)
        return obj

    def auth(self):
        token = authenticate()
        self.state.set_refresh_token(token.refresh_token)
