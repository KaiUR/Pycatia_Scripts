'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Manage_Tooling_Catalog.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.10.0
    Release:        V5R32
    Purpose:        Spreadsheet-style editor for NC tooling catalogs, built into a .catalog by CATIA.
    Author:         Kai-Uwe Rathjen
    Date:           16.07.26
    Description:    A grid (spreadsheet) editor for machining tooling catalogs. Pick a chapter (NC_TOOLS,
                    NC_TOOL_ASSEMBLIES, NC_INSERTS, NC_CORRECTORS) and a tool-type family; the family's real
                    CATIA keyword columns load into a grid. Edit tools as rows: add, delete, duplicate rows,
                    edit cells inline, add extra columns. Load / Save the whole tree as one nested CSV in
                    CATIA's batch-catalog format, and Build the .catalog from it. A saved CSV is CATIA-ready,
                    so it can also be built by hand or handed to anyone running the batch catalog tools.
                    The catalog is written with the full NC_RESOURCES tree - every resource chapter and every
                    tool family, whether or not it holds tools - as a hand-built tooling catalog has.
                    The per-family keyword columns were transcribed from this catalog's Catalog Editor keyword
                    lists; families flagged truncated may miss a few trailing columns — use Add Column to fill.
                    CATIA exposes no automation to edit an existing .catalog in place, so the CSV is the source
                    of truth and the catalog is (re)built from it.
                    Build asks CATIA to run CreateCatalogFromcsv itself, through a generated CATScript, because
                    calling it over COM from Python builds a broken catalog - see build_catalog_in_catia.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia >= 0.10.0
                    wxPython
                    Catia V5 running (only needed for Build). No open document is required.
                    Build runs a generated macro, so CATIA must be allowed to execute macros.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.enumeration.enums import CatScriptLibraryType
import wx
import wx.grid
import wx.lib.dialogs
import os
import csv
import json
import ctypes
import tempfile
import traceback

SCRIPT_NAME = "Manage_Tooling_Catalog"
NAME_COL = "Entity Name"                                                                                        #CSV column A (description name)
DOC_COL = "CATPart Path"                                                                                        #Part that physically represents the tool / assembly
ROOT_CHAPTER = "NC_RESOURCES"                                                                                   #Root chapter of a CATIA tooling catalog
RESOURCE_CHAPTERS = ["NC_TOOLS", "NC_INSERTS", "NC_TOOL_ASSEMBLIES", "NC_CORRECTORS"]                           #The four chapters NC_RESOURCES holds
BASE_NAME_COL = "MFG_NAME_BAS"                                                                                  #Keyword holding the tool family in a flat catalog CSV
TYPE_TOKENS = {"String", "Real", "Integer", "Boolean", "mm", "deg", "s", "mm_mn", "mm_turn", "m_mn"}            #Recognised on load to skip a type row
BUILD_MACRO = "BuildCatalog.CATScript"                                                                          #Generated macro CATIA runs to build the catalog

