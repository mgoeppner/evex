from enum import Enum
import time
from typing import Callable
import webbrowser

from pydantic import BaseModel
from PySide6 import QtGui
import requests

from evex.models import EsiCharacter
from evex.esi import set_destination as esi_set_destination, get_character_location
from evex.sde import get_solar_system_id, get_solar_system_name


class CompletionType(str, Enum):
    NONE = "none"
    COMMAND = "command"
    SYSTEM = "system"
    CHARACTER = "character"


class CommandPredicate(BaseModel):
    text: str
    arg_completion_type: CompletionType


class Command(BaseModel):
    modifiers: list[str] = []
    predicates: list[CommandPredicate]
    action: Callable[[EsiCharacter, str, list[str]], None]

    def match(self, input: str) -> bool:
        potential_matches = self.generate_command_completions()

        for p in potential_matches:
            if input.startswith(p):
                return True

        return False


    def parse(self, input: str) -> tuple[str | None, list[str]]:
        modifier: str | None = None
        for m in self.modifiers:
            if input.startswith(m):
                modifier = m
                break

        input_without_modifier = input.replace(modifier, "").strip() if modifier else input.strip()

        has_next_predicate = len(self.predicates) > 0
        predicate_index: int = 0
        args: list[str] = []
        while(has_next_predicate):
            has_next_predicate = len(self.predicates) - 1 > predicate_index
            current_predicate = self.predicates[predicate_index]
            next_predicate = self.predicates[predicate_index + 1] if has_next_predicate else None

            arg = input_without_modifier.split(f"{current_predicate.text} ")[-1].strip()
            if next_predicate:
                arg = arg.split(f"{next_predicate.text} ")[0].strip()

            args.append(arg)

            predicate_index = predicate_index + 1

        return (modifier, args)


    def generate_command_completions(self) -> list[str]:
        completions = []

        intent = self.predicates[0].text

        completions.append(intent)
        for modifier in self.modifiers:
            completions.append(f"{modifier} {intent}")

        return completions

        
def show_kills(character: EsiCharacter, modifier: str, args: list[str]):
    if not len(args):
        return

    name = args[0]

    system_id = None
    if name == "current":
        system_id = get_character_location(character)
    else:
        system_id = get_solar_system_id(name)

    if system_id:
        webbrowser.open_new_tab(f"https://zkillboard.com/system/{system_id}/")


def set_destination(character: EsiCharacter, modifier: str, args: list[str]):
    if not len(args):
        return

    name = args[0]
    system_id = get_solar_system_id(name)

    if system_id:
        esi_set_destination(character, system_id)


def add_waypoint(character: EsiCharacter, modifier: str, args: list[str]):
    if not len(args):
        return

    name = args[0]
    system_id = get_solar_system_id(name)

    if system_id:
        esi_set_destination(character, system_id, False, False)


def appraise_clipboard(character: EsiCharacter, modifier: str, args: list[str]):
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    params = {
        "pasteblock": QtGui.QClipboard().text(),
        "region": "10000002",
    }

    response = requests.post("https://market.fuzzwork.co.uk/appraisal/", params, headers=headers, allow_redirects=False)
    response.raise_for_status()

    appraisal_url = f"https://market.fuzzwork.co.uk{response.headers['Location']}"

    QtGui.QClipboard().setText(appraisal_url)
    webbrowser.open_new_tab(appraisal_url)


def dscan_clipboard(character: EsiCharacter, modifier: str, args: list[str]):
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    params = {
        "paste": QtGui.QClipboard().text(),
    }

    response = requests.post(f"https://dscan.info/?_={time.time()}", params, headers=headers, allow_redirects=False)
    response.raise_for_status()

    dscan_id = str(response.content).strip("\'").split(";")[-1]
    dscan_url = f"https://dscan.info/v/{dscan_id}"

    QtGui.QClipboard().setText(dscan_url)
    webbrowser.open_new_tab(dscan_url)


def jump_range(character: EsiCharacter, modifier: str, args: list[str]):
    if len(args) != 1:
        return

    ship = "Archon"
    if modifier == "blops":
        ship = "Marshal"
    elif modifier == "super":
        ship = "Avatar"
    elif modifier == "jf" or modifier == "rorq":
        ship = "Rhea"

    from_system = args[0]

    if from_system == "current":
        from_system = get_solar_system_name(get_character_location(character))

        if not from_system:
            from_system = args[0]

    from_system = from_system.replace(" ", "_")
    
    webbrowser.open_new_tab(f"https://evemaps.dotlan.net/range/{ship},5/{from_system}")

def jump_plan(character: EsiCharacter, modifier: str, args: list[str]):
    if len(args) != 2:
        return

    ship = "Archon"
    if modifier == "blops":
        ship = "Marshal"
    elif modifier == "super":
        ship = "Avatar"
    elif modifier == "jf" or modifier == "rorq":
        ship = "Rhea"

    from_system = args[0]

    if from_system == "current":
        from_system = get_solar_system_name(get_character_location(character))

        if not from_system:
            from_system = args[0]

    from_system = from_system.replace(" ", "_")

    to_system = args[-1].replace(" ", "_")

    webbrowser.open_new_tab(f"https://evemaps.dotlan.net/jump/{ship},544/{from_system}:{to_system}")


COMMANDS = [
    Command(
        predicates=[
            CommandPredicate(text="show kills in", arg_completion_type=CompletionType.SYSTEM),
        ],
        action=show_kills,
    ),
    Command(
        predicates=[
            CommandPredicate(text="set destination", arg_completion_type=CompletionType.SYSTEM),
        ],
        action=set_destination,
    ),
    Command(
        predicates=[
            CommandPredicate(text="add waypoint", arg_completion_type=CompletionType.SYSTEM),
        ],
        action=add_waypoint,
    ),
    Command(
        predicates=[
            CommandPredicate(text="appraise clipboard", arg_completion_type=CompletionType.NONE),
        ],
        action=appraise_clipboard,
    ),
    Command(
        predicates=[
            CommandPredicate(text="dscan clipboard", arg_completion_type=CompletionType.NONE),
        ],
        action=dscan_clipboard,
    ),
    Command(
        modifiers=["super", "blops", "jf", "rorq"],
        predicates=[
            CommandPredicate(text="jump range", arg_completion_type=CompletionType.SYSTEM),
        ],
        action=jump_range,
    ),
    Command(
        modifiers=["super", "blops", "jf", "rorq"],
        predicates=[
            CommandPredicate(text="jump plan from", arg_completion_type=CompletionType.SYSTEM),
            CommandPredicate(text="to", arg_completion_type=CompletionType.SYSTEM),
        ],
        action=jump_plan,
    ),
]

def generate_command_completions():
    completions = []
    for command in COMMANDS:
        completions.extend(command.generate_command_completions())

    return completions
