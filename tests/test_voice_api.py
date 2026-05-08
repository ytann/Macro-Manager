import streamlit as st
import streamlit.components.v1 as components
import base64

st.title("🎙️ Voice API Diagnostic")

diagnostic_html = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: sans-serif; display: flex; flex-direction: column; gap: 10px; padding: 20px; }
        .status { padding: 10px; border-radius: 5px; font-weight: bold; }
        .success { background-color: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
        .error { background-color: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
    </style>
</head>
<body>
    <div id="result">Checking API availability...</div>
    <div id="details" style="font-size: 0.9em; color: #666;"></div>

    <script>
        const resultDiv = document.getElementById('result');
        const detailsDiv = document.getElementById('details');

        const sr = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (sr) {
            resultDiv.innerHTML = '<div class="status success">✅ Web Speech API is AVAILABLE</div>';
            detailsDiv.innerHTML = 'Detected: ' + (window.SpeechRecognition ? 'window.SpeechRecognition' : 'window.webkitSpeechRecognition');
        } else {
            resultDiv.innerHTML = '<div class="status error">❌ Web Speech API is NOT available</div>';
            detailsDiv.innerHTML = 'Neither window.SpeechRecognition nor window.webkitSpeechRecognition were found. This is common in Firefox unless enabled in about:config.';
        }
    </script>
</body>
</html>
"""

b64_html = base64.b64encode(diagnostic_html.encode()).decode()
st.iframe(src=f"data:text/html;base64,{b64_html}", height=200)

st.info("Run this with: `streamlit run tests/test_voice_api.py` and check the result in your browser.")
