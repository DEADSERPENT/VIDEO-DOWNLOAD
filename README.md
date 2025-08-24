# Advanced YouTube Downloader

A modern, feature-rich YouTube downloader with both web and desktop interfaces. Download videos, playlists, and audio with ease using a beautiful, responsive UI.

## Features

### 🌐 Web Interface
- **Modern UI**: Clean, responsive design with custom color themes
- **Batch Downloads**: Download multiple videos or entire playlists
- **Real-time Progress**: Live download progress with WebSocket updates
- **Format Selection**: Choose from various video qualities and audio-only options
- **Queue Management**: Pause, resume, and manage download queues
- **Settings Panel**: Customize default quality, concurrent downloads, and notifications

### 🖥️ Desktop GUI
- **Standalone Application**: No browser required
- **Intuitive Interface**: Easy-to-use desktop application
- **Progress Tracking**: Visual progress bars and status updates
- **Custom Styling**: Modern tkinter interface with custom colors

### 📋 Supported Features
- YouTube videos and playlists
- Multiple video qualities (720p, 480p, best available)
- Audio-only downloads (MP3)
- Batch processing
- Download statistics and history
- Error handling and retry mechanisms

## Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/advanced-youtube-downloader.git
   cd advanced-youtube-downloader
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Web Interface

1. **Start the web server**
   ```bash
   python app.py
   ```

2. **Open your browser** and navigate to `http://localhost:5000`

3. **Enter YouTube URLs** and start downloading!

### Desktop GUI

1. **Run the desktop application**
   ```bash
   python yt_gui.py
   ```

2. **Use the intuitive interface** to download videos

## Dependencies

- **Flask**: Web framework for the web interface
- **Flask-SocketIO**: Real-time communication for progress updates
- **yt-dlp**: YouTube download engine
- **tkinter**: Desktop GUI framework (included with Python)

## Project Structure

```
advanced-youtube-downloader/
├── app.py              # Flask web application
├── yt_gui.py          # Desktop GUI application
├── index.html         # Web interface template
├── settings.json      # Application settings
├── requirements.txt   # Python dependencies
├── venv/             # Virtual environment (created after setup)
└── README.md         # This file
```

## Configuration

The application uses `settings.json` to store user preferences:
- Default video quality
- Download paths
- UI preferences
- Concurrent download limits

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for the powerful download engine
- [Flask](https://flask.palletsprojects.com/) for the web framework
- [Tailwind CSS](https://tailwindcss.com/) for styling utilities

## Disclaimer

This tool is for educational purposes only. Please respect YouTube's Terms of Service and copyright laws. Only download content you have permission to download.

## Support

If you encounter any issues or have questions, please open an issue on GitHub.

---

**Happy Downloading! 🎥📥**