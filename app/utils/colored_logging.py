"""Colored logging formatter for better visibility."""

import logging


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels."""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m',       # Reset
        'BOLD': '\033[1m',        # Bold
        'CACHE_HIT': '\033[42m\033[30m',   # Green background, black text
        'CACHE_MISS': '\033[43m\033[30m',  # Yellow background, black text
        'BLUE': '\033[34m',       # Blue
        'MAGENTA': '\033[35m',    # Magenta
    }

    def format(self, record):
        """Format log record with colors."""
        # Add color based on level
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"

        # Call parent formatter first to get the formatted message
        formatted = super().format(record)

        # Highlight cache operations with colors
        if '[CACHE HIT]' in formatted:
            formatted = formatted.replace(
                '[CACHE HIT]',
                f"{self.COLORS['CACHE_HIT']}[CACHE HIT]{self.COLORS['RESET']}"
            )
        elif '[CACHE MISS]' in formatted:
            formatted = formatted.replace(
                '[CACHE MISS]',
                f"{self.COLORS['CACHE_MISS']}[CACHE MISS]{self.COLORS['RESET']}"
            )
        elif '[CACHE STORED]' in formatted:
            formatted = formatted.replace(
                '[CACHE STORED]',
                f"{self.COLORS['BLUE']}[CACHE STORED]{self.COLORS['RESET']}"
            )

        # Highlight model operations
        if '[MODEL]' in formatted:
            formatted = formatted.replace(
                '[MODEL]',
                f"{self.COLORS['MAGENTA']}[MODEL]{self.COLORS['RESET']}"
            )

        # Highlight Redis operations
        if '[REDIS]' in formatted:
            formatted = formatted.replace(
                '[REDIS]',
                f"{self.COLORS['BLUE']}[REDIS]{self.COLORS['RESET']}"
            )

        # Highlight rate limit
        if '[RATE LIMIT]' in formatted:
            formatted = formatted.replace(
                '[RATE LIMIT]',
                f"{self.COLORS['WARNING']}[RATE LIMIT]{self.COLORS['RESET']}"
            )

        return formatted


def setup_colored_logging():
    """Set up colored logging for the application."""
    # Create formatter
    formatter = ColoredFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Get root logger
    root_logger = logging.getLogger()

    # Update all handlers
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)

    return formatter