'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Manage_Program_Names_And_Comments.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.10.0
    Release:        V5R32
    Purpose:        Review and set the names and comments of manufacturing programs and operations.
    Author:         Kai-Uwe Rathjen
    Date:           20.07.26
    Description:    Lists the whole machining tree - part operations, programs and operations - with each
                    activity's name, comment, tool and the same settings Export_Process_Table_Parameters reads.
                    Names and comments are set from template lists, program names built as K862D2008US01 and
                    renumbered in sequence, and program comments composed as TOOL DESCRIPTION TO 0.0MM
                    (M/C: -0.7MM), the machined figure coming from the operations and the stage from the job.
                    Job details are read from the CATPart name and the metal thickness from the design part.
                    Edits are staged beside the current values; nothing is written until Apply is pressed.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    wxPython
                    Catia V5 running with an open process document.
                    This script needs an open CATProcess document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.dmaps_interfaces.process_document import ProcessDocument
from pycatia.manufacturing_interfaces.manufacturing_setup import ManufacturingSetup
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pycatia.ppr_interfaces.ppr_document import PPRDocument
import wx
import wx.grid
import wx.lib.dialogs as dialogs
import ctypes
import json
import os
import re
import traceback

SCRIPT_NAME = "Manage_Program_Names_And_Comments"

# Default template lists, taken from program_templates.txt. User additions are saved to
# %APPDATA%\pycatia_scripts\<script name>\ so a fresh install works with no setup.
# Two entries carry an UPPER / LOWER prefix that the original list did not, so that every part
# classifies from its prefix and the offset rule needs no special cases:
#   LOWER FILLER      -> LOWER FILLER CAM
#   TRIM CAM POS_##   -> UPPER TRIM CAM POS_##
TEMPLATES = json.loads(r'''
{
  "die_parts": [
    "LOWER POST","LOWER BLANKHOLDER","LOWER PAD","LOWER STEELS","LOWER FILLER CAM","LOWER PUNCH","LOWER ASSY",
    "LOWER CAM","LOWER SCRAP CUTTER POS_##","UPPER DIE","UPPER CAP","UPPER PAD","UPPER TRIM STEELS",
    "UPPER FLANGE STEELS","UPPER RESTRIKE STEELS","UPPER ASSY","UPPER SCRAP CUTTER POS_##",
    "UPPER TRIM CAM POS_##","RESTRIKE CAM POS_##","FLANGE CAM POS_##","CAM PAD POS_##","ROLLER CAM POS_##"
  ],
  "machines": ["OKUMA","MECOF","HMC","DROOP","DROOP/OKUMA"],
  "part_operation_name": "DIE PART ( MACHINE )",
  "job_descriptions": [
    "FIRST CUT MACHINING","FIRST CUT MACHINING        ROUGHING","FIRST CUT MACHINING        FINISHING",
    "DIMENSIONAL CORRECTION","TRIM CORRECTION","TRIM STEEL ENTRY CORRECTION","BREAKLINE CHANGE",
    "PAD CLEARANCE","FULL RECUT - DROP ***mm AT M/C","FORM CORRECTION - LEAVE ON 0.*mm FOR SPOTTING",
    "FORM & TRIM CORRECTION","FORM & CAM TRIM CORRECTION","NESTING CUT","SCRIBED LINES ETCHING",
    "ENGINEERING CHANGE","Q-LOOP"
  ],
  "part_operation_comments": ["UPPER IS MASTER","METAL IS **.**MM","PROFILES ARE **.**MM"],
  "masters": ["UPPER","LOWER","BOTH"],
  "dividers": [
    "*** ROUGHING TO +2.0MM ***","*** ROUGHING TO +0.7MM ***","*** SEMI-FINISH TO +0.3MM ***",
    "*** FINISH TO 0.0MM ***","*** ADDITIONAL PROGRAMS ***","*** OPTIONAL PROGRAMS ***","*** Z CHECKS ***"
  ],
  "descriptions": [
    "Z-LEVEL ROUGHING","ROUGHING SWEEP","ROUGHING PENCIL","ROUGHING CONTOUR","OPTIMIZED ROUGHING SWEEP",
    "OPTIMIZED SEMI-FINISH SWEEP","SEMI-FINISH SWEEP","SEMI-FINISH CONTOUR","SEMI-FINISH PENCIL",
    "OPTIMIZED FINISH SWEEP","FINISH SWEEP","FINISH CONTOUR","FINISH SCRIBE",
    "Z CHECKS X DIR","Z CHECKS Y DIR","Z CHECKS"
  ],
  "tools": [
    "END MILL","SCRIBE TOOL","80 DEPO R8","63 DEPO R8","50 DEPO R8","32 DEPO R8","32BN","20BN","16BN",
    "12BN","10BN","8BN","6BN","4BN","20-R2 BULL"
  ],
  "die_numbers": ["D10","D15","D20","D25","D30","D35","D40","D45","D50","D55","D60"]
}
''')

# Machining stage each description belongs to, and the nominal stock left at that stage.
# The two roughing stages are different operations, not a choice: Z-level leaves +2.0, the
# later ball nose roughing sweep leaves +0.7.
STAGE_NOMINALS = {
    "Z-LEVEL ROUGHING": 2.0,
    "ROUGHING": 0.7,
    "SEMI FINISH": 0.3,
    "SEMI-FINISH": 0.3,
    "FINISH": 0.0,
    "Z CHECK": 0.0,                                                                                              #A check cuts nothing - it is at the finished face
}

# The stages in cutting order, for the dropdown. SEMI FINISH is left out - it is the same stage as
# SEMI-FINISH, spelled the way the older templates spelled it.
STAGE_ORDER = ("Z-LEVEL ROUGHING", "ROUGHING", "SEMI-FINISH", "FINISH", "Z CHECK")

ACTIVITY_SKIP = ("Start", "Stop")                                                                                #Not real operations

PLACEHOLDERS = ("**.**MM", "***MM", "0.*MM", "POS_##")                                                           #Matched case insensitively, longest first

REMEMBERED_SETTINGS = ("initial", "machine")                                                                     #All that survives between runs - the rest is read from the document

# The settings worth checking, matched on the parameter name the way Export_Process_Table_Parameters
# does. That script walks a fixed list of parameter indices; the indices move between operation
# types, so every parameter is scanned by name here and anything absent is reported as missing
# rather than left silently blank.
PARAMETER_COLUMNS = (
    ("Stepover", ("Maximum distance",)),
    ("MC Tolerance", ("Machining tolerance",)),
    ("Depth of Cut", ("Maximum depth of cut", "Depth of cut by level for Multi-Pas")),
    ("Offset on Part", ("Offset on part",)),
    ("Offset on Check", ("Offset on check",)),
    ("Depth of Cut by Level", ("Depth of cut by level for Multi-Pass",)),
)

PARAMETER_LABELS = tuple(label for label, _ in PARAMETER_COLUMNS)


'''
    This function turns an activity type into the short operation label.

    Named exactly as Export_Process_Table_Parameters does it, so the two scripts can be read
    side by side: ManufacturingM3xSweep is Sweep, and Bitangency is the pencil trace it really is.

    Inputs:
        activity_type   The activity type, e.g. "ManufacturingM3xSweep"

    output:
        The label, e.g. "Sweep"
'''
def operation_label(activity_type):
    label = (activity_type or "").replace("Manufacturing", "")
    if label == "M3xBitangency":
        return "PencilTrace"
    if label.startswith("M3x"):
        return label[3:]
    return label


'''
    This function reads a number out of a parameter value such as "0.3mm".

    Inputs:
        text            The parameter value as a string

    output:
        The number as a float, or None if there is not one in it
'''
def numeric_value(text):
    match = re.search(r"-?\d+(?:\.\d+)?", text or "")
    return float(match.group(0)) if match else None


'''
    This function reads the settings of one operation.

    Every parameter is walked once and matched on its name, so an operation type whose parameters
    sit at different indices still reports its settings.

    Inputs:
        activity        A manufacturing operation activity

    output:
        Tuple of (dict of label to value string, list of the labels that were not found)
'''
def read_operation_parameters(activity):
    values = {label: "" for label in PARAMETER_LABELS}

    try:
        parameters = activity.parameters
        count = parameters.count
    except Exception:
        return values, list(PARAMETER_LABELS)                                                                    #No parameters at all - everything is missing

    for index in range(count):
        try:
            parameter = parameters.item(index + 1)
            name = parameter.name
        except Exception:
            continue
        for label, needles in PARAMETER_COLUMNS:
            if values[label]:
                continue                                                                                         #First match wins, as in the export script
            if any(needle in name for needle in needles):
                try:
                    values[label] = parameter.value_as_string()
                except Exception:
                    pass

    missing = [label for label in PARAMETER_LABELS if not values[label]]
    return values, missing


'''
    This function turns a tool name from the document into the token used in comments.

    The diameter symbol is dropped so everything stays plain ASCII, and a ball nose closes up
    to match the sample comments - 32 BN is written 32BN. Multi word tools keep their spaces,
    so 32 DEPO R8 and 20-R2 BULL are left as they are.

    Inputs:
        raw             The tool name as CATIA holds it, e.g. "Ø 32 BN"

    output:
        The comment token, e.g. "32BN"
'''
def normalise_tool(raw):
    text = (raw or "").replace("Ø", " ").replace("ø", " ")
    text = re.sub(r"\s+", " ", text).strip().upper()
    text = re.sub(r"^T\d+\s+", "", text)                                                                          #Drop the tool number CATIA puts in front - T2 32 BN
    closed = re.fullmatch(r"(\d+(?:[.-]\w+)?)\s+BN", text)                                                        #Ball nose only - the sample comments close this one up
    if closed:
        return closed.group(1) + "BN"
    return text


