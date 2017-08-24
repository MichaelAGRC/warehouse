#!/usr/bin/env python
# * coding: utf8 *
'''
Base.py

A module that contains the pallets for the map services in the base directory of arcgis server
'''

from forklift.models import Pallet
from os.path import join


class PoliticalDistrictsPallet(Pallet):

    def __init__(self):
        super(PoliticalDistrictsPallet, self).__init__()

        self.arcgis_services = [('PoliticalDistricts', 'MapServer')]

        self.political = join(self.staging_rack, 'political_utm.gdb')

        self.copy_data = [self.political]
        self.destination_coordinate_system = 26912

    def build(self, configuration=None):
        source_workspace = join(self.garage, 'SGID10.sde')

        self.add_crates(['UtahHouseDistricts2012', 'UtahSenateDistricts2012', 'DistrictCombinationAreas2012'],
                        {'source_workspace': source_workspace,
                         'destination_workspace': self.political})


class SocrataPallet(Pallet):

    def __init__(self):
        super(SocrataPallet, self).__init__()

        self.arcgis_services = [('Socrata', 'MapServer')]

        self.political = join(self.staging_rack, 'political.gdb')
        self.boundaries = join(self.staging_rack, 'boundaries.gdb')
        self.society = join(self.staging_rack, 'society.gdb')
        self.energy = join(self.staging_rack, 'energy.gdb')
        self.economy = join(self.staging_rack, 'economy.gdb')

        self.copy_data = [self.political, self.boundaries, self.society, self.energy, self.economy]

    def build(self, configuration=None):
        source_workspace = join(self.garage, 'SGID10.sde')

        self.add_crates(['Municipalities', 'SchoolDistricts'], {'source_workspace': source_workspace, 'destination_workspace': self.boundaries})

        self.add_crates(['UtahHouseDistricts2012', 'UtahSenateDistricts2012', 'UtahSchoolBoardDistricts2012'],
                        {'source_workspace': source_workspace,
                         'destination_workspace': self.political})

        self.add_crates(['Schools'], {'source_workspace': source_workspace, 'destination_workspace': self.society})

        self.add_crates(['OilGasWells'], {'source_workspace': source_workspace, 'destination_workspace': self.energy})

        self.add_crates(['TaxEntities2014'], {'source_workspace': source_workspace, 'destination_workspace': self.economy})


class UtahEmPallet(Pallet):

    def __init__(self):
        super(UtahEmPallet, self).__init__()

        self.arcgis_services = [('UtahEM', 'MapServer')]

        self.udes = join(self.staging_rack, 'udes.gdb')
        self.udes_sde = join(self.garage, 'UDES.sde', 'UDES.DESADMIN.DES_data')

        self.copy_data = [self.udes]

    def build(self, configuration):
        self.add_crates([
            'Bridges', 'Dams', 'Electricgeneration', 'Ngplants', 'Ngstorage', 'Repeaters_AmateurRadio', 'Repeaters_LongLlink', 'UtahPowerFacilities',
            'OtherPowerFacilities', 'UtahPowerLines', 'OtherPowerLines', 'Pipelines', 'Armories', 'EOCs', 'FireStations', 'Hospitals', 'PoliceStations',
            'Shelters', 'Childcare', 'Eldercare', 'Schools', 'dambreaks_bor_causey', 'dambreaks_bor_currantcreek', 'Dambreaks_bor_deercreek',
            'Dambreaks_bor_eastcanyon', 'Dambreaks_bor_echo', 'Dambreaks_bor_flaminggorge', 'Dambreaks_bor_huntingtonnorth', 'dambreaks_bor_hyrum',
            'dambreaks_bor_joesvalley', 'dambreaks_bor_jordanelle', 'dambreaks_bor_lostcreek', 'dambreaks_bor_moonlake', 'dambreaks_bor_pineview',
            'dambreaks_bor_redfleet', 'dambreaks_bor_scofield', 'dambreaks_bor_soldiercreek', 'dambreaks_bor_starvation', 'dambreaks_bor_steinaker',
            'dambreaks_bor_upperstillwater', 'dambreaks_bor_wanship', 'Dambreaks', 'Floodways_ironco', 'Floodzones_slco_utco', 'Floodzones_sumco',
            'Floodzones_webco', 'GroundShaking_SaltLake_HIRES', 'GroundShaking_Anderson_MMI', 'GroundShaking_Bountiful_MMI', 'GroundShaking_BrighamCity_MMI',
            'GroundShaking_CedarCity_MMI', 'GroundShaking_Clarkston_MMI', 'GroundShaking_Colliston_MMI', 'GroundShaking_Fayette_MMI', 'GroundShaking_Levan_MMI',
            'GroundShaking_Malad_MMI', 'GroundShaking_Nephi_MMI', 'GroundShaking_Provo_MMI', 'GroundShaking_Richfield_MMI', 'GroundShaking_SLC1_MMI',
            'GroundShaking_SLC2_MMI', 'GroundShaking_StGeorge_MMI', 'GroundShaking_Taylorsville_MMI', 'GroundShaking_Washington_MMI', 'GroundShaking_Weber_MMI',
            'Liquifaction_Potential', 'qFaults', 'WildlandFire_Hazard'
        ], {'source_workspace': self.udes_sde,
            'destination_workspace': self.udes})