# Authoritative per-family keyword columns, transcribed from CATIA Catalog Editor keyword lists.
# Families whose screenshots scrolled off-screen are listed in TRUNCATED_FAMILIES; use Add Column to complete.
FAMILY_KEYWORDS = json.loads(r'''
{
  "NC_TOOLS": {
    "MfgDrillTool": ["MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_CUT_ANGLE","MFG_TL_TIP_LGTH","MFG_BODY_DIAM","MFG_CUT_LENGTH","MFG_LENGTH","MFG_OVERALL_LGTH","MFG_NOMINAL_DIAM","MFG_TOOTH_MAT","MFG_MACH_QUALITY","MFG_WAY_OF_ROT","MFG_TOOTH_MATDES","MFG_TOOTH_DES","MFG_NB_OF_FLUTES","MFG_RADIAL_TL_RAKE_ANG","MFG_TL_RAKE_ANG","MFG_MAX_MIL_TIME","MFG_MAX_MIL_LENGTH","MFG_WEIGHT_SNTX","MFG_COOLNT_SNTX","MFG_VC_NEW_SP","MFG_SZ_GLOBAL","MFG_VC_NEW","MFG_MAX_FEEDRATE","MFG_PP","MFG_SZ","MFG_VC"],
    "MfgEndMillTool": ["MFG_BALL_TYPE","MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_EFFECTIVE_LENGTH","MFG_TOOL_CORE_DIAMETER","MFG_CORNER_RAD","MFG_BODY_DIAM","MFG_CUT_LENGTH","MFG_LENGTH","MFG_OVERALL_LGTH","MFG_NOMINAL_DIAM","MFG_TOOTH_MAT","MFG_COMPOSITION","MFG_MACH_QUALITY","MFG_WAY_OF_ROT","MFG_TOOTH_MATDESC","MFG_TOOTH_DESC","MFG_MAX_PLNG_ANG","MFG_NB_OF_FLUTES","MFG_RADIAL_TL_RAKE_ANG","MFG_TL_RAKE_ANG","MFG_MAX_MIL_TIME","MFG_MAX_MIL_LENGTH","MFG_WEIGHT_SNTX","MFG_COOLNT_SNTX","MFG_VC_ROUGH_NEW_SP","MFG_VC_FINISH_NEW_SP","MFG_SZ_ROUGH_GLOBAL","MFG_VC_ROUGH_NEW","MFG_SZ_FINISH_GLOBAL","MFG_VC_FINISH_NEW","MFG_AR_ROUGH","MFG_AA_ROUGH","MFG_SZ_ROUGH","MFG_VC_ROUGH","MFG_AR_FINISH","MFG_AA_FINISH","MFG_SZ_FINISH","MFG_VC_FINISH"],
    "MfgFaceMillTool": ["MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_TOOL_CORE_DIAMETER","MFG_CUT_ANGLE","MFG_CORNER_RAD","MFG_BODY_DIAM","MFG_CUT_LENGTH","MFG_LENGTH","MFG_OVERALL_LGTH","MFG_OUTSIDE_DIAM","MFG_NOMINAL_DIAM","MFG_TOOTH_MAT","MFG_COMPOSITION","MFG_MACH_QUALITY","MFG_WAY_OF_ROT","MFG_TOOTH_MATDES","MFG_TOOTH_DES","MFG_MAX_PLNG_ANG","MFG_NB_OF_FLUTES","MFG_RADIAL_TL_RAKE_ANG","MFG_TL_RAKE_ANG","MFG_MAX_MIL_TIME","MFG_MAX_MIL_LENGTH","MFG_WEIGHT_SNTX","MFG_COOLNT_SNTX","MFG_VC_ROUGH_NEW_SP","MFG_VC_FINISH_NEW_SP","MFG_SZ_ROUGH_GLOBAL","MFG_VC_ROUGH_NEW","MFG_SZ_FINISH_GLOBAL","MFG_VC_FINISH_NEW","MFG_MAX_FEEDRATE","MFG_AR_ROUGH","MFG_AA_ROUGH","MFG_SZ_ROUGH","MFG_VC_ROUGH","MFG_AR_FINISH","MFG_AA_FINISH","MFG_SZ_FINISH","MFG_VC_FINISH"],
    "MfgConicalMillTool": ["MFG_BALL_TYPE","MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_CUT_ANGLE","MFG_CORNER_RAD","MFG_BODY_DIAM","MFG_CUT_LENGTH","MFG_LENGTH","MFG_OVERALL_LGTH","MFG_ENTRY_DIAM","MFG_NOMINAL_DIAM","MFG_COMPOSITION","MFG_TOOTH_MAT","MFG_MACH_QUALITY","MFG_WAY_OF_ROT","MFG_TOOTH_MATDES","MFG_TOOTH_DES","MFG_NB_OF_FLUTES","MFG_MAX_PLNG_ANG","MFG_RADIAL_TL_RAKE_ANG","MFG_TL_RAKE_ANG","MFG_MAX_MIL_TIME","MFG_MAX_MIL_LENGTH","MFG_WEIGHT_SNTX","MFG_COOLNT_SNTX","MFG_VC_ROUGH_NEW_SP","MFG_VC_FINISH_NEW_SP","MFG_SZ_ROUGH_GLOBAL","MFG_VC_ROUGH_NEW","MFG_SZ_FINISH_GLOBAL","MFG_VC_FINISH_NEW","MFG_MAX_FEEDRATE","MFG_AR_ROUGH","MFG_AA_ROUGH","MFG_SZ_ROUGH","MFG_VC_ROUGH","MFG_AR_FINISH","MFG_AA_FINISH","MFG_SZ_FINISH","MFG_VC_FINISH"],
    "MfgCounterboreMillTool": ["MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_TL_TIP_LGTH","MFG_ENTRY_DIAM","MFG_BODY_DIAM","MFG_CUT_LENGTH","MFG_LENGTH","MFG_OVERALL_LGTH","MFG_NOMINAL_DIAM","MFG_TOOTH_MAT","MFG_COMPOSITION","MFG_MACH_QUALITY","MFG_WAY_OF_ROT","MFG_TOOTH_MATDESC","MFG_TOOTH_DESC","MFG_MAX_PLNG_ANG","MFG_NB_OF_FLUTES","MFG_RADIAL_TL_RAKE_ANG","MFG_TL_RAKE_ANG","MFG_MAX_MIL_TIME","MFG_MAX_MIL_LENGTH","MFG_WEIGHT_SNTX","MFG_COOLNT_SNTX","MFG_VC_NEW_SP","MFG_SZ_GLOBAL","MFG_VC_NEW","MFG_MAX_FEEDRATE","MFG_PP","MFG_SZ","MFG_VC"],
    "MfgCountersinkTool": ["MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_CUT_ANGLE","MFG_ENTRY_DIAM","MFG_BODY_DIAM","MFG_CORNER_RAD","MFG_CUT_LENGTH","MFG_LENGTH","MFG_OVERALL_LGTH","MFG_OUTSIDE_DIAM","MFG_NOMINAL_DIAM","MFG_TOOTH_MAT","MFG_MACH_QUALITY","MFG_WAY_OF_ROT","MFG_TOOTH_MATDES","MFG_TOOTH_DES","MFG_NB_OF_FLUTES","MFG_RADIAL_TL_RAKE_ANG","MFG_TL_RAKE_ANG","MFG_MAX_MIL_TIME","MFG_MAX_MIL_LENGTH","MFG_WEIGHT_SNTX","MFG_COOLNT_SNTX","MFG_VC_NEW_SP","MFG_SZ_GLOBAL","MFG_VC_NEW","MFG_MAX_FEEDRATE","MFG_PP","MFG_SZ","MFG_VC"],
    "MfgTSlotterTool": ["MFG_BALL_TYPE","MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_LOWER_ANGLE","MFG_UPPER_ANGLE","MFG_LOWER_DIAM","MFG_UPPER_DIAM","MFG_CORNER_RAD_2","MFG_CORNER_RAD","MFG_BODY_DIAM","MFG_LENGTH","MFG_OVERALL_LGTH","MFG_NOMINAL_DIAM","MFG_MACH_QUALITY","MFG_COMPOSITION","MFG_TOOTH_MAT","MFG_WAY_OF_ROT","MFG_TOOTH_MATDES","MFG_TOOTH_DES","MFG_NB_OF_FLUTES","MFG_RADIAL_TL_RAKE_ANG","MFG_TL_RAKE_ANG","MFG_MAX_MIL_TIME","MFG_MAX_MIL_LENGTH","MFG_WEIGHT_SNTX","MFG_COOLNT_SNTX","MFG_VC_ROUGH_NEW_SP","MFG_VC_FINISH_NEW_SP","MFG_SZ_ROUGH_GLOBAL","MFG_VC_ROUGH_NEW","MFG_SZ_FINISH_GLOBAL","MFG_VC_FINISH_NEW","MFG_MAX_FEEDRATE","MFG_AR_ROUGH","MFG_AA_ROUGH","MFG_SZ_ROUGH","MFG_VC_ROUGH","MFG_AR_FINISH","MFG_AA_FINISH","MFG_SZ_FINISH","MFG_VC_FINISH"],
    "MfgThreadMillTool": ["MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_CHAMFER_ANGLE","MFG_ENTRY_DIAM","MFG_NB_OF_THREAD","MFG_TAPER_ANGLE","MFG_OUTSIDE_DIAM","MFG_BODY_DIAM","MFG_LENGTH_1","MFG_CUT_LENGTH","MFG_LENGTH","MFG_OVERALL_LGTH","MFG_NOMINAL_DIAM","MFG_THREAD_FORM","MFG_THREAD_CLASS","MFG_TOOTH_MAT","MFG_WAY_OF_ROT","MFG_TOOTH_MATDES","MFG_TOOTH_DES","MFG_THD_CLS_DESC","MFG_THD_FRM_DESC","MFG_PITCH_OF_THREAD","MFG_NB_OF_FLUTES","MFG_RADIAL_TL_RAKE_ANG","MFG_TL_RAKE_ANG","MFG_MAX_MIL_TIME","MFG_MAX_MIL_LENGTH","MFG_WEIGHT_SNTX","MFG_COOLNT_SNTX","MFG_VC_NEW_SP","MFG_SZ_GLOBAL","MFG_VC_NEW","MFG_MAX_FEEDRATE","MFG_PP","MFG_SZ","MFG_VC"],
    "MfgTwoSidesChamferingTool": ["MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_ANGLE2","MFG_CUT_ANGLE","MFG_ENTRY_DIAM","MFG_TL_TIP_LGTH","MFG_BODY_DIAM","MFG_CUT_LENGTH","MFG_LENGTH","MFG_OVERALL_LGTH","MFG_NOMINAL_DIAM","MFG_TOOTH_MAT","MFG_WAY_OF_ROT","MFG_TOOTH_MATDES","MFG_TOOTH_DES","MFG_NB_OF_FLUTES","MFG_RADIAL_TL_RAKE_ANG","MFG_TL_RAKE_ANG","MFG_MAX_MIL_TIME","MFG_MAX_MIL_LENGTH","MFG_WEIGHT_SNTX","MFG_COOLNT_SNTX","MFG_VC_NEW_SP","MFG_SZ_GLOBAL","MFG_VC_NEW","MFG_MAX_FEEDRATE","MFG_PP","MFG_SZ","MFG_VC"],
    "MfgBoringAndChamferingTool": ["MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_TAPER_ANGLE","MFG_CHAMFR_DIAM1","MFG_LENGTH_1","MFG_CORNER_RAD","MFG_BODY_DIAM","MFG_CUT_LENGTH","MFG_LENGTH","MFG_OVERALL_LGTH","MFG_NOMINAL_DIAM","MFG_TOOTH_MAT","MFG_MACH_QUALITY","MFG_WAY_OF_ROT","MFG_TOOTH_MATDES","MFG_TOOTH_DES","MFG_NB_OF_FLUTES","MFG_RADIAL_TL_RAKE_ANG","MFG_TL_RAKE_ANG","MFG_MAX_MIL_TIME","MFG_MAX_MIL_LENGTH","MFG_WEIGHT_SNTX","MFG_COOLNT_SNTX","MFG_VC_NEW_SP","MFG_SZ_GLOBAL","MFG_VC_NEW","MFG_MAX_FEEDRATE","MFG_PP","MFG_SZ","MFG_VC"],
    "MfgBoringBarTool": ["MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_TOOL_ANGLE","MFG_TIP_ANGLE","MFG_CUT_ANGLE","MFG_TIP_RADIUS","MFG_TIP_LENGTH","MFG_MAX_DIAMETER","MFG_MIN_DIAMETER","MFG_NON_CUT_DIAM","MFG_TL_TIP_LGTH","MFG_BODY_DIAM","MFG_CUT_LENGTH","MFG_LENGTH","MFG_OVERALL_LGTH","MFG_NOMINAL_DIAM","MFG_BORE_ABILITY","MFG_COMPOSITION","MFG_MACH_QUALITY","MFG_TOOTH_MAT","MFG_WAY_OF_ROT","MFG_TOOTH_MATDES","MFG_TOOTH_DES","MFG_RADIAL_TL_RAKE_ANG","MFG_TL_RAKE_ANG","MFG_MAX_MIL_TIME","MFG_MAX_MIL_LENGTH","MFG_WEIGHT_SNTX","MFG_COOLNT_SNTX","MFG_VC_NEW_SP","MFG_SZ_GLOBAL","MFG_VC_NEW","MFG_MAX_FEEDRATE","MFG_PP","MFG_SZ","MFG_VC"],
    "MfgCenterDrillTool": ["MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_TAPER_ANGLE","MFG_CUT_ANGLE","MFG_BODY_DIAM","MFG_CUT_LENGTH","MFG_LENGTH","MFG_OVERALL_LGTH","MFG_NOMINAL_DIAM","MFG_TOOTH_MAT","MFG_WAY_OF_ROT","MFG_SIZE_DESIGN","MFG_RADIAL_TL_RAKE_ANG","MFG_TL_RAKE_ANG","MFG_MAX_MIL_TIME","MFG_MAX_MIL_LENGTH","MFG_WEIGHT_SNTX","MFG_COOLNT_SNTX","MFG_VC_NEW_SP","MFG_SZ_GLOBAL","MFG_VC_NEW","MFG_MAX_FEEDRATE","MFG_PP","MFG_SZ","MFG_VC"],
    "MfgSpotDrillTool": ["MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_CUT_ANGLE","MFG_BODY_DIAM","MFG_LENGTH","MFG_OVERALL_LGTH","MFG_NOMINAL_DIAM","MFG_TOOTH_MAT","MFG_WAY_OF_ROT","MFG_TOOTH_MATDES","MFG_TOOTH_DES","MFG_NB_OF_FLUTES","MFG_RADIAL_TL_RAKE_ANG","MFG_TL_RAKE_ANG","MFG_MAX_MIL_TIME","MFG_MAX_MIL_LENGTH","MFG_WEIGHT_SNTX","MFG_COOLNT_SNTX","MFG_VC_NEW_SP","MFG_SZ_GLOBAL","MFG_VC_NEW","MFG_MAX_FEEDRATE","MFG_PP","MFG_SZ","MFG_VC"],
    "MfgReamerTool": ["MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_ENTRY_DIAM","MFG_TL_TIP_LGTH","MFG_BODY_DIAM","MFG_CUT_LENGTH","MFG_LENGTH","MFG_OVERALL_LGTH","MFG_NOMINAL_DIAM","MFG_TOOTH_MAT","MFG_WAY_OF_ROT","MFG_TOOTH_MATDES","MFG_TOOTH_DES","MFG_NB_OF_FLUTES","MFG_RADIAL_TL_RAKE_ANG","MFG_TL_RAKE_ANG","MFG_MAX_MIL_TIME","MFG_MAX_MIL_LENGTH","MFG_WEIGHT_SNTX","MFG_COOLNT_SNTX","MFG_VC_NEW_SP","MFG_SZ_GLOBAL","MFG_VC_NEW","MFG_MAX_FEEDRATE","MFG_PP","MFG_SZ","MFG_VC"],
    "MfgTapTool": ["MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_TAPER_ANGLE","MFG_LENGTH_NOM_DIAM","MFG_NB_OF_THREAD","MFG_ENTRY_DIAM","MFG_TL_TIP_LGTH","MFG_BODY_DIAM","MFG_CUT_LENGTH","MFG_LENGTH","MFG_OVERALL_LGTH","MFG_NOMINAL_DIAM","MFG_THREAD_FORM","MFG_THREAD_CLASS","MFG_TOOTH_MAT","MFG_WAY_OF_ROT","MFG_TOOTH_MATDES","MFG_TOOTH_DES","MFG_THD_CLS_DESC","MFG_THD_FRM_DESC","MFG_PITCH_OF_THREAD","MFG_NB_OF_FLUTES","MFG_RADIAL_TL_RAKE_ANG","MFG_TL_RAKE_ANG","MFG_MAX_MIL_TIME","MFG_MAX_MIL_LENGTH","MFG_WEIGHT_SNTX","MFG_COOLNT_SNTX","MFG_VC_NEW_SP","MFG_SZ_GLOBAL","MFG_VC_NEW","MFG_MAX_FEEDRATE","MFG_PP","MFG_SZ","MFG_VC"],
    "MfgMultiDiamDrillTool": ["MFG_NB_OF_STAGES","MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_ANGLE2","MFG_TAPER_ANGLE","MFG_CUT_ANGLE","MFG_CHAMFR_DIAM2","MFG_CHAMFR_DIAM1","MFG_LENGTH_2","MFG_LENGTH_1","MFG_TL_TIP_LGTH","MFG_BODY_DIAM","MFG_CUT_LENGTH","MFG_LENGTH","MFG_OVERALL_LGTH","MFG_NOMINAL_DIAM","MFG_MACH_QUALITY","MFG_TOOTH_MAT","MFG_WAY_OF_ROT","MFG_TOOTH_MATDES","MFG_TOOTH_DES","MFG_NB_OF_FLUTES","MFG_RADIAL_TL_RAKE_ANG","MFG_TL_RAKE_ANG","MFG_MAX_MIL_TIME","MFG_MAX_MIL_LENGTH","MFG_WEIGHT_SNTX","MFG_COOLNT_SNTX","MFG_VC_NEW_SP","MFG_SZ_GLOBAL","MFG_VC_NEW","MFG_MAX_FEEDRATE","MFG_PP","MFG_SZ","MFG_VC"],
    "MfgBarrelMillTool": ["MFG_BALL_TYPE","MFG_TOOL_NUMBER","MFG_REPOSITORY_SOURCE","MFG_ORIGINAL_ID","MFG_NAME","MFG_COMMENT","MFG_WAY_OF_ROT","MFG_TOOTH_DESC","MFG_TOOTH_MAT","MFG_MAX_PLNG_ANG","MFG_NB_OF_FLUTES","MFG_MACH_QUALITY","MFG_COMPOSITION","MFG_TOOTH_MATDESC","MFG_TL_RAKE_ANG","MFG_RADIAL_TL_RAKE_ANG","MFG_WEIGHT_SNTX","MFG_MAX_MIL_LENGTH","MFG_COOLNT_SNTX","MFG_MAX_MIL_TIME","MFG_BARREL_RADIUS","MFG_CORNER_RAD","MFG_OVERALL_LGTH","MFG_BODY_DIAM","MFG_RADIAL_DISTANCE","MFG_CUT_LENGTH","MFG_VERTICAL_DISTANCE","MFG_ENTRY_DIAM","MFG_SZ_FINISH","MFG_AR_ROUGH","MFG_MAX_FEEDRATE","MFG_SZ_ROUGH_GLOBAL","MFG_VC_FINISH_NEW_SP","MFG_VC_ROUGH_NEW_SP","MFG_AA_ROUGH","MFG_AA_FINISH","MFG_VC_FINISH_NEW","MFG_VC_ROUGH","MFG_SZ_ROUGH","MFG_SZ_FINISH_GLOBAL","MFG_VC_ROUGH_NEW","MFG_VC_FINISH","MFG_AR_FINISH"],
    "MfgExternalTool": ["MFG_DESC_CODE","MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_SHANK_WIDTH","MFG_SHK_LENGTH_2","MFG_SHK_LENGTH_1","MFG_SHANK_HEIGHT","MFG_SHK_CUT_WDTH","MFG_CLEAR_ANGLE","MFG_INSERT_LGTH","MFG_INSERT_ANGLE","MFG_KAPPA_R","MFG_HOLDER_CAPAB","MFG_HAND_STYLE","MFG_MAX_REC_DPTH","MFG_LEADING_ANG","MFG_TRAILING_ANG","MFG_MAX_MIL_TIME","MFG_MAX_MIL_LENGTH","MFG_WEIGHT_SNTX","MFG_COOLNT_SNTX","MFG_ISO_CUT_SIZE","MFG_ISO_LENGTH","MFG_ISO_WIDTH","MFG_ISO_HEIGHT","MFG_ISO_DIR","MFG_ISO_CLR_ANG","MFG_ISO_APPR_ANG","MFG_ISO_SHAPE","MFG_ISO_CLAM_SYS"],
    "MfgInternalTool": ["MFG_DESC_CODE","MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_BODY_DIAM","MFG_BAR_CUT_RAD","MFG_BAR_LENGTH_2","MFG_BAR_LENGTH_1","MFG_SHK_CUT_WDTH","MFG_CLEAR_ANGLE","MFG_INSERT_LGTH","MFG_INSERT_ANGLE","MFG_KAPPA_R","MFG_HAND_STYLE","MFG_MIN_DIAM","MFG_MAX_REC_DPTH","MFG_MAX_BOR_DPTH","MFG_LEADING_ANG","MFG_TRAILING_ANG","MFG_MAX_MIL_TIME","MFG_MAX_MIL_LENGTH","MFG_WEIGHT_SNTX","MFG_COOLNT_SNTX","MFG_ISO_CUT_SIZE","MFG_ISO_DIR","MFG_ISO_CLR_ANG","MFG_ISO_APPR_ANG","MFG_ISO_SHAPE","MFG_ISO_CLAM_SYS","MFG_ISO_LENGTH","MFG_ISO_BAR_DIA","MFG_ISO_BAR_TYPE"],
    "MfgGrooveExternalTool": ["MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_SHANK_WIDTH","MFG_SHK_LENGTH_2","MFG_SHK_LENGTH_1","MFG_SHANK_HEIGHT","MFG_SHK_CUT_WDTH","MFG_CLEAR_ANGLE","MFG_INSERT_WIDTH","MFG_HAND_ANGLE","MFG_HAND_STYLE","MFG_MAX_CUT_WDTH","MFG_MAX_CUT_DPTH","MFG_GAUGING_ANG","MFG_MAX_MIL_TIME","MFG_MAX_MIL_LENGTH","MFG_WEIGHT_SNTX","MFG_COOLNT_SNTX"],
    "MfgGrooveInternalTool": ["MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_BODY_DIAM","MFG_BAR_CUT_RAD","MFG_BAR_LENGTH_2","MFG_BAR_LENGTH_1","MFG_CLEAR_ANGLE","MFG_INSERT_WIDTH","MFG_HAND_ANGLE","MFG_HAND_STYLE","MFG_MIN_DIAM","MFG_MAX_CUT_WDTH","MFG_MAX_CUT_DPTH","MFG_GAUGING_ANG","MFG_MAX_MIL_TIME","MFG_MAX_MIL_LENGTH","MFG_WEIGHT_SNTX","MFG_COOLNT_SNTX"],
    "MfgGrooveFrontalTool": ["MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_HAND_STYLE","MFG_SHANK_WIDTH","MFG_SHK_LENGTH_2","MFG_SHK_LENGTH_1","MFG_SHANK_HEIGHT","MFG_SHK_CUT_WDTH","MFG_CLEAR_ANGLE","MFG_INSERT_WIDTH","MFG_MAX_CUT_WDTH","MFG_MAX_CUT_DPTH","MFG_MIN_CUT_DIAM","MFG_MAX_CUT_DIAM","MFG_GAUGING_ANG","MFG_MAX_MIL_TIME","MFG_MAX_MIL_LENGTH","MFG_WEIGHT_SNTX","MFG_COOLNT_SNTX"],
    "MfgThreadExternalTool": ["MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_SHANK_WIDTH","MFG_SHK_LENGTH_2","MFG_SHK_LENGTH_1","MFG_SHANK_HEIGHT","MFG_SHK_CUT_WDTH","MFG_INSERT_LGTH","MFG_HAND_STYLE","MFG_MAX_MIL_TIME","MFG_MAX_MIL_LENGTH","MFG_WEIGHT_SNTX","MFG_COOLNT_SNTX"],
    "MfgThreadInternalTool": ["MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_BODY_DIAM","MFG_BAR_CUT_RAD","MFG_BAR_LENGTH_2","MFG_BAR_LENGTH_1","MFG_INSERT_LGTH","MFG_HAND_STYLE","MFG_MIN_DIAM","MFG_MAX_MIL_TIME","MFG_MAX_MIL_LENGTH","MFG_WEIGHT_SNTX","MFG_COOLNT_SNTX"],
    "MfgWireEDMTool": ["MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME"],
    "MfgLaserBeam": ["MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_CUT_LENGTH","MFG_OVERALL_LGTH","MFG_NOMINAL_DIAM","MFG_TOOL_MATERIAL","MFG_MAX_MIL_TIME","MFG_MAX_MIL_LENGTH","MFG_WEIGHT_SNTX","MFG_COOLNT_SNTX"],
    "MfgBallStylusTool": ["MFG_BALL_TYPE","MFG_TOOL_NUMBER","MFG_REPOSITORY_SOURCE","MFG_ORIGINAL_ID","MFG_NAME","MFG_COMMENT","MFG_STYLUS_MATERIAL","MFG_STYLUS_TYPE","MFG_WEIGHT_SNTX","MFG_MAX_MIL_LENGTH","MFG_COOLNT_SNTX","MFG_MAX_MIL_TIME","MFG_BALL_LENGTH_DOWN","MFG_LENGTH","MFG_BODY_DIAM","MFG_OVERALL_LGTH","MFG_NOMINAL_DIAM","MFG_MAX_FEEDRATE"],
    "MfgCylinderStylusTool": ["MFG_BALL_TYPE","MFG_TOOL_NUMBER","MFG_REPOSITORY_SOURCE","MFG_ORIGINAL_ID","MFG_NAME","MFG_COMMENT","MFG_STYLUS_MATERIAL","MFG_STYLUS_TYPE","MFG_WEIGHT_SNTX","MFG_MAX_MIL_LENGTH","MFG_COOLNT_SNTX","MFG_MAX_MIL_TIME","MFG_CORNER_RAD","MFG_BODY_DIAM","MFG_OVERALL_LGTH","MFG_LENGTH","MFG_CYLINDER_LENGTH","MFG_NOMINAL_DIAM","MFG_MAX_FEEDRATE"]
  },
  "NC_TOOL_ASSEMBLIES": {
    "MfgMillAndDrillToolAssembly": ["MFG_TOOL_NAME","MFG_HOLDER_STAGES","MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_HOLDER_LENGTH_3","MFG_HOLDER_LENGTH_2","MFG_HOLDER_LENGTH_1","MFG_CONE_DIAMETER_5","MFG_CONE_DIAMETER_4","MFG_CONE_DIAMETER_3","MFG_DIAMETER_6","MFG_DIAMETER_5","MFG_DIAMETER_4","MFG_CONE_DIAMETER_2","MFG_CONE_DIAMETER_1","MFG_CONE_LENGTH","MFG_ORIENT_ANGLE","MFG_TL_SET_Z","MFG_TL_SET_Y","MFG_TL_SET_X","MFG_TL_SET_LGTH","MFG_DIAMETER_3","MFG_DIAMETER_2","MFG_DIAMETER_1","MFG_ASS_GAGE_2","MFG_ASS_GAGE_1","MFG_TURRET_NUMBER","MFG_TOOL_ASS_POWER","MFG_NB_OF_COMP"],
    "MfgLatheToolAssembly": ["MFG_TOOL_NAME","MFG_INSERT_NAME","MFG_MACHINE_COMP","MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_TOOL_NUMBER","MFG_COMMENT","MFG_NAME","MFG_TL_SETUP_ANG","MFG_TL_SET_Z","MFG_TL_SET_Y","MFG_TL_SET_X","MFG_TOOL_INVERT","MFG_OUTP_PREF_3","MFG_OUTP_PREF_2","MFG_OUTP_PREF_1","MFG_TURRET_NUMBER","MFG_TOOL_ASS_POWER","MFG_NB_OF_COMP"]
  },
  "NC_INSERTS": {
    "MfgSquareInsert": ["MFG_DESC_CODE","MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_COMMENT","MFG_NAME","MFG_CLEAR_ANGLE","MFG_INSERT_THICK","MFG_INSCRIB_DIAM","MFG_INSERT_LGTH","MFG_NOSE_RADIUS","MFG_LIFE_TIME","MFG_INSERT_MAT","MFG_MACH_QUALITY","MFG_VC_ECROUTAGE_NEW","MFG_VC_ROUGH_NEW","MFG_VC_FINISH_NEW","MFG_MAX_FEEDRATE","MFG_PP_ECROUTAGE","MFG_SZ_ECROUTAGE","MFG_VC_ECROUTAGE","MFG_PP_ROUGH","MFG_SZ_ROUGH","MFG_VC_ROUGH","MFG_SZ_FINISH","MFG_VC_FINISH","MFG_ISO_DIR","MFG_ISO_CUTCOND","MFG_ISO_NOSE_RAD","MFG_ISO_THICK","MFG_ISO_CUT_SIZE","MFG_ISO_TYPE","MFG_ISO_TOL","MFG_ISO_CLR_ANG","MFG_ISO_SHAPE"],
    "MfgRoundInsert": ["MFG_DESC_CODE","MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_COMMENT","MFG_NAME","MFG_CLEAR_ANGLE","MFG_INSERT_THICK","MFG_NOSE_RADIUS","MFG_LIFE_TIME","MFG_INSERT_MAT","MFG_MACH_QUALITY","MFG_VC_ECROUTAGE_NEW","MFG_VC_ROUGH_NEW","MFG_VC_FINISH_NEW","MFG_MAX_FEEDRATE","MFG_PP_ECROUTAGE","MFG_SZ_ECROUTAGE","MFG_VC_ECROUTAGE","MFG_PP_ROUGH","MFG_SZ_ROUGH","MFG_VC_ROUGH","MFG_SZ_FINISH","MFG_VC_FINISH","MFG_ISO_DIR","MFG_ISO_CUTCOND","MFG_ISO_NOSE_RAD","MFG_ISO_THICK","MFG_ISO_CUT_SIZE","MFG_ISO_TYPE","MFG_ISO_TOL","MFG_ISO_CLR_ANG","MFG_ISO_SHAPE"],
    "MfgDiamondInsert": ["MFG_DESC_CODE","MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_COMMENT","MFG_NAME","MFG_CLEAR_ANGLE","MFG_INSERT_THICK","MFG_INSCRIB_DIAM","MFG_INSERT_LGTH","MFG_INSERT_ANGLE","MFG_NOSE_RADIUS","MFG_LIFE_TIME","MFG_INSERT_MAT","MFG_MACH_QUALITY","MFG_VC_ECROUTAGE_NEW","MFG_VC_ROUGH_NEW","MFG_VC_FINISH_NEW","MFG_MAX_FEEDRATE","MFG_PP_ECROUTAGE","MFG_SZ_ECROUTAGE","MFG_VC_ECROUTAGE","MFG_PP_ROUGH","MFG_SZ_ROUGH","MFG_VC_ROUGH","MFG_SZ_FINISH","MFG_VC_FINISH","MFG_ISO_DIR","MFG_ISO_CUTCOND","MFG_ISO_NOSE_RAD","MFG_ISO_THICK","MFG_ISO_CUT_SIZE","MFG_ISO_TYPE","MFG_ISO_TOL","MFG_ISO_CLR_ANG","MFG_ISO_SHAPE"],
    "MfgTriangularInsert": ["MFG_DESC_CODE","MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_COMMENT","MFG_NAME","MFG_CLEAR_ANGLE","MFG_INSERT_THICK","MFG_INSCRIB_DIAM","MFG_INSERT_LGTH","MFG_NOSE_RADIUS","MFG_LIFE_TIME","MFG_INSERT_MAT","MFG_MACH_QUALITY","MFG_VC_ECROUTAGE_NEW","MFG_VC_ROUGH_NEW","MFG_VC_FINISH_NEW","MFG_MAX_FEEDRATE","MFG_PP_ECROUTAGE","MFG_SZ_ECROUTAGE","MFG_VC_ECROUTAGE","MFG_PP_ROUGH","MFG_SZ_ROUGH","MFG_VC_ROUGH","MFG_SZ_FINISH","MFG_VC_FINISH","MFG_ISO_DIR","MFG_ISO_CUTCOND","MFG_ISO_NOSE_RAD","MFG_ISO_THICK","MFG_ISO_CUT_SIZE","MFG_ISO_TYPE","MFG_ISO_TOL","MFG_ISO_CLR_ANG","MFG_ISO_SHAPE"],
    "MfgTrigonInsert": ["MFG_DESC_CODE","MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_COMMENT","MFG_NAME","MFG_CLEAR_ANGLE","MFG_INSERT_THICK","MFG_INSCRIB_DIAM","MFG_INSERT_LGTH","MFG_NOSE_RADIUS","MFG_LIFE_TIME","MFG_INSERT_MAT","MFG_MACH_QUALITY","MFG_VC_ECROUTAGE_NEW","MFG_VC_ROUGH_NEW","MFG_VC_FINISH_NEW","MFG_MAX_FEEDRATE","MFG_PP_ECROUTAGE","MFG_SZ_ECROUTAGE","MFG_VC_ECROUTAGE","MFG_PP_ROUGH","MFG_SZ_ROUGH","MFG_VC_ROUGH","MFG_SZ_FINISH","MFG_VC_FINISH","MFG_ISO_DIR","MFG_ISO_CUTCOND","MFG_ISO_NOSE_RAD","MFG_ISO_THICK","MFG_ISO_CUT_SIZE","MFG_ISO_TYPE","MFG_ISO_TOL","MFG_ISO_CLR_ANG","MFG_ISO_SHAPE"],
    "MfgGrooveInsert": ["MFG_GROOVE_TYPE","MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_COMMENT","MFG_NAME","MFG_CLEAR_ANGLE","MFG_INSERT_THICK","MFG_NOSE_RAD_2","MFG_NOSE_RAD_1","MFG_FLANK_ANG_2","MFG_FLANK_ANG_1","MFG_BOTTOM_ANGLE","MFG_INSERT_WIDTH","MFG_INSERT_HEIGH","MFG_INSERT_MAT","MFG_MACH_QUALITY","MFG_VC_ECROUTAGE_NEW","MFG_VC_ROUGH_NEW","MFG_VC_FINISH_NEW","MFG_MAX_FEEDRATE","MFG_PP_ECROUTAGE","MFG_SZ_ECROUTAGE","MFG_VC_ECROUTAGE","MFG_PP_ROUGH","MFG_SZ_ROUGH","MFG_VC_ROUGH","MFG_SZ_FINISH","MFG_VC_FINISH"],
    "MfgThreadInsert": ["MFG_MACH_TYPE","MFG_ORIGINAL_ID","MFG_REPOSITORY_SOURCE","MFG_COMMENT","MFG_NAME","MFG_INSERT_THICK","MFG_NOSE_RADIUS","MFG_TOOTH_H","MFG_TOOTH_Z","MFG_TOOTH_X","MFG_HAND_STYLE","MFG_THREAD_ANGLE","MFG_INSERT_LGTH","MFG_PITCH_NUMBER","MFG_PITCH_OF_THREAD","MFG_THREAD_DEF","MFG_THREAD_PROF","MFG_LIFE_TIME","MFG_INSERT_MAT","MFG_MACH_QUALITY","MFG_VC_ECROUTAGE_NEW","MFG_VC_ROUGH_NEW","MFG_VC_FINISH_NEW","MFG_MAX_FEEDRATE","MFG_PP_ECROUTAGE","MFG_SZ_ECROUTAGE","MFG_VC_ECROUTAGE","MFG_PP_ROUGH","MFG_SZ_ROUGH","MFG_VC_ROUGH","MFG_SZ_FINISH","MFG_VC_FINISH"]
  },
  "NC_CORRECTORS": {
    "MfgCorrector": ["MFG_TOOL_NAME","MFG_MCD_SIMULATION_LENGTH","MFG_MCD_SIMULATION_RADIUS","MFG_CMP_TL_DIAM","MFG_RAD_NUM","MFG_LNG_NUM","MFG_SITE_NUM","MFG_SITE_TYP"]
  }
}
''')

