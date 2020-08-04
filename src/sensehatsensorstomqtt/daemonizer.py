import logging
import os
import sys

_LOGGER = logging.getLogger(__name__)

class Daemonizer(object):
    _pid_file = None
    def __init__(self, *, pid_file=None):
        '''
        
        '''
        self._pid_file = pid_file

        self.run()
        return

    def run(self):
        self.__background_process()
        self.__decouple()
        self.__background_process()
        self.__redirect()

        if self._pid_file:
            self.___setup_pidfile()

        return

    def ___setup_pidfile(self):
        pid = os.getpid()

        _LOGGER.debug(f'Setting up pidfile for PID {pid} to {self._pid_file}')

        pid_desc = open(self._pid_file, 'w')

        pid_desc.write(pid)

        pid_desc.close()

        return

    def __redirect(self):
        sys.stdin.close()
        sys.stdin = open('/dev/null', 'r')

        sys.stdout.close()
        sys.stdout = open('/dev/null', 'w')

        sys.stderr.close()
        sys.stderr = open('/dev/null', 'w')

        return

    def __decouple(self):
        self.__change_directory()

        self.__set_new_sid()
        self.__change_file_mode_mask()

        return

    def __change_file_mode_mask(self):
        _LOGGER.debug('Changing filemask to 0')
    
        os.umask(0)

        return

    def __set_new_sid(self):
        _LOGGER.debug('Setting new sid')
    
        os.setpgrp()

        return

    def __change_directory(self):
        _LOGGER.debug('Changing directory to /')

        os.chdir('/')

    def __background_process(self):
        #Will raise OSError if it fails to fork
        _LOGGER.debug('Forking')
    
        pid = os.fork()

        if (pid == 0):
            # CHILD
            return
        else:
            sys.exit(0)

def start():
    worker = Daemonizer()
    worker.run()

    return

if __name__ == '__main__':
    start()