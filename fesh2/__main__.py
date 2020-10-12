#!/usr/bin/env python
from __future__ import print_function

# Inspired by nobs and fesh
from collections import OrderedDict

import configargparse
import datetime
import logging
import os
import sys
import threading
import time
import string
import signal
import re

from functools import partial
from logging.handlers import RotatingFileHandler

from fesh2.FeshConfig import Config
from fesh2.MasterSession import Session
from fesh2.Drudgery import Drudg
from fesh2 import SchedServer
from os import path
from datetime import datetime, timedelta


# TODO: Move to toml for configuration?
# TODO: If NETRC_DIR is defined, use it in preference to config file
# TODO: respect sked.ctl. See https://github.com/jejl/fesh2/issues/1

# TODO: Test with different Python versions. 2.7.3, 3.2.3 on pcfshb back to v 3.5.3 and v 2.7
# TODO: Test on old versions of Debian: Etch, Wheezy
# TODO: Logging to MAS?


# Defaults
# Name (including full path) to the configuration file
default_config_files = ["/usr2/control/fesh2.config"]
# Name of the log file. Do not include the path as this should be in the config file
log_filename = "fesh2.log"


def main_task(config):
    """
    When triggered, this will check for master and schedule files and process them with Drudg.

    :param config: Configuration parameters
    :type config: Config Class
    :return: none
    :rtype: none
    """

    # --------------------------------------------------------------------------
    if not config.check:
        # update local copy of master schedule (optional) unless we are just
        # after a status report.
        # config.logger.info("Checking the Master File...")
        if config.GetMaster:
            new = check_master(config, intensive=False)
        if config.GetMasterIntensive:
            new = check_master(config, intensive=True)
    # --------------------------------------------------------------------------
    # Read in the Master File
    # Make a list of master files to process
    mstrs = []
    if config.GetMaster:
        local_file = "{}/master{:02d}.txt".format(config.SchedDir, config.year - 2000)
        if path.exists(local_file):
            mstrs.append(local_file)
    if config.GetMasterIntensive:
        local_file = "{}/master{:02d}-int.txt".format(
            config.SchedDir, config.year - 2000
        )
        if path.exists(local_file):
            mstrs.append(local_file)
    if not mstrs:
        # No Master files obtained
        msg = "No Master file(s) found. Exiting"
        logging.error(msg)
        raise Exception(msg)

    # list of all sessions in time order
    sessions_queue_ses = read_master(mstrs, config.year, config.Stations)
    # which session(s) we process depends on arguments and config
    sessions_to_process = []
    if config.g:
        # if args.g is set then we want a specific session regardless of time or anything else
        sessions_to_process = list(
            filter(lambda i: i.code in config.g, sessions_queue_ses)
        )
    else:
        now = datetime.utcnow()
        for ses in sessions_queue_ses:
            if config.current and (ses.start <= now < ses.end or ses.start >= now):
                # ifargs.current is set then get the current or next session
                sessions_to_process = [ses]
                # now break out of the for loop
                break
            elif (ses.start <= now < ses.end) or (
                now <= ses.start < now + timedelta(days=config.LookAheadTimeDays)
            ):
                # only consider scheds within the lookahead time
                # If:
                #       1. we don't want a session with all our stations in it AND at least one of our stations in in the session
                #    OR:
                #       2. we want a session with all our stations in it AND this session satisfies that requirement
                #    THEN:
                #       We found it, so stop searching through the master schedule
                if (not config.all_stations and ses.our_stns_in_exp != set()) or (
                    config.all_stations and ses.our_stns_in_exp == set(config.Stations)
                ):
                    sessions_to_process.append(ses)
    # sessions_to_process should now be filled

    # If sessions_to_process is not empty then we found a session satisfying the input criteria
    if not sessions_to_process:
        logging.warning("No sessions were found that satisfy the criteria")
    else:
        # Process each session in the list
        for ses in sessions_to_process:
            (got_sched_file, new, sched_type) = check_sched(ses, config)
            if not config.check:
                # Drudg the schedule
                drudg_session(ses, config, got_sched_file, new, sched_type)

    if not config.check:
        # If forced downloads were set, unset them now
        if config.force_sched_update:
            logging.info(
                "A forced schedule download was set. This has now been attempted so stopping the force."
            )
            config.force_sched_update = False
        if config.force_master_update:
            logging.info(
                "A forced Master schedule download was set. This has now been attempted so stopping the force."
            )
            config.force_master_update = False
    # show a summary of the sessions
    show_summary(config, mstrs, sessions_to_process)
    # Record the time of the last update (only if we're not doing a status check)
    sched_check_text = "** Schedule check completed **"
    if not config.check:
        # get the current level
        lgr = logging.getLogger()
        llevel = lgr.getEffectiveLevel()
        # make sure the log level is INFO
        lgr.setLevel(logging.INFO)
        # send a message
        logging.info(sched_check_text)
        # revert log level
        lgr.setLevel(llevel)
    else:
        # read the log file and find the time of the last sched_check_text
        lastfound = None
        with open(logging.Logger.root.handlers[0].baseFilename) as fh:
            data = fh.readlines()
        for line in data:
            if sched_check_text in line:
                lastfound = line
        if lastfound:
            sp = lastfound.split()
            dt = datetime.fromisoformat("{} {}".format(sp[0], sp[1]))
            delta = (datetime.utcnow() - dt).total_seconds()
            delta_h = int((delta - delta % 3600) / 3600)
            delta_m = int((delta - (3600 * delta_h)) / 60)
            logging.info(
                "Schedules were last checked {:02d}:{:02d} ago (HH:MM)".format(
                    delta_h, delta_m
                )
            )


