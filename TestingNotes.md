# Tests
* Flow of parameter setting. Command-line to Env to config
* make sure skedf.ctl parameters are dealt with correctly
* Try setting sched directory to '.'
* check config parameters are interpreted correctly when comma-separated
 (stations and schedtypes)
* does fesh2 handle non-defined parameters in fesh2.config correctly?
* new schedule scenario
* check scenario
* force update scenario
* log file content
* python v 2.7.16, 3.5.3, 3.7.3
* run for an extended period

Item | 2.7.16 | 3.5.3 | 3.7.3
---- | --- | --- | ---
skedf and fesh2 config files flow | | |
env variables trump config | Y | Y | Y
command-line trumps all | Y | Y | Y
-h, --help | Y | Y | Y
-c CONFIGFILE, --ConfigFile CONFIGFILE | Y | Y | Y
-g G  | Y | Y | Y
-m, --master-update | Y | Y | Y
-u, --sched-update | Y | Y | Y
-n, --current, --now | Y | Y | Y
-a, --all              | Y | Y | Y
-o, --once             | Y | Y | Y
--update               | Y | Y | Y
--SchedDir SCHEDDIR    | Y | Y | Y
--ProcDir PROCDIR      | Y | Y | Y
--SnapDir SNAPDIR      | Y | Y | Y
--LstDir LSTDIR        | Y | Y | Y
--LogDir LOGDIR        | Y | Y | Y
--Stations [STATIONS [STATIONS ...]]  | Y | Y | Y
--GetMaster            | Y | Y | Y
--GetMasterIntensive   | Y | Y | Y
--SchedTypes           | Y | Y | Y
-t MASTERCHECKTIME, --MasterCheckTime MASTERCHECKTIME  | Y | Y | Y
-s SCHEDULECHECKTIME, --ScheduleCheckTime SCHEDULECHECKTIME  | Y | Y | Y
-l LOOKAHEADTIMEDAYS, --LookAheadTimeDays LOOKAHEADTIMEDAYS  | Y | Y | Y
-d [DODRUDG], --DoDrudg [DODRUDG]  | Y | Y | Y
--DrudgBinary DRUDGBINARY  | Y | Y | Y
--TpiPeriod TPIPERIOD  |Y  | Y |  Y
--VsiAlign VSIALIGN    | | | Not tested
--ContCalAction CONTCALACTION  | Y | Y | Y
--ContCalPolarity CONTCALPOLARITY  | Y | Y | Y
--Servers [SERVERS [SERVERS ...]]  | Y | Y | Y
--NetrcFile NETRCFILE  | Y | Y | Y
--CookiesFile COOKIESFILE  | Y | Y | Y
--CurlSecLevel1        | Y | Y | Y
-y YEAR, --year YEAR   | Y | Y | Y
-e, --check            | Y | Y | Y
-q, --quiet            | Y | Y | Y
| | |
skedf '.' response | Y | | Y
skedf directories | Y | | Y
Ctrl-C | Y* | | Y
extended run | | Y |

    ssh -p 2223 jlovell@localhost
    cd Automation
    source env/bin/activate
    cd fesh2_test

environment variables trump config. Try setting LIST_DIR, NETRC_FILE
, COOKIES_FILE

    PYTHONUNBUFFERED=1;LIST_DIR=/tmp/;NETRC_FILE=/home/jlovell/.netrc
    ;COOKIES_FILE=/home/jlovell/.urs_cookies
    
Command line trumps all. 
* Keep above env vars and add

    --LstDir /usr2/proc --NetrcFile /home/jlovell/.notrc --CookiesFile /tmp
    check cnf

* Add:
            

skedf '.':
    
    cp ../test_files/skedf.ctl_dotsched /usr2/control/skedf.ctl
    run
    should raise and Exception and a message
    
skedf directories (set all to /tmp/):

    cp ../test_files/skedf.ctl_alltmp /usr2/control/skedf.ctl
    Set break point after config loaded
    run
    check contents of cnf
    cp ../test_files/skedf.ctl /usr2/control/skedf.ctl
    
