from __future__ import annotations
import multiprocessing
import os
import sys
import io
import logging

# =====================================================================
# ПЕРЕХВАТ СИСТЕМНЫХ ПОТОКОВ (Для фикса ошибки логгера YASA)
# =====================================================================
if sys.stdout is None: sys.stdout = io.StringIO()
if sys.stderr is None: sys.stderr = io.StringIO()
logging.basicConfig(stream=sys.stdout, level=logging.ERROR)
# =====================================================================

# =====================================================================
# TENSORFLOW TLS SLOT LIMIT WORKAROUND (ERROR 1114)
# =====================================================================
if len(sys.argv) >= 2 and sys.argv[1] == '--caisr-stage-worker':
    try:
        import tensorflow as tf
        import json
        args_json = sys.argv[2]
        kwargs = json.loads(args_json)
        
        base_dir = kwargs.get('base_dir')
        if base_dir and base_dir not in sys.path:
            sys.path.insert(0, base_dir)
            
        caisr_dir = os.path.join(base_dir, 'CAISR-App-main')
        if caisr_dir not in sys.path:
            sys.path.insert(0, caisr_dir)
            
        # This will now load cleanly without PyQt/MNE stealing TLS slots!
        from caisr_stage import CAISR_stage
        
        CAISR_stage(kwargs['input_files'], kwargs['save_paths'], kwargs['model_path'])
        sys.exit(0)
    except Exception as e:
        print(f"CAISR_STAGE_WORKER_ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
# =====================================================================

import lspopt
from lspopt import spectrogram_lspopt
os.environ["OUTDATED_IGNORE"] = "1"

# =====================================================================
# ГАШЕНИЕ ВНЕШНЕГО МУЛЬТИПРОЦЕССИНГА (Решение проблемы двойного запуска)
# =====================================================================
os.environ["LOKY_MAX_CPU_COUNT"] = "1"
os.environ["JOBLIB_MULTIPROCESSING"] = "0"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
# =====================================================================

import inspect
import subprocess
import threading
import traceback
import time
import ctypes
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from math import sqrt
from collections import namedtuple
import pandas as pd

# Pillow for anti-aliasing
from PIL import Image, ImageDraw, ImageTk

# --- ДОБАВЛЕНО ДЛЯ ВИДЕО ---
try:
    import cv2
except ImportError:
    cv2 = None
    print("Warning: opencv-python is not installed. Video splash screen will not work.")

def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

try:
    import sv_ttk
except ImportError:
    messagebox.showwarning("Warning", "Library 'sv_ttk' is not installed.\nThe interface will look old-fashioned.\n\nTo fix, run: pip install sv-ttk")

FONT_FAMILY_UI = "Segoe UI"
FONT_SIZE_TITLE = 10
FONT_SIZE_BODY = 9

# -------------------- Make Modules Importable --------------------
from pathlib import Path as _Path

# 1. Динамический путь для RBDtector
RBDTECTOR_SRC = _Path(resource_path(os.path.join("RBDtector", "RBDtector")))
if str(RBDTECTOR_SRC) not in sys.path:
    sys.path.insert(0, str(RBDTECTOR_SRC))

# 2. Динамический путь для CAISR (ОБЯЗАТЕЛЬНО ДЛЯ СБОРКИ)
CAISR_SRC = _Path(resource_path("CAISR-App-main"))
if str(CAISR_SRC) not in sys.path:
    sys.path.insert(0, str(CAISR_SRC))
# ---------------------------------------------------------------------------

Electrode = namedtuple('Electrode', ['name', 'x_ratio', 'y_ratio', 'is_selectable', 'label_side'])

E_MAP = {
    "F3": ("left", "F"),
    "F4": ("right", "F"),
    "C3": ("left", "C"),
    "C4": ("right", "C"),
    "O1": ("left", "O"),
    "O2": ("right", "O")
}

# --- Splash Screen Animation ---
class SplashAnimation(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True) 
        
        # =================================================================
        # НАСТРОЙКИ ОКНА ЗАГРУЗКИ И ВИДЕО
        # =================================================================
        self.w = 460  # Ширина окна
        self.h = 280  # Высота окна

        self.crop_x = -200        # Отступ слева (Координата X левого верхнего угла)
        self.crop_y = -450       # Отступ сверху (Координата Y левого верхнего угла)
        self.crop_width = 1920  # Ширина вырезаемой области
        self.crop_height = 1080 # Высота вырезаемой области
        # =================================================================

        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws/2) - (self.w/2)
        y = (hs/2) - (self.h/2)
        self.geometry(f'{self.w}x{self.h}+{int(x)}+{int(y)}')
        
        self.trans_color = "#ff00ff"    
        self.corner_radius = 18        

        text_main = "#0369a1"      
        text_sub = "#64748b"       
        
        self.configure(bg=self.trans_color)
        try:
            self.wm_attributes("-transparentcolor", self.trans_color)
        except Exception:
            pass

        self.canvas = tk.Canvas(self, width=self.w, height=self.h, bg=self.trans_color, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.bg_canvas_id = self.canvas.create_image(0, 0, anchor="nw")
        
        self.mask = Image.new("L", (self.w, self.h), 0)
        mask_draw = ImageDraw.Draw(self.mask)
        mask_draw.rounded_rectangle([1, 1, self.w-2, self.h-2], radius=self.corner_radius, fill=255)

        video_filename = "splash.mp4"
        video_path = resource_path(video_filename)
        
        self.cap = None
        if cv2 is not None and Path(video_path).exists():
            self.cap = cv2.VideoCapture(str(video_path))
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.video_delay = int(1000 / fps) if fps > 0 else 30
        else:
            self.video_delay = 30
            print(f"Could not load video {video_filename}")

        text_white = "#EEEEEE"     
        text_glow = "#001a33"      
        
        init_text = ""
        offset_bottom = 30 
        
        self.status_text_shadow = self.canvas.create_text(20+1, self.h - offset_bottom + 1, text=init_text, font=(FONT_FAMILY_UI, 12, "italic","bold"), fill=text_glow, anchor="sw", justify="left")
        self.status_text = self.canvas.create_text(20, self.h - offset_bottom, text=init_text, font=(FONT_FAMILY_UI, 12, "italic","bold"), fill=text_white, anchor="sw", justify="left")
        
        self.tick_count = 0
        self.anim_id = None
        self._animate()

    def _animate(self):
        if not self.winfo_exists(): return
        
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
            
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                vh, vw, _ = frame.shape
                
                x1 = self.crop_x
                y1 = self.crop_y
                x2 = x1 + self.crop_width
                y2 = y1 + self.crop_height
                
                x1 = max(0, min(x1, vw - 1))
                y1 = max(0, min(y1, vh - 1))
                x2 = max(x1 + 1, min(x2, vw))
                y2 = max(y1 + 1, min(y2, vh))
                
                frame = frame[y1:y2, x1:x2]

                frame = cv2.resize(frame, (self.w, self.h))
                img = Image.fromarray(frame)
                
                final_img = Image.new("RGBA", (self.w, self.h), self.trans_color)
                final_img.paste(img, (0, 0), self.mask)
                
                draw_b = ImageDraw.Draw(final_img)
                draw_b.rounded_rectangle([4, 4, self.w-5, self.h-5], radius=self.corner_radius, fill=None, outline="#3b82f6", width=0)
                
                self.bg_photo = ImageTk.PhotoImage(final_img)
                self.canvas.itemconfig(self.bg_canvas_id, image=self.bg_photo)
        
        self.tick_count += 1
        if self.tick_count % 10 == 0: 
            dots = "." * ((self.tick_count // 10) % 4)
            new_text = f"" 
            self.canvas.itemconfig(self.status_text, text=new_text)
            self.canvas.itemconfig(self.status_text_shadow, text=new_text)

        self.anim_id = self.after(self.video_delay, self._animate)

    def stop(self):
        if self.anim_id:
            self.after_cancel(self.anim_id)
        if self.cap:
            self.cap.release()
        self.destroy()


# --- Redirector class ---
class StdoutRedirector:
    def __init__(self, app_instance, is_stderr=False):
        self.app = app_instance
        self.is_stderr = is_stderr
        self.terminal = sys.stderr if is_stderr else sys.stdout

    def write(self, message):
        if self.terminal is not None:
            try:
                self.terminal.write(message)
            except Exception:
                pass
        
        # DEBUG LOGGING (Writes to file unconditionally so we can see where it freezes)
        try:
            with open(r"C:\Users\ynirmfa\Desktop\debug_log.txt", "a", encoding="utf-8") as f:
                f.write(message)
        except Exception:
            pass

        msg_str = message.strip()
        if not msg_str:
            return

        is_detailed = self.app.detailed_log_var.get()

        if is_detailed:
            # Детальный лог ВКЛЮЧЕН: Показываем всё подряд
            tag = "error" if self.is_stderr else None
            lower_msg = msg_str.lower()
            if not tag:
                if "error" in lower_msg or "failed" in lower_msg or "traceback" in lower_msg:
                    tag = "error"
                elif "warning" in lower_msg:
                    tag = "warning"
            
            self.app._ui(lambda m=msg_str, t=tag: self.app.log_write(m, tag=t))
            
            if not self.is_stderr:
                self.app.guess_progress(msg_str, print_clean_text=False)
        else:
            # Детальный лог ВЫКЛЮЧЕН: Игнорируем весь спам
            # Мы перехватываем только ключевые слова для индикации этапа (guess_progress)
            if not self.is_stderr:
                self.app.guess_progress(msg_str, print_clean_text=True)

    def flush(self):
        if self.terminal is not None:
            try:
                self.terminal.flush()
            except Exception:
                pass

class HeadPicker(tk.Canvas):
    def __init__(self, master, *, on_pick, width=380, height=360, **kwargs):
        super().__init__(master, width=width, height=height, bg="#fafafa", highlightthickness=0, **kwargs)
        self.on_pick = on_pick
        self.selected_node = "C4" 
        self._items = {} 
        self.photo = None 
        self.is_disabled = False 

        available_subset = {'F3', 'F4', 'C3', 'C4', 'O1', 'O2'}

        all_electrodes_raw = [
            ("Nasion", 0.5, 0.05, False, "F"),
            ("Inion", 0.5, 0.95, False, "B"),
            ("Fp1", 0.35, 0.15, False, ""),
            ("Fp2", 0.65, 0.15, False, ""),
            ("F7", 0.15, 0.28, False, ""),
            ("F3", 0.32, 0.32, True, ""),
            ("Fz", 0.50, 0.28, False, ""),
            ("F4", 0.68, 0.32, True, ""),
            ("F8", 0.85, 0.28, False, ""),
            ("T3", 0.08, 0.50, False, ""),
            ("C3", 0.28, 0.50, True, ""),
            ("Cz", 0.50, 0.50, False, ""),
            ("C4", 0.72, 0.50, True, ""),
            ("T4", 0.92, 0.50, False, ""),
            ("T5", 0.15, 0.72, False, ""),
            ("P3", 0.32, 0.68, False, ""),
            ("Pz", 0.50, 0.72, False, ""),
            ("P4", 0.68, 0.68, False, ""),
            ("T6", 0.85, 0.72, False, ""),
            ("O1", 0.35, 0.85, True, ""),
            ("O2", 0.65, 0.85, True, ""),
        ]

        self.nodes = [Electrode(name=raw[0], x_ratio=raw[1], y_ratio=raw[2], 
                                is_selectable=(raw[0] in available_subset), label_side=raw[4]) 
                      for raw in all_electrodes_raw]

        self.bind("<Button-1>", self.on_click)
        self.bind("<Configure>", lambda e: self._draw())

    def set_disabled(self, disabled: bool):
        self.is_disabled = disabled
        self._draw()

    def set_selected(self, side: str, site_code: str) -> None:
        for k, v in E_MAP.items():
            if v == (side, site_code):
                self.selected_node = k
                self._draw()
                break

    def get_display_label(self, side: str, site_code: str) -> str:
        for k, v in E_MAP.items():
            if v == (side, site_code):
                return k
        return f"{site_code}?"

    def _draw(self):
        self.delete("all")
        self._items = {}
        
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10 or h < 10: 
            w, h = 380, 360 

        sf = 3 
        sw, sh = w * sf, h * sf

        img = Image.new('RGBA', (sw, sh), "#fafafa")
        draw = ImageDraw.Draw(img)

        canvas_size = min(w, h)
        scale = canvas_size * 0.9 
        pad_x = (w - scale) / 2
        pad_y = (h - scale) / 2

        def get_coords(rx, ry):
            return rx * scale + pad_x, ry * scale + pad_y

        def get_pil_coords(rx, ry):
            return (rx * scale + pad_x) * sf, (ry * scale + pad_y) * sf

        center_head_y = (0.50 * scale + pad_y) * sf
        head_radius = 0.45 * scale * sf
        ear_radius = 0.05 * scale * sf

        a1_x, a1_y = get_pil_coords(0.04, 0.50)
        draw.ellipse([a1_x - ear_radius, a1_y - ear_radius, a1_x + ear_radius, a1_y + ear_radius], 
                     outline="#a0a0a0", width=2*sf, fill="white")
        
        a2_x, a2_y = get_pil_coords(0.96, 0.50)
        draw.ellipse([a2_x - ear_radius, a2_y - ear_radius, a2_x + ear_radius, a2_y + ear_radius], 
                     outline="#a0a0a0", width=2*sf, fill="white")
        
        nasion_x, nasion_y = get_pil_coords(0.5, 0.05)
        nose_w = 0.05 * scale * sf
        draw.polygon([nasion_x - nose_w, nasion_y + ear_radius,
                      nasion_x, nasion_y,
                      nasion_x + nose_w, nasion_y + ear_radius], fill="white")
        draw.line([nasion_x - nose_w, nasion_y + ear_radius, nasion_x, nasion_y, nasion_x + nose_w, nasion_y + ear_radius], 
                  fill="#a0a0a0", width=2*sf, joint="curve")

        main_h_x, _ = get_pil_coords(0.5, 0.50)
        draw.ellipse([main_h_x - head_radius, center_head_y - head_radius,
                      main_h_x + head_radius, center_head_y + head_radius], outline="#a0a0a0", width=2*sf, fill="white")

        draw.line([nasion_x, nasion_y + nose_w + 5*sf, nasion_x, center_head_y + head_radius - 5*sf], fill="#e8e8e8", width=1*sf)
        draw.line([a1_x + ear_radius + 5*sf, a1_y, a2_x - ear_radius - 5*sf, a2_y], fill="#e8e8e8", width=1*sf)
        
        inner_rad_w = head_radius * 0.76
        inner_rad_h = head_radius * 0.70
        draw.ellipse([main_h_x - inner_rad_w, center_head_y - inner_rad_h,
                      main_h_x + inner_rad_w, center_head_y + inner_rad_h], outline="#e8e8e8", width=1*sf)

        node_radius = canvas_size * 0.038 * sf

        for node in self.nodes:
            if node.name in ("Nasion", "Inion"): continue

            px, py = get_pil_coords(node.x_ratio, node.y_ratio)
            tx, ty = get_coords(node.x_ratio, node.y_ratio)

            fill_color = "#ffffff"
            outline_color = "#b0b0b0"
            outline_width = 1 * sf

            if node.is_selectable:
                if node.name == self.selected_node:
                    fill_color = "#005fb8"
                    outline_color = "#004e98"
                    outline_width = 2 * sf
                else:
                    fill_color = "#e0f0ff"
            
            draw.ellipse([px - node_radius, py - node_radius, px + node_radius, py + node_radius], 
                         fill=fill_color, outline=outline_color, width=outline_width)
            
            if node.is_selectable:
                self._items[node.name] = (tx, ty, node_radius / sf)

        if getattr(self, 'is_disabled', False):
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            
            dim_color = (220, 220, 220, 190) 
            
            overlay_draw.ellipse([a1_x - ear_radius, a1_y - ear_radius, a1_x + ear_radius, a1_y + ear_radius], fill=dim_color)
            overlay_draw.ellipse([a2_x - ear_radius, a2_y - ear_radius, a2_x + ear_radius, a2_y + ear_radius], fill=dim_color)
            
            overlay_draw.polygon([nasion_x - nose_w, nasion_y + ear_radius,
                                  nasion_x, nasion_y,
                                  nasion_x + nose_w, nasion_y + ear_radius], fill=dim_color)
                                  
            overlay_draw.ellipse([main_h_x - head_radius, center_head_y - head_radius,
                                  main_h_x + head_radius, center_head_y + head_radius], fill=dim_color)

            img = Image.alpha_composite(img, overlay)

        img_resized = img.resize((w, h), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(img_resized)
        
        self.create_image(0, 0, image=self.photo, anchor="nw")

        font_size = max(8, int(canvas_size / 45)) 
        caption_font = (FONT_FAMILY_UI, font_size, "bold")

        for node in self.nodes:
            tx, ty = get_coords(node.x_ratio, node.y_ratio)

            if node.name == "Nasion":
                self.create_text(tx, ty - (nose_w/sf)/2 - 3, text="NASION", font=caption_font, fill="#a0a0a0", anchor="s")
                continue
            if node.name == "Inion":
                self.create_text(tx, ty + (node_radius/sf)/2 + 3, text="INION", font=caption_font, fill="#a0a0a0", anchor="n")
                continue
            
            text_color = "#a0a0a0"
            font_weight = "normal"

            if node.is_selectable:
                if node.name == self.selected_node:
                    text_color = "#ffffff"
                    font_weight = "bold"
                else:
                    text_color = "#000000"
                    font_weight = "bold"

            if getattr(self, 'is_disabled', False):
                text_color = "#999999"

            e_font = (FONT_FAMILY_UI, font_size, font_weight)
            
            if node.label_side:
                anchor = "w" if node.label_side == "L" else "e" if node.label_side == "R" else "s" if node.label_side == "F" else "n"
                offset = (node_radius/sf) + 2
                if anchor == "w": tx += offset
                if anchor == "e": tx -= offset
                if anchor == "n": ty += offset
                if anchor == "s": ty -= offset
                self.create_text(tx, ty, text=node.name, font=e_font, fill=text_color, anchor=anchor, justify="center")
            else:
                self.create_text(tx, ty, text=node.name, font=e_font, fill=text_color)

    def on_click(self, event):
        if getattr(self, 'is_disabled', False):
            return

        w, h = self.winfo_width(), self.winfo_height()
        canvas_size = min(w, h)
        hit_radius = canvas_size * 0.05 

        clicked_node = None
        for name, (ex, ey, rad) in self._items.items():
            distance = sqrt((event.x - ex)**2 + (event.y - ey)**2)
            if distance < hit_radius:
                clicked_node = name
                break 
        
        if clicked_node and clicked_node != self.selected_node:
            self.selected_node = clicked_node
            self._draw() 
            if self.on_pick and clicked_node in E_MAP:
                side, site = E_MAP[clicked_node]
                self.on_pick(side, site)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.withdraw()
        self.splash = SplashAnimation(self)
        
        self.title("Sleep Report Generator")
        self.geometry("1340x880") 
        try:
            icon_path = resource_path("ynir.ico")
            self.iconbitmap(icon_path)
        except Exception as e:
            pass
        try:
            sv_ttk.set_theme("light")
        except:
            pass

        self.mff_paths_list = []  
        self.append_pdf_path = tk.StringVar(value="") 
        self.montage_display = tk.StringVar(value="Adults E256")
        self.side = tk.StringVar(value="right")
        self.site = tk.StringVar(value="C")
        self.subject_age = tk.StringVar(value="60")
        self.sex = tk.StringVar(value="F")
        self.subject_name = tk.StringVar(value="")
        self.detailed_log_var = tk.BooleanVar(value=False) # ГАЛОЧКА ДЛЯ ЛОГОВ
        self.anchor_dir = tk.StringVar(value="")

        self.outdir_last: Path | None = None
        self.last_result: dict | None = None
        
        self.current_progress = 0
        self._is_busy = False
        self.start_time = 0.0
        self._pulse_id = None
        self.worker_thread = None 
        
        self.primary_scoring = tk.StringVar(value="YASA")

        style = ttk.Style()
        style.configure("Accent.TButton", font=(FONT_FAMILY_UI, 10, "bold"))
        style.configure("Danger.TButton", font=(FONT_FAMILY_UI, 10, "bold"), foreground="#005fb8")
        self._build_ui()
        self._load_config()
        
        threading.Thread(target=self._perform_heavy_imports, daemon=True).start()

    def _perform_heavy_imports(self):
        try:
            import mne
            import yasa
            import pipeline
        except Exception as e:
            print(f"Error during background import: {e}")
        finally:
            self.after(0, self._on_loaded)

    def _on_loaded(self):
        self.splash.stop()
        self.deiconify() 

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=20) 
        root.pack(fill="both", expand=True)

        inputs_frame = ttk.LabelFrame(root, text=" Input Data Sources ", padding=12)
        inputs_frame.pack(fill="x", pady=(0, 15))

        inputs_frame.columnconfigure(1, weight=1)

        ttk.Label(inputs_frame, text="MFF parts:").grid(row=0, column=0, sticky="nw", pady=(0, 10))
        
        list_frame = ttk.Frame(inputs_frame)
        list_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=(0, 10))
        
        self.mff_listbox = tk.Listbox(list_frame, height=2, selectmode="extended", font=(FONT_FAMILY_UI, 9))
        self.mff_listbox.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.mff_listbox.yview)
        scroll.pack(side="right", fill="y")
        self.mff_listbox.config(yscrollcommand=scroll.set)
        
        btn_frame = ttk.Frame(inputs_frame)
        btn_frame.grid(row=0, column=2, sticky="ns", pady=(0, 10))
        
        self.add_mff_btn = ttk.Button(btn_frame, text="Browse...", width=12, command=self.add_mff_part)
        self.add_mff_btn.pack(fill="x", pady=(0, 2))
        
        self.clear_mff_btn = ttk.Button(btn_frame, text="Clear", width=12, command=self.clear_mff_parts, state="disabled")
        self.clear_mff_btn.pack(fill="x")

        ttk.Label(inputs_frame, text="WatchPAT report file:").grid(row=1, column=0, sticky="w")
        ttk.Entry(inputs_frame, textvariable=self.append_pdf_path).grid(row=1, column=1, sticky="ew", padx=10)
        
        self.pdf_browse_btn = ttk.Button(inputs_frame, text="Browse...", width=12, command=self.pick_pdf)
        self.pdf_browse_btn.grid(row=1, column=2, sticky="w")

        meta = ttk.LabelFrame(root, text=" Patient and Scoring Configuration ", padding=12)
        meta.pack(fill="x", pady=(0, 15))

        ttk.Label(meta, text="EEG set:").grid(row=0, column=0, sticky="w")
        montage_box = ttk.Combobox(meta, textvariable=self.montage_display, values=["Adults E256", "Kids E128"], width=10, state="readonly")
        montage_box.grid(row=0, column=1, sticky="w", padx=(6, 12))
        montage_box.bind("<<ComboboxSelected>>", lambda e: self._on_montage_changed())

        ttk.Label(meta, text="Patient Name:").grid(row=0, column=2, sticky="w")
        name_entry = ttk.Entry(meta, textvariable=self.subject_name, width=24)
        name_entry.grid(row=0, column=3, sticky="w", padx=(6, 12))

        ttk.Label(meta, text="Age:").grid(row=0, column=4, sticky="w")
        age_spin = ttk.Spinbox(meta, textvariable=self.subject_age, from_=1, to=120, increment=1, width=6, font=(FONT_FAMILY_UI, FONT_SIZE_BODY))
        age_spin.grid(row=0, column=5, sticky="w", padx=(6, 12))

        ttk.Label(meta, text="Sex:").grid(row=0, column=6, sticky="w")
        sex_box = ttk.Combobox(meta, textvariable=self.sex, values=["F", "M"], width=4, state="readonly")
        sex_box.grid(row=0, column=7, sticky="w", padx=(6, 12))

        ttk.Label(meta, text="Scoring:").grid(row=0, column=8, sticky="w")
        scoring_box = ttk.Combobox(meta, textvariable=self.primary_scoring, values=["YASA", "CAISR"], width=7, state="readonly")
        scoring_box.grid(row=0, column=9, sticky="w", padx=(6, 12))
        scoring_box.bind("<<ComboboxSelected>>", lambda e: self._on_scoring_changed())

        ttk.Label(meta, text="Base folder:").grid(row=0, column=10, sticky="w", padx=(6, 0))
        self.anchor_browse_btn = ttk.Button(meta, text="Browse...", command=self.pick_anchor_dir)
        self.anchor_browse_btn.grid(row=0, column=11, sticky="w", padx=(6, 0))

        body = ttk.Frame(root)
        body.pack(fill="both", expand=True, pady=(0, 0))

        left = ttk.Frame(body)
        left.pack(side="left", fill="y", padx=(0, 15)) 

        ttk.Label(left, text="Scalp 10-20 System", font=(FONT_FAMILY_UI, 11, "bold")).pack(anchor="w")
        ttk.Label(left, text="Select scoring electrode:", font=(FONT_FAMILY_UI, FONT_SIZE_BODY), foreground="#808080").pack(anchor="w", pady=(2,8))

        self.head = HeadPicker(left, on_pick=self.on_pick)
        self.head.pack(expand=True, fill="both")

        self.sel_lbl = ttk.Label(left, text=self.selection_text(), font=(FONT_FAMILY_UI, FONT_SIZE_TITLE, "bold"))
        self.sel_lbl.pack(anchor="w", pady=(12, 6))

        self.preview_btn = ttk.Button(left, text="Preview Signal", command=self.show_preview_window)
        self.preview_btn.pack(anchor="center", pady=(0, 15))

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=0)

        btn_open = ttk.Button(left, text="Open Output Directory", command=self.open_outdir)
        btn_open.pack(fill="x", pady=15)

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)

        btn_row = ttk.Frame(right)
        btn_row.pack(fill="x")
        
        self.run_btn = ttk.Button(btn_row, text="RUN PIPELINE", style="Accent.TButton", command=self.run_pipeline, width=18)
        self.run_btn.pack(side="left", anchor="n")
        
        self.stop_btn = ttk.Button(btn_row, text="STOP", style="Danger.TButton", command=self.stop_pipeline, state="disabled")
        self.stop_btn.pack(side="left", padx=10, anchor="n")
        
        # ДОБАВЛЕНА ГАЛОЧКА "Detailed Log"
        self.detailed_log_cb = ttk.Checkbutton(btn_row, text="Debug Log", variable=self.detailed_log_var)
        self.detailed_log_cb.pack(side="left", padx=(15, 0), pady=(3, 0), anchor="n")

        self.scoring_check_var = tk.BooleanVar(value=False)
        self.scoring_check_cb = ttk.Checkbutton(btn_row, text="Scoring Check", variable=self.scoring_check_var)
        self.scoring_check_cb.pack(side="left", padx=(15, 0), pady=(3, 0), anchor="n")

        progress_container = ttk.Frame(btn_row)
        progress_container.pack(side="right", fill="x", expand=True, padx=(10, 0))
        
        bar_row = ttk.Frame(progress_container)
        bar_row.pack(fill="x", expand=True)

        self.progress = ttk.Progressbar(bar_row, mode="indeterminate", length=160)
        self.progress.pack(side="left", fill="x", expand=True)

        self.status_var = tk.StringVar(value="Ready")
        self.pct_label = ttk.Label(bar_row, textvariable=self.status_var, font=(FONT_FAMILY_UI, 10, "bold"), foreground="black")
        self.pct_label.pack(side="left", padx=(10, 0))

        self.time_var = tk.StringVar(value="")
        self.time_label = ttk.Label(progress_container, textvariable=self.time_var, font=(FONT_FAMILY_UI, 8, "normal"), foreground="#808080")
        self.time_label.pack(side="right", anchor="e", padx=(10, 0))

        log_frame = ttk.Frame(right)
        log_frame.pack(fill="both", expand=True, pady=(10, 0))
        
        self.log = tk.Text(log_frame, height=36, wrap="word", bg="#f8fafc", fg="#334155", font=("Consolas", FONT_SIZE_BODY), highlightthickness=1, highlightbackground="#e2e8f0")
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        scrollbar.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=scrollbar.set)

        self.log.tag_config("error", foreground="#dc2626", font=("Consolas", FONT_SIZE_BODY, "bold"))
        self.log.tag_config("success", foreground="#16a34a", font=("Consolas", FONT_SIZE_BODY, "bold"))
        self.log.tag_config("warning", foreground="#d97706", font=("Consolas", FONT_SIZE_BODY, "bold"))
        self.log.tag_config("header", foreground="#0284c7", font=("Consolas", FONT_SIZE_BODY, "bold"))

        self.head.set_selected(self.side.get(), self.site.get())
        self._on_scoring_changed()

    def add_mff_part(self) -> None:
        p = filedialog.askdirectory(title="Select .mff data folder (Part)")
        if p:
            self.mff_paths_list.append(p)
            self.mff_listbox.insert("end", Path(p).name)
            self.log_write(f"Added MFF part: {Path(p).name}")
            
            if len(self.mff_paths_list) > 0:
                self.add_mff_btn.config(text="Add part")
                self.clear_mff_btn.config(state="normal")
            
            if len(self.mff_paths_list) == 1:
                mff_dir = Path(p)
                pdf_files = list(mff_dir.glob("*.pdf"))
                if pdf_files:
                    auto_pdf = pdf_files[0]
                    self.append_pdf_path.set(str(auto_pdf))
                    self.log_write(f"WatchPAT report file detected: {auto_pdf.name}")
                    self.pdf_browse_btn.config(state="disabled")

    def clear_mff_parts(self) -> None:
        self.mff_paths_list.clear()
        self.mff_listbox.delete(0, "end")
        self.append_pdf_path.set("")
        self.pdf_browse_btn.config(state="normal")
        
        self.add_mff_btn.config(text="Browse...")
        self.clear_mff_btn.config(state="disabled")
        
        self.log_write("Cleared MFF parts list.")

    def _on_scoring_changed(self) -> None:
        if self.primary_scoring.get() == "CAISR":
            self.head.set_disabled(True)
            self.sel_lbl.config(text="Configuration: CAISR Mode (Electrode selection disabled)")
        else:
            self.head.set_disabled(False)
            self.sel_lbl.config(text=self.selection_text())

    def show_preview_window(self):
        if not self.mff_paths_list:
            messagebox.showerror("Error", "Please add at least one MFF part first.")
            return

        self.preview_btn.config(style="TButton", state="disabled", text="Loading Preview...")
        
        mff_preview_path = self.mff_paths_list[0]
        montage_type = self.get_montage_type()
        side = self.side.get()
        site = self.site.get()

        def worker():
            try:
                import mne
                import random
                from pipeline import CFGS

                cfg = CFGS.get(montage_type, {}).get(side, {})
                target_ch = cfg.get(site)
                
                if not target_ch:
                    raise ValueError("Could not determine target channel for the selected montage.")

                from pipeline import safe_read_mff
                raw = safe_read_mff(mff_preview_path, preload=False, verbose=False)
                
                if target_ch not in raw.ch_names:
                    raise ValueError(f"Channel '{target_ch}' not found in the recording.")

                target_idx = raw.ch_names.index(target_ch)
                sfreq = raw.info['sfreq']
                total_time = raw.times[-1]
                
                if total_time < 10:
                    raise ValueError("Recording is shorter than 10 seconds.")

                starts = sorted([random.uniform(0, max(0, total_time - 10)) for _ in range(5)])
                
                plot_data = []
                for start in starts:
                    start_samp = int(start * sfreq)
                    stop_samp = int((start + 10) * sfreq)
                    
                    data, times = raw[target_idx, start_samp:stop_samp]
                    data_filtered = mne.filter.filter_data(data, sfreq, 0.5, 40, verbose=False)
                    
                    plot_data.append((times, data_filtered[0] * 1e6, start))
                
                self.after(0, lambda: self._render_preview(plot_data, target_ch))

            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._preview_error(err))

        threading.Thread(target=worker, daemon=True).start()

    def _preview_error(self, err_msg):
        self.preview_btn.config(state="normal", text="Preview Signal")
        self.log_write(f"Preview skipped/failed: {err_msg}", tag="warning")

    def _render_preview(self, plot_data, ch_name):
        self.preview_btn.config(state="normal", text="Preview Signal")
        
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        
        fig, axes = plt.subplots(5, 1, figsize=(7, 5.0), sharex=False, sharey=True)
        fig.subplots_adjust(hspace=0.8, left=0.1, right=0.95, top=0.90, bottom=0.08)
        fig.patch.set_facecolor('#f8fafc')

        for i, (times, data, start) in enumerate(plot_data):
            ax = axes[i]
            ax.plot(times, data, color='#0369a1', linewidth=1)

            ax.set_ylabel("µV", fontsize=9)
            ax.grid(True, linestyle=':', alpha=0.7)
            ax.set_facecolor('#ffffff')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

        canvas = FigureCanvasTkAgg(fig, master=self.log)
        canvas.draw()
        canvas_widget = canvas.get_tk_widget()

        canvas_widget.configure(
            highlightthickness=0, 
            borderwidth=0, 
            background="#f8fafc"
        )

        self.log.configure(state="normal")
        self.log.insert("end", "\n") 
        self.log.insert("end", f"[{ch_name} Signal Preview Generated]\n", "header")
        self.log.window_create("end", window=canvas_widget)
        self.log.insert("end", "\n\n")
        
        def _on_mousewheel(event):
            self.log.yview_scroll(int(-1*(event.delta/120)), "units")
            return "break"

        canvas_widget.bind("<MouseWheel>", _on_mousewheel)
        self.log.see("end") 
        self.log.configure(state="disabled")

    def get_montage_type(self) -> str:
        val = self.montage_display.get().strip()
        if val == "Kids E128":
            return "kids_e128"
        return "adult_e256"

    def selection_text(self) -> str:
        disp = self.head.get_display_label(self.side.get(), self.site.get())
        return f"Configuration: Hemispheric Side={self.side.get()}, Point={self.site.get()} (Label: {disp})"

    def on_pick(self, side: str, site_code: str) -> None:
        self.side.set(side)
        self.site.set(site_code)
        self.sel_lbl.config(text=self.selection_text())
        self.preview_btn.config(style="Accent.TButton")

    def pick_pdf(self) -> None:
        p = filedialog.askopenfilename(title="Select WatchPAT report file", filetypes=[("PDF files", "*.pdf")])
        if p:
            self.append_pdf_path.set(p)
            self.log_write(f"WatchPAT report file selected: {Path(p).name}")

    def pick_anchor_dir(self) -> None:
        p = filedialog.askdirectory(title="Select Anchor Base Folder")
        if p:
            self.anchor_dir.set(p)
            self.anchor_browse_btn.config(text=Path(p).name)
            self.log_write(f"Anchor Base Folder set to: {p}")
            self._save_config()

    def _save_config(self) -> None:
        try:
            import json
            config_path = Path.home() / ".ynir_sleep_app_config.json"
            data = {"anchor_dir": self.anchor_dir.get()}
            config_path.write_text(json.dumps(data), encoding="utf-8")
        except Exception as e:
            print(f"Error saving config: {e}")

    def _load_config(self) -> None:
        try:
            import json
            config_path = Path.home() / ".ynir_sleep_app_config.json"
            if config_path.exists():
                data = json.loads(config_path.read_text(encoding="utf-8"))
                saved_anchor = data.get("anchor_dir", "")
                if saved_anchor and Path(saved_anchor).exists():
                    self.anchor_dir.set(saved_anchor)
                    self.anchor_browse_btn.config(text=Path(saved_anchor).name)
        except Exception as e:
            print(f"Error loading config: {e}")

    def _ui(self, fn) -> None:
        self.after(0, fn)

    def log_write(self, msg: str, tag: str = None) -> None:
        self.log.configure(state="normal")
        if not msg.endswith('\n'):
            msg += '\n'
            
        if tag is None:
            lower_msg = msg.lower()
            if "error" in lower_msg or "failed" in lower_msg or "traceback" in lower_msg:
                tag = "error"
            elif "warning" in lower_msg or "skipped" in lower_msg:
                tag = "warning"
            elif "successfully" in lower_msg or "done" in lower_msg:
                tag = "success"
            elif "===" in msg or "---" in msg or "processing initiated" in lower_msg:
                tag = "header"

        if tag:
            self.log.insert("end", msg, tag)
        else:
            self.log.insert("end", msg)
            
        self.log.see("end")
        self.log.configure(state="disabled")

    def guess_progress(self, msg: str, print_clean_text: bool = True):
        s = msg.lower()
        val = None
        human_text = ""

        # Отлавливаем технические слова и превращаем в текст для человека
        if "reading 0" in s and self.current_progress < 10: 
            val = 10; human_text = "Loading and checking EDF/MFF data..."
        elif "applying prefilter" in s and self.current_progress < 20: 
            val = 20; human_text = "Applying digital filters (Bandpass & Notch)..."
        elif "exporting channels" in s and self.current_progress < 30: 
            val = 30; human_text = "Referencing and formatting EEG channels..."
        elif ("sleep staging" in s or "yasa stages saved" in s) and self.current_progress < 40: 
            val = 40; human_text = "Running Sleep Staging analysis..."
        elif "native python for limb" in s and self.current_progress < 50: 
            val = 50; human_text = "Running CAISR Limb Movement detection..."
        elif "running rbdtector" in s and self.current_progress < 60: 
            val = 60; human_text = "Running RBDtector (REM Sleep without Atonia)..."
        elif "generating spectralpipe" in s and self.current_progress < 70: 
            val = 70; human_text = "Generating Hypnogram and Spectrogram visuals..."
        elif "generating events atlas" in s and self.current_progress < 90: 
            val = 90; human_text = "Compiling final PDF Events Atlas..."

        # Если этап сменился - двигаем прогресс-бар и ПЕЧАТАЕМ нашу красивую фразу (если разрешено)
        if val and val > self.current_progress:
            self._ui(lambda v=val, txt=human_text, pt=print_clean_text: self._set_progress(v, txt if pt else ""))
            
        # Форсированный вывод для Recovery и Warning
        if "[recovery]" in s or "[warning]" in s:
            self._ui(lambda txt=msg: self.log_write(f" {txt}"))

    def _set_progress(self, val: int, text: str = ""):
        self.current_progress = val
        self.status_var.set(f"{self.current_progress}%")
        self._pulse_percentage()
        
        if text:
            self.log_write(f" {text}")

    def _pulse_percentage(self, step=0):
        colors = ["#005fb8", "#2b5797", "#4d5375", "#664e54", "black"]
        if hasattr(self, '_pulse_id') and self._pulse_id:
            self.after_cancel(self._pulse_id)
        if step < len(colors):
            self.pct_label.configure(foreground=colors[step])
            self._pulse_id = self.after(80, lambda: self._pulse_percentage(step + 1))
        else:
            self.pct_label.configure(foreground="black")
            self._pulse_id = None

    def _update_timer(self):
        if self._is_busy:
            elapsed = int(time.time() - self.start_time)
            mins, secs = divmod(elapsed, 60)
            self.time_var.set(f"Elapsed: {mins:02d}:{secs:02d}")
            self.after(1000, self._update_timer)

    def set_busy(self, busy: bool) -> None:
        if busy:
            self._is_busy = True
            self.run_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.current_progress = 0
            self.status_var.set("0%")
            self.progress.start(10)
            
            self.start_time = time.time()
            self.time_var.set("Elapsed: 00:00")
            self._update_timer()
        else:
            self._is_busy = False
            self.run_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self.progress.stop()

    def stop_pipeline(self) -> None:
        """Метод для прерывания текущего процесса обработки"""
        if not self._is_busy or not self.worker_thread:
            return
            
        confirm = messagebox.askyesno("Stop Processing", "Are you sure you want to stop the current analysis?")
        if not confirm:
            return
            
        self.log_write("\n[!] Stopping analysis by user request...", tag="error")
        self.status_var.set("Stopping...")
        self.stop_btn.config(state="disabled")
        
        # Используем ctypes для выбрасывания исключения внутри запущенного потока
        if self.worker_thread.is_alive():
            try:
                thread_id = ctypes.c_long(self.worker_thread.ident)
                res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, ctypes.py_object(InterruptedError))
                if res > 1:
                    ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
            except Exception as e:
                self.log_write(f"Warning: Could not terminate thread directly ({e})", tag="warning")
                
        self.set_busy(False)
        self.log_write("Analysis aborted.", tag="warning")

    def _open_path(self, path: str | Path) -> None:
        p = str(path)
        if not Path(p).exists():
            messagebox.showwarning("Warning", f"Directory not found:\n{p}")
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(p)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", p])
            else:
                subprocess.Popen(["xdg-open", p])
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def validate_scoring_channel(self, mff_path: str, montage_type: str, side: str, selected_site: str) -> tuple[bool, str]:
        import mne
        import numpy as np
        from pipeline import CFGS, safe_read_mff
        
        cfg = CFGS.get(montage_type, {}).get(side, {})
        if not cfg: return True, ""
        
        target_ch = cfg.get(selected_site)
        
        all_checks = []
        for s in ["left", "right"]:
            c = CFGS.get(montage_type, {}).get(s, {})
            all_checks.extend([c.get('F'), c.get('C'), c.get('O')])
        
        all_checks = list(set([c for c in all_checks if c])) 
        
        try:
            raw = safe_read_mff(mff_path, preload=False, verbose=False)
            sfreq = raw.info['sfreq']
            
            mid = raw.times[-1] / 2
            start_samp = int(mid * sfreq)
            stop_samp = int((mid + 120) * sfreq)
            
            picks = [raw.ch_names.index(ch) for ch in all_checks if ch in raw.ch_names]
            if not picks: return True, "Channels not found"
            
            data, times = raw[picks, start_samp:stop_samp]
            data_filtered = mne.filter.filter_data(data, sfreq, 0.5, 40, verbose=False)
            
            stds = np.std(data_filtered, axis=1)
            
            ch_names_picked = [raw.ch_names[i] for i in picks]
            target_idx_in_data = ch_names_picked.index(target_ch)
            target_std = stds[target_idx_in_data]
            
            if target_std < 1e-8: return False, "Channel is 'dead' (Flatline, SD < 0.01 µV)."
            if target_std > 150e-6: return False, f"Unreal amplitude (SD = {target_std*1e6:.1f} µV). Electrode detached?"

            other_stds = np.delete(stds, target_idx_in_data)
            median_other = np.median(other_stds)
            if target_std > (median_other * 4.0):
                return False, f"Channel is very noisy (SD is {target_std/median_other:.1f} times higher than neighbors)."
            
            return True, ""
        except Exception as e:
            print(f"[Warning] MNE Error during validation: {e}")
            print(f"[Warning] The MFF file appears to have a corrupted epochs.xml. The pipeline will attempt an automatic recovery.")
            return False, f"File is corrupted (MNE Error: {e}). Automatic recovery will run (this may take up to 20 minutes)."

    def _run_pipeline_compat(self, *, mff_paths: list, montage_type: str, side: str, site: str,
                             do_fix_epochs: bool, do_preview: bool, do_rbd: bool, do_report: bool,
                             do_docx: bool, age_val: int | None, sex: str | None, subject_name: str, append_pdf: str | None, primary_scoring: str, anchor_dir: str | None = None):
        
        from pipeline import mff_yasa_sleepeegpy_combo
        
        params = inspect.signature(mff_yasa_sleepeegpy_combo).parameters
        kwargs: dict = {
            "side": side,
            "site": site,
            "verbose": True,
        }

        def put(old_name: str, new_name: str, value):
            if new_name in params: kwargs[new_name] = value
            elif old_name in params: kwargs[old_name] = value

        if "step" in params: kwargs["step"] = 1000
        if "max_k" in params: kwargs["max_k"] = 5000
        elif "maxk" in params: kwargs["maxk"] = 5000

        if "montage_type" in params: kwargs["montage_type"] = montage_type
        elif "electrode_set" in params: kwargs["electrode_set"] = montage_type
        elif "cfg_name" in params: kwargs["cfg_name"] = montage_type

        put("runrbdtectorheadless", "run_rbdtector_headless", True)
        put("makesleepreport", "make_sleep_report", True)
        put("makedocxreport", "make_docx_report", True)
        put("fixepochsendtime", "fix_epochs_endtime", True)
        put("showpreview", "show_preview", do_preview)
        put("anchor_dir", "anchor_dir", anchor_dir)
        put("scoring_check", "scoring_check", self.scoring_check_var.get())

        put("readrawkwargs", "read_raw_kwargs", {})
        put("subjectage", "subject_age", age_val)
        put("useyasaartdetect", "use_yasa_art_detect", True)
        put("yasaartepochsec", "yasa_art_epoch_sec", 30)
        put("yasaartwindow", "yasa_art_window", 5)
        put("yasaartmethod", "yasa_art_method", "covar")
        put("yasaartthreshold", "yasa_art_threshold", 2.5)
        put("yasaartinclude", "yasa_art_include", (0, 1, 2, 3, 4))
        put("append_pdf_path", "append_pdf_path", append_pdf if append_pdf else None)
        put("primary_scoring", "primary_scoring", primary_scoring)

        if "sex" in params: kwargs["sex"] = sex if do_docx else None

        if "subject_name" in params: kwargs["subject_name"] = subject_name

        return mff_yasa_sleepeegpy_combo(mff_paths, **kwargs)

    def run_pipeline(self) -> None:
        if not self.mff_paths_list:
            messagebox.showerror("Error", "Please add at least one MFF part before proceeding.")
            return

        age_raw = self.subject_age.get().strip()
        sex = self.sex.get().strip().upper() or "F"
        subject_name = self.subject_name.get().strip()
        montage_type = self.get_montage_type()
        append_pdf = self.append_pdf_path.get().strip()
        primary_scoring = self.primary_scoring.get().strip()
        anchor_dir = self.anchor_dir.get().strip() or None

        try: 
            age_val = int(age_raw)
        except Exception:
            messagebox.showerror("Validation Error", "Patient Age must be an integer.")
            return

        side = self.side.get()
        site = self.site.get()

        self.show_preview_window()

        self.log_write("\n" + "-"*30)
        self.log_write(f"Processing initiated for {len(self.mff_paths_list)} part(s).")
        self.log_write("-" *30)

        self.set_busy(True)

        def worker() -> None:
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = StdoutRedirector(self, is_stderr=False)
            sys.stderr = StdoutRedirector(self, is_stderr=True)

            try:
                self.log_write("Running signal quality validation on the first part...")
                is_ok, reason = self.validate_scoring_channel(str(self.mff_paths_list[0]), montage_type, side, site)
                
                if not is_ok:
                    self.log_write(f"WARNING: {reason}", tag="warning")
                    self._ui(lambda: self.set_busy(False))
                    
                    msg = (f"Warning: Selected electrode {site} ({side}) looks bad.\n"
                           f"Reason: {reason}\n\nContinue analysis with this electrode?\n"
                           "(Yes - proceed, No - abort and select another one)")
                    
                    proceed = messagebox.askyesno("Signal Quality Warning", msg)
                    
                    if not proceed:
                        self.log_write("Run aborted by user to select a new electrode.")
                        return
                    else:
                        self.log_write("User chose to proceed with the current electrode.")
                        self._ui(lambda: self.set_busy(True))
                else:
                    self.log_write("Validation passed: the channel appears to be working properly.", tag="success")

                # ==========================================
                # 1. ЗАПУСК ЕДИНОГО ПАЙПЛАЙНА
                # ==========================================
                res = self._run_pipeline_compat(
                    mff_paths=self.mff_paths_list, montage_type=montage_type, side=side, site=site,
                    do_fix_epochs=True, do_preview=False, do_rbd=True,
                    do_report=True, do_docx=True, age_val=age_val, sex=sex,
                    subject_name=subject_name, append_pdf=append_pdf, primary_scoring=primary_scoring, anchor_dir=anchor_dir
                )

                outdir = Path((res.get("paths", {}) or {}).get("outdir", Path(self.mff_paths_list[0]).parent))
                self.outdir_last = outdir
                self.last_result = res
                
                paths_dict = res.get("paths", {}) or {}
                sleep_stats = res.get("sleep_stats") or res.get("sleepstats") or res.get("sleep_stats_fmt")
                summary = res.get("summary")
                
                # --- MEMORY CLEANUP (Option 1) ---
                self.log_write("Freeing RAM...")
                for key in ["raw_min_loaded", "raw_export", "raw_yasa", "hyp", "hypno_1hz_int", "hypno_int_30s"]:
                    res.pop(key, None)
                
                import gc
                import matplotlib.pyplot as plt
                plt.close('all')  # clear all cached plots
                gc.collect()      # force python to release unused RAM
                self.log_write("RAM cleanup complete.")
                # ---------------------------------
                
                # ==========================================
                # 3. ФОРМИРОВАНИЕ ФИНАЛЬНОГО ОТЧЕТА В ЛОГАХ
                # ==========================================
                def report_success() -> None:
                    self._set_progress(100)
                    self.log_write("\n" + "="*35, tag="header")
                    self.log_write("ANALYSIS COMPLETED SUCCESSFULLY", tag="success")
                    self.log_write("="*35, tag="header")
                    self.log_write(f"Results have been generated in directory:\n   {outdir}\n")

                    self.log_write("Generated Result Files:")
                    for k, v in paths_dict.items():
                        if v:
                            clean_name = k.replace('_', ' ').title()
                            self.log_write(f"  * {clean_name}: {Path(v).name}")

                    self.log_write("\nKey Sleep Metrics:")
                    if sleep_stats:
                        for k, v in sleep_stats.items(): self.log_write(f"  * {k}: {v}")
                    else: self.log_write("  (Metrics not generated for this configuration)")

                    self.log_write("\nSleep Stage Distribution (Epochs and Percentage):")
                    if summary is not None:
                        try:
                            for idx, row in summary.iterrows():
                                stage_names = {"W": "Waking", "N1": "N1 (Light)", "N2": "N2 (Light)", "N3": "N3 (Deep)", "REM": "REM"}
                                stage_desc = stage_names.get(idx, idx)
                                self.log_write(f"  * {stage_desc}: {int(row['epochs'])} Epochs ({row['percent']:.1f}%)")
                        except Exception: pass

                    if res.get("rbdtector"): self.log_write(f"\nRBDtector case analysis completed.\n")
                    
                    if res.get("plm_metrics") is not None:
                        self.log_write(f"CAISR NREM event parsing completed.\n")
                        self.log_write(f"Note: Limb movements successfully detected and filtered by AASM criteria.\n")
                    else:
                        self.log_write(f"\n[!] CAISR LIMB DETECTION PRODUCED NO OUTPUT", tag="warning")

                    self.status_var.set("100%")
                    
                    dlg = tk.Toplevel(self)
                    dlg.title("Done")
                    try:
                        dlg.iconbitmap(resource_path("ynir.ico"))
                    except Exception: pass
                    dlg.geometry("450x200")
                    dlg.transient(self)
                    dlg.grab_set()
                    
                    ttk.Label(dlg, text=f"Analysis completed successfully!\n\nResults generated in:\n{outdir}", justify="center").pack(pady=20)
                    
                    btn_frame = ttk.Frame(dlg)
                    btn_frame.pack(pady=10)
                    
                    def on_open():
                        dlg.destroy()
                        self._open_path(outdir)
                        
                    ttk.Button(btn_frame, text="Open Folder", command=on_open).pack(side="left", padx=10)
                    ttk.Button(btn_frame, text="OK", command=dlg.destroy).pack(side="left", padx=10)
                    
                    dlg.update_idletasks()
                    x = self.winfo_x() + (self.winfo_width() - dlg.winfo_width()) // 2
                    y = self.winfo_y() + (self.winfo_height() - dlg.winfo_height()) // 2
                    dlg.geometry(f"+{x}+{y}")
                    
                    self.clear_mff_parts()

                self._ui(report_success)

            except InterruptedError:
                # Исключение, которое мы выбрасываем через ctypes кнопкой Stop
                self.log_write("\n[!] Processing was successfully stopped.", tag="error")
                self._ui(lambda: self.status_var.set("Aborted"))
            except Exception:
                # В случае РЕАЛЬНОГО фатального падения программы, мы всегда пишем ошибку,
                # даже если Detailed Log выключен! (потому что мы напрямую зовем log_write)
                tb = traceback.format_exc()
                self.log_write("\nFATAL ERROR IN PIPELINE:\n" + tb, tag="error")
                self._ui(lambda: self.status_var.set("Error!"))
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                self._ui(lambda: self.set_busy(False))

        # Сохраняем ссылку на поток, чтобы потом убить его через кнопку STOP
        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()

    def open_outdir(self) -> None:
        if not self.outdir_last or not self.outdir_last.exists():
            messagebox.showwarning("Warning", "Output directory not found.")
            return
        self._open_path(self.outdir_last)

if __name__ == "__main__":

    import multiprocessing
    multiprocessing.freeze_support()

    app = App()
    app.mainloop()