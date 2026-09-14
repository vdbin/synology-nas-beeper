#!/bin/python2
import sys
import telnetlib
import time
import subprocess

# user = "<the upsd_username set in upsd.users>"
# pwd = "<the upsd_pwd set in upsd.users>"
config_path = "/etc/ups/upsd.users"

if len(sys.argv) == 2:
    cmd = sys.argv[1]
else:
    print("the ups command to issue is missing.")
    print("example: upscmd.py beeper.disable")
    sys.exit(1)

def fix_config_and_reload(target_user):
    print("Access denied detected. Checking {0} for user [{1}]...".format(config_path, target_user))
    try:
        with open(config_path, "r") as f:
            lines = f.readlines()
    except Exception as e:
        print("Cannot read upsd.users: " + str(e))
        return False

    user_header = "[" + target_user + "]"
    user_found = False
    has_actions = False
    insert_idx = -1

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == user_header:
            user_found = True
            insert_idx = i + 1
            continue
        if user_found:
            if stripped.startswith("[") and stripped.endswith("]"):
                break
            if "actions = SET" in line:
                has_actions = True

    if user_found and not has_actions:
        print("Adding 'actions = SET' directly into [{0}] section...".format(target_user))
        lines.insert(insert_idx, "        instcmds = beeper.enable beeper.disable beeper.toggle ups.beeper.status\n")
        lines.insert(insert_idx, "        actions = SET\n")

        new_content = "".join(lines)
        p = subprocess.Popen(["sudo", "tee", config_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        p.communicate(input=new_content)

        print("Reloading upsd daemon...")
        subprocess.call(["sudo", "upsd", "-c", "reload"])
        time.sleep(3)
        return True
    elif not user_found:
        print("ERROR: User [{0}] was not found in {1}!".format(target_user, config_path))
        return False
    else:
        print("User [{0}] already has 'actions = SET' inside its block, but access is still denied.".format(target_user))
        return False

def execute_ups_cmd(retry_allowed=True):
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
        sys.exit(1)

    tn.write("USERNAME {0}\n".format(user))
    response = tn.read_until("OK", timeout=2)
    print("USERNAME: {0}".format(response.strip()))

    tn.write("PASSWORD {0}\n".format(pwd))
    response = tn.read_until("OK", timeout=2)
    print("PASSWORD: {0}".format(response.strip()))

    tn.write("INSTCMD ups {0}\n".format(cmd))
    response = tn.read_until("OK", timeout=2)
    resp_clean = response.strip()
    print("INSTCMD ups {0}: {1}".format(cmd, resp_clean))

    if "ERR ACCESS-DENIED" in resp_clean and retry_allowed:
        if fix_config_and_reload(user):
            tn.close()
            print("Retrying command execution...\n" + "-"*30)
            return execute_ups_cmd(retry_allowed=False)

    if resp_clean != "OK" and "ERR ACCESS-DENIED" not in resp_clean:
        tn.write("LIST CMD ups\n")
        response = tn.read_until("END LIST CMD ups", timeout=2)

        if cmd in ["beeper.enable", "beeper.disable"] and "beeper.toggle" in response:
            print("\n-- Command failed, checking beeper.toggle capability...")
            try:
                current_status = subprocess.check_output(["upsc", "ups", "ups.beeper.status"]).strip()
                print("Current ups.beeper.status: " + current_status)

                should_toggle = False
                if cmd == "beeper.enable" and current_status == "disabled":
                    should_toggle = True
                elif cmd == "beeper.disable" and current_status == "enabled":
                    should_toggle = True

                if should_toggle:
                    print("Status mismatch. Executing beeper.toggle...")
                    tn.write("INSTCMD ups beeper.toggle\n")
                    toggle_resp = tn.read_until("OK", timeout=2)
                    print("INSTCMD ups beeper.toggle: {0}".format(toggle_resp.strip()))
                else:
                    print("Beeper is already in the desired state (" + current_status + "). No action needed.")

            except Exception as e:
                print("Error checking status or toggling: " + str(e))
        else:
            print("\n-- AVAILABLE CMDS:")
            cmds = response.splitlines()[1:-1]
            for c in cmds:
                print(c.replace("CMD ups ", "- "))

    tn.write("LOGOUT\n")
    print tn.read_all().rstrip("\n")

if __name__ == "__main__":
    execute_ups_cmd()