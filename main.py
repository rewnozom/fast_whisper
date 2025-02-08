# ./fast_whisper_v2/main.py

import logging
import os
import string
import sys
import traceback
import wave
from pathlib import Path
import pickle
import threading

import keyboard
import pyaudio
from PySide6.QtCore import QThread, Signal, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QMessageBox, QWidget, QVBoxLayout, 
    QHBoxLayout, QPushButton, QLabel, QComboBox, QLineEdit, QTextEdit, 
    QGridLayout, QFrame, QDialog, QProgressBar
)

from faster_whisper import WhisperModel

import json

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
    return config

def save_config(new_config):
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'w') as config_file:
        json.dump(new_config, config_file, indent=4)

config = load_config()

from theme_manager import ThemeManager

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def list_input_devices():
    """
    Lista alla tillgängliga inmatningsenheter (mikrofoner och virtuella ljudenheter).
    """
    p = pyaudio.PyAudio()
    device_list = []
    for i in range(p.get_device_count()):
        device = p.get_device_info_by_index(i)
        if device['maxInputChannels'] > 0:
            device_list.append((i, device['name']))
    p.terminate()
    return device_list

class ModelCache:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.cache = {}
        self.initialize_cache_dir()

    def initialize_cache_dir(self):
        cache_dir = Path(config.get("cache_dir", ".whisper_cache"))
        cache_dir = Path.home() / cache_dir if not Path(config.get("cache_dir")).is_absolute() else Path(config.get("cache_dir"))
        cache_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Cache directory set to: {cache_dir}")
        self.cache_dir = cache_dir
        self.cache_file = cache_dir / config.get("cache_file", "model_cache_metadata.pkl")

    def get_model(self, model_name: str, device: str, compute_type: str):
        cache_key = f"{model_name}_{device}_{compute_type}"

        # Try to load from memory cache first
        if cache_key in self.cache:
            logger.debug(f"Model '{cache_key}' loaded from memory cache.")
            return self.cache[cache_key]

        # Check for an existing metadata file
        if self.cache_file.exists() and os.path.getsize(self.cache_file) > 0:  # Check file size
            try:
                with open(self.cache_file, 'rb') as f:
                    metadata = pickle.load(f)
                    if cache_key in metadata:
                        logger.debug(f"Metadata for model '{cache_key}' loaded from disk cache.")
                        # Recreate the model based on metadata
                        model = WhisperModel(model_name, device=device, compute_type=compute_type)
                        self.cache[cache_key] = model
                        return model
            except (EOFError, pickle.UnpicklingError) as e:
                logger.warning(f"Failed to load model metadata: {e}")
                # Optionally, recreate the metadata file if it's corrupted
                os.remove(self.cache_file)  # Delete corrupted cache file

        # Create new model if not found in cache
        model = WhisperModel(model_name, device=device, compute_type=compute_type)
        self.cache[cache_key] = model
        logger.debug(f"Model '{cache_key}' created and added to cache.")

        # Save metadata to disk cache
        try:
            with open(self.cache_file, 'wb') as f:
                metadata = {k: None for k in self.cache}  # Adjust to store metadata only
                pickle.dump(metadata, f)
            logger.debug(f"Cache metadata saved to disk at '{self.cache_file}'.")
        except Exception as e:
            logger.warning(f"Failed to save cache metadata: {e}")

        return model

class ModelLoader(QThread):
    progress_update = Signal(int)
    model_ready = Signal(object)
    
    def __init__(self, model_name, device, compute_type):
        super().__init__()
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type

    def run(self):
        try:
            self.progress_update.emit(10)
            cache = ModelCache.get_instance()
            self.progress_update.emit(50)
            model = cache.get_model(self.model_name, self.device, self.compute_type)
            self.progress_update.emit(100)
            self.model_ready.emit(model)
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.model_ready.emit(None)

class KeybindDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Change Keybind")
        self.setModal(True)
        self.setup_ui()
        self.new_key = None
        self.listening = False

    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Current keybind display
        current_layout = QHBoxLayout()
        current_layout.addWidget(QLabel("Current Keybind:"))
        self.current_keybind = QLabel(config["speak_hotkey"])
        current_layout.addWidget(self.current_keybind)
        layout.addLayout(current_layout)
        
        # New keybind input
        self.keybind_button = QPushButton("Press to record new keybind")
        self.keybind_button.clicked.connect(self.start_listening)
        layout.addWidget(self.keybind_button)
        
        # Status label
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

    def start_listening(self):
        if not self.listening:
            self.listening = True
            self.keybind_button.setText("Press any key...")
            self.status_label.setText("Listening for key press...")
            keyboard.hook(self.on_key_press)
    
    def on_key_press(self, event):
        if self.listening:
            self.new_key = event.name
            self.keybind_button.setText(f"New keybind: {self.new_key}")
            self.status_label.setText("Key recorded! Click Save to confirm.")
            self.save_button.setEnabled(True)
            self.listening = False
            keyboard.unhook(self.on_key_press)

    def get_new_keybind(self):
        return self.new_key

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Keybind section
        keybind_layout = QHBoxLayout()
        keybind_layout.addWidget(QLabel("Push-to-talk Key:"))
        self.keybind_label = QLabel(config["speak_hotkey"])
        self.change_keybind_btn = QPushButton("Change")
        self.change_keybind_btn.clicked.connect(self.show_keybind_dialog)
        keybind_layout.addWidget(self.keybind_label)
        keybind_layout.addWidget(self.change_keybind_btn)
        layout.addLayout(keybind_layout)
        
        # Add more settings here as needed
        
        # Buttons
        button_layout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

    def show_keybind_dialog(self):
        dialog = KeybindDialog(self)
        if dialog.exec() == QDialog.Accepted and dialog.get_new_keybind():
            new_key = dialog.get_new_keybind()
            # Update config
            config["speak_hotkey"] = new_key
            save_config(config)
            # Update label
            self.keybind_label.setText(new_key)
            # Update parent's keyboard hooks
            if isinstance(self.parent(), WhisperTranscription):
                self.parent().update_keyboard_hooks()

class RecordingIndicator(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("recording_indicator")
        self.setProperty("recording", False)
        
        # Setup pulse animation
        self.opacity = 1.0
        self.animation = QPropertyAnimation(self, b"opacity")
        self.animation.setDuration(1000)
        self.animation.setLoopCount(-1)  # Infinite loop
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.3)
        self.animation.setEasingCurve(QEasingCurve.InOutSine)

    def start_pulse(self):
        self.setProperty("recording", True)
        self.style().unpolish(self)
        self.style().polish(self)
        self.animation.start()

    def stop_pulse(self):
        self.setProperty("recording", False)
        self.style().unpolish(self)
        self.style().polish(self)
        self.animation.stop()
        
    def get_opacity(self):
        return self.opacity
        
    def set_opacity(self, opacity):
        self.opacity = opacity
        self.update()
        
    opacity_prop = Property(float, get_opacity, set_opacity)

class TranscriptionThread(QThread):
    transcription_complete = Signal(str)
    
    def __init__(self, model, filename, remove_punctuation):
        super().__init__()
        self.model = model
        self.filename = filename
        self.remove_punctuation = remove_punctuation

    def run(self):
        segments, _ = self.model.transcribe(self.filename)
        for segment in segments:
            text = segment.text
            if self.remove_punctuation:
                text = text.translate(str.maketrans('', '', string.punctuation))
            self.transcription_complete.emit(text)