def check_master(cnf, intensive=False):
    """
    Decides if the Master file needs checking, interrogates the server(s) and gets the most recent one if it
    has been updated.

    :param cnf: configuration parameters (from the config file)
    :type cnf: Config class
    :param intensive: Are we looking for an Intensive master file? (default is 24h session filee)
    :type intensive: boolean
    :return: Has a new version been retrieved?
    :rtype: boolean
    """
    new_sched = False
    if not intensive:
        cnf.logger.info(
            "Checking IVS 24h session Master File master{:02d}.txt".format(
                cnf.year - 2000
            )
        )
        local_file = "{}/master{:02d}.txt".format(cnf.SchedDir, cnf.year - 2000)
    else:
        cnf.logger.info(
            "Checking IVS Intensive session Master File master{:02d}-int.txt".format(
                cnf.year - 2000
            )
        )
        local_file = "{}/master{:02d}-int.txt".format(cnf.SchedDir, cnf.year - 2000)
    cnf.logger.debug("Local file is {}".format(local_file))
    now = time.time()
    if path.exists(local_file):
        stinfo = os.stat(local_file)
        file_access_time_local = stinfo.st_atime
    else:
        file_access_time_local = now
    timed_out = (now - 60 * 60 * cnf.MasterCheckTime) > file_access_time_local
    file_exists = path.exists(local_file)
    if timed_out or not file_exists or cnf.force_master_update:
        # we've waited long enough or the file doesn't exist locally or a download has been forced
        if timed_out:
            cnf.logger.info("It's been longer than the Master schedule check interval")
        if not file_exists:
            cnf.logger.info("File doesn't exist locally")
        if cnf.force_sched_update:
            cnf.logger.info("A download has been forced")
        # for each server, try to retrieve the file
        master_server = SchedServer.MasterServer(cnf.SchedDir)
        master_server.curl_setup(cnf.NetrcDir)
        force = cnf.force_master_update
        for server_url in cnf.servers:
            cnf.logger.info("Checking Master file(s) at {}".format(server_url))
            (success, new_sched) = master_server.get_master(
                server_url, cnf.year, cnf.SchedDir, force, 0, intensive
            )
            if force and success and new_sched:
                # We had a forced download and got the file. Now we only need to download from another server if it's
                # newer there. So set the force flag to False.
                force = False
        master_server.curl_close()
    else:
        cnf.logger.info(
            "Less than {} h since the file was last checked. Skipping".format(
                cnf.MasterCheckTime
            )
        )
    return new_sched


