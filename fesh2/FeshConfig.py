#!/usr/bin/env python3

import sys
import configparser
from configparser import ExtendedInterpolation
from os import path
import string


class Config:
    def __init__(self):
        # recognised schedule file types
        self.allowed_sched_types = ["vex", "skd"]

        def parse_onoff(val):
            val = val.lower()
            if val in ["on", "off"]:
                return val
            else:
                return "off"

        def parse_ccal_pol(val):
            val = val.lower()
            if val in ["none", "0", "1", "2", "3"]:
                return val
            else:
                return "none"

        def parse_vsi_align(val):
            val = val.lower()
            if val in ["none", "0", "1"]:
                return val
            else:
                return "none"

        self.config = configparser.ConfigParser(
            converters={
                "onoff": parse_onoff,
                "contcalpol": parse_ccal_pol,
                "vsialign": parse_vsi_align,
            }
        )
        self.config._interpolation = ExtendedInterpolation()

        self.ContCalAction = "off"
        self.ContCalPolarity = "none"
        self.DoDrudg = True
        self.DrudgBinary = "/usr2/fs/bin/drudg"
        # self.FsDir = "/usr2/fs"
        self.GetMaster = True
        self.GetMasterIntensive = True
        self.LogDir = "/usr2/log"
        self.LookAheadTimeDays = 14.0
        self.LstDir = "/usr2/sched"
        self.MasterCheckTime = 12.0
        self.NetrcFile = ""
        self.CookiesFile = ""
        self.CurlSecLevel1 = False
        self.ProcDir = "/usr2/proc"
        self.SchedDir = "/usr2/sched"
        self.SchedTypes = ["vex", "skd"]
        self.ScheduleCheckTime = 1.0
        self.Servers = [
            "https://cddis.nasa.gov/archive/vlbi",
            "ftp://ivs.bkg.bund.de/pub/vlbi",
            "ftp://ivsopar.obspm.fr/pub/vlbi",
        ]
        # self.StDir = "/usr2/st"
        self.Stations = ["Hb", "Ho", "Ke", "Yg"]
        self.TpiPeriod = 0
        self.VsiAlign = "none"
        self.ContCalAction = "off"
        self.ContCalPolarity = "none"

        # Things not in the config file:

        self.all_stations = False
        self.check = False
        self.ConfigFile = None
        self.current = False
        self.g = None  # Just look for schedules from this session
        self.master_update = False  # Force a download of the master file(s)
        self.once = False
        self.quiet = True
        self.sched_update = False  # Force a download of the schedule file(s)
        self.year = 2020

        self.logger = None

    def load(self, arg):
        # arg is an Args instance

        self.Stations = [word.strip(string.punctuation) for word in arg.args.Stations]
        # convert station names to lower case`
        self.Stations = list(map(lambda x: x.lower(), self.Stations))

        self.SchedDir = arg.args.SchedDir
        self.ProcDir = arg.args.ProcDir
        self.SnapDir = arg.args.SnapDir

        self.LstDir = arg.args.LstDir.strip("'\\\"")
        self.LogDir = arg.args.LogDir

        # get list of file servers
        self.Servers = [word.strip(string.punctuation) for word in arg.args.Servers]

        # get prioritised list of schedule file formats
        self.SchedTypes = [
            word.strip(string.punctuation) for word in arg.args.SchedTypes
        ]

        self.MasterCheckTime = arg.args.MasterCheckTime
        self.ScheduleCheckTime = arg.args.ScheduleCheckTime
        self.LookAheadTimeDays = arg.args.LookAheadTimeDays

        self.NetrcFile = arg.args.NetrcFile.strip("'\\\"")
        self.CookiesFile = arg.args.CookiesFile.strip("'\\\"")
        self.CurlSecLevel1 = arg.args.CurlSecLevel1

        self.DoDrudg = arg.args.DoDrudg
        self.DrudgBinary = arg.args.DrudgBinary

        self.GetMaster = arg.args.GetMaster
        self.GetMasterIntensive = arg.args.GetMasterIntensive
        if arg.args.g:
            self.g = arg.args.g
        self.force_master_update = arg.args.master_update
        self.force_sched_update = arg.args.sched_update
        self.current = arg.args.current
        self.run_once = arg.args.once
        self.all_stations = arg.args.all
        self.check = arg.args.check
        self.quiet = arg.args.quiet
        self.year = arg.args.year
        self.TpiPeriod = arg.args.TpiPeriod
        self.VsiAlign = arg.args.VsiAlign
        self.ContCalAction = arg.args.ContCalAction
        self.ContCalPolarity = arg.args.ContCalPolarity
        self.update = arg.args.update

    def check_config(self):
        # Check the configuration

        # Servers
        if not self.Servers:
            raise Exception(
                "Config file must specify at least one schedule server in [Servers] section"
            )

        if not self.SchedTypes:
            raise Exception(
                "Config file must specify at least one schedule file type in [Station] section"
            )
        for s in self.SchedTypes:
            if s not in self.allowed_sched_types:
                raise Exception(
                    "Config file has unrecognised schedule file format '{}' ([Station] section)".format(
                        s
                    )
                )

        # Stations text format
        if not self.Stations:
            raise Exception(
                "Config file must specify at least one station in [Station] section"
            )

        for s in self.Stations:
            if len(s) != 2:
                msg = 'Station name length wrong: "{}". Should be two characters.'.format(
                    s
                )
                raise Exception(msg)

        # # FS directories exist?
        # if not path.exists(self.FsDir):
        #     raise OSError(
        #         2,
        #         "Can't find the Field System directory specified in the config file: ",
        #         self.FsDir,
        #     )
        #
        # if not path.exists(self.StDir):
        #     raise OSError(
        #         2,
        #         "Can't find the Field System directory specified in the config file: ",
        #         self.StDir,
        #     )

        # curl files
        if not path.exists(self.NetrcFile):
            raise OSError(
                2,
                "Can't find the specified netrc file (needed for curl): ",
                self.NetrcFile,
            )
        if not path.exists(self.CookiesFile):
            raise OSError(
                2,
                "Can't find the specified cookies file (needed for curl): ",
                self.CookiesFile,
            )

        # Drudg paths exist?
        if not path.exists(self.DrudgBinary):
            raise OSError(
                2,
                "Can't find the drudg executable. Check the config file is correct: ",
                self.DrudgBinary,
            )
        if not path.exists(self.LstDir):
            raise OSError(
                2,
                "Can't find the directory for the Drudg LST file. Check the config file is correct: ",
                self.LstDir,
            )

        # Drudg prompts. If setting is to prompt the user, set a default

        if "yes" in self.TpiPeriod.lower():
            self.TpiPeriod = 0
        if "ask" in self.VsiAlign.lower():
            self.VsiAlign = "NONE"
        if "ask" in self.ContCalAction.lower():
            self.ContCalAction = "OFF"
        if "ask" in self.ContCalPolarity.lower():
            self.ContCalPolarity = "NONE"
