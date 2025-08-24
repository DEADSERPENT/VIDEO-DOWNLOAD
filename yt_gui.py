import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from PIL import Image, ImageTk
import requests
from io import BytesIO
import threading
import yt_dlp
import os
import json
import time
from datetime import datetime
import subprocess
import sys
import queue
from urllib.parse import urlparse
import re
import webbrowser


class DownloadManager:
    def __init__(self):
        self.download_queue = []
        self.active_downloads = {}
        self.history = []
        self.settings = self.load_settings()
        
    def load_settings(self):
        try:
            with open('settings.json', 'r') as f:
                return json.load(f)
        except:
            return {
                'download_path': os.path.expanduser('~/Downloads'),
                'auto_organize': True,
                'auto_thumbnail': False,
                'default_quality': 'best',
                'clipboard_monitor': False
            }
    
    def save_settings(self):
        with open('settings.json', 'w') as f:
            json.dump(self.settings, f)
    
    def add_to_history(self, url, title, format_type, file_path):
        self.history.append({
            'url': url,
            'title': title,
            'format': format_type,
            'file_path': file_path,
            'timestamp': datetime.now().isoformat()
        })


class YouTubeDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader Pro - Enhanced Edition")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # Updated color scheme using specified palette
        self.colors = {
            'bg': '#FFF5F2',           # rgb(255, 245, 242)
            'secondary_bg': '#F5BABB',  # rgb(245, 186, 187)
            'accent': '#568F87',        # rgb(86, 143, 135)
            'success': '#568F87',       # rgb(86, 143, 135)
            'warning': '#F5BABB',       # rgb(245, 186, 187)
            'error': '#F5BABB',         # rgb(245, 186, 187)
            'text': '#064232',          # rgb(6, 66, 50)
            'text_secondary': '#568F87' # rgb(86, 143, 135)
        }
        
        self.root.configure(bg=self.colors['bg'])
        
        self.download_manager = DownloadManager()
        self.clipboard_content = ""
        
        # Download tracking
        self.download_queue = []
        self.current_downloads = {}
        self.download_history = []
        self.stats = {
            'total': 0,
            'completed': 0,
            'failed': 0,
            'active': 0
        }
        
        # Additional variables
        self.batch_mode = tk.BooleanVar()
        self.auto_download = tk.BooleanVar()
        
        # Style configuration
        self.setup_styles()
        
        # GUI Components
        self.create_widgets()
        
        # Start clipboard monitoring if enabled
        if self.download_manager.settings.get('clipboard_monitor', False):
            self.monitor_clipboard()
        
        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_styles(self):
        """Configure modern ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure button styles
        style.configure('Accent.TButton',
                       background=self.colors['accent'],
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       padding=(10, 8))
        
        style.map('Accent.TButton',
                 background=[('active', '#3d8bfd'),
                           ('pressed', '#0d6efd')])
        
        style.configure('Success.TButton',
                       background=self.colors['success'],
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       padding=(8, 6))
        
        style.configure('Warning.TButton',
                       background=self.colors['warning'],
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       padding=(8, 6))
        
        # Configure frame styles
        style.configure('Card.TFrame',
                       background=self.colors['secondary_bg'],
                       relief='flat',
                       borderwidth=1)
        
        # Configure label styles
        style.configure('Heading.TLabel',
                       background=self.colors['bg'],
                       foreground=self.colors['text'],
                       font=('Segoe UI', 12, 'bold'))
        
        style.configure('Body.TLabel',
                       background=self.colors['bg'],
                       foreground=self.colors['text_secondary'],
                       font=('Segoe UI', 9))
        
        # Configure entry styles
        style.configure('Modern.TEntry',
                       fieldbackground=self.colors['secondary_bg'],
                       foreground=self.colors['text'],
                       borderwidth=1,
                       insertcolor=self.colors['text'])
        
        # Configure combobox styles
        style.configure('Modern.TCombobox',
                       fieldbackground=self.colors['secondary_bg'],
                       foreground=self.colors['text'],
                       borderwidth=1)
        
        # Configure progressbar styles
        style.configure('Modern.Horizontal.TProgressbar',
                       background=self.colors['accent'],
                       troughcolor=self.colors['secondary_bg'],
                       borderwidth=1,
                       lightcolor=self.colors['accent'],
                       darkcolor=self.colors['accent'],
                       relief='flat')
        
        # Map progressbar states for better visibility
        style.map('Modern.Horizontal.TProgressbar',
                 background=[('active', self.colors['accent']),
                           ('!active', self.colors['accent'])])
        
        # Configure styles for dark theme
        style.configure('TFrame', background=self.colors['bg'])
        style.configure('TLabel', background=self.colors['bg'], foreground=self.colors['text'])
        style.configure('TButton', background=self.colors['secondary_bg'], foreground=self.colors['text'])
        style.configure('TEntry', fieldbackground=self.colors['secondary_bg'], foreground=self.colors['text'])
        style.configure('TCombobox', fieldbackground=self.colors['secondary_bg'], foreground=self.colors['text'])
        style.configure('TNotebook', background=self.colors['bg'])
        style.configure('TNotebook.Tab', background=self.colors['secondary_bg'], foreground=self.colors['text'])
    
    def create_widgets(self):
        """Create the modern GUI interface with tabs and enhanced features"""
        # Main container with padding
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Header section
        self.create_header(main_container)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Create tabs
        self.create_download_tab()
        self.create_queue_tab()
        self.create_history_tab()
        self.create_settings_tab()
        
        # Initialize variables for new UI elements
        self.url_var = tk.StringVar()
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Ready")
        
        # Status bar at bottom
        self.create_status_bar(main_container)
        
    def create_header(self, parent):
        """Create the application header with title and stats"""
        header_frame = ttk.Frame(parent, style='Card.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Title and subtitle
        title_frame = ttk.Frame(header_frame)
        title_frame.pack(fill=tk.X, padx=20, pady=15)
        
        title_label = ttk.Label(title_frame, text="YouTube Downloader Pro", 
                               style='Heading.TLabel', font=("Segoe UI", 18, "bold"))
        title_label.pack(anchor=tk.W)
        
        subtitle_label = ttk.Label(title_frame, text="Enhanced Edition - Download videos, playlists, and audio", 
                                  style='Body.TLabel')
        subtitle_label.pack(anchor=tk.W, pady=(2, 0))
        
        # Stats section
        stats_frame = ttk.Frame(header_frame)
        stats_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        self.create_stat_card(stats_frame, "Total", "total", 0)
        self.create_stat_card(stats_frame, "Completed", "completed", 1)
        self.create_stat_card(stats_frame, "Active", "active", 2)
        self.create_stat_card(stats_frame, "Failed", "failed", 3)
        
    def create_stat_card(self, parent, label, key, column):
        """Create a statistics card"""
        card_frame = ttk.Frame(parent, style='Card.TFrame')
        card_frame.grid(row=0, column=column, padx=5, sticky='ew')
        parent.grid_columnconfigure(column, weight=1)
        
        value_label = ttk.Label(card_frame, text="0", font=("Segoe UI", 16, "bold"),
                               foreground=self.colors['accent'], background=self.colors['secondary_bg'])
        value_label.pack(pady=(10, 2))
        
        desc_label = ttk.Label(card_frame, text=label, style='Body.TLabel',
                              background=self.colors['secondary_bg'])
        desc_label.pack(pady=(0, 10))
        
        # Store reference for updating
        setattr(self, f'stat_{key}_label', value_label)
        
    def create_status_bar(self, parent):
        """Create the status bar at the bottom"""
        status_frame = ttk.Frame(parent, style='Card.TFrame')
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_bar_label = ttk.Label(status_frame, text="Ready", style='Body.TLabel')
        self.status_bar_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Version info
        version_label = ttk.Label(status_frame, text="v2.0 Enhanced", style='Body.TLabel')
        version_label.pack(side=tk.RIGHT, padx=10, pady=5)
    
    def create_download_tab(self):
        """Create the main download tab"""
        download_frame = ttk.Frame(self.notebook)
        self.notebook.add(download_frame, text="📥 Download")
        
        # URL input section
        url_section = ttk.LabelFrame(download_frame, text="Video URLs", padding=15)
        url_section.pack(fill=tk.X, padx=10, pady=10)
        
        # Batch mode toggle
        batch_frame = ttk.Frame(url_section)
        batch_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Checkbutton(batch_frame, text="Batch Mode (Multiple URLs)", 
                       variable=self.batch_mode, command=self.toggle_batch_mode).pack(side=tk.LEFT)
        
        ttk.Checkbutton(batch_frame, text="Auto Download", 
                       variable=self.auto_download).pack(side=tk.RIGHT)
        
        # URL input (will be replaced with text widget in batch mode)
        self.url_input_frame = ttk.Frame(url_section)
        self.url_input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.url_text = tk.Text(self.url_input_frame, height=4, bg='#404040', fg='white', insertbackground='white')
        self.url_text.pack(fill=tk.X)
        
        # URL action buttons
        url_buttons_frame = ttk.Frame(url_section)
        url_buttons_frame.pack(fill=tk.X)
        
        ttk.Button(url_buttons_frame, text="📋 Paste", command=self.paste_from_clipboard,
                  style='Success.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(url_buttons_frame, text="ℹ️ Get Info", command=self.fetch_metadata,
                  style='Accent.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(url_buttons_frame, text="🗑️ Clear", command=lambda: self.url_text.delete(1.0, tk.END),
                  style='Warning.TButton').pack(side=tk.LEFT)
        
        # Quality and format selection
        options_section = ttk.LabelFrame(download_frame, text="Download Options", padding=15)
        options_section.pack(fill=tk.X, padx=10, pady=10)
        
        # Quality selection
        quality_frame = ttk.Frame(options_section)
        quality_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(quality_frame, text="Quality:", bg=self.colors['bg'], fg=self.colors['text']).pack(side=tk.LEFT, padx=(0, 10))
        
        self.quality_var = tk.StringVar(value="best")
        quality_combo = ttk.Combobox(quality_frame, textvariable=self.quality_var, 
                                    style='Modern.TCombobox', state='readonly')
        quality_combo['values'] = (
            'best', '1080p', '720p', '480p', '360p', 'worst'
        )
        quality_combo.pack(side=tk.LEFT, padx=(0, 20))
        
        # Format checkboxes
        self.format_vars = {
            'mp4_video': tk.BooleanVar(value=True),
            'mp3_audio': tk.BooleanVar(),
            'thumbnail': tk.BooleanVar()
        }
        
        format_frame = ttk.Frame(options_section)
        format_frame.pack(fill=tk.X)
        
        ttk.Checkbutton(format_frame, text="MP4 (Video)", variable=self.format_vars['mp4_video']).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(format_frame, text="MP3 (Audio)", variable=self.format_vars['mp3_audio']).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(format_frame, text="Thumbnail", variable=self.format_vars['thumbnail']).pack(side=tk.LEFT)
        
        # Metadata preview
        preview_frame = ttk.LabelFrame(download_frame, text="Preview", padding=10)
        preview_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Thumbnail and info
        info_frame = ttk.Frame(preview_frame)
        info_frame.pack(fill='x')
        
        self.thumbnail_label = tk.Label(info_frame, bg=self.colors['bg'])
        self.thumbnail_label.pack(side='left', padx=10)
        
        info_text_frame = ttk.Frame(info_frame)
        info_text_frame.pack(side='left', fill='both', expand=True, padx=10)
        
        self.title_label = tk.Label(info_text_frame, text="Title: -", bg=self.colors['bg'], fg=self.colors['text'], wraplength=400, justify='left')
        self.title_label.pack(anchor='w', pady=2)
        
        self.duration_label = tk.Label(info_text_frame, text="Duration: -", bg=self.colors['bg'], fg=self.colors['text'])
        self.duration_label.pack(anchor='w', pady=2)
        
        self.size_label = tk.Label(info_text_frame, text="Size: -", bg=self.colors['bg'], fg=self.colors['text'])
        self.size_label.pack(anchor='w', pady=2)
        
        # Download controls
        download_frame_controls = ttk.Frame(download_frame)
        download_frame_controls.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(download_frame_controls, text="📁 Choose Download Folder", 
                  command=self.choose_download_folder).pack(side='left', padx=5)
        
        self.download_path_label = tk.Label(download_frame_controls, 
                                          text=f"📂 {self.download_manager.settings['download_path']}", 
                                          bg=self.colors['bg'], fg=self.colors['text'])
        self.download_path_label.pack(side='left', padx=10)
        
        # Main download button with enhanced styling
        download_btn_frame = ttk.Frame(download_frame)
        download_btn_frame.pack(pady=10)
        
        ttk.Button(download_btn_frame, text="🚀 Start Download", 
                  command=self.start_download, style='Accent.TButton').pack(side='left', padx=5)
        ttk.Button(download_btn_frame, text="📋 Add to Queue", 
                  command=self.add_to_queue, style='Success.TButton').pack(side='left', padx=5)
        ttk.Button(download_btn_frame, text="⏸️ Pause All", 
                  command=self.pause_all_downloads, style='Warning.TButton').pack(side='left', padx=5)
        
        # Progress section
        progress_frame = ttk.LabelFrame(download_frame, text="Progress", padding=10)
        progress_frame.pack(fill='x', padx=10, pady=5)
        
        self.progress_bar = ttk.Progressbar(progress_frame, length=600, mode="determinate", 
                                           style='Modern.Horizontal.TProgressbar')
        self.progress_bar.pack(fill='x', pady=5)
        
        self.progress_label = tk.Label(progress_frame, text="Ready to download", bg=self.colors['bg'], fg=self.colors['text'])
        self.progress_label.pack()
        
        self.speed_label = tk.Label(progress_frame, text="", bg=self.colors['bg'], fg=self.colors['text'])
        self.speed_label.pack()
    
    def create_queue_tab(self):
        """Create the download queue management tab"""
        queue_frame = ttk.Frame(self.notebook)
        self.notebook.add(queue_frame, text="📋 Queue")
        
        # Queue controls
        controls_frame = ttk.Frame(queue_frame)
        controls_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(controls_frame, text="▶️ Start Queue", command=self.start_queue,
                  style='Success.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls_frame, text="⏸️ Pause All", command=self.pause_all_downloads,
                  style='Warning.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls_frame, text="🗑️ Clear Queue", command=self.clear_queue,
                  style='Warning.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Queue list
        queue_list_frame = ttk.LabelFrame(queue_frame, text="Download Queue", padding=10)
        queue_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create treeview for queue
        columns = ('Title', 'URL', 'Quality', 'Status', 'Progress')
        self.queue_tree = ttk.Treeview(queue_list_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.queue_tree.heading(col, text=col)
            self.queue_tree.column(col, width=150)
        
        # Scrollbar for queue
        queue_scrollbar = ttk.Scrollbar(queue_list_frame, orient=tk.VERTICAL, command=self.queue_tree.yview)
        self.queue_tree.configure(yscrollcommand=queue_scrollbar.set)
        
        self.queue_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        queue_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_history_tab(self):
        """Create the download history tab"""
        history_frame = ttk.Frame(self.notebook)
        self.notebook.add(history_frame, text="📜 History")
        
        # History controls
        history_controls = ttk.Frame(history_frame)
        history_controls.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(history_controls, text="🔄 Refresh", command=self.refresh_history,
                  style='Accent.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(history_controls, text="🗑️ Clear History", command=self.clear_history,
                  style='Warning.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(history_controls, text="📁 Open Download Folder", command=self.open_download_folder,
                  style='Success.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(history_controls, text="📤 Export History", command=self.export_history,
                  style='Accent.TButton').pack(side=tk.LEFT)
        
        # History list
        history_list_frame = ttk.LabelFrame(history_frame, text="Download History", padding=10)
        history_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create treeview for history
        history_columns = ('Date', 'Title', 'URL', 'Quality', 'Status', 'File Path')
        self.history_tree = ttk.Treeview(history_list_frame, columns=history_columns, show='headings', height=15)
        
        for col in history_columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=120)
        
        # Scrollbar for history
        history_scrollbar = ttk.Scrollbar(history_list_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=history_scrollbar.set)
        
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.refresh_history()
    
    def create_settings_tab(self):
        """Create the settings and preferences tab"""
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="⚙️ Settings")
        
        # Create scrollable frame for settings
        canvas = tk.Canvas(settings_frame, bg=self.colors['bg'])
        scrollbar = ttk.Scrollbar(settings_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Download settings
        download_settings = ttk.LabelFrame(scrollable_frame, text="Download Settings", padding=15)
        download_settings.pack(fill=tk.X, padx=10, pady=10)
        
        # Default quality
        quality_frame = ttk.Frame(download_settings)
        quality_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(quality_frame, text="Default Quality:", style='Body.TLabel').pack(side=tk.LEFT)
        
        self.default_quality_var = tk.StringVar(value="best_mp4")
        quality_combo = ttk.Combobox(quality_frame, textvariable=self.default_quality_var,
                                    style='Modern.TCombobox', state='readonly')
        quality_combo['values'] = ('best_mp4', '1080p_mp4', '720p_mp4', '480p_mp4', '360p_mp4', 'mp3')
        quality_combo.pack(side=tk.RIGHT)
        
        # Download path
        path_frame = ttk.Frame(download_settings)
        path_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(path_frame, text="Download Path:", style='Body.TLabel').pack(side=tk.LEFT)
        
        self.download_path_var = tk.StringVar(value=str(self.download_manager.settings['download_path']))
        path_entry = ttk.Entry(path_frame, textvariable=self.download_path_var, style='Modern.TEntry')
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 5))
        ttk.Button(path_frame, text="Browse", command=self.browse_download_path).pack(side=tk.RIGHT)
        
        # Concurrent downloads
        concurrent_frame = ttk.Frame(download_settings)
        concurrent_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(concurrent_frame, text="Max Concurrent Downloads:", style='Body.TLabel').pack(side=tk.LEFT)
        
        self.concurrent_var = tk.IntVar(value=2)
        concurrent_spin = ttk.Spinbox(concurrent_frame, from_=1, to=5, textvariable=self.concurrent_var, width=10)
        concurrent_spin.pack(side=tk.RIGHT)
        
        self.auto_organize_var = tk.BooleanVar(value=self.download_manager.settings.get('auto_organize', True))
        ttk.Checkbutton(download_settings, text="Auto-organize files (Music → MP3 folder, Videos → MP4 folder)", 
                       variable=self.auto_organize_var, command=self.save_settings).pack(anchor='w')
        
        self.auto_thumbnail_var = tk.BooleanVar(value=self.download_manager.settings.get('auto_thumbnail', False))
        ttk.Checkbutton(download_settings, text="Always save thumbnails", 
                       variable=self.auto_thumbnail_var, command=self.save_settings).pack(anchor='w')
        
        # Application settings
        app_settings = ttk.LabelFrame(scrollable_frame, text="Application Settings", padding=15)
        app_settings.pack(fill=tk.X, padx=10, pady=10)
        
        # Checkboxes for various settings
        self.clipboard_monitor_var = tk.BooleanVar(value=self.download_manager.settings.get('clipboard_monitor', False))
        self.auto_start_var = tk.BooleanVar()
        self.notifications_var = tk.BooleanVar(value=True)
        self.minimize_to_tray_var = tk.BooleanVar()
        
        ttk.Checkbutton(app_settings, text="Monitor clipboard for YouTube URLs", 
                       variable=self.clipboard_monitor_var, command=self.toggle_clipboard_monitor).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(app_settings, text="Auto-start Downloads", 
                       variable=self.auto_start_var).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(app_settings, text="Show Notifications", 
                       variable=self.notifications_var).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(app_settings, text="Minimize to System Tray", 
                       variable=self.minimize_to_tray_var).pack(anchor=tk.W, pady=2)
        
        # Advanced settings
        advanced_settings = ttk.LabelFrame(scrollable_frame, text="Advanced Features", padding=10)
        advanced_settings.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(advanced_settings, text="🎵 Open Media Player", command=self.open_media_player).pack(anchor='w', pady=5)
        ttk.Button(advanced_settings, text="📦 Package as Executable", command=self.package_app).pack(anchor='w', pady=2)
        
        # System tray
        system_frame = ttk.LabelFrame(scrollable_frame, text="System Integration", padding=10)
        system_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(system_frame, text="⬇️ Minimize to System Tray", command=self.minimize_to_tray).pack(anchor='w', pady=2)
        
        # Settings buttons
        settings_buttons = ttk.Frame(scrollable_frame)
        settings_buttons.pack(fill=tk.X, padx=10, pady=20)
        
        ttk.Button(settings_buttons, text="💾 Save Settings", command=self.save_settings,
                  style='Success.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(settings_buttons, text="🔄 Reset to Defaults", command=self.reset_settings,
                  style='Warning.TButton').pack(side=tk.LEFT)
        ttk.Button(settings_buttons, text="ℹ️ About", command=self.show_about,
                  style='Accent.TButton').pack(side=tk.RIGHT)
        
        # Drag and drop info
        info_frame = ttk.LabelFrame(scrollable_frame, text="Tips & Info", padding=10)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tips_text = """