# Families whose Catalog Editor screenshot scrolled off-screen (a few trailing columns may be missing).
TRUNCATED_FAMILIES = {
    "MfgFaceMillTool", "MfgExternalTool", "MfgGrooveExternalTool", "MfgGrooveInternalTool",
    "MfgGrooveFrontalTool", "MfgThreadExternalTool", "MfgThreadInternalTool",
    "MfgBallStylusTool", "MfgCylinderStylusTool", "MfgWireEDMTool",
}

# Keywords picked from a fixed list — shown as dropdowns. Values are CATIA's internal (CSV) forms.
ENUM_VALUES = {
    "MFG_WAY_OF_ROT": ["RIGHT_HAND", "LEFT_HAND"],
    "MFG_MACH_QUALITY": ["ROUGH", "FINISH", "EITHER"],
    "MFG_COMPOSITION": ["ONE_PIECE", "INSERT_HOLDER"],
    "MFG_TOOTH_MAT": ["HIGH_SPEED_STEEL", "COATED_HIGH_SPEED_STEEL", "CARBIDE", "COATED_CARBIDE", "OTHER"],
}

# Default enum value for a new tool row (uniform across the sample catalog).
ENUM_DEFAULTS = {
    "MFG_WAY_OF_ROT": "RIGHT_HAND",
    "MFG_MACH_QUALITY": "EITHER",
    "MFG_COMPOSITION": "ONE_PIECE",
}

