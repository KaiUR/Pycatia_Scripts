'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Hide_Planes_And_Axis_Systems.py
    Version:        1.2
    Code:           Python3.10.4, Pycatia 0.10.0
    Release:        V5R32
    Purpose:        Hides all planes and axis systems.
    Author:         Kai-Uwe Rathjen
    Date:           04.03.26
    Description:    This script will hide all axis systems and planes.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running.
                    This script needs an open part document ,product document or process document.
    -----------------------------------------------------------------------------------------------------------------------
    
    Change:         03.06.26 1.1: Fix F401: remove unused PartDocument import.
                    20.07.26 1.2: Use CatVisPropertyShow enum instead of raw integer for set_show.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.enumeration.enums import CatVisPropertyShow

if __name__ == "__main__":

    #Anchoring relavent components
    caa = catia()                                                                                                       #Catia application instance

    selectionSet = caa.active_document.selection                                                                        #Create container for selection
    selectionSet.search("""(((FreeStyle.'Axis System' + 'Part Design'.'Axis System') + 
            'Generative Shape Design'.'Axis System') + 'Functional Molded Part'.'Axis System'),all""")                  #Search for all axis systems and select
    
    vis_properties = selectionSet.vis_properties                                                                        #Get visable properties of selected items
    vis_properties.set_show(CatVisPropertyShow.catVisPropertyNoShowAttr)                                                #Set to no show
    selectionSet.clear()                                                                                                #Clear Selection
    
    selectionSet.search("""(((FreeStyle.Plane + 'Part Design'.Plane) + 
            'Generative Shape Design'.Plane) + 'Functional Molded Part'.Plane),all""")                                  #Search for all planes and select
    
    vis_properties = selectionSet.vis_properties                                                                        #Get Visable properties
    vis_properties.set_show(CatVisPropertyShow.catVisPropertyNoShowAttr)                                                #Set to no show
    
    selectionSet.clear()                                                                                                #Clear Selection