import os
import tkinter as tk
from tkinter import Menu
from tkinter import ttk
from tkinter import filedialog as fd
from tkinter.filedialog import askdirectory
import sqlParser as sqlp


def main():
    root = tk.Tk()
    root.geometry("800x600")
    root.title("SQL Parser Plus")

    # Variables partagées dans main()
    script = None
    filename = None

    # --- Fonctions de menu / fichier ---

    def parse(selected_file: str):
        nonlocal script
        script = sqlp.Script(selected_file)

    def select_file():
        nonlocal filename
        filetypes = (
            ("Text files", "*.txt"),
            ("All files", "*.*"),
        )

        selected = fd.askopenfilename(
            title="Open a file",
            initialdir="/",
            filetypes=filetypes,
        )

        if selected:
            filename = selected
            parse(filename)

    def output_to_json():
        nonlocal script
        if script is None:
            # Rien n'a été chargé, on ne fait rien
            return

        path = askdirectory(title="Choose output directory")
        if not path:
            return

        output_path = os.path.join(path, "output.json")

        # Crée ou écrase le fichier
        with open(output_path, "w", encoding="utf-8") as outfile:
            outfile.write(script.to_json())

    # --- Frame principal ---
    main_frame = tk.Frame(root)
    main_frame.pack(fill="both", expand=True)

    # --- Menubar ---
    menubar = Menu(root)
    root.config(menu=menubar)

    file_menu = Menu(menubar, tearoff=0)
    menubar.add_cascade(label="File", menu=file_menu)
    file_menu.add_command(label="Open...", command=select_file)
    file_menu.add_command(label="Save", command=output_to_json)
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=root.destroy)

    # --- Barre de boutons ---
    toolbar = tk.Frame(main_frame, bg="lightgrey")
    toolbar.pack(side="top", fill="x")

    # --- Zone Canvas ---
    canvas_frame = tk.Frame(main_frame, bg="white")
    canvas_frame.pack(side="top", fill="both", expand=True)

    canvas = tk.Canvas(canvas_frame, bg="white", scrollregion=(0, 0, 2000, 2000))
    canvas.pack(fill="both", expand=True)

    # --- Fonctions pour les boutons ---
    def add_rectangle():
        canvas.create_rectangle(100, 200, 200, 300, fill="red")

    def add_circle():
        canvas.create_oval(300, 200, 400, 300, fill="green")

    btn_rect = tk.Button(toolbar, text="Rectangle", command=add_rectangle)
    btn_rect.pack(side="left", padx=2, pady=2)

    btn_circle = tk.Button(toolbar, text="Cercle", command=add_circle)
    btn_circle.pack(side="left", padx=2, pady=2)

    # --- Scrollbars ---
    hbar = tk.Scrollbar(root, orient="horizontal", command=canvas.xview)
    hbar.pack(side="bottom", fill="x")
    vbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
    vbar.pack(side="right", fill="y")
    canvas.config(xscrollcommand=hbar.set, yscrollcommand=vbar.set)

    # --- Objets initiaux ---
    blue_square = canvas.create_rectangle(50, 50, 150, 150, fill="blue")

    uml_rect = canvas.create_rectangle(250, 50, 400, 120, fill="lightgrey")
    uml_text = canvas.create_text(325, 85, text="MaClasse", font=("Arial", 12, "bold"))
    canvas.addtag_withtag("uml_block", uml_rect)
    canvas.addtag_withtag("uml_block", uml_text)

    # --- Déplacement des blocs ---
    drag_data = {"x": 0, "y": 0, "item": None}

    def on_click(event):
        items = canvas.find_closest(event.x, event.y)
        if not items:
            return
        item = items[0]
        drag_data["item"] = item
        drag_data["x"] = event.x
        drag_data["y"] = event.y

    def on_drag(event):
        if drag_data["item"]:
            dx = event.x - drag_data["x"]
            dy = event.y - drag_data["y"]
            if "uml_block" in canvas.gettags(drag_data["item"]):
                canvas.move("uml_block", dx, dy)
            else:
                canvas.move(drag_data["item"], dx, dy)
            drag_data["x"], drag_data["y"] = event.x, event.y

    def on_release(event):
        drag_data["item"] = None

    canvas.bind("<Button-1>", on_click)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)

    # --- Zoom molette ---
    def zoom(event):
        # Windows / macOS: event.delta est non nul
        if hasattr(event, "delta") and event.delta != 0:
            factor = 1.1 if event.delta > 0 else 0.9
        else:
            # Linux/X11: on regarde le bouton utilisé
            if event.num == 4:      # molette vers le haut
                factor = 1.1
            elif event.num == 5:    # molette vers le bas
                factor = 0.9
            else:
                return

        canvas.scale("all", event.x, event.y, factor, factor)
        canvas.configure(scrollregion=canvas.bbox("all"))

    canvas.bind("<MouseWheel>", zoom)   # Windows / macOS
    canvas.bind("<Button-4>", zoom)     # Linux scroll up
    canvas.bind("<Button-5>", zoom)     # Linux scroll down

    # --- Pan avec molette tenue ---
    def start_pan(event):
        canvas.scan_mark(event.x, event.y)

    def do_pan(event):
        canvas.scan_dragto(event.x, event.y, gain=1)

    canvas.bind("<Button-2>", start_pan)   # bouton du milieu
    canvas.bind("<B2-Motion>", do_pan)

    root.mainloop()


if __name__ == "__main__":
    main()
