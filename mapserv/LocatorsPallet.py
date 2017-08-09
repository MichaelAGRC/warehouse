#!/usr/bin/env python
# * coding: utf8 *
'''
LocatorPallet.py
A module that contains a pallet definition for data to support the mapserv roads locator services
'''

import arcpy
import locatorsupport.locator_templates
import locatorsupport.secrets
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


class LocatorPallet(Pallet):

    def build(self, config='prod'):
        self.secrets = secrets.configuration[config]
        self.configuration = config
        self.output_location = self.secrets['path_to_locators'].replace('\\', '/')

        self.sgid = join(self.garage, 'SGID10.sde')
        self.locators = join(self.staging_rack, 'locators.gdb')
        #: not to be confused with arcgis_services
        #: this pallet handles the stopping and starting outside of the forklift routine
        self.services = {'Roads_AddressSystem_ACSALIAS': ('Geolocators/Roads_AddressSystem_ACSALIAS', 'GeocodeServer'),
                         'Roads_AddressSystem_ALIAS1': ('Geolocators/Roads_AddressSystem_ALIAS1', 'GeocodeServer'),
                         'Roads_AddressSystem_ALIAS2': ('Geolocators/Roads_AddressSystem_ALIAS2', 'GeocodeServer'),
                         'Roads_AddressSystem_STREET': ('Geolocators/Roads_AddressSystem_STREET', 'GeocodeServer')}

        self.add_crates(['Roads', 'AddressPoints'],
                        {'source_workspace': self.sgid,
                         'destination_workspace': self.locators})

    def process(self):
        centerline_locators = [
            'Roads_AddressSystem_ACSALIAS', 'Roads_AddressSystem_ALIAS1',
            'Roads_AddressSystem_ALIAS2', 'Roads_AddressSystem_STREET'
        ]
        address_point_locators = ['AddressPoints_AddressSystem']
        dirty_locators = []

        #: roads
        if self.get_crates()[0].result[0] in [Crate.CREATED, Crate.UPDATED]:
            dirty_locators += centerline_locators

        #: address points
        if self.get_crates()[1].result[0] in [Crate.CREATED, Crate.UPDATED]:
            dirty_locators += address_point_locators

        if self.configuration == 'test':
            dirty_locators = ['Roads_AddressSystem_ALIAS1']

        self.log.info('dirty locators: %s', ','.join(dirty_locators))
        switch = LightSwitch()
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
            extraSwitch.ensure('off', [self.services[locator]])

            self.copy_locator_to(rebuild_path, locator, self.secrets['path_to_locators'])

            for location in self.secrets['copy_destinations']:
                self.copy_locator_to(rebuild_path, locator, location)

            self.log.debug('starting %s', locator)
            switch.ensure('on', [self.services[locator]])
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
        self.log.debug('copying %s to %s', location, to_folder) #: iterator glob for .lox .loc .loc.xml
        for filename in iglob(location + '.lo*'):
            base_folder, locator_with_extension = split(filename)

            try:
                mkdir(to_folder)
            except FileExistsError:
                pass

            output = join(to_folder, locator_with_extension)

            copyfile(filename, output)

    def create_locators(self):
        #: streets
        fields = [
            "'Feature ID' OBJECTID VISIBLE NONE;'*From Left' L_F_ADD VISIBLE NONE;",
            "'*To Left' L_T_ADD VISIBLE NONE;'*From Right' R_F_ADD VISIBLE NONE;",
            "'*To Right' R_T_ADD VISIBLE NONE;'Left Parity' <None> VISIBLE NONE;",
            "'Right Parity' <None> VISIBLE NONE;'Full Street Name' <None> VISIBLE NONE;",
            "'Prefix Direction' PREDIR VISIBLE NONE;'Prefix Type' <None> VISIBLE NONE;",
            "'*Street Name' STREETNAME VISIBLE NONE;'Suffix Type' STREETTYPE VISIBLE NONE;",
            "'Suffix Direction' SUFDIR VISIBLE NONE;'Left City or Place' ADDR_SYS VISIBLE NONE;",
            "'Right City or Place' ADDR_SYS VISIBLE NONE;'Left County' <None> VISIBLE NONE;",
            "'Right County' <None> VISIBLE NONE;'Left State' <None> VISIBLE NONE;",
            "'Right State' <None> VISIBLE NONE;'Left State Abbreviation' <None> VISIBLE NONE;",
            "'Right State Abbreviation' <None> VISIBLE NONE;'Left ZIP Code' <None> VISIBLE NONE;",
            "'Right ZIP Code' <None> VISIBLE NONE;'Country Code' <None> VISIBLE NONE;",
            "'3-Digit Language Code' <None> VISIBLE NONE;'2-Digit Language Code' <None> VISIBLE NONE;",
            "'Admin Language Code' <None> VISIBLE NONE;'Left Block ID' <None> VISIBLE NONE;",
            "'Right Block ID' <None> VISIBLE NONE;'Left Street ID' <None> VISIBLE NONE;",
            "'Right Street ID' <None> VISIBLE NONE;'Street Rank' <None> VISIBLE NONE;",
            "'Min X value for extent' <None> VISIBLE NONE;'Max X value for extent' <None> VISIBLE NONE;",
            "'Min Y value for extent' <None> VISIBLE NONE;'Max Y value for extent' <None> VISIBLE NONE;",
            "'Left Additional Field' <None> VISIBLE NONE;'Right Additional Field' <None> VISIBLE NONE;",
            "'Altname JoinID' <None> VISIBLE NONE;'City Altname JoinID' <None> VISIBLE NONE"
        ]

        start_seconds = clock()
        process_seconds = clock()
        print('creating the {} locator'.format('streets')) try:
            output_location = join(self.output_location, 'Roads_AddressSystem_STREET')
            arcpy.geocoding.CreateAddressLocator(
                in_address_locator_style='US Address - Dual Ranges',
                in_reference_data=join(self.locators, "Roads 'Primary Table'"),
                in_field_map=''.join(fields),
                out_address_locator=output_location,
                config_keyword='',
                enable_suggestions='DISABLED')

            self.update_locator_properties(output_location, locator_templates.us_dual_range_addresses)
        except Exception as e:
            print(e)

        print('finished {}'.format(format_time(clock() - process_seconds)))
        process_seconds = clock()

        #: acs alias
        fields = [
            "'Feature ID' OBJECTID VISIBLE NONE;'*From Left' L_F_ADD VISIBLE NONE;",
            "'*To Left' L_T_ADD VISIBLE NONE;'*From Right' R_F_ADD VISIBLE NONE;",
            "'*To Right' R_T_ADD VISIBLE NONE;'Left Parity' <None> VISIBLE NONE;",
            "'Right Parity' <None> VISIBLE NONE;'Full Street Name' <None> VISIBLE NONE;",
            "'Prefix Direction' PREDIR VISIBLE NONE;'Prefix Type' <None> VISIBLE NONE;",
            "'*Street Name' ACSNAME VISIBLE NONE;'Suffix Type' <None> VISIBLE NONE;",
            "'Suffix Direction' ACSSUF VISIBLE NONE;'Left City or Place' ADDR_SYS VISIBLE NONE;",
            "'Right City or Place' ADDR_SYS VISIBLE NONE;'Left County' <None> VISIBLE NONE;",
            "'Right County' <None> VISIBLE NONE;'Left State' <None> VISIBLE NONE;",
            "'Right State' <None> VISIBLE NONE;'Left State Abbreviation' <None> VISIBLE NONE;",
            "'Right State Abbreviation' <None> VISIBLE NONE;'Left ZIP Code' <None> VISIBLE NONE;",
            "'Right ZIP Code' <None> VISIBLE NONE;'Country Code' <None> VISIBLE NONE;",
            "'3-Digit Language Code' <None> VISIBLE NONE;'2-Digit Language Code' <None> VISIBLE NONE;",
            "'Admin Language Code' <None> VISIBLE NONE;'Left Block ID' <None> VISIBLE NONE;",
            "'Right Block ID' <None> VISIBLE NONE;'Left Street ID' <None> VISIBLE NONE;",
            "'Right Street ID' <None> VISIBLE NONE;'Street Rank' <None> VISIBLE NONE;",
            "'Min X value for extent' <None> VISIBLE NONE;'Max X value for extent' <None> VISIBLE NONE;",
            "'Min Y value for extent' <None> VISIBLE NONE;'Max Y value for extent' <None> VISIBLE NONE;",
            "'Left Additional Field' <None> VISIBLE NONE;'Right Additional Field' <None> VISIBLE NONE;",
            "'Altname JoinID' <None> VISIBLE NONE;'City Altname JoinID' <None> VISIBLE NONE"
        ]

        print('creating the {} locator'.format('acs alias'))
        try:
            output_location = join(self.output_location, 'Roads_AddressSystem_ACSALIAS')
            arcpy.geocoding.CreateAddressLocator(
                in_address_locator_style='US Address - Dual Ranges',
                in_reference_data=join(self.locators, "Roads 'Primary Table'"),
                in_field_map=''.join(fields),
                out_address_locator=output_location,
                config_keyword='',
                enable_suggestions='DISABLED')

            self.update_locator_properties(output_location, locator_templates.us_dual_range_addresses)
        except Exception as e:
            print(e)

        print('finished {}'.format(format_time(clock() - process_seconds)))
        process_seconds = clock()

        #: alias1
        fields = [
            "'Feature ID' OBJECTID VISIBLE NONE;'*From Left' L_F_ADD VISIBLE NONE;",
            "'*To Left' L_T_ADD VISIBLE NONE;'*From Right' R_F_ADD VISIBLE NONE;",
            "'*To Right' R_T_ADD VISIBLE NONE;'Left Parity' <None> VISIBLE NONE;",
            "'Right Parity' <None> VISIBLE NONE;'Full Street Name' <None> VISIBLE NONE;",
            "'Prefix Direction' PREDIR VISIBLE NONE;'Prefix Type' <None> VISIBLE NONE;",
            "'*Street Name' ALIAS1 VISIBLE NONE;'Suffix Type' ALIAS1TYPE VISIBLE NONE;",
            "'Suffix Direction' SUFDIR VISIBLE NONE;'Left City or Place' ADDR_SYS VISIBLE NONE;",
            "'Right City or Place' ADDR_SYS VISIBLE NONE;'Left County' <None> VISIBLE NONE;",
            "'Right County' <None> VISIBLE NONE;'Left State' <None> VISIBLE NONE;",
            "'Right State' <None> VISIBLE NONE;'Left State Abbreviation' <None> VISIBLE NONE;",
            "'Right State Abbreviation' <None> VISIBLE NONE;'Left ZIP Code' <None> VISIBLE NONE;",
            "'Right ZIP Code' <None> VISIBLE NONE;'Country Code' <None> VISIBLE NONE;",
            "'3-Digit Language Code' <None> VISIBLE NONE;'2-Digit Language Code' <None> VISIBLE NONE;",
            "'Admin Language Code' <None> VISIBLE NONE;'Left Block ID' <None> VISIBLE NONE;",
            "'Right Block ID' <None> VISIBLE NONE;'Left Street ID' <None> VISIBLE NONE;",
            "'Right Street ID' <None> VISIBLE NONE;'Street Rank' <None> VISIBLE NONE;",
            "'Min X value for extent' <None> VISIBLE NONE;'Max X value for extent' <None> VISIBLE NONE;",
            "'Min Y value for extent' <None> VISIBLE NONE;'Max Y value for extent' <None> VISIBLE NONE;",
            "'Left Additional Field' <None> VISIBLE NONE;'Right Additional Field' <None> VISIBLE NONE;",
            "'Altname JoinID' <None> VISIBLE NONE;'City Altname JoinID' <None> VISIBLE NONE"
        ]

        print('creating the {} locator'.format('alias1'))
        try:
            output_location = join(self.output_location, 'Roads_AddressSystem_ALIAS1')
            arcpy.geocoding.CreateAddressLocator(
                in_address_locator_style='US Address - Dual Ranges',
                in_reference_data=join(self.locators, "Roads 'Primary Table'"),
                in_field_map=''.join(fields),
                out_address_locator=output_location,
                config_keyword='',
                enable_suggestions='DISABLED')

            self.update_locator_properties(output_location, locator_templates.us_dual_range_addresses)
        except Exception as e:
            print(e)

        print('finished {}'.format(format_time(clock() - process_seconds)))
        process_seconds = clock()

        #: alias2
        fields = [
            "'Feature ID' OBJECTID VISIBLE NONE;'*From Left' L_F_ADD VISIBLE NONE;",
            "'*To Left' L_T_ADD VISIBLE NONE;'*From Right' R_F_ADD VISIBLE NONE;",
            "'*To Right' R_T_ADD VISIBLE NONE;'Left Parity' <None> VISIBLE NONE;",
            "'Right Parity' <None> VISIBLE NONE;'Full Street Name' <None> VISIBLE NONE;",
            "'Prefix Direction' PREDIR VISIBLE NONE;'Prefix Type' <None> VISIBLE NONE;",
            "'*Street Name' ALIAS2 VISIBLE NONE;'Suffix Type' ALIAS2TYPE VISIBLE NONE;",
            "'Suffix Direction' SUFDIR VISIBLE NONE;'Left City or Place' ADDR_SYS VISIBLE NONE;",
            "'Right City or Place' ADDR_SYS VISIBLE NONE;'Left County' <None> VISIBLE NONE;",
            "'Right County' <None> VISIBLE NONE;'Left State' <None> VISIBLE NONE;",
            "'Right State' <None> VISIBLE NONE;'Left State Abbreviation' <None> VISIBLE NONE;",
            "'Right State Abbreviation' <None> VISIBLE NONE;'Left ZIP Code' <None> VISIBLE NONE;",
            "'Right ZIP Code' <None> VISIBLE NONE;'Country Code' <None> VISIBLE NONE;",
            "'3-Digit Language Code' <None> VISIBLE NONE;'2-Digit Language Code' <None> VISIBLE NONE;",
            "'Admin Language Code' <None> VISIBLE NONE;'Left Block ID' <None> VISIBLE NONE;",
            "'Right Block ID' <None> VISIBLE NONE;'Left Street ID' <None> VISIBLE NONE;",
            "'Right Street ID' <None> VISIBLE NONE;'Street Rank' <None> VISIBLE NONE;",
            "'Min X value for extent' <None> VISIBLE NONE;'Max X value for extent' <None> VISIBLE NONE;",
            "'Min Y value for extent' <None> VISIBLE NONE;'Max Y value for extent' <None> VISIBLE NONE;",
            "'Left Additional Field' <None> VISIBLE NONE;'Right Additional Field' <None> VISIBLE NONE;",
            "'Altname JoinID' <None> VISIBLE NONE;'City Altname JoinID' <None> VISIBLE NONE"
        ]

        print('creating the {} locator'.format('alias2'))
        try:
            output_location = join(self.output_location, 'Roads_AddressSystem_ALIAS2')
            arcpy.geocoding.CreateAddressLocator(
                in_address_locator_style='US Address - Dual Ranges',
                in_reference_data=join(self.locators, "Roads 'Primary Table'"),
                in_field_map=''.join(fields),
                out_address_locator=output_location,
                config_keyword='',
                enable_suggestions='DISABLED')

            self.update_locator_properties(output_location, locator_templates.us_dual_range_addresses)
        except Exception as e:
            print(e)

        print('finished {}'.format(format_time(clock() - process_seconds)))
        process_seconds = clock()

        fields = [
            "'Point Address ID' OBJECTID VISIBLE NONE;'Street ID' <None> VISIBLE NONE;",
            "'*House Number' AddNum VISIBLE NONE;Side <None> VISIBLE NONE;'Full Street Name' <None> VISIBLE NONE;",
            "'Prefix Direction' <None> VISIBLE NONE;'Prefix Type' <None> VISIBLE NONE;",
            "'*Street Name' StreetName VISIBLE NONE;'Suffix Type' StreetType VISIBLE NONE;",
            "'Suffix Direction' SuffixDir VISIBLE NONE;'City or Place' AddSystem VISIBLE NONE;",
            "County <None> VISIBLE NONE;State <None> VISIBLE NONE;'State Abbreviation' <None> VISIBLE NONE;",
            "'ZIP Code' <None> VISIBLE NONE;'Country Code' <None> VISIBLE NONE;",
            "'3-Digit Language Code' <None> VISIBLE NONE;'2-Digit Language Code' <None> VISIBLE NONE;",
            "'Admin Language Code' <None> VISIBLE NONE;'Block ID' <None> VISIBLE NONE;",
            "'Street Rank' <None> VISIBLE NONE;'Display X' <None> VISIBLE NONE;",
            "'Display Y' <None> VISIBLE NONE;'Min X value for extent' <None> VISIBLE NONE;",
            "'Max X value for extent' <None> VISIBLE NONE;'Min Y value for extent' <None> VISIBLE NONE;",
            "'Max Y value for extent' <None> VISIBLE NONE;'Additional Field' <None> VISIBLE NONE;",
            "'Altname JoinID' <None> VISIBLE NONE;'City Altname JoinID' <None> VISIBLE NONE"
        ]

        print('creating the {} locator'.format('address points'))
        try:
            output_location = join(self.output_location, 'AddressPoints_AddressSystem')
            arcpy.geocoding.CreateAddressLocator(
                in_address_locator_style='US Address - Single House',
                in_reference_data=join(self.locators, "AddressPoints 'Primary Table'"),
                in_field_map=''.join(fields),
                out_address_locator=output_location,
                config_keyword='',
                enable_suggestions='DISABLED')

            self.update_locator_properties(output_location, locator_templates.us_single_house_addresses)
        except Exception as e:
            print(e)

        print('finished {}'.format(format_time(clock() - process_seconds)))
        print('done {}'.format(format_time(clock() - start_seconds)))

    def update_locator_properties(self, locator_path, options_to_append):
        with open(locator_path + '.loc', 'a') as f:
            f.write(options_to_append)
