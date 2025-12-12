# Blender STL 자동 렌더링 도구 (Blender STL Auto-Renderer)

이 프로젝트는 STL 파일을 Blender로 자동으로 불러와서, 최적화된 조명과 재질을 적용한 후 고품질 렌더링 이미지를 생성하는 자동화 도구입니다.

## 주요 기능

*   **자동 임포트 및 변환**: STL 파일을 불러와 1/1000 스케일(mm -> m)로 변환하고 등각뷰 방향으로 회전합니다.
*   **부품 자동 그룹화**: 수많은 부품들을 분석하여 동일한 형상(나사, 롤러 등)을 자동으로 식별하고 하나의 오브젝트로 병합(Join)합니다.
*   **재질 자동 적용**:
    *   **니켈 도금 (Nickel Plated)**: 병합된 하드웨어 부품(나사 등)에 적용
    *   **블랙 아노다이징 (Black Anodized)**: 고유한 형상의 하우징 부품에 적용 (Cycles 최적화)
*   **자동 스무딩**: 각진 표면을 부드럽게 처리하면서 날카로운 모서리는 유지합니다 (Shade Smooth by Angle).
*   **멀티 뷰 렌더링**: 두 가지 시점(우측 전방, 좌측 후방)에서 등각투영(Orthographic) 뷰로 렌더링합니다.
*   **투명 배경 지원**: 배경이 있는 이미지와 투명한(Alpha) 이미지를 각각 저장합니다 (총 4장).
*   **GUI 지원**: 파일 탐색기와 옵션 선택이 가능한 간편한 실행기를 제공합니다.

## 시스템 요구 사항

*   **Windows OS**
*   **Blender 3.0 이상** (권장 5.0, `blender.exe` 경로 설정 필요)
*   **Python 3.x** (`tkinter` 포함)

## 설치 및 설정

1. `main.py` 파일 내의 `import addon_utils` 등 Blender API 관련 코드는 Blender 내부 Python에서 실행됩니다.
2. `gui_launcher.py` 내의 `blender_exe` 변수에 본인의 Blender 실행 파일 경로가 정확한지 확인하십시오.
   * 기본값: `C:\Users\hmpublic\scoop\apps\Blender\current\blender.exe`

## 사용 방법

### 1. GUI 실행 (권장)
가장 간편한 방법입니다.

1. **`run_gui.bat`** 파일을 더블 클릭하여 실행합니다.
2. 실행 창에서 원하는 **해상도(Resolution)** 옵션을 선택합니다.
    * **Low**: 800x600
    * **Mid**: 1024x768 (기본)
    * **High**: 2048x1536
3. **"Select File & Render"** 버튼을 클릭합니다.
4. 렌더링할 **STL 파일**을 선택합니다.
5. 자동으로 Blender가 백그라운드에서 실행되며 렌더링이 진행됩니다. 하단 상태 메시지를 확인하세요.

### 2. 배치 파일 실행
특정 파일(`AA200_ASSY.STL`)이 고정되어 있다면 바로 실행 가능합니다.

1. **`run_blender.bat`** 파일을 실행합니다.
2. 스크립트에 지정된 기본 경로(`../ex/AA200_ASSY.STL`)의 파일을 읽어 렌더링합니다.

## 결과물

선택한 STL 파일이 있는 폴더에 다음과 같은 이름으로 4개의 PNG 파일이 생성됩니다.
(예: `MyModel.STL` 선택 시)

1. `MyModel_Camera_Front.png` (전방 뷰, 배경 있음)
2. `MyModel_Camera_Front_transparent.png` (전방 뷰, 투명 배경)
3. `MyModel_Camera_Back.png` (후방 뷰, 배경 있음)
4. `MyModel_Camera_Back_transparent.png` (후방 뷰, 투명 배경)

## 문제 해결

* **Blender not found**: `gui_launcher.py` 파일 12번째 줄의 `blender_exe` 경로를 자신의 컴퓨터 환경에 맞게 수정하세요.
* **검은 화면/흰 화면**: 렌더링 된 이미지가 너무 어둡거나 밝다면 `main.py`의 조명(Energy) 설정을 조절해야 할 수 있습니다. 현재는 검은색 금속에 최적화되어 있습니다.
