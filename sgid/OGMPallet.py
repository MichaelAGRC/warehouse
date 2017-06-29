'''
OGMPallet.py

Update SGID data from the DOGM database.
'''

import arcpy
from forklift.models import Pallet
from os.path import join, basename, normpath, isdir
from os import walk, makedirs, sep
from shutil import rmtree
import sgid_secrets as secrets
import zipfile


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

    def ship(self):
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

        paths = {}

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
            with arcpy.da.SearchCursor(source, fields) as search_cursor, \
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
                            construct = 0
                        else:
                            construct = row[construct_index]
                        paths.setdefault(row[api_index], {}).setdefault(construct, []).append(point)
                    else:
                        point = None

                    insert_cursor.insertRow(row + (point,))

        self.log.info('extracting surface points to scratch')
        extract_points(surface_dogm, surface_scratch, CoordsSurf_E, CoordsSurf_N)

        self.log.info('extracting down hole points to scratch')
        extract_points(downhole_dogm, downhole_scratch, CoordsBH_E, CoordsBH_N)

        self.log.info('building paths in scratch')
        with arcpy.da.InsertCursor(paths_scratch, [API, ConstructNumber, 'SHAPE@']) as paths_cursor:
            for api in paths:
                for construct in paths[api]:
                    points = paths[api][construct]
                    if len(points) > 1:
                        line = arcpy.Polyline(arcpy.Array([arcpy.Point(*coords) for coords in points]), UTM12)
                        paths_cursor.insertRow((api, construct, line))

        self.log.info('updating Jurisdiction field in surface points')
        arcpy.management.MakeFeatureLayer(surface_scratch, jurisdiction_layer)
        arcpy.management.CalculateField(jurisdiction_layer, Jurisdiction, '"state"', 'PYTHON')
        arcpy.management.SelectLayerByLocation(jurisdiction_layer, 'INTERSECT', indian_country)
        print(arcpy.management.GetCount(jurisdiction_layer))
        arcpy.management.CalculateField(jurisdiction_layer, Jurisdiction, '"indian"', 'PYTHON')

        self.log.info('updating SGID from scratch data')
        for source, destination in [(surface_scratch, surface_sgid), (downhole_scratch, downhole_sgid), (paths_scratch, paths_sgid)]:
            arcpy.management.DeleteRows(destination)
            arcpy.management.Append(source, destination)

        if (self.configuration == 'Production'):
            self.update_ftp_package()

    def update_ftp_package(self):
        self.log.info('updating ftp package')
        name = 'DOGMOilAndGasResources'
        packageFolderPath = r'\\' + secrets.HNAS + r'\ftp\UtahSGID_Vector\UTM12_NAD83\ENERGY\PackagedData\_Statewide\\' + name
        unpackagedFolderPath = r'\\' + secrets.HNAS + r'\ftp\UtahSGID_Vector\UTM12_NAD83\ENERGY\UnpackagedData\\'
        featureClasses = ["SGID10.ENERGY.DNROilGasFields",
                          "SGID10.ENERGY.DNROilGasUnits",
                          "SGID10.ENERGY.OilGasWells",
                          "SGID10.ENERGY.OilGasWells_DownHoles",
                          "SGID10.ENERGY.OilGasWells_Paths"]
        if arcpy.Exists(join(packageFolderPath, name + ".gdb")):
            arcpy.Delete_management(join(packageFolderPath, name + ".gdb"))
        arcpy.CreateFileGDB_management(packageFolderPath, name + ".gdb", "9.3")

        def zipws(pth, zip, keep):
            pth = normpath(pth)

            for (dirpath, dirnames, filenames) in walk(pth):
                for file in filenames:
                    if not file.endswith('.lock'):
                        try:
                            if keep:
                                if join(dirpath, file).find('.zip') == -1:
                                    zip.write(join(dirpath, file), join(basename(pth), join(dirpath, file)[len(pth) + len(sep):]))
                            else:
                                if join(dirpath, file).find('gdb') == -1 and join(dirpath, file).find('.zip') == -1:
                                    zip.write(join(dirpath, file), file.split(".")[0] + '\\' + file)
                        except Exception as e:
                            self.log.error("Error adding %s: %s" % (file, e))
            return None

        #: populate local file geodatabase
        for fc in featureClasses:
            arcpy.env.workspace = self.sgid
            if arcpy.Exists(join(self.sgid, fc)):
                #: add feature class to local file geodatabase to be packaged later
                arcpy.Copy_management(join(self.sgid, fc), join(packageFolderPath, name + ".gdb", fc))

                #: create another file gdb and copy to Unpackaged folder
                fcUnpackagedFolderPath = join(unpackagedFolderPath, fc.split(".")[2], '_Statewide')

                if not isdir(fcUnpackagedFolderPath):
                    makedirs(fcUnpackagedFolderPath)

                arcpy.CreateFileGDB_management(fcUnpackagedFolderPath, fc.split(".")[2] + ".gdb")
                arcpy.Copy_management(join(packageFolderPath, name + ".gdb", fc.split(".")[2]),
                                      join(fcUnpackagedFolderPath, fc.split(".")[2] + ".gdb", fc.split(".")[2]))

                zfGDBUnpackaged = zipfile.ZipFile(join(fcUnpackagedFolderPath, fc.split(".")[2] + '_gdb.zip'), 'w', zipfile.ZIP_DEFLATED)
                zipws(join(fcUnpackagedFolderPath, fc.split(".")[2] + ".gdb"), zfGDBUnpackaged, True)
                zfGDBUnpackaged.close()

                arcpy.Delete_management(join(fcUnpackagedFolderPath, fc.split(".")[2] + '.gdb'))

        arcpy.env.workspace = join(packageFolderPath, name + ".gdb")

        #: create zip file for shapefile package
        zfSHP = zipfile.ZipFile(join(packageFolderPath, name + '_shp.zip'), 'w', zipfile.ZIP_DEFLATED)
        arcpy.env.overwriteOutput = True  #: Overwrite pre-existing files

        #: output zipped shapefiles for each feature class
        fileGDB_FCs = arcpy.ListFeatureClasses()

        for fc in fileGDB_FCs:
            #: create shapefile for the feature class
            arcpy.FeatureClassToShapefile_conversion(join(packageFolderPath, name + ".gdb", fc), packageFolderPath)

            #: add to package zipfile package
            zipws(packageFolderPath, zfSHP, False)

            # create unpackaged zip file and move data into that zip file
            zfSHPUnpackaged = zipfile.ZipFile(join(unpackagedFolderPath, fc, '_Statewide', fc + '_shp.zip'), 'w', zipfile.ZIP_DEFLATED)
            zipws(packageFolderPath, zfSHPUnpackaged, False)
            zfSHPUnpackaged.close()

            # delete temporary shapefiles
            arcpy.Delete_management(join(packageFolderPath, fc + ".shp"))
        zfSHP.close()

        zfFGDB = zipfile.ZipFile(join(packageFolderPath, name + '_gdb.zip'), 'w', zipfile.ZIP_DEFLATED)
        target_dir = join(packageFolderPath, name + '.gdb')
        rootlen = len(target_dir) + 1
        for base, dirs, files in walk(target_dir):
            for file in files:
                fn = join(base, file)
                zfFGDB.write(fn, name + ".gdb/" + fn[rootlen:])
        zfFGDB.close()
        rmtree(join(packageFolderPath, name + ".gdb"))


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
    pallet.ship()
