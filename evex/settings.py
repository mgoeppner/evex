from pathlib import Path
from typing import Dict

from pydantic_settings import BaseSettings

from evex.models import EsiCharacter


class HotkeySettings(BaseSettings):
    trigger: str = "<alt>+j"


class Settings(BaseSettings):
    characters: Dict[int, EsiCharacter] = {}
    hotkeys: HotkeySettings = HotkeySettings()


def save_settings(settings: Settings):
    settings_path = Path.joinpath(Path.home(), ".config", "evex", "settings.json")

    with open(settings_path, "w") as settings_file:
        settings_file.write(settings.model_dump_json(indent=2))


def load_settings() -> Settings:
    settings_path = Path.joinpath(Path.home(), ".config", "evex", "settings.json")

    if not settings_path.exists() or not settings_path.is_file():
        save_settings(Settings())

    with open(settings_path, "r") as settings_file:
        return Settings.model_validate_json(settings_file.read())
