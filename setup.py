# -*- coding: utf8 -*-
#
# Copyright (C) Cauly Kan, mail: cauliflower.kan@gmail.com
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.


'''
Created on 2014-03-12 

@author: cauly
'''
from setuptools import find_packages, setup

setup(
    name='TracTicketRelationPlugin', version='1.5',
    packages=find_packages(exclude=['*.tests*']),
    license = "BSD 3-Clause",
    author_email='cauliflower.kan@gmail.com',
    author='Cauly Kan',
    package_data={ 'ticketrelation': ['htdocs/js/*.js', 'htdocs/images/*.png', 'htdocs/css/*.css', 'templates/*.html'] },
    entry_points={
        'trac.plugins': [
            'TracTicketRelationPlugin.api = ticketrelation.api',
            'TracTicketRelationPlugin.rpc = ticketrelation.xmlrpc',
            'TracTicketRelationPlugin.select_ticket= ticketrelation.select_ticket',
            'TracTicketRelationPlugin.schedule = ticketrelation.schedule',
            'TracTicketRelationPlugin.earn_value = ticketrelation.earn_value',
        ],
    },
)
