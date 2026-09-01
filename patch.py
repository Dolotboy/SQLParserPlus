import sys
import re

with open("app.pyw", "r") as f:
    code = f.read()

# 1. Modify load_uml
load_uml_old = """    def load_uml():
        print("Loading UML")
        # Use a copy or ensure we don't iterate indefinitely if we were modifying the list (which we won't now, but safer)
        if db_model and db_model.tables:
            # Create a map for faster lookup if UML data exists
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
        
        draw_links()"""
load_uml_new = """    def load_uml():
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
        
        draw_links()"""

code = code.replace(load_uml_old, load_uml_new)
print("load_uml patched:", load_uml_old not in code)

# 2. Add draw_view_block after draw_table_block
draw_view_block = """
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
"""

m = re.search(r'def get_column_connection_point\(block_uuid, col_idx, is_source=True\):', code)
if m:
    pos = m.start()
    code = code[:pos] + draw_view_block + "\n    " + code[pos:]
    print("draw_view_block added")

# 3. Add add_view_block after add_table_block
add_view_block = """
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
"""
m2 = re.search(r'def redraw_block\(tag_uuid\):', code)
if m2:
    pos2 = m2.start()
    code = code[:pos2] + add_view_block + "\n    " + code[pos2:]
    print("add_view_block added")

# 4. Modify draw_links
draw_links_old = """    def draw_links():
        # Clear existing links
        canvas.delete("link_line")
        
        if not db_model: return
        
        # We need to look at every table and every column to see if it has a reference
        # And if that reference points to a valid table/uuid in our current view.
        
        # Map table_name -> uuid for quick lookup
        # uuid_to_table is uuid->Table
        # We need name->uuid
        name_to_uuid = {t.name: u for u, t in uuid_to_table.items()}
        
        for u_src, t_src in uuid_to_table.items():
            for i, col in enumerate(t_src.columns):
                if col.referenceTable and col.referenceColumn:
                    # Find target uuid
                    u_tgt = name_to_uuid.get(col.referenceTable)
                    if not u_tgt: continue
                    
                    # Find column index in target table
                    # We have to look up the target table object
                    t_tgt = uuid_to_table[u_tgt]
                    tgt_col_idx = -1
                    for j, c_tgt in enumerate(t_tgt.columns):
                        if c_tgt.name == col.referenceColumn:
                            tgt_col_idx = j
                            break
                    
                    if tgt_col_idx == -1: continue
                    
                    # Get coordinates
                    src_pt = get_column_connection_point(u_src, i, is_source=True)
                    tgt_pt = get_column_connection_point(u_tgt, tgt_col_idx, is_source=False)
                    
                    if src_pt and tgt_pt:
                        # Draw line
                        # Use smooth line? 
                        canvas.create_line(src_pt[0], src_pt[1], tgt_pt[0], tgt_pt[1], 
                                           arrow=tk.LAST, fill="black", width=2, 
                                           tags=("link_line", f"link_src_{u_src}_{i}"))"""

draw_links_new = """    def draw_links():
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
                                               tags=("link_line", f"link_src_{u_src}_{i}"))"""
code = code.replace(draw_links_old, draw_links_new)
print("draw_links patched:", draw_links_old not in code)

# 5. Modify redraw_block
redraw_block_old = """    def redraw_block(tag_uuid):
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
        block_size = get_dominant_block_size() if consistent_block_size.get() else None
        draw_table_block(table, center_x, center_y, tag_uuid, block_size)
        draw_links()
        apply_selection_visuals()
        update_highlight()"""

redraw_block_new = """    def redraw_block(tag_uuid):
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
        update_highlight()"""

code = code.replace(redraw_block_old, redraw_block_new)
print("redraw_block patched:", redraw_block_old not in code)

# 6. Add toggle_views function
toggle_views_func = """
    def toggle_views(*args):
        state = "normal" if show_views.get() else "hidden"
        for item in canvas.find_withtag("type:view"):
            canvas.itemconfig(item, state=state)
        for item in canvas.find_withtag("type:view_link"):
            canvas.itemconfig(item, state=state)

    show_views.trace_add("write", toggle_views)
"""

m3 = re.search(r'load_options\(\)', code)
if m3:
    pos3 = m3.start()
    code = code[:pos3] + toggle_views_func + "\n    " + code[pos3:]
    print("toggle_views added")

with open("app.pyw", "w") as f:
    f.write(code)

print("Patching complete.")
