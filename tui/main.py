import threading
from ulid import ULID
from rich.markup import escape
from textual.app import App, ComposeResult
from textual import work
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Header,
    Footer,
    Input,
    Label,
    Select,
    Static,
    TextArea,
    Button,
    ListView,
    ListItem,
    RichLog,
)

from db import init_db, get_all_agents, insert_agent, update_agent, delete_agent
from messaging import publish_agents, run_tui_stream_loop


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
                    output.border_title = "Live run log"
                    yield RichLog(
                        id="stream-log",
                        wrap=True,
                        highlight=True,
                        markup=True,
                        max_lines=8000,
                    )
        yield Footer()

    def on_mount(self) -> None:
        init_db()
        self._refresh_list()
        self.query_one("#stream-log", RichLog).clear()

        self._stream_stop = threading.Event()
        self._stream_thread = threading.Thread(
            target=run_tui_stream_loop,
            args=(self, self._stream_stop),
            daemon=True,
            name="tui-stream",
        )
        self._stream_thread.start()

    def on_unmount(self) -> None:
        if hasattr(self, "_stream_stop"):
            self._stream_stop.set()

    def _on_stream_event(self, payload: dict) -> None:
        log = self.query_one("#stream-log", RichLog)
        kind = payload.get("kind", "")
        agent = escape(str(payload.get("agent", "?")))
        text = escape(str(payload.get("text", "")))
        if kind == "run_start":
            log.write(f"[bold magenta]── {agent} ──[/]")
        elif kind == "assistant":
            log.write(f"[cyan]{agent}[/]\n{text}")
        elif kind == "tool_start":
            log.write(f"[yellow]{agent}[/] ▶ [dim]{text}[/]")
        elif kind == "tool_done":
            log.write(f"[green]{agent}[/] ◀ {text}")
        elif kind == "error":
            log.write(f"[bold red]{agent}[/] {text}")
        elif kind == "done":
            log.write(f"[dim]{agent} — run finished[/]")

    def _clear_stream_log(self, banner: str) -> None:
        log = self.query_one("#stream-log", RichLog)
        log.clear()
        log.write(banner)

    def _append_stream_line(self, line: str) -> None:
        self.query_one("#stream-log", RichLog).write(line)

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
            self.call_from_thread(self.notify, "No agents to dispatch", severity="warning")
            return

        self.call_from_thread(self._clear_stream_log, "[bold]Dispatching agents…[/]")

        try:
            publish_agents(agents)
            names = ", ".join(a["name"] for a in agents)
            msg = f"Queued {len(agents)} agent(s): {names}. Streaming below when workers run."
            self.call_from_thread(self._append_stream_line, f"[bold green]{escape(msg)}[/]")
            self.call_from_thread(self.notify, "Agents dispatched successfully")
        except Exception as e:
            self.call_from_thread(
                self._append_stream_line,
                f"[bold red]Dispatch error: {escape(str(e))}[/]",
            )
            self.call_from_thread(self.notify, f"Dispatch failed: {e}", severity="error")

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
