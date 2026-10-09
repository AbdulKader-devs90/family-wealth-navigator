"""Create and download an encrypted guide for the family."""

from datetime import date, timedelta
import smtplib

import streamlit as st

from checkin import (
    decide, deliver_email, load_state, make_email, next_stage,
    public_demo_enabled, save_state, smtp_configured,
)
from readiness import check_readiness, readiness_label
from wealth_map import build_wealth_map

st.title("Family Wealth Map")
st.write("A private guide that helps your family find everything if you're ever unreachable.")
st.html("""
<style>
.st-key-checkin_ok button {
    background-color: #15803d;
    border-color: #15803d;
    color: #ffffff;
}
.st-key-checkin_ok button:hover,
.st-key-checkin_ok button:active {
    background-color: #166534;
    border-color: #166534;
    color: #ffffff;
}
.st-key-checkin_ok button:focus-visible {
    outline: 3px solid #86efac;
    outline-offset: 2px;
}
</style>
""")
if st.session_state.get("data_error"):
    st.error(st.session_state["data_error"])
    st.stop()

holdings = st.session_state["holdings"]
currency = st.session_state["base_currency"]
items, issues = check_readiness(holdings)
score = float(items["score"].mean())
today = date.today()
try:
    state = load_state(today, session_state=st.session_state)
    last_check_in = date.fromisoformat(state["last_check_in"])
    paused_until = date.fromisoformat(state["paused_until"]) if state["paused_until"] else None
except (OSError, ValueError, TypeError, KeyError):
    st.error("We couldn't open your saved check-in settings. Please try again.")
    st.stop()
log = st.session_state.setdefault("checkin_log", [])
if "checkin_pause_date" not in st.session_state:
    st.session_state["checkin_pause_date"] = paused_until
if "checkin_automatic_enabled" not in st.session_state:
    st.session_state["checkin_automatic_enabled"] = state["automatic_enabled"]


def friendly_date(value):
    value = date.fromisoformat(value) if isinstance(value, str) else value
    return f"{value.day} {value:%b %Y}"


def friendly_months(value):
    whole = int(value)
    number = f"{whole}½" if value != whole else str(whole)
    if number == "0½":
        number = "½"
    return f"{number} month" if value == 1 else f"{number} months"


def email_text(action):
    owner = owner_name.strip()
    family = family_member_name.strip()
    if action == "reminder_1":
        return (
            f"Hi {owner or 'there'}, we haven't heard from you in a while. "
            "Please open Family Wealth Navigator and tap 'I'm OK'. It takes 5 seconds."
        )
    if action == "reminder_2":
        return (
            f"Hi {owner or 'there'}, this is a final reminder. If we don't hear "
            f"from you within 2 weeks, your Family Wealth Map will be sent to {family or 'your family member'}."
        )
    return (
        f"Hi {family or 'there'}, {owner or 'the owner'} asked us to send you this "
        "if we couldn't reach them for 6 months. It's a guide to where everything "
        f"is and who to contact. The password is the one {owner or 'the owner'} shared "
        "with you in person – it is never sent by email."
    )


def persist_settings():
    try:
        save_state(state, session_state=st.session_state)
        return True
    except OSError:
        st.error("We couldn't save your settings. Please try again.")
        return False


def update_safety_settings():
    updated = load_state(today, session_state=st.session_state)
    pause = st.session_state["checkin_pause_date"]
    updated["paused_until"] = pause.isoformat() if pause else None
    updated["automatic_enabled"] = st.session_state["checkin_automatic_enabled"]
    try:
        save_state(updated, session_state=st.session_state)
    except OSError:
        st.session_state["checkin_save_error"] = True


ACTION_NAMES = {
    "none": "No email needed", "paused": "Paused",
    "reminder_1": "First reminder", "reminder_2": "Final reminder",
    "send_map": "Share map", "check_in": "Checked in",
    "reset_simulation": "Started demo over",
}


