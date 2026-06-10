import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import threading
import queue
import os
import sys
import shutil
import json

# Make the process DPI aware to render sharp system fonts on Windows
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# ═══════════════════════════════════════════════════════════════════
# Centralized System Font Definitions (Ensures 100% Absolute Uniformity)
# ═══════════════════════════════════════════════════════════════════
SYSTEM_FONT = ("Segoe UI", 9)
SYSTEM_FONT_BOLD = ("Segoe UI", 9, "bold")
SYSTEM_FONT_LARGE_BOLD = ("Segoe UI", 10, "bold")

# ═══════════════════════════════════════════════════════════════════
# Color Palette — Slate + Indigo (Premium Light)
# ═══════════════════════════════════════════════════════════════════
COLORS = {
    "bg":         "#f8fafc",   # Slate-50      — root background & frame background
    "bg_light":   "#f8fafc",   # Unify card background with root bg
    "bg_dark":    "#f1f5f9",   # Slate-100     — text inputs / treeview
    "fg":         "#0f172a",   # Slate-900     — primary text
    "fg_dim":     "#94a3b8",   # Slate-400     — disabled text
    "fg_sub":     "#64748b",   # Slate-500     — secondary text
    "accent":     "#6366f1",   # Indigo-500    — primary accent / selection bg
    "green":      "#34d399",   # Emerald-400   — success hover
    "green_dim":  "#059669",   # Emerald-600   — success button bg
    "red":        "#f43f5e",   # Rose-500      — error / danger
    "peach":      "#f59e0b",   # Amber-500     — warning
    "border":     "#e2e8f0",   # Slate-200     — borders
    "surface2":   "#f1f5f9",   # Slate-100     — hover / selection
}

# ═══════════════════════════════════════════════════════════════════
# ttk Style Definitions
# ═══════════════════════════════════════════════════════════════════
def setup_styles():
    """Configure all ttk widget styles using the Slate + Indigo palette."""
    style = ttk.Style()
    style.theme_use("clam")

    C = COLORS

    # ── Frame ──
    style.configure("TFrame", background=C["bg"])
    style.configure("Card.TFrame", background=C["bg_light"])

    # ── LabelFrame ──
    style.configure("TLabelframe",
        background=C["bg_light"],
        bordercolor=C["border"],
        lightcolor=C["bg_light"],
        darkcolor=C["bg_light"])
    style.configure("TLabelframe.Label",
        background=C["bg_light"],
        foreground=C["accent"],
        font=SYSTEM_FONT_LARGE_BOLD)

    # ── Label ──
    style.configure("TLabel",
        background=C["bg"],
        foreground=C["fg"],
        font=SYSTEM_FONT)
    style.configure("Card.TLabel",
        background=C["bg_light"],
        foreground=C["fg"],
        font=SYSTEM_FONT)
    style.configure("Path.TLabel",
        background=C["bg_light"],
        foreground=C["accent"],
        font=SYSTEM_FONT)
    style.configure("Bold.TLabel",
        background=C["bg"],
        foreground=C["fg"],
        font=SYSTEM_FONT_BOLD)
    style.configure("CardBold.TLabel",
        background=C["bg_light"],
        foreground=C["fg"],
        font=SYSTEM_FONT_BOLD)

    # ── Flat Buttons Configuration ──
    # Default Button
    style.configure("TButton",
        background=C["border"],
        foreground=C["fg"],
        bordercolor=C["border"],
        lightcolor=C["border"],
        darkcolor=C["border"],
        font=SYSTEM_FONT,
        padding=(6, 4))
    style.map("TButton",
        background=[("active", C["surface2"]), ("pressed", C["border"])],
        foreground=[("disabled", C["fg_dim"])],
        bordercolor=[("active", C["border"])])

    # Accent Button (Emerald)
    style.configure("Accent.TButton",
        background=C["green_dim"],
        foreground="#ffffff",
        bordercolor=C["green_dim"],
        lightcolor=C["green_dim"],
        darkcolor=C["green_dim"],
        font=SYSTEM_FONT_BOLD,
        padding=(6, 4))
    style.map("Accent.TButton",
        background=[("active", C["green"]), ("pressed", C["green_dim"])],
        foreground=[("active", "#ffffff")])

    # Info Button (Indigo)
    style.configure("Info.TButton",
        background=C["accent"],
        foreground="#ffffff",
        bordercolor=C["accent"],
        lightcolor=C["accent"],
        darkcolor=C["accent"],
        font=SYSTEM_FONT_BOLD,
        padding=(6, 4))
    style.map("Info.TButton",
        background=[("active", "#818cf8"), ("pressed", C["accent"])])

    # Danger Button (Rose)
    style.configure("Danger.TButton",
        background=C["border"],
        foreground=C["red"],
        bordercolor=C["border"],
        lightcolor=C["border"],
        darkcolor=C["border"],
        font=SYSTEM_FONT_BOLD,
        padding=(6, 4))
    style.map("Danger.TButton",
        background=[("active", "#fff1f2")],
        foreground=[("active", "#e11d48")])

    # ── Radiobutton ──
    style.configure("TRadiobutton",
        background=C["bg"],
        foreground=C["fg"],
        font=SYSTEM_FONT,
        indicatorcolor=C["border"])
    style.map("TRadiobutton",
        background=[("active", C["bg"])],
        indicatorcolor=[("selected", C["accent"])])

    style.configure("Card.TRadiobutton",
        background=C["bg_light"],
        foreground=C["fg"],
        font=SYSTEM_FONT,
        indicatorcolor=C["border"])
    style.map("Card.TRadiobutton",
        background=[("active", C["bg_light"])],
        indicatorcolor=[("selected", C["accent"])])

    # ── Entry ──
    style.configure("TEntry",
        fieldbackground=C["bg_dark"],
        foreground=C["fg"],
        bordercolor=C["border"],
        lightcolor=C["border"],
        darkcolor=C["border"],
        insertcolor=C["fg"],
        font=SYSTEM_FONT)

    # ── Spinbox ──
    style.configure("TSpinbox",
        fieldbackground=C["bg_dark"],
        foreground=C["fg"],
        bordercolor=C["border"],
        lightcolor=C["border"],
        darkcolor=C["border"],
        arrowcolor=C["fg"],
        insertcolor=C["fg"],
        font=SYSTEM_FONT)

    # ── Treeview ──
    style.configure("Treeview",
        background=C["bg_dark"],
        foreground=C["fg"],
        fieldbackground=C["bg_dark"],
        bordercolor=C["border"],
        font=SYSTEM_FONT,
        rowheight=26)
    style.configure("Treeview.Heading",
        background=C["border"],
        foreground=C["fg_sub"],
        bordercolor=C["border"],
        font=SYSTEM_FONT_BOLD,
        padding=(8, 4))
    style.map("Treeview",
        background=[("selected", "#e0e7ff")],
        foreground=[("selected", "#3730a3")])

    # ── Scrollbar ──
    style.configure("TScrollbar",
        background=C["border"],
        troughcolor=C["bg_dark"],
        bordercolor=C["bg_dark"],
        arrowcolor=C["fg_dim"])

    return style