# Boolean keywords — shown as a TRUE/FALSE dropdown, default FALSE.
BOOLEAN_KEYWORDS = {"MFG_BALL_TYPE", "MFG_TOOL_INVERT", "MfgGlobalSpindleMagnitude"}


def is_boolean(keyword):
    """True for any keyword CATIA treats as Boolean, whether named here or typed so by KEYWORD_TYPES."""
    return keyword in BOOLEAN_KEYWORDS or KEYWORD_TYPES.get(keyword) == "Boolean"


def is_feeds_speeds(keyword):
    """Feeds & speeds keywords default to 0 (CATIA shows 0 with several alternative option fields)."""
    k = keyword.upper()
    return (k.startswith("MFG_VC") or k.startswith("MFG_SZ") or k.startswith("MFG_PP")
            or k.startswith("MFG_AA_") or k.startswith("MFG_AR_") or k == "MFG_MAX_FEEDRATE")


def default_for(keyword):
    """Default cell value for a new tool row."""
    if is_boolean(keyword):
        return "FALSE"
    if keyword in ENUM_DEFAULTS:
        return ENUM_DEFAULTS[keyword]
    if is_feeds_speeds(keyword):
        return "0"
    return ""


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


def show_error(operation, exc):
    """Scrolled error dialog + full traceback to console — the standard script error pattern."""
    full_traceback = traceback.format_exc()
    print(full_traceback)
    error_msg = (
        f"Error Summary: {str(exc)}\n"
        f"------------------------------------------\n"
        f"Technical Debug Info:\n\n{full_traceback}"
    )
    e_dlg = wx.lib.dialogs.ScrolledMessageDialog(None, error_msg, "Script Error")
    error_icon = wx.ArtProvider.GetBitmap(wx.ART_ERROR, wx.ART_MESSAGE_BOX)
    icon_bitmap = wx.StaticBitmap(e_dlg, wx.ID_ANY, error_icon)
    header_text = wx.StaticText(e_dlg, label=f"An error occurred during {operation}:")
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
    e_dlg.ShowModal()
    e_dlg.Destroy()


