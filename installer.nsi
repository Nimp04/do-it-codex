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
!define MUI_FINISHPAGE_TEXT "설치 위치:$\r$\n$INSTDIR$\r$\n$\r$\n원하는 옵션을 선택한 뒤 마침을 누르세요."
!define MUI_FINISHPAGE_TEXT_LARGE
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_TEXT "바탕화면 바로가기 만들기"
!define MUI_FINISHPAGE_RUN_FUNCTION CreateDesktopShortcut
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR"
!define MUI_FINISHPAGE_SHOWREADME_TEXT "설치 폴더 열기"
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Korean"

Function CreateDesktopShortcut
    SetShellVarContext current
    ClearErrors
    CreateShortcut "$DESKTOP\JumpOverflow.lnk" "$INSTDIR\JumpOverflow.exe"
    IfErrors 0 +2
        MessageBox MB_OK|MB_ICONEXCLAMATION "바탕화면 바로가기를 만들지 못했습니다. 시작 메뉴에서 JumpOverflow를 실행하세요."
FunctionEnd

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
    Delete "$DESKTOP\JumpOverflow.lnk"
    Delete "$SMPROGRAMS\JumpOverflow.lnk"
    Delete "$INSTDIR\JumpOverflow.exe"
    Delete "$INSTDIR\Uninstall.exe"
    RMDir "$INSTDIR"
    DeleteRegKey HKCU "${UNINSTALL_KEY}"
SectionEnd
