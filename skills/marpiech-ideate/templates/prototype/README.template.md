# <Idea name> — prototype vN

Throwaway prototype for `SPEC.md` (same directory). Not part of the product repository.

## Run
```sh
PORT=<port> ./restart.sh        # prints the token URL
```
Remote machine: `ssh -L <port>:127.0.0.1:<port> <host>`, then open the printed URL.

## Test
```sh
<e2e command>                    # acceptance scenarios from SPEC §11
```

## Data
<which data, privacy class, how it was pseudonymised>

## Versions
- vN — <YYYY-MM-DD> — <what changed after the last review>

## Cleanup
Stop: kill the process listening on the port (`restart.sh` shows how). Remove the
directory and free the port in the adapter's port registry when the idea is ported or
dropped.
