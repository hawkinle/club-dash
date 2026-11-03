import html
import io
import time
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.config import (
    CLUB_NAME,
    SQUARE_ENVIRONMENT,
    USE_MOCK,
    is_square_configured,
)
from src.database import Database
from src.sync_engine import SyncEngine
from src.square_client import SquareClient

# -------------------------------------------------------------
# Streamlit Page Config & Head Chrome
# -------------------------------------------------------------
st.set_page_config(
    page_title=f"{CLUB_NAME} • Executive Intelligence Suite",
    page_icon="🏉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------
# Ultra-High-End Obsidian Glassmorphism Styling
# -------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {
        --canvas-obsidian: #06080E;
        --surface-glass: rgba(255, 255, 255, 0.035);
        --surface-hover: rgba(255, 255, 255, 0.055);
        --border-subtle: rgba(255, 255, 255, 0.07);
        --border-active: rgba(223, 177, 91, 0.35);
        
        --gold-burnished: #DFB15B;
        --gold-glow: rgba(223, 177, 91, 0.15);
        --cobalt-electric: #0052CC;
        --cobalt-glow: rgba(0, 82, 204, 0.25);
        --platinum-muted: #94A3B8;
        --jade-emerald: #10B981;
        --terracotta-rose: #F43F5E;
        --amber-warm: #F59E0B;
        
        --text-primary: #F8FAFC;
        --text-secondary: #94A3B8;
        --text-muted: #64748B;
    }

    /* 1. Sleek Streamlit Chrome & Header Controls (Sidebar Toggle Kept Fully Visible & Accessible) */
    #MainMenu { visibility: hidden !important; display: none !important; }
    footer { visibility: hidden !important; display: none !important; }
    div[data-testid="stDecoration"] { display: none !important; }
    div[data-testid="stStatusWidget"] { visibility: hidden !important; display: none !important; }
    .stDeployButton { display: none !important; }
    div[data-testid="stToolbar"] {
        display: flex !important;
        visibility: visible !important;
        background: transparent !important;
    }
    .stDeployButton, #MainMenu, [data-testid="manage-app-button"] {
        display: none !important;
        visibility: hidden !important;
    }

    /* Transparent unobtrusive header preserving the sidebar toggle button */
    header[data-testid="stHeader"] {
        background: transparent !important;
        color: #F8FAFC !important;
        height: 2.75rem !important;
        z-index: 100 !important;
    }
    header[data-testid="stHeader"] [data-testid="stDecoration"] { display: none !important; }
    header[data-testid="stHeader"] .stDeployButton { display: none !important; }

    /* Luxury Obsidian/Gold Sidebar Toggle Button */
    /* Luxury Obsidian/Gold Sidebar Toggle Button (Fully Visible & Accessible) */
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stExpandSidebarButton"],
    [data-testid="collapsedControl"],
    button[data-testid="stSidebarCollapseButton"],
    header[data-testid="stHeader"] button {
        display: inline-flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        color: var(--gold-burnished) !important;
        background: rgba(14, 19, 31, 0.92) !important;
        border: 1px solid rgba(223, 177, 91, 0.45) !important;
        border-radius: 8px !important;
        padding: 5px 10px !important;
        backdrop-filter: blur(16px) !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5) !important;
        cursor: pointer !important;
        z-index: 999999 !important;
    }
    [data-testid="stSidebarCollapsedControl"]:hover,
    [data-testid="stExpandSidebarButton"]:hover,
    [data-testid="collapsedControl"]:hover,
    button[data-testid="stSidebarCollapseButton"]:hover,
    header[data-testid="stHeader"] button:hover {
        background: rgba(223, 177, 91, 0.25) !important;
        border-color: var(--gold-burnished) !important;
        color: #FFFFFF !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 18px rgba(223, 177, 91, 0.3) !important;
    }

    /* 2. Deep Obsidian Canvas with Architectural Grid & Dual-Apex Lighting */
    .stApp {
        background-color: var(--canvas-obsidian) !important;
        background-image: 
            radial-gradient(ellipse 70% 35% at 50% -10%, rgba(223, 177, 91, 0.12) 0%, transparent 60%),
            radial-gradient(circle at 14% 16%, rgba(0, 82, 204, 0.14) 0%, transparent 45%),
            radial-gradient(circle at 86% 20%, rgba(223, 177, 91, 0.08) 0%, transparent 42%),
            radial-gradient(circle at 50% 88%, rgba(0, 82, 204, 0.08) 0%, transparent 55%),
            radial-gradient(rgba(255, 255, 255, 0.055) 1px, transparent 1px) !important;
        background-size: 100% 100%, 100% 100%, 100% 100%, 100% 100%, 24px 24px !important;
        background-attachment: fixed !important;
        color: var(--text-primary) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        letter-spacing: -0.01em;
    }

    /* Reskin BaseWeb Select Containers & Dropdown Menus into Dark Glass Pills */
    div[data-baseweb="select"] > div {
        background-color: rgba(14, 19, 31, 0.88) !important;
        border: 1px solid rgba(255, 255, 255, 0.09) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.16) !important;
        border-radius: 9px !important;
        color: #F8FAFC !important;
        font-size: 0.84rem !important;
        backdrop-filter: blur(16px) !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    div[data-baseweb="select"] > div:hover {
        border-color: rgba(223, 177, 91, 0.45) !important;
        background-color: rgba(20, 26, 42, 0.96) !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.45) !important;
    }
    div[data-baseweb="popover"], div[data-baseweb="menu"], ul[role="listbox"] {
        background-color: #0C101A !important;
        border: 1px solid rgba(223, 177, 91, 0.32) !important;
        border-radius: 10px !important;
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.85) !important;
    }
    li[role="option"] {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.82rem !important;
        color: #CBD5E1 !important;
        padding: 8px 14px !important;
    }
    li[role="option"]:hover, li[aria-selected="true"] {
        background-color: rgba(0, 82, 204, 0.28) !important;
        color: #DFB15B !important;
    }

    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 3.2rem !important;
        padding-left: 2.2rem !important;
        padding-right: 2.2rem !important;
        max-width: 1440px !important;
    }

    /* 3. Typography & Headings */
    h1, h2, h3, h4, .deck-title, .metric-val, .card-title {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif !important;
        letter-spacing: -0.02em;
        color: #F8FAFC !important;
    }

    /* Tabular figures for all currency & numbers */
    .tabular-nums, .metric-val, .waterfall-val, .tender-val {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-feature-settings: 'tnum' 1, 'zero' 1 !important;
        font-variant-numeric: tabular-nums !important;
    }

    /* 4. Sidebar Glass Styling */
    section[data-testid="stSidebar"] {
        background-color: rgba(9, 13, 22, 0.78) !important;
        backdrop-filter: blur(28px) !important;
        -webkit-backdrop-filter: blur(28px) !important;
        border-right: 1px solid var(--border-subtle) !important;
        box-shadow: 12px 0 36px rgba(0, 0, 0, 0.45) !important;
    }

    section[data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.07) !important;
        margin: 1.2rem 0 !important;
    }

    /* 5. Custom Top Deck Header */
    .top-deck {
        background: linear-gradient(135deg, rgba(0, 82, 204, 0.14) 0%, rgba(223, 177, 91, 0.07) 50%, rgba(10, 13, 21, 0.7) 100%);
        border: 1px solid var(--border-subtle);
        border-radius: 14px;
        padding: 14px 20px;
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
        margin-bottom: 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
    }

    .deck-brand {
        display: flex;
        align-items: center;
        gap: 14px;
    }

    .club-crest {
        display: flex;
        align-items: center;
        justify-content: center;
        filter: drop-shadow(0 4px 10px rgba(223, 177, 91, 0.22));
    }

    .deck-title-row {
        display: flex;
        align-items: center;
        gap: 10px;
        flex-wrap: wrap;
    }

    .deck-title {
        font-size: 1.25rem;
        font-weight: 700;
        margin: 0;
        line-height: 1.2;
        background: linear-gradient(90deg, #FFFFFF 0%, #F8FAFC 50%, var(--gold-burnished) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .deck-subtitle {
        color: var(--text-secondary);
        font-size: 0.78rem;
        margin-top: 2px;
        letter-spacing: 0.01em;
    }

    .deck-meta {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
    }

    .meta-pill {
        background: rgba(255, 255, 255, 0.035);
        border: 1px solid var(--border-subtle);
        border-radius: 18px;
        padding: 4px 10px;
        display: flex;
        flex-direction: column;
        align-items: flex-end;
    }

    .meta-label {
        font-size: 0.60rem;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        color: var(--text-muted);
        font-weight: 600;
    }

    .meta-val {
        font-size: 0.78rem;
        font-weight: 600;
        color: #F8FAFC;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* Status Pill with Pulsing Dot */
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 3px 10px;
        border-radius: 16px;
        font-size: 0.70rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }

    .status-pill-live {
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.35);
        color: #34D399;
    }

    .status-pill-sim {
        background: rgba(245, 158, 11, 0.12);
        border: 1px solid rgba(245, 158, 11, 0.35);
        color: #FBBF24;
    }

    .pulse-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        display: inline-block;
    }

    .pulse-dot-live {
        background-color: #10B981;
        box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
        animation: pulseLive 2s infinite;
    }

    .pulse-dot-sim {
        background-color: #F59E0B;
        box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.7);
        animation: pulseSim 2s infinite;
    }

    @keyframes pulseLive {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 5px rgba(16, 185, 129, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }

    @keyframes pulseSim {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 5px rgba(245, 158, 11, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }
    }

    /* 6. Luxury Executive KPI Glass Cards & Sovereign Hero Metric */
    .kpi-card {
        background: linear-gradient(145deg, rgba(255, 255, 255, 0.042) 0%, rgba(255, 255, 255, 0.012) 100%);
        border: 1px solid var(--border-subtle);
        border-top: 1px solid rgba(255, 255, 255, 0.16);
        border-radius: 12px;
        padding: 13px 15px;
        backdrop-filter: blur(22px);
        -webkit-backdrop-filter: blur(22px);
        box-shadow: 0 10px 28px -8px rgba(0, 0, 0, 0.65), 0 1px 0 rgba(255, 255, 255, 0.04) inset;
        position: relative;
        overflow: hidden;
        min-height: 102px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .kpi-card:hover {
        transform: translateY(-2px);
        border-color: var(--border-active);
        box-shadow: 0 12px 30px -6px rgba(0, 0, 0, 0.75), 0 0 18px var(--gold-glow);
    }

    .kpi-hero-card {
        background: linear-gradient(145deg, rgba(223, 177, 91, 0.11) 0%, rgba(14, 19, 31, 0.96) 100%) !important;
        border: 1px solid rgba(223, 177, 91, 0.44) !important;
        border-top: 1px solid rgba(255, 243, 196, 0.68) !important;
        box-shadow: 0 14px 36px -8px rgba(0, 0, 0, 0.85), 0 0 26px rgba(223, 177, 91, 0.15) !important;
    }

    .kpi-hero-card .hero-flag {
        position: absolute;
        top: 0;
        right: 12px;
        background: linear-gradient(180deg, #DFB15B 0%, #B8860B 100%);
        color: #06080E;
        font-size: 0.56rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        padding: 2px 7px;
        border-bottom-left-radius: 5px;
        border-bottom-right-radius: 5px;
    }

    .kpi-hero-card .kpi-value {
        font-size: 1.66rem !important;
        color: #FFFDF7 !important;
        text-shadow: 0 2px 12px rgba(223, 177, 91, 0.28);
    }

    .micro-code-pill {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.60rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        padding: 1px 6px;
        border-radius: 5px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.10);
        color: #94A3B8;
    }

    .kpi-accent-bar {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
    }

    .kpi-label {
        font-size: 0.66rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--text-secondary);
        font-weight: 600;
        margin-bottom: 2px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .kpi-value {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 1.42rem !important;
        font-weight: 700 !important;
        color: #FFFFFF;
        letter-spacing: -0.02em;
        font-feature-settings: 'tnum' 1, 'zero' 1;
        font-variant-numeric: tabular-nums;
        margin: 2px 0 4px 0;
        line-height: 1.15;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .kpi-footer {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.69rem;
        color: var(--text-muted);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .trend-pill-pos {
        background: rgba(16, 185, 129, 0.12);
        color: #10B981;
        border: 1px solid rgba(16, 185, 129, 0.28);
        padding: 1px 7px;
        border-radius: 10px;
        font-size: 0.68rem;
        font-weight: 600;
        font-feature-settings: 'tnum' 1;
        display: inline-flex;
        align-items: center;
        gap: 2px;
    }

    .trend-pill-neg {
        background: rgba(244, 63, 94, 0.12);
        color: #F43F5E;
        border: 1px solid rgba(244, 63, 94, 0.28);
        padding: 1px 7px;
        border-radius: 10px;
        font-size: 0.68rem;
        font-weight: 600;
        font-feature-settings: 'tnum' 1;
        display: inline-flex;
        align-items: center;
        gap: 2px;
    }

    /* 7. Custom Navigation Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background: rgba(12, 17, 28, 0.65);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        padding: 4px;
        margin-bottom: 18px;
        backdrop-filter: blur(20px);
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 14px;
        font-weight: 500;
        font-size: 0.82rem;
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: var(--text-secondary) !important;
        background: transparent;
        border: 1px solid transparent;
        transition: all 0.2s ease;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: #F8FAFC !important;
        background: rgba(255, 255, 255, 0.04);
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(0, 82, 204, 0.30) 0%, rgba(223, 177, 91, 0.16) 100%) !important;
        border-color: rgba(223, 177, 91, 0.40) !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 18px rgba(0, 82, 204, 0.30);
    }

    .stTabs [data-baseweb="tab-border"] {
        display: none !important;
    }

    /* 8. Streamlit Form Inputs & Buttons Reskinning */
    div[data-baseweb="select"] > div {
        background-color: rgba(255, 255, 255, 0.035) !important;
        border-color: rgba(255, 255, 255, 0.08) !important;
        border-radius: 8px !important;
        color: #F8FAFC !important;
        font-size: 0.9rem !important;
        transition: all 0.2s ease !important;
    }

    div[data-baseweb="select"] > div:hover {
        border-color: rgba(223, 177, 91, 0.4) !important;
        background-color: rgba(255, 255, 255, 0.05) !important;
    }

    div[data-baseweb="input"] > div {
        background-color: rgba(255, 255, 255, 0.035) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 8px !important;
        color: #F8FAFC !important;
    }

    div[data-baseweb="input"] input {
        color: #F8FAFC !important;
        font-family: 'Inter', sans-serif !important;
    }

    .stButton > button {
        background: linear-gradient(135deg, rgba(223, 177, 91, 0.15) 0%, rgba(0, 82, 204, 0.18) 100%) !important;
        border: 1px solid rgba(223, 177, 91, 0.35) !important;
        color: #DFB15B !important;
        font-weight: 600 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        letter-spacing: 0.02em !important;
        border-radius: 8px !important;
        padding: 0.55rem 1.2rem !important;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25) !important;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, rgba(223, 177, 91, 0.28) 0%, rgba(0, 82, 204, 0.32) 100%) !important;
        border-color: #DFB15B !important;
        box-shadow: 0 6px 20px rgba(223, 177, 91, 0.22) !important;
        transform: translateY(-2px) !important;
        color: #FFFFFF !important;
    }

    .stDownloadButton > button {
        background: linear-gradient(135deg, rgba(0, 82, 204, 0.22) 0%, rgba(16, 185, 129, 0.18) 100%) !important;
        border: 1px solid rgba(0, 82, 204, 0.45) !important;
        color: #60A5FA !important;
        font-weight: 600 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        letter-spacing: 0.02em !important;
        border-radius: 8px !important;
        padding: 0.55rem 1.2rem !important;
        transition: all 0.25s ease !important;
    }

    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, rgba(0, 82, 204, 0.4) 0%, rgba(16, 185, 129, 0.3) 100%) !important;
        border-color: #60A5FA !important;
        box-shadow: 0 6px 20px rgba(0, 82, 204, 0.3) !important;
        transform: translateY(-2px) !important;
        color: #FFFFFF !important;
    }

    /* 9. Bank Settlement Waterfall Cards */
    .waterfall-flow {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 12px;
        margin: 16px 0 24px 0;
    }

    @media (max-width: 992px) {
        .waterfall-flow {
            grid-template-columns: 1fr;
        }
    }

    .waterfall-step {
        background: linear-gradient(145deg, rgba(255, 255, 255, 0.035) 0%, rgba(255, 255, 255, 0.01) 100%);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        padding: 16px;
        position: relative;
        backdrop-filter: blur(16px);
        transition: all 0.2s ease;
    }

    .waterfall-step:hover {
        border-color: var(--border-active);
        transform: translateY(-2px);
    }

    .waterfall-step-num {
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--text-secondary);
        margin-bottom: 4px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .waterfall-op {
        font-weight: 700;
        font-size: 0.85rem;
        padding: 1px 6px;
        border-radius: 4px;
    }

    .waterfall-val {
        font-size: 1.45rem;
        font-weight: 700;
        margin: 4px 0;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    .waterfall-sub {
        font-size: 0.74rem;
        color: var(--text-muted);
    }

    /* Tender Balancing Cards */
    .tender-card {
        background: linear-gradient(145deg, rgba(255, 255, 255, 0.035) 0%, rgba(255, 255, 255, 0.01) 100%);
        border: 1px solid var(--border-subtle);
        border-radius: 14px;
        padding: 22px 24px;
        backdrop-filter: blur(20px);
        position: relative;
        overflow: hidden;
    }

    .tender-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
    }

    .tender-title {
        font-size: 0.82rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #CBD5E1;
    }

    .tender-badge {
        font-size: 0.72rem;
        padding: 3px 10px;
        border-radius: 12px;
        font-weight: 600;
    }

    .tender-val {
        font-size: 2.1rem;
        font-weight: 700;
        margin: 6px 0;
    }

    .tender-sub {
        font-size: 0.8rem;
        color: var(--text-secondary);
    }

    /* Xero Quick Procedure Callout */
    .xero-guide-card {
        background: linear-gradient(135deg, rgba(0, 82, 204, 0.12) 0%, rgba(19, 181, 234, 0.06) 100%);
        border: 1px solid rgba(0, 82, 204, 0.35);
        border-radius: 12px;
        padding: 18px 22px;
        font-size: 0.86rem;
        color: #CBD5E1;
        backdrop-filter: blur(16px);
    }

    /* Peak Operational Window Callout */
    .peak-intel-card {
        background: linear-gradient(135deg, rgba(223, 177, 91, 0.1) 0%, rgba(245, 158, 11, 0.05) 100%);
        border: 1px solid rgba(223, 177, 91, 0.28);
        border-radius: 14px;
        padding: 20px 24px;
        margin-top: 20px;
        backdrop-filter: blur(20px);
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# Luxury Palette Constants
# -------------------------------------------------------------
COLOR_GOLD = "#DFB15B"
COLOR_COBALT = "#0052CC"
COLOR_PLATINUM = "#94A3B8"
COLOR_JADE = "#10B981"
COLOR_ROSE = "#F43F5E"
COLOR_AMBER = "#F59E0B"
LUXURY_PALETTE = [COLOR_GOLD, COLOR_COBALT, COLOR_JADE, COLOR_AMBER, "#8B5CF6", COLOR_ROSE, "#06B6D4"]

# -------------------------------------------------------------
# Database & Sync Initialisation
# -------------------------------------------------------------
def get_db():
    return Database()

def get_sync_engine():
    db = get_db()
    client = SquareClient()
    return SyncEngine(db=db, client=client)

db = get_db()
sync_engine = get_sync_engine()

# -------------------------------------------------------------
# Strict Front-Door Authentication Gate & Session Security
# -------------------------------------------------------------
SESSION_TIMEOUT_SECONDS = 45 * 60  # 45-minute inactivity timeout (SEC-10)

if "authenticated_user" not in st.session_state:
    st.session_state["authenticated_user"] = None

if st.session_state["authenticated_user"] is not None:
    now_ts = time.time()
    last_ts = st.session_state.get("last_activity_ts", now_ts)
    if (now_ts - last_ts) > SESSION_TIMEOUT_SECONDS:
        st.session_state["authenticated_user"] = None
        st.session_state["session_expired_notice"] = True
        st.rerun()
    st.session_state["last_activity_ts"] = now_ts

if st.session_state["authenticated_user"] is None:
    crest_svg = '<svg width="58" height="58" viewBox="0 0 52 52" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="26" cy="26" r="24.5" stroke="url(#goldRim)" stroke-width="1.5" stroke-dasharray="3 2" /><circle cx="26" cy="26" r="22" fill="#0A0D15" stroke="rgba(223, 177, 91, 0.35)" stroke-width="1" /><circle cx="26" cy="26" r="17" fill="url(#crestCobaltGlow)" opacity="0.65" /><path d="M18 30C18 21 26 15 26 15C26 15 34 21 34 30C34 34.5 30 38 26 38C22 38 18 34.5 18 30Z" stroke="#DFB15B" stroke-width="1.8" stroke-linecap="round" fill="none"/><path d="M26 16V37" stroke="#DFB15B" stroke-width="1.3" stroke-linecap="round"/><path d="M21 24H31" stroke="#DFB15B" stroke-width="1.3" stroke-linecap="round"/><path d="M20 30H32" stroke="#DFB15B" stroke-width="1.3" stroke-linecap="round"/><circle cx="26" cy="26" r="1.8" fill="#DFB15B"/><defs><linearGradient id="goldRim" x1="0" y1="0" x2="52" y2="52" gradientUnits="userSpaceOnUse"><stop stop-color="#DFB15B" /><stop offset="0.5" stop-color="#FFF3C4" /><stop offset="1" stop-color="#B8860B" /></linearGradient><radialGradient id="crestCobaltGlow" cx="0.5" cy="0.5" r="0.5"><stop stop-color="#0052CC" stop-opacity="0.85"/><stop offset="1" stop-color="#0A0D15" stop-opacity="0"/></radialGradient></defs></svg>'

    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    c_gate_l, c_gate_m, c_gate_r = st.columns([1, 1.15, 1])
    with c_gate_m:
        if st.session_state.pop("session_expired_notice", False):
            st.warning("⏱️ Your executive session timed out after 45 minutes of inactivity. Please sign in again.")

        st.markdown(f"""
        <div style="background: linear-gradient(145deg, rgba(14, 19, 31, 0.95) 0%, rgba(10, 13, 21, 0.98) 100%); border: 1px solid rgba(223, 177, 91, 0.35); border-radius: 16px; padding: 28px 24px 20px 24px; box-shadow: 0 20px 50px rgba(0, 0, 0, 0.8), 0 0 30px rgba(223, 177, 91, 0.12); backdrop-filter: blur(28px); text-align: center; margin-bottom: 20px;">
            <div style="display: flex; justify-content: center; margin-bottom: 12px;">{crest_svg}</div>
            <h2 style="margin: 0; font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.35rem; color: #FFFFFF; font-weight: 700; letter-spacing: -0.02em;">Upper Horton Sports Club</h2>
            <div style="color: #DFB15B; font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 4px; margin-bottom: 14px;">Commercial Settlement & Executive Suite</div>
            <p style="color: #94A3B8; font-size: 0.80rem; margin: 0; line-height: 1.5;">Authorized board members and management staff sign-in.</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("front_door_login_form"):
            in_user = st.text_input("Username", placeholder="Enter your club username", key="login_username_val")
            in_pass = st.text_input("Password", type="password", placeholder="••••••••", key="login_password_val")
            btn_login = st.form_submit_button("🔐 Sign In to Executive Suite", use_container_width=True)

            if btn_login:
                user_res = db.authenticate_user(in_user, in_pass)
                if user_res:
                    if user_res.get("error") == "SUSPENDED":
                        st.error("⛔ Access Revoked: This board account is currently suspended. Please contact the Club President.")
                    elif user_res.get("error") == "LOCKED":
                        mins = user_res.get("minutes_remaining", 15)
                        st.error(f"🔒 Brute-Force Shield: Account locked due to 5 failed sign-in attempts. Please wait {mins} minutes.")
                    else:
                        st.session_state["authenticated_user"] = user_res
                        st.session_state["last_activity_ts"] = time.time()
                        st.success(f"Welcome back, {user_res['full_name']}!")
                        st.rerun()
                else:
                    st.error("❌ Invalid username or password. Please verify your credentials.")

        st.markdown("""
        <div style="text-align: center; color: #64748B; font-size: 0.72rem; margin-top: 14px;">
            🔒 Protected by PBKDF2-HMAC-SHA256 (600,000 Iterations) & Brute-Force Lockout Shield<br>
            Upper Horton Sports Club • 22 Cobbadah St, Upper Horton NSW 2347
        </div>
        """, unsafe_allow_html=True)

    st.stop()

current_user = st.session_state["authenticated_user"]
safe_full_name = html.escape(str(current_user.get("full_name", "Board Member")))
safe_username = html.escape(str(current_user.get("username", "user")))
safe_role = html.escape(str(current_user.get("role", "Member")))

# Mandatory First-Login Password Rotation Gate (SEC-06)
if current_user.get("must_change_password"):
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    _, col_rot, _ = st.columns([1, 1.25, 1])
    with col_rot:
        st.markdown(f"""
        <div style="background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.45); border-radius: 14px; padding: 22px 24px; margin-bottom: 16px;">
            <h3 style="margin: 0 0 6px 0; color: #FBBF24; font-family: 'Plus Jakarta Sans', sans-serif;">🔐 Mandatory Security Password Update</h3>
            <p style="margin: 0; font-size: 0.84rem; color: #E2E8F0; line-height: 1.5;">
                Welcome, <strong>{safe_full_name}</strong>. For Upper Horton Sports Club security compliance, you must replace the initial default password with a strong personal passphrase before accessing financial records.
            </p>
        </div>
        """, unsafe_allow_html=True)
        with st.form("mandatory_pw_rotation_form"):
            new_sec_pw1 = st.text_input("New Personal Password (8+ chars, letters & numbers/symbols)", type="password")
            new_sec_pw2 = st.text_input("Confirm New Personal Password", type="password")
            save_rot_btn = st.form_submit_button("✅ Update Password & Unlock Suite", use_container_width=True)
            if save_rot_btn:
                if new_sec_pw1 != new_sec_pw2:
                    st.error("Passwords do not match.")
                else:
                    ok_pw, msg_pw = db.reset_user_password(current_user["user_id"], new_sec_pw1, actor=current_user["username"])
                    if ok_pw:
                        st.session_state["authenticated_user"]["must_change_password"] = False
                        st.success("Password updated! Unlocking Executive Suite...")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg_pw}")
        if st.button("🚪 Cancel & Sign Out", use_container_width=True):
            st.session_state["authenticated_user"] = None
            st.rerun()
    st.stop()

# Initial Auto-Seed if database empty
with db.get_connection(read_only=True) as con:
    order_count = con.execute("SELECT count(*) FROM orders").fetchone()[0]
if order_count == 0:
    sync_engine.run_sync(force_mock=True)

# -------------------------------------------------------------
# Sidebar: Executive Flight Controls & Location Scope
# -------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
        <span style="font-size: 1.5rem;">🏉</span>
        <div>
            <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 700; font-size: 1.15rem; color: #FFFFFF; line-height: 1.1;">UHSC Console</div>
            <div style="font-size: 0.72rem; color: #94A3B8; letter-spacing: 0.05em; text-transform: uppercase;">Upper Horton Sports Club</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Active Authenticated User Badge & Sign Out (SEC-04: Escaped HTML)
    st.markdown(f"""
    <div style="background: rgba(255, 255, 255, 0.035); border: 1px solid rgba(223, 177, 91, 0.35); border-radius: 10px; padding: 10px 12px; margin-bottom: 12px; backdrop-filter: blur(16px);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
            <span style="font-size: 0.64rem; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.06em; font-weight: 600;">Active Sign-In</span>
            <span style="font-size: 0.68rem; color: #34D399; font-weight: 600;">● Verified</span>
        </div>
        <div style="font-size: 0.90rem; font-weight: 700; color: #FFFFFF; font-family: 'Plus Jakarta Sans', sans-serif;">{safe_full_name}</div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
            <span style="background: rgba(223, 177, 91, 0.15); color: #DFB15B; border: 1px solid rgba(223, 177, 91, 0.35); border-radius: 12px; padding: 1px 7px; font-size: 0.66rem; font-weight: 600;">{safe_role}</span>
            <span style="font-size: 0.70rem; color: #94A3B8;">@{safe_username}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚪 Sign Out", use_container_width=True, key="sidebar_signout_btn"):
        db.log_audit_event(current_user.get("username", "user"), "USER_LOGOUT", current_user.get("username", "user"), "Signed out via sidebar")
        st.session_state["authenticated_user"] = None
        st.rerun()
    
    # Environment Status Badge
    is_live = (not USE_MOCK) and is_square_configured()
    if is_live:
        st.markdown(f"""
        <div style="background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 8px; padding: 8px 12px; margin-top: 12px; margin-bottom: 14px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span class="pulse-dot pulse-dot-live"></span>
                <span style="color: #34D399; font-weight: 600; font-size: 0.78rem; letter-spacing: 0.04em; text-transform: uppercase;">Square {SQUARE_ENVIRONMENT} Production</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.35); border-radius: 8px; padding: 8px 12px; margin-top: 12px; margin-bottom: 14px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span class="pulse-dot pulse-dot-sim"></span>
                <span style="color: #FBBF24; font-weight: 600; font-size: 0.78rem; letter-spacing: 0.04em; text-transform: uppercase;">Simulated Sandbox Active</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    PRESET_OPTIONS = [
        "Weekly Trading (Last 7 Days)",
        "Previous Calendar Month (Full Completed Month)",
        "Monthly Trading (Month to Date)",
        "Monthly Trading (Last 30 Days)",
        "Daily Close (Today)",
        "Daily Close (Yesterday)",
        "Annual Trading (Year to Date)",
        "Custom Date Window"
    ]
    if "app_date_preset" not in st.session_state:
        st.session_state["app_date_preset"] = "Weekly Trading (Last 7 Days)"
    if "app_selected_loc" not in st.session_state:
        st.session_state["app_selected_loc"] = "ALL"

    def on_sb_preset_change():
        st.session_state["app_date_preset"] = st.session_state["sb_date_preset"]

    st.markdown("---")
    st.markdown("<div style='font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: #94A3B8; margin-bottom: 8px;'>📅 Trading Window</div>", unsafe_allow_html=True)

    sb_preset_idx = PRESET_OPTIONS.index(st.session_state["app_date_preset"]) if st.session_state["app_date_preset"] in PRESET_OPTIONS else 0
    st.selectbox(
        "Period Preset",
        PRESET_OPTIONS,
        index=sb_preset_idx,
        key="sb_date_preset",
        on_change=on_sb_preset_change,
        label_visibility="collapsed"
    )
    date_preset = st.session_state["app_date_preset"]

    now = datetime.now()
    if "Today" in date_preset:
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        cadence_type = "Daily Close"
        cadence_badge = f"DAILY REPORT • TODAY ({now.strftime('%d %b %Y')})"
        num_days = 1
    elif "Yesterday" in date_preset:
        yesterday = now - timedelta(days=1)
        start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        cadence_type = "Daily Close"
        cadence_badge = f"DAILY REPORT • YESTERDAY ({yesterday.strftime('%d %b %Y')})"
        num_days = 1
    elif "Last 7 Days" in date_preset:
        start_date = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now
        cadence_type = "Weekly Run"
        cadence_badge = "WEEKLY REPORT • LAST 7 TRADING DAYS"
        num_days = 7
    elif "Previous Calendar Month" in date_preset:
        first_of_curr = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = first_of_curr - timedelta(seconds=1)
        start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        cadence_type = "Monthly Board Pack"
        cadence_badge = f"FULL CALENDAR MONTH • {start_date.strftime('%B %Y').upper()}"
        num_days = max(1, (end_date.date() - start_date.date()).days + 1)
    elif "Month to Date" in date_preset:
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now
        cadence_type = "Monthly Run"
        cadence_badge = f"MONTH-TO-DATE (MTD) • {now.strftime('%B %Y')}"
        num_days = max(1, (end_date.date() - start_date.date()).days + 1)
    elif "Last 30 Days" in date_preset:
        start_date = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now
        cadence_type = "Monthly Run"
        cadence_badge = "MONTHLY REPORT • LAST 30 TRADING DAYS"
        num_days = 30
    elif "Year to Date" in date_preset:
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now
        cadence_type = "Annual Run"
        cadence_badge = f"ANNUAL REPORT (YTD) • {now.year}"
        num_days = max(1, (end_date.date() - start_date.date()).days + 1)
    else:
        c_d1, c_d2 = st.columns(2)
        with c_d1:
            picked_start = st.date_input("From", value=now.date() - timedelta(days=14))
        with c_d2:
            picked_end = st.date_input("To", value=now.date())
        start_date = datetime.combine(picked_start, datetime.min.time())
        end_date = datetime.combine(picked_end, datetime.max.time())
        num_days = max(1, (picked_end - picked_start).days + 1)
        cadence_type = f"{num_days}-Day Custom"
        cadence_badge = f"CUSTOM WINDOW • {num_days} TRADING DAYS"

    start_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end_date.strftime("%Y-%m-%d %H:%M:%S")

    # Club Location / Outlet Filter
    st.markdown("<div style='font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: #94A3B8; margin-top: 14px; margin-bottom: 8px;'>🏛️ Club Outlet / Register</div>", unsafe_allow_html=True)
    locations = db.get_available_locations()
    loc_options = {"ALL": "All Club Outlets (Consolidated)"}
    for loc in locations:
        loc_options[loc["location_id"]] = loc["name"]
    
    def on_sb_loc_change():
        st.session_state["app_selected_loc"] = st.session_state["sb_selected_loc"]

    sb_loc_idx = list(loc_options.keys()).index(st.session_state["app_selected_loc"]) if st.session_state["app_selected_loc"] in loc_options else 0
    st.selectbox(
        "Club Outlet",
        options=list(loc_options.keys()),
        index=sb_loc_idx,
        format_func=lambda k: loc_options[k],
        key="sb_selected_loc",
        on_change=on_sb_loc_change,
        label_visibility="collapsed"
    )
    selected_loc_id = st.session_state["app_selected_loc"]

    st.markdown("---")
    st.markdown("<div style='font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: #94A3B8; margin-bottom: 8px;'>🌙 Nightly Batch Ledger</div>", unsafe_allow_html=True)

    recent_syncs = db.get_sync_history(limit=1)
    last_sync_str = str(recent_syncs.iloc[0]["synced_at"])[:16] + " UTC" if not recent_syncs.empty else "Scheduled 02:00 AM"
    st.markdown(f"""
    <div style="background: rgba(14, 19, 31, 0.85); border: 1px solid rgba(52, 211, 153, 0.28); border-radius: 8px; padding: 9px 11px; font-size: 0.74rem; color: #E2E8F0;">
        <div style="color: #34D399; font-weight: 700; margin-bottom: 3px;">🔒 Read-Only Air-Gapped Ledger</div>
        <div style="color: #94A3B8; font-size: 0.69rem;">Auto-reconciles nightly at <strong>02:00 AM</strong></div>
        <div style="color: #64748B; font-size: 0.66rem; margin-top: 3px;">Last batch: {html.escape(last_sync_str)}</div>
    </div>
    """, unsafe_allow_html=True)

# -------------------------------------------------------------
# Sleek Top Deck: Crest Badge, Live Status & Trading Context
# -------------------------------------------------------------
if is_live:
    status_html = '<span class="status-pill status-pill-live"><span class="pulse-dot pulse-dot-live"></span>Square Production Ledger</span>'
else:
    status_html = '<span class="status-pill status-pill-sim"><span class="pulse-dot pulse-dot-sim"></span>Simulated Sandbox</span>'

# Bespoke Gold & Cobalt Club Crest Emblem SVG
crest_svg = '<svg width="52" height="52" viewBox="0 0 52 52" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="26" cy="26" r="24.5" stroke="url(#goldRim)" stroke-width="1.5" stroke-dasharray="3 2" /><circle cx="26" cy="26" r="22" fill="#0A0D15" stroke="rgba(223, 177, 91, 0.35)" stroke-width="1" /><circle cx="26" cy="26" r="17" fill="url(#crestCobaltGlow)" opacity="0.65" /><path d="M18 30C18 21 26 15 26 15C26 15 34 21 34 30C34 34.5 30 38 26 38C22 38 18 34.5 18 30Z" stroke="#DFB15B" stroke-width="1.8" stroke-linecap="round" fill="none"/><path d="M26 16V37" stroke="#DFB15B" stroke-width="1.3" stroke-linecap="round"/><path d="M21 24H31" stroke="#DFB15B" stroke-width="1.3" stroke-linecap="round"/><path d="M20 30H32" stroke="#DFB15B" stroke-width="1.3" stroke-linecap="round"/><circle cx="26" cy="26" r="1.8" fill="#DFB15B"/><defs><linearGradient id="goldRim" x1="0" y1="0" x2="52" y2="52" gradientUnits="userSpaceOnUse"><stop stop-color="#DFB15B" /><stop offset="0.5" stop-color="#FFF3C4" /><stop offset="1" stop-color="#B8860B" /></linearGradient><radialGradient id="crestCobaltGlow" cx="0.5" cy="0.5" r="0.5"><stop stop-color="#0052CC" stop-opacity="0.85"/><stop offset="1" stop-color="#0A0D15" stop-opacity="0"/></radialGradient></defs></svg>'

top_deck_html = f"""<div class="top-deck">
<div class="deck-brand">
<div class="club-crest">{crest_svg}</div>
<div class="deck-text">
<div class="deck-title-row">
<span class="deck-title">Upper Horton Sports Club</span>
{status_html}
</div>
<div class="deck-subtitle">The Heart of the Valley • Commercial & Financial Settlement Suite</div>
</div>
</div>
<div class="deck-meta">
<div class="meta-pill" style="border: 1px solid rgba(223, 177, 91, 0.4); background: rgba(223, 177, 91, 0.1);">
<span class="meta-label" style="color: #DFB15B;">Sign-In Profile</span>
<span class="meta-val" style="color: #FFFFFF; font-weight: 700;">{safe_full_name} ({safe_role})</span>
</div>
<div class="meta-pill" style="border: 1px solid rgba(223, 177, 91, 0.4); background: rgba(223, 177, 91, 0.08);">
<span class="meta-label" style="color: #DFB15B;">Report Cadence</span>
<span class="meta-val" style="color: #FFF3C4; font-weight: 700;">{cadence_badge}</span>
</div>
<div class="meta-pill">
<span class="meta-label">Trading Window</span>
<span class="meta-val">{start_date.strftime('%d %b %Y')} → {end_date.strftime('%d %b %Y')} ({num_days}d)</span>
</div>
<div class="meta-pill">
<span class="meta-label">Outlet Scope</span>
<span class="meta-val">{html.escape(str(loc_options[selected_loc_id]))}</span>
</div>
</div>
</div>"""

st.markdown(top_deck_html, unsafe_allow_html=True)

# -------------------------------------------------------------
# Quick Controls Bar (Direct Access & Synchronized with Sidebar)
# -------------------------------------------------------------
def on_main_preset_change():
    st.session_state["app_date_preset"] = st.session_state["main_quick_preset"]

def on_main_loc_change():
    st.session_state["app_selected_loc"] = st.session_state["main_quick_loc"]

q_c1, q_c2, q_c3 = st.columns([5, 4, 3])
with q_c1:
    st.markdown("<div style='font-size:0.72rem;font-weight:600;text-transform:uppercase;color:#94A3B8;letter-spacing:0.06em;margin-bottom:3px;'>⚡ Reporting Period Preset</div>", unsafe_allow_html=True)
    m_preset_idx = PRESET_OPTIONS.index(st.session_state["app_date_preset"]) if st.session_state["app_date_preset"] in PRESET_OPTIONS else 0
    st.selectbox(
        "Quick Period Scope",
        PRESET_OPTIONS,
        index=m_preset_idx,
        key="main_quick_preset",
        on_change=on_main_preset_change,
        label_visibility="collapsed"
    )

with q_c2:
    st.markdown("<div style='font-size:0.72rem;font-weight:600;text-transform:uppercase;color:#94A3B8;letter-spacing:0.06em;margin-bottom:3px;'>🏛️ Club Outlet / Register</div>", unsafe_allow_html=True)
    m_loc_idx = list(loc_options.keys()).index(st.session_state["app_selected_loc"]) if st.session_state["app_selected_loc"] in loc_options else 0
    st.selectbox(
        "Quick Outlet Scope",
        options=list(loc_options.keys()),
        index=m_loc_idx,
        format_func=lambda k: loc_options[k],
        key="main_quick_loc",
        on_change=on_main_loc_change,
        label_visibility="collapsed"
    )

with q_c3:
    st.markdown("<div style='font-size:0.72rem;font-weight:600;text-transform:uppercase;color:#94A3B8;letter-spacing:0.06em;margin-bottom:3px;'>🌙 Nightly Settlement Cadence</div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.32); border-radius: 8px; padding: 8px 12px; font-size: 0.78rem; color: #34D399; font-weight: 600; text-align: center;">
        🟢 Reconciled Daily @ 02:00 AM
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# -------------------------------------------------------------
# Executive Navigation Deck
# -------------------------------------------------------------
tab_board, tab_bar, tab_kitchen, tab_dept, tab_reconcile, tab_velocity, tab_items, tab_admin, tab_settings = st.tabs([
    "🏛️ Executive Boardroom",
    "🍺 Bar & Cellar Operations",
    "🍳 Bistro & Kitchen",
    "🍻 Department Margins",
    "⚖️ Financial Settlement & Xero",
    "⏰ Trading Velocity (12pm–12am)",
    "📦 Catalog & Movement",
    "👥 Board & Staff Governance",
    "⚙️ Settings & Homelab"
])

BOARD_FINANCE_ROLES = {"Super Admin", "Board Member (Full Read)", "Committee Member", "Treasurer", "Viewer / Auditor"}
user_role = current_user.get("role", "Committee Member")

# -------------------------------------------------------------
# TAB 1: Executive Boardroom Overview
# -------------------------------------------------------------
with tab_board:
    if user_role not in BOARD_FINANCE_ROLES:
        st.info("🔒 **Operational Role Scope:** Your account is scoped to Bar, Kitchen, Velocity, and Catalog operations. Please select the **🍺 Bar & Cellar Operations** or **🍳 Bistro & Kitchen** tabs above.")
        kpis = db.get_kpis(start_str, end_str, location_id=selected_loc_id)
    else:
        kpis = db.get_kpis(start_str, end_str, location_id=selected_loc_id)
    daily_gross = kpis.get("gross_sales", 0) / max(1, num_days)
    daily_net = kpis.get("net_sales", 0) / max(1, num_days)
    daily_orders = kpis.get("total_orders", 0) / max(1, num_days)

    # 5 Luxury KPI Cards with Hairstyle Borders & Tabular Typography
    c1, c2, c3, c4, c5 = st.columns(5)
    
    with c1:
        pop_pill = ""
        if kpis.get("net_sales_pop_pct") is not None:
            pct = kpis["net_sales_pop_pct"]
            pop_pill = f"<span class='trend-pill-pos' title='vs Prior Consecutive Window'>PoP ↑ +{pct}%</span>" if pct >= 0 else f"<span class='trend-pill-neg' title='vs Prior Consecutive Window'>PoP ↓ {pct}%</span>"
        else:
            pop_pill = "<span class='trend-pill-pos'>Active</span>"

        yoy_pill = ""
        if kpis.get("yoy_sales_pct") is not None:
            pct_y = kpis["yoy_sales_pct"]
            yoy_pill = f"<span class='trend-pill-pos' title='vs Same Window Last Year'>YoY ↑ +{pct_y}%</span>" if pct_y >= 0 else f"<span class='trend-pill-neg' title='vs Same Window Last Year'>YoY ↓ {pct_y}%</span>"
        else:
            yoy_pill = "<span class='trend-pill-pos' style='background:rgba(255,255,255,0.06);color:#94A3B8;border-color:rgba(255,255,255,0.1);'>YoY —</span>"

        st.markdown(f"""
        <div class="kpi-card kpi-hero-card">
            <div class="hero-flag">SOVEREIGN METRIC</div>
            <div class="kpi-label">
                <span style="color: #FFF3C4;">Net Sales Takings</span>
                <span class="micro-code-pill" style="color: #DFB15B; border-color: rgba(223, 177, 91, 0.35); background: rgba(223, 177, 91, 0.12);">NET</span>
            </div>
            <div class="kpi-value">${kpis.get('net_sales', 0):,.2f}</div>
            <div class="kpi-footer" style="display:flex; justify-content:space-between; align-items:center;">
                <div style="display:flex; gap:4px;">{pop_pill} {yoy_pill}</div>
                <span style="color: #E2E8F0;"><strong>${daily_net:,.2f}/d</strong></span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-accent-bar" style="background: {COLOR_COBALT};"></div>
            <div class="kpi-label">
                <span>Gross POS Revenue</span>
                <span class="micro-code-pill">GROSS</span>
            </div>
            <div class="kpi-value">${kpis.get('gross_sales', 0):,.2f}</div>
            <div class="kpi-footer">
                <span>Pre-discount • <strong>${daily_gross:,.2f}/d avg</strong></span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        pop_orders = ""
        if kpis.get("orders_pop_pct") is not None:
            pct_o = kpis["orders_pop_pct"]
            pop_orders = f"<span class='trend-pill-pos' title='vs Prior Consecutive Window'>PoP ↑ +{pct_o}%</span>" if pct_o >= 0 else f"<span class='trend-pill-neg' title='vs Prior Consecutive Window'>PoP ↓ {pct_o}%</span>"
        else:
            pop_orders = "<span class='trend-pill-pos'>Stable</span>"

        yoy_orders_pill = ""
        if kpis.get("yoy_orders_pct") is not None:
            pct_yo = kpis["yoy_orders_pct"]
            yoy_orders_pill = f"<span class='trend-pill-pos' title='vs Same Window Last Year'>YoY ↑ +{pct_yo}%</span>" if pct_yo >= 0 else f"<span class='trend-pill-neg' title='vs Same Window Last Year'>YoY ↓ {pct_yo}%</span>"
        else:
            yoy_orders_pill = "<span class='trend-pill-pos' style='background:rgba(255,255,255,0.06);color:#94A3B8;border-color:rgba(255,255,255,0.1);'>YoY —</span>"

        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-accent-bar" style="background: {COLOR_PLATINUM};"></div>
            <div class="kpi-label">
                <span>Total Transactions</span>
                <span class="micro-code-pill">TXNS</span>
            </div>
            <div class="kpi-value">{kpis.get('total_orders', 0):,}</div>
            <div class="kpi-footer" style="display:flex; justify-content:space-between; align-items:center;">
                <div style="display:flex; gap:4px;">{pop_orders} {yoy_orders_pill}</div>
                <span><strong>~{daily_orders:.0f} orders/d</strong></span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-accent-bar" style="background: {COLOR_JADE};"></div>
            <div class="kpi-label">
                <span>Avg Basket (AOV)</span>
                <span class="micro-code-pill" style="color: #34D399; border-color: rgba(16, 185, 129, 0.25);">BASKET</span>
            </div>
            <div class="kpi-value">${kpis.get('avg_order_value', 0):,.2f}</div>
            <div class="kpi-footer">
                <span>Mean patron spend per ticket</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c5:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-accent-bar" style="background: {COLOR_AMBER};"></div>
            <div class="kpi-label">
                <span>Member Comps & Promo</span>
                <span class="micro-code-pill" style="color: #FBBF24; border-color: rgba(245, 158, 11, 0.25);">COMPS</span>
            </div>
            <div class="kpi-value" style="color: #FBBF24;">${kpis.get('total_discounts', 0):,.2f}</div>
            <div class="kpi-footer">
                <span>Loss prevention & member rewards</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    # Dual-Axis Trading Trend & Outlet Donut
    col_chart1, col_chart2 = st.columns([7, 4])
    
    with col_chart1:
        st.markdown("<h4 style='margin-bottom: 12px;'>📈 Revenue Progression & Patron Velocity</h4>", unsafe_allow_html=True)
        df_trend = db.get_sales_timeseries(start_str, end_str, freq="D", location_id=selected_loc_id)
        
        if not df_trend.empty:
            fig_trend = go.Figure()
            # Net Takings Bar
            fig_trend.add_trace(go.Bar(
                x=df_trend["period"],
                y=df_trend["net_sales"],
                name="Net Takings ($ AUD)",
                marker=dict(
                    color="rgba(0, 82, 204, 0.76)",
                    line=dict(color="#2563EB", width=1.2),
                    cornerradius=4
                ),
                hovertemplate="<b>%{x}</b><br>Net Takings: <b style='color:#60A5FA;'>$%{y:,.2f} AUD</b><extra></extra>"
            ))
            # Transactions Spline with Ambient Gold Fill
            fig_trend.add_trace(go.Scatter(
                x=df_trend["period"],
                y=df_trend["order_count"],
                name="Patron Transactions",
                yaxis="y2",
                mode="lines+markers",
                line=dict(color=COLOR_GOLD, width=2.6, shape="spline"),
                fill="tozeroy",
                fillcolor="rgba(223, 177, 91, 0.035)",
                marker=dict(size=6, color=COLOR_GOLD, symbol="circle", line=dict(color="#06080E", width=1.5)),
                hovertemplate="Orders: <b style='color:#DFB15B;'>%{y} tickets</b><extra></extra>"
            ))
            # Daily Average Pacing Reference Line
            avg_daily_line = float(df_trend["net_sales"].mean()) if len(df_trend) > 1 else 0.0
            if avg_daily_line > 0:
                fig_trend.add_hline(
                    y=avg_daily_line,
                    line_dash="dot",
                    line_color="rgba(223, 177, 91, 0.42)",
                    annotation_text=f"Window Daily Mean: ${avg_daily_line:,.0f}",
                    annotation_position="top left",
                    annotation_font=dict(color="#DFB15B", size=10, family="Inter")
                )
            fig_trend.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94A3B8", family="Inter, sans-serif"),
                xaxis=dict(
                    showgrid=False,
                    linecolor="rgba(255,255,255,0.08)",
                    tickfont=dict(color="#94A3B8", size=11)
                ),
                yaxis=dict(
                    title=dict(text="Net Takings ($ AUD)", font=dict(color="#94A3B8", size=11)),
                    gridcolor="rgba(255,255,255,0.045)",
                    zerolinecolor="rgba(255,255,255,0.08)",
                    tickprefix="$",
                    tickformat=",.0f",
                    tickfont=dict(color="#94A3B8", size=11)
                ),
                yaxis2=dict(
                    title=dict(text="Order Volume", font=dict(color=COLOR_GOLD, size=11)),
                    overlaying="y",
                    side="right",
                    showgrid=False,
                    tickfont=dict(color=COLOR_GOLD, size=11)
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.04,
                    xanchor="right",
                    x=1,
                    font=dict(size=11, color="#CBD5E1")
                ),
                height=310,
                margin=dict(l=10, r=10, t=30, b=20),
                hovermode="x unified",
                hoverlabel=dict(
                    bgcolor="#0C101A",
                    bordercolor="rgba(223, 177, 91, 0.38)",
                    font=dict(family="Inter, sans-serif", size=12, color="#FFFFFF")
                )
            )
            st.plotly_chart(fig_trend, use_container_width=True, config={'displayModeBar': False, 'responsive': True})
        else:
            st.info("No trading records found in this window.")

    with col_chart2:
        st.markdown("<h4 style='margin-bottom: 12px;'>🥧 Department Takings Share</h4>", unsafe_allow_html=True)
        df_dept = db.get_department_breakdown(start_str, end_str, location_id=selected_loc_id)
        if not df_dept.empty:
            total_rev = df_dept["net_sales"].sum()
            fig_pie = go.Figure(data=[go.Pie(
                labels=df_dept["category"],
                values=df_dept["net_sales"],
                hole=0.68,
                marker=dict(
                    colors=LUXURY_PALETTE,
                    line=dict(color="#06080E", width=2)
                ),
                textinfo='percent',
                textfont=dict(family="Plus Jakarta Sans, sans-serif", size=12, color="#FFFFFF"),
                hovertemplate="<b>%{label}</b><br>Takings: $%{value:,.2f}<br>Share: %{percent}<extra></extra>"
            )])
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94A3B8", family="Inter, sans-serif"),
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=-0.1,
                    xanchor="center",
                    x=0.5,
                    font=dict(size=11, color="#CBD5E1")
                ),
                height=300,
                margin=dict(l=10, r=10, t=10, b=45),
                annotations=[dict(
                    text=f"<span style='font-size:10px;color:#94A3B8;letter-spacing:0.08em;text-transform:uppercase;'>TOTAL TAKINGS</span><br><b style='font-size:17px;color:#FFFFFF;font-family:Plus Jakarta Sans;'>${total_rev:,.0f}</b>",
                    x=0.5, y=0.5, font_size=13, showarrow=False
                )],
                hoverlabel=dict(
                    bgcolor="#0C101A",
                    bordercolor="rgba(255,255,255,0.12)",
                    font=dict(family="Inter, sans-serif", size=12, color="#FFFFFF")
                )
            )
            st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False, 'responsive': True})
        else:
            st.info("No departmental data recorded.")

    # -------------------------------------------------------------
    # Month-to-Date (MTD) Dual Comparative Analysis (MoM & YoY)
    # -------------------------------------------------------------
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 24px; margin-bottom: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 8px;">
            <div>
                <h4 style="margin: 0; color: #FFFFFF;">📊 Month-to-Date (MTD) Performance vs. Last Month & Prior Year</h4>
                <p style="margin: 4px 0 0 0; font-size: 0.84rem; color: #94A3B8;">Executive tracking of current month velocity against equivalent trading days in the prior month and prior year.</p>
            </div>
            <div>
                <span style="background: rgba(223, 177, 91, 0.12); color: #DFB15B; border: 1px solid rgba(223, 177, 91, 0.3); padding: 4px 12px; border-radius: 20px; font-size: 0.78rem; font-weight: 600;">
                    MTD Tracking Benchmark
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    mtd_data = db.get_mtd_comparative_analysis(location_id=selected_loc_id)
    
    # 3 Comparative Metric Cards: Current MTD vs Last Month (MoM) vs Same Month Last Year (YoY)
    col_mtd1, col_mtd2, col_mtd3 = st.columns(3)
    
    with col_mtd1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-accent-bar" style="background: {COLOR_GOLD};"></div>
            <div class="kpi-label">
                <span>1. Current Month-to-Date ({mtd_data['current_month_name'][:3]})</span>
                <span>📅</span>
            </div>
            <div class="kpi-value">${mtd_data['curr_mtd']['net_sales']:,.2f}</div>
            <div class="kpi-footer">
                <span class="tabular-nums">{mtd_data['curr_mtd']['total_orders']:,} orders closed</span>
                <span>• Day 1 → {mtd_data['current_day']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_mtd2:
        mom_pill = ""
        if mtd_data.get("mom_sales_pct") is not None:
            pct = mtd_data["mom_sales_pct"]
            mom_pill = f"<span class='trend-pill-pos'>↑ +{pct}%</span>" if pct >= 0 else f"<span class='trend-pill-neg'>↓ {pct}%</span>"
        else:
            mom_pill = "<span>N/A</span>"

        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-accent-bar" style="background: {COLOR_COBALT};"></div>
            <div class="kpi-label">
                <span>2. vs Prior Month ({mtd_data['prior_month_name'][:3]})</span>
                <span>⏮️</span>
            </div>
            <div class="kpi-value">${mtd_data['prior_mo_comp']['net_sales']:,.2f}</div>
            <div class="kpi-footer">
                {mom_pill}
                <span>MoM pace • Full: ${mtd_data['prior_mo_full']['net_sales']:,.0f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_mtd3:
        yoy_pill = ""
        if mtd_data.get("yoy_sales_pct") is not None:
            pct_y = mtd_data["yoy_sales_pct"]
            yoy_pill = f"<span class='trend-pill-pos'>↑ +{pct_y}%</span>" if pct_y >= 0 else f"<span class='trend-pill-neg'>↓ {pct_y}%</span>"
        else:
            yoy_pill = "<span>N/A</span>"

        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-accent-bar" style="background: {COLOR_JADE};"></div>
            <div class="kpi-label">
                <span>3. vs Prior Year ({mtd_data['last_year_month_name'][:3]} {mtd_data['last_year_month_name'][-4:]})</span>
                <span>🗓️</span>
            </div>
            <div class="kpi-value">${mtd_data['last_yr_comp']['net_sales']:,.2f}</div>
            <div class="kpi-footer">
                {yoy_pill}
                <span>YoY pace • Full: ${mtd_data['last_yr_full']['net_sales']:,.0f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Dual Comparative Pacing: MTD Intra-Month Velocity & 2026 Year-to-Date Performance
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    col_chart_mtd, col_chart_ytd = st.columns([1, 1])

    with col_chart_mtd:
        df_cum = mtd_data.get("df_cumulative")
        if df_cum is not None and not df_cum.empty:
            fig_cum = go.Figure()

            # Same Month Last Year (Silver Dotted)
            fig_cum.add_trace(go.Scatter(
                x=df_cum["day_num"],
                y=df_cum["same_month_last_year_cum"],
                name=f"Prior Year ({mtd_data['last_year_month_name'][:3]})",
                mode="lines",
                line=dict(color="#64748B", width=2, dash="dot"),
                hovertemplate="Prior Year: <b>$%{y:,.2f}</b><extra></extra>"
            ))

            # Prior Month (Cobalt Dashed)
            fig_cum.add_trace(go.Scatter(
                x=df_cum["day_num"],
                y=df_cum["prior_month_cum"],
                name=f"Prior Month ({mtd_data['prior_month_name'][:3]})",
                mode="lines",
                line=dict(color="#3B82F6", width=2.2, dash="dash"),
                hovertemplate="Prior Month: <b>$%{y:,.2f}</b><extra></extra>"
            ))

            # Current Month (Champagne Gold Solid + Soft Glow)
            fig_cum.add_trace(go.Scatter(
                x=df_cum["day_num"],
                y=df_cum["current_month_cum"],
                name=f"Current MTD ({mtd_data['current_month_name'][:3]})",
                mode="lines+markers",
                line=dict(color=COLOR_GOLD, width=3.2),
                marker=dict(size=6, color=COLOR_GOLD, symbol="circle"),
                fill="tozeroy",
                fillcolor="rgba(223, 177, 91, 0.08)",
                hovertemplate="Current MTD: <b>$%{y:,.2f}</b><extra></extra>"
            ))

            fig_cum.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94A3B8", family="Inter, sans-serif"),
                title=dict(
                    text="📈 MTD Velocity Pace (Day 1 → Day 31)",
                    font=dict(color="#FFFFFF", size=13, family="Plus Jakarta Sans")
                ),
                height=310,
                xaxis=dict(
                    title=dict(text="Day of Month", font=dict(color="#94A3B8", size=10)),
                    showgrid=False,
                    linecolor="rgba(255,255,255,0.08)",
                    tickmode="linear",
                    tick0=1,
                    dtick=3,
                    tickfont=dict(color="#94A3B8", size=10)
                ),
                yaxis=dict(
                    title=dict(text="Cumulative Takings ($ AUD)", font=dict(color="#94A3B8", size=10)),
                    gridcolor="rgba(255,255,255,0.05)",
                    zerolinecolor="rgba(255,255,255,0.08)",
                    tickprefix="$",
                    tickformat=",.0f",
                    tickfont=dict(color="#94A3B8", size=10)
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.04,
                    xanchor="right",
                    x=1,
                    font=dict(size=10, color="#CBD5E1")
                ),
                margin=dict(l=10, r=10, t=38, b=25),
                hovermode="x unified",
                hoverlabel=dict(
                    bgcolor="#0C101A",
                    bordercolor="rgba(255,255,255,0.12)",
                    font=dict(family="Inter, sans-serif", size=11, color="#FFFFFF")
                )
            )
            st.plotly_chart(fig_cum, use_container_width=True, config={'displayModeBar': False, 'responsive': True})

    with col_chart_ytd:
        ytd_data = db.get_ytd_performance(location_id=selected_loc_id)
        df_ytd = ytd_data.get("df_ytd")
        if df_ytd is not None and not df_ytd.empty:
            fig_ytd = go.Figure()

            # 2025 Monthly Net Takings (Muted baseline)
            fig_ytd.add_trace(go.Bar(
                x=df_ytd["month_label"],
                y=df_ytd["net_25"],
                name="2025 Monthly",
                marker=dict(
                    color="rgba(148, 163, 184, 0.35)",
                    line=dict(color="rgba(148, 163, 184, 0.6)", width=1),
                    cornerradius=3
                ),
                hovertemplate="2025 Monthly: <b>$%{y:,.2f} AUD</b><extra></extra>"
            ))

            # 2026 Monthly Net Takings (Electric Cobalt)
            fig_ytd.add_trace(go.Bar(
                x=df_ytd["month_label"],
                y=df_ytd["net_26"],
                name="2026 Monthly",
                marker=dict(
                    color="rgba(0, 82, 204, 0.78)",
                    line=dict(color="#0052CC", width=1.2),
                    cornerradius=3
                ),
                hovertemplate="2026 Monthly: <b>$%{y:,.2f} AUD</b><extra></extra>"
            ))

            # 2025 Cumulative YTD Pace (Silver Dashed)
            fig_ytd.add_trace(go.Scatter(
                x=df_ytd["month_label"],
                y=df_ytd["cum_net_2025"],
                name="2025 Cumul. Pace",
                yaxis="y2",
                mode="lines",
                line=dict(color="#94A3B8", width=1.8, dash="dash"),
                hovertemplate="2025 Cumulative: <b>$%{y:,.2f}</b><extra></extra>"
            ))

            # 2026 Cumulative YTD Pace (Champagne Gold Solid)
            fig_ytd.add_trace(go.Scatter(
                x=df_ytd["month_label"],
                y=df_ytd["cum_net_2026"],
                name="2026 Cumul. Pace",
                yaxis="y2",
                mode="lines+markers",
                line=dict(color=COLOR_GOLD, width=2.8, shape="spline"),
                marker=dict(size=6, color=COLOR_GOLD, symbol="circle", line=dict(color="#06080E", width=1.5)),
                hovertemplate="2026 Cumulative: <b>$%{y:,.2f}</b><extra></extra>"
            ))

            pct_lbl = f"(YoY: +{ytd_data['ytd_yoy_growth_pct']}%)" if ytd_data.get('ytd_yoy_growth_pct') is not None else ""
            fig_ytd.update_layout(
                barmode="group",
                bargap=0.25,
                bargroupgap=0.1,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94A3B8", family="Inter, sans-serif"),
                title=dict(
                    text=f"📅 Year-to-Date vs. 2025 Benchmark {pct_lbl}",
                    font=dict(color="#FFFFFF", size=13, family="Plus Jakarta Sans")
                ),
                height=310,
                xaxis=dict(
                    showgrid=False,
                    linecolor="rgba(255,255,255,0.08)",
                    tickfont=dict(color="#94A3B8", size=10)
                ),
                yaxis=dict(
                    title=dict(text="Monthly Net ($ AUD)", font=dict(color="#94A3B8", size=10)),
                    gridcolor="rgba(255,255,255,0.05)",
                    zerolinecolor="rgba(255,255,255,0.08)",
                    tickprefix="$",
                    tickformat=",.0f",
                    tickfont=dict(color="#94A3B8", size=10)
                ),
                yaxis2=dict(
                    title=dict(text="Cumulative YTD ($)", font=dict(color=COLOR_GOLD, size=10)),
                    overlaying="y",
                    side="right",
                    showgrid=False,
                    tickprefix="$",
                    tickformat=",.0f",
                    tickfont=dict(color=COLOR_GOLD, size=10)
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.04,
                    xanchor="right",
                    x=1,
                    font=dict(size=9.5, color="#CBD5E1")
                ),
                margin=dict(l=10, r=10, t=38, b=25),
                hovermode="x unified",
                hoverlabel=dict(
                    bgcolor="#0C101A",
                    bordercolor="rgba(255,255,255,0.12)",
                    font=dict(family="Inter, sans-serif", size=11, color="#FFFFFF")
                )
            )
            st.plotly_chart(fig_ytd, use_container_width=True, config={'displayModeBar': False, 'responsive': True})

            yoy_growth_str = f"↑ +{ytd_data['ytd_yoy_growth_pct']}% YoY Pace" if ytd_data.get('ytd_yoy_growth_pct', 0) >= 0 else f"↓ {ytd_data['ytd_yoy_growth_pct']}% YoY Pace"
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.06); border-radius:8px; padding:6px 12px; margin-top:4px; font-size:0.75rem; flex-wrap:wrap; gap:8px;">
                <div><span style="color:#94A3B8;">2026 YTD:</span> <strong style="color:#FFFFFF;">${ytd_data['ytd_net_2026']:,.2f}</strong> <span style="color:#64748B;">({ytd_data['ytd_orders_2026']:,} ord)</span></div>
                <div><span style="color:#94A3B8;">2025 YTD:</span> <strong style="color:#94A3B8;">${ytd_data['ytd_net_2025']:,.2f}</strong> <span style="color:#64748B;">({ytd_data['ytd_orders_2025']:,} ord)</span></div>
                <div><span style="color:#34D399; font-weight:700;">{yoy_growth_str}</span></div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No 2026 Year-to-Date data recorded.")

# -------------------------------------------------------------
# TAB 2: Bar & Cellar Operations (Bar Manager View)
# -------------------------------------------------------------
with tab_bar:
    st.markdown("<h3 style='margin-bottom: 4px;'>🍺 Bar & Cellar Operational Intelligence</h3>", unsafe_allow_html=True)
    st.caption("Bar Manager command center: stock depletion rates, keg and carton calculations, fastest movers, and dead stock watch.")

    bar_kpis = db.get_bar_manager_kpis(start_str, end_str, location_id=selected_loc_id)
    df_top_movers, df_dead_stock = db.get_bar_movement_matrix(start_str, end_str, location_id=selected_loc_id)

    # 4 Bar Cellar Pulse Cards
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-accent-bar" style="background: {COLOR_GOLD};"></div>
            <div class="kpi-label">
                <span>Total Bar Takings</span>
                <span>🍺</span>
            </div>
            <div class="kpi-value">${bar_kpis.get('total_bar_sales', 0):,.2f}</div>
            <div class="kpi-footer">
                <span class="tabular-nums">{bar_kpis.get('total_bar_units', 0):,.0f} total pours/drinks</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with b2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-accent-bar" style="background: {COLOR_AMBER};"></div>
            <div class="kpi-label">
                <span>Draught Beer Poured</span>
                <span>🛢️</span>
            </div>
            <div class="kpi-value">{bar_kpis.get('est_50l_kegs', 0):.1f} <span style="font-size:1.1rem;font-weight:500;color:#94A3B8;">50L Kegs</span></div>
            <div class="kpi-footer">
                <span class="tabular-nums">{bar_kpis.get('tap_units', 0):,.0f} schooners (~118 / keg)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with b3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-accent-bar" style="background: {COLOR_COBALT};"></div>
            <div class="kpi-label">
                <span>Packaged Beer & RTDs</span>
                <span>📦</span>
            </div>
            <div class="kpi-value">{bar_kpis.get('est_cartons', 0):.1f} <span style="font-size:1.1rem;font-weight:500;color:#94A3B8;">Cartons</span></div>
            <div class="kpi-footer">
                <span class="tabular-nums">{bar_kpis.get('packaged_units', 0):,.0f} cans & stubbies (24-pk)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with b4:
        tap_pct = bar_kpis.get('tap_ratio_pct', 0)
        pack_pct = bar_kpis.get('packaged_ratio_pct', 0)
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-accent-bar" style="background: {COLOR_JADE};"></div>
            <div class="kpi-label">
                <span>Draught vs Packaged Ratio</span>
                <span>⚖️</span>
            </div>
            <div class="kpi-value">{tap_pct:.0f}% <span style="font-size:1.1rem;font-weight:400;color:#94A3B8;">Tap /</span> {pack_pct:.0f}% <span style="font-size:1.1rem;font-weight:400;color:#94A3B8;">Pk</span></div>
            <div class="kpi-footer">
                <span>Volume ratio split</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    # What's Selling (Top Movers) vs What's NOT Selling (Dead Stock)
    col_selling, col_notselling = st.columns([1, 1])

    with col_selling:
        st.markdown("""
        <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.28); border-radius: 12px; padding: 14px 18px; margin-bottom: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h4 style="margin: 0; color: #10B981;">🔥 What's Selling (High Velocity Leaders)</h4>
                <span style="font-size: 0.76rem; color: #A7F3D0; background: rgba(16, 185, 129, 0.2); padding: 3px 10px; border-radius: 14px; font-weight: 600;">Reorder Priority</span>
            </div>
            <p style="margin: 4px 0 0 0; font-size: 0.8rem; color: #94A3B8;">Fastest depleting lines. Ensure backup kegs and cartons are chilling prior to Friday night.</p>
        </div>
        """, unsafe_allow_html=True)

        if not df_top_movers.empty:
            fig_top_bar = go.Figure(go.Bar(
                x=df_top_movers.head(8)["units_sold"],
                y=df_top_movers.head(8)["item_name"],
                orientation="h",
                marker=dict(
                    color="rgba(16, 185, 129, 0.75)",
                    line=dict(color="#10B981", width=1.2),
                    cornerradius=4
                ),
                text=df_top_movers.head(8)["units_sold"].apply(lambda u: f"{u:.0f} units"),
                textposition="outside",
                textfont=dict(color="#CBD5E1", size=10, family="Plus Jakarta Sans"),
                hovertemplate="<b>%{y}</b><br>Volume: <b>%{x:.0f} units sold</b><extra></extra>"
            ))
            fig_top_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94A3B8", family="Inter, sans-serif"),
                xaxis=dict(showgrid=False, linecolor="rgba(255,255,255,0.08)", title="Units Sold"),
                yaxis=dict(showgrid=False, autorange="reversed"),
                height=340,
                margin=dict(l=10, r=45, t=10, b=30)
            )
            st.plotly_chart(fig_top_bar, use_container_width=True, config={'displayModeBar': False, 'responsive': True})

            st.dataframe(
                df_top_movers[["item_name", "category", "units_sold", "net_revenue", "avg_unit_price"]].rename(columns={
                    "item_name": "Product",
                    "category": "Category",
                    "units_sold": "Units Sold",
                    "net_revenue": "Net Sales ($)",
                    "avg_unit_price": "Avg Price ($)"
                }).style.format({
                    "Units Sold": "{:,.0f}",
                    "Net Sales ($)": "${:,.2f}",
                    "Avg Price ($)": "${:,.2f}"
                }),
                use_container_width=True
            )
        else:
            st.info("No bar sales recorded for this period.")

    with col_notselling:
        st.markdown("""
        <div style="background: rgba(244, 63, 94, 0.08); border: 1px solid rgba(244, 63, 94, 0.28); border-radius: 12px; padding: 14px 18px; margin-bottom: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h4 style="margin: 0; color: #F43F5E;">🛑 What's NOT Selling (6-Month Dead Stock Audit)</h4>
                <span style="font-size: 0.76rem; color: #FECDD3; background: rgba(244, 63, 94, 0.2); padding: 3px 10px; border-radius: 14px; font-weight: 600;">180-Day Window</span>
            </div>
            <p style="margin: 4px 0 0 0; font-size: 0.8rem; color: #94A3B8;">Bar lines with ≤12 units sold over the past 6 months (May → Oct 2026). Cash tied up in slow-moving cool room stock.</p>
        </div>
        """, unsafe_allow_html=True)

        if not df_dead_stock.empty:
            fig_dead = go.Figure(go.Bar(
                x=df_dead_stock["units_sold"],
                y=df_dead_stock["item_name"],
                orientation="h",
                marker=dict(
                    color="rgba(244, 63, 94, 0.75)",
                    line=dict(color="#F43F5E", width=1.2),
                    cornerradius=4
                ),
                text=df_dead_stock.apply(lambda r: f"{r['units_sold']:.0f} in 6mo (last: {r['last_sold_str']})", axis=1),
                textposition="outside",
                textfont=dict(color="#CBD5E1", size=10, family="Plus Jakarta Sans"),
                hovertemplate="<b>%{y}</b><br>6-Mo Volume: <b>%{x:.0f} units</b><extra></extra>"
            ))
            fig_dead.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94A3B8", family="Inter, sans-serif"),
                xaxis=dict(showgrid=False, linecolor="rgba(255,255,255,0.08)", title="Units Sold in 6 Months"),
                yaxis=dict(showgrid=False, autorange="reversed"),
                height=340,
                margin=dict(l=10, r=45, t=10, b=30)
            )
            st.plotly_chart(fig_dead, use_container_width=True, config={'displayModeBar': False, 'responsive': True})

            st.dataframe(
                df_dead_stock[["item_name", "category", "units_sold", "net_revenue", "last_sold_str", "recommendation"]].rename(columns={
                    "item_name": "Slow-Moving Product",
                    "category": "Category",
                    "units_sold": "6-Mo Units",
                    "net_revenue": "6-Mo Takings ($)",
                    "last_sold_str": "Last Sold Date",
                    "recommendation": "Manager Action"
                }).style.format({
                    "6-Mo Units": "{:,.0f}",
                    "6-Mo Takings ($)": "${:,.2f}"
                }),
                use_container_width=True
            )
        else:
            st.success("✨ All bar catalog items are currently active and moving!")

    # Shift Day-of-Week Beverage Mix
    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
    st.markdown("<h4 style='margin-bottom: 8px;'>📅 Shift Beverage Preferences by Day of Week</h4>", unsafe_allow_html=True)
    st.caption("Pours across Friday Night Raffles, Saturday Sport, and Sunday Sessions to guide pre-chilling.")

    df_shift = db.get_bar_shift_category_mix(start_str, end_str, location_id=selected_loc_id)
    if not df_shift.empty:
        days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        fig_shift = px.bar(
            df_shift,
            x="day_name",
            y="units_sold",
            color="category",
            barmode="group",
            category_orders={"day_name": days_order},
            color_discrete_sequence=[COLOR_GOLD, COLOR_COBALT, COLOR_PLATINUM, COLOR_AMBER],
            labels={"day_name": "Day of Week", "units_sold": "Drinks Sold", "category": "Bar Category"}
        )
        fig_shift.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94A3B8", family="Inter, sans-serif"),
            xaxis=dict(showgrid=False, linecolor="rgba(255,255,255,0.08)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="Units Poured"),
            legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="right", x=1),
            margin=dict(l=10, r=10, t=30, b=25)
        )
        st.plotly_chart(fig_shift, use_container_width=True, config={'displayModeBar': False, 'responsive': True})

