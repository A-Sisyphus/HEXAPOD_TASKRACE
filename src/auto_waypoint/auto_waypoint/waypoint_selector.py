#!/usr/bin/env python3
"""
路点路径选择器 UI
- 有 X11 显示时使用 Tkinter GUI
- 无 DISPLAY 时自动降级为终端菜单
- 返回所选配置 YAML 文件的完整路径
"""

import os
import sys


# ======================== 路径配置 ========================

CONFIG_FILES = [
    'waypoint_config0.yaml',
    'waypoint_config1.yaml',
    'waypoint_config2.yaml',
    'waypoint_config3.yaml',
]

CONFIG_LABELS = [
    'A',
    'B',
    'C',
    'D',
]


def _get_config_dir():
    """
    获取 config 目录的绝对路径。
    优先使用 ament_index，fallback 为相对路径。
    """
    try:
        from ament_index_python.packages import get_package_share_directory
        return os.path.join(
            get_package_share_directory('auto_waypoint'), 'config')
    except ImportError:
        pass

    # Fallback: 相对于本文件的路径
    # 本文件位于 .../auto_waypoint/auto_waypoint/waypoint_selector.py
    # config 位于 .../auto_waypoint/config/
    this_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(this_dir, '..', '..', 'config')


# ======================== 终端菜单 ========================

def show_terminal_selector():
    """终端交互式路径选择器（通过 SSH 也能用）"""
    config_dir = _get_config_dir()

    print()
    print('=' * 50)
    print('        ROBOCON 任务赛系统')
    print('=' * 50)
    for i, label in enumerate(CONFIG_LABELS):
        print(f'  [{i}] {label}')
    print('=' * 50)

    while True:
        try:
            choice = input('请输入路径编号 (0-3): ').strip()
            idx = int(choice)
            if 0 <= idx < len(CONFIG_FILES):
                selected = CONFIG_FILES[idx]
                config_path = os.path.join(config_dir, selected)
                print(f'\n已选择: {CONFIG_LABELS[idx]}')
                print(f'配置文件: {config_path}')
                return config_path
            else:
                print(f'无效选择，请输入 0-{len(CONFIG_FILES)-1}')
        except (ValueError, EOFError):
            print('无效输入，请输入数字')
        except KeyboardInterrupt:
            print('\n已取消')
            sys.exit(0)


# ======================== Tkinter GUI（触摸屏优化版）======================

# 路径按钮颜色（4 种区分色）
PATH_COLORS = ['#3498db', '#2ecc71', '#e67e22', '#9b59b6']
PATH_COLORS_SELECTED = ['#1a5276', '#1a7a3a', '#935116', '#5b2c6f']

# 路径编号（按钮上显示）
PATH_NUMS = ['A', 'B', 'C', 'D']


