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
    job_command_string += 'job_start=$(date +%s)\n' # Time
    job_command_string += 'echo "[Timing] job_start_time=$job_start"\n' # Time absolute
    job_command_string += 'JOB_DIR="$PWD"\n'

    # Rucio
    job_command_string += 'source /cvmfs/cms.cern.ch/rucio/setup-py3.sh\n'
    job_command_string += 'echo "[Info] Rucio executable: $(which rucio)"\n'
    job_command_string += 'echo "X509_USER_PROXY=$X509_USER_PROXY"\n'
    job_command_string += 'rucio whoami || exit 1\n'
    job_command_string += 'echo "[Info] Rucio transfer tools:"\n'
    job_command_string += 'which gfal-copy || true\n'
    job_command_string += 'which xrdcp || true\n'
    job_command_string += 'which davix-get || true\n'
    job_command_string += 'gfal-copy --version || true\n'
    job_command_string += 'xrdcp --version || true\n'
    job_command_string += '\n'

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

    # Check transferred files
    job_command_string += '\n'
    job_command_string += 'echo "[Info] Files in job directory:"\n'
    job_command_string += 'find . -maxdepth 3 -type f -print\n'
    job_command_string += '\n'

    # Write commands
    for command_index, command_info in enumerate(commands_info):
      command = command_info[0]
    
      # Example command:
      # ./run/process_nano.exe
      #   -f f0fa....root
      #   -i /store/data/Run2023D/.../50000/
      #   -o ./zgamma/
      #   --nent 10000
    
      nano_file = command.split("-f ")[1].split()[0]
      nano_lfn_dir = command.split("-i ")[1].split()[0]
      nano_lfn = nano_lfn_dir + nano_file
    
      # Remote path used only for xrdcp.
      # redirector = "root://cms-xrd-global.cern.ch/"
      # nano_remote_file = redirector + nano_lfn_dir + nano_file
    
      # Preserve the LFN directory structure locally.
      nano_local_dir = "." + nano_lfn_dir
      nano_local_file = nano_local_dir + nano_file
    
      # Start this divided command. job_log_string begins.
      job_command_string += 'echo [Info] command_divider : Start divided_command[{}]\n'.format(command_index)
      job_command_string += 'total_start=$(date +%s)\n' # Time
    
      # Prepare input NanoAOD using xrdcp.
      job_command_string += 'echo "[Info] Create local NanoAOD directory: {}"\n'.format(nano_local_dir)
      job_command_string += 'mkdir -p "{}"\n'.format(nano_local_dir)
      #job_command_string += 'echo "[Info] Copy NanoAOD input from XRootD"\n'
      #job_command_string += 'xrdcp -f "{}" "{}" || exit 1\n'.format(
      #    nano_remote_file,
      #    nano_local_file
      #)
      job_command_string += 'download_start=$(date +%s)\n' # Time
      job_command_string += 'echo "[Info] Copy NanoAOD input from Rucio"\n'
      job_command_string += (
                             'timeout 1h rucio download --dir . --no-subdir "cms:{}" '
                             '|| {{ echo "[Error] rucio download nano failed or timed out"; exit 1; }}\n'
                             ).format(nano_lfn)
      job_command_string += 'download_end=$(date +%s)\n' # Time
      job_command_string += 'echo "[Timing] download_sec=$((download_end-download_start))"\n' # Time
      job_command_string += 'echo "[Info] Copy done from Rucio."\n'
      job_command_string += 'echo "[Info] Check downloaded NanoAOD:"\n'
      job_command_string += 'find "$JOB_DIR" -type f -name "{}" -ls\n'.format(nano_file)
      job_command_string += 'find "{}" -maxdepth 3 -type f -name "*.root" -ls\n'.format(nano_local_dir)

      # Replace LFN input directory with local input directory.
      local_command = command.replace(
          nano_lfn_dir,
          nano_local_dir,
          1
      )
    
      # CMSSW
      job_command_string += 'source /cvmfs/cms.cern.ch/cmsset_default.sh\n'
      job_command_string += 'cd /cvmfs/cms.cern.ch/el9_amd64_gcc12/cms/cmssw/CMSSW_15_0_17/src\n'
      job_command_string += 'eval "$(scram runtime -sh)"\n'
      job_command_string += 'cd "$JOB_DIR"\n'
      # Check shared library resolution before running process_nano.
      job_command_string += ('echo "[Info] Shared-library check for process_nano.exe:"\n')
      #job_command_string += 'ldd run/process_nano.exe\n'
      job_command_string += 'if ldd run/process_nano.exe 2>&1 | grep -q "not found"; then exit 1; fi\n'
      job_command_string += '\n'
      # Run process_nano.
      job_command_string += 'echo [Info] command_divider : Current directory: "$PWD"\n'
      job_command_string += 'echo [Info] command_divider : command: ' + local_command + '\n'
      job_command_string += 'process_start=$(date +%s)\n' # Time
      job_command_string += local_command + ' || { echo "[Error] process_nano failed"; exit 1; }\n'
      job_command_string += 'process_end=$(date +%s)\n' # Time
      job_command_string += 'echo "[Timing] process_nano_sec=$((process_end-process_start))"\n' # Time
    
      job_command_string += 'echo [Info] command_divider : End divided_command[{}]\n'.format(command_index)
    
      # Transfer output pico.
      job_command_string += 'echo [Info] command_divider : Transfer processed pico of divided_command[{}] to remote T3 storage\n'.format(command_index)
      job_command_string += 'transfer_start=$(date +%s)\n' # Time
      job_command_string += (
                             'xrdcp -f zgamma/raw_pico/raw_pico_*__{} '
                             'root://cluster142.knu.ac.kr:1094//store/user/sucho/out_zgamma/raw_pico/ '
                             '|| {{ echo "[Error] xrdcp transfer pico failed"; exit 1; }}\n'
                             ).format(nano_file)
      job_command_string += 'transfer_end=$(date +%s)\n' # Time
      job_command_string += 'echo "[Timing] transfer_sec=$((transfer_end-transfer_start))"\n' # Time
      job_command_string += 'total_end=$(date +%s)\n' # Time
      job_command_string += 'echo "[Timing] total_sec=$((total_end-total_start))"\n' # Time
      job_command_string += 'echo [Info] command_divider : Transfer done for divided_command[{}]\n'.format(command_index)

      # Unset CMSSW and reset Rucio for next divided command. This is needed to prevent env crash between Rucio & CMSSW.
      job_command_string += 'echo "[Info] Unset CMSSW environment"\n'
      job_command_string += 'eval "$(scram unsetenv -sh)"\n'
      job_command_string += 'source /cvmfs/cms.cern.ch/rucio/setup-py3.sh\n'
    
    job_command_string += 'job_end=$(date +%s)\n' # Time
    job_command_string += 'echo "[Timing] job_end_time=$job_end"\n' # Time absoulte
    job_command_string += 'echo "[Timing] job_total_sec=$((job_end-job_start))"\n' # Time
    job_command_string += 'echo [Info] command_divider : Finished\n' # All divided commands finished and transferred to destination SE.

    
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
    submission_string += 'use_x509userproxy = true\n'
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
    # submit_result = subprocess.check_output('condor_submit '+submission_file_path, shell=True, encoding='UTF-8')
    try :
      submit_result = subprocess.check_output(
              'condor_submit '+submission_file_path, shell=True, encoding='UTF-8', stderr=subprocess.STDOUT
              )
    except subprocess.CalledProcessError as e:
      print("[Warning] condor_submit failed.")
      print(e.output)
      print("[Warning] Jobs remain to_submit and will be retried in the next cycle.")
      return
    
    print(submit_result) # Example) submit_result = "6 job(s) submitted to cluster 10"

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
  
    log_path = 'logs/out.' + job_id
    log_string = 'not_found'
  
    print("DEBUG cwd:", os.getcwd())
    print("DEBUG log_path:", os.path.abspath(log_path))
    print("DEBUG job_id:", job_id)
    print("DEBUG multiple_index:", repr(multiple_index))
  
    if os.path.exists(log_path):
  
      # Divide according to:
      #
      # [Info] command_divider : Start divided_command[multiple_index]
      # ...
      # [Info] command_divider : End divided_command[multiple_index]
  
      log_string = ''
      log_start = False
      log_end = False
  
      with open(log_path) as log_file:
  
        for line in log_file:
  
          if '[Info] command_divider : Start divided_command[' + multiple_index + ']' in line:
            log_start = True
            print("DEBUG found START")
          if '[Info] command_divider : Transfer done for divided_command[' + multiple_index + ']' in line:
            log_end = True
            print("DEBUG found END")
  
          if 'Terminated\n' == line:
            log_string += (
              '[Error] Job was terminated. job_id: '
              + str(job_id)
              + ' multiple_index: '
              + str(multiple_index)
              + '.'
            )
            return log_string
  
          if log_start:
            log_string += line
  
          if log_end:
            break
  
      print("DEBUG log_start:", log_start)
      print("DEBUG log_end:", log_end)
      # print("DEBUG get_job_log_string: return =", repr(log_string))
  
      if log_start == False:
        log_string = 'not_found'
  
    else:
      print("DEBUG log file does not exist")
  
    # print("DEBUG return log_string:", repr(log_string))
  
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

