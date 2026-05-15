import streamlit as st
import httpx
import asyncio
import base64
from app.utils.vision_client import send_vision_log


API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="MacroManager", page_icon="🥗", layout="centered")

# --- Helpers for Sync Calls in Streamlit ---
_client = httpx.Client(timeout=300.0)

def sync_get(url):
    return _client.get(url)

def sync_post(url, json_data):
    return _client.post(url, json=json_data)

def sync_delete(url):
    return _client.delete(url)

async def async_onboard(bio_text: str):
    """Async wrapper for onboarding using the shared sync client."""
    return await asyncio.to_thread(sync_post, f"{API_URL}/onboard", {"bio_text": bio_text})

def render_macro_hud(consumed, goals):
    """Renders a minimalist equidistant glass Macro HUD with 3D flip animations."""
    total_cals = consumed.get('calories', 0.0)
    hud_config = [
        {
            "label": "Protein", 
            "key": "protein", 
            "unit": "g", 
            "color": "rgba(79, 70, 229, 0.2)", 
            "sub": f"Fiber: {consumed.get('fiber', 0):.1f}g",
            "pos": "top: 20px; left: 145px;"
        },
        {
            "label": "Carbs", 
            "key": "carbs", 
            "unit": "g", 
            "color": "rgba(245, 158, 11, 0.2)", 
            "sub": f"Sugar: {consumed.get('sugar', 0):.1f}g",
            "pos": "top: 228px; left: 25px;"
        },
        {
            "label": "Fat", 
            "key": "fat", 
            "unit": "g", 
            "color": "rgba(16, 185, 129, 0.2)", 
            "sub": f"Sat Fat: {consumed.get('saturated_fat', 0):.1f}g",
            "pos": "top: 228px; left: 265px;"
        },
    ]
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
                :root {{
                    --hud-text: white;
                    --hud-glass-border: rgba(255, 255, 255, 0.3);
                    --hud-glass-shadow: inset 0 0 20px rgba(255,255,255,0.1), 0 10px 30px rgba(0, 0, 0, 0.1);
                    --hud-orb-border: rgba(255, 255, 255, 0.4);
                    --hud-orb-shadow: inset 0 0 15px rgba(255,255,255,0.3), 0 10px 25px rgba(0, 0, 0, 0.2);
                }}

                @media (prefers-color-scheme: light) {{
                    :root {{
                        --hud-text: #111827;
                        --hud-glass-border: rgba(0, 0, 0, 0.3);
                        --hud-glass-shadow: inset 0 0 20px rgba(0,0,0,0.1), 0 10px 30px rgba(255, 255, 255, 0.1);
                        --hud-orb-border: rgba(0, 0, 0, 0.4);
                        --hud-orb-shadow: inset 0 0 15px rgba(0,0,0,0.3), 0 10px 25px rgba(255, 255, 255, 0.2);
                    }}
                }}

                body {{
                    margin: 0;
                    padding: 0;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    background-color: transparent;
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    overflow: hidden;
                }}
                .venn-container {{
                    position: relative;
                    width: 550px;
                    height: 500px;
                    perspective: 1000px;
                }}
                .macro-card {{
                    width: 260px;
                    height: 260px;
                    cursor: pointer;
                    position: absolute;
                    transform-style: preserve-3d;
                    transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
                    z-index: 1;
                }}
                .macro-card.flipped {{
                    transform: rotateY(180deg);
                    z-index: 10;
                }}
                .card-face {{
                    position: absolute;
                    width: 100%;
                    height: 100%;
                    backface-visibility: hidden;
                    border-radius: 50%;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    text-align: center;
                    border: 1px solid var(--hud-glass-border);
                    box-shadow: var(--hud-glass-shadow);
                    backdrop-filter: blur(25px);
                    -webkit-backdrop-filter: blur(25px);
                    color: var(--hud-text);
                    padding: 30px;
                    box-sizing: border-box;
                }}
                .card-front {{
                    z-index: 2;
                }}
                .card-back {{
                    transform: rotateY(180deg);
                    background: rgba(255, 255, 255, 0.1);
                }}
                .macro-val {{
                    font-size: 2.8rem;
                    font-weight: 800;
                    margin: 0;
                    text-shadow: 0 2px 8px rgba(0,0,0,0.3);
                }}
                .macro-label {{
                    font-size: 1.2rem;
                    opacity: 0.9;
                    text-transform: uppercase;
                    letter-spacing: 2px;
                    margin-bottom: 10px;
                    font-weight: 600;
                }}
                .macro-goal {{
                    font-size: 0.9rem;
                    opacity: 0.7;
                }}
                .breakdown-title {{
                    font-size: 1.4rem;
                    font-weight: bold;
                    margin-bottom: 12px;
                }}
                .breakdown-item {{
                    font-size: 1rem;
                    margin: 6px 0;
                }}
                .calorie-orb {{
                    position: absolute;
                    top: 228.6px;
                    left: 215px;
                    width: 120px;
                    height: 120px;
                    border-radius: 50%;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    text-align: center;
                    border: 1px solid var(--hud-orb-border);
                    box-shadow: var(--hud-orb-shadow);
                    backdrop-filter: blur(25px);
                    -webkit-backdrop-filter: blur(25px);
                    color: var(--hud-text);
                    z-index: 20;
                    pointer-events: none;
                    background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.4) 0%, rgba(255,255,255,0) 60%), rgba(255, 255, 255, 0.3);
                }}
                .orb-val {{
                    font-size: 1.3rem;
                    font-weight: 800;
                    text-shadow: 0 2px 8px rgba(0,0,0,0.3);
                }}
                .orb-label {{
                    font-size: 0.7rem;
                    text-transform: uppercase;
                    opacity: 0.8;
                    letter-spacing: 1px;
                }}
                .macro-alert {{
                    position: absolute;
                    top: -25px;
                    font-size: 1.5rem;
                    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5));
                    z-index: 11;
                }}
            </style>
    
        </head>
        <body>
            <div class="venn-container">
                <div class="calorie-orb">
                    <div class="orb-label">Total</div>
                    <div class="orb-val">🔥 {total_cals:.1f} kcal</div>
                </div>
        """
    
    for item in hud_config:
        val = consumed.get(item['key'], 0.0)
        goal = goals.get(item['key'], 1.0)
        ratio = val / goal if goal > 0 else 0
        clamped_ratio = min(ratio, 1.0)
        
        # Dynamic fill: from bottom (180deg)
        # If val is 0, we use a transparent fallback
        if val > 0:
            fill_color = item['color'].replace('0.2', '0.5') # Slightly more opaque for fill
            gloss_bg = f"conic-gradient(from 180deg, {fill_color} {clamped_ratio*100:.0f}%, transparent {clamped_ratio*100:.0f}%), radial-gradient(circle at 30% 30%, rgba(255,255,255,0.3) 0%, rgba(255,255,255,0) 60%), {item['color']}"
        else:
            gloss_bg = f"radial-gradient(circle at 30% 30%, rgba(255,255,255,0.3) 0%, rgba(255,255,255,0) 60%), {item['color']}"
        
        # Alert Logic
        alert_html = ""
        if ratio > 1.0:
            if item['key'] == 'protein':
                alert_html = '<div class="macro-alert">🟢!</div>'
            else:
                alert_html = '<div class="macro-alert">⚠️</div>'
        
        html_content += f"""
        <div class="macro-card" style="{item['pos']}" onclick="this.classList.toggle('flipped')">
            {alert_html}
            <div class="card-face card-front" style="background: {gloss_bg};">
                <div class="macro-label">{item['label']}</div>
                <div class="macro-val">{val:.1f}{item['unit']}</div>
                <div class="macro-goal">Goal: {goal:.1f}{item['unit']}</div>
            </div>
            <div class="card-face card-back" style="background: {item['color']};">
                <div class="breakdown-title">{item['label']}</div>
                <div class="breakdown-item">Total: {val:.1f}{item['unit']}</div>
                <div class="breakdown-item">{item['sub']}</div>
            </div>
        </div>
        """
        
    html_content += """
        </div>
    </body>
    </html>
    """
    return html_content

# --- Voice Input Handling ---
query_params = st.query_params
voice_text = query_params.get("voice_text")

# Initialize session state for reruns
if "log_success" not in st.session_state:
    st.session_state.log_success = False
if "polling_meal_id" not in st.session_state:
    st.session_state.polling_meal_id = None
if "extracted_items" not in st.session_state:
    st.session_state.extracted_items = []

if st.session_state.log_success:
    st.session_state.log_success = False
    st.rerun()

st.title("🥗 MacroManager")

# --- HERO SECTION: Daily Totals ---
st.subheader("📅 Daily Progress")
try:
    response = sync_get(f"{API_URL}/summary")
    if response.status_code == 200:
        full_data = response.json()
        
        # Backward compatibility: handle both new (wrapped in 'daily') and old structures
        if 'daily' in full_data:
            daily_data = full_data.get('daily', {})
            weekly_data = full_data.get('weekly', {})
        else:
            daily_data = full_data
            weekly_data = {}
            
        consumed = daily_data.get('consumed', {})
        goals = daily_data.get('goals', {})
        
        # Render Interactive Glass HUD with dynamic ceilings
        dynamic_goals = goals.copy()
        
        # Capped Rollover (Cheat Bank) Calculations
        days_active = weekly_data.get("days_logged", 1)
        daily_carb_goal = goals.get("carbs", 200.0)
        daily_fat_goal = goals.get("fat", 65.0)
        
        carb_savings = max(0, (daily_carb_goal * days_active) - weekly_data.get("carbs", 0.0))
        carb_cheat_bank = min(carb_savings, daily_carb_goal * 0.3) if carb_savings > 0 else 0.0
        dynamic_goals['carbs'] = daily_carb_goal + carb_cheat_bank
        
        fat_savings = max(0, (daily_fat_goal * days_active) - weekly_data.get("fat", 0.0))
        fat_cheat_bank = min(fat_savings, daily_fat_goal * 0.3) if fat_savings > 0 else 0.0
        dynamic_goals['fat'] = daily_fat_goal + fat_cheat_bank
        
        if carb_cheat_bank > (daily_carb_goal * 0.25) or fat_cheat_bank > (daily_fat_goal * 0.25):
            st.success("🎉 You've been consistent! You have a cheat meal banked (up to +30% macros today).")

        hud_html = render_macro_hud(consumed, dynamic_goals)
        st.iframe(src=f"data:text/html;base64,{base64.b64encode(hud_html.encode()).decode()}", height=500)

        # --- 🗓️ 7-Day Rolling Buffer ---
        st.subheader("🗓️ 7-Day Rolling Buffer")
        
        # Fix: Always use 7-day capacity as visual maximum
        w_carb_max = goals.get("carbs", 200.0) * 7
        w_fat_max = goals.get("fat", 65.0) * 7
        
        w_carb_consumed = weekly_data.get("carbs", 0.0)
        w_fat_consumed = weekly_data.get("fat", 0.0)
        
        # Render Progress Bars (capped at 1.0)
        st.markdown("**Weekly Carbs**")
        st.progress(min(w_carb_consumed / w_carb_max, 1.0) if w_carb_max > 0 else 0.0, text=f"{w_carb_consumed:.1f} / {w_carb_max:.1f}g")
        
        st.markdown("**Weekly Fats**")
        st.progress(min(w_fat_consumed / w_fat_max, 1.0) if w_fat_max > 0 else 0.0, text=f"{w_fat_consumed:.1f} / {w_fat_max:.1f}g")
        
        # Insulin Ceiling Calculations
        daily_carb_goal = goals.get("carbs", 200.0)
        daily_fat_goal = goals.get("fat", 65.0)
        today_carb = consumed.get('carbs', 0.0)
        today_fat = consumed.get('fat', 0.0)
        
        # Carb Ceiling
        standard_carb_buffer_left = w_carb_max - w_carb_consumed
        todays_carb_ceiling_left = (daily_carb_goal * 1.3) - today_carb
        allowable_carb_today = min(standard_carb_buffer_left, todays_carb_ceiling_left)
        
        # Fat Ceiling
        standard_fat_buffer_left = w_fat_max - w_fat_consumed
        todays_fat_ceiling_left = (daily_fat_goal * 1.3) - today_fat
        allowable_fat_today = min(standard_fat_buffer_left, todays_fat_ceiling_left)
        
        if todays_carb_ceiling_left <= 0 or todays_fat_ceiling_left <= 0:
            st.error("🚨 130% Daily Limit Reached. Weekly buffer locked to prevent insulin spike.")
        else:
            st.info(f"**Allowable today (Insulin Guardrail):** Carbs: {max(0, allowable_carb_today):.1f}g | Fats: {max(0, allowable_fat_today):.1f}g")

        # Empathetic Messaging
        daily_carb_limit = goals.get("carbs", 200.0)
        daily_prot_limit = goals.get("protein", 150.0)
        
        if consumed.get('carbs', 0) > daily_carb_limit and w_carb_consumed < w_carb_max:
            st.info("You are over your daily carbs, but don't stress! You are still perfectly within your weekly buffer. Enjoy your meal.")
        
        if consumed.get('protein', 0) > daily_prot_limit:
            st.success("Great job hitting high protein! This helps stabilize your blood sugar.")
        
        with st.expander("🧬 Profile & Onboarding"):
            st.markdown("### 🧬 PCOS Baseline Calibrator")
            bio_text = st.text_area("Tell MacroManager about yourself", 
                                   placeholder="e.g., 'I am 28 years old, 160cm, 65kg, want to maintain my weight, and work a desk job'")
            
            if st.button("Calibrate Macros"):
                if bio_text:
                    with st.spinner("Applying PCOS metabolic adjustments..."):
                        try:
                            # Use asyncio.run to call the async helper from sync Streamlit
                            response = asyncio.run(async_onboard(bio_text))
                            if response.status_code == 200:
                                macros = response.json().get("macros", {})
                                st.success(f"Calibration complete! 🎯\n\n**Target Calories:** {macros.get('calories')} kcal\n\n**Macros:** P: {macros.get('protein')}g | C: {macros.get('carbs')}g | F: {macros.get('fat')}g")
                                st.rerun()
                            else:
                                st.error(f"Calibration failed: {response.json().get('detail', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"Connection Error: {e}")
                else:
                    st.warning("Please provide your bio details first.")

        with st.expander("⚙️ Goal Settings"):



            g_col1, g_col2 = st.columns(2)
            with g_col1:
                g_prot = st.number_input("Protein (g)", value=float(goals.get("protein", 150.0)), min_value=0.0)
                g_carb = st.number_input("Carbs (g)", value=float(goals.get("carbs", 200.0)), min_value=0.0)
            with g_col2:
                g_fat = st.number_input("Fat (g)", value=float(goals.get("fat", 65.0)), min_value=0.0)
                g_cal = st.number_input("Calories (kcal)", value=float(goals.get("calories", 2000.0)), min_value=0.0)
            
            if st.button("Save Goals"):
                payload = {"protein": g_prot, "carbs": g_carb, "fat": g_fat, "calories": g_cal}
                sync_post(f"{API_URL}/goals", payload)
                st.toast("Goals updated! 🎯")
                st.rerun()

        with st.expander("🧠 Sovereign Memory"):
            st.markdown("### 🧠 Sovereign Memory")
            st.markdown("Teach MacroManager about your specific utensils, allergies, and routines.")
            
            memory_input = st.text_area("New memory fact", placeholder="e.g., 'My dinner plate is 25cm and usually holds 400g of food' or 'I have a severe allergy to peanuts'")
            
            if st.button("Save to Memory"):
                if memory_input:
                    with st.spinner("Integrating into memory..."):
                        try:
                            response = sync_post(f"{API_URL}/memory", {"text": memory_input})
                            if response.status_code == 200:
                                st.toast("Memory updated! 🧠", icon="✅")
                                st.rerun()
                            else:
                                st.error(f"Memory error: {response.json().get('detail', 'Failed to update memory')}")
                        except Exception as e:
                            st.error(f"Connection Error: {e}")
                else:
                    st.warning("Please enter a fact first.")
            
            st.divider()
            st.markdown("**Current Memory:**")
            try:
                # The MemoryService just overwrites the file. 
                # We can fetch the current content via a new endpoint or just read it if we have access.
                # Since the API doesn't have a GET /memory, I should add one or just use the file if I'm on same machine.
                # But frontend is a separate process usually. I should add a GET /memory endpoint in api.py.
                resp = sync_get(f"{API_URL}/memory")
                if resp.status_code == 200:
                    st.markdown(resp.json().get("content", "No memory stored yet."))
                else:
                    st.info("No memory stored yet.")
            except Exception as e:
                st.info("No memory stored yet.")
    else:
        st.error("Could not fetch summary data.")
except Exception as e:
    st.error(f"Connection Error: {e}")

# --- Async Polling UI ---
if st.session_state.polling_meal_id:
    with st.status("🚀 Resolving Nutrition...", expanded=True) as status:
        st.write("Extracted items:")
        for item in st.session_state.extracted_items:
            st.write(f"- {item['name']} ({item['grams']}g) ... ⏳")
        
        # Poll for completion
        import time
        meal_id = st.session_state.polling_meal_id
        completed = False
        for _ in range(30): # 30 second timeout
            time.sleep(1)
            resp = sync_get(f"{API_URL}/log/status/{meal_id}")
            if resp.status_code == 200 and resp.json()["status"] == "completed":
                completed = True
                break
        
        if completed:
            status.update(label="✅ Meal Logged!", state="complete", expanded=False)
            st.session_state.polling_meal_id = None
            st.session_state.extracted_items = []
            st.session_state.log_success = True
            st.rerun()
        else:
            status.update(label="❌ Resolution Timed Out", state="error")
            st.session_state.polling_meal_id = None
            st.session_state.extracted_items = []

st.divider()

# --- LOGGING SECTION ---

st.subheader("📝 Log Food")
tabs = st.tabs(["⌨️ Text", "📸 Camera"])

with tabs[0]:
    # We use columns to place the record button next to the text input
    with st.form("log_form"):
        col_type, col_input, col_voice = st.columns([0.2, 0.65, 0.15])
        
        with col_type:
            meal_type = st.selectbox("Meal Type", ["Breakfast", "Lunch", "Dinner", "Snack", "General"])
        
        with col_input:
            user_input = st.text_input("What did you eat?", value=voice_text, placeholder="e.g. 200g chicken breast and 100g brown rice")
        
        with col_voice:
            # Voice recording button using Web Speech API
            # We use a custom HTML component to handle the 'Hold to Record' logic
            st.iframe(src=f"{API_URL}/static/voice_btn.html", height=70)
     
        submit_button = st.form_submit_button("Log Meal")
    
    success = False
    if submit_button:
        if user_input:
            try:
                with st.spinner("Extracting items..."):
                    payload = {"text": user_input, "meal_type": meal_type, "is_voice": False}
                    response = sync_post(f"{API_URL}/log/start", payload)
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.polling_meal_id = data["meal_id"]
                        st.session_state.extracted_items = data["items"]
                        st.rerun()
                    else:
                        st.error(f"Error: {response.json().get('detail', 'Failed to start logging')}")
            except Exception as e:
                st.error(f"Connection Error: {e}")
        else:
            st.warning("Please enter some text first.")



# Automatic Trigger for Voice Logging
if voice_text:
        try:
            payload = {"text": voice_text, "meal_type": "General", "is_voice": True} # Defaulting to General for voice
            response = sync_post(f"{API_URL}/log/start", payload)
            if response.status_code == 200:
                data = response.json()
                st.session_state.polling_meal_id = data["meal_id"]
                st.session_state.extracted_items = data["items"]
                st.toast("Voice extraction started! 🎤", icon="✅")
            else:
                st.error(f"Voice log failed: {response.json().get('detail')}")
                
            # Clear query params
            st.query_params.clear()
        except Exception as e:
            st.error(f"Voice log error: {e}")
        
        st.rerun()


with tabs[1]:
    environment = st.radio("Environment", ["Home", "Wild"], horizontal=True)
    camera_photo = st.camera_input("Take a picture of your food")
    
    if camera_photo:
        with st.spinner('Gemma 4 is estimating macros...'):
            try:
                result = send_vision_log(camera_photo.getvalue(), environment)
                if result.get("status") == "success":
                    items = result.get("items", [])
                    item_list = ", ".join([f"{i['name']} ({i['calories']} kcal)" for i in items])
                    st.success(f"Extracted: {item_list}")
                    st.session_state.log_success = True
                    st.rerun()
                else:
                    st.error(f"Vision API Error: {result.get('detail', 'Unknown error')}")
            except httpx.HTTPStatusError as err:
                if err.response.status_code == 400:
                    st.warning("No edible food detected in the image.")
                else:
                    st.error(f"Vision API Error: {err}")
            except Exception as e:
                st.error(f"Connection Error: {e}")
st.divider()

# --- FOOD JOURNAL VIEW ---
st.subheader("📖 Daily Food Journal")
try:
    # Fetch detailed meals for chronological timeline
    response = sync_get(f"{API_URL}/meals")
    if response.status_code == 200:
        meals = response.json()
        if not meals:
            st.info("No items logged today.")
        else:
            meals.sort(key=lambda x: x['timestamp'], reverse=True)
            for meal in meals:
                items = meal.get('items', [])
                with st.container():
                    st.markdown(f"🕒 **{meal['timestamp'][:16]}**")
                    for item in items:
                        verified_mark = " ✅" if item.get('verified') else ""
                        sub_macros = item.get('sub_macros') or {}
                        fiber = sub_macros.get('fiber', 0) or 0
                        sugar = sub_macros.get('sugar', 0) or 0
                        sat_fat = sub_macros.get('saturated_fat', 0) or 0
                        st.markdown(
                            f"- {verified_mark} **{item['name']}** ({item['grams']}g) "
                            f"→ `{item['cals']:.1f} kcal` | Fiber: `{fiber:.1f}g` | Sugar: `{sugar:.1f}g` | SatFat: `{sat_fat:.1f}g`"
                        )
                    st.divider()
    else:
        st.error("Could not fetch journal data.")
except Exception as e:
    st.error(f"Connection Error: {e}")


# --- CLEAR OPTIONS ---
st.divider()
if st.button("🗑️ Clear Daily Macros", use_container_width=True):
    try:
        clear_resp = sync_delete(f"{API_URL}/clear")
        if clear_resp.status_code == 200:
            st.success("Daily totals cleared!")
            st.rerun()
        else:
            st.error("Failed to clear data.")
    except Exception as e:
        st.error(f"Connection Error: {e}")
