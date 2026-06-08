# Auto Render Tool (자동 렌더링 도구)

이 프로그램은 SolidWorks 어셈블리 파일(`*.SLDASM`)을 Blender 씬으로 자동 변환하고, 최적의 조감도 뷰포트에서 고품질 제품 이미지를 자동으로 렌더링해주는 도구입니다.

부품의 이름 키워드(예: Screw, Bolt, Bearing, Housing 등)에 따라 적절한 재질(Brushed Nickel, Stainless Steel, Copper, Aluminium, Pearl Black Plastic 등)을 자동으로 매핑해주며, 최적의 3점 조명과 4방향 Isometric 카메라를 자동으로 배치해줍니다.

특히 모든 GUI와 팝업은 윈도우 **시스템 기본 폰트**를 적용하여 선명하고 또렷하게 표시되며, 고해상도(DPI) 배율을 완벽히 지원합니다.

![](AUTO_RENDER_01.png)


---

## ✨ 핵심 기능 요약

* **4방향 Isometric 카메라 및 스마트 클리핑(Clip) 지원**: 피사체를 비스듬히 내려다보는 4가지 조감도 방향의 카메라(`Camera_ISO_FR`, `Camera_ISO_FL`, `Camera_ISO_BR`, `Camera_ISO_BL`)를 자동 배치합니다. **가져온 부품들의 크기(최대 치수)와 카메라 거리를 계산하여 카메라 및 뷰포트의 Clip Start/End 임계값을 동적으로 설정하므로, 대형 모델이나 분해 애니메이션 시 화면에서 잘리는 현상이 없고, 생성된 blend 파일을 열었을 때 자동으로 정사뷰(Orthographic) 및 Isometric FR 카메라 화면으로 최적 핏(Fit)되어 즉시 확인 가능합니다.**
* **자동 쉐이드 자동 스무스(Shade Auto Smooth) 및 쉐이드 플랫(Shade Flat) 부여**: 가져온 모든 3D 부품(Mesh)에 대해 Blender 버전에 맞게 자동으로 "쉐이드 자동 스무스" 처리를 적용합니다. **단, "Green Plastic" 재질이 적용된 회로 기판 등의 부품은 정교한 렌더링 품질을 보장하기 위해 자동으로 "쉐이드 플랫(Shade Flat)"을 부여합니다.**
* **이름 기반 스마트 재질 매핑**: 하드코딩된 색상 정보 대신 부품명을 기반으로 질감과 반사율이 가미된 정밀한 스튜디오 금속/플라스틱 재질을 자동 부여합니다.
* **프로 스튜디오 조명**: 피사체의 크기에 알맞은 광량(Energy)과 크기를 가진 3점 Area 조명(Key, Fill, Rim)을 카메라 앵글에 맞춰 자동 생성합니다.
* **Cycles GPU 고품질 렌더링 및 디노이즈**: Cycles 렌더 엔진 및 GPU 연산을 활용하며, 뷰포트 최대 64 샘플 및 렌더 최대 512 샘플링과 디노이즈(Denoise)를 기본 적용해 깨끗하고 부드러운 고품질 이미지를 빠르게 얻을 수 있습니다.
* **BlenderKit HDRI 환경 조명 및 배경 투명화 (RGBA)**: BlenderKit에서 제공하는 무료 Office HDRI 환경 텍스처를 배경 조명으로 자동 매핑하여 피사체에 더욱 사실적이고 입체적인 반사광과 음영을 제공합니다. 동시에 최종 렌더링 필름은 투명하게 처리(RGBA)하여 배경이 투명하게 제거된 고품질 제품 이미지를 즉시 추출할 수 있습니다.


---

## 🛠️ 사전 요구 사항 (Prerequisites)

이 도구를 실행하기 위해 다음 프로그램들이 Windows 환경에 설치되어 있어야 합니다.

