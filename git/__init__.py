import logging
import os
import subprocess
import time
from util import LazyString

git_logger = logging.getLogger('git')
# git_logger.setLevel(logging.INFO)


class GitProcess(object):
    def __init__(self, args, stdin=None):
        self._proc = subprocess.Popen(['git'] + list(args), stdin=stdin,
                                      stdout=subprocess.PIPE)

    def readline(self):
        return self._proc.stdout.readline()

    def read(self, length=0):
        return self._proc.stdout.read(length)

    def __iter__(self):
        return iter(self._proc.stdout)

    def wait(self):
        return self._proc.wait()

    @property
    def pid(self):
        return self._proc.pid


def git(*args, **kwargs):
    assert not kwargs or not set(kwargs.keys()) - set(['keepends', 'stdin'])
    keepends = kwargs.get('keepends', False)
    stdin = kwargs.get('stdin', None)
    assert stdin != subprocess.PIPE
    start = time.time()

    proc = GitProcess(args, stdin)
    git_logger.info(LazyString(lambda: '[%d] git %s' % (
        proc.pid,
        ' '.join(args),
    )))
    for line in proc:
        git_logger.debug(LazyString(lambda: '[%d] => %s' % (
            proc.pid,
            repr(line),
        )))
        if not keepends:
            line = line.rstrip('\n')
        yield line

    proc.wait()
    git_logger.info(LazyString(lambda: '[%d] wall time: %.3fs' % (
        proc.pid,
        time.time() - start,
    )))


def git_for_each_ref(pattern, format='%(objectname)'):
    if not pattern.startswith('refs/'):
        pattern = 'refs/remote-hg/%s' % pattern
    if format:
        return git('for-each-ref', '--format', format, pattern)
    return git('for-each-ref', pattern)


# TODO: properly wait() for the process somehow
class git_cat_file(object):
    def __init__(self):
        self.__proc = None
        self.__pipe = None

    def __call__(self, typ, sha1):
        self._pipe.write(sha1 + '\n')
        header = self._proc.readline().split()
        if header[1] == 'missing':
            return None
        assert header[1] == typ
        size = int(header[2])
        ret = self._proc.read(size)
        self._proc.read(1)  # LF
        return ret

    @property
    def _pipe(self):
        if not self.__pipe:
            self._init()
        return self.__pipe

    @property
    def _proc(self):
        if not self.__proc:
            self._init()
        return self.__proc

    def _init(self):
        reader, writer = os.pipe()
        self.__pipe = os.fdopen(writer, 'w', 0)
        self.__proc = GitProcess(['cat-file', '--batch'], stdin=reader)

git_cat_file = git_cat_file()
