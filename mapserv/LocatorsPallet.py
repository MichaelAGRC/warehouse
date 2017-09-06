#!/usr/bin/env python
# * coding: utf8 *
'''
LocatorPallet.py
A module that contains a pallet definition for data to support the web api locator services and
methods to keep them current.

Pre-requisites
    - The `secrets.py` file has been populated from the template file
    - The locators in `self.services` have been created
    - The locators are published to arcgis server

Creating the locators
    - Make sure your `Dev` secrets are populated as that configuration will be used
    - In arcgis pro python execute `LocatorsPallet.py`'''

import arcpy
import locatorsupport.templates as template
import locatorsupport.secrets as secrets
import sys
from forklift.arcgis import LightSwitch
from forklift.models import Crate
from forklift.models import Pallet
from forklift.seat import format_time
from glob import iglob
from os import mkdir
from os.path import join
from os.path import split
from shutil import copyfile
from shutil import rmtree
from time import clock
from xml.etree import ElementTree


class LocatorsPallet(Pallet):

    def __init__(self):
        super(LocatorsPallet, self).__init__()

        self.destination_coordinate_system = 26912

    def build(self, config='Production'):
        #: not to be confused with arcgis_services
        #: this pallet handles the stopping and starting outside of the forklift routine
        self.services = {
            'AddressPoints_AddressSystem': ('Geolocators/AddressPoints_AddressSystem', 'GeocodeServer'),
            'Roads_AddressSystem_STREET': ('Geolocators/Roads_AddressSystem_STREET', 'GeocodeServer')
        }

        self.secrets = secrets.configuration[config]
        self.configuration = config
        self.output_location = self.secrets['path_to_locators'].replace('\\', '/')

        self.locators = join(self.staging_rack, 'locators.gdb')
        self.sgid = join(self.garage, 'SGID10.sde')
        self.road_grinder = self.secrets['path_to_roadgrinder']

        self.add_crate('AddressPoints', {'source_workspace': self.sgid, 'destination_workspace': self.locators})
        self.add_crates(['AtlNamesAddrPnts', 'AtlNamesRoads', 'GeocodeRoads'], {'source_workspace': self.road_grinder, 'destination_workspace': self.locators})

    def process(self):
        centerline_locators = ['Roads_AddressSystem_STREET']
        address_point_locators = ['AddressPoints_AddressSystem']
        dirty_locators = []

        dirty = set([Crate.CREATED, Crate.UPDATED])
        crates = self.get_crates()

        address_point_results = set([crates[0].result[0], crates[1].result[0]])
        road_results = set([crates[2].result[0], crates[3].result[0]])

        if len(dirty.intersection(address_point_results)) > 0:
            dirty_locators += address_point_locators

        #: roads
        if len(dirty.intersection(road_results)) > 0:
            dirty_locators += centerline_locators

        self.log.info('dirty locators: %s', ','.join(dirty_locators))
        switch = LightSwitch()
        extraSwitch = None
        if self.secrets['username'] or self.secrets['password'] or self.secrets['host']:
            extraSwitch = LightSwitch()
            extraSwitch.set_credentials(username=self.secrets['username'], password=self.secrets['password'], host=self.secrets['host'])

        for locator in dirty_locators:
            #: copy current locator
            rebuild_path = join(self.secrets['path_to_locators'], 'rebuilding')

            self.copy_locator_to(self.secrets['path_to_locators'], locator, rebuild_path)
            locator_path = join(rebuild_path, locator)

            #: rebuild locator
            self.rebuild_locator(locator_path)

            self.log.debug('stopping %s', locator)
            switch.ensure('off', [self.services[locator]])
            if extraSwitch:
                extraSwitch.ensure('off', [self.services[locator]])

            self.copy_locator_to(rebuild_path, locator, self.secrets['path_to_locators'])

            for location in self.secrets['copy_destinations']:
                self.copy_locator_to(rebuild_path, locator, location)

            self.log.debug('starting %s', locator)
            switch.ensure('on', [self.services[locator]])
            if extraSwitch:
                extraSwitch.ensure('on', [self.services[locator]])

            #: delete rebuilding
            try:
                rmtree(rebuild_path)
            except OSError as e:
                self.log.error('error removing temp locator folder: %s', e, exc_info=True)

    def rebuild_locator(self, locator):
        self.log.debug('rebuilding %s', locator)

        #: rebuild in temp location
        arcpy.geocoding.RebuildAddressLocator(locator)

    def copy_locator_to(self, file_path, locator, to_folder):
        location = join(file_path, locator)
        self.log.debug('copying %s to %s', location, to_folder)
        #: iterator glob for .lox .loc .loc.xml
        for filename in iglob(location + '.lo*'):
            base_folder, locator_with_extension = split(filename)

            try:
                mkdir(to_folder)
            except FileExistsError:
                pass

            output = join(to_folder, locator_with_extension)

            copyfile(filename, output)

    def create_locators(self):
        #: address points
        fields = [
            "'Primary Table:Point Address ID' AddressPoints:OBJECTID VISIBLE NONE;'Primary Table:Street ID' <None> VISIBLE NONE;",
            "'*Primary Table:House Number' AddressPoints:AddNum VISIBLE NONE;'Primary Table:Side' <None> VISIBLE NONE;",
            "'Primary Table:Full Street Name' <None> VISIBLE NONE;'Primary Table:Prefix Direction' AddressPoints:PrefixDir VISIBLE NONE;",
            "'Primary Table:Prefix Type' <None> VISIBLE NONE;'*Primary Table:Street Name' AddressPoints:STREETNAME VISIBLE NONE;",
            "'Primary Table:Suffix Type' AddressPoints:STREETTYPE VISIBLE NONE;'Primary Table:Suffix Direction' AddressPoints:SUFFIXDIR VISIBLE NONE;",
            "'Primary Table:City or Place' AddressPoints:AddSystem VISIBLE NONE;'Primary Table:County' <None> VISIBLE NONE;",
            "'Primary Table:State' <None> VISIBLE NONE;'Primary Table:State Abbreviation' <None> VISIBLE NONE;'Primary Table:ZIP Code' <None> VISIBLE NONE;",
            "'Primary Table:Country Code' <None> VISIBLE NONE;'Primary Table:3-Digit Language Code' <None> VISIBLE NONE;",
            "'Primary Table:2-Digit Language Code' <None> VISIBLE NONE;'Primary Table:Admin Language Code' <None> VISIBLE NONE;",
            "'Primary Table:Block ID' <None> VISIBLE NONE;'Primary Table:Street Rank' <None> VISIBLE NONE;'Primary Table:Display X' <None> VISIBLE NONE;",
            "'Primary Table:Display Y' <None> VISIBLE NONE;'Primary Table:Min X value for extent' <None> VISIBLE NONE;",
            "'Primary Table:Max X value for extent' <None> VISIBLE NONE;'Primary Table:Min Y value for extent' <None> VISIBLE NONE;",
            "'Primary Table:Max Y value for extent' <None> VISIBLE NONE;'Primary Table:Additional Field' <None> VISIBLE NONE;",
            "'*Primary Table:Altname JoinID' AddressPoints:UTAddPtID VISIBLE NONE;'Primary Table:City Altname JoinID' <None> VISIBLE NONE;",
            "'*Alternate Name Table:JoinID' AtlNamesAddrPnts:UTAddPtID VISIBLE NONE;'Alternate Name Table:Full Street Name' <None> VISIBLE NONE;",
            "'Alternate Name Table:Prefix Direction' AtlNamesAddrPnts:PrefixDir VISIBLE NONE;'Alternate Name Table:Prefix Type' <None> VISIBLE NONE;",
            "'Alternate Name Table:Street Name' AtlNamesAddrPnts:STREETNAME VISIBLE NONE;",
            "'Alternate Name Table:Suffix Type' AtlNamesAddrPnts:STREETTYPE VISIBLE NONE;",
            "'Alternate Name Table:Suffix Direction' AtlNamesAddrPnts:SUFFIXDIR VISIBLE NONE"
        ]

        start_seconds = clock()
        process_seconds = clock()
        self.log.info('creating the %s locator', 'address point')
        try:
            output_location = join(self.output_location, 'AddressPoints_AddressSystem')
            arcpy.geocoding.CreateAddressLocator(
                in_address_locator_style='US Address - Single House',
                in_reference_data='{0}/{1};{0}/{2}'.format(self.locators, "AtlNamesAddrPnts 'Alternate Name Table'", "AddressPoints 'Primary Table'"),
                in_field_map=''.join(fields),
                out_address_locator=output_location,
                config_keyword='',
                enable_suggestions='DISABLED')

            self.update_locator_properties(output_location, template.us_single_house_addresses)
        except Exception as e:
            self.log.error(e)

        self.log.info('finished %s', format_time(clock() - process_seconds))
        process_seconds = clock()

        #: streets
        fields = [
            "'Primary Table:Feature ID' GeocodeRoads:OBJECTID VISIBLE NONE;'*Primary Table:From Left' GeocodeRoads:FROMADDR_L VISIBLE NONE;",
            "'*Primary Table:To Left' GeocodeRoads:TOADDR_L VISIBLE NONE;'*Primary Table:From Right' GeocodeRoads:FROMADDR_R VISIBLE NONE;",
            "'*Primary Table:To Right' GeocodeRoads:TOADDR_R VISIBLE NONE;'Primary Table:Left Parity' <None> VISIBLE NONE;",
            "'Primary Table:Right Parity' <None> VISIBLE NONE;'Primary Table:Full Street Name' <None> VISIBLE NONE;",
            "'Primary Table:Prefix Direction' GeocodeRoads:PREDIR VISIBLE NONE;'Primary Table:Prefix Type' <None> VISIBLE NONE;",
            "'*Primary Table:Street Name' GeocodeRoads:NAME VISIBLE NONE;'Primary Table:Suffix Type' GeocodeRoads:POSTTYPE VISIBLE NONE;",
            "'Primary Table:Suffix Direction' GeocodeRoads:POSTDIR VISIBLE NONE;", "'Primary Table:Left City or Place' GeocodeRoads:ADDRSYS_L VISIBLE NONE;",
            "'Primary Table:Right City or Place' GeocodeRoads:ADDRSYS_R VISIBLE NONE;'Primary Table:Left County' <None> VISIBLE NONE;",
            "'Primary Table:Right County' <None> VISIBLE NONE;'Primary Table:Left State' <None> VISIBLE NONE;'Primary Table:Right State' <None> VISIBLE NONE;",
            "'Primary Table:Left State Abbreviation' <None> VISIBLE NONE;'Primary Table:Right State Abbreviation' <None> VISIBLE NONE;",
            "'Primary Table:Left ZIP Code' <None> VISIBLE NONE;'Primary Table:Right ZIP Code' <None> VISIBLE NONE;'Primary Table:Country Code' <None> VISIBLE NONE;",
            "'Primary Table:3-Digit Language Code' <None> VISIBLE NONE;'Primary Table:2-Digit Language Code' <None> VISIBLE NONE;",
            "'Primary Table:Admin Language Code' <None> VISIBLE NONE;'Primary Table:Left Block ID' <None> VISIBLE NONE;",
            "'Primary Table:Right Block ID' <None> VISIBLE NONE;'Primary Table:Left Street ID' <None> VISIBLE NONE;",
            "'Primary Table:Right Street ID' <None> VISIBLE NONE;'Primary Table:Street Rank' <None> VISIBLE NONE;",
            "'Primary Table:Min X value for extent' <None> VISIBLE NONE;'Primary Table:Max X value for extent' <None> VISIBLE NONE;",
            "'Primary Table:Min Y value for extent' <None> VISIBLE NONE;'Primary Table:Max Y value for extent' <None> VISIBLE NONE;",
            "'Primary Table:Left Additional Field' <None> VISIBLE NONE;'Primary Table:Right Additional Field' <None> VISIBLE NONE;",
            "'*Primary Table:Altname JoinID' GeocodeRoads:GLOBALID_SGID VISIBLE NONE;'Primary Table:City Altname JoinID' <None> VISIBLE NONE;",
            "'*Alternate Name Table:JoinID' AtlNamesRoads:GLOBALID_SGID VISIBLE NONE;'Alternate Name Table:Full Street Name' <None> VISIBLE NONE;",
            "'Alternate Name Table:Prefix Direction' AtlNamesRoads:PREDIR VISIBLE NONE;'Alternate Name Table:Prefix Type' <None> VISIBLE NONE;",
            "'Alternate Name Table:Street Name' AtlNamesRoads:NAME VISIBLE NONE;'Alternate Name Table:Suffix Type' AtlNamesRoads:POSTTYPE VISIBLE NONE;",
            "'Alternate Name Table:Suffix Direction' AtlNamesRoads:POSTDIR VISIBLE NONE"
        ]

        self.log.info('creating the %s locator', 'streets')
        try:
            output_location = join(self.output_location, 'Roads_AddressSystem_STREET')
            arcpy.geocoding.CreateAddressLocator(
                in_address_locator_style='US Address - Dual Ranges',
                in_reference_data='{0}/{1};{0}/{2}'.format(self.locators, "GeocodeRoads 'Primary Table'", "AtlNamesRoads 'Alternate Name Table'"),
                in_field_map=''.join(fields),
                out_address_locator=output_location,
                config_keyword='',
                enable_suggestions='DISABLED')

            self.update_locator_properties(output_location, template.us_dual_range_addresses)
        except Exception as e:
            self.log.error(e)

        self.log.info('finished %s', format_time(clock() - process_seconds))
        process_seconds = clock()

        self.log.info('finished %s', format_time(clock() - process_seconds))
        self.log.info('done %s', format_time(clock() - start_seconds))

    def update_locator_properties(self, locator_path, options_to_append):
        with open(locator_path + '.loc', 'a') as f:
            f.write(options_to_append)

        self.update_locator_xml(locator_path)

    def update_locator_xml(self, locator_path):
        locator_path += '.loc.xml'

        tree = ElementTree.parse(locator_path)
        root = tree.getroot()

        for data_path in root.findall('./locator/ref_data/data_source/workspace_properties/path'):
            data_path.text = self.locators

        tree.write(locator_path)


