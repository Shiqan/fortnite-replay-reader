from ray import Reader

with Reader("filepath") as replay:
    print(replay.stats)
    print(replay.team_stats)
    
    for elim in replay.eliminations:
        print(elim)
