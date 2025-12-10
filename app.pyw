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
    file_label_id = None

    # --- Fonctions de menu / fichier ---

    def load_sql(selected_file: str):
        nonlocal script
        try:
            script = sqlp.Script(selected_file)
            print(f"Successfully parsed {selected_file}")
            if file_label_id:
                canvas.itemconfig(file_label_id, text=f"Fichier : {selected_file}")
            load_uml()
        except Exception as e:
            print(f"Error parsing file: {e}")
            script = None

    def load_json(selected_file: str):
        nonlocal script
        print("Loading JSON")
        try:
            print(f"Successfully loaded {selected_file}")
            if file_label_id:
                canvas.itemconfig(file_label_id, text=f"Fichier : {selected_file}")
            load_uml()
        except Exception as e:
            print(f"Error loading file: {e}")
            script = None

    def load_uml():
        print("Loading UML")
        for table in script.tables:
            print(f"Table : {table.name}")
            add_table_block(table.name)

    def select_file():
        nonlocal filename
        filetypes = (
            ("SQL & JSON files", "*.sql *.json"),
            ("All files", "*.*"),
        )

        selected = fd.askopenfilename(
            title="Open a file",
            initialdir="/",
            filetypes=filetypes,
        )

        if selected:
            filename = selected
            if filename.lower().endswith(".sql"):
                print("SQL File selected")
                load_sql(filename)
            elif filename.lower().endswith(".json"):
                print("JSON File selected")
                load_json(filename)

    def output_to_json(output_path: str):
        nonlocal script
        if script is None:
            # Rien n'a été chargé, on ne fait rien
            print("Nothing to save...")
            return

        # Crée ou écrase le fichier
        with open(output_path, "w", encoding="utf-8") as outfile:
            outfile.write(script.to_json())
        print(f"Successfully saved {output_path}")

    def save():
        nonlocal filename
        if not filename.lower().endswith(".json") or not filename:
            path = askdirectory(title="Choose output directory")
            if not path:
                return
            output_path = os.path.join(path, "output.json")
            output_to_json(output_path)
        else:
            output_to_json(filename)

    # --- Frame principal ---
    main_frame = tk.Frame(root)
    main_frame.pack(fill="both", expand=True)

    # --- Menubar ---
    menubar = Menu(root)
    root.config(menu=menubar)

    file_menu = Menu(menubar, tearoff=0)
    menubar.add_cascade(label="File", menu=file_menu)
    file_menu.add_command(label="Open...", command=select_file)
    file_menu.add_command(label="Save", command=save)
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

    def add_table_block(table_name: str):
        uml_rect = canvas.create_rectangle(250, 50, 400, 120, fill="lightgrey")
        uml_text = canvas.create_text(325, 85, text=table_name, font=("Arial", 12, "bold"))
        canvas.addtag_withtag("uml_block_" + table_name, uml_rect)
        canvas.addtag_withtag("uml_block_" + table_name, uml_text)

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
    file_label_id = canvas.create_text(10, 10, anchor="nw", text="Aucun fichier chargé", fill="black", font=("Arial", 10))
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
            
            # Identify the group tag if it exists
            tags = canvas.gettags(drag_data["item"])
            group_tag = None
            for tag in tags:
                if tag.startswith("uml_block"):
                    group_tag = tag
                    break
            
            if group_tag:
                 canvas.move(group_tag, dx, dy)
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