def run_action(action, check_date, *, simulation, manual=False):
    entry = {
        "Date": friendly_date(check_date), "Action": ACTION_NAMES[action],
        "Mode": "Demo" if simulation else "Real",
    }
    if action in ("none", "paused"):
        entry["Result"] = "No email needed yet." if action == "none" else "Paused — no email sent."
        log.append(entry)
        return entry
    try:
        message = make_email(
            action, state, st.session_state.get("wealth_map_pdf"), manual=manual,
        )
        message.get_body(preferencelist=("plain",)).set_content(email_text(action))
        with st.spinner("Preparing email…" if simulation else "Sending email…"):
            result = deliver_email(message, simulate=simulation)
    except ValueError as error:
        entry["Result"] = f"Not completed: {error}"
        log.append(entry)
        return entry
    except (OSError, smtplib.SMTPException):
        entry["Result"] = "Not completed: we couldn't send the email; please check the email setup and try again."
        log.append(entry)
        return entry
    # Only SMTP success on a real date advances real stages. Dry-run results and
    # simulated dates always have their own independent no-repeat history.
    is_simulation = simulation or result["mode"] == "dry-run"
    target = state["simulation"] if is_simulation else state
    stages = target["stages_sent"]
    if action not in stages:
        stages.append(action)
        target.setdefault("sent_on", {})[action] = check_date.isoformat()
    saved = persist_settings()
    entry.update({
        "Mode": "Demo" if is_simulation else "Real",
        "Result": (
            "Email preview ready; nothing was sent." if is_simulation else "Email sent."
        ) if saved else (
            "Email preview ready, but we couldn't save your progress."
            if is_simulation else "Email sent, but we couldn't save your progress."
        ),
        "To": result["to"], "Subject": result["subject"],
    })
    if result["mode"] == "dry-run":
        entry["Preview"] = result
    log.append(entry)
    return entry


def show_preview(entry):
    if "Preview" in entry:
        preview = entry["Preview"]
        with st.expander("Email preview", expanded=False):
            st.write("To:", preview["to"])
            st.write("Subject:", preview["subject"])
            st.text(preview["body"])
            if preview["attachment_name"]:
                st.write("Attachment:", preview["attachment_name"])


with st.container(border=True):
    st.subheader("Your safety net")
    status = st.empty()
    if st.button("I'm OK – check in", key="checkin_ok", type="primary", width="stretch"):
        state["last_check_in"] = today.isoformat()
        state["stages_sent"] = []
        state["sent_on"] = {}
        state["simulation"] = {"stages_sent": [], "sent_on": {}}
        if persist_settings():
            st.session_state["checkin_demo_months"] = 0.0
            st.session_state.pop("checkin_demo_result", None)
            log.append({
                "Date": friendly_date(today), "Action": "Checked in",
                "Result": "You're checked in. Your safety net and demo have started fresh.",
            })

configured = smtp_configured()
if not configured:
    st.info("Practice mode – emails are shown here, not sent")
if st.session_state.pop("checkin_save_error", False):
    st.error("We couldn't save your safety net settings. Please try again.")

create_tab, share_tab, safety_tab, demo_tab = st.tabs([
    "1 · Create your map", "2 · Share with family", "3 · Safety net", "Try it out (demo)",
])

with create_tab:
    st.caption("The PDF uses all loaded holdings, not the sidebar-filtered subset.")
    with st.form("family_wealth_map"):
        owner_name = st.text_input("Owner name", value="Arjun" if public_demo_enabled() else "")
        family_member_name = st.text_input(
            "Family member name", value="Meera" if public_demo_enabled() else "",
            key="map_family_member_name",
        )
        country_options = sorted(
            {"UAE", "India"} | set(holdings["country"].dropna().loc[lambda values: values.ne("")])
        )
        home_countries = st.multiselect("Home countries", country_options, default=["UAE", "India"])
        personal_message = st.text_area("A personal message", height=120)
        password = st.text_input("PDF password", type="password")
        password_confirm = st.text_input("Confirm PDF password", type="password")
        create = st.form_submit_button("Create encrypted Family Wealth Map")
    if create:
        st.session_state.pop("wealth_map_pdf", None)
        if len(password) < 8:
            st.error("The PDF password must be at least 8 characters.")
        elif password != password_confirm:
            st.error("The two PDF passwords must match.")
        else:
            with st.spinner("Creating the encrypted PDF…"):
                st.session_state["wealth_map_pdf"] = build_wealth_map(
                    holdings, currency, owner_name, family_member_name,
                    home_countries, personal_message, password,
                    benchmark=st.session_state["benchmark_return_pct"],
                )
    if st.session_state.get("wealth_map_pdf"):
        st.download_button(
            "Download your encrypted map", data=st.session_state["wealth_map_pdf"],
            file_name="Family_Wealth_Map.pdf", mime="application/pdf", on_click="ignore",
        )