'''
    This function works out which side of the die a part sits on.

    The UPPER / LOWER prefix decides it, with no exceptions. A part with no prefix - a roller,
    restrike or flange cam, or a cam pad - genuinely can be either, so it returns None and is
    asked for rather than guessed.

    Inputs:
        die_part        A die part name, e.g. "LOWER POST"

    output:
        "UPPER", "LOWER", or None when the name does not say
'''
def side_for_die_part(die_part):
    text = (die_part or "").upper().strip()
    if text.startswith("UPPER"):
        return "UPPER"
    if text.startswith("LOWER"):
        return "LOWER"
    return None


'''
    This function applies the master rule to a stage nominal.

    The master side is cut to nominal. The other side has the metal taken off it. BOTH means no
    metal comes off either side, so both are cut to nominal.

    Inputs:
        nominal         Stock left at this stage, e.g. 0.3
        side            "UPPER" or "LOWER" - the side this part sits on
        master          "UPPER", "LOWER" or "BOTH"
        metal           Metal thickness in mm

    output:
        The offset in mm, or None when the side is not known and the answer could be wrong by
        the full metal thickness
'''
def offset_for(nominal, side, master, metal):
    if nominal is None:
        return None
    if master == "BOTH":
        return nominal
    if side is None:
        return None                                                                                              #Never guess - a wrong side is wrong by the whole metal
    if side == master:
        return nominal
    return nominal - metal


'''
    This function writes an offset the way it appears in a comment.

    Inputs:
        offset          The offset in mm

    output:
        Text such as "+0.3MM", "0.0MM" or "-1.2MM"
'''
def format_offset(offset):
    if offset is None:
        return ""
    if offset > 0:
        return f"+{offset:.1f}MM"
    return f"{offset:.1f}MM"


'''
    This function composes a manufacturing program comment.

    Two different offsets are carried. The stage offset is what the stage always means - rough to
    +2.0 or +0.7, semi to +0.3, finish to 0.0 - and does not move when metal comes off. The
    machine offset is what the tool is actually driven to, which on a part that is not the master
    is the stage offset less the metal. Where the two differ the machine figure is spelled out:

        32BN FINISH SWEEP TO 0.0MM (M/C: -0.7MM)

    Where they are the same there is nothing to add, and the comment reads as it always has.

    Inputs:
        tool            The tool token, e.g. "32BN"
        description     The operation description, e.g. "FINISH SWEEP"
        stage_offset    The nominal for the stage in mm, or None to leave the "TO ..." off
        machine_offset  The offset actually machined in mm, or None if it is not known

    output:
        The comment, e.g. "32BN FINISH SWEEP TO 0.0MM (M/C: -0.7MM)"
'''
def compose_program_comment(tool, description, stage_offset, machine_offset=None):
    text = " ".join(part for part in (tool, description) if part)

    if stage_offset is None:
        stage_offset = machine_offset                                                                             #No stage to quote, so the machined figure is the only one

    if stage_offset is not None:
        text = f"{text} TO {format_offset(stage_offset)}"
    if machine_offset is not None and stage_offset is not None and abs(machine_offset - stage_offset) > 0.001:
        text = f"{text} (M/C: {format_offset(machine_offset)})"                                                   #Only worth saying when it differs
    return text.strip()


'''
    This function finds the placeholders in a template.

    Inputs:
        template        A template string

    output:
        List of the placeholders present, in the order they appear
'''
def placeholders_in(template):
    text = (template or "").upper()
    found = []
    for placeholder in PLACEHOLDERS:
        if placeholder in text:
            found.append(placeholder)
    return found


'''
    This function replaces a placeholder with the number the user gave.

    Inputs:
        template        The template text
        placeholder     The placeholder to replace, e.g. "**.**MM"
        value           The number to put in its place, without its unit

    output:
        The template with that placeholder replaced. The template's own spelling of the unit is
        kept, so "DROP ***mm" stays lower case while "METAL IS **.**MM" stays upper.
'''
def fill_placeholder(template, placeholder, value):
    def swap(match):
        return value + match.group(0)[-2:] if placeholder.endswith("MM") else value

    return re.sub(re.escape(placeholder), swap, template, flags=re.IGNORECASE)


'''
    This function loads the saved job settings.

    Inputs:
        settings_dir    The folder settings live in

    output:
        Dict of settings, with defaults for anything not saved yet
'''
def load_settings(settings_dir):
    settings = {"initial": "", "project": "", "die": "", "revision": "", "code": "", "master": "UPPER",
                "metal": "", "machine": "OKUMA", "pos": ""}
    path = os.path.join(settings_dir, "settings.json")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            saved = json.load(handle)
    except Exception:
        return settings                                                                                          #A missing or unreadable file just means defaults

    for key in REMEMBERED_SETTINGS:                                                                              #Older files may hold job values - ignore them
        if saved.get(key):
            settings[key] = saved[key]
    return settings


'''
    This function saves the settings that are remembered between runs.

    Only the programmer's initial and their usual machine are kept. Everything else - project,
    die, revision, master, metal - belongs to the document and is read from it every time. Keeping
    those would mean a part name that failed to parse silently inherited the last job's die
    number, which is the one thing the numbering must never do.

    Inputs:
        settings_dir    The folder settings live in
        settings        Dict of settings to take the remembered values from

    output:
        None
'''
def save_settings(settings_dir, settings):
    remembered = {key: settings.get(key, "") for key in REMEMBERED_SETTINGS}
    try:
        with open(os.path.join(settings_dir, "settings.json"), "w", encoding="utf-8") as handle:
            json.dump(remembered, handle, indent=2)
    except Exception:
        pass                                                                                                     #Settings are a convenience, never worth failing the run for


'''
    This function draws the window icon, so no image file has to ship alongside the script.

    A rounded blue tile carrying three bars - a list of names. Plain shapes rather than text, so
    it stays legible where Windows scales it down to 16 pixels for the title bar.

    output:
        A wx.Icon
'''
def _make_icon():
    size = 32
    bitmap = wx.Bitmap(size, size)
    dc = wx.MemoryDC(bitmap)

    mask_colour = wx.Colour(255, 0, 255)                                                                         #Not used in the drawing, so only the background is masked
    dc.SetBackground(wx.Brush(mask_colour))
    dc.Clear()

    dc.SetBrush(wx.Brush(wx.Colour(31, 78, 121)))
    dc.SetPen(wx.Pen(wx.Colour(31, 78, 121)))
    dc.DrawRoundedRectangle(2, 2, size - 4, size - 4, 5)

    dc.SetBrush(wx.Brush(wx.Colour(255, 255, 255)))
    dc.SetPen(wx.Pen(wx.Colour(255, 255, 255)))
    for row, width in enumerate((18, 14, 10)):                                                                   #Bars shorten down the list
        dc.DrawRectangle(7, 9 + row * 6, width, 3)

    dc.SelectObject(wx.NullBitmap)
    bitmap.SetMask(wx.Mask(bitmap, mask_colour))

    icon = wx.Icon()
    icon.CopyFromBitmap(bitmap)
    return icon


def _bring_to_front(window):
    u32 = ctypes.windll.user32
    hwnd = window.GetHandle()
    fg_hwnd = u32.GetForegroundWindow()
    fg_tid = u32.GetWindowThreadProcessId(fg_hwnd, None)
    our_tid = ctypes.windll.kernel32.GetCurrentThreadId()
    if fg_tid != our_tid:
        u32.AttachThreadInput(fg_tid, our_tid, True)
    u32.SetWindowLongW(hwnd, -20, u32.GetWindowLongW(hwnd, -20) | 0x0008)
    u32.BringWindowToTop(hwnd)
    u32.SetForegroundWindow(hwnd)
    if fg_tid != our_tid:
        u32.AttachThreadInput(fg_tid, our_tid, False)


'''
    This function works out which machining stage a description belongs to and how much stock it leaves.

    Inputs:
        description     An operation description, e.g. "SEMI FINISH SWEEP"

    output:
        Tuple of (stage name, nominal stock in mm), or (None, None) if the description is not recognised
'''
def stage_for_description(description):
    text = (description or "").upper().replace("_", " ")                                                          #Operations are named Z_CHECK_X_DIR, comments say Z CHECK
    if "Z-LEVEL" in text:                                                                                        #Anywhere in the text - ROUGHING Z-LEVEL reads the same way
        return "Z-LEVEL ROUGHING", STAGE_NOMINALS["Z-LEVEL ROUGHING"]
    for stage in ("Z CHECK", "SEMI FINISH", "SEMI-FINISH", "ROUGHING", "FINISH"):                                #Longest first - SEMI FINISH before FINISH
        if stage in text:
            return stage, STAGE_NOMINALS[stage]
    return None, None


'''
    This function reads the job number, die number and revision out of a CATPart file name.

    The name normally carries a job number as TJ###, and a die number as D##-**, D##_OP@@-** or
    OP##-**. Where only an OP number is present the die number can differ from it, so it is
    reported as unconfirmed rather than used.

    Inputs:
        part_name       The CATPart file name

    output:
        Dict with keys job, die, op, revision and confirmed. Values are None when not found.
'''
def parse_part_name(part_name):
    found = {"job": None, "die": None, "op": None, "revision": None, "confirmed": False}
    if not part_name:
        return found

    text = part_name.upper()

    job = re.search(r"TJ[\s_-]?(\d+)", text)
    if job:
        found["job"] = job.group(1)

    die = re.search(r"(?<![A-Z0-9])D[\s_-]?(\d{2})(?![0-9])"                                                     #\b fails here - _ is a word char
                    r"(?:[\s_-](?!OP)([A-Z0-9]{1,3})(?![A-Z0-9]))?", text)                                       #Revision sits straight after the die number
    if die:
        found["die"] = "D" + die.group(1)
        if die.group(2):
            found["revision"] = die.group(2)                                                                     #D##_** and D##-** both carry it here

    op = re.search(r"(?<![A-Z0-9])OP[\s_-]?(\d+)", text)
    if op:
        found["op"] = op.group(1)

    if not found["revision"]:
        tail = text[die.end():] if die else text                                                                 #Past the die, or the die itself reads as a revision
        revision = re.search(r"[-_](\w{1,3})$", tail)                                                            #Trailing -** / _**, e.g. after D##_OP@@
        if revision:
            found["revision"] = revision.group(1)

    found["confirmed"] = bool(found["die"])                                                                      #An OP number alone does not confirm the die
    return found


