import sqlite3

from evex.utils import get_resource

def db():
    return sqlite3.connect(get_resource("sde.sqlite"))


def get_solar_system_names() -> list[str]:
    with db() as con:
        cur = con.cursor()
        res = cur.execute(f"SELECT solarSystemName FROM mapSolarSystems")

        system_names = list(map(lambda a: a[0],res.fetchall()))
        system_names.append("current")

        return system_names


def get_solar_system_name(solar_system_id: int) -> str:
    with db() as con:
        cur = con.cursor()
        res = cur.execute(f"SELECT solarSystemName FROM mapSolarSystems WHERE solarSystemID = ?", [solar_system_id])
        name = res.fetchone()
    
        return name[0] if name else None

def get_solar_system_id(name: str) -> int:
    with db() as con:
        cur = con.cursor()
        res = cur.execute(f"SELECT solarSystemID FROM mapSolarSystems WHERE lower(solarSystemName) = ?", [name.lower()])
        sid = res.fetchone()
    
        return sid[0] if sid else None
