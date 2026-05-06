import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="MacroManager", page_icon="🥗", layout="centered")

st.title("🥗 MacroManager")

# --- HERO SECTION: Daily Totals ---
st.subheader("📅 Daily Progress")
try:
    response = requests.get(f"{API_URL}/summary")
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
tabs = st.tabs(["⌨️ Text", "🎙️ Voice", "📸 Camera"])

with tabs[0]:
    with st.form("log_form"):
        meal_type = st.selectbox("Meal Type", ["Breakfast", "Lunch", "Dinner", "Snack", "General"])
        user_input = st.text_input("What did you eat?", placeholder="e.g. 200g chicken breast and 100g brown rice")
        submit_button = st.form_submit_button("Log Meal")
        
        if submit_button:
            if user_input:
                try:
                    with st.spinner("Parsing and logging food..."):
                        payload = {"text": user_input, "meal_type": meal_type}
                        response = requests.post(f"{API_URL}/log", json=payload)
                        if response.status_code == 200:
                            st.toast("Meal logged successfully! 🥗", icon="✅")
                            st.rerun()
                        else:
                            st.error(f"Error: {response.json().get('detail', 'Failed to log meal')}")
                except Exception as e:
                    st.error(f"Connection Error: {e}")
            else:
                st.warning("Please enter some text first.")

with tabs[1]:
    st.info("Voice logging coming soon! 🎙️")

with tabs[2]:
    st.info("Camera logging coming soon! 📸")

st.divider()

# --- FOOD JOURNAL VIEW ---
st.subheader("📖 Daily Food Journal")
try:
    # Use the same summary endpoint to get grouped meals
    response = requests.get(f"{API_URL}/summary")
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
        clear_resp = requests.delete(f"{API_URL}/clear")
        if clear_resp.status_code == 200:
            st.success("Daily totals cleared!")
            st.rerun()
        else:
            st.error("Failed to clear data.")
    except Exception as e:
        st.error(f"Connection Error: {e}")
