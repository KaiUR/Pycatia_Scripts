'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Check_Open_Bodies.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Check all solid bodies in the active part for open or invalid geometry.
    Author:         Kai-Uwe Rathjen
    Date:           21.05.26
    Description:    This script iterates all solid bodies in the active CATPart and uses the SPA
                    workbench to attempt a volume measurement on each one. A body that fails the
                    measurement or returns a zero volume is flagged as potentially open or invalid.
                    Results are printed to the console. Useful as a geometry quality check before
                    downstream use such as FEA, manufacturing, or STEP export.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pycatia.space_analyses_interfaces.spa_workbench import SPAWorkbench

if __name__ == "__main__":
    caa = catia()                                                                                                   #Catia application instance
    active_doc = caa.active_document                                                                               #Current open document

    if not type(active_doc) is PartDocument:
        print("A CATPart document must be the active document.")
        exit()

    part_document: PartDocument = active_doc
    part = part_document.part
    bodies = part.bodies
    body_count = bodies.count

    if body_count == 0:
        print("No solid bodies found in this part document.")
        exit()

    spa = SPAWorkbench(active_doc.com_object)                                                                      #SPA workbench for geometry analysis

    print(f"\n Checking {body_count} solid body(ies)\n")
    print(f"  {'Body Name':<40} {'Volume (mm³)':>18} {'Status'}")
    print(f"  {'-'*40} {'-'*18} {'-'*20}")

    ok_count     = 0
    warning_count = 0
    error_count  = 0

    for i in range(body_count):
        body      = bodies.item(i + 1)
        body_name = body.name
        status    = ""
        volume_str = ""

        try:
            body_ref = part.create_reference_from_object(body)
            meas     = spa.get_measurable(body_ref)
            volume   = meas.Volume

            if volume is None or volume == 0.0:
                status     = "WARNING — zero volume"
                volume_str = "0.0"
                warning_count += 1
            elif volume < 0.0:
                status     = "WARNING — negative volume"
                volume_str = str(round(volume, 3))
                warning_count += 1
            else:
                status     = "OK"
                volume_str = str(round(volume, 3))
                ok_count   += 1

        except Exception as e:
            status     = f"ERROR — {e}"
            volume_str = "N/A"
            error_count += 1

        print(f"  {body_name:<40} {volume_str:>18} {status}")

    print(f"\n Summary: {ok_count} OK  |  {warning_count} Warning(s)  |  {error_count} Error(s)")

    if warning_count > 0 or error_count > 0:
        print("\n Bodies with warnings or errors may be:")
        print("   - Open shells (no enclosed volume)")
        print("   - Bodies with missing or failed features")
        print("   - Bodies that require a part.update() to resolve")

    print("\n\n Completed\n\n")
