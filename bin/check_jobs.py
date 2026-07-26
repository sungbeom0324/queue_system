#!/usr/bin/env python3
import nested_dict
import subprocess
#import ucsb_condor_queue
import connect_condor_queue
import queue_system
import os
import argparse
import sys
import ask
# This script depends on the queue system

def which(program):
  def is_exe(fpath):
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)
  fpath, fname = os.path.split(program)
  if fpath:
    if is_exe(program):
      return program
  else:
    for path in os.environ["PATH"].split(os.pathsep):
      exe_file = os.path.join(path, program)
      if is_exe(exe_file):
        return exe_file
  return None

def initialize_arguments(args):
  for key in args:
    if isinstance(args[key], list) and len(args[key])==1: 
      args[key] = args[key][0]
      if str(args[key]).isnumeric():
        args[key] = int(args[key])
  if not args['output_json']:
    folder = os.path.dirname(args['jobs_info_filename'])
    filename = os.path.basename(args['jobs_info_filename'])
    args['output_json'] = os.path.join(folder,'checked_'+filename)
  #if not args['jobscript_check_filename']: args['jobscript_check_filename'] = './jobscript_check.py'
  if not args['statuses']: args['statuses'] = ['submitted']
  else:
    statuses_split = args['statuses'].split(',')
    args['statuses'] = [x for x in statuses_split if x!='']

def are_arguments_valid(args):
  if not os.path.isfile(args['jobs_info_filename']):
    return False, 'jobs_info_filename: '+args['jobs_info_filename']+" doesn't exist."

  if os.path.isfile(args['output_json']):
    overwrite = ask.ask_key(args['output_json']+' already exits. Do you want to overwrite? (y/n) Default is n. ', ['y','n'], 'n')
    if overwrite == 'n':
      return False, 'output_json: '+args['output_json']+' already exits.'

  # TODO fix below
  #if args['jobscript_check_filename'] != None:
  #  if not os.path.isfile(args['jobscript_check_filename']):
  #    return False, 'jobscript_check_filename: '+args['jobscript_check_filename']+" doesn't exist."

  if args['jobscript_check_filename'] != None:
    if not which(args['jobscript_check_filename']):
      return False, 'jobscript_check_filename: '+args['jobscript_check_filename']+" isn't executable."

  valid_statuses = ['submitted', 'done', 'fail', 'success', 'to_submit']
  if len(args['statuses']) == 0:
    return False, 'len(statuses) is 0'
  for status in args['statuses']:
    if status not in valid_statuses:
      return False, status + ' is not valid'

  return True, ''

if __name__ == '__main__':

  parser = argparse.ArgumentParser(description='Checks jobs using jobs_info.json')
  parser.add_argument('jobs_info_filename', metavar='jobs_info.json')
  parser.add_argument('-o', '--output_json', metavar='checked_jobs_info.json', nargs=1)
  parser.add_argument('-c', '--jobscript_check_filename', metavar='None', nargs=1)
  parser.add_argument('-s', '--statuses', metavar='submitted,', nargs=1)
  parser.add_argument('-d', '--debug', action='store_true')
  args = vars(parser.parse_args())

  initialize_arguments(args)
  valid, log = are_arguments_valid(args)
  if not valid:
    print('[Error] '+log)
    sys.exit()

  #queue = ucsb_condor_queue.ucsb_condor_queue()
  queue = connect_condor_queue.connect_condor_queue()

  #jobs_info_filename = 'jsons/submitted_test_mc_jobs_info.json'
  #output_json = 'jsons/checked_test_mc_jobs_info.json'
  #jobscript_check_filename = './copy_aods_check_entries.py'
  #statuses = ['submitted']

  jobs_info_filename = args['jobs_info_filename']
  output_json = args['output_json']
  jobscript_check_filename = args['jobscript_check_filename']
  statuses = args['statuses']

  # Checks the jobs
  # jobs_info = [{'command_script':command_script, 'other_global_key':other_global_key, 'ignore_keys':['job_id', 'job_status', ...]},{'key_for_job':key_for_job},{'key_for_job':key_for_job},...]
  jobs_info = nested_dict.load_json_file(jobs_info_filename)

  # Each job type should make job_script, and job_check_script
  # The ./job_check_script job_log_string should return 'success' or 'fail' for a job_log_string
  # statuses: [status], where status = 'submitted', 'done', 'fail', 'success', 'to_submit'
  queue.check_jobs(jobs_info, statuses, jobscript_check_filename, args['debug'])
  #queue.check_jobs(jobs_info, ['submitted', 'done', 'fail', 'success', 'to_submit'], jobscript_check_filename)
  queue.print_jobs_status(jobs_info)

  nested_dict.save_json_file(jobs_info, output_json)