1. **SolidWorks**: 어셈블리 파일을 열고 STL을 내보내기 위해 설치되어 있어야 합니다.
2. **Blender (5.0 이상 권장)**: 3D 씬 구성 및 렌더링을 위해 필요합니다.
   * 이 폴더의 `config.json` 파일에 Blender 실행 파일(`blender.exe`)의 전체 경로(`blender_exe`) 및 각종 렌더링/분해 설정값을 설정할 수 있습니다.
3. **uv**: 빠르고 효율적인 Python 패키지 실행 관리자입니다.
   * `uv`가 내부 스크립트 실행 환경을 자동으로 관리해 줍니다.

> [!TIP]
> **추천 설치 방법 (Scoop 이용 시):**
> ```bash
> scoop install uv blender
> ```
> 이 폴더에 `config.json` 파일이 없더라도 기본적으로 `config.json.template`을 읽어 동작하므로 별도로 파일을 복사할 필요가 없습니다. 프로그램 실행 후 우측 하단의 `CONFIG` 버튼을 눌러 설정을 편집하고 저장(`Save`)하면 `config.json` 파일이 자동으로 생성됩니다. 각 설정 항목의 의미와 지정 가능한 구체적인 값들은 아래 **설정 파일 상세 설명 (config.json)** 단락을 참고하여 설정해 주십시오.

* Solidworks 셋팅은 아래 이미지 참조

![](AUTO_RENDER_02.png)

---

## ⚙️ 설정 파일 상세 설명 (config.json)

프로그램 실행 폴더 내의 `config.json` 파일을 통해 다양한 설정을 조정할 수 있습니다. 각 설정 항목의 상세 설명 및 가능한 값은 다음과 같습니다:

### 1. 기본 및 렌더링 설정
* **`blender_exe`**: 설치된 Blender 실행 파일(`blender.exe`)의 전체 경로 또는 명령어 이름 (기본값: `"blender"`)
* **`render_samples`**: 최종 이미지 생성 시 Cycles 렌더 엔진의 최대 샘플 수 (기본값: `512`)
* **`viewport_samples`**: 블렌더 뷰포트 내에서의 Cycles 렌더 최대 샘플 수 (기본값: `64`)
* **`use_denoising`**: 최종 렌더링 결과물에 디노이저(Denoising)를 적용하여 노이즈를 제어할지 여부
  * `true`: 디노이즈 활성화 (기본값)
  * `false`: 디노이즈 비활성화

### 2. 분해 애니메이션 설정 (EXPLODE)
* **`explode_axis`**: 분해 애니메이션 시 부품이 흩어지는 기준 축
  * `"X"`: X축 방향
  * `"Y"`: Y축 방향 (기본값)
  * `"Z"`: Z축 방향
* **`explode_dir_mode`**: 분해 애니메이션 시 부품이 흩어지는 방향 모드
  * `"POS"`: 양(+)의 방향으로 이동 (기본값)
  * `"NEG"`: 음(-)의 방향으로 이동
* **`explode_duration`**: 분해 애니메이션 동영상의 총 재생 시간 (초 단위, 기본값: `20`)

### 3. 해상도 및 배율 설정
* **`resolution_x`**: 최종 렌더링 이미지의 가로 크기 (픽셀 단위, 기본값: `800`)
* **`resolution_y`**: 최종 렌더링 이미지의 세로 크기 (픽셀 단위, 기본값: `600`)
* **`resolution_percentage`**: 최종 렌더링 시 해상도 적용 비율 (기본값: `200` - 즉, 원래 해상도 기준 200% 크기로 렌더링)
* **`resolution_percentage_explode`**: EXPLODE(분해) 애니메이션 렌더링 시 해상도 적용 비율 (기본값: `100` - 즉, 원래 해상도 크기 100%로 렌더링)

