import os


def is_windows():
    return os.name == 'nt'


def flush():
    if is_windows():
        os.system('ipconfig /flushdns')
    else:
        raise NotImplementedError
