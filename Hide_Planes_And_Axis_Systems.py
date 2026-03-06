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
    requirements:   Python >= 9.10
                    pycatia
                    Catia V5 running.
                    This script needs an open part document or product document.
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
    caa = catia()                                                                                                       #Catia application instance
    product_document: product_document = caa.active_document                                                            #Current open document

    selectionSet = caa.active_document.selection                                                                        #Create container for selection
    selectionSet.search("""(((FreeStyle.'Axis System' + 'Part Design'.'Axis System') + 
            'Generative Shape Design'.'Axis System') + 'Functional Molded Part'.'Axis System'),all""")                  #Search for all axis systems and select
    
    vis_properties = selectionSet.vis_properties                                                                        #Get visable properties of selected items
    vis_properties.set_show(1)                                                                                          #Set to no show
    selectionSet.clear()                                                                                                #Clear Selection
    
    selectionSet.search("""(((FreeStyle.Plane + 'Part Design'.Plane) + 
            'Generative Shape Design'.Plane) + 'Functional Molded Part'.Plane),all""")                                  #Search for all planes and select
    
    vis_properties = selectionSet.vis_properties                                                                        #Get Visable properties
    vis_properties.set_show(1)                                                                                          #Set to no show
    
    selectionSet.clear()                                                                                                #Clear Selection