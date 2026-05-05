import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="MacroManager", page_icon="🥗")

st.title("🥗 MacroManager")

# 1. Text input for food logging
with st.form("log_form"):
    user_input = st.text_input("What did you eat?", placeholder="e.g. 200g chicken breast and 100g brown rice")
    submit_button = st.form_submit_button("Log Meal")

if submit_button:
    if user_input:
        try:
            response = requests.post(f"{API_URL}/log", json={"text": user_input})
            if response.status_code == 200:
                st.success(response.json().get("message", "Meal logged successfully!"))
            else:
                st.error(f"Error: {response.json().get('detail', 'Failed to log meal')}")
        except Exception as e:
            st.error(f"Connection Error: {e}")
    else:
        st.warning("Please enter some text first.")

st.divider()

# 4. Fetch and display daily totals
st.subheader("📅 Daily Totals")
try:
    response = requests.get(f"{API_URL}/summary")
    if response.status_code == 200:
        totals = response.json()
        
        # Layout metrics in columns
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Protein", f"{totals.get('protein', 0):.1f}g")
        col2.metric("Carbs", f"{totals.get('carbs', 0):.1f}g")
        col3.metric("Fat", f"{totals.get('fat', 0):.1f}g")
        col4.metric("Calories", f"{totals.get('calories', 0):.1f} kcal")
        
        # Sub-macros in smaller columns below
        st.write("---")
        sub_col1, sub_col2, sub_col3, sub_col4 = st.columns(4)
        sub_col1.caption(f"Fiber: {totals.get('fiber', 0):.1f}g")
        sub_col2.caption(f"Sugar: {totals.get('sugar', 0):.1f}g")
        sub_col3.caption(f"Sat Fat: {totals.get('saturated_fat', 0):.1f}g")
        sub_col4.caption(f"Unsat Fat: {totals.get('unsaturated_fat', 0):.1f}g")
        
        # Visual bar chart for macros
        macro_data = {
            "Protein": totals.get('protein', 0),
            "Carbs": totals.get('carbs', 0),
            "Fat": totals.get('fat', 0)
        }
        st.bar_chart(macro_data)
        
    else:
        st.error("Could not fetch summary data.")
except Exception as e:
    st.error(f"Connection Error: {e}")

st.divider()

# 5. Individual Food Items View
st.subheader("🥗 Logged Items")
try:
    meals_resp = requests.get(f"{API_URL}/meals")
    if meals_resp.status_code == 200:
        meals = meals_resp.json()
        if not meals:
            st.info("No items logged today.")
        else:
            for meal in meals:
                with st.expander(f"Meal {meal['meal_id']} ({meal['timestamp']})"):
                    for item in meal['items']:
                        st.text(f"• {item['name']}: {item['grams']}g | {item['cals']:.1f} kcal")
    else:
        st.error("Could not fetch meal logs.")
except Exception as e:
    st.error(f"Connection Error: {e}")

# 6. Clear Options
st.divider()
col_clear1, col_clear2 = st.columns(2)
if col_clear1.button("🗑️ Clear Daily Macros"):
    try:
        clear_resp = requests.delete(f"{API_URL}/clear")
        if clear_resp.status_code == 200:
            st.success("Daily totals cleared!")
            st.rerun()
        else:
            st.error("Failed to clear data.")
    except Exception as e:
        st.error(f"Connection Error: {e}")