'''
    This function finds the CATPart name behind a part operation.

    The activity handed back by children_activities.item() is a plain Activity, which carries no
    product of its own - the part is reached by treating the same com object as the
    ManufacturingSetup it really is. Several routes are tried and the one that worked is
    reported, because a setup with no design part linked still has to say so rather than fall
    back to something that only looks like a file name.

    Inputs:
        part_op         The part operation activity

    output:
        Tuple of (part name or None, description of the route that found it)
'''
def find_part_name(part_op):

    def try_route(label, getter):
        try:
            value = getter()
            if value:
                return str(value).strip(), label
        except Exception:
            pass
        return None, None

    setup = ManufacturingSetup(part_op.com_object)                                                                #Same com object, properly typed

    product = None
    try:
        product = setup.get_product_instance()
    except Exception:
        product = None

    if product is not None:
        full_name, label = try_route("setup product FullName", lambda: product.full_name)                         #Full path of the CATPart on disk
        if full_name:
            return os.path.splitext(os.path.basename(full_name))[0], label

        name, label = try_route("setup product PartNumber", lambda: product.part_number)
        if name:
            return name, label

        name, label = try_route("setup product Name", lambda: product.name)
        if name:
            return name, label

    name, label = try_route("setup GetPartName", lambda: setup.get_part_name())                                   #Design part name held by the setup
    if name:
        return name, label

    return None, "no design part linked to this setup"


'''
    This function reads an activity's comment, treating CATIA's placeholder as no comment at all.

    Inputs:
        activity        Any activity

    output:
        The comment, or an empty string where CATIA holds its "No Description" placeholder
'''
def read_comment(activity):
    try:
        comment = activity.description or ""
    except Exception:
        return ""
    return "" if "No Description" in comment else comment


'''
    This function reads the master side and metal thickness out of a piece of text.

    Both are stated in the design part, in the name of the body holding the master panel, as
    "MASTER PANEL RH CP12 REV47 - UPPER IS MASTER - METAL IS 0.7mm". The same wording turns up in
    part operation comments, so one reader serves both.

    Inputs:
        comment         Any text - a body name, a geometric set name or a comment

    output:
        Dict with keys master and metal, either of which may be None
'''
def parse_master_and_metal(comment):
    found = {"master": None, "metal": None}
    text = (comment or "").upper()

    master = (re.search(r"\b(UPPER|LOWER|BOTH)\b[\s\-_=:]*(?:IS[\s\-_=:]+)?MASTER", text)                         #UPPER IS MASTER, UPPER MASTER
              or re.search(r"\bMASTER\b[\s\-_=:]*(?:IS[\s\-_=:]+)?(UPPER|LOWER|BOTH)\b", text))                   #MASTER IS UPPER
    if master:
        found["master"] = master.group(1)

    metal = (re.search(r"\bMETAL\b[^0-9]{0,15}(\d+(?:\.\d+)?)\s*MM", text)                                        #METAL IS 0.7mm, METAL - 0.7MM, METAL 0.7
             or re.search(r"(\d+(?:\.\d+)?)\s*MM[\s\-_=:]*METAL\b", text))                                        #0.7MM METAL
    if metal:
        found["metal"] = metal.group(1)

    return found


'''
    This function says whether a program is a divider rather than a real program.

    A divider is a program that carries a heading instead of machining anything, written between
    stars. It takes no program number.

    Inputs:
        name            The program name

    output:
        True where the name is a heading
'''
def is_divider(name):
    return (name or "").strip().startswith("***")


'''
    This function builds a manufacturing program name.

        K    862    D20   08    US    01
        |    |      |     |     |     +-- program number, the part renumbering rewrites
        |    |      |     |     +-------- die part code
        |    |      |     +-------------- revision
        |    |      +-------------------- die number
        |    +--------------------------- project number
        +-------------------------------- programmer initial

    Inputs:
        initial         Programmer initial
        project         Project number
        die             Die number, e.g. "D20"
        revision        Revision number
        code            Die part code, e.g. "US"
        number          Program number

    output:
        The name, e.g. "K862D2008US01"
'''
def program_name_token(initial, project, die, revision, code, number):
    return f"{initial}{project}{die}{revision}{code}{int(number):02d}".upper()


'''
    This function suggests the die part code from a die part name.

    The first letter of the first and last word gives the codes in use - LOWER POST is LP and
    UPPER DIRECT RESTRIKE STEELS is US. It is only a suggestion and stays editable, because a
    code is a shop convention rather than something that can be derived with certainty.

    Inputs:
        die_part        The die part name

    output:
        A two letter code, or an empty string when there is nothing to go on
'''
def die_part_code(die_part):
    text = re.sub(r"[_\-]+", " ", (die_part or "").upper())
    text = re.sub(r"\(.*?\)", " ", text)                                                                          #Drop the machine in brackets
    words = [word for word in text.split() if word.isalpha() and word != "POS"]                                   #POS_## is a position, not part of the name
    if not words:
        return ""
    if len(words) == 1:
        return words[0][:2]
    return words[0][0] + words[-1][0]


'''
    This function reads the trailing program number off a name.

    Inputs:
        name            A program name, e.g. "K862D2008US01"

    output:
        Tuple of (the name without its trailing number, the number or None)
'''
def split_program_number(name):
    match = re.search(r"(\d+)\s*$", name or "")
    if not match:
        return (name or ""), None
    return (name or "")[:match.start(1)], int(match.group(1))


'''
    This function builds the part of a program name that comes before the number.

    Inputs:
        settings        The job settings

    output:
        The stem, e.g. "K862D2008US", or an empty string where the job is not filled in
'''
def job_stem(settings):
    pieces = (settings.get("initial", ""), settings.get("project", ""), settings.get("die", ""),
              settings.get("revision", ""), settings.get("code", ""))
    return "".join(pieces).upper() if all(pieces) else ""


'''
    This function reads a program's number, but only where the name is one of this job's.

    A program CATIA named itself - Manufacturing Program.19 - ends in the number of the activity
    CATIA has created, which has nothing to do with the program numbering. Taking it would suggest
    19 where the job has only reached 09, so a number is read only from a name built on this job's
    stem.

    Inputs:
        name            The program name
        stem            The job stem, e.g. "K862D2008US"

    output:
        The program number, or None where this name does not carry one
'''
def program_number_of(name, stem):
    text = (name or "").strip()
    if not stem or is_divider(text) or not text.upper().startswith(stem.upper()):
        return None
    tail = text[len(stem):]
    return int(tail) if tail.isdigit() else None


'''
    This function works out the next free program number.

    Inputs:
        rows            All rows read from the tree
        part_op_row     The part operation to number within, or None for the whole process
        stem            The job stem

    output:
        One past the highest number in use, or 1 where none are numbered yet
'''
def next_program_number(rows, part_op_row, stem):
    numbers = []
    for row in rows:
        if row["kind"] != "Program":
            continue
        if part_op_row is not None and row.get("parent") is not part_op_row:
            continue
        number = program_number_of(row["name"], stem)
        if number is not None:
            numbers.append(number)
    return max(numbers) + 1 if numbers else 1


'''
    This function collects the body and geometric set names of a design part.

    Inputs:
        part            The Part behind a part operation

    output:
        List of names, geometric sets included at any depth
'''
def collect_feature_names(part):
    names = []

    def walk(collection):
        try:
            count = collection.count
        except Exception:
            return
        for index in range(count):
            try:
                item = collection.item(index + 1)
                names.append(item.name)
            except Exception:
                continue
            try:
                walk(item.hybrid_bodies)                                                                          #Geometric sets nest
            except Exception:
                pass

    try:
        walk(part.bodies)
    except Exception:
        pass
    try:
        walk(part.hybrid_bodies)
    except Exception:
        pass
    return names


'''
    This function reads the master side and metal thickness from the design part.

    The part is the authority for metal thickness - it is stated in the name of the body holding
    the master panel. Metal belongs to the panel being formed, so it is read per part operation
    rather than once for the job: two die parts with different metal each get their own, and no
    choice has to be made between them.

    Where a part names more than one thickness, every one found is handed back with the name it
    came from so the user can say which applies to this part operation. Nothing is picked here.

    Inputs:
        part_op         The part operation activity

    output:
        Dict with keys master, metal, masters, metals and note. metals maps each thickness to the
        names that stated it; metal is filled in only where there was just the one.
'''
def read_part_master_and_metal(part_op):
    found = {"master": None, "metal": None, "masters": {}, "metals": {}, "note": ""}

    try:
        setup = ManufacturingSetup(part_op.com_object)
        document = setup.get_product_instance().reference_product.parent
        part = PartDocument(document.com_object).part
    except Exception as error:
        found["note"] = f"design part could not be opened ({error})"
        return found

    for name in collect_feature_names(part):
        stated = parse_master_and_metal(name)
        if stated["master"]:
            found["masters"].setdefault(stated["master"], []).append(name)
        if stated["metal"]:
            found["metals"].setdefault(stated["metal"], []).append(name)

    notes = []
    if len(found["metals"]) == 1:
        found["metal"] = next(iter(found["metals"]))
    elif len(found["metals"]) > 1:
        notes.append("this part names " + ", ".join(f"{value}mm" for value in sorted(found["metals"]))
                     + " - pick the one that applies")
    else:
        notes.append("no metal thickness found in the part")

    if len(found["masters"]) == 1:
        found["master"] = next(iter(found["masters"]))
    elif len(found["masters"]) > 1:
        notes.append("this part names more than one master - " + ", ".join(sorted(found["masters"])))
    else:
        notes.append("no master found in the part")

    found["note"] = "; ".join(notes)
    return found