family_name = family_member_name.strip() or "your family member"
with share_tab:
    with st.form("checkin_settings"):
        family_email = st.text_input("Family member email", value=state["family_member_email"])
        owner_email = st.text_input("Owner email", value=state["owner_email"])
        save_emails = st.form_submit_button("Save email addresses")
        manual_paused = decide(state, today) == "paused"
        send_now = st.form_submit_button("Send map now", disabled=manual_paused)
    if save_emails or send_now:
        state.update({
            "family_member_email": family_email.strip(), "owner_email": owner_email.strip(),
        })
        if persist_settings():
            if send_now and not manual_paused:
                entry = run_action("send_map", today, simulation=not configured, manual=True)
                st.session_state["checkin_share_result"] = entry
            else:
                st.success("Email addresses saved.")
    st.caption(f"We never email the password. Tell {family_name} the password in person.")
    if manual_paused:
        st.caption(f"Sending is paused until {friendly_date(state['paused_until'])}.")
    if "checkin_share_result" in st.session_state:
        entry = st.session_state["checkin_share_result"]
        if entry["Result"].startswith("Not completed"):
            st.error(entry["Result"])
        else:
            st.info(entry["Result"])
        show_preview(entry)

with safety_tab:
    st.toggle(
        "Send my map automatically if I go quiet", key="checkin_automatic_enabled",
        on_change=update_safety_settings,
    )
    for column, text in zip(st.columns(3), (
        "5 months without a check-in → we email you a reminder",
        "5½ months → we email you a final reminder",
        f"6 months → we email your map to {family_name}",
    )):
        with column:
            st.container(border=True).write(text)
    st.caption("We never skip reminders. Your map waits at least 7 days after the final reminder.")
    pause_date = st.date_input(
        "Pause while travelling", value=None, key="checkin_pause_date",
        on_change=update_safety_settings,
    )
    st.caption(
        f"No reminders until {friendly_date(pause_date)}" if pause_date else "No travel pause is set."
    )
    with st.expander("Last check-in date"):
        check_date = st.date_input("Last check-in", value=date.fromisoformat(state["last_check_in"]))
        st.caption(f"Your last check-in was {(today - date.fromisoformat(state['last_check_in'])).days} days ago.")
        if st.button("Save check-in date"):
            state["last_check_in"] = check_date.isoformat()
            if persist_settings():
                st.success("Last check-in date saved.")
    stage, due = next_stage(state, today)
    if stage:
        if due:
            st.caption(f"Next: {ACTION_NAMES[stage].lower()} on {friendly_date(due)}.")
        else:
            st.caption("Please check in to start fresh: the earlier final reminder has no recorded date.")
    st.caption("In production, a daily scheduled job would run these checks automatically.")
    if st.button("Check now", help="Check whether a reminder or map is due today."):
        if configured:
            entry = run_action(decide(state, today), today, simulation=False)
        else:
            practice_state = dict(
                state, stages_sent=state["simulation"]["stages_sent"],
                sent_on=state["simulation"]["sent_on"],
            )
            entry = run_action(decide(practice_state, today), today, simulation=True)
        st.info(entry["Result"])
        show_preview(entry)

