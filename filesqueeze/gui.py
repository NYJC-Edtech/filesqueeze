"""filesqueeze.gui

GUI status window for FileSqueeze service monitoring.
"""

import tkinter as tk
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import scrolledtext, ttk

from .service import ServiceState, StateProvider


class StatusWindow:
    """Status window for displaying FileSqueeze service state.

    This window provides a real-time view of the service status, including:
    - Service running state
    - Input/output directories
    - Currently processing file (single line)
    - Processed files (scrollable list with timestamps)
    - Compression statistics (completed/failed counts)
    - Service uptime
    - Log file viewer (last 1000 lines)

    The window uses the StateProvider interface for read-only state queries,
    ensuring loose coupling with the service implementation.
    """

    def __init__(self, state_provider: StateProvider, refresh_interval: int | None = 2000):
        """Initialize the status window.

        Args:
            state_provider: StateProvider instance for querying service state.
            refresh_interval: Auto-refresh interval in milliseconds (None for manual refresh only).
                             Default: 2000ms (2 seconds).
        """
        self.state_provider = state_provider
        self.refresh_interval = refresh_interval
        self._auto_refresh_job = None
        self._logs_first_load = True  # Track first log load for auto-scroll

        # Cache config and log file path (avoid creating new Config every refresh)
        from .config import Config

        self._config = Config()
        self._log_file = self._config.log_file

        # Create main window
        self.root = tk.Tk()
        self.root.title("FileSqueeze Status")
        self.root.geometry("700x600")
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
        main_frame.rowconfigure(1, weight=1)  # Tab control expands

        # Title
        title_label = ttk.Label(main_frame, text="FileSqueeze Service Status", font=("Helvetica", 14, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 10))

        # Create notebook (tabs)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Create Status tab
        self._create_status_tab()

        # Create Logs tab
        self._create_logs_tab()

    def _create_status_tab(self):
        """Create the Status tab with service information."""
        # Status tab frame
        status_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(status_tab, text="Status")

        # Configure grid weights
        status_tab.columnconfigure(0, weight=1)
        status_tab.rowconfigure(5, weight=1)  # Processed files expands

        # Service status section
        status_frame = ttk.LabelFrame(status_tab, text="Service Status", padding="5")
        status_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.columnconfigure(1, weight=1)

        # Running status
        ttk.Label(status_frame, text="State:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.status_value = ttk.Label(status_frame, text="", font=("Helvetica", 10, "bold"))
        self.status_value.grid(row=0, column=1, sticky=tk.W)

        # Uptime
        ttk.Label(status_frame, text="Uptime:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.uptime_value = ttk.Label(status_frame, text="")
        self.uptime_value.grid(row=1, column=1, sticky=tk.W)

        # Statistics section
        stats_frame = ttk.LabelFrame(status_tab, text="Statistics", padding="5")
        stats_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        stats_frame.columnconfigure(1, weight=1)

        # Completed count
        ttk.Label(stats_frame, text="Completed:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.completed_value = ttk.Label(stats_frame, text="")
        self.completed_value.grid(row=0, column=1, sticky=tk.W)

        # Failed count
        ttk.Label(stats_frame, text="Failed:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.failed_value = ttk.Label(stats_frame, text="")
        self.failed_value.grid(row=1, column=1, sticky=tk.W)

        # Cleanup Statistics section
        cleanup_frame = ttk.LabelFrame(status_tab, text="Retention Cleanup", padding="5")
        cleanup_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        cleanup_frame.columnconfigure(1, weight=1)

        # Last cleanup time
        ttk.Label(cleanup_frame, text="Last cleanup:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.last_cleanup_value = ttk.Label(cleanup_frame, text="", font=("Helvetica", 9))
        self.last_cleanup_value.grid(row=0, column=1, sticky=tk.W)

        # Compressed files deleted
        ttk.Label(cleanup_frame, text="Compressed deleted:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.compressed_deleted_value = ttk.Label(cleanup_frame, text="", font=("Helvetica", 9))
        self.compressed_deleted_value.grid(row=1, column=1, sticky=tk.W)

        # Archived files deleted
        ttk.Label(cleanup_frame, text="Archived deleted:").grid(row=2, column=0, sticky=tk.W, padx=(0, 5))
        self.archived_deleted_value = ttk.Label(cleanup_frame, text="", font=("Helvetica", 9))
        self.archived_deleted_value.grid(row=2, column=1, sticky=tk.W)

        # Total space freed
        ttk.Label(cleanup_frame, text="Space freed:").grid(row=3, column=0, sticky=tk.W, padx=(0, 5))
        self.space_freed_value = ttk.Label(cleanup_frame, text="", font=("Helvetica", 9))
        self.space_freed_value.grid(row=3, column=1, sticky=tk.W)

        # Directories section
        dirs_frame = ttk.LabelFrame(status_tab, text="Directories", padding="5")
        dirs_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        dirs_frame.columnconfigure(1, weight=1)

        # Input directory
        ttk.Label(dirs_frame, text="Input:").grid(row=0, column=0, sticky=tk.NW, padx=(0, 5))
        self.input_value = ttk.Label(dirs_frame, text="", wraplength=600)
        self.input_value.grid(row=0, column=1, sticky=tk.W)

        # Output directory
        ttk.Label(dirs_frame, text="Output:").grid(row=1, column=0, sticky=tk.NW, padx=(0, 5))
        self.output_value = ttk.Label(dirs_frame, text="", wraplength=600)
        self.output_value.grid(row=1, column=1, sticky=tk.W)

        # Currently processing (single line)
        processing_frame = ttk.LabelFrame(status_tab, text="Currently Processing", padding="5")
        processing_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        processing_frame.columnconfigure(0, weight=1)

        self.processing_value = ttk.Label(processing_frame, text="", font=("Helvetica", 9), anchor=tk.W)
        self.processing_value.grid(row=0, column=0, sticky=(tk.W, tk.E))

        # Processed files section (scrollable)
        processed_frame = ttk.LabelFrame(status_tab, text="Processed Files", padding="5")
        processed_frame.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        processed_frame.columnconfigure(0, weight=1)
        processed_frame.rowconfigure(0, weight=1)

        # Processed files list (scrollable)
        self.processed_text = scrolledtext.ScrolledText(
            processed_frame, height=15, wrap=tk.WORD, state=tk.DISABLED, font=("Consolas", 9)
        )
        self.processed_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Close button
        close_button = ttk.Button(status_tab, text="Close", command=self.close)
        close_button.grid(row=6, column=0, pady=(10, 0))

    def _create_logs_tab(self):
        """Create the Logs tab with log file content."""
        # Logs tab frame
        logs_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(logs_tab, text="Logs")

        # Configure grid weights
        logs_tab.columnconfigure(0, weight=1)
        logs_tab.rowconfigure(1, weight=1)  # Log text expands

        # Instructions label
        instructions = ttk.Label(
            logs_tab,
            text="Showing last 1000 lines. Auto-refreshes every 2s. At bottom = follows new logs. Scrolled up = freezes position.",
            font=("Helvetica", 9),
        )
        instructions.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))

        # Log content (scrollable)
        self.logs_text = scrolledtext.ScrolledText(logs_tab, wrap=tk.WORD, state=tk.DISABLED, font=("Consolas", 8))
        self.logs_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    def update_display(self):
        """Update the display with current service state."""
        try:
            state = self.state_provider.get_state()
            self._update_status(state)
            self._update_stats(state)
            self._update_cleanup_stats(state)
            self._update_directories(state)
            self._update_processing_file(state)
            self._update_processed_files(state)
            self._update_logs()
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

    def _update_cleanup_stats(self, state: ServiceState):
        """Update cleanup statistics display.

        Args:
            state: Current service state.
        """
        cleanup_stats = state.cleanup_stats

        if cleanup_stats.last_cleanup_time:
            # Format the timestamp for display
            try:
                from datetime import datetime

                dt = datetime.fromisoformat(cleanup_stats.last_cleanup_time)
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                self.last_cleanup_value.config(text=time_str)
            except Exception:
                self.last_cleanup_value.config(text=cleanup_stats.last_cleanup_time)
        else:
            self.last_cleanup_value.config(text="Never")

        # Display file counts
        self.compressed_deleted_value.config(text=str(cleanup_stats.compressed_files_deleted))
        self.archived_deleted_value.config(text=str(cleanup_stats.archived_files_deleted))

        # Display space freed in MB
        space_mb = cleanup_stats.total_space_freed / (1024 * 1024)
        if space_mb > 0:
            self.space_freed_value.config(text=f"{space_mb:.2f} MB")
        else:
            self.space_freed_value.config(text="0 MB")

    def _update_directories(self, state: ServiceState):
        """Update directories display.

        Args:
            state: Current service state.
        """
        self.input_value.config(text=str(state.input_dir))
        self.output_value.config(text=str(state.output_dir))

    def _update_processing_file(self, state: ServiceState):
        """Update currently processing file display (single line).

        Args:
            state: Current service state.
        """
        if not state.processing_files:
            self.processing_value.config(text="No files currently processing.")
        else:
            # Show only the first file (should typically be only one anyway)
            filepath = state.processing_files[0]
            filename = Path(filepath).name
            self.processing_value.config(text=filename)

            # If there are more files, indicate it
            if len(state.processing_files) > 1:
                self.processing_value.config(text=f"{filename} (+{len(state.processing_files) - 1} more)")

    def _update_processed_files(self, state: ServiceState):
        """Update processed files list with timestamps.

        Args:
            state: Current service state.
        """
        self.processed_text.config(state=tk.NORMAL)
        self.processed_text.delete(1.0, tk.END)

        if not state.processed_files:
            self.processed_text.insert(tk.END, "No files processed yet.")
        else:
            # Show all processed files, newest at the bottom
            for processed_file in state.processed_files:
                # Parse ISO timestamp and format it
                try:
                    dt = datetime.fromisoformat(processed_file.timestamp)
                    timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    timestamp_str = processed_file.timestamp

                # Format status icon
                status_icon = "✓" if processed_file.success else "✗"

                # Insert line with timestamp and filename
                self.processed_text.insert(tk.END, f"{timestamp_str} {status_icon} {processed_file.filename}\n")

            # Auto-scroll to bottom (newest)
            self.processed_text.see(tk.END)

        self.processed_text.config(state=tk.DISABLED)

    def _update_logs(self):
        """Update logs tab with last 1000 lines from log file.

        Scroll behavior:
        - First load: Always scroll to bottom to show latest logs
        - User at bottom: Auto-scroll to show new logs (follow mode)
        - User scrolled up: Preserve current position (browse mode)
        """
        try:
            log_file = self._log_file

            # Read last 1000 lines
            if log_file.exists():
                with open(log_file, encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                    last_1000 = lines[-1000:] if len(lines) > 1000 else lines

                # Check scroll state BEFORE modifying content
                # yview() returns (first_visible_fraction, last_visible_fraction)
                # e.g., (0.0, 0.5) = viewing top half, (0.5, 1.0) = viewing bottom half
                _, last_fraction = self.logs_text.yview()
                was_at_bottom = last_fraction >= 0.98  # Within 2% of bottom

                # Update content
                new_content = "".join(last_1000)
                self.logs_text.config(state=tk.NORMAL)
                self.logs_text.delete(1.0, tk.END)
                self.logs_text.insert(tk.END, new_content)

                # Restore appropriate scroll position
                if self._logs_first_load or was_at_bottom:
                    # First load or user was following logs -> scroll to bottom
                    self.logs_text.see(tk.END)
                # else: User was browsing -> Tkinter naturally preserves position

                self.logs_text.config(state=tk.DISABLED)
                self._logs_first_load = False
            else:
                self.logs_text.config(state=tk.NORMAL)
                self.logs_text.delete(1.0, tk.END)
                self.logs_text.insert(tk.END, f"Log file not found: {log_file}")
                self.logs_text.config(state=tk.DISABLED)

        except Exception as e:
            self.logs_text.config(state=tk.NORMAL)
            self.logs_text.delete(1.0, tk.END)
            self.logs_text.insert(tk.END, f"Error reading log file: {e}")
            self.logs_text.config(state=tk.DISABLED)

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
            self._auto_refresh_job = self.root.after(self.refresh_interval, self._schedule_refresh)

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
