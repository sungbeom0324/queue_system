#!/bin/env python3
import queue_system
import argparse
import subprocess

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Submit jobs using jobs_info.json')
  parser.add_argument('job_check_script')
  args = vars(parser.parse_args())

  job_check_script = args['job_check_script']
  queue = queue_system.queue_system()
  
  job_log_string = 'STRING_OF_JOB_LOG'
  key_string = '''--SOME_GLOBAL_KEY="SOME_GLOBAL_VALUE" --job_status="SOME_STATUS" --job_trials="['JOBID_INDEXOFJOB']" --job_identifier="JOBID_INDEXOFJOB" --command="COMMAND ARGUMENT.." --job_trials_reason="{'JOBID_INDEXOFJOB': 'SOME_REASON'}'''
  
  check_command = job_check_script+' '+queue_system.compress_string(job_log_string)+' '+queue_system.compress_string(key_string)
  
  print('[Info] Non-compressed command. compress_string() shows what will be compressed.')
  print('  '+job_check_script+' compress_string('+job_log_string+') compress_string('+key_string+')')
  print('[Info] Actual command.')
  print('  '+check_command)
  print('[Info] Running command.')
  status_reason_string = subprocess.check_output(check_command, shell=True)
  print('[Info] Command result')
  print('  '+status_reason_string)
  print('[Info] Parsed command result')
  job_status, trial_reason = queue.get_status_reason(status_reason_string)
  print('  job_status: '+job_status)
  print('  trial_reason: '+trial_reason)
