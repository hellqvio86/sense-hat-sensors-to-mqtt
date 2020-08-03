import os
import sys


class Daemonizer(object):
    def __init__(self):
        '''
        Empty
        '''
        self.run()
        return

    def run(self):
        self.__background_process()
        self.__decouple()
        self.__background_process()
        self.__redirect()

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
        os.umask(0)

        return

    def __set_new_sid(self):
        os.setpgrp()

        return

    def __change_directory(self):
        os.chdir('/')

        return

    def __background_process(self):
        #Will raise OSError if it fails to fork
        pid = os.fork()
        if (pid == 0):
            # CHILD
            return
        else:
            sys.exit(0)
        return

def start():
    worker = Daemonizer()
    worker.run()

    return

if __name__ == '__main__':
    start()