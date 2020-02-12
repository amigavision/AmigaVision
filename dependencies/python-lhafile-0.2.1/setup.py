# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Hidekazu Ohnishi
#
# This software is released under the terms of the BSD license.
# For more information see the COPYING.txt file in this directory.

from distutils.core import setup, Extension
import sys
import platform

extra_compile_args=[]
extra_link_args=[]
if sys.platform == "darwin" and platform.machine() == "i386":
    extra_compile_args.append("-m32")
    extra_link_args.append("-m32")

lzhlib = Extension('lzhlib',
                   extra_compile_args=extra_compile_args,
                   extra_link_args=extra_link_args,
                   define_macros=[('MAJOR_VERSION', '0'),
                                  ('MINOR_VERSION', '2')],
                   sources=['lzhlib.c'])

setup(name="lhafile",
      packages=['lhafile'],
      version='0.2.1',
      description="LHA(.lzh) file extract interface",
      long_description="""Extract LHA(.lzh) file extension.
Its interface is likely zipfile extension is included in regular
python distribution.""",
      author='Hidekazu Ohnishi',
      author_email='the-o@neotitans.net',
      url='http://trac.neotitans.net/wiki/lhafile',
      download_url='http://trac.neotitans.net/wiki/lhafile',
      license='BSD',
      keywords = [],
      classifiers = [
        'Development Status :: 4 - Beta',
        'Envrionment :: Other Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent'
        'Programming Language :: Python',
        'Topic :: Software Development'],
      ext_modules=[lzhlib])
