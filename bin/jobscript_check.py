#!/usr/bin/env python3
# The ./jobscript_check.py should return 'success' or 'fail' or 'to_submit' or 'submitted' for a job_log_string
# The input is given as sys.argv[1] = queue_system.compress_string(job_log_string) sys.argv[2] = queue_system.compress_string(job_argument_string)
import sys
import queue_system

job_log_string = queue_system.decompress_string(sys.argv[1])
job_argument_string = queue_system.decompress_string(sys.argv[2])

#print('')
#print(sys.argv[0]+' '+sys.argv[1]+' '+sys.argv[2])
#print(job_log_string)
#print(job_argument_string)
#print('')

if ('error' not in job_log_string.lower()) and ('segmentation fault' not in job_log_string.lower()):
  print('[For queue_system] success')
else:
  print('[For queue_system] fail: Error in job_log')
