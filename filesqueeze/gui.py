"""filesqueeze.gui

GUI status window for FileSqueeze service monitoring.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from pathlib import Path
from typing import Optional
from datetime import timedelta

from .service import StateProvider, ServiceState


class StatusWindow:
    """Status window for displaying FileSqueeze service state.

    This window provides a real-time view of the service status, including:
    - Service running state
    - Input/output directories
    - Currently processing files
    - Compression statistics (completed/failed counts)
    - Service uptime

    The window uses the StateProvider interface for read-only state queries,
    ensuring loose coupling with the service implementation.
    """

    def __init__(
        self,
        state_provider: StateProvider,
        refresh_interval: Optional[int] = 2000
    ):
        """Initialize the status window.

        Args:
            state_provider: StateProvider instance for querying service state.
            refresh_interval: Auto-refresh interval in milliseconds (None for manual refresh only).
                             Default: 2000ms (2 seconds).
        """
        self.state_provider = state_provider
        self.refresh_interval = refresh_interval
        self._auto_refresh_job = None

        # Create main window
        self.root = tk.Tk()
        self.root.title("FileSqueeze Status")
        self.root.geometry("600x500")
        self.root.resizable(True, True)

        # Create UI components
        self._create_widgets()

        # Initial state update
        self.update_display()

    def _create_widgets(self):
        """Create all UI widgets."""
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)  # Processing files list expands

        # Title
        title_label = ttk.Label(
            main_frame,
            text="FileSqueeze Service Status",
            font=('Helvetica', 14, 'bold')
        )
        title_label.grid(row=0, column=0, pady=(0, 10))

        # Service status section
        status_frame = ttk.LabelFrame(main_frame, text="Service Status", padding="5")
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.columnconfigure(1, weight=1)

        # Running status
        ttk.Label(status_frame, text="State:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.status_value = ttk.Label(status_frame, text="", font=('Helvetica', 10, 'bold'))
        self.status_value.grid(row=0, column=1, sticky=tk.W)

        # Uptime
        ttk.Label(status_frame, text="Uptime:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.uptime_value = ttk.Label(status_frame, text="")
        self.uptime_value.grid(row=1, column=1, sticky=tk.W)

        # Statistics section
        stats_frame = ttk.LabelFrame(main_frame, text="Statistics", padding="5")
        stats_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        stats_frame.columnconfigure(1, weight=1)

        # Completed count
        ttk.Label(stats_frame, text="Completed:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.completed_value = ttk.Label(stats_frame, text="")
        self.completed_value.grid(row=0, column=1, sticky=tk.W)

        # Failed count
        ttk.Label(stats_frame, text="Failed:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.failed_value = ttk.Label(stats_frame, text="")
        self.failed_value.grid(row=1, column=1, sticky=tk.W)

        # Directories section
        dirs_frame = ttk.LabelFrame(main_frame, text="Directories", padding="5")
        dirs_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        dirs_frame.columnconfigure(1, weight=1)

        # Input directory
        ttk.Label(dirs_frame, text="Input:").grid(row=0, column=0, sticky=tk.NW, padx=(0, 5))
        self.input_value = ttk.Label(dirs_frame, text="", wraplength=500)
        self.input_value.grid(row=0, column=1, sticky=tk.W)

        # Output directory
        ttk.Label(dirs_frame, text="Output:").grid(row=1, column=0, sticky=tk.NW, padx=(0, 5))
        self.output_value = ttk.Label(dirs_frame, text="", wraplength=500)
        self.output_value.grid(row=1, column=1, sticky=tk.W)

        # Processing files section
        processing_frame = ttk.LabelFrame(main_frame, text="Currently Processing", padding="5")
        processing_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        processing_frame.columnconfigure(0, weight=1)
        processing_frame.rowconfigure(0, weight=1)

        # Processing files list (scrollable)
        self.processing_text = scrolledtext.ScrolledText(
            processing_frame,
            height=8,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.processing_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Close button
        close_button = ttk.Button(main_frame, text="Close", command=self.close)
        close_button.grid(row=5, column=0, pady=(10, 0))

    def update_display(self):
        """Update the display with current service state."""
        try:
            state = self.state_provider.get_state()
            self._update_status(state)
            self._update_stats(state)
            self._update_directories(state)
            self._update_processing_files(state)
        except Exception as e:
            # Log error but don't crash
            self.status_value.config(text="Error", foreground="red")
            print(f"Error updating display: {e}")

    def _update_status(self, state: ServiceState):
        """Update service status display.

        Args:
            state: Current service state.
        """
        if state.running:
            self.status_value.config(text="Running", foreground="green")
        else:
            self.status_value.config(text="Stopped", foreground="red")

        # Format uptime
        uptime_str = self._format_timedelta(state.uptime)
        self.uptime_value.config(text=uptime_str)

    def _update_stats(self, state: ServiceState):
        """Update statistics display.

        Args:
            state: Current service state.
        """
        self.completed_value.config(text=str(state.completed_count))
        self.failed_value.config(text=str(state.failed_count))

    def _update_directories(self, state: ServiceState):
        """Update directories display.

        Args:
            state: Current service state.
        """
        self.input_value.config(text=str(state.input_dir))
        self.output_value.config(text=str(state.output_dir))

    def _update_processing_files(self, state: ServiceState):
        """Update processing files list.

        Args:
            state: Current service state.
        """
        self.processing_text.config(state=tk.NORMAL)
        self.processing_text.delete(1.0, tk.END)

        if not state.processing_files:
            self.processing_text.insert(tk.END, "No files currently processing.")
        else:
            for filepath in state.processing_files:
                # Extract just the filename for cleaner display
                filename = Path(filepath).name
                self.processing_text.insert(tk.END, f"{filename}\n")

        self.processing_text.config(state=tk.DISABLED)

    def _format_timedelta(self, td: timedelta) -> str:
        """Format timedelta for display.

        Args:
            td: Timedelta to format.

        Returns:
            Formatted string (e.g., "2h 30m 15s").
        """
        total_seconds = int(td.total_seconds())
        if total_seconds == 0:
            return "Not started"

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0 or not parts:
            parts.append(f"{seconds}s")

        return " ".join(parts)

    def start_auto_refresh(self):
        """Start automatic state refresh."""
        if self.refresh_interval is not None and self._auto_refresh_job is None:
            self._schedule_refresh()

    def _schedule_refresh(self):
        """Schedule the next refresh."""
        if self.root.winfo_exists():
            self.update_display()
            self._auto_refresh_job = self.root.after(
                self.refresh_interval,
                self._schedule_refresh
            )

    def stop_auto_refresh(self):
        """Stop automatic state refresh."""
        if self._auto_refresh_job is not None:
            self.root.after_cancel(self._auto_refresh_job)
            self._auto_refresh_job = None

    def show(self):
        """Show the window and start the event loop."""
        self.start_auto_refresh()
        self.root.mainloop()

    def close(self):
        """Close the window and cleanup resources."""
        self.stop_auto_refresh()
        self.root.destroy()


def show_status_window(state_provider: StateProvider, refresh_interval: int = 2000):
    """Show a status window for the given StateProvider.

    This is a convenience function for creating and displaying a status window.

    Args:
        state_provider: StateProvider instance for querying service state.
        refresh_interval: Auto-refresh interval in milliseconds (default: 2000ms).

    Returns:
        StatusWindow instance.
    """
    window = StatusWindow(state_provider, refresh_interval)
    window.show()
    return window
