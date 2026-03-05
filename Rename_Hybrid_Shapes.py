'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Rename_Hybrid_Shapes.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Renames multiple hybrid shapes in one go.
    Author:         Kai-Uwe Rathjen
    Date:           04.03.26
    Description:    This script will ask the user to select hybrid shapes and the script will cycle through them and
                    rename them all.
    dependencies = [
                    "pycatia",
                    "wxPython",
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

    object_filter = ("AnyObject",)                                                                              #Set user selection filter                               
    selectionSet = caa.active_document.selection                                                                #Create container for selection
    status = selectionSet.select_element3(object_filter,"Select objects to rename" , False , 2 , False)         #Runs an interactive selection command, exhaustive version. 
    if status != "Normal":                                                                                      #Check if selection was succesful
        exit()

    newName = ''
    app = wx.App(None)                                                                                          #bootstrap the wxPython system 
    style = wx.OK | wx.CANCEL | wx.CENTRE | wx.STAY_ON_TOP
    dialog = wx.TextEntryDialog(None, "Enter a new name for the Objects", "Rename Objects", "New Name", style)  #Create dialog
    if dialog.ShowModal() == wx.ID_OK:                                                                          #Show dialog and wait for ok
        newName = dialog.GetValue()                                                                             #Get path that user selected
    else:                                                                                                       #Something whent wrong or user canceled
        dialog.Destroy()
        exit()                                 
    dialog.Destroy()                                                                                            #Close dialog
        
    for index in range(selectionSet.count):
        selectionSet.item(index + 1).value.name = newName