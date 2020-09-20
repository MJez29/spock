import click

@click.group()
def spock():
    pass

@spock.command()
def resume():
    print('Resuming')

@spock.command()
def pause():
    print('Pausing')

@spock.command()
def next():
    print('Going to next')

@spock.command()
def prev():
    print('Going to previous')

@spock.command()
@click.argument('level', type=click.IntRange(0, 100))
def volume(level):
    print(f'Setting volume to {level}')

@spock.command()
@click.argument('state', required=False, type=click.BOOL)
def shuffle(state):
    if state is None:
        print('Toggling shuffle')
    else:
        if state:
            print('Shuffle on')
        else:
            print('Shuffle off')

@spock.command()
@click.argument('state', required=False, type=click.Choice(['song', 'context', 'off']))
def repeat(state):
    if state is None:
        print('Toggling repeat')
    else:
        print(f'Setting repeat to {state}')

@spock.command()
def devices():
    print('Listing devices')

@spock.command()
@click.argument('devname', type=click.STRING)
def device(devname):
    print(f'Switching to device {devname}')

@spock.command()
@click.option('-l')
@click.option('-a')
@click.option('-b')
@click.option('-t')
@click.option('-p')
@click.argument('name', type=click.STRING)
def play(name, l=False, a=False, b=False, t=False, p=False):
    print(f'Playing {name}')

if __name__ == '__main__':
    spock()
