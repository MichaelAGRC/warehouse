'''
SGID10MercatorPallet.py
A module that contains a pallet definition for the data that gets pushed to AGOL.
'''

from forklift.models import Pallet
from os.path import join
import sgid_secrets as secrets


class SGID10Mercator(Pallet):

    def build(self, config):
        self.sgid = join(self.garage, 'SGID10.sde')
        self.SGID10Mercator = r'\\{}\AGRCBackup\AGRC Projects\AGOL\SGID10Mercator\SGID10Mercator.gdb'.format(secrets.HNAS)

        self.add_crates([
            'AddressPoints',
            'AssociationOfGovernments',
            'BusRoutes_UTA',
            'BusStops_UTA',
            'CitiesTownsLocations',
            'CommuterRailRoutes_UTA',
            'CommuterRailStations_UTA',
            'Counties',
            'Courts_City',
            'Courts_County',
            'HUC',
            'LawEnforcementBoundaries',
            'LightRail_UTA',
            'LightRailStations_UTA',
            'LiquorStores',
            'Municipalities',
            'ParksLocal',
            'PlaceNamesGNIS2010',
            'PLSSPoint_GCDB',
            'PLSSQuarterQuarterSections_GCDB',
            'PLSSQuarterSections_GCDB',
            'PLSSSections_GCDB',
            'PLSSTownships_GCDB',
            'Railroads',
            'Roads',
            'SchoolDistricts',
            'Schools',
            'SkiAreaBoundaries',
            'SkiAreaLocations',
            'SkiLifts',
            'StateCourtDistricts',
            'StateFuelSites',
            'TaxAreas2016',
            'Trailheads',
            'Trails',
            'TURN_GPS_BaseLines',
            'TURN_GPS_Stations',
            'UHPDispatch',
            'Utah',
            'UtahHouseDistricts2012',
            'UtahMajorLakes',
            'UtahMajorRiversPoly',
            'UtahSenateDistricts2012',
            'ZipCodes',
        ], {'source_workspace': self.sgid,
            'destination_workspace': self.SGID10Mercator})
