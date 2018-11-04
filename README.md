# Ray - Go 86 em

Fortnites favorite assistent is here to help you parse replay files.

```python
from ray import Reader

with Reader("filepath") as replay:
    print(replay.stats)
    print(replay.team_stats)
    
    for elim in replay.eliminations:
        print(elim)
```

## License

Licensed under the [MIT License](LICENSE).
