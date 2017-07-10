'''
SGID10MercatorPallet.py
A module that contains a pallet definition for the data that gets pushed to AGOL.
'''

import arcpy
from forklift.models import Pallet, Crate
from os.path import join
import sgid_secrets as secrets
from arcgis.gis import GIS


project_folder = r'\\{}\AGRCBackup\AGRC Projects\AGOL\SGID10Mercator'.format(secrets.HNAS)
SGID10MercatorGDB = join(project_folder, 'SGID10Mercator.gdb')
AGOL_Layers_Project = join(project_folder, 'AGOL_Layers.aprx')
drafts_folder = join(project_folder, 'sddrafts')


class SGID10Mercator(Pallet):

    def build(self, config):
        sgid = join(self.garage, 'SGID10.sde')

        self.log.info('getting layers from pro project')
        agol_map = arcpy.mp.ArcGISProject(AGOL_Layers_Project).listMaps('AGOL')[0]
        layers = agol_map.listLayers()

        self.layer_lookup = {}
        for layer in layers:
            self.layer_lookup[layer.name] = layer

        self.add_crates([layer.name for layer in layers], {'source_workspace': sgid, 'destination_workspace': SGID10MercatorGDB})

    def process(self):
        updated_crates = [crate for crate in self.get_crates() if crate.result[0] in [Crate.CREATED, Crate.UPDATED]]
        if len(updated_crates) > 0:
            gis = GIS('http://utah.maps.arcgis.com', secrets.AGOL_USER, secrets.AGOL_PASSWORD)

        for crate in updated_crates:
            name = crate.destination_name
            draft = join(drafts_folder, name + '.sddraft')
            sd = join(drafts_folder, name + '.sd')

            self.log.info('updating %s service in AGOL', name)
            original_setting = arcpy.env.overwriteOutput
            arcpy.env.overwriteOutput = True
            arcpy.mp.CreateWebLayerSDDraft(self.layer_lookup[name], draft, name, overwrite_existing_service=True, copy_data_to_server=True)
            arcpy.server.StageService(draft, sd)
            arcpy.server.UploadServiceDefinition(sd, 'My Hosted Services', in_override='USE_DEFINITION', in_public='PUBLIC')
            arcpy.env.overwriteOutput = original_setting

            #: update sharing because for some reason in_public isn't working
            item = gis.content.search(name, item_type='Feature Service')[0]
            item.share(True)
