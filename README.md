# Ray - Go 86 em

[![Build Status](https://travis-ci.org/Shiqan/fortnite-replay-reader.svg?branch=master)](https://travis-ci.org/Shiqan/fortnite-replay-reader)
[![PyPI](https://img.shields.io/pypi/v/fortnite-replay-reader.svg)](https://pypi.org/project/fortnite-replay-reader/)
[![BCH compliance](https://bettercodehub.com/edge/badge/Shiqan/fortnite-replay-reader?branch=develop)](https://bettercodehub.com/)

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
