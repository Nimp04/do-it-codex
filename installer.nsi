Unicode true
!include "MUI2.nsh"

!cd "${__FILEDIR__}"
!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\JumpOverflow"

Name "JumpOverflow"
OutFile "dist\JumpOverflow-Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\JumpOverflow"
InstallDirRegKey HKCU "${UNINSTALL_KEY}" "InstallLocation"
RequestExecutionLevel user

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Korean"

Section "Install"
    SetShellVarContext current
    SetOutPath "$INSTDIR"
    File "dist\JumpOverflow.exe"

    ClearErrors
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    IfErrors 0 +2
        Abort "제거 프로그램을 만들지 못했습니다."

    CreateShortcut "$SMPROGRAMS\JumpOverflow.lnk" "$INSTDIR\JumpOverflow.exe"
    WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayName" "JumpOverflow"
    WriteRegStr HKCU "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKCU "${UNINSTALL_KEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
    WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoModify" 1
    WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoRepair" 1
SectionEnd

Section "Uninstall"
    SetShellVarContext current
    Delete "$SMPROGRAMS\JumpOverflow.lnk"
    Delete "$INSTDIR\JumpOverflow.exe"
    Delete "$INSTDIR\Uninstall.exe"
    RMDir "$INSTDIR"
    DeleteRegKey HKCU "${UNINSTALL_KEY}"
SectionEnd