class HavaPallet(Pallet):
    # NOTE: This pallet can be removed as soon as the Vista app upgrades and switches to using the "Vista" map service
    # which already has a pallet defined within it's project repo
    def __init__(self):
        super(HavaPallet, self).__init__()

        self.arcgis_services = [('Hava', 'MapServer')]

        self.sgid = join(self.garage, 'SGID10.sde')

        self.political = join(self.staging_rack, 'political_utm.gdb')
        self.boundaries = join(self.staging_rack, 'boundaries_utm.gdb')
        self.cadastre = join(self.staging_rack, 'cadastre_utm.gdb')
        self.location = join(self.staging_rack, 'location_utm.gdb')

        self.copy_data = [self.political, self.boundaries, self.cadastre, self.location]

    def build(self, configuration):
        self.add_crates(['UtahHouseDistricts2012', 'UtahSenateDistricts2012', 'USCongressDistricts2012', 'VistaBallotAreas', 'VistaBallotAreas_Proposed'],
                        {'source_workspace': self.sgid,
                         'destination_workspace': self.political})
        self.add_crates([
            'LandOwnership', 'Parcels_Beaver', 'Parcels_BoxElder', 'Parcels_Cache', 'Parcels_Carbon', 'Parcels_Daggett', 'Parcels_Davis', 'Parcels_Duchesne',
            'Parcels_Emery', 'Parcels_Garfield', 'Parcels_Grand', 'Parcels_Iron', 'Parcels_Juab', 'Parcels_Kane', 'Parcels_Millard', 'Parcels_Morgan',
            'Parcels_Piute', 'Parcels_Rich', 'Parcels_SaltLake', 'Parcels_SanJuan', 'Parcels_Sanpete', 'Parcels_Sevier', 'Parcels_Summit', 'Parcels_Tooele',
            'Parcels_Uintah', 'Parcels_Utah', 'Parcels_Wasatch', 'Parcels_Washington', 'Parcels_Wayne', 'Parcels_Weber', 'PLSSSections_GCDB',
            'PLSSTownships_GCDB'
        ], {'source_workspace': self.sgid,
            'destination_workspace': self.cadastre})
        self.add_crates(['Counties', 'ZipCodes'], {'source_workspace': self.sgid, 'destination_workspace': self.boundaries})
        self.add_crate(['AddressPoints', self.sgid, self.location])


class UtahPlssPallet(Pallet):
    # NOTE: This pallet can be removed as soon as we deprecate this service. it's a vector cache in ago now.
    def __init__(self):
        super(UtahPlssPallet, self).__init__()

        self.arcgis_services = [('UtahPLSS', 'MapServer')]

        self.sgid = join(self.garage, 'SGID10.sde')

        self.cadastre = join(self.staging_rack, 'cadastre_utm.gdb')

        self.copy_data = [self.cadastre]
        self.destination_coordinate_system = 26912

    def build(self, configuration):
        self.add_crates(['PLSSTownships_GCDB', 'PLSSSections_GCDB', 'PLSSQuarterSections_GCDB', 'PLSSQuarterQuarterSections_GCDB'],
                        {'source_workspace': self.sgid,
                         'destination_workspace': self.cadastre})
