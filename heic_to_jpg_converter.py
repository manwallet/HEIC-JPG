#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
import queue
import pyheif
from PIL import Image
import time

class HeicToJpgConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("HEIC to JPG 转换器")
        self.root.geometry("700x500")
        self.root.resizable(True, True)
        
        # 设置窗口图标和样式
        self.style = ttk.Style()
        self.style.configure('TButton', font=('Arial', 10))
        self.style.configure('TLabel', font=('Arial', 10))
        
        # 创建用于线程间通信的队列
        self.queue = queue.Queue()
        
        # 创建和放置组件
        self.create_widgets()
        
        # 设置默认值
        self.input_dir_var.set(os.path.expanduser("~/Pictures"))
        self.output_dir_var.set(os.path.expanduser("~/Pictures/JPG_Output"))
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 转换状态标志
        self.is_converting = False
        self.conversion_thread = None
        
    def create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding=(20, 10))
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 输入目录选择
        input_frame = ttk.LabelFrame(main_frame, text="输入目录 (HEIC 文件)", padding=(10, 5))
        input_frame.pack(fill=tk.X, pady=5)
        
        self.input_dir_var = tk.StringVar()
        input_entry = ttk.Entry(input_frame, textvariable=self.input_dir_var, width=50)
        input_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        input_btn = ttk.Button(input_frame, text="选择目录", command=self.select_input_dir)
        input_btn.pack(side=tk.RIGHT, padx=5)
        
        # 输出目录选择
        output_frame = ttk.LabelFrame(main_frame, text="输出目录 (JPG 文件)", padding=(10, 5))
        output_frame.pack(fill=tk.X, pady=5)
        
        self.output_dir_var = tk.StringVar()
        output_entry = ttk.Entry(output_frame, textvariable=self.output_dir_var, width=50)
        output_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        output_btn = ttk.Button(output_frame, text="选择目录", command=self.select_output_dir)
        output_btn.pack(side=tk.RIGHT, padx=5)
        
        # 质量选择
        quality_frame = ttk.Frame(main_frame)
        quality_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(quality_frame, text="JPG 质量:").pack(side=tk.LEFT, padx=5)
        
        self.quality_var = tk.IntVar(value=90)
        quality_scale = ttk.Scale(quality_frame, from_=10, to=100, length=200,
                                  variable=self.quality_var, orient=tk.HORIZONTAL)
        quality_scale.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        quality_label = ttk.Label(quality_frame, textvariable=self.quality_var, width=3)
        quality_label.pack(side=tk.LEFT, padx=5)
        
        # 进度条
        progress_frame = ttk.LabelFrame(main_frame, text="转换进度", padding=(10, 5))
        progress_frame.pack(fill=tk.X, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        
        self.status_var = tk.StringVar(value="准备就绪")
        status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        status_label.pack(pady=5)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="转换日志", padding=(10, 5))
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 创建日志文本框和滚动条
        log_scroll = ttk.Scrollbar(log_frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(log_frame, height=10, width=50, yscrollcommand=log_scroll.set, 
                                wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        log_scroll.config(command=self.log_text.yview)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.convert_btn = ttk.Button(button_frame, text="开始转换", 
                                       command=self.start_conversion)
        self.convert_btn.pack(side=tk.RIGHT, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="停止转换", 
                                    command=self.stop_conversion, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.RIGHT, padx=5)

    def select_input_dir(self):
        directory = filedialog.askdirectory(title="选择包含HEIC文件的目录")
        if directory:
            self.input_dir_var.set(directory)
    
    def select_output_dir(self):
        directory = filedialog.askdirectory(title="选择JPG输出目录")
        if directory:
            self.output_dir_var.set(directory)
    
    def log_message(self, message):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
        self.log_text.see(tk.END)  # 自动滚动到最新的消息
        self.log_text.configure(state=tk.DISABLED)
    
    def start_conversion(self):
        # 验证目录
        input_dir = self.input_dir_var.get()
        output_dir = self.output_dir_var.get()
        
        if not os.path.exists(input_dir):
            messagebox.showerror("错误", "输入目录不存在!")
            return
        
        # 检查输入目录中是否有HEIC文件
        has_heic = False
        for file in os.listdir(input_dir):
            if file.lower().endswith(('.heic', '.heif')):
                has_heic = True
                break
        
        if not has_heic:
            messagebox.showerror("错误", "输入目录中没有HEIC文件!")
            return
        
        # 创建输出目录（如果不存在）
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                messagebox.showerror("错误", f"无法创建输出目录: {str(e)}")
                return
        
        # 更新UI状态
        self.convert_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self.status_var.set("正在转换...")
        self.is_converting = True
        
        # 清空日志
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state=tk.DISABLED)
        
        # 启动转换线程
        self.conversion_thread = threading.Thread(
            target=self.convert_files,
            args=(input_dir, output_dir, self.quality_var.get())
        )
        self.conversion_thread.daemon = True
        self.conversion_thread.start()
        
        # 开始定期检查队列和更新UI
        self.root.after(100, self.check_queue)
    
    def convert_files(self, input_dir, output_dir, quality):
        try:
            # 获取所有HEIC文件
            heic_files = [f for f in os.listdir(input_dir) 
                         if f.lower().endswith(('.heic', '.heif'))]
            
            total_files = len(heic_files)
            converted = 0
            
            if total_files == 0:
                self.queue.put(("log", "没有找到HEIC文件"))
                self.queue.put(("complete", None))
                return
            
            self.queue.put(("log", f"共找到 {total_files} 个HEIC文件"))
            
            for filename in heic_files:
                if not self.is_converting:
                    self.queue.put(("log", "转换已停止"))
                    break
                
                input_path = os.path.join(input_dir, filename)
                output_filename = os.path.splitext(filename)[0] + '.jpg'
                output_path = os.path.join(output_dir, output_filename)
                
                try:
                    # 读取HEIC文件
                    heif_file = pyheif.read(input_path)
                    
                    # 转换为PIL Image
                    image = Image.frombytes(
                        heif_file.mode, 
                        heif_file.size, 
                        heif_file.data,
                        "raw", 
                        heif_file.mode, 
                        heif_file.stride,
                    )
                    
                    # 保存为JPG
                    image.save(output_path, 'JPEG', quality=quality)
                    
                    converted += 1
                    progress = (converted / total_files) * 100
                    
                    self.queue.put(("progress", progress))
                    self.queue.put(("log", f"已转换: {filename} -> {output_filename}"))
                
                except Exception as e:
                    self.queue.put(("log", f"转换 {filename} 失败: {str(e)}"))
            
            self.queue.put(("log", f"转换完成! 共转换 {converted}/{total_files} 文件"))
            self.queue.put(("complete", None))
        
        except Exception as e:
            self.queue.put(("log", f"转换过程中发生错误: {str(e)}"))
            self.queue.put(("complete", None))
    
    def check_queue(self):
        try:
            while True:
                message_type, message = self.queue.get_nowait()
                
                if message_type == "progress":
                    self.progress_var.set(message)
                elif message_type == "log":
                    self.log_message(message)
                elif message_type == "complete":
                    self.on_conversion_complete()
                
                self.queue.task_done()
        except queue.Empty:
            if self.is_converting:
                self.root.after(100, self.check_queue)
    
    def on_conversion_complete(self):
        self.is_converting = False
        self.convert_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_var.set("转换完成")
        
        # 如果转换成功，询问是否打开输出目录
        if messagebox.askyesno("转换完成", "转换已完成，是否打开输出目录?"):
            self.open_output_dir()
    
    def stop_conversion(self):
        if self.is_converting:
            self.is_converting = False
            self.status_var.set("已停止转换")
            self.log_message("用户停止了转换")
    
    def open_output_dir(self):
        output_dir = self.output_dir_var.get()
        if os.path.exists(output_dir):
            # 根据操作系统打开文件夹
            if os.name == 'nt':  # Windows
                os.startfile(output_dir)
            elif os.name == 'posix':  # macOS 和 Linux
                import subprocess
                subprocess.Popen(['open', output_dir])
    
    def on_closing(self):
        if self.is_converting:
            if messagebox.askyesno("退出", "转换正在进行中，确定要退出吗?"):
                self.is_converting = False
                self.root.destroy()
        else:
            self.root.destroy()

def main():
    root = tk.Tk()
    app = HeicToJpgConverter(root)
    root.mainloop()

if __name__ == "__main__":
    main() 