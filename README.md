A repository for OSS class project


## 개요
Doodle Jump 기반 종 스크롤 방식 게임 개발하기


## 설치 방법
Latest Release를 통해 Installer 다운로드 후 설치.

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

## 팀 구성
| 직책 | 이름 |
| 팀장 | 조연우 |
| 개발리드 | 정해원 |
| 문서담당 | 장여민 |
| 리뷰품질담당 | 김진우 |

## 기여 방법
[보러가기](CONTRIBUTING.md), [보러가기](LICENSE) 참조
