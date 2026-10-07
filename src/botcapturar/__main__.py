"""Application entry point."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Callable

from botcapturar.credentials import CredentialStore, CredentialStoreError
from botcapturar.ui import BotCapturarWindow


def main(
    *,
    root_factory: Callable[[], tk.Tk] | None = None,
    credential_store_factory: Callable[[], CredentialStore] | None = None,
    window_factory: Callable[..., BotCapturarWindow] | None = None,
) -> int:
    root = (root_factory or tk.Tk)()
    store_factory = credential_store_factory or CredentialStore
    app_window_factory = window_factory or BotCapturarWindow
    try:
        credential_store = store_factory()
    except CredentialStoreError as error:
        messagebox.showerror("BotCapturar", str(error), parent=root)
        root.destroy()
        return 1

    app_window_factory(root, credential_store=credential_store)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
