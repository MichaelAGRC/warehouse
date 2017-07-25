import arcgisscripting
from agrc93 import email


UDSH_SDE = r'Database Connections\UDSHSpatial_New.sde'
SALINITY_SDE = r'Database Connections\Salinty_Production.sde'
UDSH_OUTPUT_FGDB = r'C:\Scheduled\LocalScripts\DataPickup\UDSHSpatial_New.gdb'
SALINITY_OUTPUT_FGDB = r'C:\Scheduled\LocalScripts\DataPickup\Salinity.gdb'

udsh_feature_classes = [
    'UDSHSpatial_New.UDSH.IMACS_SITE_POINT',
    'UDSHSpatial_New.UDSH.IMACS_SITE_LINE',
    'UDSHSpatial_New.UDSH.IMACS_SITE_POLYGON'
]
salinity_feature_classes = [
    'SALINITY.SALINITYADMIN.ProjectArea',
    'SALINITY.SALINITYADMIN.ProjectArea_Points',
]
salinity_tables = [
    'SALINITY.SALINITYADMIN.ProjectInformation',
    'SALINITY.SALINITYADMIN.ContractInformation',
    'SALINITY.SALINITYADMIN.COUNTY'
]

emailer = email.Emailer('stdavis@utah.gov')

try:
    gp = arcgisscripting.create()

    for sde, feature_classes, tables, output_fgdb in [[UDSH_SDE, udsh_feature_classes, [], UDSH_OUTPUT_FGDB],
                                                      [SALINITY_SDE, salinity_feature_classes, salinity_tables, SALINITY_OUTPUT_FGDB]]:
        print(output_fgdb)
        gp.Workspace = output_fgdb
        for dataset in feature_classes + tables:
            print('deleting: ' + dataset)
            dataset = dataset.replace('.', '_')
            if gp.Exists(dataset):
                gp.Delete_management(dataset)

        gp.Workspace = sde
        print('importing feature classes')
        gp.FeatureClassToGeodatabase_conversion(';'.join(feature_classes), output_fgdb)

        if len(tables) > 0:
            print('importing tables')
            gp.TableToGeodatabase_conversion(';'.join(tables), output_fgdb)
except:
    print(gp.GetMessages(2))
    emailer.sendEmail('Error in forkliftDropoff.py on <ip address>',
                      gp.GetMessages(2) + '\n\nC:\Scheduled\LocalScripts\forkliftDropoff.py')

print('done')
