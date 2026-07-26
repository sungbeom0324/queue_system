#!/usr/bin/env python3
import argparse
import nested_dict
import subprocess
#import ucsb_condor_queue
import connect_condor_queue
import queue_system
import sys
import os
import ask
# This script depends on the queue system

def initialize_arguments(args):
  #print(args)
  for key in args:
    if isinstance(args[key], list) and len(args[key])==1: 
      args[key] = args[key][0]
      if str(args[key]).isnumeric():
        args[key] = int(args[key])
  if not args['output_json']:
    folder = os.path.dirname(args['jobs_info_filename'])
    filename = os.path.basename(args['jobs_info_filename'])
    args['output_json'] = os.path.join(folder,'submitted_'+filename)

def are_arguments_valid(args):
  if not os.path.isfile(args['jobs_info_filename']):
    return False, 'jobs_info_filename: '+args['jobs_info_filename']+" doesn't exist."

  if os.path.isfile(args['output_json']):
    overwrite = ask.ask_key(args['output_json']+' already exists. Do you want to overwrite? (y/n) Default is n. ', ['y','n'], 'n')
    if overwrite == 'n':
      return False, 'output_json: '+args['output_json']+' already exists.'

  return True, ''

if __name__ == '__main__':

  parser = argparse.ArgumentParser(description='Submit jobs using jobs_info.json')
  parser.add_argument('jobs_info_filename', metavar='jobs_info.json')
  parser.add_argument('-o', '--output_json', metavar='submitted_jobs_info.json', nargs=1)
  parser.add_argument('-n', '--node', metavar='"node_name"', nargs=1)
  parser.add_argument('-r', '--max_run', nargs=1)
  args = vars(parser.parse_args())

  initialize_arguments(args)
  valid, log = are_arguments_valid(args)
  if not valid:
    print('[Error] '+log)
    sys.exit()

  #jobs_info_filename = 'jsons/test_mc_jobs_info.json'
  #output_json = 'jsons/submitted_test_mc_jobs_info.json'
  #node = 'cms1'

  jobs_info_filename = args['jobs_info_filename']
  output_json = args['output_json']
  node = args['node']
  max_run = args['max_run']

  # jobs_info = [{'command_script':command_script, 'other_global_key':other_global_key},{'key_for_job':key_for_job},{'key_for_job':key_for_job},...]
  jobs_info = nested_dict.load_json_file(jobs_info_filename)
  #queue = ucsb_condor_queue.ucsb_condor_queue()
  queue = connect_condor_queue.connect_condor_queue()
  # statuses: [status], where status = 'submitted', 'done', 'fail', 'success', 'to_submit'
  node, number_combined_commands, print_or_run = queue.submit_jobs_info(jobs_info, jobs_info_filename, node=node, max_run=max_run)

  if print_or_run == 'r': nested_dict.save_json_file(jobs_info, output_json)
