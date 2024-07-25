from shiny import render, ui
from shiny.express import input
from sys import argv

ui.panel_title("Hello Shiny!")
ui.input_slider("n", "N", 0, 100, 20)
ui.input_text("txtBox", "Text")

if "--test" in argv:
    print("Running in test mode")

@render.text
def txt():
    # return f"n*2 is {input.n() * 2}"
    return f"{input.txtBox()}"
