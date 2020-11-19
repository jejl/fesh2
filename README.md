# Fesh2: Geodetic VLBI schedule file management and processing

## What is it?
**Fesh2** is a Python package that provides automated schedule file
 preparation. It requires an installation of the 
 [NASA Field System](https://github.com/nvi-inc/fs). 

**Fesh2** runs in a
terminal window and regularly checks IVS schedule repositories for new or updated 
versions of Master files and schedule files for one or more specified stations. 
A check for the latest version of the Master file(s) is done first, but skipped if the time since the last check is less than a
specified amount (configurable on the command line or in the config file). 
Similarly, checks on schedule files are only done if the time since the
last check exceeds a specified time. 
If new or updated schedules are found, they are optionally processed with **Drudg** 
to produce `snp`, `prc` and `lst` files. By default, once the files have been
checked, **fesh2** will provide a summary and then go into a wait
state before carrying out another check. **Fesh2** can also be run once for a 
single check or status report and not go into a wait state.
Multiple instances can be run simultaneously. If drudg output (`snp` or `prc
` files) have been modified by the user and a new schedule becomes available
, **fesh2** will download the file but not overwrite Drudg output, but it
 will warn the user.
  
**Fesh2** can be run as a foreground application or as a service in the
 background.

## Compatibility
  * **Fesh2** has been tested for the following Python versions:
    * 2.7.16
    * 3.5.3
    * 3.7.3

## Installation
**Fesh2** will eventually be distributed as part of the 
[Field System](https://github.com/nvi-inc/fs), but for
 now there are a couple of ways to obtain it. Installation should probably be
  carried out under the superuser account

### Option 1: pip
```
pip install fesh2
```
or for Python version 3:
```
pip3 install fesh2
```

### Option 2: Manual installation

 1. Download and unpack the distribution 
 [from github](https://github.com/jejl/fesh2) or 
 [from PyPI](https://pypi.org/project/fesh2/) and put it into
  `/usr2/fs/`, renaming the top directory `fesh2`
 2. Run the following:
    ```
    cd /usr2/fs/fesh2/fesh2
    python setup.py install
    ```
Replace `python` with `python3` above for installation under Python version 3.
You will then need to edit the **fesh2** configuration file for your station(s). 
More information on configuration is provided below.

### PycURL dependency
Fesh2 depends on the python CURL library ([PycURL](http://pycurl.io/docs/latest/index.html)) 
which should be installed automatically when you install
 fesh2. However, PycURL depends on the Python development libraries, and it
  won't install if they're not there. On a Debian machine, `apt-get install
   python-dev` should do the trick, or for Python version 3, try `apt-get
    install python3-dev`.
    
## Configuration
**Fesh2** will take its configuration in the following priority order: 
  * Command-line parameters
  * Environment variables
  * Two config files, in this order:
    * `/usr2/control/fesh2.config`
    * `/usr2/control/skedf.ctl`

### Environment Variables
The following environment variables are recognised by **fesh2**:
 * `NETRC_FILE` and `COOKIES_FILE`: the locations of the `.netrc` and
  `.urs_cookies
 ` files, used by CURL for the https protocol. Curl sets these to files in the
  home
  directory by default. More information is given below on CURL configuration.
 * `LIST_DIR` : the directory where **drudg** puts `.lst` output files. If
  this is not set, then the `LstDir` parameter in `fesh2.config` is used if
   set. Otherwise **drudg** defaults to the `$schedules` parameter in `skedf.ctl`

The following environment variables are _NOT_ recognised by **fesh2**:
* `STATION` is used in the Field System but not recognised by **fesh2** as it
 is possible to configure **fesh2** to manage schedules for multiple stations
 . The `Stations` parameter _must_ be set in `fesh2.config`



### The fesh2 configuration file     
On startup, **fesh2** looks for a configuration
 file in `/usr2/control` called `fesh2.config`. 
*This will need to be set up for your station before running **fesh2** for
 the first time.* Use
 your favourite text editor to modify the file. The comments in the file
  describe the parameters but here are a few points to note:
#### Station settings
You will want to edit options in the `[Station]` section to configure which
stations you want to process, what types of Master and schedule files you
want to obtain, how far into the future you want to search for schedule
files and how often you want to look for them.

#### Servers
The `[Servers]` section allows you to list all the IVS schedule file servers
you want to search and the protocols to use for each. Specify the location
of the top directory (i.e. the `vlbi` directory). Protocols known to work are
https (secure HTTP), ftp (anonymous FTP) and ftps (secure (SSL) anonymous FTP).
    
#### Curl
**Fesh2** uses [curl](http://pycurl.io/docs/latest/index.html) to access files 
on the servers. If https is being used
 (e.g. to access the CDDIS repository), then **fesh2** needs to know the
  location of your `.netrc` and (optionally) `.urs_cookies` files. Curl
   puts these in the user's
  home directory by default but they can be placed elsewhere if desired. This can be set
  on the command line or via the NETRC_FILE and COOKIES_FILE environment
   variables (see above
  ) or in the **fesh2** config file by setting the NetrcFile and CookiesFile
   parameters. 

#### Drudg
After finding and downloading a new or updated schedule, **Fesh2** can
 optionally run **Drudg** to produce
 new snp, prc and lst files. The `[Drudg]` section allows you to configure
  this behaviour. If you don't want **fesh2** to
   automatically process your
   schedules, this feature con be turned off by
    setting `DodDrudg` to `False`.

Because **fesh2** manages schedule files and uses **drudg** to process them, 
and to keep things consistent across the Field System, it will use 
settings in `skedf.ctl`. 
However, there are some caveats regarding `skedf.ctl` for the case where there is
 not an overriding definition:
 
   * **Fesh2** requires that `$schedules` is defined in `skedf.ctl`. The
    default of '.' (i.e. the directory the software is started in) is too
     arbitrary and could cause **fesh2** to lose track of files.
   * If `$snap` or `$proc` are not defined, then they will be set to the same as
   `$schedules`
 
Depending on how it is configured by `skedf.ctl`, **drudg** may prompt
the user for input. For example, if `tpicd` is set to 'YES' then **Drudg** 
will prompt the user for a TPI sampling period every time. This
needs to be automated in **fesh2**, so a value must be set and will override 
whatever is set in `skedf.ctl`. The table below details how **fesh2** handles these cases:
     
 `skedf.ctl` condition       | **fesh2** reaction
 --------------------------- | ------------------------------
 `tpicd YES`           | **drudg** will be told to set the TPI period to 0 (i.e. don't use the TPI daemon) unless it is specifically set by `TpiPeriod` in `fesh2.config`
 `vsi_align ASK`       | **drudg** will be told not to use `dbbc=vsi_align` unless it is specifically set by `VsiAlign` in `fesh2.config`
 `cont_cal ASK`        | **drudg** will be told not to use continuous cal unless it is specifically set by `ContCalAction` in `fesh2.config`
 `cont_cal_polarity ASK` | **drudg** will be told to set the polarity to `none` unless it is specifically set by `ContCalPolarity` in `fesh2.config`
     
The new version of **drudg** will have an additional option to write a `.snp
` file that skips setup on scans when the mode hasn’t changed. There will be
 an option to prompt the user in this case and **fesh2** will have an
  automated response. This is currently not supported in **fesh2** pending
   the new **drudg** release.


## Usage
In many cases, **Fesh2** can be started by just typing
```
fesh2
```
which starts it in its default mode. However command-line options exist to
 change many of the configuration parameters, allow for a one-off checks
  (no wait mode), forcing of file downloads etc. Some common usages are:
  

* Only consider the current or next experiment
```
fesh2 -n
```

* Just run once then exit, don't go into a wait loop
```
fesh2 --once
```

* Just get a schedule for a specified session, then exit. e.g.:
```
fesh2 --once -g r1456
```
                        
* Force an update to the schedule file when there's a
new one available to replace the old one. The default
behaviour is to give the new file the name
<code>.skd.new and prompt the user to take action. The
file will also be drudged if the DoDrudg option is
True (default = False)
```
fesh2 --update
```

* Obtain schedule files, but don't process them:
```
fesh2 --DoDrudg False
```

* Get a status report. Shows the status of schedule files and when schedule
 servers were last queried.
```
fesh2 --check
```
                        
* Run fesh2 with all terminal output suppressed. Useful when running fesh2 as
 a service.
```
fesh2 --quiet
```

All command-line parameters are as follows:  

```
usage:       fesh2 [-h] [-c CONFIGFILE] [-g G] [-m] [-u] [-n] [-a] [-o]
                   [--update] [--SchedDir SCHEDDIR] [--ProcDir PROCDIR]
                   [--SnapDir SNAPDIR] [--LstDir LSTDIR] [--LogDir LOGDIR]
                   --Stations [STATIONS [STATIONS ...]]
                   [--GetMaster [GETMASTER]]
                   [--GetMasterIntensive [GETMASTERINTENSIVE]]
                   [--SchedTypes [SCHEDTYPES [SCHEDTYPES ...]]] -t
                   MASTERCHECKTIME -s SCHEDULECHECKTIME [-l LOOKAHEADTIMEDAYS]
                   [-d [DODRUDG]] --DrudgBinary DRUDGBINARY
                   [--TpiPeriod TPIPERIOD] [--VsiAlign VSIALIGN]
                   [--ContCalAction CONTCALACTION]
                   [--ContCalPolarity CONTCALPOLARITY]
                   [--Servers [SERVERS [SERVERS ...]]] [--NetrcFile NETRCFILE]
                   [--CookiesFile COOKIESFILE]
                   [--CurlSecLevel1 [CURLSECLEVEL1]] [-y YEAR] [-e] [-q]

Automated schedule file preparation for the current, next or specified
session. A check for the latest version of the Master File(s) is done first,
but skipped if the time since the last check is less than a specified amount
(configureable on the command line or in the config file). Similarly, checks
on schedule files are only done if the time since the last check exceeds a
specified time. Checks can be forced on the command line. Args that start with
'--' (eg. -m) can also be set in a config file (/usr2/control/fesh2.config or
specified via -c). Config file syntax allows: key=value, flag=true,
stuff=[a,b,c] (for details, see syntax at https://goo.gl/R74nmi). If an arg is
specified in more than one place, then commandline values override environment
variables which override config file values which override defaults.
optional arguments:

  -h, --help            show this help message and exit
  -c CONFIGFILE, --ConfigFile CONFIGFILE
                        The configuration file to use. (default is
                        ['/usr2/control/fesh2.config'])
  -g G                  Just get a schedule for this specified session. Give
                        the name of the session (e.g. r4951).
  -m, --master-update   Force a download of the Master Schedule (default =
                        False), but just on the first check cycle.
  -u, --sched-update    Force a download of the Schedules (default = False),
                        but just on the first check cycle.
  -n, --current, --now  Only process the current or next experiment
  -a, --all             Find the experiments with all "Stations" in it
  -o, --once            Just run once then exit, don't go into a wait loop
                        (default = False)
  --update              Force an update to the schedule file when there's a
                        new one available to replace the old one. The default
                        behaviour is to give the new file the name
                        <code>.skd.new and prompt the user to take action. The
                        file will also be drudged if the DoDrudg option is
                        True (default = False)
  --SchedDir SCHEDDIR   Schedule file directory
  --ProcDir PROCDIR     Procedure (PRC) file directory
  --SnapDir SNAPDIR     SNAP file directory
  --LstDir LSTDIR       LST file directory [env var: LIST_DIR]
  --LogDir LOGDIR       Log file directory
  --Stations [STATIONS [STATIONS ...]]
                        Stations to consider (default "hb ke yg ho")
  --GetMaster [GETMASTER]
                        Maintain a local copy of the main Multi-Agency
                        schedule, i.e. mostly 24h sessions (default = True)
  --GetMasterIntensive [GETMASTERINTENSIVE]
                        Maintain a local copy of the main Multi-Agency
                        Intensive schedul (default = True)
  --SchedTypes [SCHEDTYPES [SCHEDTYPES ...]]
                        Schedule file formats to be obtained? This is a
                        prioritised list with the highest priority first. Use
                        the file name suffix (vex and/or skd) and comma-
                        separated
  -t MASTERCHECKTIME, --MasterCheckTime MASTERCHECKTIME
                        Only check for a new master file if the last check was
                        more than this number of hours ago. The default is set
                        in the configuration file.
  -s SCHEDULECHECKTIME, --ScheduleCheckTime SCHEDULECHECKTIME
                        Only check for a new schedule file (SKD or VEX) if the
                        last check was more than this number of hours ago. The
                        default is set in the configuration file.
  -l LOOKAHEADTIMEDAYS, --LookAheadTimeDays LOOKAHEADTIMEDAYS
                        only look for schedules less than this number of days
                        away (default is 7)
  -d [DODRUDG], --DoDrudg [DODRUDG]
                        Run Drudg on the downloaded/updated schedules (default
                        = True)
  --DrudgBinary DRUDGBINARY
                        Location of Drudg executable (default =
                        /usr2/fs/bin/drudg)
  --TpiPeriod TPIPERIOD
                        Drudg config: TPI period in centiseconds. 0 = don't
                        use the TPI daemon (default)
  --VsiAlign VSIALIGN   Drudg config: Applicable only for PFB DBBCs, none =
                        never use dbbc=vsi_align=... (default) 0 = always use
                        dbbc=vsi_align=0 1 = always use dbbc=vsi_align=1
  --ContCalAction CONTCALACTION
                        Drudg config: Continuous cal option. Either 'on' or
                        'off'. Default is 'off'
  --ContCalPolarity CONTCALPOLARITY
                        Drudg config: If continuous cal is in use, what is the
                        polarity? Options are 0-3 or 'none'. Default is none
  --Servers [SERVERS [SERVERS ...]]
                        Schedule file server URLs. Each of these will be
                        checked for the most recent files. Use comma-separated
                        URLs and specify the top directory (i.e. the 'vlbi'
                        directory). Use protocols https (Curl), ftp (anonymous
                        FTP) or sftp (anonymous secure FTP)
  --NetrcFile NETRCFILE
                        The location of the .netrc file, needed by CURL for
                        the https protocol. (CURL puts this in ~/.netrc by
                        default) [env var: NETRC_FILE]
  --CookiesFile COOKIESFILE
                        The location of the .urs_cookies files used by CURL.
                        (CURL puts this in ~/.urs_cookies by default) [env
                        var: COOKIES_FILE]
  --CurlSecLevel1 [CURLSECLEVEL1]
                        Workaround for CDDIS https access in some Debian
                        distributions. See the documentation (default = False)
  -y YEAR, --year YEAR  The year of the Master Schedule (default is 2020)
  -e, --check           Check the current fesh2 status. Shows if the systemd
                        service is running and prints the status of schedule
                        files
  -q, --quiet           Runs fesh2 with all terminal output suppressed. Useful
                        when running fesh2 as a service.

```

## Logging
As well as writing information to the screen on activity, **fesh2** also
keeps a log of activity in the Field System log directory (by default) at
`/usr2/log/fesh2.log`. The log file location can be configured in `fesh2.config`

## Running fesh2 as a service
Fesh2 can be run in the background as a `systemd` service. All output is
 suppressed and status is available by examining the log file or using the
  `--check` or `-e` flag. Here's how to set it up from the superuser account
   for Debian Jessie or later:
  
1. Type the following command to add a `systemd` service: 
    ```
   systemctl edit --force --full fesh2.service
   ```
    This should open a text editor. Paste in the following:
    ```
   [Unit]
   Description=Fesh2 Service
   After=network-online.target
   Wants=network-online.target
   
   [Service]
   ExecStart=sudo -H -u oper /usr/local/bin/fesh2 --quiet
   
   [Install]
   WantedBy=multi-user.target
   ```
   Save and exit. This will configure `systemd` to start fesh2, running as user
    oper and suppress all output.
2. Enable the service:
    ```
    sudo systemctl enable fesh2.service
    ```
3. Check the status of the service:
    ```
    sudo systemctl status fesh2.service
    ```
4. You can stop, start and query the service:
    ```
    sudo systemctl stop fesh2.service          # Stop running the service 
    sudo systemctl start fesh2.service         # Start running the service 
    sudo systemctl restart fesh2.service       # Restart the service 
    ```
5. To see the current schedule file status (as user oper):
    ```
   fesh2 --check
   ```
   
If you would prefer to set this up as a user service, some notes are here:
* https://www.unixsysadmin.com/systemd-user-services/

For versions of Debian older thean Jessie (e.g. Wheezy), systemd can be
 enabled and some notes are here:
* https://scottlinux.com/2014/10/20/how-to-switch-to-systemd-on-debian-wheezy/