'''
    This function works out the offset that describes a whole program.

    A program's comment carries one offset, so the operations under it have to agree. Where they
    do not, the disagreement is reported instead of one of them being picked silently.

    Inputs:
        rows            The rows read so far
        program_row     The program whose operations should be looked at

    output:
        Tuple of (offset or None, the attribute that answered or a note about the disagreement)
'''
def program_offset(rows, program_row):
    offsets = [row["offset"] for row in rows
               if row.get("parent") is program_row and row.get("offset") is not None]
    if not offsets:
        return None, ""

    attribute = next((row["offset_attribute"] for row in rows
                      if row.get("parent") is program_row and row.get("offset") is not None), "")
    unique = sorted(set(offsets))
    if len(unique) > 1:
        return unique[0], "operations disagree: " + ", ".join(f"{value:+.1f}" for value in unique)
    return unique[0], attribute


'''
    This function walks the machining tree and returns one row per activity.

    Inputs:
        ppr_doc         The PPRDocument of the active process document

    output:
        List of dicts with keys level, kind, name, comment, tool, activity_type
'''
def read_tree(ppr_doc):
    rows = []
    processes = ppr_doc.processes

    for process_index in range(processes.count):
        process = processes.item(process_index + 1)
        part_operations = process.children_activities

        for part_op_index in range(part_operations.count):
            part_op = part_operations.item(part_op_index + 1)
            if part_op.type != "ManufacturingSetup":
                continue

            part_name, route = find_part_name(part_op)
            stated = read_part_master_and_metal(part_op)                                                          #The part is the authority for metal
            rows.append({
                "level": 0,
                "kind": "Part Operation",
                "name": part_op.name,
                "comment": read_comment(part_op),
                "tool": "",
                "activity_type": part_op.type,
                "part_name": part_name or "",
                "part_name_route": route,
                "activity": part_op,
                "parent": None,
                "master": stated["master"],
                "metal": stated["metal"],
                "metals": stated["metals"],
                "masters": stated["masters"],
                "metal_note": stated["note"],
                "new_name": "",
                "new_comment": "",
                "offset": None,
                "offset_attribute": "",
            })
            part_op_row = rows[-1]

            programs = part_op.children_activities
            for program_index in range(programs.count):
                program = programs.item(program_index + 1)
                if program.type != "ManufacturingProgram":
                    continue

                rows.append({
                    "level": 1,
                    "kind": "Program",
                    "name": program.name,
                    "comment": read_comment(program),
                    "tool": "",
                    "activity_type": program.type,
                    "part_name": "",
                    "part_name_route": "",
                    "activity": program,
                    "parent": part_op_row,
                    "new_name": "",
                    "new_comment": "",
                    "offset": None,
                    "offset_attribute": "",
                })
                program_row = rows[-1]

                current_tool = ""                                                                                #A tool change applies to the operations after it
                first_tool = ""
                activities = program.children_activities
                for activity_index in range(activities.count):
                    activity = activities.item(activity_index + 1)

                    if activity.type == "ToolChange":
                        try:
                            current_tool = normalise_tool(activity.resources.item(1).name.split("(")[0])
                        except Exception:
                            current_tool = ""
                        if not first_tool:
                            first_tool = current_tool
                        continue

                    if activity.type in ACTIVITY_SKIP:
                        continue

                    parameters, missing = read_operation_parameters(activity)
                    offset = numeric_value(parameters["Offset on Part"])                                          #What this operation actually leaves on
                    rows.append({
                        "level": 2,
                        "kind": "Operation",
                        "name": activity.name,
                        "comment": read_comment(activity),
                        "tool": current_tool,
                        "activity_type": activity.type,
                        "part_name": "",
                        "part_name_route": "",
                        "activity": activity,
                        "parent": program_row,
                        "new_name": "",
                        "new_comment": "",
                        "offset": offset,
                        "offset_attribute": "Offset on part" if offset is not None else "",
                        "parameters": parameters,
                        "missing": missing,
                    })

                program_row["tool"] = first_tool                                                                 #Show the program's first tool on its own row
                program_row["offset"], program_row["offset_attribute"] = program_offset(rows, program_row)

    calibrate_missing(rows)
    return rows


'''
    This function decides which settings are genuinely missing.

    An operation type that never carries a setting has not lost it - a pencil trace has no
    stepover. So a setting only counts as missing when another operation of the same type in
    this process does have one, which keeps the report free of noise without a hard coded list
    of what each type is supposed to own.

    Inputs:
        rows            The rows read from the tree, altered in place

    output:
        None
'''
def calibrate_missing(rows):
    operations = [row for row in rows if row["kind"] == "Operation"]

    expected = {}
    for row in operations:
        label_set = expected.setdefault(operation_label(row["activity_type"]), set())
        for label in PARAMETER_LABELS:
            if row["parameters"].get(label):
                label_set.add(label)

    for row in operations:
        wanted = expected.get(operation_label(row["activity_type"]), set())
        row["missing"] = [label for label in PARAMETER_LABELS
                          if label in wanted and not row["parameters"].get(label)]


'''
    This function asks which metal thickness applies to a part operation.

    A die can hold parts of different thickness, and a part can name more than one, so the choice
    is offered with the name each came from rather than decided in code.

    Inputs:
        parent          The parent window
        row             The part operation row

    output:
        None - the row is updated in place
'''
def choose_metal(parent, row):
    metals = row.get("metals") or {}
    if len(metals) < 2:
        return

    values = sorted(metals, key=lambda value: float(value))
    choices = [f"{value}mm   -   {metals[value][0]}" for value in values]
    dialog = wx.SingleChoiceDialog(
        parent,
        f"{row['name']}\n\nThis part names more than one metal thickness.\n"
        f"Which applies to this part operation?",
        "Metal thickness", choices)
    dialog.SetSize((760, 320))
    if dialog.ShowModal() == wx.ID_OK:
        row["metal"] = values[dialog.GetSelection()]
        row["metal_note"] = f"{row['metal']}mm chosen from {len(values)} stated in the part"
    dialog.Destroy()