# -------------------------------------------------------------
# TAB: Bistro & Kitchen Commercial Operations
# -------------------------------------------------------------
with tab_kitchen:
    st.markdown("<h3 style='margin-bottom: 4px;'>🍳 Bistro & Kitchen Commercial Operations</h3>", unsafe_allow_html=True)
    st.caption("Kitchen operations command center: covers served, food check averages, service window velocity (Lunch vs Dinner), and menu item demand.")

    k_kpis = db.get_kitchen_kpis(start_str, end_str, location_id=selected_loc_id)
    df_dishes, df_courses = db.get_kitchen_movement_matrix(start_str, end_str, location_id=selected_loc_id)

    # 4 Kitchen Operations Cards
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-accent-bar" style="background: {COLOR_GOLD};"></div>
            <div class="kpi-label">
                <span>Total Kitchen Takings</span>
                <span>🍽️</span>
            </div>
            <div class="kpi-value">${k_kpis.get('total_kitchen_revenue', 0):,.2f}</div>
            <div class="kpi-footer">
                <span class="tabular-nums">{k_kpis.get('total_food_items', 0):,.0f} total food items prepared</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with k2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-accent-bar" style="background: {COLOR_JADE};"></div>
            <div class="kpi-label">
                <span>Main Meals Served</span>
                <span>🥩</span>
            </div>
            <div class="kpi-value">{k_kpis.get('meals_served', 0):,.0f} <span style="font-size:1.1rem;font-weight:500;color:#94A3B8;">Plates</span></div>
            <div class="kpi-footer">
                <span class="tabular-nums">Avg ~${k_kpis.get('avg_meal_price', 0):,.2f} yield per main meal</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with k3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-accent-bar" style="background: {COLOR_COBALT};"></div>
            <div class="kpi-label">
                <span>Average Dining Check</span>
                <span>🧾</span>
            </div>
            <div class="kpi-value">${k_kpis.get('avg_check', 0):,.2f}</div>
            <div class="kpi-footer">
                <span class="tabular-nums">Across {k_kpis.get('food_orders_count', 0):,.0f} dining tickets</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with k4:
        din_pct = k_kpis.get('dinner_pct', 0)
        lun_pct = k_kpis.get('lunch_pct', 0)
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-accent-bar" style="background: {COLOR_AMBER};"></div>
            <div class="kpi-label">
                <span>Service Split (Dinner vs Lunch)</span>
                <span>🌓</span>
            </div>
            <div class="kpi-value">{din_pct:.0f}% <span style="font-size:1.1rem;font-weight:400;color:#94A3B8;">Din /</span> {lun_pct:.0f}% <span style="font-size:1.1rem;font-weight:400;color:#94A3B8;">Lun</span></div>
            <div class="kpi-footer">
                <span>${k_kpis.get('dinner_sales', 0):,.0f} Dinner / ${k_kpis.get('lunch_sales', 0):,.0f} Lunch</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    # Dish Popularity Leaderboard and Course Breakdown
    col_dishes, col_courses = st.columns([1.2, 0.8])

    with col_dishes:
        st.markdown("""
        <div style="background: rgba(0, 82, 204, 0.08); border: 1px solid rgba(0, 82, 204, 0.3); border-radius: 12px; padding: 14px 18px; margin-bottom: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h4 style="margin: 0; color: #60A5FA;">🏆 Top Kitchen Sellers (Volume & Takings)</h4>
                <span style="font-size: 0.76rem; color: #93C5FD; background: rgba(0, 82, 204, 0.25); padding: 3px 10px; border-radius: 14px; font-weight: 600;">Menu Popularity</span>
            </div>
            <p style="margin: 4px 0 0 0; font-size: 0.8rem; color: #94A3B8;">Highest demand kitchen items by plates prepared and revenue contributed.</p>
        </div>
        """, unsafe_allow_html=True)

        if not df_dishes.empty:
            top_10 = df_dishes.head(10)
            fig_dishes = go.Figure(go.Bar(
                x=top_10["qty_sold"],
                y=top_10["dish_name"],
                orientation='h',
                marker=dict(
                    color=top_10["net_revenue"],
                    colorscale=[[0, '#0052CC'], [1, '#DFB15B']],
                    line=dict(color='rgba(255,255,255,0.2)', width=1)
                ),
                text=[f"${r:,.0f} ({int(q)} orders)" for r, q in zip(top_10["net_revenue"], top_10["qty_sold"])],
                textposition='inside',
                insidetextfont=dict(color='#FFFFFF', size=11, family='Inter, sans-serif')
            ))
            fig_dishes.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=10, b=10),
                height=340,
                xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", tickfont=dict(color="#94A3B8"), title="Plates Prepared"),
                yaxis=dict(autorange="reversed", tickfont=dict(color="#CBD5E1", size=12)),
            )
            st.plotly_chart(fig_dishes, use_container_width=True, config={'displayModeBar': False, 'responsive': True})

            # Dish Data Table
            st.dataframe(
                df_dishes.head(15)[["dish_name", "course_type", "qty_sold", "net_revenue", "avg_price", "revenue_share_pct"]].rename(columns={
                    "dish_name": "Menu Item",
                    "course_type": "Category",
                    "qty_sold": "Plates Sold",
                    "net_revenue": "Net Sales ($)",
                    "avg_price": "Avg Price ($)",
                    "revenue_share_pct": "Share (%)"
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No kitchen orders in this period.")

    with col_courses:
        st.markdown("""
        <div style="background: rgba(223, 177, 91, 0.08); border: 1px solid rgba(223, 177, 91, 0.3); border-radius: 12px; padding: 14px 18px; margin-bottom: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h4 style="margin: 0; color: #DFB15B;">🍽️ Menu Category Breakdown</h4>
                <span style="font-size: 0.76rem; color: #FFF3C4; background: rgba(223, 177, 91, 0.25); padding: 3px 10px; border-radius: 14px; font-weight: 600;">Course Share</span>
            </div>
            <p style="margin: 4px 0 0 0; font-size: 0.8rem; color: #94A3B8;">Sales distribution across steaks, schnitzels, pizzas, burgers, seafood, and specials.</p>
        </div>
        """, unsafe_allow_html=True)

        if not df_courses.empty:
            fig_courses = px.pie(
                df_courses,
                names="course_type",
                values="revenue",
                color_discrete_sequence=['#DFB15B', '#0052CC', '#10B981', '#F59E0B', '#60A5FA', '#EC4899', '#8B5CF6', '#64748B'],
                hole=0.45
            )
            fig_courses.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=10, b=10),
                height=340,
                legend=dict(font=dict(color="#CBD5E1", size=11), orientation="v")
            )
            st.plotly_chart(fig_courses, use_container_width=True, config={'displayModeBar': False, 'responsive': True})

            # Summary Table
            st.dataframe(
                df_courses.rename(columns={
                    "course_type": "Course",
                    "dishes_sold": "Dishes",
                    "revenue": "Takings ($)",
                    "revenue_pct": "Share (%)"
                }),
                use_container_width=True,
                hide_index=True
            )

# -------------------------------------------------------------
# TAB 3: Revenue & Department Margin Deep Dive
# -------------------------------------------------------------
with tab_dept:
    st.markdown("<h3 style='margin-bottom: 4px;'>🍻 Outlet & Department Commercial Performance</h3>", unsafe_allow_html=True)
    st.caption("Detailed departmental contribution across Bar, Bistro / Dining, Merchandise, and Club Raffles.")

    df_dept = db.get_department_breakdown(start_str, end_str, location_id=selected_loc_id)

    if not df_dept.empty:
        c_d1, c_d2 = st.columns([3, 2])
        with c_d1:
            st.markdown("<h4 style='margin-bottom: 8px;'>Net Sales Contribution by Department</h4>", unsafe_allow_html=True)
            df_dept_sorted = df_dept.sort_values("net_sales", ascending=True)
            fig_hbar = go.Figure(go.Bar(
                x=df_dept_sorted["net_sales"],
                y=df_dept_sorted["category"],
                orientation="h",
                marker=dict(
                    color=df_dept_sorted["net_sales"],
                    colorscale=[[0, "rgba(0, 82, 204, 0.7)"], [1, "rgba(223, 177, 91, 0.9)"]],
                    cornerradius=4
                ),
                text=[f"${v:,.2f}" for v in df_dept_sorted["net_sales"]],
                textposition="outside",
                textfont=dict(family="Plus Jakarta Sans, sans-serif", size=11, color="#F8FAFC"),
                hovertemplate="<b>%{y}</b><br>Net Takings: <b>$%{x:,.2f}</b><extra></extra>"
            ))
            fig_hbar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94A3B8", family="Inter, sans-serif"),
                xaxis=dict(
                    title=dict(text="Net Revenue ($ AUD)", font=dict(color="#94A3B8", size=11)),
                    gridcolor="rgba(255,255,255,0.05)",
                    zerolinecolor="rgba(255,255,255,0.08)",
                    tickprefix="$",
                    tickformat=",.0f"
                ),
                yaxis=dict(title="", tickfont=dict(color="#CBD5E1", size=12)),
                showlegend=False,
                height=290,
                margin=dict(l=10, r=40, t=20, b=20),
                hoverlabel=dict(
                    bgcolor="#0C101A",
                    bordercolor="rgba(255,255,255,0.12)",
                    font=dict(family="Inter, sans-serif", size=12, color="#FFFFFF")
                )
            )
            st.plotly_chart(fig_hbar, use_container_width=True, config={'displayModeBar': False, 'responsive': True})

        with c_d2:
            st.markdown("<h4 style='margin-bottom: 8px;'>Inventory Units Depleted</h4>", unsafe_allow_html=True)
            df_units_sorted = df_dept.sort_values("units_sold", ascending=True)
            fig_units = go.Figure(go.Bar(
                x=df_units_sorted["units_sold"],
                y=df_units_sorted["category"],
                orientation="h",
                marker=dict(
                    color="rgba(223, 177, 91, 0.75)",
                    line=dict(color=COLOR_GOLD, width=1),
                    cornerradius=4
                ),
                text=[f"{int(u):,} units" for u in df_units_sorted["units_sold"]],
                textposition="outside",
                textfont=dict(family="Plus Jakarta Sans, sans-serif", size=11, color="#F8FAFC"),
                hovertemplate="<b>%{y}</b><br>Depleted Volume: <b>%{x:,.0f} units</b><extra></extra>"
            ))
            fig_units.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94A3B8", family="Inter, sans-serif"),
                xaxis=dict(
                    title=dict(text="Volume (Units Depleted)", font=dict(color="#94A3B8", size=11)),
                    gridcolor="rgba(255,255,255,0.05)",
                    zerolinecolor="rgba(255,255,255,0.08)"
                ),
                yaxis=dict(title="", tickfont=dict(color="#CBD5E1", size=12)),
                showlegend=False,
                height=290,
                margin=dict(l=10, r=45, t=20, b=20),
                hoverlabel=dict(
                    bgcolor="#0C101A",
                    bordercolor="rgba(255,255,255,0.12)",
                    font=dict(family="Inter, sans-serif", size=12, color="#FFFFFF")
                )
            )
            st.plotly_chart(fig_units, use_container_width=True, config={'displayModeBar': False, 'responsive': True})

        st.markdown("<h4 style='margin-top: 16px; margin-bottom: 8px;'>Departmental Ledger & Margin Breakdown</h4>", unsafe_allow_html=True)
        st.dataframe(
            df_dept.style.format({
                "units_sold": "{:,.0f}",
                "gross_sales": "${:,.2f}",
                "discounts": "${:,.2f}",
                "net_sales": "${:,.2f}",
                "percentage_of_sales": "{:.1f}%"
            }),
            use_container_width=True
        )
    else:
        st.info("No department transactions available.")

