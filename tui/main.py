from ulid import ULID
from textual.app import App, ComposeResult
from textual import work
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Input, Label, Select, Static, TextArea, Button, ListView, ListItem

from db import init_db, get_all_agents, insert_agent, update_agent, delete_agent
from messaging import publish_agents


LLM_MODELS = [
    ("DeepSeek Chat", "deepseek-chat"),
]


class InsightsApp(App):
    CSS_PATH = "app.tcss"

    BINDINGS = [("q", "quit", "Quit")]

    editing_id: str | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="layout"):
            with Vertical(id="sidebar"):
                with Vertical(id="form-box") as form_box:
                    form_box.border_title = "New Agent"
                    with Vertical(classes="field"):
                        yield Label("ID")
                        yield Input(placeholder="Auto-generated", id="agent-id", disabled=True)
                    with Vertical(classes="field"):
                        yield Label("Name")
                        yield Input(placeholder="Agent name", id="name")
                    with Vertical(classes="field"):
                        yield Label("LLM Model")
                        yield Select(LLM_MODELS, prompt="Select a model", id="llm-model")
                    with Vertical(classes="field"):
                        yield Label("Instructions")
                        yield TextArea(id="instructions")
                    yield Button("Submit", id="btn-submit", variant="primary")
                    yield Button("Delete", id="btn-delete", variant="error", disabled=True)
                    yield Button("Clear", id="btn-clear", variant="default", disabled=True)
                with Vertical(id="dispatch-box") as dispatch_box:
                    dispatch_box.border_title = "Dispatch"
                    yield Button("Dispatch Agents", id="btn-dispatch", variant="success")
            with Vertical(id="agents-panel"):
                with Vertical(id="agents-section") as agents_sec:
                    agents_sec.border_title = "Agents"
                    yield ListView(id="agents-list")
            with Vertical(id="main-panel"):
                with Vertical(id="output-section") as output:
                    output.border_title = "Output"
                    yield Static(id="output-content")
        yield Footer()

    def on_mount(self) -> None:
        init_db()
        self._refresh_list()

    def _clear_form(self) -> None:
        self.query_one("#agent-id", Input).value = ""
        self.query_one("#name", Input).value = ""
        self.query_one("#llm-model", Select).clear()
        self.query_one("#instructions", TextArea).clear()
        self.editing_id = None
        self.query_one("#form-box", Vertical).border_title = "New Agent"
        self.query_one("#btn-submit", Button).label = "Submit"
        self.query_one("#btn-delete", Button).disabled = True
        self.query_one("#btn-clear", Button).disabled = False

    def _refresh_list(self) -> None:
        agents_list = self.query_one("#agents-list", ListView)
        agents_list.clear()
        for agent in get_all_agents():
            agents_list.append(ListItem(Label(f"{agent['name']} ({agent['model']})")))

    @work(thread=True)
    def _handle_dispatch(self) -> None:
        agents = get_all_agents()
        if not agents:
            self.app.call_from_thread(self.notify, "No agents to dispatch", severity="warning")
            return

        output = self.query_one("#output-content", Static)
        self.app.call_from_thread(output.update, "[bold]Dispatching agents...[/bold]")

        try:
            publish_agents(agents)
            names = ", ".join(a["name"] for a in agents)
            msg = f"Dispatched {len(agents)} agent(s): {names}"
            self.app.call_from_thread(output.update, f"[bold green]{msg}[/bold green]")
            self.app.call_from_thread(self.notify, "Agents dispatched successfully")
        except Exception as e:
            self.app.call_from_thread(output.update, f"[bold red]Error: {e}[/bold red]")
            self.app.call_from_thread(self.notify, f"Dispatch failed: {e}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-dispatch":
            self._handle_dispatch()
            return

        if event.button.id == "btn-clear":
            self._clear_form()
            return

        if event.button.id == "btn-delete":
            if self.editing_id is not None:
                agents = get_all_agents()
                agent = next((a for a in agents if a["id"] == self.editing_id), None)
                if agent:
                    delete_agent(self.editing_id)
                    self._refresh_list()
                    self._clear_form()
                    self.notify(f"Agent '{agent['name']}' deleted")
            return

        if event.button.id != "btn-submit":
            return

        name = self.query_one("#name", Input).value
        model = self.query_one("#llm-model", Select).value
        instructions = self.query_one("#instructions", TextArea).text

        if not name:
            self.notify("Name is required", severity="error")
            return

        if self.editing_id is not None:
            update_agent(self.editing_id, name, model, instructions)
            self._refresh_list()
            self.notify(f"Agent '{name}' updated")
        else:
            agent_id = str(ULID())
            insert_agent(agent_id, name, model, instructions)
            self._refresh_list()
            self.notify(f"Agent '{name}' added")

        self._clear_form()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        index = event.list_view.index
        agents = get_all_agents()
        if index is not None and index < len(agents):
            agent = agents[index]
            self.editing_id = agent["id"]
            self.query_one("#agent-id", Input).value = agent["id"]
            self.query_one("#name", Input).value = agent["name"]
            self.query_one("#llm-model", Select).value = agent["model"]
            self.query_one("#instructions", TextArea).text = agent["instructions"]
            self.query_one("#form-box", Vertical).border_title = f"Edit Agent: {agent['name']}"
            self.query_one("#btn-submit", Button).label = "Update"
            self.query_one("#btn-delete", Button).disabled = False
            self.query_one("#btn-clear", Button).disabled = False


if __name__ == "__main__":
    InsightsApp().run()
