import win32com.client
import pythoncom
import os

def test():
    try:
        swApp = win32com.client.GetActiveObject("SldWorks.Application")
        print("Connected to SolidWorks.")
    except Exception as e:
        print(f"Could not connect to SolidWorks: {e}")
        return

    model = swApp.ActiveDoc
    if not model:
        print("No active document found.")
        return

    title = model.GetTitle()
    path = model.GetPathName()
    print(f"Active Doc Title: '{title}'")
    print(f"Active Doc Path: '{path}'")
    
    # Try closing using title
    print(f"Attempting to close using title: '{title}'")
    try:
        swApp.CloseDoc(title)
        print("CloseDoc call finished.")
    except Exception as e:
        print(f"CloseDoc failed: {e}")

if __name__ == "__main__":
    test()
