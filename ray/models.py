#!/usr/bin/python
# -*- coding: utf-8 -*-

import datetime
from enum import Enum

from dataclasses import dataclass, field


class Weapons(Enum):
    STORM = 0
    FALL = 1
    PISTOL = 2
    SHOTGUN = 3
    AR = 4
    SMG = 5
    SNIPER = 6
    PICKAXE = 7
    GRENADE = 8
    GRENADELAUNCHER = 10
    RPG = 11
    MINIGUN = 12
    BOW = 13
    TRAP = 14
    FINALLYELIMINATED = 15
    UNKNOWN17 = 17
    GASNADE = 23
    UNKNOWN24 = 24
    TEAMSWITCH = 26
    UNKNOWN28 = 28


class BitTypes(Enum):
    '''See bitstring for more types'''
    UINT8 = 'uint:8'
    INT_32 = 'intle:32'
    UINT_32 = 'uintle:32'
    UINT_64 = 'uintle:64'
    FLOAT_LE_32 = 'floatle:32'
    BIT = 'bin:1'
    BYTE = 'bytes:1'
    BOOL = 'bool'

class ChunkTypes(Enum):
    HEADER = 0
    REPLAYDATA = 1
    CHECKPOINT = 2
    EVENT = 3

class HistoryTypes(Enum):
    HISTORY_INITIAL = 0
    HISTORY_FIXEDSIZE_FRIENDLY_NAME = 1
    HISTORY_COMPRESSION = 2
    HISTORY_RECORDED_TIMESTAMP = 3

class EventTypes(Enum):
    PLAYER_ELIMINATION = 'playerElim'
    MATCH_STATS = 'AthenaMatchStats'
    TEAM_STATS = 'AthenaMatchTeamStats'

@dataclass
class Elimination:
    eliminated: str
    eliminator: str
    gun_type: int
    time: datetime
    knocked: bool = False
    weapon: str = field(init=False)

    def __post_init__(self):
        self.weapon = Weapons(self.gun_type).name

    def __repr__(self):
        return '{eliminated} got {event} by {eliminator} with {gun_type}'.format(eliminated=self.eliminated, event=('knocked' if self.knocked else 'eliminated'), eliminator=self.eliminator, gun_type=self.weapon)


@dataclass
class Stats:
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
    unknown: int
    position: int
    total_players: int