### 4. 부품 이름 기반 재질(Material) 매핑 키워드 설정
부품 파일명(소문자 변환 기준)에 아래 키워드가 포함되어 있으면 해당하는 BlenderKit/절차적 재질이 자동으로 부여됩니다. 키워드는 쉼표(`,`)로 구분하여 여러 개를 지정할 수 있으며, 두 개 이상의 키워드가 모두 충족되어야 하는 경우는 덧셈 기호(`+`)를 사용하여 지정할 수 있습니다.

* **`keywords_green_plastic`**: 단자, 커넥터, PCB 기판 등에 적용되는 **Green Plastic** 재질 키워드
* **`keywords_brass`**: 지지대 등에 적용되는 **Brass** (황동) 재질 키워드
* **`keywords_brushed_nickel`**: 볼트, 나사 등에 적용되는 **Brushed Nickel** 재질 키워드
* **`keywords_stainless_steel`**: 베어링 등에 적용되는 **Stainless Steel** 재질 키워드
* **`keywords_copper`**: 구리 코일 부품 등에 적용되는 **Copper** 재질 키워드
* **`keywords_carbon_steel`**: 코어 부품 등에 적용되는 **Carbon Steel** 재질 키워드
* **`keywords_pearl_black_plastic`**: 하우징, 케이스 등 제품 외관 부품에 적용되는 **Pearl Black Plastic** 재질 키워드

> [!NOTE]
> **조합 키워드(`+`) 사용 예시:**
> - `stator+coil`로 설정된 경우, 부품명에 `stator`와 `coil` 단어가 **모두** 들어가 있을 때만 구리 재질이 부여됩니다.
> - 일반 단일 단어(예: `bearing`)로 설정된 경우, 단어가 부품명의 일부로 포함되어 있으면 매핑이 적용됩니다.

---

## 🚀 사용 방법

`AUTO_RENDER_GUI.bat`를 사용하여 마우스 클릭만으로 [SolidWorks ➡️ STL ➡️ Blender ➡️ 렌더링] 전체 단계를 제어할 수 있습니다.


#### **Step 1: 프로그램 실행**
* `AUTO_RENDER_GUI.bat` 파일을 더블 클릭하여 통합 GUI 창을 띄웁니다.
* > [!TIP]
  > **환경설정 편집 (`CONFIG`)**: GUI 우측 하단 `HELP` 버튼 왼쪽에 위치한 `CONFIG` 버튼을 누르면 팝업창에서 `config.json` 파일의 설정을 트리 형태로 간편하게 편집할 수 있습니다. 각 항목의 값을 더블클릭하여 편집을 수행하고 `Save` 버튼을 눌러 저장합니다.

#### **Step 2: SolidWorks 파일 선택**
* `Choose SLDASM` 버튼을 클릭하여 변환하고자 하는 SolidWorks 어셈블리 파일(`.SLDASM`)을 선택합니다.
* *선택한 어셈블리에 여러 설정(Configuration)이 존재하는 경우, 설정 선택 팝업창이 나타나며 원하는 구성을 편리하게 고를 수 있습니다.*

#### **Step 3: STL 부품 파일 추출 (`Make STL`)**
* `Make STL` 버튼을 누르면 솔리드웍스가 실행되어 개별 부품 단위의 STL 파일들을 내보냅니다.
* > [!IMPORTANT]
  > **억제 부품 자동 필터링**: 현재 선택된 설정(Configuration)에서 **억제된(Suppressed) 부품들은 자동으로 감지되어 추출에서 제외**되며, 오직 활성화된 부품들만 내보냅니다. 원본 파일은 수정 없이 안전하게 닫힙니다.
* 완료 시 어셈블리 파일과 동일한 경로에 `[어셈블리명]__STL` 폴더가 생성됩니다.