# Keyword -> CATIA type, extracted from the batch-catalog samples CATIA ships in
# <CATIA>\win_b64\startup\Manufacturing\Samples\*.csv. CATIA types dimensional keywords with
# unit tokens (mm, deg, s, mm_mn, mm_turn, m_mn), not Real - across all 24 sample files "Real"
# appears once and "Boolean" once, so neither is used here.
KEYWORD_TYPES = json.loads(r'''
{
  "MATERIAL":"String","MFG_AA_FINISH":"mm","MFG_AA_ROUGH":"mm","MFG_ANGLE2":"deg","MFG_ANG_X":"deg","MFG_ANG_Y":"deg",
  "MFG_ANG_Z":"deg","MFG_AR_FINISH":"mm","MFG_AR_ROUGH":"mm","MFG_ASS_GAGE_1":"mm","MFG_ASS_GAGE_2":"mm",
  "MFG_BALL_LENGTH_DOWN":"mm","MFG_BALL_TYPE":"Boolean","MFG_BAR_CUT_RAD":"mm","MFG_BAR_LENGTH_1":"mm",
  "MFG_BAR_LENGTH_2":"mm","MFG_BODY_DIAM":"mm","MFG_BORE_ABILITY":"String","MFG_BOTTOM_ANGLE":"deg",
  "MFG_CHAMFER_ANGLE":"deg","MFG_CHAMFR_DIAM1":"mm","MFG_CHAMFR_DIAM2":"mm","MFG_CLEAR_ANGLE":"deg",
  "MFG_CMP_TL_DIAM":"mm","MFG_COMMENT":"String","MFG_COMPOSITION":"String","MFG_CONE_DIAMETER_1":"mm",
  "MFG_CONE_DIAMETER_2":"mm","MFG_CONE_LENGTH":"mm","MFG_COOLNT_SNTX":"String","MFG_CORNER_RAD":"mm",
  "MFG_CORNER_RAD_2":"mm","MFG_CUT_ANGLE":"deg","MFG_CUT_LENGTH":"mm","MFG_CYLINDER_LENGTH":"mm",
  "MFG_DIAMETER_1":"mm","MFG_DIAMETER_2":"mm","MFG_DIAMETER_3":"mm","MFG_ENTRY_DIAM":"mm","MFG_FLANK_ANG_1":"deg",
  "MFG_FLANK_ANG_2":"deg","MFG_GAGE_X1":"mm","MFG_GAGE_X2":"mm","MFG_GAGE_Y1":"mm","MFG_GAGE_Y2":"mm",
  "MFG_GAGE_Z1":"mm","MFG_GAGE_Z2":"mm","MFG_GAUGING_ANG":"deg","MFG_HAND_ANGLE":"deg","MFG_HAND_STYLE":"String",
  "MFG_HAND_TYPE":"String","MFG_HOLDER_CAPAB":"String","MFG_INCL_ANGLE":"deg","MFG_INSCRIB_DIAM":"mm",
  "MFG_INSERT_ANGLE":"deg","MFG_INSERT_FORM":"String","MFG_INSERT_HEIGH":"mm","MFG_INSERT_LGTH":"mm",
  "MFG_INSERT_MAT":"String","MFG_INSERT_NAME":"String","MFG_INSERT_THICK":"mm","MFG_INSERT_WIDTH":"mm",
  "MFG_INS_COMMENT":"String","MFG_ISO_APPR_ANG":"String","MFG_ISO_BAR_DIA":"String","MFG_ISO_BAR_TYPE":"String",
  "MFG_ISO_CLAM_SYS":"String","MFG_ISO_CLR_ANG":"String","MFG_ISO_CUTCOND":"String","MFG_ISO_CUT_SIZE":"String",
  "MFG_ISO_DIR":"String","MFG_ISO_HEIGHT":"String","MFG_ISO_LENGTH":"String","MFG_ISO_NOSE_RAD":"String",
  "MFG_ISO_SHAPE":"String","MFG_ISO_THICK":"String","MFG_ISO_TOL":"String","MFG_ISO_TYPE":"String",
  "MFG_ISO_WIDTH":"String","MFG_KAPPA_R":"deg","MFG_LEADING_ANG":"deg","MFG_LENGTH":"mm","MFG_LENGTH_1":"mm",
  "MFG_LENGTH_2":"mm","MFG_LIFE_LGTH":"mm","MFG_LIFE_TIME":"s","MFG_LNG_NUM":"Integer","MFG_LOWER_ANGLE":"deg",
  "MFG_LOWER_DIAM":"mm","MFG_MACH_QUALITY":"String","MFG_MACH_TYPE":"String","MFG_MANUF_NAME":"String",
  "MFG_MANUF_OPTION":"String","MFG_MAX_BOR_DPTH":"mm","MFG_MAX_CUT_DIAM":"mm","MFG_MAX_CUT_DPTH":"mm",
  "MFG_MAX_CUT_WDTH":"mm","MFG_MAX_DIAMETER":"mm","MFG_MAX_FEEDRATE":"mm_mn","MFG_MAX_MIL_LENGTH":"mm",
  "MFG_MAX_MIL_TIME":"s","MFG_MAX_PLNG_ANG":"deg","MFG_MAX_REC_DPTH":"mm","MFG_MIN_CUT_DIAM":"mm",
  "MFG_MIN_CUT_WDTH":"mm","MFG_MIN_DIAM":"mm","MFG_MIN_DIAMETER":"mm","MFG_NAME":"String","MFG_NAME_BAS":"String",
  "MFG_NB_OF_COMP":"Integer","MFG_NB_OF_FLUTES":"Integer","MFG_NB_OF_STAGES":"Integer","MFG_NOMINAL_DIAM":"mm",
  "MFG_NON_CUT_DIAM":"mm","MFG_NOSE_RADIUS":"mm","MFG_NOSE_RAD_1":"mm","MFG_NOSE_RAD_2":"mm",
  "MFG_ORDER_CODE":"String","MFG_ORIENT_ANGLE":"deg","MFG_OUTP_PREF_1":"String","MFG_OUTP_PREF_2":"String",
  "MFG_OUTP_PREF_3":"String","MFG_OUTSIDE_DIAM":"mm","MFG_OVERALL_LGTH":"mm","MFG_PITCH_NUMBER":"Integer",
  "MFG_PITCH_OF_THREAD":"mm","MFG_PP":"mm","MFG_RADIAL_TL_RAKE_ANG":"deg","MFG_RAD_NUM":"Integer",
  "MFG_SHANK_HEIGHT":"mm","MFG_SHANK_HEIGTH":"mm","MFG_SHANK_WIDTH":"mm","MFG_SHK_CUT_WDTH":"mm",
  "MFG_SHK_LENGTH_1":"mm","MFG_SHK_LENGTH_2":"mm","MFG_SITE_NUM":"Integer","MFG_SITE_TYP":"String",
  "MFG_STYLUS_MATERIAL":"String","MFG_STYLUS_TYPE":"String","MFG_SZ":"mm_turn","MFG_SZ_FINISH":"mm_turn",
  "MFG_SZ_GLOBAL":"mm_turn","MFG_SZ_ROUGH":"mm_turn","MFG_TAPER_ANGLE":"deg","MFG_THD_CLS_DESC":"String",
  "MFG_THD_FRM_DESC":"String","MFG_THREAD_ANGLE":"deg","MFG_THREAD_CLASS":"String","MFG_THREAD_DEF":"String",
  "MFG_THREAD_FORM":"String","MFG_THREAD_PROF":"String","MFG_THREAD_UNIT":"String","MFG_TIP_ANGLE":"deg",
  "MFG_TIP_LENGTH":"mm","MFG_TIP_RADIUS":"mm","MFG_TL_RAKE_ANG":"deg","MFG_TL_SETUP_ANG":"deg","MFG_TL_SET_LGTH":"mm",
  "MFG_TL_SET_X":"mm","MFG_TL_SET_Y":"mm","MFG_TL_SET_Z":"mm","MFG_TL_TIP_LGTH":"mm","MFG_TOOL_ANGLE":"deg",
  "MFG_TOOL_ASS_POWER":"String","MFG_TOOL_CORE_DIAMETER":"mm","MFG_TOOL_INVERT":"Integer","MFG_TOOL_NAME":"String",
  "MFG_TOOL_NUMBER":"Integer","MFG_TOOTH_DES":"String","MFG_TOOTH_DESC":"String","MFG_TOOTH_H":"mm",
  "MFG_TOOTH_MAT":"String","MFG_TOOTH_MATDES":"String","MFG_TOOTH_MATDESC":"String","MFG_TOOTH_X":"mm",
  "MFG_TOOTH_Z":"mm","MFG_TRAILING_ANG":"deg","MFG_UPPER_ANGLE":"deg","MFG_UPPER_DIAM":"mm","MFG_VC":"mm_mn",
  "MFG_VC_FINISH":"m_mn","MFG_VC_ROUGH":"m_mn","MFG_WAY_OF_ROT":"String","MFG_WEIGHT_SNTX":"String","Name":"String",
  "Original Name":"String","Replacing Name":"String"
}
''')


