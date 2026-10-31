import subprocess
import time

py = r"C:\Python314\pythonw.exe"
main = r"D:\work\Dev\TIDOS\tidos_orb\__main__.py"
action = f'"{py}" -I "{main}" run --show'
create_cmd = f'schtasks /create /tn TIDOS_ORB_LAUNCH /tr "{action}" /sc once /st 23:59 /f /it'
res1 = subprocess.run(create_cmd, shell=True, capture_output=True, text=True)
print('Create:', res1.stdout.strip(), res1.stderr.strip())
res2 = subprocess.run('schtasks /run /tn TIDOS_ORB_LAUNCH', shell=True, capture_output=True, text=True)
print('Run:', res2.stdout.strip(), res2.stderr.strip())
time.sleep(2)
subprocess.run('schtasks /delete /tn TIDOS_ORB_LAUNCH /f', shell=True, capture_output=True)
