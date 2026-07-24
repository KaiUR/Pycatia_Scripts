'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Manage_Program_Names_And_Comments.py
    Version:        1.4
    Code:           Python3.10.4, Pycatia 0.10.0
    Release:        V5R32
    Purpose:        Review and set the names and comments of manufacturing programs and operations.
    Author:         Kai-Uwe Rathjen
    Date:           20.07.26
    Description:    Lists the whole machining tree - part operations, programs and operations - with each
                    activity's name, comment, tool and the same settings Export_Process_Table_Parameters reads.
                    Names and comments are set from template lists, program names built as A104D4503LP01 and
                    renumbered in sequence, and program comments composed as TOOL DESCRIPTION TO 0.0MM
                    (M/C: -0.7MM), the machined figure coming from the operations and the stage from the job.
                    Job details are read from the CATPart name and the metal thickness from the design part.
                    Stepover, depth of cut and part offset are checked against editable limits and shown on
                    red where they are off. Several rows can be selected and edited together as a group.
                    Edits are staged in place over the current values; nothing is written until Apply is pressed.
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

    Change:         21.07.26 1.1: Staged edits shown in place of the current values rather than in
                                  their own columns, Apply no longer asks to confirm, staged names
                                  counted when numbering, the stage read from the staged comment,
                                  the operation description filled in when a row is reopened, and
                                  PPInstruction activities given their name and their PP words
                                  syntax from two template lists of the user's own.
                    23.07.26 1.2: Contour stepover read from Minimum step distance and its depth
                                  of cut from Maximum depth of cut, the CATIA Roughing operation
                                  shown as Roughing with its pass overlap as the stepover,
                                  stepover / depth of cut / part offset checked against editable
                                  limits and shown on red where off, several rows editable at
                                  once as a group, any known tool stripped from a prefilled
                                  description, and the buttons grouped by colour.
                    24.07.26 1.3: Contour stepover read from Maximum distance again, the same
                                  parameter Export_Process_Table_Parameters reads - the 1.2
                                  change to Minimum step distance was wrong.
                    24.07.26 1.4: Contour stepover read from Step distance. A parameter dump
                                  of a live document shows Step distance moving between the
                                  semi-finish and finish operations - 1mm and 0.5mm - while
                                  Maximum distance and Minimum step distance, the 1.3 and 1.2
                                  guesses, sit still whatever the dialog holds.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.dmaps_interfaces.process_document import ProcessDocument
from pycatia.manufacturing_interfaces.manufacturing_setup import ManufacturingSetup
from pycatia.knowledge_interfaces.str_param import StrParam
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
  "instruction_names": [],
  "instructions": [],
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

# Activities that carry a post processor instruction rather than a cut. They sit at the head of a
# program and hold two separate things: the activity name - MECOF_HEAD - and the instruction the
# post processor actually reads - head/'TCB6'. Each has its own template list, and both ship empty
# because the instructions belong to the shop and its machines rather than to the script.
INSTRUCTION_TYPES = ("PPInstruction",)

# The activity parameter the instruction lives in. SetPPWORDSyntax and GetPPWORDSyntax are not on
# the activity in V5R32, so the parameter is read and written directly, wrapped as a StrParam.
INSTRUCTION_PARAMETER = "PP words syntax"

PLACEHOLDERS = ("**.**MM", "***MM", "0.*MM", "POS_##")                                                           #Matched case insensitively, longest first

REMEMBERED_SETTINGS = ("initial", "machine")                                                                     #All that survives between runs - the rest is read from the document

DEFAULT_TEMPLATES = json.loads(json.dumps(TEMPLATES))                                                            #Kept whole, so Reset can put every list back

TEMPLATE_STATE = {"use_defaults": True}                                                                          #False where the shop keeps its own lists only

# The lists the editor offers, in the order they are shown. part_operation_name is left out - it
# is the shape of a name rather than a list of choices.
TEMPLATE_LISTS = (
    ("die_parts", "Die parts"),
    ("machines", "Machines"),
    ("job_descriptions", "Job descriptions"),
    ("part_operation_comments", "Part operation comments"),
    ("masters", "Masters"),
    ("dividers", "Dividers"),
    ("descriptions", "Operation descriptions"),
    ("instruction_names", "PP instruction names"),
    ("instructions", "PP instructions"),
    ("tools", "Tools"),
    ("die_numbers", "Die numbers"),
)


'''
    This function loads the template lists, with the user's own entries on top of the defaults.

    Inputs:
        settings_dir    The folder settings live in

    output:
        None - TEMPLATES is updated in place, so every reference to it sees the change
'''
def load_templates(settings_dir):
    path = os.path.join(settings_dir, "templates.json")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            saved = json.load(handle)
    except Exception:
        return                                                                                                   #No file yet, or an unreadable one - the defaults stand

    TEMPLATE_STATE["use_defaults"] = bool(saved.get("_use_defaults", True))
    for key, value in saved.items():
        if key in TEMPLATES and isinstance(value, type(TEMPLATES[key])):
            TEMPLATES[key] = value


'''
    This function saves the template lists.

    Inputs:
        settings_dir    The folder settings live in

    output:
        True where it was written
'''
def save_templates(settings_dir):
    try:
        content = dict(TEMPLATES)
        content["_use_defaults"] = TEMPLATE_STATE["use_defaults"]                                                 #Remembered, so the tick box comes back as it was left
        with open(os.path.join(settings_dir, "templates.json"), "w", encoding="utf-8") as handle:
            json.dump(content, handle, indent=2)
        return True
    except Exception:
        return False

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

# Operation types whose settings live under different parameter names. A contour driven
# operation's stepover is its Step distance - the dialog value, which a parameter dump shows
# moving between the semi-finish and finish operations while the Maximum distance the type
# also carries sits still - and its depth of cut is Maximum depth of cut, because the
# Multi-Pass depth stays set while Multi-Pass itself is off.
PARAMETER_OVERRIDES = {
    "M3xBetweenContour": {
        "Stepover": ("Step distance",),
        "Depth of Cut": ("Maximum depth of cut",),
    },
}

# The CATIA Roughing operation - M3xHardMaterial - states its stepover as a pass overlap: a mode
# and two values, of which the mode says which one is in force. A ratio is shown as a percentage
# of the tool diameter, a length as the distance it is.
ROUGHING_TYPE = "M3xHardMaterial"
OVERLAP_MODE = "Pass overlap mode"
OVERLAP_RATIO = "Pass overlap (diameter ratio)"
OVERLAP_LENGTH = "Pass overlap (length)"

# The values the settings are checked against, editable under [Edit limits]. Stepover limits are
# per machining stage, the stage read from the operation's comment or name, or its program's.
# The CATIA Roughing operation is checked on its own two rules instead - its pass overlap and
# its depth of cut - whatever stage its program belongs to. A value off its list is shown on red.
DEFAULT_LIMITS = {
    "stepover": {"ROUGHING": [3.0, 2.0, 1.0], "SEMI-FINISH": [1.5, 1.0], "FINISH": [1.0, 0.5]},
    "roughing_overlap": [50.0],
    "roughing_depth_of_cut": [1.0, 1.5, 2.0],
}

LIMITS = json.loads(json.dumps(DEFAULT_LIMITS))                                                                  #Replaced by whatever limits.json holds


'''
    This function loads the saved limits, where the user has changed them.

    Inputs:
        settings_dir    The folder settings live in

    output:
        None - LIMITS is updated in place, so every reference to it sees the change
'''
def load_limits(settings_dir):
    path = os.path.join(settings_dir, "limits.json")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            saved = json.load(handle)
    except Exception:
        return                                                                                                   #No file yet, or an unreadable one - the defaults stand

    for key, value in saved.items():
        if key in LIMITS and isinstance(value, type(LIMITS[key])):
            LIMITS[key] = value


'''
    This function saves the limits.

    Inputs:
        settings_dir    The folder settings live in

    output:
        True where it was written
'''
def save_limits(settings_dir):
    try:
        with open(os.path.join(settings_dir, "limits.json"), "w", encoding="utf-8") as handle:
            json.dump(LIMITS, handle, indent=2)
        return True
    except Exception:
        return False


'''
    This function says whether a value sits on a list of allowed values.

    Inputs:
        value           The value to check
        choices         The allowed values

    output:
        True where it matches one, within a hair
'''
def value_allowed(value, choices):
    return any(abs(value - choice) <= 0.001 for choice in choices)


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
    if label == "M3xHardMaterial":
        return "Roughing"                                                                                        #What the CATIA dialog calls it
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
    sit at different indices still reports its settings. Types listed in PARAMETER_OVERRIDES have
    some settings read from other parameter names, and the Roughing operation's stepover is put
    together from its pass overlap mode and whichever of the two overlap values that mode is on.

    Inputs:
        activity        A manufacturing operation activity

    output:
        Tuple of (dict of label to value string, list of the labels that were not found)
'''
def read_operation_parameters(activity):
    values = {label: "" for label in PARAMETER_LABELS}

    try:
        activity_type = activity.type
    except Exception:
        activity_type = ""
    overrides = PARAMETER_OVERRIDES.get(activity_type, {})
    columns = tuple((label, overrides.get(label, needles)) for label, needles in PARAMETER_COLUMNS)
    overlap = {}                                                                                                 #The Roughing operation's pass overlap pieces

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
        if activity_type == ROUGHING_TYPE:
            for key in (OVERLAP_MODE, OVERLAP_RATIO, OVERLAP_LENGTH):
                if key in name and key not in overlap:
                    try:
                        overlap[key] = parameter.value_as_string()
                    except Exception:
                        pass
        for label, needles in columns:
            if values[label]:
                continue                                                                                         #First match wins, as in the export script
            if any(needle in name for needle in needles):
                try:
                    values[label] = parameter.value_as_string()
                except Exception:
                    pass

    if activity_type == ROUGHING_TYPE and not values["Stepover"]:
        mode = overlap.get(OVERLAP_MODE, "")                                                                     #M3xRatio, or one of the length modes
        if "Ratio" in mode and overlap.get(OVERLAP_RATIO):
            values["Stepover"] = overlap[OVERLAP_RATIO] + "%"                                                    #A percentage of the tool diameter
        elif "Length" in mode and overlap.get(OVERLAP_LENGTH):
            values["Stepover"] = overlap[OVERLAP_LENGTH]

    missing = [label for label in PARAMETER_LABELS if not values[label]]
    return values, missing


'''
    This function finds the parameter holding a PP instruction.

    The post processor reads this, not the activity name - MECOF_HEAD is what the activity is
    called, head/'TCB6' is what it does. It is wrapped as a StrParam so the value can be read
    and written as a string.

    Inputs:
        activity        A PPInstruction activity

    output:
        The StrParam, or None where the activity has no such parameter
'''
def instruction_parameter(activity):
    try:
        parameters = activity.parameters
        count = parameters.count
    except Exception:
        return None

    for index in range(count):
        try:
            parameter = parameters.item(index + 1)
            if INSTRUCTION_PARAMETER in parameter.name:
                return StrParam(parameter.com_object)
        except Exception:
            continue
    return None


'''
    This function reads the PP instruction off an activity.

    Inputs:
        activity        A PPInstruction activity

    output:
        The instruction, e.g. head/'TCB6', or an empty string where there is none
'''
def read_instruction(activity):
    parameter = instruction_parameter(activity)
    if parameter is None:
        return ""
    try:
        return parameter.value or ""
    except Exception:
        return ""


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
    This function works out whether a part is an upper or a lower part.

    It is read from the UPPER or LOWER in the part operation's name, which is the name the user
    gives it from the die parts list - name it UPPER PAD and it is an upper part. There is no
    separate setting, so the name and the offset can never disagree.

    Inputs:
        die_part        A die part name, e.g. "UPPER TRIM CAM POS_01"

    output:
        "UPPER", "LOWER", or None where the name does not say
'''
def upper_or_lower(die_part):
    text = re.sub(r"[_\-]+", " ", (die_part or "").upper())
    if re.search(r"\bUPPER\b", text):
        return "UPPER"
    if re.search(r"\bLOWER\b", text):
        return "LOWER"
    return None


'''
    This function applies the master rule to a stage nominal.

    The master side is cut to nominal. The other side has the metal taken off it. So an upper cam
    is cut to nominal where UPPER is master, and has the metal taken out of it where LOWER is.
    BOTH means no metal comes off either side.

        Master    Upper parts        Lower parts
        UPPER     nominal            nominal - metal
        LOWER     nominal - metal    nominal
        BOTH      nominal            nominal

    Inputs:
        nominal         Stock left at this stage, e.g. 0.3
        part            "UPPER" or "LOWER" - what this part is
        master          "UPPER", "LOWER" or "BOTH"
        metal           Metal thickness in mm

    output:
        The offset in mm, or None where it is not known what the part is and the answer could be
        wrong by the whole metal thickness
'''
def offset_for(nominal, part, master, metal, spotting=0.0):
    if nominal is None:
        return None
    if master == "BOTH":
        return nominal + spotting
    if part is None:
        return None                                                                                              #Never guess - a wrong side is wrong by the whole metal
    if part == master:
        return nominal + spotting
    return nominal - metal + spotting