def infer_type(keyword):
    """Return the CATIA keyword type for the CSV type row, preferring CATIA's own sample data."""
    if keyword in KEYWORD_TYPES:
        return KEYWORD_TYPES[keyword]
    k = keyword.upper()                                                                                          #Fall back to unit-aware name matching
    if any(t in k for t in ("_ANG", "ANGLE", "KAPPA")):
        return "deg"
    if any(t in k for t in ("MAX_MIL_TIME", "LIFE_TIME")):
        return "s"
    if k.startswith("MFG_VC"):
        return "m_mn"
    if "MAX_FEEDRATE" in k:
        return "mm_mn"
    if any(t in k for t in ("NB_OF", "_NUM", "STAGES", "PITCH_NUMBER")):
        return "Integer"
    if any(t in k for t in ("DIAM", "LENGTH", "LGTH", "RADIUS", "RAD", "WIDTH", "WDTH", "HEIGHT", "HEIGH",
                            "THICK", "DPTH", "DISTANCE", "PITCH", "GAGE")):
        return "mm"
    if k.startswith(("MFG_SZ", "MFG_AR", "MFG_AA", "MFG_PP")):
        return "mm"
    return "String"


# --------------------------------------------------------------------------------------------------------------
# Whole-tree CSV (CATIA batch-catalog format, nested CHAPTER / ENDCHAPTER).
# tree = { chapter_name: { family_name: {"columns": [...], "rows": [[...]]} } }
# Grid/CSV column layout per family: [Entity Name] + [keyword columns...] + [CATPart Path]
# --------------------------------------------------------------------------------------------------------------
def default_tree():
    tree = {}
    for chapter, families in FAMILY_KEYWORDS.items():
        tree[chapter] = {}
        for family, keywords in families.items():
            tree[chapter][family] = {"columns": [NAME_COL] + list(keywords) + [DOC_COL], "rows": []}
    return tree


