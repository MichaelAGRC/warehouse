'''
OGMPallet.py

Update SGID data from the DOGM database.
'''

from os.path import basename, join

import arcpy
import sgid_secrets as secrets
from forklift.models import Pallet

#: field names
CoordsSurf_E = 'CoordsSurf_E'
CoordsSurf_N = 'CoordsSurf_N'
CoordsBH_E = 'CoordsBH_E'
CoordsBH_N = 'CoordsBH_N'
API = 'API'
ConstructNumber = 'ConstructNumber'
UTMZone = 'UTMZone'
Jurisdiction = 'Jurisdiction'

UTM12 = arcpy.SpatialReference(26912)
UTM11 = arcpy.SpatialReference(26911)

jurisdiction_layer = 'jurisdiction_layer'


class OGMPallet(Pallet):
    def build(self, configuration):
        self.configuration = configuration

    def prepare_packaging(self):
        sgid = join(self.garage, 'SGID10_Energy.sde')
        self.sgid = sgid
        dogm = join(self.garage, 'UTRBDMSNET.sde')
        surface_dogm = join(dogm, 'UTRBDMSNET.dbo.viewAGRC_WellData_Surf')
        downhole_dogm = join(dogm, 'UTRBDMSNET.dbo.viewAGRC_WellData_DownHole')
        surface_sgid = join(sgid, 'SGID10.ENERGY.OilGasWells')
        downhole_sgid = join(sgid, 'SGID10.ENERGY.OilGasWells_DownHoles')
        paths_sgid = join(sgid, 'SGID10.ENERGY.OilGasWells_Paths')
        surface_scratch = join(arcpy.env.scratchGDB, basename(surface_sgid).split('.')[-1])
        downhole_scratch = join(arcpy.env.scratchGDB, basename(downhole_sgid).split('.')[-1])
        paths_scratch = join(arcpy.env.scratchGDB, basename(paths_sgid).split('.')[-1])

        if self.configuration == 'Dev':
            #: must be in UTM
            indian_country = r'C:\MapData\deqreferencedata.gdb\Total_IC_and_ReservationTribalLand'
        else:
            indian_country = (r'\\' + secrets.DEQSERVER +
                              '\gis\AQGIS\GISSHARED\GISData\Total IC and Reservation_TribalLand\Total_IC_and_ReservationTribalLand.shp')

        self.log.info('ensuring that temp data is created')
        for create_fc in [surface_scratch, downhole_scratch, paths_scratch]:
            if not arcpy.Exists(create_fc):
                self.log.info('creating: %s', create_fc)
                name = basename(create_fc)
                template = join(sgid, 'SGID10.ENERGY.{}'.format(name))
                arcpy.management.CreateFeatureclass(arcpy.env.scratchGDB, name, template=template)
            else:
                self.log.info('truncating: %s', create_fc)
                arcpy.management.TruncateTable(create_fc)

        downhole_points = {}
        surface_points = {}

        def extract_points(source, destination, x_field, y_field):
            fields = [f.name for f in arcpy.Describe(source).fields]
            x_index = fields.index(x_field)
            y_index = fields.index(y_field)
            zone_index = fields.index(UTMZone)
            api_index = fields.index(API)
            try:
                construct_index = fields.index(ConstructNumber)
            except ValueError:
                #: this field isn't present in the surface points
                construct_index = None
            query = '{} IS NOT NULL AND {} IS NOT NULL'.format(x_field, y_field)
            with arcpy.da.SearchCursor(source, fields, query) as search_cursor, \
                    arcpy.da.InsertCursor(destination, fields + ['SHAPE@XY']) as insert_cursor:
                for row in search_cursor:
                    x = row[x_index]
                    y = row[y_index]
                    if x is not None and y is not None:
                        if row[zone_index] == 11:
                            zone_11_point = arcpy.PointGeometry(arcpy.Point(x, y), UTM11)
                            projected_point = zone_11_point.projectAs(UTM12)
                            point = (projected_point.x, projected_point.y)
                        else:
                            point = (x, y)

                        if construct_index is None:
                            surface_points[row[api_index]] = point
                        else:
                            construct = row[construct_index]
                            downhole_points.setdefault(row[api_index], {}).setdefault(construct, []).append(point)
                    else:
                        point = None

                    insert_cursor.insertRow(row + (point,))

        self.log.info('extracting surface points to scratch')
        extract_points(surface_dogm, surface_scratch, CoordsSurf_E, CoordsSurf_N)

        self.log.info('extracting down hole points to scratch')
        extract_points(downhole_dogm, downhole_scratch, CoordsBH_E, CoordsBH_N)

        self.log.info('building paths in scratch')
        with arcpy.da.InsertCursor(paths_scratch, [API, ConstructNumber, 'SHAPE@']) as paths_cursor:
            for api in downhole_points:
                for construct in downhole_points[api]:
                    points = [surface_points[api]] + downhole_points[api][construct]

                    #: remove duplicates while preserving order so that lines go from surface to downholes
                    unique_points = []
                    [unique_points.append(point) for point in points if point not in unique_points]

                    if len(unique_points) > 1:
                        line = arcpy.Polyline(arcpy.Array([arcpy.Point(*coords) for coords in points]), UTM12)
                        paths_cursor.insertRow((api, construct, line))

        self.log.info('updating Jurisdiction field in surface points')
        arcpy.management.MakeFeatureLayer(surface_scratch, jurisdiction_layer)
        arcpy.management.CalculateField(jurisdiction_layer, Jurisdiction, '"state"', 'PYTHON')
        arcpy.management.SelectLayerByLocation(jurisdiction_layer, 'INTERSECT', indian_country)
        arcpy.management.CalculateField(jurisdiction_layer, Jurisdiction, '"indian"', 'PYTHON')

        self.log.info('updating SGID from scratch data')
        for source, destination in [(surface_scratch, surface_sgid), (downhole_scratch, downhole_sgid), (paths_scratch, paths_sgid)]:
            arcpy.management.DeleteRows(destination)
            arcpy.management.Append(source, destination)


if __name__ == '__main__':
    import logging

    pallet = OGMPallet()
    logging.basicConfig(
        format='%(levelname)s %(asctime)s %(lineno)s %(message)s',
        datefmt='%H:%M:%S',
        level=logging.INFO
    )
    pallet.log = logging
    pallet.build('Dev')
    pallet.prepare_packaging()
