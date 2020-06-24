# fesh2
Geodetic VLBI schedule management and processing

Fesh2 provides automated schedule file preparation for the current, next or specified
session. It requires an installation of the [NASA Field System](https://github.com/nvi-inc/fs).
When run, a check for the latest version of the Master File(s) is done first,
but skipped if the time since the last check is less than a specified amount
(configureable on the command line or in the config file). Similarly, checks
on schedule files are only done if the time since the last check exceeds a
specified time. Checks can be forced on the command line.

## Installation
```git install fesh2```

## Configuration
Fesh2 looks for a configuration file in `/usr2/control` called `fesh2.config`. This will need to be set up for your station before running it.


## Usage
```
usage: fesh2 [-h] [-c CONFIG] [-g GET] [-t TMASTER] [-s TSCHED] [-m] [-u] [-d]
             [-n] [-a] [-o] [-l LOOKAHEAD] [-y YEAR]
             [stns [stns ...]]

positional arguments:
  stns                  Stations to consider (default "hb ke yg ho")

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        The configuration file to use. (default is
                        /usr2/control/fesh2.config)
  -g GET, --get GET     Just get a schedule for this specified session. Give
                        the name of the session (e.g. r4951).
  -t TMASTER, --tmaster TMASTER
                        Only check for a new master file if the last check was
                        more than this number of hours ago. The default is set
                        in the configuration file.
  -s TSCHED, --tsched TSCHED
                        Only check for a new schedule file (SKD or VEX) if the
                        last check was more than this number of hours ago. The
                        default is set in the configuration file.
  -m, --master-update   Force a download of the Master Schedule (default =
                        False).
  -u, --sched-update    Force a download of the Schedules (default = False).
  -d, --no-drudg        Force NOT to run Drudg on the downloaded/updated
                        schedules (default = False)
  -n, --current, --now  Only process the current or next experiment
  -a, --all             find the experiments with all "stns" in it
  -o, --once            Just run once then exit, don't go into a wait loop
                        (default = False)
  -l LOOKAHEAD, --lookahead LOOKAHEAD
                        only look for schedules less than this number of days
                        away (default is 7)
  -y YEAR, --year YEAR  The year of the Master Schedule (default is 2020)
```
