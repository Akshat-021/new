"""
tool_demo.py — Streamlit UI for the PromptForge Tool-Calling Demo.

Run with:
    streamlit run tool_demo.py
"""

from __future__ import annotations

import json
import time

import streamlit as st

from tool_agent import run_tool_agent, DEFAULT_MODEL
from tools import ALL_TOOLS, TOOL_REGISTRY

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PromptForge — Self Improving AI Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Dark gradient background */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0d0d1a 0%, #111827 40%, #0d1117 100%);
    min-height: 100vh;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] {
    background: rgba(17, 24, 39, 0.95);
    border-right: 1px solid rgba(99, 102, 241, 0.2);
}

/* Hero header */
.hero-title {
    font-size: 2.6rem;
    font-weight: 800;
    background: linear-gradient(90deg, #818cf8, #c084fc, #f472b6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 4px;
    line-height: 1.2;
}
.hero-sub {
    font-size: 1rem;
    color: rgba(148, 163, 184, 0.9);
    margin-bottom: 0;
}

/* Tool cards */
.tool-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(99, 102, 241, 0.25);
    border-radius: 14px;
    padding: 16px 18px;
    margin-bottom: 10px;
    transition: border-color 0.2s, background 0.2s;
    cursor: default;
}
.tool-card:hover {
    border-color: rgba(129, 140, 248, 0.55);
    background: rgba(255,255,255,0.07);
}
.tool-name {
    font-size: 0.95rem;
    font-weight: 600;
    color: #a5b4fc;
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 4px;
}
.tool-desc {
    font-size: 0.8rem;
    color: rgba(148, 163, 184, 0.85);
    line-height: 1.5;
}