'''
    This function writes the spotting allowance the way it appears in a comment.

    Spotting is material left on for hand work at try out. It is either built into the programs,
    so the tool never cuts it away, or left to the operator to hold off at the machine - in which
    case the programs are unchanged and the comment tells them to.

    Inputs:
        value           The allowance in mm as text, e.g. "0.3"
        built_in        True where the programs already leave it

    output:
        The note, or an empty string where there is no allowance
'''
def spotting_note(value, built_in):
    try:
        allowance = float(value)
    except (TypeError, ValueError):
        return ""
    if not allowance:
        return ""
    return f"SPOTTING {format_offset(allowance)} BUILT IN" if built_in else f"LEAVE {allowance}MM FOR SPOTTING"


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
def compose_program_comment(tool, description, stage_offset, machine_offset=None, spotting=""):
    text = " ".join(part for part in (tool, description) if part)

    if stage_offset is None:
        stage_offset = machine_offset                                                                             #No stage to quote, so the machined figure is the only one

    if stage_offset is not None:
        text = f"{text} TO {format_offset(stage_offset)}"
    if machine_offset is not None and stage_offset is not None and abs(machine_offset - stage_offset) > 0.001:
        text = f"{text} (M/C: {format_offset(machine_offset)})"                                                   #Only worth saying when it differs
    if spotting:
        text = f"{text}\n{spotting}"                                                                             #A line of its own
    return text.strip()


'''
    This function reads the description back out of a program comment.

    A composed comment reads TOOL DESCRIPTION TO +0.3MM (M/C: -0.7MM) with any spotting note on a
    line of its own, so the description is what is left once the tool in front and the offsets
    behind are taken off. A comment written some other way has no offsets to cut, and keeps
    whatever text it carries.

    Any recognised tool is stripped, not only the one the row detected - a comment carrying the
    tool the program used to run would otherwise keep it in the description, and composing would
    then write both tools in front of it.

    Inputs:
        comment         The comment on the program, staged or current
        tool            The tool token the row detected, e.g. "32BN"

    output:
        The description, e.g. "SEMI FINISH SWEEP", or an empty string
'''
def description_from_comment(comment, tool):
    text = (comment or "").replace("\r\n", "\n").split("\n")[0].strip()                                          #The spotting note is never part of it
    if not text:
        return ""

    offsets = text.rfind(" TO ")                                                                                 #The offsets are appended last, so cut the rightmost
    if offsets != -1:
        text = text[:offsets]

    tokens = [token.strip() for token in [tool] + TEMPLATES["tools"] if token and token.strip()]
    for token in sorted(set(tokens), key=len, reverse=True):                                                     #Longest first - 32 DEPO R8 before 32BN
        if text.upper().startswith(token.upper() + " ") or text.upper() == token.upper():
            text = text[len(token):]
            break
    else:
        text = re.sub(r"^\d+(?:[.-]\w+)?\s*BN\b\s*", "", text, flags=re.IGNORECASE)                              #A ball nose not on the list - 16BN FINISH SWEEP

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
    settings = {"initial": "", "project": "", "die": "", "revision": "",
                "machine": "OKUMA", "pos": ""}                                                                    #Code, metal and master are per part operation
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
    This function compares two pieces of text ignoring how their lines end.

    A comment read back from CATIA carries carriage returns that the dialog does not, so a
    comment that was only read and put back would otherwise look like a change.

    Inputs:
        left            A piece of text
        right           Another piece of text

    output:
        True where they say the same thing
'''
def same_text(left, right):
    def tidy(text):
        return (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    return tidy(left) == tidy(right)


'''
    These two functions give the name and comment a row will carry once the staged edits are
    written, which is what everything downstream has to work from. Numbering a program against
    the name it is about to lose would hand out a number that is already spoken for, and the
    stage of a comment that is about to be replaced is not the stage the row is heading for.

    Inputs:
        row             A row from the tree

    output:
        The staged value where there is one, otherwise what the activity carries now
'''
def effective_name(row):
    return (row.get("new_name") or row.get("name") or "") if row else ""


def effective_comment(row):
    return (row.get("new_comment") or row.get("comment") or "") if row else ""


def effective_instruction(row):
    return (row.get("new_instruction") or row.get("instruction") or "") if row else ""


'''
    This function says whether a row has anything waiting to be written.

    Inputs:
        row             A row from the tree

    output:
        True where a name, a comment or a PP instruction is staged
'''
def is_staged(row):
    return bool(row.get("new_name") or row.get("new_comment") or row.get("new_instruction"))


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
    "MASTER PANEL LH CP02 REV11 - UPPER IS MASTER - METAL IS 1.5mm". The same wording turns up in
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

        A    104    D45   03    LP    01
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
        The name, e.g. "A104D4503LP01"
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
        name            A program name, e.g. "A104D4503LP01"

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
        The stem, e.g. "A104D4503LP", or an empty string where the job is not filled in
'''
def job_stem(settings, part_op=None):
    code = (part_op or {}).get("code") or die_part_code((part_op or {}).get("name", ""))                          #The die part code belongs to the part operation
    pieces = (settings.get("initial", ""), settings.get("project", ""), settings.get("die", ""),
              settings.get("revision", ""), code)
    return "".join(pieces).upper() if all(pieces) else ""


'''
    This function finds the part operation a row sits under.

    Inputs:
        row             Any row

    output:
        The part operation row, or None
'''
def part_operation_of(row):
    while row and row["kind"] != "Part Operation":
        row = row["parent"]
    return row


'''
    This function reads a program's number, but only where the name is one of this job's.

    A program CATIA named itself - Manufacturing Program.14 - ends in the number of the activity
    CATIA has created, which has nothing to do with the program numbering. Taking it would suggest
    19 where the job has only reached 09, so a number is read only from a name built on this job's
    stem.

    Inputs:
        name            The program name
        stem            The job stem, e.g. "A104D4503LP"

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
        One past the highest number in use, staged names counted, or 1 where none are numbered yet
'''
def next_program_number(rows, part_op_row, stem):
    numbers = []
    for row in rows:
        if row["kind"] != "Program":
            continue
        if part_op_row is not None and row.get("parent") is not part_op_row:
            continue
        number = program_number_of(effective_name(row), stem)                                                    #A staged name has already claimed its number
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
    This function works out the stage an operation belongs to.

    Its own comment or name is read first, then its program's, so an operation named after its
    tool still checks against the stage the program says it is cutting. A name CATIA gave the
    operation itself - Roughing.1, Sweeping.3 - is its type with a counter, not a statement of
    the stage, so it is not read as one.

    Inputs:
        row             An operation row

    output:
        Tuple of (stage name, nominal stock in mm), or (None, None) where no stage is stated
'''
def stage_of_row(row):
    name = effective_name(row)
    if re.fullmatch(re.escape(operation_label(row["activity_type"])) + r"\.\d+", name.strip()):
        name = ""                                                                                                #CATIA's own default name says the type, not the stage
    stage, nominal = stage_for_description(effective_comment(row) or name)
    if stage is None and row.get("parent") is not None:
        parent = row["parent"]
        stage, nominal = stage_for_description(effective_comment(parent) or effective_name(parent))
    return stage, nominal


'''
    This function checks an operation's settings against the limits.

    Three things are looked at. The stepover has to sit on the allowed list for the operation's
    stage. The CATIA Roughing operation is instead held to its own two rules - a pass overlap on
    the allowed percentages and a depth of cut on the allowed depths. And the Offset on part has
    to match what the stage rule works out from the part operation's master, metal and spotting.
    Anything that cannot be worked out - no stage, no master, no metal - is not checked, so a
    row is only marked where the value is genuinely off.

    Inputs:
        row             An operation row
        part_op         The part operation it sits under, or None

    output:
        Dict of column label to a short reason, empty where everything checks out
'''
def check_operation(row, part_op):
    bad = {}
    if row["kind"] != "Operation":
        return bad
    parameters = row.get("parameters") or {}
    stage, nominal = stage_of_row(row)

    stepover_text = parameters.get("Stepover") or ""
    stepover = numeric_value(stepover_text)
    if row["activity_type"] == ROUGHING_TYPE:
        if stepover_text.endswith("%"):
            if stepover is not None and not value_allowed(stepover, LIMITS["roughing_overlap"]):
                bad["Stepover"] = "pass overlap should be " + ", ".join(
                        f"{choice:g}%" for choice in LIMITS["roughing_overlap"])
        elif stepover_text:
            bad["Stepover"] = "a length, where a pass overlap percentage is expected"

        depth = numeric_value(parameters.get("Depth of Cut"))
        if depth is not None and not value_allowed(depth, LIMITS["roughing_depth_of_cut"]):
            bad["Depth of Cut"] = "should be " + ", ".join(
                    f"{choice:g}" for choice in LIMITS["roughing_depth_of_cut"])
    else:
        key = (stage or "").replace("SEMI FINISH", "SEMI-FINISH")                                                #The older templates' spelling of the same stage
        choices = LIMITS["stepover"].get(key)
        if choices and stepover is not None and not value_allowed(stepover, choices):
            bad["Stepover"] = "should be " + ", ".join(f"{choice:g}" for choice in choices)

    measured = row.get("offset")
    if measured is not None and nominal is not None and part_op:
        part = upper_or_lower(effective_name(part_op))
        master = part_op.get("master")
        try:
            metal = float(part_op.get("metal")) if part_op.get("metal") else None
        except ValueError:
            metal = None
        spotting = 0.0
        if part_op.get("spotting_mode") == "built in":
            try:
                spotting = float(part_op.get("spotting") or 0)
            except ValueError:
                spotting = 0.0

        expected = None
        if master == "BOTH" or (part and master and part == master):
            expected = nominal + spotting                                                                        #The metal never comes into it on the master side
        elif part and master and metal is not None:
            expected = offset_for(nominal, part, master, metal, spotting)
        if expected is not None and abs(expected - measured) > 0.001:
            bad["Offset on Part"] = f"the stage rule gives {format_offset(expected)}"
    return bad


'''
    This function walks the machining tree and returns one row per activity.

    Inputs:
        ppr_doc         The PPRDocument of the active process document

    output:
        List of dicts with keys level, kind, name, comment, tool, activity_type
'''
def count_programs(ppr_doc):
    total = 0
    try:
        processes = ppr_doc.processes
        for process_index in range(processes.count):
            part_operations = processes.item(process_index + 1).children_activities
            for part_op_index in range(part_operations.count):
                part_op = part_operations.item(part_op_index + 1)
                if part_op.type != "ManufacturingSetup":
                    continue
                programs = part_op.children_activities
                for program_index in range(programs.count):                                                      #Only the programs, not the Start and Stop
                    if programs.item(program_index + 1).type == "ManufacturingProgram":
                        total += 1
    except Exception:
        pass                                                                                                     #Only used to size the bar
    return total


'''
    This function walks the machining tree and returns one row per activity.

    Inputs:
        ppr_doc         The PPRDocument of the active process document
        report          Optional callable taking (programs done, message). Reading the settings of
                        every operation takes a while, so the caller can show how far along it is.

    output:
        List of dicts, one per activity
'''
def read_tree(ppr_doc, report=None):
    rows = []
    done = 0
    processes = ppr_doc.processes

    for process_index in range(processes.count):
        process = processes.item(process_index + 1)
        part_operations = process.children_activities

        for part_op_index in range(part_operations.count):
            part_op = part_operations.item(part_op_index + 1)
            if part_op.type != "ManufacturingSetup":
                continue

            if report:
                report(done, f"Reading {part_op.name}")
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
                "instruction": "",                                                                               #Only a PPInstruction carries one
                "new_instruction": "",
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
                    "instruction": "",                                                                           #Only a PPInstruction carries one
                    "new_instruction": "",
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
                        "instruction": (read_instruction(activity)                                                #What the post processor reads
                                        if activity.type in INSTRUCTION_TYPES else ""),
                        "new_instruction": "",
                        "offset": offset,
                        "offset_attribute": "Offset on part" if offset is not None else "",
                        "parameters": parameters,
                        "missing": missing,
                    })

                program_row["tool"] = first_tool                                                                 #Show the program's first tool on its own row
                program_row["offset"], program_row["offset_attribute"] = program_offset(rows, program_row)

                done += 1
                if report:
                    report(done, f"{program.name}")

    calibrate_missing(rows)
    return rows


'''
    This function reads the tree behind a progress bar.

    Every operation is asked for its settings one parameter at a time, so a big process takes a
    while. The bar says what it is on rather than leaving the window looking hung.

    Inputs:
        ppr_doc         The PPRDocument of the active process document
        parent          The window to sit over, or None at startup

    output:
        The rows read
'''
def read_tree_with_progress(ppr_doc, parent=None):
    total = count_programs(ppr_doc)
    dialog = wx.ProgressDialog("Manage Program Names And Comments",
                               "Reading the machining tree...".ljust(60),
                               maximum=max(total, 1), parent=parent,
                               style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_SMOOTH)
    dialog.SetIcon(_make_icon())

    def report(done, message):
        dialog.Update(min(done, total) if total else 0, message[:60].ljust(60))

    try:
        return read_tree(ppr_doc, report)
    finally:
        dialog.Destroy()


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
    This function gathers every metal thickness found across the whole process.

    Each thickness becomes one row, carrying the body name it was read from, so a die holding
    parts of different thickness shows them all and each part operation is pointed at the one
    that applies to it.

    Inputs:
        rows            The rows read from the tree

    output:
        List of dicts with keys value, source and custom
'''
def collect_metal_rows(rows):
    metal_rows = []
    seen = set()
    for row in rows:
        if row["kind"] != "Part Operation":
            continue
        for value, sources in sorted((row.get("metals") or {}).items(), key=lambda item: float(item[0])):
            if value in seen:
                continue
            seen.add(value)
            master = parse_master_and_metal(sources[0])["master"] or row.get("master")                            #The same body name states both
            metal_rows.append({"value": value, "master": master or "", "source": sources[0], "custom": False})
    return metal_rows


