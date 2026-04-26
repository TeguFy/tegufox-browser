import pytest

import tegufox_flow.steps.browser   # noqa
import tegufox_flow.steps.control   # noqa

from tegufox_gui.pages.flow_editor_page import FlowEditorPage


def test_editor_constructs_empty(qapp, tmp_path):
    p = FlowEditorPage(db_path=str(tmp_path / "t.db"))
    assert p.list_widget.steps() == []
    assert p.palette is not None
    assert p.form_panel is not None


def test_palette_choice_appends_step(qapp, tmp_path):
    p = FlowEditorPage(db_path=str(tmp_path / "t.db"))
    p.palette._emit_choice("browser.goto")
    assert len(p.list_widget.steps()) == 1
    assert p.list_widget.steps()[0].type == "browser.goto"


def test_load_existing_flow(qapp, tmp_path):
    from datetime import datetime
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from tegufox_core.database import Base, FlowRecord

    db = tmp_path / "x.db"
    eng = create_engine(f"sqlite:///{db}")
    Base.metadata.create_all(eng)
    s = sessionmaker(bind=eng)()
    yaml = ("schema_version: 1\nname: f\nsteps:\n  - id: a\n    type: control.sleep\n    ms: 1\n")
    s.add(FlowRecord(name="f", yaml_text=yaml, schema_version=1,
                     created_at=datetime.utcnow(), updated_at=datetime.utcnow()))
    s.commit(); s.close()

    p = FlowEditorPage(db_path=str(db))
    p.load_flow_by_name("f")
    assert p.name_edit.text() == "f"
    assert len(p.list_widget.steps()) == 1
    assert p.list_widget.steps()[0].id == "a"


def test_validate_button_reports_ok(qapp, tmp_path):
    p = FlowEditorPage(db_path=str(tmp_path / "t.db"))
    p.name_edit.setText("ok")
    p.palette._emit_choice("control.sleep")
    msg, ok = p._validate_now()
    assert ok, msg


def test_validate_button_reports_error(qapp, tmp_path):
    p = FlowEditorPage(db_path=str(tmp_path / "t.db"))
    p.name_edit.setText("")
    msg, ok = p._validate_now()
    assert not ok
