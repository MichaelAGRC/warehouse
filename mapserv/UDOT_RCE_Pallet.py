#!/usr/bin/env python
# * coding: utf8 *
'''
UDOT_RCE_Pallet.py

A module that contains a pallet that updates data in the UDOT_RCE service
'''

from forklift.models import Pallet
from os.path import join


class UDOT_RCE_Pallet(Pallet):

    def __init__(self):
        super(UDOT_RCE_Pallet, self).__init__()

        self.arcgis_services = [('UDOT_RCE', 'MapServer')]

        self.boundaries = join(self.staging_rack, 'boundaries.gdb')

        self.copy_data = [self.boundaries]

    def build(self, configuration=None):
        self.add_crates(['Municipalities', 'Counties'],
                        {'source_workspace': join(self.garage, 'SGID10.sde'),
                         'destination_workspace': self.boundaries})