def check_sched(ses, config):
    """
    For a given session, decides if the schedule file needs checking, interrogates the server(s) and gets the most
    recent one if it hasn't been downloaded yet or has been updated.

    :param ses: The session to be processed
    :type ses: Session class
    :param config: configuration parameters (from the config file)
    :type config: Config class
    :return: got_sched_file: Did we get a file?,
    new: Is it new?
    sched_type: file type (vex or skd)
    :rtype: boolean, boolean, string
    """
    now = datetime.utcnow()
    new = False
    got_sched_file = False
    # Is the session current, the next one, or a specific one?
    if not config.check:
        logging.info(
            "Session: {}. Start {}, Stop {}, Stations: {}".format(
                ses.code, ses.start, ses.end, " ".join(sorted(ses.stations))
            )
        )
    if ses.start <= now < ses.end:
        # it's on now
        logging.debug("This session is currently running")
    elif ses.start >= now:
        # it's in the future
        logging.debug("This session is in the future")

    # set up for Schedule File operations
    if not config.check:
        config.logger.info(
            "Getting schedule file for {} if it's available...".format(ses.code)
        )
    # For each schedule type, go through the servers and check for them if they haven't
    sched_server = SchedServer.SchedFileServer(config.SchedDir)
    sched_server.curl_setup(config.NetrcDir)
    # do we have either a vex or skd file locally? If yes, then just check that type
    (got_sched_file, sched_type) = sched_server.check_exists_sched(ses.code, config)
    types = []
    if got_sched_file:
        # we have a local copy (downloaded previously), so just check this type
        types.append(sched_type)
    else:
        # we don't have any local files, so check all types
        types = config.SchedTypes
    # now go through the valid different types
    config.logger.debug("Checking file types {}".format(types))
    for type in types:
        # name of the local file:
        local_file = "{}/{}.{}".format(config.SchedDir, ses.code, type)
        config.logger.debug("Local file is {}".format(local_file))
        now_s = time.time()
        # get the last file access time (if it exists)
        if path.exists(local_file):
            stinfo = os.stat(local_file)
            file_access_time_local = stinfo.st_atime
        else:
            file_access_time_local = now_s
        # Should we check?
        timed_out = (
            now_s - 60 * 60 * config.ScheduleCheckTime
        ) > file_access_time_local
        file_exists = path.exists(local_file)
        if (
            not config.check
        ):  # If we just want a status report, don't access the servers
            if timed_out or not file_exists or config.force_sched_update:
                # we've waited long enough or the file doesn't exist locally or a download has been forced
                if timed_out:
                    config.logger.info(
                        "It's been longer than the schedule check interval"
                    )
                if not file_exists:
                    config.logger.info("File doesn't exist locally")
                if config.force_sched_update:
                    config.logger.info("A download has been forced")
                # for each server, try to retrieve the file
                force = config.force_sched_update
                for server_url in config.Servers:
                    # get the schedule. Set check_delta_hours=0 to make sure we get the latest version
                    # regardless of server
                    (
                        got_sched_file_from_server,
                        new_from_server,
                    ) = sched_server.get_sched(
                        server_url,
                        ses.code,
                        type,
                        config.year,
                        config.SchedDir,
                        force,
                        check_delta_hours=0,
                    )
                    if force and got_sched_file_from_server and new_from_server:
                        # We had a forced download and got the file. Now we only need to download from another server if it's
                        # newer there. So set the force flag to False.
                        force = False

                    if got_sched_file_from_server:
                        got_sched_file = True
                    if new_from_server:
                        new = True
            else:
                if not timed_out:
                    config.logger.info(
                        "It's less than {} h since the last schedule check. Not checking.".format(
                            config.ScheduleCheckTime
                        )
                    )
            if got_sched_file:
                # Got the file, don't keep looking down the prioritised list of types
                sched_type = type
                break
    sched_server.curl_close()

    return (got_sched_file, new, sched_type)


def drudg_session(ses, config, got_sched_file, new, sched_type):
    """
    Runs Drudg on the specified schedule file

    :param ses: The session to be processed
    :type ses: Session class
    :param config: configuration parameters (from the config file)
    :type config: Config class
    :param got_sched_file: Did we get a file?
    :type got_sched_file: boolean
    :param new: Is it a new file?
    :type new: boolean
    :param sched_type: schedule file type (vex or skd)
    :type sched_type: string
    :return: none
    :rtype: none
    """
    if not config.DoDrudg:
        logging.info("Drudg will not be run on the schedule file")
    else:
        update_stns = []
        drg = Drudg(
            config.DrudgBinary,
            config.SchedDir,
            config.ProcDir,
            sched_type,
            config.LstDir,
        )

        if not new:
            # Checks came back with no new schedule file or no schedule file at all.
            if not got_sched_file:
                logging.info("There is no schedule file on the server.")
            else:
                logging.info("The local copy of the schedule file hasn't changed.")
                # Has the file been drudged?
                # Look for snp, prc files that are later than the modification time of the schedule file
                for station in ses.our_stns_in_exp:
                    drudge_products_up_to_date = drg.check_drudg_output_time(
                        config.SchedDir, config.ProcDir, sched_type, ses.code, station,
                    )
                    if not drudge_products_up_to_date:
                        update_stns.append(station)
        else:
            # There's a new schedule file
            for i in ses.our_stns_in_exp:
                update_stns.append(i)
        if update_stns:
            # Run drudg
            # print("Run drudg for these stations: {}".format(update_stns))
            for s in update_stns:
                (o1, o2, o3) = drg.godrudg(s, ses.code, config)
                logging.info(
                    "Drudg created the following files: {} {} {}".format(o1, o2, o3)
                )
                # put them in the locations specified by the config file