💡 Tips:
• Drag and drop URL files into the URL text area
• Use multiple URLs separated by new lines for bulk downloads
• Right-click on queue items for more options
• Supports YouTube, Instagram, Twitter, TikTok, and more platforms
        """
        tk.Label(info_frame, text=tips_text, bg='#2b2b2b', fg='white', justify='left').pack(anchor='w')
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def fetch_metadata(self):
        urls = self.get_urls_from_text()
        if not urls:
            messagebox.showerror("Error", "Please enter at least one URL")
            return
        
        def fetch_thread():
            try:
                url = urls[0]  # Get metadata for first URL
                ydl_opts = {"quiet": True, "no_warnings": True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                
                # Update UI in main thread
                self.root.after(0, lambda: self.update_metadata_ui(info))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        
        threading.Thread(target=fetch_thread, daemon=True).start()
    
    def update_metadata_ui(self, info):
        self.title_label.config(text=f"Title: {info.get('title', 'Unknown')}")
        self.duration_label.config(text=f"Duration: {self.format_duration(info.get('duration', 0))}")
        
        # Estimate file size
        filesize = info.get('filesize') or info.get('filesize_approx')
        if filesize:
            size_mb = filesize / (1024 * 1024)
            self.size_label.config(text=f"Size: ~{size_mb:.1f} MB")
        
        # Load thumbnail
        thumbnail_url = info.get("thumbnail")
        if thumbnail_url:
            threading.Thread(target=lambda: self.load_thumbnail(thumbnail_url), daemon=True).start()
    
    def load_thumbnail(self, thumbnail_url):
        try:
            response = requests.get(thumbnail_url, timeout=10)
            img_data = response.content
            img = Image.open(BytesIO(img_data))
            img = img.resize((160, 90))  # 16:9 ratio
            tk_img = ImageTk.PhotoImage(img)
            
            self.root.after(0, lambda: self.update_thumbnail(tk_img))
        except Exception as e:
            print(f"Error loading thumbnail: {e}")
    
    def update_thumbnail(self, tk_img):
        self.thumbnail_label.config(image=tk_img)
        self.thumbnail_label.image = tk_img
    
    def get_urls_from_text(self):
        text_content = self.url_text.get(1.0, tk.END).strip()
        urls = [url.strip() for url in text_content.split('\n') if url.strip()]
        return [url for url in urls if self.is_valid_url(url)]
    
    def is_valid_url(self, url):
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def start_download(self):
        urls = self.get_urls_from_text()
        if not urls:
            messagebox.showerror("Error", "Please enter at least one valid URL")
            return
        
        # Check what formats are selected
        formats_to_download = []
        if self.format_vars['mp4_video'].get():
            formats_to_download.append('mp4')
        if self.format_vars['mp3_audio'].get():
            formats_to_download.append('mp3')
        
        if not formats_to_download:
            messagebox.showerror("Error", "Please select at least one format")
            return
        
        # Add downloads to queue
        for url in urls:
            for format_type in formats_to_download:
                self.add_to_download_queue(url, format_type)
        
        # Start processing queue
        self.process_download_queue()
    
    def add_to_download_queue(self, url, format_type):
        download_item = {
            'url': url,
            'format': format_type,
            'status': 'Queued',
            'progress': 0,
            'speed': '',
            'eta': '',
            'title': 'Fetching...'
        }
        self.download_manager.download_queue.append(download_item)
        self.update_queue_display()
    
    def process_download_queue(self):
        if not self.download_manager.download_queue:
            return
        
        def download_worker():
            while self.download_manager.download_queue:
                item = self.download_manager.download_queue.pop(0)
                self.download_single_item(item)
                self.root.after(0, self.update_queue_display)
        
        threading.Thread(target=download_worker, daemon=True).start()
    
    def download_single_item(self, item):
        url = item['url']
        format_type = item['format']
        
        # Create download directory
        base_path = self.download_manager.settings['download_path']
        if self.download_manager.settings.get('auto_organize', True):
            if format_type == 'mp3':
                download_path = os.path.join(base_path, 'Music')
            else:
                download_path = os.path.join(base_path, 'Videos')
        else:
            download_path = base_path
        
        os.makedirs(download_path, exist_ok=True)
        
        # Configure yt-dlp options
        if format_type == 'mp3':
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": os.path.join(download_path, "%(title)s.%(ext)s"),
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
                "progress_hooks": [lambda d: self.progress_hook(d, item)]
            }
        else:  # mp4
            quality = self.quality_var.get()
            format_selector = "bestvideo+bestaudio/best" if quality == "best" else f"best[height<={quality[:-1]}]"
            
            ydl_opts = {
                "format": format_selector,
                "merge_output_format": "mp4",
                "outtmpl": os.path.join(download_path, "%(title)s.%(ext)s"),
                "progress_hooks": [lambda d: self.progress_hook(d, item)]
            }
        
        try:
            item['status'] = 'Downloading'
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                item['title'] = info.get('title', 'Unknown')
                
                # Download thumbnail if requested
                if self.format_vars['thumbnail'].get() or self.download_manager.settings.get('auto_thumbnail', False):
                    self.download_thumbnail(info, download_path)
                
                ydl.download([url])
                
                item['status'] = 'Completed'
                
                # Add to history
                file_path = os.path.join(download_path, f"{info['title']}.{format_type}")
                self.download_manager.add_to_history(url, info['title'], format_type, file_path)
                
        except Exception as e:
            item['status'] = f'Error: {str(e)}'
    
    def download_thumbnail(self, info, download_path):
        try:
            thumbnail_url = info.get("thumbnail")
            if thumbnail_url:
                response = requests.get(thumbnail_url)
                img_filename = f"{info['title']}_thumbnail.jpg"
                img_path = os.path.join(download_path, img_filename)
                
                with open(img_path, 'wb') as f:
                    f.write(response.content)
        except Exception as e:
            print(f"Error downloading thumbnail: {e}")
    
    def progress_hook(self, d, item):
        if d["status"] == "downloading":
            percent = d.get("_percent_str", "0.0%").replace("%", "").strip()
            try:
                percent_float = float(percent)
                item['progress'] = percent_float
            except ValueError:
                item['progress'] = 0
            
            item['speed'] = d.get("_speed_str", "")
            item['eta'] = d.get("_eta_str", "")
            
            # Update main progress bar for first item
            self.root.after(0, lambda: self.update_main_progress(item))
            
        elif d["status"] == "finished":
            item['progress'] = 100
            item['status'] = 'Processing'
    
    def update_main_progress(self, item):
        self.progress_bar["value"] = item['progress']
        self.progress_label.config(text=f"Downloading: {item['title'][:50]}...")
        self.speed_label.config(text=f"Speed: {item['speed']} | ETA: {item['eta']}")
        self.root.update_idletasks()
    
    def update_queue_display(self):
        # Clear existing items
        for item in self.queue_tree.get_children():
            self.queue_tree.delete(item)
        
        # Add queue items
        for item in self.download_manager.download_queue + list(self.download_manager.active_downloads.values()):
            self.queue_tree.insert('', 'end', values=(
                item['title'][:30] + '...' if len(item['title']) > 30 else item['title'],
                item['status'],
                f"{item['progress']:.1f}%",
                item['speed'],
                item['eta']
            ))
    
    def choose_download_folder(self):
        folder = filedialog.askdirectory(initialdir=self.download_manager.settings['download_path'])
        if folder:
            self.download_manager.settings['download_path'] = folder
            self.download_path_label.config(text=f"📂 {folder}")
            self.save_settings()
    
    def save_settings(self):
        self.download_manager.settings['auto_organize'] = self.auto_organize_var.get()
        self.download_manager.settings['auto_thumbnail'] = self.auto_thumbnail_var.get()
        self.download_manager.save_settings()
    
    def paste_from_clipboard(self):
        try:
            clipboard_content = self.root.clipboard_get()
            if self.is_valid_url(clipboard_content):
                self.url_text.delete(1.0, tk.END)
                self.url_text.insert(1.0, clipboard_content)
        except:
            messagebox.showinfo("Info", "No valid URL found in clipboard")
    
    def monitor_clipboard(self):
        try:
            current_clipboard = self.root.clipboard_get()
            if (current_clipboard != self.clipboard_content and 
                self.is_valid_url(current_clipboard) and
                any(domain in current_clipboard.lower() for domain in ['youtube', 'youtu.be', 'instagram', 'twitter', 'tiktok'])):
                
                self.clipboard_content = current_clipboard
                result = messagebox.askyesno("URL Detected", f"YouTube URL detected in clipboard:\n\n{current_clipboard[:100]}...\n\nAdd to download list?")
                if result:
                    self.url_text.insert(tk.END, current_clipboard + '\n')
        except:
            pass
        
        if self.download_manager.settings.get('clipboard_monitor', False):
            self.root.after(2000, self.monitor_clipboard)  # Check every 2 seconds
    
    def toggle_clipboard_monitor(self):
        self.download_manager.settings['clipboard_monitor'] = self.clipboard_monitor_var.get()
        self.save_settings()
        if self.clipboard_monitor_var.get():
            self.monitor_clipboard()
    
    def refresh_history(self):
        # Clear existing items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        # Add history items
        for item in self.download_manager.history:
            date_str = datetime.fromisoformat(item['timestamp']).strftime('%Y-%m-%d %H:%M')
            self.history_tree.insert('', 'end', values=(
                item['title'][:40] + '...' if len(item['title']) > 40 else item['title'],
                item['format'].upper(),
                date_str,
                item['file_path']
            ))
    
    def clear_history(self):
        if messagebox.askyesno("Confirm", "Clear all download history?"):
            self.download_manager.history.clear()
            self.refresh_history()
    
    def open_download_folder(self):
        path = self.download_manager.settings['download_path']
        if sys.platform.startswith('darwin'):  # macOS
            subprocess.call(["open", path])
        elif sys.platform.startswith('linux'):  # Linux
            subprocess.call(["xdg-open", path])
        elif sys.platform.startswith('win'):  # Windows
            subprocess.call(["explorer", path])
    
    def open_media_player(self):
        # Simple built-in media player using system default
        messagebox.showinfo("Media Player", "This would open a built-in media player for streaming without downloading.\nFeature coming soon!")
    
    def minimize_to_tray(self):
        self.root.withdraw()  # Hide window
        messagebox.showinfo("System Tray", "App minimized to system tray.\n(This is a simulation - full tray integration requires additional libraries)")
        self.root.deiconify()  # Show again for demo
    
    def package_app(self):
        info_text = """