/* Turn timeline */
.turn-assistant {
    background: rgba(99, 102, 241, 0.1);
    border-left: 3px solid #818cf8;
    border-radius: 0 10px 10px 0;
    padding: 12px 16px;
    margin-bottom: 10px;
}
.turn-tool {
    background: rgba(16, 185, 129, 0.08);
    border-left: 3px solid #34d399;
    border-radius: 0 10px 10px 0;
    padding: 12px 16px;
    margin-bottom: 10px;
}
.turn-label {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.turn-label.assistant { color: #818cf8; }
.turn-label.tool { color: #34d399; }

/* Answer box */
.answer-box {
    background: linear-gradient(135deg, rgba(99,102,241,0.12), rgba(192,132,252,0.08));
    border: 1px solid rgba(129, 140, 248, 0.4);
    border-radius: 16px;
    padding: 20px 24px;
    margin-top: 4px;
}
.answer-text {
    font-size: 1.05rem;
    color: #e2e8f0;
    line-height: 1.75;
    white-space: pre-wrap;
}

/* Pill badge */
.pill {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    margin-right: 5px;
    margin-bottom: 4px;
    font-family: 'JetBrains Mono', monospace;
}
.pill-purple { background: rgba(99,102,241,0.2); color: #a5b4fc; border: 1px solid rgba(99,102,241,0.35); }
.pill-green  { background: rgba(16,185,129,0.15); color: #6ee7b7; border: 1px solid rgba(16,185,129,0.3); }
.pill-pink   { background: rgba(244,114,182,0.15); color: #f9a8d4; border: 1px solid rgba(244,114,182,0.3); }

/* Metrics */
.metric-row { display: flex; gap: 12px; margin-bottom: 18px; flex-wrap: wrap; }
.metric-card {
    flex: 1; min-width: 110px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 14px 16px;
    text-align: center;
}
.metric-num { font-size: 1.8rem; font-weight: 800; color: #a5b4fc; line-height: 1; }
.metric-lbl { font-size: 0.72rem; color: rgba(148,163,184,0.7); margin-top: 4px; }

/* Code override */
code { font-family: 'JetBrains Mono', monospace !important; }
</style>
""", unsafe_allow_html=True)

# ── Language definitions ──────────────────────────────────────────────────────
LANGUAGES = {
    "🇬🇧 English":    {"code": "en", "wiki": "en", "label": "English"},
    "🇮🇳 Hindi":      {"code": "hi", "wiki": "hi", "label": "Hindi"},
    "🇪🇸 Spanish":    {"code": "es", "wiki": "es", "label": "Spanish"},
    "🇫🇷 French":     {"code": "fr", "wiki": "fr", "label": "French"},
    "🇩🇪 German":     {"code": "de", "wiki": "de", "label": "German"},
    "🇮🇹 Italian":    {"code": "it", "wiki": "it", "label": "Italian"},
    "🇵🇹 Portuguese": {"code": "pt", "wiki": "pt", "label": "Portuguese"},
    "🇷🇺 Russian":    {"code": "ru", "wiki": "ru", "label": "Russian"},
    "🇯🇵 Japanese":   {"code": "ja", "wiki": "ja", "label": "Japanese"},
    "🇨🇳 Chinese":    {"code": "zh", "wiki": "zh", "label": "Chinese"},
    "🇸🇦 Arabic":     {"code": "ar", "wiki": "ar", "label": "Arabic"},
    "🇰🇷 Korean":     {"code": "ko", "wiki": "ko", "label": "Korean"},
    "🇹🇷 Turkish":    {"code": "tr", "wiki": "tr", "label": "Turkish"},
    "🇳🇱 Dutch":      {"code": "nl", "wiki": "nl", "label": "Dutch"},
    "🇵🇱 Polish":     {"code": "pl", "wiki": "pl", "label": "Polish"},
    "🇸🇪 Swedish":    {"code": "sv", "wiki": "sv", "label": "Swedish"},
    "🇺🇦 Ukrainian":  {"code": "uk", "wiki": "uk", "label": "Ukrainian"},
    "🇧🇩 Bengali":    {"code": "bn", "wiki": "bn", "label": "Bengali"},
    "🇮🇩 Indonesian": {"code": "id", "wiki": "id", "label": "Indonesian"},
    "🇬🇷 Greek":      {"code": "el", "wiki": "el", "label": "Greek"},
}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    model = st.text_input("Ollama model", value=DEFAULT_MODEL, help="Must be running locally via `ollama serve`")
    st.caption(f"Model: `{model}`")
    st.info("🔀 **Auto-mode:** native tool-calling for `llama3.1` / `qwen2.5`. Prompt-based fallback for `mistral` / `llama3`.", icon="🤖")

    st.divider()

    # Language selector
    st.markdown("### 🌐 Response Language")
    lang_options = list(LANGUAGES.keys())
    selected_lang_key = st.selectbox(
        "Respond in:",
        lang_options,
        index=0,
        key="lang_select",
        label_visibility="collapsed",
    )
    lang_info = LANGUAGES[selected_lang_key]
    selected_lang_label = selected_lang_key
    lang_code = lang_info["code"]
    wiki_lang = lang_info["wiki"]
    lang_name = lang_info["label"]

    # Build language-aware system prompt
    if lang_code == "en":
        LANG_SYSTEM = "You are a helpful assistant with access to tools. Use them whenever they help you answer better. Always respond in English."
    else:
        LANG_SYSTEM = (
            f"You are a helpful assistant with access to tools. Use them whenever they help you answer better. "
            f"IMPORTANT: Always respond entirely in {lang_name}. "
            f"When using the wiki_search tool, set the 'language' parameter to '{wiki_lang}'. "
            f"When the user asks to translate something, use the translator tool with target_language='{lang_name}'."
        )

    st.divider()

    # Target score + max versions
    st.markdown("### 🎯 Self-Improvement Controls")
    target_score = st.slider(
        "Target score",
        min_value=0.50, max_value=1.00, value=0.90, step=0.05,
        help="Agent keeps refining until it hits this score (or runs out of versions).",
    )
    max_versions = st.selectbox(
        "Max versions (iterations)",
        options=[1, 2, 3, 4, 5, 6],
        index=2,
        help="Maximum number of self-improvement iterations the agent will attempt.",
    )
    demo_mode = st.toggle("Demo mode (faster, fewer calls)", value=False)
    if demo_mode:
        max_versions = min(max_versions, 2)

    st.divider()
    st.markdown("### 🔧 Active Tools")
    selected_tools = []
    tool_names_all = list(TOOL_REGISTRY.keys())
    toggles = {}
    for t in ALL_TOOLS:
        tname = t["function"]["name"]
        toggles[tname] = st.toggle(tname, value=True, key=f"toggle_{tname}")
        if toggles[tname]:
            selected_tools.append(t)

    st.divider()
    st.markdown("### 💡 Example Prompts")
    examples = [
        "What is the current weather in Mumbai?",
        "Fetch the content of https://httpbin.org/json and summarize it",
        "Calculate (2 ** 32) + sqrt(144) * pi",
        "Search Wikipedia for 'quantum entanglement' and give me a 3-sentence summary",
        "Write and run Python code to generate the first 15 Fibonacci numbers",
        "Translate 'Hello, how are you?' to French",
        "Translate 'Artificial intelligence is the future' to Hindi",
        'Query the JSON \'{"user":{"name":"Akshat","age":22}}\' for user.name',
    ]
    for ex in examples:
        if st.button(ex[:55] + ("…" if len(ex) > 55 else ""), key=f"ex_{hash(ex)}", use_container_width=True):
            st.session_state["prefill"] = ex

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero-title">🤖 PromptForge — Self Improving AI Agent</div>
<p class="hero-sub">Local Ollama model × 8 real tools → intelligent agentic responses &nbsp;·&nbsp; <span style="color:#a5b4fc">{selected_lang_label}</span></p>
""", unsafe_allow_html=True)

st.divider()

# ── Tool showcase grid ────────────────────────────────────────────────────────
with st.expander("📦 Available Tools (click to inspect schemas)", expanded=False):
    cols = st.columns(3)
    icons = {
        "web_fetch": "🌐", "file_reader": "📄", "calculator": "🧮",
        "weather": "🌤️", "wiki_search": "📖", "code_runner": "🐍",
        "json_query": "🗄️", "translator": "🌍",
    }
    for i, tool_schema in enumerate(ALL_TOOLS):
        tname = tool_schema["function"]["name"]
        tdesc = tool_schema["function"]["description"]
        icon = icons.get(tname, "🔧")
        with cols[i % 3]:
            st.markdown(f"""
            <div class="tool-card">
                <div class="tool-name">{icon} {tname}</div>
                <div class="tool-desc">{tdesc[:120]}{'…' if len(tdesc) > 120 else ''}</div>
            </div>
            """, unsafe_allow_html=True)

st.divider()

# ── Chat input ────────────────────────────────────────────────────────────────
prefill = st.session_state.pop("prefill", "")
user_input = st.text_area(
    "Ask anything — the model will decide which tools to call:",
    value=prefill,
    height=100,
    placeholder="e.g. What's the weather in Tokyo and what is e^pi?",
    key="user_input",
)

col_btn, col_clear = st.columns([1, 5])
with col_btn:
    run_clicked = st.button("🚀 Run Agent", type="primary", use_container_width=True)
with col_clear:
    if st.button("🗑️ Clear", use_container_width=False):
        st.session_state.pop("last_result", None)
        st.rerun()

# ── Execution ──────────────────────────────────────────────────────────────────
if run_clicked and user_input.strip():
    if not selected_tools:
        st.warning("⚠️ Please enable at least one tool in the sidebar.")
    else:
        lang_indicator = f" (responding in {lang_name})" if lang_code != "en" else ""
        with st.spinner(f"🤖 Agent is thinking and calling tools{lang_indicator}…"):
            t0 = time.time()
            try:
                result = run_tool_agent(
                    user_message=user_input.strip(),
                    system_prompt=LANG_SYSTEM,
                    model=model,
                    tools=selected_tools,
                    verbose=False,
                    max_turns=max_versions,
                )
                result["elapsed"] = round(time.time() - t0, 2)
                st.session_state["last_result"] = result
            except Exception as e:
                st.error(f"**Error:** {e}")

# ── Results ────────────────────────────────────────────────────────────────────
if "last_result" in st.session_state:
    result = st.session_state["last_result"]
    turns = result.get("turns", [])
    tool_calls_made = result.get("tool_calls_made", [])
    final_answer = result.get("final_answer", "")
    elapsed = result.get("elapsed", 0)

    # Metrics row
    n_turns = len([t for t in turns if t["role"] == "assistant"])
    mode = result.get("mode", "native")
    mode_label = "🔌 Native" if mode == "native" else "📝 Prompt"
    score_display = result.get("score", "—")
    score_str = f"{score_display:.2f}" if isinstance(score_display, float) else str(score_display)
    hit_target = isinstance(score_display, float) and score_display >= target_score
    status_label = "✅ Target hit" if hit_target else f"⏳ Best of {max_versions}"
    st.markdown(f"""
    <div class="metric-row">
      <div class="metric-card"><div class="metric-num">{n_turns}</div><div class="metric-lbl">Agent turns</div></div>
      <div class="metric-card"><div class="metric-num">{len(tool_calls_made)}</div><div class="metric-lbl">Tool calls</div></div>
      <div class="metric-card"><div class="metric-num">{elapsed}s</div><div class="metric-lbl">Total time</div></div>
      <div class="metric-card"><div class="metric-num" style="font-size:1.1rem">{mode_label}</div><div class="metric-lbl">Tool-call mode</div></div>
      <div class="metric-card"><div class="metric-num" style="font-size:1rem">{target_score:.2f}</div><div class="metric-lbl">Target score</div></div>
      <div class="metric-card"><div class="metric-num">{max_versions}</div><div class="metric-lbl">Max versions</div></div>
    </div>
    """, unsafe_allow_html=True)

    # Target score progress bar
    col_prog1, col_prog2 = st.columns([3, 1])
    with col_prog1:
        st.caption(f"**Score vs Target:** {status_label}")
        st.progress(min(target_score, 1.0), text=f"Target → {target_score:.0%}")
    with col_prog2:
        st.metric(label="Target", value=f"{target_score:.2f}")

    # Language + tools used pills
    meta_html = f'<span class="pill pill-purple">🌐 {selected_lang_key}</span>&nbsp;'
    if tool_calls_made:
        meta_html += "".join(
            f'<span class="pill pill-green">🔧 {t}</span>' for t in tool_calls_made
        )
    st.markdown(meta_html, unsafe_allow_html=True)

    # Final answer
    st.markdown("### 💬 Final Answer")
    st.markdown(f'<div class="answer-box"><div class="answer-text">{final_answer}</div></div>', unsafe_allow_html=True)

    # Turn-by-turn trace
    if turns:
        st.divider()
        st.markdown("### 🔍 Agent Trace (turn-by-turn)")
        for turn in turns:
            role = turn["role"]
            if role == "assistant":
                tool_calls = turn["message"].get("tool_calls") or []
                content = turn["message"].get("content") or ""
                tc_names = [tc["function"]["name"] for tc in tool_calls]
                st.markdown(f"""
                <div class="turn-assistant">
                    <div class="turn-label assistant">🤖 Assistant — Turn {turn['turn']}</div>
                    {"<b>Content:</b> " + content if content else ""}
                    {"<br><b>Calling tools:</b> " + ", ".join(f"<code>{n}</code>" for n in tc_names) if tc_names else ""}
                </div>
                """, unsafe_allow_html=True)
            elif role == "tool":
                try:
                    pretty = json.dumps(json.loads(turn["result"]), indent=2)
                except Exception:
                    pretty = turn["result"]
                with st.expander(f"🔧 `{turn['tool_name']}({json.dumps(turn['arguments'])[:60]}…)` — Turn {turn['turn']}"):
                    st.code(pretty, language="json")

elif not run_clicked:
    st.info("👆 Enter a question above and click **Run Agent** — the model will automatically pick and call the right tools.", icon="💡")