class RecordingThread(QThread):
    recording_complete = Signal()
    error_occurred = Signal(str)
    
    def __init__(self, audio_format, channels, rate, chunk, filename, input_source, mic_device_index=None, computer_device_index=None):
        super().__init__()
        self.audio_format = audio_format
        self.channels = channels
        self.rate = rate
        self.chunk = chunk
        self.filename = filename
        self.input_source = input_source  # "microphone", "computer_audio", "both"
        self.mic_device_index = mic_device_index
        self.computer_device_index = computer_device_index
        self.is_recording = False
        self.audio = None
        self.streams = []
        self._sample_width = None
        
    def run(self):
        try:
            self.audio = pyaudio.PyAudio()
            
            # Öppna strömmar baserat på ljudkälla
            if self.input_source in ["microphone", "both"]:
                if self.mic_device_index is not None:
                    mic_stream = self.audio.open(
                        format=self.audio_format,
                        channels=self.channels,
                        rate=self.rate,
                        input=True,
                        frames_per_buffer=self.chunk,
                        input_device_index=self.mic_device_index
                    )
                    self.streams.append(mic_stream)
                else:
                    raise ValueError("Ingen mikrofonenhet vald.")
            
            if self.input_source in ["computer_audio", "both"]:
                if self.computer_device_index is not None:
                    computer_stream = self.audio.open(
                        format=self.audio_format,
                        channels=self.channels,
                        rate=self.rate,
                        input=True,
                        frames_per_buffer=self.chunk,
                        input_device_index=self.computer_device_index
                    )
                    self.streams.append(computer_stream)
                else:
                    raise ValueError("Ingen datorljudenhet vald.")
            
            self._sample_width = self.audio.get_sample_size(self.audio_format)
            frames = []
            self.is_recording = True
            
            while self.is_recording:
                for stream in self.streams:
                    try:
                        data = stream.read(self.chunk, exception_on_overflow=False)
                        frames.append(data)
                    except IOError as e:
                        logging.error(f"IOError under inspelning: {e}")
                        continue
            
            # Stäng strömmar
            for stream in self.streams:
                stream.stop_stream()
                stream.close()
            self.streams = []
            
            # Spara WAV-fil
            if frames:
                try:
                    with wave.open(self.filename, 'wb') as wf:
                        wf.setnchannels(self.channels)
                        wf.setsampwidth(self._sample_width)
                        wf.setframerate(self.rate)
                        wf.writeframes(b''.join(frames))
                    self.recording_complete.emit()
                except Exception as e:
                    self.error_occurred.emit(f"Fel vid sparning av inspelning: {str(e)}")
            
        except Exception as e:
            self.error_occurred.emit(f"Inspelningsfel: {str(e)}")
            traceback.print_exc()
        finally:
            self.cleanup_resources()

    def cleanup_resources(self):
        try:
            for stream in self.streams:
                if stream.is_active():
                    stream.stop_stream()
                stream.close()
            self.streams = []
            if self.audio:
                self.audio.terminate()
                self.audio = None
            self.is_recording = False
        except Exception as e:
            logging.error(f"Fel vid städning av ljudresurser: {e}")

    def stop(self):
        self.is_recording = False
        self.wait()

