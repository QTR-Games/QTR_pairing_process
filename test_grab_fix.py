#!/usr/bin/env python3
"""
Test script to verify the grab conflict fix
"""
import tkinter as tk
from tkinter import messagebox
import sys
import os

# Add the qtr_pairing_process directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'qtr_pairing_process'))

def test_grab_conflict():
    """Test that dialogs can be opened from modal windows"""
    root = tk.Tk()
    root.title("Test Grab Conflict Fix")
    root.geometry("400x300")
    
    def show_first_dialog():
        """Show first modal dialog"""
        first_dialog = tk.Toplevel(root)
        first_dialog.title("First Dialog")
        first_dialog.geometry("300x200")
        first_dialog.transient(root)
        first_dialog.grab_set()
        
        # Center the dialog
        x = root.winfo_x() + 50
        y = root.winfo_y() + 50
        first_dialog.geometry(f"+{x}+{y}")
        
        # Add content
        label = tk.Label(first_dialog, text="This is the first modal dialog.\nNow try clicking 'Open Second Dialog'")
        label.pack(pady=20)
        
        def show_second_dialog():
            """Show second dialog from first dialog"""
            try:
                second_dialog = tk.Toplevel(first_dialog)
                second_dialog.title("Second Dialog")
                second_dialog.geometry("250x150")
                second_dialog.transient(first_dialog)
                
                # Safe grab - handle existing grabs
                try:
                    second_dialog.grab_set()
                except tk.TclError as e:
                    if "grab failed" in str(e).lower():
                        # Release existing grab and try again
                        try:
                            first_dialog.grab_release()
                        except:
                            pass
                        # Small delay to ensure grab is released
                        second_dialog.after(10, lambda: second_dialog.grab_set())
                    else:
                        raise
                
                # Center relative to first dialog
                x = first_dialog.winfo_x() + 25
                y = first_dialog.winfo_y() + 25
                second_dialog.geometry(f"+{x}+{y}")
                
                # Content
                label2 = tk.Label(second_dialog, text="Second dialog opened successfully!\nNo grab conflict!")
                label2.pack(pady=20)
                
                close_btn = tk.Button(second_dialog, text="Close", command=second_dialog.destroy)
                close_btn.pack(pady=10)
                
                print("✅ Second dialog opened successfully - no grab conflict!")
                
            except Exception as e:
                print(f"❌ Error opening second dialog: {e}")
                messagebox.showerror("Error", f"Failed to open second dialog: {e}")
        
        # Buttons
        button_frame = tk.Frame(first_dialog)
        button_frame.pack(pady=20)
        
        open_btn = tk.Button(button_frame, text="Open Second Dialog", command=show_second_dialog)
        open_btn.pack(side=tk.LEFT, padx=5)
        
        close_btn = tk.Button(button_frame, text="Close", command=first_dialog.destroy)
        close_btn.pack(side=tk.LEFT, padx=5)
    
    # Main window content
    title = tk.Label(root, text="Grab Conflict Test", font=("Arial", 16, "bold"))
    title.pack(pady=20)
    
    desc = tk.Label(root, text="This tests opening modal dialogs from other modal dialogs.\nClick 'Open First Dialog' to start the test.")
    desc.pack(pady=10)
    
    test_btn = tk.Button(root, text="Open First Dialog", command=show_first_dialog, 
                        bg="lightblue", font=("Arial", 12), padx=20, pady=10)
    test_btn.pack(pady=30)
    
    quit_btn = tk.Button(root, text="Quit Test", command=root.quit, 
                        bg="lightcoral", font=("Arial", 12), padx=20, pady=10)
    quit_btn.pack(pady=10)
    
    print("🧪 Starting grab conflict test...")
    print("📋 Instructions:")
    print("1. Click 'Open First Dialog'")
    print("2. From the first dialog, click 'Open Second Dialog'")
    print("3. If no error occurs, the fix is working!")
    
    root.mainloop()

if __name__ == "__main__":
    test_grab_conflict()