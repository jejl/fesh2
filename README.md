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
single check and not go into a wait state.

**Fesh2** can be run as a foreground application or as a service in the
 background.

## Compatibility
  * **Fesh2** has been tested for the following Python versions:
    * 2.7.16
    * 3.7.3
    * 3.8.2
  * Limited testing has been carried out with version 3.5.3 but it appears to
   work with this
   version too.

## Installation
**Fesh2** will eventually be distributed as part of the 
[Field System](https://github.com/nvi-inc/fs), but for
 now there are a couple of ways to obtain it. Installation should probably be
  carried out under the superuser account

### Option 1: pip
```
pip install fesh2
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
You will then need to edit the **fesh2** configuration file for your station(s). 
More information on configuration is provided below.

### PycURL dependency
Fesh2 depends on the python CURL library ([PycURL](http://pycurl.io/docs/latest/index.html)) which should be installed automatically when you install
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
 * `NETRC_DIR` : the directory containing the `.netrc` and `.urs_cookies
 ` files, needed by CURL for the https protocol. Curl sets ths to the home
  directory by default. More information is given below on CURL configuration.
 * `LIST_DIR` : the directory where **drudg** puts `.lst` output files. If
  this is not set, then the `LstDir` parameter in `fesh2.config` is used if
   set. Otherwise **drudg** defaults to the `$schedules` parameter in `skedf
   .ctl`

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
  location of your `.netrc` and `.urs_cookies` files. Curl puts these in the user's
  home directory by default but they can be placed elsewhere if desired. This can be set
  on the command line or via the NETRC_DIR environment variable (see above
  ) or in the **fesh2** config file by setting the NetrcDir parameter. The
   command-line overrides
  the environment variable which overrides the config file. If you  don't
    intend to 
  use https then place empty `.netrc` and `.urs_cookies` files in these
   locations. 

#### Drudg
After finding and downloading a new or updated schedule, **Fesh2** can
 optionally run **Drudg** to produce
 new snp, prc and lst files. The `[Drudg]` section allows you to configure
  this behaviour. If you don't want **fesh2** to
   automatically process your
   schedules (it will overwrite old files), this feature con be turned off by
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
  (no wait mode), forcing of file downloads etc. Command-line parameters are
   as follows:  

```
TBD
```

## Logging
As well as writing information to the screen on activity, **fesh2** also
keeps a log of activity in the Field System log directory (by default) at
`/usr2/log/fesh2.log`. The log file location can be configured in `fesh2.config`

## Running fesh2 as a service
Fesh2 can be run in the background as a `systemd` service. All output is
 suppressed and status is available by examining the log file or using the
  `--check` or `-e` flag. Here's how to set it up from the superuser account:
  
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
   
  