'''
AGOLPallet.py
A module that contains a pallet definition for the data that gets pushed to AGOL.
'''

from datetime import timedelta
from os.path import basename, join
from time import time

import arcpy
import sgid_secrets as secrets
from arcgis.gis import GIS
from forklift import core
from forklift.models import Crate, Pallet

project_folder = r'\\{}\AGRCBackup\AGRC Projects\AGOL\SGID10Mercator'.format(secrets.HNAS)
SGID10MercatorGDB = join(project_folder, 'SGID10Mercator.gdb')
ThumbnailExtents = join(project_folder, 'AGOL_Layers.gdb', 'ThumbnailExtents')
AGOL_Layers_Project = join(project_folder, 'AGOL_Layers.aprx')
# AGOL_Layers_Project = join(project_folder, 'AGOL_Layers_TEST.aprx')
drafts_folder = join(project_folder, 'sddrafts')


class AGOLPallet(Pallet):

    def build(self, config):
        sgid = join(self.garage, 'SGID10.sde')

        self.log.info('getting layers from pro project')
        self.pro_project = arcpy.mp.ArcGISProject(AGOL_Layers_Project)
        self.agol_map = self.pro_project.listMaps('AGOL')[0]

        self.layer_lookup = {}
        for layer in self.agol_map.listLayers():
            self.layer_lookup[basename(layer.dataSource)] = layer

        self.add_crates(list(self.layer_lookup.keys()), {'source_workspace': sgid, 'destination_workspace': SGID10MercatorGDB})

        self.log.info('validating that destination feature classes have FORKLIFT_HASH field')
        for crate in self.get_crates():
            if core.hash_field not in [field.name for field in arcpy.Describe(crate.destination).fields]:
                self.log.info('truncating data and adding missing {} field to {}'.format(core.hash_field, crate.destination_name))
                arcpy.management.TruncateTable(crate.destination)
                arcpy.management.AddField(crate.destination, core.hash_field, 'TEXT', field_length=core.hash_field_length)

    def process(self):
        updated_crates = [crate for crate in self.get_crates() if crate.result[0] in [Crate.CREATED, Crate.UPDATED]]

        if len(updated_crates) == 0:
            return

        gis = GIS('http://utah.maps.arcgis.com', secrets.AGOL_USER, secrets.AGOL_PASSWORD)

        for crate in updated_crates:
            layer = self.layer_lookup[crate.destination_name]

            self.toggle_layers(layer)

            with arcpy.da.SearchCursor(ThumbnailExtents, ['SHAPE@'], 'LAYER_NAME = \'{}\''.format(layer.name)) as scursor:
                for shape, in scursor:
                    self.agol_map.defaultCamera.setExtent(shape.extent)

            self.pro_project.save()

            feature_class_name = basename(layer.dataSource)
            draft = join(drafts_folder, feature_class_name + '.sddraft')
            sd = join(drafts_folder, feature_class_name + '.sd')

            self.log.info('updating %s service in AGOL', layer.name)
            original_setting = arcpy.env.overwriteOutput
            arcpy.env.overwriteOutput = True
            arcpy.mp.CreateWebLayerSDDraft(layer, draft, layer.name, overwrite_existing_service=True, copy_data_to_server=True)
            arcpy.server.StageService(draft, sd)
            arcpy.server.UploadServiceDefinition(sd, 'My Hosted Services', in_override='USE_DEFINITION', in_public='PUBLIC')
            arcpy.env.overwriteOutput = original_setting

            #: update sharing because for some reason in_public isn't working
            for item in gis.content.search(layer.name, item_type='Feature Layer', sort_field='modified', sort_order='desc'):
                if item.title == layer.name:
                    share_item = item

                    #: check to see if a brand new service was created
                    if item.created/1000 > time() - timedelta(minutes=5).total_seconds():
                        crate.result = (Crate.ERROR, 'New service created! Please notify Michael so that he can sort it out.')

                    break
            share_item.share(True)

    def toggle_layers(self, show_layer):
        #: turn off all layers other than the passed in layer
        for layer in self.agol_map.listLayers():
            if layer.name != show_layer.name:
                layer.visible = False
        show_layer.visible = True