def show_summary(config, mstrs, sessions_to_process):
    """
    Prints a summary of the status of session processing ro the screen
    :param config: configuration parameters (from the config file)
    :type config: Config class
    :param mstrs: list of master file names (full path)
    :type mstrs: array of strings
    :param sessions_to_process: List of sessions to process
    :type sessions_to_process: Session class
    :return: none
    :rtype: none
    """
    config.logger.info("--------------------------------------------------------------")
    config.logger.info(
        Colour.BOLD
        + Colour.UNDERLINE
        + "Schedule Status for {}:".format(", ".join(sorted(config.Stations)))
        + Colour.END
    )
    if len(mstrs) > 1:
        config.logger.info(
            Colour.UNDERLINE
            + "Master file versions (UTC of latest version downloaded):"
            + Colour.END
        )
    else:
        config.logger.info(
            Colour.UNDERLINE
            + "Master file version (UTC of latest version downloaded):"
            + Colour.END
        )
    for m in mstrs:
        stinfo = os.stat(m)
        tvers_txt = time.strftime("%Y-%m-%d %H:%M", time.gmtime(stinfo.st_mtime))
        if "int" in m:
            config.logger.info("\tIntensive sessions: {}".format(tvers_txt))
        else:
            config.logger.info("\t24h sessions:       {}".format(tvers_txt))
    config.logger.info("")
    config.logger.info(Colour.UNDERLINE + "Sessions:" + Colour.END)
    if not sessions_to_process:
        config.logger.info("\tNo sessions to process")
    else:
        if len(config.Stations) > 1:
            config.logger.info(
                "Session   Start (UT)         Got         Age*    FS files prepared?"
            )
            txt = "                             schedule?   (hrs)   "
            for i in config.Stations:
                txt = "{}{}     ".format(txt, i)
            config.logger.info(txt)
            txt = "-------   ----------------   ---------   -----   "
            for i in config.Stations:
                txt = "{}-------".format(txt)
            config.logger.info(txt)
        else:
            config.logger.info(
                "Session   Start (UT)         Got         Age*   FS files"
            )
            config.logger.info(
                "                             schedule?   (hrs)  prepared?"
            )
            config.logger.info(
                "-------   ----------------   ---------   -----  ---------"
            )
        for ses in sessions_to_process:
            txt = ""
            got_sched = False
            for ext in ("skd", "vex"):
                local_file = "{}/{}.{}".format(config.SchedDir, ses.code, ext)
                if path.exists(local_file):
                    got_sched = True
                    stinfo = os.stat(local_file)

            txt = "{}{:<7s}   {:<16s}   {:<9s}".format(
                txt, ses.code, ses.start.strftime("%Y-%m-%d %H:%M"), yn(got_sched)
            )
            if got_sched:
                txt = "{}   {:<5d}   ".format(
                    txt, int((time.time() - stinfo.st_mtime) / 60.0 / 60.0)
                )
            else:
                txt = "{}           ".format(txt)

            if len(config.Stations) > 1:
                got_snp = {}
                got_prc = {}
                got_lst = {}
                for i in config.Stations:
                    if i in ses.our_stns_in_exp:
                        got_snp[i] = path.exists(
                            "{}/{}{}.snp".format(config.SchedDir, ses.code, i)
                        )
                        got_prc[i] = path.exists(
                            "{}/{}{}.prc".format(config.ProcDir, ses.code, i)
                        )
                        got_lst[i] = path.exists(
                            "{}/{}{}.lst".format(config.LstDir, ses.code, i)
                        )
                        tmp_txt = "{}".format(
                            yn(got_snp[i] and got_prc[i] and got_lst[i])
                        )
                    else:
                        tmp_txt = "-"
                    txt = "{}{:<7s}".format(txt, tmp_txt)
                config.logger.info(txt)
            else:
                i = config.Stations[0]
                got_snp = path.exists(
                    "{}/{}{}.snp".format(config.SchedDir, ses.code, i)
                )
                got_prc = path.exists("{}/{}{}.prc".format(config.ProcDir, ses.code, i))
                got_lst = path.exists("{}/{}{}.lst".format(config.LstDir, ses.code, i))
                txt = "{}".format(yn(got_snp and got_prc and got_lst))
                config.logger.info(txt)

        config.logger.info("")
    config.logger.info("--------------------------------------------------------------")
    config.logger.info("[*] Age = time since the schedule file was released.")


def yn(a):
    """
    Takes a boolean and returns it as 'yes' or 'no'
    :param a: True or false
    :type a: boolean
    :return: 'Yes' if True, otherwise 'no'
    :rtype: string
    """
    if a:
        return "Yes"
    else:
        return "No"


class Colour:
    """
    Defines colours and styles for printing on a terminal
    """

    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    DARKCYAN = "\033[36m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


