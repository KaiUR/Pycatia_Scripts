'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Replace_Name_Hybrid_Shapes.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Renames multiple hybrid shapes in one go.
    Author:         Kai-Uwe Rathjen
    Date:           14.04.26
    Description:    This script will ask the user to select hybrid shapes and the script will cycle through them and
                    replace a text with new text in all of them. Works like classic search and replace.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    wxPython
                    Catia V5 running with an open part, product or process.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''
#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
import wx

#--- Classic Find & Replace dialog ---
class FindReplaceDialog(wx.Dialog):                                                                             #Custom dialog class
    def __init__(self, parent):
        super().__init__(parent, title="Find and Replace", style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        mainSizer    = wx.BoxSizer(wx.VERTICAL)                                                                 #Outer vertical sizer
        gridSizer    = wx.FlexGridSizer(rows=2, cols=2, vgap=8, hgap=8)                                        #2x2 grid for labels + fields
        btnSizer     = wx.BoxSizer(wx.HORIZONTAL)                                                               #Button row

        self.findCtrl    = wx.TextCtrl(self, size=(260, -1))                                                    #Find text input
        self.replaceCtrl = wx.TextCtrl(self, size=(260, -1))                                                    #Replace text input

        gridSizer.Add(wx.StaticText(self, label="Find what:"),    0, wx.ALIGN_CENTER_VERTICAL)
        gridSizer.Add(self.findCtrl,    1, wx.EXPAND)
        gridSizer.Add(wx.StaticText(self, label="Replace with:"), 0, wx.ALIGN_CENTER_VERTICAL)
        gridSizer.Add(self.replaceCtrl, 1, wx.EXPAND)
        gridSizer.AddGrowableCol(1)                                                                             #Let the input column stretch

        btnOk     = wx.Button(self, wx.ID_OK,     label="Replace All")                                         #Confirm button
        btnCancel = wx.Button(self, wx.ID_CANCEL, label="Cancel")                                               #Cancel button
        btnOk.SetDefault()                                                                                      #Enter key triggers Replace All
        btnSizer.Add(btnOk,     0, wx.RIGHT, 8)
        btnSizer.Add(btnCancel, 0)

        mainSizer.Add(gridSizer, 0, wx.EXPAND | wx.ALL,                   12)
        mainSizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        mainSizer.Add(btnSizer,  0, wx.ALIGN_RIGHT | wx.ALL,              12)
        self.SetSizerAndFit(mainSizer)
        self.Centre()

def apply_replacement(currentName):                                                                             #Helper - applies find/replace logic to a single name
    if findText in currentName:                                                                                 #Plain text substring match
        return currentName.replace(findText, newName)                                                          #Replace all occurrences
    return None                                                                                                 #No match - return None to skip

if __name__ == "__main__":
    #Anchoring relavent components
    caa = catia()                                                                                               #Catia application instance

    object_filter = ("AnyObject",)                                                                             #Set user selection filter
    selectionSet = caa.active_document.selection                                                               #Create container for selection
    status = selectionSet.select_element3(object_filter, "Select objects to rename", False, 2, False)          #Runs an interactive selection command, exhaustive version.
    if status != "Normal":                                                                                      #Check if selection was succesful
        print("You must select an object")
        exit()

    findText  = ''                                                                                              #Initilise varible
    newName   = ''                                                                                              #Initilise varible

    app = wx.App(None)                                                                                         #Bootstrap the wxPython system

    dialog = FindReplaceDialog(None)                                                                           #Create dialog
    if dialog.ShowModal() == wx.ID_OK:                                                                         #Show dialog and wait for ok
        findText = dialog.findCtrl.GetValue()                                                                  #Get search text
        newName  = dialog.replaceCtrl.GetValue()                                                               #Get replacement text
    else:
        dialog.Destroy()
        print("You must enter a search text and replacement text")
        exit()
    dialog.Destroy()                                                                                           #Close dialog

    for index in range(selectionSet.count):                                                                    #Loop through selection

        if selectionSet.item(index + 1).value.name.find("Selection_") != -1:                                   #If selecting is Boundary ref instead of hybridshape
            currentName = selectionSet.item(index + 1).value.parent.name                                      #Get current parent name
            result = apply_replacement(currentName)                                                            #Apply find/replace
            if result is not None:
                selectionSet.item(index + 1).value.parent.name = result                                       #Change name of each parent object
        else:
            currentName = selectionSet.item(index + 1).value.name                                             #Get current name
            result = apply_replacement(currentName)                                                            #Apply find/replace
            if result is not None:
                selectionSet.item(index + 1).value.name = result                                              #Change name of each object
