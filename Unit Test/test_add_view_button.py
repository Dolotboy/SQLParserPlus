import runpy
import tkinter as tk
import unittest
from pathlib import Path


APP_PATH = Path(__file__).resolve().parents[1] / "app.pyw"


def _descendants(widget):
    widgets = []
    for child in widget.winfo_children():
        widgets.append(child)
        widgets.extend(_descendants(child))
    return widgets


class AddViewButtonTests(unittest.TestCase):
    def test_add_view_button_creates_lightblue_view_block(self):
        try:
            probe = tk.Tk()
            probe.withdraw()
            probe.destroy()
        except tk.TclError as error:
            self.skipTest(f"Tk display unavailable: {error}")

        original_mainloop = tk.Tk.mainloop

        def inspect_view_block(root):
            try:
                root.update_idletasks()
                widgets = _descendants(root)
                canvas = next(widget for widget in widgets if isinstance(widget, tk.Canvas))
                add_view_button = next(
                    widget
                    for widget in widgets
                    if isinstance(widget, tk.Button) and widget.cget("text") == "Add View"
                )

                add_view_button.invoke()
                root.update_idletasks()

                view_backgrounds = [
                    item
                    for item in canvas.find_withtag("type:view")
                    if canvas.type(item) == "rectangle"
                ]
                self.assertTrue(view_backgrounds, "Add View did not draw a view block")
                self.assertEqual(canvas.itemcget(view_backgrounds[0], "fill"), "lightblue")
            finally:
                root.destroy()

        tk.Tk.mainloop = inspect_view_block
        try:
            app_module = runpy.run_path(str(APP_PATH), run_name="sqlparserplus_unit_test")
            app_module["main"]()
        finally:
            tk.Tk.mainloop = original_mainloop


if __name__ == "__main__":
    unittest.main()