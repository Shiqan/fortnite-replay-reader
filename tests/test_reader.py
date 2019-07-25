import os
import pytest

from dataclasses import asdict
from ray.reader import Reader
from ray.models import Stats, TeamStats

def test_season8():
    filename = os.path.join(os.path.dirname(__file__), 'Replays/season08-2019.04.05.replay')
    with Reader(filename) as replay:
        assert replay.header
        assert replay.team_stats

def test_season910():
    filename = os.path.join(os.path.dirname(__file__), 'Replays/season09-2019.05.22.replay')
    with Reader(filename) as replay:
        assert replay.header
        assert replay.team_stats

def test_season940():
    filename = os.path.join(os.path.dirname(__file__), 'Replays/season09-2019.07.25.replay')
    with Reader(filename) as replay:
        assert replay.header
        assert replay.team_stats

def test_reader_filepath():
    TESTDATA_FILENAME = os.path.join(os.path.dirname(
        __file__), 'Replays/UnsavedReplay-2018.10.17-20.33.41.replay')

    with Reader(TESTDATA_FILENAME) as replay:
        expected_stats = asdict(Stats(
            unknown=0,
            accuracy=22,
            assists=4,
            eliminations=3,
            weapon_damage=753,
            other_damage=119,
            revives=0,
            damage_taken=839,
            damage_structures=43504,
            materials_gathered=2063,
            materials_used=710,
            total_traveled=4
        ))

        expected_team_stats = asdict(TeamStats(
            unknown=0,
            position=2,
            total_players=96
        ))

        assert replay.stats == expected_stats
        assert replay.team_stats == expected_team_stats


def test_reader_bytes():
    TESTDATA_FILENAME = os.path.join(os.path.dirname(
        __file__), 'Replays/UnsavedReplay-2018.10.17-20.33.41.replay')

    f = open(TESTDATA_FILENAME, 'rb')
    with Reader(f.read()) as replay:
        expected_stats = asdict(Stats(
            unknown=0,
            accuracy=22,
            assists=4,
            eliminations=3,
            weapon_damage=753,
            other_damage=119,
            revives=0,
            damage_taken=839,
            damage_structures=43504,
            materials_gathered=2063,
            materials_used=710,
            total_traveled=4
        ))

        expected_team_stats = asdict(TeamStats(
            unknown=0,
            position=2,
            total_players=96
        ))

        assert replay.stats == expected_stats
        assert replay.team_stats == expected_team_stats
    f.close()


def test_reader_exception():
    with pytest.raises(FileNotFoundError):
        with Reader("") as replay:
            pass
