import datetime
import re

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple

from ray import logger

__all__ = ['Weapons', 'BitTypes', 'HistoryTypes', 'ChunkTypes',
           'EventTypes', 'Elimination', 'Stats', 'TeamStats', 'Header', 'HeaderTypes']


class Weapons(Enum):
    """ Enumeration of weapon types as they occur in the replay """
    STORM = 0
    FALL = 1
    PISTOL = 2
    SHOTGUN = 3
    AR = 4
    SMG = 5
    SNIPER = 6
    PICKAXE = 7
    GRENADE = 8
    # UNKNOWN9 = 9
    GRENADELAUNCHER = 10
    RPG = 11
    MINIGUN = 12
    # BOW = 13
    TRAP = 14
    FINALLYELIMINATED = 15
    # UNKNOWN16 = 16
    # UNKNOWN17 = 17 bleed out by storm?
    VEHICLE = 21
    LMG = 22
    GASNADE = 23
    OUTOFBOUND = 24
    # TURRET = 25
    TEAMSWITCH = 26
    # UNKNOWN27 = 27 TURRET HEADSHOT?
    # UNKNOWN28 = 28
    # UNKNOWN29 = 29
    # UNKNOWN32 = 32
    # UNKNOWN34 = 34
    # UNKNOWN35 = 35
    # BIPLANE_GUNS = 38
    # BIPLANE_GUNS = 39
    # UNKNOWN40 = 40
    MISSING = 99

    @classmethod
    def _missing_(cls, value):
        logger.error(f'Missing weapon type {value}')
        return cls.MISSING


class BitTypes(Enum):
    """ See bitstring for more types """
    INT_32 = 'intle:32'
    UINT8 = 'uint:8'
    UINT_16 = 'uintle:16'
    UINT_32 = 'uintle:32'
    UINT_64 = 'uintle:64'
    FLOAT_LE_32 = 'floatle:32'
    BIT = 'bin:1'
    BYTE = 'bytes:1'
    BOOL = 'bool'


class ChunkTypes(Enum):
    """ Replay chunk types as defined by Unreal Engine """
    HEADER = 0
    REPLAYDATA = 1
    CHECKPOINT = 2
    EVENT = 3


class HistoryTypes(Enum):
    """ Replay history types """
    HISTORY_INITIAL = 0
    HISTORY_FIXEDSIZE_FRIENDLY_NAME = 1
    HISTORY_COMPRESSION = 2
    HISTORY_RECORDED_TIMESTAMP = 3


class HeaderTypes(Enum):
    """ Replay header types """
    HEADER_GUID = 11


class EventTypes(Enum):
    """ Replay event types """
    PLAYER_ELIMINATION = 'playerElim'
    MATCH_STATS = 'AthenaMatchStats'
    TEAM_STATS = 'AthenaMatchTeamStats'


@dataclass
class Elimination:
    """ Elimination data """
    eliminated: str
    eliminator: str
    gun_type: int
    time: datetime
    knocked: bool = False
    weapon: str = field(init=False)

    def __post_init__(self):
        self.weapon = Weapons(self.gun_type).name
        if self.weapon == Weapons.MISSING.value:
            logger.error(self)

    def __repr__(self):
        elim_type = 'knocked' if self.knocked else 'eliminated'
        return f'{self.eliminated} got {elim_type} by {self.eliminator} with {self.gun_type}'


@dataclass
class Stats:
    """ Personal stats from a replay """
    unknown: int
    accuracy: float
    assists: int
    eliminations: int
    weapon_damage: int
    other_damage: int
    revives: int
    damage_taken: int
    damage_structures: int
    materials_gathered: int
    materials_used: int
    total_traveled: int


@dataclass
class TeamStats:
    """ Team stats from a replay """
    unknown: int
    position: int
    total_players: int


@dataclass
class Header:
    """ Fortnite replay header """
    network_version: int
    network_checksum: int
    engine_network_version: int
    game_network_protocol: int
    guid: str
    major: int
    minor: int
    patch: int
    changelist: int
    branch: str
    levelnames_and_times: List[Tuple[str, int]]
    flags: int
    game_specific_data: List[str]

    version_regex = re.compile(r'\+\+Fortnite\+Release\-(?P<major>\d+)\.(?P<minor>\d*)')
    _version = defaultdict(int)

    @property
    def version(self) -> dict:
        if self._version:
            return self._version

        match = self.version_regex.search(self.branch)
        if match:
            self._version =  {**self._version, **{k: int(v) for k,v in match.groupdict().items()}}
            return self._version
        return 0

    @version.setter
    def version(self, value: dict):
        self._version = value
