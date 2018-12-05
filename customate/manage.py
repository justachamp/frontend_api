#!/usr/bin/env python
import os
import sys

sys.path.append('pycharm-debug-py3k.egg')
import pydevd
pydevd.settrace('docker.for.mac.localhost', port=1234,  suspend=True, stdoutToServer=True, stderrToServer=True)

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'customate.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)
