#!/usr/bin/env python3

import sys
import configparser
from configparser import ExtendedInterpolation
from os import path
import string

class Config:

    def __init__(self):
        # recognised schedule file types
        self.allowed_sched_types = ['vex', 'skd']

        def parse_onoff(val):
            val = val.lower()
            if val in ['on', 'off']:
                return val
            else:
                return 'off'

        def parse_ccal_pol(val):
            val = val.lower()
            if val in ['none', '0', '1', '2', '3']:
                return val
            else:
                return 'none'

        def parse_vsi_align(val):
            val = val.lower()
            if val in ['none', '0', '1']:
                return val
            else:
                return 'none'

        self.config = configparser.ConfigParser(
            converters = {'onoff': parse_onoff,
                          'contcalpol': parse_ccal_pol,
                          'vsialign': parse_vsi_align}
        )
        self.config._interpolation = ExtendedInterpolation()


        self.ContCalAction = 'off'
        self.ContCalPolarity = 'none'
        self.DoDrudg = True
        self.DrudgBinary = '/usr2/fs/bin/drudg'
        self.FsDir = '/usr2/fs'
        self.GetMaster = True
        self.GetMasterIntensive = True
        self.LogDir = '/usr2/log'
        self.LookAheadTimeDays = 14.0
        self.LstDir = '/usr2/sched'
        self.MasterCheckTime = 12.0
        self.NetrcDir = '/usr2/control/'
        self.ProcDir = '/usr2/proc'
        self.SchedDir = '/usr2/sched'
        self.SchedTypes = ['vex','skd']
        self.ScheduleCheckTime=1.0
        self.Servers=['https://cddis.nasa.gov/archive/vlbi', 'ftp://ivs.bkg.bund.de/pub/vlbi',
                  'ftp://ivsopar.obspm.fr/pub/vlbi']
        self.StDir='/usr2/st'
        self.Stations=['Hb', 'Ho', 'Ke', 'Yg']
        self.TpiPeriod=0
        self.VsiAlign='none'

        # Things not in the config file:

        self.all_stations=False
        self.check=False
        self.ConfigFile=None
        self.current=False
        self.g=None # Just look for schedules from this session
        self.master_update=False # Force a download of the master file(s)
        self.once=False
        self.quiet=True
        self.sched_update=False # Force a download of the schedule file(s)
        self.year=2020

        self.logger = None


    def load(self, arg):
        # arg is an Args instance

        # # Check that the config file exists (the default is set in Args.)
        # if not path.exists(arg.args.config):
        #     raise OSError(2, "Can't find the config file: ", arg.args.config)
        # print("Config file found: {}".format(arg.args.config))
        # # Read the config file
        # self.config.read(arg.args.config)

        # If snts=[] then nothing set on the command line, so use the config file

        # if len(arg.args.Stations) > 0:
        #     # station names given on the command line
        #     self.stations = arg.args.Stations
        # else:
        #     Stations = self.config['Station']['Stations']
        #     self.stations = [word.strip(string.punctuation) for word in Stations.split()]
        self.Stations = [word.strip(string.punctuation) for word in arg.args.Stations]
        # convert station names to lower case`
        self.Stations = list(map(lambda x: x.lower(), self.Stations))

        # get list of file servers
        # servs = self.config['Servers']['url']
        # self.servers = [word.strip(string.punctuation) for word in servs.split()]
        self.Servers = [word.strip(string.punctuation) for word in arg.args.Servers]

        # get prioritised list of schedule file formats
        # types = self.config['Station']['schedtypes']
        # self.sched_types = [word.strip(string.punctuation) for word in types.split()]
        self.SchedTypes = [word.strip(string.punctuation) for word in arg.args.SchedTypes]

        # try:
        #     if arg.args.tmaster is not None:
        #         self.MasterCheckTime = float(arg.args.tmaster)
        #     else:
        #         self.MasterCheckTime = self.config.getfloat('Station', 'masterchecktime')
        # except ValueError as err:
        #     print("ERROR: Can't interpret MasterCheckTime in config file. Not a number?: {}".format(err))
        #     print("Setting the Master File check interval to 24 hours.")
        #     self.MasterCheckTime = 24
        # except:
        #     print("Unexpected error:", sys.exc_info()[0])
        #     raise
        self.MasterCheckTime = arg.args.MasterCheckTime

        # try:
        #     if arg.args.tsched is not None:
        #         self.ScheduleCheckTime = float(arg.args.tsched)
        #     else:
        #         self.ScheduleCheckTime = self.config.getfloat('Station', 'schedulechecktime')
        # except ValueError as err:
        #     print("ERROR: Can't interpret ScheduleCheckTime in config file. Not a number?: {}".format(err))
        #     print("Setting the Schedule File check interval to 1 hour.")
        #     self.ScheduleCheckTime = 1
        # except:
        #     print("Unexpected error:", sys.exc_info()[0])
        #     raise

        self.ScheduleCheckTime = arg.args.ScheduleCheckTime

        # try:
        #     if arg.args.lookahead is not None:
        #         self.LookAheadTimeDays = int(arg.args.lookahead)
        #     else:
        #         self.LookAheadTimeDays = self.config.getint('Station', 'lookaheadtimedays')
        # except ValueError as err:
        #     print("ERROR: Can't interpret LookAheadTimeDays in config file. Not an integer?: {}".format(err))
        #     print("Setting the Schedule File look-ahead time to 7 days.")
        #     self.LookAheadTimeDays = 7
        # except:
        #     print("Unexpected error:", sys.exc_info()[0])
        #     raise
        self.LookAheadTimeDays = arg.args.LookAheadTimeDays

        self.DoDrudg = arg.args.DoDrudg

        if arg.args.g:
            self.g = arg.args.g

        self.force_master_update = arg.args.master_update
        # if arg.args.master_update:
        #     self.force_master_update = True
        self.force_sched_update = arg.args.sched_update
        # if arg.args.sched_update:
        #     self.force_sched_update = True
        self.current = arg.args.current
        # if arg.args.current:
        #     self.current = True
        self.run_once = arg.args.once
        # if arg.args.once:
        #     self.run_once = True
        self.all_stations = arg.args.all
        # if arg.args.all:
        #     self.all_stations = True
        self.check = arg.args.check
        # if arg.args.check:
        #     self.check = True
        self.quiet = arg.args.quiet
        # if arg.args.quiet:
        #     self.quiet = True

        self.year = arg.args.year

        # self.tpi_period = self.config.getint('Drudg', 'tpi_period')
        # self.cont_cal_action = self.config.getonoff('Drudg', 'cont_cal_action')
        # self.cont_cal_polarity = self.config.getcontcalpol('Drudg', 'cont_cal_polarity')
        # self.vsi_align = self.config.getvsialign('Drudg', 'vsi_align')

    def check_config(self):
        # Check the configuration

        # Servers
        if not self.Servers:
            raise Exception("Config file must specify at least one schedule server in [Servers] section")

        if not self.SchedTypes:
            raise Exception("Config file must specify at least one schedule file type in [Station] section")
        for s in self.SchedTypes:
            if s not in self.allowed_sched_types:
                raise Exception("Config file has unrecognised schedule file format '{}' ([Station] section)".format(s))

        # Stations text format
        if not self.Stations:
            raise Exception("Config file must specify at least one station in [Station] section")

        for s in self.Stations:
            if len(s) != 2:
                msg = 'Station name length wrong: "{}". Should be two characters.'.format(s)
                raise Exception(msg)

        # FS directories exist?
        if not path.exists(self.FsDir):
            raise OSError(2, "Can't find the Field System directory specified in the config file: ",
                          self.FsDir)

        if not path.exists(self.StDir):
            raise OSError(2, "Can't find the Field System directory specified in the config file: ",
                          self.StDir)

        # curl files
        if not path.exists(self.NetrcDir):
            raise OSError(2, "Can't find the netrc file (needed for curl) specified in the config file: ",
                          self.NetrcDir)

        # Drudg paths exist?
        if not path.exists(self.DrudgBinary):
            raise OSError(2, "Can't find the drudg executable. Check the config file is correct: ",
                          self.DrudgBinary)
        if not path.exists(self.LstDir):
            raise OSError(2, "Can't find the directory for the Drudg LST file. Check the config file is correct: ",
                          self.LstDir)
