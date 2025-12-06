#!/usr/bin/env python3
"""
Simple test for the dynamic UI manager classes
"""
import tkinter as tk

def test_dynamic_ui():
    """Test the basic dynamic UI sizing"""
    root = tk.Tk()
    
    # Test a simple dynamic dialog
    dialog = tk.Toplevel(root)
    dialog.title("Dynamic Sizing Test")
    dialog.transient(root)
    dialog.grab_set()
    
    # Create some content
    frame = tk.Frame(dialog, padx=20, pady=20)
    frame.pack(fill=tk.BOTH, expand=True)
    
    title = tk.Label(frame, text="Dynamic Sizing Test", font=("Arial", 16, "bold"))
    title.pack(pady=(0, 10))
    
    text = tk.Label(frame, text="This dialog should automatically size itself based on content. "
                                "The window should be just big enough to display all content clearly "
                                "without any overflow or excessive whitespace.", 
                    wraplength=400, justify=tk.LEFT)
    text.pack(pady=(0, 20))
    
    button = tk.Button(frame, text="Close", command=dialog.destroy)
    button.pack()
    
    # Update the dialog to calculate its required size
    dialog.update_idletasks()
    
    # Get the required size
    width_needed = frame.winfo_reqwidth() + 40  # padding
    height_needed = frame.winfo_reqheight() + 40  # padding
    
    # Set the minimum size
    dialog.minsize(width_needed, height_needed)
    
    # Center the dialog
    dialog.geometry(f"{width_needed}x{height_needed}")
    
    # Position in center of parent
    x = root.winfo_x() + (root.winfo_width() // 2) - (width_needed // 2)
    y = root.winfo_y() + (root.winfo_height() // 2) - (height_needed // 2)
    dialog.geometry(f"{width_needed}x{height_needed}+{x}+{y}")
    
    root.withdraw()  # Hide main window
    dialog.wait_window()
    root.destroy()

if __name__ == "__main__":
    print("Testing dynamic UI sizing...")
    test_dynamic_ui()
    print("Test completed!")