#!/usr/bin/env python3
"""
Pixel Measurement Application
Aplikasi untuk mengukur pixel pada gambar dengan fitur kalibrasi
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
import math
import os

class PixelMeasurementApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pixel Measurement Tool")
        self.root.geometry("2880x1800")
        
        # Variables
        self.image = None
        self.display_image = None
        self.photo = None
        self.scale_factor = 1.0
        self.zoom_factor = 1.0  # Separate zoom factor for user interaction
        self.calibration_pixels_per_cm = 1.0  # Default: 1 pixel = 1 cm
        
        # Drawing variables
        self.drawing = False
        self.start_x = None
        self.start_y = None
        self.lines = []  # Store all drawn lines
        self.current_line = None
        
        # Modes
        self.mode = "measure"  # "measure" or "calibrate"
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Control panel
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # File operations
        file_frame = ttk.LabelFrame(control_frame, text="File Operations")
        file_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(file_frame, text="Load Image", command=self.load_image).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(file_frame, text="Clear Lines", command=self.clear_lines).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(file_frame, text="Reset Zoom", command=self.reset_zoom).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Mode selection
        mode_frame = ttk.LabelFrame(control_frame, text="Mode")
        mode_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        self.mode_var = tk.StringVar(value="measure")
        ttk.Radiobutton(mode_frame, text="Measure", variable=self.mode_var, 
                       value="measure", command=self.change_mode).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Radiobutton(mode_frame, text="Calibrate", variable=self.mode_var, 
                       value="calibrate", command=self.change_mode).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Calibration frame
        cal_frame = ttk.LabelFrame(control_frame, text="Calibration")
        cal_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(cal_frame, text="Real distance (cm):").pack(side=tk.LEFT, padx=5, pady=5)
        self.cal_distance_var = tk.StringVar(value="1.0")
        cal_entry = ttk.Entry(cal_frame, textvariable=self.cal_distance_var, width=8)
        cal_entry.pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Button(cal_frame, text="Set Calibration", command=self.set_calibration).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Info frame
        info_frame = ttk.LabelFrame(control_frame, text="Information")
        info_frame.pack(side=tk.LEFT)
        
        self.info_text = tk.StringVar(value="Pixels/cm: 1.0")
        ttk.Label(info_frame, textvariable=self.info_text).pack(padx=5, pady=5)
        
        self.zoom_text = tk.StringVar(value="Zoom: 100%")
        ttk.Label(info_frame, textvariable=self.zoom_text).pack(padx=5, pady=5)
        
        # Canvas frame
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create canvas with scrollbars
        self.canvas = tk.Canvas(canvas_frame, bg="white")
        
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        
        self.canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind canvas events
        self.canvas.bind("<Button-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.draw_line)
        self.canvas.bind("<ButtonRelease-1>", self.end_draw)
        # Bind mouse wheel for zooming
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)  # Linux scroll up
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)  # Linux scroll down
        # Make canvas focusable for mouse wheel events
        self.canvas.focus_set()
        
        # Results frame
        results_frame = ttk.LabelFrame(main_frame, text="Measurements")
        results_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Create treeview for measurements
        columns = ("Line", "Pixels", "Real Distance (cm)")
        self.tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=6)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)
        
        tree_scroll = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
    def load_image(self):
        """Load an image file"""
        file_types = [
            ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff *.gif"),
            ("All files", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="Select Image",
            filetypes=file_types
        )
        
        if filename:
            try:
                # Load image with OpenCV
                self.image = cv2.imread(filename)
                if self.image is None:
                    raise ValueError("Could not load image")
                
                # Convert BGR to RGB
                self.image = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
                
                # Clear previous data
                self.lines = []
                self.clear_tree()
                
                # Reset zoom
                self.zoom_factor = 1.0
                
                # Display image
                self.display_image_on_canvas()
                self.update_zoom_display()
                
                messagebox.showinfo("Success", "Image loaded successfully!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Could not load image: {str(e)}")
    
    def display_image_on_canvas(self):
        """Display image on canvas with proper scaling"""
        if self.image is None:
            return
        
        # Get canvas size
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            # Canvas not ready, try again later
            self.root.after(100, self.display_image_on_canvas)
            return
        
        # Calculate base scale factor to fit image in canvas
        img_height, img_width = self.image.shape[:2]
        
        scale_x = (canvas_width - 20) / img_width
        scale_y = (canvas_height - 20) / img_height
        base_scale = min(scale_x, scale_y, 1.0)  # Don't upscale by default
        
        # Apply zoom factor
        self.scale_factor = base_scale * self.zoom_factor
        
        # Resize image
        new_width = int(img_width * self.scale_factor)
        new_height = int(img_height * self.scale_factor)
        
        display_img = cv2.resize(self.image, (new_width, new_height))
        
        # Convert to PIL and then to PhotoImage
        pil_image = Image.fromarray(display_img)
        self.photo = ImageTk.PhotoImage(pil_image)
        
        # Clear canvas and display image
        self.canvas.delete("all")
        self.canvas.create_image(10, 10, anchor=tk.NW, image=self.photo)
        
        # Update canvas scroll region
        self.canvas.configure(scrollregion=(0, 0, new_width + 20, new_height + 20))
        
        # Redraw existing lines
        self.redraw_lines()
    
    def on_mouse_wheel(self, event):
        """Handle mouse wheel for zooming"""
        if self.image is None:
            return
        
        # Determine zoom direction
        if event.delta > 0 or event.num == 4:  # Zoom in
            zoom_factor = 1.1
        else:  # Zoom out
            zoom_factor = 0.9
        
        # Calculate new zoom factor with limits
        new_zoom = self.zoom_factor * zoom_factor
        
        # Set zoom limits (0.1x to 10x)
        if 0.1 <= new_zoom <= 10.0:
            self.zoom_factor = new_zoom
            self.display_image_on_canvas()
            self.update_zoom_display()
    
    def start_draw(self, event):
        """Start drawing a line"""
        if self.image is None:
            return
        
        self.drawing = True
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        
        # Adjust for image position
        self.start_x -= 10
        self.start_y -= 10
    
    def draw_line(self, event):
        """Draw line while dragging"""
        if not self.drawing or self.image is None:
            return
        
        current_x = self.canvas.canvasx(event.x) - 10
        current_y = self.canvas.canvasy(event.y) - 10
        
        # Remove previous temporary line
        if self.current_line:
            self.canvas.delete(self.current_line)
        
        # Draw new temporary line
        color = "red" if self.mode == "calibrate" else "blue"
        self.current_line = self.canvas.create_line(
            self.start_x + 10, self.start_y + 10,
            current_x + 10, current_y + 10,
            fill=color, width=2
        )
    
    def end_draw(self, event):
        """End drawing and record the line"""
        if not self.drawing or self.image is None:
            return
        
        self.drawing = False
        end_x = self.canvas.canvasx(event.x) - 10
        end_y = self.canvas.canvasy(event.y) - 10
        
        # Calculate pixel distance (scaled back to original image)
        dx = (end_x - self.start_x) / self.scale_factor
        dy = (end_y - self.start_y) / self.scale_factor
        pixel_distance = math.sqrt(dx*dx + dy*dy)
        
        if pixel_distance < 5:  # Ignore very small lines
            if self.current_line:
                self.canvas.delete(self.current_line)
            self.current_line = None
            return
        
        # Store line data
        line_data = {
            'start': (self.start_x, self.start_y),
            'end': (end_x, end_y),
            'pixels': pixel_distance,
            'mode': self.mode
        }
        
        self.lines.append(line_data)
        self.current_line = None
        
        # Calculate real distance
        real_distance = pixel_distance / self.calibration_pixels_per_cm
        
        # Add to tree
        line_num = len(self.lines)
        mode_prefix = "CAL" if self.mode == "calibrate" else "MEA"
        self.tree.insert("", "end", values=(
            f"{mode_prefix}-{line_num}",
            f"{pixel_distance:.1f}",
            f"{real_distance:.2f}"
        ))
        
        # Auto-scroll to show new measurement
        children = self.tree.get_children()
        if children:
            self.tree.see(children[-1])
    
    def change_mode(self):
        """Change between measure and calibrate mode"""
        self.mode = self.mode_var.get()
    
    def set_calibration(self):
        """Set calibration based on last drawn line"""
        if not self.lines:
            messagebox.showwarning("Warning", "Please draw a calibration line first!")
            return
        
        try:
            real_distance = float(self.cal_distance_var.get())
            if real_distance <= 0:
                raise ValueError("Distance must be positive")
            
            # Use the last line for calibration
            last_line = self.lines[-1]
            pixel_distance = last_line['pixels']
            
            # Calculate pixels per cm
            self.calibration_pixels_per_cm = pixel_distance / real_distance
            
            # Update info
            self.info_text.set(f"Pixels/cm: {self.calibration_pixels_per_cm:.2f}")
            
            # Update all measurements in tree
            self.update_measurements()
            
            messagebox.showinfo("Success", 
                f"Calibration set!\n"
                f"Pixel distance: {pixel_distance:.1f}\n"
                f"Real distance: {real_distance} cm\n"
                f"Scale: {self.calibration_pixels_per_cm:.2f} pixels/cm")
            
        except ValueError as e:
            messagebox.showerror("Error", "Please enter a valid positive number for distance!")
    
    def update_measurements(self):
        """Update all measurements in the tree with new calibration"""
        # Clear and repopulate tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for i, line_data in enumerate(self.lines, 1):
            pixel_distance = line_data['pixels']
            real_distance = pixel_distance / self.calibration_pixels_per_cm
            mode_prefix = "CAL" if line_data['mode'] == "calibrate" else "MEA"
            
            self.tree.insert("", "end", values=(
                f"{mode_prefix}-{i}",
                f"{pixel_distance:.1f}",
                f"{real_distance:.2f}"
            ))
    
    def clear_lines(self):
        """Clear all drawn lines"""
        self.lines = []
        self.clear_tree()
        if self.image is not None:
            self.display_image_on_canvas()
    
    def clear_tree(self):
        """Clear the measurements tree"""
        for item in self.tree.get_children():
            self.tree.delete(item)
    
    def reset_zoom(self):
        """Reset zoom to 100%"""
        self.zoom_factor = 1.0
        if self.image is not None:
            self.display_image_on_canvas()
        self.update_zoom_display()
    
    def update_zoom_display(self):
        """Update the zoom percentage display"""
        zoom_percent = int(self.zoom_factor * 100)
        self.zoom_text.set(f"Zoom: {zoom_percent}%")
    
    def redraw_lines(self):
        """Redraw all stored lines on the canvas"""
        for line_data in self.lines:
            start_x, start_y = line_data['start']
            end_x, end_y = line_data['end']
            color = "red" if line_data['mode'] == "calibrate" else "blue"
            
            self.canvas.create_line(
                start_x + 10, start_y + 10,
                end_x + 10, end_y + 10,
                fill=color, width=2
            )

def main():
    """Main function"""
    root = tk.Tk()
    app = PixelMeasurementApp(root)
    
    # Handle window close
    def on_closing():
        root.quit()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()