To package this app as an executable:

1. Install PyInstaller: pip install pyinstaller
2. Run: pyinstaller --onefile --windowed --add-data "settings.json;." youtube_downloader.py

This will create:
• Windows: .exe file
• macOS: .app bundle  
• Linux: executable binary

For better distribution, consider using:
• cx_Freeze for cross-platform
• py2app for macOS
• Electron + Python for modern UI
        """
        messagebox.showinfo("Packaging Guide", info_text)
    
    def pause_all_downloads(self):
        messagebox.showinfo("Feature", "Pause/Resume functionality would be implemented here")
    
    def resume_all_downloads(self):
        messagebox.showinfo("Feature", "Resume functionality would be implemented here")
    
    def clear_completed(self):
        messagebox.showinfo("Feature", "Clear completed downloads from queue")
    
    def toggle_playlist(self):
        messagebox.showinfo("Playlist", "Playlist download support would be implemented here")
    
    def toggle_batch_mode(self):
        """Toggle between single URL and batch mode"""
        if self.batch_mode.get():
            # Switch to text widget for multiple URLs
            if hasattr(self, 'url_entry'):
                self.url_entry.destroy()
            if not hasattr(self, 'url_text') or not self.url_text.winfo_exists():
                self.url_text = tk.Text(self.url_input_frame, height=4, bg='#404040', fg='white', insertbackground='white')
                self.url_text.pack(fill=tk.BOTH, expand=True)
        else:
            # Switch to single entry widget
            if hasattr(self, 'url_text') and self.url_text.winfo_exists():
                self.url_text.destroy()
            self.url_entry = ttk.Entry(self.url_input_frame, textvariable=self.url_var, 
                                      style='Modern.TEntry', font=("Segoe UI", 10))
            self.url_entry.pack(fill=tk.X)
    
    def clear_urls(self):
        """Clear URL input"""
        if hasattr(self, 'url_text') and self.url_text.winfo_exists():
            self.url_text.delete(1.0, tk.END)
        else:
            self.url_var.set("")
    
    def get_video_info(self):
        """Alias for fetch_metadata for compatibility"""
        self.fetch_metadata()
    
    def format_duration(self, seconds):
        if not seconds:
            return "Unknown"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def add_to_queue(self):
        """Add current URL(s) to download queue without starting immediately"""
        urls = self.get_urls_from_text()
        if not urls:
            messagebox.showerror("Error", "Please enter at least one valid URL")
            return
        
        # Check what formats are selected
        formats_to_download = []
        if self.format_vars['mp4_video'].get():
            formats_to_download.append('mp4')
        if self.format_vars['mp3_audio'].get():
            formats_to_download.append('mp3')
        
        if not formats_to_download:
            messagebox.showerror("Error", "Please select at least one format")
            return
        
        # Add downloads to queue
        for url in urls:
            for format_type in formats_to_download:
                self.add_to_download_queue(url, format_type)
        
        messagebox.showinfo("Queue", f"Added {len(urls) * len(formats_to_download)} items to download queue")
    
    def browse_download_path(self):
        """Browse for download directory"""
        folder = filedialog.askdirectory(initialdir=self.download_path_var.get())
        if folder:
            self.download_path_var.set(folder)
            self.download_manager.settings['download_path'] = folder
            self.save_settings()
    
    def reset_settings(self):
        """Reset all settings to defaults"""
        if messagebox.askyesno("Reset Settings", "Reset all settings to defaults?"):
            self.download_manager.settings = {
                'download_path': os.path.expanduser('~/Downloads'),
                'auto_organize': True,
                'auto_thumbnail': False,
                'default_quality': 'best',
                'clipboard_monitor': False
            }
            self.save_settings()
            messagebox.showinfo("Settings", "Settings reset to defaults")
    
    def show_about(self):
        """Show about dialog"""
        about_text = """