def write_catalog_csv(path, tree):
    """Write the CATIA batch-catalog CSV that create_catalog_from_csv consumes.

    A tooling catalog is a tree: the root chapter NC_RESOURCES holds the four resource chapters
    NC_TOOLS, NC_INSERTS, NC_TOOL_ASSEMBLIES and NC_CORRECTORS, and each of those holds the tool
    families. That structure is reproduced here, matching ToolAssembliesSample01.csv:

        CHAPTER,NC_RESOURCES         a chapter block, listing its members by name
        Keywords,Name
        Types,String
        NC_TOOLS,NC_TOOLS
        NC_INSERTS,NC_INSERTS
        END

        CHAPTER,NC_TOOLS             each resource chapter lists its families
        Keywords,Name
        Types,String
        MfgEndMillTool,MfgEndMillTool
        END

        ENDCHAPTER,MfgEndMillTool    a family block, holding the keyword columns and the tools
        Keywords,<kw1>,<kw2>,...
        Types,<type1>,<type2>,...
        <entity name>,<v1>,<v2>,...
        END

    CATIA's naming is counter-intuitive: ENDCHAPTER *opens* a family block, and every block -
    chapter and family alike - is closed by END.

    Every chapter and every family is written, whether or not it holds any tools, so the
    catalog carries the full empty skeleton the way a hand-built tooling catalog does.

    The CATPart path column is deliberately not emitted; it is not a CATIA keyword, so it is
    carried in the app's own CSV only. The samples are Excel exports: every row is padded with
    trailing commas to one uniform column count and lines end with LF, both reproduced here.
    """
    chapters = [c for c in RESOURCE_CHAPTERS if c in tree]                                                       #Standard order first
    chapters += [c for c in tree if c not in chapters]
    if not chapters:
        return False

    rows = []
    rows.append(["CHAPTER", ROOT_CHAPTER])                                                                       #Root of a tooling catalog
    rows.append(["Keywords", "Name"])
    rows.append(["Types", "String"])
    for chapter in chapters:
        rows.append([chapter, chapter])
    rows.append(["END"])

    for chapter in chapters:                                                                                     #Each resource chapter lists its families
        rows.append(["CHAPTER", chapter])
        rows.append(["Keywords", "Name"])
        rows.append(["Types", "String"])
        for family in tree[chapter]:
            rows.append([family, family])
        rows.append(["END"])

    for chapter in chapters:                                                                                     #Family blocks, empty ones included
        for family, data in tree[chapter].items():
            keywords = data["columns"][1:-1]                                                                     #Drop Entity Name / CATPart Path
            rows.append(["ENDCHAPTER", family])
            rows.append(["Keywords"] + keywords)
            rows.append(["Types"] + [infer_type(k) for k in keywords])
            for row in data["rows"]:
                values = row[1:1 + len(keywords)]
                values += [""] * (len(keywords) - len(values))                                                   #Pad short rows
                rows.append([row[0]] + values)
            rows.append(["END"])

    width = max(len(r) for r in rows)                                                                            #Uniform grid, as Excel exports it
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")                                                              #CATIA's samples use LF, not CRLF
        for row in rows:
            writer.writerow(row + [""] * (width - len(row)))
    return True


'''
    Build the .catalog by having CATIA run CreateCatalogFromcsv itself.

    Calling CreateCatalogFromcsv over COM from Python produces a catalog rooted at a stray
    empty "Chapter.1" with the real tree unreachable inside it. The identical call made from
    a CATScript running inside CATIA produces the correct catalog rooted at NC_RESOURCES.
    So the macro is generated here and handed to CATIA through SystemService.ExecuteScript,
    which runs it in-process.

    Inputs:
        caa         The catia() application instance
        csv_path    The catalog CSV written by write_catalog_csv
        out_path    Where the .catalog should be created

    output:
        None
'''
def build_catalog_in_catia(caa, csv_path, out_path):
    macro_dir = os.path.join(tempfile.gettempdir(), "catia_macros")
    os.makedirs(macro_dir, exist_ok=True)
    macro = (
        'Language="VBSCRIPT"\n\n'
        'Sub CATMain()\n'
        ' Dim Catlg As Document\n'
        ' Set Catlg = CATIA.Documents.Add("CatalogDocument")\n'
        f' Catlg.CreateCatalogFromcsv "{csv_path}", "{out_path}"\n'
        'End Sub\n'
    )
    with open(os.path.join(macro_dir, BUILD_MACRO), "w", encoding="latin-1", newline="\r\n") as f:
        f.write(macro)
    caa.system_service.execute_script(macro_dir,                                                               #Runs inside CATIA, not over COM
                                      CatScriptLibraryType.catScriptLibraryTypeDirectory,
                                      BUILD_MACRO,
                                      "CATMain",
                                      [])


def read_tree_csv(path, tree):
    """Merge rows from a catalog CSV into the given tree (matching by chapter + family).

    Reads the CATIA batch format written by write_catalog_csv, and also a variant with no
    Keywords / Types row labels, where the first two body rows of a family block are the keyword
    names and their types. CHAPTER blocks only list member names and carry no tool data,
    so their bodies are skipped; the owning chapter of a family is resolved from the tree by
    family name rather than from the preceding CHAPTER line, because CATIA emits every chapter
    block before any family block.
    """
    with open(path, "r", newline="", encoding="utf-8") as f:
        sample = f.read(2048)
        f.seek(0)
        delimiter = ";" if sample.count(";") > sample.count(",") else ","
        rows = list(csv.reader(f, delimiter=delimiter))

    chapter = None
    family = None
    keywords = []
    expect_types = False
    cleared = set()
    for row in rows:
        if not row or not any(c.strip() for c in row):
            continue
        tag = row[0].strip()
        if tag.upper() == "CHAPTER":
            chapter = family = None                                                                            #Chapter blocks list member names only
            continue
        if tag.upper() == "END":
            chapter = family = None
            continue
        if tag.upper() == "ENDCHAPTER":
            label = row[1].strip() if len(row) > 1 else ""
            keywords = []
            expect_types = False
            if label in tree:                                                                                  #Block names a chapter: family comes from MFG_NAME_BAS
                chapter, family = label, None
            else:                                                                                              #Block names a family directly
                chapter = next((c for c, fams in tree.items() if label in fams), None)
                family = label if chapter else None
            continue
        if chapter not in tree:
            continue
        if tag == "Keywords":
            keywords = [c.strip() for c in row[1:] if c.strip()]
            continue
        if tag == "Types":
            continue
        if not keywords:                                                                                       #Unlabelled variant: first body row is the keywords
            keywords = [c.strip() for c in row[1:] if c.strip()]
            expect_types = True
            continue
        if expect_types:                                                                                       #Unlabelled variant: second body row is the types
            expect_types = False
            if all(c.strip() in TYPE_TOKENS or not c.strip() for c in row[1:]):
                continue

        values = dict(zip(keywords, [c.strip() for c in row[1:1 + len(keywords)]]))
        owner = family or values.get(BASE_NAME_COL)                                                            #Family per block, or per row
        if not owner or owner not in tree[chapter]:
            continue
        if (chapter, owner) not in cleared:
            tree[chapter][owner]["rows"] = []                                                                  #Replace on load, once per family
            cleared.add((chapter, owner))
        columns = tree[chapter][owner]["columns"][1:-1]
        document = row[1 + len(keywords)].strip() if len(row) > 1 + len(keywords) else ""
        tree[chapter][owner]["rows"].append(
            [row[0].strip()] + [values.get(c, "") for c in columns] + [document])
    return tree


