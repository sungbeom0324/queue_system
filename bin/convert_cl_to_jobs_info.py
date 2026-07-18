#!/usr/bin/env python3
import subprocess
import queue_system
import argparse
import sys
import os
import json
import nested_dict
import ask

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
  #print(args)
  for key in args:
    if isinstance(args[key], list) and len(args[key])==1: 
      args[key] = args[key][0]
      if str(args[key]).isnumeric():
        args[key] = int(args[key])

def are_arguments_valid(args):
  if os.path.isfile(args['jobs_info_filename']):
    if args['force_run']:
      fileIndex = 1
      while (1):
        filename = args['jobs_info_filename']+"."+str(fileIndex)
        if not os.path.isfile(filename):
          os.system('mv '+args['jobs_info_filename']+' '+args['jobs_info_filename']+"."+str(fileIndex))
          print("[Info] Moved old "+args['jobs_info_filename']+" to "+args['jobs_info_filename']+"."+str(fileIndex))
          break
        fileIndex += 1
    else:
      overwrite = ask.ask_key(args['jobs_info_filename']+' already exits. Do you want to overwrite? (y/n) Default is n. ', ['y','n'], 'n')
      if overwrite == 'n':
        return False, args['jobs_info_filename']+' already exist.'


  if not os.path.isfile(args['command_list_filename']):
    return False, args['command_list_filename']+" does not exist."

  if not which(args['command_list_filename']):
    return False, "Can't execute "+args['command_list_filename']+"."

  return True, ''

if __name__ == '__main__':

  parser = argparse.ArgumentParser(description='Converts a command_list.py(cl) to a jobs_info.json')
  parser.add_argument('command_list_filename', metavar='cl_task.py')
  parser.add_argument('jobs_info_filename', metavar='jobs_info.json')
  parser.add_argument('-f', '--force_run', action="store_true", help='Does not ask questions')
  args = vars(parser.parse_args())

  initialize_arguments(args)
  valid, log = are_arguments_valid(args)
  if not valid:
    print('[Error] '+log)
    sys.exit()

  jobs_info = [{}]
  command_list_output = subprocess.check_output(args['command_list_filename'], shell=True, text = True)
  for line in command_list_output.split('\n'):
    if line == '': continue
    # Parse global_key
    if '# [global_key]' == line[:len('# [global_key]')]:
      key_value_split = line.replace('# [global_key]','').split(':')
      if len(key_value_split)<2:
        print('[Warning]: Cannot add below line to global_key.')
        print('  '+line)
        continue
      key = key_value_split[0].lstrip().rstrip()
      value = ':'.join(key_value_split[1:]).lstrip().rstrip()
      json_value = None
      try: 
        json_value = json.loads(value)
        nested_dict.convert_to_ascii(json_value)
        value = json_value
      except ValueError:
        pass
      jobs_info[0][key] = value
      if json_value:
        print('Setting job_info[0]['+key+'] to '+repr(value)+' as a json')
      else:
        print('Setting job_info[0]['+key+'] to '+str(value)+' as a string')
    # Parse commands
    elif '#' != line[0]:
      jobs_info.append({'command':line.rstrip()})

  nested_dict.save_json_file(jobs_info, args['jobs_info_filename'])
