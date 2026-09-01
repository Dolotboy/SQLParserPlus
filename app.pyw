import os
import json
import tkinter as tk
from tkinter import Menu
from tkinter import ttk
from tkinter import filedialog as fd
from tkinter.filedialog import askdirectory
import uuid
from collections import Counter
import sqlParser as sqlp


def main():
    root = tk.Tk()
    root.geometry("800x600")
    root.title("SQL Parser Plus")

    # Variables partagées dans main()
    db_model = None
    filename = None
    db_model = None
    filename = None
    file_label_widget = None
    
    # Mapping visual blocks UUID -> Table object
    uuid_to_table = {}
    
    # Context menu state
    ctx_menu_data = {"uuid": None, "column_index": None, "link_tag": None}

    # Link Creation State
    link_creation = {
        "active": False,
        "source_uuid": None,
        "source_col_idx": None,
        "line_id": None
    }
    
    # Selection State
    selection_state = {
        "uuid": None,
        "col_idx": None,
        "rect_item_id": None # For column highlight
    }

    # Edit State
    edit_state = {
        "active": False,
        "save_callback": None
    }

    consistent_block_size = tk.BooleanVar(value=False)
    show_views = tk.BooleanVar(value=True)

    options_path = os.path.join(os.path.expanduser("~"), ".sqlparserplus_options.json")



    def load_options():
        try:
            if os.path.exists(options_path):
                with open(options_path, "r", encoding="utf-8") as infile:
                    opts = json.load(infile)
                if "consistent_block_size" in opts:
                    consistent_block_size.set(opts["consistent_block_size"])
                if "show_views" in opts:
                    show_views.set(opts["show_views"])
        except Exception as exc:
            print(f"Unable to read options: {exc}")

    def save_options(*args):
        try:
            opts = {
                "consistent_block_size": consistent_block_size.get(),
                "show_views": show_views.get()
            }
            with open(options_path, "w", encoding="utf-8") as outfile:
                json.dump(opts, outfile)
        except Exception as exc:
            print(f"Unable to save options: {exc}")

    load_options()

    # --- Fonctions de menu / fichier ---
    last_open_dir_path = os.path.join(os.path.expanduser("~"), ".sqlparserplus_lastdir")

    def get_default_initial_dir() -> str:
        if os.name == "nt":
            return os.path.abspath(os.sep)
        return os.path.expanduser("~")

    def get_last_open_dir() -> str:
        try:
            if os.path.exists(last_open_dir_path):
                with open(last_open_dir_path, "r", encoding="utf-8") as infile:
                    last_dir = infile.read().strip()
                if last_dir and os.path.isdir(last_dir):
                    return last_dir
        except Exception as exc:
            print(f"Unable to read the last used directory: {exc}")
        return get_default_initial_dir()

    def save_last_open_dir(path: str):
        try:
            chosen_dir = os.path.dirname(path) if path else None
            if not chosen_dir or not os.path.isdir(chosen_dir):
                return
            with open(last_open_dir_path, "w", encoding="utf-8") as outfile:
                outfile.write(chosen_dir)
        except Exception as exc:
            print(f"Unable to save the last used directory: {exc}")

    def load_sql(selected_file: str):
        nonlocal db_model
        try:
            db_model = sqlp.DB(selected_file)
            print(f"Successfully parsed {selected_file}")
            if file_label_widget:
                file_label_widget.config(text=f"Fichier : {selected_file}")
            load_uml()
        except Exception as e:
            print(f"Error parsing file: {e}")
            db_model = None
            import traceback
            traceback.print_exc()

    def load_json(selected_file: str):
        nonlocal db_model
        print("Loading JSON")
        try:
            with open(selected_file, "r", encoding="utf-8") as infile:
                data = json.load(infile)
                
            db_model = sqlp.DB.from_dict(data)

            db_model.UML = data.get("UML", [])
            
            print(f"Successfully loaded {selected_file}")
            if file_label_widget:
                file_label_widget.config(text=f"Fichier : {selected_file}")
            load_uml()
        except Exception as e:
            print(f"Error loading file: {e}")
            db_model = None
            import traceback
            traceback.print_exc()

    def load_uml():
        print("Loading UML")
        if db_model and (db_model.tables or db_model.views):
            uml_map = {}
            if hasattr(db_model, "UML") and db_model.UML:
                for item in db_model.UML:
                    uml_map[item.get("table")] = (item.get("x"), item.get("y"))

            for table in db_model.tables:
                print(f"Table : {table.name}")
                if table.name in uml_map:
                    x, y = uml_map[table.name]
                    add_table_block(table.name, table_x=x, table_y=y, add_to_model=False)
                else:
                    add_table_block(table.name, add_to_model=False)
            
            for view in db_model.views:
                print(f"View : {view.name}")
                if view.name in uml_map:
                    x, y = uml_map[view.name]
                    add_view_block(view.name, view_x=x, view_y=y, add_to_model=False)
                else:
                    add_view_block(view.name, add_to_model=False)
        
        draw_links()

    def select_file():
        nonlocal filename
        filetypes = (
            ("SQL & JSON files", "*.sql *.json"),
            ("All files", "*.*"),
        )

        selected = fd.askopenfilename(
            title="Open a file",
            initialdir=get_last_open_dir(),
            filetypes=filetypes,
        )

        if selected:
            filename = selected
            save_last_open_dir(filename)
            if filename.lower().endswith(".sql"):
                print("SQL File selected")
                load_sql(filename)
            elif filename.lower().endswith(".json"):
                print("JSON File selected")
                load_json(filename)

    def output_to_json(output_path: str):
        nonlocal db_model
        if db_model is None:
            # Rien n'a été chargé, on ne fait rien
            print("Nothing to save...")
            return

        # Prepare Data
        # 1. Get Model Data
        data = json.loads(db_model.to_json())
        
        # 2. Get UML Data (Positions)
        # Temporarily show hidden view items so canvas.bbox() works
        hidden_items = []
        for item in canvas.find_withtag("type:view"):
            if canvas.itemcget(item, "state") == "hidden":
                canvas.itemconfig(item, state="normal")
                hidden_items.append(item)

        uml_data = []
        for tag, table_or_view in uuid_to_table.items():
            # Get visual bounds
            bbox = canvas.bbox(tag)
            if bbox:
                x1, y1, x2, y2 = bbox
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                
                uml_entry = {
                    "table": table_or_view.name,
                    "x": int(center_x / zoom_state["level"]),
                    "y": int(center_y / zoom_state["level"])
                }
                uml_data.append(uml_entry)

        # Restore hidden state
        for item in hidden_items:
            canvas.itemconfig(item, state="hidden")
        
        # 3. Add to output
        data["UML"] = uml_data

        # Crée ou écrase le fichier
        with open(output_path, "w", encoding="utf-8") as outfile:
            outfile.write(json.dumps(data, indent=4))
        print(f"Successfully saved {output_path}")

    def export_to_sql():
        nonlocal db_model
        if db_model is None:
            # Rien n'a été chargé, on ne fait rien
            print("Nothing to export...")
            return

        path = askdirectory(title="Choose output directory")
        if not path:
            return
        
        output_path = os.path.join(path, "output.sql")
        with open(output_path, "w", encoding="utf-8") as outfile:
            outfile.write(db_model.to_sql())
        print(f"Successfully exported {output_path}")

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
    file_menu.add_command(label="Export to SQL", command=export_to_sql)

    options_menu = Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Options", menu=options_menu)
    options_menu.add_checkbutton(
        label="Use Dominant Block Size",
        variable=consistent_block_size,
        command=save_options
    )
    options_menu.add_checkbutton(
        label="Show Views",
        variable=show_views,
        command=save_options
    )
    
    def close_current():
        nonlocal db_model, filename, file_label_widget
        db_model = None
        filename = None
        uuid_to_table.clear()
        canvas.delete("all")
        zoom_state["level"] = 1.0
        zoom_state["level"] = 1.0
        # Restore default label
        if file_label_widget:
             file_label_widget.config(text="No file loaded")
        print("Closed current model.")

    file_menu.add_command(label="Close", command=close_current)
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

    def toggle_views(*args):
        state = "normal" if show_views.get() else "hidden"
        for item in canvas.find_withtag("type:view"):
            canvas.itemconfig(item, state=state)
        for item in canvas.find_withtag("type:view_link"):
            canvas.itemconfig(item, state=state)

    show_views.trace_add("write", toggle_views)

    def get_dominant_block_size():
        zoom_level = zoom_state["level"]
        if zoom_level <= 0:
            return None

        sizes = []
        for tag_id in uuid_to_table:
            for item in canvas.find_withtag(tag_id):
                if canvas.type(item) == "rectangle":
                    x1, y1, x2, y2 = canvas.coords(item)
                    sizes.append((
                        round((x2 - x1) / zoom_level),
                        round((y2 - y1) / zoom_level),
                    ))
                    break

        return Counter(sizes).most_common(1)[0][0] if sizes else None

    def draw_table_block(table, center_x, center_y, tag_id, block_size=None):
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
            # Display format: Name : Type [PK][NN][AI]
            attr_text = ""
            if col.attributes:
                attrs_upper = [a.upper() for a in col.attributes]
                if "PRIMARY" in attrs_upper: attr_text += "[PK]"
                if "NOT" in attrs_upper and "NULL" in attrs_upper: attr_text += "[NN]"
                if "AUTO_INCREMENT" in attrs_upper: attr_text += "[AI]"
            
            col_str = f"{col.name} : {col.dataType}" if col.dataType else col.name
            if attr_text:
                col_str += f" {attr_text}"
                
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
        
        btn_row_h = 22 # Space for the "+" button row
        block_h = header_h + cols_h + btn_row_h

        if block_size:
            natural_block_w = block_w
            natural_block_h = block_h
            layout_scale_x = block_size[0] / natural_block_w
            layout_scale_y = block_size[1] / natural_block_h
            content_scale = min(layout_scale_x, layout_scale_y) * zoom_state["level"]
            initial_scale = min(layout_scale_x, layout_scale_y)

            block_w, block_h = block_size
            title_font = tkfont.Font(
                family="Arial",
                size=max(1, round(12 * content_scale)),
                weight="bold",
            )
            col_font = tkfont.Font(
                family="Arial",
                size=max(1, round(10 * content_scale)),
            )
            title_h = title_font.metrics("linespace")
            col_h = col_font.metrics("linespace")
            padding_x *= layout_scale_x * zoom_state["level"]
            padding_y *= layout_scale_y * zoom_state["level"]
            header_h = title_h + padding_y * 2
            cols_h = len(table.columns) * (col_h + 2 * layout_scale_y * zoom_state["level"]) + padding_y
            btn_row_h = 22 * layout_scale_y * zoom_state["level"]

        if block_size:
            block_w *= zoom_state["level"]
            block_h *= zoom_state["level"]
        else:
            initial_scale = 1.0 / zoom_state["level"]
        
        x1 = center_x - block_w / 2
        y1 = center_y - block_h / 2
        x2 = center_x + block_w / 2
        y2 = center_y + block_h / 2
        
        
        # Draw Background Rectangle
        rect_id = canvas.create_rectangle(x1, y1, x2, y2, fill="lightgrey", tags=(tag_id, "type:table_bg"))
        
        # Draw Title
        title_y = y1 + padding_y + title_h / 2
        canvas.create_text(center_x, title_y, text=table.name, font=title_font, 
                           justify="center", anchor="center", tags=(tag_id, "type:title", f"scale:{initial_scale}"))
        
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
                               anchor="nw", tags=(tag_id, col_tag, "type:column", f"scale:{initial_scale}"))
            
            current_y += col_h + 2
            
        # Draw Add Column Button (+)
        btn_size = 18
        btn_font_size = 12
        btn_inset = 5
        if block_size:
            btn_size *= content_scale
            btn_font_size = max(1, round(btn_font_size * content_scale))
            btn_inset *= content_scale
        bx2 = x2 - btn_inset
        by2 = y2 - btn_inset
        bx1 = bx2 - btn_size
        by1 = by2 - btn_size
        
        canvas.create_rectangle(bx1, by1, bx2, by2, fill="#e1e1e1", outline="#999999", tags=(tag_id, "add_btn"))
        canvas.create_text(
            (bx1+bx2)/2,
            (by1+by2)/2,
            text="+",
            font=("Arial", btn_font_size, "bold"),
            fill="#333333",
            tags=(tag_id, "add_btn", "type:add_btn_text", f"scale:{initial_scale}"),
        )
        
        # Draw Links associated with this block (or all links)
        # Calling draw_links() here might be expensive if many blocks move.
        # Ideally we call it once after a move or load.
        # But for now, let's just ensure links are up to date.
        # We will expose a draw_links() function and call it externally or here.
        pass

    
    def draw_view_block(view, center_x, center_y, tag_id, block_size=None):
        from tkinter import font as tkfont
        title_font = tkfont.Font(family="Arial", size=12, weight="bold", slant="italic")
        col_font = tkfont.Font(family="Arial", size=10)
        
        title_w = title_font.measure(view.name)
        title_h = title_font.metrics("linespace")
        
        col_items_metrics = []
        max_col_w = 0
        col_h = col_font.metrics("linespace")
        
        for col in view.columns:
            if col.actualName and col.name != col.actualName:
                col_str = f"{col.actualName} AS {col.name}"
            else:
                col_str = col.name
                
            w = col_font.measure(col_str)
            max_col_w = max(max_col_w, w)
            col_items_metrics.append((col_str, w))
            
        padding_x = 10
        block_w = max(title_w, max_col_w) + padding_x * 2 + 20
        padding_y = 5 
        header_h = title_h + padding_y * 2
        cols_h = len(view.columns) * (col_h + 2) + padding_y
        
        btn_row_h = 0
        block_h = header_h + cols_h + btn_row_h

        if block_size:
            natural_block_w = block_w
            natural_block_h = block_h
            layout_scale_x = block_size[0] / natural_block_w
            layout_scale_y = block_size[1] / natural_block_h
            content_scale = min(layout_scale_x, layout_scale_y) * zoom_state["level"]
            initial_scale = min(layout_scale_x, layout_scale_y)

            block_w, block_h = block_size
            title_font = tkfont.Font(
                family="Arial",
                size=max(1, round(12 * content_scale)),
                weight="bold",
                slant="italic"
            )
            col_font = tkfont.Font(
                family="Arial",
                size=max(1, round(10 * content_scale)),
            )
            title_h = title_font.metrics("linespace")
            col_h = col_font.metrics("linespace")
            padding_x *= layout_scale_x * zoom_state["level"]
            padding_y *= layout_scale_y * zoom_state["level"]
            header_h = title_h + padding_y * 2
            cols_h = len(view.columns) * (col_h + 2 * layout_scale_y * zoom_state["level"]) + padding_y

        if block_size:
            block_w *= zoom_state["level"]
            block_h *= zoom_state["level"]
        else:
            initial_scale = 1.0 / zoom_state["level"]
        
        x1 = center_x - block_w / 2
        y1 = center_y - block_h / 2
        x2 = center_x + block_w / 2
        y2 = center_y + block_h / 2
        
        state = "normal" if show_views.get() else "hidden"
        
        rect_id = canvas.create_rectangle(x1, y1, x2, y2, fill="lightblue", tags=(tag_id, "type:view", "type:table_bg"), state=state)
        
        title_y = y1 + padding_y + title_h / 2
        canvas.create_text(center_x, title_y, text=view.name, font=title_font, 
                           justify="center", anchor="center", tags=(tag_id, "type:view", "type:title", f"scale:{initial_scale}"), state=state)
        
        sep_y = y1 + header_h
        canvas.create_line(x1, sep_y, x2, sep_y, fill="black", tags=(tag_id, "type:view"), state=state)
        
        current_y = sep_y + padding_y
        for i, (col_str, _) in enumerate(col_items_metrics):
            col_x = x1 + padding_x
            col_tag = f"col_idx:{i}"
            cid = canvas.create_text(col_x, current_y, text=col_str, font=col_font, 
                               anchor="nw", tags=(tag_id, col_tag, "type:view", "type:column", f"scale:{initial_scale}"), state=state)
            current_y += col_h + 2

    def get_column_connection_point(block_uuid, col_idx, is_source=True):
        # Find the rectangle
        items = canvas.find_withtag(block_uuid)
        rect_id = None
        for item in items:
             if canvas.type(item) == "rectangle":
                 rect_id = item
                 break
        if not rect_id: return None
        
        rx1, ry1, rx2, ry2 = canvas.coords(rect_id)
        
        # Find the column text
        col_tag = f"col_idx:{col_idx}"
        # Intersection of block_uuid and col_tag
        # Ideally we search items with both tags.
        # canvas.find_withtag is for single tag.
        # Iterate items in group
        col_item = None
        for item in items:
            tags = canvas.gettags(item)
            if col_tag in tags:
                col_item = item
                break
        
        if not col_item:
            # Fallback to header or something? No, return None
            return None
        
        # Get column text center y
        # Text is anchored nw
        cx, cy = canvas.coords(col_item)
        # We need height to find mid-y.
        # Since we don't have the font object easily here reused, 
        # we can use bbox of the text item.
        bbox = canvas.bbox(col_item)
        if not bbox: return None
        mid_y = (bbox[1] + bbox[3]) / 2
        
        if is_source:
            return (rx2, mid_y) # Right side
        else:
            return (rx1, mid_y) # Left side

    def draw_links():
        # Clear existing links
        canvas.delete("link_line")
        
        if not db_model: return
        
        # Map table_name -> uuid for quick lookup
        name_to_uuid = {t.name: u for u, t in uuid_to_table.items()}
        
        for u_src, t_src in uuid_to_table.items():
            if isinstance(t_src, sqlp.View):
                # Handle View links
                for i, col in enumerate(t_src.columns):
                    if col.sourceTable:
                        u_tgt = name_to_uuid.get(col.sourceTable)
                        if not u_tgt: continue
                        t_tgt = uuid_to_table[u_tgt]
                        tgt_col_idx = -1
                        for j, c_tgt in enumerate(t_tgt.columns):
                            if c_tgt.name == col.actualName:
                                tgt_col_idx = j
                                break
                        if tgt_col_idx == -1: continue
                        src_pt = get_column_connection_point(u_src, i, is_source=True)
                        tgt_pt = get_column_connection_point(u_tgt, tgt_col_idx, is_source=False)
                        if src_pt and tgt_pt:
                            state = "normal" if show_views.get() else "hidden"
                            canvas.create_line(src_pt[0], src_pt[1], tgt_pt[0], tgt_pt[1], 
                                               arrow=tk.LAST, fill="green", width=2, 
                                               tags=("link_line", "type:view_link", f"link_src_{u_src}_{i}"), state=state)
            else:
                for i, col in enumerate(t_src.columns):
                    if hasattr(col, "referenceTable") and col.referenceTable and col.referenceColumn:
                        # Find target uuid
                        u_tgt = name_to_uuid.get(col.referenceTable)
                        if not u_tgt: continue
                        
                        t_tgt = uuid_to_table[u_tgt]
                        tgt_col_idx = -1
                        for j, c_tgt in enumerate(t_tgt.columns):
                            if c_tgt.name == col.referenceColumn:
                                tgt_col_idx = j
                                break
                        
                        if tgt_col_idx == -1: continue
                        
                        src_pt = get_column_connection_point(u_src, i, is_source=True)
                        tgt_pt = get_column_connection_point(u_tgt, tgt_col_idx, is_source=False)
                        
                        if src_pt and tgt_pt:
                            canvas.create_line(src_pt[0], src_pt[1], tgt_pt[0], tgt_pt[1], 
                                               arrow=tk.LAST, fill="black", width=2, 
                                               tags=("link_line", f"link_src_{u_src}_{i}"))


    def add_table_block(table_name: str = "Table_Name", table_x: int = 325, table_y: int = 85, add_to_model: bool = True):
        nonlocal db_model
        if db_model is None:
            db_model = sqlp.DB()
        
        target_table = None
        if add_to_model:
            target_table = sqlp.Table(table_name)
            db_model.tables.append(target_table)
        else:
            # Find existing table by name
            # Assuming uniqueness or picking last
            for t in db_model.tables:
                if t.name == table_name:
                    target_table = t
            
            # Fallback if not found (shouldn't happen if logic is consistent)
            if not target_table:
                target_table = sqlp.Table(table_name)
                db_model.tables.append(target_table)

        # Generate unique tag for this visualization block
        tag_uuid = f"uml_block_{uuid.uuid4()}"
        
        # Register mapping
        uuid_to_table[tag_uuid] = target_table
        
        # Default Position
        center_x = table_x
        center_y = table_y
        
        block_size = get_dominant_block_size() if consistent_block_size.get() else None
        draw_table_block(target_table, center_x, center_y, tag_uuid, block_size)
        draw_links()


    
    def add_view_block(view_name: str, view_x: int = 325, view_y: int = 85, add_to_model: bool = True):
        nonlocal db_model
        if db_model is None:
            db_model = sqlp.DB()
        
        target_view = None
        if add_to_model:
            target_view = sqlp.View(view_name)
            db_model.views.append(target_view)
        else:
            for v in db_model.views:
                if v.name == view_name:
                    target_view = v
            
            if not target_view:
                target_view = sqlp.View(view_name)
                db_model.views.append(target_view)

        tag_uuid = f"uml_block_{uuid.uuid4()}"
        uuid_to_table[tag_uuid] = target_view
        
        center_x = view_x
        center_y = view_y
        
        block_size = get_dominant_block_size() if consistent_block_size.get() else None
        draw_view_block(target_view, center_x, center_y, tag_uuid, block_size)
        draw_links()

    def redraw_block(tag_uuid):
        table = uuid_to_table.get(tag_uuid)
        if not table:
            return
            
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
            block_w = coords[2] - coords[0]
            block_h = coords[3] - coords[1]
            zoom_level = zoom_state["level"]
            block_size = (round(block_w / zoom_level), round(block_h / zoom_level)) if consistent_block_size.get() else None
        else:
            center_x = 325
            center_y = 85
            block_size = get_dominant_block_size() if consistent_block_size.get() else None
            
        canvas.delete(tag_uuid)
        
        if isinstance(table, sqlp.View):
            draw_view_block(table, center_x, center_y, tag_uuid, block_size)
        else:
            draw_table_block(table, center_x, center_y, tag_uuid, block_size)
        draw_links()
        apply_selection_visuals()
        update_highlight()

    def update_highlight():
        # Clear previous highlights
        # 1. Reset all table outlines to black (simple bruteforce or smart tracking?)
        # Smart tracking: we know what was selected before, but tracking "previous" is state sync hell.
        # Let's just find the previously selected block if we knew it? 
        # Actually, we can just reset the specific one we are unselecting if we track it.
        # But simpler: We iterate items in selection_state["uuid"] to "unselect" them first?
        # A simpler approach: Tag all "selected" items with "highlighted".
        
        # Reset Table Borders
        # We find touches only the necessary table if possible.
        # But here, let's just use canvas.itemconfig to reset everything? No, slow.
        # Let's rely on finding the item we want to Highlight, and assuming we must Unhighlight others.
        # To avoid global reset, let's assume we maintain the state correctly.
        
        # For now, let's just reset the specific target if state changed?
        # Let's iterate all blocks? No. 
        # Let's search for items with "highlight_border" tag?
        # Better: Tag the highlight effect.
        
        # 1. Remove column highlight rect
        canvas.delete("selection_highlight")
        
        # 2. Reset table borders
        # Find all rectangles in uml blocks? or just the one we knew?
        # Let's search for "type:table_bg" (we need to tag background rects)
        # We didn't tag them "type:table_bg" yet. Let's add that to draw_table_block.
        # Assuming we modify draw_table_block below.
        
        # For now, simplistic approach:
        # We know the UUID of the CURRENT selection.
        # We need to unselect everything else? 
        # Actually, standard behavior: Select New -> Unselect Old.
        # So we just need to ensure we don't leave artifacts.
        
        pass 
        # Real implementation inside checking selection_state below
        
        uuid = selection_state["uuid"]
        col_idx = selection_state["col_idx"]
        
        # First, reset ALL outlines to black. 
        # Ideally we only reset the previous one.
        # We can store "last_highlighted_uuid" in state.
        pass

    def apply_selection_visuals():
        # Clean up
        canvas.delete("selection_highlight")
        # Reset all blocks to black outline? 
        # This is heavy. Let's optimize: only reset if we change selection.
        # But since valid "black" is standard, let's just ensure we set "blue" on current.
        # AND reset "blue" items to "black".
        
        # Find all items that are blue and reset them?
        # Canvas doesn't easily query by color.
        # We will use a dedicated tag "selected_border" for the rectangle.
        
        # Strategy:
        # 1. Find all items with tag "selected" (we will add this tag).
        # 2. Reset their outline to black.
        # 3. Remove tag "selected".
        # 4. Apply new selection.
        
        # Existing selected items
        items = canvas.find_withtag("selected_table")
        for item in items:
            canvas.itemconfig(item, outline="black", width=1)
            canvas.dtag(item, "selected_table")
            
        if not selection_state["uuid"]:
            return

        tag = selection_state["uuid"]
        
        # If Table Selection
        if selection_state["col_idx"] is None:
            # Find the rectangle
            # We assume the rectangle is the one with tag `tag` and type rectangle
            items = canvas.find_withtag(tag)
            for item in items:
                if canvas.type(item) == "rectangle":
                    canvas.itemconfig(item, outline="blue", width=2)
                    canvas.addtag_withtag("selected_table", item)
                    break 
        
        # If Column Selection
        else:
            # We want to draw a blue rectangle around the column text
            # And it must move with the block.
            idx = selection_state["col_idx"]
            
            # Find the column text item
            # Helper function logic
            items = canvas.find_withtag(tag)
            col_item = None
            col_tag = f"col_idx:{idx}"
            for item in items:
                tags = canvas.gettags(item)
                if col_tag in tags:
                    col_item = item
                    break
            
            if col_item:
                bbox = canvas.bbox(col_item)
                if bbox:
                    # Draw rect
                    # Expand slightly
                    x1, y1, x2, y2 = bbox
                    rect = canvas.create_rectangle(x1-2, y1-2, x2+2, y2+2, outline="blue", width=2, 
                                                   tags=("selection_highlight", tag)) 
                                                   # Add 'tag' so it moves with group!


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
    
    def on_delete_table():
        tag = ctx_menu_data["uuid"]
        if not tag: return
        table = uuid_to_table.get(tag)
        if table:
            # Remove from model
            if db_model and table in db_model.tables:
                db_model.tables.remove(table)
            
            # Remove from visual mapping
            del uuid_to_table[tag]
            
            # Remove from canvas
            canvas.delete(tag)
            
    menu_table.add_command(label="Delete Table", command=on_delete_table)

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
    menu_column.add_separator()

    def on_toggle_pk():
        tag = ctx_menu_data["uuid"]
        idx = ctx_menu_data["column_index"]
        if not tag or idx is None: return
        table = uuid_to_table.get(tag)
        if table and 0 <= idx < len(table.columns):
            col = table.columns[idx]
            if not col.attributes: col.attributes = []
            attrs_upper = [a.upper() for a in col.attributes]
            if "PRIMARY" in attrs_upper:
                # Remove PRIMARY KEY
                col.attributes = [a for a in col.attributes if a.upper() not in ["PRIMARY", "KEY"]]
            else:
                # Add PRIMARY KEY
                col.attributes.extend(["PRIMARY", "KEY"])
            redraw_block(tag)

    def on_toggle_nn():
        tag = ctx_menu_data["uuid"]
        idx = ctx_menu_data["column_index"]
        if not tag or idx is None: return
        table = uuid_to_table.get(tag)
        if table and 0 <= idx < len(table.columns):
            col = table.columns[idx]
            if not col.attributes: col.attributes = []
            attrs_upper = [a.upper() for a in col.attributes]
            if "NOT" in attrs_upper and "NULL" in attrs_upper:
                # Remove NOT NULL
                col.attributes = [a for a in col.attributes if a.upper() not in ["NOT", "NULL"]]
            else:
                # Add NOT NULL
                col.attributes.extend(["NOT", "NULL"])
            redraw_block(tag)

    def on_toggle_ai():
        tag = ctx_menu_data["uuid"]
        idx = ctx_menu_data["column_index"]
        if not tag or idx is None: return
        table = uuid_to_table.get(tag)
        if table and 0 <= idx < len(table.columns):
            col = table.columns[idx]
            if not col.attributes: col.attributes = []
            attrs_upper = [a.upper() for a in col.attributes]
            if "AUTO_INCREMENT" in attrs_upper:
                # Remove AUTO_INCREMENT
                col.attributes = [a for a in col.attributes if a.upper() != "AUTO_INCREMENT"]
            else:
                # Add AUTO_INCREMENT
                col.attributes.append("AUTO_INCREMENT")
            redraw_block(tag)

    menu_column.add_command(label="Toggle Primary Key", command=on_toggle_pk)
    menu_column.add_command(label="Toggle Not Null", command=on_toggle_nn)
    menu_column.add_command(label="Toggle Auto Increment", command=on_toggle_ai)
    menu_column.add_separator()
    
    def on_create_link():
        # Start link creation mode
        tag = ctx_menu_data["uuid"]
        idx = ctx_menu_data["column_index"]
        if not tag or idx is None: return
        
        # Set state
        link_creation["active"] = True
        link_creation["source_uuid"] = tag
        link_creation["source_col_idx"] = idx
        
        # Get starting point
        start_pt = get_column_connection_point(tag, idx, is_source=True)
        if start_pt:
            # Create a temp line
            # End point is initially same as start
            line = canvas.create_line(start_pt[0], start_pt[1], start_pt[0], start_pt[1], 
                                      dash=(4, 2), fill="blue", width=2, tags="temp_link")
            link_creation["line_id"] = line
        
        print(f"Link creation started from {tag} col {idx}")

    menu_column.add_command(label="Create a link", command=on_create_link)

    def on_delete_link_column():
        tag = ctx_menu_data["uuid"]
        idx = ctx_menu_data["column_index"]
        if not tag or idx is None: return
        
        table = uuid_to_table.get(tag)
        if not table: return
        
        # Check specific column FK deletion
        if 0 <= idx < len(table.columns):
            col = table.columns[idx]
            if col.referenceTable:
                # It is a Foreign Key, simple delete
                col.referenceTable = None
                col.referenceColumn = None
                print(f"Deleted FK on {table.name}.{col.name}")
        
        # Check Reference deletion (Cascade)
        # Search ALL tables for columns referencing THIS column
        col_name = table.columns[idx].name
        for t in db_model.tables:
            for c in t.columns:
                 if c.referenceTable == table.name and c.referenceColumn == col_name:
                     c.referenceTable = None
                     c.referenceColumn = None
                     print(f"Deleted reference from {t.name}.{c.name} to {table.name}.{col_name}")
        
        draw_links()

    menu_column.add_command(label="Delete Link", command=on_delete_link_column)
    
    # --- Link Context Menu ---
    menu_link = Menu(root, tearoff=0)
    
    def on_delete_link_line():
        link_tag = ctx_menu_data["link_tag"] # Expected format: link_src_UUID_IDX
        if not link_tag: return
        
        try:
             parts = link_tag.split("_")
             # format: link_src_{uuid}_{idx}
             # uuid might haveunderscores? UUID usually uses hyphens.
             # Let's handle parsing carefully.
             # parts[0] = link
             # parts[1] = src
             # parts[-1] = idx
             # middle = uuid
             
             idx = int(parts[-1])
             uuid_str = "_".join(parts[2:-1])
             
             table = uuid_to_table.get(f"uml_block_{uuid_str}")
             # Wait, our tag constructed: f"link_src_{u_src}_{i}" where u_src is the full tag key "uml_block_..."
             
             # So u_src contains underscores. 
             # Re-parse:
             # prefix: "link_src_" length 9.
             # suffix: "_{i}" last underscore.
             
             last_underscore = link_tag.rfind("_")
             idx_str = link_tag[last_underscore+1:]
             idx = int(idx_str)
             
             u_src = link_tag[9:last_underscore]
             
             table = uuid_to_table.get(u_src)
             if table and 0 <= idx < len(table.columns):
                 col = table.columns[idx]
                 col.referenceTable = None
                 col.referenceColumn = None
                 print(f"Deleted link via line click: {table.name}.{col.name}")
                 draw_links()
        except Exception as e:
            print(f"Error deleting link: {e}")

    menu_link.add_command(label="Delete Link", command=on_delete_link_line)


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
            
            # UPDATE SELECTION FOR RIGHT CLICK
            selection_state["uuid"] = block_tag
            selection_state["col_idx"] = col_idx
            apply_selection_visuals()
            
            menu_column.post(event.x_root, event.y_root)
            return

        # Check for Link (lower priority than column/table blocks usually, but strict check here)
        # We need to check if we clicked a line. 
        # find_overlapping returns all. We looked at top-most (-1).
        # If top most was NOT a block, maybe it was a link?
        # Or maybe the link is ON TOP of the block? (Usually lines are drawn after/above rects or before?)
        # Let's iterate all items found
        link_tag_found = None
        for item in items:
            tgs = canvas.gettags(item)
            for t in tgs:
                if t.startswith("link_src_"):
                    link_tag_found = t
                    break
            if link_tag_found: break
        
        if link_tag_found:
            ctx_menu_data["link_tag"] = link_tag_found
            menu_link.post(event.x_root, event.y_root)
            return

        # If block tag found but not column
        if block_tag:
             selection_state["uuid"] = block_tag
             selection_state["col_idx"] = None
             apply_selection_visuals()
             
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
    # Create a Label widget instead of canvas text to keep it fixed
    file_label_widget = tk.Label(canvas_frame, text="Aucun fichier chargé", bg="white", font=("Arial", 10))
    file_label_widget.place(x=10, y=10)

    # --- Déplacement des blocs ---
    drag_data = {"x": 0, "y": 0, "item": None}
    
    # State for resizing
    resize_state = {
        "active": False,
        "selected_block_tag": None,
        "active": False,
        "selected_block_tag": None,
        "original_outline": "black" # Default, will be captured
    }
    
    # Zoom State
    zoom_state = {"level": 1.0}

    def on_click(event):
        # Auto-save edit if active
        if edit_state["active"] and edit_state["save_callback"]:
             edit_state["save_callback"]()
             # If we saved, we might have redrawn blocks. 
             # Proceeding with standard click logic is fine as it re-finds items based on coordinates.
             
        # Close any open context menus
        try:
             menu_table.unpost()
             menu_column.unpost()
             menu_link.unpost()
        except:
             pass

        # LINK CREATION LOGIC
        if link_creation["active"]:
            # Check what we clicked on
            cx = canvas.canvasx(event.x)
            cy = canvas.canvasy(event.y)
            
            # Find closest item
            items = canvas.find_overlapping(cx-1, cy-1, cx+1, cy+1)
            target_col_item = None
            target_block_uuid = None
            
            # Logic to find if we clicked a valid column
            for item in items:
                tags = canvas.gettags(item)
                # We need to find the block and the col index
                # Tags: "uml_block_...", "col_idx:..."
                is_col = False
                blk = None
                for t in tags:
                    if t.startswith("col_idx:"):
                        is_col = True
                    if t.startswith("uml_block_"):
                        blk = t
                
                if is_col and blk:
                     target_col_item = item
                     target_block_uuid = blk
                     break
            
            
            # Clean up target indicator if exists
            canvas.delete("link_target_indicator")

            if target_col_item and target_block_uuid:
                 # Resolve column index
                 tags = canvas.gettags(target_col_item)
                 col_idx = -1
                 for t in tags:
                     if t.startswith("col_idx:"):
                         try: col_idx = int(t.split(":")[1])
                         except: pass
                 
                 # UPDATE SELECTION
                 selection_state["uuid"] = target_block_uuid
                 selection_state["col_idx"] = col_idx
                 apply_selection_visuals()
                 
                 # Create the link in Model
                 source_uuid = link_creation["source_uuid"]
                 source_idx = link_creation["source_col_idx"]
                 
                 source_table = uuid_to_table.get(source_uuid)
                 target_table = uuid_to_table.get(target_block_uuid)
                 
                 if source_table and target_table and col_idx != -1:
                     # Update the SOURCE column to point to TARGET
                     src_col = source_table.columns[source_idx]
                     tgt_col = target_table.columns[col_idx]
                     
                     # Check if we are linking to same table? (Self-referencing is allowed)
                     
                     src_col.referenceTable = target_table.name
                     src_col.referenceColumn = tgt_col.name
                     
                     print(f"Created link: {source_table.name}.{src_col.name} -> {target_table.name}.{tgt_col.name}")
            
            # Finish link creation (success or cancel if clicked elsewhere)
            link_creation["active"] = False
            canvas.delete(link_creation["line_id"])
            canvas.delete("link_target_indicator") # Ensure cleanup
            link_creation["line_id"] = None
            link_creation["source_uuid"] = None
            link_creation["source_col_idx"] = None
            
            draw_links()
            return # Don't process other click logic

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
        
        # Check if Add Column Button was clicked
        tags = canvas.gettags(item)
        if "add_btn" in tags:
            for t in tags:
                if t.startswith("uml_block_"):
                    ctx_menu_data["uuid"] = t
                    on_add_column()
                    return "break"

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
            
            # Update links during drag (could be optimized)
            draw_links()

    def on_mouse_move(event):
        if link_creation["active"] and link_creation["line_id"]:
            cx = canvas.canvasx(event.x)
            cy = canvas.canvasy(event.y)
            coords = canvas.coords(link_creation["line_id"])
            # coords is [x1, y1, x2, y2]. Update x2, y2
            canvas.coords(link_creation["line_id"], coords[0], coords[1], cx, cy)
            
            # Target Indicator Logic
            # Find closest item under mouse same way as click
            items = canvas.find_overlapping(cx-1, cy-1, cx+1, cy+1)
            target_uuid = None
            target_col_idx = None
            
            for item in items:
                tags = canvas.gettags(item)
                is_col = False
                blk = None
                for t in tags:
                     if t.startswith("col_idx:"):
                         is_col = True
                     if t.startswith("uml_block_"):
                         blk = t
                if is_col and blk:
                     # Check if it's the source?
                     if blk == link_creation["source_uuid"]:
                          # Optional: Don't highlight self if not desired, 
                          # but self-references are valid SQL.
                          pass
                     
                     target_uuid = blk
                     # Extract idx
                     for t in tags:
                         if t.startswith("col_idx:"):
                             try: target_col_idx = int(t.split(":")[1])
                             except: pass
                     break
            
            # If found valid target, show indicator
            if target_uuid and target_col_idx is not None:
                # Calculate connection point
                # is_source=False => Left side
                pt = get_column_connection_point(target_uuid, target_col_idx, is_source=False)
                if pt:
                    # Draw or move indicator
                    # Check if exists
                    ind = canvas.find_withtag("link_target_indicator")
                    r = 4
                    if ind:
                        canvas.coords(ind, pt[0]-r, pt[1]-r, pt[0]+r, pt[1]+r)
                    else:
                        canvas.create_oval(pt[0]-r, pt[1]-r, pt[0]+r, pt[1]+r, fill="blue", outline="blue", tags="link_target_indicator")
            else:
                 # Remove if not over valid target
                 canvas.delete("link_target_indicator")


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
        
        # ACTIVATE EDIT STATE
        edit_state["active"] = True
        
        container = None
        entry = None # For title
        name_entry = None # For column
        type_combo = None # For column
        pk_var = None
        nn_var = None
        ai_var = None
        
        if is_title:
             entry = tk.Entry(canvas, highlightthickness=0, relief="flat", font=("Arial", 12, "bold"), justify='center')
             entry.insert(0, current_text)
             entry.focus_force()
             
             center_x = (bbox[0] + bbox[2]) / 2
             center_y = (bbox[1] + bbox[3]) / 2
             window_id = canvas.create_window(center_x, center_y, window=entry, width=width+20, height=height+5)
             
             widget_main = entry
             
        elif col_index is not None:
             # Parse current text "Name : Type"
             col_name_val = ""
             col_type_val = ""
             if ":" in current_text:
                 parts = current_text.split(":")
                 col_name_val = parts[0].strip()
                 if len(parts) > 1: result_type = parts[1].strip()
                 # But wait, original code constructed it as f"{col.name} : {col.dataType}"
                 # So we can trust that structure mostly.
                 col_type_val = parts[1].strip() if len(parts)>1 else ""
             else:
                 col_name_val = current_text
            
             # Create Frame
             container = tk.Frame(canvas, bg="white")
             
             # Name Entry
             name_entry = tk.Entry(container, width=15, highlightthickness=1, relief="solid")
             name_entry.insert(0, col_name_val)
             name_entry.pack(side="left", padx=1)
             
             # Type Combobox
             common_types = ["INTEGER", "VARCHAR(255)", "TEXT", "BOOLEAN", "DATE", "DATETIME", "FLOAT", "DOUBLE", "BLOB", "SERIAL"]
             type_combo = ttk.Combobox(container, values=common_types, width=12)
             type_combo.set(col_type_val)
             type_combo.pack(side="left", padx=1)
             
             # Attributes Checkbuttons
             col = table.columns[col_index]
             attrs_upper = [a.upper() for a in col.attributes] if col.attributes else []
             
             pk_var = tk.BooleanVar(value="PRIMARY" in attrs_upper)
             nn_var = tk.BooleanVar(value="NOT" in attrs_upper and "NULL" in attrs_upper)
             ai_var = tk.BooleanVar(value="AUTO_INCREMENT" in attrs_upper)
             
             tk.Checkbutton(container, text="PK", variable=pk_var, bg="white").pack(side="left", padx=1)
             tk.Checkbutton(container, text="NN", variable=nn_var, bg="white").pack(side="left", padx=1)
             tk.Checkbutton(container, text="AI", variable=ai_var, bg="white").pack(side="left", padx=1)
             
             name_entry.focus_force()
             
             center_x = (bbox[0] + bbox[2]) / 2
             center_y = (bbox[1] + bbox[3]) / 2
             # We need more width for both
             window_id = canvas.create_window(center_x, center_y, window=container) # Let it size itself?
             
             widget_main = name_entry # For binding? Bind to both?
        
        def save_edit(event=None):
            if is_title and entry:
                new_text = entry.get()
                table.name = new_text
            elif col_index is not None and name_entry and type_combo:
                new_name = name_entry.get()
                new_type = type_combo.get()
                
                # Update column
                if 0 <= col_index < len(table.columns):
                    col = table.columns[col_index]
                    col.name = new_name
                    col.dataType = new_type
                    
                    # Update attributes
                    new_attrs = []
                    if pk_var.get(): new_attrs.extend(["PRIMARY", "KEY"])
                    if nn_var.get(): new_attrs.extend(["NOT", "NULL"])
                    if ai_var.get(): new_attrs.append("AUTO_INCREMENT")
                    col.attributes = new_attrs
            
            canvas.delete(window_id)
            edit_state["active"] = False
            edit_state["save_callback"] = None
            redraw_block(uuid_tag)
            canvas.focus_set()

        def cancel_edit(event=None):
            canvas.delete(window_id)
            edit_state["active"] = False
            edit_state["save_callback"] = None
            canvas.focus_set()
        
        # Register callback for auto-save
        edit_state["save_callback"] = save_edit

        if is_title and entry:
            entry.bind("<Return>", save_edit)
            entry.bind("<FocusOut>", save_edit) 
            entry.bind("<Escape>", cancel_edit)
        elif container:
            # Bind to internal widgets
            name_entry.bind("<Return>", save_edit)
            # name_entry.bind("<FocusOut>", save_edit) # FocusOut on one widget might trigger when moving to next.
            # Ideally verify focus is leaving the Container? 
            # Tkinter doesn't have easy "FocusOut of Frame".
            # Let's remove FocusOut auto-save for columns to allow switching between Name and Type.
            # User must press Return to save.
            
            type_combo.bind("<Return>", save_edit)
            
            name_entry.bind("<Escape>", cancel_edit)
            type_combo.bind("<Escape>", cancel_edit)

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
    canvas.bind("<Motion>", on_mouse_move)
    canvas.bind("<ButtonRelease-1>", on_release)
    canvas.bind("<Double-Button-1>", on_double_click)
    
    # Key bindings
    root.bind("<Control-t>", toggle_resize_mode)
    root.bind("<Control-T>", toggle_resize_mode) # Case insensitive safety

    # --- Zoom molette ---
    def zoom(event):
        # Determine scale factor
        if hasattr(event, "delta") and event.delta != 0:
            # Windows/Mac
            factor = 1.1 if event.delta > 0 else 0.9
        else:
            # Linux buttons
            if event.num == 4: factor = 1.1
            elif event.num == 5: factor = 0.9
            else: return

        # 1. Get mouse position in Canvas Coordinates BEFORE scale
        # canvasx/y gives the coordinate in the scrollable space
        cx = canvas.canvasx(event.x)
        cy = canvas.canvasy(event.y)
        
        # 2. Scale all items around (0,0)
        # This preserves the global coordinate system integrity (Model * Zoom = View)
        canvas.scale("all", 0, 0, factor, factor)
        
        # 3. Update Global Zoom State
        zoom_state["level"] *= factor
        
        # 4. Update Scrollregion
        # We need to update this so the scrollbars know the new universe size
        canvas.configure(scrollregion=canvas.bbox("all"))

        # 5. Adjust Viewport to keep mouse fixed
        # The point (cx, cy) is now at (cx*factor, cy*factor) in the new space.
        # We want the screen position (event.x, event.y) to point to this new location.
        # Current Left-Top of view is (canvasx(0), canvasy(0)).
        # New desired Left-Top (L, T) must satisfy: 
        #    L + event.x = cx * factor
        #    T + event.y = cy * factor
        # => L = cx * factor - event.x
        
        new_left = cx * factor - event.x
        new_top = cy * factor - event.y
        
        # We use xview_moveto / yview_moveto
        # Need to calculate fraction relative to scrollregion
        scroll_bbox = canvas.bbox("all")
        if scroll_bbox:
            sx1, sy1, sx2, sy2 = scroll_bbox
            # Width/Height of content
            w = sx2 - sx1
            h = sy2 - sy1
            
            # Avoid division by zero
            if w > 1:
                # fraction = (desired_pos - start_pos) / total_width
                fx = (new_left - sx1) / w
                canvas.xview_moveto(fx)
            if h > 1:
                fy = (new_top - sy1) / h
                canvas.yview_moveto(fy)
        
        # 6. Scale Fonts (Text sizes remain constant in scale(), so we adjust manually)
        def update_font_size(tag_type, base_size, is_bold=False):
            for item in canvas.find_withtag(tag_type):
                tags = canvas.gettags(item)
                scale = 1.0
                for t in tags:
                    if t.startswith("scale:"):
                        try:
                            scale = float(t.split(":")[1])
                        except ValueError:
                            pass
                new_size = max(1, round(base_size * scale * zoom_state["level"]))
                font_config = ("Arial", new_size, "bold") if is_bold else ("Arial", new_size)
                canvas.itemconfig(item, font=font_config)

        update_font_size("type:title", 12, True)
        update_font_size("type:column", 10, False)
        update_font_size("type:add_btn_text", 12, True)

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
