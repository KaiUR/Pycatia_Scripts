'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Your_Script_Name.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        EDIT: One line summary shown on the script button.
    Author:         EDIT: Your Name
    Date:           EDIT: DD.MM.YY
    Description:    EDIT: Full description of what the script does.
                    EDIT: Continuation lines must be indented.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    wxPython
                    Catia V5 running with an open part document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
import wx

class ScriptDialog(wx.Dialog):
    def __init__(self, parent, title):
        super().__init__(parent, title=title, size=(420, 200))                                                  #EDIT: Adjust dialog size to fit your fields

        vbox = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(2, 2, 10, 10)                                                                  #EDIT: First arg = number of parameter rows

        # EDIT: Add one StaticText + TextCtrl pair per input. Duplicate rows as needed.
        grid.Add(wx.StaticText(self, label="EDIT Parameter 1:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.param_1 = wx.TextCtrl(self, value="EDIT default")                                                 #EDIT: Set field default value
        grid.Add(self.param_1, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self, label="EDIT Parameter 2:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.param_2 = wx.TextCtrl(self, value="EDIT default")                                                 #EDIT: Set field default value
        grid.Add(self.param_2, 1, wx.EXPAND)

        grid.AddGrowableCol(1, 1)
        vbox.Add(grid, 1, wx.ALL | wx.EXPAND, 15)

        btn_sizer = wx.StdDialogButtonSizer()
        btn_ok     = wx.Button(self, wx.ID_OK,     label="OK")
        btn_cancel = wx.Button(self, wx.ID_CANCEL, label="Cancel")
        btn_ok.SetDefault()
        btn_sizer.AddButton(btn_ok)
        btn_sizer.AddButton(btn_cancel)
        btn_sizer.Realize()
        vbox.Add(btn_sizer, 0, wx.ALL | wx.EXPAND, 10)

        self.SetSizer(vbox)
        self.Center()

if __name__ == "__main__":
    caa = catia()                                                                                               #Catia application instance
    active_doc = caa.active_document                                                                           #Current active document
    app = wx.App(None)                                                                                         #Initialize wx application

    if type(active_doc) is not PartDocument:                                                                   #Check that a CATPart is active
        wx.MessageBox("A CATPart document must be the active document.", "Error",
                wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP)
        exit()

    part_document: PartDocument = active_doc                                                                   #Cast to PartDocument
    part = part_document.part                                                                                  #Current part
    hybrid_bodies = part.hybrid_bodies                                                                         #Top level geometric sets
    hybrid_shape_factory = part.hybrid_shape_factory                                                           #GSD workbench for creating hybrid shapes

    dlg = ScriptDialog(None, "EDIT: Dialog Title")                                                             #EDIT: Set dialog title
    if dlg.ShowModal() != wx.ID_OK:                                                                            #If user cancelled
        dlg.Destroy()
        exit()

    param_1 = dlg.param_1.GetValue().strip()                                                                   #EDIT: Get each field value
    param_2 = dlg.param_2.GetValue().strip()                                                                   #EDIT: Get each field value
    dlg.Destroy()                                                                                              #Destroy dialog

    # EDIT: Validate inputs
    if not param_1:
        wx.MessageBox("EDIT: Parameter 1 cannot be empty.", "Error", wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP)
        exit()

    selectionSet = active_doc.selection                                                                        #Create container for selection
    selectionSet.clear()                                                                                       #Clear any existing selection

    # TODO: Add script logic here using param_1, param_2, part, hybrid_bodies, hybrid_shape_factory

    part.update()                                                                                              #Update part after all operations

    print("\n\n Completed\n\n")
