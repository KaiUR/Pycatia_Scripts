'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Export_Mass_CoG_Inertia_To_CSV.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Export mass, centre of gravity and inertia tensor from all solid bodies to CSV.
    Author:         Kai-Uwe Rathjen
    Date:           16.05.26
    Description:    This script iterates through all solid bodies in the active part and uses the CATIA
                    SPA workbench to extract volume, surface area, centre of gravity, and inertia tensor
                    for each body. Results are exported to a CSV file next to the CATPart.
                    Mass is derived from the product Analyze interface — it requires a material to be
                    applied to the body; bodies without material will show mass as N/A.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part document containing solid bodies.
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pathlib import Path

if __name__ == "__main__":
    caa = catia()
    active_doc = caa.active_document

    if not type(active_doc) is PartDocument:
        print("A CATPart document must be the active document.")
        exit()

    part_document: PartDocument = active_doc
    part = part_document.part

    doc_path_str = str(part_document.path())
    doc_name = part_document.name.removesuffix('.CATPart')

    if doc_path_str == part_document.name:
        output_path = Path.home() / "Downloads" / (doc_name + "_MassProperties.csv")
    else:
        output_path = Path(doc_path_str).parent / (doc_name + "_MassProperties.csv")

    spa = active_doc.com_object.GetWorkbench("SPAWorkbench")                                                      #SPA workbench for measurement

    bodies_com = part.com_object.Bodies                                                                           #All solid bodies in part
    body_count = bodies_com.Count

    if body_count == 0:
        print("No solid bodies found in this part document.")
        exit()

    print(f"\n Found {body_count} solid body(ies)\n")

    rows = []

    for i in range(body_count):
        body_com = bodies_com.Item(i + 1)
        body_name = body_com.Name
        print(f"  Processing: {body_name}")

        row = {'Body': body_name, 'Mass_kg': 'N/A', 'Volume_mm3': 'N/A',
               'Area_mm2': 'N/A', 'CoG_X': 'N/A', 'CoG_Y': 'N/A', 'CoG_Z': 'N/A',
               'Ixx': 'N/A', 'Ixy': 'N/A', 'Ixz': 'N/A',
               'Iyx': 'N/A', 'Iyy': 'N/A', 'Iyz': 'N/A',
               'Izx': 'N/A', 'Izy': 'N/A', 'Izz': 'N/A'}

        try:
            body_ref = part.com_object.CreateReferenceFromObject(body_com)
            meas = spa.GetMeasurable(body_ref)

            row['Volume_mm3'] = round(meas.Volume, 6)
            row['Area_mm2']   = round(meas.Area * 1e6, 3)                                                        #SPA returns m², convert to mm²

            cog = [0.0, 0.0, 0.0]
            meas.GetCOGPosition(cog)
            row['CoG_X'] = round(cog[0], 6)
            row['CoG_Y'] = round(cog[1], 6)
            row['CoG_Z'] = round(cog[2], 6)

            meas.ComputeInertia()                                                                                  #Must call before GetInertia
            inertia = [0.0] * 9
            meas.GetInertia(inertia)
            row['Ixx'] = round(inertia[0], 6)
            row['Ixy'] = round(inertia[1], 6)
            row['Ixz'] = round(inertia[2], 6)
            row['Iyx'] = round(inertia[3], 6)
            row['Iyy'] = round(inertia[4], 6)
            row['Iyz'] = round(inertia[5], 6)
            row['Izx'] = round(inertia[6], 6)
            row['Izy'] = round(inertia[7], 6)
            row['Izz'] = round(inertia[8], 6)
        except Exception as e:
            print(f"    Warning: SPA measurement failed for '{body_name}': {e}")

        try:
            product_com = active_doc.com_object.Product                                                           #Mass via product Analyze (needs material)
            analyze = product_com.Analyze
            row['Mass_kg'] = round(analyze.Mass, 9)
        except Exception:
            pass                                                                                                   #Mass remains N/A if no material applied

        rows.append(row)

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("Body,Mass_kg,Volume_mm3,Area_mm2,CoG_X,CoG_Y,CoG_Z,"
                    "Ixx,Ixy,Ixz,Iyx,Iyy,Iyz,Izx,Izy,Izz\n")
            for row in rows:
                f.write(
                    f"\"{row['Body']}\",\"{row['Mass_kg']}\",\"{row['Volume_mm3']}\","
                    f"\"{row['Area_mm2']}\",\"{row['CoG_X']}\",\"{row['CoG_Y']}\",\"{row['CoG_Z']}\","
                    f"\"{row['Ixx']}\",\"{row['Ixy']}\",\"{row['Ixz']}\","
                    f"\"{row['Iyx']}\",\"{row['Iyy']}\",\"{row['Iyz']}\","
                    f"\"{row['Izx']}\",\"{row['Izy']}\",\"{row['Izz']}\"\n"
                )

        print(f"\n\n Completed - saved to: {output_path}\n\n")

    except PermissionError:
        print("Error: Permission denied. Is the output file already open?")
    except IOError as e:
        print(f"Error: Could not write to file. {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
