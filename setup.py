# ND-300-serial
# This file is licensed under the AGPL v3.0. You may find it here:
# https://github.com/TrueLevelSA/ND-300-serial/blob/master/LICENSE
# Copyright (C) 2020 TrueLevel SA.
# Authors: Quentin Jeanmonod "roflolilolmao" q@truelevel.ch

from setuptools import setup
import nd300

with open('README.md', 'r') as f:
    long_description = f.read()

setup(
    name='nd300',
    version=nd300.__version__,
    description='Serial drivers for ND-300CM/KM',
    license='AGPL-3.0',
    long_description=long_description,
    author='Quentin Jeanmonod',
    author_email='q@truelevel.ch',
    url='https://github.com/TrueLevelSA/ND-300-serial',
    py_modules=['nd300'],
    python_requires='>=3.6',
)
