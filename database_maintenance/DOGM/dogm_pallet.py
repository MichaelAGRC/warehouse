#!/usr/bin/env python
# * coding: utf8 *
'''
dogm_pallet.py

A module that contains a pallet that updates data in the DOGM database from SGID
'''

import arcpy
from forklift.models import Pallet, Crate
from os.path import join


WELLS_DESTINATION_NAME = 'OilGasWells_sde'


class DOGMPallet(Pallet):
    def build(self, configuration=None):
        sgid = join(self.garage, 'SGID10.sde')
        dogm_stage = join(self.staging_rack, 'dogm_stage.gdb')

        self.add_crates(['LandOwnership', 'PLSSQuarterQuarterSections_GCDB'], {
            'source_workspace': sgid,
            'destination_workspace': dogm_stage
        })
        self.add_crate(('OilGasWells', sgid, dogm_stage, WELLS_DESTINATION_NAME))

    def process(self):
        dogm_admin = join(self.garage, 'dogm', 'DOGMADMIN@DOGM@dogm.agrc.utah.gov.sde')
        dogm_wells = join(self.garage, 'dogm', 'OilGas@DOGM@dogm.agrc.utah.gov.sde')

        for crate in self.get_crates():
            if crate.result[0] in [Crate.UPDATED, Crate.CREATED]:
                if crate.destination_name == WELLS_DESTINATION_NAME:
                    sde_destination = join(dogm_wells, 'DOGM.OILGAS.{}'.format(crate.destination_name))
                else:
                    sde_destination = join(dogm_admin, 'DOGM.DOGMADMIN.{}'.format(crate.destination_name))
                self.log.info('truncating and appending {}'.format(sde_destination))

                arcpy.TruncateTable_management(sde_destination)
                arcpy.Append_management(crate.destination, sde_destination, 'NO_TEST')
