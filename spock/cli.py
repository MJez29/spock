import click
import tekore as tk
from spock.state import State
from functools import wraps
from fuzzywuzzy import fuzz
import itertools

# TODO change me to the actual client ID when auth is done
SPOCK_CLIENT_ID = None


def spotify_invoker(func):
    """
    Wrap spock command function invoking actions on spotify user with error checking
    :param func: Function accepting state
    :return: Wrapped function accepting state and user
    """

    @click.pass_obj
    @wraps(func)
    def invoke(*args, **kwargs):
        try:
            user = args[0].get_user()
            if user is None:
                print("Authentication is needed, run spock auth")
                return
            kwargs["user"] = user
            return func(*args, **kwargs)
        except (tk.Forbidden, tk.NotFound) as e:
            # TODO better error messages
            print(e)

    return invoke


def track_verbose(result):
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


@click.group()
@click.pass_context
def spock(ctx):
    state = State(default_client_id=SPOCK_CLIENT_ID)
    ctx.obj = state


@spock.command()
@spotify_invoker
def resume(state, user):
    user.playback_resume()
    print(f"Resuming {track_verbose(user.playback().item)}")


@spock.command()
@spotify_invoker
def pause(state, user):
    user.playback_pause()
    print(f"Pausing {track_verbose(user.playback().item)}")


@spock.command()
@spotify_invoker
def next(state, user):
    user.playback_next()
    print(f"Going to next {track_verbose(user.playback().item)}")


@spock.command()
@spotify_invoker
def prev(state, user):
    user.playback_previous()
    print(f"Going to previous {track_verbose(user.playback().item)}")


@spock.command()
@click.argument("level", type=click.IntRange(0, 100))
@spotify_invoker
def volume(state, user, level):
    user.playback_volume(level)
    print(f"Setting volume to {level}")


@spock.command()
@click.argument("shuffle_state", required=False, type=click.BOOL)
@spotify_invoker
def shuffle(state, user, shuffle_state):
    if shuffle_state is None:
        shuffle_state = False  # set a default so we don't 400 when no device active
        context = user.playback()
        if context is not None:
            shuffle_state = not context.shuffle_state

    user.playback_shuffle(shuffle_state)
    if shuffle_state:
        print("Shuffle on")
    else:
        print("Shuffle off")


REPEAT_STATES = ["track", "context", "off"]


@spock.command()
@click.argument("repeat_state", required=False, type=click.Choice(REPEAT_STATES))
@spotify_invoker
def repeat(state, user, repeat_state):
    if repeat_state is None:
        repeat_state = "off"  # set a default so we don't 400 when no device active
        context = user.playback()
        if context is not None:
            current_repeat_state = context.repeat_state
            repeat_state = REPEAT_STATES[
                (REPEAT_STATES.index(current_repeat_state) + 1) % len(REPEAT_STATES)
            ]
    user.playback_repeat(repeat_state)
    print(f"Setting repeat to {repeat_state}")


@spock.command()
@spotify_invoker
def devices(state, user):
    device_list = user.playback_devices()
    if device_list:
        for dev in device_list:
            print(f"{'*' if dev.is_active else ''}{dev.name} on {dev.type}")
    else:
        print("No devices found")


@spock.command()
@click.argument("devname", type=click.STRING)
@spotify_invoker
def device(state, user, devname):
    device_list = user.playback_devices()
    # find closest named device looking at name and type
    # e.g. name='Web Player (Chrome)', type='Computer'
    scorer = lambda dev: fuzz.partial_ratio(devname, f"{dev.name} {dev.type}")
    best_device = max(device_list, key=scorer)
    score = scorer(best_device)
    if best_device and score > 50:
        user.playback_transfer(best_device.id, force_play=True)
        print(f"Switching to device {best_device.name} on {best_device.type}")
    else:
        print(f"No device found for query '{devname}''")


@spock.command()
@click.option("-l", is_flag=True)
@click.option("-a", is_flag=True)
@click.option("-b", is_flag=True)
@click.option("-t", is_flag=True)
@click.option("-p", is_flag=True)
@click.argument("name", nargs=-1)
@spotify_invoker
def play(state, user: tk.Spotify, name, l=False, a=False, b=False, t=False, p=False):
    query = " ".join(name)
    if not query:
        print("No query")
        return

    if a:
        types = ("artist",)
    elif b:
        types = ("album",)
    elif t:
        types = ("track",)
    elif p:
        types = ("playlist",)
    else:
        types = ("playlist", "artist", "album", "track")

    # source from user library
    if l:
        results = []
        if "playlist" in types:
            results.extend(user.all_items(user.playlists(user.current_user().id)))
        if "album" in types:
            results.extend([x.album for x in user.all_items(user.saved_albums())])
        if "track" in types:
            results.extend([x.track for x in user.all_items(user.saved_tracks())])
    # source from global search
    else:
        # flatten results across different categories into list
        results = list(
            itertools.chain(
                *[list(x.items) for x in user.search(query, types, limit=1)]
            )
        )

    # find best match irrespective of category by name
    scorer = (
        lambda x: 0
        if x is None
        else fuzz.ratio(query.lower(), ascii(x.name).lower())
        + (x.popularity / 10 if x.type == "track" or x.type == "artist" else 0)
    )
    best_result = max(results, key=scorer, default=None)
    score = scorer(best_result)
    if score < 50:
        print(f"No results found for query '{query}''")
        return

    if best_result.type == "track":
        user.playback_start_tracks([best_result.id])
    else:
        user.playback_start_context(best_result.uri)
    print(f"Now playing {track_verbose(best_result)}")


if __name__ == "__main__":
    spock()
