Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Get the folder where this .vbs lives
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Run pythonw (no console window) with timer.pyw
WshShell.Run "pythonw """ & scriptDir & "\timer.pyw""", 0, False
