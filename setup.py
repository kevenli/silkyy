import os
from setuptools import setup
from setuptools import find_packages
from pkgutil import walk_packages
import io

def read_file(filename):
    with io.open(filename) as fp:
        return fp.read().strip()


def read_rst(filename):
    # Ignore unsupported directives by pypi.
    content = read_file(filename)
    return ''.join(line for line in io.StringIO(content)
                   if not line.startswith('.. comment::'))


def read_requirements(filename):
    return [line.strip() for line in read_file(filename).splitlines()
            if not line.startswith('#')]

os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='silkyy',
    version=read_file('silkyy/VERSION'),
    packages=find_packages(),
    include_package_data=True,
    install_requires=read_requirements('requirements.txt'),
    data_files=[('', ['silkyy/VERSION', 'silkyy/migrations/migrate.cfg'])],
)

