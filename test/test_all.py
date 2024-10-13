
import os
import time

py_files = os.listdir(".")
py_files.remove('test_all.py')
py_files.sort()

for py in py_files:
    cmd = f'python3 {py}'
    if py == 'transfer_data2.py':
        bin_file = 'bin_10k.bin'
        os.system(f'dd if=/dev/urandom of={bin_file} bs=10K count=1')
        cmd = f'python3 {py} {bin_file}'
    print("============================")
    print(cmd)
    print("============================")
    os.system(cmd)
    time.sleep(1)

