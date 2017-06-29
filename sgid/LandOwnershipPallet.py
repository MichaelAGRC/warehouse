'''
LandOwnershipPallet.py
Truncate and append sitla land ownership into SGID10
'''

import arcpy
from forklift.models import Pallet
from time import strftime
from os.path import join


class LandownershipPallet(Pallet):
    def is_ready_to_ship(self):
        run_day = 'Monday'
        ready = strftime('%A') == run_day
        if not ready:
            self.success = (True, 'This pallet only runs on {}s.'.format(run_day))

        return ready

    def ship(self):
        cadastre = join(self.garage, 'DC_Cadastre@SGID10@sgid.agrc.utah.gov.sde')
        sitlaLand = join(cadastre, 'SGID10.CADASTRE.LandOwnership_WeeklyUpdate')
        agrcLand10 = join(cadastre, 'SGID10.CADASTRE.LandOwnership')

        self.log.info('Truncating and appending: ' + agrcLand10)
        arcpy.TruncateTable_management(agrcLand10)
        arcpy.Append_management(sitlaLand, agrcLand10, 'TEST')

if __name__ == '__main__':
    import logging

    pallet = LandownershipPallet()
    logging.basicConfig(
        format='%(levelname)s %(asctime)s %(lineno)s %(message)s',
        datefmt='%H:%M:%S',
        level=logging.INFO
    )
    pallet.log = logging
    pallet.ship()
