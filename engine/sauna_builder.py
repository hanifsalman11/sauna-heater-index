import os
import json
import re
import time
import math
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/sauna-heater-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4").strip()
CUSTOM_SAUNA = os.environ.get("CUSTOM_SAUNA", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_saunas.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

_CACHED_MODELS = None

# Format: (Heater / Sauna Room Scenario, Length Ft, Width Ft, Height Ft, Glass/Tile Sq Ft, Heater kW, Stone Lbs)
SEED_SAUNAS = [
    ("Harvia KIP-60B1 (6.0 kW 240V) Wall-Mount Sauna Heater", 6.0, 5.0, 7.0, 14, 6.0, 50),
    ("Harvia KIP-80B1 (8.0 kW 240V) Traditional Sauna Heater", 7.0, 6.0, 7.0, 18, 8.0, 50),
    ("Harvia KIP-45B1 (4.5 kW 240V) Compact Sauna Heater", 5.0, 4.0, 6.5, 12, 4.5, 50),
    ("Harvia Cilindro PC70 / PC90 (6.8 kW & 9.0 kW) Pillar Heater", 8.0, 7.0, 7.0, 22, 9.0, 180),
    ("Harvia The Wall SW60 & SW80 (6.0 kW / 8.0 kW) Sauna Heater", 7.0, 6.0, 7.0, 16, 8.0, 45),
    ("Harvia Spirit SP60E & SP80E Wi-Fi Curved Stone Heater", 7.0, 6.0, 7.0, 18, 8.0, 110),
    ("Harvia Virta HL90E / HL110E (9.0 kW / 10.5 kW) Floor Heater", 9.0, 8.0, 7.0, 25, 10.5, 150),
    ("HUUM DROP 6 kW & 9 kW Wall-Mounted Teardrop Sauna Heater", 7.5, 6.5, 7.0, 20, 9.0, 125),
    ("HUUM HIVE Mini 6 kW / 9 kW / 11 kW Floor Pillar Heater", 8.0, 7.0, 7.0, 24, 9.0, 330),
    ("HUUM STEEL 6 kW & 9 kW Slim Clearance Sauna Heater", 7.0, 6.0, 7.0, 18, 9.0, 330),
    ("VEVOR 6 kW 240V Stainless Steel Dry Steam Sauna Heater", 6.0, 5.0, 7.0, 14, 6.0, 45),
    ("VEVOR 8 kW & 9 kW 240V Commercial/Home Sauna Stove", 8.0, 6.0, 7.0, 18, 9.0, 50),
    ("VEVOR 4.5 kW 240V Compact Home Sauna Heater Stove", 5.0, 4.0, 6.5, 12, 4.5, 35),
    ("Tylo Sense Sport & Pure 6.6 kW / 8.0 kW Fast-Heat Sauna", 7.0, 6.0, 7.0, 16, 8.0, 45),
    ("Sawo Scandia & Aries 6.0 kW / 8.0 kW / 9.0 kW Sauna Stove", 7.5, 6.0, 7.0, 18, 8.0, 50),
    ("Finlandia FLB-60 & FLB-80 (6.0 kW / 8.0 kW) Sauna Heater", 7.0, 6.0, 7.0, 16, 8.0, 50),
    (" Polar / Amerec Junior 2.2 kW (120V) & Designer 6.0 kW (240V)", 4.0, 4.0, 6.5, 10, 3.0, 30),
    ("Homecraft Revive 6 kW / 7.5 kW / 9 kW Tower Sauna Heater", 7.5, 6.5, 7.0, 20, 9.0, 150),
    ("4x4x6.5 Ft 2-Person Compact Indoor Cedar Sauna Sizing", 4.0, 4.0, 6.5, 14, 3.5, 45),
    ("5x6x7 Ft 3-Person Home Basement Dry Sauna Sizing", 6.0, 5.0, 7.0, 15, 6.0, 50),
    ("6x7x7 Ft 4-Person Family Cedar Sauna w/ Glass Door Sizing", 7.0, 6.0, 7.0, 18, 8.0, 60),
    ("6x8x7 Ft 5-Person Custom Sauna w/ Panoramic Glass Wall", 8.0, 6.0, 7.0, 36, 9.0, 90),
    ("8x8x7 Ft 6-to-8 Person Commercial & Gym Sauna Sizing", 8.0, 8.0, 7.0, 24, 10.5, 130),
    ("6x6 Ft 4-Person Outdoor Uninsulated Cedar Barrel Sauna", 6.0, 6.0, 6.0, 14, 6.0, 50),
    ("6x7 Ft 6-Person Outdoor Cedar Barrel Sauna (Winter Spec)", 7.0, 6.0, 6.0, 16, 8.0, 55),
    ("6x8 Ft 8-Person Outdoor Panoramic Window Barrel Sauna", 8.0, 6.0, 6.0, 28, 9.0, 80),
    ("Almost Heaven Pinnacle 4-Person Barrel Sauna Heater Sizing", 6.0, 6.0, 6.0, 14, 6.0, 50),
    ("Almost Heaven Audra & Bridgeport 6-Person Sauna Sizing", 7.0, 6.0, 6.5, 18, 8.0, 50),
    ("8.0 kW vs 9.0 kW Sauna Heater 240V Breaker & 8 AWG Wire", 8.0, 6.5, 7.0, 20, 9.0, 80),
    ("6.0 kW Sauna Heater 240V 30A Breaker & 10 AWG Wire Setup", 6.0, 5.5, 7.0, 14, 6.0, 50)
]


def load_json(filepath, default):
    """Self-healing JSON loader: otomatis pulih jika file korup atau belum ada."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, type(default)) else default
        except Exception as e:
            print(f"[SELF-HEAL] Recovering {filepath} due to read notice: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=6.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def get_active_gemini_model(api_key):
    """
    LAPIS 1: Mesin Pemindai Versi Otomatis berbasis Regex tanpa angka versi manual.
    Otomatis mendeteksi model Gemini Flash STABIL generasi tertinggi lintas tahun.
    """
    global _CACHED_MODELS
    if _CACHED_MODELS is not None:
        return _CACHED_MODELS

    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        req = urllib.request.Request(list_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            scored_models = []

            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])

                if "generateContent" not in methods or "flash" not in name.lower():
                    continue

                if any(bad in name.lower() for bad in [
                    "preview", "exp", "thinking", "image", "tts", "audio", "vision", "8b"
                ]):
                    continue

                ver_match = re.search(r"gemini-(\d+(?:\.\d+)?)-flash", name.lower())
                if ver_match:
                    ver_num = float(ver_match.group(1))
                    if name.lower() == f"gemini-{ver_match.group(1)}-flash":
                        tier_score = 2
                    elif name.lower() == f"gemini-{ver_match.group(1)}-flash-lite":
                        tier_score = 1
                    else:
                        tier_score = 0
                    scored_models.append((ver_num, tier_score, name))
                elif name.lower() == "gemini-flash-latest":
                    scored_models.append((0.1, 0, name))

            if scored_models:
                scored_models.sort(key=lambda x: (x[0], x[1]), reverse=True)
                _CACHED_MODELS = [item[2] for item in scored_models[:2]]
                print(f"[GEMINI] Future-proof active models locked: {_CACHED_MODELS}")
                return _CACHED_MODELS
    except Exception as e:
        print(f"[WARN] Dynamic model discovery notice: {e}")

    _CACHED_MODELS = ["gemini-flash-latest"]
    return _CACHED_MODELS


def discover_google_sauna_queries(published_slugs):
    """
    LAPIS 4: 3-Tier Infinite Keyword Supply:
    Tier A: Seed List -> Tier B: Google Suggest US -> Tier C: Combinatorial Sauna Room × Glass Door Permutator.
    """
    discovered = []
    seeds = [
        "what size sauna heater for ",
        "harvia sauna heater ",
        "huum drop sauna heater ",
        "sauna heater kw calculator "
    ]
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(seed)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = suggestion.lower()
                    for pref in seeds:
                        if "what size" in pref or "calculator" in pref:
                            cleaned = cleaned.replace(pref, "")
                    cleaned = re.sub(
                        r"\b(calculator|size|sizing|chart|manual|review|reddit|for)\b",
                        "",
                        cleaned
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        kw_m = re.search(r"(\d(?:\.\d)?)\s*kw", cleaned)
                        kw_v = float(kw_m.group(1)) if kw_m else 8.0
                        l_v = 6.0 if kw_v <= 6.0 else 7.5
                        w_v = 5.0 if kw_v <= 6.0 else 6.0
                        discovered.append((cleaned.title(), l_v, w_v, 7.0, 16, kw_v, 60))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")

    # Tier C Fallback: Combinatorial Permutator (Anti-Habis Lintas Tahun)
    footprints = [
        (4.0, 5.0, "4x5 Ft 2-Person Sauna"),
        (5.0, 6.0, "5x6 Ft 3-Person Sauna"),
        (6.0, 6.0, "6x6 Ft 4-Person Sauna"),
        (6.0, 7.0, "6x7 Ft 5-Person Sauna"),
        (6.0, 8.0, "6x8 Ft 6-Person Sauna"),
        (7.0, 8.0, "7x8 Ft 7-Person Sauna"),
        (8.0, 10.0, "8x10 Ft Commercial Sauna")
    ]
    glazing_types = [
        (14, "Standard Glass Door (14 Sq Ft)"),
        (28, "Glass Door + Side Window (28 Sq Ft)"),
        (42, "Full Panoramic Front Glass Wall (42 Sq Ft)"),
        (20, "Outdoor Uninsulated Cedar Barrel")
    ]
    for w_f, l_f, dim_desc in footprints:
        for gl_sqft, gl_desc in glazing_types:
            combo_title = f"{dim_desc} with {gl_desc}"
            test_slug = slugify(f"{combo_title}-kw-breaker-calculator")
            if test_slug not in published_slugs:
                raw_cu = w_f * l_f * 7.0
                adj_cu = raw_cu + (gl_sqft * 15.0)
                if "Barrel" in gl_desc:
                    adj_cu = adj_cu * 1.20
                rec_kw = 4.5 if adj_cu <= 210 else (6.0 if adj_cu <= 310 else (8.0 if adj_cu <= 425 else (9.0 if adj_cu <= 500 else 10.5)))
                st_lbs = 50 if rec_kw <= 8.0 else 90
                discovered.append((combo_title, l_f, w_f, 7.0, gl_sqft, rec_kw, st_lbs))
                if len(discovered) >= 25:
                    return discovered
    return discovered


def build_deterministic_sauna_data(sauna_tuple):
    """
    LAPIS 3: Mesin Fisika Termodinamika Sauna Finlandia (195°F / 90°C) & NEC 424 (100% Bebas Gagal).
    """
    item_name, len_ft, wid_ft, hgt_ft, glass_sqft, heater_kw, stone_lbs = sauna_tuple

    raw_cuft = int(round(len_ft * wid_ft * hgt_ft))
    # Standar Termal Sauna Finlandia:
    # Setiap 1 sq ft kaca tanpa insulasi (pintu/jendela) atau dinding ubin/batu menambah beban setara +15 cubic feet!
    # Jika Barrel Sauna (kayu log 1.5" tanpa insulasi foil), kalikan volume dengan 1.20x
    is_barrel = "barrel" in item_name.lower()
    glass_penalty_cuft = int(round(glass_sqft * 15.0))
    base_adjusted = raw_cuft + glass_penalty_cuft
    adjusted_cuft = int(round(base_adjusted * 1.20)) if is_barrel else base_adjusted

    # Rumus Ukuran Heater: 1.0 kW per 45 - 50 Adjusted Cubic Feet (target 185°F - 195°F dalam 45 menit)
    exact_kw_needed = round(adjusted_cuft / 46.0, 1)
    if heater_kw <= 0:
        heater_kw = 4.5 if exact_kw_needed <= 4.6 else (6.0 if exact_kw_needed <= 6.2 else (8.0 if exact_kw_needed <= 8.2 else 9.0))

    # Perhitungan Kelistrikan 240V Single-Phase (NEC Article 424 Continuous Space Heating = 125% Breaker Rule):
    running_amps_240v = round((heater_kw * 1000.0) / 240.0, 1)
    min_breaker_raw = running_amps_240v * 1.25
    if min_breaker_raw <= 20.0:
        breaker_amps = 20
        wire_awg = "12/2 AWG Copper (90°C Rated THHN/NM-B)"
    elif min_breaker_raw <= 30.0:
        breaker_amps = 30
        wire_awg = "10/2 AWG Copper (90°C Rated THHN/NM-B)"
    elif min_breaker_raw <= 40.0:
        breaker_amps = 40
        wire_awg = "8/2 AWG Stranded Copper (90°C Rated)"
    elif min_breaker_raw <= 50.0:
        breaker_amps = 50
        wire_awg = "6/2 AWG Stranded Copper (90°C Rated)"
    else:
        breaker_amps = 60
        wire_awg = "6/2 AWG or 4/2 AWG Copper + External Contactor Box"

    # Luas Aluminium Foil Vapor Barrier (Walls + Ceiling + 15% overlap)
    surface_area_sqft = int(round(((2.0 * (len_ft + wid_ft) * hgt_ft) + (len_ft * wid_ft)) * 1.15, -1))
    session_cost_usd = round(heater_kw * 1.15 * 0.16, 2)

    return {
        "sauna_name": item_name,
        "seo_title": f"{item_name} kW Heater, Adjusted Cubic Feet & Breaker Calculator (2026)",
        "meta_description": f"Calculate exact sauna heater size ({heater_kw} kW for {adjusted_cuft} Adjusted Cu Ft / {raw_cuft} Raw Cu Ft), 240V NEC breaker & wire ({breaker_amps}A / {wire_awg}), and {stone_lbs} lbs olivine rocks for {item_name}.",
        "specs": {
            "length_ft": len_ft,
            "width_ft": wid_ft,
            "height_ft": hgt_ft,
            "raw_volume_cuft": raw_cuft,
            "glass_stone_sqft": glass_sqft,
            "adjusted_volume_cuft": adjusted_cuft,
            "recommended_heater_kw": heater_kw,
            "running_amps_240v": running_amps_240v,
            "required_breaker_amps": breaker_amps,
            "recommended_wire_awg": wire_awg,
            "olivine_stone_lbs": stone_lbs,
            "foil_barrier_sqft": surface_area_sqft,
            "cost_per_session_usd": session_cost_usd
        },
        "thermal_verdict": f"Measuring {wid_ft}' W × {len_ft}' L × {hgt_ft}' H ({raw_cuft} raw cu. ft.) with {glass_sqft} sq. ft. of uninsulated glass/stone surface (+{glass_penalty_cuft} cu. ft. thermal loss penalty{' + 20% barrel log factor' if is_barrel else ''}), {item_name} has an Effective Thermal Volume of {adjusted_cuft} Adjusted Cubic Feet (ACF). Reaching authentic 190°F (88°C) Finnish löyly temperatures within 45 minutes requires a {heater_kw} kW 240V electric sauna heater ({running_amps_240v}A draw, ~${session_cost_usd} per 90-minute session) wired on a dedicated {breaker_amps}-Amp 2-pole breaker using {wire_awg} and loaded with {stone_lbs} lbs of split-face Olivine Diabase stones.",
        "hardware_bundle": [
            {
                "badge": f"{heater_kw} kW 240V Sauna Heater",
                "title": f"{heater_kw} kW 240V Stainless Steel Electric Sauna Heater ({raw_cuft}–{adjusted_cuft + 40} Cu Ft Rated)",
                "price_range": "$289 - $1,499",
                "amazon_query": f"{heater_kw} kW 240V Electric Sauna Heater Harvia Vevor Stainless",
                "sauna_note": f"Corrosion-resistant Incoloy heating elements heat {adjusted_cuft} adjusted cubic feet to 194°F in 40–45 minutes."
            },
            {
                "badge": f"{stone_lbs} lbs Olivine Diabase",
                "title": f"100% Natural Split-Face Olivine Diabase Sauna Stones ({stone_lbs}+ Lbs Box — 2\" to 4\" Vulcanite)",
                "price_range": "$54 - $169",
                "amazon_query": "Olivine Diabase Sauna Stones Rocks Harvia Split Face",
                "sauna_note": "High-density volcanic olivine diabase stores extreme thermal mass and won't crack or release sulfur odors when ladling water."
            },
            {
                "badge": f"{breaker_amps}A Breaker & 90°C Wire",
                "title": f"240V {breaker_amps}-Amp 2-Pole Breaker + {wire_awg.split()[0]} AWG 90°C High-Temp Silicone/Copper Whip Kit",
                "price_range": "$79 - $229",
                "amazon_query": f"{breaker_amps} Amp 2 Pole Breaker {wire_awg.split()[0]} AWG Copper Wire Liquid Tight Whip",
                "sauna_note": f"Meets NEC 424.3(B) 125% continuous heater sizing for {running_amps_240v}A @ 240V using 90°C high-temperature terminal insulation."
            },
            {
                "badge": f"{surface_area_sqft} ft² Foil Vapor Barrier",
                "title": " tear-Proof Aluminum Foil Sauna Vapor Barrier Roll + High-Temp Foil Tape & Cedar Bucket/Ladle Set",
                "price_range": "$69 - $159",
                "amazon_query": "Aluminum Foil Sauna Vapor Barrier Roll Tape Cedar Bucket Ladle",
                "sauna_note": "Reflects 97% of radiant infrared heat back behind the tongue-and-groove cedar cladding and blocks steam from rotting wall studs."
            }
        ],
        "builder_checklist": [
            f"Never size a sauna heater by Raw Cubic Feet ({raw_cuft} ft³) alone! Add +15 cubic feet for every 1 sq. ft. of glass door/window or tile wall ({glass_sqft} ft² × 15 = +{glass_penalty_cuft} ft³), and multiply by 1.25x for uninsulated outdoor barrel saunas to get {adjusted_cuft} Adjusted Cubic Feet.",
            f"Use 90°C (194°F) rated copper conductors ({wire_awg}) inside the sauna wall cavity and do NOT install a GFCI breaker unless explicitly required by local code—moisture condensation inside cold heating elements can cause nuisance GFCI trips.",
            "Keep ceiling height between 6.5 and 7.0 feet maximum: heat stratifies steeply in a sauna, so ceilings above 7.5 feet waste kW energy heating empty air above the upper bench.",
            "Place a 4\"×6\" passive Fresh Air Intake Vent directly beneath the electric heater (2 inches off the floor) and a sliding Exhaust Vent on the opposite wall beneath the upper bench (24 inches off the floor) so fresh oxygenated air circulates over the rocks without triggering the heater's high-limit reset switch."
        ],
        "faqs": [
            {
                "q": f"How do I calculate Adjusted Cubic Feet for {item_name}?",
                "a": f"First multiply Length × Width × Height ({len_ft}' × {wid_ft}' × {hgt_ft}' = {raw_cuft} raw cubic feet). Next, add 15 cubic feet for every square foot of glass door, window, or stone/tile wall ({glass_sqft} sq. ft. × 15 = +{glass_penalty_cuft} cu. ft.). That gives {adjusted_cuft} Adjusted Cubic Feet, requiring a {heater_kw} kW heater (1 kW per 45–50 ACF)."
            },
            {
                "q": f"What size 240V breaker and wire gauge do I need for a {heater_kw} kW sauna heater?",
                "a": f"A {heater_kw} kW heater at 240V draws {running_amps_240v} Amps ({heater_kw * 1000:,.0f}W ÷ 240V). Multiplying by the NEC 125% continuous heater rule ({running_amps_240v}A × 1.25 = {round(running_amps_240v * 1.25, 1)}A) requires a dedicated {breaker_amps}-Amp double-pole breaker wired with {wire_awg} (plus one 12 AWG copper equipment ground)."
            },
            {
                "q": f"How many pounds of sauna rocks do I need and how should I stack them?",
                "a": f"The {item_name} requires {stone_lbs} lbs of 2\"–4\" split-face Olivine Diabase stones. Rinse rock dust off before loading, place larger stones at the bottom, and stack loosely around (never wedged tightly between) the red-hot Incoloy elements so convective air flows freely."
            }
        ]
    }


def generate_sauna_data(sauna_tuple):
    """
    LAPIS 2: Memanggil model Gemini stabil dengan proteksi Cooldown HTTP 429 & Fallback Otomatis.
    """
    if not GEMINI_API_KEY:
        return build_deterministic_sauna_data(sauna_tuple)

    item_name, len_ft, wid_ft, hgt_ft, glass_sqft, heater_kw, stone_lbs = sauna_tuple
    det_fallback = build_deterministic_sauna_data(sauna_tuple)
    sp = det_fallback["specs"]

    prompt = f"""
You are a Certified Finnish Sauna Builder & Master Electrical Engineer (NEC Article 424 Specialist). Create an accurate 2026 electric sauna heater kW capacity, Adjusted Cubic Feet (glass/log thermal loss), 240V breaker/wire gauge, and olivine diabase stone guide for: "{item_name}".
Baseline specs: Dimensions={wid_ft}' W x {len_ft}' L x {hgt_ft}' H ({sp['raw_volume_cuft']} raw cu ft), Glass/Tile Area={glass_sqft} sq ft, Adjusted Thermal Volume={sp['adjusted_volume_cuft']} ACF, Recommended Heater={sp['recommended_heater_kw']} kW ({sp['running_amps_240v']}A @ 240V), Breaker={sp['required_breaker_amps']}A ({sp['recommended_wire_awg']}), Stones={stone_lbs} lbs, Foil Barrier={sp['foil_barrier_sqft']} sq ft.
Return ONLY a valid JSON object matching this exact schema:
{{
  "sauna_name": "{item_name}",
  "seo_title": "{item_name} kW Heater, Adjusted Cubic Feet & Breaker Calculator (2026)",
  "meta_description": "Calculate exact sauna heater kW rating, Adjusted Cubic Feet (with glass door and barrel log penalties), 240V breaker/wire AWG, and stone weight for {item_name}.",
  "specs": {{
    "length_ft": {len_ft},
    "width_ft": {wid_ft},
    "height_ft": {hgt_ft},
    "raw_volume_cuft": {sp['raw_volume_cuft']},
    "glass_stone_sqft": {glass_sqft},
    "adjusted_volume_cuft": {sp['adjusted_volume_cuft']},
    "recommended_heater_kw": {sp['recommended_heater_kw']},
    "running_amps_240v": {sp['running_amps_240v']},
    "required_breaker_amps": {sp['required_breaker_amps']},
    "recommended_wire_awg": "{sp['recommended_wire_awg']}",
    "olivine_stone_lbs": {stone_lbs},
    "foil_barrier_sqft": {sp['foil_barrier_sqft']},
    "cost_per_session_usd": {sp['cost_per_session_usd']}
  }},
  "thermal_verdict": "3-sentence technical summary stating raw cubic feet, glass/barrel thermal penalty, Adjusted Cubic Feet (ACF), required kW heater, and 240V NEC breaker/wire gauge.",
  "hardware_bundle": [
    {{
      "badge": "{sp['recommended_heater_kw']} kW 240V Heater",
      "title": "{sp['recommended_heater_kw']} kW 240V Stainless Steel Electric Sauna Heater",
      "price_range": "$289 - $1,499",
      "amazon_query": "{sp['recommended_heater_kw']} kW 240V Electric Sauna Heater Harvia Vevor",
      "sauna_note": "1-sentence heating speed and ACF capacity note"
    }},
    {{
      "badge": "{stone_lbs} lbs Olivine Stones",
      "title": "100% Natural Split-Face Olivine Diabase Sauna Stones ({stone_lbs}+ Lbs)",
      "price_range": "$54 - $169",
      "amazon_query": "Olivine Diabase Sauna Stones Rocks Harvia",
      "sauna_note": "1-sentence thermal shock resistance and löyly steam note"
    }},
    {{
      "badge": "{sp['required_breaker_amps']}A Breaker & 90°C Wire",
      "title": "240V {sp['required_breaker_amps']}-Amp 2-Pole Breaker + {sp['recommended_wire_awg'].split()[0]} AWG 90°C Copper Wire Kit",
      "price_range": "$79 - $229",
      "amazon_query": "{sp['required_breaker_amps']} Amp 2 Pole Breaker {sp['recommended_wire_awg'].split()[0]} AWG Copper Wire",
      "sauna_note": "1-sentence NEC 125% continuous heater ampacity note"
    }},
    {{
      "badge": "Foil Barrier & Cedar Kit",
      "title": "Aluminum Foil Sauna Vapor Barrier Roll + Foil Tape & Cedar Bucket/Ladle",
      "price_range": "$69 - $159",
      "amazon_query": "Aluminum Foil Sauna Vapor Barrier Roll Cedar Bucket Ladle",
      "sauna_note": "1-sentence radiant heat reflection and moisture protection note"
    }}
  ],
  "builder_checklist": [
    "Step 1 regarding +15 cu ft penalty per sq ft of glass door/window and 1.25x barrel log multiplier",
    "Step 2 regarding 90C rated copper wire and NEC 125% breaker sizing",
    "Step 3 regarding 7-foot max ceiling height to prevent heat stratification",
    "Step 4 regarding intake vent under heater and high-limit reset switch protection"
  ],
  "faqs": [
    {{"q": "How do I calculate the right kW sauna heater for {item_name}?", "a": "Exact raw cubic feet, glass penalty, Adjusted Cubic Feet, and kW rating."}},
    {{"q": "What size breaker and wire gauge do I need for a {sp['recommended_heater_kw']} kW sauna heater?", "a": "Exact 240V amps, 1.25x NEC breaker rating, and 90C AWG copper wire."}},
    {{"q": "What kind of rocks are safe for an electric sauna heater?", "a": "Direct geological explanation of why split-face Olivine Diabase / Peridotite is mandatory and river rocks explode."}}
  ]
}}
"""

    for model_id in get_active_gemini_model(GEMINI_API_KEY):
        for attempt in range(2):
            try:
                endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json"
                    }
                }
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=40) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)
                    parsed = json.loads(raw_text)
                    if "specs" in parsed and "hardware_bundle" in parsed:
                        time.sleep(6)
                        return parsed
            except urllib.error.HTTPError as he:
                if he.code == 429:
                    print(f"[RATE-LIMIT] HTTP 429 on {model_id} (attempt {attempt + 1}). Cooling down 20s...")
                    time.sleep(20)
                else:
                    print(f"[WARN] HTTP {he.code} on {model_id} for '{item_name}': {he}")
                    break
            except Exception as e:
                print(f"[WARN] Gemini ({model_id}) notice for '{item_name}': {e}")
                break

    return det_fallback


def build_sauna_html_page(data, slug, mon_cfg):
    sauna_name = data.get("sauna_name", "Electric Sauna Heater System")
    sp = data.get("specs", {})
    len_ft = round(safe_float(sp.get("length_ft", 7.0), 7.0), 1)
    wid_ft = round(safe_float(sp.get("width_ft", 6.0), 6.0), 1)
    hgt_ft = round(safe_float(sp.get("height_ft", 7.0), 7.0), 1)
    raw_cu = int(safe_float(sp.get("raw_volume_cuft", 294), 294))
    glass_sq = int(safe_float(sp.get("glass_stone_sqft", 18), 18))
    adj_cu = int(safe_float(sp.get("adjusted_volume_cuft", 564), 564))
    kw = round(safe_float(sp.get("recommended_heater_kw", 8.0), 8.0), 1)
    amps = round(safe_float(sp.get("running_amps_240v", 33.3), 33.3), 1)
    brk_a = int(safe_float(sp.get("required_breaker_amps", 40), 40))
    wire_awg = sp.get("recommended_wire_awg", "8/2 AWG Stranded Copper (90°C)")
    stone_lbs = int(safe_float(sp.get("olivine_stone_lbs", 60), 60))
    sess_cost = round(safe_float(sp.get("cost_per_session_usd", 1.47), 1.47), 2)

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "240V+Electric+Sauna+Heater+Harvia+Sauna+Stones"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{sauna_name} kW Heater, Adjusted Cubic Feet & Breaker Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "Electric Sauna Heater")), mon_cfg)
        bundle_html += f"""
        <div class="bg-stone-900 border border-stone-800 rounded-xl p-5 flex flex-col justify-between hover:border-amber-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'Sauna Gear')}</span>
              <span class="text-sm font-bold text-emerald-400">{item.get('price_range', '$59+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-stone-400 mt-2 leading-relaxed">🧖 {item.get('sauna_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-amber-500 hover:bg-amber-400 text-stone-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build Sauna Heater kW vs Adjusted Cubic Volume, Amps & Wire Gauge Reference Matrix Table
    sauna_tiers = [
        ("3.0 kW (240V / 12.5A)", "100 – 150 Adj. Cu Ft", "20A 2-Pole Breaker", "12/2 AWG Copper (90°C)", "35 – 45 lbs Stones"),
        ("4.5 kW (240V / 18.8A)", "150 – 210 Adj. Cu Ft", "25A / 30A 2-Pole Brk", "10/2 AWG Copper (90°C)", "45 – 50 lbs Stones"),
        ("6.0 kW (240V / 25.0A)", "210 – 300 Adj. Cu Ft", "30A / 35A 2-Pole Brk", "10/2 AWG Copper (90°C)", "50 – 90 lbs Stones"),
        ("8.0 kW (240V / 33.3A)", "300 – 425 Adj. Cu Ft", "40A / 45A 2-Pole Brk", "8/2 AWG Copper (90°C)", "50 – 125 lbs Stones"),
        ("9.0 kW (240V / 37.5A)", "400 – 500 Adj. Cu Ft", "50A 2-Pole Breaker", "6/2 or 8/2 AWG (90°C)", "60 – 150 lbs Stones"),
        ("10.5 kW (240V / 43.8A)", "475 – 600 Adj. Cu Ft", "60A 2-Pole + Contactor", "6/2 AWG Copper (90°C)", "110 – 200 lbs Stones")
    ]
    matrix_rows_html = ""
    for kw_lbl, acf_lbl, br_lbl, wi_lbl, st_lbl in sauna_tiers:
        matrix_rows_html += f"""
        <tr class="border-b border-stone-800 hover:bg-stone-800/40">
          <td class="py-3 px-4 font-bold text-white">{kw_lbl}</td>
          <td class="py-3 px-4 font-bold text-amber-400">{acf_lbl}</td>
          <td class="py-3 px-4 text-emerald-400 font-semibold">{br_lbl}</td>
          <td class="py-3 px-4 text-stone-300">{wi_lbl}</td>
          <td class="py-3 px-4 text-xs text-stone-300">{st_lbl}</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("builder_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-stone-900 border border-stone-800 rounded-xl p-4 cursor-pointer hover:border-stone-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-amber-500 rounded cursor-pointer sauna-check">
          <span class="text-sm text-stone-200 leading-relaxed"><strong>Sauna Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-stone-900 border border-stone-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-stone-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', sauna_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', sauna_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-stone-950 text-stone-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-stone-800 bg-stone-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-amber-500 text-stone-950 px-2 py-0.5 rounded font-black">SAUNA</span>kWIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-amber-500 hover:bg-amber-400 text-stone-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Sauna Heaters & Stones →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-amber-500 text-stone-950 px-3 py-1 rounded-full">{kw} kW Heater ({amps}A @ 240V)</span>
        <span class="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">Raw: {raw_cu} ft³ → Adjusted: {adj_cu} ft³</span>
        <span class="text-xs font-semibold bg-stone-800 text-stone-300 px-3 py-1 rounded-full">{brk_a}A Breaker ({wire_awg.split()[0]} AWG) | {stone_lbs} lbs Rocks</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', sauna_name)}</h1>
      <div class="mt-4 bg-stone-900 border-l-4 border-amber-500 p-4 rounded-r-xl text-sm text-stone-200 leading-relaxed">
        <strong>Finnish Thermal & NEC 424 Sizing Verdict:</strong> {data.get('thermal_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE SAUNA ADJUSTED CUBIC FEET, HEATER KW & 240V BREAKER CALCULATOR -->
    <section class="bg-stone-900 border border-stone-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {sauna_name} kW, Glass Penalty & Wire Calculator</h2>
      <p class="text-xs text-stone-400 mb-6">Adjust your sauna room dimensions, uninsulated glass door/window area, and wall construction to compute exact Adjusted Cubic Feet (ACF), required heater kW, and 240V breaker/wire gauge.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div class="grid grid-cols-3 gap-3">
            <div>
              <div class="flex justify-between text-xs font-medium mb-1">
                <label for="lenSlider" class="text-stone-300">Length (Ft)</label>
                <span class="text-amber-400 font-bold"><span id="lenVal">{len_ft}</span>'</span>
              </div>
              <input id="lenSlider" type="range" min="3.5" max="12.0" step="0.5" value="{len_ft}" class="w-full accent-amber-500 cursor-pointer">
            </div>
            <div>
              <div class="flex justify-between text-xs font-medium mb-1">
                <label for="widSlider" class="text-stone-300">Width (Ft)</label>
                <span class="text-amber-400 font-bold"><span id="widVal">{wid_ft}</span>'</span>
              </div>
              <input id="widSlider" type="range" min="3.5" max="10.0" step="0.5" value="{wid_ft}" class="w-full accent-amber-500 cursor-pointer">
            </div>
            <div>
              <div class="flex justify-between text-xs font-medium mb-1">
                <label for="hgtSlider" class="text-stone-300">Height (Ft)</label>
                <span class="text-amber-400 font-bold"><span id="hgtVal">{hgt_ft}</span>'</span>
              </div>
              <input id="hgtSlider" type="range" min="6.0" max="8.5" step="0.5" value="{hgt_ft}" class="w-full accent-amber-500 cursor-pointer">
            </div>
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="glassSlider" class="text-stone-300">Glass Door, Window & Tile/Stone Wall Area (Sq Ft — +15 ft³/ft²)</label>
              <span class="text-amber-400 font-bold"><span id="glassVal">{glass_sq}</span> sq ft</span>
            </div>
            <input id="glassSlider" type="range" min="0" max="65" step="2" value="{glass_sq}" class="w-full accent-amber-500 cursor-pointer">
          </div>

          <div>
            <label for="wallTypeSelect" class="block text-xs font-medium text-stone-400 mb-1">Sauna Wall Construction & Insulation</label>
            <select id="wallTypeSelect" class="w-full bg-stone-950 border border-stone-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500">
              <option value="1.00" selected>Insulated R-13 Stud Wall + Foil Vapor Barrier (1.0x)</option>
              <option value="1.20">Outdoor Uninsulated 1.5" Cedar Barrel Sauna (+20% ACF)</option>
              <option value="1.30">Heavy Timber Log Cabin Wall without Foil (+30% ACF)</option>
            </select>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-stone-950 border border-amber-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-amber-400 font-bold">Required Heater Size</span>
            <div class="text-2xl sm:text-3xl font-black text-white mt-1"><span id="kwOut">{kw}</span> <span class="text-sm font-normal text-stone-400">kW</span></div>
            <p id="acfOut" class="text-xs text-amber-400 font-semibold mt-1">{adj_cu} Adj. Cu Ft ({raw_cu} Raw)</p>
          </div>

          <div class="bg-stone-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">240V Breaker & Wire</span>
            <div id="brkWireOut" class="text-xl sm:text-2xl font-black text-emerald-400 mt-1">{brk_a}A ({wire_awg.split()[0]} AWG)</div>
            <p id="ampCostOut" class="text-xs text-stone-300 font-semibold mt-1">{amps}A Draw (~${sess_cost}/session)</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-amber-950/40 border border-amber-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="saunaAdviceBanner" class="text-sm text-amber-100 font-medium"></div>
        <a id="dynamicSaunaBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-amber-500 hover:bg-amber-400 text-stone-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched Sauna Heater & Rocks on Amazon →
        </a>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {sauna_name} Heater, Olivine Rocks & Foil Kit</h2>
        <span class="text-xs text-stone-400">UL-875 & NEC Article 424 Compliant</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">Electric Sauna Heater kW, Adjusted Cubic Feet, 240V Breaker & Wire Chart</h2>
      <div class="overflow-x-auto bg-stone-900 border border-stone-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-stone-800 bg-stone-950/60 text-stone-400 uppercase text-xs">
              <th class="py-3.5 px-4">Heater Rating & Amps</th>
              <th class="py-3.5 px-4 text-amber-400">Adjusted Cubic Volume</th>
              <th class="py-3.5 px-4 text-emerald-400">NEC 240V Breaker</th>
              <th class="py-3.5 px-4">90°C Copper Wire</th>
              <th class="py-3.5 px-4">Olivine Stone Load</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Finnish Sauna Foil Barrier, Ventilation & Wiring Checklist</h2>
        <span id="saunaBadge" class="text-xs font-bold bg-stone-800 text-amber-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({sauna_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-stone-800 py-8 text-center text-xs text-stone-500 px-4">
    <p>© {datetime.now(timezone.utc).year} SaunakWIndex. Independent Finnish Sauna Thermodynamics & NEC 424 Electrical Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const lenSlider = document.getElementById('lenSlider');
    const widSlider = document.getElementById('widSlider');
    const hgtSlider = document.getElementById('hgtSlider');
    const glassSlider = document.getElementById('glassSlider');
    const wallTypeSelect = document.getElementById('wallTypeSelect');
    const lenVal = document.getElementById('lenVal');
    const widVal = document.getElementById('widVal');
    const hgtVal = document.getElementById('hgtVal');
    const glassVal = document.getElementById('glassVal');
    const kwOut = document.getElementById('kwOut');
    const acfOut = document.getElementById('acfOut');
    const brkWireOut = document.getElementById('brkWireOut');
    const ampCostOut = document.getElementById('ampCostOut');
    const saunaAdviceBanner = document.getElementById('saunaAdviceBanner');
    const dynamicSaunaBtn = document.getElementById('dynamicSaunaBtn');

    function recalculateSauna() {{
      const lFt = parseFloat(lenSlider.value);
      const wFt = parseFloat(widSlider.value);
      const hFt = parseFloat(hgtSlider.value);
      const glSqft = parseInt(glassSlider.value, 10);
      const wallMult = parseFloat(wallTypeSelect.value);

      lenVal.textContent = lFt.toFixed(1);
      widVal.textContent = wFt.toFixed(1);
      hgtVal.textContent = hFt.toFixed(1);
      glassVal.textContent = glSqft;

      const rawCu = Math.round(lFt * wFt * hFt);
      const glPenalty = glSqft * 15;
      const adjCu = Math.round((rawCu + glPenalty) * wallMult);

      let stdKw = 4.5;
      let brkSpec = "30A (10/2 AWG)";
      if (adjCu <= 150) {{
        stdKw = 3.0; brkSpec = "20A (12/2 AWG)";
      }} else if (adjCu <= 215) {{
        stdKw = 4.5; brkSpec = "30A (10/2 AWG)";
      }} else if (adjCu <= 315) {{
        stdKw = 6.0; brkSpec = "30A/35A (10/2 AWG)";
      }} else if (adjCu <= 425) {{
        stdKw = 8.0; brkSpec = "40A (8/2 AWG)";
      }} else if (adjCu <= 510) {{
        stdKw = 9.0; brkSpec = "50A (6/2 or 8/2 AWG)";
      }} else {{
        stdKw = 10.5; brkSpec = "60A (6/2 AWG)";
      }}

      const amps240 = ((stdKw * 1000.0) / 240.0).toFixed(1);
      const sessUsd = (stdKw * 1.15 * 0.16).toFixed(2);
      const foilSqft = Math.ceil((((2.0 * (lFt + wFt) * hFt) + (lFt * wFt)) * 1.15) / 10) * 10;

      kwOut.textContent = stdKw.toFixed(1);
      acfOut.textContent = `${{adjCu}} Adj. Cu Ft (${{rawCu}} Raw)`;
      brkWireOut.textContent = brkSpec;
      ampCostOut.textContent = `${{amps240}}A Draw (~$${{sessUsd}}/session)`;

      saunaAdviceBanner.innerHTML = `🧖 <strong>Finnish Build Spec:</strong> Your <strong>${{adjCu}} Adjusted Cu. Ft.</strong> room requires a <strong>${{stdKw.toFixed(1)}} kW 240V Sauna Heater</strong> on a <strong>${{brkSpec}} 90°C circuit</strong>, <strong>50–110 lbs of Olivine Diabase Stones</strong>, and <strong>${{foilSqft}} sq ft of Aluminum Foil Vapor Barrier</strong>.`;
      dynamicSaunaBtn.href = `https://${{amzDomain}}/s?k=${{stdKw}}kW+240V+Electric+Sauna+Heater+Harvia+Olivine+Sauna+Stones&tag=${{amzTag}}`;
    }}

    lenSlider.addEventListener('input', recalculateSauna);
    widSlider.addEventListener('input', recalculateSauna);
    hgtSlider.addEventListener('input', recalculateSauna);
    glassSlider.addEventListener('input', recalculateSauna);
    wallTypeSelect.addEventListener('change', recalculateSauna);
    recalculateSauna();

    const checks = document.querySelectorAll('.sauna-check');
    const badge = document.getElementById('saunaBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "240V+Electric+Sauna+Heater+Harvia+Sauna+Stones"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-stone-900 border border-stone-800 hover:border-amber-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-amber-500 text-stone-950 px-2.5 py-0.5 rounded">{item.get('kw', 8.0)} kW ({item.get('brk_a', 40)}A Brk)</span>
            <span class="text-xs text-stone-400">Adj: {item.get('adj_cu', 380)} ft³ | {item.get('stones', 60)} lb Rocks</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-amber-400 transition">{item['sauna_name']}</h2>
          <p class="text-xs text-stone-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-amber-400">Calculate kW, Glass Penalty & Wire →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SaunakWIndex — Electric Sauna Heater kW, Adjusted Cubic Feet & Breaker Calculator (2026)</title>
  <meta name="description" content="Calculate exact Finnish and barrel sauna heater kW capacity, Adjusted Cubic Feet (with glass door and log penalties), NEC 240V breaker/wire gauge, and olivine stone weight for Harvia, Huum, Vevor, and Finlandia heaters.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="SaunakWIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-stone-950 text-stone-100 min-h-screen flex flex-col">
  <header class="border-b border-stone-800 bg-stone-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-amber-500 text-stone-950 px-2 py-0.5 rounded font-black">SAUNA</span>kWIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-amber-500 hover:bg-amber-400 text-stone-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Sauna Heaters & Stones →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">Sauna Heater kW, Adjusted Cubic Volume & 240V Breaker Database</h1>
      <p class="text-stone-400 mt-3 text-base sm:text-lg">Select your sauna heater model or cedar room dimensions below to calculate Adjusted Cubic Feet (including glass door and uninsulated barrel log penalties), 240V breaker/wire AWG, and olivine stone mass.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search heater or sauna size (e.g. Harvia KIP 6kW, 8kW, Huum Drop, Vevor, 6x8 Sauna, Barrel Sauna...)" class="w-full bg-stone-900 border border-stone-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-amber-500">
      </div>
    </div>

    <div id="saunaGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-stone-800 py-8 text-center text-xs text-stone-500">
    <p>© {datetime.now(timezone.utc).year} SaunakWIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('saunaGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>SaunakWIndex Finnish & Barrel Sauna Heater Sizing Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive Electric Sauna Heater kW, Adjusted Cubic Feet & 240V Breaker Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    """Multi-Endpoint Search Engine Pinger (IndexNow Global + Bing + Google WebSub)."""
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    for idx_endpoint in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]:
        try:
            req = urllib.request.Request(
                idx_endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                print(f"[INDEXNOW] Pushed {len(new_urls)} URLs to {idx_endpoint} (HTTP {resp.status})")
                break
        except Exception as e:
            print(f"[WARN] IndexNow ({idx_endpoint}) notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published if "slug" in item}

    candidates = []
    if CUSTOM_SAUNA:
        candidates.append((CUSTOM_SAUNA.strip(), 7.0, 6.0, 7.0, 18, 8.0, 60))
    candidates.extend(SEED_SAUNAS)
    candidates.extend(discover_google_sauna_queries(published_slugs))

    new_urls = []
    count = 0

    for sauna_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        s_name = sauna_tuple[0]
        slug = slugify(f"{s_name}-kw-breaker-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating sauna heater kW & Adjusted Cubic Feet calculator for: {s_name}...")
        try:
            data = generate_sauna_data(sauna_tuple)
            build_sauna_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "sauna_name": data.get("sauna_name", s_name),
                "slug": slug,
                "title": data.get("seo_title", f"{s_name} Sauna Calculator"),
                "description": data.get("meta_description", ""),
                "kw": round(safe_float(sp.get("recommended_heater_kw", sauna_tuple[5]), sauna_tuple[5]), 1),
                "brk_a": int(safe_float(sp.get("required_breaker_amps", 40), 40)),
                "adj_cu": int(safe_float(sp.get("adjusted_volume_cuft", 380), 380)),
                "stones": int(safe_float(sp.get("olivine_stone_lbs", sauna_tuple[6]), sauna_tuple[6])),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            if count < PAGES_PER_RUN:
                time.sleep(15)
        except Exception as e:
            print(f"[ERROR] Failed building {s_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new electric sauna heater kW calculator pages.")


if __name__ == "__main__":
    main()