def load_config():
    config = {
        "blender_exe": "blender",
        "render_samples": 512,
        "viewport_samples": 64,
        "use_denoising": True,
        "explode_axis": "Y",
        "explode_dir_mode": "POS",
        "explode_duration": 20,
        "resolution_x": 800,
        "resolution_y": 600,
        "resolution_percentage": 200,
        "resolution_percentage_explode": 100,
        "render_engine": "CYCLES",
        "compute_device": "GPU",
        "cycles_device_type": "OPTIX",
        "keywords_green_plastic": "ap-, bp-, pcb, connector, T-10-15-25, T-15-20-30, T-20-25-35, T-25-30-40, T-30-35-45, PT-10-20, PT-13-25, PT-14-25, PT-15-25, PT-20-30, PT-25-35, PT-30-40, PT-35-45, stator+bobbin",
        "keywords_brass": "hex_post",
        "keywords_brushed_nickel": "screw, bolt, key, pin, washer, nut, rivet, 나사, 볼트, 핀, 와셔, 너트, 리벳, 키, rotor+magnet",
        "keywords_stainless_steel": "bearing, 베어링, 6803zz, 6905zz, 6807zz, 6808zz, 6809zz, 6903zz, nsk, rau",
        "keywords_copper": "stator+coil",
        "keywords_carbon_steel": "stator+core",
        "keywords_pearl_black_plastic": "housing, case, cover, body, frame, shell, panel, enclosure, 하우징, 케이스, 커버, 외관, 몸체, 프레임, 패널, 셀"
    }
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    template_path = os.path.join(script_dir, "config.json.template")
    
    selected_path = None
    if os.path.exists(config_path):
        selected_path = config_path
    elif os.path.exists(template_path):
        selected_path = template_path
        
    if selected_path:
        try:
            with open(selected_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
                config.update(user_config)
        except Exception as e:
            print(f"Warning: Failed to load config from {selected_path}: {e}")
    return config


# ═══════════════════════════════════════════════════════════════════
# Dialog Classes
# ═══════════════════════════════════════════════════════════════════

class TipDialog(tk.Toplevel):
    def __init__(self, parent, title, text):
        super().__init__(parent)
        self.configure(bg=COLORS["bg_light"])
        self.title(title)
        self.geometry("500x320")
        self.resizable(True, True)
        
        self.transient(parent)
        self.grab_set()
        
        # Center relative to parent
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        
        x = parent_x + (parent_w - 500) // 2
        y = parent_y + (parent_h - 320) // 2
        self.geometry(f"+{x}+{y}")
        
        frame_text = ttk.Frame(self, style="Card.TFrame")
        frame_text.pack(fill="both", expand=True, padx=15, pady=(15, 10))
        
        # [Updated] Centralized SYSTEM_FONT variable applied to the text widget
        txt = tk.Text(frame_text, wrap="word",
            bg=COLORS["bg_dark"], fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
            selectbackground=COLORS["accent"], selectforeground="#ffffff",
            relief="flat", highlightthickness=0,
            font=SYSTEM_FONT)
        txt.insert("1.0", text)
        txt.config(state="disabled")
        txt.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(frame_text, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        
        btn_ok = ttk.Button(self, text="Close", width=10, command=self.destroy)
        btn_ok.pack(pady=(0, 15))
        
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Return>", lambda e: self.destroy())


class ConfigEditorDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.configure(bg=COLORS["bg_light"])
        self.title("Configuration Editor")
        
        width = 800
        height = 620
        self.geometry(f"{width}x{height}")
        self.resizable(True, True)
        
        self.transient(parent)
        self.grab_set()
        
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        
        x = parent_x + (parent_w - width) // 2
        y = parent_y + (parent_h - height) // 2
        self.geometry(f"+{x}+{y}")
        
        frame_buttons = ttk.Frame(self, style="Card.TFrame")
        frame_buttons.pack(side="bottom", fill="x", pady=10, padx=10)
        
        btn_save = ttk.Button(frame_buttons, text="Save", width=10,
            command=self.on_save, style="Accent.TButton")
        btn_save.pack(side="right", padx=5)
        
        btn_cancel = ttk.Button(frame_buttons, text="Cancel", width=10,
            command=self.destroy)
        btn_cancel.pack(side="right", padx=5)
        
        btn_tip = ttk.Button(frame_buttons, text="Tip", width=10,
            command=self.show_tip, style="Info.TButton")
        btn_tip.pack(side="right", padx=5)
        
        self.frame_details = ttk.LabelFrame(self,
            text="Selected Value Details (Word Wrapped & Editable)",
            padding=(10, 5))
        self.frame_details.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        
        self.lbl_selected_key = ttk.Label(self.frame_details,
            text="Select a key from the list above to view/edit",
            style="CardBold.TLabel", anchor="w")
        self.lbl_selected_key.pack(fill="x", pady=(0, 5))
        
        # [Updated] Centralized SYSTEM_FONT variable applied
        self.txt_value = tk.Text(self.frame_details, height=5, wrap="word",
            bg=COLORS["bg_dark"], fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
            selectbackground=COLORS["accent"], selectforeground="#ffffff",
            relief="flat",
            highlightthickness=1, highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
            font=SYSTEM_FONT)
        self.txt_value.pack(side="left", fill="both", expand=True)
        self.txt_value.config(state="disabled")
        
        txt_scrollbar = ttk.Scrollbar(self.frame_details, orient="vertical",
            command=self.txt_value.yview)
        self.txt_value.configure(yscrollcommand=txt_scrollbar.set)
        txt_scrollbar.pack(side="right", fill="y")
        
        frame_tree = ttk.Frame(self, style="Card.TFrame")
        frame_tree.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        
        self.tree = ttk.Treeview(frame_tree, columns=("Value"), show="tree headings")
        self.tree.heading("#0", text="Key")
        self.tree.heading("Value", text="Value")
        self.tree.column("#0", width=200, anchor="w")
        self.tree.column("Value", width=550, anchor="w")
        
        scrollbar = ttk.Scrollbar(frame_tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.config_data = load_config()
        self.populate_tree()
        
        self.current_selected_key = None
        self.tree.bind("<<TreeviewSelect>>", self.on_select_item)
        self.txt_value.bind("<KeyRelease>", self.on_text_change)
        self.tree.bind("<Double-1>", self.on_double_click)
        
    def populate_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for key, val in self.config_data.items():
            self.tree.insert("", "end", iid=key, text=key, values=(str(val),))
            
    def on_select_item(self, event):
        selected = self.tree.selection()
        if not selected:
            self.current_selected_key = None
            self.lbl_selected_key.config(text="Select a key from the list above to view/edit")
            self.txt_value.delete("1.0", tk.END)
            self.txt_value.config(state="disabled")
            return
            
        key = selected[0]
        self.current_selected_key = key
        val = self.tree.set(key, "Value")
        
        self.lbl_selected_key.config(text=f"Key: {key}")
        self.txt_value.config(state="normal")
        self.txt_value.delete("1.0", tk.END)
        self.txt_value.insert("1.0", val)
        
    def on_text_change(self, event=None):
        if not self.current_selected_key:
            return
        new_val_str = self.txt_value.get("1.0", "end-1c")
        self.tree.set(self.current_selected_key, "Value", new_val_str)
        
    def show_tip(self):
        selected = self.tree.selection()
        if not selected:
            TipDialog(self, "Tip", "키 목록에서 항목을 선택하시면 해당 설정값에 대한 구체적인 도움말을 확인하실 수 있습니다.")
            return
            
        key = selected[0]
        tip_text = self.get_tip_text(key)
        TipDialog(self, f"Tip: {key}", tip_text)
        
    def get_tip_text(self, key):
        tips = {
            "blender_exe": "Blender 실행 파일(blender.exe)의 전체 경로 또는 명령어 이름을 지정합니다.\n\n예: blender, C:\\Program Files\\Blender Foundation\\Blender 4.2\\blender.exe",
            "render_samples": "최종 고품질 이미지 생성 시 Cycles 렌더 엔진의 최대 샘플링 횟수입니다. 값이 클수록 화질이 좋아지지만 렌더링 시간이 길어집니다.\n\n예: 512, 1024",
            "viewport_samples": "블렌더 뷰포트(실시간 미리보기) 내에서 Cycles 엔진이 사용할 최대 샘플 수입니다.\n\n예: 64, 128",
            "use_denoising": "최종 이미지의 지저분한 노이즈를 자동으로 제거하는 디노이저(Denoising) 활성화 여부입니다.\n\n허용 값: True (활성), False (비활성)",
            "explode_axis": "EXPLODE(분해) 애니메이션 시 부품들이 퍼져 나갈 기준 중심 축입니다.\n\n허용 값: X, Y, Z",
            "explode_dir_mode": "EXPLODE(분해) 애니메이션 시 부품들이 흩어지는 이동 방향입니다.\n\n허용 값:\n- POS: 양의 방향 (X, Y, Z축의 + 방향)\n- NEG: 음의 방향 (X, Y, Z축의 - 방향)",
            "explode_duration": "분해 조립 애니메이션 동영상의 총 재생 시간(초 단위)입니다.\n\n예: 20, 30",
            "resolution_x": "최종 렌더링 이미지의 가로 크기(픽셀 단위)입니다.\n\n예: 800, 1920",
            "resolution_y": "최종 렌더링 이미지의 세로 크기(픽셀 단위)입니다.\n\n예: 600, 1080",
            "resolution_percentage": "최종 이미지 렌더링 시 해상도(resolution_x, resolution_y)에 곱할 비율(%)입니다. 200% 설정 시 2배 크기로 렌더링되어 정밀한 결과물이 나옵니다.\n\n예: 100, 200",
            "resolution_percentage_explode": "EXPLODE(분해) 동영상 렌더링 시 적용될 해상도 비율(%)입니다. 비디오 렌더링 속도 단축을 위해 일반적으로 100을 지정합니다.\n\n예: 100, 150",
            "render_engine": "렌더링 시 사용할 엔진을 설정합니다.\n\n허용 값:\n- Cycles: 고품질 광선 추적(Raytracing) 렌더러 (기본값, 실사 렌더링에 권장)\n- EEVEE: 고속 실시간 렌더러",
            "compute_device": "렌더링 계산에 사용할 연산 장치를 설정합니다.\n\n허용 값:\n- GPU: 그래픽카드 가속 연산 사용 (기본값, 권장)\n- CPU: CPU 연산 사용 (느림)",
            "cycles_device_type": "Cycles 렌더 엔진에서 사용할 GPU 가속 API/프레임워크 기술 규격을 설정합니다.\n\n허용 값:\n- OptiX: NVIDIA RTX 그래픽카드 전용 초고속 레이트레이싱 API (RTX 시리즈 권장)\n- CUDA: NVIDIA 그래픽카드 범용 연산 API\n- HIP: AMD Radeon 그래픽카드용 API\n- None: 사용 안 함 (CPU 렌더링 시 선택)",
            "keywords_green_plastic": "PCB 회로 기판, 커넥터 등에 녹색 플라스틱(Green Plastic) 재질을 부여할 부품명의 키워드 목록입니다. 쉼표(,)로 각 키워드를 나열하며, 대소문자는 구분하지 않습니다. 단어 조합 규칙은 '+'를 사용합니다.\n\n예: pcb, connector, stator+bobbin",
            "keywords_brass": "지지 기둥(hex_post) 등에 Brass(황동) 재질을 부여할 부품명의 키워드 목록입니다. 쉼표(,)로 구분합니다.\n\n예: hex_post, brass_pin",
            "keywords_brushed_nickel": "은색 무광의 Brushed Nickel(브러시드 니켈) 재질을 부여할 부품명 키워드 목록입니다. 나사, 볼트, 와셔, 핀 등에 유용합니다.\n\n예: screw, bolt, key, pin, 나사, 볼트, rotor+magnet",
            "keywords_stainless_steel": "Stainless Steel(스테인리스 스틸) 재질을 부여할 부품명 키워드 목록입니다. 베어링, 구동 샤프트 등에 유용합니다.\n\n예: bearing, 베어링, nsk, rau",
            "keywords_copper": "구리 코일 등에 Copper(구리) 재질을 부여할 부품명 키워드 목록입니다.\n\n예: stator+coil, copper_wire",
            "keywords_carbon_steel": "Carbon Steel(탄소강) 재질을 부여할 부품명 키워드 목록입니다. 모터 코어 부위 등에 유용합니다.\n\n예: stator+core, iron_plate",
            "keywords_pearl_black_plastic": "제품의 외부 하우징, 커버, 케이스 등에 펄 블랙 플라스틱(Pearl Black Plastic) 재질을 부여할 부품명 키워드 목록입니다.\n\n예: housing, case, cover, 하우징, 케이스, 프레임"
        }
        return tips.get(key, "이 항목에 대한 도움말 정보가 없습니다.")
        
    def on_double_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
            
        column = self.tree.identify_column(event.x)
        item_id = self.tree.identify_row(event.y)
        
        if not item_id:
            return
            
        if column != "#1":
            return
            
        bbox = self.tree.bbox(item_id, column)
        if not bbox:
            return
            
        x, y, w, h = bbox
        
        # [Updated] Centralized SYSTEM_FONT variable applied
        entry = tk.Entry(self.tree,
            bg=COLORS["bg_dark"], fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
            selectbackground=COLORS["accent"], selectforeground="#ffffff",
            relief="flat", font=SYSTEM_FONT)
        entry.insert(0, self.tree.set(item_id, "Value"))
        entry.select_range(0, tk.END)
        entry.focus_set()
        
        entry.place(x=x, y=y, width=w, height=h)
        
        editing = True
        def save_edit(event_or_none=None):
            nonlocal editing
            if not editing:
                return
            new_val = entry.get()
            orig_val = self.config_data.get(item_id)
            typed_val = new_val
            
            if isinstance(orig_val, bool):
                typed_val = new_val.lower() in ("true", "1", "yes", "on")
            elif isinstance(orig_val, int):
                try:
                    typed_val = int(new_val)
                except ValueError:
                    messagebox.showerror("Error", f"Value for {item_id} must be an integer.")
                    editing = False
                    entry.destroy()
                    return
            elif isinstance(orig_val, float):
                try:
                    typed_val = float(new_val)
                except ValueError:
                    messagebox.showerror("Error", f"Value for {item_id} must be a number.")
                    editing = False
                    entry.destroy()
                    return
            
            self.tree.set(item_id, "Value", str(typed_val))
            editing = False
            entry.destroy()
            
            if self.current_selected_key == item_id:
                self.txt_value.config(state="normal")
                self.txt_value.delete("1.0", tk.END)
                self.txt_value.insert("1.0", str(typed_val))
            
        def cancel_edit(event=None):
            nonlocal editing
            if editing:
                editing = False
                entry.destroy()
            
        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", save_edit)
        entry.bind("<Escape>", cancel_edit)
        
    def on_save(self):
        updated_config = {}
        for key in self.config_data.keys():
            val_str = self.tree.set(key, "Value")
            orig_val = self.config_data[key]
            
            if isinstance(orig_val, bool):
                val_lower = val_str.strip().lower()
                if val_lower in ("true", "1", "yes", "on"):
                    typed_val = True
                elif val_lower in ("false", "0", "no", "off"):
                    typed_val = False
                else:
                    messagebox.showerror("Validation Error", f"Value for '{key}' must be True or False.")
                    self.tree.selection_set(key)
                    self.tree.focus(key)
                    return
            elif isinstance(orig_val, int):
                try:
                    typed_val = int(val_str.strip())
                except ValueError:
                    messagebox.showerror("Validation Error", f"Value for '{key}' must be an integer.")
                    self.tree.selection_set(key)
                    self.tree.focus(key)
                    return
            elif isinstance(orig_val, float):
                try:
                    typed_val = float(val_str.strip())
                except ValueError:
                    messagebox.showerror("Validation Error", f"Value for '{key}' must be a number.")
                    self.tree.selection_set(key)
                    self.tree.focus(key)
                    return
            else:
                typed_val = val_str
                
            updated_config[key] = typed_val
            
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, "config.json")
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(updated_config, f, indent=2)
            messagebox.showinfo("Success", "Configuration saved successfully.")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config.json: {e}")


class AxisSelectionDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.result = None
        self.configure(bg=COLORS["bg_light"])
        
        self.title("Select Explode Axis & Direction")
        self.geometry("360x260")
        self.resizable(False, False)
        
        self.transient(parent)
        self.grab_set()
        
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        
        x = parent_x + (parent_w - 360) // 2
        y = parent_y + (parent_h - 260) // 2
        self.geometry(f"+{x}+{y}")
        
        lbl_msg = ttk.Label(self, text="Select the disassembly (explode) axis:",
            style="Bold.TLabel")
        lbl_msg.pack(pady=(15, 5))
        
        config = load_config()
        self.axis_var = tk.StringVar(value=config.get("explode_axis", "Y"))
        frame_radio = ttk.Frame(self, style="Card.TFrame")
        frame_radio.pack(pady=5)
        
        for axis in ["X", "Y", "Z"]:
            rb = ttk.Radiobutton(frame_radio, text=f"{axis} Axis",
                variable=self.axis_var, value=axis, style="Card.TRadiobutton")
            rb.pack(side="left", padx=15)

        lbl_dir = ttk.Label(self, text="Select the explosion direction:",
            style="Bold.TLabel")
        lbl_dir.pack(pady=(15, 5))

        self.dir_var = tk.StringVar(value=config.get("explode_dir_mode", "POS"))
        frame_dir = ttk.Frame(self, style="Card.TFrame")
        frame_dir.pack(pady=5)

        directions = [("+ (Positive)", "POS"), ("- (Negative)", "NEG")]
        for text, value in directions:
            rb = ttk.Radiobutton(frame_dir, text=text,
                variable=self.dir_var, value=value, style="Card.TRadiobutton")
            rb.pack(side="left", padx=20)
            
        frame_buttons = ttk.Frame(self, style="Card.TFrame")
        frame_buttons.pack(pady=20)
        
        btn_ok = ttk.Button(frame_buttons, text="OK", width=10,
            command=self.on_ok, style="Accent.TButton")
        btn_ok.pack(side="left", padx=10)
        
        btn_cancel = ttk.Button(frame_buttons, text="Cancel", width=10,
            command=self.on_cancel)
        btn_cancel.pack(side="left", padx=10)
        
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.wait_window(self)
        
    def on_ok(self):
        self.result = (self.axis_var.get(), self.dir_var.get())
        self.destroy()
        
    def on_cancel(self):
        self.result = None
        self.destroy()


class DurationSelectionDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.result = None
        self.configure(bg=COLORS["bg_light"])
        
        self.title("Select Explode Duration")
        self.geometry("320x180")
        self.resizable(False, False)
        
        self.transient(parent)
        self.grab_set()
        
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        
        x = parent_x + (parent_w - 320) // 2
        y = parent_y + (parent_h - 180) // 2
        self.geometry(f"+{x}+{y}")
        
        lbl_msg = ttk.Label(self, text="Set disassembly duration (seconds):",
            style="Bold.TLabel")
        lbl_msg.pack(pady=15)
        
        config = load_config()
        self.duration_var = tk.StringVar(value=str(config.get("explode_duration", 20)))
        
        frame_input = ttk.Frame(self, style="Card.TFrame")
        frame_input.pack(pady=5)
        
        self.spin = ttk.Spinbox(frame_input, from_=1, to=3600,
            textvariable=self.duration_var, width=10)
        self.spin.pack(side="left", padx=5)
        
        lbl_sec = ttk.Label(frame_input, text="seconds", style="Card.TLabel")
        lbl_sec.pack(side="left")
        
        frame_buttons = ttk.Frame(self, style="Card.TFrame")
        frame_buttons.pack(pady=15)
        
        btn_ok = ttk.Button(frame_buttons, text="OK", width=10,
            command=self.on_ok, style="Accent.TButton")
        btn_ok.pack(side="left", padx=10)
        
        btn_cancel = ttk.Button(frame_buttons, text="Cancel", width=10,
            command=self.on_cancel)
        btn_cancel.pack(side="left", padx=10)
        
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.wait_window(self)
        
    def on_ok(self):
        val_str = self.duration_var.get().strip()
        try:
            val = int(val_str)
            if val <= 0:
                raise ValueError
            self.result = val
            self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid positive integer for seconds.")
        
    def on_cancel(self):
        self.result = None
        self.destroy()


# ═══════════════════════════════════════════════════════════════════
# Main Application
# ═══════════════════════════════════════════════════════════════════

class AutoRenderApp:
    def __init__(self, root):
        self.root = root
        self.root.option_add("*Font", SYSTEM_FONT)
        self.root.title("Auto Render GUI")
        self.root.geometry("800x500")
        
        self.selected_file_path = tk.StringVar()
        self.selected_file_path.set("No file selected")
        self.selected_blend_path = tk.StringVar()
        self.selected_blend_path.set("No blend file selected")
        self.resolution_var = tk.StringVar(value="800x600")
        self.log_queue = queue.Queue()
        
        self.setup_ui()
        self.root.after(100, self.process_log_queue)

    def setup_ui(self):
        # 1. File Selection Frame
        frame_file = ttk.LabelFrame(self.root, text="Target File", padding=(8, 4))
        frame_file.pack(fill="x", padx=10, pady=2)
        
        lbl_file = ttk.Label(frame_file, textvariable=self.selected_file_path,
            style="Path.TLabel", wraplength=760, anchor="w")
        lbl_file.pack(side="left", fill="x", expand=True)
        
        btn_browse = ttk.Button(frame_file, text="Choose SLDASM", width=20,
            command=self.choose_file)
        btn_browse.pack(side="right")

        # 1.5. Blend File Selection Frame
        frame_blend = ttk.LabelFrame(self.root, text="blend File", padding=(8, 4))
        frame_blend.pack(fill="x", padx=10, pady=2)
        
        lbl_blend = ttk.Label(frame_blend, textvariable=self.selected_blend_path,
            style="Path.TLabel", wraplength=760, anchor="w")
        lbl_blend.pack(side="left", fill="x", expand=True)
        
        btn_browse_blend = ttk.Button(frame_blend, text="Choose BLEND", width=20,
            command=self.choose_blend_file)
        btn_browse_blend.pack(side="right")
        
        # 2. Action Buttons Frame
        frame_actions = ttk.Frame(self.root, padding=(10, 4))
        frame_actions.pack(fill="x", padx=10, pady=2)
        
        self.btn_stl = ttk.Button(frame_actions, text="Make STL",
            command=self.run_make_stl, width=12, state="disabled")
        self.btn_stl.pack(side="left", padx=2)
        
        self.btn_blend = ttk.Button(frame_actions, text="Make BLEND",
            command=self.run_make_blend, width=14, state="disabled")
        self.btn_blend.pack(side="left", padx=2)
        
        self.btn_open = ttk.Button(frame_actions, text="Open BLEND",
            command=self.run_open_blend, width=14, state="disabled")
        self.btn_open.pack(side="left", padx=2)
        
        self.btn_render = ttk.Button(frame_actions, text="RENDER",
            command=self.run_render, width=10, state="disabled")
        self.btn_render.pack(side="left", padx=2)
        
        self.btn_explode = ttk.Button(frame_actions, text="EXPLODE",
            command=self.run_explode, width=10, state="disabled")
        self.btn_explode.pack(side="left", padx=2)
        
        btn_exit = ttk.Button(frame_actions, text="EXIT",
            command=self.root.quit, width=8, style="Danger.TButton")
        btn_exit.pack(side="right", padx=2)
        
        btn_help = ttk.Button(frame_actions, text="HELP",
            command=self.open_help, width=8, style="Info.TButton")
        btn_help.pack(side="right", padx=2)
        
        btn_config = ttk.Button(frame_actions, text="CONFIG",
            command=self.open_config, width=8)
        btn_config.pack(side="right", padx=2)
        
        # 3. Output Log Area
        frame_log = ttk.LabelFrame(self.root, text="Output Log", padding=(8, 4))
        frame_log.pack(fill="both", expand=True, padx=10, pady=2)
        
        log_inner = ttk.Frame(frame_log, style="Card.TFrame")
        log_inner.pack(fill="both", expand=True)
        
        # [Updated] Centralized SYSTEM_FONT variable applied
        self.txt_log = tk.Text(log_inner, state="disabled", height=10,
            bg=COLORS["bg_dark"], fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
            selectbackground=COLORS["accent"], selectforeground="#ffffff",
            relief="flat",
            highlightthickness=1, highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
            font=SYSTEM_FONT)
        
        log_scrollbar = ttk.Scrollbar(log_inner, orient="vertical",
            command=self.txt_log.yview)
        self.txt_log.configure(yscrollcommand=log_scrollbar.set)
        
        self.txt_log.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")
        
        self.txt_log.tag_config("stderr", foreground=COLORS["red"])

    def log(self, message, is_error=False):
        self.log_queue.put((message, is_error))

    def open_help(self):
        import webbrowser
        webbrowser.open("https://codeberg.org/dymaxionkim/AUTO_RENDER")

    def open_config(self):
        ConfigEditorDialog(self.root)

    def process_log_queue(self):
        try:
            while True:
                msg, is_error = self.log_queue.get_nowait()
                self.txt_log.config(state='normal')
                if is_error:
                    self.txt_log.insert(tk.END, msg + "\n", "stderr")
                else:
                    self.txt_log.insert(tk.END, msg + "\n")
                self.txt_log.see(tk.END)
                self.txt_log.config(state='disabled')
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_log_queue)

    def choose_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("SolidWorks Assembly", "*.SLDASM"), ("All Files", "*.*")]
        )
        if file_path:
            self.selected_file_path.set(file_path)
            self.btn_stl.config(state="normal")
            
            stl_dir = os.path.splitext(file_path)[0] + "__STL"
            if os.path.isdir(stl_dir):
                self.btn_blend.config(state="normal")
            else:
                self.btn_blend.config(state="disabled")
                
            self.check_blend_file()

    def choose_blend_file(self):
        initial_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = self.selected_file_path.get()
        if file_path and file_path != "No file selected" and os.path.exists(file_path):
            suggested_dir = os.path.splitext(file_path)[0] + "__BLENDER"
            if os.path.isdir(suggested_dir):
                initial_dir = suggested_dir
            else:
                initial_dir = os.path.dirname(file_path)
                
        blend_file = filedialog.askopenfilename(
            initialdir=initial_dir,
            title="Select Blender File",
            filetypes=[("Blender File", "*.blend"), ("All Files", "*.*")]
        )
        if blend_file:
            self.selected_blend_path.set(blend_file)
            self.btn_open.config(state="normal")
            self.btn_render.config(state="normal")
            self.btn_explode.config(state="normal")

    def run_command(self, cmd):
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1,
                cwd=os.path.dirname(os.path.abspath(__file__)) 
            )
            
            def read_stream(stream, is_error):
                import locale
                sys_encoding = locale.getpreferredencoding() or 'cp949'
                for line in iter(stream.readline, b''):
                    try:
                        decoded_line = line.decode('utf-8').strip()
                    except UnicodeDecodeError:
                        try:
                            decoded_line = line.decode(sys_encoding).strip()
                        except Exception:
                            decoded_line = line.decode('utf-8', errors='replace').strip()
                        
                    if decoded_line:
                        self.log(decoded_line, is_error=is_error)
                stream.close()

            t_out = threading.Thread(target=read_stream, args=(process.stdout, False))
            t_err = threading.Thread(target=read_stream, args=(process.stderr, True))
            
            t_out.start()
            t_err.start()
            
            t_out.join()
            t_err.join()
            
            return_code = process.wait()
            
            if return_code == 0:
                self.log(f"Process finished successfully.", is_error=False)
            else:
                self.log(f"Process failed with exit code {return_code}", is_error=True)
            
            return return_code
                
        except Exception as e:
            self.log(f"Error running command: {e}", is_error=True)
            return -1

    def run_make_stl(self):
        file_path = self.selected_file_path.get()
        if not os.path.exists(file_path):
            messagebox.showerror("Error", "Selected file not found.")
            return

        self.btn_stl.config(state="disabled")
        self.btn_blend.config(state="disabled")
        self.log("-" * 40)
        self.log(f"Starting Export to STL: {os.path.basename(file_path)}")

        cmd = [sys.executable, "sw2stl.py", file_path]
        
        def task():
            ret = self.run_command(cmd)
            self.root.after(0, lambda: self.btn_stl.config(state="normal"))
            
            if ret == 0:
                derived_stl_dir = os.path.splitext(file_path)[0] + "__STL"
                if os.path.isdir(derived_stl_dir):
                     self.root.after(0, lambda: self.btn_blend.config(state="normal"))
                     self.log("Ready for Blender conversion.")
                     self.root.after(0, lambda: self.check_blend_file())
                else:
                     self.log(f"Warning: Expected directory not found: {derived_stl_dir}", is_error=True)

        threading.Thread(target=task, daemon=True).start()

    def run_make_blend(self):
        file_path = self.selected_file_path.get()
        stl_dir = os.path.splitext(file_path)[0] + "__STL"
        
        if not os.path.isdir(stl_dir):
            messagebox.showerror("Error", f"STL Directory not found:\n{stl_dir}\nPlease run 'Make STL' first.")
            return

        self.btn_blend.config(state="disabled")
        self.log("-" * 40)
        self.log(f"Starting Blender Conversion: {os.path.basename(stl_dir)}")
        
        cmd = [sys.executable, "stl2blender.py", stl_dir]
        
        def task():
            ret = self.run_command(cmd)
            self.root.after(0, lambda: self.btn_blend.config(state="normal"))
            self.root.after(0, lambda: self.check_blend_file())
            if ret == 0:
                self.log(f"Blender conversion successful. Deleting STL directory: {stl_dir}")
                try:
                    shutil.rmtree(stl_dir)
                    self.log("Successfully deleted STL directory.")
                except Exception as e:
                    self.log(f"Failed to delete STL directory: {e}", is_error=True)

        threading.Thread(target=task, daemon=True).start()

    def run_render(self):
        blend_file = self.selected_blend_path.get()
        if not blend_file or blend_file in ("No blend file selected", "No blend file found"):
            messagebox.showerror("Error", "No Blender file selected or found.")
            return

        if not os.path.exists(blend_file):
            messagebox.showerror("Error", f"Blend file not found:\n{blend_file}")
            return
             
        self.btn_render.config(state="disabled")
        self.btn_explode.config(state="disabled")
        self.log("-" * 40)
        self.log(f"Starting Render: {os.path.basename(blend_file)}")
        self.log("Resolution: Keep blend file settings")
        
        cmd = [sys.executable, "blender2png.py", blend_file]
        
        def task():
            self.run_command(cmd)
            self.root.after(0, lambda: self.btn_render.config(state="normal"))
            self.root.after(0, lambda: self.btn_explode.config(state="normal"))

        threading.Thread(target=task, daemon=True).start()

    def run_explode(self):
        dialog = AxisSelectionDialog(self.root)
        if not dialog.result:
            self.log("Explode operation cancelled by user.")
            return
        selected_axis, selected_dir_mode = dialog.result

        duration_dialog = DurationSelectionDialog(self.root)
        selected_duration = duration_dialog.result
        if not selected_duration:
            self.log("Explode operation cancelled by user.")
            return

        blend_file = self.selected_blend_path.get()
        if not blend_file or blend_file in ("No blend file selected", "No blend file found"):
            messagebox.showerror("Error", "No Blender file selected or found.")
            return

        if not os.path.exists(blend_file):
            messagebox.showerror("Error", f"Blend file not found:\n{blend_file}")
            return
             
        self.btn_render.config(state="disabled")
        self.btn_explode.config(state="disabled")
        self.log("-" * 40)
        self.log(f"Starting Explode Render Sequence: {os.path.basename(blend_file)} (Axis: {selected_axis}, Direction: {selected_dir_mode}, Duration: {selected_duration}s)")
        
        explode_blend_file = f"{os.path.splitext(blend_file)[0]}_explode.blend"
        try:
            shutil.copy(blend_file, explode_blend_file)
            self.log(f"Copied blend file to: {os.path.basename(explode_blend_file)}")
        except Exception as e:
            self.log(f"Failed to copy blend file: {e}", is_error=True)
            self.btn_render.config(state="normal")
            self.btn_explode.config(state="normal")
            return

        config = load_config()
        blender_exe = config.get("blender_exe", "blender")
        resolution_percentage_explode = config.get("resolution_percentage_explode", 100)
        render_engine = config.get("render_engine", "CYCLES")
        compute_device = config.get("compute_device", "GPU")
        cycles_device_type = config.get("cycles_device_type", "OPTIX")

        mapped_engine = "BLENDER_EEVEE" if render_engine.upper() == "EEVEE" else "CYCLES"
        mapped_device = "GPU" if "GPU" in compute_device.upper() else "CPU"
        mapped_cycles_device_type = cycles_device_type.upper()

        temp_script_path = os.path.join(os.path.dirname(explode_blend_file), "_temp_explode_render.py")
        temp_script_path = os.path.normpath(temp_script_path)
        explode_py_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "explode.py"))
        
        script_content = f"""
import bpy
import os
import sys

os.environ["EXPLODE_AXIS"] = "{selected_axis}"
os.environ["EXPLODE_DIR_MODE"] = "{selected_dir_mode}"
os.environ["EXPLODE_DURATION"] = "{selected_duration}"

bpy.context.scene.render.engine = '{mapped_engine}'
bpy.context.scene.cycles.device = '{mapped_device}'
bpy.context.scene.cycles.samples = 64
bpy.context.scene.cycles.use_denoising = False

try:
    cycles_pref = bpy.context.preferences.addons['cycles'].preferences
    dev_type = '{mapped_cycles_device_type}'
    if dev_type != 'NONE':
        cycles_pref.compute_device_type = dev_type
        cycles_pref.get_devices()
        has_gpu = False
        for dev in cycles_pref.devices:
            if dev.type != 'CPU':
                dev.use = True
                has_gpu = True
            else:
                dev.use = False
        if has_gpu:
            print(f"Cycles GPU Compute Device Type configured: {{dev_type}}")
        else:
            print(f"Warning: GPU devices not found for {{dev_type}}")
except Exception as e:
    print(f"Warning: Could not configure Cycles GPU preferences: {{e}}")

bpy.context.scene.render.resolution_x = 800
bpy.context.scene.render.resolution_y = 600
bpy.context.scene.render.resolution_percentage = {resolution_percentage_explode}
bpy.context.scene.render.fps = 30
bpy.context.scene.render.filepath = os.path.dirname(bpy.data.filepath) + "/"
bpy.context.scene.render.image_settings.media_type = 'VIDEO'
bpy.context.scene.render.image_settings.file_format = 'FFMPEG'
bpy.context.scene.render.ffmpeg.format = 'MPEG4'

explode_py_path = {repr(explode_py_path)}
try:
    with open(explode_py_path, 'r', encoding='utf-8') as f:
        explode_code = f.read()
    text_block = bpy.data.texts.new(name="explode.py")
    text_block.from_string(explode_code)
    exec(compile(explode_code, 'explode.py', 'exec'), globals())
except Exception as e:
    print(f"Error executing explode.py: {{e}}")
    sys.exit(1)

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath, relative_remap=False)
bpy.ops.render.render(animation=True)
"""

        try:
            with open(temp_script_path, "w", encoding="utf-8") as f:
                f.write(script_content)
        except Exception as e:
            self.log(f"Error creating temp render script: {e}", is_error=True)
            self.btn_render.config(state="normal")
            self.btn_explode.config(state="normal")
            return

        cmd = [blender_exe, "-b", explode_blend_file, "-P", temp_script_path]
        
        def task():
            ret = self.run_command(cmd)
            if os.path.exists(temp_script_path):
                try:
                    os.remove(temp_script_path)
                except Exception as e:
                    self.log(f"Warning: Failed to delete temp script: {e}", is_error=True)
            
            if ret == 0:
                self.log("=" * 60)
                self.log("EXPLODE ANIMATION RENDER COMPLETED SUCCESSFULLY!")
                self.log(f"Exploded Blender File: {os.path.basename(explode_blend_file)}")
                self.log(f"Output files saved to: {os.path.dirname(explode_blend_file)}")
                self.log("=" * 60)
            else:
                self.log("=" * 60)
                self.log("EXPLODE ANIMATION RENDER FAILED!", is_error=True)
                self.log("=" * 60)

            self.root.after(0, lambda: self.btn_render.config(state="normal"))
            self.root.after(0, lambda: self.btn_explode.config(state="normal"))

        threading.Thread(target=task, daemon=True).start()

    def run_open_blend(self):
        blend_file = self.selected_blend_path.get()
        if not blend_file or blend_file in ("No blend file selected", "No blend file found") or not os.path.exists(blend_file):
            messagebox.showerror("Error", "No Blender file selected or found.")
            return
            
        config = load_config()
        blender_exe = config.get("blender_exe", "blender")
                
        self.log("-" * 40)
        self.log(f"Launching Blender GUI with: {os.path.basename(blend_file)}")
        
        try:
            if os.name == 'nt':
                subprocess.Popen([blender_exe, blend_file], creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                subprocess.Popen([blender_exe, blend_file])
            self.log("Blender GUI launched successfully.")
        except Exception as e:
            self.log(f"Error launching Blender: {e}", is_error=True)

    def check_blend_file(self):
        file_path = self.selected_file_path.get()
        if not file_path or file_path == "No file selected": return
        
        base_path_no_ext = os.path.splitext(file_path)[0]
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        blend_dir = base_path_no_ext + "__BLENDER"
        blend_file = os.path.join(blend_dir, f"{base_name}.blend")
        
        if os.path.exists(blend_file):
            self.log(f"Suggested Blend file found: {os.path.basename(blend_file)}")
            self.btn_open.config(state="normal")
            self.btn_render.config(state="normal")
            self.btn_explode.config(state="normal")
            self.selected_blend_path.set(blend_file)
        else:
            self.btn_open.config(state="disabled")
            self.btn_render.config(state="disabled")
            self.btn_explode.config(state="disabled")
            self.selected_blend_path.set("No blend file found")


if __name__ == "__main__":
    root = tk.Tk()
    root.configure(bg=COLORS["bg"])
    setup_styles()
    app = AutoRenderApp(root)
    root.mainloop()