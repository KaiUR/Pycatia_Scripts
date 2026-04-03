
# Pycatia Scripts

This is a collection of pycatia scripts that I use.


## Acknowledgements

 - [Pycatia](https://github.com/evereux/pycatia)


## Appendix

Any Document Scripts:

    Hide_Planes_And_Axis_Systems.py

        Hides all planes and axis systems in a Product document or part document

    Rename_Hybrid_Shapes.py

        Allows user to rename hybrid shapes through message box

Part Document Scripts

    Create_ISM_OSM_STEP_Files.py

        Allows user to select two faces or surfaces, then preforms an extract in tangency and exports 
        the result as two step files ISM and OSM. Used to create Inside of metal and Outside of metal surfaces.

    Export_Points_Select_Axis_and_Geo_Set_To_CSV.py

        Exports points contained in Geometric set relative to selected axis system to a csv file

    Export_Points_Select_Axis_and_Geo_Set_To_XYZ.py

        Exports points contained in Geometric set relative to selected axis system to a xyz file (Specifically PCDimms Format)

    Export_Points_Select_Geo_Set_To_CSV.py

        Exports points contained in Geometric set relative to absolute axis system to a csv file

    Export_Points_Select_Geo_Set_To_XYZ.py

        Exports points contained in Geometric set relative to absolute axis system to a xyz file (Specifically PCDimms Format)

    IGES_Export_Curve_AXIS.py

        Exports curve to IGES file after axis to axis moves curve from a reference axis system to absolute axis system.

    Insert_Points_Catia.py

        Inserts points into active part from text file (Tab seperated) or csv file

    Insert_Points_Catia_With_Names.py

        Inserts points into active part from text file (Tab seperated) or csv file with point names 

	Involute_Gear_Generator_Mathamatical.py

		Allows the user to create an involute profiles gear using inputted parameters. Script will get user input with a message box.

    Join_Explicit_No_Connect.py

        Joins curves or surfaces without checking connex as datum in one curve/surface

    Join_Explicit_No_Connect_Curve.py

        Joins curves without checking connex as datum in one curve

    Join_Explicit_No_Connect_Surface.py

        Joins surfaces without checking connex as datum in one surface

    Measure_Curve_With_3_PTS_AS_CIRCLE.py

        Allows user to measure radius of curves using 3 point circle through curve

    Measure_Curve_With_3_PTS_AS_CIRCLE_Keep_Con.py

        Allows user to measure radius of curves using 3 point circle through curve without removing constuction elements

    Measure_Radius_Surface.py
        Allows user to meaure radius of surface using intersection and three point circle without removing construction.

Process Document Scripts

    Export_Process_Table_Parameters.py

        Exports machinging program parameters to excel file for user to check parameters.
		
	Export_ResourceListy.py
		
		Exports the names of all resources in process document to an csv file

Product Document Scripts

    Save_Child_Parts_To_STEP.py

        Script to save all parts in product to seperate STEP files.

## Requirments

Packages

			pycatia
			wxPython
			xlsxwriter
