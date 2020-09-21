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
    @wraps(func)
    def invoke(*args, **kwargs):
        try:
            user = args[0].get_user()
            if user is None:
                print("Authentication is needed, run spock auth")
                return
            kwargs['user'] = user
            return func(*args, **kwargs)
        except (tk.Forbidden, tk.NotFound) as e:
            # TODO better error messages
            print(e)

    return invoke


@click.group()
@click.pass_context
def spock(ctx):
    state = State(default_client_id=SPOCK_CLIENT_ID)
    ctx.obj = state


@spock.command()
@click.pass_obj
@spotify_invoker
def resume(state, user):
    user.playback_resume()
    print("Resuming")


@spock.command()
@click.pass_obj
@spotify_invoker
def pause(state, user):
    user.playback_pause()
    print("Pausing")


@spock.command()
@click.pass_obj
@spotify_invoker
def next(state, user):
    user.playback_next()
    print('Going to next')


@spock.command()
@click.pass_obj
@spotify_invoker
def prev(state, user):
    user.playback_previous()
    print('Going to previous')


@spock.command()
@click.pass_obj
@click.argument('level', type=click.IntRange(0, 100))
@spotify_invoker
def volume(state, user, level):
    user.playback_volume(level)
    print(f'Setting volume to {level}')


@spock.command()
@click.argument('shuffle_state', required=True, type=click.BOOL)
@click.pass_obj
@spotify_invoker
def shuffle(state, user, shuffle_state):
    user.playback_shuffle(shuffle_state)
    # TODO remember state for toggle
    if shuffle_state:
        print('Shuffle on')
    else:
        print('Shuffle off')


@spock.command()
@click.argument('repeat_state', required=True, type=click.Choice(['track', 'context', 'off']))
@click.pass_obj
@spotify_invoker
def repeat(state, user, repeat_state):
    user.playback_repeat(repeat_state)
    # TODO remember state for cycle
    print(f'Setting repeat to {repeat_state}')


@spock.command()
@click.pass_obj
@spotify_invoker
def devices(state, user):
    device_list = user.playback_devices()
    for dev in device_list:
        print(dev)


@spock.command()
@click.argument('devname', type=click.STRING)
@click.pass_obj
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
        print(f'Switching to device {best_device.name}')
    else:
        print(f'No device found for query {devname}')


@spock.command()
@click.option('-l')
@click.option('-a')
@click.option('-b')
@click.option('-t')
@click.option('-p')
@click.argument('name', type=click.STRING)
@click.pass_obj
@spotify_invoker
def play(state, user: tk.Spotify, name, l=False, a=False, b=False, t=False, p=False):
    if l:
        # TODO library search support (pain)
        types = ('track',)
    elif a:
        types = ('artist',)
    elif b:
        types = ('album',)
    elif t:
        types = ('track',)
    elif p:
        types = ('playlist',)
    else:
        types = ('track', 'album', 'playlist', 'artist')

    # flatten results across different categories into list
    results = list(itertools.chain(*[list(x.items) for x in user.search(name, types, limit=1)]))
    if not results:
        print(f'No results found for query {name}')
        return

    # find best match irrespective of category by name
    scorer = lambda x: fuzz.partial_ratio(name, x.name)
    best_result = max(results, key=scorer)
    if isinstance(best_result, tk.model.FullTrack):
        user.playback_start_tracks([best_result.id])
    else:
        user.playback_start_context(best_result.uri)

    print(f'Playing {best_result.name}')


if __name__ == '__main__':
    spock()