class EditDialog(wx.Dialog):
    """Gives one activity a name and a comment from the template lists."""

    PREVIEW_LINES = 9                                                                                            #The most the preview ever shows, for a program

    def __init__(self, parent, row, settings, rows=None):
        super().__init__(parent, title=f"Set {row['kind'].lower()} - {row['name']}",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.row = row
        self.settings = settings
        self.rows = rows or [row]                                                                                #Needed to see which numbers are already in use
        self.new_name = row["new_name"] or ""
        self.new_comment = row["new_comment"] or ""
        self.current_name = row["name"] or ""                                                                    #What is on the activity now
        self.current_comment = row["comment"] or ""

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        summary = f"Now:  {row['name']}\n      {row['comment'] or '(no comment)'}"
        if row["kind"] == "Operation":
            settings_text = "  ".join(f"{label} {row['parameters'].get(label) or '?'}"
                                      for label in PARAMETER_LABELS)
            summary += f"\n{operation_label(row['activity_type'])}:  {settings_text}"
            if row["missing"]:
                summary += f"\n      missing: {', '.join(row['missing'])}"
        current = wx.StaticText(panel, label=summary)
        current.SetFont(wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        vbox.Add(current, 0, wx.ALL, 8)
        vbox.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.ALL, 4)

        grid_sizer = wx.FlexGridSizer(0, 2, 6, 8)
        grid_sizer.AddGrowableCol(1, 1)

        self.name_choice = wx.ComboBox(panel, choices=[""] + self._name_templates(), style=wx.CB_DROPDOWN)
        self.name_choice.SetValue(self.new_name or self.current_name)                                            #Edit from what is there, not from blank
        grid_sizer.Add(wx.StaticText(panel, label="Name"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid_sizer.Add(self.name_choice, 1, wx.EXPAND)

        if row["kind"] == "Part Operation":
            in_brackets = re.search(r"\(([^)]*)\)", self.current_name)                                            #The machine the name already carries
            self.machine_choice = wx.ComboBox(panel, choices=[""] + TEMPLATES["machines"], style=wx.CB_DROPDOWN)
            self.machine_choice.SetValue(in_brackets.group(1).strip() if in_brackets
                                         else settings.get("machine", ""))
            grid_sizer.Add(wx.StaticText(panel, label="Machine"), 0, wx.ALIGN_CENTER_VERTICAL)
            grid_sizer.Add(self.machine_choice, 1, wx.EXPAND)                                                    #Fills the MACHINE half of DIE PART ( MACHINE )
        else:
            self.machine_choice = None

        self.comment_choice = wx.ComboBox(panel, choices=[""] + self._comment_templates(), style=wx.CB_DROPDOWN)
        self.comment_choice.SetValue(self.new_comment or self.current_comment)
        grid_sizer.Add(wx.StaticText(panel, label="Comment"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid_sizer.Add(self.comment_choice, 1, wx.EXPAND)

        vbox.Add(grid_sizer, 0, wx.EXPAND | wx.ALL, 8)

        if row["kind"] == "Program":
            vbox.Add(self._name_builder(panel), 0, wx.EXPAND | wx.ALL, 8)                                        #K862D2008US01
            vbox.Add(self._composer(panel), 0, wx.EXPAND | wx.ALL, 8)                                            #TOOL DESCRIPTION TO OFFSETMM

        self.preview = wx.StaticText(panel, label="")
        self.preview.SetFont(wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        vbox.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.ALL, 4)
        vbox.Add(self.preview, 0, wx.EXPAND | wx.ALL, 8)
        vbox.AddStretchSpacer()                                                                                  #Keeps the buttons at the bottom when resized

        buttons = wx.StdDialogButtonSizer()
        ok_button = wx.Button(panel, wx.ID_OK, "Stage")
        ok_button.SetDefault()
        buttons.AddButton(ok_button)
        buttons.AddButton(wx.Button(panel, wx.ID_CANCEL))
        buttons.Realize()
        vbox.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 8)

        panel.SetSizer(vbox)

        self.name_choice.Bind(wx.EVT_TEXT, self._on_change)
        self.comment_choice.Bind(wx.EVT_TEXT, self._on_change)
        if self.machine_choice:
            self.machine_choice.Bind(wx.EVT_TEXT, self._on_change)
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)

        self._update_preview()                                                                                   #Must come first - the preview is empty until it runs
        self._fit_to_content()
        self.Center()

    '''
        This function sizes the dialog around whatever it is showing.

        The preview is several lines for a program and two for an operation, and it is only
        filled once the boxes have been read, so the dialog can only be measured after that.
        Sizing it before would leave the Stage button below the bottom edge.
    '''
    def _fit_to_content(self):
        self.preview.Wrap(-1)
        self.GetSizer().Layout() if self.GetSizer() else None

        panel = self.GetChildren()[0]
        panel.GetSizer().Layout()
        best = panel.GetSizer().GetMinSize()

        border = self.GetSize() - self.GetClientSize()                                                           #Title bar and frame
        width = max(700, best.width + border.width)
        height = best.height + border.height + 12

        screen = wx.Display(0).GetClientArea()
        self.SetSize((min(width, screen.width), min(height, screen.height)))
        self.SetMinSize((min(width, screen.width), min(height, screen.height)))
        self.Layout()

    '''
        This function builds the program name from the job settings and a program number.
    '''
    def _name_builder(self, panel):
        box = wx.StaticBoxSizer(wx.HORIZONTAL, panel, "Build program name")

        stem = job_stem(self.settings)
        current_number = program_number_of(self.row["name"], stem)                                                #None where CATIA named the program
        if current_number is None:
            part_op = self.row
            while part_op and part_op["kind"] != "Part Operation":
                part_op = part_op["parent"]
            current_number = next_program_number(self.rows, part_op, stem)                                        #Carry on from the highest in use

        self.number_text = wx.TextCtrl(panel, value=str(current_number), size=(50, -1))

        box.Add(wx.StaticText(panel, label="Program number"), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 6)
        box.Add(self.number_text, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 6)

        self.built_name = wx.StaticText(panel, label="")
        self.built_name.SetFont(wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        box.Add(self.built_name, 1, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 12)

        use_button = wx.Button(panel, label="Use as name")
        use_button.Bind(wx.EVT_BUTTON, self._on_use_built_name)
        box.Add(use_button, 0, wx.LEFT, 6)

        self.number_text.Bind(wx.EVT_TEXT, self._on_change)
        return box

    '''
        This function works out the program name the job settings would give.

        output:
            The name, or an empty string where a piece of the job is missing
    '''
    def _built_name(self):
        try:
            number = int(self.number_text.GetValue().strip())
        except ValueError:
            return ""
        pieces = (self.settings.get("initial", ""), self.settings.get("project", ""),
                  self.settings.get("die", ""), self.settings.get("revision", ""),
                  self.settings.get("code", ""))
        if not all(pieces):
            return ""
        return program_name_token(*pieces, number)

    def _on_use_built_name(self, event):
        built = self._built_name()
        if not built:
            wx.MessageBox("Fill in initial, project, die, revision and code in the Job bar first.",
                          "Program name", wx.OK | wx.ICON_INFORMATION, self)
            return
        self.name_choice.SetValue(built)
        self._update_preview()

    '''
        This function builds the tool / description / offset composer for a program comment.
    '''
    def _composer(self, panel):
        box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Compose comment")
        inner = wx.FlexGridSizer(0, 2, 6, 8)
        inner.AddGrowableCol(1, 1)

        detected = self.row["tool"] or ""
        self.tool_choice = wx.ComboBox(panel, choices=[""] + TEMPLATES["tools"], style=wx.CB_DROPDOWN)
        self.tool_choice.SetValue(detected)
        label = "Tool (from tool change)" if detected else "Tool (none detected)"
        inner.Add(wx.StaticText(panel, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
        inner.Add(self.tool_choice, 1, wx.EXPAND)

        self.description_choice = wx.ComboBox(panel, choices=[""] + TEMPLATES["descriptions"], style=wx.CB_DROPDOWN)
        inner.Add(wx.StaticText(panel, label="Description"), 0, wx.ALIGN_CENTER_VERTICAL)
        inner.Add(self.description_choice, 1, wx.EXPAND)

        detected_stage, detected_nominal = stage_for_description(self.row["comment"] or self.row["name"])
        self.stage_choice = wx.ComboBox(panel, choices=[""] + list(STAGE_ORDER), style=wx.CB_DROPDOWN)
        if detected_stage:
            self.stage_choice.SetValue(detected_stage)                                                           #What the program already reads as
        inner.Add(wx.StaticText(panel, label="Stage"), 0, wx.ALIGN_CENTER_VERTICAL)
        inner.Add(self.stage_choice, 1, wx.EXPAND)

        offsets = [f"{STAGE_NOMINALS[stage]:.1f}" for stage in STAGE_ORDER]
        self.stage_text = wx.ComboBox(panel, choices=sorted(set(offsets), key=float, reverse=True),              #What the stage always means
                                      style=wx.CB_DROPDOWN)
        if detected_nominal is not None:
            self.stage_text.SetValue(f"{detected_nominal:.1f}")
        inner.Add(wx.StaticText(panel, label="Stage offset mm (TO)"), 0, wx.ALIGN_CENTER_VERTICAL)
        inner.Add(self.stage_text, 1, wx.EXPAND)

        measured = self.row.get("offset")
        self.offset_text = wx.TextCtrl(panel)                                                                    #What the tool is actually driven to
        if measured is not None:
            self.offset_text.SetValue(f"{measured:.1f}")
            offset_label = "M/C offset mm (from operations)"
        else:
            side, ruled, note = self._offset_context(self.row["comment"] or self.row["name"])                    #Nothing measured - fall back to the rule
            if ruled is not None:
                self.offset_text.SetValue(f"{ruled:.1f}")
                offset_label = "M/C offset mm (from the stage rule)"
            else:
                offset_label = "M/C offset mm"
        inner.Add(wx.StaticText(panel, label=offset_label), 0, wx.ALIGN_CENTER_VERTICAL)
        inner.Add(self.offset_text, 1, wx.EXPAND)

        self.compose_button = wx.Button(panel, label="Build comment")
        inner.Add(wx.StaticText(panel, label=""), 0)
        inner.Add(self.compose_button, 0)

        box.Add(inner, 0, wx.EXPAND | wx.ALL, 6)

        self.tool_choice.Bind(wx.EVT_TEXT, self._on_change)
        self.description_choice.Bind(wx.EVT_TEXT, self._on_description)
        self.stage_choice.Bind(wx.EVT_TEXT, self._on_stage)
        self.stage_text.Bind(wx.EVT_TEXT, self._on_change)
        self.offset_text.Bind(wx.EVT_TEXT, self._on_change)
        self.compose_button.Bind(wx.EVT_BUTTON, self._on_compose)
        return box

    '''
        This function lists the name templates that suit the kind of row being edited.
    '''
    def _name_templates(self):
        if self.row["kind"] == "Part Operation":
            return TEMPLATES["die_parts"]
        if self.row["kind"] == "Program":
            return TEMPLATES["dividers"]                                                                         #A divider is a program carrying a heading
        return TEMPLATES["descriptions"]

    '''
        This function lists the comment templates that suit the kind of row being edited.
    '''
    def _comment_templates(self):
        if self.row["kind"] == "Part Operation":
            return TEMPLATES["job_descriptions"] + TEMPLATES["part_operation_comments"]
        return TEMPLATES["descriptions"]

    '''
        This function works out the side and offset that apply to the row being edited.

        output:
            Tuple of (side or None, offset or None, note explaining the offset)
    '''
    def _offset_context(self, description):
        part_op = self.row
        while part_op and part_op["kind"] != "Part Operation":
            part_op = part_op["parent"]

        side = side_for_die_part(part_op["name"]) if part_op else None
        if side is None and part_op:
            side = part_op.get("side")                                                                           #Answered once per job for prefix-less cams
        if side is None and self.row["kind"] == "Part Operation":
            side = side_for_die_part(self.name_choice.GetValue())

        stage, nominal = stage_for_description(description)
        if nominal is None:
            return side, None, "no stage in the description"

        master = (part_op.get("master") if part_op else None) or self.settings.get("master", "UPPER")
        metal_text = (part_op.get("metal") if part_op else None)                                                  #Read from this part, not from the job bar
        if metal_text is None:
            note = (part_op or {}).get("metal_note") or "no metal thickness for this part"
            return side, None, f"{stage} +{nominal} - {note}, so no offset"

        try:
            metal = float(metal_text)
        except ValueError:
            return side, None, f"{stage} +{nominal} - metal '{metal_text}' is not a number, so no offset"

        offset = offset_for(nominal, side, master, metal)
        if offset is None:
            return side, None, f"{stage} +{nominal} - side of this part is not known, so no offset"
        if master == "BOTH":
            return side, offset, f"{stage} nominal {nominal:+.1f}, master BOTH - nominal both sides"
        if side == master:
            return side, offset, f"{stage} nominal {nominal:+.1f}, {side} is master - nominal"
        return side, offset, f"{stage} nominal {nominal:+.1f}, {side} is not master - less {metal} metal"

    '''
        This function fills the stage offset when a stage is picked by hand.
    '''
    def _on_stage(self, event):
        nominal = STAGE_NOMINALS.get(self.stage_choice.GetValue().strip().upper())
        if nominal is not None:
            self.stage_text.SetValue(f"{nominal:.1f}")
        self._update_preview()
        event.Skip()

    def _on_description(self, event):
        stage, nominal = stage_for_description(self.description_choice.GetValue())
        if stage:
            self.stage_choice.SetValue(stage)                                                                    #The description says which stage it is
        if nominal is not None:
            self.stage_text.SetValue(f"{nominal:.1f}")                                                           #The stage offset does not move when metal comes off

        if self.row.get("offset") is None:                                                                       #Only fall back to the rule where the operations gave nothing
            side, offset, note = self._offset_context(self.description_choice.GetValue())
            if offset is not None:
                self.offset_text.SetValue(f"{offset:.1f}")                                                       #Still editable - not every job uses every stage
        self._update_preview()
        event.Skip()

    '''
        This function reads one of the offset boxes.

        output:
            Tuple of (value or None, True if it was readable)
    '''
    def _read_offset(self, field, label, quiet=False):
        text = field.GetValue().strip()
        if not text:
            return None, True
        try:
            return float(text), True
        except ValueError:
            if not quiet:                                                                                        #The preview redraws on every keystroke - no warning there
                wx.MessageBox(f"'{text}' is not a number.", label, wx.OK | wx.ICON_WARNING, self)
            return None, False

    def _on_compose(self, event):
        stage_offset, ok = self._read_offset(self.stage_text, "Stage offset")
        if not ok:
            return
        machine_offset, ok = self._read_offset(self.offset_text, "M/C offset")
        if not ok:
            return
        self.comment_choice.SetValue(
            compose_program_comment(self.tool_choice.GetValue().strip(),
                                    self.description_choice.GetValue().strip(),
                                    stage_offset, machine_offset))
        self._update_preview()

    def _on_change(self, event):
        self._update_preview()
        event.Skip()

    '''
        This function works out the name the boxes describe.

        A part operation name is DIE PART ( MACHINE ), but only where the box holds a bare die
        part. A name that already carries its machine in brackets is left exactly as it is, so
        opening a part operation and pressing Stage cannot reformat a name that was already right.

        output:
            The name
    '''
    def _composed_name(self):
        name = self.name_choice.GetValue().strip()
        if self.machine_choice is None or not name or "(" in name:
            return name
        machine = self.machine_choice.GetValue().strip()
        return TEMPLATES["part_operation_name"].replace("DIE PART", name).replace("MACHINE", machine)

    def _update_preview(self):
        name = self._composed_name()

        comment = self.comment_choice.GetValue().strip()
        lines = [f"Name    : {name or '(cleared - will not be written)'}"
                 + ("   unchanged" if name == self.current_name else ""),
                 f"Comment : {comment or '(cleared - will not be written)'}"
                 + ("   unchanged" if comment == self.current_comment else "")]

        if self.row["kind"] == "Program":
            built = self._built_name()
            self.built_name.SetLabel(built or "fill Initial, Project, Die, Rev and Code in the Job bar")

        if self.row["kind"] == "Program":
            side, offset, note = self._offset_context(self.description_choice.GetValue())
            measured = self.row.get("offset")
            lines.append("")
            lines.append(f"Side    : {side or 'not known'}")
            stage = self.stage_choice.GetValue().strip() or None
            nominal, _ = self._read_offset(self.stage_text, "Stage offset", quiet=True)
            lines.append(f"Stage   : {stage or 'not known'}"
                         + ("" if nominal is None else f", TO {format_offset(nominal)}"))
            if measured is None:
                lines.append(f"M/C     : from the stage rule - {note}")
            else:
                lines.append(f"M/C     : {format_offset(measured)} read from the operations [Offset on part]")
                if offset is not None and abs(offset - measured) > 0.001:
                    lines.append(f"          the stage rule would give {format_offset(offset)} - the operations win")

        lines.append("")
        lines.append("Placeholders are asked for when you press Stage." if
                     placeholders_in(name) or placeholders_in(self.comment_choice.GetValue())
                     else "Nothing is written until Apply.")

        while len(lines) < self.PREVIEW_LINES:                                                                   #Fixed height, so the dialog never has to resize
            lines.append("")
        self.preview.SetLabel("\n".join(lines[:self.PREVIEW_LINES]))

    '''
        This function asks for any placeholder numbers, then stages the result.
    '''
    def _on_ok(self, event):
        name = self._composed_name()
        comment = self.comment_choice.GetValue().strip()

        name = self._resolve_placeholders(name, "name")
        if name is None:
            return
        comment = self._resolve_placeholders(comment, "comment")
        if comment is None:
            return

        self.new_name = "" if name == self.current_name else name                                                 #Only what actually differs is staged
        self.new_comment = "" if comment == self.current_comment else comment
        if self.machine_choice is not None:
            self.settings["machine"] = self.machine_choice.GetValue().strip()
        event.Skip()

    '''
        This function prompts for each placeholder in a template.

        output:
            The filled text, or None if the user cancelled
    '''
    def _resolve_placeholders(self, text, what):
        for placeholder in placeholders_in(text):
            default = self.settings.get("pos", "") if placeholder == "POS_##" else ""
            prompt = wx.TextEntryDialog(self, f"Value for {placeholder} in the {what}:", "Placeholder", default)
            if prompt.ShowModal() != wx.ID_OK:
                prompt.Destroy()
                return None
            value = prompt.GetValue().strip()
            prompt.Destroy()
            if placeholder == "POS_##":
                self.settings["pos"] = value
                text = fill_placeholder(text, "POS_##", f"POS_{value}")
            else:
                text = fill_placeholder(text, placeholder, value)
        return text


class RenumberDialog(wx.Dialog):
    """Renumbers the programs, in sequence from a starting number or by hand."""

    def __init__(self, parent, program_rows, settings):
        super().__init__(parent, title="Renumber programs", size=(820, 560))
        self.program_rows = program_rows
        self.settings = settings

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        top = wx.BoxSizer(wx.HORIZONTAL)
        top.Add(wx.StaticText(panel, label="Start at"), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 6)
        self.start_text = wx.TextCtrl(panel, value="1", size=(50, -1))
        top.Add(self.start_text, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 6)

        top.Add(wx.StaticText(panel, label="Step"), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 12)
        self.step_text = wx.TextCtrl(panel, value="1", size=(50, -1))
        top.Add(self.step_text, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 6)

        self.rebuild_check = wx.CheckBox(panel, label="Rebuild the whole name from the job settings")
        self.rebuild_check.SetValue(True)                                                                        #Off leaves the name alone but for its number
        top.Add(self.rebuild_check, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 16)

        sequence_button = wx.Button(panel, label="Number in sequence")
        sequence_button.Bind(wx.EVT_BUTTON, self._on_sequence)
        top.Add(sequence_button, 0, wx.LEFT, 12)
        vbox.Add(top, 0, wx.ALL, 8)

        note = wx.StaticText(panel, label="Dividers are skipped. Type in the Number column to set one by hand.")
        vbox.Add(note, 0, wx.LEFT | wx.BOTTOM, 10)

        self.grid = wx.grid.Grid(panel)
        self.grid.CreateGrid(len(program_rows), 3)
        for index, label in enumerate(("Current name", "Number", "New name")):
            self.grid.SetColLabelValue(index, label)
        stem = job_stem(settings)
        for row_index, row in enumerate(program_rows):
            number = program_number_of(row["name"], stem)                                                         #Blank where CATIA named it, so its counter is not mistaken for a number
            self.grid.SetCellValue(row_index, 0, row["name"] or "")
            self.grid.SetCellValue(row_index, 1, str(number) if number is not None else "")
            self.grid.SetReadOnly(row_index, 0, True)
            self.grid.SetReadOnly(row_index, 2, True)
        self.grid.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self._on_number_typed)
        self._refresh_names()
        self.grid.AutoSizeColumns()
        vbox.Add(self.grid, 1, wx.EXPAND | wx.ALL, 8)

        buttons = wx.StdDialogButtonSizer()
        ok_button = wx.Button(panel, wx.ID_OK, "Stage these names")
        ok_button.SetDefault()
        buttons.AddButton(ok_button)
        buttons.AddButton(wx.Button(panel, wx.ID_CANCEL))
        buttons.Realize()
        vbox.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 8)

        panel.SetSizer(vbox)
        self.Center()

    '''
        This function fills the Number column in sequence from the starting number.
    '''
    def _on_sequence(self, event):
        try:
            number = int(self.start_text.GetValue().strip())
            step = int(self.step_text.GetValue().strip())
        except ValueError:
            wx.MessageBox("Start and step must be whole numbers.", "Renumber", wx.OK | wx.ICON_WARNING, self)
            return

        for row_index, row in enumerate(self.program_rows):
            if is_divider(row["name"]):
                self.grid.SetCellValue(row_index, 1, "")                                                          #A heading carries no number
                continue
            self.grid.SetCellValue(row_index, 1, str(number))
            number += step
        self._refresh_names()

    def _on_number_typed(self, event):
        self._refresh_names()
        event.Skip()

    '''
        This function works out the new name for every program from its number.
    '''
    def _refresh_names(self):
        rebuild = self.rebuild_check.GetValue()
        pieces = (self.settings.get("initial", ""), self.settings.get("project", ""),
                  self.settings.get("die", ""), self.settings.get("revision", ""),
                  self.settings.get("code", ""))

        for row_index, row in enumerate(self.program_rows):
            text = self.grid.GetCellValue(row_index, 1).strip()
            if not text or is_divider(row["name"]):
                self.grid.SetCellValue(row_index, 2, "")
                continue
            try:
                number = int(text)
            except ValueError:
                self.grid.SetCellValue(row_index, 2, "not a number")
                continue

            stem = job_stem(self.settings)
            if rebuild and all(pieces):
                new_name = program_name_token(*pieces, number)
            elif program_number_of(row["name"], stem) is not None:
                new_name = f"{stem}{number:02d}"                                                                 #Keep the name, change the number
            elif stem:
                new_name = f"{stem}{number:02d}"                                                                 #CATIA named this one - there is no stem worth keeping
            else:
                existing, _ = split_program_number(row["name"])
                new_name = f"{existing}{number:02d}" if existing else f"{number:02d}"
            self.grid.SetCellValue(row_index, 2, new_name)
        self.grid.ForceRefresh()

    '''
        This function hands back the names that were worked out.

        output:
            Dict of row to new name, for the programs that got one
    '''
    def staged_names(self):
        names = {}
        for row_index, row in enumerate(self.program_rows):
            new_name = self.grid.GetCellValue(row_index, 2).strip()
            if new_name and new_name != "not a number" and new_name != row["name"]:
                names[id(row)] = new_name
        return names


class TreeFrame(wx.Frame):
    """The machining tree, the staged edits, and the button that writes them."""

    COLUMNS = (("Level", "Operation", "Name", "Comment", "Tool") + PARAMETER_LABELS
               + ("Stage", "Nominal", "New name", "New comment"))

    ROW_COLOURS = {                                                                                              #The tree levels, deepest the palest
        "Part Operation": wx.Colour(214, 228, 240),
        "Program": wx.Colour(238, 242, 247),
        "Operation": wx.Colour(243, 240, 248),
    }
    DIVIDER_COLOUR = wx.Colour(255, 242, 204)                                                                    #*** heading *** programs
    STAGED_COLOUR = wx.Colour(198, 239, 206)                                                                     #A value waiting to be written
    STAGED_MARK_COLOUR = wx.Colour(155, 209, 155)                                                                #Row marker, so staged rows are findable at a glance

    def __init__(self, rows, job_info, settings, settings_dir, ppr_document=None):
        super().__init__(None, title="Manage Program Names And Comments", size=(1400, 760))
        self.SetIcon(_make_icon())
        self.rows = rows
        self.settings = settings
        self.settings_dir = settings_dir
        self.ppr_document = ppr_document                                                                         #Kept so the tree can be read again

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        header = wx.StaticText(panel, label=self._job_summary(job_info))
        header.SetFont(wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        vbox.Add(header, 0, wx.ALL, 8)

        vbox.Add(self._job_bar(panel), 0, wx.EXPAND | wx.ALL, 6)

        self.grid = wx.grid.Grid(panel)
        self.grid.CreateGrid(len(rows), len(self.COLUMNS))
        for index, label in enumerate(self.COLUMNS):
            self.grid.SetColLabelValue(index, label)
        self.grid.EnableEditing(False)
        self.grid.SetSelectionMode(wx.grid.Grid.SelectRows)
        self.grid.Bind(wx.grid.EVT_GRID_CELL_LEFT_DCLICK, self._on_edit_row)
        self._fill_grid()
        vbox.Add(self.grid, 1, wx.EXPAND | wx.ALL, 5)

        vbox.Add(self._legend(panel), 0, wx.LEFT | wx.RIGHT, 5)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in (("Edit selected row", self._on_edit_row),
                               ("Renumber programs", self._on_renumber),
                               ("Refresh from CATIA", self._on_refresh),
                               ("Clear staged edit", self._on_clear),
                               ("Apply staged edits to CATIA", self._on_apply),
                               ("Close", self._on_close)):
            button = wx.Button(panel, label=label)
            button.Bind(wx.EVT_BUTTON, handler)
            buttons.Add(button, 0, wx.RIGHT, 6)
        vbox.Add(buttons, 0, wx.ALL, 8)

        self.status = wx.StaticText(panel, label="Double click a row to set its name and comment. "
                                                 "Nothing is written until Apply is pressed.")
        vbox.Add(self.status, 0, wx.ALL, 8)

        panel.SetSizer(vbox)
        self._size_to_grid()
        self.Center()

    '''
        This function opens the window wide enough to show the grid without scrolling sideways.

        The grid is wide - every setting has a column - so a fixed size would always cut it off
        on one screen or waste space on another. The width the columns actually need is measured
        and used, held within what the screen can show.
    '''
    def _size_to_grid(self):
        needed = sum(self.grid.GetColSize(column) for column in range(self.grid.GetNumberCols()))
        needed += self.grid.GetRowLabelSize() + 60                                                               #Row labels, borders and the vertical scrollbar

        screen = wx.Display(wx.Display.GetFromWindow(self) if self.IsShown() else 0).GetClientArea()
        width = max(900, min(needed, screen.width))
        height = min(max(760, self.GetSize().height), screen.height)
        self.SetSize((width, height))

    '''
        This function builds the colour key for the grid.
    '''
    def _legend(self, panel):
        box = wx.BoxSizer(wx.HORIZONTAL)
        for colour, label in ((self.ROW_COLOURS["Part Operation"], "Part operation"),
                              (self.DIVIDER_COLOUR, "Divider"),
                              (self.ROW_COLOURS["Program"], "Program"),
                              (self.ROW_COLOURS["Operation"], "Operation"),
                              (self.STAGED_COLOUR, "Staged, waiting for Apply"),
                              (wx.WHITE, "Missing setting shown in red")):
            patch = wx.Panel(panel, size=(16, 16))
            patch.SetBackgroundColour(colour)
            box.Add(patch, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
            text = wx.StaticText(panel, label=label)
            if label.startswith("Missing"):
                text.SetForegroundColour(wx.Colour(192, 0, 0))
            box.Add(text, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 4)
        return box

    '''
        This function builds the job settings bar - the values the offset rule needs.
    '''
    def _job_bar(self, panel):
        box = wx.StaticBoxSizer(wx.HORIZONTAL, panel, "Job")
        self.fields = {}
        for key, label, width in (("initial", "Initial", 40), ("project", "Project", 60),
                                  ("die", "Die", 60), ("revision", "Rev", 40), ("code", "Code", 50),
                                  ("metal", "Metal mm", 60)):
            box.Add(wx.StaticText(panel, label=label), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 8)
            field = wx.TextCtrl(panel, value=str(self.settings.get(key, "")), size=(width, -1))
            self.fields[key] = field
            box.Add(field, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 4)

        box.Add(wx.StaticText(panel, label="Master"), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 8)
        self.master_choice = wx.Choice(panel, choices=TEMPLATES["masters"])
        master = self.settings.get("master", "UPPER")
        self.master_choice.SetSelection(TEMPLATES["masters"].index(master) if master in TEMPLATES["masters"] else 0)
        box.Add(self.master_choice, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 4)
        return box

    '''
        This function copies the job bar back into the settings dict.
    '''
    def _read_job_bar(self):
        for key, field in self.fields.items():
            self.settings[key] = field.GetValue().strip()
        self.settings["master"] = self.master_choice.GetStringSelection()

    def _fill_grid(self):
        for row_index, row in enumerate(self.rows):
            indent = "    " * row["level"]
            stage, nominal = stage_for_description(row["comment"] or row["name"])
            is_operation = row["kind"] == "Operation"                                                            #Only operations carry these settings
            parameters = row.get("parameters") or {}
            missing = (row.get("missing") or []) if is_operation else []
            values = ((row["kind"], operation_label(row["activity_type"]), indent + (row["name"] or ""),
                       row["comment"] or "", row["tool"] or "")
                      + tuple(parameters.get(label, "") or ("missing" if label in missing else "")
                              for label in PARAMETER_LABELS)
                      + (stage or "", "" if nominal is None else f"{nominal:+.1f}",
                         row["new_name"], row["new_comment"]))
            for column, value in enumerate(values):
                self.grid.SetCellValue(row_index, column, value)

            for offset_index, label in enumerate(PARAMETER_LABELS):                                              #Missing settings are called out, not left blank
                column = 5 + offset_index
                self.grid.SetCellTextColour(row_index, column,
                                            wx.Colour(192, 0, 0) if label in missing else wx.BLACK)

            row_colour = self.ROW_COLOURS.get(row["kind"], wx.WHITE)                                             #Part operations and dividers stand out from operations
            if row["kind"] == "Program" and is_divider(row["name"]):
                row_colour = self.DIVIDER_COLOUR
            for column in range(len(self.COLUMNS)):
                self.grid.SetCellBackgroundColour(row_index, column, row_colour)

            name_column, comment_column = len(self.COLUMNS) - 2, len(self.COLUMNS) - 1
            self.grid.SetCellBackgroundColour(row_index, name_column,
                                              self.STAGED_COLOUR if row["new_name"] else row_colour)
            self.grid.SetCellBackgroundColour(row_index, comment_column,
                                              self.STAGED_COLOUR if row["new_comment"] else row_colour)

            if row["new_name"] or row["new_comment"]:                                                            #Mark the whole row so staged edits are easy to find
                self.grid.SetCellBackgroundColour(row_index, 0, self.STAGED_MARK_COLOUR)
                for column in (name_column, comment_column):
                    self.grid.SetCellTextColour(row_index, column, wx.Colour(0, 97, 0))
        self.grid.AutoSizeColumns()
        self.grid.ForceRefresh()

    def _selected_row(self):
        selected = self.grid.GetSelectedRows()
        if selected:
            return selected[0]
        cursor = self.grid.GetGridCursorRow()
        return cursor if 0 <= cursor < len(self.rows) else None

    def _on_edit_row(self, event):
        row_index = event.GetRow() if hasattr(event, "GetRow") else self._selected_row()
        if row_index is None or not (0 <= row_index < len(self.rows)):
            self.status.SetLabel("Select a row first.")
            return

        self._read_job_bar()
        row = self.rows[row_index]
        dialog = EditDialog(self, row, self.settings, self.rows)
        if dialog.ShowModal() == wx.ID_OK:
            row["new_name"] = dialog.new_name
            row["new_comment"] = dialog.new_comment
            self._fill_grid()
            self.status.SetLabel(f"Staged - {sum(1 for r in self.rows if r['new_name'] or r['new_comment'])} "
                                 f"row(s) waiting to be applied.")
        dialog.Destroy()

    '''
        This function reads the whole tree again from the document.

        Staged edits are lost, because they were worked out against activities that may no longer
        be there, so they are counted and confirmed first rather than silently dropped. A metal
        thickness that was chosen by hand is carried across, so the choice does not have to be
        made again on every refresh.
    '''
    def _on_refresh(self, event):
        if self.ppr_document is None:
            self.status.SetLabel("No document to read - this window was opened without one.")
            return

        staged = [row for row in self.rows if row["new_name"] or row["new_comment"]]
        if staged:
            confirm = wx.MessageBox(f"{len(staged)} staged edit(s) have not been applied.\n\n"
                                    f"Reading again will discard them. Carry on?",
                                    "Refresh", wx.YES_NO | wx.ICON_QUESTION, self)
            if confirm != wx.YES:
                return

        chosen = {row["name"]: row["metal"] for row in self.rows                                                  #Keep the metal that was picked by hand
                  if row["kind"] == "Part Operation" and len(row.get("metals") or {}) > 1}

        wx.BeginBusyCursor()
        try:
            rows = read_tree(self.ppr_document)
        except Exception as error:
            wx.EndBusyCursor()
            wx.MessageBox(f"The document could not be read:\n\n{error}", "Refresh", wx.OK | wx.ICON_ERROR, self)
            return
        wx.EndBusyCursor()

        for row in rows:
            if row["kind"] == "Part Operation" and row["name"] in chosen and chosen[row["name"]]:
                row["metal"] = chosen[row["name"]]

        self.rows = rows
        difference = len(rows) - self.grid.GetNumberRows()
        if difference > 0:
            self.grid.AppendRows(difference)
        elif difference < 0:
            self.grid.DeleteRows(0, -difference)

        self._fill_grid()
        self.status.SetLabel(f"Read again from the document - {len(rows)} row(s). "
                             f"Staged edits were cleared.")

    '''
        This function renumbers the programs, staging the new names.
    '''
    def _on_renumber(self, event):
        self._read_job_bar()
        program_rows = [row for row in self.rows if row["kind"] == "Program"]
        if not program_rows:
            self.status.SetLabel("There are no programs to renumber.")
            return

        dialog = RenumberDialog(self, program_rows, self.settings)
        if dialog.ShowModal() == wx.ID_OK:
            names = dialog.staged_names()
            for row in program_rows:
                if id(row) in names:
                    row["new_name"] = names[id(row)]
            self._fill_grid()
            self.status.SetLabel(f"Staged {len(names)} new program name(s). Nothing is written until Apply.")
        dialog.Destroy()

    def _on_clear(self, event):
        row_index = self._selected_row()
        if row_index is None:
            self.status.SetLabel("Select a row first.")
            return
        self.rows[row_index]["new_name"] = ""
        self.rows[row_index]["new_comment"] = ""
        self._fill_grid()
        self.status.SetLabel("Staged edit cleared.")

    '''
        This function writes the staged edits to the document.

        Only values that were actually given are written - an empty staged name leaves the name
        alone rather than blanking it.
    '''
    def _on_apply(self, event):
        self._read_job_bar()
        save_settings(self.settings_dir, self.settings)

        staged = [row for row in self.rows if row["new_name"] or row["new_comment"]]
        if not staged:
            self.status.SetLabel("Nothing staged.")
            return

        confirm = wx.MessageBox(f"Write {len(staged)} staged edit(s) to the document?",
                                "Apply", wx.YES_NO | wx.ICON_QUESTION, self)
        if confirm != wx.YES:
            return

        written = 0
        failures = []
        for row in staged:
            try:
                if row["new_name"]:
                    row["activity"].name = row["new_name"]
                    row["name"] = row["new_name"]
                if row["new_comment"]:
                    row["activity"].description = row["new_comment"]
                    row["comment"] = row["new_comment"]
                row["new_name"] = ""
                row["new_comment"] = ""
                written += 1
            except Exception as error:
                failures.append(f"{row['kind']} {row['name']}: {error}")

        self._fill_grid()
        if failures:
            wx.MessageBox("Written: {0}\n\nFailed:\n{1}".format(written, "\n".join(failures)),
                          "Apply", wx.OK | wx.ICON_WARNING, self)
        self.status.SetLabel(f"Applied {written} edit(s). Save the document in CATIA to keep them.")

    def _on_close(self, event):
        self._read_job_bar()
        save_settings(self.settings_dir, self.settings)
        self.Close()

    def _job_summary(self, job_info):
        if not job_info:
            return "No part operations found."
        lines = []
        for info in job_info:
            parsed = info["parsed"]
            die = parsed["die"] or "not found"
            if not parsed["confirmed"] and parsed["op"]:
                die = f"{die}  (only OP {parsed['op']} present - die number must be confirmed)"
            lines.append(
                f"{info['setup']}\n"
                f"    CATPart  : {info['part_name'] or 'not found'}   [{info['route']}]\n"
                f"    Job      : {parsed['job'] or 'not found'}\n"
                f"    Die      : {die}\n"
                f"    Revision : {parsed['revision'] or 'not found'}"
            )
        return "\n".join(lines)


if __name__ == "__main__":
    app = wx.App(None)

    try:
        #Anchoring relavent components
        caa = catia()                                                                                            #Catia application instance
        check_document = caa.active_document                                                                     #Current active document

        if type(check_document) is ProcessDocument:                                                              #Active document is ProcessDocument
            ppr_document: PPRDocument = check_document.ppr_document                                              #Get PPRDocument
        elif type(check_document) is PPRDocument:                                                                #Active document is PPRDocument
            ppr_document: PPRDocument = caa.active_document
        else:
            print("A CATProcess document must be the active document.")
            exit()

        settings_dir = os.path.join(os.environ['APPDATA'], 'pycatia_scripts', SCRIPT_NAME)
        if not os.path.exists(settings_dir):
            os.makedirs(settings_dir)                                                                            #User templates will live here

        print("\n Reading the machining tree...\n")
        rows = read_tree(ppr_document)

        job_info = []
        for row in rows:
            if row["kind"] == "Part Operation":
                job_info.append({
                    "setup": row["name"],
                    "part_name": row["part_name"],
                    "route": row["part_name_route"],
                    "parsed": parse_part_name(row["part_name"]),
                })

        counts = {}
        for row in rows:
            counts[row["kind"]] = counts.get(row["kind"], 0) + 1
        print(" Found: " + ", ".join(f"{count} {kind}" for kind, count in counts.items()))

        operations = [row for row in rows if row["kind"] == "Operation"]
        total = len(operations)
        print(f"\n Settings read from {total} operation(s):")
        for label in PARAMETER_LABELS:
            found = sum(1 for row in operations if row["parameters"].get(label))
            note = "" if found == total else f"   <- missing on {total - found}"
            print(f"   {label:<24} {found} of {total}{note}")

        incomplete = [row for row in operations if row["missing"]]
        if incomplete:
            print(f"\n {len(incomplete)} operation(s) with missing settings:")
            for row in incomplete:
                print(f"   {operation_label(row['activity_type']):<14} {row['name']:<34} "
                      f"missing {', '.join(row['missing'])}")

        with_offset = sum(1 for row in operations if row["offset"] is not None)
        print(f"\n Offset on part read from {with_offset} of {total} operation(s)"
              + ("" if with_offset == total else " - the rest fall back to the stage rule"))

        for info in job_info:
            parsed = info["parsed"]
            print(f"\n {info['setup']}")
            print(f"   CATPart  : {info['part_name'] or 'not found'}  [{info['route']}]")
            print(f"   Job      : {parsed['job'] or 'not found'}")
            print(f"   Die      : {parsed['die'] or 'not found'}"
                  + ("" if parsed["confirmed"] else f"  (unconfirmed, OP {parsed['op']})" if parsed["op"] else ""))
            print(f"   Revision : {parsed['revision'] or 'not found'}")

        if not rows:
            print("\n No part operations found in this document.\n")
            exit()

        settings = load_settings(settings_dir)
        for info in job_info:                                                                                    #Prefill from the part name, still editable
            parsed = info["parsed"]
            for key, value in (("project", parsed["job"]), ("die", parsed["die"]),
                               ("revision", parsed["revision"])):
                if value:
                    settings[key] = value

        print("\n Metal thickness, read from each design part:")
        for row in rows:                                                                                         #Per part operation - metal belongs to the panel
            if row["kind"] != "Part Operation":
                continue

            if len(row["metals"]) > 1:
                choose_metal(None, row)                                                                          #A die can hold parts of different thickness

            side = side_for_die_part(row["name"]) or "not known"
            print(f"   {row['name']}")
            print(f"     master {row['master'] or 'not stated'}, "
                  f"metal {row['metal'] + 'mm' if row['metal'] else 'not known'}, side {side}")
            for value, sources in sorted(row["metals"].items()):
                mark = "  <- chosen" if value == row["metal"] and len(row["metals"]) > 1 else ""
                for source in sources:
                    print(f"       {value}mm from: {source}{mark}")
            if row["metal_note"]:
                print(f"       note: {row['metal_note']}")
            if not row["metal"]:
                print("       no offsets will be worked out for this part operation")

            if row["master"]:
                settings["master"] = row["master"]
            if row["metal"]:
                settings["metal"] = row["metal"]
            if not settings.get("code"):
                settings["code"] = die_part_code(row["name"])                                                    #A suggestion - it stays editable in the Job bar

        frame = TreeFrame(rows, job_info, settings, settings_dir, ppr_document)
        frame.Show()
        wx.CallAfter(_bring_to_front, frame)
        app.MainLoop()

        print("\n\n Completed\n\n")

    except Exception as e:
        full_traceback = traceback.format_exc()
        print(full_traceback)
        error_msg = (
            f"Error Summary: {str(e)}\n"
            f"------------------------------------------\n"
            f"Technical Debug Info:\n\n{full_traceback}"
        )
        e_dlg = dialogs.ScrolledMessageDialog(None, error_msg, "Script Error")
        error_icon = wx.ArtProvider.GetBitmap(wx.ART_ERROR, wx.ART_MESSAGE_BOX)
        icon_bitmap = wx.StaticBitmap(e_dlg, wx.ID_ANY, error_icon)
        header_text = wx.StaticText(e_dlg, label="An error occurred while reading the machining tree:")
        header_font = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        header_text.SetFont(header_font)
        main_sizer = e_dlg.GetSizer()
        header_sizer = wx.BoxSizer(wx.HORIZONTAL)
        header_sizer.Add(icon_bitmap, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 15)
        header_sizer.Add(header_text, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        main_sizer.Prepend(header_sizer, 0, wx.EXPAND)
        mono_font = wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        e_dlg.text.SetFont(mono_font)
        e_dlg.SetSize((600, 400))
        e_dlg.CenterOnParent()
        wx.CallAfter(_bring_to_front, e_dlg)
        e_dlg.ShowModal()
        e_dlg.Destroy()
        exit()
