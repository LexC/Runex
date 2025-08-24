""" README
This script pair allows you to extract and rebuild VBA code modules from an
Excel `.xlsm` file for version control purposes. It supports exporting all
VBA modules and later reconstructing the `.xlsm` file by injecting them back.
"""

#%% === Libraries ===

import os
import glob
import win32com.client

#%% === General Tools ===

# ---------- Variables ----------
def global_variables():
    """
    Defines global settings for file paths used in VBA module handling.

    Returns:
        dict: Dictionary containing the Excel macro file and folder paths.
    """
    return {
        "input_xlsm": "source/source_file.xlsm",
        "output_xlsm": "dist/rebuilt_file.xlsm",
        "vba_folder": "vba_modules"
    }

VAR = global_variables()

#%% === Functions ===

# ---------- VBA Export Utilities ----------

# -----> export_vba_modules
def export_vba_modules():
    """
    Exports all VBA modules from the specified Excel `.xlsm` file
    into individual text files in the `vba_modules` folder.
    """
    excel = win32com.client.Dispatch("Excel.Application")
    excel.Visible = False
    wb = excel.Workbooks.Open(os.path.abspath(VAR["input_xlsm"]))
    vba_project = wb.VBProject

    os.makedirs(VAR["vba_folder"], exist_ok=True)

    for component in vba_project.VBComponents:
        name = component.Name
        file_type = component.Type  # 1=Module, 2=Class, 3=Form, 100=ThisWorkbook, 101=Worksheet

        ext = {1: "bas", 2: "cls", 3: "frm"}.get(file_type, "cls")
        path = os.path.join(VAR["vba_folder"], f"{name}.{ext}")
        component.Export(path)

    wb.Close(False)
    excel.Quit()

# -----> import_vba_modules
def import_vba_modules():
    """
    Rebuilds an Excel file by injecting all code modules found in the
    `vba_modules` folder into a copy of the base Excel file.
    """
    excel = win32com.client.Dispatch("Excel.Application")
    excel.Visible = False
    wb = excel.Workbooks.Open(os.path.abspath(VAR["input_xlsm"]))
    vba_project = wb.VBProject

    for component in list(vba_project.VBComponents):
        if component.Type in [1, 2, 3] and component.Name not in ("ThisWorkbook",):
            vba_project.VBComponents.Remove(component)

    for filepath in glob.glob(os.path.join(VAR["vba_folder"], "*.*")):
        vba_project.VBComponents.Import(os.path.abspath(filepath))

    wb.SaveAs(os.path.abspath(VAR["output_xlsm"]), FileFormat=52)
    wb.Close()
    excel.Quit()

#%% === Show Time ===

def main():
    """
    Main function to demonstrate VBA export and import utilities.
    """
    print("Exporting VBA modules...")
    export_vba_modules()
    print("Modules exported.")

    print("Rebuilding .xlsm file...")
    import_vba_modules()
    print("Rebuild complete.")

if __name__ == "__main__":
    main()