YouTube Downloader Pro - Enhanced Edition
Version 2.0

A powerful YouTube downloader with modern UI
Supports multiple platforms and formats

Features:
• Download videos and audio
• Batch processing
• Queue management
• Download history
• Clipboard monitoring
• Auto-organization

Built with Python, tkinter, and yt-dlp
        """
        messagebox.showinfo("About", about_text)
    
    def start_queue(self):
        """Start processing the download queue"""
        if not self.download_manager.download_queue:
            messagebox.showinfo("Queue", "Download queue is empty")
            return
        
        self.process_download_queue()
        messagebox.showinfo("Queue", "Started processing download queue")
    
    def clear_queue(self):
        """Clear the download queue"""
        if messagebox.askyesno("Clear Queue", "Clear all items from download queue?"):
            self.download_manager.download_queue.clear()
            self.update_queue_display()
    
    def export_history(self):
        """Export download history to file"""
        if not self.download_manager.history:
            messagebox.showinfo("Export", "No history to export")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    json.dump(self.download_manager.history, f, indent=4)
                messagebox.showinfo("Export", f"History exported to {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))
    
    def on_closing(self):
        """Handle application closing"""
        if messagebox.askokcancel("Quit", "Do you want to quit? Any active downloads will be stopped."):
            self.download_manager.save_settings()
            self.root.destroy()
    
    def update_stats(self):
        """Update statistics display"""
        self.stat_total_label.config(text=str(self.stats['total']))
        self.stat_completed_label.config(text=str(self.stats['completed']))
        self.stat_active_label.config(text=str(self.stats['active']))
        self.stat_failed_label.config(text=str(self.stats['failed']))




# Drag and drop functionality
class DropTarget:
    def __init__(self, widget, callback):
        self.widget = widget
        self.callback = callback
        self.setup_drag_drop()
    
    def setup_drag_drop(self):
        # Basic drag and drop simulation (full implementation would require tkinterdnd2)
        self.widget.bind('<Button-1>', self.on_click)
        self.widget.bind('<B1-Motion>', self.on_drag)
        self.widget.bind('<ButtonRelease-1>', self.on_drop)
    
    def on_click(self, event):
        pass
    
    def on_drag(self, event):
        pass
    
    def on_drop(self, event):
        # This would handle actual file drops
        pass


# Enhanced media player window
class MediaPlayer:
    def __init__(self, parent):
        self.parent = parent
        self.player_window = None
        
    def open_player(self):
        if self.player_window and self.player_window.winfo_exists():
            self.player_window.lift()
            return
            
        self.player_window = tk.Toplevel(self.parent)
        self.player_window.title("Built-in Media Player")
        self.player_window.geometry("600x400")
        self.player_window.configure(bg='#1a1a1a')
        
        # Player controls
        controls_frame = ttk.Frame(self.player_window)
        controls_frame.pack(side='bottom', fill='x', padx=10, pady=10)
        
        ttk.Button(controls_frame, text="⏮️", width=3).pack(side='left', padx=2)
        ttk.Button(controls_frame, text="⏯️", width=3).pack(side='left', padx=2)
        ttk.Button(controls_frame, text="⏭️", width=3).pack(side='left', padx=2)
        ttk.Button(controls_frame, text="🔊", width=3).pack(side='left', padx=2)
        
        # Progress bar
        progress = ttk.Progressbar(controls_frame, length=200)
        progress.pack(side='left', padx=10, fill='x', expand=True)
        
        # URL input for streaming
        url_frame = ttk.Frame(self.player_window)
        url_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(url_frame, text="Stream URL:", bg='#1a1a1a', fg='white').pack(side='left')
        stream_url = ttk.Entry(url_frame, width=50)
        stream_url.pack(side='left', padx=5, fill='x', expand=True)
        ttk.Button(url_frame, text="Stream", command=lambda: self.start_stream(stream_url.get())).pack(side='left', padx=5)
        
        # Video display area
        video_frame = tk.Frame(self.player_window, bg='black')
        video_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        tk.Label(video_frame, text="🎬 Video Player\n\nEnter a YouTube URL above to start streaming", 
                bg='black', fg='white', font=('Arial', 14)).pack(expand=True)
    
    def start_stream(self, url):
        messagebox.showinfo("Streaming", f"Would start streaming: {url}\n\nThis would integrate with VLC or ffplay for actual playback.")


# System tray integration (simplified)
class SystemTrayManager:
    def __init__(self, root):
        self.root = root
        self.hidden = False
        
    def minimize_to_tray(self):
        self.root.withdraw()
        self.hidden = True
        # In a full implementation, this would create a system tray icon
        messagebox.showinfo("System Tray", "App minimized to system tray")
        
        # Simulate tray menu
        self.root.after(3000, self.show_tray_menu)
    
    def show_tray_menu(self):
        if self.hidden:
            result = messagebox.askyesno("System Tray Menu", "Show application window?")
            if result:
                self.restore_from_tray()
    
    def restore_from_tray(self):
        self.root.deiconify()
        self.hidden = False


# URL validation and extraction
class URLProcessor:
    @staticmethod
    def extract_urls_from_text(text):
        """Extract URLs from text using regex"""
        url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        return url_pattern.findall(text)
    
    @staticmethod
    def is_supported_platform(url):
        """Check if URL is from supported platforms"""
        supported_domains = [
            'youtube.com', 'youtu.be', 'instagram.com', 'twitter.com', 
            'tiktok.com', 'facebook.com', 'vimeo.com', 'dailymotion.com'
        ]
        return any(domain in url.lower() for domain in supported_domains)
    
    @staticmethod
    def clean_url(url):
        """Remove tracking parameters and clean URL"""
        # Remove common tracking parameters
        tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'fbclid', 'gclid']
        parsed_url = urlparse(url)
        
        # This would implement URL cleaning logic
        return url


# Configuration manager for advanced settings
class ConfigManager:
    def __init__(self):
        self.config_file = 'advanced_config.json'
        self.default_config = {
            'max_concurrent_downloads': 3,
            'retry_attempts': 3,
            'timeout_seconds': 30,
            'temp_directory': None,
            'proxy_settings': None,
            'custom_headers': {},
            'rate_limit': None,
            'preferred_codec': 'auto',
            'subtitle_languages': ['en'],
            'thumbnail_quality': 'maxresdefault',
            'audio_bitrate': '192',
            'video_quality_priority': ['1080p', '720p', '480p'],
            'naming_template': '%(title)s.%(ext)s',
            'auto_update_ytdlp': True
        }
        self.config = self.load_config()
    
    def load_config(self):
        try:
            with open(self.config_file, 'r') as f:
                loaded_config = json.load(f)
                # Merge with defaults
                config = self.default_config.copy()
                config.update(loaded_config)
                return config
        except FileNotFoundError:
            return self.default_config.copy()
    
    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)
    
    def get(self, key, default=None):
        return self.config.get(key, default)
    
    def set(self, key, value):
        self.config[key] = value
        self.save_config()


# Enhanced download statistics
class DownloadStats:
    def __init__(self):
        self.stats = {
            'total_downloads': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'total_size_downloaded': 0,
            'total_time_spent': 0,
            'favorite_formats': {},
            'platform_stats': {},
            'daily_downloads': {}
        }
        self.load_stats()
    
    def load_stats(self):
        try:
            with open('download_stats.json', 'r') as f:
                self.stats.update(json.load(f))
        except FileNotFoundError:
            pass
    
    def save_stats(self):
        with open('download_stats.json', 'w') as f:
            json.dump(self.stats, f, indent=4)
    
    def record_download(self, success=True, file_size=0, format_type='mp4', platform='youtube'):
        self.stats['total_downloads'] += 1
        if success:
            self.stats['successful_downloads'] += 1
            self.stats['total_size_downloaded'] += file_size
        else:
            self.stats['failed_downloads'] += 1
        
        # Update format stats
        self.stats['favorite_formats'][format_type] = self.stats['favorite_formats'].get(format_type, 0) + 1
        
        # Update platform stats
        self.stats['platform_stats'][platform] = self.stats['platform_stats'].get(platform, 0) + 1
        
        # Update daily stats
        today = datetime.now().strftime('%Y-%m-%d')
        self.stats['daily_downloads'][today] = self.stats['daily_downloads'].get(today, 0) + 1
        
        self.save_stats()


def main():
    root = tk.Tk()
    
    # Set window icon (would load from file in real implementation)
    try:
        # root.iconbitmap('icon.ico')  # Windows
        pass
    except:
        pass
    
    app = YouTubeDownloaderApp(root)
    
    # Set up drag and drop for URL text area
    drop_target = DropTarget(app.url_text, lambda files: app.handle_dropped_files(files))
    
    # Configure window closing behavior
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Start the application
    root.mainloop()


if __name__ == "__main__":
    # Check for required dependencies
    try:
        import yt_dlp
        from PIL import Image, ImageTk
        import requests
    except ImportError as e:
        print(f"Missing required dependency: {e}")
        print("\nTo install required packages, run:")
        print("pip install yt-dlp pillow requests")
        input("Press Enter to exit...")
        sys.exit(1)
    
    main()