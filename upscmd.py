#!/bin/python2
import sys
import telnetlib
import time

user = "<the upsd_username set in upsd.users>"
pwd = "<the upsd_pwd set in upsd.users>"

if len(sys.argv) == 2:
    cmd = sys.argv[1]
else:
    print("the ups command to issue is missing.")
    print("example: upscmd.py beeper.enable")
    exit(1)

tn = None
for attempt in range(10):
    try:
        print("Connecting to UPS (attempt {}/10)...".format(attempt + 1))
        tn = telnetlib.Telnet("127.0.0.1", 3493, timeout=3)
        break
    except Exception as e:
        print("Connection failed: {}".format(e))
        time.sleep(10)

if tn is None:
    print("ERROR: Unable to connect to UPS after 10 attempts.")
    exit(1)

tn.write("USERNAME {0}\n".format(user))
response = tn.read_until("OK", timeout=2)
print("USERNAME: {0}".format(response.strip()))

tn.write("PASSWORD {0}\n".format(pwd))
response = tn.read_until("OK", timeout=2)
print("PASSWORD: {0}".format(response.strip()))

tn.write("INSTCMD ups {0}\n".format(cmd))
response = tn.read_until("OK", timeout=2)
print("INSTCMD ups {0}: {1}".format(cmd, response.strip()))

if response.strip() != "OK":
  tn.write("LIST CMD ups\n")
  response = tn.read_until("END LIST CMD ups", timeout=2)
  print("\n>> AVAILABLE CMDS:")
  cmds = response.splitlines()[1:-1]
  for cmd in cmds:
    print(cmd.replace("CMD ups ", "- "))

tn.write("LOGOUT\n")
print tn.read_all().rstrip("\n")
