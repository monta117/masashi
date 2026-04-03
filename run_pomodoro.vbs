Set ws = CreateObject("WScript.Shell")
ws.Run "pythonw """ & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\pomodoro_mini.py""", 0, False
