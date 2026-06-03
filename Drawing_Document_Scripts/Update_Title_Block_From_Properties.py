'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Update_Title_Block_From_Properties.py
    Version:        1.2
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Update title block text items from the linked model's properties.
    Author:         Kai-Uwe Rathjen
    Date:           21.05.26
    Description:    This script reads all text items from the background view (title block frame)
                    of the active drawing sheet and the properties of the linked CATPart or CATProduct.
                    A dialog lets the user map each title block text to a model property. Confirmed
                    mappings are applied immediately. Only the active sheet is processed.
                    Note: The script reads linked model properties from the first generative view
                    found in the sheet. If no generative link exists, properties are read from the
                    first open CATPart or CATProduct found in CATIA.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    wxPython
                    Catia V5 running with an open CATDrawing document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         21.05.26 1.1: Replaced property dropdown with editable ComboBox to allow custom text input.
                              Heading labels (texts ending with ':') are now excluded — only value fields are shown.
                    03.06.26 1.2: Fix F401: remove unused Path import.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.drafting_interfaces.drawing_document import DrawingDocument
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
    u32.SetWindowLongW(hwnd, -20, u32.GetWindowLongW(hwnd, -20) | 0x0008)
    u32.BringWindowToTop(hwnd)
    u32.SetForegroundWindow(hwnd)
    if fg_tid != our_tid:
        u32.AttachThreadInput(fg_tid, our_tid, False)


def _get_texts_from_view(view_com):
    texts = {}
    try:
        texts_col = view_com.Texts
        for i in range(texts_col.Count):
            t = texts_col.Item(i + 1)
            try:
                texts[t.Name] = t.Text
            except Exception:
                pass
    except Exception:
        pass
    return texts


def _get_model_properties(caa):
    props = {}

    for doc in caa.documents:
        doc_name = doc.name
        if not (doc_name.endswith('.CATPart') or doc_name.endswith('.CATProduct')):
            continue
        try:
            prod_com = doc.com_object.Product
            for attr, label in [
                ("PartNumber",   "Part Number"),
                ("Revision",     "Revision"),
                ("Definition",   "Definition"),
                ("Nomenclature", "Nomenclature"),
                ("DescriptionRef", "Description"),
            ]:
                try:
                    val = getattr(prod_com, attr)
                    if val:
                        props[label] = str(val)
                except Exception:
                    pass

            try:
                user_props = prod_com.UserRefProperties
                for i in range(user_props.Count):
                    p = user_props.Item(i + 1)
                    try:
                        props[p.Name] = str(p.ValueAsString())
                    except Exception:
                        pass
            except Exception:
                pass

            if props:
                break
        except Exception:
            continue

    return props


class MappingDialog(wx.Dialog):
    def __init__(self, parent, texts, props):
        super().__init__(parent, title="Map Title Block Texts to Properties",
                         size=(700, 500), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.STAY_ON_TOP)

        self.texts = texts
        self.props = props

        prop_choices = ["(leave unchanged)"] + sorted(props.keys())
        text_names   = sorted(texts.keys())

        panel = wx.Panel(self)
        vbox  = wx.BoxSizer(wx.VERTICAL)

        info = wx.StaticText(panel, label=f"Found {len(texts)} text item(s) and {len(props)} model property(ies).\n"
                                          "Select a property from the dropdown, or type any custom text directly.")
        vbox.Add(info, flag=wx.ALL, border=10)

        scroll = wx.ScrolledWindow(panel, style=wx.VSCROLL)
        scroll.SetScrollRate(0, 10)
        sgrid = wx.FlexGridSizer(len(text_names), 3, 6, 8)
        sgrid.AddGrowableCol(1, 1)
        sgrid.AddGrowableCol(2, 2)

        self.combos = {}
        for name in text_names:
            current_val = texts[name]
            sgrid.Add(wx.StaticText(scroll, label=name + ":"), flag=wx.ALIGN_CENTER_VERTICAL)
            sgrid.Add(wx.StaticText(scroll, label=f'"{current_val[:40]}"'), flag=wx.ALIGN_CENTER_VERTICAL)
            combo = wx.ComboBox(scroll, choices=prop_choices, style=wx.CB_DROPDOWN)
            combo.SetSelection(0)
            sgrid.Add(combo, flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
            self.combos[name] = combo

        scroll.SetSizer(sgrid)
        vbox.Add(scroll, proportion=1, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=10)
        panel.SetSizer(vbox)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(panel, proportion=1, flag=wx.EXPAND)
        main_sizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), flag=wx.ALIGN_CENTER | wx.ALL, border=10)
        self.SetSizer(main_sizer)

    def get_mapping(self):
        result = {}
        for name, combo in self.combos.items():
            val = combo.GetValue().strip()
            if not val or val == "(leave unchanged)":
                continue
            if val in self.props:
                result[name] = self.props[val]                                                                       #Property label selected — use its value
            else:
                result[name] = val                                                                                   #Custom text typed directly
        return result