def read_master(files, year, stations):
    """
    Reads a list of master files and returns an array of sessions sorted by start time

    :param files: An array of filenames (including full path)
    :type files: array
    :param year: the year of the master schedule(s)
    :type year: int
    :param stations: A list of stations (2-letter codes) to process
    :type stations: array
    :return: lis, a list of sessions sorted by start time
    :rtype: an array of sessions from the Session class (see MasterSession.py)
    """

    # make the list of stations a set
    stns = set(stations)
    # this will contain a list of sessions
    sessions_queue_ses = []
    now = datetime.utcnow()
    for file in files:
        # read each master file in turn
        with open(file, mode="r") as fd:
            for line in fd.readlines():
                if line.startswith("|"):
                    # line starts with a |, so it's a session
                    # read it:
                    ses = Session(line, year)
                    # if any of our selected stations is in the session, tag it in ses.our_stns_in_exp
                    ses.our_stns_in_exp = stns.intersection(ses.stations)
                    # add the sesion to the list
                    sessions_queue_ses.append(ses)
    # sort the sessions by start time
    lis = sorted(sessions_queue_ses, key=lambda i: i.start)
    return lis


class CustomConfigParser:
    def __init__(self, *args, **kwargs):
        super(CustomConfigParser, self).__init__(*args, **kwargs)

    def parse(self, stream):
        items = OrderedDict()
        for i, line in enumerate(stream):
            line = line.strip()
            print(line)
            if not line or line[0] in ["*"]:
                # a comment or empty line
                continue
            space_and_comment_regex = "(?P<space_comment>\!\s*.*)*"
            if line[0] in ["$"]:
                # A key match
                key_regex = "\$(?P<key>.*)"
                key_match = re.match(key_regex + space_and_comment_regex + "$", line)
                if key_match:
                    key = key_match.group("key")
                    value = ""
                    items[key] = value.strip()
                    continue
            else:
                # its a value
                if key in ["catalogs", "schedules", "snap", "proc", "scratch"]:
                    # these have single values
                    value_regex = "^\s*(?P<value>.+?)" + space_and_comment_regex + "$"
                    value_match = re.match(value_regex, line)
                    value = value_match.group("value")
                    items[key] = value.strip()
                    continue
                if key in ["print", "misc"]:
                    # these classify multiple key/value pairs
                    white_space = "\s*"
                    # TODO: up to here equipment_override has e chopped off
                    key_val_regex = "^\s*(?P<key>\w*)\s*(?P<value>.*?)"
                    match = re.match(
                        key_val_regex + space_and_comment_regex + "$", line
                    )
                    if match:
                        sub_key = match.group("key")
                        value = match.group("value")
                        newkey = "{}.{}".format(key, sub_key)
                        # if not items[newkey]:
                        #     items[newkey] = OrderedDict()
                        items[newkey] = value.strip()
                        continue
            raise "Unexpected line {} in {}: {}".format(
                i, getattr(stream, "name", "stream"), line
            )
        return items


