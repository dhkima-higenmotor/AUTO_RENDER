# Auto Render Tool

이 프로그램은 SolidWorks 어셈블리 파일을 Blender 씬으로 자동 변환해주는 도구입니다. 복잡한 설정 없이 클릭 몇 번으로 최적화된 조명, 카메라, 재질이 적용된 렌더링 준비 파일을 생성할 수 있습니다.

## 사전 요구 사항 (Prerequisites)

이 도구를 사용하기 위해서는 다음 프로그램들이 설치되어 있어야 합니다.

1.  **SolidWorks**: SLDASM 파일을 열고 처리하기 위해 필요합니다.
2.  **Blender (5.0 이상)**: 3D 렌더링을 수행하기 위해 필요합니다.
    *   `blender_exe.txt` 파일에 Blender 실행 파일(`blender.exe`)의 경로가 올바르게 지정되어 있어야 합니다.
3.  **uv**: 빠르고 효율적인 Python 패키지 관리를 위해 사용됩니다. (Python 환경 자동 구성)

## 사용 방법

이 프로그램은 두 가지 실행 방식을 제공합니다. 취향에 맞는 방법을 선택하세요.

### 1. GUI 모드 (추천)
직관적인 윈도우 창에서 버튼을 클릭하며 단계별로 진행합니다.

1.  **`AUTO_RENDER_GUI.bat`** 파일을 실행합니다.
2.  **`Choose SLDASM`**: 작업할 SolidWorks 어셈블리 파일을 선택합니다.
3.  **`Make STL`**: SolidWorks에서 모델을 내보냅니다.
4.  **`Make BLEND`**: Blender 씬을 생성합니다.
5.  **`RENDER`**: 최종 이미지를 렌더링합니다. (해상도 조절 가능)

### 2. TUI 모드 (빠른 실행)
파일을 드래그하여 한 번에 모든 과정을 자동으로 처리합니다.

*   **드래그 앤 드롭**: `.SLDASM` 파일을 **`AUTO_RENDER_TUI.bat`** 아이콘 위로 드래그합니다.
    *   자동 순서: STL 변환 -> Blender 생성 -> 렌더링(기본 1024x768)
*   **명령줄 실행**: `AUTO_RENDER_TUI.bat [파일경로] --res [해상도]`

---

## 독립 실행 도구 (Standalone Tools)

특정 기능만 따로 수행하고 싶을 때 사용하는 배치 파일들입니다.

*   **`blender2png.bat`**: 
    *   기존에 생성된 `.blend` 파일을 다시 렌더링할 때 사용합니다.
    *   파일을 드래그하거나, 명령줄에서 `--res 1920x1080` 옵션과 함께 실행할 수 있습니다.
    *   특징: 폴더 내의 모든 카메라 뷰를 렌더링합니다.

*   **`sw2stl.bat`**:
    *   SolidWorks 어셈블리를 STL 및 재질 데이터로 변환만 수행합니다.
    *   사용법: `.SLDASM` 파일을 드래그 앤 드롭.

*   **`stl2blender.bat`**:
    *   생성된 `__STL` 폴더를 기반으로 Blender 씬(`__BLENDER`)을 생성만 수행합니다.
    *   사용법: `__STL` 폴더를 드래그 앤 드롭.

## 주요 기능 요약

*   **Automatic Import**: STL 파일 자동 임포트 및 정렬
*   **Auto Smooth**: 표면 자동 부드러움 처리
*   **Smart Materials**: SolidWorks 재질 색상 자동 계승
*   **Pro Studio Setup**: 2개의 Isometric 카메라 및 3점 조명 자동 배치
*   **Multi-Camera Render**: 씬에 존재하는 모든 카메라 자동 렌더링
*   **Transparent Output**: 배경 투명화(RGBA) 지원