def show_gui_selector():
    """Tkinter 图形化路径选择器（触摸屏优化）"""
    import tkinter as tk

    config_dir = _get_config_dir()

    # ---- 主窗口（全屏）----
    root = tk.Tk()
    root.title('ROBOCON任务赛系统')
    root.configure(bg='#ecf0f1')

    # 获取屏幕尺寸，窗口占屏幕 95%
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    ww = int(sw * 0.95)
    wh = int(sh * 0.95)
    wx = (sw - ww) // 2
    wy = (sh - wh) // 2
    root.geometry(f'{ww}x{wh}+{wx}+{wy}')
    root.resizable(False, False)

    # 按比例计算字体和尺寸
    base_font_size = max(14, min(wh // 25, 32))
    btn_font_size = max(40, min(wh // 8, 80))
    confirm_font_size = max(28, min(wh // 15, 48))
    status_font_size = max(18, min(wh // 30, 28))

    selected_var = tk.StringVar(value=CONFIG_FILES[0])

    result = {'path': None}

    # ---- 标题 ----
    title_label = tk.Label(
        root, text='ROBOCON 任务赛系统',
        font=('Arial', base_font_size + 8, 'bold'),
        bg='#ecf0f1', fg='#2c3e50')
    title_label.pack(pady=int(wh * 0.04))

    # ---- 4 个路径大按钮（水平排列）----
    path_buttons_frame = tk.Frame(root, bg='#ecf0f1')
    path_buttons_frame.pack(
        expand=True, fill='both',
        padx=int(ww * 0.03), pady=int(wh * 0.02))

    # 让 4 个按钮等分宽度
    for i in range(4):
        path_buttons_frame.columnconfigure(i, weight=1, uniform='path')
    path_buttons_frame.rowconfigure(0, weight=1)

    path_btns = []

    def select_path(idx):
        """选中某个路径，更新按钮样式"""
        selected_var.set(CONFIG_FILES[idx])
        for j, btn in enumerate(path_btns):
            if j == idx:
                btn.configure(
                    bg=PATH_COLORS_SELECTED[j],
                    fg='white',
                    relief='sunken',
                    bd=6)
            else:
                btn.configure(
                    bg=PATH_COLORS[j],
                    fg='white',
                    relief='raised',
                    bd=3)

    for i in range(4):
        btn = tk.Button(
            path_buttons_frame,
            text=PATH_NUMS[i],
            font=('Arial', btn_font_size, 'bold'),
            bg=PATH_COLORS[i],
            fg='white',
            activebackground=PATH_COLORS_SELECTED[i],
            activeforeground='white',
            relief='raised',
            bd=3,
            cursor='hand2',
            command=lambda idx=i: select_path(idx),
        )
        btn.grid(row=0, column=i, sticky='nsew', padx=int(ww * 0.01), pady=int(wh * 0.01))
        path_btns.append(btn)

    # 默认选中第 0 个
    select_path(0)

    # ---- 状态提示 ----
    status_var = tk.StringVar(
        value=f'当前选择: {CONFIG_LABELS[0]}')
    status_label = tk.Label(
        root, textvariable=status_var,
        font=('Arial', status_font_size),
        bg='#ecf0f1', fg='#2c3e50')
    status_label.pack(pady=int(wh * 0.02))

    # 更新状态的回调
    def on_path_changed(*args):
        selected = selected_var.get()
        if selected in CONFIG_FILES:
            idx = CONFIG_FILES.index(selected)
            status_var.set(f'当前选择: {CONFIG_LABELS[idx]}')
            select_path(idx)

    selected_var.trace_add('write', on_path_changed)

    # ---- 确定 / 取消按钮 ----
    action_frame = tk.Frame(root, bg='#ecf0f1')
    action_frame.pack(pady=int(wh * 0.03), padx=int(ww * 0.05), fill='x')

    def on_confirm():
        selected = selected_var.get()
        config_path = os.path.join(config_dir, selected)
        result['path'] = config_path
        idx = CONFIG_FILES.index(selected)
        print(f'已选择: {CONFIG_LABELS[idx]}')
        root.destroy()

    def on_cancel():
        root.destroy()
        sys.exit(0)

    # 确定按钮（占 2/3 宽度）
    confirm_btn = tk.Button(
        action_frame,
        text='确  定',
        font=('Arial', confirm_font_size, 'bold'),
        bg='#27ae60', fg='white',
        activebackground='#1e8449', activeforeground='white',
        relief='raised', bd=3,
        cursor='hand2',
        command=on_confirm,
    )
    confirm_btn.pack(side='left', expand=True, fill='both',
                     padx=(0, int(ww * 0.01)), ipady=int(wh * 0.02))

    # 取消按钮（占 1/3 宽度）
    cancel_btn = tk.Button(
        action_frame,
        text='取  消',
        font=('Arial', confirm_font_size, 'bold'),
        bg='#7f8c8d', fg='white',
        activebackground='#616a6b', activeforeground='white',
        relief='raised', bd=3,
        cursor='hand2',
        command=on_cancel,
    )
    cancel_btn.pack(side='left', expand=True, fill='both',
                    padx=(int(ww * 0.01), 0), ipady=int(wh * 0.02))

    # ---- 关闭窗口 = 取消 ----
    root.protocol('WM_DELETE_WINDOW', on_cancel)

    # 让窗口获得焦点
    root.lift()
    root.focus_force()

    root.mainloop()

    if result['path'] is None:
        print('已取消选择')
        sys.exit(0)

    print(f'配置文件: {result["path"]}')
    return result['path']


# ======================== 自动选择入口 ========================

def show_selector():
    """
    自动检测环境并显示合适的选择器。
    有 DISPLAY → GUI 模式
    无 DISPLAY → 终端模式
    """
    has_display = bool(os.environ.get('DISPLAY', ''))
    if has_display:
        try:
            return show_gui_selector()
        except Exception as e:
            print(f'[Selector] GUI 启动失败 ({e})，切换到终端模式...')
            return show_terminal_selector()
    else:
        return show_terminal_selector()


def main():
    """独立运行入口"""
    path = show_selector()
    print(f'\n最终选择: {path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