class Args:
    """
    This class uses the Python Argparse library to process command-line arguments
    """

    def __init__(self, default_config_files):
        """
        Set up command-line paramaters
        """

        parser_skedf = configargparse.ArgParser(
            default_config_files=["/usr2/control/skedf.ctl"],
            config_file_parser_class=CustomConfigParser,
        )
        # Not setting up and arguments here. Getting args back as a list in args_skedf[1]. Use these as default
        # values below, to be overriden by the command line, env_variables when we run ArgParser
        args_skedf = parser_skedf.parse_known_args()

        items = OrderedDict()
        for keyval in args_skedf[1]:
            if '=' in keyval:
                (k, v) = keyval.split("=")
                print(k, v)
                items[k[2:]] = v
        #TODO: up to here. decide how to assign defaults for fesh

        now = datetime.utcnow()
        self.parser = configargparse.ArgParser(
            default_config_files=default_config_files,
            #            config_file_parser_class=configargparse.ConfigparserConfigFileParser,
            description=(
                "Automated schedule file preparation for the current, next or specified session.\n\n"
                "A check for the latest version of the Master File(s) is done first, but skipped if the\n"
                "time since the last check is less than a specified amount (configureable on the command\n"
                "line or in the config file). Similarly, checks on schedule files are only done if the\n"
                "time since the last check exceeds a specified time.\nChecks can be forced on the command\n"
                "line."
            ),
        )
        self.parser.add_argument(
            "--Stations",
            nargs="*",
            # default=['hb', 'ke', 'yg', 'ho'],
            # type=self.station_label,
            help='Stations to consider (default "hb ke yg ho")',
        )
        self.parser.add_argument(
            "-c",
            "--ConfigFile",
            #            required= True,
            is_config_file=True,
            #            default=config_filename,
            help="The configuration file to use. (default is {})".format(
                default_config_files
            ),
        )

        self.parser.add_argument(
            "--FsDir", default="/usr2/fs", help="Field system top directory",
        )

        self.parser.add_argument(
            "--TopDir", default="/usr2", help="Top directory for the Field System. the fs, st and control directories "
                                              "top directory",
        )

        self.parser.add_argument(
            "--StDir", default="/usr2/st", help="Station-specific FS directory",
        )


        self.parser.add_argument(
            "--SchedDir",
            default=get_default(items, 'schedules', '/usr2/sched/'),
            help="Schedule directory (including Master file)",
        )

        self.parser.add_argument(
            "--ProcDir", default=get_default(items, 'proc', '/usr2/proc/'), help="Procedure file directory",
        )

        self.parser.add_argument(
            "--LstDir", default="/usr2/sched", help="LST file directory",
        )

        self.parser.add_argument(
            "--LogDir", default="/usr2/log", help="Log file directory",
        )

        self.parser.add_argument(
            "--GetMaster",
            default=True,
            action="store_true",
            help="Maintain a local copy of the main Multi-Agency schedule, i.e. mostly 24h sessions",
        )

        self.parser.add_argument(
            "--GetMasterIntensive",
            default=True,
            action="store_true",
            help="Maintain a local copy of the main Multi-Agency Intensive schedule",
        )

        self.parser.add_argument(
            "--SchedTypes",
            nargs="*",
            default=["vex", "skd"],
            # type=self.station_label,
            help="Schedule file formats to be obtained? This is a prioritised list with the highest priority "
            "first. Use the file name suffix (vex and/or skd) and comma-separated",
        )

        self.parser.add_argument(
            "-g",
            default=None,
            help="Just get a schedule for this specified session. Give the name of the session (e.g. r4951).",
        )

        self.parser.add_argument(
            "-t",
            "--MasterCheckTime",
            type=float,
            help="Only check for a new master file if the last check "
            "was more than this number of hours ago. The default "
            "is set in the configuration file.",
        )

        self.parser.add_argument(
            "-s",
            "--ScheduleCheckTime",
            type=float,
            help="Only check for a new schedule file (SKD or VEX) if the last check "
            "was more than this number of hours ago. The default "
            "is set in the configuration file.",
        )

        self.parser.add_argument(
            "-m",
            "--master-update",
            action="store_true",
            default=False,
            help="Force a download of the Master Schedule (default = False).",
        )

        self.parser.add_argument(
            "-u",
            "--sched-update",
            action="store_true",
            default=False,
            help="Force a download of the Schedules (default = False).",
        )

        self.parser.add_argument(
            "-d",
            "--DoDrudg",
            action="store_true",
            default=True,
            help="Run Drudg on the downloaded/updated schedules (default = True)",
        )

        self.parser.add_argument(
            "--DrudgBinary", default="/usr2/proc", help="Log file directory",
        )

        self.parser.add_argument(
            "--TpiPeriod",
            default=0,
            type=int,
            help="Drudg config: TPI period in centiseconds. 0 = don't use the TPI daemon (default)",
        )

        self.parser.add_argument(
            "--ContCalAction",
            default="off",
            help="Drudg config: Continuous cal option. Either 'on' or 'off'. Default is 'off'",
        )

        self.parser.add_argument(
            "--ContCalPolarity",
            default="none",
            help="Drudg config: If continuous cal is in use, what is the polarity? Options are 0-3 or 'none'. Default is none",
        )

        self.parser.add_argument(
            "--VsiAlign",
            default="none",
            help="Drudg config: Applicable only for PFB DBBCs,\nnone = never use dbbc=vsi_align=... (default)\n0 = "
            "always use dbbc=vsi_align=0\n1 = always use dbbc=vsi_align=1",
        )

        self.parser.add_argument(
            "--Servers",
            nargs="*",
            default=[
                "https://cddis.nasa.gov/archive/vlbi",
                "ftp://ivs.bkg.bund.de/pub/vlbi",
                "ftp://ivsopar.obspm.fr/pub/vlbi",
            ],
            # type=self.station_label,
            help="Schedule file server URLs. Each of these will be checked for the most recent files. Use "
            "comma-separated URLs and specify the top directory (i.e. the 'vlbi' directory). Use protocols https "
            "(Curl), ftp (anonymous FTP) or sftp (anonymous secure FTP)",
        )

        self.parser.add_argument(
            "--NetrcDir",
            default="/usr2/control",
            env_var="NETRC_DIR",
            help="The directory where the .netrc and .urs_cookies files are kept for CURL. (CURL puts this in "
            "~/.netrc by default)",
        )

        self.parser.add_argument(
            "-n",
            "--current",
            "--now",
            action="store_true",
            default=False,
            help="Only process the current or next experiment",
        )

        self.parser.add_argument(
            "-a",
            "--all",
            action="store_true",
            help='find the experiments with all "Stations" in it',
        )

        self.parser.add_argument(
            "-o",
            "--once",
            action="store_true",
            default=False,
            help="Just run once then exit, don't go into a wait loop (default = False)",
        )

        self.parser.add_argument(
            "-l",
            "--LookAheadTimeDays",
            default=None,
            type=float,
            help="only look for schedules less than this number of days away (default is 7)",
        )

        # self.parser.add_argument('-p', '--tpi-period', default=None, type=int, help="TPI period in centiseconds (0
        # = don't use the TPI Daemon, default). This can be set in the config file.")

        self.parser.add_argument(
            "-y",
            "--year",
            default=now.year,
            type=int,
            help="The year of the Master Schedule (default is {})".format(now.year),
        )

        self.parser.add_argument(
            "-e",
            "--check",
            action="store_true",
            help="Check the current fesh2 status. Shows if the systemd service is running and prints the status of "
            "schedule files",
        )

        self.parser.add_argument(
            "-q",
            "--quiet",
            action="store_true",
            help="Runs fesh2 with all terminal output suppressed. Useful when running fesh2 as a service.",
        )

        self.args = self.parser.parse_args()
        # if self.args.Stations:
        #     self.Stations = set(self.args.Stations)

    def station_label(self, str):
        """
        Used by Args class to check format of station ID strings
        :param str: station ID (punctuation etc will be removed)
        :type str: string
        :return: string, hopefully lower-case 2-letter code
        :rtype: string
        """
        str = str.strip(string.punctuation).lower()
        if len(str) != 2:
            msg = 'Station name length wrong: "{}". Should be two characters.'.format(
                str
            )
            raise configargparse.ArgumentTypeError(msg)
        return str

