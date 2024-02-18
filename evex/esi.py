import asyncio
import base64
import hashlib
import requests
import secrets
import socket
import time
import webbrowser

from contextlib import contextmanager
from urllib import parse
from urllib.parse import urlencode

from jose import jwt

from evex.models import EsiCharacter
from evex.settings import load_settings, save_settings

CLIENT_ID = "1b677fbf08124810a442ba019ee4f1b8"

JWKS_URL = "https://login.eveonline.com/oauth/jwks"
AUTH_URL = "https://login.eveonline.com/v2/oauth/authorize/"
TOKEN_URL = "https://login.eveonline.com/v2/oauth/token/"

ESI_BASE_URL = "https://esi.evetech.net/latest"

JWK_ALGORITHM = "RS256"
JWK_ISSUERS = ("login.eveonline.com", "https://login.eveonline.com")
JWK_AUDIENCE = "EVE Online"


def decode_token(token: str):
    response = requests.get(JWKS_URL)
    response.raise_for_status()

    jwks = response.json()

    jwk = [item for item in jwks["keys"] if item["alg"] == JWK_ALGORITHM].pop()

    return jwt.decode(token=token, key=jwk, algorithms=jwk["alg"], issuer=JWK_ISSUERS, audience=JWK_AUDIENCE)


def generate_challenge():
    random = base64.urlsafe_b64encode(secrets.token_bytes(32))
    m = hashlib.sha256()
    m.update(random)
    d = m.digest()
    code_challenge = base64.urlsafe_b64encode(d).decode().replace("=", "")

    return (code_challenge, random)


async def login() -> EsiCharacter:
    code_challenge, code_verifier = generate_challenge()

    auth_params = {
        "response_type": "code",
        "redirect_uri": "http://localhost:42069",
        "client_id": CLIENT_ID,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "scope": "publicData esi-location.read_location.v1 esi-location.read_ship_type.v1 esi-ui.open_window.v1 esi-ui.write_waypoint.v1 esi-location.read_online.v1",
        "state": "evex-login",
    }

    webbrowser.open(f"{AUTH_URL}?{urlencode(auth_params)}")

    loop = asyncio.get_event_loop()

    # FIXME: warcrimes below
    with socket_server(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", 42069))
        sock.listen(1)

        conn, address = await loop.sock_accept(sock)
        while True:
            data = await loop.sock_recv(conn, 1024)
            if not data or "code=" in data.decode("utf-8"):
                break

        request = data.decode("utf-8").split("\r\n")
        url = request[0].split(" ")[1]
        query = dict(parse.parse_qsl(parse.urlparse(url).query))

        if query.get("state") != auth_params["state"]:
            raise Exception("invalid state!")

        code = query.get("code")

        if not code:
            failure_body = "<html><body><h1>evex login failure</h1><p>please try again!</p></body></html>"
            await loop.sock_sendall(conn, bytes(f"HTTP/1.1 200\r\nContent-Type: text/html\r\nContent-Length: {len(failure_body)}\r\n\r\n{failure_body}", "utf-8"))
            raise Exception("missing code!")

        success_body = "<html><body><h1>evex login success</h1><p>you may close this page!</p></body></html>"
        await loop.sock_sendall(conn, bytes(f"HTTP/1.1 200\r\nContent-Type: text/html\r\nContent-Length: {len(success_body)}\r\n\r\n{success_body}", "utf-8"))


    token_params = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "code": code,
        "code_verifier": code_verifier,
    }

    response = requests.post(TOKEN_URL, data=token_params)
    response.raise_for_status()

    result = response.json()

    claims = decode_token(result["access_token"])

    character_id = claims["sub"].replace("CHARACTER:EVE:", "")
    character = EsiCharacter(
         id=character_id,
         name=claims["name"],
         access_token=result["access_token"],
         refresh_token=result["refresh_token"],
         expires_at=claims["exp"],
    )

    return character


def refresh(character: EsiCharacter) -> EsiCharacter:
    refresh_params = {
        "grant_type": "refresh_token",
        "refresh_token": character.refresh_token,
        "client_id": CLIENT_ID,
    }

    response = requests.post(TOKEN_URL, data=refresh_params)
    response.raise_for_status()

    result = response.json()

    claims = decode_token(result["access_token"])

    if character.name != claims["name"]:
        raise Exception("bad character refresh!")

    character.access_token = result["access_token"]
    character.expires_at = claims["exp"]
    character.refresh_token = result["refresh_token"]

    settings = load_settings()
    settings.characters[character.id] = character
    save_settings(settings)

    return character


def get_auth_headers(character: EsiCharacter) -> dict:
    if time.time() >= character.expires_at:
        character = refresh(character)

    headers = {
        "Authorization": f"Bearer {character.access_token}"
    }

    return headers


def set_destination(character: EsiCharacter, destination_id: str, add_to_beginning=True, clear_other_waypoints=True):
    response = requests.post(
        f"{ESI_BASE_URL}/ui/autopilot/waypoint/?add_to_beginning={str(add_to_beginning).lower()}&clear_other_waypoints={str(clear_other_waypoints).lower()}&datasource=tranquility&destination_id={destination_id}",
        headers=get_auth_headers(character)
    )
    response.raise_for_status()


def get_character_location(character: EsiCharacter):
    response = requests.get(
        f"{ESI_BASE_URL}/characters/{character.id}/location/",
        headers=get_auth_headers(character)
    )
    response.raise_for_status()

    location = response.json()

    return location["solar_system_id"]


'''
def get_portrait(esi_character) -> QtGui.QPixmap:
    portrait_url = f"https://images.evetech.net/characters/{esi_character.id}/portrait?size=32"
    response = requests.get(portrait_url)
    response.raise_for_status()

    pixmap = QtGui.QPixmap()
    pixmap.loadFromData(response.content)

    return pixmap
'''



@contextmanager
def socket_server(*args, **kwargs):
    s = socket.socket(*args, **kwargs)
    try:
        yield s
    finally:
        s.close()