with demo_tab:
    st.info("Nothing here affects your real safety net.")
    if st.button("Start demo over", type="tertiary"):
        state["simulation"] = {"stages_sent": [], "sent_on": {}}
        if persist_settings():
            st.session_state["checkin_demo_months"] = 0.0
            st.session_state.pop("checkin_demo_result", None)
            log.append({
                "Date": friendly_date(today), "Action": "Started demo over",
                "Result": "Demo cleared. Your real safety net is unchanged.",
            })
    months = st.select_slider(
        "Pretend this much time has passed", options=[half / 2 for half in range(15)],
        format_func=friendly_months, key="checkin_demo_months",
    )
    st.caption("For this demo, 1 month means 30 days.")
    effective_today = today + timedelta(days=int(months * 30))
    if st.button("See what would happen"):
        practice_state = dict(
            state, stages_sent=state["simulation"]["stages_sent"],
            sent_on=state["simulation"]["sent_on"], automatic_enabled=True,
        )
        action = decide(practice_state, effective_today)
        entry = run_action(action, effective_today, simulation=True)
        outcomes = {
            "reminder_1": "we'd email you a reminder.",
            "reminder_2": "we'd email you a final reminder.",
            "send_map": f"we'd email your map to {family_name}.",
            "paused": f"we'd wait until {friendly_date(state['paused_until'])} before emailing."
            if state["paused_until"] else "we'd wait before emailing.",
            "none": "no email would be needed yet.",
        }
        if action == "none" and "send_map" in practice_state["stages_sent"]:
            outcomes["none"] = "the demo map has already been shown; we wouldn't send it again."
        elif action == "none" and "reminder_2" in practice_state["stages_sent"]:
            _, map_due = next_stage(practice_state, effective_today)
            outcomes["none"] = (
                f"we'd wait until {friendly_date(map_due)} to share the map."
                if map_due else "we'd need a new check-in because the final reminder has no recorded date."
            )
        sentence = (
            entry["Result"] if entry["Result"].startswith("Not completed")
            else f"After {friendly_months(months)}: {outcomes[action]}"
        )
        st.session_state["checkin_demo_result"] = (sentence, entry)
    if "checkin_demo_result" in st.session_state:
        sentence, entry = st.session_state["checkin_demo_result"]
        st.write(sentence)
        show_preview(entry)

with status.container():
    sent = state["stages_sent"]
    pause = state["paused_until"]
    if pause and today < date.fromisoformat(pause):
        st.caption(f"Paused until {friendly_date(pause)} – no reminders or sending.")
    elif "send_map" in sent:
        sent_date = state["sent_on"].get("send_map")
        st.error(
            f"Your family has been sent the map on {friendly_date(sent_date)}."
            if sent_date else "Your family has been sent the map. The send date wasn't recorded."
        )
    elif any(reminder in sent for reminder in ("reminder_1", "reminder_2")):
        st.warning("We sent you a reminder. Please check in.")
    elif not st.session_state.get("wealth_map_pdf"):
        st.info("Start by creating your map in step 1.")
    else:
        last = date.fromisoformat(state["last_check_in"])
        reminder_due = last + timedelta(days=150)
        message = f"You're all set. Last check-in: {friendly_date(last)}."
        message += (
            f" We'll only remind you if we don't hear from you by {friendly_date(reminder_due)}."
            if state["automatic_enabled"] else " Automatic sending is off."
        )
        st.success(message)
    if not st.session_state.get("wealth_map_pdf") and (sent or pause):
        st.caption("Start by creating your map in step 1.")
    st.caption(
        f"Readiness Score: {score:.1f} / 100 ({readiness_label(score)}) · Open issues: {len(issues)}"
    )

with st.expander("History", expanded=False):
    if log:
        rows = []
        for entry in log:
            day = entry["Date"]
            if len(day) == 10 and day[4] == "-":
                day = friendly_date(day)
            result = entry["Result"]
            legacy_results = {
                "dry-run": "Email preview ready; nothing was sent.",
                "SMTP": "Email sent.", "Not completed": "Not completed: check the required details and try again.",
                "SMTP failed — stage not recorded": "Not completed: email couldn't be sent.",
                "Real and simulation stages reset": "Checked in; safety net and demo started fresh.",
                "Simulation reset; real stages unchanged": "Demo cleared; real safety net unchanged.",
            }
            rows.append({
                "Date": day, "Action": ACTION_NAMES.get(entry["Action"], entry["Action"]),
                "Mode": "Demo" if (
                    entry.get("Mode") == "Demo" or entry.get("Scope") == "Simulation"
                    or entry["Action"] in ("reset_simulation", "Started demo over")
                ) else "Real",
                "Result": legacy_results.get(result, result),
                "To": entry.get("To", ""), "Subject": entry.get("Subject", ""),
            })
        st.dataframe(rows, hide_index=True, width="stretch")
    else:
        st.caption("Nothing has happened in this visit yet.")
