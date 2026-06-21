#!/usr/bin/env python3
"""
路点到达弹窗 — 到达路点 1 时显示当前使用的路径编号。
独立进程运行，通过 subprocess 调用，kill 时关闭。
用法: python3 waypoint_popup.py <number>
"""

import sys
import signal
import tkinter as tk


def show_popup(number: int):
    """全屏弹窗，显示大号数字"""
    root = tk.Tk()
    root.title(f'路径 {number}')

    # 白色背景
    root.configure(bg='white')

    # 全屏
    root.attributes('-fullscreen', True)

    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()

    # 大号数字，按屏幕高度缩放
    font_size = max(120, min(sh // 2, 400))

    # ---- 数字 ----
    num_label = tk.Label(
        root,
        text=str(number),
        font=('Arial', font_size, 'bold'),
        bg='white',
        fg='black',
    )
    num_label.place(relx=0.5, rely=0.45, anchor='center')

    # ---- 底部文字 ----
    info_label = tk.Label(
        root,
        text=f'题目答案: {number}',
        font=('Arial', max(20, min(sh // 30, 48))),
        bg='white',
        fg='#555555',
    )
    info_label.place(relx=0.5, rely=0.65, anchor='center')

    # ---- 关闭按钮（右上角小按钮）----
    close_btn = tk.Button(
        root,
        text='✕',
        font=('Arial', 14),
        bg='#cccccc', fg='black',
        bd=0, padx=10, pady=2,
        command=lambda: sys.exit(0),
    )
    close_btn.place(relx=0.98, rely=0.02, anchor='ne')

    # ---- SIGTERM 优雅退出 ----
    def on_sigterm(signum, frame):
        root.destroy()
        sys.exit(0)

    signal.signal(signal.SIGTERM, on_sigterm)

    # 按 Esc 或 q 也可退出
    root.bind('<Escape>', lambda e: sys.exit(0))
    root.bind('<q>', lambda e: sys.exit(0))
    root.bind('<Q>', lambda e: sys.exit(0))

    root.mainloop()


def main():
    if len(sys.argv) < 2:
        print('用法: python3 waypoint_popup.py <number>', file=sys.stderr)
        sys.exit(1)

    try:
        number = int(sys.argv[1])
    except ValueError:
        print(f'错误: "{sys.argv[1]}" 不是有效数字', file=sys.stderr)
        sys.exit(1)

    show_popup(number)


if __name__ == '__main__':
    main()
