"""Allow `py -3 -m echo` as an alternative entry point."""

import tkinter as tk

from echo.ui.app import TranscriberApp


def main() -> None:
    root = tk.Tk()
    TranscriberApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
