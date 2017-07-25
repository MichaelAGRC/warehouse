#!/usr/bin/env python
# * coding: utf8 *
'''
HistoricalSitesPallet.py

A module that contains a pallet definition for updating the historical sites in SGID from the UDSH database

This pallet works in conjunction with a script that is scheduled to run nightly on the UDSH server.
It exports the data into an FGDB so that forklift can read it. The UDSH SQL database is too old for Pro support.
'''


from forklift.models import Pallet
from os.path import join
import arcpy
import history_secrets as secrets


class HistoricalSitesPallet(Pallet):
    def build(self, config):
        self.udsh = r'\\{}\c$\Scheduled\LocalScripts\DataPickup\UDSHSpatial_New.gdb'.format(secrets.UDSH_MACHINE)
        self.udsh_stage = join(self.staging_rack, 'UDSHSpatial_New.gdb')
        self.sgid = join(self.garage, 'SGID_History@SGID10.sde')

        self.udsh_feature_classes = ['UDSHSpatial_New_UDSH_IMACS_SITE_POINT',
                                     'UDSHSpatial_New_UDSH_IMACS_SITE_LINE',
                                     'UDSHSpatial_New_UDSH_IMACS_SITE_POLYGON']

        self.add_crates(self.udsh_feature_classes, {'source_workspace': self.udsh, 'destination_workspace': self.udsh_stage})

    def process(self):
        field = 'PresenceYN'
        archSites = join(self.sgid, 'SGID10.HISTORY.ArchaeologySites')

        self.log.info('creating layer')
        archSitesFL = arcpy.MakeFeatureLayer_management(archSites)

        self.log.info('selecting by location')
        for fc in self.udsh_feature_classes:
            arcpy.SelectLayerByLocation_management(archSitesFL, 'INTERSECT', join(self.udsh_stage, fc), '', 'NEW_SELECTION')

        self.log.info('calculating new values for: ' + field)
        arcpy.CalculateField_management(archSitesFL, field, '"Site(s) Present"', 'PYTHON')
        arcpy.SelectLayerByAttribute_management(archSitesFL, 'SWITCH_SELECTION')
        arcpy.CalculateField_management(archSitesFL, field, '"Site Presence Unknown"', 'PYTHON')
