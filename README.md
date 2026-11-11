A repository for OSS class project


## 개요
Doodle Jump 기반 종 스크롤 방식 게임 개발하기


## 설치 및 실행 방법 (Windows)

1. [최신 릴리스](https://github.com/Nimp04/do-it-codex/releases/latest)에서
   **Assets → JumpOverflow-Setup.exe**를 다운로드합니다.
2. 설치 파일을 실행하고 설치 위치를 선택한 뒤 설치를 완료합니다.
   기본 위치는 현재 사용자의 `%LOCALAPPDATA%\Programs\JumpOverflow`입니다.
3. 설치 완료 화면에서 **바탕화면 바로가기 만들기**, **설치 폴더 열기**를
   각각 선택할 수 있습니다. 두 옵션은 기본적으로 선택되어 있으며,
   원하지 않는 옵션의 체크를 해제한 뒤 **마침**을 누르면 적용됩니다.
4. Windows 시작 메뉴에서 **JumpOverflow**를 검색하거나, 생성한 바탕화면 바로가기로 실행합니다.
   설치 폴더의 `JumpOverflow.exe`를 직접 실행해도 됩니다.
5. 게임 화면에서 **시작**을 누릅니다. **← / →** 또는 **A / D**로 좌우 이동하며,
   발판에 착지하면 자동으로 점프합니다.

Python이나 NSIS를 별도로 설치할 필요는 없습니다.
게임을 종료하려면 창의 닫기 버튼을 누르세요.
제거하려면 Windows 설정의 앱 목록에서 **JumpOverflow**를 선택해 제거합니다.

## MVP 시연

중간발표용 영상은 GitHub Releases의 인스톨러로 설치하는 과정부터 실제 플레이까지
보여줄 예정입니다. 촬영 기준 버전은 [v0.1.1](https://github.com/Nimp04/do-it-codex/releases/tag/v0.1.1)이며,
설치 방법은 위의 **설치 및 실행 방법 (Windows)**을 따릅니다.

| 순서 | 시연 내용 |
|---|---|
| 1 | 릴리스 페이지에서 `JumpOverflow-Setup.exe` 다운로드 |
| 2 | 인스톨러 실행, 설치 위치 선택, 설치 완료 화면의 바로가기·폴더 열기 옵션 확인 |
| 3 | 설치한 게임 실행 후 대기 화면에서 **시작** 선택 |
| 4 | **← / →** 또는 **A / D** 이동과 발판 착지 시 자동 점프 시연 |
| 5 | 상승에 따른 카메라 추적, 배경 스크롤, 발판 추가 생성과 점수 변화 확인 |
| 6 | 추락 후 게임 오버, **다시하기**, **홈으로** 동작 시연 |

영상은 약 1분으로 편집하며, 다운로드·설치 대기 구간은 배속하거나 줄입니다.
현재는 촬영 전이며, 촬영 후 영상 링크와 실제 확인 결과를 추가할 예정입니다.

## 소스에서 실행 (개발용)

Python 3.12 이상을 설치하고 저장소를 내려받은 뒤, 저장소 루트에서 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## Windows EXE 빌드
프로젝트 가상환경을 활성화한 Windows에서 저장소 루트를 기준으로 실행합니다.

```powershell
python -m pip install -r requirements-build.txt
python -m PyInstaller --onefile --windowed --name JumpOverflow --specpath build main.py
```

`main.py`가 사용하는 프로젝트 모듈과 Python, pygame-ce를 묶어
`dist/JumpOverflow.exe`를 생성합니다. 실행 시 콘솔 창은 표시하지 않습니다.
NSIS 설치파일을 만들 때 이 EXE를 포함합니다.
현재 한글 표시는 Windows의 맑은 고딕 글꼴을 사용합니다.

## NSIS 설치 파일 빌드

NSIS 3을 설치하고 위의 EXE 빌드를 마친 뒤, 저장소 루트에서 실행합니다.
NSIS 실행 파일은 PATH 또는 설치 레지스트리에서 찾으므로 개인 PC 경로를 적지 않습니다.

```powershell
$ErrorActionPreference = 'Stop'
$nsisCompiler = Get-Command makensis.exe -ErrorAction SilentlyContinue
if ($nsisCompiler) {
    $nsisCompilerPath = $nsisCompiler.Source
} else {
    $nsisInstallPath = @(
        'HKLM:\SOFTWARE\WOW6432Node\NSIS'
        'HKLM:\SOFTWARE\NSIS'
        'HKCU:\SOFTWARE\NSIS'
    ) | ForEach-Object {
        (Get-ItemProperty -LiteralPath $_ -ErrorAction SilentlyContinue).'(default)'
    } | Where-Object { $_ -and (Test-Path -LiteralPath (Join-Path $_ 'makensis.exe')) } | Select-Object -First 1
    if (-not $nsisInstallPath) { throw 'NSIS 3을 설치하거나 makensis.exe를 PATH에 추가하세요.' }
    $nsisCompilerPath = Join-Path $nsisInstallPath 'makensis.exe'
}
& $nsisCompilerPath /INPUTCHARSET UTF8 /WX .\installer.nsi
if ($LASTEXITCODE -ne 0) { throw 'NSIS 설치 파일 빌드에 실패했습니다.' }
```

결과는 `dist/JumpOverflow-Setup.exe`입니다. `installer.nsi`의 파일 경로는
스크립트 폴더 기준 상대경로이며, 기본 설치 위치는 설치하는 사용자의
`$LOCALAPPDATA\Programs\JumpOverflow`입니다. 시작 메뉴 바로가기와 앱 제거를 지원하며,
완료 화면에서 바탕화면 바로가기 생성과 설치 폴더 열기를 선택할 수 있습니다.
`build/`, `dist/`는 Git에서 제외되므로 소스와 `installer.nsi`만 커밋하고,
설치 EXE는 GitHub Releases에 첨부합니다.

## 팀 구성
| 직책 | 이름 |
| 팀장 | 조연우 |
| 개발리드 | 정해원 |
| 문서담당 | 장여민 |
| 리뷰품질담당 | 김진우 |

## 기여 방법
[보러가기](CONTRIBUTING.md), [보러가기](LICENSE) 참조
