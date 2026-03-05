'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Hide_Planes_And_Axis_Systems.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Hides all planes and axis systems.
    Author:         Kai-Uwe Rathjen
    Date:           04.03.26
    Description:    This script will hide all axis systems and planes.
    dependencies = [
                    "pycatia",
                    ]
    -----------------------------------------------------------------------------------------------------------------------
    
    Change:
    
    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
import wx

if __name__ == "__main__":

    #Anchoring relavent components
    caa = catia()                                                                                               #Catia application instance
    part_document: PartDocument = caa.active_document                                                           #Current open document
    part = part_document.part                                                                                   #Current part
    hybrid_bodies = part.hybrid_bodies                                                                          #Set off all top level geometric sets

    selectionSet = caa.active_document.selection                                                                #Create container for selection
    selectionSet.search("(((FreeStyle.'Axis System' + 'Part Design'.'Axis System') + 'Generative Shape Design'.'Axis System') + 'Functional Molded Part'.'Axis System'),all")
    
    vis_properties = selectionSet.vis_properties
    vis_properties.set_show(1)
    
    selectionSet.clear()

    part.update()
    
    selectionSet.search("(((FreeStyle.Plane + 'Part Design'.Plane) + 'Generative Shape Design'.Plane) + 'Functional Molded Part'.Plane),all")
    
    vis_properties = selectionSet.vis_properties
    vis_properties.set_show(1)
    
    selectionSet.clear()

    part.update()