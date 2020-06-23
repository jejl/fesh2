#from distutils.core import setup, find_packages
from setuptools import setup, find_packages

setup(
    name='fesh2',
    version='2.0c1',
    # packages=['__main__.py'],
    url='https://github.com/jejl/fesh2',
    license='GPL v3',
    author='Jim Lovell',
    author_email='jejlovell@gmail.com',
    description='Geodetic VLBI schedule management and processing',
    long_description = "file: README.md",
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=["pexpect >= 4.7.0", "pycurl >=7.43.0.2]"],
    include_package_data=True
)
