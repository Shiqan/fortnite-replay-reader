import datetime
import re

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple

from ray import logger

__all__ = ['BitTypes', 'HistoryTypes', 'ChunkTypes',
           'EventTypes', 'Elimination', 'Stats', 'TeamStats',
           'Header', 'HeaderTypes', 'PlayerTypes', 'PlayerId', 'Meta']


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
    HISTORY_STREAM_CHUNK_TIMES = 4
    HISTORY_FRIENDLY_NAME_ENCODING = 5
    HISTORY_ENCRYPTION = 6


class HeaderTypes(Enum):
    """ Replay header types """
    HISTORY_REPLAY_INITIAL = 1
    HISTORY_SAVE_ABS_TIME_MS = 2               # We now save the abs demo time in ms for each frame (solves accumulation errors)
    HISTORY_INCREASE_BUFFER = 3                # Increased buffer size of packets, which invalidates old replays
    HISTORY_SAVE_ENGINE_VERSION = 4            # Now saving engine net version + InternalProtocolVersion
    HISTORY_EXTRA_VERSION = 5                  # We now save engine/game protocol version, checksum, and changelist
    HISTORY_MULTIPLE_LEVELS = 6                # Replays support seamless travel between levels
    HISTORY_MULTIPLE_LEVELS_TIME_CHANGES = 7   # Save out the time that level changes happen
    HISTORY_DELETED_STARTUP_ACTORS = 8         # Save DeletedNetStartupActors inside checkpoints
    HISTORY_HEADER_FLAGS = 9                   # Save out enum flags with demo header
    HISTORY_LEVEL_STREAMING_FIXES = 10         # Optional level streaming fixes.
    HISTORY_SAVE_FULL_ENGINE_VERSION = 11      # Now saving the entire FEngineVersion including branch name
    HISTORY_HEADER_GUID = 12                   # Save guid to demo header
    HISTORY_CHARACTER_MOVEMENT = 13            # Change to using replicated movement and not interpolation
    HISTORY_CHARACTER_MOVEMENT_NOINTERP = 14   # No longer recording interpolated movement samples


class EventTypes(Enum):
    """ Replay event types """
    PLAYER_ELIMINATION = 'playerElim'
    MATCH_STATS = 'AthenaMatchStats'
    TEAM_STATS = 'AthenaMatchTeamStats'

class PlayerTypes(Enum):
    """ Player types """
    NAMELESS_BOT = 0x03
    NAMED_BOT = 0x10

@dataclass
class PlayerId:
    name: str
    guid: str
    is_player: bool

@dataclass
class Elimination:
    """ Elimination data """
    eliminated: str
    eliminator: str
    gun_type: int
    time: datetime
    knocked: bool = False

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

@dataclass
class Meta:
    """ Fortnite replay meta information """
    file_version: int
    lenght_in_ms: int
    network_version: int
    change_list: int
    friendly_name: str
    is_live: bool
    time_stamp: int
    is_compressed: bool
    is_encrypted: bool
    encryption_key: bytes
