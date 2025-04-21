import subprocess
import os
import signal
import time

def run_tshark(interface, output_file):
    """
    Start tshark to capture packets on the given interface.
    """
    command = f'tshark -i {interface} -w {output_file}'
    process = subprocess.Popen(command, stdout=subprocess.PIPE,
                           shell=True, preexec_fn=os.setsid)

    return process

def kill_tshark(process):
    """
    Kill the tshark process.
    :param process: The process to kill
    """
    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    time.sleep(3)
    subprocess.run('pkill -15 -f tshark', shell=True, executable='/bin/bash')