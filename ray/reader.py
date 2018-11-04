#!/usr/bin/python
# -*- coding: utf-8 -*-

from datetime import datetime

import bitstring

from ray.exceptions import InvalidReplayException, ReadStringException
from ray.models import (BitTypes, ChunkTypes, Elimination, EventTypes,
                        HistoryTypes, Stats, TeamStats)

FILE_MAGIC = 0x1CA2E27F


class ConstBitStreamWrapper(bitstring.ConstBitStream):
    def read_uint32(self):
        return self.read(BitTypes.INT_32.value)

    def read_int32(self):
        return self.read(BitTypes.INT_32.value)

    def read_uint64(self):
        return self.read(BitTypes.UINT_64.value)

    def read_float32(self):
        return self.read(BitTypes.FLOAT_LE_32.value)

    def read_byte(self):
        return int.from_bytes(self.read(BitTypes.BYTE.value), byteorder='little')

    def read_string(self):
        size = self.read(BitTypes.INT_32.value)
        is_unicode = size < 0

        if is_unicode:
            size *= -2
            return self.read('bytes:'+str(size))[:-2].decode('utf-16')

        stream_bytes = self.read('bytes:'+str(size))
        string = stream_bytes[:-1]
        if stream_bytes[-1] != 0:
            raise ReadStringException('End of string not zero')

        try:
            return string.decode('utf-8')
        except UnicodeDecodeError:
            return string.decode('latin-1')


class Reader:
    def __init__(self, path):
        self.path = path
        self._file = None
        self.replay = None
        self.eliminations = []
        self.stats = None
        self.team_stats = None

    def __len__(self):
        return self.replay.len

    def __sizeof__(self):
        return self.replay.len

    def __repr__(self):
        return 'Replay file {path}'.format(path=self.path)

    def __enter__(self):
        self._file = open(self.path, 'r')
        self.replay = ConstBitStreamWrapper(self._file)
        self.parse_meta()
        self.parse_chunks()
        return self

    def __exit__(self, *args):
        self._file.close()

    def parse_meta(self):
        magic_number = self.replay.read_uint32()
        if (magic_number != FILE_MAGIC):
            raise InvalidReplayException()
        file_version = self.replay.read_uint32()
        lenght_in_ms = self.replay.read_uint32()
        network_version = self.replay.read_uint32()
        change_list = self.replay.read_uint32()
        friendly_name = self.replay.read_string()
        is_live = self.replay.read_uint32()

        if file_version >= HistoryTypes.HISTORY_RECORDED_TIMESTAMP.value:
            time_stamp = self.replay.read_uint64()
        if file_version >= HistoryTypes.HISTORY_COMPRESSION.value:
            is_compressed = self.replay.read_uint32()

    def parse_chunks(self):
        while (self.replay.pos < len(self.replay)):
            chunk_type = self.replay.read_uint32()
            chunk_size = self.replay.read_int32()
            offset = self.replay.bytepos

            if chunk_type == ChunkTypes.EVENT.value:
                event_id = self.replay.read_string()
                group = self.replay.read_string()
                metadata = self.replay.read_string()
                start_time = self.replay.read_uint32()
                end_time = self.replay.read_uint32()
                size = self.replay.read_uint32()

                if group == EventTypes.PLAYER_ELIMINATION.value:
                    self.replay.bytepos += 45
                    eliminated = self.replay.read_string()
                    eliminator = self.replay.read_string()
                    gun_type = self.replay.read_byte()
                    knocked = self.replay.read_uint32()

                    self.eliminations.append(Elimination(
                        eliminated=eliminated,
                        eliminator=eliminator,
                        gun_type=gun_type,
                        time=datetime.fromtimestamp(start_time/1000.0),
                        knocked=knocked))

                if metadata == EventTypes.MATCH_STATS.value:
                    unknown = self.replay.read_uint32()
                    accuracy = self.replay.read_float32()
                    assists = self.replay.read_uint32()
                    eliminations = self.replay.read_uint32()
                    weapon_damage = self.replay.read_uint32()
                    other_damage = self.replay.read_uint32()
                    revives = self.replay.read_uint32()
                    damage_taken = self.replay.read_uint32()
                    damage_structures = self.replay.read_uint32()
                    materials_gathered = self.replay.read_uint32()
                    materials_used = self.replay.read_uint32()
                    total_traveled = self.replay.read_uint32()

                    self.stats = Stats(
                        unknown=unknown,
                        accuracy=int(accuracy*100),
                        assists=assists,
                        eliminations=eliminations,
                        weapon_damage=weapon_damage,
                        other_damage=other_damage,
                        revives=revives,
                        damage_taken=damage_taken,
                        damage_structures=damage_structures,
                        materials_gathered=materials_gathered,
                        materials_used=materials_used,
                        total_traveled=round(total_traveled / 100000.0)
                    )

                if metadata == EventTypes.TEAM_STATS.value:
                    unknown = self.replay.read_uint32()
                    position = self.replay.read_uint32()
                    total_players = self.replay.read_uint32()

                    self.team_stats = TeamStats(
                        unknown=unknown,
                        position=position,
                        total_players=total_players
                    )

            self.replay.bytepos = offset + chunk_size
