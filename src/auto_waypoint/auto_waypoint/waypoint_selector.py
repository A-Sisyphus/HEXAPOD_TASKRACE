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
    '路径 0 - 右侧巡逻 (y≈1.05)',
    '路径 1 - 直行右偏 (y≈0.25)',
    '路径 2 - 左侧巡逻 (y≈-0.65)',
    '路径 3 - 远端左侧 (y≈-1.45)',
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
    print('        路 点 路 径 选 择 器')
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


# ======================== Tkinter GUI ========================

def show_gui_selector():
    """Tkinter 图形化路径选择器"""
    import tkinter as tk
    from tkinter import ttk

    config_dir = _get_config_dir()

    # 主窗口
    root = tk.Tk()
    root.title('路点路径选择器')
    root.geometry('420x380')
    root.resizable(False, False)

    # 居中
    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f'{w}x{h}+{x}+{y}')

    selected_var = tk.StringVar(value=CONFIG_FILES[0])

    # 标题
    ttk.Label(
        root, text='请选择导航路径',
        font=('Arial', 16, 'bold')
    ).pack(pady=15)

    # Radio 选项区
    radio_frame = ttk.LabelFrame(root, text='可用路径', padding=10)
    radio_frame.pack(pady=5, padx=25, fill='x')

    for name, label in zip(CONFIG_FILES, CONFIG_LABELS):
        ttk.Radiobutton(
            radio_frame,
            text=label,
            variable=selected_var,
            value=name,
        ).pack(anchor='w', pady=4, padx=5)

    # 状态提示
    status_var = tk.StringVar(value='')
    status_label = ttk.Label(
        root, textvariable=status_var,
        foreground='gray', font=('Arial', 10))
    status_label.pack(pady=8)

    result = {'path': None}

    def on_confirm():
        selected = selected_var.get()
        config_path = os.path.join(config_dir, selected)
        result['path'] = config_path
        print(f'已选择: {CONFIG_LABELS[CONFIG_FILES.index(selected)]}')
        root.destroy()

    def on_cancel():
        root.destroy()
        sys.exit(0)

    # 按钮区
    button_frame = ttk.Frame(root)
    button_frame.pack(pady=15)

    ttk.Button(
        button_frame, text='✓  确 定',
        command=on_confirm, width=12
    ).pack(side='left', padx=10)

    ttk.Button(
        button_frame, text='✗  取 消',
        command=on_cancel, width=12
    ).pack(side='left', padx=10)

    # 关闭窗口 = 取消
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
