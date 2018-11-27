#!/usr/bin/python
# -*- coding: utf-8 -*-

from datetime import datetime

import bitstring

from dataclasses import asdict
from ray.exceptions import (InvalidReplayException, PlayerEliminationException,
                            ReadStringException)
from ray.logging import logger
from ray.models import (BitTypes, ChunkTypes, Elimination, EventTypes,
                        HistoryTypes, Stats, TeamStats)

FILE_MAGIC = 0x1CA2E27F


class ConstBitStreamWrapper(bitstring.ConstBitStream):
    """ Wrapper for the bitstring.ConstBitStream class to provide some convience methods """

    def read_uint16(self):
        """ Read and interpret next 16 bits as an unassigned integer """
        return self.read(BitTypes.UINT_16.value)

    def read_uint32(self):
        """ Read and interpret next 32 bits as an unassigned integer """
        return self.read(BitTypes.UINT_32.value)

    def read_int32(self):
        """ Read and interpret next 32 bits as an signed integer """
        return self.read(BitTypes.INT_32.value)

    def read_uint64(self):
        """  Read and interpret next 64 bits as an unassigned integer """
        return self.read(BitTypes.UINT_64.value)

    def read_float32(self):
        """ Read and interpret next 32 bits as a float """
        return self.read(BitTypes.FLOAT_LE_32.value)

    def read_byte(self):
        """ Read and interpret next bit as an integer """
        return int.from_bytes(self.read(BitTypes.BYTE.value), byteorder='little')

    def read_bool(self):
        """ Read and interpret next 32 bits as an boolean """
        return self.read_uint32() == 1

    def read_guid(self):
        """ Read and interpret next 16 bits as a guid """
        return self.read('bytes:16')

    def read_string(self):
        """ Read and interpret next i bits as a string where i is determined defined by the first 32 bits """
        size = self.read(BitTypes.INT_32.value)

        if size == 0:
            return ""

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
    """ Replay reader class to use as a context manager.

    Can be used with either a file path or a stream of bytes:
    >>> with Reader('filepath') as replay:
            print(replay.stats)
    >>> f = open('filepath', 'rb')
    >>> with Reader(f.read()) as replay:
            print(replay.stats)
    >>> f.close()
    """
    _close_on_exit = False

    def __init__(self, src):
        self.src = src
        self._file = None
        self.replay = None
        self.release = 0
        self.eliminations = []
        self.stats = None
        self.team_stats = None

    def __len__(self):
        return self.replay.len

    def __sizeof__(self):
        return self.replay.len

    def __repr__(self):
        return 'Replay file {path}'.format(path=self.src)

    def __enter__(self):
        logger.info(f'__enter__() replay file {self.src}')

        if isinstance(self.src, str):
            self._file = open(self.src, 'rb')
            self._close_on_exit = True
        elif isinstance(self.src, bytes):
            self._file = self.src
        else:
            raise TypeError()

        self.replay = ConstBitStreamWrapper(self._file)
        self.parse_meta()
        self.parse_chunks()
        return self

    def __exit__(self, *args):
        logger.info(f'__exit__() replay file {self.src}')

        if self._close_on_exit:
            self._file.close()

    def parse_meta(self):
        """ Parse metadata of the file replay (Unreal Engine) """
        logger.info('parse_meta()')

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
        """ Parse chunks of the file replay """
        logger.info('parse_chunks()')

        while (self.replay.pos < len(self.replay)):
            chunk_type = self.replay.read_uint32()
            chunk_size = self.replay.read_int32()
            offset = self.replay.bytepos

            if chunk_type == ChunkTypes.CHECKPOINT.value:
                self.parse_checkpoint()

            elif chunk_type == ChunkTypes.EVENT.value:
                self.parse_event()

            elif chunk_type == ChunkTypes.REPLAYDATA.value:
                self.parse_replaydata()

            elif chunk_type == ChunkTypes.HEADER.value:
                self.parse_header(chunk_size)

            self.replay.bytepos = offset + chunk_size

    def parse_checkpoint(self):
        """ Parse snapshot of the game environment """
        logger.info('parse_checkpoint()')
        checkpointId = self.replay.read_string()
        checkpoint = self.replay.read_string()

    def parse_replaydata(self):
        """ Parse incremental changes to the last checkpoint """
        logger.info('parse_replaydata()')

        start = self.replay.read_uint32()
        end = self.replay.read_uint32()
        remaining_offset = self.replay.read_uint32()
        _ = self.replay.read_uint32()
        remaining_offset = self.replay.read_uint32()

    def parse_header(self, size):
        """ Parse metadata of the file replay (Fortnite) """
        logger.info('parse_header()')

        logger.debug(self.replay.read(f'bytes:{size}'))
        self.replay.bytepos -= size

        self.replay.bytepos += 4
        header_version = self.replay.read_uint32()
        server_side_version = self.replay.read_uint32()
        season = self.replay.read_uint32()
        _0 = self.replay.read_uint32()

        if header_version > 11:
            guid = self.replay.read_guid()

        _4 = self.replay.read_uint16()
        some_increasing_number = self.replay.read_uint32()
        fortnite_version = self.replay.read_uint32()
        self.release = self.replay.read_string()

        if self.replay.read_bool():
            game_map = self.replay.read_string()
        _0 = self.replay.read_uint32()
        _3 = self.replay.read_uint32()

        if self.replay.read_bool():
            game_sub = self.replay.read_string()

    # solo
    # 3D A1 F5 2C 0D 00 00 00 99 D0 AB 87 06 00 00 00 00 00 00 00 42 23 B4 E8 C8 EC FF 47 AE F0 6D 2F 16 82 1F F0 04 00 15 00 00 00 EA 5C 44 00
    # 3D A1 F5 2C 0D 00 00 00 99 D0 AB 87 06 00 00 00 00 00 00 00 7A 00 6F 41 C4 E3 E4 47 8C 7E 31 AC 5E 6A 41 2B 04 00 15 00 00 00 EA 5C 44 00
    # 3D A1 F5 2C 0D 00 00 00 99 D0 AB 87 06 00 00 00 00 00 00 00 59 F2 58 E2 AF D7 F9 43 AC 1B F8 5E 5C 01 87 93 04 00 15 00 00 00 EA 5C 44 00
    # 3D A1 F5 2C 0D 00 00 00 99 D0 AB 87 06 00 00 00 00 00 00 00 1E 6F B0 A7 D4 6B 63 41 B3 39 11 B3 A5 60 F5 F9 04 00 15 00 00 00 EA 5C 44 00

    # solo (winter ...)
    # 3D A1 F5 2C 0D 00 00 00 91 43 5D 23 06 00 00 00 00 00 00 00 1D 2E 50 EF AA 20 BF 4A AC B0 B8 BC 0E CE A6 47 04 00 15 00 00 00 E4 DE 45 00

    # duo (wild west)
    # 3D A1 F5 2C 0D 00 00 00 91 43 5D 23 06 00 00 00 00 00 00 00 2D D6 8F 22 39 DB 0C 4B AF FC 73 B6 63 73 D8 62 04 00 15 00 00 00 E4 DE 45 00
    # 3D A1 F5 2C 0D 00 00 00 91 43 5D 23 06 00 00 00 00 00 00 00 88 12 6F A6 BA 9D E0 4D 98 47 3F AE 72 DF DB 58 04 00 15 00 00 00 E4 DE 45 00

    # duo(fortnitemares)
    # 3D A1 F5 2C 0D 00 00 00 6A 61 A3 EA 06 00 00 00 00 00 00 00 34 74 C7 F5 50 B3 56 47 92 8A F4 66 AD 67 EC DF 04 00 15 00 00 00 4E A0 44 00
    # 3D A1 F5 2C 0D 00 00 00 6A 61 A3 EA 06 00 00 00 00 00 00 00 04 FF F2 A7 9E 43 66 47 B4 54 C9 88 95 1A EA 9A 04 00 15 00 00 00 9C BA 44 00
    # 3D A1 F5 2C 0D 00 00 00 6A 61 A3 EA 06 00 00 00 00 00 00 00 16 48 E0 E4 A0 37 AC 4E B1 54 60 D6 68 68 1E 18 04 00 15 00 00 00 9C BA 44 00

    # squad
    # 3D A1 F5 2C 0D 00 00 00 99 D0 AB 87 06 00 00 00 00 00 00 00 94 78 46 E8 46 B6 25 45 B2 85 96 92 59 00 A4 2F 04 00 15 00 00 00 C2 4C 44 00
    # 3D A1 F5 2C 0D 00 00 00 99 D0 AB 87 06 00 00 00 00 00 00 00 DD 2C F1 11 F3 C6 13 46 99 BD C6 07 20 C9 A0 57 04 00 15 00 00 00 C2 4C 44 00
    # 3D A1 F5 2C 0D 00 00 00 91 43 5D 23 06 00 00 00 00 00 00 00 F0 76 AB 5B 8F 81 72 40 A8 2F 39 7C E9 4E 3C 65 04 00 15 00 00 00 E4 DE 45 00

    # squad(fortnitemares)
    # 3D A1 F5 2C 0D 00 00 00 6A 61 A3 EA 06 00 00 00 00 00 00 00 B2 FF FA 4A A7 09 B7 4E A3 6F 25 EC 8C 92 3F 9D 04 00 15 00 00 00 9C BA 44 00
    # 3D A1 F5 2C 0D 00 00 00 6A 61 A3 EA 06 00 00 00 00 00 00 00 E5 7F 0C 98 87 B4 26 41 A7 04 79 50 CD D6 D7 9C 04 00 15 00 00 00 9C BA 44 00
    # 3D A1 F5 2C 0D 00 00 00 6A 61 A3 EA 06 00 00 00 00 00 00 00 38 C4 26 0A 7F 1F 5D 41 AF E5 B5 39 43 9C 0E 47 04 00 15 00 00 00 9C BA 44 00

    def parse_event(self):
        """ Parse custom Fortnite events """
        event_id = self.replay.read_string()
        group = self.replay.read_string()
        metadata = self.replay.read_string()
        start_time = self.replay.read_uint32()
        end_time = self.replay.read_uint32()
        size = self.replay.read_uint32()

        current_pos = self.replay.bytepos
        logger.info(
            f'parse_event(), event id => {event_id}, group id => {group}, current offset => {current_pos}')

        if group == EventTypes.PLAYER_ELIMINATION.value:
            try:
                if self.release == '++Fortnite+Release-4.0':
                    self.replay.bytepos += 12
                elif self.release == '++Fortnite+Release-4.2':
                    self.replay.bytepos += 40
                elif self.release >= '++Fortnite+Release-4.3':
                    self.replay.bytepos += 45
                elif self.release == '++Fortnite+Main':
                    self.replay.bytepos += 45
                else:
                    raise PlayerEliminationException()
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
            except:
                logger.error("Couldnt parse event PLAYER_ELIMINATION")
                self.replay.bytepos = current_pos + size

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

            stats = Stats(
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
            self.stats = asdict(stats)

        if metadata == EventTypes.TEAM_STATS.value:
            unknown = self.replay.read_uint32()
            position = self.replay.read_uint32()
            total_players = self.replay.read_uint32()

            team_stats = TeamStats(
                unknown=unknown,
                position=position,
                total_players=total_players
            )
            self.team_stats = asdict(team_stats)
