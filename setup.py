import os
import subprocess
from setuptools import setup, find_packages
from setuptools.command.install import install

class InstallWithCompile(install):
    def run(self):
        locale_dir = os.path.abspath('pytr/locale')
        if not os.path.exists(locale_dir):
            raise FileNotFoundError(f"The locale directory '{locale_dir}' does not exist.")
        try:
            subprocess.check_call(['pybabel', 'compile', '-d', locale_dir])
        except subprocess.CalledProcessError as e:
            print(f"Error while compiling catalog: {e}")
            raise
        install.run(self)

setup(
    package_data={
        '': ['pytr/locale/*/*/*.mo', 'pytr/locale/*/*/*.po'],  # Include locale files
    },
    cmdclass={'install': InstallWithCompile}
)