class MetalDialog(wx.Dialog):
    """Lists every metal thickness found, and says what applies to each part operation."""

    NAME, CODE, METAL, MASTER, SPOTTING, BUILT_IN, USE = range(7)                                                #Columns of the lower grid
    SPOTTING_MODES = ("", "built in", "at the machine")

    def __init__(self, parent, part_ops, metal_rows):
        super().__init__(parent, title="Metal thicknesses", size=(900, 620),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.part_ops = part_ops
        self.metal_rows = [dict(entry) for entry in metal_rows]                                                   #Only copied back on OK

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        vbox.Add(wx.StaticText(panel, label="Thicknesses found in the design parts. Add a row by hand "
                                            "where a part does not state one."), 0, wx.ALL, 8)

        self.metal_grid = wx.grid.Grid(panel)
        self.metal_grid.CreateGrid(0, 4)
        for index, label in enumerate(("Metal mm", "Master", "Where it came from", "Row")):
            self.metal_grid.SetColLabelValue(index, label)
        self.metal_grid.SetSelectionMode(wx.grid.Grid.SelectRows)
        self.metal_grid.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self._on_metal_edited)
        vbox.Add(self.metal_grid, 1, wx.EXPAND | wx.ALL, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in (("Add row", self._on_add), ("Delete row", self._on_delete)):
            button = wx.Button(panel, label=label)
            button.Bind(wx.EVT_BUTTON, handler)
            buttons.Add(button, 0, wx.RIGHT, 6)
        self.delete_note = wx.StaticText(panel, label="Only rows added by hand can be deleted.")
        self.delete_note.SetForegroundColour(wx.Colour(90, 90, 90))
        buttons.Add(self.delete_note, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 8)
        vbox.Add(buttons, 0, wx.LEFT | wx.BOTTOM, 8)

        vbox.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.ALL, 4)
        vbox.Add(wx.StaticText(panel, label="Which row above applies to each part operation. Pick one in "
                                            "the last column and its thickness and master are used."),
                 0, wx.ALL, 8)

        self.setup_grid = wx.grid.Grid(panel)
        self.setup_grid.CreateGrid(len(part_ops), 7)
        for index, label in enumerate(("Part operation", "Code", "Metal mm", "Master",
                                       "Spotting mm", "Spotting", "Use")):
            self.setup_grid.SetColLabelValue(index, label)
        for row_index, row in enumerate(part_ops):
            self.setup_grid.SetCellValue(row_index, self.NAME, row["name"] or "")
            self.setup_grid.SetCellValue(row_index, self.CODE,
                                         row.get("code") or die_part_code(row["name"]))                          #Suggested from the name, editable
            self.setup_grid.SetCellValue(row_index, self.SPOTTING, row.get("spotting") or "")
            self.setup_grid.SetCellValue(row_index, self.BUILT_IN, row.get("spotting_mode") or "")
            self.setup_grid.SetCellEditor(row_index, self.MASTER, wx.grid.GridCellChoiceEditor(
                list(TEMPLATES["masters"]), False))
            self.setup_grid.SetCellEditor(row_index, self.BUILT_IN, wx.grid.GridCellChoiceEditor(
                list(self.SPOTTING_MODES), False))
            self.setup_grid.SetReadOnly(row_index, self.NAME, True)
            self.setup_grid.SetReadOnly(row_index, self.METAL, True)                                             #Filled in from whatever row is picked
        self.setup_grid.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self._on_use_chosen)
        self.setup_grid.Bind(wx.grid.EVT_GRID_SELECT_CELL, self._on_select_cell)                                 #Open dropdowns on a single click
        vbox.Add(self.setup_grid, 1, wx.EXPAND | wx.ALL, 8)

        panel.SetSizer(vbox)

        bottom = wx.StdDialogButtonSizer()
        ok_button = wx.Button(self, wx.ID_OK, "OK")
        ok_button.SetDefault()
        bottom.AddButton(ok_button)
        bottom.AddButton(wx.Button(self, wx.ID_CANCEL))
        bottom.Realize()

        frame = wx.BoxSizer(wx.VERTICAL)
        frame.Add(panel, 1, wx.EXPAND)
        frame.Add(bottom, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizer(frame)

        self._fill_metal_grid()
        for row_index, row in enumerate(part_ops):                                                               #Every part operation is filled the same way
            own = row.get("metal")
            if not own and len(row.get("metals") or {}) == 1:
                own = next(iter(row["metals"]))                                                                  #Its own part states just the one
            if not own:
                continue
            for label, entry in zip(self._labels(), self.metal_rows):
                if entry["value"] == own:
                    self._use_row(row_index, label)
                    break
        self._default_single_row()
        self.setup_grid.AutoSizeColumns()
        self.Center()

    def _values(self):
        return [entry["value"] for entry in self.metal_rows]

    '''
        This function writes each thickness row the way the dropdown shows it.

        output:
            A label per row, e.g. "1.5mm   UPPER"
    '''
    def _labels(self):
        return [f"{entry['value']}mm   {entry.get('master') or 'no master'}" for entry in self.metal_rows]

    '''
        This function fills a part operation's thickness and master from the row it was pointed at.

        Inputs:
            row_index       The part operation row in the lower grid
            label           The label of the chosen thickness row, or empty to clear it

        output:
            None
    '''
    def _use_row(self, row_index, label):
        labels = self._labels()
        if label not in labels:
            for column in (self.METAL, self.USE):
                self.setup_grid.SetCellValue(row_index, column, "")
            return

        entry = self.metal_rows[labels.index(label)]
        self.setup_grid.SetCellValue(row_index, self.METAL, entry["value"])
        self.setup_grid.SetCellValue(row_index, self.USE, label)
        if entry.get("master"):
            self.setup_grid.SetCellValue(row_index, self.MASTER, entry["master"])                                #Only where the row states one

    def _on_use_chosen(self, event):
        if event.GetCol() == self.USE:
            self._use_row(event.GetRow(), self.setup_grid.GetCellValue(event.GetRow(), self.USE).strip())
            self.setup_grid.AutoSizeColumns()
            self.setup_grid.ForceRefresh()
        event.Skip()

    '''
        This function drops the list open as soon as the cell is clicked, rather than on a second click.
    '''
    def _on_select_cell(self, event):
        if event.GetCol() in (self.MASTER, self.BUILT_IN, self.USE):
            wx.CallAfter(self.setup_grid.EnableCellEditControl)                                                   #After the selection settles
        event.Skip()

    '''
        This function points every part operation that has no row yet at the only one there is.

        Where the process turns up a single thickness there is nothing to choose between, so
        making each part operation say so by hand would be busywork.

        output:
            The number of part operations that were filled in
    '''
    def _default_single_row(self):
        if len(self.metal_rows) != 1:
            return 0
        label = self._labels()[0]
        filled = 0
        for row_index in range(self.setup_grid.GetNumberRows()):
            if not self.setup_grid.GetCellValue(row_index, self.USE).strip():
                self._use_row(row_index, label)
                filled += 1
        return filled

    '''
        This function redraws the thickness rows and re-points the part operation dropdowns at them.
    '''
    def _fill_metal_grid(self):
        difference = len(self.metal_rows) - self.metal_grid.GetNumberRows()
        if difference > 0:
            self.metal_grid.AppendRows(difference)
        elif difference < 0:
            self.metal_grid.DeleteRows(0, -difference)

        for row_index, entry in enumerate(self.metal_rows):
            self.metal_grid.SetCellValue(row_index, 0, entry["value"])
            self.metal_grid.SetCellValue(row_index, 1, entry.get("master") or "not stated")
            self.metal_grid.SetCellValue(row_index, 2, entry["source"])
            self.metal_grid.SetCellValue(row_index, 3, "added by hand" if entry["custom"] else "from the part")
            if entry["custom"]:
                self.metal_grid.SetCellEditor(row_index, 1, wx.grid.GridCellChoiceEditor(
                    [""] + list(TEMPLATES["masters"]), False))
            for column, editable in ((0, entry["custom"]), (1, entry["custom"]),                                 #What the part states is not retyped
                                     (2, entry["custom"]), (3, False)):
                self.metal_grid.SetReadOnly(row_index, column, not editable)
            colour = wx.Colour(255, 242, 204) if entry["custom"] else wx.WHITE
            for column in range(4):
                self.metal_grid.SetCellBackgroundColour(row_index, column, colour)
        self.metal_grid.AutoSizeColumns()

        labels = self._labels()
        for row_index in range(self.setup_grid.GetNumberRows()):                                                 #Dropdown of whatever rows now exist
            self.setup_grid.SetCellEditor(row_index, self.USE,
                                          wx.grid.GridCellChoiceEditor([""] + labels, False))
            if self.setup_grid.GetCellValue(row_index, self.USE) not in labels:
                for column in (self.METAL, self.USE):
                    self.setup_grid.SetCellValue(row_index, column, "")
        self.setup_grid.AutoSizeColumns()
        self.metal_grid.ForceRefresh()
        self.setup_grid.ForceRefresh()

    def _on_metal_edited(self, event):
        row_index = event.GetRow()
        if 0 <= row_index < len(self.metal_rows):
            entry = self.metal_rows[row_index]
            entry["value"] = self.metal_grid.GetCellValue(row_index, 0).strip()
            entry["master"] = self.metal_grid.GetCellValue(row_index, 1).strip()
            entry["source"] = self.metal_grid.GetCellValue(row_index, 2).strip()
            if entry["master"] == "not stated":
                entry["master"] = ""
            self._fill_metal_grid()
        event.Skip()

    def _on_add(self, event):
        dialog = wx.TextEntryDialog(self, "Metal thickness in mm:", "Add row", "")
        value = dialog.GetValue().strip() if dialog.ShowModal() == wx.ID_OK else None
        dialog.Destroy()
        if not value:
            return
        try:
            float(value)
        except ValueError:
            wx.MessageBox(f"'{value}' is not a number.", "Add row", wx.OK | wx.ICON_WARNING, self)
            return
        if value in self._values():
            wx.MessageBox(f"{value}mm is already listed.", "Add row", wx.OK | wx.ICON_INFORMATION, self)
            return

        masters = list(TEMPLATES["masters"])
        choose = wx.SingleChoiceDialog(self, f"{value}mm - which side is master?", "Add row", masters)
        master = masters[choose.GetSelection()] if choose.ShowModal() == wx.ID_OK else ""
        choose.Destroy()

        self.metal_rows.append({"value": value, "master": master, "source": "added by hand", "custom": True})
        self._fill_metal_grid()
        self._default_single_row()

    def _on_delete(self, event):
        selected = self.metal_grid.GetSelectedRows() or [self.metal_grid.GetGridCursorRow()]
        row_index = selected[0] if selected else -1
        if not (0 <= row_index < len(self.metal_rows)):
            return

        entry = self.metal_rows[row_index]
        if not entry["custom"]:
            wx.MessageBox("That thickness was read from the design part, so it cannot be deleted.\n\n"
                          "Only rows added by hand can be removed.", "Delete row",
                          wx.OK | wx.ICON_INFORMATION, self)
            return

        using = [row["name"] for index, row in enumerate(self.part_ops)
                 if self.setup_grid.GetCellValue(index, self.METAL) == entry["value"]]
        if using and wx.MessageBox(f"{entry['value']}mm is in use by:\n\n" + "\n".join(using)
                                   + "\n\nDelete it anyway? Those part operations will be left "
                                     "with no thickness.", "Delete row",
                                   wx.YES_NO | wx.ICON_QUESTION, self) != wx.YES:
            return

        del self.metal_rows[row_index]
        self._fill_metal_grid()

    '''
        This function writes the choices back onto the part operations.
    '''
    def apply(self):
        for row_index, row in enumerate(self.part_ops):
            row["code"] = self.setup_grid.GetCellValue(row_index, self.CODE).strip()
            row["spotting"] = self.setup_grid.GetCellValue(row_index, self.SPOTTING).strip()
            row["spotting_mode"] = self.setup_grid.GetCellValue(row_index, self.BUILT_IN).strip()
            chosen = self.setup_grid.GetCellValue(row_index, self.METAL).strip()
            master = self.setup_grid.GetCellValue(row_index, self.MASTER).strip()

            row["metal"] = chosen or None
            if master:
                row["master"] = master                                                                           #The row that was picked states both
            if chosen:
                entry = next((e for e in self.metal_rows if e["value"] == chosen), None)
                row["metal_note"] = (f"{chosen}mm added by hand" if entry and entry["custom"]
                                     else f"{chosen}mm from the part")
            else:
                row["metal_note"] = "no thickness chosen"
        return self.metal_rows


class EditDialog(wx.Dialog):
    """Gives one activity - or a selected group of them - a name and a comment from the
    template lists."""

    PREVIEW_LINES = 9                                                                                            #The most the preview ever shows, for a program

    def __init__(self, parent, row, settings, rows=None, group=None):
        self.group = group if group and len(group) > 1 else None                                                 #None for the ordinary single-row edit
        title = (f"Set {len(self.group)} {row['kind'].lower()}s - from {row['name']}" if self.group
                 else f"Set {row['kind'].lower()} - {row['name']}")
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.row = row
        self.settings = settings
        self.rows = rows or [row]                                                                                #Needed to see which numbers are already in use
        self.new_name = row["new_name"] or ""
        self.new_comment = row["new_comment"] or ""
        self.current_name = row["name"] or ""                                                                    #What is on the activity now
        self.current_comment = row["comment"] or ""
        self.new_instruction = row.get("new_instruction") or ""
        self.current_instruction = row.get("instruction") or ""
        self.is_instruction = row["activity_type"] in INSTRUCTION_TYPES
        self.composed = None                                                                                     #What Build comment last wrote, so a group knows to recompose
        self.built_used = False                                                                                  #Whether [Use as name] was pressed - a group numbers on from it
        self.name_prefill = self.new_name or self.current_name                                                   #A group only takes what was actually changed
        self.comment_prefill = self.new_comment or self.current_comment
        self.instruction_prefill = self.new_instruction or self.current_instruction

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        if self.group:
            note = (f"Editing {len(self.group)} programs. A built name numbers on in sequence from "
                    f"here, a composed comment is built again for each program with its own tool "
                    f"and offset, and only what is changed below is applied. Dividers keep their "
                    f"names." if row["kind"] == "Program" else
                    f"Editing {len(self.group)} rows. Only what is changed below is applied, the "
                    f"same to every one.")
            group_note = wx.StaticText(panel, label=note)
            group_note.SetForegroundColour(wx.Colour(0, 97, 0))
            vbox.Add(group_note, 0, wx.ALL, 8)

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

        if row["kind"] in ("Part Operation", "Program"):
            self.comment_choice = wx.TextCtrl(panel, style=wx.TE_MULTILINE, size=(-1, 74))                        #The comment runs to several lines
        else:
            self.comment_choice = wx.ComboBox(panel, choices=[""] + self._comment_templates(),
                                              style=wx.CB_DROPDOWN)
        self.comment_choice.SetValue(self.new_comment or self.current_comment)
        grid_sizer.Add(wx.StaticText(panel, label="Comment"), 0, wx.ALIGN_TOP | wx.TOP, 4)
        grid_sizer.Add(self.comment_choice, 1, wx.EXPAND)

        if self.is_instruction:                                                                                  #What the post processor reads, not the name
            self.instruction_choice = wx.ComboBox(panel, choices=[""] + TEMPLATES["instructions"],
                                                  style=wx.CB_DROPDOWN)
            self.instruction_choice.SetValue(self.new_instruction or self.current_instruction)
            self.instruction_choice.Bind(wx.EVT_TEXT, self._on_change)
            grid_sizer.Add(wx.StaticText(panel, label="PP instruction"), 0, wx.ALIGN_CENTER_VERTICAL)
            grid_sizer.Add(self.instruction_choice, 1, wx.EXPAND)
        else:
            self.instruction_choice = None

        vbox.Add(grid_sizer, 0, wx.EXPAND | wx.ALL, 8)

        if row["kind"] == "Part Operation":
            vbox.Add(self._part_operation_composer(panel), 0, wx.EXPAND | wx.ALL, 8)                             #UPPER IS MASTER / METAL IS 1.5MM
        if row["kind"] == "Program":
            vbox.Add(self._name_builder(panel), 0, wx.EXPAND | wx.ALL, 8)                                        #A104D4503LP01
            vbox.Add(self._composer(panel), 0, wx.EXPAND | wx.ALL, 8)                                            #TOOL DESCRIPTION TO OFFSETMM

        self.preview = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_NONE,                #Wraps, rather than running off the edge
                                   size=(-1, 16 * self.PREVIEW_LINES))
        self.preview.SetFont(wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        self.preview.SetBackgroundColour(panel.GetBackgroundColour())
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
        This function builds the multi line comment a part operation carries.

        The comment is several lines - the job description, which side is master, the metal
        thickness, the profile thickness - so they are ticked rather than typed. The master and
        the metal are already known from the design part, so those lines come out filled in.
    '''
    def _part_operation_composer(self, panel):
        box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Compose comment")

        inner = wx.FlexGridSizer(0, 2, 6, 8)
        inner.AddGrowableCol(1, 1)
        self.job_choice = wx.ComboBox(panel, choices=[""] + TEMPLATES["job_descriptions"], style=wx.CB_DROPDOWN)
        inner.Add(wx.StaticText(panel, label="Job description"), 0, wx.ALIGN_CENTER_VERTICAL)
        inner.Add(self.job_choice, 1, wx.EXPAND)
        box.Add(inner, 0, wx.EXPAND | wx.ALL, 6)

        master = self.row.get("master")
        metal = self.row.get("metal")

        self.line_checks = []
        for key, label, known in (
                ("master", f"{master} IS MASTER" if master else "UPPER IS MASTER", bool(master)),
                ("metal", f"METAL IS {metal}MM" if metal else "METAL IS **.**MM", bool(metal))):
            check = wx.CheckBox(panel, label=label + ("" if known else "   (not read from the part)"))
            check.SetValue(known)                                                                                #What the part states is ticked to start with
            check.Bind(wx.EVT_CHECKBOX, self._on_change)
            self.line_checks.append((key, check, label))
            box.Add(check, 0, wx.LEFT | wx.BOTTOM, 12)

        profiles = wx.BoxSizer(wx.HORIZONTAL)                                                                    #Nothing in the part states this one - type it
        self.profiles_check = wx.CheckBox(panel, label="PROFILES ARE")
        self.profiles_check.Bind(wx.EVT_CHECKBOX, self._on_change)
        self.profiles_text = wx.TextCtrl(panel, size=(60, -1))
        self.profiles_text.Bind(wx.EVT_TEXT, self._on_change)
        profiles.Add(self.profiles_check, 0, wx.ALIGN_CENTER_VERTICAL)
        profiles.Add(self.profiles_text, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 6)
        profiles.Add(wx.StaticText(panel, label="MM"), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 4)
        box.Add(profiles, 0, wx.LEFT | wx.BOTTOM, 12)

        build_button = wx.Button(panel, label="Build comment")
        build_button.Bind(wx.EVT_BUTTON, self._on_build_part_operation_comment)
        box.Add(build_button, 0, wx.LEFT | wx.BOTTOM, 12)

        self.job_choice.Bind(wx.EVT_TEXT, self._on_change)
        return box

    '''
        This function assembles the ticked lines into the comment box.
    '''
    def _on_build_part_operation_comment(self, event):
        lines = []
        job = self.job_choice.GetValue().strip()
        if job:
            lines.append(job)
        for key, check, label in self.line_checks:
            if check.GetValue():
                lines.append(label)

        if self.profiles_check.GetValue():
            value = self.profiles_text.GetValue().strip()
            lines.append(f"PROFILES ARE {value}MM" if value else "PROFILES ARE **.**MM")

        if not lines:
            wx.MessageBox("Tick a line or pick a job description first.", "Compose comment",
                          wx.OK | wx.ICON_INFORMATION, self)
            return

        self.comment_choice.SetValue("\n".join(lines))
        self._update_preview()

    '''
        This function builds the program name from the job settings and a program number.
    '''
    def _name_builder(self, panel):
        box = wx.StaticBoxSizer(wx.HORIZONTAL, panel, "Build program name")

        part_op = part_operation_of(self.row)
        stem = job_stem(self.settings, part_op)                                                                  #The code comes from this part operation
        current_number = program_number_of(self.new_name or self.current_name, stem)                              #None where CATIA named the program
        if current_number is None:
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
        part_op = part_operation_of(self.row)
        stem = job_stem(self.settings, part_op)
        return f"{stem}{number:02d}" if stem else ""

    def _on_use_built_name(self, event):
        built = self._built_name()
        if not built:
            wx.MessageBox("Fill in Initial, Project, Die and Rev in the Job bar, and the Code for "
                          "this part operation in [Metal thicknesses].",
                          "Program name", wx.OK | wx.ICON_INFORMATION, self)
            return
        self.name_choice.SetValue(built)
        self.built_used = True                                                                                   #An explicit ask - a group renumbers even from the same name
        self._update_preview()

    '''
        This function gives the text the stage is read from.

        A staged comment is what the row is heading for, so it is read in preference to the one
        the activity still carries. Reopening a row that was edited then shows the stage that was
        staged, rather than the stage it is being changed away from.

        output:
            The staged comment, or the current comment, or the name
    '''
    def _staged_text(self):
        return (self.new_comment or self.current_comment
                or self.new_name or self.current_name)

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
        self.description_choice.SetValue(                                                                        #Edit from what is there, not from blank
            description_from_comment(self.new_comment or self.current_comment, detected))
        inner.Add(wx.StaticText(panel, label="Description"), 0, wx.ALIGN_CENTER_VERTICAL)
        inner.Add(self.description_choice, 1, wx.EXPAND)

        detected_stage, detected_nominal = stage_for_description(self._staged_text())
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
            part, ruled, note = self._offset_context(self._staged_text())                                        #Nothing measured - fall back to the rule
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
        if self.row["activity_type"] in INSTRUCTION_TYPES:
            return TEMPLATES["instruction_names"]                                                                #A post processor instruction cuts nothing
        return TEMPLATES["descriptions"]

    '''
        This function lists the comment templates that suit the kind of row being edited.
    '''
    def _comment_templates(self):
        if self.row["kind"] == "Part Operation":
            return TEMPLATES["job_descriptions"] + TEMPLATES["part_operation_comments"]
        return TEMPLATES["descriptions"]

    '''
        This function works out the offset that applies to the row being edited.

        Inputs:
            description     The description the stage is read from
            row             The row to work it out for - the dialog's own where not given

        output:
            Tuple of (what the part is, offset or None, note explaining the offset)
    '''
    def _offset_context(self, description, row=None):
        row = row or self.row
        part_op = part_operation_of(row)

        part = upper_or_lower(effective_name(part_op)) if part_op else None                                      #A staged rename decides the side too
        if part is None and row is self.row and row["kind"] == "Part Operation":
            part = upper_or_lower(self.name_choice.GetValue())                                                    #The name being given to it now

        master = (part_op.get("master") if part_op else None)                                                    #Set per part operation in [Metal thicknesses]

        stage, nominal = stage_for_description(description)
        if nominal is None:
            return part, None, "no stage in the description"

        if not master:
            return part, None, f"{stage} +{nominal} - no master set, set one with [Metal thicknesses]"

        metal_text = (part_op.get("metal") if part_op else None)                                                  #This part operation's own, never another's
        if not metal_text:
            note = (part_op or {}).get("metal_note") or "no metal thickness for this part"
            return part, None, f"{stage} +{nominal} - {note}, set one with [Metal thicknesses], so no offset"

        try:
            metal = float(metal_text)
        except ValueError:
            return part, None, f"{stage} +{nominal} - metal '{metal_text}' is not a number, so no offset"

        spotting = self._spotting_allowance(part_op)                                                             #Only where it is built into the programs
        offset = offset_for(nominal, part, master, metal, spotting)
        extra = f", plus {spotting} spotting built in" if spotting else ""

        if master == "BOTH":
            return part, offset, f"{stage} nominal {nominal:+.1f}, master BOTH - nominal{extra}"
        if offset is None:
            return part, None, (f"{stage} +{nominal} - the name does not say whether this is an upper "
                                f"or a lower part, so no offset")
        if part == master:
            return part, offset, (f"{stage} nominal {nominal:+.1f}, {part} part and {master} is master - "
                                  f"nominal{extra}")
        return part, offset, (f"{stage} nominal {nominal:+.1f}, {part} part and {master} is master - "
                              f"less {metal} metal{extra}")

    '''
        This function reads the spotting allowance that is built into the programs.

        An allowance the operator holds off at the machine changes no offset here, so it counts
        as nothing.

        output:
            The allowance in mm, or 0.0
    '''
    def _spotting_allowance(self, part_op):
        if not part_op or part_op.get("spotting_mode") != "built in":
            return 0.0
        try:
            return float(part_op.get("spotting") or 0)
        except ValueError:
            return 0.0

    def _on_stage(self, event):
        nominal = STAGE_NOMINALS.get(self.stage_choice.GetValue().strip().upper())
        if nominal is not None:
            self.stage_text.SetValue(f"{nominal + self._spotting_allowance(part_operation_of(self.row)):.1f}")
        self._update_preview()
        event.Skip()

    def _on_description(self, event):
        stage, nominal = stage_for_description(self.description_choice.GetValue())
        if stage:
            self.stage_choice.SetValue(stage)                                                                    #The description says which stage it is
        if nominal is not None:
            spotting = self._spotting_allowance(part_operation_of(self.row))                                     #Material left on for hand work
            self.stage_text.SetValue(f"{nominal + spotting:.1f}")                                                #The stage offset does not move when metal comes off

        if self.row.get("offset") is None:                                                                       #Only fall back to the rule where the operations gave nothing
            part, offset, note = self._offset_context(self.description_choice.GetValue())
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
        part_op = part_operation_of(self.row)
        note = spotting_note((part_op or {}).get("spotting"),
                             (part_op or {}).get("spotting_mode") == "built in") \
            if (part_op or {}).get("spotting_mode") else ""

        self.comment_choice.SetValue(
            compose_program_comment(self.tool_choice.GetValue().strip(),
                                    self.description_choice.GetValue().strip(),
                                    stage_offset, machine_offset, note))
        self.composed = self.comment_choice.GetValue()                                                           #A group recomposes this per row rather than copying it
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
        shown = (comment or "(cleared - will not be written)").replace("\n", "\n          ")                     #Line up the second and later lines
        lines = [f"Name    : {name or '(cleared - will not be written)'}"
                 + ("   unchanged" if name == self.current_name else ""),
                 f"Comment : {shown}"
                 + ("   unchanged" if same_text(comment, self.current_comment) else "")]

        if self.instruction_choice is not None:
            instruction = self.instruction_choice.GetValue().strip()
            lines.append(f"PP instr: {instruction or '(cleared - will not be written)'}"
                         + ("   unchanged" if instruction == self.current_instruction else ""))

        if self.row["kind"] == "Program":
            built = self._built_name()
            self.built_name.SetLabel(built or "fill Initial, Project, Die and Rev, and the Code "
                                              "for this part operation")

        if self.row["kind"] == "Program":
            part, offset, note = self._offset_context(self.description_choice.GetValue())
            measured = self.row.get("offset")
            lines.append("")
            lines.append(f"Part    : {part or 'the name does not say'}")
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

        self.preview.SetValue("\n".join(lines))

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

        self.final_name = name                                                                                   #The group path works from these, not the diffs
        self.final_comment = comment
        self.final_instruction = ""

        self.new_name = "" if name == self.current_name else name                                                 #Only what actually differs is staged
        self.new_comment = "" if same_text(comment, self.current_comment) else comment

        if self.instruction_choice is not None:
            instruction = self._resolve_placeholders(self.instruction_choice.GetValue().strip(), "PP instruction")
            if instruction is None:
                return
            self.final_instruction = instruction
            self.new_instruction = "" if instruction == self.current_instruction else instruction

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

    '''
        This function composes the group comment for one row.

        The description, stage and stage offset are shared across the group - they are what the
        group has in common - but the tool and the machined offset are the row's own, so one
        program's tool is never written into another's comment.

        Inputs:
            row             A program row from the group

        output:
            The comment for that row
    '''
    def compose_for(self, row):
        stage_offset, _ = self._read_offset(self.stage_text, "Stage offset", quiet=True)
        machine_offset = row.get("offset")                                                                       #What this row's operations actually machine to
        if machine_offset is None:
            _, machine_offset, _ = self._offset_context(self.description_choice.GetValue(), row)                 #Nothing measured - the stage rule for this row
        part_op = part_operation_of(row)
        note = spotting_note((part_op or {}).get("spotting"),
                             (part_op or {}).get("spotting_mode") == "built in") \
            if (part_op or {}).get("spotting_mode") else ""
        tool = row["tool"] or self.tool_choice.GetValue().strip()
        return compose_program_comment(tool, self.description_choice.GetValue().strip(),
                                       stage_offset, machine_offset, note)

    '''
        This function stages the dialog's result onto every row of the group.

        Only what was actually changed in the dialog is applied, so opening a group and staging
        with the name untouched does not rename every program to the first one's name. A built
        program name numbers on in sequence from the number it carries, skipping dividers, and a
        comment built with the composer is composed again for each row rather than copied.

        output:
            The number of rows staged
    '''
    def apply_group(self):
        name_changed = bool(self.final_name) and (self.final_name != self.name_prefill
                                                  or self.built_used)
        comment_changed = not same_text(self.final_comment, self.comment_prefill)
        composed = bool(self.final_comment) and same_text(self.final_comment, self.composed)
        instruction_changed = (self.instruction_choice is not None
                               and self.final_instruction != self.instruction_prefill)

        number = None
        if name_changed and self.row["kind"] == "Program":
            number = program_number_of(self.final_name,
                                       job_stem(self.settings, part_operation_of(self.row)))                     #None where the name is not a built one

        staged = 0
        for row in self.group:
            if name_changed:
                name = self.final_name
                if number is not None:
                    if is_divider(effective_name(row)):
                        name = None                                                                              #A heading keeps its name and takes no number
                    else:
                        stem = job_stem(self.settings, part_operation_of(row))
                        if stem:
                            name = f"{stem}{number:02d}"
                            number += 1
                if name is not None:
                    row["new_name"] = "" if name == row["name"] else name

            recompose = composed and self.row["kind"] == "Program"
            if (comment_changed or recompose) and not (recompose and is_divider(effective_name(row))):
                comment = self.compose_for(row) if recompose else self.final_comment                             #A heading machines nothing - no composed comment
                row["new_comment"] = "" if same_text(comment, row["comment"]) else comment

            if instruction_changed and row["activity_type"] in INSTRUCTION_TYPES:
                row["new_instruction"] = ("" if self.final_instruction == (row.get("instruction") or "")
                                          else self.final_instruction)

            if is_staged(row):
                staged += 1
        return staged


class TemplateEditor(wx.Dialog):
    """Adds, edits, reorders and removes the entries in the template lists."""

    def __init__(self, parent, settings_dir):
        super().__init__(parent, title="Edit templates", size=(880, 620),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.settings_dir = settings_dir
        self.working = json.loads(json.dumps(TEMPLATES))                                                         #Edited here, only copied back on Save

        panel = wx.Panel(self)
        outer = wx.BoxSizer(wx.HORIZONTAL)

        self.list_choice = wx.ListBox(panel, choices=[label for _, label in TEMPLATE_LISTS], size=(200, -1))
        self.list_choice.SetSelection(0)
        self.list_choice.Bind(wx.EVT_LISTBOX, self._on_list_chosen)
        outer.Add(self.list_choice, 0, wx.EXPAND | wx.ALL, 8)

        right = wx.BoxSizer(wx.VERTICAL)
        self.caption = wx.StaticText(panel, label="")
        right.Add(self.caption, 0, wx.ALL, 6)

        self.entries = wx.ListBox(panel, style=wx.LB_SINGLE)
        self.entries.Bind(wx.EVT_LISTBOX_DCLICK, self._on_edit)
        right.Add(self.entries, 1, wx.EXPAND | wx.ALL, 6)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in (("Add", self._on_add), ("Edit", self._on_edit), ("Remove", self._on_remove),
                               ("Move up", self._on_up), ("Move down", self._on_down),
                               ("Sort", self._on_sort), ("Reset this list", self._on_reset_list)):
            button = wx.Button(panel, label=label)
            button.Bind(wx.EVT_BUTTON, handler)
            buttons.Add(button, 0, wx.RIGHT, 4)
        right.Add(buttons, 0, wx.ALL, 6)
        outer.Add(right, 1, wx.EXPAND)

        panel.SetSizer(outer)

        self.use_defaults = wx.CheckBox(self, label="Use the entries built into the script")
        self.use_defaults.SetValue(TEMPLATE_STATE["use_defaults"])
        self.use_defaults.SetToolTip("Untick to keep only the entries you have added, so the "
                                     "shipped lists do not appear in the dropdowns.")
        self.use_defaults.Bind(wx.EVT_CHECKBOX, self._on_use_defaults)

        bottom = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in (("Import...", self._on_import), ("Export...", self._on_export)):
            button = wx.Button(self, label=label)
            button.Bind(wx.EVT_BUTTON, handler)
            bottom.Add(button, 0, wx.RIGHT, 4)
        reset_all = wx.Button(self, label="Reset every list to defaults")
        reset_all.Bind(wx.EVT_BUTTON, self._on_reset_all)
        bottom.Add(reset_all, 0, wx.RIGHT, 8)
        bottom.Add(self.use_defaults, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        bottom.AddStretchSpacer()
        save = wx.Button(self, wx.ID_OK, "Save")
        save.SetDefault()
        bottom.Add(save, 0, wx.RIGHT, 4)
        bottom.Add(wx.Button(self, wx.ID_CANCEL), 0)

        frame = wx.BoxSizer(wx.VERTICAL)
        frame.Add(panel, 1, wx.EXPAND)
        frame.Add(bottom, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizer(frame)

        self._show_list()
        self.Center()

    def _key(self):
        return TEMPLATE_LISTS[self.list_choice.GetSelection()][0]

    def _show_list(self):
        key = self._key()
        self.entries.Set(self.working[key])
        label = dict(TEMPLATE_LISTS)[key]
        self.caption.SetLabel(f"{label} - {len(self.working[key])} entr"
                              f"{'y' if len(self.working[key]) == 1 else 'ies'}")

    def _on_list_chosen(self, event):
        self._show_list()

    def _ask(self, title, value=""):
        dialog = wx.TextEntryDialog(self, "Entry:", title, value)
        dialog.SetSize((560, 180))
        text = dialog.GetValue().strip() if dialog.ShowModal() == wx.ID_OK else None
        dialog.Destroy()
        return text

    def _on_add(self, event):
        text = self._ask("Add entry")
        if not text:
            return
        key = self._key()
        if text in self.working[key]:
            wx.MessageBox("That entry is already in the list.", "Add", wx.OK | wx.ICON_INFORMATION, self)
            return
        self.working[key].append(text)
        self._show_list()
        self.entries.SetSelection(len(self.working[key]) - 1)

    def _on_edit(self, event):
        index = self.entries.GetSelection()
        if index == wx.NOT_FOUND:
            return
        key = self._key()
        text = self._ask("Edit entry", self.working[key][index])
        if not text:
            return
        self.working[key][index] = text
        self._show_list()
        self.entries.SetSelection(index)

    def _on_remove(self, event):
        index = self.entries.GetSelection()
        if index == wx.NOT_FOUND:
            return
        key = self._key()
        entry = self.working[key][index]
        if wx.MessageBox(f"Remove '{entry}'?", "Remove", wx.YES_NO | wx.ICON_QUESTION, self) != wx.YES:
            return
        del self.working[key][index]
        self._show_list()

    def _move(self, step):
        index = self.entries.GetSelection()
        key = self._key()
        if index == wx.NOT_FOUND or not (0 <= index + step < len(self.working[key])):
            return
        entries = self.working[key]
        entries[index], entries[index + step] = entries[index + step], entries[index]
        self._show_list()
        self.entries.SetSelection(index + step)

    def _on_up(self, event):
        self._move(-1)

    def _on_down(self, event):
        self._move(1)

    def _on_sort(self, event):
        key = self._key()
        self.working[key] = sorted(self.working[key])
        self._show_list()

    def _on_reset_list(self, event):
        key = self._key()
        label = dict(TEMPLATE_LISTS)[key]
        question = (f"Put {label} back to the entries the script ships with?"
                    if DEFAULT_TEMPLATES[key] else
                    f"{label} ships empty - the entries are yours, not the script's.\n\n"       #Nothing to put back
                    f"Resetting empties the list. Carry on?")
        if wx.MessageBox(question, "Reset", wx.YES_NO | wx.ICON_QUESTION, self) != wx.YES:
            return
        self.working[key] = list(DEFAULT_TEMPLATES[key])
        self._show_list()

    def _on_reset_all(self, event):
        if wx.MessageBox("Put every list back to the entries the script ships with?\n\n"
                         "Anything added or edited is lost.", "Reset",
                         wx.YES_NO | wx.ICON_QUESTION, self) != wx.YES:
            return
        self.working = json.loads(json.dumps(DEFAULT_TEMPLATES))
        self._show_list()

    '''
        This function takes the shipped entries out of the lists, or puts them back.

        Unticking leaves only what was added by hand, so a shop that names things its own way is
        not made to scroll past entries it never uses. The shipped lists are still held, so
        ticking again restores them and nothing added by hand is lost either way.
    '''
    def _on_use_defaults(self, event):
        if self.use_defaults.GetValue():
            for key, _ in TEMPLATE_LISTS:
                added = [entry for entry in self.working[key] if entry not in DEFAULT_TEMPLATES[key]]
                self.working[key] = list(DEFAULT_TEMPLATES[key]) + added                                          #Shipped first, then anything added
            self._show_list()
            return

        kept = sum(len([e for e in self.working[key] if e not in DEFAULT_TEMPLATES[key]])
                   for key, _ in TEMPLATE_LISTS)
        if wx.MessageBox("Take the entries built into the script out of every list, leaving only "
                         f"what you have added?\n\nThat leaves {kept} entr"
                         f"{'y' if kept == 1 else 'ies'} across all lists. Ticking the box again "
                         "puts the shipped entries back.",
                         "Use the entries built into the script",
                         wx.YES_NO | wx.ICON_QUESTION, self) != wx.YES:
            self.use_defaults.SetValue(True)
            return

        for key, _ in TEMPLATE_LISTS:
            self.working[key] = [entry for entry in self.working[key] if entry not in DEFAULT_TEMPLATES[key]]
        self._show_list()

    '''
        This function writes the lists out to a file that can be given to someone else.
    '''
    def _on_export(self, event):
        dialog = wx.FileDialog(self, "Export templates", wildcard="JSON files (*.json)|*.json",
                               defaultFile="program_templates.json",
                               style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dialog.ShowModal() != wx.ID_OK:
            dialog.Destroy()
            return
        path = dialog.GetPath()
        dialog.Destroy()

        content = {key: self.working[key] for key, _ in TEMPLATE_LISTS}
        content["_use_defaults"] = self.use_defaults.GetValue()
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(content, handle, indent=2)
        except Exception as error:
            wx.MessageBox(f"It could not be written:\n\n{error}", "Export", wx.OK | wx.ICON_ERROR, self)
            return
        wx.MessageBox(f"Written to:\n\n{path}", "Export", wx.OK | wx.ICON_INFORMATION, self)

    '''
        This function reads lists back in from a file.

        Only the lists the file actually holds are taken, so a file carrying just the tools can be
        imported without disturbing anything else.
    '''
    def _on_import(self, event):
        dialog = wx.FileDialog(self, "Import templates", wildcard="JSON files (*.json)|*.json",
                               style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dialog.ShowModal() != wx.ID_OK:
            dialog.Destroy()
            return
        path = dialog.GetPath()
        dialog.Destroy()

        try:
            with open(path, "r", encoding="utf-8") as handle:
                content = json.load(handle)
        except Exception as error:
            wx.MessageBox(f"It could not be read:\n\n{error}", "Import", wx.OK | wx.ICON_ERROR, self)
            return

        known = {key for key, _ in TEMPLATE_LISTS}
        found = {key: value for key, value in (content or {}).items()
                 if key in known and isinstance(value, list) and all(isinstance(e, str) for e in value)}
        if not found:
            wx.MessageBox("There are no template lists in that file.", "Import",
                          wx.OK | wx.ICON_WARNING, self)
            return

        labels = dict(TEMPLATE_LISTS)
        summary = "\n".join(f"   {labels[key]}: {len(value)} entr{'y' if len(value) == 1 else 'ies'}"
                            for key, value in sorted(found.items()))
        choice = wx.MessageBox(f"The file holds:\n\n{summary}\n\n"
                               f"Yes replaces those lists with what the file holds.\n"
                               f"No adds the entries that are not already there.",
                               "Import", wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION, self)
        if choice == wx.CANCEL:
            return

        for key, value in found.items():
            if choice == wx.YES:
                self.working[key] = list(value)
            else:
                self.working[key] += [entry for entry in value if entry not in self.working[key]]

        if "_use_defaults" in (content or {}):
            self.use_defaults.SetValue(bool(content["_use_defaults"]))
        self._show_list()
        wx.MessageBox(f"{len(found)} list(s) imported. Press Save to keep them.", "Import",
                      wx.OK | wx.ICON_INFORMATION, self)

    '''
        This function copies the edited lists back and saves them.
    '''
    def save(self):
        for key, _ in TEMPLATE_LISTS:
            TEMPLATES[key] = self.working[key]
        TEMPLATE_STATE["use_defaults"] = self.use_defaults.GetValue()
        return save_templates(self.settings_dir)


class LimitsDialog(wx.Dialog):
    """Edits the allowed values the settings are checked against."""

    FIELDS = (                                                                                                   #(limits key, stage key or None, label)
        ("stepover", "ROUGHING", "Roughing stepover mm"),
        ("stepover", "SEMI-FINISH", "Semi-finish stepover mm"),
        ("stepover", "FINISH", "Finish stepover mm"),
        ("roughing_overlap", None, "Roughing operation pass overlap %"),
        ("roughing_depth_of_cut", None, "Roughing operation depth of cut mm"),
    )

    def __init__(self, parent, settings_dir):
        super().__init__(parent, title="Edit limits", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.settings_dir = settings_dir

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        vbox.Add(wx.StaticText(panel, label="The allowed values, as comma separated lists. A stepover, "
                                            "depth of cut or offset off its list is shown on red in "
                                            "the grid.\nThe stage limits go by the operation's stage; "
                                            "the Roughing rows are the CATIA Roughing operation, "
                                            "whatever its stage."), 0, wx.ALL, 8)

        grid_sizer = wx.FlexGridSizer(0, 2, 6, 8)
        grid_sizer.AddGrowableCol(1, 1)
        self.fields = {}
        for key, stage, label in self.FIELDS:
            values = LIMITS[key][stage] if stage else LIMITS[key]
            field = wx.TextCtrl(panel, value=", ".join(f"{value:g}" for value in values), size=(220, -1))
            self.fields[(key, stage)] = field
            grid_sizer.Add(wx.StaticText(panel, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            grid_sizer.Add(field, 1, wx.EXPAND)
        vbox.Add(grid_sizer, 0, wx.EXPAND | wx.ALL, 8)

        reset_button = wx.Button(panel, label="Reset to defaults")
        reset_button.Bind(wx.EVT_BUTTON, self._on_reset)
        vbox.Add(reset_button, 0, wx.LEFT | wx.BOTTOM, 8)

        buttons = wx.StdDialogButtonSizer()
        save_button = wx.Button(panel, wx.ID_OK, "Save")
        save_button.SetDefault()
        buttons.AddButton(save_button)
        buttons.AddButton(wx.Button(panel, wx.ID_CANCEL))
        buttons.Realize()
        vbox.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 8)

        panel.SetSizer(vbox)
        frame = wx.BoxSizer(wx.VERTICAL)
        frame.Add(panel, 1, wx.EXPAND)
        self.SetSizer(frame)
        frame.Fit(self)
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self.Center()

    def _on_reset(self, event):
        for key, stage, _ in self.FIELDS:
            values = DEFAULT_LIMITS[key][stage] if stage else DEFAULT_LIMITS[key]
            self.fields[(key, stage)].SetValue(", ".join(f"{value:g}" for value in values))

    '''
        This function reads the fields back, refusing anything that is not a list of numbers.
    '''
    def _on_ok(self, event):
        parsed = {}
        for key, stage, label in self.FIELDS:
            text = self.fields[(key, stage)].GetValue()
            try:
                values = [float(piece) for piece in text.replace(";", ",").split(",") if piece.strip()]
            except ValueError:
                wx.MessageBox(f"'{text}' is not a list of numbers - see {label}.", "Edit limits",
                              wx.OK | wx.ICON_WARNING, self)
                return
            if not values:
                wx.MessageBox(f"{label} cannot be empty - every check needs at least one value.",
                              "Edit limits", wx.OK | wx.ICON_WARNING, self)
                return
            parsed[(key, stage)] = values

        for (key, stage), values in parsed.items():
            if stage:
                LIMITS[key][stage] = values
            else:
                LIMITS[key] = values
        self.saved = save_limits(self.settings_dir)
        event.Skip()


class RenumberDialog(wx.Dialog):
    """Renumbers the programs, part operation by part operation."""

    HEADER_COLOUR = wx.Colour(157, 195, 230)                                                                     #Matches the part operation rows in the main grid

    NAME, START, STEP, NUMBER, NEW_NAME = range(5)                                                               #Columns

    def __init__(self, parent, program_rows, settings):
        super().__init__(parent, title="Renumber programs", size=(860, 620),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.settings = settings

        # One entry per grid row - a part operation heading, or one of its programs. The numbering
        # is per part operation, so the programs sit under their own heading rather than in one list.
        self.lines = []
        for row in program_rows:
            part_op = part_operation_of(row)
            if not any(line[0] == "header" and line[1] is part_op for line in self.lines):
                self.lines.append(("header", part_op))
            self.lines.append(("program", row))

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        top = wx.BoxSizer(wx.HORIZONTAL)
        self.rebuild_check = wx.CheckBox(panel, label="Rebuild the whole name from the job settings")
        self.rebuild_check.SetValue(True)                                                                        #Off leaves the name alone but for its number
        top.Add(self.rebuild_check, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 16)

        sequence_button = wx.Button(panel, label="Number in sequence")
        sequence_button.Bind(wx.EVT_BUTTON, self._on_sequence)
        top.Add(sequence_button, 0, wx.LEFT, 12)
        vbox.Add(top, 0, wx.ALL, 8)

        note = wx.StaticText(panel, label="Each part operation has its own Start and Step, on its blue row. "
                                          "Dividers are skipped. Type in the Number column to set one by hand.")
        vbox.Add(note, 0, wx.LEFT | wx.BOTTOM, 10)

        self.grid = wx.grid.Grid(panel)
        self.grid.CreateGrid(len(self.lines), 5)
        for index, label in enumerate(("Current name", "Start", "Step", "Number", "New name")):
            self.grid.SetColLabelValue(index, label)

        for row_index, (kind, row) in enumerate(self.lines):
            if kind == "header":
                self.grid.SetCellValue(row_index, self.NAME, (effective_name(row) if row else "(no part operation)"))
                self.grid.SetCellValue(row_index, self.START, "1")                                               #This part operation's own numbering
                self.grid.SetCellValue(row_index, self.STEP, "1")
                for column in range(5):
                    self.grid.SetReadOnly(row_index, column, column not in (self.START, self.STEP))
                    self.grid.SetCellBackgroundColour(row_index, column, self.HEADER_COLOUR)
                continue
            number = program_number_of(effective_name(row),                                                      #Blank where CATIA named it
                                       job_stem(settings, part_operation_of(row)))
            self.grid.SetCellValue(row_index, self.NAME, "    " + effective_name(row))                           #What it will be called, staging included
            self.grid.SetCellValue(row_index, self.NUMBER, str(number) if number is not None else "")
            for column in (self.NAME, self.START, self.STEP, self.NEW_NAME):
                self.grid.SetReadOnly(row_index, column, True)
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
        This function fills the Number column in sequence, restarting for every part operation.
    '''
    def _on_sequence(self, event):
        number, step = 1, 1
        for row_index, (kind, row) in enumerate(self.lines):
            if kind == "header":
                try:
                    number = int(self.grid.GetCellValue(row_index, self.START).strip())                          #This part operation's own start
                    step = int(self.grid.GetCellValue(row_index, self.STEP).strip())
                except ValueError:
                    name = self.grid.GetCellValue(row_index, self.NAME)
                    wx.MessageBox(f"Start and step must be whole numbers - see {name}.",
                                  "Renumber", wx.OK | wx.ICON_WARNING, self)
                    return
                continue
            if is_divider(row["name"]):
                self.grid.SetCellValue(row_index, self.NUMBER, "")                                               #A heading carries no number
                continue
            self.grid.SetCellValue(row_index, self.NUMBER, str(number))
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
        for row_index, (kind, row) in enumerate(self.lines):
            if kind == "header":
                continue
            text = self.grid.GetCellValue(row_index, self.NUMBER).strip()
            if not text or is_divider(effective_name(row)):
                self.grid.SetCellValue(row_index, self.NEW_NAME, "")
                continue
            try:
                number = int(text)
            except ValueError:
                self.grid.SetCellValue(row_index, self.NEW_NAME, "not a number")
                continue

            stem = job_stem(self.settings, part_operation_of(row))
            if rebuild and stem:
                new_name = f"{stem}{number:02d}"
            elif program_number_of(effective_name(row), stem) is not None:
                new_name = f"{stem}{number:02d}"                                                                 #Keep the name, change the number
            elif stem:
                new_name = f"{stem}{number:02d}"                                                                 #CATIA named this one - there is no stem worth keeping
            else:
                existing, _ = split_program_number(effective_name(row))
                new_name = f"{existing}{number:02d}" if existing else f"{number:02d}"
            self.grid.SetCellValue(row_index, self.NEW_NAME, new_name)
        self.grid.ForceRefresh()

    '''
        This function hands back the names that were worked out.

        output:
            Dict of row to new name, for the programs that got one
    '''
    def staged_names(self):
        names = {}
        for row_index, (kind, row) in enumerate(self.lines):
            if kind == "header":
                continue
            new_name = self.grid.GetCellValue(row_index, self.NEW_NAME).strip()
            if new_name and new_name != "not a number" and new_name != effective_name(row):
                names[id(row)] = new_name
        return names


class TreeFrame(wx.Frame):
    """The machining tree, the staged edits, and the button that writes them."""

    COLUMNS = (("Level", "Operation", "Name", "Comment", "PP instruction", "Tool") + PARAMETER_LABELS
               + ("Stage", "Nominal"))

    NAME_COLUMN, COMMENT_COLUMN, INSTRUCTION_COLUMN = 2, 3, 4                                                    #Staged values are shown in place, and coloured

    ROW_COLOURS = {                                                                                              #Blue for the two upper levels, warm for operations
        "Part Operation": wx.Colour(157, 195, 230),
        "Program": wx.Colour(208, 227, 245),
        "Operation": wx.Colour(252, 249, 241),
    }
    DIVIDER_COLOUR = wx.Colour(255, 230, 153)                                                                    #*** heading *** programs
    STAGED_COLOUR = wx.Colour(169, 224, 178)                                                                     #A value waiting to be written
    STAGED_MARK_COLOUR = wx.Colour(112, 173, 122)                                                                #Row marker, so staged rows are findable at a glance
    BAD_COLOUR = wx.Colour(255, 199, 206)                                                                        #A value off the allowed list, or an offset off the rule
    BAD_TEXT_COLOUR = wx.Colour(156, 0, 6)

    BUTTON_GROUPS = (                                                                                            #The buttons, grouped by function and coloured to match
        ("editing", wx.Colour(189, 215, 238)),
        ("staging", wx.Colour(198, 224, 180)),
        ("settings", wx.Colour(255, 230, 153)),
        ("window", None),
    )

    def __init__(self, rows, job_info, settings, settings_dir, ppr_document=None):
        super().__init__(None, title="Manage Program Names And Comments", size=(1400, 760))
        self.SetIcon(_make_icon())
        self.rows = rows
        self.settings = settings
        self.settings_dir = settings_dir
        self.ppr_document = ppr_document                                                                         #Kept so the tree can be read again
        self.metal_rows = collect_metal_rows(rows)

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        self.header = wx.StaticText(panel, label=self._job_summary())
        self.header.SetFont(wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        vbox.Add(self.header, 0, wx.ALL, 8)

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
        groups = {
            "editing": (("Edit selected rows", self._on_edit_row),
                        ("Metal thicknesses", self._on_metal),
                        ("Renumber programs", self._on_renumber)),
            "staging": (("Clear staged edit", self._on_clear),
                        ("Apply staged edits to CATIA", self._on_apply)),
            "settings": (("Edit templates", self._on_templates),
                         ("Edit limits", self._on_limits),
                         ("Clear saved settings", self._on_clear_settings)),
            "window": (("Refresh from CATIA", self._on_refresh),
                       ("Help", self._on_help),
                       ("Close", self._on_close)),
        }
        for group_index, (group, colour) in enumerate(self.BUTTON_GROUPS):
            for label, handler in groups[group]:
                button = wx.Button(panel, label=label)
                if colour is not None:
                    button.SetBackgroundColour(colour)
                button.Bind(wx.EVT_BUTTON, handler)
                buttons.Add(button, 0, wx.RIGHT, 6)
            if group_index < len(self.BUTTON_GROUPS) - 1:
                buttons.AddSpacer(12)                                                                            #A gap between the groups
        vbox.Add(buttons, 0, wx.ALL, 8)

        self.status = wx.StaticText(panel, label="Double click a row to set its name and comment, or "
                                                 "select several with Ctrl or Shift and press [Edit "
                                                 "selected rows]. Nothing is written until Apply is pressed.")
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
                              (self.BAD_COLOUR, "Off the limits, or offset off the rule"),
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
                                  ("die", "Die", 60), ("revision", "Rev", 40)):
            box.Add(wx.StaticText(panel, label=label), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 8)
            field = wx.TextCtrl(panel, value=str(self.settings.get(key, "")), size=(width, -1))
            self.fields[key] = field
            box.Add(field, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 4)

        return box

    '''
        This function copies the job bar back into the settings dict.
    '''
    def _read_job_bar(self):
        for key, field in self.fields.items():
            self.settings[key] = field.GetValue().strip()

    def _fill_grid(self):
        for row_index, row in enumerate(self.rows):
            indent = "    " * row["level"]
            name, comment = effective_name(row), effective_comment(row)                                          #What the row is heading for, not what it leaves
            stage, nominal = stage_for_description(comment or name)
            is_operation = row["kind"] == "Operation"                                                            #Only operations carry these settings
            parameters = row.get("parameters") or {}
            missing = (row.get("missing") or []) if is_operation else []
            one_line = re.sub(r"\s*[\r\n]+\s*", " / ", comment).strip()                                          #A part operation comment is several lines
            values = ((row["kind"], operation_label(row["activity_type"]), indent + name,
                       one_line, effective_instruction(row), row["tool"] or "")
                      + tuple(parameters.get(label, "") or ("missing" if label in missing else "")
                              for label in PARAMETER_LABELS)
                      + (stage or "", "" if nominal is None else f"{nominal:+.1f}"))
            for column, value in enumerate(values):
                self.grid.SetCellValue(row_index, column, value)

            for offset_index, label in enumerate(PARAMETER_LABELS):                                              #Missing settings are called out, not left blank
                column = len(self.COLUMNS) - 2 - len(PARAMETER_LABELS) + offset_index
                self.grid.SetCellTextColour(row_index, column,
                                            wx.Colour(192, 0, 0) if label in missing else wx.BLACK)

            row_colour = self.ROW_COLOURS.get(row["kind"], wx.WHITE)                                             #Part operations and dividers stand out from operations
            if row["kind"] == "Program" and is_divider(row["name"]):
                row_colour = self.DIVIDER_COLOUR
            for column in range(len(self.COLUMNS)):
                self.grid.SetCellBackgroundColour(row_index, column, row_colour)

            for column, staged in ((self.NAME_COLUMN, row["new_name"]),                                          #The staged value stands where the current one did
                                   (self.COMMENT_COLUMN, row["new_comment"]),
                                   (self.INSTRUCTION_COLUMN, row.get("new_instruction"))):
                self.grid.SetCellBackgroundColour(row_index, column,
                                                  self.STAGED_COLOUR if staged else row_colour)
                self.grid.SetCellTextColour(row_index, column,
                                            wx.Colour(0, 97, 0) if staged else wx.BLACK)

            bad = check_operation(row, part_operation_of(row)) if is_operation else {}                           #Values off the limits go on red
            for offset_index, label in enumerate(PARAMETER_LABELS):
                if label in bad:
                    column = len(self.COLUMNS) - 2 - len(PARAMETER_LABELS) + offset_index
                    self.grid.SetCellBackgroundColour(row_index, column, self.BAD_COLOUR)
                    self.grid.SetCellTextColour(row_index, column, self.BAD_TEXT_COLOUR)

            if is_staged(row):                                                                                   #Mark the whole row so staged edits are easy to find
                self.grid.SetCellBackgroundColour(row_index, 0, self.STAGED_MARK_COLOUR)
        self.grid.AutoSizeColumns()
        self.grid.ForceRefresh()

    def _selected_row(self):
        selected = self.grid.GetSelectedRows()
        if selected:
            return selected[0]
        cursor = self.grid.GetGridCursorRow()
        return cursor if 0 <= cursor < len(self.rows) else None

    '''
        This function lists every selected row, in grid order.

        output:
            List of row indices - the cursor row where nothing is selected
    '''
    def _selected_rows(self):
        selected = sorted(index for index in set(self.grid.GetSelectedRows())
                          if 0 <= index < len(self.rows))
        if selected:
            return selected
        cursor = self.grid.GetGridCursorRow()
        return [cursor] if 0 <= cursor < len(self.rows) else []

    '''
        This function edits the selected rows - one on its own, or several as a group.

        A group is edited through one dialog and staged onto every selected row. The rows have
        to be of one kind, because a program's comment is composed and an operation's is not,
        and applying one kind's edit to the other would write the wrong shape of comment.
    '''
    def _on_edit_row(self, event):
        indices = self._selected_rows()
        if hasattr(event, "GetRow") and 0 <= event.GetRow() < len(self.rows) \
                and event.GetRow() not in indices:
            indices = [event.GetRow()]                                                                           #A double click lands on the row it hit
        if not indices:
            self.status.SetLabel("Select a row first.")
            return

        selected_rows = [self.rows[index] for index in indices]
        kinds = sorted({row["kind"] for row in selected_rows})
        if len(kinds) > 1:
            self.status.SetLabel("Select rows of one kind to edit them together - the selection "
                                 "mixes " + " and ".join(kind.lower() + "s" for kind in kinds) + ".")
            return

        self._read_job_bar()
        row = selected_rows[0]
        dialog = EditDialog(self, row, self.settings, self.rows,
                            group=selected_rows if len(selected_rows) > 1 else None)
        if dialog.ShowModal() == wx.ID_OK:
            if len(selected_rows) > 1:
                dialog.apply_group()
            else:
                row["new_name"] = dialog.new_name
                row["new_comment"] = dialog.new_comment
                row["new_instruction"] = dialog.new_instruction
            self._fill_grid()
            self.status.SetLabel(f"Staged - {sum(1 for r in self.rows if is_staged(r))} "
                                 f"row(s) waiting to be applied.")
        dialog.Destroy()

    '''
        This function opens the metal thickness table.
    '''
    def _on_metal(self, event):
        part_ops = [row for row in self.rows if row["kind"] == "Part Operation"]
        if not part_ops:
            self.status.SetLabel("There are no part operations.")
            return

        dialog = MetalDialog(self, part_ops, self.metal_rows)
        if dialog.ShowModal() == wx.ID_OK:
            self.metal_rows = dialog.apply()
            self.header.SetLabel(self._job_summary())
            self._fill_grid()                                                                                    #The offset checks go by the metal and master
            self.Layout()
            chosen = sum(1 for row in part_ops if row["metal"])
            self.status.SetLabel(f"{chosen} of {len(part_ops)} part operation(s) have a metal thickness.")
        dialog.Destroy()

    '''
        This function opens the template editor and takes on whatever was saved.
    '''
    def _on_templates(self, event):
        dialog = TemplateEditor(self, self.settings_dir)
        if dialog.ShowModal() == wx.ID_OK:
            written = dialog.save()
            self.status.SetLabel("Templates saved." if written else
                                 "Templates changed for this run, but the file could not be written.")
        dialog.Destroy()

    '''
        This function opens the limits editor and re-runs the checks with whatever was saved.
    '''
    def _on_limits(self, event):
        dialog = LimitsDialog(self, self.settings_dir)
        if dialog.ShowModal() == wx.ID_OK:
            self._fill_grid()                                                                                    #The red cells go by the limits
            self.status.SetLabel("Limits saved." if getattr(dialog, "saved", False) else
                                 "Limits changed for this run, but the file could not be written.")
        dialog.Destroy()

    '''
        This function deletes the saved settings and puts the templates back to the defaults.
    '''
    def _on_clear_settings(self, event):
        if wx.MessageBox("Delete the saved settings and put every template list and limit back "
                         "to what the script ships with?\n\n"
                         f"{self.settings_dir}\n\n"
                         "The document is not touched.", "Clear saved settings",
                         wx.YES_NO | wx.ICON_QUESTION, self) != wx.YES:
            return

        removed = []
        for name in ("settings.json", "templates.json", "limits.json"):
            path = os.path.join(self.settings_dir, name)
            try:
                if os.path.exists(path):
                    os.remove(path)
                    removed.append(name)
            except Exception as error:
                wx.MessageBox(f"{name} could not be deleted:\n\n{error}", "Clear saved settings",
                              wx.OK | wx.ICON_WARNING, self)
                return

        for key, value in DEFAULT_TEMPLATES.items():
            TEMPLATES[key] = json.loads(json.dumps(value))
        for key, value in DEFAULT_LIMITS.items():
            LIMITS[key] = json.loads(json.dumps(value))

        for key, field in self.fields.items():
            field.SetValue("")
        self.settings.update({key: "" for key in REMEMBERED_SETTINGS})

        self._fill_grid()                                                                                        #The red cells go by the limits
        self.status.SetLabel(f"Cleared {', '.join(removed) if removed else 'nothing - there was nothing saved'}. "
                             f"Templates and limits are back to the defaults.")

    '''
        This function shows the help window.
    '''
    def _on_help(self, event):
        help_text = (
            "MANAGE PROGRAM NAMES AND COMMENTS\n"
            "--------------------------------------------------------------------------\n"
            " Lists the machining tree of the open CATProcess and sets the names and\n"
            " comments of its part operations, programs and operations.\n\n"
            " Edits are staged in place - the Name and Comment columns show what the row\n"
            " will be called, coloured green while it is waiting. Nothing reaches the\n"
            " document until [Apply staged edits to CATIA] is pressed, and only values\n"
            " that differ from what is already there are written. [Clear staged edit]\n"
            " puts a row back to what the document still holds.\n\n"

            "BUTTONS\n"
            "--------------------------------------------------------------------------\n"
            " Grouped by colour: blue edits rows, green handles the staged edits,\n"
            " amber holds the settings, grey the window itself.\n\n"
            " [Edit selected rows]   Sets the name and comment of the selected rows.\n"
            "                        Double clicking a row does the same. Select several\n"
            "                        rows of one kind with Ctrl or Shift to edit them as\n"
            "                        a group: only what is changed in the dialog is\n"
            "                        applied, a built program name numbers on in\n"
            "                        sequence, and a composed comment is built again for\n"
            "                        each program with its own tool and offset.\n"
            " [Metal thicknesses]    Lists every thickness found in the design parts and\n"
            "                        says which applies to each part operation. Rows can\n"
            "                        be added by hand where a part does not state one.\n"
            " [Renumber programs]    Numbers the programs in sequence, or by hand.\n"
            " [Clear staged edit]    Drops the staged values on the selected row, so it\n"
            "                        shows what the document holds again.\n"
            " [Apply staged edits]   Writes every staged value to the document, without\n"
            "                        asking again.\n"
            " [Edit templates]       Adds, edits, reorders and removes the entries in\n"
            "                        the dropdown lists.\n"
            " [Edit limits]          Sets the allowed stepover, pass overlap, and depth\n"
            "                        of cut values the checks go by.\n"
            " [Clear saved settings] Deletes the saved settings and puts every template\n"
            "                        list and limit back to what the script ships with.\n"
            " [Refresh from CATIA]   Reads the whole tree again. Staged edits are lost.\n"
            " [Help]                 Opens this window.\n\n"

            "CHECKS\n"
            "--------------------------------------------------------------------------\n"
            " Three settings are checked, and a value that is off goes on red:\n\n"
            "   Stepover        Has to sit on the allowed list for the operation's\n"
            "                   stage - roughing 3, 2 or 1, semi-finish 1.5 or 1,\n"
            "                   finish 1 or 0.5. The stage is read from the operation's\n"
            "                   comment or name, or failing that its program's.\n"
            "   Roughing op     The CATIA Roughing operation is checked on its own two\n"
            "                   rules instead, whatever its stage: a pass overlap of\n"
            "                   50% and a depth of cut of 1, 1.5 or 2. Its stepover\n"
            "                   column shows the pass overlap, a ratio as a percentage\n"
            "                   of the tool diameter.\n"
            "   Offset on part  Has to match what the stage rule works out from the\n"
            "                   part operation's master, metal and spotting.\n\n"
            " Anything that cannot be worked out - no stage, no master, no metal - is\n"
            " not checked, so a red cell is always a value that is genuinely off. All\n"
            " the allowed values are editable under [Edit limits].\n\n"

            "THE JOB BAR\n"
            "--------------------------------------------------------------------------\n"
            " Initial   Programmer initial. Typed once and remembered.\n"
            " Project   Read from the CATPart name, e.g. TJ104 gives 104.\n"
            " Die       Read from the CATPart name, e.g. D45.\n"
            " Rev       Read from straight after the die number, D45_03 gives 03.\n"
            " Code      Die part code. Suggested from the die part name - LOWER POST\n"
            "           gives LP - and editable.\n"
            " Master    Which side is cut to nominal, where the part does not say.\n\n"
            " Metal thickness is not here - it belongs to the part, not the job. Use\n"
            " [Metal thicknesses].\n\n"
            " A die number found only as an OP number is reported unconfirmed, since\n"
            " OP 40 can be D30. Confirm it before generating names.\n\n"

            "PROGRAM NAMES\n"
            "--------------------------------------------------------------------------\n"
            " Programs are named as one token:\n\n"
            "     A   104   D45   03   LP   01\n"
            "     |   |     |     |    |    +-- program number\n"
            "     |   |     |     |    +------- die part code\n"
            "     |   |     |     +------------ revision\n"
            "     |   |     +------------------ die number\n"
            "     |   +------------------------ project number\n"
            "     +---------------------------- programmer initial\n\n"
            " Set the program number in the edit window and press [Use as name], or\n"
            " number a whole process at once with [Renumber programs].\n\n"
            " Dividers - programs named *** LIKE THIS *** - carry no number and are\n"
            " skipped when renumbering.\n\n"
            " A program CATIA named itself, Manufacturing Program.14, ends in CATIA's\n"
            " own activity counter, not a program number. It is ignored and the next\n"
            " free number is offered instead.\n\n"

            "PROGRAM COMMENTS\n"
            "--------------------------------------------------------------------------\n"
            " Composed rather than typed:\n\n"
            "     16BN SEMI-FINISH SWEEP TO +0.3MM\n"
            "     16BN FINISH SWEEP TO 0.0MM (M/C: -1.5MM)\n\n"
            " Tool          Taken from the program's tool change. A ball nose closes\n"
            "               up, so T4 16 BN becomes 16BN.\n"
            " Description   Picked from the list.\n"
            " TO ...MM      The stage. Rough +2.0 or +0.7, semi-finish +0.3, finish\n"
            "               0.0, Z check 0.0. This does not move when metal comes off.\n"
            " (M/C: ...MM)  What the operations actually machine to, read from their\n"
            "               Offset on part. Shown only when it differs from the stage.\n\n"

            "PP INSTRUCTIONS\n"
            "--------------------------------------------------------------------------\n"
            " A PPInstruction - the activity sitting at the head of a program - cuts\n"
            " nothing and carries two separate things:\n\n"
            "     Name             MECOF_HEAD     what the activity is called\n"
            "     PP instruction   head/'TCB6'    what the post processor reads\n\n"
            " Renaming it does not change what gets posted. The instruction is held in\n"
            " the activity's PP words syntax parameter, and is set in the edit window\n"
            " on its own row, staged and applied like a name or a comment.\n\n"
            " Both have their own template list, and both ship empty - the entries\n"
            " belong to the shop and its machines rather than to the script. Add your\n"
            " own under [Edit templates], PP instruction names and PP instructions,\n"
            " and press Save to keep them. They export and import like any other list.\n\n"

            "THE OFFSET RULE\n"
            "--------------------------------------------------------------------------\n"
            " The master side is cut to nominal. The other side has the metal taken\n"
            " off it. BOTH means no metal comes off either side.\n\n"
            "     Master    Upper parts        Lower parts\n"
            "     UPPER     nominal            nominal - metal\n"
            "     LOWER     nominal - metal    nominal\n"
            "     BOTH      nominal            nominal\n\n"
            " So an upper cam is cut to nominal where UPPER is master, and has the\n"
            " metal taken out of it where LOWER is.\n\n"
            " Upper or lower comes from the part operation's name - name it UPPER PAD\n"
            " and it is an upper part. There is no separate setting for it, because\n"
            " the name already says it.\n\n"
            " A name that says neither - ROLLER CAM POS_01, CAM PAD POS_02 - could be\n"
            " either, so no offset is worked out. Name it UPPER ROLLER CAM or LOWER\n"
            " ROLLER CAM and it will be.\n\n"
            " The master is set per part operation in [Metal thicknesses].\n\n"
            " The rule is only a fallback. Where the operations state an Offset on\n"
            " part that figure is used instead, and the rule is used to check it.\n\n"

            "METAL THICKNESS\n"
            "--------------------------------------------------------------------------\n"
            " Read from the design part, from the name of the body holding the master\n"
            " panel:\n\n"
            "     MASTER PANEL LH CP02 REV11 - UPPER IS MASTER - METAL IS 1.5mm\n\n"
            " Metal belongs to the panel, so it is read per part operation. Two die\n"
            " parts of different thickness each get their own. Where one part names\n"
            " more than one thickness the choice is offered, with the body name each\n"
            " came from.\n\n"

            "COLUMN COLOURS\n"
            "--------------------------------------------------------------------------\n"
            " Blue        Part operation.\n"
            " Pale blue   Manufacturing program.\n"
            " Cream       Operation.\n"
            " Amber       Divider - a program carrying a *** heading ***.\n"
            " Green       A staged Name or Comment, shown in place and waiting for\n"
            "             Apply. The darker mark on the Level column finds the row.\n"
            " Red cell    A stepover or depth of cut off the allowed values, or an\n"
            "             Offset on part that does not match the stage rule. See\n"
            "             CHECKS and [Edit limits].\n"
            " Red text    A setting this operation type should have but does not. A\n"
            "             setting counts as missing only where another operation of\n"
            "             the same type has one, so a pencil trace is not reported\n"
            "             for the stepover it never had.\n\n"

            "PLACEHOLDERS\n"
            "--------------------------------------------------------------------------\n"
            " A template carrying **.**MM, ***mm, 0.*mm or POS_## asks for the number\n"
            " when the edit is staged. The template's own spelling of the unit is\n"
            " kept, so DROP ***mm becomes DROP 3mm.\n\n"

            "TEMPLATES\n"
            "--------------------------------------------------------------------------\n"
            " Every dropdown is fed by a list that [Edit templates] can change - die\n"
            " parts, machines, job descriptions, part operation comments, masters,\n"
            " dividers, operation descriptions, tools and die numbers.\n\n"
            " Entries can be added, edited, reordered, sorted and removed. Saving\n"
            " writes them to templates.json; the lists built into the script are the\n"
            " fallback, so a list can always be put back with [Reset this list].\n\n"

            "SETTINGS PERSISTENCE\n"
            "--------------------------------------------------------------------------\n"
            " Three files, in:\n"
            "   %APPDATA%\\pycatia_scripts\\Manage_Program_Names_And_Comments\\\n\n"
            "   settings.json    The programmer initial and the machine. Nothing else.\n"
            "   templates.json   The template lists, once they have been edited.\n"
            "   limits.json      The allowed values the checks go by, once edited.\n\n"
            " Project, die, revision, metal and master belong to the document and are\n"
            " read from it every run, so a part name that fails to parse can never\n"
            " inherit the last job's die number.\n\n"
            " [Clear saved settings] deletes all three files and puts the templates\n"
            " and limits back.\n\n"

            "NOTES\n"
            "--------------------------------------------------------------------------\n"
            " The settings columns are the ones Export_Process_Table_Parameters writes\n"
            " to Excel, read by parameter name rather than by index.\n\n"
            " Applying writes to the document but does not save it. Save in CATIA to\n"
            " keep the changes."
        )
        dialog = dialogs.ScrolledMessageDialog(self, help_text, "Help")
        dialog.text.SetFont(wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        dialog.SetSize((680, 620))
        dialog.CenterOnParent()
        dialog.ShowModal()
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

        staged = [row for row in self.rows if is_staged(row)]
        if staged:
            confirm = wx.MessageBox(f"{len(staged)} staged edit(s) have not been applied.\n\n"
                                    f"Reading again will discard them. Carry on?",
                                    "Refresh", wx.YES_NO | wx.ICON_QUESTION, self)
            if confirm != wx.YES:
                return

        chosen = {row["name"]: row["metal"] for row in self.rows                                                  #Keep the metal that was picked by hand
                  if row["kind"] == "Part Operation" and len(row.get("metals") or {}) > 1}

        try:
            rows = read_tree_with_progress(self.ppr_document, self)
        except Exception as error:
            wx.MessageBox(f"The document could not be read:\n\n{error}", "Refresh", wx.OK | wx.ICON_ERROR, self)
            return

        for row in rows:
            if row["kind"] == "Part Operation" and row["name"] in chosen and chosen[row["name"]]:
                row["metal"] = chosen[row["name"]]

        self.rows = rows
        self.metal_rows = collect_metal_rows(rows)                                                               #The parts may have changed too
        difference = len(rows) - self.grid.GetNumberRows()
        if difference > 0:
            self.grid.AppendRows(difference)
        elif difference < 0:
            self.grid.DeleteRows(0, -difference)

        self._fill_grid()
        self.header.SetLabel(self._job_summary())
        self.Layout()
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
                    row["new_name"] = "" if names[id(row)] == row["name"] else names[id(row)]                    #Back to its own name is not an edit
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
        self.rows[row_index]["new_instruction"] = ""
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

        staged = [row for row in self.rows if is_staged(row)]
        if not staged:
            self.status.SetLabel("Nothing staged.")
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
                if row.get("new_instruction"):
                    parameter = instruction_parameter(row["activity"])                                           #The post processor reads this, not the name
                    if parameter is None:
                        raise ValueError(f"no {INSTRUCTION_PARAMETER} parameter on this activity")
                    parameter.value = row["new_instruction"]
                    row["instruction"] = row["new_instruction"]
                row["new_name"] = ""
                row["new_comment"] = ""
                row["new_instruction"] = ""
                written += 1
            except Exception as error:
                failures.append(f"{row['kind']} {row['name']}: {error}")

        self._fill_grid()
        self.header.SetLabel(self._job_summary())                                                                #Names may have changed
        self.Layout()
        if failures:
            wx.MessageBox("Written: {0}\n\nFailed:\n{1}".format(written, "\n".join(failures)),
                          "Apply", wx.OK | wx.ICON_WARNING, self)
        self.status.SetLabel(f"Applied {written} edit(s). Save the document in CATIA to keep them.")

    def _on_close(self, event):
        self._read_job_bar()
        save_settings(self.settings_dir, self.settings)
        self.Close()

    '''
        This function writes the block above the grid, one entry per part operation.

        Metal and master belong to the part, not to the job, so a process holding several parts
        of different thickness shows each one with its own figures rather than a single value
        that could only be right for one of them.

        output:
            The text to show
    '''
    def _job_summary(self):
        setups = [row for row in self.rows if row["kind"] == "Part Operation"]
        if not setups:
            return "No part operations found."

        blocks = []
        for row in setups:
            parsed = parse_part_name(row["part_name"])
            die = parsed["die"] or "not found"
            if not parsed["confirmed"] and parsed["op"]:
                die = f"{die} (only OP {parsed['op']} present - confirm the die number)"

            metal = f"{row['metal']}mm" if row["metal"] else "not known - no offsets"
            if len(row.get("metals") or {}) > 1:
                metal += f"  (chosen from {', '.join(sorted(row['metals']))})"

            blocks.append(
                f"{row['name']}\n"
                f"    CATPart : {row['part_name'] or 'not found'}\n"
                f"    Job {parsed['job'] or '?'}   Die {die}   Rev {parsed['revision'] or '?'}\n"
                f"    Metal {metal}   Master {row['master'] or 'not stated'}"
                + (f"   Spotting {row['spotting']}mm {row['spotting_mode']}"
                   if row.get("spotting") and row.get("spotting_mode") else "")
            )
        return "\n".join(blocks)


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
        rows = read_tree_with_progress(ppr_document)

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

        load_templates(settings_dir)                                                                             #User entries sit on top of the built in lists
        load_limits(settings_dir)                                                                                #The values the checks go by
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

            print(f"   {row['name']}")
            print(f"     master {row['master'] or 'not stated'}, "
                  f"metal {row['metal'] + 'mm' if row['metal'] else 'not known'}")
            for value, sources in sorted(row["metals"].items()):
                mark = "  <- chosen" if value == row["metal"] and len(row["metals"]) > 1 else ""
                for source in sources:
                    print(f"       {value}mm from: {source}{mark}")
            if row["metal_note"]:
                print(f"       note: {row['metal_note']}")
            if not row["metal"]:
                print("       set one with [Metal thicknesses], or no offsets are worked out")

            if not row.get("code"):
                row["code"] = die_part_code(row["name"])                                                         #Suggested, editable in [Metal thicknesses]

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