def get_default(items, key, defult):
    ''' given a dict, a key and a default, if the item[key] exists and it's not
    and empty string, return it as the default, otherwise 'default' is the default
    '''
    if key in items.keys():
        if items[key] != '':
            return items[key]
        else:
            return default

def start_thread_main(event, config):
    """
    Set up and start the wait_for_event thread 'sched_check' which does a schedule check when triggered
    by the 'timing_loop' thread

    :param event: When this event is set, a schedule check loop is done or underway
    :type event: threading event
    :param config: configuration parameters (from the config file)
    :type config: Config class
    :return: activated thread
    :rtype: a python threading thread.
    """
    thread = threading.Thread(
        name="sched_check", target=wait_for_event, args=(event, config)
    )
    thread.start()
    return thread


def start_thread_timing_loop(event_1, event_2, thread, config):
    """
    This thread manages the main_task wait loop. It waits a specified time (the shortest out of the master and schedule file
    check wait times) then triggers a check.

    :param event_1: When this event is set, a schedule check loop is done or underway
    :type event_1: threading event
    :param event_2: When this event is set, the event loop is exited
    :type event_2: threading event
    :param thread: the sched_check thread
    :type thread: a python threading thread
    :param config: configuration parameters (from the config file)
    :type config: Config class
    :return: activated thread
    :rtype: a python threading thread.
    """
    thread_2 = threading.Thread(
        name="timing_loop",
        target=set_event_loop,
        args=(event_1, event_2, thread, config),
    )
    thread_2.start()
    return thread_2


def wait_for_event(event, config):
    """
    Waits for the event to be triggerered, then does a schedule check.
    :param event: When this event is set, a schedule check loop is done or underway
    :type event: threading event
    :param config: configuration parameters (from the config file)
    :type config: Config class
    """
    config.logger.debug("WFE: wait for event")
    event_is_set = event.wait()
    config.logger.debug("WFE event set: {}".format(event_is_set))
    main_task(config)
    config.logger.debug("WFE: clearing event1...")
    event.clear()