#### **Step 4: 블렌더 씬 구성, BlenderKit 재질 및 HDRI 매핑 (`Make BLEND`)**
* `Make BLEND` 버튼을 누릅니다. 추출된 STL 파일들을 모아 자동으로 3D 씬을 재구성합니다.
* > [!TIP]
  > **BlenderKit 기반 스마트 재질 매핑**: 부품 파일명에 포함된 단어를 스캔하여 **BlenderKit**의 고품질 재질을 자동으로 매핑합니다. (인터넷 미연결 시 로컬 캐시에서 불러오며, 실패 시 기본 절차적 재질로 폴백됩니다.)
  > * `screw`, `bolt`, `pin`, `washer` 등 🔩 ➡️ **Brushed Nickel** (브러시드 니켈, Asset ID: `b058fc10-bd2a-4cb5-8e05-f330fad99101`)
  > * `bearing`, `베어링`, `6803ZZ`, `6905ZZ`, `6807ZZ`, `6808ZZ`, `6809ZZ`, `6903ZZ`, `NSK`, `RAU` 등 ⚙️ ➡️ **Stainless Steel** (스테인리스 스틸, Asset ID: `79540f1a-c977-436f-b949-d9a2aa4c44a1`)
  > * `ap-`, `bp-`, `pcb`, `connector`, `T-10-15-25`~`T-30-35-45`, `PT-10-20`~`PT-35-45` 등 단자/커넥터 부품 ➡️ **Green Plastic** (녹색 플라스틱, Asset ID: `387e8822-6486-473d-92ff-3a91f426dd64` - **쉐이드 플랫 적용**)
  > * `hex_post` ➡️ **Brass** (황동, Asset ID: `f0c815ea-41ce-448e-ade1-8bcf1beebd3e` / `e7be890c-f95e-43eb-9686-6a1e09e25aa4`)
  > * `stator` + `coil` ➡️ **Copper** (구리 코일, Asset ID: `b19cef5d-04f7-4569-b53f-8c3475b2526d`)
  > * `stator` + `core` ➡️ **Carbon Steel** (탄소강, Asset ID: `58281db0-4437-4069-b925-5a8ab1c32197`)
  > * `stator` + `bobbin` ➡️ **Green Plastic** (녹색 플라스틱, Asset ID: `387e8822-6486-473d-92ff-3a91f426dd64` - **쉐이드 플랫 적용**)
  > * `rotor` + `magnet` ➡️ **Brushed Nickel** (브러시드 니켈, Asset ID: `b058fc10-bd2a-4cb5-8e05-f330fad99101`)
  > * `housing`, `case`, `cover` 등 외관 부품 ➡️ **Pearl Black Plastic** (펄 블랙 플라스틱, Asset ID: `386d3d08-9144-4145-881e-4b2d25c8202e`)
  > * 기타 일반 부품 ➡️ **Aluminium Sand** (알루미늄 샌드, Asset ID: `8e58e654-b722-49b7-aa44-e24210d5eede`)
* > [!TIP]
  > **BlenderKit HDRI 자동 매핑**: BlenderKit의 무료 Office HDRi 배경 이미지(예: `Office` 이름으로 된 HDRi)를 환경 텍스처로 자동 적용하여 현실적인 반사와 라이팅 환경을 조성합니다.
* 4방향 Isometric 카메라와 3점 스튜디오 조명이 배치되고, 각 부품의 재질에 맞춰 **쉐이드 자동 스무스(Shade Auto Smooth)** 또는 **쉐이드 플랫(Shade Flat)**이 차례대로 적용됩니다. 씬 배치 완료 후에는 **정사뷰(Orthographic) 및 쿼터뷰 카메라 각도로 뷰포트가 자동 정렬 및 최적 크기로 핏(Fit)되며, 모델 크기에 맞게 클리핑 임계값(Clip Start/End)이 동적으로 계산되어 뷰포트 및 자동 실행 스크립트(`autoplay.py`)에 반영**됩니다. 모든 작업이 끝나면 `[어셈블리명]__BLENDER` 폴더 내에 `[어셈블리명].blend` 파일이 생성됩니다.
* *(변환이 성공하면 임시로 생성되었던 `__STL` 폴더는 공간 확보를 위해 자동으로 안전하게 삭제됩니다.)*