command line parameters tests

    python3 -m fesh2 -h
    python3 -m fesh2 -c /home/jlovell/Automation/test_files/fesh2.config_-ctest
    python3 -m fesh2  -g r1974 
    python3 -m fesh2  -m, --master-update
    python3 -m fesh2  -u, --sched-update
    python3 -m fesh2  -n, --current, --now
    python3 -m fesh2  --Stations hb ke yg -a            
    python3 -m fesh2  -o, --once            
    python3 -m fesh2  --update  
        run to get a sched file, then change mod times. e.g.:
            python3 -m fesh2  -o   
            vi /usr2/sched/aov053.skd (change something)
            touch -m -t 202010101200 /usr2/*/aov053*
            python3 -m fesh2  -o
            (should see the warning)
            python3 -m fesh2 -o --update --DoDrudg -g aov053
                    
    mkdir /tmp/sched
    mkdir /tmp/proc                
    mkdir /tmp/snap                
    mkdir /tmp/lst                
    mkdir /tmp/log                
    python -m fesh2  -o --SchedDir /tmp/sched   
    python -m fesh2  -o --ProcDir /tmp/proc     
    python -m fesh2  -o --SnapDir /tmp/snap     
    python -m fesh2  -o --LstDir /tmp/lst       
    python -m fesh2  -o --LogDir /tmp/log  
        rm /tmp/*/aov*
        python -m fesh2  -o --LogDir /tmp/log --SchedDir /tmp/sched --ProcDir /tmp/proc --SnapDir /tmp/snap --LstDir /tmp/lst 
         
    python -m fesh2  --Stations hb ke yg
    python -m fesh2  -o --GetMaster False        
    python -m fesh2  -o --GetMasterIntensive False
    rm /usr2/*/aov*
    python -m fesh2  -o --SchedTypes vex
    python -m fesh2  -o --SchedTypes skd
    python -m fesh2  -o --SchedTypes vex skd
    
    python -m fesh2  -t 18
    python -m fesh2  --MasterCheckTime 18

    python -m fesh2  -s 14
    python -m fesh2  --ScheduleCheckTime 14
    
    python -m fesh2  -s 14 - t 18
    python -m fesh2  -s 18 - t 14

    python -m fesh2  -l 30
    python -m fesh2  --LookAheadTimeDays 12

    python -m fesh2  -d [DODRUDG], --DoDrudg [DODRUDG]
        rm /usr2/*/aov*
        python -m fesh2  -o -d False
        python -m fesh2  -o --DoDrudg False
        python -m fesh2  -o --DoDrudg

    python -m fesh2  --DrudgBinary DRUDGBINARY
        rm /usr2/*/aov*
        python -m fesh2  --DrudgBinary /usr2/fs/bin/drudg_same
        python -m fesh2  --DrudgBinary /usr2/fs/bin/drudg_same2
        
    python -m fesh2  --TpiPeriod TPIPERIOD
    python -m fesh2  --VsiAlign VSIALIGN   
    python -m fesh2  --ContCalAction CONTCALACTION
    python -m fesh2  --ContCalPolarity CONTCALPOLARITY
        rm /usr2/*/aov*
        python -m fesh2  --TpiPeriod 10 --VsiAlign 0 --ContCalAction on
         --ContCalPolarity 0
         
    python -m fesh2  --Servers https://cddis.nasa.gov/archive/vlbi
    python -m fesh2  --Servers ftp://ivs.bkg.bund.de/pub/vlbi https://cddis.nasa.gov/archive/vlbi
    
    python -m fesh2  --NetrcFile NETRCFILE  see above
    python -m fesh2  --CookiesFile COOKIESFILE see above

    python -m fesh2  --CurlSecLevel1 False      
    python -m fesh2  --CurlSecLevel1 True      

    python -m fesh2  -y 2019
     
    python -m fesh2  -e, --check           
    python -m fesh2  -q, --quiet           
