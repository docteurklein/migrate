import paramiko


def get_current_step(params):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(params.hostname, port=params.port, username=params.username, password=params.password)
    stdin, stdout, stderr = client.exec_command('cat %s' % params.path)
    if stdout.channel.recv_exit_status() != 0:
        pass
        #raise Exception
    return stdout.read()


def put_current_step(step, params):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(params.hostname, port=params.port, username=params.username, password=params.password)
    stdin, stdout, stderr = client.exec_command('sh -c "cat - > %s"' % params.path)
    stdin.write(step)
    stdin.channel.close()
    if stdout.channel.recv_exit_status() != 0:
        pass
        #raise Exception