#### **Step 5: 씬 최종 확인 및 편집 (선택 사항 - `Open BLEND`)**
* `Open BLEND` 버튼을 클릭하면, 현재 구성된 `.blend` 파일의 디자인을 수동으로 편집할 수 있도록 독립된 Blender GUI 창이 비동기로 실행됩니다. 
* 레이아웃을 확인하거나 카메라/조명 위치 등을 직접 미세 조정하고 저장한 뒤 창을 닫으시면 됩니다.

#### **Step 6: 자동 배치 렌더링 (`RENDER`)**
* `RENDER` 버튼을 클릭하고 생성된 `.blend` 파일을 선택합니다.
* 백그라운드(헤드리스)에서 블렌더의 고품질 **Cycles GPU 렌더러**가 실행되어, 미리 세팅된 4가지 Isometric 카메라 각도에서 고품질 제품 이미지를 자동으로 차례대로 렌더링합니다.
* 결과물은 `.blend` 파일이 있는 `__BLENDER` 폴더 내에 투명 배경(`RGBA PNG`) 형태로 저장됩니다.

#### **Step 7: 조립분해도 애니메이션 렌더링 (`EXPLODE`)**
* `EXPLODE` 버튼을 클릭하면 다음과 같은 조립분해도 애니메이션 렌더링 프로세스가 진행됩니다:
  1. **분해 축 및 방향 선택 팝업**: 분해 애니메이션이 진행될 기준 축(X, Y, Z축 중 선택, 기본값 Y축)과 분해 진행 방향(Positive `+` 또는 Negative `-` 중 선택)을 한번에 지정할 수 있는 팝업창이 나타납니다.
  2. **분해 동영상 시간 설정 팝업**: 애니메이션의 총 재생 시간(초 단위, 기본값 20초)을 설정할 수 있는 팝업창이 나타납니다.
  3. 기존에 생성된 `.blend` 파일의 이름 뒤에 `_explode` 접미사를 붙여 복사본을 생성합니다.
  4. 복사된 blend 파일을 열어, 최대 렌더 샘플수를 64로 조절하고 디노이즈(Denoising) 옵션을 비활성화합니다.
  5. 해상도를 `800x600px` (100% 배율)로 변경하고 프레임 레이트를 `30 fps`로 변경합니다. 출력 경로는 blend 파일과 같은 경로로 지정되며, 미디어 유형은 비디오(`FFMPEG` MP4 형식)로 설정됩니다.
  6. 지정한 분해 축, 방향, 재생 시간을 반영한 `explode.py` 애니메이션 스크립트가 실행됩니다.
     * > [!TIP]
     * > **카메라 뷰포트 기반 안전 이탈(Off-Screen Exit) 및 어댑티브 간격(Adaptive Clearance)**: 
     * > * Blender의 카메라 뷰 투영 연산(`world_to_camera_view`)을 활용하여 모든 부품(특히 안쪽의 핵심 부품)이 화면 밖으로 완전히 이탈하는 데 필요한 최소 이동 거리를 계산합니다.
     * > * 부품 간 바운딩 박스 크기를 고려해 어댑티브 간격(Adaptive Gap)을 두어, 분해 애니메이션 시 부품이 겹치거나 충돌하지 않고 정돈된 간격을 유지하도록 부품별 이동량이 외곽부터 순차 누적 계산됩니다.
  7. 변경된 설정을 그대로 적용하여 blend 파일을 저장합니다.
  8. 새로 만들어진 타임라인으로 최종 비디오 애니메이션 렌더링을 실시합니다. (시간이 많이 걸림)
  9. 완료 시 GUI의 Output Log 창을 통해 성공적으로 완료되었음을 알리는 종료 메세지를 출력합니다.

#### **Step 8: 종료 (`EXIT`)**
* `EXIT` 버튼을 눌러 GUI를 닫고 전체 작업을 종료합니다.

