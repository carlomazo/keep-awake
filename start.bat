@echo off
if not DEFINED IS_MINIMIZED set IS_MINIMIZED=1 && start "" /min "%~f0" %* && exit
pythonw "%~dp0keep_awake.py"
