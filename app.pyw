import os
import tkinter as tk
from tkinter import Menu
from tkinter import ttk
from tkinter import filedialog as fd
from tkinter.filedialog import askdirectory
import uuid
import sqlParser as sqlp


def main():
    root = tk.Tk()
    root.geometry("800x600")
    root.title("SQL Parser Plus")

    # Variables partagées dans main()
    script = None
    filename = None
    file_label_id = None
    
    # Mapping visual blocks UUID -> Table object
    uuid_to_table = {}
    
    # Context menu state
    ctx_menu_data = {"uuid": None, "column_index": None}

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
        # Use a copy or ensure we don't iterate indefinitely if we were modifying the list (which we won't now, but safer)
        for table in script.tables:
            print(f"Table : {table.name}")
            add_table_block(table.name, add_to_model=False)

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
        if not filename or not filename.lower().endswith(".json"):
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
    file_menu.add_command(label="Exit", command=root.destroy)

    # --- Barre de boutons ---
    toolbar = tk.Frame(main_frame, bg="lightgrey")
    toolbar.pack(side="top", fill="x")

    # --- Zone Canvas ---
    canvas_frame = tk.Frame(main_frame, bg="white")
    canvas_frame.pack(side="top", fill="both", expand=True)

    canvas = tk.Canvas(canvas_frame, bg="white", scrollregion=(0, 0, 2000, 2000))
    canvas.pack(fill="both", expand=True)

    def draw_table_block(table, center_x, center_y, tag_id):
        # Calculate text size for title
        from tkinter import font as tkfont
        title_font = tkfont.Font(family="Arial", size=12, weight="bold")
        col_font = tkfont.Font(family="Arial", size=10)
        
        # Measure title width
        title_w = title_font.measure(table.name)
        title_h = title_font.metrics("linespace")
        
        # Measure columns width
        col_items_metrics = []
        max_col_w = 0
        col_h = col_font.metrics("linespace")
        
        for col in table.columns:
            # Display format: Name (Type)
            # You can adjust this string format as desired
            col_str = f"{col.name} : {col.dataType}" if col.dataType else col.name
            w = col_font.measure(col_str)
            max_col_w = max(max_col_w, w)
            col_items_metrics.append((col_str, w))
            
        padding_x = 10
        # padding_y = 5 # Used inside loops, redefined below
        
        # Calculate Block Dimensions
        # Width is max of title or widest column, plus padding
        block_w = max(title_w, max_col_w) + padding_x * 2 + 20 # Extra 20 for safety/visual
        
        padding_y = 5 
        # Height: title + separator + columns + padding
        # Title section height
        header_h = title_h + padding_y * 2
        
        # Columns section height
        cols_h = len(table.columns) * (col_h + 2) + padding_y # +2 for spacing line
        
        block_h = header_h + cols_h
        
        x1 = center_x - block_w / 2
        y1 = center_y - block_h / 2
        x2 = center_x + block_w / 2
        y2 = center_y + block_h / 2
        
        # Draw Background Rectangle
        rect_id = canvas.create_rectangle(x1, y1, x2, y2, fill="lightgrey", tags=tag_id)
        
        # Draw Title
        title_y = y1 + padding_y + title_h / 2
        canvas.create_text(center_x, title_y, text=table.name, font=title_font, 
                           justify="center", anchor="center", tags=(tag_id, "type:title"))
        
        # Draw Separator
        sep_y = y1 + header_h
        canvas.create_line(x1, sep_y, x2, sep_y, fill="black", tags=tag_id)
        
        # Draw Columns
        current_y = sep_y + padding_y
        for i, (col_str, _) in enumerate(col_items_metrics):
            col_x = x1 + padding_x
            
            # Create text item
            # Tag format: generic block tag, plus specific column tag to identify it
            col_tag = f"col_idx:{i}"
            cid = canvas.create_text(col_x, current_y, text=col_str, font=col_font, 
                               anchor="nw", tags=(tag_id, col_tag, "type:column"))
            
            current_y += col_h + 2

    def add_table_block(table_name: str = "Table_Name", add_to_model: bool = True):
        nonlocal script
        if script is None:
            script = sqlp.Script()
        
        target_table = None
        if add_to_model:
            target_table = sqlp.Table(table_name)
            script.tables.append(target_table)
        else:
            # Find existing table by name
            # Assuming uniqueness or picking last
            for t in script.tables:
                if t.name == table_name:
                    target_table = t
            
            # Fallback if not found (shouldn't happen if logic is consistent)
            if not target_table:
                target_table = sqlp.Table(table_name)
                script.tables.append(target_table)

        # Generate unique tag for this visualization block
        tag_uuid = f"uml_block_{uuid.uuid4()}"
        
        # Register mapping
        uuid_to_table[tag_uuid] = target_table
        
        # Default Position
        center_x = 325
        center_y = 85
        
        draw_table_block(target_table, center_x, center_y, tag_uuid)

    def redraw_block(tag_uuid):
        table = uuid_to_table.get(tag_uuid)
        if not table:
            return
            
        # Get current position center from the rectangle
        # We find items with this tag
        items = canvas.find_withtag(tag_uuid)
        rect_item = None
        for item in items:
            if canvas.type(item) == "rectangle":
                rect_item = item
                break
        
        if rect_item:
            coords = canvas.coords(rect_item)
            center_x = (coords[0] + coords[2]) / 2
            center_y = (coords[1] + coords[3]) / 2
        else:
            # Fallback
            center_x = 325
            center_y = 85
            
        # Clear old items
        canvas.delete(tag_uuid)
        
        # Redraw
        draw_table_block(table, center_x, center_y, tag_uuid)

    # --- Menu Contextuel ---
    menu_table = Menu(root, tearoff=0)
    
    def on_add_column():
        tag = ctx_menu_data["uuid"]
        if not tag: return
        table = uuid_to_table.get(tag)
        if table:
            # Add a default column
            new_col = sqlp.Column("new_col", "VARCHAR(255)")
            table.add_column(new_col)
            redraw_block(tag)
            
    menu_table.add_command(label="Add Column", command=on_add_column)

    menu_column = Menu(root, tearoff=0)
    
    def on_delete_column():
        tag = ctx_menu_data["uuid"]
        idx = ctx_menu_data["column_index"]
        if not tag or idx is None: return
        table = uuid_to_table.get(tag)
        if table and 0 <= idx < len(table.columns):
            table.columns.pop(idx)
            redraw_block(tag)

    menu_column.add_command(label="Delete Column", command=on_delete_column)

    def show_context_menu(event):
        # Determine what we clicked on
        cx = canvas.canvasx(event.x)
        cy = canvas.canvasy(event.y)
        
        # Find closest/overlapping
        items = canvas.find_overlapping(cx-1, cy-1, cx+1, cy+1)
        if not items:
            return
            
        item = items[-1]
        tags = canvas.gettags(item)
        
        # Identify block UUID
        block_tag = None
        for t in tags:
            if t.startswith("uml_block_"):
                block_tag = t
                break
        
        if not block_tag:
            return
            
        ctx_menu_data["uuid"] = block_tag
        ctx_menu_data["column_index"] = None
        
        # Check if it is a column
        is_column = False
        col_idx = None
        for t in tags:
            if t.startswith("col_idx:"):
                try:
                    col_idx = int(t.split(":")[1])
                    is_column = True
                except:
                    pass
        
        if is_column:
            ctx_menu_data["column_index"] = col_idx
            menu_column.post(event.x_root, event.y_root)
        else:
            # Assume general table click
            menu_table.post(event.x_root, event.y_root)

    canvas.bind("<Button-3>", show_context_menu)

    btn_rect = tk.Button(toolbar, text="Add Table", command=add_table_block)
    btn_rect.pack(side="left", padx=2, pady=2)

    btn_circle = tk.Button(toolbar, text="Add Table", command=add_table_block)
    btn_circle.pack(side="left", padx=2, pady=2)

    # --- Scrollbars ---
    hbar = tk.Scrollbar(root, orient="horizontal", command=canvas.xview)
    hbar.pack(side="bottom", fill="x")
    vbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
    vbar.pack(side="right", fill="y")
    canvas.config(xscrollcommand=hbar.set, yscrollcommand=vbar.set)

    # --- Objets initiaux ---
    file_label_id = canvas.create_text(10, 10, anchor="nw", text="Aucun fichier chargé", fill="black", font=("Arial", 10))

    # --- Déplacement des blocs ---
    drag_data = {"x": 0, "y": 0, "item": None}
    
    # State for resizing
    resize_state = {
        "active": False,
        "selected_block_tag": None,
        "original_outline": "black" # Default, will be captured
    }

    def on_click(event):
        # find_closest returns the closest item even if far away.
        # Use find_overlapping to ensure we click ON the item.
        # We MUST convert screen coordinates (event.x, y) to canvas coordinates
        # to account for scrolling (and potential zoom offsets if they affect view).
        cx = canvas.canvasx(event.x)
        cy = canvas.canvasy(event.y)
        
        # Use a small tolerance (1px)
        items = canvas.find_overlapping(cx-1, cy-1, cx+1, cy+1)
        if not items:
            # If strict behavior: clear drag_data item.
            drag_data["item"] = None
            return
            
        # find_overlapping returns tuple. The last one is the top-most.
        item = items[-1]
        drag_data["item"] = item
        drag_data["x"] = event.x
        drag_data["y"] = event.y

        # Update selected block for resizing
        tags = canvas.gettags(item)
        group_tag = None
        for tag in tags:
            if tag.startswith("uml_block"):
                group_tag = tag
                break
        
        if group_tag:
            # If we select a DIFFERENT block, we should reset resize mode on the OLD one if it was active?
            # Or just switch selection.
            # Per plan: "Reset resize mode when clicking a new block" seems safest to avoid confusion.
            if resize_state["selected_block_tag"] and resize_state["selected_block_tag"] != group_tag:
                # If the old one was in resize mode, turn it off visually
                if resize_state["active"]:
                     # Revert appearance of old block
                     old_items = canvas.find_withtag(resize_state["selected_block_tag"])
                     for i in old_items:
                         if canvas.type(i) == 'rectangle':
                             canvas.itemconfig(i, outline=resize_state["original_outline"], width=1)
                     resize_state["active"] = False

            resize_state["selected_block_tag"] = group_tag
            # We don't automatically enter resize mode here, just track selection.

    def toggle_resize_mode(event=None):
        if not resize_state["selected_block_tag"]:
            return
            
        group_tag = resize_state["selected_block_tag"]
        # Find the rectangle item in this group to change border
        items = canvas.find_withtag(group_tag)
        rect_item = None
        text_item = None
        for item in items:
            if canvas.type(item) == 'rectangle':
                rect_item = item
            elif canvas.type(item) == 'text':
                text_item = item
        
        if not rect_item:
            return

        resize_state["active"] = not resize_state["active"]
        
        if resize_state["active"]:
            # Enable resize mode: Blue border
            # Capture original color first just in case (though we assume black/default mostly)
            resize_state["original_outline"] = canvas.itemcget(rect_item, "outline")
            canvas.itemconfig(rect_item, outline="blue", width=3)
            print(f"Resize Mode ON for {group_tag}")
        else:
            # Disable resize mode: Restore
            canvas.itemconfig(rect_item, outline=resize_state["original_outline"], width=1)
            print(f"Resize Mode OFF for {group_tag}")
            
            # Recenter text horizontally
            if text_item:
                x1, y1, x2, y2 = canvas.coords(rect_item)
                center_x = (x1 + x2) / 2
                # Get current text coords
                text_coords = canvas.coords(text_item)
                # Text coords: [x, y]. We only change x.
                canvas.coords(text_item, center_x, text_coords[1])


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
            
            # RESIZE LOGIC
            if resize_state["active"] and resize_state["selected_block_tag"] == group_tag:
                 # We are resizing the SELECTED group
                 # We need to find the rectangle to resize it
                 # And maybe the text to center it? Or just leave text?
                 # Requirement: "redimensionner" - implies updating the rectangle.
                 
                 items_in_group = canvas.find_withtag(group_tag)
                 for item in items_in_group:
                     if canvas.type(item) == 'rectangle':
                         # Get coords
                         x1, y1, x2, y2 = canvas.coords(item)
                         # Simple resize: Dragging anywhere adds dx to x2 and dy to y2 (bottom-right resize)
                         # Or we could be smarter depending on where they clicked, but user asked for "drag and drop" style
                         # usually implying dragging the object itself in a specific mode.
                         # Let's just adjust width/height by dx/dy.
                         
                         # Minimum size check
                         new_x2 = x2 + dx
                         new_y2 = y2 + dy
                         if new_x2 - x1 < 20: new_x2 = x1 + 20
                         if new_y2 - y1 < 20: new_y2 = y1 + 20
                         
                         canvas.coords(item, x1, y1, new_x2, new_y2)
                         
                         # Update center text if desired? 
                         # Usually text stays centered or top-left.
                         # Let's re-center text if strict center is preferred, 
                         # OR just let it wrap if it was elaborate.
                         # The text item is separate.
                     elif canvas.type(item) == 'text':
                         # Optional: realign text?
                         # Current impl: text is just placed at specific coord.
                         # If we want it to stay centered:
                         # We need to know the new rect center.
                         pass
                 
                 # Don't move the items, just resized the rect.
                 # What about text position? If we only resize rect, text might separate visually.
                 # Let's simple-move text relative to resize? No, usually text is content.
                 # Let's keep text in place for now, or maybe it should be anchored.
            
            # MOVE LOGIC (Standard)
            else:
                if group_tag:
                     canvas.move(group_tag, dx, dy)
                else:
                    canvas.move(drag_data["item"], dx, dy)
            
            drag_data["x"], drag_data["y"] = event.x, event.y

    def on_release(event):
        drag_data["item"] = None

    def edit_text_item(item):
        # Retrieve tags to identify what we are editing
        tags = canvas.gettags(item)
        uuid_tag = None
        col_index = None
        is_title = False
        
        for tag in tags:
            if tag.startswith("uml_block_"):
                uuid_tag = tag
            if tag == "type:title":
                is_title = True
            if tag.startswith("col_idx:"):
                try:
                    col_index = int(tag.split(":")[1])
                except: pass
                
        table = uuid_to_table.get(uuid_tag)
        if not table:
            return

        # Get Text
        current_text = canvas.itemcget(item, "text")
        bbox = canvas.bbox(item)
        if not bbox: return
        
        # Entry setup
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        
        entry = tk.Entry(canvas, highlightthickness=0, relief="flat", font="Arial 10") # Font match generic
        if is_title:
             entry.config(font=("Arial", 12, "bold"), justify='center')
        
        entry.insert(0, current_text)
        entry.focus_force()
        
        center_x = (bbox[0] + bbox[2]) / 2
        center_y = (bbox[1] + bbox[3]) / 2
        
        window_id = canvas.create_window(center_x, center_y, window=entry, width=width+20, height=height+5)
        
        def save_edit(event=None):
            new_text = entry.get()
            
            if is_title:
                table.name = new_text
            elif col_index is not None:
                # Update column
                # Checker bounds
                if 0 <= col_index < len(table.columns):
                    if ":" in new_text:
                        parts = new_text.split(":")
                        table.columns[col_index].name = parts[0].strip()
                        if len(parts) > 1:
                            table.columns[col_index].dataType = parts[1].strip()
                    else:
                        table.columns[col_index].name = new_text
            
            canvas.delete(window_id)
            redraw_block(uuid_tag)
            canvas.focus_set()

        def cancel_edit(event=None):
            canvas.delete(window_id)
            canvas.focus_set()

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", save_edit) # Auto-save on click away
        entry.bind("<Escape>", cancel_edit)

    def on_double_click(event):
        # Find item closest to click, corrected for scroll/zoom
        cx = canvas.canvasx(event.x)
        cy = canvas.canvasy(event.y)
        items = canvas.find_closest(cx, cy)
        if not items:
            return
        item = items[0]
        
        # Check if it is a text object and part of a uml_block
        tags = canvas.gettags(item)
        is_uml_block = any(tag.startswith("uml_block") for tag in tags)
        item_type = canvas.type(item)
        
        if is_uml_block and item_type == "text":
            edit_text_item(item)

    canvas.bind("<Button-1>", on_click)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    canvas.bind("<Double-Button-1>", on_double_click)
    
    # Key bindings
    root.bind("<Control-t>", toggle_resize_mode)
    root.bind("<Control-T>", toggle_resize_mode) # Case insensitive safety

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
