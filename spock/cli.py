import click
import tekore as tk
from spock.state import State
from spock.authenticate import authenticate
from spock.interface import Spock, get_track_info_string
from functools import wraps
from fuzzywuzzy import fuzz
import itertools
from spock.config import CLIENT_ID


@click.group()
@click.pass_context
def spock(ctx):
    spock_interface = Spock()
    ctx.obj = spock_interface


@spock.command()
@click.pass_obj
def resume(spock_interface):
    playback = spock_interface.resume()
    if playback:
        print(f"Resuming {get_track_info_string(playback.item)}")


@spock.command()
@click.pass_obj
def pause(spock_interface):
    res = spock_interface.pause()
    if res:
        action, playback = res
        if action:
            print(f"Pausing {get_track_info_string(playback.item)}")
        else:
            print(f"Resuming {get_track_info_string(playback.item)}")


@spock.command()
@click.pass_obj
def next(spock_interface):
    playback = spock_interface.next()
    if playback:
        print(f"Going to next {get_track_info_string(playback.item)}")


@spock.command()
@click.pass_obj
def prev(spock_interface):
    playback = spock_interface.prev()
    if playback:
        print(f"Going to previous {get_track_info_string(playback.item)}")


@spock.command()
@click.argument("level", type=click.IntRange(0, 100))
@click.pass_obj
def volume(spock_interface, level):
    try:
        spock_interface.volume(level)
    except:
        print("Unable to set volume for this device")
        return
    print(f"Setting volume to {level}")


@spock.command()
@click.argument("shuffle_state", required=False, type=click.BOOL)
@click.pass_obj
def shuffle(spock_interface, shuffle_state):
    playback = spock_interface.shuffle(state)
    if playback:
        if playback.shuffle_state:
            print("Shuffle on")
        else:
            print("Shuffle off")


@spock.command()
@click.argument(
    "repeat_state", required=False, type=click.Choice(["track", "context", "off"])
)
@click.pass_obj
def repeat(spock_interface, repeat_state):
    playback = spock_interface.repeat(repeat_state)
    if playback:
        print(f"Setting repeat to {playback.repeat_state}")


@spock.command()
@click.pass_obj
def devices(spock_interface):
    device_list = spock_interface.get_devices()
    if device_list:
        for dev in device_list:
            print(f"{'*' if dev.is_active else ''}{dev.name} on {dev.type}")
    else:
        print("No devices found")


@spock.command()
@click.argument("devname", type=click.STRING)
@click.pass_obj
def device(spock_interface, devname):
    dev = spock_interface.use_device(devname)
    if dev:
        print(f"Switching to device {dev.name} on {dev.type}")
    else:
        print(f"No device found for query '{devname}'")


@spock.command()
@click.option("-l", "--library", is_flag=True)
@click.option("-a", "--artist", is_flag=True)
@click.option("-b", "--album", is_flag=True)
@click.option("-t", "--track", is_flag=True)
@click.option("-p", "--playlist", is_flag=True)
@click.argument("name", nargs=-1)
@click.pass_obj
def play(
    spock_interface,
    name,
    library=False,
    artist=False,
    album=False,
    track=False,
    playlist=False,
):
    query = " ".join(name)
    res = spock_interface.play(
        query,
        use_library=library,
        artist=artist,
        album=album,
        track=track,
        playlist=playlist,
    )
    if res:
        print(f"Now playing {get_track_info_string(res)}")
    else:
        print(f"No results found for query '{query}'")


@spock.command()
@click.option("-r", "--for-remote", is_flag=True)
@click.option("-k", "--key")
@click.pass_obj
def auth(spock_interface, key, for_remote):
    if key:
        spock_interface.auth_with_key(key=key)
    else:
        spock_interface.auth(remote=for_remote)


if __name__ == "__main__":
    spock()
