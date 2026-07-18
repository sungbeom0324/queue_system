#!/usr/bin/env python3
# Runs multiple commands, where each argument is a compressed command
import sys
import zlib
import argparse
import subprocess
import os

# Compress string to pass things through posix
def compress_string(string):
  return zlib.compress(string.encode('utf-8')).hex()

# Decompress string for passed things through posix
def decompress_string(compressed_string):
  return zlib.decompress(bytes.fromhex(compressed_string)).decode('utf-8')

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Helps queue_system to run multiple commands. Runs arguments')
  parser.add_argument('command', nargs='+')
  parser.add_argument('-u', '--uncompressed_commands', action='store_true', help='Runs arguments without uncompression')
  args = vars(parser.parse_args())

  for command_index, compressed_command in enumerate(args['command']):
    if args['uncompressed_commands']: command = compressed_command
    else: command = decompress_string(compressed_command)
    print('[Info] command_divider : Start divided_command['+str(command_index)+']')
    print('[Info] command_divider : Current directory: '+os.getcwd())
    print('[Info] command_divider : command: '+command)
    #os.system(command)
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    if output != '': 
      print(output.rstrip())
    if error != '': 
      print(error.rstrip())
    print('[Info] command_divider : End divided_command['+str(command_index)+']')

  print('[Info] command_divider : Finished')
