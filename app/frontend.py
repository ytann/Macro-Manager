import streamlit as st
import httpx
import asyncio
import base64
import streamlit.components.v1 as components

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="MacroManager", page_icon="🥗", layout="centered")

# --- Helpers for Async Calls in Streamlit ---
async def async_get(url):
    async with httpx.AsyncClient() as client:
        return await client.get(url)

async def async_post(url, json_data):
    async with httpx.AsyncClient() as client:
        return await client.post(url, json=json_data)

async def async_delete(url):
    async with httpx.AsyncClient() as client:
        return await client.delete(url)

# --- Voice Input Handling ---
query_params = st.query_params
voice_text = query_params.get("voice_text")

st.title("🥗 MacroManager")

# --- HERO SECTION: Daily Totals ---
st.subheader("📅 Daily Progress")
try:
    response = asyncio.run(async_get(f"{API_URL}/summary"))
    if response.status_code == 200:
        data = response.json()
        consumed = data.get('consumed', {})
        goals = data.get('goals', {})
        grouped = data.get('grouped', {})
        
        metrics = [
            ("Calories", "calories", "kcal"),
            ("Protein", "protein", "g"),
            ("Carbs", "carbs", "g"),
            ("Fat", "fat", "g"),
        ]
        
        cols = st.columns(4)
        for i, (label, key, unit) in enumerate(metrics):
            with cols[i]:
                goal = goals.get(key, 1.0)
                val = consumed.get(key, 0.0)
                progress = min(val / goal, 1.0) if goal > 0 else 0.0
                
                st.write(f"**{label}**")
                st.progress(progress)
                remaining = max(goal - val, 0.0)
                st.caption(f"{val:.1f}/{goal:.1f} {unit}")
                st.caption(f"📉 {remaining:.1f} {unit} left")
        
        with st.expander("🔍 View Micronutrients"):
            sub_cols = st.columns(4)
            sub_cols[0].metric("Fiber", f"{consumed.get('fiber', 0):.1f}g")
            sub_cols[1].metric("Sugar", f"{consumed.get('sugar', 0):.1f}g")
            sub_cols[2].metric("Sat Fat", f"{consumed.get('saturated_fat', 0):.1f}g")
            sub_cols[3].metric("Unsat Fat", f"{consumed.get('unsaturated_fat', 0):.1f}g")
    else:
        st.error("Could not fetch summary data.")
except Exception as e:
    st.error(f"Connection Error: {e}")

st.divider()

# --- LOGGING SECTION ---
st.subheader("📝 Log Food")
tabs = st.tabs(["⌨️ Text", "📸 Camera"])

