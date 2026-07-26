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
    args['output_json'] = os.path.join(folder,'resubmit_'+filename)
  if not args['statuses']: args['statuses'] = ['fail']
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

  #if args['jobscript_check_filename']:
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


#def ask_yn(question, default=None):
#  answer_yn = input(question)
#  if answer_yn != 'y' and answer_yn != 'n' and answer_yn != '':
#    print('[Error] Did not enter y or n')
#    return ask_yn(question, default)
#  if answer_yn == '': 
#    if default == None:
#      print('[Error] Did not enter y or n')
#      return ask_yn(question, default)
#    else:
#      return default
#  return answer_yn

def ask_key_value():
  key = input('Type key to change: ')
  value = input('Type changed value: ')
  sure = ask.ask_yn('Are you sure to change keys: '+key+' to value: '+value+'? (y/n) ')
  if sure == 'n': return ask_key_value()
  return key, value

# Return change_key_globally, key, value
def ask_change_key_globally():
  #change_key_globally = ask_yn('Do you want to change key globally? (y/n) Default is n. ', 'n')
  change_key_globally = ask.ask_key('Do you want to change key globally? (y/n) Default is n. ', ['y','n'], 'n')
  if change_key_globally == 'n': return 'n', None, None
  key, value = ask_key_value()
  return change_key_globally, key, value

# jobs_info = ({'command_script':command_script, 'other_global_key':other_global_key, 'ignore_keys':('job_id', 'job_status', ...)},{'key_for_job':key_for_job},{'key_for_job':key_for_job},...)
def change_key_globally(key, value, jobs_info):
  for job_info in jobs_info:
    if key in job_info:
      job_info[key] = value

if __name__ == '__main__':

  parser = argparse.ArgumentParser(description='Submit jobs using jobs_info.json')
  parser.add_argument('jobs_info_filename', metavar='jobs_info.json')
  parser.add_argument('-o', '--output_json', metavar='resubmit_jobs_info.json', nargs=1)
  parser.add_argument('-c', '--jobscript_check_filename', metavar='None', nargs=1)
  parser.add_argument('-s', '--statuses', metavar='fail,', nargs=1)
  args = vars(parser.parse_args())

  initialize_arguments(args)
  valid, log = are_arguments_valid(args)
  if not valid:
    print('[Error] '+log)
    sys.exit()


  #queue = ucsb_condor_queue.ucsb_condor_queue()
  queue = connect_condor_queue.connet_condor_queue()

  #jobs_info_filename = 'jsons/auto_fix_checked_mc_2016_jobs_info.json'
  #output_json = 'jsons/auto_fix_checked_mc_2016_jobs_info.json'
  #jobscript_check_filename = './copy_aods_check_entries.py'
  #statuses = ['fail']

  jobs_info_filename = args['jobs_info_filename']
  output_json = args['output_json']
  jobscript_check_filename = args['jobscript_check_filename']
  statuses = args['statuses']

  # jobs_info = ({'command_script':command_script, 'other_global_key':other_global_key, 'ignore_keys':('job_id', 'job_status', ...)},{'key_for_job':key_for_job},{'key_for_job':key_for_job},...)
  jobs_info = nested_dict.load_json_file(jobs_info_filename)

  # key_value = (key, value)
  print('[Global keys]\n  '+'\n  '.join([x+': '+jobs_info[0][x] for x in jobs_info[0]]))
  is_change_key_globally, key, value = ask_change_key_globally()
  if is_change_key_globally == 'y': change_key_globally(key, value, jobs_info)

  number_failed_jobs = queue.get_number_jobs(jobs_info, statuses)
  print('Number of jobs that can be rerun: '+str(number_failed_jobs))
  is_all_rerun = ask.ask_key('Check logs to re-run? (y/n) Default is y. ', ['y', 'n'], 'y')
  if is_all_rerun == 'n':
    queue.all_jobs_to_submit(jobs_info, statuses)

  # Ask if job should be rerun
  if is_all_rerun == 'y':
    queue.jobs_to_submit(jobs_info, statuses, jobscript_check_filename)

  #queue.print_jobs_status(jobs_info)

  #filtered_jobs_info = queue.filtered_jobs_info(jobs_info, ['to_submit'])
  filtered_jobs_info = jobs_info
  queue.print_jobs_status(filtered_jobs_info)

  nested_dict.save_json_file(filtered_jobs_info, output_json)
