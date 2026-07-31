#!/usr/bin/env python3
import subprocess
import queue_system
import os
import uuid
import re
import datetime

class connect_condor_queue(queue_system.queue_system):

  def find_new_command_file_path(self,command_directory, command_filename):
    command_file_path = os.path.join(command_directory, command_filename)
    if os.path.exists(command_file_path):
      return self.find_new_command_file_path(command_directory, str(uuid.uuid4())+'.sh')
    else:
      return command_file_path

  # Return command to run job for queue system
  # Should handle multiple commands in one job 
  # commands_info = [[command, job_index]]
  # submission_command_info = [submission_command, commands_info]
  def get_submission_command_info(self, commands_info, node, input_files):
    job_command_directory = 'job_submit_commands'
    if not os.path.exists(job_command_directory):
      os.makedirs(job_command_directory)
    job_command_file_path = self.find_new_command_file_path(job_command_directory, str(uuid.uuid4())+'.sh')

    #if os.environ['CMSSW_BASE'] == "": 
    #  print('[Error] CMSSW is not set')
    #  return []

    # Making command file
    job_command_string = '#!/bin/bash\n'
    job_command_string += 'JOB_DIR="$PWD"\n'
    job_command_string += 'source /cvmfs/cms.cern.ch/cmsset_default.sh\n'
    job_command_string += 'cd /cvmfs/cms.cern.ch/el9_amd64_gcc12/cms/cmssw/CMSSW_15_0_17/src\n'
    job_command_string += 'eval "$(scram runtime -sh)"\n'
    job_command_string += 'cd "$JOB_DIR"\n'

    # Make directories    
    job_command_string += 'mkdir -p zgamma/raw_pico\n'
    job_command_string += 'mkdir -p zgamma/wgt_sums\n'

    # Untar input files
    for input_file in input_files.split(','):
      input_basename = os.path.basename(input_file)

      if input_file.endswith('.tar.gz'): job_command_string += f'tar -zxvf {input_basename}\n'
      elif input_file.endswith('process_nano.exe'):
        job_command_string += 'mkdir -p ./run\n'
        job_command_string += f'mv {input_basename} run/process_nano.exe\n'
        job_command_string += 'chmod +x run/process_nano.exe\n'
      elif input_file.endswith('sucho_data_list.txt'):
        job_command_string += 'mkdir -p txt/datasets\n'
        job_command_string += f'mv {input_basename} txt/datasets/sucho_data_list.txt\n'
        job_command_string += 'chmod 644 txt/datasets/sucho_data_list.txt\n'
      elif input_file.endswith('Cert_Collisions2023_366442_370790_Golden.json'):
        job_command_string += 'mkdir -p txt/json\n'
        job_command_string += f'mv {input_basename} txt/json/Cert_Collisions2023_366442_370790_Golden.json\n'
        job_command_string += 'chmod 644 txt/json/Cert_Collisions2023_366442_370790_Golden.json\n'

    # Check transferred files
    job_command_string += '\n'
    job_command_string += 'echo "[Info] Files in job directory:"\n'
    job_command_string += 'find . -maxdepth 3 -type f -print\n'
    job_command_string += '\n'

    # Check shared library resolution before running process_nano.
    job_command_string += ('echo "[Info] Shared-library check for process_nano.exe:"\n')
    job_command_string += 'ldd run/process_nano.exe\n'
    job_command_string += 'if ldd run/process_nano.exe 2>&1 | grep -q "not found"; then exit 1; fi\n'
    job_command_string += '\n'

    # Write commands
    for command_index, command_info in enumerate(commands_info):
      command = command_info[0]
      #command_with_env = os.environ['JB_QUEUE_SYSTEM_DIR']+'/bin/setcmsenv.sh '+os.environ['CMSSW_BASE']+' '+command

      job_command_string += 'echo [Info] command_divider : Start divided_command['+str(command_index)+']\n'
      job_command_string += 'echo [Info] command_divider : Current directory: '+os.getcwd()+'\n'
      job_command_string += 'echo [Info] command_divider : command: '+command+'\n'
      job_command_string += command+'\n'
      job_command_string += 'echo [Info] command_divider : End divided_command['+str(command_index)+']\n'
      job_command_string += 'echo [Info] command_divider : Transfer processed pico to remote T3 storage\n'
      job_command_string += 'xrdcp -f zgamma/raw_pico/raw_pico_458276d1-ecc0-4e0e-b8d5-bd016136af57.root root://cluster142.knu.ac.kr:1094//store/user/sucho/out_zgamma/raw_pico/\n'
    job_command_string += 'echo [Info] command_divider : Finished\n'


    # Write command file to file
    with open(job_command_file_path, 'w') as job_command_file:
      job_command_file.write(job_command_string)
    os.system('chmod +x '+job_command_file_path)

    submission_command = job_command_file_path

    submission_command_info = [submission_command, commands_info]
    return submission_command_info

  # job_index starts from 1
  # commands_info = [[command, job_index]]
  # submission_commands_info = [[submission_command, [command, job_index]]]
  # Should modify jobs_info[job_index]['job_identifier']. Should modify jobs_info[job_index]['job_status'] to 'submitted'
  # jobs_info = ({'global_key':global_value},{'command': command for job 1, 'key_for_job':value_for_job1},{'command': command for job 2', key_for_job':value2_for_job2},...)
  def submit_jobs(self, submission_commands_info, jobs_info, jobs_info_filename, node=None, max_run=None, input_files=None, output_files=None, ncpus_in_job=None):
    if len(submission_commands_info) == 0:
      print("[Info] No jobs to submit.")
      return

    submission_file_path = jobs_info_filename+'.sub.'+datetime.datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
    #if max_run == None:
    #  max_run = subprocess.check_output("condor_status --total | grep X86 | awk '{ print $2 }'", shell=True, encoding='UTF-8').rstrip()
    #  max_run = int(int(max_run)*1.5)

    # Make submission script
    submission_string = ''
    submission_string += 'universe = vanilla\n'
    submission_string += '+ProjectName="cms.org.cern"\n'
    submission_string += 'Notification = Never\n'
    submission_string += 'Requirements = HasSingularity\n'
    #submission_string += '+SingularityImage = "/cvmfs/singularity.opensciencegrid.org/cmssw/cms:rhel9"\n'
    #submission_string += '+DesiredOS = "EL9"\n'
    submission_string += '+SingularityImage = "/cvmfs/unpacked.cern.ch/registry.hub.docker.com/cmssw/el9:x86_64"\n'
    submission_string += 'transfer_executable = True\n'
    if input_files:
      #submission_string += 'transfer_input_files = voms_proxy.txt,CMSSW_10_6_26.tar.gz\n'
      submission_string += f'transfer_input_files = {input_files}\n'
      submission_string += 'should_transfer_files = YES\n'
    if output_files:
      submission_string += 'when_to_transfer_output = ON_EXIT\n'
      submission_string += f'transfer_output_files = {output_files}\n'
    submission_string += '\n'
    submission_string += 'executable = $(command)\n'
    submission_string += 'output = logs/out.$(Cluster).$(Process)\n'
    submission_string += 'error  = logs/out.$(Cluster).$(Process)\n'
    submission_string += 'log    = logs/out.$(Cluster).$(Process).log\n'
    submission_string += '# Limit number of jobs\n'
    if max_run != None:
      submission_string += 'max_materialize = '+str(max_run)+'\n'
    #max_idle = int(int(max_run)*1.5+1)
    #submission_string += 'max_idle = '+str(max_idle)+'\n'
    #submission_string += '# Resolve automount nsf\n'
    #submission_string += 'initialdir = '+os.getcwd()+'\n'
    if ncpus_in_job != None:
        submission_string += f'request_cpus = {ncpus_in_job}\n'
    if node:
      submission_string += 'Requirements = (TARGET.Machine == "'+node+'.physics.ucsb.edu")\n'
    submission_string += 'queue command from (\n'
    for submission_command_info in submission_commands_info:
      # submission_command_info = [submission_command, commands_info]
      # commands_info = [(command, job_index)]
      submission_string += submission_command_info[0]+'\n'
    submission_string += ')\n'
    with open(submission_file_path, 'w') as submission_file:
      submission_file.write(submission_string)

    # Submit submission script
    submit_result = subprocess.check_output('condor_submit '+submission_file_path, shell=True, encoding='UTF-8')
    # Example) submit_result = "6 job(s) submitted to cluster 10"
    print(submit_result)

    # Change job_info
    cluster = re.search('cluster (\d+)', submit_result).group(1) 
    for index, submission_command_info in enumerate(submission_commands_info):
      # submission_command_info = [submission_command, commands_info]
      # commands_info = [(command, job_index)]
      job_id = cluster+'.'+str(index)
      submission_command = submission_command_info[0]
      commands_info = submission_command_info[1]
      job_indices = self.get_job_indices_from_commands_info(commands_info)
      for multiple_index, job_index in enumerate(job_indices):
        jobs_info[job_index]['job_identifier'] = self.get_job_identifier(job_id,multiple_index)
        jobs_info[job_index]['job_status'] = 'submitted'
        print('[Info] Modified jobs_info['+str(job_index)+'] to '+job_id)
        print('[Info] Modified jobs_info['+str(job_index)+'] to submitted')
        jobs_info[job_index]['submission_command'] = submission_command
        jobs_info[job_index]['job_trials'].append(jobs_info[job_index]['job_identifier'])

  ## job_index starts from 1
  ## commands_info = [[command, job_index]]
  ## submission_command_info = [submission_command, commands_info]
  ## Should modify jobs_info[job_index]['job_identifier']. Should modify jobs_info[job_index]['job_status'] to 'submitted'
  ## jobs_info = ({'global_key':global_value},{'command': command for job 1, 'key_for_job':value_for_job1},{'command': command for job 2', key_for_job':value2_for_job2},...)
  #def submit_job(self, submission_command_info, jobs_info):
  #  submission_command = submission_command_info[0]
  #  commands_info = submission_command_info[1]
  #  #print(commands_info)
  #  job_indices = self.get_job_indices_from_commands_info(commands_info)
  #  print('submit job_index(s): ' +str(job_indices)+' command: '+submission_command)

  #  job_result = subprocess.check_output(submission_command, shell=True)
  #  print(job_result)
  #  job_id = job_result.rstrip().replace('Submitted job ','')

  #  for multiple_index, job_index in enumerate(job_indices):
  #    jobs_info[job_index]['job_identifier'] = self.get_job_identifier(job_id,multiple_index)
  #    jobs_info[job_index]['job_status'] = 'submitted'
  #    print('[Info] Modified jobs_info['+str(job_index)+'] to '+job_id)
  #    print('[Info] Modified jobs_info['+str(job_index)+'] to submitted')

  # Should get job_index log using multiple_index and job_id.
  # Return 'not_found' if the file does not exists
  def get_job_log_string(self, job_id, multiple_index):
    log_path = 'logs/out.'+job_id
    log_string = 'not_found'
    if os.path.exists(log_path):
      # Divide according to below.
      # [Info] command_divider : Start divided_command[multiple_index]
      # [Info] command_divider : End divided_command[multiple_index]
      log_string = ''
      log_start = False
      log_end = False
      with open(log_path) as log_file:
        for line in log_file:
          if '[Info] command_divider : Start divided_command['+multiple_index+']' in line: log_start = True
          if '[Info] command_divider : End divided_command['+multiple_index+']' in line: log_end = True
          if 'Terminated\n' == line: 
            log_string += '[Error] Job was terminated. job_id: '+str(job_id)+' multiple_index: '+str(multiple_index)+'.'
            return log_string
          if log_start: log_string += line
          if log_end: break
      if log_start == False or log_end == False:
        log_string = 'not_found'
        #log_string = "[Error] Couldn't find log_start: "+str(log_start)+" or log_end:"+str(log_end)+'\n'
        #with open(log_path) as log_file:
        #  log_string += log_file.read()
    return log_string

  def does_job_exist(self, job_id):
    # Check factory
    cluster_id, process_id = job_id.split('.')
    command = "condor_q -factory "+cluster_id+" | grep -A1 OWNER | grep -v OWNER | awk '{print $10}'"
    next_id = subprocess.check_output(command, shell=True, encoding='UTF-8').rstrip()
    if next_id != "":
      if int(process_id) >= int(next_id): return True
    # Check running
    command = "condor_q -nobatch "+job_id+" | grep -A1 OWNER | grep -v OWNER | sed '/^$/d' | wc -l"
    t_does_job_exist = (subprocess.check_output(command, shell=True, encoding='UTF-8').rstrip() == "1")
    if t_does_job_exist: return True
    # Check history
    command = "condor_history "+job_id+" | grep -A1 OWNER | grep -v OWNER | wc -l"
    t_does_job_exist = (subprocess.check_output(command, shell=True, encoding='UTF-8').rstrip() == "1")
    if t_does_job_exist: return True
    return False
    #list_dir = '/net/cms2/cms2r0/'+os.getenv('USER')+'/jobs/'
    #command = "cat "+list_dir+"queued.list "+list_dir+"ready.list "+list_dir+"running.list "+list_dir+"completed.list "+list_dir+"old.list | awk '{print $1}' | grep "+job_id+" | wc -l"
    #t_does_job_exist = subprocess.check_output(command, shell=True).rstrip()
    ## Check it again to be sure
    #if (t_does_job_exist == "0"):
    #  t_does_job_exist = subprocess.check_output(command, shell=True).rstrip()
    ## Check it again to be sure
    #if (t_does_job_exist == "0"):
    #  t_does_job_exist = subprocess.check_output(command, shell=True).rstrip()
    #return t_does_job_exist != "0"

if __name__ == '__main__':
  # Reserved keys: job_id, job_status
  # multiple jobs can have same job_id if they were submitted with one job command

  jobs_info_filename = 'jsons/mc_2016_jobs_info.json'
  out_jobs_info_filename = 'jsons/submitted_mc_2016_jobs_info.json'

  #jobs_info = datasets.load_json_file(jobs_info_filename)
  #queue = ucsb_job()
  #queue.submit_jobs_info(jobs_info, node='cms1')
  ##assign_job_id(queue, jobs_info, 6068)

  #datasets.save_json_file(jobs_info, out_jobs_info_filename)

