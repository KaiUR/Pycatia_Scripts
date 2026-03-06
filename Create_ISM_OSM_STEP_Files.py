'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Create_ISM_OSM_STEP_Files.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Create two step files, with ISM and OSM surfaces.
    Author:         Kai-Uwe Rathjen
    Date:           03.03.26
    Description:    This script will ask the user to select a face on the ISM (Inside of Metal) and a face on the OSM (Outside of Metal). The script will then take an
                    multiple extract in tangency and create two step files from these surfaces. This macro will assume that the
                    surfaces for ISM and OSM are in tangent continuity, if not this macro cannot be used, but in most cases this macro will work.
                    Like name Step files will be overwritten.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 9.10
                    pycatia
                    Catia V5 running with an open part that contains either surfaces or solids.
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------
    
    Change:
    
    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.hybrid_shape_interfaces.hybrid_shape_extract import HybridShapeExtract
from pycatia.hybrid_shape_interfaces.hybrid_shape_surface_explicit import HybridShapeSurfaceExplicit
from pycatia.mec_mod_interfaces.part_document import PartDocument

if __name__ == "__main__":
    #Anchoring relavent components
    caa = catia()                                                                                               #Catia application instance
    part_document: PartDocument = caa.active_document                                                           #Current open document
    part = part_document.part                                                                                   #Current part
    hybrid_bodies = part.hybrid_bodies                                                                          #Set off all top level geometric sets
    hybrid_shape_factory = part.hybrid_shape_factory                                                            #GSD workbentch to create hybridshapes
    documents = caa.documents                                                                                   #Collection of documents
    refISM = None
    refOSM = None

    partDocumentName = part_document.name.removesuffix('.CATPart')                                              #Name of current part
    partDocumentPath = str(part_document.path()).removesuffix(part_document.name)                               #path of current part, as string with filename removed

    #Get User to select ISM Face
    object_filter = ("Face",)                                                                                   #Set user selection filter                               
    selectionSet = caa.active_document.selection                                                                #Create container for selection
    status = selectionSet.select_element3(object_filter,"Select face on ISM" , False , 2 , False)               #Runs an interactive selection command, exhaustive version. 
    if status == "Normal":                                                                                      #Check if selection was succesful
        refISM = part_document.selection.item(1).reference
    else:
        exit()

    status = selectionSet.select_element3(object_filter,"Select face on OSM" , False , 2 , False)               #Runs an interactive selection command, exhaustive version. 
    if status == "Normal":                                                                                      #Check if selection was succesful
        refOSM = part_document.selection.item(1).reference
    else:
        exit()

    #Create new geometric set and extract for ISM and OSM
    hb = hybrid_bodies.add()                                                                                    #Add new geometric set
    hb.name = "ISM_OSM_Surfaces"                                                                                #Set name for new geometric set
    part.in_work_object = hb                                                                                    #Make new geometric set inwork object

    ISM_Extract = hybrid_shape_factory.add_new_extract(refISM)                                                  #Create new extract
    OSM_Extract = hybrid_shape_factory.add_new_extract(refOSM)                                                  #Create new extract

    ISM_Extract.propagation_type = 2                                                                            #Set Propagation type to tangent
    OSM_Extract.propagation_type = 2                                                                            #Set Propagation type to tangent

    ISM_Extract.complementary_extract = False                                                                   #Set Comp extract to false
    OSM_Extract.complementary_xtract = False                                                                    #Set Comp extract to false

    ISM_Extract.is_federated = False                                                                            #Set federated to false
    OSM_Extract.is_federated = False                                                                            #Set federated to false

    hb.append_hybrid_shape(ISM_Extract)                                                                         #Add ectract to geometric set
    hb.append_hybrid_shape(OSM_Extract)                                                                         #Add ectract to geometric set

    hb.hybrid_shapes.item(1).name = "ISM_Extract"                                                               #Rename Extract
    hb.hybrid_shapes.item(2).name = "OSM_Extract"                                                               #Rename Extract

    part.update()                                                                                               #Update part document

    #Create Datums
    ISM_Extract_Explicit = hybrid_shape_factory.add_new_surface_datum(hb.hybrid_shapes.item(1))                 #Create datum
    hb.append_hybrid_shape(ISM_Extract_Explicit)                                                                #Add to geometric set
    OSM_Extract_Explicit = hybrid_shape_factory.add_new_surface_datum(hb.hybrid_shapes.item(2))                 #Create datum
    hb.append_hybrid_shape(OSM_Extract_Explicit)                                                                #Add to geometric set

    hb.hybrid_shapes.item(3).name = "ISM_Extract_Datum"                                                         #Rename datum
    hb.hybrid_shapes.item(4).name = "OSM_Extract_Datum"                                                         #Rename datum

    hybrid_shape_factory.delete_object_for_datum(hb.hybrid_shapes.item(1))                                      #Remove construction
    hybrid_shape_factory.delete_object_for_datum(hb.hybrid_shapes.item(1))                                      #Remove construction

    part.update()                                                                                               #Update part document

    # Disable user prompts and confirmantions
    caa.RefreshDisplay = False
    caa.DisplayFileAlerts = False

    #Create new parts for ISM and OSM
    ISM_documnet = documents.add("Part")                                                                        #Add new part
    ISM_part = ISM_documnet.part                                                                                #New part object
    ISM_part.part_number = "ISM"                                                                                #Rename new part 
       
    ISM_hybrid_bodies = ISM_part.hybrid_bodies                                                                  #Get geometric sets
    ISM_hb = ISM_hybrid_bodies.add()                                                                            #Add new geometric set
    ISM_hb.name = "ISM_Surfaces"                                                                                #Rename geometric set

    selectionSet.clear()                                                                                        #Clear selection
    selectionSet.add(hb.hybrid_shapes.item(1))                                                                  #Selecting ISM surface
    selectionSet.copy()                                                                                         #Copy selection
    selectionSet.clear()                                                                                        #Clear selection

    selectionExport = caa.active_document.selection                                                             #New selection Object
    selectionExport.clear()
    selectionExport.add(ISM_hb)                                                                                 #Select paste location
    selectionExport.paste_special("CATPrtResultWithOutLink")                                                    #Paste selection

    selectionExport.clear()                                                                                     #Clear selection
    selectionExport.search("Name=Geometrical Set.1,all")                                                        #Look for default geometric set                                                     
    if selectionExport.count == 1:                                                                              #If found
        selectionExport.delete()                                                                                #Delete set
    else:                                                                                                       #If not found
        selectionExport.clear()                                                                                 #Clear selection

    ISM_part.update()
    ISM_documnet.export_data(partDocumentPath + partDocumentName + "_ISM.stp", "stp", overwrite=True)           #Export part
    ISM_documnet.close()                                                                                        #Close part

    OSM_documnet = documents.add("Part")                                                                        #Add new part
    OSM_part = OSM_documnet.part                                                                                #New part object
    OSM_part.part_number = "OSM"                                                                                #Rename new part
    OSM_hybrid_bodies = OSM_part.hybrid_bodies                                                                  #Get geometric sets
    OSM_hb = OSM_hybrid_bodies.add()                                                                            #Add new geometric set
    OSM_hb.name = "OSM_Surfaces"                                                                                #Rename geometric set

    selectionSet.clear()                                                                                        #Clear selection
    selectionSet.add(hb.hybrid_shapes.item(2))                                                                  #Selecting OSM surface
    selectionSet.copy()                                                                                         #Copy selection
    selectionSet.clear()                                                                                        #Clear selection

    selectionExport = caa.active_document.selection                                                             #New selection Object
    selectionExport.clear()
    selectionExport.add(OSM_hb)                                                                                 #Select paste location
    selectionExport.paste_special("CATPrtResultWithOutLink")                                                    #Paste selection

    selectionExport.clear()                                                                                     #Clear selection
    selectionExport.search("Name=Geometrical Set.1,all")                                                        #Look for defauld geometric set                                 
    if selectionExport.count == 1:                                                                              #If found
        selectionExport.delete()                                                                                #Delete set
    else:                                                                                                       #If not found
        selectionExport.clear()                                                                                 #Clear selection

    OSM_part.update()
    OSM_documnet.export_data(partDocumentPath + partDocumentName + "_OSM.stp", "stp", overwrite=True)           #Export part
    OSM_documnet.close()                                                                                        #Close part

    # Enable user prompts and confirmantions
    caa.RefreshDisplay = True
    caa.DisplayFileAlerts = True

    #Delete Construction
    selectionSet.clear()                                                                                        #Clear selection
    selectionSet.add(hb)                                                                                        #Select geometric set
    selectionSet.delete()                                                                                       #Delete geometric set