class WhisperTranscription(QWidget):
    def __init__(self):
        super().__init__()
        self.model = None
        self.defining_all_config_variables_from_config()

        # Hämta lista över inmatningsenheter innan setup_ui
        self.input_devices = list_input_devices()  

        self.setup_ui()
        self.update_record_button_text()
        self.recording_thread = None
        self.transcription_thread = None
        self.is_recording = False
        self.hotkey_pressed = False
        
        # Start loading the model in background
        self.setup_model_loader()
        
        self.setup_connections()
        ThemeManager.apply_widget_theme(self)

    def defining_all_config_variables_from_config(self):
        """
        Retrieve and define all config variables from the config dictionary.
        """
        # Audio settings
        self.audio_format = (pyaudio.paInt16 if config.get("audio_format", "Int16") == "Int16" 
                           else pyaudio.paInt24)
        self.channels = config.get("channels", 1)
        self.rate = config.get("rate", 16000)
        self.chunk = config.get("chunk", 1024)
        self.filename = config.get("wave_output_filename", "output.wav")
        
        # Remove punctuation setting
        self.remove_punctuation = config.get("remove_punctuation", False)

    def setup_model_loader(self):
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout = self.layout()
        if layout:
            layout.insertWidget(0, self.progress_bar)
        else:
            logger.warning("No layout found to insert the progress bar.")
        
        self.loader = ModelLoader(
            config.get("model_name", "base"),
            config.get("device", "cpu"),
            config.get("compute_type", "float32")
        )
        self.loader.progress_update.connect(self.update_progress)
        self.loader.model_ready.connect(self.handle_model_loaded)
        self.loader.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def handle_model_loaded(self, model):
        if model:
            self.model = model
            self.record_btn.setEnabled(True)
            self.status_label.setText("Ready")
            logger.debug("Model loaded and ready.")
        else:
            self.status_label.setText("Error loading model")
            logger.error("Failed to load model.")
        
        self.progress_bar.hide()

    def init_model(self):
        self.model = WhisperModel(
            config.get("model_name", "base"),
            device=config.get("device", "cpu"),
            compute_type=config.get("compute_type", "float32")
        )

    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Status section
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("status_label")
        self.recording_indicator = RecordingIndicator()
        status_layout.addWidget(self.recording_indicator)
        status_layout.addWidget(self.status_label)
        
        # Add the settings button here
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.clicked.connect(self.show_settings)  # Connect to the show_settings method
        status_layout.addWidget(self.settings_btn)
        
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # Model settings
        model_layout = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.model_combo.setCurrentText(config.get("model_name", "base"))
        model_layout.addWidget(QLabel("Model:"))
        model_layout.addWidget(self.model_combo)
        layout.addLayout(model_layout)
        
        # Audio settings
        settings_layout = QGridLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Int16", "Int24"])
        self.format_combo.setCurrentText(config.get("audio_format", "Int16"))
        self.channels_input = QLineEdit(str(self.channels))
        self.rate_input = QLineEdit(str(self.rate))
        self.chunk_input = QLineEdit(str(self.chunk))
        
        settings_layout.addWidget(QLabel("Format:"), 0, 0)
        settings_layout.addWidget(self.format_combo, 0, 1)
        settings_layout.addWidget(QLabel("Channels:"), 0, 2)
        settings_layout.addWidget(self.channels_input, 0, 3)
        settings_layout.addWidget(QLabel("Rate:"), 1, 0)
        settings_layout.addWidget(self.rate_input, 1, 1)
        settings_layout.addWidget(QLabel("Chunk:"), 1, 2)
        settings_layout.addWidget(self.chunk_input, 1, 3)
        layout.addLayout(settings_layout)
        
        # Ljudkällor inställningar
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("Ljudkälla:"))
        
        self.input_source_combo = QComboBox()
        self.input_source_combo.addItems(["microphone", "computer_audio", "both"])
        self.input_source_combo.setCurrentText(config.get("input_source", "microphone"))
        self.input_source_combo.currentTextChanged.connect(self.update_input_source)
        source_layout.addWidget(self.input_source_combo)
        
        layout.addLayout(source_layout)
        
        # Enhetsval för mikrofon
        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("Välj enhet:"))
        
        self.device_combo = QComboBox()
        self.device_combo.addItem("Välj en enhet")
        for idx, name in self.input_devices:
            self.device_combo.addItem(name, userData=idx)
        
        # Sätt valt enhetsindex om det finns i config
        selected_device_index = config.get("input_device_index")
        if selected_device_index is not None:
            for i in range(self.device_combo.count()):
                if self.device_combo.itemData(i) == selected_device_index:
                    self.device_combo.setCurrentIndex(i)
                    break
        
        self.device_combo.currentIndexChanged.connect(self.update_input_device)
        device_layout.addWidget(self.device_combo)
        
        layout.addLayout(device_layout)
        
        # Enhetsval för datorljud
        computer_device_layout = QHBoxLayout()
        computer_device_layout.addWidget(QLabel("Datorljudenhet:"))
        
        self.computer_device_combo = QComboBox()
        self.computer_device_combo.addItem("Välj en enhet")
        for idx, name in self.input_devices:
            if "cable" in name.lower() or "virtual" in name.lower():
                self.computer_device_combo.addItem(name, userData=idx)
        
        # Sätt valt datorenhetsindex om det finns i config
        selected_computer_device_index = config.get("computer_device_index")
        if selected_computer_device_index is not None:
            for i in range(self.computer_device_combo.count()):
                if self.computer_device_combo.itemData(i) == selected_computer_device_index:
                    self.computer_device_combo.setCurrentIndex(i)
                    break
        
        self.computer_device_combo.currentIndexChanged.connect(self.update_computer_device)
        computer_device_layout.addWidget(self.computer_device_combo)
        
        layout.addLayout(computer_device_layout)
        
        # Controls
        controls_layout = QHBoxLayout()
        self.record_btn = QPushButton()
        self.record_btn.setEnabled(False)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.clear_btn = QPushButton("Clear")
        controls_layout.addWidget(self.record_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addWidget(self.clear_btn)
        layout.addLayout(controls_layout)
        
        # Output
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        layout.addWidget(self.output_text)
        
        self.setLayout(layout)
        
        # Initial aktivering/deaktivera dropdowns baserat på ljudkälla
        self.update_input_source(self.input_source_combo.currentText())

    def update_record_button_text(self):
        # Update the record button's text with the current keybind
        self.record_btn.setText(f"Record ({config.get('speak_hotkey', 'None')})")

    def setup_connections(self):
        self.record_btn.clicked.connect(self.toggle_recording)
        self.stop_btn.clicked.connect(self.stop_recording)
        self.clear_btn.clicked.connect(self.output_text.clear)
        self.model_combo.currentTextChanged.connect(self.update_model)
        self.format_combo.currentTextChanged.connect(self.update_audio_format)
        self.channels_input.editingFinished.connect(self.update_channels)
        self.rate_input.editingFinished.connect(self.update_rate)
        self.chunk_input.editingFinished.connect(self.update_chunk)
        
        # Setup keyboard hooks based on config
        keyboard.on_press_key(config.get("speak_hotkey", "None"), self.handle_hotkey_press, suppress=True)
        keyboard.on_release_key(config.get("speak_hotkey", "None"), self.handle_hotkey_release, suppress=True)

    def update_audio_format(self):
        new_format = self.format_combo.currentText()
        config["audio_format"] = new_format
        save_config(config)
        self.audio_format = pyaudio.paInt16 if new_format == "Int16" else pyaudio.paInt24
        logger.debug(f"Audio format uppdaterad till {new_format}.")

    def update_channels(self):
        try:
            new_channels = int(self.channels_input.text())
            config["channels"] = new_channels
            save_config(config)
            self.channels = new_channels
            logger.debug(f"Channels uppdaterade till {new_channels}.")
        except ValueError:
            logger.error("Invalid channels input. Reverting to previous value.")
            self.channels_input.setText(str(config.get("channels", 1)))

    def update_rate(self):
        try:
            new_rate = int(self.rate_input.text())
            config["rate"] = new_rate
            save_config(config)
            self.rate = new_rate
            logger.debug(f"Rate uppdaterade till {new_rate}.")
        except ValueError:
            logger.error("Invalid rate input. Reverting to previous value.")
            self.rate_input.setText(str(config.get("rate", 16000)))

    def update_chunk(self):
        try:
            new_chunk = int(self.chunk_input.text())
            config["chunk"] = new_chunk
            save_config(config)
            self.chunk = new_chunk
            logger.debug(f"Chunk size uppdaterades till {new_chunk}.")
        except ValueError:
            logger.error("Invalid chunk input. Reverting to previous value.")
            self.chunk_input.setText(str(config.get("chunk", 1024)))

    def show_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def update_keyboard_hooks(self):
        # Remove old hooks
        keyboard.unhook_all()
        # Add new hooks based on updated config
        keyboard.on_press_key(config.get("speak_hotkey", "None"), self.handle_hotkey_press, suppress=True)
        keyboard.on_release_key(config.get("speak_hotkey", "None"), self.handle_hotkey_release, suppress=True)
        # Update record button's text
        self.update_record_button_text()
        logger.debug("Keyboard hooks uppdaterade.")

    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def update_status(self, text, is_recording=False):
        self.status_label.setText(text)
        if is_recording:
            self.recording_indicator.start_pulse()
        else:
            self.recording_indicator.stop_pulse()

    def start_recording(self):
        if self.is_recording:
            return
            
        try:
            self.is_recording = True
            self.record_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.update_status("Recording...", True)
            
            if self.recording_thread and self.recording_thread.isRunning():
                self.recording_thread.cleanup_resources()
                self.recording_thread.wait()
            
            # Hämta valda enhetsindex från config
            input_source = config.get("input_source", "microphone")
            mic_device_index = config.get("input_device_index")
            computer_device_index = config.get("computer_device_index")
            
            self.recording_thread = RecordingThread(
                self.audio_format,
                self.channels,
                self.rate,
                self.chunk,
                self.filename,
                input_source,
                mic_device_index=mic_device_index,
                computer_device_index=computer_device_index
            )
            self.recording_thread.recording_complete.connect(self.handle_recording_complete)
            self.recording_thread.error_occurred.connect(self.handle_recording_error)
            self.recording_thread.start()
            logger.debug("Inspelning startad.")
            
        except Exception as e:
            logger.error(f"Fel vid start av inspelning: {e}")
            self.handle_recording_error(str(e))
            self.is_recording = False

    def stop_recording(self):
        if not self.is_recording:
            return
            
        try:
            self.is_recording = False
            if self.recording_thread and self.recording_thread.isRunning():
                self.recording_thread.stop()
            
            self.record_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.update_status("Processing...", False)
            logger.debug("Inspelning stoppad.")
            
        except Exception as e:
            logger.error(f"Fel vid stopp av inspelning: {e}")
            self.handle_recording_error(str(e))

    def handle_recording_error(self, error_message):
        logger.error(f"Inspelningsfel: {error_message}")
        self.update_status(f"Error: {error_message}", False)
        self.record_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.recording_indicator.stop_pulse()
        self.is_recording = False
        self.hotkey_pressed = False

    def cleanup(self):
        if self.recording_thread:
            self.recording_thread.cleanup_resources()
            self.recording_thread.wait()
        if self.transcription_thread:
            self.transcription_thread.wait()
        logger.debug("Cleaned up recording and transcription threads.")

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)

    def handle_recording_complete(self):
        self.update_status("Transcribing...", False)
        self.transcription_thread = TranscriptionThread(
            self.model, self.filename, self.remove_punctuation
        )
        self.transcription_thread.transcription_complete.connect(self.handle_transcription)
        self.transcription_thread.start()
        logger.debug("Recording complete. Started transcription.")

    def handle_transcription(self, text):
        self.output_text.append(text)
        self.update_status("Ready", False)
        self.record_btn.setEnabled(True)
        logger.debug("Transcription complete.")

    def update_model(self, model_name):
        config["model_name"] = model_name
        save_config(config)
        self.init_model()
        logger.debug(f"Model uppdaterad till '{model_name}'.")

    def handle_hotkey_press(self, event):
        if not self.hotkey_pressed:
            self.hotkey_pressed = True
            self.start_recording()

    def handle_hotkey_release(self, event):
        if self.hotkey_pressed:
            self.hotkey_pressed = False
            self.stop_recording()

    # Nya metoder för att hantera ljudkällor och enheter
    def update_input_source(self, selected_source):
        config["input_source"] = selected_source
        save_config(config)
        
        # Aktivera/deaktivera enhetsdropdowns baserat på val
        if selected_source == "microphone":
            self.device_combo.setEnabled(True)
            self.computer_device_combo.setEnabled(False)
        elif selected_source == "computer_audio":
            self.device_combo.setEnabled(False)
            self.computer_device_combo.setEnabled(True)
        elif selected_source == "both":
            self.device_combo.setEnabled(True)
            self.computer_device_combo.setEnabled(True)
        
        logger.debug(f"Ljudkälla uppdaterad till '{selected_source}'.")

    def update_input_device(self, index):
        device_index = self.device_combo.itemData(index)
        if device_index is not None:
            config["input_device_index"] = device_index
            save_config(config)
            logger.debug(f"Mikrofonenhet uppdaterad till index {device_index}.")

    def update_computer_device(self, index):
        computer_device_index = self.computer_device_combo.itemData(index)
        if computer_device_index is not None:
            config["computer_device_index"] = computer_device_index
            save_config(config)
            logger.debug(f"Datorljudenhet uppdaterad till index {computer_device_index}.")

