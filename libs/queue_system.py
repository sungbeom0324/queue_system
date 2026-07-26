#!/usr/bin/env python3
import subprocess
import zlib
import re
import ask

# Compress string to pass things through posix
def compress_string(string):
  #return zlib.compress(string.encode('utf-8')).encode('hex')
  #temp = zlib.compress(string.encode())
  ##temp = zlib.compress(str.encode(string))
  #print('zipped')
  #print(temp)
  #print('zip hex')
  #temphex = temp.hex()
  #print(temphex)
  #print('unzipped')
  #print(zlib.decompress(bytes.fromhex(temphex)).decode())
  return zlib.compress(string.encode()).hex()

# Decompress string for passed things through posix
def decompress_string(compressed_string):
  #return zlib.decompress(compressed_string.decode('hex'))
  return zlib.decompress(bytes.fromhex(compressed_string)).decode()

class queue_system():
  # job_index starts from 1
  # submission_commands_info = [[submission_command, [command, job_index]]]
  # Should modify jobs_info[job_index]['job_identifier']. Should modify jobs_info[job_index]['job_status'] to 'submitted'
  def submit_job(self, submission_command_info, jobs_info):
    pass

  # Return command to run job for queue system
  # Should handle multiple commands in one job 
  # commands_info = [[command, job_index]]
  # Ex) commands_info[x] = [[command_1, job_index_1], [command_2, job_index_2], ...]
  # submission_command_info = [submission_command, [command, job_index]]
  def get_submission_command_info(self, command_string, node, input_files=None):
    pass

  # Should get job_index log using multiple_index and job_identifier
  # Return 'not_found' if the file does not exists
  def get_job_log_string(self, job_identifier, multiple_index):
    pass

  # Returns True if job is in queue system. False if job can't be found
  def does_job_exist(self, job_identifier):
    pass

  # Should return either 'submitted', 'done', 'fail', 'success', 'to_submit'
  # Returns '' if there is no reason
  def get_status_reason(self, status_reason_string):
    valid_statuses = ['submitted', 'done', 'fail', 'success', 'to_submit']
    # Do rstrip and remove ansi_escape code
    raw_status_reason_parse = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]').sub('', status_reason_string.rstrip())
    # Get lines that has '[For queue_system]'
    status_reason_parse = ''
    for line in raw_status_reason_parse.split('\n'):
      if '[For queue_system]' in line:
        status_reason_parse += line.replace('[For queue_system]','').lstrip()+'\n'
    # Return status if possible
    if status_reason_parse.rstrip() in valid_statuses:
      return status_reason_parse.rstrip(), ''
    # Find status and reason. Divide by :
    status_reason_split = status_reason_parse.split(':')
    if len(status_reason_split) < 2:
      print('[Error] status_reason_split: len('+str(status_reason_split)+') is smaller than 2')
      return 'unknown', ''
    return status_reason_split[0].rstrip(), ':'.join(status_reason_split[1:]).lstrip().rstrip()

  # Should return either 'submitted', 'done', 'fail', 'success', 'to_submit'
  # job_log_string is 'not_found' if the file does not exists
  # The ./job_check_script queue_system.compress_string(job_log_string) should return 'success' or 'fail' or 'to_submit' for a job_log_string
  def get_job_status_trial_reason(self, check_command, job_log_string, default_info):
    job_status = 'submitted'
    trial_reason = ''
    if job_log_string != 'not_found':
      # If job is finished
      if ('[Info] command_divider : End divided_command[' in job_log_string):
        if check_command:
          try:
            status_reason_string = subprocess.check_output(check_command, shell=True, encoding='UTF-8')
          except:
            status_reason_string = '[For queue_system] fail: check script crashed: '+check_command
          job_status, trial_reason = self.get_status_reason(status_reason_string)
          if job_status != 'fail' and job_status != 'success' and job_status != 'to_submit':
            print('[Error] Below command gave unkown status: '+repr(job_status)+'. Setting job_status to done.')
            print('  '+check_command)
            job_status = 'done'
        else:
          job_status = 'done'
      elif '[Error] Job was terminated' in job_log_string:
        job_status = 'fail'
        trial_reason = 'Job was terminated'
    return job_status, trial_reason

  # job_index starts from 1
  # combined_commands_info = [[[command, job_index]]]
  # Ex) combined_commands_info[x] = [[command_1, job_index_1], [command_2, job_index_2], ...]
  # submission_commands_info = [[submission_command, [command, job_index]]]
  def get_submission_commands_info(self, combined_commands_info, node, input_files=None):
    submission_commands_info = []
    for commands_info in combined_commands_info:
      submission_commands_info.append(self.get_submission_command_info(commands_info, node, input_files))
    return submission_commands_info

  # Handles string, numbers, and lists
  def get_key_string(self, default_info, job_info):
    command_string = ''
    # Loop over default_info keys
    for key in default_info:
      command_string += ' --'+key+'="'+str(default_info[key])+'"'
    # Loop over job_info keys
    for key in job_info:
      command_string += ' --'+key+'="'+str(job_info[key])+'"'
    return command_string[1:]

  # jobs_info = ({'global_key':global_value},{'command': command for job 1, 'key_for_job':value_for_job1},{'command': command for job 2', key_for_job':value2_for_job2},...)
  # commands_info = [[command, job_index]]
  # Ex) commands_info[x] = [[command_1, job_index_1], [command_2, job_index_2], ...]
  def get_commands_info(self, jobs_info):
    commands_info = []
    default_info = jobs_info[0]
    # Iterate over each job_info
    for job_index_raw, job_info in enumerate(jobs_info[1:]):
      if job_info['job_status'] != 'to_submit': continue

      job_index = job_index_raw + 1
      command_string = job_info['command']
      commands_info.append([command_string, job_index])
    return commands_info

  def chunker(self, seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size)) # python3
    #return (seq[pos:pos + size] for pos in xrange(0, len(seq), size))

  # commands_info = [[command, job_index]]
  # combined_commands_info = [[[command, job_index]]]
  # Ex) combined_commands_info[x] = [[command_1, job_index_1], [command_2, job_index_2], ...]
  def get_combined_commands_info(self, number_combined_commands, commands_info):
    return list(self.chunker(commands_info, number_combined_commands))
 
  def get_number_combined_commands(self):
    number_combined_commands = input('Number commands to combine (Default: 1) : ')
    if number_combined_commands == '': number_combined_commands = 1
    else:
      if not str(number_combined_commands).isnumeric():
        print('[Error] '+number_combined_commands+' is not a number.')
        return self.get_number_combined_commands()
    return int(number_combined_commands)

  def get_print_or_run(self):
    print_or_run = input('(p)rint commands or (r)un commands (Default: p) : ')
    if print_or_run == '': print_or_run = 'p'
    else:
      if print_or_run != 'p' and print_or_run != 'r':
        print('[Error] '+print_or_run+' is not p or r')
        return self.get_print_or_run()
    return print_or_run
 
  # jobs_info = ({'global_key':global_value},{'command': command for job 1, 'key_for_job':value_for_job1},{'command': command for job 2', key_for_job':value2_for_job2},...)
  # statuses: [status], where status = 'submitted', 'done', 'fail', 'success', 'to_submit'
  # job_trials: [job_identifier]
  def initialize_jobs_info(self, jobs_info):
    commands_info = []
    default_info = jobs_info[0]
    # Iterate over each job_info
    for job_index_raw, job_info in enumerate(jobs_info[1:]):
      job_index = job_index_raw + 1
      if 'job_status' not in job_info:
        jobs_info[job_index]['job_status'] = 'to_submit'
      if 'job_trials' not in job_info:
        jobs_info[job_index]['job_trials'] = []
      if 'job_trials_reason' not in job_info:
        jobs_info[job_index]['job_trials_reason'] = {}

  # Returns 'r' or 'p' if run or printed
  # jobs_info = ({'global_key':global_value},{'command': command for job 1, 'key_for_job':value_for_job1},{'command': command for job 2', key_for_job':value2_for_job2},...)
  # statuses: [status], where status = 'submitted', 'done', 'fail', 'success', 'to_submit'
  def submit_jobs_info(self, jobs_info, jobs_info_filename, node=None, max_run=None, input_files=None, output_files=None, ncpus_in_job=None):
    self.initialize_jobs_info(jobs_info)

    print('[Info] Number of commands to submit: '+str(self.get_number_jobs(jobs_info, ['to_submit'])))

    number_combined_commands = self.get_number_combined_commands()
    print_or_run = self.get_print_or_run()
    return self.raw_submit_jobs_info(jobs_info, node, number_combined_commands, print_or_run, jobs_info_filename, max_run, input_files, output_files, ncpus_in_job)

  # jobs_info = ({'global_key':global_value},{'command': command for job 1, 'key_for_job':value_for_job1},{'command': command for job 2', key_for_job':value2_for_job2},...)
  # statuses: [status], where status = 'submitted', 'done', 'fail', 'success', 'to_submit'
  def raw_submit_jobs_info(self, jobs_info, node, number_combined_commands, print_or_run, jobs_info_filename, max_run=None, input_files=None, output_files=None, ncpus_in_job=None):
    self.initialize_jobs_info(jobs_info)

    # commands_info = [[command, job_index]]
    commands_info = self.get_commands_info(jobs_info)
    # combined_commands_info = [[[command, job_index]]]
    # Ex) combined_commands_info[x] = [[command_1, job_index_1], [command_2, job_index_2], ...]
    combined_commands_info = self.get_combined_commands_info(number_combined_commands, commands_info)
    # submission_commands_info = [[submission_command, [command, job_index]]]
    submission_commands_info = self.get_submission_commands_info(combined_commands_info, node, input_files)
    
    if print_or_run == 'r':
      self.submit_jobs(submission_commands_info, jobs_info, jobs_info_filename, node, max_run, input_files, output_files, ncpus_in_job)
    elif print_or_run == 'p':
      for submission_command_info in submission_commands_info:
        # submission_command_info = [submission_command, commands_info]
        # commands_info = [(command, job_index)]
        submission_command = submission_command_info[0]
        job_indices = self.get_job_indices_from_commands_info(submission_command_info[1])
        print('job_index(s): ' +str(job_indices)+' command: '+submission_command)

    return node, number_combined_commands, print_or_run

  # submission_command_info = [submission_command, commands_info]
  # commands_info = [[command, job_index]]
  def get_job_indices_from_submission_command_info(self, submission_command_info):
    job_indices = []
    print(submission_command_info)
    commands_info = submission_command_info[1]
    for command_info in commands_info:
      job_index = command_info[1]
      job_indices.append(job_index)
    return job_indices

  # commands_info = [[command, job_index]]
  def get_job_indices_from_commands_info(self, commands_info):
    #print(commands_info)
    job_indices = []
    for command, job_index in commands_info:
      job_indices.append(job_index)
    return job_indices

  # job_id_to_indices[job_identifier] = [job_index]
  def get_job_identifier_to_indices(self, jobs_info):
    job_identifier_to_indices = {}
    for job_index_raw, job_info in enumerate(jobs_info[1:]):
      job_index = job_index_raw + 1
      job_identifier = job_info['job_identifier']
      if job_identifier not in job_identifier_to_indices:
        job_identifier_to_indices[job_identifier] = []
      job_identifier_to_indices[job_identifier].append(job_index)
    return job_identifier_to_indices

  #def get_job_id_index_string(self, job_id, multiple_index):
  def get_job_identifier(self, job_id, multiple_index):
    return str(job_id) + '_' + str(multiple_index)

  #def get_job_id_index(self, job_identifier):
  def get_job_id_multiple_index(self, job_identifier):
    job_identifier_split = job_identifier.split('_')
    return job_identifier_split[0], job_identifier_split[1]

  def check_job(self, jobs_info, statuses, job_check_script, job_index, debug=False, force_check=False):
    default_info = jobs_info[0]
    job_info = jobs_info[job_index]
    job_id, multiple_index = self.get_job_id_multiple_index(job_info['job_identifier'])
    job_status = job_info['job_status']
    if job_status not in statuses: return
    # Return 'not_found' if the file does not exists
    job_log_string = self.get_job_log_string(job_id, multiple_index)
    check_command = self.get_check_command(jobs_info, job_check_script, job_index)
    if debug: print (check_command)
    # If job is not in queue system resubmit
    if self.does_job_exist(job_id) == False and force_check == False: 
      job_status = 'to_submit'
      trial_reason = "Job not in queue system"
    else: 
      job_status, trial_reason = self.get_job_status_trial_reason(check_command, job_log_string, default_info)
    job_info['job_status'] = job_status
    if trial_reason != '':
      job_info['job_trials_reason'][job_info['job_identifier']] = trial_reason
      print('[Info]: Checked job_index: '+str(job_index)+' job_id: '+job_id+' multiple_index: '+multiple_index+' job_status: '+job_info['job_status']+' job_trial_reason: '+trial_reason)
    else:
      print('[Info]: Checked job_index: '+str(job_index)+' job_id: '+job_id+' multiple_index: '+multiple_index+' job_status: '+job_info['job_status'])

  # Check jobs in certain statuses 
  # jobs_info = ({'global_key':global_value},{'command': command for job 1, 'key_for_job':value_for_job1},{'command': command for job 2', key_for_job':value2_for_job2},...)
  # statuses: [status], where status = 'submitted', 'done', 'fail', 'success', 'to_submit'
  def check_jobs(self, jobs_info, statuses, job_check_script=None, debug=False, force_check=False):
    self.initialize_jobs_info(jobs_info)
    for job_index_raw, job_info in enumerate(jobs_info[1:]):
      job_index = job_index_raw + 1
      self.check_job(jobs_info, statuses, job_check_script, job_index, debug, force_check)

  # Sets trial for jobs in certain statuses 
  # jobs_info = ({'global_key':global_value},{'command': command for job 1, 'key_for_job':value_for_job1},{'command': command for job 2', key_for_job':value2_for_job2},...)
  # statuses: [status], where status = 'submitted', 'done', 'fail', 'success', 'to_submit'
  # job_trial = (job_id, multiple_index)
  def set_trials_jobs(self, jobs_info, statuses, trial):
    default_info = jobs_info[0]
    for job_index_raw, job_info in enumerate(jobs_info[1:]):
      job_index = job_index_raw + 1
      job_id, multiple_index = self.get_job_id_multiple_index(job_info['job_identifier'])
      job_status = job_info['job_status']
      if job_status not in statuses: continue
      job_info['job_trials'] = trial

  # Adds job_id, multiple index to job_trials in certain statuses 
  # jobs_info = ({'global_key':global_value},{'command': command for job 1, 'key_for_job':value_for_job1},{'command': command for job 2', key_for_job':value2_for_job2},...)
  # submission_command_info = [submission_command, commands_info]
  # job_index starts from 1
  # commands_info = [(command, job_index)]
  # job_trials: [(job_id, multiple_index)]
  def add_trial_job(self, submission_command_info, jobs_info):
    submission_command = submission_command_info[0]
    commands_info = submission_command_info[1]
    job_indices = self.get_job_indices_from_commands_info(commands_info)
    for multiple_index, job_index in enumerate(job_indices):
      job_info = jobs_info[job_index]
      if job_info['job_identifier'] in job_info['job_trials']: continue
      job_info['job_trials'].append(job_info['job_identifier'])

  # Adds submission command to jobs_info
  # jobs_info = ({'global_key':global_value},{'command': command for job 1, 'key_for_job':value_for_job1},{'command': command for job 2', key_for_job':value2_for_job2},...)
  # submission_command_info = [submission_command, commands_info]
  # job_index starts from 1
  # commands_info = [(command, job_index)]
  # job_trials: [(job_id, multiple_index)]
  def add_submission_command(self, submission_command_info, jobs_info):
    submission_command = submission_command_info[0]
    commands_info = submission_command_info[1]
    job_indices = self.get_job_indices_from_commands_info(commands_info)
    for multiple_index, job_index in enumerate(job_indices):
      job_info = jobs_info[job_index]
      job_info['submission_command'] = submission_command

  # Adds job_id, multiple index to job_trials in certain statuses 
  # jobs_info = ({'global_key':global_value},{'command': command for job 1, 'key_for_job':value_for_job1},{'command': command for job 2', key_for_job':value2_for_job2},...)
  # statuses: [status], where status = 'submitted', 'done', 'fail', 'success', 'to_submit'
  # job_trials: [(job_id, multiple_index)]
  def add_trials_jobs(self, jobs_info, statuses):
    default_info = jobs_info[0]
    for job_index_raw, job_info in enumerate(jobs_info[1:]):
      job_index = job_index_raw + 1
      job_id, multiple_index = self.get_job_id_multiple_index(job_info['job_identifier'])
      job_status = job_info['job_status']
      if job_status not in statuses: continue
      if [job_id, multiple_index] in job_info['job_trials']: continue
      job_info['job_trials'].append([job_id, multiple_index])

  # Set job to fail if trial >= max_trial for jobs in certain status
  # jobs_info = ({'global_key':global_value},{'command': command for job 1, 'key_for_job':value_for_job1},{'command': command for job 2', key_for_job':value2_for_job2},...)
  # statuses: [status], where status = 'submitted', 'done', 'fail', 'success', 'to_submit'
  # job_trials: [(job_id, multiple_index)]
  def fail_max_trials_jobs(self, jobs_info, statuses, max_trial):
    default_info = jobs_info[0]
    for job_index_raw, job_info in enumerate(jobs_info[1:]):
      job_index = job_index_raw + 1
      job_id, multiple_index = self.get_job_id_multiple_index(job_info['job_identifier'])
      job_status = job_info['job_status']
      if job_status not in statuses: continue
      if len(job_info['job_trials']) >= max_trial:
        job_info['job_status'] = 'fail'
        #job_id_index = self.get_job_id_index_string(job_id, multiple_index)
        job_info['job_trials_reason'][job_info['job_identifier']] = job_info['job_trials_reason'][job_info['job_identifier']].rstrip() + ' and Max trial: '+str(max_trial)+' reached'
        print('[Info]: fail_max_trials job_index: '+str(job_index)+' job_id: '+job_id+' multiple_index: '+multiple_index+' job_status: '+job_info['job_status']+' job_trial_reason: '+job_info['job_trials_reason'][job_info['job_identifier']])

  # jobs_info = ({'global_key':global_value},{'command': command for job 1, 'key_for_job':value_for_job1},{'command': command for job 2', key_for_job':value2_for_job2},...)
  # statuses: [status], where status = 'submitted', 'done', 'fail', 'success', 'to_submit'
  def get_number_jobs(self, jobs_info, statuses):
    self.initialize_jobs_info(jobs_info)
    number_jobs = 0
    default_info = jobs_info[0]
    for job_index_raw, job_info in enumerate(jobs_info[1:]):
      job_index = job_index_raw + 1
      job_status = job_info['job_status']
      if job_status not in statuses: continue
      number_jobs += 1
    return number_jobs

  # Get jobs that have status in statuses
  # statuses: [status], where status = 'submitted', 'done', 'fail', 'success', 'to_submit'
  # jobs_info = ({'global_key':global_value},{'command': command for job 1, 'key_for_job':value_for_job1},{'command': command for job 2', key_for_job':value2_for_job2},...)
  def filtered_jobs_info(self, jobs_info, statuses):
    filtered_jobs_info = []
    filtered_jobs_info.append(jobs_info[0])
    for job_index_raw, job_info in enumerate(jobs_info[1:]):
      job_index = job_index_raw + 1
      job_status = job_info['job_status']
      if job_status not in statuses: continue
      filtered_jobs_info.append(job_info)
    return filtered_jobs_info

  # jobs_info = ({'global_key':global_value},{'command': command for job 1, 'key_for_job':value_for_job1},{'command': command for job 2', key_for_job':value2_for_job2},...)
  # statuses: [status], where status = 'submitted', 'done', 'fail', 'success', 'to_submit'
  def print_log_jobs(self, jobs_info, statuses):
    default_info = jobs_info[0]
    for job_index_raw, job_info in enumerate(jobs_info[1:]):
      job_index = job_index_raw + 1
      job_id, multiple_index = self.get_job_id_multiple_index(job_info['job_identifier'])
      job_status = job_info['job_status']
      if job_status not in statuses: continue
      print('[Info]: Printing job_index: '+str(job_index)+', job_id: '+job_id+', multiple_index: '+multiple_index+', job_status: '+job_status)
      # Return 'not_found' if the file does not exists
      job_log_string = self.get_job_log_string(job_id, multiple_index)
      print(job_log_string)

  # jobs_info = ({'global_key':global_value},{'command': command for job 1, 'key_for_job':value_for_job1},{'command': command for job 2', key_for_job':value2_for_job2},...)
  # statuses: [status], where status = 'submitted', 'done', 'fail', 'success', 'to_submit'
  def all_jobs_to_submit(self, jobs_info, statuses):
    default_info = jobs_info[0]
    for job_index_raw, job_info in enumerate(jobs_info[1:]):
      job_index = job_index_raw + 1
      job_id, multiple_index = self.get_job_id_multiple_index(job_info['job_identifier'])
      job_status = job_info['job_status']
      if job_status not in statuses: continue
      job_info['job_status'] = 'to_submit'

  # jobs_info = ({'global_key':global_value},{'command': command for job 1, 'key_for_job':value_for_job1},{'command': command for job 2', key_for_job':value2_for_job2},...)
  def get_check_command(self, jobs_info, job_check_script, job_index):
    if job_check_script == None: return None
    default_info = jobs_info[0]
    job_info = jobs_info[job_index]
    job_id, multiple_index = self.get_job_id_multiple_index(job_info['job_identifier'])
    job_status = job_info['job_status']
    job_log_string = self.get_job_log_string(job_id, multiple_index)
    # Cut away if job_log is too long
    if len(job_log_string) > 100000:
      job_log_string = job_log_string[:100000]
    key_string = self.get_key_string(default_info, job_info)
    return job_check_script+' '+compress_string(job_log_string)+' '+compress_string(key_string)

  # jobs_info = ({'global_key':global_value},{'command': command for job 1, 'key_for_job':value_for_job1},{'command': command for job 2', key_for_job':value2_for_job2},...)
  # statuses: [status], where status = 'submitted', 'done', 'fail', 'success', 'to_submit'
  def jobs_to_submit(self, jobs_info, statuses, job_check_script=None):
    default_info = jobs_info[0]
    for job_index_raw, job_info in enumerate(jobs_info[1:]):
      job_index = job_index_raw + 1
      job_id, multiple_index = self.get_job_id_multiple_index(job_info['job_identifier'])
      job_status = job_info['job_status']
      if job_status not in statuses: continue
      job_log_string = self.get_job_log_string(job_id, multiple_index)
      print('--------')
      print('job_id: '+str(job_id)+', multiple_index: '+str(multiple_index))
      print('job_script: '+job_info['submission_command'])
      print('--------Job Log--------')
      print(job_log_string.rstrip())
      print('--------Job Log--------')
      if (job_info['job_identifier'] in job_info['job_trials_reason']): print('fail reason: '+job_info['job_trials_reason'][job_info['job_identifier']])
      else: print('fail reason: unknown')
      print('--------')
      if job_check_script:
        print(self.get_check_command(jobs_info, job_check_script, job_index))
        print('--------')
      is_rerun = ask.ask_key('Do you want to re-run? (y/n) Default is y. ', ['y','n'], 'y')
      if is_rerun == 'y': job_info['job_status'] = 'to_submit'

  # statuses: [status], where status = 'submitted', 'done', 'fail', 'success', 'to_submit'
  def print_jobs_status(self, jobs_info):
    print('Submitted commands: '+str(self.get_number_jobs(jobs_info, ['submitted'])))
    print('Done commands:      '+str(self.get_number_jobs(jobs_info, ['done'])))
    print('Success commands:   '+str(self.get_number_jobs(jobs_info, ['success'])))
    print('Fail commands:    '+str(self.get_number_jobs(jobs_info, ['fail'])))
    print('To_submit commands: '+str(self.get_number_jobs(jobs_info, ['to_submit'])))
    
if __name__ == '__main__':
  # Reserved keys: job_id, job_status
  # multiple jobs can have same job_id if they were submitted with one job command
  pass

  #jobs_info_filename = 'jsons/mc_2016_jobs_info.json'
  #out_jobs_info_filename = 'jsons/submitted_mc_2016_jobs_info.json'

  #jobs_info = datasets.load_json_file(jobs_info_filename)
  #queue = ucsb_job()
  ##queue.submit_jobs_info(jobs_info, node='cms1')
  ##assign_job_id(queue, jobs_info, 6068)

  #datasets.save_json_file(jobs_info, out_jobs_info_filename)