with tabs[0]:
    # We use columns to place the record button next to the text input
    with st.form("log_form"):
        meal_type = st.selectbox("Meal Type", ["Breakfast", "Lunch", "Dinner", "Snack", "General"])
        
        col1, col2 = st.columns([0.85, 0.15])
        with col1:
            user_input = st.text_input("What did you eat?", value=voice_text, placeholder="e.g. 200g chicken breast and 100g brown rice")
        with col2:
            # Voice recording button using Web Speech API
            # We use a custom HTML component to handle the 'Hold to Record' logic
            voice_btn_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body { margin: 0; padding: 0; overflow: hidden; display: flex; align-items: flex-end; height: 100vh; }
                    #record-btn {
                        width: 50px; 
                        height: 50px; 
                        border-radius: 50%; 
                        border: none; 
                        background-color: #ef4444; 
                        color: white; 
                        cursor: pointer; 
                        font-size: 20px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                        transition: background-color 0.2s;
                        margin-bottom: 5px;
                    }
                    #record-btn:disabled {
                        background-color: #9ca3af !important;
                        cursor: not-allowed;
                        opacity: 0.6;
                    }
                </style>
            </head>
            <body>
                <button id="record-btn">🎤</button>
                <script>
                    const btn = document.getElementById('record-btn');
                    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

                    if (!SpeechRecognition) {
                        btn.disabled = true;
                        btn.title = "Browser not supported";
                        alert('Voice logging is not supported in this browser. Please try Chrome or Brave.');
                    } else {
                        const recognition = new SpeechRecognition();
                        recognition.continuous = false;
                        recognition.interimResults = false;
                        recognition.lang = 'en-US';

                        btn.onmousedown = () => {
                            btn.style.backgroundColor = '#b91c1c';
                            try {
                                recognition.start();
                            } catch (e) {
                                console.error('Recognition already started');
                            }
                        };

                        btn.onmouseup = () => {
                            btn.style.backgroundColor = '#ef4444';
                            recognition.stop();
                        };

                        btn.ontouchstart = (e) => {
                            e.preventDefault();
                            btn.onmousedown();
                        };
                        btn.ontouchend = (e) => {
                            e.preventDefault();
                            btn.onmouseup();
                        };

                        recognition.onresult = (event) => {
                            const text = event.results[0][0].transcript;
                            window.top.location.href = `?voice_text=${encodeURIComponent(text)}`;
                        };

                        recognition.onerror = (event) => {
                            let message = 'Speech Recognition Error: ' + event.error;
                            if (event.error === 'not-allowed') {
                                message = 'Permission Denied: Please allow microphone access in your browser settings.';
                            } else if (event.error === 'network') {
                                message = 'Network Error: Unable to reach speech servers. Please check your internet or try refreshing.';
                            } else if (event.error === 'no-speech') {
                                message = 'No speech detected. Please try again.';
                            }
                            alert(message);
                            btn.style.backgroundColor = '#ef4444';
                        };

                        recognition.onend = () => {
                            btn.style.backgroundColor = '#ef4444';
                        };
                    }
                </script>
            </body>
            </html>
            """
            b64_html = base64.b64encode(voice_btn_html.encode()).decode()
            st.iframe(src=f"data:text/html;base64,{b64_html}", height=70)

        submit_button = st.form_submit_button("Log Meal")
        
        if submit_button:
            if user_input:
                try:
                    with st.spinner("Parsing and logging food..."):
                        payload = {"text": user_input, "meal_type": meal_type}
                        response = asyncio.run(async_post(f"{API_URL}/log", payload))
                        if response.status_code == 200:
                            st.toast("Meal logged successfully! 🥗", icon="✅")
                            st.rerun()
                        else:
                            st.error(f"Error: {response.json().get('detail', 'Failed to log meal')}")
                except Exception as e:
                    st.error(f"Connection Error: {e}")
            else:
                st.warning("Please enter some text first.")

# Automatic Trigger for Voice Logging
if voice_text:
    try:
        # Use the current meal_type selection from session state if available, 
        # otherwise default to the first one in the list
        current_meal_type = st.session_state.get('meal_type', 'Breakfast') 
        # Note: meal_type in the form doesn't update session_state automatically 
        # unless we wrap it in a function. We'll use a default for now or 
        # allow the user to see it in the box before it logs.
        
        # To strictly follow "Automatically trigger the existing Log button", 
        # we simulate the POST request.
        payload = {"text": voice_text, "meal_type": "General"} # Defaulting to General for voice
        response = asyncio.run(async_post(f"{API_URL}/log", payload))
        if response.status_code == 200:
            st.toast("Meal logged via voice! 🎤", icon="✅")
        else:
            st.error(f"Voice log failed: {response.json().get('detail')}")
            
        # Clear query params and rerun to clean UI
        st.query_params.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Voice log error: {e}")

with tabs[1]:
    st.info("Camera logging coming soon! 📸")

st.divider()

# --- FOOD JOURNAL VIEW ---
st.subheader("📖 Daily Food Journal")
try:
    # Use the same summary endpoint to get grouped meals
    response = asyncio.run(async_get(f"{API_URL}/summary"))
    if response.status_code == 200:
        data = response.json()
        grouped = data.get('grouped', {})
        
        if not grouped:
            st.info("No items logged today.")
        else:
            # Map category to emoji
            category_icons = {
                "Breakfast": "🍳",
                "Lunch": "🍱",
                "Dinner": "🌙",
                "Snack": "🍎",
                "General": "🥗"
            }
            
            # Iterate through categories in a fixed order
            for cat in ["Breakfast", "Lunch", "Dinner", "Snack", "General"]:
                if cat in grouped:
                    category_meals = grouped[cat]
                    
                    # Calculate category total calories
                    cat_calories = 0
                    for meal_items in category_meals:
                        cat_calories += sum(item['cals'] for item in meal_items)
                    
                    st.markdown(f"### {category_icons.get(cat, '🍽️')} {cat} — `{cat_calories:.1f} kcal`")
                    
                    with st.container():
                        for meal_items in category_meals:
                            for item in meal_items:
                                sub_macros = item.get('sub_macros') or {}
                                fiber = sub_macros.get('fiber', 0) or 0
                                
                                st.markdown(
                                    f"**{item['name']}** ({item['grams']}g) "
                                    f"→ `{item['cals']:.1f} kcal` | Fiber: `{fiber:.1f}g`"
                                )
    else:
        st.error("Could not fetch journal data.")
except Exception as e:
    st.error(f"Connection Error: {e}")

# --- CLEAR OPTIONS ---
st.divider()
if st.button("🗑️ Clear Daily Macros", use_container_width=True):
    try:
        clear_resp = asyncio.run(async_delete(f"{API_URL}/clear"))
        if clear_resp.status_code == 200:
            st.success("Daily totals cleared!")
            st.rerun()
        else:
            st.error("Failed to clear data.")
    except Exception as e:
        st.error(f"Connection Error: {e}")
