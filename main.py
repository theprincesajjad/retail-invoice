import os
import sys
import customtkinter as ctk
from database import init_db
from ui import App

# Set appearance mode for DOS-style green-on-black theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

def main():
    # Initialize database
    init_db()
    
    # Run application
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
