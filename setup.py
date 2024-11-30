import os
import subprocess
from setuptools import setup
from setuptools.command.build_py import build_py


class BuildWithCompile(build_py):
    def run(self):
        locale_dir = os.path.abspath("pytr/locale")
        if not os.path.exists(locale_dir):
            raise FileNotFoundError(
                f"The locale directory '{locale_dir}' does not exist."
            )
        try:
            subprocess.check_call(["pybabel", "compile", "-d", locale_dir])
        except subprocess.CalledProcessError as e:
            print(f"Error while compiling catalog: {e}")
            raise
        build_py.run(self)


setup(cmdclass={"build_py": BuildWithCompile})
