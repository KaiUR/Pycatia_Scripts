'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Find_And_Select_By_Name.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Find and select all hybrid shapes whose names contain a search string.
    Author:         Kai-Uwe Rathjen
    Date:           06.05.26
    Description:    This script will ask the user to enter a search string. The script will then search through all
                    hybrid shapes in the active document and select any whose name contains the search string.
                    The count of found elements is printed to the console.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    wxPython
                    Catia V5 running with an open part, product, or process document containing hybrid shapes.
                    This script needs an open part document, product document or process document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         12.05.26 1.1: Dialog raised to foreground of CATIA window.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
import wx
import ctypes

def _bring_to_front(window):
    u32 = ctypes.windll.user32
    hwnd = window.GetHandle()
    fg_hwnd = u32.GetForegroundWindow()
    fg_tid = u32.GetWindowThreadProcessId(fg_hwnd, None)
    our_tid = ctypes.windll.kernel32.GetCurrentThreadId()
    if fg_tid != our_tid:
        u32.AttachThreadInput(fg_tid, our_tid, True)
    u32.BringWindowToTop(hwnd)
    u32.SetForegroundWindow(hwnd)
    if fg_tid != our_tid:
        u32.AttachThreadInput(fg_tid, our_tid, False)

if __name__ == "__main__":
    #Anchoring relavent components
    caa = catia()                                                                                               #Catia application instance

    app = wx.App(None)                                                                                          #Initilize wx application

    dlg = wx.TextEntryDialog(None, "Enter name to search for:", "Find and Select By Name", "",
            wx.OK | wx.CANCEL | wx.CENTRE | wx.STAY_ON_TOP)                                                     #Create text entry dialog

    wx.CallAfter(_bring_to_front, dlg)
    if dlg.ShowModal() == wx.ID_OK:                                                                             #If user clicked OK
        search_string = dlg.GetValue().strip()                                                                  #Get search string
    else:                                                                                                       #If user cancelled
        dlg.Destroy()
        print("No search string entered")
        exit()

    dlg.Destroy()                                                                                               #Destroy dialog

    if search_string == "":                                                                                     #If search string is empty
        print("You must enter a search string")
        exit()

    selectionSet = caa.active_document.selection                                                                #Create container for selection
    selectionSet.clear()                                                                                        #Clear any existing selection

    search_query = f"Name=*{search_string}*,all"                                                                #Build search query using wildcard matching
    selectionSet.search(search_query)                                                                           #Search for all elements matching name

    found_count = selectionSet.count                                                                            #Get count of found elements

    if found_count == 0:                                                                                        #If nothing found
        print(f"No elements found with name containing: '{search_string}'")
    else:                                                                                                       #If found
        print(f"Found and selected {found_count} element(s) containing: '{search_string}'")
        for index in range(found_count):                                                                        #Print each found element name
            print(f"  [{index + 1}] {selectionSet.item(index + 1).value.name}")