if __name__ == "__main__":
    caa = catia()                                                                                                   #Catia application instance
    active_doc = caa.active_document                                                                               #Current open document

    try:
        drawing_doc = DrawingDocument(active_doc.com_object)
        _ = drawing_doc.drawing_root
    except Exception:
        print("A CATDrawing document must be the active document.")
        exit()

    sheets = drawing_doc.drawing_root.sheets
    active_sheet_com = None
    try:
        active_sheet_com = drawing_doc.drawing_root.com_object.Sheets.ActiveSheet                                  #Get active sheet via COM
    except Exception:
        if sheets.count > 0:
            active_sheet_com = sheets.item(1).com_object

    if active_sheet_com is None:
        print("Could not access the active drawing sheet.")
        exit()

    all_texts = {}

    try:
        bg_view = active_sheet_com.GetBackgroundView()                                                             #Background view (title block frame)
        all_texts.update(_get_texts_from_view(bg_view))
    except Exception:
        pass

    try:
        views_com = active_sheet_com.Views
        for vi in range(views_com.Count):
            view_com = views_com.Item(vi + 1)
            all_texts.update(_get_texts_from_view(view_com))
    except Exception as e:
        print(f"  Warning: Could not read views ({e})")

    if not all_texts:
        print("No text items found in the active drawing sheet.")
        exit()

    #Exclude heading labels (e.g. "DRAWN BY:", "TITLE:") — only offer the named value fields
    value_texts = {name: val for name, val in all_texts.items() if not val.strip().endswith(":")}

    if not value_texts:
        print("No value fields found in the active drawing sheet.")
        exit()

    model_props = _get_model_properties(caa)

    if not model_props:
        print("No linked CATPart or CATProduct found with readable properties.")
        exit()

    print(f"\n Found {len(value_texts)} value field(s) and {len(model_props)} model property(ies)\n")

    app = wx.App(None)
    dlg = MappingDialog(None, value_texts, model_props)
    wx.CallAfter(_bring_to_front, dlg)

    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        print("Cancelled")
        exit()

    mapping = dlg.get_mapping()
    dlg.Destroy()

    if not mapping:
        print("No mappings selected — nothing to update.")
        exit()

    updated = 0
    failed  = 0

    for text_name, new_value in mapping.items():                                                                   #Apply the text updates
        try:
            found = False
            try:
                bg_view = active_sheet_com.GetBackgroundView()
                texts_com = bg_view.Texts
                for ti in range(texts_com.Count):
                    t = texts_com.Item(ti + 1)
                    if t.Name == text_name:
                        t.Text = new_value
                        found = True
                        break
            except Exception:
                pass

            if not found:
                views_com = active_sheet_com.Views
                for vi in range(views_com.Count):
                    view_com = views_com.Item(vi + 1)
                    try:
                        texts_com = view_com.Texts
                        for ti in range(texts_com.Count):
                            t = texts_com.Item(ti + 1)
                            if t.Name == text_name:
                                t.Text = new_value
                                found = True
                                break
                    except Exception:
                        pass
                    if found:
                        break

            if found:
                print(f"  Updated: '{text_name}' -> '{new_value}'")
                updated += 1
            else:
                print(f"  Not found: '{text_name}' (skipped)")
                failed += 1

        except Exception as e:
            print(f"  Failed to update '{text_name}': {e}")
            failed += 1

    print(f"\n\n Completed - {updated} updated, {failed} skipped/failed\n\n")