class WhisperHub(QMainWindow):
    def __init__(self, config=None):
        super().__init__()
        self.config = config if config is not None else {"default_theme": "dark"}

        # Initialize all config variables
        self.defining_all_config_variables_from_config()
        
        # Pre-initialize cache in background
        threading.Thread(target=self.init_cache, daemon=True).start()
        
        self.init_ui()
        ThemeManager.apply_widget_theme(self)

    def defining_all_config_variables_from_config(self):
        """
        Retrieve and define all config variables from the config dictionary.
        """
        # Set window geometry using default_window_size
        default_size = config.get("default_window_size", "800x600")
        try:
            width, height = map(int, default_size.lower().split("x"))
            self.setFixedSize(width, height)
            logger.debug(f"Window size set to {width}x{height}.")
        except ValueError:
            logger.error(f"Invalid default_window_size format: '{default_size}'. Expected format 'WIDTHxHEIGHT'.")
        
        # Set window title
        self.setWindowTitle("Whisper Hub")
        logger.debug("Window title set to 'Whisper Hub'.")

    def init_cache(self):
        ModelCache.get_instance()

    def init_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        self.whisper_tab = WhisperTranscription()
        self.tabs.addTab(self.whisper_tab, "Whisper")
        logger.debug("Whisper tab added to the application.")

def main():
    try:
        app = QApplication(sys.argv)
        
        # Load themes based on config
        themes_file_path = config.get("themes_file_path", "themes/custom_themes.json")
        ThemeManager.load_themes(os.path.join(os.path.dirname(__file__), themes_file_path))
        
        # Apply theme
        default_theme = config.get("default_theme", "dark")
        ThemeManager.apply_theme(app, config.get('theme', default_theme))
        logger.debug(f"Theme '{config.get('theme', default_theme)}' applied.")

        window = WhisperHub()
        window.show()
        
        return app.exec()
    
    except Exception as e:
        logger.error(f"Fatal error during startup: {str(e)}")
        traceback.print_exc()
        
        if QApplication.instance():
            QMessageBox.critical(
                None,
                "Fatal Error",
                f"A fatal error occurred during startup:\n\n{str(e)}"
            )
        return 1

if __name__ == "__main__":
    sys.exit(main())