if __name__ == '__main__':
    '''
    Usage:
        python LocatorsPallet.py                            Creates lLocators
        python LocatorsPallet.py <locator>                  Rebuilds <locator> as Dev
        python LocatorsPallet.py <locator> <configuration>  Rebuilds <locator> as <configuration>
    Arguments:
        locator         Roads or AddressPoints
        configuration   Dev Staging Production
    '''
    import logging

    pallet = LocatorsPallet()
    logging.basicConfig(format='%(levelname)s %(asctime)s %(lineno)s %(message)s', datefmt='%H:%M:%S', level=logging.INFO)
    pallet.log = logging

    params = len(sys.argv)
    if params == 1:
        pallet.build('Dev')
        logging.info('creating locators')
        pallet.create_locators()
    elif params == 2:
        what = sys.argv[1]

        pallet.build('Dev')

        if what == 'Roads':
            index = 2
            logging.info('dirtying roads')
        elif what == 'AddressPoints':
            index = 0
            logging.info('dirtying address points')
        else:
            index = 2
            pallet.get_crates()[0].result = (Crate.UPDATED, None)

        pallet.get_crates()[index].result = (Crate.UPDATED, None)

        logging.info('processing')
        pallet.process()
    elif params == 3:
        what = sys.argv[1]
        configuration = sys.argv[2]

        pallet.build(configuration)

        logging.info('acting as %s', configuration)
        if what == 'Roads':
            index = 2
            logging.info('dirtying roads')
        elif what == 'AddressPoints':
            index = 0
            logging.info('dirtying address points')
        else:
            index = 2
            pallet.get_crates()[0].result = (Crate.UPDATED, None)

        pallet.get_crates()[index].result = (Crate.UPDATED, None)

        logging.info('processing')
        pallet.process()
