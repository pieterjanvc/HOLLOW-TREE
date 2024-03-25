from shiny import reactive
from shiny.express import input, render, ui
from htmltools import HTML, div

log = reactive.value(f"<b>BOT:</b><br>Welcome to the app!")

@reactive.effect
@reactive.event(input.send)
def _():
    log.set(log.get() + f"<br><b>YOU:</b><br>{input.newChat()}")
    ui.update_text("newChat", value = "")

@render.ui
def chatLog():
    return HTML(log.get())

ui.input_text("newChat", "", value="")
ui.input_action_button("send", "Send")