# -------------------------------------------------------------
# TAB 3: Financial Settlement & Xero General Ledger Bridge
# -------------------------------------------------------------
with tab_reconcile:
    st.markdown("<h3 style='margin-bottom: 4px;'>⚖️ Bank Settlement Bridge & Accounting Reconciliation</h3>", unsafe_allow_html=True)
    st.caption("Exact waterfall reconciliation bridging Gross POS takings to physical cash safe count and electronic EFTPOS settlements.")

    if user_role not in BOARD_FINANCE_ROLES:
        st.warning("🔒 **Access Restricted:** Bank settlement totals, safe bag targets, and Xero General Ledger exports are restricted to Board Members, Treasurers, and Super Admins.")
    else:
        bridge = db.get_bank_settlement_bridge(start_str, end_str, location_id=selected_loc_id)

        # 5-Step Executive Waterfall Flow
        st.markdown(f"""
        <div class="waterfall-flow">
            <div class="waterfall-step">
                <div class="waterfall-step-num">
                    <span>1. Gross POS Takings</span>
                    <span class="waterfall-op" style="background: rgba(255,255,255,0.08); color: #FFFFFF;">START</span>
                </div>
                <div class="waterfall-val tabular-nums" style="color: #FFFFFF;">${bridge['gross_sales']:,.2f}</div>
                <div class="waterfall-sub">Total register sales</div>
            </div>
            <div class="waterfall-step">
                <div class="waterfall-step-num">
                    <span>2. Member Comps</span>
                    <span class="waterfall-op" style="background: rgba(245, 158, 11, 0.15); color: #F59E0B;">LESS (-)</span>
                </div>
                <div class="waterfall-val tabular-nums" style="color: #FBBF24;">-${bridge['discounts']:,.2f}</div>
                <div class="waterfall-sub">Member rewards & comps</div>
            </div>
            <div class="waterfall-step">
                <div class="waterfall-step-num">
                    <span>3. Net POS Sales</span>
                    <span class="waterfall-op" style="background: rgba(0, 82, 204, 0.2); color: #60A5FA;">EQUALS (=)</span>
                </div>
                <div class="waterfall-val tabular-nums" style="color: #60A5FA;">=${bridge['net_sales']:,.2f}</div>
                <div class="waterfall-sub">Taxable club takings</div>
            </div>
            <div class="waterfall-step">
                <div class="waterfall-step-num">
                    <span>4. Square Fees</span>
                    <span class="waterfall-op" style="background: rgba(244, 63, 94, 0.15); color: #F43F5E;">LESS (-)</span>
                </div>
                <div class="waterfall-val tabular-nums" style="color: #F43F5E;">-${bridge['square_fees']:,.2f}</div>
                <div class="waterfall-sub">Merchant terminal fee</div>
            </div>
            <div class="waterfall-step" style="border-color: rgba(16, 185, 129, 0.35); background: linear-gradient(145deg, rgba(16, 185, 129, 0.08) 0%, rgba(255,255,255,0.02) 100%);">
                <div class="waterfall-step-num">
                    <span style="color: #34D399;">5. Net Bank Settlement</span>
                    <span class="waterfall-op" style="background: rgba(16, 185, 129, 0.2); color: #34D399;">FINAL (=)</span>
                </div>
                <div class="waterfall-val tabular-nums" style="color: #10B981;">=${bridge['net_settlement']:,.2f}</div>
                <div class="waterfall-sub" style="color: #34D399;">Club bank account target</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Tender Balancing Side-by-Side Cards
        c_t1, c_t2 = st.columns(2)
        with c_t1:
            st.markdown(f"""
            <div class="tender-card">
                <div class="tender-header">
                    <span class="tender-title">💵 Physical Cash Count (Drawer & Safe)</span>
                    <span class="tender-badge" style="background: rgba(223, 177, 91, 0.15); color: #DFB15B; border: 1px solid rgba(223, 177, 91, 0.3);">Safe Bag Deposit Target</span>
                </div>
                <div class="tender-val tabular-nums" style="color: #DFB15B;">${bridge['cash_takings']:,.2f}</div>
                <div class="tender-sub">Physical cash tendered into till drawers. Must balance against bar float and target the commercial night-safe banking bag.</div>
            </div>
            """, unsafe_allow_html=True)

        with c_t2:
            net_card = bridge['card_takings'] - bridge['square_fees']
            st.markdown(f"""
            <div class="tender-card">
                <div class="tender-header">
                    <span class="tender-title">💳 Electronic EFTPOS Batch Settlement</span>
                    <span class="tender-badge" style="background: rgba(0, 82, 204, 0.2); color: #60A5FA; border: 1px solid rgba(0, 82, 204, 0.35);">Direct Bank Clearance</span>
                </div>
                <div class="tender-val tabular-nums" style="color: #60A5FA;">${net_card:,.2f}</div>
                <div class="tender-sub">Electronic card takings (${bridge['card_takings']:,.2f}) minus Square merchant processing fees (${bridge['square_fees']:,.2f}). Deposited automatically to club bank account.</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
        st.markdown("<h4 style='margin-bottom: 4px;'>📑 1-Click Xero Manual Journal Export</h4>", unsafe_allow_html=True)
        st.caption("Pre-formatted strictly to the Australian Xero Manual Journal import schema. Automatically balances General Ledger Debits and Credits.")

        df_gl = db.get_gl_export(start_str, end_str, location_id=selected_loc_id)

        if not df_gl.empty:
            st.dataframe(df_gl, use_container_width=True)

            col_xero_dl, col_xero_info = st.columns([1, 1])
            with col_xero_dl:
                csv_gl = df_gl.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Xero Manual Journal (.csv)",
                    data=csv_gl,
                    file_name=f"uhsc_xero_journal_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            with col_xero_info:
                st.markdown("""
                <div class="xero-guide-card">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                        <strong style="color: #60A5FA; font-size: 0.95rem;">⚡ 30-Second Xero Posting Procedure:</strong>
                    </div>
                    <div style="line-height: 1.6; font-size: 0.84rem;">
                        <strong>1.</strong> Click <strong>Download Xero Manual Journal (.csv)</strong>.<br>
                        <strong>2.</strong> Log into Xero ➔ <strong>Accounting</strong> ➔ <strong>Manual Journals</strong>.<br>
                        <strong>3.</strong> Click <strong>Import</strong> and upload the downloaded CSV file.<br>
                        <strong>4.</strong> Confirm Debits balance Credits, then click <strong>Post</strong>. Done!
                    </div>
                </div>
                """, unsafe_allow_html=True)

# -------------------------------------------------------------
# TAB 4: Trading Velocity Heatmap & Operational Planning
# -------------------------------------------------------------
with tab_velocity:
    st.markdown("<h3 style='margin-bottom: 4px;'>⏰ Midday to Midnight Trading Velocity (12:00 PM – 12:00 AM)</h3>", unsafe_allow_html=True)
    st.caption("Commercial intensity mapped across active trading hours (12:00 Midday to 12:00 Midnight in Upper Horton local time) and day of week. Essential for staging kitchen food service and volunteer bar rosters.")

    df_heat = db.get_trading_heatmap(start_str, end_str, location_id=selected_loc_id, min_hour=12, max_hour=24)

    if not df_heat.empty:
        days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        all_operating_hours = list(range(12, 24))
        pivot_sales = df_heat.pivot_table(
            index="day_name",
            columns="hour_of_day",
            values="total_sales",
            aggfunc="sum",
            fill_value=0.0
        ).reindex(index=days_order, columns=all_operating_hours, fill_value=0.0)

        # Plotly Heatmap using Bespoke Obsidian-to-Gold Heat Scale
        heat_scale = [
            [0.0, "#080B14"],
            [0.25, "#0D1E3A"],
            [0.55, "#0052CC"],
            [0.8, "#D97706"],
            [1.0, "#DFB15B"]
        ]

        hour_labels = [
            "12 PM (Noon)", "1 PM", "2 PM", "3 PM", "4 PM", "5 PM",
            "6 PM", "7 PM", "8 PM", "9 PM", "10 PM", "11 PM"
        ]

        fig_heat = px.imshow(
            pivot_sales,
            labels=dict(x="Trading Hour", y="Day of Week", color="Takings ($ AUD)"),
            x=hour_labels,
            y=pivot_sales.index,
            color_continuous_scale=heat_scale,
            aspect="auto"
        )
        fig_heat.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94A3B8", family="Inter, sans-serif"),
            height=380,
            margin=dict(l=10, r=10, t=20, b=20),
            xaxis=dict(tickfont=dict(color="#CBD5E1", size=11)),
            yaxis=dict(tickfont=dict(color="#CBD5E1", size=12)),
            coloraxis_colorbar=dict(
                tickprefix="$",
                tickfont=dict(color="#94A3B8", size=10),
                title=dict(font=dict(color="#94A3B8", size=11))
            ),
            hoverlabel=dict(
                bgcolor="#0C101A",
                bordercolor="rgba(255,255,255,0.12)",
                font=dict(family="Inter, sans-serif", size=12, color="#FFFFFF")
            )
        )
        st.plotly_chart(fig_heat, use_container_width=True, config={'displayModeBar': False, 'responsive': True})

        # Peak Velocity Operational Insight
        hourly_totals = df_heat.groupby("hour_of_day")["total_sales"].sum().reset_index()
        busiest_hour_row = hourly_totals.loc[hourly_totals["total_sales"].idxmax()]
        b_hour = int(busiest_hour_row["hour_of_day"])
        
        st.markdown(f"""
        <div class="peak-intel-card">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px;">
                <span style="font-size: 1.25rem;">💡</span>
                <span style="color: #DFB15B; font-weight: 700; font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.05rem;">Peak Operational Velocity Window</span>
            </div>
            <div style="color: #E2E8F0; line-height: 1.6; font-size: 0.92rem;">
                The club experiences maximum commercial velocity between <strong>{b_hour:02d}:00 – {b_hour+1:02d}:00</strong>, generating <strong>${busiest_hour_row['total_sales']:,.2f}</strong> in this window. 
                Ensure bar volunteer rosters, cold beer lines, and bistro kitchen staging are fully staffed by <strong>{b_hour-1:02d}:30</strong> to eliminate customer queues and maximize ticket turnover.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("No velocity data available.")

# -------------------------------------------------------------
# TAB 5: Catalog & Item Movement Intelligence
# -------------------------------------------------------------
with tab_items:
    st.markdown("<h3 style='margin-bottom: 4px;'>📦 Product Movement & Treasurer Export</h3>", unsafe_allow_html=True)
    st.caption("Individual item velocity, units depleted, and gross-to-net takings across all club categories.")

    categories = ["ALL"] + db.get_available_categories()
    c_f1, c_f2 = st.columns([1, 2])
    with c_f1:
        selected_cat = st.selectbox("Department / Category Filter", categories)
    with c_f2:
        search_query = st.text_input("Search Catalog Items", placeholder="e.g. Great Northern, Carlton Draught, Works Burger, Club Raffle...")

    df_items = db.get_top_items(start_str, end_str, limit=250, category=selected_cat, location_id=selected_loc_id)

    if not df_items.empty:
        if search_query:
            df_items = df_items[df_items["item_name"].str.contains(search_query, case=False, na=False)]

        df_top10 = df_items.head(10).sort_values("net_sales", ascending=True)
        fig_top = go.Figure(go.Bar(
            x=df_top10["net_sales"],
            y=df_top10["item_name"],
            orientation="h",
            marker=dict(
                color=df_top10["net_sales"],
                colorscale=[[0, "rgba(0, 82, 204, 0.75)"], [1, "rgba(223, 177, 91, 0.95)"]],
                cornerradius=4
            ),
            text=[f"${v:,.2f}" for v in df_top10["net_sales"]],
            textposition="outside",
            textfont=dict(family="Plus Jakarta Sans, sans-serif", size=11, color="#F8FAFC"),
            hovertemplate="<b>%{y}</b><br>Net Takings: <b>$%{x:,.2f} AUD</b><extra></extra>"
        ))
        fig_top.update_layout(
            title=dict(text="Top 10 Club Performers by Net Takings", font=dict(family="Plus Jakarta Sans, sans-serif", size=14, color="#F8FAFC")),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94A3B8", family="Inter, sans-serif"),
            showlegend=False,
            height=320,
            margin=dict(l=10, r=40, t=50, b=20),
            xaxis=dict(
                title=dict(text="Net Takings ($ AUD)", font=dict(color="#94A3B8", size=11)),
                gridcolor="rgba(255,255,255,0.05)",
                zerolinecolor="rgba(255,255,255,0.08)",
                tickprefix="$",
                tickformat=",.0f"
            ),
            yaxis=dict(tickfont=dict(color="#CBD5E1", size=11)),
            hoverlabel=dict(
                bgcolor="#0C101A",
                bordercolor="rgba(255,255,255,0.12)",
                font=dict(family="Inter, sans-serif", size=12, color="#FFFFFF")
            )
        )
        st.plotly_chart(fig_top, use_container_width=True, config={'displayModeBar': False, 'responsive': True})

        st.markdown("<h4 style='margin-top: 18px; margin-bottom: 8px;'>Item Movement Master Table</h4>", unsafe_allow_html=True)
        st.dataframe(
            df_items.style.format({
                "total_qty_sold": "{:,.0f}",
                "gross_sales": "${:,.2f}",
                "discounts": "${:,.2f}",
                "net_sales": "${:,.2f}",
                "avg_unit_price": "${:,.2f}"
            }),
            use_container_width=True
        )

        col_e1, col_e2 = st.columns(2)
        with col_e1:
            csv_items = df_items.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Item Movement (.csv)",
                data=csv_items,
                file_name=f"uhsc_items_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col_e2:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_items.to_excel(writer, index=False, sheet_name="Product Movement")
            st.download_button(
                label="📊 Download Excel Spreadsheet (.xlsx)",
                data=buffer.getvalue(),
                file_name=f"uhsc_items_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    else:
        st.info("No items match the selected criteria.")

# -------------------------------------------------------------
# TAB: Board & Staff Governance (Admin Panel)
# -------------------------------------------------------------
with tab_admin:
    st.markdown("<h3 style='margin-bottom: 4px;'>👥 Board of Directors & Staff Governance</h3>", unsafe_allow_html=True)
    st.caption("Manage user access, onboard incoming board members, assign governance roles, and revoke/offboard departing members.")

    if current_user.get("role") != "Super Admin":
        st.warning("🔒 Access Restricted: Only Super Admins have permission to manage board member accounts.")
    else:
        actor_uname = current_user.get("username", "admin")

        # 1. Active Board Members Roster
        st.markdown("<h4 style='margin-top: 14px; margin-bottom: 8px;'>📋 Current Access Register</h4>", unsafe_allow_html=True)
        df_users = db.get_users()
        if not df_users.empty:
            st.dataframe(
                df_users.rename(columns={
                    "username": "Username",
                    "full_name": "Full Name",
                    "email": "Email",
                    "role": "Governance Role",
                    "status": "Access Status",
                    "created_date": "Date Added",
                    "last_login_str": "Last Sign-In"
                })[["Username", "Full Name", "Email", "Governance Role", "Access Status", "Date Added", "Last Sign-In"]],
                use_container_width=True,
                hide_index=True
            )
        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        col_onboard, col_offboard = st.columns([1, 1])

        # 2. Onboard New Member Form
        with col_onboard:
            st.markdown("""
            <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.28); border-radius: 12px; padding: 14px 18px; margin-bottom: 14px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h4 style="margin: 0; color: #10B981;">➕ Onboard New Board Member / Staff</h4>
                    <span style="font-size: 0.74rem; color: #A7F3D0; background: rgba(16, 185, 129, 0.2); padding: 3px 10px; border-radius: 14px; font-weight: 600;">New Account</span>
                </div>
                <p style="margin: 4px 0 0 0; font-size: 0.8rem; color: #94A3B8;">Provision credentials (600k PBKDF2-SHA256) and assign governance roles for club personnel.</p>
            </div>
            """, unsafe_allow_html=True)

            with st.form("create_user_form", clear_on_submit=True):
                new_u = st.text_input("Username (Unique Login ID)*", placeholder="e.g. jsmith or treasurer")
                new_fn = st.text_input("Full Name*", placeholder="e.g. John Smith")
                new_em = st.text_input("Email Address (Optional)", placeholder="e.g. john@sportsclub.com.au")
                new_role = st.selectbox("Assign Governance Role*", [
                    "Committee Member",
                    "Treasurer",
                    "Bar Manager",
                    "Kitchen Supervisor",
                    "Viewer / Auditor",
                    "Super Admin"
                ])
                new_pw = st.text_input("Initial Password* (8+ chars, letters & numbers/symbols)", type="password", placeholder="Minimum 8 characters")
                new_pw2 = st.text_input("Confirm Initial Password*", type="password", placeholder="Repeat password")

                submitted = st.form_submit_button("➕ Provision Board Member Account", use_container_width=True)
                if submitted:
                    if not new_u or not new_fn or not new_pw:
                        st.error("Please fill in all required fields (Username, Full Name, Password).")
                    elif new_pw != new_pw2:
                        st.error("Passwords do not match. Please verify.")
                    else:
                        ok, msg = db.create_user(new_u, new_fn, new_em, new_role, new_pw, actor=actor_uname)
                        if ok:
                            st.success(f"✅ {msg}")
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")

        # 3. Offboard or Modify Existing Member
        with col_offboard:
            st.markdown("""
            <div style="background: rgba(244, 63, 94, 0.08); border: 1px solid rgba(244, 63, 94, 0.28); border-radius: 12px; padding: 14px 18px; margin-bottom: 14px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h4 style="margin: 0; color: #F43F5E;">🔒 Member Offboarding & Access Control</h4>
                    <span style="font-size: 0.74rem; color: #FECDD3; background: rgba(244, 63, 94, 0.2); padding: 3px 10px; border-radius: 14px; font-weight: 600;">Revoke & Offboard</span>
                </div>
                <p style="margin: 4px 0 0 0; font-size: 0.8rem; color: #94A3B8;">Instantly suspend access when board members depart or change positions.</p>
            </div>
            """, unsafe_allow_html=True)

            if not df_users.empty:
                user_options = {row["user_id"]: f"{row['full_name']} (@{row['username']}) — {row['role']} [{row['status']}]" for _, row in df_users.iterrows()}
                target_uid = st.selectbox("Select Board Member to Manage", options=list(user_options.keys()), format_func=lambda k: user_options[k])

                target_row = df_users[df_users["user_id"] == target_uid].iloc[0]
                is_self = (target_uid == current_user.get("user_id"))

                # SEC-04: Escape user metadata before rendering in HTML
                esc_target_name = html.escape(str(target_row["full_name"]))
                esc_target_role = html.escape(str(target_row["role"]))
                esc_target_status = html.escape(str(target_row["status"]))

                st.markdown(f"""
                <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.07); border-radius: 8px; padding: 10px 14px; margin-bottom: 12px; font-size: 0.82rem;">
                    <div><strong>Member:</strong> {esc_target_name}</div>
                    <div><strong>Current Role:</strong> {esc_target_role} • <strong>Status:</strong> <span style="color: {'#34D399' if target_row['status'] == 'ACTIVE' else '#F43F5E'}; font-weight: 700;">{esc_target_status}</span></div>
                </div>
                """, unsafe_allow_html=True)

                if is_self:
                    st.info("ℹ️ You are signed in as this Super Admin account. Self-suspension, role demotion, and deletion are locked.")
                    with st.popover("🔑 Change My Password", use_container_width=True):
                        self_pw = st.text_input("New Personal Password (8+ chars)", type="password", key=f"self_pw_{target_uid}")
                        if st.button("Update My Password", key=f"self_pw_btn_{target_uid}"):
                            ok_p, msg_p = db.reset_user_password(target_uid, self_pw, actor=actor_uname)
                            if ok_p:
                                st.success(msg_p)
                            else:
                                st.error(msg_p)
                else:
                    col_act1, col_act2 = st.columns(2)
                    with col_act1:
                        if target_row["status"] == "ACTIVE":
                            if st.button("⏸️ Suspend Member Access", use_container_width=True, key=f"btn_susp_{target_uid}"):
                                ok_s, msg_s = db.update_user_status(target_uid, "SUSPENDED", actor=actor_uname)
                                if ok_s:
                                    st.success(msg_s)
                                    st.rerun()
                                else:
                                    st.error(msg_s)
                        else:
                            if st.button("▶️ Reactivate Access", use_container_width=True, key=f"btn_act_{target_uid}"):
                                ok_s, msg_s = db.update_user_status(target_uid, "ACTIVE", actor=actor_uname)
                                if ok_s:
                                    st.success(msg_s)
                                    st.rerun()
                                else:
                                    st.error(msg_s)

                    with col_act2:
                        with st.popover("🔑 Reset Password", use_container_width=True):
                            rst_pw = st.text_input("New Password (8+ chars)", type="password", key=f"rst_input_{target_uid}")
                            if st.button("Confirm Reset", key=f"rst_save_{target_uid}"):
                                ok_r, msg_r = db.reset_user_password(target_uid, rst_pw, actor=actor_uname)
                                if ok_r:
                                    st.success(msg_r)
                                else:
                                    st.error(msg_r)

                    with st.expander("🔄 Reassign Governance Role"):
                        new_r = st.selectbox("Assign New Role", ["Committee Member", "Treasurer", "Bar Manager", "Kitchen Supervisor", "Viewer / Auditor", "Super Admin"], key=f"role_sel_{target_uid}")
                        if st.button("Update Role", key=f"role_btn_{target_uid}"):
                            ok_rl, msg_rl = db.update_user_role(target_uid, new_r, actor=actor_uname)
                            if ok_rl:
                                st.success(msg_rl)
                                st.rerun()
                            else:
                                st.error(msg_rl)

                    with st.expander("🗑️ Permanent Member Removal (Danger Zone)"):
                        st.caption("Permanently removes the member's account from the database. This action is irreversible.")
                        chk = st.checkbox("Confirm permanent removal", key=f"chk_del_{target_uid}")
                        if st.button("Delete Account Permanently", key=f"del_btn_{target_uid}", disabled=not chk):
                            ok_d, msg_d = db.delete_user(target_uid, actor=actor_uname)
                            if ok_d:
                                st.success(msg_d)
                                st.rerun()
                            else:
                                st.error(msg_d)

        st.markdown("---")
        st.markdown("<h4 style='margin-bottom: 8px;'>🛡️ Security & Governance Audit Trail</h4>", unsafe_allow_html=True)
        st.caption("Immutable log of sign-in events, brute-force lockouts, user creations, password resets, and role changes.")
        df_audit = db.get_audit_logs(limit=40)
        if not df_audit.empty:
            st.dataframe(
                df_audit.rename(columns={
                    "timestamp_str": "Timestamp",
                    "actor": "Actor",
                    "event": "Security Event",
                    "target": "Target Account",
                    "details": "Audit Details"
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.caption("No security audit events recorded yet.")

# -------------------------------------------------------------
# TAB 9: System Diagnostics, OAuth Security & Nightly Cron
# -------------------------------------------------------------
with tab_settings:
    st.markdown("<h3 style='margin-bottom: 4px;'>⚙️ Security Posture, OAuth Scope & Nightly Sync Architecture</h3>", unsafe_allow_html=True)
    st.caption("Super Admin diagnostics for Square OAuth/API token hardening, read-only database locks, and 02:00 AM nightly batch reconciliation.")

    # SEC-02: Strict Super Admin RBAC Gate
    if current_user.get("role") != "Super Admin":
        st.warning("🔒 Access Restricted: System diagnostics, OAuth configuration, and ledger synchronization require Super Admin privileges.")
    else:
        token_sec = SquareClient().inspect_token_security()
        c_s1, c_s2 = st.columns(2)
        with c_s1:
            st.markdown("<h4 style='margin-bottom: 10px;'>🔑 Square OAuth & API Security Posture</h4>", unsafe_allow_html=True)
            env_badge = "🟢 Production (Live Club Data)" if SQUARE_ENVIRONMENT == "production" else "🟡 Sandbox (Test Mode)"
            st.write(f"**Square Environment:** {env_badge}")
            st.write(f"**Masked Token Fingerprint:** `{token_sec['masked_token']}`")
            st.write(f"**Credential Classification:** `{token_sec['token_type']}`")
            st.write(f"**Read-Only API Policy:** `🔒 Enforced (GET / Search Only — Zero Write/Refund Endpoints)`")
            st.write(f"**Active Read Scopes:** `{', '.join(token_sec['scopes'])}`")
            st.write(f"**Database File Lock Mode:** `🔒 Read-Only Analytical Connections + chmod 600`")

            if st.button("🧪 Verify Square Read-Only Handshake"):
                with st.spinner("Testing TLS 1.3 handshake with Square API..."):
                    ok, msg = SquareClient().test_connection()
                    if ok:
                        st.success(f"Connection verified: {msg}")
                    else:
                        st.error(f"Handshake failed: {msg}")

        with c_s2:
            st.markdown("<h4 style='margin-bottom: 10px;'>🌙 Automated 02:00 AM Nightly Batch Sync</h4>", unsafe_allow_html=True)
            st.markdown("""
            The reporting suite operates on an **Air-Gapped Nightly Batch Ledger** model:
            - General users **cannot** trigger live Square API calls from the web UI.
            - Every morning at **02:00 AM**, `scripts/nightly_sync.py` reconciles the trailing 3 days into an isolated staging file (`club_sales.duckdb.staging`) and performs an **atomic OS file swap** (`os.replace`) with zero database lock contention.
            
            **Host Cron Configuration (`crontab -e`):**
            ```bash
            0 2 * * * /home/leith/AI/Square/.venv/bin/python /home/leith/AI/Square/scripts/nightly_sync.py >> /home/leith/AI/Square/data/nightly_sync.log 2>&1
            ```
            """)

            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            col_sync_d, col_sync_b = st.columns([1.2, 1.8])
            with col_sync_d:
                admin_sync_days = st.selectbox(
                    "Emergency Delta Window",
                    [3, 7, 14, 30, 90],
                    index=0,
                    format_func=lambda d: f"Trailing {d} Days"
                )
            with col_sync_b:
                st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
                if st.button("🔄 Run Atomic Delta Sync Now (Super Admin)", use_container_width=True):
                    with st.spinner(f"Executing atomic staging sync for trailing {admin_sync_days} days..."):
                        res = sync_engine.run_sync(days_back=admin_sync_days, atomic_staging=True)
                        if res.get("status") == "SUCCESS":
                            db.log_audit_event(current_user.get("username", "admin"), "MANUAL_ADMIN_SYNC", "SQUARE_API", f"Synced {admin_sync_days}d window")
                            st.success(f"Atomic Sync Complete! {res.get('message')}")
                            st.rerun()
                        else:
                            st.error(f"Sync Notice: {res.get('message')}")

        st.markdown("---")
        st.markdown("<h4 style='margin-bottom: 10px;'>📊 Ledger Synchronization Audit History</h4>", unsafe_allow_html=True)
        df_syncs = db.get_sync_history(limit=15)
        if not df_syncs.empty:
            st.dataframe(df_syncs, use_container_width=True, hide_index=True)
        else:
            st.caption("No sync events recorded in the ledger yet.")
