'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    IGES_Export_Curve_AXIS.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Exports curve as IGES in 
    Author:         Kai-Uwe Rathjen
    Date:           05.03.26
    Description:    This script will ask the user to select curves and an axis. The script will then do an axis to axis move
                    and export the result as an IGES. Script assumes that the curves are datums. The output IGES file will have 
                    all curves moved to the Absolute Axis.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 9.10
                    pycatia
                    Catia V5 running wtih an open part containing a curve and an axis system.
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------
    
    Change:         19.03.26
                    Modified script to work when there is a process or procuct open containing a part.
    
    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.hybrid_shape_interfaces.hybrid_shape_axis_to_axis import HybridShapeAxisToAxis
from pycatia.mec_mod_interfaces.part_document import PartDocument
import wx

if __name__ == "__main__":
    #Anchoring relavent components
    caa = catia()                                                                                               #Catia application instance
    active_doc = caa.active_document                                                                            #Current Document
    documents = caa.documents                                                                                   #Collection of documents

    object_filter = ("MonoDimInfinite",)                                                                        #Set user selection filter (Curves)                             
    selectionSet = caa.active_document.selection                                                                #Create container for selection
    status = selectionSet.select_element3(object_filter,"Select curves to export" , False , 2 , False)          #Runs an interactive selection command, exhaustive version. 
    if status != "Normal":                                                                                      #Check if selection was succesful
        print("You must select a curve for export")
        exit()
        
    selected_item = selectionSet.item(1) 

    if type(active_doc) is PartDocument:
        part = active_doc.part                                                                                  #If document is part document
        part_document : PartDocument = active_doc
    else:                                                                                                       #Else get part from product structure
        # We are in a Product or Process; find the Part via the selection
        # We use .com_object to access the LeafProduct property
        leaf_product = selected_item.com_object.LeafProduct
        part_document = PartDocument(leaf_product.ReferenceProduct.Parent)
        # Navigation: LeafProduct -> ReferenceProduct -> Parent (PartDocument) -> Part
        part = part_document.part                                                                               #Get new part object

    hybrid_bodies = part.hybrid_bodies                                                                          #Set off all top level geometric sets
    hybrid_shape_factory = part.hybrid_shape_factory                                                            #GSD workbentch to create hybridshapes
    
    partDocumentName = part_document.name.removesuffix('.CATPart')                                              #Name of current part
    partDocumentPath = str(part_document.path()).removesuffix(part_document.name)                               #path of current part, as string with filename removed
    
    curves_selected = [None] * selectionSet.count                                                               #Create array to store curves
    curves_count = selectionSet.count                                                                           #Store number of curves
    for index in range(selectionSet.count):                                                                     #Loop through selection
        curves_selected[index] = selectionSet.item(index + 1).reference                                         #Store selected curves as reference
        
    object_filter = ("AnyObject",)                                                                              #Set user selection filter (Curves)                             
    selectionSet = caa.active_document.selection                                                                #Create container for selection
    status = selectionSet.select_element3(object_filter,"Select reference axis system" , False , 2 , False)     #Runs an interactive selection command, exhaustive version. 
    if status != "Normal":                                                                                      #Check if selection was succesful
        print("You must select a reference axis system")
        exit()

    selected_axis_system = selectionSet.item(1).value                                                           #Store selected axis system
    selected_axis_system_name = selectionSet.item(1).name                                                       #Store selected axis system name
    
    # Disable user prompts and confirmantions
    caa.RefreshDisplay = False
    caa.DisplayFileAlerts = False

    #Create new part for export
    IGES_documnet = documents.add("Part")                                                                       #Add new part
    IGES_part = IGES_documnet.part                                                                              #New part object
    IGES_part.part_number = "IGES_EXPORT"                                                                       #Rename new part 
       
    IGES_hybrid_bodies = IGES_part.hybrid_bodies                                                                #Get geometric sets
    IGES_hb_con = IGES_hybrid_bodies.add()                                                                      #Add new geometric set
    IGES_hb_con.name = "IGES_EXPORT_CURVES_CON"                                                                 #Rename geometric set
    IGES_hb = IGES_hybrid_bodies.add()                                                                          #Add new geometric set
    IGES_hb.name = "IGES_EXPORT_CURVES"                                                                         #Rename geometric set

    selectionSet.clear()                                                                                        #Clear selection

    for index in range(curves_count):                                                                           #Loop through curves
        selectionSet.add(curves_selected[index])                                                                #Add curves to selection
    selectionSet.add(selected_axis_system)                                                                      #Add axis system to selection
    selectionSet.copy()                                                                                         #Copy selection
    selectionSet.clear()                                                                                        #Clear selection

    selectionExport = caa.active_document.selection                                                             #New selection Object
    selectionExport.clear()
    selectionExport.add(IGES_hb_con)                                                                            #Select paste location
    selectionExport.paste_special("CATPrtResultWithOutLink")                                                    #Paste selection

    selectionExport.clear()                                                                                     #Clear selection
    selectionExport.search("Name=Geometrical Set.1,all")                                                        #Look for default geometric set                                                     
    if selectionExport.count == 1:                                                                              #If found
        selectionExport.delete()                                                                                #Delete set
    else:                                                                                                       #If not found
        selectionExport.clear()                                                                                 #Clear selection

    IGES_part.update()                                                                                          #Update part
    
    hybrid_shape_factory_IGES = IGES_part.hybrid_shape_factory                                                  #GSD workbentch to create hybridshapes
    
    for index in range(IGES_hb_con.hybrid_shapes.count):                                                        #For each curve
        axis_to_axis = hybrid_shape_factory_IGES.add_new_axis_to_axis(IGES_part.create_reference_from_object(
                IGES_hb_con.hybrid_shapes.item(index + 1)), 
                IGES_part.create_reference_from_object(IGES_part.axis_systems.item(2)), 
                IGES_part.create_reference_from_object(IGES_part.axis_systems.item(1)))                         #Preform an axis to axis transformation 
        IGES_hb_con.append_hybrid_shape(axis_to_axis)                                                           #Add axix to axis result to geometric set
        
        IGES_part.update()        
        curve_Explicit = hybrid_shape_factory_IGES.add_new_curve_datum(
                IGES_hb_con.hybrid_shapes.item(IGES_hb_con.hybrid_shapes.count))                                #Create datum
        IGES_hb.append_hybrid_shape(curve_Explicit)

    IGES_part.update()
    
    selectionExport = caa.active_document.selection                                                             #New selection Object
    selectionExport.clear()
    selectionExport.add(IGES_hb_con)                                                                            #Select paste location
    selectionExport.add(IGES_part.axis_systems.item(2))
    selectionExport.delete()
    
    export_file_name = ''
    app = wx.App(None)                                                                                          #bootstrap the wxPython system 
    style = wx.OK | wx.CANCEL | wx.CENTRE | wx.STAY_ON_TOP
    dialog = wx.TextEntryDialog(
            None, "Enter a name for the IGES to Export", "IGES File Name", "Enter File Name", style)            #Create dialog
    if dialog.ShowModal() == wx.ID_OK:                                                                          #Show dialog and wait for ok
        export_file_name = dialog.GetValue()                                                                    #Get path that user selected
    else:                                                                                                       #Something whent wrong or user canceled
        dialog.Destroy()
        # Enable user prompts and confirmantions
        caa.RefreshDisplay = True
        caa.DisplayFileAlerts = True
        IGES_documnet.close()                                                                                   #Close part
        print("Error when getting file name for export")
        exit()                                 
    dialog.Destroy()                                                                                            #Close dialog
    
    IGES_documnet.export_data(partDocumentPath + export_file_name + ".igs", "igs", overwrite=True)              #Export part
    IGES_documnet.close()                                                                                       #Close part

    # Enable user prompts and confirmantions
    caa.RefreshDisplay = True
    caa.DisplayFileAlerts = True