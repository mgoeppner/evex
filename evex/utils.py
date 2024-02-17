import os

def get_resource(name: str) -> str:
    return os.path.join(os.path.abspath(os.getcwd()), fr'resources/{name}')


