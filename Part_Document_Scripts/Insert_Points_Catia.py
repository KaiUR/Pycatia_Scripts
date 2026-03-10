'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    insert_points_catia.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3, wx 4.2.5
    Release:        V5R32
    Purpose:        Imports points into catia from file
    Author:         Kai-Uwe Rathjen
    Date:           03.03.26
    Description:    This script allow the user to import points from a text file or a csv file. This script does not
                    support names for the points. The points should be written in the file in the following format:
                        Text File:  x y z
                        Csv File: x,y,z,
                        
                    Text file points are space seperated, csv file points are comma seperated.
                    If the user has only two entires for a point like x,y the script will set z to zero.
                    If the user only has on entry it will skip the line. There is no other error correction in this script.
    dependencies = [
                    "pycatia", 
                    "wxPython",
                    ]
    requirements:   Python >= 9.10
                    pycatia
                    Catia V5 running wtih an open part. A CVS or Text file containing the points.
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------
    
    Change:
    
    -----------------------------------------------------------------------------------------------------------------------
'''

from pycatia import catia
from pycatia.hybrid_shape_interfaces.hybrid_shape_point_coord import (HybridShapePointCoord,)
from pycatia.mec_mod_interfaces.part_document import PartDocument
import wx

'''
    This function will open an open file dialog for the user to select a file.
    
    Inputs:
        wildcard        This is the filter for what files the user can select.
                        In this example: '*.txt;*.csv' The user can select text files and csv files.
        
    output:
        The path to a file that the user has selected. 
        The path will be None if no valid selecttion was made of if the user closes the dialog
        without selecting anything.
'''
def get_path(wildcard):
    app = wx.App(None)                                                      #bootstrap the wxPython system
    style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST                              #Add conditions
    dialog = wx.FileDialog(None, 'Open', wildcard=wildcard, style=style)    #Create dialog
    if dialog.ShowModal() == wx.ID_OK:                                      #Show dialog and wait for ok
        path = dialog.GetPath()                                             #Get path that user selected
    else:                                                                   #Something whent wrong or user canceled
        path = None                                                         #Set path to none                                 
    dialog.Destroy()                                                        #Close dialog
    return path                                                             #Return path


if __name__ == "__main__":
    #Anchoring relavent components
    caa = catia()                                                               #Catia application instance
    part_document: PartDocument = caa.active_document                           #Current open document
    part = part_document.part                                                   #Current part
    hybrid_bodies = part.hybrid_bodies                                          #Set off all top level geometric sets
    hybrid_shape_factory = part.hybrid_shape_factory                            #GSD workbentch to create hybridshapes

    inport_filepath = get_path('*.txt;*.csv')                                   #Ask the user to select a file, either txt or csv

    if ".txt" in inport_filepath:                                               #If text file
        delimiter = ' '
    elif ".csv" in inport_filepath:                                             #If csv file
        delimiter = ','

    hb = hybrid_bodies.add()                                                    #Add new geometric set
    hb.name = "Point Inport"                                                    #Set name for new geometric set

    with open(inport_filepath, 'r', encoding='UTF-8') as file:                  #Open file
        while line := file.readline():                                          #Read each line of the file untill empty
            current_line = line.rstrip()                                        #get current line
            coords = current_line.split(delimiter)                              #get seperate components

            if len(coords) < 2:                                                 #Skip if only one or none
                continue
            elif len(coords) == 2:                                              #Add zero if Z is left blank
                coords.append(0)

            point = hybrid_shape_factory.add_new_point_coord(
                    coords[0], coords[1], coords[2])                            #Create new point
            hb.append_hybrid_shape(point)                                       #Add point to geometric shape

    part.update()                                                               #Update part document