# --------------------------------------------------------------------------------------------------------------
# Grid editor frame
# --------------------------------------------------------------------------------------------------------------
class CatalogEditor(wx.Frame):
    def __init__(self, caa, settings, settings_file):
        super().__init__(None, title="Tooling Catalog Editor", size=(1150, 680),
                         style=wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP)
        self.caa = caa
        self.settings = settings
        self.settings_file = settings_file
        self.tree = default_tree()
        self.current = None                                                                                    #(chapter, family)

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        #Selector row
        sel = wx.BoxSizer(wx.HORIZONTAL)
        sel.Add(wx.StaticText(panel, label="Chapter:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.chapter_ctrl = wx.Choice(panel, choices=list(self.tree.keys()))
        self.chapter_ctrl.Bind(wx.EVT_CHOICE, self.on_chapter)
        sel.Add(self.chapter_ctrl, 0, wx.ALL, 5)
        sel.Add(wx.StaticText(panel, label="Family:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.family_ctrl = wx.Choice(panel, choices=[])
        self.family_ctrl.Bind(wx.EVT_CHOICE, self.on_family)
        sel.Add(self.family_ctrl, 1, wx.ALL, 5)
        self.trunc_label = wx.StaticText(panel, label="")
        self.trunc_label.SetForegroundColour(wx.Colour(200, 90, 0))
        sel.Add(self.trunc_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        vbox.Add(sel, 0, wx.EXPAND)

        #Grid
        self.grid = wx.grid.Grid(panel)
        self.grid.CreateGrid(0, 1)
        self.grid.Bind(wx.grid.EVT_GRID_CELL_LEFT_DCLICK, self.on_cell_dclick)                                 #Double-click a CATPart Path cell to browse
        self.grid.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.on_select_cell)                                      #Open dropdowns on a single click
        vbox.Add(self.grid, 1, wx.EXPAND | wx.ALL, 5)

        #Buttons
        btns = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in (
            ("Add Row", self.on_add_row),
            ("Duplicate Row", self.on_dup_row),
            ("Delete Row", self.on_del_row),
            ("Add Column", self.on_add_col),
            (f"Browse {DOC_COL}", self.on_browse_doc),
            ("Load CSV", self.on_load),
            ("Save CSV", self.on_save),
            ("Build Catalog", self.on_build),
        ):
            b = wx.Button(panel, label=label)
            b.Bind(wx.EVT_BUTTON, handler)
            btns.Add(b, 0, wx.ALL, 4)
        vbox.Add(btns, 0, wx.ALIGN_CENTER)

        panel.SetSizer(vbox)
        self.Center()

        if self.tree:
            self.chapter_ctrl.SetSelection(0)
            self.on_chapter(None)

    #--- selection ---
    def on_chapter(self, event):
        self._flush_grid()
        chapter = self.chapter_ctrl.GetStringSelection()
        families = list(self.tree[chapter].keys())
        self.family_ctrl.Set(families)
        if families:
            self.family_ctrl.SetSelection(0)
        self.on_family(None)

    def on_family(self, event):
        self._flush_grid()
        chapter = self.chapter_ctrl.GetStringSelection()
        family = self.family_ctrl.GetStringSelection()
        if not chapter or not family:
            return
        self.current = (chapter, family)
        self.trunc_label.SetLabel("  ⚠ columns may be incomplete — use Add Column" if family in TRUNCATED_FAMILIES else "")
        self._load_grid()

    #--- grid <-> model ---
    def _load_grid(self):
        chapter, family = self.current
        data = self.tree[chapter][family]
        cols = data["columns"]
        if self.grid.GetNumberCols():
            self.grid.DeleteCols(0, self.grid.GetNumberCols())
        if self.grid.GetNumberRows():
            self.grid.DeleteRows(0, self.grid.GetNumberRows())
        self.grid.AppendCols(len(cols))
        for c, name in enumerate(cols):
            self.grid.SetColLabelValue(c, name)
        self._apply_col_editors()
        self.grid.AppendRows(len(data["rows"]))
        for r, row in enumerate(data["rows"]):
            for c in range(len(cols)):
                self.grid.SetCellValue(r, c, row[c] if c < len(row) else "")
        self.grid.AutoSizeColumns()

    #--- CATPart link ---
    def _doc_column(self):
        """Grid column index of the CATPart Path column, or None."""
        for c in range(self.grid.GetNumberCols()):
            if self.grid.GetColLabelValue(c) == DOC_COL:
                return c
        return None

    def _pick_catpart(self, row, col):
        """Browse for the CATPart that physically represents this tool, and store its path."""
        current = self.grid.GetCellValue(row, col)
        start = os.path.dirname(current) if current else self.settings.get("catpart_dir", "")
        with wx.FileDialog(self, f"Select the CATPart for row {row + 1}", defaultDir=start,
                           wildcard="CATPart files (*.CATPart)|*.CATPart|All files (*.*)|*.*",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fd:
            if fd.ShowModal() != wx.ID_OK:
                return
            path = fd.GetPath()
        self.grid.SetCellValue(row, col, path)
        self.settings["catpart_dir"] = os.path.dirname(path)
        self.grid.AutoSizeColumns()

    def on_select_cell(self, event):
        """Drop a choice list open as soon as its cell is selected, rather than on a second click."""
        name = self.grid.GetColLabelValue(event.GetCol())
        if name in ENUM_VALUES or is_boolean(name):
            wx.CallAfter(self.grid.EnableCellEditControl)                                                      #After the selection settles
        event.Skip()

    def on_cell_dclick(self, event):
        col = event.GetCol()
        if self.grid.GetColLabelValue(col) == DOC_COL:
            self._pick_catpart(event.GetRow(), col)                                                            #Browse instead of typing a path
            return
        event.Skip()                                                                                           #Any other column edits normally

    def on_browse_doc(self, event):
        try:
            col = self._doc_column()
            if col is None:
                self._info(f"This family has no {DOC_COL} column.")
                return
            row = self.grid.GetGridCursorRow()
            if row < 0 or not self.grid.GetNumberRows():
                self._info("Select a row first.")
                return
            self._pick_catpart(row, col)
        except Exception as exc:
            show_error("browsing for the CATPart", exc)

    def _apply_col_editors(self):
        """Attach dropdown editors to enum / boolean columns."""
        for c in range(self.grid.GetNumberCols()):
            name = self.grid.GetColLabelValue(c)
            if name in ENUM_VALUES:
                choices, allow = ENUM_VALUES[name], True
            elif is_boolean(name):
                choices, allow = ["FALSE", "TRUE"], False
            else:
                continue
            attr = wx.grid.GridCellAttr()
            attr.SetEditor(wx.grid.GridCellChoiceEditor(choices, allowOthers=allow))
            attr.SetRenderer(wx.grid.GridCellStringRenderer())                                                 #Keep the value visible when not editing
            self.grid.SetColAttr(c, attr)

    def _flush_grid(self):
        if not self.current:
            return
        chapter, family = self.current
        data = self.tree[chapter][family]
        ncols = self.grid.GetNumberCols()
        data["columns"] = [self.grid.GetColLabelValue(c) for c in range(ncols)]
        rows = []
        for r in range(self.grid.GetNumberRows()):
            rows.append([self.grid.GetCellValue(r, c) for c in range(ncols)])
        data["rows"] = rows

    #--- row/column ops ---
    def on_add_row(self, event):
        self.grid.AppendRows(1)
        r = self.grid.GetNumberRows() - 1
        for c in range(self.grid.GetNumberCols()):
            value = default_for(self.grid.GetColLabelValue(c))
            if value:
                self.grid.SetCellValue(r, c, value)

    def on_dup_row(self, event):
        r = self.grid.GetGridCursorRow()
        if r < 0:
            return
        values = [self.grid.GetCellValue(r, c) for c in range(self.grid.GetNumberCols())]
        self.grid.InsertRows(r + 1, 1)
        for c, v in enumerate(values):
            self.grid.SetCellValue(r + 1, c, v)

    def on_del_row(self, event):
        r = self.grid.GetGridCursorRow()
        if r >= 0 and self.grid.GetNumberRows():
            self.grid.DeleteRows(r, 1)

    def on_add_col(self, event):
        dlg = wx.TextEntryDialog(self, "New column (keyword) name:", "Add Column", "MFG_")
        dlg.SetWindowStyleFlag(dlg.GetWindowStyleFlag() | wx.STAY_ON_TOP)
        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetValue().strip()
            if name:
                insert_at = max(self.grid.GetNumberCols() - 1, 0)                                              #Keep CATPath last
                self.grid.InsertCols(insert_at, 1)
                self.grid.SetColLabelValue(insert_at, name)
        dlg.Destroy()

    #--- file ops ---
    def on_load(self, event):
        try:
            path = self._pick("Load catalog CSV", save=False)
            if not path:
                return
            self._flush_grid()
            read_tree_csv(path, self.tree)
            self.settings["last_csv"] = path
            self.on_family(None)
            self._info(f"Loaded rows from:\n{path}")
        except Exception as exc:
            show_error("loading the CSV", exc)

    def on_save(self, event):
        try:
            self._flush_grid()
            path = self._pick("Save catalog CSV", save=True, default="tooling_catalog.csv")
            if not path:
                return
            if not write_catalog_csv(path, self.tree):
                self._info("There are no rows to save.\n\nAdd at least one tool to a family first.")
                return
            self.settings["last_csv"] = path
            dropped = sum(1 for fams in self.tree.values() for data in fams.values()
                          for row in data["rows"] if len(row) > 1 and row[-1].strip())                         #CATPart paths the CSV cannot carry
            message = f"Saved catalog CSV:\n{path}"
            if dropped:
                message += (f"\n\nNote: {dropped} {DOC_COL} value(s) were not written. "
                            f"{DOC_COL} is not a CATIA keyword, so it is not part of the catalog CSV.")
            self._info(message)
        except Exception as exc:
            show_error("saving the CSV", exc)

    def on_build(self, event):
        try:
            self._flush_grid()
            out_path = self._pick("Save the .catalog to", save=True, default="tooling_catalog.catalog",
                                  wildcard="Catalog files (*.catalog)|*.catalog")
            if not out_path:
                return
            csv_path = os.path.join(tempfile.gettempdir(), "tooling_catalog_build.csv")                        #Input CSV (temp, not in user folder)
            if not write_catalog_csv(csv_path, self.tree):                                                     #CATIA batch format, not the app's own CSV
                self._info("There is nothing to build.")
                return
            if os.path.exists(out_path):
                os.remove(out_path)                                                                            #CATIA's own sample deletes an existing catalog first
            build_catalog_in_catia(self.caa, csv_path, out_path)
            self.settings["catalog_dir"] = os.path.dirname(out_path)
            if os.path.exists(out_path):
                self._info(f"Built catalog:\n{out_path}")
            else:
                self._info("CATIA did not create a .catalog from the data.\n\n"
                           f"The CSV sent to CATIA is here for inspection:\n{csv_path}")
        except Exception as exc:
            show_error("building the catalog", exc)

    #--- helpers ---
    def _pick(self, message, save=False, default="", wildcard="CSV files (*.csv)|*.csv"):
        style = (wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) if save else (wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        with wx.FileDialog(self, message, defaultDir=self.settings.get("csv_dir", ""), defaultFile=default,
                           wildcard=wildcard, style=style) as fd:
            if fd.ShowModal() != wx.ID_OK:
                return None
            path = fd.GetPath()
            self.settings["csv_dir"] = os.path.dirname(path)
            return path

    def _info(self, message):
        dlg = wx.MessageDialog(self, message, "Tooling Catalog", wx.OK | wx.ICON_INFORMATION | wx.STAY_ON_TOP)
        dlg.ShowModal()
        dlg.Destroy()
        with open(self.settings_file, "w") as f:
            json.dump(self.settings, f, indent=4)


if __name__ == "__main__":
    SETTINGS_DIR = os.path.join(os.environ['APPDATA'], 'pycatia_scripts', SCRIPT_NAME)
    SETTINGS_FILE = os.path.join(SETTINGS_DIR, 'user_settings.json')
    if not os.path.exists(SETTINGS_DIR):
        os.makedirs(SETTINGS_DIR)

    settings = {}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
        except Exception:
            settings = {}

    caa = catia()                                                                                              #Catia application instance
    app = wx.App(None)
    frame = CatalogEditor(caa, settings, SETTINGS_FILE)
    frame.Show()
    wx.CallAfter(_bring_to_front, frame)
    app.MainLoop()
