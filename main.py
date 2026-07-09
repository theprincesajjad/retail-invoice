import customtkinter as ctk
from database import init_db
from ui import App

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


def main():
    init_db()
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