def set_event_loop(event_1, event_2, thread, config):
    """
    Waits a specified time (the shortest out of the master and schedule file
    check wait times) then triggers a schedule check in the other thread.

    :param event_1: When this event is set, a schedule check loop is done or underway
    :type event_1: threading event
    :param event_2: When this event is set, the event loop is exited
    :type event_2: threading event
    :param thread: the sched_check thread
    :type thread: a python threading thread
    :param config: configuration parameters (from the config file)
    :type config: Config class
    """
    while not event_2.isSet():
        # get time to wait until next check from the smallest check interval. Add 30 sec just to make sure we don't
        # under-shoot
        t_wait_h = min([config.ScheduleCheckTime, config.MasterCheckTime])
        t_wait_s = (t_wait_h * 60 * 60) + 30
        start_time = time.time()
        target_time = start_time + t_wait_s
        barLength = 36
        test = time.time() >= target_time or event_2.isSet()
        # logging.debug(
        #     "set_event_loop top of wait loop. time.time() = {}, target_time = {}, event2.isSet() = {}, test = {}".format(start_time,target_time,event2.isSet(),test))
        nwaits = 0
        while not test:
            time.sleep(2)
            nwaits += 1
            dt = time.time() - start_time
            if dt < 0:
                dt = 0.0
            frac = dt / t_wait_s
            block = int(round(barLength * frac))

            if not config.quiet:
                text = "\rNext check in {} [{}]".format(
                    time.strftime("%H:%M:%S", time.gmtime(t_wait_s - dt)),
                    "=" * block + " " * (barLength - block),
                )
                sys.stdout.write(text)
                sys.stdout.flush()
            elif nwaits % 15 == 0:
                logging.info(
                    "Next check in {}".format(
                        time.strftime("%H:%M:%S", time.gmtime(t_wait_s - dt))
                    )
                )
            test_time = time.time()
            test = test_time >= target_time or event_2.isSet()
            # logging.debug(
            #     "set_event_loop bottom of wait loop. time.time() = {}, target_time = {}, event2.isSet() = {}, test = {}".format(start_time,target_time,event2.isSet(),test))
        if not config.quiet:
            print("")
        if event_1.isSet():
            # the check routine is still running, don't tell it to start again
            logging.warning(
                "set_event_loop: not signaling another schedule check as the previous one is still running. "
            )
        else:
            logging.debug("set_event_loop setting event")
            event_1.set()
            logging.debug("set_event_loop: wait for thread to finish")
            thread.join()
            logging.debug("set_event_loop: thread finished")
            logging.debug("set_event_loop: starting thread1")
            thread = start_thread_main(event_1, config)
            logging.debug("set_event_loop: thread started")
    logging.debug("Event 2 is set")


def signal_handler(event, thread, sig, frame):
    # see https://stackoverflow.com/questions/1112343/how-do-i-capture-sigint-in-python
    logging.warning("Interrupt sent. Will end threads and exit.")
    if thread:
        event.set()
        logging.warning("Waiting for up to 10 sec for the main thread to finish...")
        thread.join()
        if thread.is_alive():
            logging.warning("Thread is still alive. Exiting anyway.")
        else:
            logging.warning("Thread terminated.")
    logging.warning("Exiting.")
    sys.exit(0)


def main():
    """
    Reads command line arguments and the config file, starts logging, does an initial schedule
    check and then starts the two threads that manage the main_task loop to periodically check for
    schedule files and process them with Drudg 
    """
    # --------------------------------------------------------------------------
    # Read command-line arguments, config from the config file and env variables
    config_in = Args(default_config_files)
    # --------------------------------------------------------------------------
    # Create a configuration instance and add the parameters from above
    # Config instance
    cnf = Config()
    # Load in the
    cnf.load(config_in)
    # check the config makes sense
    cnf.check_config()
    # --------------------------------------------------------------------------
    # Set up logging
    log_file_str = "{}/{}".format(cnf.LogDir, log_filename)
    format_txt_main = "%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s"
    format_txt_short = "%(asctime)s - %(message)s"
    logging.basicConfig(
        #        filename=log_file_str,
        # filemode="a",
        format=format_txt_main,
        # level=logging.DEBUG,
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[RotatingFileHandler(log_file_str, maxBytes=1000000.0, backupCount=9)],
    )

    logging.Formatter.converter = time.gmtime
    cnf.logger = logging.getLogger()
    # handler = RotatingFileHandler(log_file_str, maxBytes=1000000.0, backupCount=9)
    # cnf.logger.addHandler(handler)
    # Rotate logs when they get larger than
    if not cnf.quiet:
        ch = logging.StreamHandler()
        # ch.setLevel(logging.INFO)
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(logging.Formatter(format_txt_short))
        cnf.logger.addHandler(ch)
        print("Writing to log file {}.".format(log_file_str))

    # What to do if someone generates a keyboard interrupt
    signal.signal(signal.SIGINT, partial(signal_handler, None, None))

    # run an initial update
    main_task(cnf)

    # Finish here if we are running in a one-pass only mode
    if (not cnf.run_once) and (not cnf.check):
        # Set up threading
        event1 = threading.Event()
        event2 = threading.Event()
        # Thread1 waits for event1 to set, then runs the schedule check
        thread1 = start_thread_main(event1, cnf)
        # event1.set()
        # Thread2 runs a timing loop to set event2 every (specified) minutes
        # If event2 is set then thread2 should quit
        thread2 = start_thread_timing_loop(event1, event2, thread1, cnf)
        # Set up so that keyboard interrupts will result in threads being terminated now
        signal.signal(signal.SIGINT, partial(signal_handler, event2, thread2))
    logging.shutdown()


if __name__ == "__main__":
    main()
