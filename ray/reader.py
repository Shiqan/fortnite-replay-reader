from datetime import datetime

import bitstring

from dataclasses import asdict
from ray.exceptions import (InvalidReplayException, PlayerEliminationException,
                            ReadStringException)
from ray.logging import logger
from ray.models import (BitTypes, ChunkTypes, Elimination, EventTypes, Header,
                        HeaderTypes, HistoryTypes, Stats, TeamStats, PlayerTypes, PlayerId)

FILE_MAGIC = 0x1CA2E27F
NETWORK_MAGIC = 0x2CF5A13D

class ConstBitStreamWrapper(bitstring.ConstBitStream):
    """ Wrapper for the bitstring.ConstBitStream class to provide some convience methods """

    def skip(self, count):
        """ Skip the next count bytes """
        self.bytepos += count

    def read_uint8(self):
        """ Read and interpret next 8 bits as an unassigned integer """
        return self.read(BitTypes.UINT8.value)

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

    def hextostring(self, i):
        s = hex(i)[2:]
        return s if len(s) == 2 else f'0{s}'

    def read_guid(self):
        """ Read and interpret next 16 bits as a guid"""
        return ''.join(self.hextostring(i) for i in self.read('bytes:16'))

    def read_array(self, f):
        """ Read an array where the first 32 bits indicate the length of the array """
        length = self.read_uint32()
        return [f() for _ in range(length)]

    def read_tuple_array(self, f1, f2):
        """ Read an tuple array where the first 32 bits indicate the length of the array """
        length = self.read_uint32()
        return [(f1(), f2()) for _ in range(length)]

    def read_string(self):
        """ Read and interpret next i bits as a string where i is determined defined by the first 32 bits """
        size = self.read_int32()

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
        self.header = None
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

        magic = self.replay.read_uint32()
        if (magic != FILE_MAGIC):
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
        pass

    def parse_replaydata(self):
        """ Parse incremental changes to the last checkpoint """
        pass

    def parse_header(self, size):
        """ Parse metadata of the file replay (Fortnite) """
        logger.info('parse_header()')

        magic = self.replay.read_uint32()
        if (magic != NETWORK_MAGIC):
            raise InvalidReplayException()
        network_version = self.replay.read_uint32()
        network_checksum = self.replay.read_uint32()
        engine_network_version = self.replay.read_uint32()
        game_network_protocol = self.replay.read_uint32()

        if network_version > HeaderTypes.HEADER_GUID.value:
            guid = self.replay.read_guid()
        else:
            guid = ""

        major = self.replay.read_uint16()
        minor = self.replay.read_uint16()
        patch = self.replay.read_uint16()
        changelist = self.replay.read_uint32()
        branch = self.replay.read_string()
    
        levelnames_and_times = self.replay.read_tuple_array(self.replay.read_string, self.replay.read_uint32)
        flags = self.replay.read_uint32()
        game_specific_data = self.replay.read_array(self.replay.read_string)

        self.header = Header(
            network_version=network_version,
            network_checksum=network_checksum,
            engine_network_version=engine_network_version,
            game_network_protocol=game_network_protocol,
            guid=guid,
            major=major,
            minor=minor,
            patch=patch,
            changelist=changelist,
            branch=branch,
            levelnames_and_times=levelnames_and_times,
            flags=flags,
            game_specific_data=game_specific_data,
            )

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
                self.parse_elimination_event(start_time)
            except:
                logger.error("Couldnt parse event PLAYER_ELIMINATION")
                self.replay.bytepos = current_pos + size

        if metadata == EventTypes.MATCH_STATS.value:
            self.parse_matchstats_event()

        if metadata == EventTypes.TEAM_STATS.value:
            self.parse_teamstats_event()

    def parse_teamstats_event(self):
        """ Parse Fortnite team stats event """
        unknown = self.replay.read_uint32()
        position = self.replay.read_uint32()
        total_players = self.replay.read_uint32()

        team_stats = TeamStats(
            unknown=unknown,
            position=position,
            total_players=total_players
        )
        self.team_stats = asdict(team_stats)

    def parse_matchstats_event(self):
        """ Parse Fortnite stats event """
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

    def parse_elimination_event(self, time):
        """ Parse Fortnite elimination event (kill feed) """

        if self.header.engine_network_version >= 11 and self.header.version['major'] >= 9:
            self.replay.skip(85)
            eliminated = self.read_player()
            eliminator = self.read_player()
        else:
            if self.header.branch == '++Fortnite+Release-4.0':
                self.replay.skip(12)
            elif self.header.branch == '++Fortnite+Release-4.2':
                self.replay.skip(40)
            elif self.header.branch >= '++Fortnite+Release-4.3':
                self.replay.skip(45)
            elif self.header.branch == '++Fortnite+Main':
                self.replay.skip(45)
            else:
                raise PlayerEliminationException()

            eliminated = PlayerId('', self.replay.read_string(), True)
            eliminator = PlayerId('', self.replay.read_string(), True)

        gun_type = self.replay.read_byte()
        knocked = self.replay.read_uint32()

        self.eliminations.append(Elimination(
            eliminated=eliminated,
            eliminator=eliminator,
            gun_type=gun_type,
            time=datetime.fromtimestamp(time/1000.0),
            knocked=knocked))

    def read_player(self):
        player_type = self.replay.read_byte()
        if player_type == PlayerTypes.NAMELESS_BOT.value:
            player = PlayerId('Bot', '', False)
        elif player_type == PlayerTypes.NAMED_BOT.value:
            player = PlayerId(self.replay.read_string(), '', False)
        else:
            self.replay.skip(1) # size
            player = PlayerId('', self.replay.read_guid(), True)

        return player
