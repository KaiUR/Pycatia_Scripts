'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Your_Script_Name.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.9.5
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
                    pycatia >= 0.9.5
                    wxPython
                    Catia V5 / DELMIA running with an open CATProcess document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.dmaps_interfaces.process_document import ProcessDocument
from pycatia.ppr_interfaces.ppr_document import PPRDocument
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
    check_document = caa.active_document                                                                       #Current active document
    current_document = None
    app = wx.App(None)                                                                                         #Initialize wx application

    if type(check_document) is ProcessDocument:                                                                #Active document is a ProcessDocument
        current_document: PPRDocument = check_document.ppr_document                                           #Get PPRDocument from ProcessDocument
    elif type(check_document) is PPRDocument:                                                                  #Active document is already a PPRDocument
        current_document: PPRDocument = caa.active_document
    else:
        wx.MessageBox("A CATProcess document must be the active document.", "Error",
                wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP)
        exit()

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

    processes = current_document.processes                                                                     #Get process list

    for process_index in range(processes.count):                                                               #Cycle through all processes
        activity = processes.item(process_index + 1)                                                          #Get process

        part_operations = activity.children_activities                                                        #Get all Part operations for this process

        for part_operation_index in range(part_operations.count):                                             #Cycle through Part operations
            part_op = part_operations.item(part_operation_index + 1)                                          #Get Part operation

            if part_op.type == "ManufacturingSetup":                                                          #Check for Part operation type
                programs = part_op.children_activities                                                        #Get manufacturing programs

                for program_index in range(programs.count):                                                   #Cycle through programs
                    program = programs.item(program_index + 1)                                                #Get program

                    if program.type == "ManufacturingProgram":                                                #Check for manufacturing program type
                        operations = program.children_activities                                              #Get operations for this program

                        for operation_index in range(operations.count):                                      #Cycle through operations
                            operation = operations.item(operation_index + 1)                                 #Get operation

                            # TODO: Add logic for each operation here using param_1, param_2
                            pass

    print("\n\n Completed\n\n")
