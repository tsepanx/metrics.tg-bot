

This module is supposed to host and `API` of providing `.ics` file publicly by `http`.

The only enpoint available is: `http://hostname:port/ics/{username}` <br>
**WARNING**: for now `username` value doesn't count, and it fetches all entries.

This is module is only dependent on `UserDBCache` class, using which it fetches data from `DB`.

### How to run

```bash
PYTHONPATH="./" HTTP_HOST=0.0.0.0 HTTP_PORT=80 python src/ics/ics-main.py
```

### TODO 

- [ ] Mb merge with existing `src/main.py` and run in parallel using `asyncio` (#research)
