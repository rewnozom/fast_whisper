# ./fast_whisper_v2/theme_manager.py

from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt
import json
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class ThemeManager:
    DEFAULT_THEMES = {
        "dark": {
            "primary": "#212121",
            "secondary_bg": "#424242",
            "primary_btn": "#B71C1C",
            "primary_btn_hover": "#D32F2F",
            "primary_text": "#d4d4d4",
            "tertiary": "#424242",
            "border": "#616161",
            "error": "#f44336",
            "pressed": "#9A0007"
        },
        "light": {
            "primary": "#ffffff",
            "secondary_bg": "#f5f5f5",
            "primary_btn": "#2196F3",
            "primary_btn_hover": "#1976D2",
            "primary_text": "#212121",
            "tertiary": "#e0e0e0",
            "border": "#bdbdbd",
            "error": "#f44336",
            "pressed": "#1565C0"
        }
    }

    _current_theme = "dark"
    _themes = {}
    _initialized = False

    @classmethod
    def load_themes(cls, custom_themes_path: Optional[str] = None):
        """
        Load themes from a JSON file and combine with default themes.
        """
        cls._themes = cls.DEFAULT_THEMES.copy()
        
        if custom_themes_path and os.path.exists(custom_themes_path):
            try:
                with open(custom_themes_path, 'r') as f:
                    custom_themes = json.load(f)
                cls._themes.update(custom_themes)
                logger.info(f"Loaded custom themes from {custom_themes_path}")
            except Exception as e:
                logger.error(f"Error loading custom themes: {e}")
        
        cls._initialized = True

    @classmethod
    def get_theme_colors(cls, theme_name: str = None):
        """
        Get colors for the specified theme or current theme.
        """
        if not cls._initialized:
            cls.load_themes()
            
        theme_name = theme_name or cls._current_theme
        return cls._themes.get(theme_name, cls.DEFAULT_THEMES["dark"])

    @classmethod
    def apply_theme(cls, app, theme_name: str = None):
        """
        Apply theme to the entire application (compatible with old apply_theme method).
        """
        if not cls._initialized:
            cls.load_themes()
            
        theme_name = theme_name or cls._current_theme
        colors = cls.get_theme_colors(theme_name)
        cls._current_theme = theme_name

        # Create and configure palette
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(colors["primary"]))
        palette.setColor(QPalette.WindowText, QColor(colors["primary_text"]))
        palette.setColor(QPalette.Base, QColor(colors["secondary_bg"]))
        palette.setColor(QPalette.AlternateBase, QColor(colors["tertiary"]))
        palette.setColor(QPalette.Text, QColor(colors["primary_text"]))
        palette.setColor(QPalette.Button, QColor(colors["primary_btn"]))
        palette.setColor(QPalette.ButtonText, QColor(colors["primary_text"]))
        app.setPalette(palette)

        # Apply global stylesheet
        app.setStyleSheet(cls._generate_stylesheet(colors))

    @classmethod
    def apply_widget_theme(cls, widget, theme_name: str = None):
        """
        Apply theme to a specific widget.
        """
        if not cls._initialized:
            cls.load_themes()
            
        theme_name = theme_name or cls._current_theme
        colors = cls.get_theme_colors(theme_name)
        
        # Apply palette to widget
        palette = widget.palette()
        palette.setColor(QPalette.Window, QColor(colors["primary"]))
        palette.setColor(QPalette.WindowText, QColor(colors["primary_text"]))
        palette.setColor(QPalette.Base, QColor(colors["secondary_bg"]))
        palette.setColor(QPalette.AlternateBase, QColor(colors["tertiary"]))
        palette.setColor(QPalette.Text, QColor(colors["primary_text"]))
        palette.setColor(QPalette.Button, QColor(colors["primary_btn"]))
        palette.setColor(QPalette.ButtonText, QColor(colors["primary_text"]))
        widget.setPalette(palette)
        
        # Apply stylesheet to widget
        widget.setStyleSheet(cls._generate_stylesheet(colors))

    @staticmethod
    def _generate_stylesheet(colors):
        """
        Generate stylesheet based on theme colors.
        """
        return f"""
            QPushButton {{
                background-color: {colors["primary_btn"]};
                color: {colors["primary_text"]};
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {colors["primary_btn_hover"]};
            }}
            QPushButton:pressed {{
                background-color: {colors["pressed"]};
            }}
            QTabWidget::pane {{
                border: 1px solid {colors["tertiary"]};
                background: {colors["primary"]};
            }}
            QTabBar::tab {{
                background: {colors["tertiary"]};
                color: {colors["primary_text"]};
                padding: 8px 16px;
            }}
            QTabBar::tab:selected {{
                background: {colors["primary_btn"]};
            }}
            QLineEdit {{
                background-color: {colors["secondary_bg"]};
                color: {colors["primary_text"]};
                border: 1px solid {colors["border"]};
                padding: 4px;
                border-radius: 4px;
            }}
            QComboBox {{
                background-color: {colors["secondary_bg"]};
                color: {colors["primary_text"]};
                border: 1px solid {colors["border"]};
                padding: 4px;
                border-radius: 4px;
            }}
            QTextEdit {{
                background-color: {colors["secondary_bg"]};
                color: {colors["primary_text"]};
                border: 1px solid {colors["border"]};
                padding: 4px;
                border-radius: 4px;
            }}
            QLabel#status_label {{
                color: {colors["primary_text"]};
                font-size: 14px;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }}
            QFrame#recording_indicator {{
                background-color: {colors["primary_btn"]};
                border-radius: 8px;
                min-width: 16px;
                min-height: 16px;
                max-width: 16px;
                max-height: 16px;
            }}
            QFrame#recording_indicator[recording="true"] {{
                background-color: {colors["error"]};
            }}
        """

# For backward compatibility
def apply_theme(app, theme_name: str = "dark"):
    """
    Backward compatibility function for old apply_theme usage.
    """
    ThemeManager.apply_theme(app, theme_name)